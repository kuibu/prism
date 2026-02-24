from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.assistant_models import SecretaryRoomMode
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
        return {"reachable": True}

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
            filtered = [item for item in filtered if item.actor_id == query.actor_id]
        if query.user_id is not None:
            filtered = [item for item in filtered if item.user_id == query.user_id]
        if query.action_type is not None:
            filtered = [item for item in filtered if item.action_type == query.action_type]
        filtered.sort(key=lambda item: item.ts_ms, reverse=True)
        return filtered[: query.limit]

    async def verify_audit_chain(self, query: AuditQuery) -> AuditVerifyResponse:
        events = await self.query_audit_events(query)
        ordered = list(reversed(events))
        expected_prev = ordered[0].prev_hash if ordered else None
        verified, broken_event_id, reason = verify_chain(
            ordered, expected_first_prev_hash=expected_prev
        )
        return AuditVerifyResponse(
            verified=verified,
            checked_events=len(ordered),
            first_event_id=ordered[0].event_id if ordered else None,
            last_event_id=ordered[-1].event_id if ordered else None,
            broken_event_id=broken_event_id,
            reason=reason,
            state_tx_id=len(self.events),
            state_tx_hash=sha256_hex({"count": len(self.events)}),
        )


class _StubOPAClient:
    def __init__(self) -> None:
        self.grants: dict[str, dict[str, object]] = {}
        self.documents: dict[str, dict[str, object]] = {}

    async def health(self) -> dict[str, object]:
        return {"reachable": True}

    async def get_document(self, document_path: str) -> dict[str, object]:
        if document_path.endswith("/grants"):
            return {grant_id: dict(value) for grant_id, value in self.grants.items()}

        grant_id = self._extract_grant_id(document_path)
        if grant_id is not None:
            if grant_id not in self.grants:
                raise OPANotFoundError(f"opa_document_not_found:{document_path}")
            return dict(self.grants[grant_id])

        if document_path not in self.documents:
            raise OPANotFoundError(f"opa_document_not_found:{document_path}")
        return dict(self.documents[document_path])

    async def put_document(self, document_path: str, payload: dict[str, object]) -> None:
        if document_path.endswith("/grants"):
            self.grants = {
                grant_id: dict(value)
                for grant_id, value in payload.items()
                if isinstance(value, dict)
            }
            return

        grant_id = self._extract_grant_id(document_path)
        if grant_id is not None:
            self.grants[grant_id] = dict(payload)
            return

        self.documents[document_path] = dict(payload)

    async def delete_document(self, document_path: str) -> None:
        grant_id = self._extract_grant_id(document_path)
        if grant_id is not None:
            if grant_id not in self.grants:
                raise OPANotFoundError(f"opa_document_not_found:{document_path}")
            del self.grants[grant_id]
            return

        if document_path in self.documents:
            del self.documents[document_path]
            return
        raise OPANotFoundError(f"opa_document_not_found:{document_path}")

    async def evaluate(self, policy_path: str, payload: dict[str, object]) -> dict[str, object]:
        _ = policy_path
        action = str(payload.get("action", ""))
        if action == "healthcheck":
            return {"allow": True, "reason": "healthcheck"}
        if action not in {"read_messages", "collect_messages", "run_skill", "read_memory"}:
            return {"allow": False, "reason": "no_active_grant"}

        user_id = str(payload.get("user_id", ""))
        agent_id = str(payload.get("agent_id", ""))
        purpose = str(payload.get("purpose", ""))
        data_category = str(payload.get("data_category", "room_messages"))
        request_count = int(payload.get("request_count_per_minute", 1))
        ts = self._parse_ts(payload.get("ts"))

        matching = [
            value
            for value in self.grants.values()
            if str(value.get("user_id", "")) == user_id
            and str(value.get("agent_id", "")) == agent_id
            and str(value.get("data_category", "room_messages")) == data_category
        ]

        for grant in matching:
            if str(grant.get("purpose", "")) != purpose:
                continue
            if str(grant.get("status")) == "revoked":
                return {"allow": False, "reason": "grant_revoked"}
            if str(grant.get("status")) != "active":
                continue
            if not self._in_time_window(grant, ts):
                return {"allow": False, "reason": "time_window_exceeded"}
            limit = int(grant.get("rate_limit_per_minute", 60))
            if request_count > limit:
                return {"allow": False, "reason": "rate_limit_exceeded"}
            return {"allow": True, "reason": "grant_active"}

        if matching:
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
    def _parse_optional_ts(value: object) -> datetime | None:
        if not isinstance(value, str) or value == "":
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class _StubMatrixClient:
    def __init__(self) -> None:
        self._token_to_user = {"token_alice": "@alice:localhost", "token_bob": "@bob:localhost"}
        self.sent_messages: list[dict[str, str | None]] = []

    async def whoami(self, *, access_token: str) -> dict[str, object]:
        user_id = self._token_to_user.get(access_token)
        if user_id is None:
            raise MatrixClientError("invalid_token")
        return {"user_id": user_id}

    async def sync(
        self,
        *,
        access_token: str,
        since: str | None,
        timeout_ms: int,
        full_state: bool,
    ) -> dict[str, object]:
        _ = access_token, since, timeout_ms, full_state
        return {
            "next_batch": "s2",
            "rooms": {
                "join": {
                    "!room:localhost": {
                        "timeline": {
                            "events": [
                                {
                                    "type": "m.room.message",
                                    "event_id": "$evt1:localhost",
                                    "sender": "@bob:localhost",
                                    "origin_server_ts": 1731000000000,
                                    "content": {
                                        "msgtype": "m.text",
                                        "body": (
                                            "todo: finish API reference and update risk section"
                                        ),
                                    },
                                },
                                {
                                    "type": "m.room.message",
                                    "event_id": "$evt2:localhost",
                                    "sender": "@alice:localhost",
                                    "origin_server_ts": 1731000002000,
                                    "content": {
                                        "msgtype": "m.text",
                                        "body": "I will follow up with deployment tasks",
                                    },
                                },
                            ]
                        }
                    }
                }
            },
        }

    async def read_room_messages(
        self,
        *,
        access_token: str,
        room_id: str,
        limit: int,
    ) -> list[str]:
        _ = access_token, room_id, limit
        return [
            "todo: finish API reference",
            "Need follow-up with QA",
            "Please summarize blockers for tomorrow",
        ]

    async def register(self, *, username: str, password: str) -> dict[str, object]:
        _ = username, password
        return {"user_id": "@stub:localhost", "access_token": "token_stub", "device_id": "DEV"}

    async def login(self, *, username: str, password: str) -> dict[str, object]:
        _ = username, password
        return {"user_id": "@stub:localhost", "access_token": "token_stub", "device_id": "DEV"}

    async def join_room(self, *, access_token: str, room_id: str) -> dict[str, object]:
        _ = access_token, room_id
        return {"room_id": room_id}

    async def invite_user(
        self, *, access_token: str, room_id: str, user_id: str
    ) -> dict[str, object]:
        _ = access_token, room_id, user_id
        return {}

    async def send_text_message(
        self,
        *,
        access_token: str,
        room_id: str,
        body: str,
        txn_id: str | None = None,
    ) -> dict[str, object]:
        sender = self._token_to_user.get(access_token)
        self.sent_messages.append(
            {
                "sender": sender,
                "room_id": room_id,
                "body": body,
                "txn_id": txn_id,
            }
        )
        return {"event_id": "$skill_send:localhost"}


