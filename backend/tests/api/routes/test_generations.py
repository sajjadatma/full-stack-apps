# ruff: noqa: ARG001
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app import crud
from app.api.routes import generations, products, visualization_projects
from app.core.config import settings
from app.core.db import engine
from app.core.rbac import GENERATIONS_CREATE, GENERATIONS_READ_OWN
from app.models import (
    GenerationJob,
    GenerationStatus,
    Permission,
    Product,
    ProductImage,
    Role,
    User,
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


@pytest.fixture(autouse=True)
def forbid_unmocked_ai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent any API test in this module from reaching a paid provider."""

    def fail_if_unmocked() -> None:
        pytest.fail("Generation API tests must replace the external AI provider")

    monkeypatch.setattr(
        generation_processor, "create_image_edit_provider", fail_if_unmocked
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


def test_history_read_any_sees_foreign_jobs_but_read_own_does_not(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    customer_project = _create_project(client, normal_user_token_headers)
    staff_project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    customer_job = _create_generation(
        client,
        normal_user_token_headers,
        customer_project["id"],
        product["id"],
    )
    staff_job = _create_generation(
        client,
        superuser_token_headers,
        staff_project["id"],
        product["id"],
    )
    assert customer_job.status_code == staff_job.status_code == 202

    customer_history = client.get(
        f"{settings.API_V1_STR}/generations/",
        headers=normal_user_token_headers,
    )
    support_url = f"{settings.API_V1_STR}/generations/"
    support_history = client.get(
        support_url,
        headers=superuser_token_headers,
        params={"skip": 0, "limit": 100},
    )
    customer_ids = {row["id"] for row in customer_history.json()["data"]}
    support_ids = set()
    support_count = support_history.json()["count"]
    for offset in range(0, support_count, 100):
        page = client.get(
            support_url,
            headers=superuser_token_headers,
            params={"skip": offset, "limit": 100},
        )
        support_ids.update(row["id"] for row in page.json()["data"])

    assert customer_history.status_code == support_history.status_code == 200
    assert customer_job.json()["id"] in customer_ids
    assert staff_job.json()["id"] not in customer_ids
    assert {customer_job.json()["id"], staff_job.json()["id"]} <= support_ids


def test_generation_history_includes_inactive_product_without_catalog_access(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    db: Session,
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    project = _create_project(client, normal_user_token_headers)
    product = _create_product(client, superuser_token_headers)
    created = _create_generation(
        client, normal_user_token_headers, project["id"], product["id"]
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]

    product_row = db.get(Product, product["id"])
    assert product_row is not None
    product_row.is_active = False
    product_row.width_mm = None
    product_row.height_mm = None
    db.add(product_row)
    db.commit()

    detail = client.get(
        f"{settings.API_V1_STR}/generations/{job_id}",
        headers=normal_user_token_headers,
    )
    history = client.get(
        f"{settings.API_V1_STR}/generations/",
        headers=normal_user_token_headers,
    )
    ordinary_product = client.get(
        f"{settings.API_V1_STR}/products/{product['id']}",
        headers=normal_user_token_headers,
    )
    ordinary_product_image = client.get(
        f"{settings.API_V1_STR}/product-images/{product['primary_image']['id']}/content",
        headers=normal_user_token_headers,
    )

    assert detail.status_code == history.status_code == 200
    summary = detail.json()["selected_product"]
    history_job = next(row for row in history.json()["data"] if row["id"] == job_id)
    assert history_job["selected_product"] == summary
    assert summary == {
        "id": product["id"],
        "name": product["name"],
        "sku": product["sku"],
        "width_mm": None,
        "height_mm": None,
        "thickness_mm": None,
        "finish": "matte",
        "material": "porcelain",
        "color_family": None,
        "is_active": False,
        "primary_image_id": product["primary_image"]["id"],
    }
    assert ordinary_product.status_code == 404
    assert ordinary_product_image.status_code == 404


def test_generation_scoped_product_image_uses_generation_permissions(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    db: Session,
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    own_project = _create_project(client, normal_user_token_headers)
    foreign_project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    own_job = _create_generation(
        client, normal_user_token_headers, own_project["id"], product["id"]
    )
    foreign_job = _create_generation(
        client, superuser_token_headers, foreign_project["id"], product["id"]
    )
    assert own_job.status_code == foreign_job.status_code == 202

    product_row = db.get(Product, product["id"])
    assert product_row is not None
    product_row.is_active = False
    db.add(product_row)
    db.commit()

    owner_image = client.get(
        f"{settings.API_V1_STR}/generations/{own_job.json()['id']}/product-image",
        headers=normal_user_token_headers,
    )
    privileged_image = client.get(
        f"{settings.API_V1_STR}/generations/{own_job.json()['id']}/product-image",
        headers=superuser_token_headers,
    )
    foreign_image = client.get(
        f"{settings.API_V1_STR}/generations/{foreign_job.json()['id']}/product-image",
        headers=normal_user_token_headers,
    )

    assert owner_image.status_code == privileged_image.status_code == 200
    assert owner_image.headers["content-type"] == "image/png"
    assert owner_image.content == privileged_image.content == _png_bytes()
    assert foreign_image.status_code == 404


@pytest.mark.parametrize("unavailable_image", ["no_primary", "missing_bytes"])
def test_generation_scoped_product_image_returns_not_found_when_unavailable(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
    unavailable_image: str,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    project = _create_project(client, superuser_token_headers)
    product = _create_product(client, superuser_token_headers)
    created = _create_generation(
        client, superuser_token_headers, project["id"], product["id"]
    )
    assert created.status_code == 202, created.text

    primary_image = db.get(ProductImage, product["primary_image"]["id"])
    assert primary_image is not None
    if unavailable_image == "no_primary":
        primary_image.is_primary = False
    else:
        primary_image.storage_key = "product-images/no-such-image.png"
    db.add(primary_image)
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/generations/{created.json()['id']}/product-image",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404


def test_generation_history_product_loading_does_not_grow_per_job(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_provider(monkeypatch, FakeImageEditProvider())
    project = _create_project(client, normal_user_token_headers)
    product = _create_product(client, superuser_token_headers)
    for _ in range(5):
        response = _create_generation(
            client, normal_user_token_headers, project["id"], product["id"]
        )
        assert response.status_code == 202, response.text

    def list_query_count(limit: int) -> tuple[int, dict[str, Any]]:
        statements: list[str] = []

        def record_query(
            connection: Any,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            executemany: bool,
        ) -> None:
            if statement.lstrip().lower().startswith("select"):
                statements.append(statement)

        event.listen(engine, "before_cursor_execute", record_query)
        try:
            response = client.get(
                f"{settings.API_V1_STR}/generations/",
                headers=normal_user_token_headers,
                params={"skip": 0, "limit": limit},
            )
        finally:
            event.remove(engine, "before_cursor_execute", record_query)
        assert response.status_code == 200, response.text
        return len(statements), response.json()

    one_query_count, one_job_page = list_query_count(1)
    five_query_count, five_job_page = list_query_count(5)

    assert len(one_job_page["data"]) == 1
    assert len(five_job_page["data"]) == 5
    assert all(row.get("selected_product") for row in five_job_page["data"])
    assert five_query_count == one_query_count


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


def _create_failed_generation(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    product_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, FakeImageEditProvider]:
    failed_provider = FakeImageEditProvider(
        error=ImageEditProviderError(
            ImageEditErrorCategory.PROVIDER_TIMEOUT,
            "safe provider timeout",
        )
    )
    _fake_provider(monkeypatch, failed_provider)
    response = _create_generation(client, headers, project_id, product_id)
    assert response.status_code == 202
    detail = client.get(
        f"{settings.API_V1_STR}/generations/{response.json()['id']}",
        headers=headers,
    )
    assert detail.json()["status"] == GenerationStatus.FAILED
    return detail, failed_provider


@pytest.mark.parametrize("retry_outcome", ["completed", "failed"])
def test_failed_generation_retry_creates_linked_new_attempt(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
    retry_outcome: str,
) -> None:
    project = _create_project(client, normal_user_token_headers)
    product = _create_product(client, superuser_token_headers)
    original_detail, _ = _create_failed_generation(
        client,
        normal_user_token_headers,
        project["id"],
        product["id"],
        monkeypatch,
    )
    source = original_detail.json()
    retry_provider = (
        FakeImageEditProvider()
        if retry_outcome == "completed"
        else FakeImageEditProvider(
            error=ImageEditProviderError(
                ImageEditErrorCategory.PROVIDER_CONTENT_REJECTED,
                "safe provider rejection",
            )
        )
    )
    _fake_provider(monkeypatch, retry_provider)

    retry_response = client.post(
        f"{settings.API_V1_STR}/generations/{source['id']}/retry",
        headers=normal_user_token_headers,
    )
    original_after = client.get(
        f"{settings.API_V1_STR}/generations/{source['id']}",
        headers=normal_user_token_headers,
    ).json()
    retry_id = retry_response.json()["id"]
    retry_after = client.get(
        f"{settings.API_V1_STR}/generations/{retry_id}",
        headers=normal_user_token_headers,
    ).json()

    assert retry_response.status_code == 202, retry_response.text
    assert retry_response.json()["status"] == GenerationStatus.PENDING
    assert retry_id != source["id"]
    assert retry_after["retry_of_job_id"] == source["id"]
    assert retry_after["retry_count"] == source["retry_count"] + 1
    assert retry_after["project_id"] == source["project_id"]
    assert retry_after["selected_product_id"] == source["selected_product_id"]
    assert retry_after["target_surface"] == source["target_surface"]
    assert retry_after["prompt_version"] == "tilevision-v1"
    assert retry_after["status"] == (
        GenerationStatus.COMPLETED
        if retry_outcome == "completed"
        else GenerationStatus.FAILED
    )
    assert retry_after["error_code"] == (
        None if retry_outcome == "completed" else "content_rejected"
    )
    assert original_after == source
    assert len(retry_provider.requests) == 1
    assert "Preserve the original camera position" in "\n".join(
        retry_provider.requests[0].instructions.constraints
    )


@pytest.mark.parametrize(
    "status",
    [
        GenerationStatus.PENDING,
        GenerationStatus.PROCESSING,
        GenerationStatus.COMPLETED,
    ],
)
def test_only_failed_generation_jobs_can_be_retried(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    db: Session,
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
    status: GenerationStatus,
) -> None:
    project = _create_project(client, normal_user_token_headers)
    product = _create_product(client, superuser_token_headers)
    original_detail, _ = _create_failed_generation(
        client,
        normal_user_token_headers,
        project["id"],
        product["id"],
        monkeypatch,
    )
    source_id = original_detail.json()["id"]
    source = db.get(GenerationJob, source_id)
    assert source is not None
    source.status = status
    db.add(source)
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/generations/{source_id}/retry",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 409


def test_read_any_permission_does_not_allow_retrying_another_users_job(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _create_project(client, normal_user_token_headers)
    product = _create_product(client, superuser_token_headers)
    source, _ = _create_failed_generation(
        client,
        normal_user_token_headers,
        project["id"],
        product["id"],
        monkeypatch,
    )

    readable = client.get(
        f"{settings.API_V1_STR}/generations/{source.json()['id']}",
        headers=superuser_token_headers,
    )
    retry = client.post(
        f"{settings.API_V1_STR}/generations/{source.json()['id']}/retry",
        headers=superuser_token_headers,
    )

    assert readable.status_code == 200
    assert retry.status_code == 404


@pytest.mark.parametrize(
    "eligibility_failure", ["inactive", "unsupported_surface", "no_primary_image"]
)
def test_retry_rechecks_product_eligibility_but_history_remains_readable(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    db: Session,
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
    eligibility_failure: str,
) -> None:
    project = _create_project(client, normal_user_token_headers)
    product = _create_product(client, superuser_token_headers)
    source, _ = _create_failed_generation(
        client,
        normal_user_token_headers,
        project["id"],
        product["id"],
        monkeypatch,
    )
    product_row = db.get(Product, product["id"])
    assert product_row is not None
    if eligibility_failure == "inactive":
        product_row.is_active = False
        db.add(product_row)
    elif eligibility_failure == "unsupported_surface":
        product_row.suitable_surfaces = []
        db.add(product_row)
    else:
        primary_image = db.exec(
            select(ProductImage).where(ProductImage.product_id == product["id"])
        ).first()
        assert primary_image is not None
        primary_image.is_primary = False
        db.add(primary_image)
    db.commit()

    history = client.get(
        f"{settings.API_V1_STR}/generations/",
        headers=normal_user_token_headers,
    )
    detail = client.get(
        f"{settings.API_V1_STR}/generations/{source.json()['id']}",
        headers=normal_user_token_headers,
    )
    retry = client.post(
        f"{settings.API_V1_STR}/generations/{source.json()['id']}/retry",
        headers=normal_user_token_headers,
    )

    assert history.status_code == detail.status_code == 200
    assert source.json()["id"] in {job["id"] for job in history.json()["data"]}
    assert detail.json()["status"] == GenerationStatus.FAILED
    assert retry.status_code == 422


@pytest.mark.parametrize(
    "granted_permission", [GENERATIONS_CREATE, GENERATIONS_READ_OWN]
)
def test_retry_requires_both_create_and_read_own_permissions(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
    granted_permission: str,
) -> None:
    user_headers = authentication_token_from_email(
        client=client, email=random_email(), db=db
    )
    project = _create_project(client, user_headers)
    product = _create_product(client, superuser_token_headers)
    source, _ = _create_failed_generation(
        client,
        user_headers,
        project["id"],
        product["id"],
        monkeypatch,
    )
    granted = db.exec(
        select(Permission).where(Permission.code == granted_permission)
    ).one()
    role = Role(
        name=f"Single generation permission {random_lower_string()}",
        slug=f"single-generation-permission-{random_lower_string()}",
        is_system=False,
        permissions=[granted],
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    user_id = client.get(
        f"{settings.API_V1_STR}/users/me", headers=user_headers
    ).json()["id"]
    owner = db.get(User, user_id)
    assert owner is not None
    owner.role_id = role.id
    db.add(owner)
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/generations/{source.json()['id']}/retry",
        headers=user_headers,
    )

    assert response.status_code == 403
