import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, delete, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    ensure_permissions,
    require_permissions,
)
from app.core.config import settings
from app.core.i18n import t
from app.core.rbac import (
    ROLES_ASSIGN,
    SUPERUSER_ROLE_SLUG,
    USER_ROLE_SLUG,
    USERS_CREATE,
    USERS_DELETE,
    USERS_DELETE_SELF,
    USERS_READ,
    USERS_READ_SELF,
    USERS_UPDATE,
    USERS_UPDATE_SELF,
    is_subset_of_actor,
    is_superuser_role,
    permission_codes,
    user_permission_codes,
)
from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    Message,
    Role,
    RoleAssignment,
    UpdatePassword,
    User,
    UserCreate,
    UserMePublic,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email

router = APIRouter(prefix="/users", tags=["users"])


def _ensure_not_last_superuser(*, session: SessionDep, user: User) -> None:
    if not user.is_active:
        return
    superuser_role = crud.get_role_by_slug(session=session, slug=SUPERUSER_ROLE_SLUG)
    if superuser_role is None or user.role_id != superuser_role.id:
        return
    # Lock the current active administrators before counting. Concurrent role
    # changes then serialize on this row set instead of both removing the last
    # administrator based on the same stale count.
    session.exec(
        select(User)
        .where(User.role_id == superuser_role.id, col(User.is_active))
        .order_by(col(User.id))
        .with_for_update()
    ).all()
    count = crud.count_active_users_with_role(
        session=session, role_id=superuser_role.id
    )
    if count <= 1:
        raise HTTPException(status_code=400, detail=t("last_superuser"))


def _validate_role_assignment(*, current_user: User, role: Role) -> None:
    if is_superuser_role(role) and not is_superuser_role(current_user.role):
        raise HTTPException(status_code=403, detail=t("cannot_assign_superuser_role"))
    if not is_subset_of_actor(current_user, permission_codes(role)):
        raise HTTPException(
            status_code=403, detail=t("cannot_grant_unowned_permissions")
        )


@router.get(
    "/",
    dependencies=[Depends(require_permissions(USERS_READ))],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = (
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    )
    users = session.exec(statement).all()

    users_public = [UserPublic.model_validate(user) for user in users]
    return UsersPublic(data=users_public, count=count)


@router.post(
    "/",
    dependencies=[Depends(require_permissions(USERS_CREATE))],
    response_model=UserPublic,
)
def create_user(
    *, session: SessionDep, current_user: CurrentUser, user_in: UserCreate
) -> Any:
    """
    Create new user.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail=t("user_with_email_exists_period"),
        )

    role: Role | None = None
    default_role = crud.get_role_by_slug(session=session, slug=USER_ROLE_SLUG)
    if user_in.role_id is not None:
        requested_role = crud.get_role_by_id(session=session, role_id=user_in.role_id)
        if not requested_role:
            raise HTTPException(status_code=404, detail=t("role_not_found"))
        # Selecting the default role needs no extra privilege; assigning any
        # other role requires the role-assignment permission.
        if default_role is None or requested_role.id != default_role.id:
            ensure_permissions(current_user, ROLES_ASSIGN)
            _validate_role_assignment(current_user=current_user, role=requested_role)
        role = requested_role
    elif user_in.is_superuser:
        superuser_role = crud.get_role_by_slug(
            session=session, slug=SUPERUSER_ROLE_SLUG
        )
        if superuser_role is None:
            raise HTTPException(status_code=404, detail=t("role_not_found"))
        ensure_permissions(current_user, ROLES_ASSIGN)
        _validate_role_assignment(current_user=current_user, role=superuser_role)
        role = superuser_role
    else:
        role = crud.get_role_by_slug(session=session, slug=USER_ROLE_SLUG)

    user = crud.create_user(session=session, user_create=user_in, role=role)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email,
            username=user_in.email,
            password=user_in.password,
            locale=user_in.locale,
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """
    ensure_permissions(current_user, USERS_UPDATE_SELF)

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail=t("user_with_email_already_exists")
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    ensure_permissions(current_user, USERS_UPDATE_SELF)
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail=t("incorrect_password"))
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail=t("new_password_same_as_current"))
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message=t("password_updated_successfully"))