class _OpenVikingDummyResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP {self.status_code}",
                request=httpx.Request("POST", "http://openviking.local"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, Any]:
        return self._payload


class _OpenVikingDummyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    async def __aenter__(self) -> _OpenVikingDummyClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        _ = exc_type, exc, tb
        return False

    async def request(
        self,
        method: str,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> _OpenVikingDummyResponse:
        self.calls.append((method, endpoint, json))
        if endpoint == "/api/v1/sessions":
            return _OpenVikingDummyResponse(
                {"status": "ok", "result": {"session_id": "sess_prism_1"}}
            )
        if endpoint.endswith("/messages"):
            return _OpenVikingDummyResponse(
                {
                    "status": "ok",
                    "result": {"session_id": "sess_prism_1"},
                }
            )
        if endpoint.endswith("/commit"):
            return _OpenVikingDummyResponse(
                {
                    "status": "ok",
                    "result": {
                        "status": "committed",
                        "memories_extracted": 1,
                    },
                }
            )
        return _OpenVikingDummyResponse({"status": "ok", "result": {}})


def _auth_headers(token: str = "token_alice") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _install_stubs(client: TestClient) -> tuple[_StubAuditClient, _StubMatrixClient]:
    audit_stub = _StubAuditClient()
    opa_stub = _StubOPAClient()
    matrix_stub = _StubMatrixClient()

    client.app.state.immudb_client = audit_stub
    client.app.state.opa_client = opa_stub
    client.app.state.matrix_client = matrix_stub
    client.app.state.agent_bot_manager = AgentBotManager(
        matrix_client=matrix_stub,
        username_prefix="agent_stub",
        password_secret="secret_stub",
    )
    client.app.state.agent_rate_counter = InMemoryRateCounter(window_seconds=60)
    return audit_stub, matrix_stub


def _grant_payload(*, user_id: str, agent_id: str, purpose: str) -> dict[str, object]:
    return {
        "user_id": user_id,
        "agent_id": agent_id,
        "data_category": "room_messages",
        "purpose": purpose,
        "rate_limit_per_minute": 120,
    }


def test_secretary_mode_enum_contains_three_modes() -> None:
    assert {item.value for item in SecretaryRoomMode} == {"auto", "semi", "off"}


def test_agents_bootstrap_and_list() -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        listed = client.get("/api/v1/agents", headers=_auth_headers())

    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    assert payload["secretary"]["kind"] == "secretary"
    assert payload["secretary"]["agent_id"].startswith("agent.secretary")
    assert payload["secretary"]["llm"]["enabled"] is True
    assert payload["secretary"]["llm"]["model"] == "qwen2.5-32b"
    assert payload["secretary"]["llm"]["base_url"] == "https://32b.qwen.rag8.cn/v1"

    assert listed.status_code == 200
    agents = listed.json()["agents"]
    assert len(agents) >= 1
    assert any(item["kind"] == "secretary" for item in agents)


def test_secretary_collect_memory_requires_grant_then_succeeds() -> None:
    with TestClient(app) as client:
        audit_stub, _ = _install_stubs(client)

        bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        secretary_id = bootstrap.json()["secretary"]["agent_id"]

        denied = client.post(
            f"/api/v1/agents/{secretary_id}/memory/collect",
            headers=_auth_headers(),
            json={
                "purpose": "secretary_collect",
                "limit_per_room": 50,
                "include_self_messages": False,
            },
        )

        grant = client.post(
            "/api/v1/policy/grants",
            headers=_auth_headers(),
            json=_grant_payload(
                user_id="@alice:localhost",
                agent_id=secretary_id,
                purpose="secretary_collect",
            ),
        )

        allowed = client.post(
            f"/api/v1/agents/{secretary_id}/memory/collect",
            headers=_auth_headers(),
            json={
                "purpose": "secretary_collect",
                "limit_per_room": 50,
                "include_self_messages": False,
            },
        )

        memory = client.get(
            f"/api/v1/agents/{secretary_id}/memory",
            headers=_auth_headers(),
            params={"limit": 20},
        )

    assert denied.status_code == 403
    assert grant.status_code == 201
    assert allowed.status_code == 200
    assert allowed.json()["stored_count"] >= 1
    assert memory.status_code == 200
    assert len(memory.json()["hits"]) >= 1

    audit_events = [
        event for event in audit_stub.events if event.action_type == "agent_memory_collect"
    ]
    assert any(event.decision.value == "allow" for event in audit_events)


def test_secretary_collect_memory_openviking_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        settings = client.app.state.settings
        original_backend = settings.agent_memory_backend
        original_base_url = settings.openviking_base_url
        original_retry = settings.openviking_retry_attempts
        original_timeout = settings.openviking_timeout_seconds

        settings.agent_memory_backend = "openviking"
        settings.openviking_base_url = "http://openviking.local:1933"
        settings.openviking_retry_attempts = 1
        settings.openviking_timeout_seconds = 2.0

        dummy_client = _OpenVikingDummyClient()
        monkeypatch.setattr(
            "app.agent.memory_backends.httpx.AsyncClient",
            lambda **_: dummy_client,
        )

        try:
            bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
            secretary_id = bootstrap.json()["secretary"]["agent_id"]

            grant = client.post(
                "/api/v1/policy/grants",
                headers=_auth_headers(),
                json=_grant_payload(
                    user_id="@alice:localhost",
                    agent_id=secretary_id,
                    purpose="secretary_collect",
                ),
            )
            assert grant.status_code == 201

            allowed = client.post(
                f"/api/v1/agents/{secretary_id}/memory/collect",
                headers=_auth_headers(),
                json={
                    "purpose": "secretary_collect",
                    "limit_per_room": 50,
                    "include_self_messages": False,
                },
            )
            assert allowed.status_code == 200
            assert allowed.json()["stored_count"] >= 1
            assert any(endpoint == "/api/v1/sessions" for _, endpoint, _ in dummy_client.calls)
            assert any(endpoint.endswith("/messages") for _, endpoint, _ in dummy_client.calls)
            assert any(endpoint.endswith("/commit") for _, endpoint, _ in dummy_client.calls)
        finally:
            settings.agent_memory_backend = original_backend
            settings.openviking_base_url = original_base_url
            settings.openviking_retry_attempts = original_retry
            settings.openviking_timeout_seconds = original_timeout


def test_specialist_memory_note_openviking_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        settings = client.app.state.settings
        original_backend = settings.agent_memory_backend
        original_base_url = settings.openviking_base_url
        original_retry = settings.openviking_retry_attempts
        original_timeout = settings.openviking_timeout_seconds

        settings.agent_memory_backend = "openviking"
        settings.openviking_base_url = "http://openviking.local:1933"
        settings.openviking_retry_attempts = 1
        settings.openviking_timeout_seconds = 2.0

        dummy_client = _OpenVikingDummyClient()
        monkeypatch.setattr(
            "app.agent.memory_backends.httpx.AsyncClient",
            lambda **_: dummy_client,
        )

        try:
            bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
            assert bootstrap.status_code == 200

            create_specialist = client.post(
                "/api/v1/agents",
                headers=_auth_headers(),
                json={
                    "kind": "specialist",
                    "display_name": "Memory Specialist",
                    "purpose": "memory_organize",
                    "description": "Organize memory notes",
                    "system_prompt": "Organize notes by priority.",
                    "skill_ids": ["specialist.todo_extractor"],
                    "room_ids": [],
                    "auto_collect_enabled": False,
                },
            )
            assert create_specialist.status_code == 201
            specialist_id = create_specialist.json()["agent_id"]

            note = client.post(
                f"/api/v1/agents/{specialist_id}/memory/notes",
                headers=_auth_headers(),
                json={
                    "content": "记录一个子 agent 的长期记忆样例。",
                    "tags": ["memory", "specialist"],
                    "importance": 0.7,
                },
            )
            assert note.status_code == 201
            assert note.json()["stored_count"] >= 1
            assert any(endpoint == "/api/v1/sessions" for _, endpoint, _ in dummy_client.calls)
            assert any(endpoint.endswith("/messages") for _, endpoint, _ in dummy_client.calls)
            assert any(endpoint.endswith("/commit") for _, endpoint, _ in dummy_client.calls)
        finally:
            settings.agent_memory_backend = original_backend
            settings.openviking_base_url = original_base_url
            settings.openviking_retry_attempts = original_retry
            settings.openviking_timeout_seconds = original_timeout


def test_specialist_skill_run_writes_audit() -> None:
    with TestClient(app) as client:
        audit_stub, _ = _install_stubs(client)

        client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        create_specialist = client.post(
            "/api/v1/agents",
            headers=_auth_headers(),
            json={
                "kind": "specialist",
                "display_name": "Todo Specialist",
                "purpose": "todo_followup",
                "description": "Extract todos from messages",
                "system_prompt": "Focus on concrete follow-up tasks.",
                "skill_ids": ["specialist.todo_extractor"],
                "room_ids": ["!room:localhost"],
                "auto_collect_enabled": False,
            },
        )
        specialist_id = create_specialist.json()["agent_id"]

        grant = client.post(
            "/api/v1/policy/grants",
            headers=_auth_headers(),
            json=_grant_payload(
                user_id="@alice:localhost",
                agent_id=specialist_id,
                purpose="todo_followup",
            ),
        )

        run = client.post(
            f"/api/v1/agents/{specialist_id}/skills/run",
            headers=_auth_headers(),
            json={
                "skill_id": "specialist.todo_extractor",
                "query": "please extract todo and next actions",
                "purpose": "todo_followup",
                "room_id": "!room:localhost",
                "room_message_limit": 50,
                "memory_limit": 20,
                "send_to_room": False,
            },
        )

    assert create_specialist.status_code == 201
    assert grant.status_code == 201
    assert run.status_code == 200
    payload = run.json()
    assert payload["skill_id"] == "specialist.todo_extractor"
    output_text = str(payload["output_text"]).lower()
    assert output_text != ""
    assert (
        "todo" in output_text
        or "next action" in output_text
        or "follow up" in output_text
    )

    audit_events = [event for event in audit_stub.events if event.action_type == "agent_skill_run"]
    assert len(audit_events) >= 1
    assert any(event.decision.value == "allow" for event in audit_events)


def test_specialist_auto_bound_to_secretary_manager() -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        secretary_id = bootstrap.json()["secretary"]["agent_id"]

        create_specialist = client.post(
            "/api/v1/agents",
            headers=_auth_headers(),
            json={
                "kind": "specialist",
                "display_name": "Ops Specialist",
                "purpose": "ops_followup",
                "description": "Operations follow-up",
                "system_prompt": "Track operational tasks.",
                "skill_ids": ["specialist.todo_extractor"],
                "room_ids": [],
                "auto_collect_enabled": False,
            },
        )

    assert create_specialist.status_code == 201
    payload = create_specialist.json()
    assert payload["kind"] == "specialist"
    assert payload["manager_agent_id"] == secretary_id
    assert payload["parent_policy_mode"] == "inherit"


def test_secretary_room_mode_suggestion_and_approve_flow() -> None:
    with TestClient(app) as client:
        audit_stub, matrix_stub = _install_stubs(client)

        bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        secretary_id = bootstrap.json()["secretary"]["agent_id"]

        grant = client.post(
            "/api/v1/policy/grants",
            headers=_auth_headers(),
            json=_grant_payload(
                user_id="@alice:localhost",
                agent_id=secretary_id,
                purpose="assistant_reply",
            ),
        )
        assert grant.status_code == 201

        mode = client.put(
            "/api/v1/agents/secretary/modes/!room:localhost",
            headers=_auth_headers(),
            json={"mode": "semi"},
        )
        assert mode.status_code == 200
        assert mode.json()["mode"] == "semi"

        generated = client.post(
            "/api/v1/agents/secretary/suggestions/generate",
            headers=_auth_headers(),
            json={
                "room_id": "!room:localhost",
                "source_text": "请整理今天的todo并给优先级",
                "source_event_id": "$evt3:localhost",
                "source_sender_id": "@bob:localhost",
                "purpose": "assistant_reply",
            },
        )
        assert generated.status_code == 200
        generated_payload = generated.json()
        assert generated_payload["status"] == "ok"
        assert generated_payload["mode"] == "semi"
        assert generated_payload["memory_ingest"]["stored_count"] >= 1
        assert generated_payload["suggestion"]["status"] == "pending"
        assert len(generated_payload["insights"]) >= 4

        suggestion_id = generated_payload["suggestion"]["suggestion_id"]
        listed = client.get(
            "/api/v1/agents/secretary/suggestions",
            headers=_auth_headers(),
            params={"room_id": "!room:localhost", "status": "pending"},
        )
        assert listed.status_code == 200
        assert any(item["suggestion_id"] == suggestion_id for item in listed.json()["suggestions"])

        approved = client.post(
            f"/api/v1/agents/secretary/suggestions/{suggestion_id}/approve",
            headers=_auth_headers(),
            json={"send_to_room": True, "purpose": "assistant_reply"},
        )
        assert approved.status_code == 200
        approved_payload = approved.json()
        assert approved_payload["suggestion"]["status"] == "posted"
        assert approved_payload["room_event_id"] == "$skill_send:localhost"

        insights = client.get(
            "/api/v1/agents/secretary/insights",
            headers=_auth_headers(),
            params={"room_id": "!room:localhost"},
        )
        assert insights.status_code == 200
        assert len(insights.json()["insights"]) >= 4

    assert any(event.action_type == "secretary_suggestion_generate" for event in audit_stub.events)
    assert any(event.action_type == "secretary_suggestion_approve" for event in audit_stub.events)
    assert len(matrix_stub.sent_messages) >= 1


def test_secretary_mode_off_skips_suggestion_creation() -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        secretary_id = bootstrap.json()["secretary"]["agent_id"]
        grant = client.post(
            "/api/v1/policy/grants",
            headers=_auth_headers(),
            json=_grant_payload(
                user_id="@alice:localhost",
                agent_id=secretary_id,
                purpose="assistant_reply",
            ),
        )
        assert grant.status_code == 201

        generated = client.post(
            "/api/v1/agents/secretary/suggestions/generate",
            headers=_auth_headers(),
            json={
                "room_id": "!room:localhost",
                "source_text": "今天是否要上线？",
                "purpose": "assistant_reply",
            },
        )
        assert generated.status_code == 200
        payload = generated.json()
        assert payload["status"] == "ignored"
        assert payload["mode"] == "off"
        assert "suggestion" not in payload
        assert payload["memory_ingest"]["stored_count"] >= 1

        memory = client.get(
            f"/api/v1/agents/{secretary_id}/memory",
            headers=_auth_headers(),
            params={"limit": 20},
        )
        assert memory.status_code == 200
        hits = memory.json()["hits"]
        assert len(hits) >= 1
        assert any("今天是否要上线" in row.get("content", "") for row in hits)


def test_secretary_auto_ingest_memory_deduplicates_by_source_event_id() -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        secretary_id = bootstrap.json()["secretary"]["agent_id"]
        grant = client.post(
            "/api/v1/policy/grants",
            headers=_auth_headers(),
            json=_grant_payload(
                user_id="@alice:localhost",
                agent_id=secretary_id,
                purpose="assistant_reply",
            ),
        )
        assert grant.status_code == 201

        first = client.post(
            "/api/v1/agents/secretary/suggestions/generate",
            headers=_auth_headers(),
            json={
                "room_id": "!room:localhost",
                "source_text": "请确认风险清单",
                "source_event_id": "$evt-ingest-1:localhost",
                "source_sender_id": "@bob:localhost",
                "purpose": "assistant_reply",
            },
        )
        second = client.post(
            "/api/v1/agents/secretary/suggestions/generate",
            headers=_auth_headers(),
            json={
                "room_id": "!room:localhost",
                "source_text": "请确认风险清单",
                "source_event_id": "$evt-ingest-1:localhost",
                "source_sender_id": "@bob:localhost",
                "purpose": "assistant_reply",
            },
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["memory_ingest"]["stored_count"] == 1
        assert second.json()["memory_ingest"]["stored_count"] == 0
        assert second.json()["memory_ingest"]["skipped_count"] >= 1

        memory = client.get(
            f"/api/v1/agents/{secretary_id}/memory",
            headers=_auth_headers(),
            params={"limit": 40},
        )
        assert memory.status_code == 200
        hits = memory.json()["hits"]
        matched = [row for row in hits if row.get("source_id") == "$evt-ingest-1:localhost"]
        assert len(matched) == 1


def test_secretary_auto_mode_posts_as_user_with_marker() -> None:
    with TestClient(app) as client:
        _, matrix_stub = _install_stubs(client)

        bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        secretary_id = bootstrap.json()["secretary"]["agent_id"]
        grant = client.post(
            "/api/v1/policy/grants",
            headers=_auth_headers(),
            json=_grant_payload(
                user_id="@alice:localhost",
                agent_id=secretary_id,
                purpose="assistant_reply",
            ),
        )
        assert grant.status_code == 201

        mode = client.put(
            "/api/v1/agents/secretary/modes/!room:localhost",
            headers=_auth_headers(),
            json={"mode": "auto"},
        )
        assert mode.status_code == 200

        generated = client.post(
            "/api/v1/agents/secretary/suggestions/generate",
            headers=_auth_headers(),
            json={
                "room_id": "!room:localhost",
                "source_text": "请确认今晚的发布窗口和回滚预案",
                "purpose": "assistant_reply",
            },
        )
        assert generated.status_code == 200
        payload = generated.json()
        assert payload["status"] == "ok"
        assert payload["mode"] == "auto"
        assert payload["suggestion"]["status"] == "posted"
        assert payload["bot_user_id"] == "@alice:localhost"

    assert len(matrix_stub.sent_messages) >= 1
    latest = matrix_stub.sent_messages[-1]
    assert latest["sender"] == "@alice:localhost"
    assert latest["room_id"] == "!room:localhost"
    assert "数字秘书自动回复" in str(latest["body"])


def test_create_agent_with_llm_config_persisted() -> None:
    with TestClient(app) as client:
        _install_stubs(client)

        bootstrap = client.post("/api/v1/agents/bootstrap", headers=_auth_headers())
        assert bootstrap.status_code == 200

        created = client.post(
            "/api/v1/agents",
            headers=_auth_headers(),
            json={
                "kind": "specialist",
                "display_name": "Planning Specialist",
                "purpose": "planning_assist",
                "description": "Plan projects with concrete milestones",
                "system_prompt": "You are a planning specialist.",
                "skill_ids": ["specialist.topic_summary"],
                "room_ids": [],
                "auto_collect_enabled": False,
                "llm": {
                    "enabled": True,
                    "provider": "openrouter",
                    "model": "openai/gpt-4o-mini",
                    "api_key": "sk-test-key",
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_path": "/chat/completions",
                },
            },
        )
        assert created.status_code == 201
        created_payload = created.json()
        assert created_payload["llm"]["enabled"] is True
        assert created_payload["llm"]["provider"] == "openrouter"
        assert created_payload["llm"]["model"] == "openai/gpt-4o-mini"

        listed = client.get("/api/v1/agents", headers=_auth_headers())
        assert listed.status_code == 200
        specialist_rows = [row for row in listed.json()["agents"] if row["kind"] == "specialist"]
        assert len(specialist_rows) >= 1
        assert any(
            row.get("llm", {}).get("provider") == "openrouter"
            and row.get("llm", {}).get("model") == "openai/gpt-4o-mini"
            for row in specialist_rows
        )
