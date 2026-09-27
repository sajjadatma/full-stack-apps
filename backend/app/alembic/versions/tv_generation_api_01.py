"""Add explicit suitable surfaces to products.

Revision ID: tv_generation_api_01
Revises: tv_visualizer_domain_01
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "tv_generation_api_01"
down_revision = "tv_visualizer_domain_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Legacy products are intentionally ineligible until staff explicitly sets
    # suitable surfaces. Never guess from product_type.
    op.add_column(
        "product",
        sa.Column(
            "suitable_surfaces",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("product", "suitable_surfaces")
