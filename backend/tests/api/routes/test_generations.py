# ruff: noqa: ARG001
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app import crud
from app.api.routes import generations, products, visualization_projects
from app.core.config import settings
from app.core.db import engine
from app.models import (
    GenerationJob,
    GenerationStatus,
    Role,
    UserCreate,
)
from app.services import generation_processor
from app.services.image_edit import (
    ImageEditErrorCategory,
    ImageEditInput,
    ImageEditProviderError,
    ImageEditResult,
)
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


class FakeImageEditProvider:
    provider_name = "fake-provider"
    model = "fake-model-v1"

    def __init__(
        self,
        *,
        result: ImageEditResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or ImageEditResult(
            provider=self.provider_name,
            model=self.model,
            provider_request_id="safe-request-id",
            image_bytes=_png_bytes(),
            content_type="image/png",
            provider_metadata={
                "output_format": "png",
                "created": 1_800_000_000,
                "api_key": "must-not-persist",
                "prompt": "private prompt text",
                "image_bytes": "sensitive image payload",
            },
        )
        self.error = error
        self.requests: list[ImageEditInput] = []
        self.observed_status: str | None = None

    def edit(self, request: ImageEditInput) -> ImageEditResult:
        self.requests.append(request)
        with Session(engine) as session:
            latest = session.exec(
                select(GenerationJob).order_by(
                    GenerationJob.created_at.desc(), GenerationJob.id.desc()
                )
            ).first()
            self.observed_status = latest.status if latest is not None else None
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def local_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StorageService:
    storage = StorageService(
        LocalStorageBackend(tmp_path), max_file_size_bytes=1024 * 1024
    )
    monkeypatch.setattr(generations, "get_storage_service", lambda: storage)
    monkeypatch.setattr(generation_processor, "get_storage_service", lambda: storage)
    monkeypatch.setattr(products, "get_storage_service", lambda: storage)
    monkeypatch.setattr(visualization_projects, "get_storage_service", lambda: storage)
    return storage


def _create_project(
    client: TestClient, headers: dict[str, str], *, name: str = "Living room"
) -> dict[str, Any]:
    response = client.post(
        f"{settings.API_V1_STR}/visualization-projects/",
        headers=headers,
        files={"file": ("room.png", _png_bytes(), "image/png")},
        data={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_product(
    client: TestClient,
    headers: dict[str, str],
    *,
    suitable_surfaces: list[str] | None = None,
    is_active: bool = True,
    with_primary_image: bool = True,
) -> dict[str, Any]:
    suffix = random_lower_string()
    category_response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=headers,
        json={"name": f"Tile category {suffix}", "slug": f"tile-category-{suffix}"},
    )
    assert category_response.status_code == 201, category_response.text
    product_response = client.post(
        f"{settings.API_V1_STR}/products/",
        headers=headers,
        json={
            "name": f"Tile {suffix}",
            "sku": f"SKU-{suffix}",
            "slug": f"tile-{suffix}",
            "category_id": category_response.json()["id"],
            "product_type": "mosaic",
            "material": "porcelain",
            "finish": "matte",
            "width_mm": 300,
            "height_mm": 300,
            "suitable_surfaces": (
                ["FLOOR", "WALL"] if suitable_surfaces is None else suitable_surfaces
            ),
            "is_active": is_active,
        },
    )
    assert product_response.status_code == 201, product_response.text
    product = product_response.json()
    if with_primary_image:
        image_response = client.post(
            f"{settings.API_V1_STR}/products/{product['id']}/images/",
            headers=headers,
            files={"file": ("tile.png", _png_bytes(), "image/png")},
        )
        assert image_response.status_code == 201, image_response.text
        product["primary_image"] = image_response.json()
    return product


def _create_generation(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    product_id: str,
    *,
    surface: str = "FLOOR",
) -> Any:
    return client.post(
        f"{settings.API_V1_STR}/generations/",
        headers=headers,
        json={
            "visualization_project_id": project_id,
            "selected_product_id": product_id,
            "target_surface": surface,
        },
    )


def _fake_provider(
    monkeypatch: pytest.MonkeyPatch, provider: FakeImageEditProvider
) -> None:
    monkeypatch.setattr(
        generation_processor, "create_image_edit_provider", lambda: provider
    )


def test_generation_lifecycle_persists_safe_metadata_and_streams_result(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeImageEditProvider()
    _fake_provider(monkeypatch, provider)
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)

    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )

    assert created.status_code == 202, created.text
    job_id = created.json()["id"]
    assert created.json()["status"] == GenerationStatus.PENDING
    assert created.json()["prompt_version"] == "tilevision-v1"

    detail = client.get(
        f"{settings.API_V1_STR}/generations/{job_id}",
        headers=superuser_token_headers,
    )
    job = detail.json()
    assert detail.status_code == 200
    assert job["status"] == GenerationStatus.COMPLETED
    assert job["provider"] == "fake-provider"
    assert job["provider_model"] == "fake-model-v1"
    assert job["provider_params"] == {
        "output_format": "png",
        "created": 1_800_000_000,
    }
    assert "must-not-persist" not in detail.text
    assert "private prompt text" not in detail.text
    assert "sensitive image payload" not in detail.text
    assert job["output_image_url"].endswith(f"/generations/{job_id}/result")
    assert "output_image_key" not in job
    assert len(provider.requests) == 1
    assert provider.observed_status == GenerationStatus.PROCESSING
    assert provider.requests[0].target_surface.value == "FLOOR"
    assert "Preserve the original camera position" in "\n".join(
        provider.requests[0].instructions.constraints
    )
    with Session(engine) as session:
        stored_job = session.get(GenerationJob, job_id)
        assert stored_job is not None
        assert stored_job.output_image_key is not None
        assert (
            local_storage.backend.root / stored_job.output_image_key
        ).read_bytes() == _png_bytes()

    result = client.get(
        f"{settings.API_V1_STR}/generations/{job_id}/result",
        headers=superuser_token_headers,
    )
    assert result.status_code == 200
    assert result.headers["content-type"] == "image/png"
    assert result.headers["cache-control"] == "private, no-store"
    assert result.content == _png_bytes()


def test_generation_rejects_a_project_owned_by_another_user(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    local_storage: StorageService,
) -> None:
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)

    response = _create_generation(
        client,
        normal_user_token_headers,
        project["id"],
        product["id"],
    )

    assert response.status_code == 404


