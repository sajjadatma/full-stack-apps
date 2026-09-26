import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def test_product_domain_migration_applies_and_downgrades_on_sqlite() -> None:
    migration_path = (
        Path(__file__).parents[2]
        / "app"
        / "alembic"
        / "versions"
        / "tv_product_domain_01.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tv_product_domain_01", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        migration_context = MigrationContext.configure(connection)
        with Operations.context(migration_context):
            migration.upgrade()

        inspector = inspect(connection)
        assert {"category", "brand", "product", "product_image"}.issubset(
            set(inspector.get_table_names())
        )
        product_columns = {
            column["name"]: column for column in inspector.get_columns("product")
        }
        assert str(product_columns["price"]["type"]) == "NUMERIC(12, 2)"
        assert str(product_columns["sqm_per_box"]["type"]) == "NUMERIC(10, 3)"
        assert str(product_columns["kg_per_box"]["type"]) == "NUMERIC(10, 3)"
        assert str(product_columns["stock_quantity"]["type"]) == "INTEGER"

        with Operations.context(migration_context):
            migration.downgrade()
        assert not {"category", "brand", "product", "product_image"}.intersection(
            inspect(connection).get_table_names()
        )

    engine.dispose()
