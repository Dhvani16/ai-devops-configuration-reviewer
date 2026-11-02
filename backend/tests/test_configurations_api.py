"""HTTP integration tests for configuration and analysis API endpoints."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.db.session as db_session_module
from app.ai.mock_provider import MockAIProvider
from app.ai.schemas import AIAnalysisResponse
from app.api.deps import get_ai_provider_dep
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app

_DOCKERFILE = "FROM python:3.12\nRUN apt-get install vim\n"
_REGISTER = {"email": "cfg@example.com", "password": "secure-password-123"}


@pytest.fixture
def client() -> TestClient:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def override_session():
        async with factory() as session:
            yield session

    asyncio.run(create_tables())
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_ai_provider_dep] = lambda: MockAIProvider(
        AIAnalysisResponse(findings=[])
    )

    # Patch the module-level session factory so background tasks use the same in-memory DB
    original_factory = db_session_module.AsyncSessionLocal
    db_session_module.AsyncSessionLocal = factory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    db_session_module.AsyncSessionLocal = original_factory
    asyncio.run(engine.dispose())


def _auth_header(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=_REGISTER)
    token = client.post("/api/v1/auth/login", json=_REGISTER).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_configurations(client: TestClient) -> None:
    headers = _auth_header(client)
    payload = {
        "name": "My Dockerfile",
        "configuration_type": "dockerfile",
        "original_content": _DOCKERFILE,
    }

    created = client.post("/api/v1/configurations/", json=payload, headers=headers)
    assert created.status_code == 201
    assert created.json()["name"] == "My Dockerfile"
    assert created.json()["configuration_type"] == "dockerfile"
    assert created.json()["original_content"] == _DOCKERFILE

    listed = client.get("/api/v1/configurations/", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_get_configuration_by_id(client: TestClient) -> None:
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/configurations/",
        json={"name": "X", "configuration_type": "dockerfile", "original_content": _DOCKERFILE},
        headers=headers,
    )
    config_id = created.json()["id"]

    fetched = client.get(f"/api/v1/configurations/{config_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == config_id


def test_delete_configuration(client: TestClient) -> None:
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/configurations/",
        json={"name": "X", "configuration_type": "dockerfile", "original_content": _DOCKERFILE},
        headers=headers,
    )
    config_id = created.json()["id"]

    assert client.delete(f"/api/v1/configurations/{config_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/configurations/{config_id}", headers=headers).status_code == 404


def test_analyze_returns_findings_and_score(client: TestClient) -> None:
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/configurations/",
        json={"name": "X", "configuration_type": "dockerfile", "original_content": _DOCKERFILE},
        headers=headers,
    )
    config_id = created.json()["id"]

    # Analyze now returns 202 immediately with pending status + static findings
    result = client.post(f"/api/v1/configurations/{config_id}/analyze", headers=headers)
    assert result.status_code == 202
    body = result.json()
    assert body["status"] == "pending"
    assert isinstance(body["findings"], list)
    assert len(body["findings"]) > 0  # static findings are present immediately

    # Background task runs synchronously in TestClient — fetch to confirm completion
    analysis_id = body["id"]
    fetched = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers)
    assert fetched.status_code == 200
    completed = fetched.json()
    assert completed["status"] == "completed"
    assert completed["overall_score"] is not None


def test_get_analysis_by_id(client: TestClient) -> None:
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/configurations/",
        json={"name": "X", "configuration_type": "dockerfile", "original_content": _DOCKERFILE},
        headers=headers,
    )
    config_id = created.json()["id"]
    analysis_id = client.post(
        f"/api/v1/configurations/{config_id}/analyze", headers=headers
    ).json()["id"]

    fetched = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == analysis_id


def test_list_analyses(client: TestClient) -> None:
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/configurations/",
        json={"name": "X", "configuration_type": "dockerfile", "original_content": _DOCKERFILE},
        headers=headers,
    )
    config_id = created.json()["id"]
    client.post(f"/api/v1/configurations/{config_id}/analyze", headers=headers)

    listed = client.get("/api/v1/analyses/", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_configuration_not_accessible_by_other_user(client: TestClient) -> None:
    other = {"email": "other@example.com", "password": "secure-password-456"}
    client.post("/api/v1/auth/register", json=other)
    other_token = client.post("/api/v1/auth/login", json=other).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    headers = _auth_header(client)
    created = client.post(
        "/api/v1/configurations/",
        json={"name": "X", "configuration_type": "dockerfile", "original_content": _DOCKERFILE},
        headers=headers,
    )
    config_id = created.json()["id"]

    assert (
        client.get(f"/api/v1/configurations/{config_id}", headers=other_headers).status_code == 404
    )
    assert (
        client.post(
            f"/api/v1/configurations/{config_id}/analyze", headers=other_headers
        ).status_code
        == 404
    )
