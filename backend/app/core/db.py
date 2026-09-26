from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.rbac import (
    PERMISSIONS,
    SUPERUSER_ROLE_SLUG,
    SYSTEM_ROLE_DEFINITIONS,
)
from app.models import Permission, Role, User, UserCreate

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def seed_rbac(session: Session) -> None:
    """Idempotently create the permission catalog and the built-in roles."""
    permission_by_code: dict[str, Permission] = {}
    for info in PERMISSIONS:
        permission = session.exec(
            select(Permission).where(Permission.code == info.code)
        ).first()
        if permission is None:
            permission = Permission(code=info.code, description=info.description)
        else:
            permission.description = info.description
        session.add(permission)
        permission_by_code[info.code] = permission
    session.commit()
    for permission in permission_by_code.values():
        session.refresh(permission)

    for slug, definition in SYSTEM_ROLE_DEFINITIONS.items():
        role = session.exec(select(Role).where(Role.slug == slug)).first()
        if role is None:
            role = Role(
                slug=slug,
                name=definition.name,
                description=definition.description,
                is_system=True,
            )
            session.add(role)
            session.commit()
            session.refresh(role)
        else:
            role.name = definition.name
            role.description = definition.description
            role.is_system = True
            session.add(role)
        role.permissions = [
            permission_by_code[code] for code in sorted(definition.permissions)
        ]
        session.add(role)
        session.commit()


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    seed_rbac(session)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        superuser_role = crud.get_role_by_slug(
            session=session, slug=SUPERUSER_ROLE_SLUG
        )
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(
            session=session, user_create=user_in, role=superuser_role
        )
