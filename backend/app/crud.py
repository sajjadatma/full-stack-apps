import uuid
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.rbac import SUPERUSER_ROLE_SLUG, USER_ROLE_SLUG
from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    ItemCreate,
    Permission,
    Role,
    User,
    UserCreate,
    UserUpdate,
)


def get_role_by_slug(*, session: Session, slug: str) -> Role | None:
    return session.exec(select(Role).where(Role.slug == slug)).first()


def get_role_by_id(*, session: Session, role_id: uuid.UUID) -> Role | None:
    return session.get(Role, role_id)


def get_permission_by_code(*, session: Session, code: str) -> Permission | None:
    return session.exec(select(Permission).where(Permission.code == code)).first()


def get_permissions_by_codes(*, session: Session, codes: list[str]) -> list[Permission]:
    if not codes:
        return []
    statement = select(Permission).where(col(Permission.code).in_(codes))
    return list(session.exec(statement).all())


def count_role_users(*, session: Session, role_id: uuid.UUID) -> int:
    statement = select(User).where(User.role_id == role_id)
    return len(session.exec(statement).all())


def create_user(
    *, session: Session, user_create: UserCreate, role: Role | None = None
) -> User:
    resolved_role = role
    if resolved_role is None:
        if user_create.role_id is not None:
            resolved_role = get_role_by_id(session=session, role_id=user_create.role_id)
        elif user_create.is_superuser:
            resolved_role = get_role_by_slug(session=session, slug=SUPERUSER_ROLE_SLUG)
        else:
            resolved_role = get_role_by_slug(session=session, slug=USER_ROLE_SLUG)
    if resolved_role is None:
        raise ValueError("No role available to assign to the new user")

    db_obj = User.model_validate(
        user_create,
        update={
            "hashed_password": get_password_hash(user_create.password),
            "role_id": resolved_role.id,
            "is_superuser": resolved_role.slug == SUPERUSER_ROLE_SLUG,
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found
# This is an Argon2 hash of a random password, used to ensure constant-time comparison
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when user doesn't exist
        # This ensures the response time is similar whether or not the email exists
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def set_user_role(*, session: Session, db_user: User, role: Role) -> User:
    """Assign exactly one role to a user and mirror the legacy superuser flag."""
    db_user.role_id = role.id
    db_user.is_superuser = role.slug == SUPERUSER_ROLE_SLUG
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def set_role_permissions(
    *, session: Session, role: Role, permissions: list[Permission]
) -> Role:
    role.permissions = permissions
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


def count_active_users_with_role(*, session: Session, role_id: uuid.UUID) -> int:
    statement = (
        select(func.count())
        .select_from(User)
        .where(User.role_id == role_id, col(User.is_active))
    )
    return int(session.exec(statement).one())