def test_generation_rejects_inactive_product(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
) -> None:
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers, is_active=False)

    response = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )

    assert response.status_code == 422


def test_generation_rejects_product_without_primary_reference(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
) -> None:
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers, with_primary_image=False)

    response = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )

    assert response.status_code == 422
    assert "primary" in response.json()["detail"].lower()


def test_generation_rejects_missing_product_and_corrupt_primary_image(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
) -> None:
    project = _create_project(client, superuser_token_headers)
    missing_product = _create_generation(
        client, superuser_token_headers, project["id"], str(uuid4())
    )
    product = _create_product(client, superuser_token_headers)
    image_key = product["primary_image"]["storage_key"]
    (local_storage.backend.root / image_key).write_bytes(b"not an image")

    corrupt_image = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )

    assert missing_product.status_code == 422
    assert corrupt_image.status_code == 422
    assert "valid primary reference image" in corrupt_image.json()["detail"]


def test_generation_rejects_unsuitable_or_empty_surface_list(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
) -> None:
    project = _create_project(client, superuser_token_headers)
    floor_only = _create_product(
        client, superuser_token_headers, suitable_surfaces=["FLOOR"]
    )
    no_surfaces = _create_product(client, superuser_token_headers, suitable_surfaces=[])

    unsuitable = _create_generation(
        client,
        superuser_token_headers,
        project["id"],
        floor_only["id"],
        surface="WALL",
    )
    empty = _create_generation(
        client, superuser_token_headers, project["id"], no_surfaces["id"]
    )

    assert unsuitable.status_code == 422
    assert empty.status_code == 422


