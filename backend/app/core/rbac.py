"""Role based access control catalog and policy helpers.

The permission catalog and the built-in system roles are defined here in code.
Administrators can create custom roles and choose which of these permissions
they grant, but the set of permission codes itself is owned by the application.
"""

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from typing import Final

from app.models import Item, Permission, Role, User

# ---------------------------------------------------------------------------
# Permission catalog
# ---------------------------------------------------------------------------

# Users
USERS_READ = "users.read"
USERS_CREATE = "users.create"
USERS_UPDATE = "users.update"
USERS_DELETE = "users.delete"
USERS_READ_SELF = "users.read_self"
USERS_UPDATE_SELF = "users.update_self"
USERS_DELETE_SELF = "users.delete_self"

# Items
ITEMS_READ_OWN = "items.read_own"
ITEMS_READ_ANY = "items.read_any"
ITEMS_CREATE = "items.create"
ITEMS_UPDATE_OWN = "items.update_own"
ITEMS_UPDATE_ANY = "items.update_any"
ITEMS_DELETE_OWN = "items.delete_own"
ITEMS_DELETE_ANY = "items.delete_any"

# Product catalog reference data and products
PRODUCTS_READ = "products.read"
PRODUCTS_READ_ANY = "products.read_any"
PRODUCTS_CREATE = "products.create"
PRODUCTS_UPDATE = "products.update"
PRODUCTS_DELETE = "products.delete"
PRODUCTS_MANAGE_IMAGES = "products.manage_images"

# Generations
GENERATIONS_CREATE = "generations.create"
GENERATIONS_READ_OWN = "generations.read_own"
GENERATIONS_READ_ANY = "generations.read_any"

# Roles
ROLES_READ = "roles.read"
ROLES_CREATE = "roles.create"
ROLES_UPDATE = "roles.update"
ROLES_DELETE = "roles.delete"
ROLES_ASSIGN = "roles.assign"

# Utilities
UTILS_SEND_TEST_EMAIL = "utils.send_test_email"
UTILS_READ_PASSWORD_RECOVERY_HTML = "utils.read_password_recovery_html"


@dataclass(frozen=True)
class PermissionInfo:
    """Metadata for a single permission code."""

    code: str
    description: str


# Keep this tuple ordered: it is the canonical, stable permission catalog.
PERMISSIONS: Final[tuple[PermissionInfo, ...]] = (
    PermissionInfo(USERS_READ, "Read any user account"),
    PermissionInfo(USERS_CREATE, "Create user accounts"),
    PermissionInfo(USERS_UPDATE, "Update any user account"),
    PermissionInfo(USERS_DELETE, "Delete any user account"),
    PermissionInfo(USERS_READ_SELF, "Read own user account"),
    PermissionInfo(USERS_UPDATE_SELF, "Update own user account"),
    PermissionInfo(USERS_DELETE_SELF, "Delete own user account"),
    PermissionInfo(ITEMS_READ_OWN, "Read own items"),
    PermissionInfo(ITEMS_READ_ANY, "Read all items"),
    PermissionInfo(ITEMS_CREATE, "Create items"),
    PermissionInfo(ITEMS_UPDATE_OWN, "Update own items"),
    PermissionInfo(ITEMS_UPDATE_ANY, "Update all items"),
    PermissionInfo(ITEMS_DELETE_OWN, "Delete own items"),
    PermissionInfo(ITEMS_DELETE_ANY, "Delete all items"),
    PermissionInfo(PRODUCTS_READ, "Read the active product catalog"),
    PermissionInfo(PRODUCTS_READ_ANY, "Read all product catalog data"),
    PermissionInfo(PRODUCTS_CREATE, "Create product catalog data"),
    PermissionInfo(PRODUCTS_UPDATE, "Update product catalog data"),
    PermissionInfo(PRODUCTS_DELETE, "Delete product catalog data"),
    PermissionInfo(PRODUCTS_MANAGE_IMAGES, "Manage product images"),
    PermissionInfo(GENERATIONS_CREATE, "Create image generations"),
    PermissionInfo(GENERATIONS_READ_OWN, "Read own image generations"),
    PermissionInfo(GENERATIONS_READ_ANY, "Read any image generation"),
    PermissionInfo(ROLES_READ, "View roles and permissions"),
    PermissionInfo(ROLES_CREATE, "Create roles"),
    PermissionInfo(ROLES_UPDATE, "Update roles"),
    PermissionInfo(ROLES_DELETE, "Delete roles"),
    PermissionInfo(ROLES_ASSIGN, "Assign roles to users"),
    PermissionInfo(UTILS_SEND_TEST_EMAIL, "Send test emails"),
    PermissionInfo(
        UTILS_READ_PASSWORD_RECOVERY_HTML,
        "Preview password recovery emails",
    ),
)

