import logging
import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import col, delete, func, select

from app.api.deps import CurrentUser, SessionDep, ensure_permissions
from app.core.config import settings
from app.core.i18n import t
from app.core.rbac import (
    PRODUCTS_CREATE,
    PRODUCTS_DELETE,
    PRODUCTS_MANAGE_IMAGES,
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
    ProductImage,
    ProductImageOrder,
    ProductImagePublic,
    ProductImagesPublic,
    ProductPublic,
    ProductsPublic,
    ProductUpdate,
)
from app.services.storage import (
    StorageNamespace,
    UploadValidationError,
    get_storage_service,
)

router = APIRouter(prefix="/products", tags=["products"])
image_router = APIRouter(prefix="/product-images", tags=["product-images"])
logger = logging.getLogger(__name__)


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
    images = sorted(
        product.images,
        key=lambda image: (
            image.sort_order,
            image.created_at is None,
            image.created_at.isoformat() if image.created_at else "",
            str(image.id),
        ),
    )
    storage = get_storage_service()
    return ProductPublic.model_validate(
        product,
        update={
            "stock_state": _stock_state(product),
            "images": [
                ProductImagePublic.model_validate(
                    image,
                    update={
                        "url": storage.access_url(
                            image.storage_key,
                            local_url=(
                                f"{settings.API_V1_STR}/product-images/{image.id}/content"
                            ),
                        )
                    },
                )
                for image in images
            ],
        },
    )


def _get_manageable_product(*, session: SessionDep, product_id: uuid.UUID) -> Product:
    product = session.exec(
        select(Product).where(Product.id == product_id).with_for_update()
    ).first()
    if product is None:
        raise HTTPException(status_code=404, detail=t("product_not_found"))
    return product


def _locked_product_images(
    *, session: SessionDep, product_id: uuid.UUID
) -> Sequence[ProductImage]:
    return session.exec(
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(
            col(ProductImage.sort_order),
            col(ProductImage.created_at),
            col(ProductImage.id),
        )
        .with_for_update()
    ).all()


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
    statement = select(Product).options(selectinload(cast(Any, Product.images)))
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


@router.post(
    "/{product_id}/images/", response_model=ProductImagePublic, status_code=201
)
def upload_product_image(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    product_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str | None, Form(max_length=255)] = None,
) -> ProductImagePublic:
    ensure_permissions(current_user, PRODUCTS_MANAGE_IMAGES)
    product = _get_manageable_product(session=session, product_id=product_id)
    existing_images = _locked_product_images(session=session, product_id=product_id)
    storage = get_storage_service()
    content = file.file.read(storage.max_file_size_bytes + 1)
    try:
        stored = storage.upload(
            content=content,
            content_type=file.content_type or "",
            namespace=StorageNamespace.PRODUCT_IMAGES,
        )
    except UploadValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    image = ProductImage(
        product_id=product.id,
        storage_key=stored.key,
        content_type=stored.content_type,
        alt_text=alt_text,
        sort_order=max((image.sort_order for image in existing_images), default=-1) + 1,
        is_primary=not existing_images,
    )
    session.add(image)
    try:
        session.commit()
        session.refresh(image)
    except Exception as error:
        session.rollback()
        try:
            storage.delete(stored.key)
        except Exception:
            logger.exception(
                "Failed to compensate product image upload for key %s", stored.key
            )
        raise HTTPException(
            status_code=500, detail=t("product_image_upload_failed")
        ) from error
    return _product_image_public(image)


def _product_image_public(image: ProductImage) -> ProductImagePublic:
    local_url = f"{settings.API_V1_STR}/product-images/{image.id}/content"
    url = get_storage_service().access_url(
        image.storage_key, private=False, local_url=local_url
    )
    return ProductImagePublic.model_validate(image, update={"url": url})


