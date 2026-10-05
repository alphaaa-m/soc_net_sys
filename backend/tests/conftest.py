"""Phase 0 test fixtures: isolated SQLite DB, TestClient, auth headers.

Tests NEVER touch the dev database. Each test gets a fresh schema
(create_all before, drop_all after) so tests are independent (PRD Part K).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import create_app
from app.models import User
from app.security import create_access_token, get_password_hash

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db):
    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def user(db) -> User:
    u = User(
        username="ali", email="ali@chirp.local",
        password_hash=get_password_hash("password123"),
        display_name="Ali", bio=None, role="user", is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def admin_user(db) -> User:
    u = User(
        username="admin", email="admin@chirp.local",
        password_hash=get_password_hash("password123"),
        display_name="Admin", bio=None, role="admin", is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture()
def admin_headers(admin_user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(admin_user.id)}"}
