"""Tests for the FastAPI health endpoint."""

from fastapi.testclient import TestClient

from music_to_mp3.web.main import app


def test_health_endpoint() -> None:
    """Return an affirmative health response."""

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
