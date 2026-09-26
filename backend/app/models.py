import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import EmailStr, StringConstraints
from sqlalchemy import DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


Locale = Annotated[str, StringConstraints(max_length=10, pattern="^(en|fa)$")]


# ---------------------------------------------------------------------------
# Roles and permissions (RBAC)
# ---------------------------------------------------------------------------


# Link table between roles and permissions.
class RolePermissionLink(SQLModel, table=True):
    role_id: uuid.UUID = Field(
        foreign_key="role.id", primary_key=True, ondelete="CASCADE"
    )
    permission_id: uuid.UUID = Field(
        foreign_key="permission.id", primary_key=True, ondelete="CASCADE"
    )


# Database model, database table inferred from class name
class Permission(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    roles: list[Role] = Relationship(
        back_populates="permissions", link_model=RolePermissionLink
    )


# Shared properties
class RoleBase(SQLModel):
    name: str = Field(min_length=1, max_length=100, index=True, unique=True)
    description: str | None = Field(default=None, max_length=255)


# Database model, database table inferred from class name
class Role(RoleBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(unique=True, index=True, max_length=100)
    is_system: bool = False
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    permissions: list[Permission] = Relationship(
        back_populates="roles", link_model=RolePermissionLink
    )
    users: list[User] = Relationship(back_populates="role")


class PermissionPublic(SQLModel):
    id: uuid.UUID
    code: str
    description: str | None = None


class RoleSummary(SQLModel):
    id: uuid.UUID
    slug: str
    name: str
    is_system: bool


class RolePublic(RoleBase):
    id: uuid.UUID
    slug: str
    is_system: bool
    permissions: list[PermissionPublic] = Field(default_factory=list)
    created_at: datetime | None = None


class RolesPublic(SQLModel):
    data: list[RolePublic]
    count: int


# Properties to receive via API on role creation.
class RoleCreate(RoleBase):
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    permissions: list[str] = Field(default_factory=list)


# Properties to receive via API on role update, all are optional.
class RoleUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] | None = None


# Payload to assign a single role to a user.
class RoleAssignment(SQLModel):
    role_id: uuid.UUID


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    locale: Locale = "en"


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role_id: uuid.UUID | None = None


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    locale: Locale = "en"


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    locale: Locale | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    locale: Locale | None = None


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    role_id: uuid.UUID = Field(
        foreign_key="role.id", nullable=False, index=True, ondelete="RESTRICT"
    )
    role: Role | None = Relationship(back_populates="users")
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None
    role: RoleSummary | None = None


# Properties to return for the authenticated user, including permissions.
class UserMePublic(UserPublic):
    permissions: list[str] = Field(default_factory=list)


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# ---------------------------------------------------------------------------
# TileVision product catalog
# ---------------------------------------------------------------------------


class CategoryBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class Category(CategoryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(min_length=1, max_length=100, unique=True, index=True)
    slug: str = Field(min_length=1, max_length=120, unique=True, index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    products: list[Product] = Relationship(back_populates="category")


class CategoryPublic(CategoryBase):
    id: uuid.UUID
    created_at: datetime | None = None


class CategoriesPublic(SQLModel):
    data: list[CategoryPublic]
    count: int


class BrandBase(SQLModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=140)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class BrandCreate(BrandBase):
    pass


class BrandUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class Brand(BrandBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(min_length=1, max_length=120, unique=True, index=True)
    slug: str = Field(min_length=1, max_length=140, unique=True, index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    products: list[Product] = Relationship(back_populates="brand")


class BrandPublic(BrandBase):
    id: uuid.UUID
    created_at: datetime | None = None


class BrandsPublic(SQLModel):
    data: list[BrandPublic]
    count: int


class ProductBase(SQLModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    category_id: uuid.UUID
    brand_id: uuid.UUID | None = None
    product_type: str | None = Field(default=None, max_length=64)
    material: str | None = Field(default=None, max_length=64)
    finish: str | None = Field(default=None, max_length=64)
    usage_area: str | None = Field(default=None, max_length=64)
    color_family: str | None = Field(default=None, max_length=64)
    width_mm: int | None = Field(default=None, gt=0)
    height_mm: int | None = Field(default=None, gt=0)
    thickness_mm: int | None = Field(default=None, gt=0)
    rectified: bool = False
    anti_slip_rating: str | None = Field(default=None, max_length=32)
    water_absorption_percent: Decimal | None = Field(
        default=None, sa_type=Numeric(5, 2), ge=0, le=100
    )
    pieces_per_box: int | None = Field(default=None, gt=0)
    sqm_per_box: Decimal | None = Field(default=None, sa_type=Numeric(10, 3), gt=0)
    kg_per_box: Decimal | None = Field(default=None, sa_type=Numeric(10, 3), gt=0)
    country_of_origin: str | None = Field(default=None, max_length=100)
    price: Decimal | None = Field(default=None, sa_type=Numeric(12, 2), ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool = True
    is_featured: bool = False


class ProductCreate(ProductBase):
    pass


class ProductUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    product_type: str | None = Field(default=None, max_length=64)
    material: str | None = Field(default=None, max_length=64)
    finish: str | None = Field(default=None, max_length=64)
    usage_area: str | None = Field(default=None, max_length=64)
    color_family: str | None = Field(default=None, max_length=64)
    width_mm: int | None = Field(default=None, gt=0)
    height_mm: int | None = Field(default=None, gt=0)
    thickness_mm: int | None = Field(default=None, gt=0)
    rectified: bool | None = None
    anti_slip_rating: str | None = Field(default=None, max_length=32)
    water_absorption_percent: Decimal | None = Field(
        default=None, sa_type=Numeric(5, 2), ge=0, le=100
    )
    pieces_per_box: int | None = Field(default=None, gt=0)
    sqm_per_box: Decimal | None = Field(default=None, sa_type=Numeric(10, 3), gt=0)
    kg_per_box: Decimal | None = Field(default=None, sa_type=Numeric(10, 3), gt=0)
    country_of_origin: str | None = Field(default=None, max_length=100)
    price: Decimal | None = Field(default=None, sa_type=Numeric(12, 2), ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_featured: bool | None = None


class Product(ProductBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    sku: str = Field(min_length=1, max_length=64, unique=True, index=True)
    slug: str = Field(min_length=1, max_length=255, unique=True, index=True)
    category_id: uuid.UUID = Field(
        foreign_key="category.id", nullable=False, index=True, ondelete="RESTRICT"
    )
    brand_id: uuid.UUID | None = Field(
        default=None, foreign_key="brand.id", index=True, ondelete="RESTRICT"
    )
    category: Category | None = Relationship(back_populates="products")
    brand: Brand | None = Relationship(back_populates="products")
    images: list[ProductImage] = Relationship(
        back_populates="product", cascade_delete=True
    )


class ProductPublic(ProductBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    stock_state: str
    images: list[ProductImagePublic] = Field(default_factory=list)


class ProductsPublic(SQLModel):
    data: list[ProductPublic]
    count: int


class ProductImageBase(SQLModel):
    product_id: uuid.UUID
    storage_key: str = Field(min_length=1, max_length=1024)
    content_type: str = Field(min_length=1, max_length=64)
    url: str | None = Field(default=None, max_length=2048)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False


class ProductImageCreate(ProductImageBase):
    pass


class ProductImageUpdate(SQLModel):
    product_id: uuid.UUID | None = None
    storage_key: str | None = Field(default=None, min_length=1, max_length=1024)
    url: str | None = Field(default=None, max_length=2048)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int | None = Field(default=None, ge=0)
    is_primary: bool | None = None


class ProductImage(ProductImageBase, table=True):
    __tablename__ = "product_image"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    product_id: uuid.UUID = Field(
        foreign_key="product.id", nullable=False, index=True, ondelete="CASCADE"
    )
    product: Product | None = Relationship(back_populates="images")


class ProductImagePublic(ProductImageBase):
    id: uuid.UUID
    created_at: datetime | None = None


class ProductImagesPublic(SQLModel):
    data: list[ProductImagePublic]
    count: int


class ProductImageOrder(SQLModel):
    image_ids: list[uuid.UUID]


ProductPublic.model_rebuild()


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
