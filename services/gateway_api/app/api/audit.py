from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import (
    AuditEvent,
    AuditEventCreate,
    AuditListResponse,
    AuditQuery,
    AuditVerifyResponse,
    DecisionType,
)
from app.core.deps import get_immudb_client

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/events", response_model=AuditEvent, status_code=201)
async def create_audit_event(
    request: AuditEventCreate,
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> AuditEvent:
    try:
        return await immudb_client.append_audit_event(request)
    except ImmudbOperationError as exc:
        raise HTTPException(status_code=503, detail=f"audit_write_failed: {exc}") from exc


@router.get("/events", response_model=AuditListResponse)
async def query_audit_events(
    actor_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    room_id: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    decision: DecisionType | None = Query(default=None),
    start_ts: datetime | None = Query(default=None),
    end_ts: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> AuditListResponse:
    try:
        query = AuditQuery(
            actor_id=actor_id,
            user_id=user_id,
            room_id=room_id,
            action_type=action_type,
            decision=decision,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
        )
        events = await immudb_client.query_audit_events(query)
        return AuditListResponse(events=events)
    except ImmudbOperationError as exc:
        raise HTTPException(status_code=503, detail=f"audit_query_failed: {exc}") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/verify", response_model=AuditVerifyResponse)
async def verify_audit_chain(
    actor_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    room_id: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    decision: DecisionType | None = Query(default=None),
    start_ts: datetime | None = Query(default=None),
    end_ts: datetime | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> AuditVerifyResponse:
    try:
        query = AuditQuery(
            actor_id=actor_id,
            user_id=user_id,
            room_id=room_id,
            action_type=action_type,
            decision=decision,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
        )
        return await immudb_client.verify_audit_chain(query)
    except ImmudbOperationError as exc:
        raise HTTPException(status_code=503, detail=f"audit_verify_failed: {exc}") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
