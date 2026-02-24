from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.audit.schemas import AuditEventCreate
from app.main import app
from app.matrix.client import MatrixClientError


class _StubAuditClient:
    def __init__(self) -> None:
        self.events: list[AuditEventCreate] = []

    async def health(self) -> dict[str, object]:
        return {"reachable": True}

    async def append_audit_event(self, request: AuditEventCreate) -> dict[str, object]:
        self.events.append(request)
        return {"event_id": f"evt_{len(self.events)}"}


class _StubOPAClient:
    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    async def health(self) -> dict[str, object]:
        return {"reachable": True}

    async def get_document(self, path: str) -> dict[str, Any]:
        return self.docs.get(path, {})

    async def put_document(self, path: str, payload: dict[str, Any]) -> None:
        self.docs[path] = dict(payload)

    async def delete_document(self, path: str) -> None:
        self.docs.pop(path, None)

    async def evaluate(self, policy_path: str, payload: dict[str, object]) -> dict[str, object]:
        _ = policy_path, payload
        return {"allow": True, "reason": "ok"}

    async def close(self) -> None:
        return None


class _StubMatrixClient:
    def __init__(self) -> None:
        self._token_to_user = {"token_alice": "@alice:localhost"}
        self.sent_messages: list[dict[str, str]] = []
        self.now_ms = int(datetime.now(UTC).timestamp() * 1000)

    async def whoami(self, *, access_token: str) -> dict[str, object]:
        user_id = self._token_to_user.get(access_token)
        if user_id is None:
            raise MatrixClientError("invalid_token")
        return {"user_id": user_id}

    async def send_text_message(
        self,
        *,
        access_token: str,
        room_id: str,
        body: str,
        txn_id: str | None = None,
    ) -> dict[str, object]:
        _ = txn_id
        user_id = self._token_to_user.get(access_token)
        if user_id is None:
            raise MatrixClientError("invalid_token")
        self.sent_messages.append(
            {
                "user_id": user_id,
                "room_id": room_id,
                "body": body,
            }
        )
        return {"event_id": f"$bridge_{len(self.sent_messages)}:localhost"}

    async def read_room_messages(
        self,
        *,
        access_token: str,
        room_id: str,
        limit: int,
    ) -> list[str]:
        user_id = self._token_to_user.get(access_token)
        if user_id is None:
            raise MatrixClientError("invalid_token")
        _ = room_id
        rows = [
            "Standup moved to 10:30.",
            "Please confirm release checklist.",
            "Ticket #123 is blocked by API migration.",
        ]
        return rows[-max(1, limit) :]


def _auth_headers(token: str = "token_alice") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _install_stubs(client: TestClient) -> tuple[_StubAuditClient, _StubMatrixClient]:
    audit_stub = _StubAuditClient()
    opa_stub = _StubOPAClient()
    matrix_stub = _StubMatrixClient()
    client.app.state.immudb_client = audit_stub
    client.app.state.opa_client = opa_stub
    client.app.state.matrix_client = matrix_stub
    return audit_stub, matrix_stub


def test_bridge_connector_and_link_crud_flow() -> None:
    with TestClient(app) as client:
        audit_stub, _ = _install_stubs(client)

        created_connector = client.post(
            "/api/v1/bridges/connectors",
            headers=_auth_headers(),
            json={
                "platform": "telegram",
                "display_name": "Telegram Team Bridge",
                "direction": "bidirectional",
                "enabled": True,
                "secret_refs": ["telegram_bot_token"],
            },
        )
        assert created_connector.status_code == 201
        connector_payload = created_connector.json()
        connector_id = connector_payload["connector_id"]
        assert connector_payload["platform"] == "telegram"

        listed_connectors = client.get("/api/v1/bridges/connectors", headers=_auth_headers())
        assert listed_connectors.status_code == 200
        assert any(
            row["connector_id"] == connector_id for row in listed_connectors.json()["connectors"]
        )

        updated_connector = client.patch(
            f"/api/v1/bridges/connectors/{connector_id}",
            headers=_auth_headers(),
            json={"enabled": False},
        )
        assert updated_connector.status_code == 200
        assert updated_connector.json()["enabled"] is False

        created_link = client.post(
            "/api/v1/bridges/links",
            headers=_auth_headers(),
            json={
                "connector_id": connector_id,
                "room_id": "!room:localhost",
                "external_room_id": "tg_group_1001",
                "external_room_name": "Release Bridge Group",
                "relay_prefix": "[TelegramBridge]",
            },
        )
        assert created_link.status_code == 201
        link_payload = created_link.json()
        link_id = link_payload["link_id"]

        listed_links = client.get(
            f"/api/v1/bridges/links?connector_id={connector_id}",
            headers=_auth_headers(),
        )
        assert listed_links.status_code == 200
        assert any(row["link_id"] == link_id for row in listed_links.json()["links"])

        deleted_link = client.delete(f"/api/v1/bridges/links/{link_id}", headers=_auth_headers())
        assert deleted_link.status_code == 204

        deleted_connector = client.delete(
            f"/api/v1/bridges/connectors/{connector_id}",
            headers=_auth_headers(),
        )
        assert deleted_connector.status_code == 204

        action_types = [item.action_type for item in audit_stub.events]
        assert "bridge_connector_upsert" in action_types
        assert "bridge_link_upsert" in action_types
        assert "bridge_link_delete" in action_types
        assert "bridge_connector_delete" in action_types


