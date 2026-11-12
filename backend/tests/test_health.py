from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["agent_provider"] == "mock"
    assert set(body) == {"status", "app", "version", "environment", "agent_provider"}


def test_cors_allows_local_frontend() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_unknown_origin() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
