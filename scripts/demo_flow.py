from __future__ import annotations

import json
import random
import string
import urllib.error
import urllib.parse
import urllib.request

GW = "http://localhost:8080/api/v1"


def req_json(
    method: str, url: str, body: dict | None = None, token: str | None = None
) -> tuple[int, dict]:
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        payload = json.loads(raw) if raw else {}
        return exc.code, payload


def main() -> None:
    suffix = "".join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(8)
    )
    username = f"demo_{suffix}"
    password = "Passw0rd!"
    agent_id = "agent.summary.demo"
    purpose = "daily_summary"

    code, reg = req_json(
        "POST", f"{GW}/matrix/register", {"username": username, "password": password}
    )
    assert code in (200, 201), (code, reg)
    token = reg["access_token"]
    user_id = reg["user_id"]

    code, room = req_json(
        "POST",
        f"{GW}/matrix/rooms",
        {"name": f"demo-room-{suffix}", "invite": [], "preset": "private_chat"},
        token=token,
    )
    assert code == 201, (code, room)
    room_id = room["room_id"]

    for msg in ["demo hello", "demo policy", "demo audit"]:
        code, out = req_json(
            "POST",
            f"{GW}/matrix/rooms/{urllib.parse.quote(room_id, safe='')}/messages",
            {"body": msg},
            token=token,
        )
        assert code == 201, (code, out)

    code, grant = req_json(
        "POST",
        f"{GW}/policy/grants",
        {
            "user_id": user_id,
            "agent_id": agent_id,
            "data_category": "room_messages",
            "purpose": purpose,
            "rate_limit_per_minute": 20,
        },
        token=token,
    )
    assert code == 201, (code, grant)
    grant_id = grant["grant_id"]

    code, summary = req_json(
        "POST",
        f"{GW}/agent/summarize",
        {
            "agent_id": agent_id,
            "room_id": room_id,
            "purpose": purpose,
            "recent_message_limit": 30,
            "max_items": 8,
        },
        token=token,
    )
    assert code == 200 and summary.get("decision") == "allow", (code, summary)

    code, sent = req_json(
        "POST",
        f"{GW}/agent/summarize-and-send",
        {
            "agent_id": agent_id,
            "room_id": room_id,
            "purpose": purpose,
            "recent_message_limit": 30,
            "max_items": 8,
        },
        token=token,
    )
    assert code == 200 and isinstance(sent.get("event_id"), str), (code, sent)

    code, revoke = req_json(
        "POST",
        f"{GW}/policy/revoke",
        {"user_id": user_id, "grant_id": grant_id, "reason": "demo_revoke"},
        token=token,
    )
    assert code == 200, (code, revoke)

    code, denied = req_json(
        "POST",
        f"{GW}/agent/summarize",
        {
            "agent_id": agent_id,
            "room_id": room_id,
            "purpose": purpose,
            "recent_message_limit": 30,
            "max_items": 8,
        },
        token=token,
    )
    assert code == 403, (code, denied)

    query = urllib.parse.urlencode({"actor_id": agent_id, "limit": 100})
    code, verify = req_json("GET", f"{GW}/audit/verify?{query}", token=token)
    assert code == 200 and verify.get("verified") is True, (code, verify)

    print("DEMO_OK")
    print(
        json.dumps(
            {
                "user_id": user_id,
                "room_id": room_id,
                "grant_id": grant_id,
                "checked_events": verify.get("checked_events"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
