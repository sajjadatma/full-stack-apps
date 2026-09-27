from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def _load_migration():
    migration_path = (
        Path(__file__).parents[2]
        / "app"
        / "alembic"
        / "versions"
        / "tv_generation_api_01.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tv_generation_api_01", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_product_surfaces_migration_backfills_empty_json_without_inference() -> None:
    migration = _load_migration()
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE product (id INTEGER PRIMARY KEY, product_type TEXT, is_active BOOLEAN)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO product (id, product_type, is_active) VALUES "
                "(1, 'floor_tile', 1), (2, 'wall_tile', 1), "
                "(3, 'mosaic', 1), (4, NULL, 0)"
            )
        )
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

        surfaces = connection.execute(
            text("SELECT suitable_surfaces FROM product ORDER BY id")
        ).all()
        column = next(
            column
            for column in inspect(connection).get_columns("product")
            if column["name"] == "suitable_surfaces"
        )
        assert [row[0] for row in surfaces] == ["[]", "[]", "[]", "[]"]
        assert column["nullable"] is False
        assert migration.down_revision == "tv_visualizer_domain_01"
        with Operations.context(context):
            migration.downgrade()
        assert "suitable_surfaces" not in {
            column["name"] for column in inspect(connection).get_columns("product")
        }
    engine.dispose()
