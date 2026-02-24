from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.agent.assistant_models import MemorySourceType
from app.agent.memory_backends import (
    OPADocumentMemoryBackend,
    OpenVikingConfig,
    OpenVikingMemoryBackend,
)


class _StubOPAClient:
    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    async def get_document(self, path: str) -> dict[str, Any]:
        return self.docs.get(path, {})

    async def put_document(self, path: str, payload: dict[str, Any]) -> None:
        self.docs[path] = dict(payload)


class _DummyResponse:
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


class _DummyOpenVikingClient:
    def __init__(self, *, fail_search: bool = False) -> None:
        self.fail_search = fail_search
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    async def __aenter__(self) -> _DummyOpenVikingClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        _ = exc_type, exc, tb
        return False

    async def request(
        self,
        method: str,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> _DummyResponse:
        self.calls.append((method, endpoint, json))
        if endpoint == "/api/v1/sessions":
            return _DummyResponse({"status": "ok", "result": {"session_id": "sess_demo_1"}})
        if endpoint.endswith("/messages"):
            return _DummyResponse(
                {
                    "status": "ok",
                    "result": {"session_id": "sess_demo_1", "message_count": len(self.calls)},
                }
            )
        if endpoint.endswith("/commit"):
            return _DummyResponse(
                {
                    "status": "ok",
                    "result": {"status": "committed", "memories_extracted": 1},
                }
            )
        if endpoint == "/api/v1/search/find":
            if self.fail_search:
                raise httpx.RequestError("openviking_search_unavailable")
            target = (json or {}).get("target_uri")
            if target == "viking://user/memories":
                return _DummyResponse(
                    {
                        "status": "ok",
                        "result": {
                            "memories": [
                                {
                                    "context_type": "memory",
                                    "uri": "viking://user/memories/events/phoenix_launch.md",
                                    "abstract": "phoenix launch checklist and risks",
                                }
                            ],
                            "resources": [],
                            "skills": [],
                            "total": 1,
                        },
                    }
                )
            return _DummyResponse(
                {
                    "status": "ok",
                    "result": {
                        "memories": [],
                        "resources": [],
                        "skills": [],
                        "total": 0,
                    },
                }
            )
        return _DummyResponse({"status": "ok", "result": {}})


@pytest.mark.asyncio
async def test_openviking_backend_mirrors_memory_via_session_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opa_stub = _StubOPAClient()
    local_backend = OPADocumentMemoryBackend(opa_client=opa_stub, opa_data_root="/v1/data/prism")
    dummy_client = _DummyOpenVikingClient()
    monkeypatch.setattr(
        "app.agent.memory_backends.httpx.AsyncClient",
        lambda **kwargs: dummy_client,
    )
    backend = OpenVikingMemoryBackend(
        primary=local_backend,
        config=OpenVikingConfig(base_url="http://openviking.local:1933"),
    )

    entry_a = await backend.create_memory_entry(
        user_id="@alice:localhost",
        agent_id="agent.secretary.alice",
        source_type=MemorySourceType.MATRIX_ROOM_MESSAGE,
        source_id="$evt-001",
        content="今天需要确认 phoenix 发布窗口。",
        room_id="!room:localhost",
        sender_id="@bob:localhost",
        tags=["release", "phoenix"],
        importance=0.8,
        metadata={"source": "test"},
    )
    entry_b = await backend.create_memory_entry(
        user_id="@alice:localhost",
        agent_id="agent.secretary.alice",
        source_type=MemorySourceType.MATRIX_ROOM_MESSAGE,
        source_id="$evt-002",
        content="请把风险清单整理给我。",
        room_id="!room:localhost",
        sender_id="@bob:localhost",
        tags=["risk"],
        importance=0.7,
        metadata={"source": "test"},
    )

    append_result = await backend.append_memory_entries(
        user_id="@alice:localhost",
        agent_id="agent.secretary.alice",
        entries=[entry_a, entry_b],
    )

    assert append_result.stored_count == 2
    assert append_result.skipped_count == 0
    assert any(
        endpoint == "/api/v1/sessions"
        and isinstance(payload, dict)
        and payload.get("user") == "@alice:localhost"
        for _, endpoint, payload in dummy_client.calls
    )
    assert any(endpoint.endswith("/commit") for _, endpoint, _ in dummy_client.calls)

    rows = await backend.list_memory_entries(
        user_id="@alice:localhost",
        agent_id="agent.secretary.alice",
        limit=10,
    )
    assert len(rows) == 2
    assert rows[0].source_id == "$evt-002"
    assert rows[1].source_id == "$evt-001"


@pytest.mark.asyncio
async def test_openviking_backend_search_falls_back_to_local_when_remote_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opa_stub = _StubOPAClient()
    local_backend = OPADocumentMemoryBackend(opa_client=opa_stub, opa_data_root="/v1/data/prism")
    dummy_client = _DummyOpenVikingClient(fail_search=True)
    monkeypatch.setattr(
        "app.agent.memory_backends.httpx.AsyncClient",
        lambda **kwargs: dummy_client,
    )
    backend = OpenVikingMemoryBackend(
        primary=local_backend,
        config=OpenVikingConfig(base_url="http://openviking.local:1933"),
    )

    entry = await backend.create_memory_entry(
        user_id="@alice:localhost",
        agent_id="agent.secretary.alice",
        source_type=MemorySourceType.MATRIX_ROOM_MESSAGE,
        source_id="$evt-003",
        content="phoenix 发布窗口需要在今晚 20:00 前确认。",
        room_id="!room:localhost",
        sender_id="@bob:localhost",
        tags=["phoenix", "release"],
        importance=0.9,
        metadata={"source": "test"},
    )
    await backend.append_memory_entries(
        user_id="@alice:localhost",
        agent_id="agent.secretary.alice",
        entries=[entry],
    )

    hits = await backend.search_memory_entries(
        user_id="@alice:localhost",
        agent_id="agent.secretary.alice",
        query="phoenix 发布",
        limit=5,
    )
    assert len(hits) == 1
    assert "phoenix" in hits[0].content.lower()


@pytest.mark.asyncio
async def test_openviking_backend_mirror_skips_duplicate_source_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opa_stub = _StubOPAClient()
    local_backend = OPADocumentMemoryBackend(opa_client=opa_stub, opa_data_root="/v1/data/prism")
    dummy_client = _DummyOpenVikingClient()
    monkeypatch.setattr(
        "app.agent.memory_backends.httpx.AsyncClient",
        lambda **kwargs: dummy_client,
    )
    backend = OpenVikingMemoryBackend(
        primary=local_backend,
        config=OpenVikingConfig(base_url="http://openviking.local:1933"),
    )

    entry_a = await backend.create_memory_entry(
        user_id="@alice:localhost",
        agent_id="agent.specialist.memory",
        source_type=MemorySourceType.MANUAL_NOTE,
        source_id="manual-note-1",
        content="第一条记忆",
        room_id=None,
        sender_id="@alice:localhost",
        tags=["manual"],
        importance=0.6,
        metadata={},
    )
    entry_dup = await backend.create_memory_entry(
        user_id="@alice:localhost",
        agent_id="agent.specialist.memory",
        source_type=MemorySourceType.MANUAL_NOTE,
        source_id="manual-note-1",
        content="重复记忆，不应重复镜像",
        room_id=None,
        sender_id="@alice:localhost",
        tags=["manual"],
        importance=0.5,
        metadata={},
    )

    result = await backend.append_memory_entries(
        user_id="@alice:localhost",
        agent_id="agent.specialist.memory",
        entries=[entry_a, entry_dup],
    )

    message_calls = [item for item in dummy_client.calls if item[1].endswith("/messages")]
    assert result.stored_count == 1
    assert result.skipped_count == 1
    assert len(message_calls) == 1