def test_bridge_inbound_relay_sends_matrix_message() -> None:
    with TestClient(app) as client:
        audit_stub, matrix_stub = _install_stubs(client)

        connector_resp = client.post(
            "/api/v1/bridges/connectors",
            headers=_auth_headers(),
            json={
                "platform": "discord",
                "display_name": "Discord Release Bridge",
                "direction": "bidirectional",
                "enabled": True,
            },
        )
        assert connector_resp.status_code == 201
        connector_id = connector_resp.json()["connector_id"]

        link_resp = client.post(
            "/api/v1/bridges/links",
            headers=_auth_headers(),
            json={
                "connector_id": connector_id,
                "room_id": "!release:localhost",
                "external_room_id": "discord_channel_42",
                "external_room_name": "release-room",
                "relay_prefix": "[DiscordBridge]",
            },
        )
        assert link_resp.status_code == 201

        relayed = client.post(
            "/api/v1/bridges/relay/inbound",
            headers=_auth_headers(),
            json={
                "connector_id": connector_id,
                "external_room_id": "discord_channel_42",
                "external_sender": "alex",
                "message": "please help summarize blockers for today's release",
            },
        )
        assert relayed.status_code == 200
        payload = relayed.json()
        assert payload["status"] == "ok"
        assert payload["room_id"] == "!release:localhost"
        assert payload["event_id"].startswith("$bridge_")
        assert payload["relayed_body"].startswith("[DiscordBridge]")
        assert "alex" in payload["relayed_body"]

        assert len(matrix_stub.sent_messages) == 1
        assert matrix_stub.sent_messages[0]["room_id"] == "!release:localhost"

        relay_audits = [item for item in audit_stub.events if item.action_type == "bridge_inbound_relay"]
        assert relay_audits
        assert relay_audits[-1].decision == relay_audits[-1].decision.ALLOW


def test_bridge_outbound_preview_returns_messages() -> None:
    with TestClient(app) as client:
        audit_stub, _ = _install_stubs(client)

        connector_resp = client.post(
            "/api/v1/bridges/connectors",
            headers=_auth_headers(),
            json={
                "platform": "slack",
                "display_name": "Slack Sync Bridge",
                "direction": "outbound",
                "enabled": True,
            },
        )
        assert connector_resp.status_code == 201
        connector_id = connector_resp.json()["connector_id"]

        preview_resp = client.post(
            "/api/v1/bridges/relay/outbound/preview",
            headers=_auth_headers(),
            json={
                "connector_id": connector_id,
                "room_id": "!ops:localhost",
                "external_room_id": "slack_ops_room",
                "limit": 2,
            },
        )
        assert preview_resp.status_code == 200
        payload = preview_resp.json()
        assert payload["connector_id"] == connector_id
        assert payload["room_id"] == "!ops:localhost"
        assert len(payload["preview_items"]) == 2
        assert payload["preview_items"][0]["external_room_id"] == "slack_ops_room"
        assert payload["preview_items"][0]["payload_text"].startswith("[Matrix->slack]")

        preview_audits = [item for item in audit_stub.events if item.action_type == "bridge_outbound_preview"]
        assert preview_audits
        assert preview_audits[-1].decision == preview_audits[-1].decision.ALLOW