@pytest.mark.parametrize(
    ("category", "error_code", "safe_message"),
    [
        (
            ImageEditErrorCategory.PROVIDER_TIMEOUT,
            "provider_timeout",
            "Image provider request timed out.",
        ),
        (
            ImageEditErrorCategory.PROVIDER_CONTENT_REJECTED,
            "content_rejected",
            "Image provider rejected the submitted content.",
        ),
    ],
)
def test_provider_failures_become_failed_jobs_with_safe_errors(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
    category: ImageEditErrorCategory,
    error_code: str,
    safe_message: str,
) -> None:
    provider = FakeImageEditProvider(
        error=ImageEditProviderError(category, safe_message)
    )
    _fake_provider(monkeypatch, provider)
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)

    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )
    detail = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}",
        headers=superuser_token_headers,
    )

    assert created.status_code == 202
    assert detail.status_code == 200
    assert detail.json()["status"] == GenerationStatus.FAILED
    assert detail.json()["error_code"] == error_code
    assert detail.json()["error_message"] == safe_message
    assert "raw provider response" not in detail.text
    assert detail.json()["provider"] == "fake-provider"
    assert detail.json()["provider_model"] == "fake-model-v1"
    assert detail.json()["prompt_version"] == "tilevision-v1"


def test_unexpected_provider_failure_does_not_persist_exception_text(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(
        monkeypatch,
        FakeImageEditProvider(
            error=RuntimeError("raw provider body and api-key-secret")
        ),
    )
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )
    detail = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}",
        headers=superuser_token_headers,
    )

    assert detail.json()["status"] == GenerationStatus.FAILED
    assert detail.json()["error_code"] == "internal_error"
    assert detail.json()["error_message"] == "Generation could not be completed."
    assert "raw provider body" not in detail.text
    assert "api-key-secret" not in detail.text


def test_dimension_mismatch_fails_without_exposing_result(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeImageEditProvider(
        result=ImageEditResult(
            provider="fake-provider",
            model="fake-model-v1",
            provider_request_id=None,
            image_bytes=_png_bytes(32, 24),
            content_type="image/png",
            provider_metadata={"output_format": "png"},
        )
    )
    _fake_provider(monkeypatch, provider)
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)

    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )
    detail = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}",
        headers=superuser_token_headers,
    )
    result = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}/result",
        headers=superuser_token_headers,
    )

    assert detail.json()["status"] == GenerationStatus.FAILED
    assert detail.json()["error_code"] == "provider_error"
    assert detail.json()["output_image_url"] is None
    assert result.status_code == 409
    assert list((local_storage.backend.root / "generation-results").glob("*")) == []


@pytest.mark.parametrize(
    ("image_bytes", "content_type"),
    [(b"", "image/png"), (_png_bytes(), "image/gif")],
)
def test_empty_or_unsupported_provider_output_fails(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
    image_bytes: bytes,
    content_type: str,
) -> None:
    _fake_provider(
        monkeypatch,
        FakeImageEditProvider(
            result=ImageEditResult(
                provider="fake-provider",
                model="fake-model-v1",
                provider_request_id=None,
                image_bytes=image_bytes,
                content_type=content_type,
                provider_metadata={},
            )
        ),
    )
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )
    detail = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}",
        headers=superuser_token_headers,
    )

    assert detail.json()["status"] == GenerationStatus.FAILED
    assert detail.json()["error_code"] == "provider_error"
    assert list((local_storage.backend.root / "generation-results").glob("*")) == []


def test_output_storage_failure_becomes_a_safe_failed_job(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)

    def fail_output_upload(**_kwargs: Any) -> None:
        raise OSError("storage credential secret")

    monkeypatch.setattr(local_storage, "upload", fail_output_upload)
    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )
    detail = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}",
        headers=superuser_token_headers,
    )

    assert detail.json()["status"] == GenerationStatus.FAILED
    assert detail.json()["error_code"] == "internal_error"
    assert detail.json()["error_message"] == "Generation could not be completed."
    assert "storage credential secret" not in detail.text


