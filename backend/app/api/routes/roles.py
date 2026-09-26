import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep, require_permissions
from app.core.i18n import t
from app.core.rbac import (
    PERMISSION_CODES,
    PERMISSIONS,
    ROLES_CREATE,
    ROLES_DELETE,
    ROLES_READ,
    ROLES_UPDATE,
    is_subset_of_actor,
)
from app.models import (
    Message,
    Permission,
    PermissionPublic,
    Role,
    RoleCreate,
    RolePublic,
    RolesPublic,
    RoleUpdate,
)

router = APIRouter(prefix="/roles", tags=["roles"])

_PERMISSION_ORDER: dict[str, int] = {
    info.code: index for index, info in enumerate(PERMISSIONS)
}


def _role_public(role: Role) -> RolePublic:
    permissions = sorted(
        (
            PermissionPublic.model_validate(permission)
            for permission in (role.permissions or [])
        ),
        key=lambda permission: _PERMISSION_ORDER.get(
            permission.code, len(_PERMISSION_ORDER)
        ),
    )
    return RolePublic(
        id=role.id,
        name=role.name,
        description=role.description,
        slug=role.slug,
        is_system=role.is_system,
        permissions=permissions,
        created_at=role.created_at,
    )


def _validate_permission_codes(codes: list[str]) -> None:
    if len(codes) != len(set(codes)):
        raise HTTPException(status_code=400, detail=t("duplicate_permissions"))
    unknown = sorted(code for code in codes if code not in PERMISSION_CODES)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=t("unknown_permissions", permissions=", ".join(unknown)),
        )


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "role"


def _get_role_or_404(*, session: SessionDep, role_id: uuid.UUID) -> Role:
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail=t("role_not_found"))
    return role


@router.get(
    "/",
    dependencies=[Depends(require_permissions(ROLES_READ))],
    response_model=RolesPublic,
)
def read_roles(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve roles.
    """
    count_statement = select(func.count()).select_from(Role)
    count = session.exec(count_statement).one()
    statement = (
        select(Role)
        .order_by(col(Role.is_system).desc(), col(Role.name))
        .offset(skip)
        .limit(limit)
    )
    roles = session.exec(statement).all()
    return RolesPublic(data=[_role_public(role) for role in roles], count=count)


@router.get(
    "/permissions",
    dependencies=[Depends(require_permissions(ROLES_READ))],
    response_model=list[PermissionPublic],
)
def read_permissions(session: SessionDep) -> Any:
    """
    List every permission code known to the application.
    """
    permissions = session.exec(select(Permission)).all()
    return [
        PermissionPublic.model_validate(permission)
        for permission in sorted(
            permissions,
            key=lambda permission: _PERMISSION_ORDER.get(
                permission.code, len(_PERMISSION_ORDER)
            ),
        )
    ]


@router.get(
    "/{role_id}",
    dependencies=[Depends(require_permissions(ROLES_READ))],
    response_model=RolePublic,
)
def read_role(role_id: uuid.UUID, session: SessionDep) -> Any:
    """
    Get a role by ID.
    """
    return _role_public(_get_role_or_404(session=session, role_id=role_id))


@router.post(
    "/",
    dependencies=[Depends(require_permissions(ROLES_CREATE))],
    response_model=RolePublic,
    status_code=201,
)
def create_role(
    *, session: SessionDep, current_user: CurrentUser, role_in: RoleCreate
) -> Any:
    """
    Create a custom role.
    """
    _validate_permission_codes(role_in.permissions)
    if not is_subset_of_actor(current_user, role_in.permissions):
        raise HTTPException(
            status_code=403, detail=t("cannot_grant_unowned_permissions")
        )

    existing_name = session.exec(select(Role).where(Role.name == role_in.name)).first()
    if existing_name:
        raise HTTPException(status_code=400, detail=t("role_name_exists"))

    slug = _slugify(role_in.slug or role_in.name)
    existing_slug = crud.get_role_by_slug(session=session, slug=slug)
    if existing_slug:
        raise HTTPException(status_code=400, detail=t("role_slug_exists"))

    role = Role(
        name=role_in.name,
        description=role_in.description,
        slug=slug,
        is_system=False,
    )
    session.add(role)
    session.commit()
    session.refresh(role)

    permissions = crud.get_permissions_by_codes(
        session=session, codes=role_in.permissions
    )
    role = crud.set_role_permissions(
        session=session, role=role, permissions=permissions
    )
    return _role_public(role)


@router.patch(
    "/{role_id}",
    dependencies=[Depends(require_permissions(ROLES_UPDATE))],
    response_model=RolePublic,
)
def update_role(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    role_id: uuid.UUID,
    role_in: RoleUpdate,
) -> Any:
    """
    Update a custom role.
    """
    role = _get_role_or_404(session=session, role_id=role_id)
    if role.is_system:
        raise HTTPException(status_code=400, detail=t("system_role_immutable"))

    if role_in.name and role_in.name != role.name:
        existing_name = session.exec(
            select(Role).where(Role.name == role_in.name)
        ).first()
        if existing_name:
            raise HTTPException(status_code=400, detail=t("role_name_exists"))
        role.name = role_in.name

    if role_in.description is not None:
        role.description = role_in.description

    if role_in.permissions is not None:
        _validate_permission_codes(role_in.permissions)
        if not is_subset_of_actor(current_user, role_in.permissions):
            raise HTTPException(
                status_code=403, detail=t("cannot_grant_unowned_permissions")
            )

    session.add(role)
    session.commit()
    session.refresh(role)

    if role_in.permissions is not None:
        permissions = crud.get_permissions_by_codes(
            session=session, codes=role_in.permissions
        )
        role = crud.set_role_permissions(
            session=session, role=role, permissions=permissions
        )
    return _role_public(role)


@router.delete(
    "/{role_id}",
    dependencies=[Depends(require_permissions(ROLES_DELETE))],
)
def delete_role(role_id: uuid.UUID, session: SessionDep) -> Message:
    """
    Delete a custom role.
    """
    role = _get_role_or_404(session=session, role_id=role_id)
    if role.is_system:
        raise HTTPException(status_code=400, detail=t("system_role_immutable"))
    if crud.count_role_users(session=session, role_id=role.id):
        raise HTTPException(status_code=400, detail=t("role_in_use"))
    session.delete(role)
    session.commit()
    return Message(message=t("role_deleted_successfully"))
