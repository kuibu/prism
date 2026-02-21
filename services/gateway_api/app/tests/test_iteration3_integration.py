from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.agent.tool_gateway import InMemoryRateCounter
from app.audit.schemas import AuditEvent, AuditEventCreate, AuditQuery, AuditVerifyResponse
from app.audit.verification import compute_chain_hash, sha256_hex, verify_chain
from app.main import app
from app.matrix.admin import AgentBotManager
from app.matrix.client import MatrixClientError
from app.policy.opa_client import OPANotFoundError


class _StubAuditClient:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def health(self) -> dict[str, object]:
        return {"reachable": True, "host": "stub", "port": 3322}

    async def append_audit_event(self, request: AuditEventCreate) -> AuditEvent:
        ts = datetime.now(UTC)
        ts_ms = int(ts.timestamp() * 1000)
        prev_hash = self.events[-1].chain_hash if self.events else None
        input_hash = request.input_hash or sha256_hex(request.input_data)
        output_hash = request.output_hash or sha256_hex(request.output_data)
        event_id = str(uuid4())
        chain_hash = compute_chain_hash(
            {
                "event_id": event_id,
                "ts_ms": ts_ms,
                "actor_type": request.actor_type.value,
                "actor_id": request.actor_id,
                "action_type": request.action_type,
                "resource_type": request.resource_type,
                "resource_id": request.resource_id,
                "decision": request.decision.value,
                "reason_code": request.reason_code,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "prev_hash": prev_hash,
                "signature": request.signature,
                "user_id": request.user_id,
                "room_id": request.room_id,
                "metadata": request.metadata,
            }
        )

        event = AuditEvent(
            event_id=event_id,
            ts=ts,
            ts_ms=ts_ms,
            actor_type=request.actor_type,
            actor_id=request.actor_id,
            action_type=request.action_type,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            decision=request.decision,
            reason_code=request.reason_code,
            input_hash=input_hash,
            output_hash=output_hash,
            prev_hash=prev_hash,
            chain_hash=chain_hash,
            signature=request.signature,
            user_id=request.user_id,
            room_id=request.room_id,
            metadata=request.metadata,
            immudb_tx_id=len(self.events) + 1,
        )
        self.events.append(event)
        return event

    async def query_audit_events(self, query: AuditQuery) -> list[AuditEvent]:
        filtered = list(self.events)

        if query.actor_id is not None:
            filtered = [event for event in filtered if event.actor_id == query.actor_id]
        if query.user_id is not None:
            filtered = [event for event in filtered if event.user_id == query.user_id]
        if query.room_id is not None:
            filtered = [event for event in filtered if event.room_id == query.room_id]
        if query.action_type is not None:
            filtered = [event for event in filtered if event.action_type == query.action_type]

        filtered.sort(
            key=lambda event: (event.ts_ms, event.immudb_tx_id or 0),
            reverse=True,
        )
        return filtered[: query.limit]

    async def verify_audit_chain(self, query: AuditQuery) -> AuditVerifyResponse:
        events = await self.query_audit_events(query)
        ordered = list(reversed(events))
        expected_prev = ordered[0].prev_hash if ordered else None
        verified, broken_event_id, reason = verify_chain(
            ordered,
            expected_first_prev_hash=expected_prev,
        )
        first_event_id = ordered[0].event_id if ordered else None
        last_event_id = ordered[-1].event_id if ordered else None
        return AuditVerifyResponse(
            verified=verified,
            checked_events=len(ordered),
            first_event_id=first_event_id,
            last_event_id=last_event_id,
            broken_event_id=broken_event_id,
            reason=reason,
            state_tx_id=len(self.events),
            state_tx_hash=sha256_hex({"count": len(self.events)}),
        )


