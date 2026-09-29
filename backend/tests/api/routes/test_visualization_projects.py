from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app import crud
from app.api.routes import visualization_projects
from app.core.config import settings
from app.core.db import engine
from app.models import Role, UserCreate, VisualizationProject
from app.services.storage import LocalStorageBackend, StorageService
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def _png_bytes(width: int = 64, height: int = 48) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )


def _jpeg_bytes(width: int = 64, height: int = 48) -> bytes:
    frame = (
        b"\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03"
        + b"\x01\x11\x00" * 3
    )
    return b"\xff\xd8\xff\xc0" + (len(frame) + 2).to_bytes(2, "big") + frame


def _webp_bytes(width: int = 64, height: int = 48) -> bytes:
    payload = (
        b"\x00\x00\x00\x00"
        + (width - 1).to_bytes(3, "little")
        + (height - 1).to_bytes(3, "little")
    )
    return b"RIFF" + b"\x00\x00\x00\x00" + b"WEBPVP8X" + b"\x0a\x00\x00\x00" + payload


@pytest.fixture
def local_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StorageService:
    storage = StorageService(LocalStorageBackend(tmp_path), max_file_size_bytes=128)
    monkeypatch.setattr(visualization_projects, "get_storage_service", lambda: storage)
    return storage


def _upload(
    client: TestClient,
    headers: dict[str, str],
    *,
    content: bytes | None = None,
    content_type: str = "image/png",
    name: str = "Kitchen",
) -> Any:
    files = {
        "file": (
            "room.png",
            _png_bytes() if content is None else content,
            content_type,
        )
    }
    return client.post(
        f"{settings.API_V1_STR}/visualization-projects/",
        headers=headers,
        files=files,
        data={"name": name},
    )


def test_room_upload_creates_owned_project_with_validated_metadata(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
) -> None:
    current_user = client.get(
        f"{settings.API_V1_STR}/users/me", headers=superuser_token_headers
    ).json()
    response = _upload(client, superuser_token_headers)

    assert response.status_code == 201, response.text
    project = response.json()
    assert project["owner_id"] == current_user["id"]
    assert project["name"] == "Kitchen"
    assert project["source_image_key"].startswith("rooms/")
    assert project["source_image_content_type"] == "image/png"
    assert project["source_image_size_bytes"] == len(_png_bytes())
    assert project["source_image_width_px"] == 64
    assert project["source_image_height_px"] == 48
    assert project["source_image_url"].endswith(
        f"/visualization-projects/{project['id']}/source-image"
    )
    assert "signed" not in project["source_image_url"]
    assert (local_storage.backend.root / project["source_image_key"]).read_bytes() == (
        _png_bytes()
    )
    with Session(engine) as session:
        stored_project = session.get(VisualizationProject, project["id"])
        assert stored_project is not None
        assert stored_project.source_image_url is None


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (_jpeg_bytes(), "image/jpeg"),
        (_png_bytes(), "image/png"),
        (_webp_bytes(), "image/webp"),
    ],
)
def test_room_upload_accepts_supported_formats_and_records_dimensions(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    content: bytes,
    content_type: str,
) -> None:
    response = _upload(
        client,
        superuser_token_headers,
        content=content,
        content_type=content_type,
    )

    assert response.status_code == 201, response.text
    project = response.json()
    assert project["source_image_content_type"] == content_type
    assert project["source_image_width_px"] == 64
    assert project["source_image_height_px"] == 48
    assert (local_storage.backend.root / project["source_image_key"]).is_file()


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"not an image", "image/png"),
        (_png_bytes(), "image/jpeg"),
        (_png_bytes() * 5, "image/png"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
    ],
)
def test_invalid_oversized_or_unreadable_room_upload_is_rejected(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    content: bytes,
    content_type: str,
) -> None:
    response = _upload(
        client,
        superuser_token_headers,
        content=content,
        content_type=content_type,
    )

    assert response.status_code == 422
    assert list((local_storage.backend.root / "rooms").glob("*")) == []


def test_project_create_requires_authentication(client: TestClient) -> None:
    response = _upload(client, {})

    assert response.status_code == 401


def test_room_upload_requires_generation_create_permission(
    client: TestClient,
    db: Session,
    local_storage: StorageService,
) -> None:
    suffix = random_lower_string()
    role = Role(
        name=f"No generation create {suffix}",
        slug=f"no-generation-create-{suffix}",
        is_system=False,
        permissions=[],
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password="test-password-123"),
        role=role,
    )
    headers = authentication_token_from_email(
        client=client,
        email=user.email,
        db=db,
    )

    response = _upload(client, headers)

    assert response.status_code == 403
    assert list((local_storage.backend.root / "rooms").glob("*")) == []


def test_owner_can_list_and_get_projects_with_newest_first_pagination(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    base_url = f"{settings.API_V1_STR}/visualization-projects/"
    existing_count = client.get(base_url, headers=superuser_token_headers).json()[
        "count"
    ]
    first = _upload(client, superuser_token_headers, name="First").json()
    second = _upload(client, superuser_token_headers, name="Second").json()
    third = _upload(client, superuser_token_headers, name="Third").json()

    page = client.get(
        base_url,
        headers=superuser_token_headers,
        params={"skip": 0, "limit": 3},
    )
    detail = client.get(f"{base_url}{second['id']}", headers=superuser_token_headers)

    assert page.status_code == 200, page.text
    assert page.json()["count"] == existing_count + 3
    assert [project["id"] for project in page.json()["data"]] == [
        third["id"],
        second["id"],
        first["id"],
    ]
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == second["id"]
    assert first["id"] != third["id"]


def test_project_and_source_image_are_hidden_from_other_users(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    project = _upload(client, superuser_token_headers).json()
    base_url = f"{settings.API_V1_STR}/visualization-projects/{project['id']}"

    project_response = client.get(base_url, headers=normal_user_token_headers)
    image_response = client.get(
        f"{base_url}/source-image", headers=normal_user_token_headers
    )
    own_list = client.get(
        f"{settings.API_V1_STR}/visualization-projects/",
        headers=normal_user_token_headers,
    )

    assert project_response.status_code == 404
    assert image_response.status_code == 404
    assert own_list.status_code == 200
    assert all(
        item["owner_id"] != project["owner_id"] for item in own_list.json()["data"]
    )


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (_jpeg_bytes(), "image/jpeg"),
        (_png_bytes(), "image/png"),
        (_webp_bytes(), "image/webp"),
    ],
)
def test_owner_receives_streamed_room_image_with_validated_content_type(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    content: bytes,
    content_type: str,
) -> None:
    project = _upload(
        client,
        superuser_token_headers,
        content=content,
        content_type=content_type,
    ).json()
    assert (local_storage.backend.root / project["source_image_key"]).is_file()

    response = client.get(
        f"{settings.API_V1_STR}/visualization-projects/{project['id']}/source-image",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == content_type
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content == content


def test_database_failure_deletes_uploaded_room_image(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_commit = Session.commit

    def fail_project_commit(session: Session) -> None:
        if any(isinstance(entity, VisualizationProject) for entity in session.new):
            raise SQLAlchemyError("simulated database failure")
        original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_project_commit)

    response = _upload(client, superuser_token_headers)

    assert response.status_code == 500
    assert list((local_storage.backend.root / "rooms").glob("*")) == []
