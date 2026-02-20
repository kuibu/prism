from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.audit.immudb_client import ImmudbOperationError
from app.audit.schemas import ActorType, AuditEventCreate, DecisionType
from app.matrix.client import MatrixClientError

router = APIRouter(prefix="/matrix", tags=["matrix"])


@router.get("/sync")
async def matrix_sync(
    request: Request,
    access_token: str = Query(min_length=1),
    user_id: str | None = Query(default=None),
    room_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    timeout_ms: int = Query(default=0, ge=0, le=60000),
    full_state: bool = Query(default=False),
) -> dict:
    matrix_client = request.app.state.matrix_client
    immudb_client = request.app.state.immudb_client

    try:
        payload = await matrix_client.sync(
            access_token=access_token,
            since=since,
            timeout_ms=timeout_ms,
            full_state=full_state,
        )
    except MatrixClientError as exc:
        if user_id is not None:
            deny_event = AuditEventCreate(
                actor_type=ActorType.USER,
                actor_id=user_id,
                action_type="matrix_sync",
                resource_type="room",
                resource_id=room_id or "all_rooms",
                decision=DecisionType.DENY,
                reason_code="matrix_sync_failed",
                user_id=user_id,
                room_id=room_id,
                metadata={"since": since, "timeout_ms": timeout_ms},
            )
            try:
                await immudb_client.append_audit_event(deny_event)
            except ImmudbOperationError:
                pass

        raise HTTPException(status_code=502, detail=f"matrix_sync_failed: {exc}") from exc

    if user_id is not None:
        allow_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=user_id,
            action_type="matrix_sync",
            resource_type="room",
            resource_id=room_id or "all_rooms",
            decision=DecisionType.ALLOW,
            reason_code="sync_ok",
            user_id=user_id,
            room_id=room_id,
            metadata={"since": since, "timeout_ms": timeout_ms},
        )
        try:
            await immudb_client.append_audit_event(allow_event)
        except ImmudbOperationError:
            pass

    return payload
