"""Add TileVision product catalog domain

Revision ID: tv_product_domain_01
Revises: ae77f319a39b
Create Date: 2026-09-26

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "tv_product_domain_01"
down_revision = "ae77f319a39b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "category",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_category_name", "category", ["name"], unique=True)
    op.create_index("ix_category_slug", "category", ["slug"], unique=True)

    op.create_table(
        "brand",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(length=140), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brand_name", "brand", ["name"], unique=True)
    op.create_index("ix_brand_slug", "brand", ["slug"], unique=True)

    op.create_table(
        "product",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("sku", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=4000), nullable=True
        ),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("brand_id", sa.UUID(), nullable=True),
        sa.Column(
            "product_type", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column(
            "material", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column("finish", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column(
            "usage_area", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column(
            "color_family", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column("width_mm", sa.Integer(), nullable=True),
        sa.Column("height_mm", sa.Integer(), nullable=True),
        sa.Column("thickness_mm", sa.Integer(), nullable=True),
        sa.Column("rectified", sa.Boolean(), nullable=False),
        sa.Column(
            "anti_slip_rating",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=True,
        ),
        sa.Column("water_absorption_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("pieces_per_box", sa.Integer(), nullable=True),
        sa.Column("sqm_per_box", sa.Numeric(10, 3), nullable=True),
        sa.Column("kg_per_box", sa.Numeric(10, 3), nullable=True),
        sa.Column(
            "country_of_origin",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brand.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_brand_id", "product", ["brand_id"], unique=False)
    op.create_index("ix_product_category_id", "product", ["category_id"], unique=False)
    op.create_index("ix_product_sku", "product", ["sku"], unique=True)
    op.create_index("ix_product_slug", "product", ["slug"], unique=True)

    op.create_table(
        "product_image",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column(
            "storage_key", sqlmodel.sql.sqltypes.AutoString(length=1024), nullable=False
        ),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
        sa.Column(
            "alt_text", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_image_product_id", "product_image", ["product_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_product_image_product_id", table_name="product_image")
    op.drop_table("product_image")
    op.drop_index("ix_product_slug", table_name="product")
    op.drop_index("ix_product_sku", table_name="product")
    op.drop_index("ix_product_category_id", table_name="product")
    op.drop_index("ix_product_brand_id", table_name="product")
    op.drop_table("product")
    op.drop_index("ix_brand_slug", table_name="brand")
    op.drop_index("ix_brand_name", table_name="brand")
    op.drop_table("brand")
    op.drop_index("ix_category_slug", table_name="category")
    op.drop_index("ix_category_name", table_name="category")
    op.drop_table("category")
