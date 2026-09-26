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
    CategoriesPublic,
    Category,
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    Message,
    Product,
)

router = APIRouter(prefix="/categories", tags=["categories"])


def _ensure_read_access(current_user: CurrentUser) -> None:
    ensure_permissions(
        current_user, PRODUCTS_READ, PRODUCTS_READ_ANY, require_all=False
    )


def _category_or_404(
    *, session: SessionDep, category_id: uuid.UUID, current_user: CurrentUser
) -> Category:
    category = session.get(Category, category_id)
    if category is None or (
        not category.is_active and not has_permissions(current_user, PRODUCTS_READ_ANY)
    ):
        raise HTTPException(status_code=404, detail=t("category_not_found"))
    return category


def _raise_duplicate_category() -> None:
    raise HTTPException(status_code=409, detail=t("category_name_or_slug_exists"))


def _check_category_conflict(
    *, session: SessionDep, name: str, slug: str, exclude_id: uuid.UUID | None = None
) -> None:
    statement = select(Category).where(
        or_(Category.name == name, Category.slug == slug)
    )
    if exclude_id is not None:
        statement = statement.where(Category.id != exclude_id)
    if session.exec(statement).first() is not None:
        _raise_duplicate_category()


@router.get("/", response_model=CategoriesPublic)
def read_categories(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    _ensure_read_access(current_user)
    statement = select(Category)
    if not has_permissions(current_user, PRODUCTS_READ_ANY):
        statement = statement.where(Category.is_active.is_(True))
    count = session.exec(select(func.count()).select_from(statement.subquery())).one()
    categories = session.exec(
        statement.order_by(Category.name).offset(skip).limit(limit)
    ).all()
    return CategoriesPublic(
        data=[CategoryPublic.model_validate(category) for category in categories],
        count=count,
    )


@router.get("/{category_id}", response_model=CategoryPublic)
def read_category(
    category_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Category:
    _ensure_read_access(current_user)
    return _category_or_404(
        session=session, category_id=category_id, current_user=current_user
    )


@router.post("/", response_model=CategoryPublic, status_code=201)
def create_category(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    category_in: CategoryCreate,
) -> Category:
    ensure_permissions(current_user, PRODUCTS_CREATE)
    _check_category_conflict(
        session=session, name=category_in.name, slug=category_in.slug
    )
    category = Category.model_validate(category_in)
    session.add(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        _raise_duplicate_category()
    session.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryPublic)
def update_category(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    category_id: uuid.UUID,
    category_in: CategoryUpdate,
) -> Category:
    ensure_permissions(current_user, PRODUCTS_UPDATE)
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail=t("category_not_found"))

    update_data = category_in.model_dump(exclude_unset=True)
    for field in ("name", "slug", "is_active"):
        if update_data.get(field) is None:
            update_data.pop(field, None)
    _check_category_conflict(
        session=session,
        name=update_data.get("name", category.name),
        slug=update_data.get("slug", category.slug),
        exclude_id=category.id,
    )
    category.sqlmodel_update(update_data)
    session.add(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        _raise_duplicate_category()
    session.refresh(category)
    return category


@router.delete("/{category_id}", response_model=Message)
def delete_category(
    *, session: SessionDep, current_user: CurrentUser, category_id: uuid.UUID
) -> Message:
    ensure_permissions(current_user, PRODUCTS_DELETE)
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail=t("category_not_found"))
    if session.exec(
        select(Product.id).where(Product.category_id == category_id).limit(1)
    ).first():
        raise HTTPException(status_code=409, detail=t("category_in_use"))
    session.delete(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail=t("category_in_use"))
    return Message(message=t("category_deleted_successfully"))
