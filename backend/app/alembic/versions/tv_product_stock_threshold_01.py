"""Add product low-stock threshold

Revision ID: tv_product_stock_threshold_01
Revises: tv_catalog_permissions_01
Create Date: 2026-09-26

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "tv_product_stock_threshold_01"
down_revision = "tv_catalog_permissions_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product", sa.Column("low_stock_threshold", sa.Integer()))


def downgrade() -> None:
    op.drop_column("product", "low_stock_threshold")