class _StubOPAClient:
    def __init__(self) -> None:
        self.grants: dict[str, dict[str, object]] = {}

    async def health(self) -> dict[str, object]:
        return {"reachable": True, "status_code": 200}

    async def get_document(self, document_path: str) -> dict[str, object]:
        if document_path.endswith("/grants"):
            return {grant_id: dict(value) for grant_id, value in self.grants.items()}

        grant_id = self._extract_grant_id(document_path)
        if grant_id is None or grant_id not in self.grants:
            raise OPANotFoundError(f"opa_document_not_found:{document_path}")
        return dict(self.grants[grant_id])

    async def put_document(self, document_path: str, payload: dict[str, object]) -> None:
        if document_path.endswith("/grants"):
            self.grants = {
                grant_id: dict(value)
                for grant_id, value in payload.items()
                if isinstance(value, dict)
            }
            return

        grant_id = self._extract_grant_id(document_path)
        if grant_id is None:
            return
        self.grants[grant_id] = dict(payload)

    async def delete_document(self, document_path: str) -> None:
        grant_id = self._extract_grant_id(document_path)
        if grant_id is None or grant_id not in self.grants:
            raise OPANotFoundError(f"opa_document_not_found:{document_path}")
        del self.grants[grant_id]

    async def evaluate(self, policy_path: str, payload: dict[str, object]) -> dict[str, object]:
        _ = policy_path
        action = str(payload.get("action", ""))
        if action == "healthcheck":
            return {"allow": True, "reason": "healthcheck"}
        if action != "read_messages":
            return {"allow": False, "reason": "no_active_grant"}

        user_id = str(payload.get("user_id", ""))
        agent_id = str(payload.get("agent_id", ""))
        purpose = str(payload.get("purpose", ""))
        data_category = str(payload.get("data_category", "room_messages"))
        request_count = int(payload.get("request_count_per_minute", 1))
        ts = self._parse_ts(payload.get("ts"))

        grants = list(self.grants.values())

        for grant in grants:
            if not self._base_match(
                grant,
                user_id=user_id,
                agent_id=agent_id,
                purpose=purpose,
                data_category=data_category,
            ):
                continue
            if str(grant.get("status")) != "active":
                continue
            if not self._in_time_window(grant, ts):
                continue
            rate_limit = int(grant.get("rate_limit_per_minute", 60))
            if request_count <= rate_limit:
                return {"allow": True, "reason": "grant_active"}

        for grant in grants:
            if not self._base_match(
                grant,
                user_id=user_id,
                agent_id=agent_id,
                purpose=purpose,
                data_category=data_category,
            ):
                continue
            if str(grant.get("status")) != "active":
                continue
            if not self._in_time_window(grant, ts):
                continue
            rate_limit = int(grant.get("rate_limit_per_minute", 60))
            if request_count > rate_limit:
                return {"allow": False, "reason": "rate_limit_exceeded"}

        for grant in grants:
            if not self._base_match(
                grant,
                user_id=user_id,
                agent_id=agent_id,
                purpose=purpose,
                data_category=data_category,
            ):
                continue
            if str(grant.get("status")) != "active":
                continue
            if not self._in_time_window(grant, ts):
                return {"allow": False, "reason": "time_window_exceeded"}

        for grant in grants:
            if not self._base_match(
                grant,
                user_id=user_id,
                agent_id=agent_id,
                purpose=purpose,
                data_category=data_category,
            ):
                continue
            if str(grant.get("status")) == "revoked":
                return {"allow": False, "reason": "grant_revoked"}

        for grant in grants:
            if str(grant.get("user_id")) != user_id:
                continue
            if str(grant.get("agent_id")) != agent_id:
                continue
            grant_data_category = str(grant.get("data_category", "room_messages"))
            if grant_data_category != data_category:
                continue
            if str(grant.get("purpose", "")) != purpose:
                return {"allow": False, "reason": "purpose_not_allowed"}

        return {"allow": False, "reason": "no_active_grant"}

    async def close(self) -> None:
        return None

    @staticmethod
    def _extract_grant_id(path: str) -> str | None:
        parts = path.strip("/").split("/")
        if len(parts) < 2:
            return None
        if parts[-2] != "grants":
            return None
        return parts[-1]

    @staticmethod
    def _parse_ts(value: object) -> datetime:
        if not isinstance(value, str) or value == "":
            return datetime.now(UTC)
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)

    @staticmethod
    def _parse_optional_ts(value: object) -> datetime | None:
        if not isinstance(value, str) or value == "":
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)

    @classmethod
    def _in_time_window(cls, grant: dict[str, object], ts: datetime) -> bool:
        start = cls._parse_optional_ts(grant.get("time_window_start"))
        end = cls._parse_optional_ts(grant.get("time_window_end"))
        if start is not None and ts < start:
            return False
        if end is not None and ts > end:
            return False
        return True

    @staticmethod
    def _base_match(
        grant: dict[str, object],
        *,
        user_id: str,
        agent_id: str,
        purpose: str,
        data_category: str,
    ) -> bool:
        grant_data_category = str(grant.get("data_category", "room_messages"))
        return (
            str(grant.get("user_id", "")) == user_id
            and str(grant.get("agent_id", "")) == agent_id
            and str(grant.get("purpose", "")) == purpose
            and grant_data_category == data_category
        )


