from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.agent.runtime import summarize_messages
from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import ActorType, AuditEventCreate, DecisionType
from app.core.deps import get_immudb_client, get_opa_client
from app.policy.opa_client import OPAClient

router = APIRouter(prefix="/agent", tags=["agent"])


class SummarizeRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=255)
    user_id: str = Field(min_length=1, max_length=255)
    room_id: str = Field(min_length=1, max_length=255)
    purpose: str = Field(min_length=1, max_length=128)
    messages: list[str] = Field(default_factory=list, max_length=200)
    max_items: int = Field(default=8, ge=1, le=50)


class SummarizeResponse(BaseModel):
    status: str
    decision: str
    reason: str
    summary: str | None = None


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    payload: SummarizeRequest,
    http_request: Request,
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> SummarizeResponse:
    settings = http_request.app.state.settings
    rate_counter = http_request.app.state.agent_rate_counter
    rate_key = f"{payload.user_id}:{payload.agent_id}:{payload.room_id}:{payload.purpose}"
    request_count = rate_counter.increment_and_count(rate_key)

    policy_input = {
        "agent_id": payload.agent_id,
        "user_id": payload.user_id,
        "room_id": payload.room_id,
        "action": "read_messages",
        "data_category": "room_messages",
        "purpose": payload.purpose,
        "request_count_per_minute": request_count,
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    decision = await opa_client.evaluate(settings.opa_policy_path, policy_input)
    allow = bool(decision.get("allow", False))
    reason = str(decision.get("reason", "policy_decision_missing"))

    if not allow:
        deny_event = AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=payload.agent_id,
            action_type="agent_summarize",
            resource_type="tool",
            resource_id="summarize",
            decision=DecisionType.DENY,
            reason_code=reason,
            user_id=payload.user_id,
            room_id=payload.room_id,
            input_data={
                "message_count": len(payload.messages),
                "max_items": payload.max_items,
            },
            metadata={
                "purpose": payload.purpose,
                "policy_input": {
                    "request_count_per_minute": request_count,
                },
            },
        )
        try:
            await immudb_client.append_audit_event(deny_event)
        except ImmudbOperationError:
            pass

        raise HTTPException(
            status_code=403,
            detail={
                "status": "denied",
                "decision": "deny",
                "reason": reason,
            },
        )

    summary = summarize_messages(payload.messages, max_items=payload.max_items)
    allow_event = AuditEventCreate(
        actor_type=ActorType.AGENT,
        actor_id=payload.agent_id,
        action_type="agent_summarize",
        resource_type="tool",
        resource_id="summarize",
        decision=DecisionType.ALLOW,
        reason_code=reason,
        user_id=payload.user_id,
        room_id=payload.room_id,
        input_data={
            "message_count": len(payload.messages),
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

    try:
        await immudb_client.append_audit_event(allow_event)
    except ImmudbOperationError as exc:
        raise HTTPException(status_code=503, detail=f"agent_audit_failed: {exc}") from exc

    return SummarizeResponse(
        status="ok",
        decision="allow",
        reason=reason,
        summary=summary,
    )
