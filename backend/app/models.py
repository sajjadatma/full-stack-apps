import uuid
from datetime import UTC, datetime
from typing import Annotated

from pydantic import EmailStr, StringConstraints
from sqlalchemy import DateTime
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
