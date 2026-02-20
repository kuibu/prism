from typing import Any

from fastapi.testclient import TestClient

from app.main import app


class _StubOPAClient:
    def __init__(self, reachable: bool) -> None:
        self.reachable = reachable

    async def health(self) -> dict[str, Any]:
        if self.reachable:
            return {"reachable": True, "status_code": 200}
        return {"reachable": False, "error": "down"}

    async def close(self) -> None:
        return None


class _StubImmudbClient:
    def __init__(self, reachable: bool) -> None:
        self.reachable = reachable

    async def health(self) -> dict[str, Any]:
        if self.reachable:
            return {"reachable": True, "host": "immudb", "port": 3322}
        return {"reachable": False, "error": "connection refused"}


def test_liveness_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
        payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "gateway_api"


def test_readiness_endpoint_ready() -> None:
    with TestClient(app) as client:
        client.app.state.opa_client = _StubOPAClient(reachable=True)
        client.app.state.immudb_client = _StubImmudbClient(reachable=True)
        response = client.get("/api/v1/health/ready")
        payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["dependencies"]["opa"]["reachable"] is True
    assert payload["dependencies"]["immudb"]["reachable"] is True


def test_readiness_endpoint_degraded() -> None:
    with TestClient(app) as client:
        client.app.state.opa_client = _StubOPAClient(reachable=False)
        client.app.state.immudb_client = _StubImmudbClient(reachable=True)
        response = client.get("/api/v1/health/ready")
        payload = response.json()

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["opa"]["reachable"] is False
