"""Add generation retry lineage.

Revision ID: tv_generation_retry_01
Revises: tv_generation_api_01
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "tv_generation_retry_01"
down_revision = "tv_generation_api_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("generation_job") as batch_op:
        batch_op.add_column(
            sa.Column(
                "retry_of_job_id",
                sa.Uuid(),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_generation_job_retry_of_job_id",
            "generation_job",
            ["retry_of_job_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("generation_job") as batch_op:
        batch_op.drop_column("retry_of_job_id")
