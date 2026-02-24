from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import ActorType, AuditEventCreate, DecisionType
from app.bridge.models import (
    BridgeConnectorCreateRequest,
    BridgeConnectorListResponse,
    BridgeConnectorUpdateRequest,
    BridgeDirection,
    BridgeInboundRelayRequest,
    BridgeInboundRelayResponse,
    BridgeOutboundPreviewItem,
    BridgeOutboundPreviewRequest,
    BridgeOutboundPreviewResponse,
    BridgePlatform,
    BridgePlatformDescriptor,
    BridgePlatformListResponse,
    BridgeRoomLinkCreateRequest,
    BridgeRoomLinkListResponse,
    BridgeRoomLinkUpdateRequest,
)
from app.bridge.store import (
    BridgeConflictError,
    BridgeNotFoundError,
    BridgeStoreError,
    OPABridgeStore,
)
from app.core.deps import (
    AuthenticatedUser,
    get_authenticated_user,
    get_immudb_client,
    get_opa_client,
)
from app.matrix.client import MatrixClient, MatrixClientError
from app.policy.opa_client import OPAClient

router = APIRouter(prefix="/bridges", tags=["bridges"])


PLATFORM_DESCRIPTORS: list[BridgePlatformDescriptor] = [
    BridgePlatformDescriptor(
        platform=BridgePlatform.SLACK,
        display_name="Slack",
        direction_support=[BridgeDirection.BIDIRECTIONAL],
        notes="Use bot token + signing secret; ideal for workspace channels.",
    ),
    BridgePlatformDescriptor(
        platform=BridgePlatform.TELEGRAM,
        display_name="Telegram",
        direction_support=[BridgeDirection.BIDIRECTIONAL],
        notes="Use bot token and target chats/groups.",
    ),
    BridgePlatformDescriptor(
        platform=BridgePlatform.DISCORD,
        display_name="Discord",
        direction_support=[BridgeDirection.BIDIRECTIONAL],
        notes="Supports guild channels with bot applications.",
    ),
    BridgePlatformDescriptor(
        platform=BridgePlatform.WECOM,
        display_name="WeCom",
        direction_support=[BridgeDirection.BIDIRECTIONAL],
        notes="Enterprise WeCom webhooks and app messages.",
    ),
    BridgePlatformDescriptor(
        platform=BridgePlatform.WHATSAPP,
        display_name="WhatsApp",
        direction_support=[BridgeDirection.INBOUND, BridgeDirection.OUTBOUND],
        notes="Typically integrated through business providers.",
    ),
    BridgePlatformDescriptor(
        platform=BridgePlatform.SIGNAL,
        display_name="Signal",
        direction_support=[BridgeDirection.INBOUND, BridgeDirection.OUTBOUND],
        notes="Connector support varies by deployment model.",
    ),
    BridgePlatformDescriptor(
        platform=BridgePlatform.CUSTOM,
        display_name="Custom Webhook",
        direction_support=[BridgeDirection.BIDIRECTIONAL],
        notes="Bring-your-own transport adapter over webhook/HTTP.",
    ),
]


def _store(request: Request, opa_client: OPAClient) -> OPABridgeStore:
    settings = request.app.state.settings
    return OPABridgeStore(
        opa_client=opa_client,
        opa_data_root=settings.opa_data_root,
    )


def _matrix_client(request: Request) -> MatrixClient:
    return cast(MatrixClient, request.app.state.matrix_client)


def _map_matrix_error_status(exc: MatrixClientError) -> int:
    status_code = exc.status_code
    if isinstance(status_code, int):
        if status_code in {400, 401, 403, 404, 409, 429}:
            return status_code
        if 500 <= status_code < 600:
            return 502
    lowered = str(exc).lower()
    if "timed out" in lowered or "timeout" in lowered:
        return 504
    return 502


async def _append_audit(
    *,
    immudb_client: ImmudbClient,
    event: AuditEventCreate,
) -> None:
    try:
        await immudb_client.append_audit_event(event)
    except ImmudbOperationError as exc:
        raise HTTPException(status_code=503, detail=f"audit_write_failed: {exc}") from exc


@router.get("/platforms", response_model=BridgePlatformListResponse)
async def list_bridge_platforms() -> BridgePlatformListResponse:
    return BridgePlatformListResponse(platforms=PLATFORM_DESCRIPTORS)


@router.get("/connectors", response_model=BridgeConnectorListResponse)
async def list_connectors(
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> BridgeConnectorListResponse:
    store = _store(request, opa_client)
    try:
        connectors = await store.list_connectors(authenticated_user.user_id)
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc
    return BridgeConnectorListResponse(connectors=connectors)


@router.post("/connectors", status_code=201, response_model=dict[str, Any])
async def create_connector(
    payload: BridgeConnectorCreateRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    store = _store(request, opa_client)
    try:
        connector = await store.create_connector(user_id=authenticated_user.user_id, request=payload)
    except BridgeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="bridge_connector_upsert",
            resource_type="bridge_connector",
            resource_id=connector.connector_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_connector_created",
            user_id=authenticated_user.user_id,
            metadata={"platform": connector.platform.value, "direction": connector.direction.value},
        ),
    )
    return connector.model_dump(mode="json")


