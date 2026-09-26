import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select

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
    BrandCreate,
    BrandPublic,
    BrandsPublic,
    BrandUpdate,
    Message,
    Product,
)

router = APIRouter(prefix="/brands", tags=["brands"])


def _ensure_read_access(current_user: CurrentUser) -> None:
    ensure_permissions(
        current_user, PRODUCTS_READ, PRODUCTS_READ_ANY, require_all=False
    )


def _brand_or_404(
    *, session: SessionDep, brand_id: uuid.UUID, current_user: CurrentUser
) -> Brand:
    brand = session.get(Brand, brand_id)
    if brand is None or (
        not brand.is_active and not has_permissions(current_user, PRODUCTS_READ_ANY)
    ):
        raise HTTPException(status_code=404, detail=t("brand_not_found"))
    return brand


def _raise_duplicate_brand() -> None:
    raise HTTPException(status_code=409, detail=t("brand_name_or_slug_exists"))


def _check_brand_conflict(
    *, session: SessionDep, name: str, slug: str, exclude_id: uuid.UUID | None = None
) -> None:
    statement = select(Brand).where(or_(Brand.name == name, Brand.slug == slug))
    if exclude_id is not None:
        statement = statement.where(Brand.id != exclude_id)
    if session.exec(statement).first() is not None:
        _raise_duplicate_brand()


@router.get("/", response_model=BrandsPublic)
def read_brands(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    _ensure_read_access(current_user)
    statement = select(Brand)
    if not has_permissions(current_user, PRODUCTS_READ_ANY):
        statement = statement.where(Brand.is_active.is_(True))
    count = session.exec(select(func.count()).select_from(statement.subquery())).one()
    brands = session.exec(
        statement.order_by(Brand.name).offset(skip).limit(limit)
    ).all()
    return BrandsPublic(
        data=[BrandPublic.model_validate(brand) for brand in brands], count=count
    )


@router.get("/{brand_id}", response_model=BrandPublic)
def read_brand(
    brand_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Brand:
    _ensure_read_access(current_user)
    return _brand_or_404(session=session, brand_id=brand_id, current_user=current_user)


@router.post("/", response_model=BrandPublic, status_code=201)
def create_brand(
    *, session: SessionDep, current_user: CurrentUser, brand_in: BrandCreate
) -> Brand:
    ensure_permissions(current_user, PRODUCTS_CREATE)
    _check_brand_conflict(session=session, name=brand_in.name, slug=brand_in.slug)
    brand = Brand.model_validate(brand_in)
    session.add(brand)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        _raise_duplicate_brand()
    session.refresh(brand)
    return brand


@router.patch("/{brand_id}", response_model=BrandPublic)
def update_brand(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    brand_id: uuid.UUID,
    brand_in: BrandUpdate,
) -> Brand:
    ensure_permissions(current_user, PRODUCTS_UPDATE)
    brand = session.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail=t("brand_not_found"))

    update_data = brand_in.model_dump(exclude_unset=True)
    for field in ("name", "slug", "is_active"):
        if update_data.get(field) is None:
            update_data.pop(field, None)
    _check_brand_conflict(
        session=session,
        name=update_data.get("name", brand.name),
        slug=update_data.get("slug", brand.slug),
        exclude_id=brand.id,
    )
    brand.sqlmodel_update(update_data)
    session.add(brand)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        _raise_duplicate_brand()
    session.refresh(brand)
    return brand


@router.delete("/{brand_id}", response_model=Message)
def delete_brand(
    *, session: SessionDep, current_user: CurrentUser, brand_id: uuid.UUID
) -> Message:
    ensure_permissions(current_user, PRODUCTS_DELETE)
    brand = session.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail=t("brand_not_found"))
    if session.exec(
        select(Product.id).where(Product.brand_id == brand_id).limit(1)
    ).first():
        raise HTTPException(status_code=409, detail=t("brand_in_use"))
    session.delete(brand)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail=t("brand_in_use"))
    return Message(message=t("brand_deleted_successfully"))