@router.delete("/{product_id}/images/{image_id}", response_model=Message)
def delete_product_image(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    product_id: uuid.UUID,
    image_id: uuid.UUID,
) -> Message:
    ensure_permissions(current_user, PRODUCTS_MANAGE_IMAGES)
    _get_manageable_product(session=session, product_id=product_id)
    images = _locked_product_images(session=session, product_id=product_id)
    image = next((item for item in images if item.id == image_id), None)
    if image is None:
        raise HTTPException(status_code=404, detail=t("product_image_not_found"))

    image_data = {
        "id": image.id,
        "product_id": image.product_id,
        "storage_key": image.storage_key,
        "content_type": image.content_type,
        "url": image.url,
        "alt_text": image.alt_text,
        "sort_order": image.sort_order,
        "created_at": image.created_at,
    }
    was_primary = image.is_primary
    next_primary = (
        next((item for item in images if item.id != image.id), None)
        if was_primary
        else None
    )
    if next_primary is not None:
        # Release the unique primary slot before promoting its replacement.
        image.is_primary = False
        session.flush()
        next_primary.is_primary = True
    session.delete(image)
    try:
        session.commit()
    except Exception as error:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=t("product_image_delete_failed")
        ) from error

    storage = get_storage_service()
    try:
        storage.delete(image.storage_key)
    except Exception as error:
        session.rollback()
        try:
            restored_primary = (
                session.get(ProductImage, next_primary.id) if next_primary else None
            )
            if restored_primary is not None:
                restored_primary.is_primary = False
                session.flush()
            session.add(ProductImage(**image_data, is_primary=was_primary))
            session.commit()
        except Exception:
            session.rollback()
            logger.exception(
                "Failed to restore database state after product image delete failure: %s",
                image.id,
            )
        raise HTTPException(
            status_code=503, detail=t("product_image_storage_delete_failed")
        ) from error
    return Message(message=t("product_image_deleted_successfully"))


@router.put("/{product_id}/images/order", response_model=ProductImagesPublic)
def reorder_product_images(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    product_id: uuid.UUID,
    order: ProductImageOrder,
) -> ProductImagesPublic:
    ensure_permissions(current_user, PRODUCTS_MANAGE_IMAGES)
    _get_manageable_product(session=session, product_id=product_id)
    images = _locked_product_images(session=session, product_id=product_id)
    requested_ids = order.image_ids
    if len(requested_ids) != len(set(requested_ids)) or set(requested_ids) != {
        image.id for image in images
    }:
        raise HTTPException(status_code=422, detail=t("product_image_order_invalid"))
    image_by_id = {image.id: image for image in images}
    ordered_images = [image_by_id[image_id] for image_id in requested_ids]
    for sort_order, image in enumerate(ordered_images):
        image.sort_order = sort_order
    session.add_all(ordered_images)
    session.commit()
    return ProductImagesPublic(
        data=[_product_image_public(image) for image in ordered_images],
        count=len(ordered_images),
    )


@router.put(
    "/{product_id}/images/{image_id}/primary", response_model=ProductImagePublic
)
def set_primary_product_image(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    product_id: uuid.UUID,
    image_id: uuid.UUID,
) -> ProductImagePublic:
    ensure_permissions(current_user, PRODUCTS_MANAGE_IMAGES)
    _get_manageable_product(session=session, product_id=product_id)
    images = _locked_product_images(session=session, product_id=product_id)
    target = next((image for image in images if image.id == image_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=t("product_image_not_found"))
    for image in images:
        if image.is_primary and image.id != target.id:
            image.is_primary = False
    session.flush()
    target.is_primary = True
    session.add(target)
    session.commit()
    session.refresh(target)
    return _product_image_public(target)


@image_router.get("/{image_id}/content")
def read_product_image_content(
    *,
    image_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> StreamingResponse:
    read_all = _ensure_read_access(current_user)
    image = session.get(ProductImage, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail=t("product_image_not_found"))
    _get_readable_product(
        session=session, product_id=image.product_id, read_all=read_all
    )
    try:
        content = get_storage_service().stream(image.storage_key)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail=t("product_image_not_found")
        ) from error
    return StreamingResponse(content, media_type=image.content_type)
