from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.api.routes import products
from app.core.config import settings
from app.models import ProductImage
from app.services.storage import LocalStorageBackend, StorageService
from tests.api.routes.test_products import (
    _create_brand,
    _create_category,
    _product_payload,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"valid-test-image"


@pytest.fixture(autouse=True)
def local_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StorageService:
    storage = StorageService(LocalStorageBackend(tmp_path), max_file_size_bytes=1024)
    monkeypatch.setattr(products, "get_storage_service", lambda: storage, raising=False)
    return storage


def _create_product(client: TestClient, headers: dict[str, str]) -> str:
    category_id = _create_category(client, headers)
    brand_id = _create_brand(client, headers)
    response = client.post(
        f"{settings.API_V1_STR}/products/",
        headers=headers,
        json=_product_payload(category_id, brand_id),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload_image(
    client: TestClient,
    headers: dict[str, str],
    product_id: str,
    *,
    content: bytes = PNG_BYTES,
    content_type: str = "image/png",
    alt_text: str = "Tile surface",
) -> dict:
    response = client.post(
        f"{settings.API_V1_STR}/products/{product_id}/images/",
        headers=headers,
        files={"file": ("client-name.png", content, content_type)},
        data={"alt_text": alt_text},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _product_images(
    client: TestClient, headers: dict[str, str], product_id: str
) -> list[dict]:
    response = client.get(
        f"{settings.API_V1_STR}/products/{product_id}", headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()["images"]


def test_upload_sets_first_image_primary_and_later_images_non_primary(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)

    first = _upload_image(client, superuser_token_headers, product_id)
    second = _upload_image(client, superuser_token_headers, product_id)
    images = _product_images(client, superuser_token_headers, product_id)

    assert first["is_primary"] is True
    assert second["is_primary"] is False
    assert [image["id"] for image in images] == [first["id"], second["id"]]
    assert all(image["content_type"] == "image/png" for image in images)
    assert all(image["url"].endswith(f"/{image['id']}/content") for image in images)
    assert len([image for image in images if image["is_primary"]]) == 1


def test_set_primary_and_full_list_reorder(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    first = _upload_image(client, superuser_token_headers, product_id)
    second = _upload_image(client, superuser_token_headers, product_id)
    third = _upload_image(client, superuser_token_headers, product_id)
    image_url = f"{settings.API_V1_STR}/products/{product_id}/images"

    made_primary = client.put(
        f"{image_url}/{second['id']}/primary", headers=superuser_token_headers
    )
    assert made_primary.status_code == 200, made_primary.text
    assert made_primary.json()["is_primary"] is True

    reordered = client.put(
        f"{image_url}/order",
        headers=superuser_token_headers,
        json={"image_ids": [third["id"], second["id"], first["id"]]},
    )
    assert reordered.status_code == 200, reordered.text
    assert [image["id"] for image in reordered.json()["data"]] == [
        third["id"],
        second["id"],
        first["id"],
    ]
    assert [image["sort_order"] for image in reordered.json()["data"]] == [0, 1, 2]
    assert [
        image["id"]
        for image in _product_images(client, superuser_token_headers, product_id)
    ] == [third["id"], second["id"], first["id"]]
    assert [
        image["id"] for image in reordered.json()["data"] if image["is_primary"]
    ] == [second["id"]]


def test_delete_non_primary_preserves_primary(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    primary = _upload_image(client, superuser_token_headers, product_id)
    secondary = _upload_image(client, superuser_token_headers, product_id)

    deleted = client.delete(
        f"{settings.API_V1_STR}/products/{product_id}/images/{secondary['id']}",
        headers=superuser_token_headers,
    )

    assert deleted.status_code == 200, deleted.text
    images = _product_images(client, superuser_token_headers, product_id)
    assert [image["id"] for image in images] == [primary["id"]]
    assert images[0]["is_primary"] is True


def test_delete_primary_promotes_lowest_order_and_delete_last_leaves_no_primary(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    first = _upload_image(client, superuser_token_headers, product_id)
    second = _upload_image(client, superuser_token_headers, product_id)
    third = _upload_image(client, superuser_token_headers, product_id)
    image_url = f"{settings.API_V1_STR}/products/{product_id}/images"
    reordered = client.put(
        f"{image_url}/order",
        headers=superuser_token_headers,
        json={"image_ids": [third["id"], first["id"], second["id"]]},
    )
    assert reordered.status_code == 200, reordered.text

    deleted = client.delete(
        f"{image_url}/{first['id']}", headers=superuser_token_headers
    )
    assert deleted.status_code == 200, deleted.text
    remaining = _product_images(client, superuser_token_headers, product_id)
    assert [image["id"] for image in remaining if image["is_primary"]] == [third["id"]]

    for image in remaining:
        assert (
            client.delete(
                f"{image_url}/{image['id']}", headers=superuser_token_headers
            ).status_code
            == 200
        )
    assert _product_images(client, superuser_token_headers, product_id) == []


def test_database_enforces_at_most_one_primary_image_per_product(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    _upload_image(client, superuser_token_headers, product_id)
    duplicate_primary = ProductImage(
        product_id=uuid.UUID(product_id),
        storage_key=f"product-images/{uuid.uuid4()}.png",
        content_type="image/png",
        is_primary=True,
    )
    db.add(duplicate_primary)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_image_content_requires_catalog_read_and_streams_with_mime_type(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    image = _upload_image(client, superuser_token_headers, product_id)
    content_url = f"{settings.API_V1_STR}/product-images/{image['id']}/content"

    assert client.get(content_url).status_code == 401
    response = client.get(content_url, headers=normal_user_token_headers)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG_BYTES


def test_image_mutations_require_manage_images_permission(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    image = _upload_image(client, superuser_token_headers, product_id)
    image_url = f"{settings.API_V1_STR}/products/{product_id}/images"

    assert (
        client.post(
            f"{image_url}/",
            headers=normal_user_token_headers,
            files={"file": ("tile.png", PNG_BYTES, "image/png")},
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"{image_url}/{image['id']}/primary", headers=normal_user_token_headers
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"{image_url}/order",
            headers=normal_user_token_headers,
            json={"image_ids": [image["id"]]},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"{image_url}/{image['id']}", headers=normal_user_token_headers
        ).status_code
        == 403
    )


def test_upload_database_failure_compensates_by_deleting_stored_object(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    original_commit = Session.commit

    def fail_image_commit(session: Session) -> None:
        if any(isinstance(row, ProductImage) for row in session.new):
            raise RuntimeError("simulated database failure")
        original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_image_commit)
    response = client.post(
        f"{settings.API_V1_STR}/products/{product_id}/images/",
        headers=superuser_token_headers,
        files={"file": ("tile.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 500
    assert list(local_storage.backend.root.rglob("*.*")) == []


def test_storage_delete_failure_restores_image_database_state(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    local_storage: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    image = _upload_image(client, superuser_token_headers, product_id)

    def fail_delete(_key: str) -> None:
        raise OSError("simulated storage failure")

    monkeypatch.setattr(local_storage.backend, "delete", fail_delete)
    response = client.delete(
        f"{settings.API_V1_STR}/products/{product_id}/images/{image['id']}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 503
    images = _product_images(client, superuser_token_headers, product_id)
    assert len(images) == 1
    assert images[0]["id"] == image["id"]
    assert images[0]["is_primary"] is True


def test_invalid_upload_is_rejected_without_creating_image(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    response = client.post(
        f"{settings.API_V1_STR}/products/{product_id}/images/",
        headers=superuser_token_headers,
        files={"file": ("tile.svg", b"<svg/>", "image/svg+xml")},
    )

    assert response.status_code == 422
    assert _product_images(client, superuser_token_headers, product_id) == []


def test_reorder_requires_every_product_image_exactly_once(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    first = _upload_image(client, superuser_token_headers, product_id)
    second = _upload_image(client, superuser_token_headers, product_id)

    response = client.put(
        f"{settings.API_V1_STR}/products/{product_id}/images/order",
        headers=superuser_token_headers,
        json={"image_ids": [first["id"], first["id"]]},
    )

    assert response.status_code == 422
    assert [
        image["id"]
        for image in _product_images(client, superuser_token_headers, product_id)
    ] == [first["id"], second["id"]]


def test_image_response_urls_are_generated_by_storage_backend(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, superuser_token_headers)
    image = _upload_image(client, superuser_token_headers, product_id)

    assert image["url"] == (
        f"{settings.API_V1_STR}/product-images/{image['id']}/content"
    )
    assert image["storage_key"].startswith("product-images/")


def test_missing_product_image_content_is_not_found(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/product-images/{uuid.uuid4()}/content",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 404