class _StubMatrixClient:
    def __init__(self) -> None:
        self._token_to_user = {
            "token_alice": "@alice:localhost",
            "token_bob": "@bob:localhost",
        }
        self._user_to_token = {
            "@alice:localhost": "token_alice",
            "@bob:localhost": "token_bob",
        }
        self._token_counter = 0

    async def whoami(self, *, access_token: str) -> dict[str, object]:
        user_id = self._token_to_user.get(access_token)
        if user_id is None:
            raise MatrixClientError("invalid_token")
        return {"user_id": user_id}

    def _token_for_user(self, user_id: str) -> str:
        existing = self._user_to_token.get(user_id)
        if existing is not None:
            return existing

        self._token_counter += 1
        token = f"token_auto_{self._token_counter}"
        self._user_to_token[user_id] = token
        self._token_to_user[token] = user_id
        return token

    async def register(self, *, username: str, password: str) -> dict[str, object]:
        _ = password
        user_id = f"@{username}:localhost"
        return {
            "user_id": user_id,
            "device_id": "DEVICE123",
            "access_token": self._token_for_user(user_id),
        }

    async def login(self, *, username: str, password: str) -> dict[str, object]:
        _ = password
        user_id = f"@{username}:localhost"
        return {
            "user_id": user_id,
            "device_id": "DEVICE123",
            "access_token": self._token_for_user(user_id),
        }

    async def create_room(
        self,
        *,
        access_token: str,
        name: str | None,
        invite: list[str],
        preset: str,
    ) -> dict[str, object]:
        _ = access_token, name, invite, preset
        return {"room_id": "!room:localhost"}

    async def join_room(self, *, access_token: str, room_id: str) -> dict[str, object]:
        if access_token not in self._token_to_user:
            raise MatrixClientError("invalid_token")
        return {"room_id": room_id}

    async def invite_user(
        self,
        *,
        access_token: str,
        room_id: str,
        user_id: str,
    ) -> dict[str, object]:
        _ = room_id, user_id
        if access_token not in self._token_to_user:
            raise MatrixClientError("invalid_token")
        return {}

    async def get_joined_members(
        self,
        *,
        access_token: str,
        room_id: str,
    ) -> dict[str, object]:
        _ = room_id
        user_id = self._token_to_user.get(access_token)
        if user_id is None:
            raise MatrixClientError("invalid_token")
        joined: dict[str, dict[str, str]] = {
            "@bob:localhost": {"display_name": "@bob:localhost"},
            "@alice:localhost": {"display_name": "@alice:localhost"},
        }
        if user_id not in joined:
            joined[user_id] = {"display_name": user_id}
        return {"joined": joined}

    async def get_room_state_event(
        self,
        *,
        access_token: str,
        room_id: str,
        event_type: str,
        state_key: str | None = None,
    ) -> dict[str, object]:
        _ = access_token, room_id, state_key
        if event_type == "m.room.name":
            return {"name": "Stub Room"}
        if event_type == "m.room.create":
            return {"creator": "@alice:localhost"}
        return {}

    async def download_media(
        self,
        *,
        access_token: str,
        mxc_uri: str,
    ) -> tuple[bytes, dict[str, str]]:
        _ = access_token, mxc_uri
        return b"stub-media", {"content-type": "application/octet-stream"}

    async def send_text_message(
        self,
        *,
        access_token: str,
        room_id: str,
        body: str,
        txn_id: str | None = None,
    ) -> dict[str, object]:
        _ = room_id, body
        if access_token not in self._token_to_user:
            raise MatrixClientError("invalid_token")
        suffix = txn_id or f"m{self._token_counter + 1}"
        return {"event_id": f"$event_{suffix}:localhost"}

    async def upload_media(
        self,
        *,
        access_token: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, object]:
        _ = access_token, filename, content_type, content
        return {"content_uri": "mxc://localhost/abc123"}

    async def send_file_message(
        self,
        *,
        access_token: str,
        room_id: str,
        filename: str,
        content_uri: str,
        content_type: str,
        size_bytes: int,
        txn_id: str | None = None,
    ) -> dict[str, object]:
        _ = access_token, room_id, filename, content_uri, content_type, size_bytes, txn_id
        return {"event_id": "$fileevent:localhost"}

    async def read_room_messages(
        self,
        *,
        access_token: str,
        room_id: str,
        limit: int,
    ) -> list[str]:
        _ = room_id, limit
        if access_token not in self._token_to_user:
            raise MatrixClientError("invalid_token")
        return ["finish API", "review PR", "write docs"]

    async def sync(
        self,
        *,
        access_token: str,
        since: str | None,
        timeout_ms: int,
        full_state: bool,
    ) -> dict[str, object]:
        return {
            "next_batch": "s1",
            "rooms": {"join": {}},
            "echo": {
                "since": since,
                "timeout_ms": timeout_ms,
                "full_state": full_state,
                "token_len": len(access_token),
            },
        }


