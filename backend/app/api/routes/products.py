import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import delete, func, select

from app.api.deps import CurrentUser, SessionDep, ensure_permissions
from app.core.i18n import t
from app.core.rbac import (
    PRODUCTS_CREATE,
    PRODUCTS_DELETE,
    PRODUCTS_READ,
    PRODUCTS_READ_ANY,
    PRODUCTS_UPDATE,
    has_permissions,
)
from app.models import (
    Brand,
    Category,
    Message,
    Product,
    ProductCreate,
    ProductPublic,
    ProductsPublic,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"])


def _ensure_read_access(current_user: CurrentUser) -> bool:
    ensure_permissions(
        current_user, PRODUCTS_READ, PRODUCTS_READ_ANY, require_all=False
    )
    return has_permissions(current_user, PRODUCTS_READ_ANY)


def _stock_state(product: Product) -> str:
    if product.stock_quantity == 0:
        return "out_of_stock"
    if (
        product.low_stock_threshold is not None
        and product.stock_quantity <= product.low_stock_threshold
    ):
        return "low_stock"
    return "in_stock"


def _product_public(product: Product) -> ProductPublic:
    return ProductPublic.model_validate(
        product, update={"stock_state": _stock_state(product)}
    )


def _get_readable_product(
    *, session: SessionDep, product_id: uuid.UUID, read_all: bool
) -> Product:
    product = session.get(Product, product_id)
    if product is None or (not product.is_active and not read_all):
        raise HTTPException(status_code=404, detail=t("product_not_found"))
    return product


def _validate_references(
    *, session: SessionDep, category_id: uuid.UUID, brand_id: uuid.UUID | None
) -> None:
    category = session.get(Category, category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail=t("product_category_not_found"))
    if brand_id is not None:
        brand = session.get(Brand, brand_id)
        if brand is None or not brand.is_active:
            raise HTTPException(status_code=404, detail=t("product_brand_not_found"))


def _raise_product_conflict() -> None:
    raise HTTPException(status_code=409, detail=t("product_sku_or_slug_exists"))


@router.get("/", response_model=ProductsPublic)
def read_products(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    q: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    product_type: str | None = None,
    material: str | None = None,
    finish: str | None = None,
    usage_area: str | None = None,
    color_family: str | None = None,
    width_mm: Annotated[int | None, Query(gt=0)] = None,
    height_mm: Annotated[int | None, Query(gt=0)] = None,
    thickness_mm: Annotated[int | None, Query(gt=0)] = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    stock_state: Literal["in_stock", "low_stock", "out_of_stock"] | None = None,
    is_active: bool | None = None,
    is_featured: bool | None = None,
) -> ProductsPublic:
    read_all = _ensure_read_access(current_user)
    statement = select(Product)
    if not read_all:
        statement = statement.where(Product.is_active.is_(True))
    elif is_active is not None:
        statement = statement.where(Product.is_active == is_active)

    for column, value in (
        (Product.category_id, category_id),
        (Product.brand_id, brand_id),
        (Product.product_type, product_type),
        (Product.material, material),
        (Product.finish, finish),
        (Product.usage_area, usage_area),
        (Product.color_family, color_family),
        (Product.width_mm, width_mm),
        (Product.height_mm, height_mm),
        (Product.thickness_mm, thickness_mm),
        (Product.is_featured, is_featured),
    ):
        if value is not None:
            statement = statement.where(column == value)

    if min_price is not None:
        statement = statement.where(Product.price >= min_price)
    if max_price is not None:
        statement = statement.where(Product.price <= max_price)
    if q:
        search = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Product.name.ilike(search),
                Product.sku.ilike(search),
                Product.slug.ilike(search),
                Product.description.ilike(search),
            )
        )
    if stock_state == "out_of_stock":
        statement = statement.where(Product.stock_quantity == 0)
    elif stock_state == "low_stock":
        statement = statement.where(
            Product.stock_quantity > 0,
            Product.low_stock_threshold.is_not(None),
            Product.stock_quantity <= Product.low_stock_threshold,
        )
    elif stock_state == "in_stock":
        statement = statement.where(
            Product.stock_quantity > 0,
            or_(
                Product.low_stock_threshold.is_(None),
                Product.stock_quantity > Product.low_stock_threshold,
            ),
        )

    count = session.exec(select(func.count()).select_from(statement.subquery())).one()
    products = session.exec(
        statement.order_by(Product.name, Product.id).offset(skip).limit(limit)
    ).all()
    return ProductsPublic(
        data=[_product_public(product) for product in products], count=count
    )


@router.get("/{product_id}", response_model=ProductPublic)
def read_product(
    product_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> ProductPublic:
    read_all = _ensure_read_access(current_user)
    return _product_public(
        _get_readable_product(session=session, product_id=product_id, read_all=read_all)
    )


@router.post("/", response_model=ProductPublic, status_code=201)
def create_product(
    *, session: SessionDep, current_user: CurrentUser, product_in: ProductCreate
) -> ProductPublic:
    ensure_permissions(current_user, PRODUCTS_CREATE)
    _validate_references(
        session=session,
        category_id=product_in.category_id,
        brand_id=product_in.brand_id,
    )
    product = Product.model_validate(product_in)
    session.add(product)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        _raise_product_conflict()
    session.refresh(product)
    return _product_public(product)


@router.patch("/{product_id}", response_model=ProductPublic)
def update_product(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    product_id: uuid.UUID,
    product_in: ProductUpdate,
) -> ProductPublic:
    ensure_permissions(current_user, PRODUCTS_UPDATE)
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=t("product_not_found"))
    update_data = product_in.model_dump(exclude_unset=True)
    for field in ("name", "sku", "slug", "category_id", "is_active", "is_featured"):
        if update_data.get(field) is None:
            update_data.pop(field, None)
    _validate_references(
        session=session,
        category_id=update_data.get("category_id", product.category_id),
        brand_id=update_data.get("brand_id", product.brand_id),
    )
    product.sqlmodel_update(update_data)
    session.add(product)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        _raise_product_conflict()
    session.refresh(product)
    return _product_public(product)


@router.post("/{product_id}/deactivate", response_model=ProductPublic)
def deactivate_product(
    *, session: SessionDep, current_user: CurrentUser, product_id: uuid.UUID
) -> ProductPublic:
    ensure_permissions(current_user, PRODUCTS_UPDATE)
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=t("product_not_found"))
    product.is_active = False
    session.add(product)
    session.commit()
    session.refresh(product)
    return _product_public(product)


@router.delete("/{product_id}", response_model=Message)
def delete_product(
    *, session: SessionDep, current_user: CurrentUser, product_id: uuid.UUID
) -> Message:
    ensure_permissions(current_user, PRODUCTS_DELETE)
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=t("product_not_found"))
    session.exec(delete(Product).where(Product.id == product_id))
    session.commit()
    return Message(message=t("product_deleted_successfully"))