@router.patch("/connectors/{connector_id}", response_model=dict[str, Any])
async def update_connector(
    connector_id: str,
    payload: BridgeConnectorUpdateRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    store = _store(request, opa_client)
    try:
        connector = await store.update_connector(
            user_id=authenticated_user.user_id,
            connector_id=connector_id.strip(),
            request=payload,
        )
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="bridge_connector_upsert",
            resource_type="bridge_connector",
            resource_id=connector.connector_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_connector_updated",
            user_id=authenticated_user.user_id,
            metadata={"enabled": connector.enabled},
        ),
    )
    return connector.model_dump(mode="json")


@router.delete("/connectors/{connector_id}", status_code=204)
async def delete_connector(
    connector_id: str,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> None:
    normalized_id = connector_id.strip()
    store = _store(request, opa_client)
    try:
        await store.delete_connector(user_id=authenticated_user.user_id, connector_id=normalized_id)
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="bridge_connector_delete",
            resource_type="bridge_connector",
            resource_id=normalized_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_connector_deleted",
            user_id=authenticated_user.user_id,
        ),
    )


@router.get("/links", response_model=BridgeRoomLinkListResponse)
async def list_links(
    request: Request,
    connector_id: str | None = Query(default=None),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> BridgeRoomLinkListResponse:
    normalized_connector_id = connector_id.strip() if isinstance(connector_id, str) else None
    store = _store(request, opa_client)
    try:
        links = await store.list_links(
            user_id=authenticated_user.user_id,
            connector_id=normalized_connector_id if normalized_connector_id else None,
        )
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc
    return BridgeRoomLinkListResponse(links=links)


@router.post("/links", status_code=201, response_model=dict[str, Any])
async def create_link(
    payload: BridgeRoomLinkCreateRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    store = _store(request, opa_client)
    try:
        link = await store.create_link(user_id=authenticated_user.user_id, request=payload)
    except BridgeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="bridge_link_upsert",
            resource_type="bridge_link",
            resource_id=link.link_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_link_created",
            user_id=authenticated_user.user_id,
            room_id=link.room_id,
            metadata={
                "connector_id": link.connector_id,
                "external_room_id": link.external_room_id,
            },
        ),
    )
    return link.model_dump(mode="json")


@router.patch("/links/{link_id}", response_model=dict[str, Any])
async def update_link(
    link_id: str,
    payload: BridgeRoomLinkUpdateRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    store = _store(request, opa_client)
    try:
        link = await store.update_link(
            user_id=authenticated_user.user_id,
            link_id=link_id.strip(),
            request=payload,
        )
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="bridge_link_upsert",
            resource_type="bridge_link",
            resource_id=link.link_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_link_updated",
            user_id=authenticated_user.user_id,
            room_id=link.room_id,
            metadata={"enabled": link.enabled},
        ),
    )
    return link.model_dump(mode="json")


@router.delete("/links/{link_id}", status_code=204)
async def delete_link(
    link_id: str,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> None:
    normalized_id = link_id.strip()
    store = _store(request, opa_client)
    try:
        await store.delete_link(user_id=authenticated_user.user_id, link_id=normalized_id)
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="bridge_link_delete",
            resource_type="bridge_link",
            resource_id=normalized_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_link_deleted",
            user_id=authenticated_user.user_id,
        ),
    )


