from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.agent.runtime import summarize_messages
from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import ActorType, AuditEventCreate, DecisionType
from app.core.deps import (
    AuthenticatedUser,
    get_authenticated_user,
    get_immudb_client,
    get_opa_client,
)
from app.matrix.client import MatrixClientError
from app.policy.opa_client import OPAClient

router = APIRouter(prefix="/agent", tags=["agent"])


class SummarizeRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=255)
    room_id: str = Field(min_length=1, max_length=255)
    purpose: str = Field(min_length=1, max_length=128)
    recent_message_limit: int = Field(default=30, ge=1, le=200)
    max_items: int = Field(default=8, ge=1, le=50)


class SummarizeResponse(BaseModel):
    status: str
    decision: str
    reason: str
    message_count: int = 0
    summary: str | None = None


async def _write_audit_or_raise(
    *,
    immudb_client: ImmudbClient,
    event: AuditEventCreate,
) -> None:
    try:
        await immudb_client.append_audit_event(event)
    except ImmudbOperationError as exc:
        raise HTTPException(status_code=503, detail=f"agent_audit_failed: {exc}") from exc


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    payload: SummarizeRequest,
    http_request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> SummarizeResponse:
    settings = http_request.app.state.settings
    rate_counter = http_request.app.state.agent_rate_counter
    matrix_client = http_request.app.state.matrix_client
    user_id = authenticated_user.user_id
    rate_key = f"{user_id}:{payload.agent_id}:{payload.room_id}:{payload.purpose}"
    request_count = rate_counter.increment_and_count(rate_key)

    policy_input = {
        "agent_id": payload.agent_id,
        "user_id": user_id,
        "room_id": payload.room_id,
        "action": "read_messages",
        "data_category": "room_messages",
        "purpose": payload.purpose,
        "request_count_per_minute": request_count,
        "ts": datetime.now(UTC).isoformat(),
    }

    decision = await opa_client.evaluate(settings.opa_policy_path, policy_input)
    allow = bool(decision.get("allow", False))
    reason = str(decision.get("reason", "policy_decision_missing"))

    if not allow:
        deny_event = AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=payload.agent_id,
            action_type="agent_read_room_messages",
            resource_type="room",
            resource_id=payload.room_id,
            decision=DecisionType.DENY,
            reason_code=reason,
            user_id=user_id,
            room_id=payload.room_id,
            input_data={"requested_limit": payload.recent_message_limit},
            metadata={
                "purpose": payload.purpose,
                "policy_input": {
                    "request_count_per_minute": request_count,
                },
            },
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)

        raise HTTPException(
            status_code=403,
            detail={
                "status": "denied",
                "decision": "deny",
                "reason": reason,
            },
        )

    try:
        messages = await matrix_client.read_room_messages(
            access_token=authenticated_user.access_token,
            room_id=payload.room_id,
            limit=payload.recent_message_limit,
        )
    except MatrixClientError as exc:
        read_fail_event = AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=payload.agent_id,
            action_type="agent_read_room_messages",
            resource_type="room",
            resource_id=payload.room_id,
            decision=DecisionType.DENY,
            reason_code="matrix_read_messages_failed",
            user_id=user_id,
            room_id=payload.room_id,
            input_data={"requested_limit": payload.recent_message_limit},
            metadata={"error": str(exc), "purpose": payload.purpose},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=read_fail_event)
        raise HTTPException(status_code=502, detail=f"matrix_read_messages_failed: {exc}") from exc

    read_allow_event = AuditEventCreate(
        actor_type=ActorType.AGENT,
        actor_id=payload.agent_id,
        action_type="agent_read_room_messages",
        resource_type="room",
        resource_id=payload.room_id,
        decision=DecisionType.ALLOW,
        reason_code=reason,
        user_id=user_id,
        room_id=payload.room_id,
        output_data={"message_count": len(messages)},
        metadata={
            "purpose": payload.purpose,
            "requested_limit": payload.recent_message_limit,
            "policy_input": {"request_count_per_minute": request_count},
        },
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=read_allow_event)

    summary = summarize_messages(messages, max_items=payload.max_items)
    allow_event = AuditEventCreate(
        actor_type=ActorType.AGENT,
        actor_id=payload.agent_id,
        action_type="agent_summarize",
        resource_type="tool",
        resource_id="summarize",
        decision=DecisionType.ALLOW,
        reason_code=reason,
        user_id=user_id,
        room_id=payload.room_id,
        input_data={
            "message_count": len(messages),
            "max_items": payload.max_items,
        },
        output_data={"summary_length": len(summary)},
        metadata={
            "purpose": payload.purpose,
            "policy_input": {
                "request_count_per_minute": request_count,
            },
        },
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)

    return SummarizeResponse(
        status="ok",
        decision="allow",
        reason=reason,
        message_count=len(messages),
        summary=summary,
    )
