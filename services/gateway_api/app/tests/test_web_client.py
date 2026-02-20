from fastapi.testclient import TestClient

from app.main import app


def test_web_root_redirects() -> None:
    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/web/"


def test_web_client_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/web/")

    assert response.status_code == 200
    assert "Prism Web Console" in response.text
