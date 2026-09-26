from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import (
    Brand,
    Category,
    GenerationJob,
    Item,
    Product,
    Role,
    User,
    VisualizationProject,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    with Session(engine) as session:
        init_db(session)
        yield session
        # Delete children before parents to respect FK dependency order.
        session.execute(delete(GenerationJob))
        session.execute(delete(VisualizationProject))
        statement = delete(Item)
        session.execute(statement)
        session.execute(delete(Product))
        session.execute(delete(Brand))
        session.execute(delete(Category))
        statement = delete(User).where(User.email != settings.FIRST_SUPERUSER)
        session.execute(statement)
        session.commit()
        # Remove custom roles created by tests, keep the seeded system roles.
        statement = delete(Role).where(col(Role.is_system).is_(False))
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
