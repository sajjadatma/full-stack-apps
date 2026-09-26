"""Add room visualizer projects and generation jobs

Revision ID: tv_visualizer_domain_01
Revises: tv_product_images_01
Create Date: 2026-09-27

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "tv_visualizer_domain_01"
down_revision = "tv_product_images_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visualization_project",
        sa.Column(
            "name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column(
            "source_image_key",
            sqlmodel.sql.sqltypes.AutoString(length=1024),
            nullable=False,
        ),
        sa.Column(
            "source_image_content_type",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column("source_image_size_bytes", sa.Integer(), nullable=False),
        sa.Column("source_image_width_px", sa.Integer(), nullable=False),
        sa.Column("source_image_height_px", sa.Integer(), nullable=False),
        sa.Column(
            "source_image_url",
            sqlmodel.sql.sqltypes.AutoString(length=2048),
            nullable=True,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_visualization_project_owner_created",
        "visualization_project",
        ["owner_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "generation_job",
        sa.Column(
            "target_surface",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
        ),
        sa.Column(
            "status", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False
        ),
        sa.Column(
            "provider", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column(
            "provider_model",
            sqlmodel.sql.sqltypes.AutoString(length=120),
            nullable=True,
        ),
        sa.Column("provider_params", sa.JSON(), nullable=True),
        sa.Column(
            "prompt_version",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
        sa.Column(
            "output_image_key",
            sqlmodel.sql.sqltypes.AutoString(length=1024),
            nullable=True,
        ),
        sa.Column(
            "output_image_url",
            sqlmodel.sql.sqltypes.AutoString(length=2048),
            nullable=True,
        ),
        sa.Column(
            "output_image_content_type",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
        sa.Column("output_image_width_px", sa.Integer(), nullable=True),
        sa.Column("output_image_height_px", sa.Integer(), nullable=True),
        sa.Column(
            "error_code",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("selected_product_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["visualization_project.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["selected_product_id"], ["product.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generation_job_project_created",
        "generation_job",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_job_status_created",
        "generation_job",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_job_selected_product_id",
        "generation_job",
        ["selected_product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generation_job_selected_product_id", table_name="generation_job"
    )
    op.drop_index("ix_generation_job_status_created", table_name="generation_job")
    op.drop_index("ix_generation_job_project_created", table_name="generation_job")
    op.drop_table("generation_job")
    op.drop_index(
        "ix_visualization_project_owner_created", table_name="visualization_project"
    )
    op.drop_table("visualization_project")