def _install_stubs(client: TestClient) -> _StubAuditClient:
    audit_stub = _StubAuditClient()
    matrix_stub = _StubMatrixClient()
    client.app.state.immudb_client = audit_stub
    client.app.state.opa_client = _StubOPAClient()
    client.app.state.matrix_client = matrix_stub
    client.app.state.agent_bot_manager = AgentBotManager(
        matrix_client=matrix_stub,
        username_prefix="agent_stub",
        password_secret="secret_stub",
    )
    client.app.state.agent_rate_counter = InMemoryRateCounter(window_seconds=60)
    return audit_stub


def _grant_payload() -> dict[str, object]:
    return {
        "user_id": "@alice:localhost",
        "agent_id": "agent.summary",
        "data_category": "room_messages",
        "purpose": "daily_summary",
        "rate_limit_per_minute": 60,
    }


def _summarize_payload() -> dict[str, object]:
    return {
        "agent_id": "agent.summary",
        "room_id": "!room:localhost",
        "purpose": "daily_summary",
        "recent_message_limit": 20,
        "max_items": 3,
    }


def _auth_headers(token: str = "token_alice") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_required_mvp_routes_not_404() -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        checks = {
            "/api/v1/policy/grants": client.get("/api/v1/policy/grants"),
            "/api/v1/policy/revoke": client.get("/api/v1/policy/revoke"),
            "/api/v1/audit/events": client.get("/api/v1/audit/events"),
            "/api/v1/audit/verify": client.get("/api/v1/audit/verify"),
            "/api/v1/agent/summarize": client.get("/api/v1/agent/summarize"),
            "/api/v1/matrix/sync": client.get("/api/v1/matrix/sync"),
        }

    for path, response in checks.items():
        assert response.status_code != 404, path


