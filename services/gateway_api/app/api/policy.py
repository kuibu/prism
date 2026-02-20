from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError

from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import ActorType, AuditEventCreate, DecisionType
from app.core.deps import (
    AuthenticatedUser,
    get_authenticated_user,
    get_immudb_client,
    get_opa_client,
)
from app.policy.models import (
    GrantCreateRequest,
    GrantListResponse,
    GrantRecord,
    GrantStatus,
    RevokeRequest,
    RevokeResponse,
)
from app.policy.opa_client import OPAClient, OPAClientError, OPANotFoundError

router = APIRouter(prefix="/policy", tags=["policy"])


def _grants_root_path(settings: object) -> str:
    data_root = str(getattr(settings, "opa_data_root", "/v1/data/prism")).rstrip("/")
    return f"{data_root}/grants"


def _grant_document_path(settings: object, grant_id: str) -> str:
    return f"{_grants_root_path(settings)}/{grant_id}"


@router.get("/grants", response_model=GrantListResponse)
async def list_grants(
    http_request: Request,
    user_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    include_revoked: bool = Query(default=False),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> GrantListResponse:
    settings = http_request.app.state.settings
    effective_user_id = user_id or authenticated_user.user_id
    if user_id is not None and user_id != authenticated_user.user_id:
        raise HTTPException(status_code=403, detail="user_id_mismatch")

    try:
        raw_grants = await opa_client.get_document(_grants_root_path(settings))
    except OPANotFoundError:
        raw_grants = {}
    except OPAClientError as exc:
        raise HTTPException(status_code=503, detail=f"policy_query_failed: {exc}") from exc

    grants: list[GrantRecord] = []
    for value in raw_grants.values():
        if not isinstance(value, dict):
            continue
        try:
            grant = GrantRecord.model_validate(value)
        except ValidationError:
            continue
        if grant.user_id != effective_user_id:
            continue
        if agent_id is not None and grant.agent_id != agent_id:
            continue
        if not include_revoked and grant.status == GrantStatus.REVOKED:
            continue
        grants.append(grant)

    grants.sort(key=lambda item: item.created_at, reverse=True)
    return GrantListResponse(grants=grants)


@router.post("/grants", response_model=GrantRecord, status_code=201)
async def create_grant(
    request: GrantCreateRequest,
    http_request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> GrantRecord:
    if request.user_id != authenticated_user.user_id:
        raise HTTPException(status_code=403, detail="user_id_mismatch")

    if (
        request.time_window_start is not None
        and request.time_window_end is not None
        and request.time_window_end < request.time_window_start
    ):
        raise HTTPException(status_code=422, detail="invalid_time_window")

    settings = http_request.app.state.settings
    created = GrantRecord(
        grant_id=f"grant_{uuid4().hex}",
        user_id=request.user_id,
        agent_id=request.agent_id,
        data_category=request.data_category,
        purpose=request.purpose,
        time_window_start=request.time_window_start,
        time_window_end=request.time_window_end,
        rate_limit_per_minute=request.rate_limit_per_minute,
        status=GrantStatus.ACTIVE,
        created_at=datetime.now(UTC),
        metadata=request.metadata,
    )
    grant_path = _grant_document_path(settings, created.grant_id)

    try:
        await opa_client.put_document(grant_path, created.model_dump(mode="json"))
    except OPAClientError as exc:
        raise HTTPException(status_code=503, detail=f"policy_store_failed: {exc}") from exc

    audit_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=request.user_id,
        action_type="policy_grant",
        resource_type="policy",
        resource_id=created.grant_id,
        decision=DecisionType.ALLOW,
        reason_code="policy_granted",
        user_id=request.user_id,
        metadata={
            "agent_id": request.agent_id,
            "data_category": request.data_category.value,
            "purpose": request.purpose,
            "rate_limit_per_minute": request.rate_limit_per_minute,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )

    try:
        await immudb_client.append_audit_event(audit_event)
    except ImmudbOperationError as exc:
        try:
            await opa_client.delete_document(grant_path)
        except OPAClientError:
            pass
        raise HTTPException(status_code=503, detail=f"policy_audit_failed: {exc}") from exc

    return created


@router.get("/revoke", response_model=RevokeResponse)
async def revoke_help() -> RevokeResponse:
    return RevokeResponse(
        grant_id="",
        status=GrantStatus.REVOKED,
        reason="use POST /api/v1/policy/revoke with {user_id, grant_id}",
    )


@router.post("/revoke", response_model=RevokeResponse)
async def revoke_grant(
    request: RevokeRequest,
    http_request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> RevokeResponse:
    if request.user_id != authenticated_user.user_id:
        raise HTTPException(status_code=403, detail="user_id_mismatch")

    settings = http_request.app.state.settings
    grant_path = _grant_document_path(settings, request.grant_id)

    try:
        raw_grant = await opa_client.get_document(grant_path)
    except OPANotFoundError:
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=request.user_id,
            action_type="policy_revoke",
            resource_type="policy",
            resource_id=request.grant_id,
            decision=DecisionType.DENY,
            reason_code="grant_not_found",
            user_id=request.user_id,
            metadata={"revoke_reason": request.reason},
        )
        try:
            await immudb_client.append_audit_event(deny_event)
        except ImmudbOperationError:
            pass
        raise HTTPException(status_code=404, detail="grant_not_found") from None
    except OPAClientError as exc:
        raise HTTPException(status_code=503, detail=f"policy_query_failed: {exc}") from exc

    try:
        existing = GrantRecord.model_validate(raw_grant)
    except ValidationError as exc:
        raise HTTPException(status_code=503, detail=f"policy_data_invalid: {exc}") from exc

    if existing.user_id != request.user_id:
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=request.user_id,
            action_type="policy_revoke",
            resource_type="policy",
            resource_id=request.grant_id,
            decision=DecisionType.DENY,
            reason_code="grant_owner_mismatch",
            user_id=request.user_id,
            metadata={"revoke_reason": request.reason},
        )
        try:
            await immudb_client.append_audit_event(deny_event)
        except ImmudbOperationError:
            pass
        raise HTTPException(status_code=403, detail="grant_owner_mismatch")

    updated_metadata = dict(existing.metadata)
    if request.reason is not None:
        updated_metadata["revoke_reason"] = request.reason

    updated = existing.model_copy(
        update={
            "status": GrantStatus.REVOKED,
            "revoked_at": existing.revoked_at or datetime.now(UTC),
            "metadata": updated_metadata,
        }
    )

    try:
        await opa_client.put_document(grant_path, updated.model_dump(mode="json"))
    except OPAClientError as exc:
        raise HTTPException(status_code=503, detail=f"policy_store_failed: {exc}") from exc

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=request.user_id,
        action_type="policy_revoke",
        resource_type="policy",
        resource_id=request.grant_id,
        decision=DecisionType.ALLOW,
        reason_code="policy_revoked",
        user_id=request.user_id,
        metadata={"revoke_reason": request.reason},
    )
    try:
        await immudb_client.append_audit_event(allow_event)
    except ImmudbOperationError as exc:
        try:
            await opa_client.put_document(grant_path, existing.model_dump(mode="json"))
        except OPAClientError:
            pass
        raise HTTPException(status_code=503, detail=f"policy_audit_failed: {exc}") from exc

    return RevokeResponse(
        grant_id=request.grant_id,
        status=updated.status,
        reason=request.reason or "revoked",
    )