def test_owner_scoped_history_is_paginated_newest_first_and_support_can_read_any(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    created_ids = [
        _create_generation(
            client, superuser_token_headers, project["id"], product["id"]
        ).json()["id"]
        for _ in range(3)
    ]

    first_page = client.get(
        f"{settings.API_V1_STR}/generations/",
        headers=superuser_token_headers,
        params={"skip": 0, "limit": 2},
    )
    second_page = client.get(
        f"{settings.API_V1_STR}/generations/",
        headers=superuser_token_headers,
        params={"skip": 2, "limit": 2},
    )
    denied = client.get(
        f"{settings.API_V1_STR}/generations/{created_ids[0]}",
        headers=normal_user_token_headers,
    )

    assert first_page.status_code == second_page.status_code == 200
    assert first_page.json()["count"] >= 3
    assert len(first_page.json()["data"]) == 2
    assert len(second_page.json()["data"]) >= 1
    rows = first_page.json()["data"] + second_page.json()["data"]
    ordering = [(row["created_at"], row["id"]) for row in rows]
    assert ordering == sorted(ordering, reverse=True)
    assert denied.status_code == 404


def test_owner_and_read_any_can_read_job_and_stream_result(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    project = _create_project(client, normal_user_token_headers)
    product = _create_product(client, superuser_token_headers)
    created = _create_generation(
        client, normal_user_token_headers, project["id"], product["id"]
    )
    job_id = created.json()["id"]

    owner_detail = client.get(
        f"{settings.API_V1_STR}/generations/{job_id}",
        headers=normal_user_token_headers,
    )
    support_detail = client.get(
        f"{settings.API_V1_STR}/generations/{job_id}",
        headers=superuser_token_headers,
    )
    support_result = client.get(
        f"{settings.API_V1_STR}/generations/{job_id}/result",
        headers=superuser_token_headers,
    )

    assert owner_detail.status_code == support_detail.status_code == 200
    assert owner_detail.json()["status"] == GenerationStatus.COMPLETED
    assert support_result.status_code == 200
    assert support_result.content == _png_bytes()


def test_user_without_generations_create_permission_is_forbidden(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
) -> None:
    role = Role(
        name=f"No generation role {random_lower_string()}",
        slug=f"no-generation-{random_lower_string()}",
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
    no_permission_headers = authentication_token_from_email(
        client=client, email=user.email, db=db
    )
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)

    response = _create_generation(
        client,
        no_permission_headers,
        project["id"],
        product["id"],
    )

    assert response.status_code == 403


def test_read_own_permission_is_required_for_history(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
) -> None:
    role = Role(
        name=f"No history role {random_lower_string()}",
        slug=f"no-history-{random_lower_string()}",
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
    no_permission_headers = authentication_token_from_email(
        client=client, email=user.email, db=db
    )

    response = client.get(
        f"{settings.API_V1_STR}/generations/", headers=no_permission_headers
    )

    assert response.status_code == 403


def test_output_is_deleted_when_completion_persistence_fails(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeImageEditProvider()
    _fake_provider(monkeypatch, provider)
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    original_commit = Session.commit
    failed_once = False

    def fail_completed_commit(session: Session) -> None:
        nonlocal failed_once
        if not failed_once and any(
            isinstance(entity, GenerationJob)
            and entity.status == GenerationStatus.COMPLETED
            for entity in session.dirty
        ):
            failed_once = True
            raise SQLAlchemyError("private database error")
        original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_completed_commit)

    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )
    detail = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}",
        headers=superuser_token_headers,
    )

    assert failed_once is True
    assert detail.json()["status"] == GenerationStatus.FAILED
    assert detail.json()["error_code"] == "internal_error"
    assert detail.json()["output_image_url"] is None
    assert list((local_storage.backend.root / "generation-results").glob("*")) == []


def test_completed_job_is_not_processed_twice(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeImageEditProvider()
    _fake_provider(monkeypatch, provider)
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )

    generations.process_generation_job(created.json()["id"])

    assert len(provider.requests) == 1


def test_result_endpoint_requires_authentication(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )

    result = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}/result"
    )

    assert result.status_code == 401