@router.get("/me", response_model=UserMePublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user, including effective permissions.
    """
    return UserMePublic.model_validate(
        current_user,
        update={"permissions": sorted(user_permission_codes(current_user))},
    )


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    ensure_permissions(current_user, USERS_DELETE_SELF)
    if is_superuser_role(current_user.role):
        raise HTTPException(status_code=403, detail=t("superuser_cannot_delete_self"))
    session.delete(current_user)
    session.commit()
    return Message(message=t("user_deleted_successfully"))


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail=t("user_with_email_exists"),
        )
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    return user


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    if user_id == current_user.id:
        ensure_permissions(current_user, USERS_READ_SELF)
        return current_user
    ensure_permissions(current_user, USERS_READ)
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=t("user_not_found"))
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(require_permissions(USERS_UPDATE))],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail=t("user_with_id_not_exist"),
        )
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail=t("user_with_email_already_exists")
            )

    # Legacy compatibility: translate the boolean flag into a role change.
    role_change: Role | None = None
    if user_in.is_superuser is not None:
        if (
            db_user.id == current_user.id
            and user_in.is_superuser != db_user.is_superuser
        ):
            raise HTTPException(status_code=400, detail=t("cannot_change_own_role"))
        if user_in.is_superuser and not db_user.is_superuser:
            superuser_role = crud.get_role_by_slug(
                session=session, slug=SUPERUSER_ROLE_SLUG
            )
            if superuser_role is None:
                raise HTTPException(status_code=404, detail=t("role_not_found"))
            ensure_permissions(current_user, ROLES_ASSIGN)
            _validate_role_assignment(current_user=current_user, role=superuser_role)
            role_change = superuser_role
        elif not user_in.is_superuser and db_user.is_superuser:
            ensure_permissions(current_user, ROLES_ASSIGN)
            _ensure_not_last_superuser(session=session, user=db_user)
            role_change = crud.get_role_by_slug(session=session, slug=USER_ROLE_SLUG)
            if role_change is None:
                raise HTTPException(status_code=404, detail=t("role_not_found"))

    update_data = user_in.model_dump(exclude_unset=True)
    update_data.pop("is_superuser", None)
    if user_in.is_active is False and db_user.is_active and db_user.is_superuser:
        _ensure_not_last_superuser(session=session, user=db_user)
    if user_in.is_active is True and not db_user.is_active and db_user.is_superuser:
        ensure_permissions(current_user, ROLES_ASSIGN)
    db_user = crud.update_user(
        session=session, db_user=db_user, user_in=UserUpdate(**update_data)
    )
    if role_change is not None:
        db_user = crud.set_user_role(session=session, db_user=db_user, role=role_change)
    return db_user


@router.put(
    "/{user_id}/role",
    dependencies=[Depends(require_permissions(ROLES_ASSIGN))],
    response_model=UserPublic,
)
def assign_user_role(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    user_id: uuid.UUID,
    body: RoleAssignment,
) -> Any:
    """
    Replace the single role assigned to a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=t("user_not_found"))
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail=t("cannot_change_own_role"))
    role = crud.get_role_by_id(session=session, role_id=body.role_id)
    if not role:
        raise HTTPException(status_code=404, detail=t("role_not_found"))

    _validate_role_assignment(current_user=current_user, role=role)
    if user.is_superuser and not is_superuser_role(role):
        _ensure_not_last_superuser(session=session, user=user)
    return crud.set_user_role(session=session, db_user=user, role=role)


@router.delete(
    "/{user_id}",
    dependencies=[Depends(require_permissions(USERS_DELETE))],
)
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=t("user_not_found"))
    if user == current_user:
        raise HTTPException(status_code=403, detail=t("superuser_cannot_delete_self"))
    _ensure_not_last_superuser(session=session, user=user)
    statement = delete(Item).where(col(Item.owner_id) == user_id)
    session.exec(statement)
    session.delete(user)
    session.commit()
    return Message(message=t("user_deleted_successfully"))
