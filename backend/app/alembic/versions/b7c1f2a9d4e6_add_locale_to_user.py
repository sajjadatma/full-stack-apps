"""Add locale to User

Revision ID: b7c1f2a9d4e6
Revises: fe56fa70289e
Create Date: 2026-09-26 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c1f2a9d4e6"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column(
            "locale",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'en'"),
        ),
    )


def downgrade():
    op.drop_column("user", "locale")
