from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence

from app.audit.schemas import AuditEvent


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_hex(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compute_chain_hash(event_payload: dict[str, Any]) -> str:
    chain_input = {
        "event_id": event_payload["event_id"],
        "ts_ms": event_payload["ts_ms"],
        "actor_type": event_payload["actor_type"],
        "actor_id": event_payload["actor_id"],
        "action_type": event_payload["action_type"],
        "resource_type": event_payload["resource_type"],
        "resource_id": event_payload["resource_id"],
        "decision": event_payload["decision"],
        "reason_code": event_payload.get("reason_code"),
        "input_hash": event_payload["input_hash"],
        "output_hash": event_payload["output_hash"],
        "prev_hash": event_payload.get("prev_hash"),
        "signature": event_payload.get("signature"),
        "user_id": event_payload.get("user_id"),
        "room_id": event_payload.get("room_id"),
        "metadata": event_payload.get("metadata", {}),
    }
    return sha256_hex(chain_input)


def verify_chain(
    events: Sequence[AuditEvent],
    *,
    expected_first_prev_hash: str | None,
) -> tuple[bool, str | None, str | None]:
    if not events:
        return True, None, None

    first = events[0]
    if first.prev_hash != expected_first_prev_hash:
        return False, first.event_id, "first_prev_hash_mismatch"

    previous_chain_hash = expected_first_prev_hash
    for event in events:
        if event.prev_hash != previous_chain_hash:
            return False, event.event_id, "prev_hash_mismatch"

        calculated = compute_chain_hash(
            {
                "event_id": event.event_id,
                "ts_ms": event.ts_ms,
                "actor_type": event.actor_type.value,
                "actor_id": event.actor_id,
                "action_type": event.action_type,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "decision": event.decision.value,
                "reason_code": event.reason_code,
                "input_hash": event.input_hash,
                "output_hash": event.output_hash,
                "prev_hash": event.prev_hash,
                "signature": event.signature,
                "user_id": event.user_id,
                "room_id": event.room_id,
                "metadata": event.metadata,
            }
        )
        if calculated != event.chain_hash:
            return False, event.event_id, "chain_hash_mismatch"

        previous_chain_hash = event.chain_hash

    return True, None, None
