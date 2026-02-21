from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import (
    ActorType,
    AuditEvent,
    AuditEventCreate,
    AuditListResponse,
    AuditQuery,
    AuditVerifyResponse,
    DecisionType,
)
from app.core.deps import AuthenticatedUser, get_authenticated_user, get_immudb_client

router = APIRouter(prefix="/audit", tags=["audit"])


def _scoped_user_id(
    *,
    requested_user_id: str | None,
    authenticated_user: AuthenticatedUser,
) -> str:
    if requested_user_id is not None and requested_user_id != authenticated_user.user_id:
        raise HTTPException(status_code=403, detail="user_id_mismatch")
    return requested_user_id or authenticated_user.user_id


@router.post("/events", response_model=AuditEvent, status_code=201)
async def create_audit_event(
    request: AuditEventCreate,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> AuditEvent:
    if request.user_id is not None and request.user_id != authenticated_user.user_id:
        raise HTTPException(status_code=403, detail="user_id_mismatch")
    if request.actor_type == ActorType.USER and request.actor_id != authenticated_user.user_id:
        raise HTTPException(status_code=403, detail="actor_id_mismatch")

    scoped_request = request
    if request.user_id is None:
        scoped_request = request.model_copy(update={"user_id": authenticated_user.user_id})

    try:
        return await immudb_client.append_audit_event(scoped_request)
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
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> AuditListResponse:
    scoped_user_id = _scoped_user_id(
        requested_user_id=user_id,
        authenticated_user=authenticated_user,
    )

    try:
        query = AuditQuery(
            actor_id=actor_id,
            user_id=scoped_user_id,
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
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> AuditVerifyResponse:
    scoped_user_id = _scoped_user_id(
        requested_user_id=user_id,
        authenticated_user=authenticated_user,
    )

    try:
        query = AuditQuery(
            actor_id=actor_id,
            user_id=scoped_user_id,
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
