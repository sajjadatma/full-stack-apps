"""Add product image metadata, primary constraint, and permission.

Revision ID: tv_product_images_01
Revises: tv_product_stock_threshold_01
Create Date: 2026-09-27

"""

import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "tv_product_images_01"
down_revision = "tv_product_stock_threshold_01"
branch_labels = None
depends_on = None

_NAMESPACE = uuid.UUID("6f1b1e2a-0d6e-4c2b-9f7a-2c5b8d3e4a11")
_PERMISSION_ID = uuid.uuid5(_NAMESPACE, "permission:products.manage_images")


def upgrade() -> None:
    op.add_column(
        "product_image",
        sa.Column(
            "content_type",
            sa.String(length=64),
            nullable=False,
            server_default="application/octet-stream",
        ),
    )
    op.alter_column("product_image", "content_type", server_default=None)

    op.execute(
        sa.text(
            "WITH ranked AS ("
            "SELECT id, row_number() OVER ("
            "PARTITION BY product_id "
            "ORDER BY is_primary DESC, sort_order, created_at NULLS LAST, id"
            ") AS position FROM product_image) "
            "UPDATE product_image AS image SET is_primary = (ranked.position = 1) "
            "FROM ranked WHERE image.id = ranked.id "
            "AND image.is_primary IS DISTINCT FROM (ranked.position = 1)"
        )
    )
    op.create_index(
        "uq_product_image_one_primary_per_product",
        "product_image",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE"),
    )

    op.execute(
        "INSERT INTO permission (id, code, description) "
        f"VALUES ('{_PERMISSION_ID}', 'products.manage_images', 'Manage product images') "
        "ON CONFLICT (code) DO UPDATE SET description = EXCLUDED.description"
    )
    op.execute(
        "INSERT INTO rolepermissionlink (role_id, permission_id) "
        "SELECT DISTINCT rolepermissionlink.role_id, permission.id "
        "FROM rolepermissionlink "
        "JOIN permission AS managed_permission "
        "ON managed_permission.id = rolepermissionlink.permission_id "
        "JOIN permission ON permission.code = 'products.manage_images' "
        "WHERE managed_permission.code IN "
        "('products.create', 'products.update', 'products.delete') "
        "ON CONFLICT (role_id, permission_id) DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM rolepermissionlink WHERE permission_id = "
        "(SELECT id FROM permission WHERE code = 'products.manage_images')"
    )
    op.execute("DELETE FROM permission WHERE code = 'products.manage_images'")
    op.drop_index(
        "uq_product_image_one_primary_per_product", table_name="product_image"
    )
    op.drop_column("product_image", "content_type")