def test_audit_event_write_and_verify() -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        payload = {
            "actor_type": "user",
            "actor_id": "@alice:localhost",
            "action_type": "send_message",
            "resource_type": "room",
            "resource_id": "!room:localhost",
            "decision": "allow",
            "reason_code": "ok",
            "user_id": "@alice:localhost",
            "room_id": "!room:localhost",
            "input_data": {"n": 1},
            "output_data": {"result": "sent"},
        }

        first = client.post("/api/v1/audit/events", json=payload, headers=_auth_headers())
        second = client.post("/api/v1/audit/events", json=payload, headers=_auth_headers())
        listed = client.get(
            "/api/v1/audit/events",
            params={"actor_id": "@alice:localhost"},
            headers=_auth_headers(),
        )
        verified = client.get(
            "/api/v1/audit/verify",
            params={"actor_id": "@alice:localhost"},
            headers=_auth_headers(),
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert listed.status_code == 200
    assert len(listed.json()["events"]) == 2
    assert verified.status_code == 200
    assert verified.json()["verified"] is True
    assert verified.json()["checked_events"] == 2


def test_policy_allow_with_opa_grant() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        grant_response = client.post(
            "/api/v1/policy/grants",
            json=_grant_payload(),
            headers=_auth_headers(),
        )
        summarize_response = client.post(
            "/api/v1/agent/summarize",
            json=_summarize_payload(),
            headers=_auth_headers(),
        )

    assert grant_response.status_code == 201
    assert summarize_response.status_code == 200
    assert summarize_response.json()["decision"] == "allow"
    assert summarize_response.json()["reason"] == "grant_active"


def test_policy_deny_after_revoke() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        grant_response = client.post(
            "/api/v1/policy/grants",
            json=_grant_payload(),
            headers=_auth_headers(),
        )
        grant = grant_response.json()
        revoke_response = client.post(
            "/api/v1/policy/revoke",
            json={
                "user_id": "@alice:localhost",
                "grant_id": grant["grant_id"],
                "reason": "user_request",
            },
            headers=_auth_headers(),
        )
        summarize_response = client.post(
            "/api/v1/agent/summarize",
            json=_summarize_payload(),
            headers=_auth_headers(),
        )

    assert grant_response.status_code == 201
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"
    assert summarize_response.status_code == 403
    assert summarize_response.json()["detail"]["reason"] == "grant_revoked"


def test_agent_tool_call_writes_audit() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        client.post(
            "/api/v1/policy/grants",
            json=_grant_payload(),
            headers=_auth_headers(),
        )
        summarize_response = client.post(
            "/api/v1/agent/summarize",
            json=_summarize_payload(),
            headers=_auth_headers(),
        )
        audit_response = client.get(
            "/api/v1/audit/events",
            params={"actor_id": "agent.summary", "action_type": "agent_summarize"},
            headers=_auth_headers(),
        )

    assert summarize_response.status_code == 200
    assert audit_response.status_code == 200
    events = audit_response.json()["events"]
    assert len(events) >= 1
    assert events[0]["action_type"] == "agent_summarize"
    assert events[0]["decision"] == "allow"


def test_agent_summarize_and_send_writes_audit() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        client.post(
            "/api/v1/policy/grants",
            json=_grant_payload(),
            headers=_auth_headers(),
        )
        summarize_response = client.post(
            "/api/v1/agent/summarize-and-send",
            json=_summarize_payload(),
            headers=_auth_headers(),
        )
        audit_response = client.get(
            "/api/v1/audit/events",
            params={"actor_id": "agent.summary", "action_type": "agent_send_summary_message"},
            headers=_auth_headers(),
        )

    assert summarize_response.status_code == 200
    payload = summarize_response.json()
    assert payload["decision"] == "allow"
    assert payload["event_id"].startswith("$event_")
    assert payload["bot_user_id"].startswith("@agent_stub_")
    assert audit_response.status_code == 200
    events = audit_response.json()["events"]
    assert len(events) >= 1
    assert events[0]["decision"] == "allow"


def test_matrix_sync_smoke_mocked() -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        response = client.get(
            "/api/v1/matrix/sync",
            headers=_auth_headers(),
            params={
                "room_id": "!room:localhost",
                "since": "s0",
                "timeout_ms": 1000,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_batch"] == "s1"
    assert payload["echo"]["since"] == "s0"


def test_matrix_invite_forbidden_maps_to_403() -> None:
    class _InviteForbiddenMatrix(_StubMatrixClient):
        async def invite_user(
            self,
            *,
            access_token: str,
            room_id: str,
            user_id: str,
        ) -> dict[str, object]:
            _ = access_token, room_id, user_id
            raise MatrixClientError(
                "M_FORBIDDEN: no invite permission",
                status_code=403,
                errcode="M_FORBIDDEN",
            )

    with TestClient(app) as client:
        audit_stub = _install_stubs(client)
        matrix_stub = _InviteForbiddenMatrix()
        client.app.state.matrix_client = matrix_stub
        client.app.state.agent_bot_manager = AgentBotManager(
            matrix_client=matrix_stub,
            username_prefix="agent_stub",
            password_secret="secret_stub",
        )

        response = client.post(
            "/api/v1/matrix/rooms/!room:localhost/invite",
            headers=_auth_headers(),
            json={"user_id": "@bob:localhost"},
        )

        assert response.status_code == 403
        assert "matrix_invite_user_forbidden" in response.json()["detail"]

        audit_events = [event for event in audit_stub.events if event.action_type == "matrix_invite_user"]
        assert len(audit_events) == 1
        assert audit_events[0].decision.value == "deny"


def test_matrix_sync_timeout_maps_to_504() -> None:
    class _SyncTimeoutMatrix(_StubMatrixClient):
        async def sync(
            self,
            *,
            access_token: str,
            since: str | None,
            timeout_ms: int,
            full_state: bool,
        ) -> dict[str, object]:
            _ = access_token, since, timeout_ms, full_state
            raise MatrixClientError("matrix_request_timeout")

    with TestClient(app) as client:
        _install_stubs(client)
        matrix_stub = _SyncTimeoutMatrix()
        client.app.state.matrix_client = matrix_stub
        client.app.state.agent_bot_manager = AgentBotManager(
            matrix_client=matrix_stub,
            username_prefix="agent_stub",
            password_secret="secret_stub",
        )

        response = client.get(
            "/api/v1/matrix/sync",
            headers=_auth_headers(),
            params={"timeout_ms": 12000},
        )

    assert response.status_code == 504
    assert "matrix_sync_timeout" in response.json()["detail"]


def test_matrix_members_forbidden_maps_to_403() -> None:
    class _MembersForbiddenMatrix(_StubMatrixClient):
        async def get_joined_members(
            self,
            *,
            access_token: str,
            room_id: str,
        ) -> dict[str, object]:
            _ = access_token, room_id
            raise MatrixClientError(
                "User not in room, and room previews are disabled",
                status_code=403,
                errcode="M_FORBIDDEN",
            )

    with TestClient(app) as client:
        _install_stubs(client)
        matrix_stub = _MembersForbiddenMatrix()
        client.app.state.matrix_client = matrix_stub
        client.app.state.agent_bot_manager = AgentBotManager(
            matrix_client=matrix_stub,
            username_prefix="agent_stub",
            password_secret="secret_stub",
        )

        response = client.get(
            "/api/v1/matrix/rooms/!room:localhost/members",
            headers=_auth_headers(),
        )

    assert response.status_code == 403
    assert "matrix_get_joined_members_forbidden" in response.json()["detail"]


def test_matrix_room_summary_returns_name_creator_and_members() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        response = client.get(
            "/api/v1/matrix/rooms/!room:localhost/summary",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["room_id"] == "!room:localhost"
    assert payload["room_name"] == "Stub Room"
    assert payload["creator_user_id"] == "@alice:localhost"
    assert payload["joined_count"] >= 2
    assert payload["joined_user_ids"][0] == "@alice:localhost"
    assert "@bob:localhost" in payload["joined_user_ids"]


def test_matrix_download_media_proxy() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        response = client.get(
            "/api/v1/matrix/media/download",
            params={"mxc_uri": "mxc://localhost/abc123", "filename": "demo.bin"},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.content == b"stub-media"
    assert "attachment; filename=\"demo.bin\"" in response.headers.get("content-disposition", "")


def test_matrix_proxy_login_create_send_audited() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        login_response = client.post(
            "/api/v1/matrix/login",
            json={"username": "alice", "password": "Passw0rd!"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = _auth_headers(token)

        create_response = client.post(
            "/api/v1/matrix/rooms",
            headers=headers,
            json={"name": "Test", "invite": [], "preset": "private_chat"},
        )
        send_response = client.post(
            "/api/v1/matrix/rooms/!room:localhost/messages",
            headers=headers,
            json={"body": "hello"},
        )
        audit_response = client.get(
            "/api/v1/audit/events",
            params={"actor_id": "@alice:localhost", "action_type": "matrix_send_message"},
            headers=headers,
        )

    assert create_response.status_code == 201
    assert send_response.status_code == 201
    assert audit_response.status_code == 200
    events = audit_response.json()["events"]
    assert len(events) >= 1
    assert events[0]["decision"] == "allow"


def test_matrix_file_upload_audited() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        response = client.post(
            "/api/v1/matrix/rooms/room123/files",
            headers=_auth_headers(),
            files={"file": ("notes.txt", b"hello from test", "text/plain")},
        )
        audit_response = client.get(
            "/api/v1/audit/events",
            params={"actor_id": "@alice:localhost", "action_type": "matrix_upload_media"},
            headers=_auth_headers(),
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["content_uri"].startswith("mxc://")
    assert payload["event_id"] == "$fileevent:localhost"
    assert audit_response.status_code == 200
    assert len(audit_response.json()["events"]) >= 1


def test_policy_rejects_user_spoofing() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        response = client.post(
            "/api/v1/policy/grants",
            headers=_auth_headers("token_bob"),
            json=_grant_payload(),
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "user_id_mismatch"


def test_agent_requires_auth_header() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        response = client.post("/api/v1/agent/summarize", json=_summarize_payload())

    assert response.status_code == 401
    assert response.json()["detail"] == "missing_bearer_token"


def test_audit_query_rejects_cross_user_scope() -> None:
    with TestClient(app) as client:
        _install_stubs(client)
        response = client.get(
            "/api/v1/audit/events",
            params={"user_id": "@alice:localhost"},
            headers=_auth_headers("token_bob"),
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "user_id_mismatch"
