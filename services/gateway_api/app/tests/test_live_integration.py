from __future__ import annotations

import os
import random
import string
import time
from collections.abc import Generator

import httpx
import pytest

RUN_LIVE = os.getenv("PRISM_RUN_LIVE_TESTS") == "1"
GATEWAY_BASE_URL = os.getenv("PRISM_GATEWAY_BASE_URL", "http://localhost:8080/api/v1")

pytestmark = pytest.mark.skipif(
    not RUN_LIVE,
    reason="set PRISM_RUN_LIVE_TESTS=1 to run live integration tests",
)


def _suffix(length: int = 8) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def _request_json(
    client: httpx.Client,
    *,
    method: str,
    path: str,
    json_body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    response = client.request(
        method=method,
        url=f"{GATEWAY_BASE_URL.rstrip('/')}{path}",
        json=json_body,
        headers=headers,
    )
    try:
        payload = response.json() if response.content else {}
    except ValueError:
        payload = {"raw": response.text}
    assert isinstance(payload, dict)
    return response.status_code, payload


@pytest.fixture
def live_ctx() -> Generator[dict[str, str], None, None]:
    username = f"live_{_suffix()}"
    password = "Passw0rd!"

    with httpx.Client(timeout=20.0) as client:
        register: dict = {}
        code = 0
        for attempt in range(1, 6):
            code, register = _request_json(
                client,
                method="POST",
                path="/matrix/register",
                json_body={"username": username, "password": password},
            )
            if code in (200, 201):
                break
            if code == 502 and "429" in str(register.get("detail", "")):
                time.sleep(0.8 * attempt)
                continue
            break
        assert code in (200, 201), register
        user_id = register["user_id"]
        token = register["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        code, room = _request_json(
            client,
            method="POST",
            path="/matrix/rooms",
            headers=headers,
            json_body={
                "name": f"live-room-{_suffix(5)}",
                "preset": "private_chat",
                "invite": [],
            },
        )
        assert code == 201, room
        room_id = room["room_id"]

        for text in ["line one", "line two", "line three"]:
            code, send = _request_json(
                client,
                method="POST",
                path=f"/matrix/rooms/{room_id}/messages",
                headers=headers,
                json_body={"body": text},
            )
            assert code == 201, send

    yield {
        "user_id": user_id,
        "token": token,
        "room_id": room_id,
    }


def test_live_policy_allow(live_ctx: dict[str, str]) -> None:
    agent_id = f"agent.live.{_suffix(6)}"
    purpose = f"purpose_{_suffix(5)}"
    headers = {"Authorization": f"Bearer {live_ctx['token']}"}

    with httpx.Client(timeout=20.0) as client:
        code, grant = _request_json(
            client,
            method="POST",
            path="/policy/grants",
            headers=headers,
            json_body={
                "user_id": live_ctx["user_id"],
                "agent_id": agent_id,
                "data_category": "room_messages",
                "purpose": purpose,
                "rate_limit_per_minute": 100,
            },
        )
        assert code == 201, grant

        code, summary = _request_json(
            client,
            method="POST",
            path="/agent/summarize",
            headers=headers,
            json_body={
                "agent_id": agent_id,
                "room_id": live_ctx["room_id"],
                "purpose": purpose,
                "recent_message_limit": 20,
                "max_items": 5,
            },
        )
        assert code == 200, summary
        assert summary["decision"] == "allow"


def test_live_policy_deny_after_revoke(live_ctx: dict[str, str]) -> None:
    agent_id = f"agent.live.{_suffix(6)}"
    purpose = f"purpose_{_suffix(5)}"
    headers = {"Authorization": f"Bearer {live_ctx['token']}"}

    with httpx.Client(timeout=20.0) as client:
        code, grant = _request_json(
            client,
            method="POST",
            path="/policy/grants",
            headers=headers,
            json_body={
                "user_id": live_ctx["user_id"],
                "agent_id": agent_id,
                "data_category": "room_messages",
                "purpose": purpose,
                "rate_limit_per_minute": 100,
            },
        )
        assert code == 201, grant

        code, revoke = _request_json(
            client,
            method="POST",
            path="/policy/revoke",
            headers=headers,
            json_body={
                "user_id": live_ctx["user_id"],
                "grant_id": grant["grant_id"],
                "reason": "live_test_revoke",
            },
        )
        assert code == 200, revoke

        code, denied = _request_json(
            client,
            method="POST",
            path="/agent/summarize",
            headers=headers,
            json_body={
                "agent_id": agent_id,
                "room_id": live_ctx["room_id"],
                "purpose": purpose,
                "recent_message_limit": 20,
                "max_items": 5,
            },
        )
        assert code == 403, denied
        detail = denied.get("detail", {})
        assert isinstance(detail, dict)
        assert detail.get("reason") == "grant_revoked"


def test_live_audit_chain_verify(live_ctx: dict[str, str]) -> None:
    headers = {"Authorization": f"Bearer {live_ctx['token']}"}
    with httpx.Client(timeout=20.0) as client:
        code, verify = _request_json(
            client,
            method="GET",
            path=f"/audit/verify?user_id={live_ctx['user_id']}&limit=500",
            headers=headers,
        )
        assert code == 200, verify
        assert verify["verified"] is True
        assert int(verify["checked_events"]) >= 1


def test_live_agent_tool_call_writes_audit(live_ctx: dict[str, str]) -> None:
    agent_id = f"agent.live.{_suffix(6)}"
    purpose = f"purpose_{_suffix(5)}"
    headers = {"Authorization": f"Bearer {live_ctx['token']}"}

    with httpx.Client(timeout=20.0) as client:
        code, grant = _request_json(
            client,
            method="POST",
            path="/policy/grants",
            headers=headers,
            json_body={
                "user_id": live_ctx["user_id"],
                "agent_id": agent_id,
                "data_category": "room_messages",
                "purpose": purpose,
                "rate_limit_per_minute": 100,
            },
        )
        assert code == 201, grant

        code, summary = _request_json(
            client,
            method="POST",
            path="/agent/summarize",
            headers=headers,
            json_body={
                "agent_id": agent_id,
                "room_id": live_ctx["room_id"],
                "purpose": purpose,
                "recent_message_limit": 20,
                "max_items": 5,
            },
        )
        assert code == 200, summary

        code, events = _request_json(
            client,
            method="GET",
            path=f"/audit/events?actor_id={agent_id}&action_type=agent_summarize&limit=20",
            headers=headers,
        )
        assert code == 200, events
        assert len(events.get("events", [])) >= 1


def test_live_agent_summarize_and_send(live_ctx: dict[str, str]) -> None:
    agent_id = f"agent.live.{_suffix(6)}"
    purpose = f"purpose_{_suffix(5)}"
    headers = {"Authorization": f"Bearer {live_ctx['token']}"}

    with httpx.Client(timeout=20.0) as client:
        code, grant = _request_json(
            client,
            method="POST",
            path="/policy/grants",
            headers=headers,
            json_body={
                "user_id": live_ctx["user_id"],
                "agent_id": agent_id,
                "data_category": "room_messages",
                "purpose": purpose,
                "rate_limit_per_minute": 100,
            },
        )
        assert code == 201, grant

        code, sent = _request_json(
            client,
            method="POST",
            path="/agent/summarize-and-send",
            headers=headers,
            json_body={
                "agent_id": agent_id,
                "room_id": live_ctx["room_id"],
                "purpose": purpose,
                "recent_message_limit": 20,
                "max_items": 5,
            },
        )
        assert code == 200, sent
        assert sent.get("event_id")
        assert str(sent.get("bot_user_id", "")).startswith("@")

        code, events = _request_json(
            client,
            method="GET",
            path=f"/audit/events?actor_id={agent_id}&action_type=agent_send_summary_message&limit=20",
            headers=headers,
        )
        assert code == 200, events
        assert len(events.get("events", [])) >= 1


def test_live_matrix_send_sync_smoke(live_ctx: dict[str, str]) -> None:
    headers = {"Authorization": f"Bearer {live_ctx['token']}"}
    with httpx.Client(timeout=20.0) as client:
        code, send = _request_json(
            client,
            method="POST",
            path=f"/matrix/rooms/{live_ctx['room_id']}/messages",
            headers=headers,
            json_body={"body": "sync smoke"},
        )
        assert code == 201, send

        code, sync = _request_json(
            client,
            method="GET",
            path=f"/matrix/sync?room_id={live_ctx['room_id']}&timeout_ms=0",
            headers=headers,
        )
        assert code == 200, sync
        assert "next_batch" in sync
