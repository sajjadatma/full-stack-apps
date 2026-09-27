import uuid
from collections.abc import Sequence

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.core.rbac import (
    DEFAULT_USER_PERMISSIONS,
    GENERATIONS_CREATE,
    GENERATIONS_READ_ANY,
    GENERATIONS_READ_OWN,
    ITEMS_READ_ANY,
    ROLES_ASSIGN,
    SUPERUSER_ROLE_SLUG,
    USER_ROLE_SLUG,
)
from app.models import User
from tests.utils.user import authentication_token_from_email, create_random_user
from tests.utils.utils import random_email, random_lower_string


def _create_role(
    client: TestClient, headers: dict[str, str], permissions: Sequence[str]
) -> dict:
    response = client.post(
        f"{settings.API_V1_STR}/roles/",
        headers=headers,
        json={"name": random_lower_string(), "permissions": list(permissions)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_read_permissions_catalog(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/roles/permissions",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    codes = [permission["code"] for permission in response.json()]
    assert ITEMS_READ_ANY in codes
    assert ROLES_ASSIGN in codes
    assert len(codes) == len(set(codes))


def test_generation_permissions_are_seeded_to_the_approved_system_roles(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    catalog = client.get(
        f"{settings.API_V1_STR}/roles/permissions",
        headers=superuser_token_headers,
    )
    customer = client.get(
        f"{settings.API_V1_STR}/users/me", headers=normal_user_token_headers
    )
    administrator = client.get(
        f"{settings.API_V1_STR}/users/me", headers=superuser_token_headers
    )

    assert (
        catalog.status_code == customer.status_code == administrator.status_code == 200
    )
    catalog_codes = {item["code"] for item in catalog.json()}
    customer_permissions = set(customer.json()["permissions"])
    admin_permissions = set(administrator.json()["permissions"])
    assert {
        GENERATIONS_CREATE,
        GENERATIONS_READ_OWN,
        GENERATIONS_READ_ANY,
    } <= catalog_codes
    assert {GENERATIONS_CREATE, GENERATIONS_READ_OWN} <= customer_permissions
    assert {
        GENERATIONS_CREATE,
        GENERATIONS_READ_OWN,
        GENERATIONS_READ_ANY,
    } <= admin_permissions


def test_read_roles(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/roles/", headers=superuser_token_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 2
    roles_by_slug = {role["slug"]: role for role in body["data"]}
    assert {"user", "superuser"} <= set(roles_by_slug)
    superuser_role = roles_by_slug["superuser"]
    assert superuser_role["is_system"] is True
    assert len(superuser_role["permissions"]) > len(DEFAULT_USER_PERMISSIONS)


def test_read_roles_forbidden_for_normal_user(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/roles/", headers=normal_user_token_headers
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


def test_system_roles_are_immutable(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    superuser_role = crud.get_role_by_slug(session=db, slug="superuser")
    assert superuser_role is not None

    response = client.patch(
        f"{settings.API_V1_STR}/roles/{superuser_role.id}",
        headers=superuser_token_headers,
        json={"name": "Renamed"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "System roles cannot be modified or deleted"

    response = client.delete(
        f"{settings.API_V1_STR}/roles/{superuser_role.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "System roles cannot be modified or deleted"


def test_create_role_with_unknown_permission(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/roles/",
        headers=superuser_token_headers,
        json={"name": random_lower_string(), "permissions": ["does.not.exist"]},
    )
    assert response.status_code == 400
    assert "does.not.exist" in response.json()["detail"]


def test_create_role_rejects_duplicate_permissions(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/roles/",
        headers=superuser_token_headers,
        json={"name": random_lower_string(), "permissions": [ITEMS_READ_ANY] * 2},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "A permission was selected more than once"


def test_create_role_forbidden_for_normal_user(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/roles/",
        headers=normal_user_token_headers,
        json={"name": random_lower_string(), "permissions": []},
    )
    assert response.status_code == 403


def test_role_creator_cannot_grant_permissions_they_do_not_have(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email = random_email()
    actor_headers = authentication_token_from_email(client=client, email=email, db=db)
    actor = crud.get_user_by_email(session=db, email=email)
    assert actor is not None

    role = _create_role(client, superuser_token_headers, ["roles.create"])
    role_model = crud.get_role_by_id(session=db, role_id=uuid.UUID(role["id"]))
    assert role_model is not None
    crud.set_user_role(session=db, db_user=actor, role=role_model)

    response = client.post(
        f"{settings.API_V1_STR}/roles/",
        headers=actor_headers,
        json={"name": random_lower_string(), "permissions": ["users.delete"]},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "You cannot grant permissions you do not have"


def test_assign_role_changes_effective_permissions(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email = random_email()
    user_headers = authentication_token_from_email(client=client, email=email, db=db)
    user = crud.get_user_by_email(session=db, email=email)
    assert user is not None

    role = _create_role(client, superuser_token_headers, [ITEMS_READ_ANY])

    response = client.put(
        f"{settings.API_V1_STR}/users/{user.id}/role",
        headers=superuser_token_headers,
        json={"role_id": role["id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"]["slug"] == role["slug"]

    me = client.get(f"{settings.API_V1_STR}/users/me", headers=user_headers).json()
    assert ITEMS_READ_ANY in me["permissions"]
    assert "items.create" not in me["permissions"]


def test_assign_role_to_self_is_forbidden(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    super_user = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    user_role = crud.get_role_by_slug(session=db, slug=USER_ROLE_SLUG)
    assert super_user is not None
    assert user_role is not None

    response = client.put(
        f"{settings.API_V1_STR}/users/{super_user.id}/role",
        headers=superuser_token_headers,
        json={"role_id": str(user_role.id)},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot change your own role"


def test_assign_unknown_role(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    user = create_random_user(db)
    response = client.put(
        f"{settings.API_V1_STR}/users/{user.id}/role",
        headers=superuser_token_headers,
        json={"role_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Role not found"


def test_delete_role_in_use(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    role = _create_role(client, superuser_token_headers, [ITEMS_READ_ANY])
    user = create_random_user(db)
    db_role = crud.get_role_by_id(session=db, role_id=uuid.UUID(role["id"]))
    assert db_role is not None
    crud.set_user_role(session=db, db_user=user, role=db_role)

    response = client.delete(
        f"{settings.API_V1_STR}/roles/{role['id']}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"].startswith("This role is assigned")


def test_update_and_delete_custom_role(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    role = _create_role(client, superuser_token_headers, [ITEMS_READ_ANY])

    response = client.patch(
        f"{settings.API_V1_STR}/roles/{role['id']}",
        headers=superuser_token_headers,
        json={"permissions": []},
    )
    assert response.status_code == 200
    assert response.json()["permissions"] == []

    response = client.delete(
        f"{settings.API_V1_STR}/roles/{role['id']}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200


def test_cannot_demote_last_superuser(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    actor_email = random_email()
    actor_headers = authentication_token_from_email(
        client=client, email=actor_email, db=db
    )
    actor = crud.get_user_by_email(session=db, email=actor_email)
    assert actor is not None

    permissions = sorted(DEFAULT_USER_PERMISSIONS | {ROLES_ASSIGN})
    role = _create_role(client, superuser_token_headers, permissions)
    db_role = crud.get_role_by_id(session=db, role_id=uuid.UUID(role["id"]))
    assert db_role is not None
    crud.set_user_role(session=db, db_user=actor, role=db_role)

    super_user = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    user_role = crud.get_role_by_slug(session=db, slug=USER_ROLE_SLUG)
    superuser_role = crud.get_role_by_slug(session=db, slug=SUPERUSER_ROLE_SLUG)
    assert super_user is not None
    assert user_role is not None
    assert superuser_role is not None

    # Keep the test deterministic even when earlier browser tests have left
    # additional superusers in the shared development database.
    other_active_superusers = db.exec(
        select(User).where(
            User.role_id == superuser_role.id,
            User.id != super_user.id,
            User.is_active,
        )
    ).all()
    for other_user in other_active_superusers:
        other_user.is_active = False
        db.add(other_user)
    db.commit()

    try:
        response = client.put(
            f"{settings.API_V1_STR}/users/{super_user.id}/role",
            headers=actor_headers,
            json={"role_id": str(user_role.id)},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "At least one active superuser must remain"
    finally:
        for other_user in other_active_superusers:
            db.refresh(other_user)
            other_user.is_active = True
            db.add(other_user)
        db.commit()


def test_user_me_includes_permissions(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/users/me", headers=superuser_token_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"]["slug"] == "superuser"
    assert ROLES_ASSIGN in body["permissions"]


def test_role_public_model_roundtrip(db: Session) -> None:
    role = crud.get_role_by_slug(session=db, slug="user")
    assert role is not None
    assert len(role.permissions) == len(DEFAULT_USER_PERMISSIONS)
    users = db.exec(select(User).where(User.role_id == role.id)).all()
    assert isinstance(users, list)