PERMISSION_CODES: Final[frozenset[str]] = frozenset(p.code for p in PERMISSIONS)


# ---------------------------------------------------------------------------
# Built-in roles
# ---------------------------------------------------------------------------

SUPERUSER_ROLE_SLUG: Final[str] = "superuser"
USER_ROLE_SLUG: Final[str] = "user"

SYSTEM_ROLE_SLUGS: Final[frozenset[str]] = frozenset(
    {SUPERUSER_ROLE_SLUG, USER_ROLE_SLUG}
)

DEFAULT_USER_PERMISSIONS: Final[frozenset[str]] = frozenset(
    {
        USERS_READ_SELF,
        USERS_UPDATE_SELF,
        USERS_DELETE_SELF,
        ITEMS_READ_OWN,
        ITEMS_CREATE,
        ITEMS_UPDATE_OWN,
        ITEMS_DELETE_OWN,
        PRODUCTS_READ,
        GENERATIONS_CREATE,
        GENERATIONS_READ_OWN,
    }
)


@dataclass(frozen=True)
class SystemRoleInfo:
    """Definition of a built-in role that cannot be modified by administrators."""

    name: str
    description: str
    permissions: frozenset[str]


SYSTEM_ROLE_DEFINITIONS: Final[dict[str, SystemRoleInfo]] = {
    USER_ROLE_SLUG: SystemRoleInfo(
        name="User",
        description="Default role for regular users",
        permissions=DEFAULT_USER_PERMISSIONS,
    ),
    SUPERUSER_ROLE_SLUG: SystemRoleInfo(
        name="Superuser",
        description="Full administrative access",
        permissions=PERMISSION_CODES,
    ),
}


# ---------------------------------------------------------------------------
# Policy helpers
# ---------------------------------------------------------------------------


def permission_codes(role: Role | None) -> set[str]:
    """Return the permission codes granted by a role."""
    if role is None:
        return set()
    permissions: Iterable[Permission] = role.permissions or []
    return {permission.code for permission in permissions}


def user_permission_codes(user: User) -> set[str]:
    """Return the effective permission codes granted by the user's one role."""
    return permission_codes(user.role)


def has_permissions(user: User, *codes: str, require_all: bool = True) -> bool:
    """Check whether ``user`` holds the requested permission code(s)."""
    if not codes:
        return True
    granted = permission_codes(user.role)
    if require_all:
        return all(code in granted for code in codes)
    return any(code in granted for code in codes)


def is_superuser_role(role: Role | None) -> bool:
    return role is not None and role.slug == SUPERUSER_ROLE_SLUG


def is_subset_of_actor(actor: User, codes: Collection[str]) -> bool:
    """Return whether the actor is allowed to grant every code in ``codes``."""
    return set(codes).issubset(permission_codes(actor.role))


# --- Item ownership policies ------------------------------------------------


def can_read_items_any(user: User) -> bool:
    return has_permissions(user, ITEMS_READ_ANY)


def can_read_item(user: User, item: Item) -> bool:
    if has_permissions(user, ITEMS_READ_ANY):
        return True
    return has_permissions(user, ITEMS_READ_OWN) and item.owner_id == user.id


def can_create_item(user: User) -> bool:
    return has_permissions(user, ITEMS_CREATE)


def can_update_item(user: User, item: Item) -> bool:
    if has_permissions(user, ITEMS_UPDATE_ANY):
        return True
    return has_permissions(user, ITEMS_UPDATE_OWN) and item.owner_id == user.id


def can_delete_item(user: User, item: Item) -> bool:
    if has_permissions(user, ITEMS_DELETE_ANY):
        return True
    return has_permissions(user, ITEMS_DELETE_OWN) and item.owner_id == user.id
