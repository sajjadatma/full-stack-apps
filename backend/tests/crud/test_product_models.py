from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine

from app.models import (
    Brand,
    BrandCreate,
    BrandPublic,
    BrandsPublic,
    BrandUpdate,
    CategoriesPublic,
    Category,
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    Product,
    ProductCreate,
    ProductImage,
    ProductImageCreate,
    ProductImagePublic,
    ProductImagesPublic,
    ProductImageUpdate,
    ProductPublic,
    ProductsPublic,
    ProductUpdate,
)


@pytest.fixture
def product_session() -> Session:
    engine = create_engine("sqlite://")
    tables = [
        Category.__table__,
        Brand.__table__,
        Product.__table__,
        ProductImage.__table__,
    ]
    SQLModel.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_product_schema_preserves_decimal_measurements_and_integer_stock() -> None:
    payload = ProductCreate(
        name="Carrara Porcelain",
        sku="CAR-60120",
        slug="carrara-porcelain",
        category_id=uuid4(),
        product_type="porcelain_tile",
        material="porcelain",
        price=Decimal("29.95"),
        sqm_per_box=Decimal("1.440"),
        kg_per_box=Decimal("28.500"),
        stock_quantity=18,
    )

    assert payload.price == Decimal("29.95")
    assert payload.sqm_per_box == Decimal("1.440")
    assert payload.kg_per_box == Decimal("28.500")
    assert payload.stock_quantity == 18
    assert isinstance(payload.stock_quantity, int)


def test_product_schema_rejects_fractional_stock() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Carrara Porcelain",
            sku="CAR-60120",
            slug="carrara-porcelain",
            category_id=uuid4(),
            stock_quantity=1.5,
        )


def test_product_schema_exposes_requested_catalog_attributes() -> None:
    payload = ProductCreate(
        name="Carrara Porcelain",
        sku="CAR-60120",
        slug="carrara-porcelain",
        description="Polished stone-look tile",
        category_id=uuid4(),
        brand_id=uuid4(),
        product_type="tile",
        material="porcelain",
        finish="polished",
        usage_area="floor",
        color_family="white",
        width_mm=600,
        height_mm=1200,
        thickness_mm=9,
        rectified=True,
        anti_slip_rating="R10",
        water_absorption_percent=Decimal("0.50"),
        pieces_per_box=2,
        sqm_per_box=Decimal("1.440"),
        kg_per_box=Decimal("28.500"),
        country_of_origin="Italy",
        price=Decimal("29.95"),
        stock_quantity=18,
        is_active=True,
        is_featured=True,
    )

    assert payload.model_dump(exclude_unset=True)["width_mm"] == 600
    assert payload.model_dump(exclude_unset=True)["is_featured"] is True


def test_product_database_uses_numeric_price_coverage_and_weight_integer_stock() -> (
    None
):
    columns = Product.__table__.c

    assert str(columns.price.type) == "NUMERIC(12, 2)"
    assert str(columns.sqm_per_box.type) == "NUMERIC(10, 3)"
    assert str(columns.kg_per_box.type) == "NUMERIC(10, 3)"
    assert str(columns.stock_quantity.type) == "INTEGER"


def test_product_sku_and_slug_are_unique(product_session: Session) -> None:
    category = Category(name="Floor", slug="floor")
    product_session.add(category)
    product_session.commit()
    product_session.add(
        Product(name="First", sku="SKU-1", slug="tile-one", category_id=category.id)
    )
    product_session.commit()

    product_session.add(
        Product(name="Second", sku="SKU-1", slug="tile-two", category_id=category.id)
    )
    with pytest.raises(IntegrityError):
        product_session.commit()
    product_session.rollback()

    product_session.add(
        Product(name="Second", sku="SKU-2", slug="tile-one", category_id=category.id)
    )
    with pytest.raises(IntegrityError):
        product_session.commit()


def test_category_and_brand_names_and_slugs_are_unique(
    product_session: Session,
) -> None:
    product_session.add(Category(name="Floor", slug="floor"))
    product_session.commit()
    product_session.add(Category(name="Floor", slug="floor-copy"))
    with pytest.raises(IntegrityError):
        product_session.commit()
    product_session.rollback()

    product_session.add(Brand(name="Acme", slug="acme"))
    product_session.commit()
    product_session.add(Brand(name="Acme", slug="acme-copy"))
    with pytest.raises(IntegrityError):
        product_session.commit()


def test_product_supports_multiple_images(product_session: Session) -> None:
    category = Category(name="Wall", slug="wall")
    product = Product(name="Mosaic", sku="MOS-1", slug="mosaic-one", category=category)
    product.images = [
        ProductImage(storage_key="products/mosaic/front.jpg", is_primary=True),
        ProductImage(storage_key="products/mosaic/detail.jpg", sort_order=1),
    ]
    product_session.add(product)
    product_session.commit()
    product_session.refresh(product)

    assert len(product.images) == 2
    assert product.images[0].product_id == product.id
    assert product.images[1].product_id == product.id


def test_category_brand_and_image_schemas_have_create_update_public_and_list_shapes() -> (
    None
):
    category = CategoryPublic(id=uuid4(), name="Floor", slug="floor")
    brand = BrandPublic(id=uuid4(), name="Acme", slug="acme")
    image = ProductImagePublic(
        id=uuid4(), product_id=uuid4(), storage_key="products/tile/image.jpg"
    )

    assert CategoryCreate(name="Floor", slug="floor").name == "Floor"
    assert CategoryUpdate(description="Updated").description == "Updated"
    assert CategoriesPublic(data=[category], count=1).count == 1
    assert BrandCreate(name="Acme", slug="acme").slug == "acme"
    assert BrandUpdate(is_active=False).is_active is False
    assert BrandsPublic(data=[brand], count=1).data[0].id == brand.id
    assert (
        ProductImageCreate(
            product_id=uuid4(), storage_key="products/tile/image.jpg"
        ).sort_order
        == 0
    )
    assert ProductImageUpdate(alt_text="Tile detail").alt_text == "Tile detail"
    assert ProductImagesPublic(data=[image], count=1).data[0].id == image.id


def test_product_update_and_list_schemas_support_partial_update() -> None:
    product = ProductPublic(
        id=uuid4(),
        name="Carrara",
        sku="CAR-1",
        slug="carrara",
        category_id=uuid4(),
        stock_state="in_stock",
    )

    assert ProductUpdate(price=Decimal("31.25")).model_dump(exclude_unset=True) == {
        "price": Decimal("31.25")
    }
    assert ProductsPublic(data=[product], count=1).data[0].sku == "CAR-1"
