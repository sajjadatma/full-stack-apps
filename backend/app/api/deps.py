from collections.abc import Callable, Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.i18n import set_locale, t
from app.core.rbac import USERS_READ, has_permissions
from app.models import TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except InvalidTokenError, ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("could_not_validate_credentials"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail=t("user_not_found"))
    set_locale(user.locale)
    if not user.is_active:
        raise HTTPException(status_code=400, detail=t("inactive_user"))
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not has_permissions(current_user, USERS_READ):
        raise HTTPException(status_code=403, detail=t("not_enough_privileges"))
    return current_user


def ensure_permissions(
    current_user: User, *codes: str, require_all: bool = True
) -> User:
    """Raise 403 unless the current user holds the requested permission(s)."""
    if not has_permissions(current_user, *codes, require_all=require_all):
        raise HTTPException(status_code=403, detail=t("not_enough_permissions"))
    return current_user


def require_permissions(
    *codes: str, require_all: bool = True
) -> Callable[[User], User]:
    """Build a FastAPI dependency that enforces permission code(s)."""

    def dependency(current_user: CurrentUser) -> User:
        return ensure_permissions(current_user, *codes, require_all=require_all)

    return dependency
