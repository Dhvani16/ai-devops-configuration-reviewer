import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app


@pytest.fixture
def client() -> TestClient:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_tables() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with session_factory() as session:
            yield session

    asyncio.run(create_tables())
    app.dependency_overrides[get_db_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_register_login_and_current_user(client: TestClient) -> None:
    registration = client.post(
        "/api/v1/auth/register", json={"email": "student@example.com", "password": "secure-password-123"}
    )
    assert registration.status_code == 201
    assert registration.json()["email"] == "student@example.com"
    assert "hashed_password" not in registration.json()

    login = client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "secure-password-123"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    current_user = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "student@example.com"
    assert client.get("/ready").json() == {"status": "ready"}


def test_auth_rejects_duplicate_credentials_and_missing_token(client: TestClient) -> None:
    payload = {"email": "student@example.com", "password": "secure-password-123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409
    assert client.post("/api/v1/auth/login", json={**payload, "password": "wrong-password-123"}).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
