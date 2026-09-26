"""Add product catalog permissions

Revision ID: tv_catalog_permissions_01
Revises: tv_product_domain_01
Create Date: 2026-09-26

"""

import uuid

from alembic import op

# revision identifiers, used by Alembic.
revision = "tv_catalog_permissions_01"
down_revision = "tv_product_domain_01"
branch_labels = None
depends_on = None

_NAMESPACE = uuid.UUID("6f1b1e2a-0d6e-4c2b-9f7a-2c5b8d3e4a11")
_USER_ROLE_ID = uuid.uuid5(_NAMESPACE, "role:user")
_SUPERUSER_ROLE_ID = uuid.uuid5(_NAMESPACE, "role:superuser")
_PERMISSIONS = (
    ("products.read", "Read the active product catalog"),
    ("products.read_any", "Read all product catalog data"),
    ("products.create", "Create product catalog data"),
    ("products.update", "Update product catalog data"),
    ("products.delete", "Delete product catalog data"),
)


def _permission_id(code: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"permission:{code}")


def upgrade() -> None:
    for code, description in _PERMISSIONS:
        op.execute(
            "INSERT INTO permission (id, code, description) "
            f"VALUES ('{_permission_id(code)}', '{code}', '{description}') "
            "ON CONFLICT (code) DO UPDATE "
            "SET description = EXCLUDED.description"
        )

    role_grants = [
        (_USER_ROLE_ID, "products.read"),
        *[
            (
                _SUPERUSER_ROLE_ID,
                code,
            )
            for code, _ in _PERMISSIONS
        ],
    ]
    for role_id, code in role_grants:
        op.execute(
            "INSERT INTO rolepermissionlink (role_id, permission_id) "
            "SELECT "
            f"'{role_id}', id FROM permission WHERE code = '{code}' "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )


def downgrade() -> None:
    codes = ", ".join(f"'{code}'" for code, _ in _PERMISSIONS)
    op.execute(
        "DELETE FROM rolepermissionlink WHERE permission_id IN "
        f"(SELECT id FROM permission WHERE code IN ({codes}))"
    )
    op.execute(f"DELETE FROM permission WHERE code IN ({codes})")
