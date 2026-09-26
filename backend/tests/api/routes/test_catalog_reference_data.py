import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.models import Brand, Category, Product
from tests.utils.utils import random_lower_string


def _category_payload() -> dict[str, str]:
    suffix = random_lower_string()
    return {"name": f"Category {suffix}", "slug": f"category-{suffix}"}


def _brand_payload() -> dict[str, str]:
    suffix = random_lower_string()
    return {"name": f"Brand {suffix}", "slug": f"brand-{suffix}"}


def test_category_crud_and_active_catalog_visibility(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    payload = _category_payload()
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    category_id = response.json()["id"]

    listed = client.get(
        f"{settings.API_V1_STR}/categories/", headers=superuser_token_headers
    )
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1
    assert any(row["id"] == category_id for row in listed.json()["data"])

    read = client.get(
        f"{settings.API_V1_STR}/categories/{category_id}",
        headers=normal_user_token_headers,
    )
    assert read.status_code == 200
    assert read.json()["slug"] == payload["slug"]

    updated = client.patch(
        f"{settings.API_V1_STR}/categories/{category_id}",
        headers=superuser_token_headers,
        json={"description": "Updated category", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated category"

    customer_list = client.get(
        f"{settings.API_V1_STR}/categories/", headers=normal_user_token_headers
    )
    assert all(row["id"] != category_id for row in customer_list.json()["data"])

    deleted = client.delete(
        f"{settings.API_V1_STR}/categories/{category_id}",
        headers=superuser_token_headers,
    )
    assert deleted.status_code == 200

    missing = client.get(
        f"{settings.API_V1_STR}/categories/{category_id}",
        headers=superuser_token_headers,
    )
    assert missing.status_code == 404


def test_brand_crud(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    payload = _brand_payload()
    response = client.post(
        f"{settings.API_V1_STR}/brands/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    brand_id = response.json()["id"]

    listed = client.get(
        f"{settings.API_V1_STR}/brands/", headers=superuser_token_headers
    )
    assert listed.status_code == 200
    assert any(row["id"] == brand_id for row in listed.json()["data"])

    read = client.get(
        f"{settings.API_V1_STR}/brands/{brand_id}", headers=superuser_token_headers
    )
    assert read.status_code == 200
    assert read.json()["name"] == payload["name"]

    updated = client.patch(
        f"{settings.API_V1_STR}/brands/{brand_id}",
        headers=superuser_token_headers,
        json={"name": f"{payload['name']} Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"].endswith(" Updated")

    deleted = client.delete(
        f"{settings.API_V1_STR}/brands/{brand_id}",
        headers=superuser_token_headers,
    )
    assert deleted.status_code == 200


@pytest.mark.parametrize(
    ("resource", "payload_factory"),
    [("categories", _category_payload), ("brands", _brand_payload)],
)
def test_duplicate_reference_data_returns_conflict(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    resource: str,
    payload_factory: Callable[[], dict[str, str]],
) -> None:
    payload = payload_factory()
    created = client.post(
        f"{settings.API_V1_STR}/{resource}/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert created.status_code == 201, created.text

    duplicate = client.post(
        f"{settings.API_V1_STR}/{resource}/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert duplicate.status_code == 409
    client.delete(
        f"{settings.API_V1_STR}/{resource}/{created.json()['id']}",
        headers=superuser_token_headers,
    )


@pytest.mark.parametrize(
    ("resource", "payload_factory"),
    [("categories", _category_payload), ("brands", _brand_payload)],
)
def test_update_duplicate_reference_data_returns_conflict(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    resource: str,
    payload_factory: Callable[[], dict[str, str]],
) -> None:
    first = client.post(
        f"{settings.API_V1_STR}/{resource}/",
        headers=superuser_token_headers,
        json=payload_factory(),
    )
    second = client.post(
        f"{settings.API_V1_STR}/{resource}/",
        headers=superuser_token_headers,
        json=payload_factory(),
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    conflict = client.patch(
        f"{settings.API_V1_STR}/{resource}/{first.json()['id']}",
        headers=superuser_token_headers,
        json={"name": second.json()["name"]},
    )
    assert conflict.status_code == 409

    for record in (first, second):
        client.delete(
            f"{settings.API_V1_STR}/{resource}/{record.json()['id']}",
            headers=superuser_token_headers,
        )


@pytest.mark.parametrize("resource", ["categories", "brands"])
def test_reference_data_read_update_and_delete_not_found(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    resource: str,
) -> None:
    resource_id = uuid.uuid4()
    url = f"{settings.API_V1_STR}/{resource}/{resource_id}"

    assert client.get(url, headers=superuser_token_headers).status_code == 404
    assert (
        client.patch(
            url, headers=superuser_token_headers, json={"description": "missing"}
        ).status_code
        == 404
    )
    assert client.delete(url, headers=superuser_token_headers).status_code == 404


@pytest.mark.parametrize(
    ("resource", "payload_factory", "model"),
    [
        ("categories", _category_payload, Category),
        ("brands", _brand_payload, Brand),
    ],
)
def test_delete_reference_data_in_use_returns_conflict(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    resource: str,
    payload_factory: Callable[[], dict[str, str]],
    model: type[Category] | type[Brand],
) -> None:
    payload = payload_factory()
    created = client.post(
        f"{settings.API_V1_STR}/{resource}/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    reference = db.get(model, uuid.UUID(created.json()["id"]))
    assert reference is not None

    product_data: dict[str, object] = {
        "name": f"Product {random_lower_string()}",
        "sku": random_lower_string(),
        "slug": random_lower_string(),
        "category_id": reference.id if resource == "categories" else uuid.uuid4(),
        "brand_id": reference.id if resource == "brands" else None,
    }
    if resource == "brands":
        category = Category(
            name=f"Category {random_lower_string()}", slug=random_lower_string()
        )
        db.add(category)
        db.commit()
        product_data["category_id"] = category.id
    product = Product.model_validate(product_data)
    db.add(product)
    db.commit()

    response = client.delete(
        f"{settings.API_V1_STR}/{resource}/{reference.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 409

    db.exec(delete(Product).where(Product.id == product.id))
    db.commit()
    db.delete(reference)
    db.commit()
    if resource == "brands":
        db.delete(category)
        db.commit()


@pytest.mark.parametrize(
    ("resource", "payload_factory"),
    [("categories", _category_payload), ("brands", _brand_payload)],
)
def test_default_user_cannot_mutate_reference_data(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    resource: str,
    payload_factory: Callable[[], dict[str, str]],
) -> None:
    payload = payload_factory()
    created = client.post(
        f"{settings.API_V1_STR}/{resource}/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    resource_id = created.json()["id"]

    create_attempt = client.post(
        f"{settings.API_V1_STR}/{resource}/",
        headers=normal_user_token_headers,
        json=payload_factory(),
    )
    update_attempt = client.patch(
        f"{settings.API_V1_STR}/{resource}/{resource_id}",
        headers=normal_user_token_headers,
        json={"description": "Unauthorized"},
    )
    delete_attempt = client.delete(
        f"{settings.API_V1_STR}/{resource}/{resource_id}",
        headers=normal_user_token_headers,
    )

    assert create_attempt.status_code == 403
    assert update_attempt.status_code == 403
    assert delete_attempt.status_code == 403
    client.delete(
        f"{settings.API_V1_STR}/{resource}/{resource_id}",
        headers=superuser_token_headers,
    )


def test_reference_data_read_requires_authentication(client: TestClient) -> None:
    assert client.get(f"{settings.API_V1_STR}/categories/").status_code == 401
    assert client.get(f"{settings.API_V1_STR}/brands/").status_code == 401