@router.post("/relay/inbound", response_model=BridgeInboundRelayResponse)
async def relay_inbound(
    payload: BridgeInboundRelayRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> BridgeInboundRelayResponse:
    store = _store(request, opa_client)
    matrix_client = _matrix_client(request)
    normalized_connector_id = payload.connector_id.strip()
    normalized_external_room_id = payload.external_room_id.strip()
    normalized_room_override = payload.room_id.strip() if isinstance(payload.room_id, str) else ""

    try:
        connector = await store.get_connector(authenticated_user.user_id, normalized_connector_id)
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    if not connector.enabled:
        raise HTTPException(status_code=409, detail="bridge_connector_disabled")

    try:
        links = await store.list_links(
            user_id=authenticated_user.user_id,
            connector_id=normalized_connector_id,
        )
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    matched_link = None
    for link in links:
        if not link.enabled:
            continue
        if link.external_room_id != normalized_external_room_id:
            continue
        if normalized_room_override != "" and link.room_id != normalized_room_override:
            continue
        matched_link = link
        break

    if matched_link is None and normalized_room_override == "":
        raise HTTPException(status_code=404, detail="bridge_link_not_found_for_external_room")

    room_id = normalized_room_override or (matched_link.room_id if matched_link is not None else "")
    if room_id == "":
        raise HTTPException(status_code=422, detail="bridge_target_room_required")

    relay_prefix = (
        matched_link.relay_prefix
        if matched_link is not None and matched_link.relay_prefix.strip() != ""
        else "[Bridge]"
    )
    external_label = (
        matched_link.external_room_name
        if matched_link is not None
        and isinstance(matched_link.external_room_name, str)
        and matched_link.external_room_name.strip() != ""
        else normalized_external_room_id
    )
    relayed_body = (
        f"{relay_prefix} [{connector.platform.value}:{external_label}] "
        f"{payload.external_sender.strip()}: {payload.message.strip()}"
    )

    try:
        send_payload = await matrix_client.send_text_message(
            access_token=authenticated_user.access_token,
            room_id=room_id,
            body=relayed_body,
        )
    except MatrixClientError as exc:
        mapped_status = _map_matrix_error_status(exc)
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.SERVICE,
                actor_id="bridge_runtime",
                action_type="bridge_inbound_relay",
                resource_type="bridge_link",
                resource_id=matched_link.link_id if matched_link is not None else normalized_connector_id,
                decision=DecisionType.DENY,
                reason_code="bridge_matrix_send_failed",
                user_id=authenticated_user.user_id,
                room_id=room_id,
                metadata={
                    "connector_id": normalized_connector_id,
                    "external_room_id": normalized_external_room_id,
                    "error": str(exc),
                },
            ),
        )
        raise HTTPException(status_code=mapped_status, detail=f"bridge_relay_failed: {exc}") from exc

    event_id = send_payload.get("event_id")
    if not isinstance(event_id, str) or event_id == "":
        raise HTTPException(status_code=502, detail="bridge_matrix_send_invalid_response")

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.SERVICE,
            actor_id="bridge_runtime",
            action_type="bridge_inbound_relay",
            resource_type="bridge_link",
            resource_id=matched_link.link_id if matched_link is not None else normalized_connector_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_relay_ok",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            metadata={
                "connector_id": normalized_connector_id,
                "platform": connector.platform.value,
                "external_room_id": normalized_external_room_id,
                "event_id": event_id,
            },
        ),
    )

    return BridgeInboundRelayResponse(
        status="ok",
        connector_id=normalized_connector_id,
        room_id=room_id,
        event_id=event_id,
        relayed_body=relayed_body,
    )


@router.post("/relay/outbound/preview", response_model=BridgeOutboundPreviewResponse)
async def relay_outbound_preview(
    payload: BridgeOutboundPreviewRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> BridgeOutboundPreviewResponse:
    store = _store(request, opa_client)
    matrix_client = _matrix_client(request)
    normalized_connector_id = payload.connector_id.strip()
    normalized_room_id = payload.room_id.strip()

    try:
        connector = await store.get_connector(authenticated_user.user_id, normalized_connector_id)
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    if not connector.enabled:
        raise HTTPException(status_code=409, detail="bridge_connector_disabled")

    try:
        messages = await matrix_client.read_room_messages(
            access_token=authenticated_user.access_token,
            room_id=normalized_room_id,
            limit=payload.limit,
        )
    except MatrixClientError as exc:
        mapped_status = _map_matrix_error_status(exc)
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.SERVICE,
                actor_id="bridge_runtime",
                action_type="bridge_outbound_preview",
                resource_type="bridge_link",
                resource_id=normalized_connector_id,
                decision=DecisionType.DENY,
                reason_code="bridge_matrix_read_failed",
                user_id=authenticated_user.user_id,
                room_id=normalized_room_id,
                metadata={"error": str(exc)},
            ),
        )
        raise HTTPException(status_code=mapped_status, detail=f"bridge_outbound_preview_failed: {exc}") from exc

    external_room_id = (
        payload.external_room_id.strip()
        if isinstance(payload.external_room_id, str) and payload.external_room_id.strip() != ""
        else f"matrix:{normalized_room_id}"
    )
    preview_items = [
        BridgeOutboundPreviewItem(
            external_room_id=external_room_id,
            payload_text=f"[Matrix->{connector.platform.value}] {message}",
        )
        for message in messages
    ]

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.SERVICE,
            actor_id="bridge_runtime",
            action_type="bridge_outbound_preview",
            resource_type="bridge_link",
            resource_id=normalized_connector_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_outbound_preview_ok",
            user_id=authenticated_user.user_id,
            room_id=normalized_room_id,
            metadata={"preview_count": len(preview_items), "platform": connector.platform.value},
        ),
    )

    return BridgeOutboundPreviewResponse(
        connector_id=normalized_connector_id,
        room_id=normalized_room_id,
        preview_items=preview_items,
    )

