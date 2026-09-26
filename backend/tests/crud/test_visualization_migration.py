import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def _load_migration():
    migration_path = (
        Path(__file__).parents[2]
        / "app"
        / "alembic"
        / "versions"
        / "tv_visualizer_domain_01.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tv_visualizer_domain_01", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_visualizer_domain_migration_applies_and_downgrades_on_sqlite() -> None:
    migration = _load_migration()

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        migration_context = MigrationContext.configure(connection)
        with Operations.context(migration_context):
            migration.upgrade()

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        assert {"visualization_project", "generation_job"}.issubset(tables)

        project_columns = {
            column["name"] for column in inspector.get_columns("visualization_project")
        }
        assert {
            "id",
            "owner_id",
            "source_image_key",
            "source_image_content_type",
            "source_image_size_bytes",
            "source_image_width_px",
            "source_image_height_px",
            "source_image_url",
            "created_at",
            "updated_at",
        }.issubset(project_columns)

        job_columns = {
            column["name"] for column in inspector.get_columns("generation_job")
        }
        assert {
            "id",
            "project_id",
            "selected_product_id",
            "target_surface",
            "status",
            "provider",
            "provider_model",
            "provider_params",
            "prompt_version",
            "output_image_key",
            "output_image_url",
            "output_image_content_type",
            "output_image_width_px",
            "output_image_height_px",
            "error_code",
            "error_message",
            "retry_count",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        }.issubset(job_columns)

        project_indexes = {
            index["name"] for index in inspector.get_indexes("visualization_project")
        }
        job_indexes = {
            index["name"] for index in inspector.get_indexes("generation_job")
        }
        assert "ix_visualization_project_owner_created" in project_indexes
        assert "ix_generation_job_project_created" in job_indexes
        assert "ix_generation_job_status_created" in job_indexes
        assert "ix_generation_job_selected_product_id" in job_indexes

        with Operations.context(migration_context):
            migration.downgrade()
        remaining = set(inspect(connection).get_table_names())
        assert not {"visualization_project", "generation_job"}.intersection(remaining)

    engine.dispose()
