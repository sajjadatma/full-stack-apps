from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.core.rbac import GENERATIONS_READ_OWN, PRODUCTS_READ
from app.models import (
    Category,
    GenerationJob,
    GenerationStatus,
    Product,
    Role,
    User,
    UserCreate,
    VisualizationProject,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def _make_product(
    db: Session,
    *,
    is_active: bool,
    stock_quantity: int,
    low_stock_threshold: int | None,
) -> Product:
    suffix = random_lower_string()
    category = Category(name=f"Dashboard {suffix}", slug=f"dashboard-{suffix}")
    db.add(category)
    db.flush()
    product = Product(
        name=f"Dashboard tile {suffix}",
        sku=f"DASH-{suffix}",
        slug=f"dashboard-tile-{suffix}",
        category_id=category.id,
        is_active=is_active,
        stock_quantity=stock_quantity,
        low_stock_threshold=low_stock_threshold,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _make_generation(
    db: Session, *, owner: User, product: Product, status: GenerationStatus
) -> None:
    project = VisualizationProject(
        owner_id=owner.id,
        source_image_key=f"rooms/{uuid4()}.png",
        source_image_content_type="image/png",
        source_image_size_bytes=1,
        source_image_width_px=1,
        source_image_height_px=1,
    )
    db.add(project)
    db.flush()
    db.add(
        GenerationJob(
            project_id=project.id,
            selected_product_id=product.id,
            target_surface="FLOOR",
            status=status,
        )
    )
    db.commit()


def _make_user_with_permissions(
    *, db: Session, client: TestClient, permissions: list[str]
) -> tuple[User, dict[str, str]]:
    suffix = random_lower_string()
    role = Role(
        name=f"Dashboard role {suffix}",
        slug=f"dashboard-{suffix}",
        is_system=False,
        permissions=[],
    )
    role.permissions = [
        permission
        for code in permissions
        if (permission := crud.get_permission_by_code(session=db, code=code))
    ]
    db.add(role)
    db.commit()
    db.refresh(role)
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password="test-password-123"),
        role=role,
    )
    headers = authentication_token_from_email(client=client, email=user.email, db=db)
    return user, headers


def test_dashboard_summary_aggregates_product_and_generation_metrics_by_scope(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    admin = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert admin is not None
    ordinary_user, ordinary_headers = _make_user_with_permissions(
        db=db, client=client, permissions=[PRODUCTS_READ, GENERATIONS_READ_OWN]
    )
    before_admin = client.get(
        f"{settings.API_V1_STR}/dashboard/summary/",
        headers=superuser_token_headers,
    )
    before_ordinary = client.get(
        f"{settings.API_V1_STR}/dashboard/summary/", headers=ordinary_headers
    )
    assert before_admin.status_code == before_ordinary.status_code == 200

    active_low = _make_product(
        db, is_active=True, stock_quantity=2, low_stock_threshold=5
    )
    _make_product(db, is_active=True, stock_quantity=0, low_stock_threshold=5)
    _make_product(db, is_active=False, stock_quantity=1, low_stock_threshold=5)
    _make_generation(
        db, owner=ordinary_user, product=active_low, status=GenerationStatus.PENDING
    )
    _make_generation(
        db, owner=ordinary_user, product=active_low, status=GenerationStatus.COMPLETED
    )
    _make_generation(
        db, owner=admin, product=active_low, status=GenerationStatus.PROCESSING
    )
    _make_generation(
        db, owner=admin, product=active_low, status=GenerationStatus.FAILED
    )

    after_admin = client.get(
        f"{settings.API_V1_STR}/dashboard/summary/",
        headers=superuser_token_headers,
    )
    after_ordinary = client.get(
        f"{settings.API_V1_STR}/dashboard/summary/", headers=ordinary_headers
    )
    assert after_admin.status_code == after_ordinary.status_code == 200

    before_admin_json = before_admin.json()
    admin_json = after_admin.json()
    assert admin_json["products"]["total_products"] == (
        before_admin_json["products"]["total_products"] + 3
    )
    assert admin_json["products"]["active_products"] == (
        before_admin_json["products"]["active_products"] + 2
    )
    assert admin_json["products"]["low_stock_products"] == (
        before_admin_json["products"]["low_stock_products"] + 1
    )
    assert admin_json["generations"]["total"] == (
        before_admin_json["generations"]["total"] + 4
    )
    assert {
        key: admin_json["generations"][key]
        - before_admin_json["generations"][key]
        for key in ("pending", "processing", "completed", "failed")
    } == {"pending": 1, "processing": 1, "completed": 1, "failed": 1}

    before_ordinary_json = before_ordinary.json()
    ordinary_json = after_ordinary.json()
    assert ordinary_json["products"]["total_products"] == (
        before_ordinary_json["products"]["total_products"] + 2
    )
    assert ordinary_json["products"]["active_products"] == (
        before_ordinary_json["products"]["active_products"] + 2
    )
    assert ordinary_json["products"]["low_stock_products"] == (
        before_ordinary_json["products"]["low_stock_products"] + 1
    )
    assert ordinary_json["generations"]["total"] == (
        before_ordinary_json["generations"]["total"] + 2
    )
    assert {
        key: ordinary_json["generations"][key]
        - before_ordinary_json["generations"][key]
        for key in ("pending", "processing", "completed", "failed")
    } == {"pending": 1, "processing": 0, "completed": 1, "failed": 0}


def test_dashboard_summary_returns_only_authorized_metric_sections(
    client: TestClient,
    db: Session,
) -> None:
    _, products_only_headers = _make_user_with_permissions(
        db=db, client=client, permissions=[PRODUCTS_READ]
    )
    _, generations_only_headers = _make_user_with_permissions(
        db=db, client=client, permissions=[GENERATIONS_READ_OWN]
    )
    products_only = client.get(
        f"{settings.API_V1_STR}/dashboard/summary/", headers=products_only_headers
    )
    generations_only = client.get(
        f"{settings.API_V1_STR}/dashboard/summary/",
        headers=generations_only_headers,
    )
    unauthenticated = client.get(f"{settings.API_V1_STR}/dashboard/summary/")

    assert products_only.status_code == generations_only.status_code == 200
    assert products_only.json()["products"] is not None
    assert products_only.json()["generations"] is None
    assert generations_only.json()["products"] is None
    assert generations_only.json()["generations"] is not None
    assert unauthenticated.status_code == 401


def test_dashboard_metrics_use_a_fixed_number_of_aggregate_queries(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    statements: list[str] = []

    def record_query(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        lowered = statement.lower()
        if lowered.lstrip().startswith("select"):
            statements.append(lowered)

    event.listen(engine, "before_cursor_execute", record_query)
    try:
        response = client.get(
            f"{settings.API_V1_STR}/dashboard/summary/",
            headers=superuser_token_headers,
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_query)

    assert response.status_code == 200
    metric_statements = [
        statement
        for statement in statements
        if "product" in statement or "generation_job" in statement
    ]
    assert len(metric_statements) == 2
    assert any("count(" in statement and "case when" in statement for statement in metric_statements)
    assert any("group by" in statement for statement in metric_statements)
