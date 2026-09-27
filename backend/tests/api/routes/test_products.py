from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.utils.utils import random_lower_string


def _create_category(client: TestClient, headers: dict[str, str]) -> str:
    suffix = random_lower_string()
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=headers,
        json={"name": f"Category {suffix}", "slug": f"category-{suffix}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_brand(client: TestClient, headers: dict[str, str]) -> str:
    suffix = random_lower_string()
    response = client.post(
        f"{settings.API_V1_STR}/brands/",
        headers=headers,
        json={"name": f"Brand {suffix}", "slug": f"brand-{suffix}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _product_payload(category_id: str, brand_id: str) -> dict:
    suffix = random_lower_string()
    return {
        "name": f"Porcelain tile {suffix}",
        "sku": f"SKU-{suffix}",
        "slug": f"tile-{suffix}",
        "category_id": category_id,
        "brand_id": brand_id,
        "product_type": "floor_tile",
        "material": "porcelain",
        "finish": "matte",
        "usage_area": "indoor",
        "color_family": "grey",
        "width_mm": 600,
        "height_mm": 1200,
        "thickness_mm": 9,
        "price": "24.50",
        "stock_quantity": 4,
        "low_stock_threshold": 5,
        "is_featured": True,
    }


def test_product_create_update_deactivate_read_and_delete(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    category_id = _create_category(client, superuser_token_headers)
    brand_id = _create_brand(client, superuser_token_headers)
    payload = _product_payload(category_id, brand_id)

    created = client.post(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    product = created.json()
    assert product["price"] == "24.50"
    assert product["stock_state"] == "low_stock"
    product_id = product["id"]

    read = client.get(
        f"{settings.API_V1_STR}/products/{product_id}",
        headers=superuser_token_headers,
    )
    assert read.status_code == 200
    assert read.json()["sku"] == payload["sku"]

    updated = client.patch(
        f"{settings.API_V1_STR}/products/{product_id}",
        headers=superuser_token_headers,
        json={"price": "26.75", "stock_quantity": 0},
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == "26.75"
    assert updated.json()["stock_state"] == "out_of_stock"

    deactivated = client.post(
        f"{settings.API_V1_STR}/products/{product_id}/deactivate",
        headers=superuser_token_headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert (
        client.get(
            f"{settings.API_V1_STR}/products/{product_id}",
            headers=normal_user_token_headers,
        ).status_code
        == 404
    )

    deleted = client.delete(
        f"{settings.API_V1_STR}/products/{product_id}",
        headers=superuser_token_headers,
    )
    assert deleted.status_code == 200
    assert (
        client.get(
            f"{settings.API_V1_STR}/products/{product_id}",
            headers=superuser_token_headers,
        ).status_code
        == 404
    )


def test_combined_product_filters_and_accurate_pagination(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    category_id = _create_category(client, superuser_token_headers)
    brand_id = _create_brand(client, superuser_token_headers)
    payloads = [_product_payload(category_id, brand_id) for _ in range(3)]
    payloads[0].update(price="20.00", stock_quantity=10, is_featured=True)
    payloads[1].update(price="24.50", stock_quantity=4, is_featured=True)
    payloads[2].update(price="80.00", stock_quantity=0, is_featured=True)
    for payload in payloads:
        response = client.post(
            f"{settings.API_V1_STR}/products/",
            headers=superuser_token_headers,
            json=payload,
        )
        assert response.status_code == 201, response.text

    filtered = client.get(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        params={
            "q": "porcelain",
            "category_id": category_id,
            "brand_id": brand_id,
            "product_type": "floor_tile",
            "material": "porcelain",
            "finish": "matte",
            "usage_area": "indoor",
            "color_family": "grey",
            "width_mm": 600,
            "height_mm": 1200,
            "min_price": 20,
            "max_price": 100,
            "is_active": True,
            "is_featured": True,
            "skip": 0,
            "limit": 1,
        },
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["count"] == 3
    assert len(filtered.json()["data"]) == 1

    low_stock = client.get(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        params={"category_id": category_id, "stock_state": "low_stock"},
    )
    assert low_stock.status_code == 200
    assert low_stock.json()["count"] == 1
    assert low_stock.json()["data"][0]["stock_state"] == "low_stock"


def test_regular_user_sees_only_active_products(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    category_id = _create_category(client, superuser_token_headers)
    brand_id = _create_brand(client, superuser_token_headers)
    payload = _product_payload(category_id, brand_id)
    payload["is_active"] = False
    created = client.post(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert created.status_code == 201, created.text

    customer_list = client.get(
        f"{settings.API_V1_STR}/products/", headers=normal_user_token_headers
    )
    assert customer_list.status_code == 200
    assert all(
        row["id"] != created.json()["id"] for row in customer_list.json()["data"]
    )
    assert (
        client.get(
            f"{settings.API_V1_STR}/products/{created.json()['id']}",
            headers=normal_user_token_headers,
        ).status_code
        == 404
    )


def test_product_conflicts_and_missing_related_records(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    category_id = _create_category(client, superuser_token_headers)
    brand_id = _create_brand(client, superuser_token_headers)
    payload = _product_payload(category_id, brand_id)
    first = client.post(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert first.status_code == 201
    assert (
        client.post(
            f"{settings.API_V1_STR}/products/",
            headers=superuser_token_headers,
            json=payload,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{settings.API_V1_STR}/products/",
            headers=superuser_token_headers,
            json=_product_payload(str(uuid.uuid4()), brand_id),
        ).status_code
        == 404
    )
    second = client.post(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        json=_product_payload(category_id, brand_id),
    )
    assert second.status_code == 201, second.text
    duplicate_update = client.patch(
        f"{settings.API_V1_STR}/products/{second.json()['id']}",
        headers=superuser_token_headers,
        json={"sku": first.json()["sku"]},
    )
    assert duplicate_update.status_code == 409


def test_product_detail_update_and_delete_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    product_id = uuid.uuid4()
    url = f"{settings.API_V1_STR}/products/{product_id}"
    assert client.get(url, headers=superuser_token_headers).status_code == 404
    assert (
        client.patch(
            url, headers=superuser_token_headers, json={"name": "Missing"}
        ).status_code
        == 404
    )
    assert client.delete(url, headers=superuser_token_headers).status_code == 404


def test_suitable_surface_filter_returns_only_eligible_products(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    category_id = _create_category(client, superuser_token_headers)
    brand_id = _create_brand(client, superuser_token_headers)
    floor_only = _product_payload(category_id, brand_id)
    floor_only.update(suitable_surfaces=["FLOOR"])
    wall_only = _product_payload(category_id, brand_id)
    wall_only.update(suitable_surfaces=["WALL"])
    both = _product_payload(category_id, brand_id)
    both.update(suitable_surfaces=["WALL", "FLOOR"])
    none = _product_payload(category_id, brand_id)
    none.update(suitable_surfaces=[])
    for payload in (floor_only, wall_only, both, none):
        response = client.post(
            f"{settings.API_V1_STR}/products/",
            headers=superuser_token_headers,
            json=payload,
        )
        assert response.status_code == 201, response.text

    floor = client.get(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        params={
            "category_id": category_id,
            "suitable_surface": "FLOOR",
            "is_active": True,
            "limit": 1,
        },
    )
    wall = client.get(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        params={"category_id": category_id, "suitable_surface": "WALL"},
    )
    combined = client.get(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        params={
            "category_id": category_id,
            "suitable_surface": "FLOOR",
            "q": wall_only["sku"],
        },
    )
    invalid = client.get(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        params={"suitable_surface": "CEILING"},
    )

    assert floor.status_code == 200, floor.text
    assert floor.json()["count"] == 2
    assert len(floor.json()["data"]) == 1
    assert all("FLOOR" in row["suitable_surfaces"] for row in floor.json()["data"])
    assert wall.status_code == 200
    assert wall.json()["count"] == 2
    assert all("WALL" in row["suitable_surfaces"] for row in wall.json()["data"])
    assert combined.status_code == 200
    assert combined.json()["count"] == 0
    assert invalid.status_code == 422


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_product_mutations_require_permissions(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    method: str,
) -> None:
    category_id = _create_category(client, superuser_token_headers)
    brand_id = _create_brand(client, superuser_token_headers)
    created = client.post(
        f"{settings.API_V1_STR}/products/",
        headers=superuser_token_headers,
        json=_product_payload(category_id, brand_id),
    )
    assert created.status_code == 201
    response = client.request(
        method,
        f"{settings.API_V1_STR}/products/{created.json()['id']}",
        headers=normal_user_token_headers,
        json={"name": "Unauthorized"} if method == "patch" else None,
    )
    assert response.status_code == 403
