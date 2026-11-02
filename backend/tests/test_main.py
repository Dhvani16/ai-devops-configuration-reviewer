from fastapi.testclient import TestClient

from app.main import app


def test_service_information_is_available() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "ai-devops-configuration-reviewer",
        "docs": "/docs",
    }
