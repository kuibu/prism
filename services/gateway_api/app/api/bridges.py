from __future__ import annotations

import os
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import ActorType, AuditEventCreate, DecisionType
from app.bridge.models import (
    BridgeConnector,
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
    BridgeRoomLink,
    BridgeRoomLinkCreateRequest,
    BridgeRoomLinkListResponse,
    BridgeRoomLinkUpdateRequest,
    BridgeTelegramPollRequest,
    BridgeTelegramPollResponse,
    BridgeTelegramSendRequest,
    BridgeTelegramSendResponse,
)
from app.bridge.telegram_client import TelegramBridgeClient, TelegramBridgeClientError
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
    get_telegram_bridge_client,
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


def _telegram_client(request: Request) -> TelegramBridgeClient:
    return cast(TelegramBridgeClient, request.app.state.telegram_bridge_client)


def _mask_secret(value: str) -> str:
    if value == "":
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{'*' * (len(value) - 6)}{value[-6:]}"


def _sanitize_connector(connector: BridgeConnector) -> BridgeConnector:
    config_raw = connector.config if isinstance(connector.config, dict) else {}
    config = dict(config_raw)
    token = config.get("bot_token")
    if isinstance(token, str):
        config["bot_token"] = _mask_secret(token)
    return connector.model_copy(update={"config": config})


def _sanitize_connector_payload(connector: BridgeConnector) -> dict[str, Any]:
    return _sanitize_connector(connector).model_dump(mode="json")


def _connector_supports_inbound(connector: BridgeConnector) -> bool:
    return connector.direction in {BridgeDirection.INBOUND, BridgeDirection.BIDIRECTIONAL}


def _connector_supports_outbound(connector: BridgeConnector) -> bool:
    return connector.direction in {BridgeDirection.OUTBOUND, BridgeDirection.BIDIRECTIONAL}


def _map_telegram_error_status(exc: TelegramBridgeClientError) -> int:
    status_code = exc.status_code
    if isinstance(status_code, int):
        if status_code in {400, 401, 403, 404, 409, 422, 429}:
            return status_code
        if status_code >= 500:
            return 502
    lowered = str(exc).lower()
    if "timed out" in lowered or "timeout" in lowered:
        return 504
    return 502


def _resolve_telegram_bot_token(connector: BridgeConnector) -> str:
    config = connector.config if isinstance(connector.config, dict) else {}
    token = config.get("bot_token")
    if isinstance(token, str) and token.strip() != "":
        return token.strip()

    for secret_ref in connector.secret_refs:
        key = secret_ref.strip()
        if key == "":
            continue
        candidates = [key, key.upper(), key.lower()]
        for candidate in candidates:
            value = os.getenv(candidate, "")
            if value.strip() != "":
                return value.strip()
    raise HTTPException(status_code=422, detail="telegram_bot_token_missing")


def _resolve_telegram_api_base_url(connector: BridgeConnector) -> str | None:
    config = connector.config if isinstance(connector.config, dict) else {}
    value = config.get("api_base_url")
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    return None


def _extract_telegram_text(update: dict[str, Any]) -> tuple[str, str, str, int | None]:
    candidates = ["message", "edited_message", "channel_post", "edited_channel_post"]
    for key in candidates:
        message = update.get(key)
        if not isinstance(message, dict):
            continue
        chat = message.get("chat")
        if not isinstance(chat, dict):
            continue
        chat_id_raw = chat.get("id")
        if chat_id_raw is None:
            continue
        chat_id = str(chat_id_raw).strip()
        if chat_id == "":
            continue

        text_value = message.get("text")
        if not isinstance(text_value, str) or text_value.strip() == "":
            caption_value = message.get("caption")
            if isinstance(caption_value, str) and caption_value.strip() != "":
                text_value = caption_value
            else:
                continue

        sender = message.get("from")
        sender_name = "telegram_user"
        if isinstance(sender, dict):
            username = sender.get("username")
            first_name = sender.get("first_name")
            last_name = sender.get("last_name")
            if isinstance(username, str) and username.strip() != "":
                sender_name = f"@{username.strip()}"
            else:
                combined = " ".join(
                    part.strip()
                    for part in [first_name, last_name]
                    if isinstance(part, str) and part.strip() != ""
                )
                if combined != "":
                    sender_name = combined
                else:
                    sender_id = sender.get("id")
                    if sender_id is not None:
                        sender_name = f"user_{sender_id}"

        update_id_raw = update.get("update_id")
        update_id = update_id_raw if isinstance(update_id_raw, int) else None
        return chat_id, sender_name, text_value.strip(), update_id
    return "", "", "", None


def _find_link_for_external_room(
    *,
    links: list[BridgeRoomLink],
    external_room_id: str,
    room_id_override: str,
) -> BridgeRoomLink | None:
    for link in links:
        if not link.enabled:
            continue
        if link.external_room_id != external_room_id:
            continue
        if room_id_override != "" and link.room_id != room_id_override:
            continue
        return link
    return None


def _resolve_external_room_for_send(
    *,
    links: list[BridgeRoomLink],
    room_id: str,
    external_room_id: str,
) -> str:
    if external_room_id != "":
        return external_room_id
    matched = [
        link for link in links if link.enabled and link.room_id == room_id and link.external_room_id.strip() != ""
    ]
    if len(matched) == 1:
        return matched[0].external_room_id
    if len(matched) > 1:
        raise HTTPException(status_code=409, detail="bridge_external_room_ambiguous")
    raise HTTPException(status_code=404, detail="bridge_link_not_found_for_room")


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
    sanitized = [_sanitize_connector(item) for item in connectors]
    return BridgeConnectorListResponse(connectors=sanitized)


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
        connector = await store.create_connector(
            user_id=authenticated_user.user_id,
            request=payload,
        )
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
    return _sanitize_connector_payload(connector)


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
    return _sanitize_connector_payload(connector)


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
    if not _connector_supports_inbound(connector):
        raise HTTPException(status_code=409, detail="bridge_connector_inbound_not_supported")

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
                resource_id=(
                    matched_link.link_id
                    if matched_link is not None
                    else normalized_connector_id
                ),
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
        raise HTTPException(
            status_code=mapped_status,
            detail=f"bridge_relay_failed: {exc}",
        ) from exc

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
            resource_id=(
                matched_link.link_id
                if matched_link is not None
                else normalized_connector_id
            ),
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
    if not _connector_supports_outbound(connector):
        raise HTTPException(status_code=409, detail="bridge_connector_outbound_not_supported")

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
        raise HTTPException(
            status_code=mapped_status,
            detail=f"bridge_outbound_preview_failed: {exc}",
        ) from exc

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


@router.post("/telegram/poll", response_model=BridgeTelegramPollResponse)
async def telegram_poll_updates(
    payload: BridgeTelegramPollRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
    telegram_client: TelegramBridgeClient = Depends(get_telegram_bridge_client),
) -> BridgeTelegramPollResponse:
    store = _store(request, opa_client)
    matrix_client = _matrix_client(request)
    settings = request.app.state.settings

    normalized_connector_id = payload.connector_id.strip()
    room_override = payload.room_id.strip() if isinstance(payload.room_id, str) else ""
    external_filter = payload.external_room_id.strip() if isinstance(payload.external_room_id, str) else ""

    try:
        connector = await store.get_connector(authenticated_user.user_id, normalized_connector_id)
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    if connector.platform != BridgePlatform.TELEGRAM:
        raise HTTPException(status_code=409, detail="bridge_connector_not_telegram")
    if not connector.enabled:
        raise HTTPException(status_code=409, detail="bridge_connector_disabled")
    if not _connector_supports_inbound(connector):
        raise HTTPException(status_code=409, detail="bridge_connector_inbound_not_supported")

    try:
        links = await store.list_links(
            user_id=authenticated_user.user_id,
            connector_id=normalized_connector_id,
        )
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    bot_token = _resolve_telegram_bot_token(connector)
    api_base_url = _resolve_telegram_api_base_url(connector)
    max_updates = max(1, min(payload.max_updates, 100))
    default_timeout = max(0, int(settings.telegram_poll_default_timeout_seconds))
    timeout_seconds = payload.timeout_seconds if payload.timeout_seconds > 0 else default_timeout

    metadata = connector.metadata if isinstance(connector.metadata, dict) else {}
    last_update_id_raw = metadata.get("telegram_last_update_id")
    last_update_id = last_update_id_raw if isinstance(last_update_id_raw, int) else None
    offset = (last_update_id + 1) if isinstance(last_update_id, int) else None

    try:
        updates = await telegram_client.get_updates(
            bot_token=bot_token,
            offset=offset,
            limit=max_updates,
            timeout_seconds=timeout_seconds,
            api_base_url=api_base_url,
        )
    except TelegramBridgeClientError as exc:
        mapped_status = _map_telegram_error_status(exc)
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.SERVICE,
                actor_id="bridge_runtime",
                action_type="bridge_telegram_poll",
                resource_type="bridge_connector",
                resource_id=normalized_connector_id,
                decision=DecisionType.DENY,
                reason_code="bridge_telegram_poll_failed",
                user_id=authenticated_user.user_id,
                room_id=room_override or None,
                metadata={"error": str(exc)},
            ),
        )
        raise HTTPException(status_code=mapped_status, detail=f"bridge_telegram_poll_failed: {exc}") from exc

    processed = 0
    skipped = 0
    room_event_ids: list[str] = []
    max_seen_update_id = last_update_id

    for update in updates:
        external_room_id, sender_name, text, update_id = _extract_telegram_text(update)
        if isinstance(update_id, int):
            if max_seen_update_id is None or update_id > max_seen_update_id:
                max_seen_update_id = update_id

        if external_room_id == "" or text == "":
            skipped += 1
            continue
        if external_filter != "" and external_room_id != external_filter:
            skipped += 1
            continue

        link = _find_link_for_external_room(
            links=links,
            external_room_id=external_room_id,
            room_id_override=room_override,
        )
        if link is None:
            skipped += 1
            continue

        room_id = room_override or link.room_id
        relay_prefix = link.relay_prefix.strip() if link.relay_prefix.strip() != "" else "[TelegramBridge]"
        external_label = (
            link.external_room_name.strip()
            if isinstance(link.external_room_name, str) and link.external_room_name.strip() != ""
            else external_room_id
        )
        relayed_body = f"{relay_prefix} [telegram:{external_label}] {sender_name}: {text}"

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
                    action_type="bridge_telegram_poll_relay",
                    resource_type="bridge_link",
                    resource_id=link.link_id,
                    decision=DecisionType.DENY,
                    reason_code="bridge_matrix_send_failed",
                    user_id=authenticated_user.user_id,
                    room_id=room_id,
                    metadata={
                        "connector_id": normalized_connector_id,
                        "external_room_id": external_room_id,
                        "error": str(exc),
                    },
                ),
            )
            raise HTTPException(status_code=mapped_status, detail=f"bridge_telegram_poll_failed: {exc}") from exc

        event_id = send_payload.get("event_id")
        if not isinstance(event_id, str) or event_id == "":
            raise HTTPException(status_code=502, detail="bridge_matrix_send_invalid_response")

        processed += 1
        room_event_ids.append(event_id)
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.SERVICE,
                actor_id="bridge_runtime",
                action_type="bridge_telegram_poll_relay",
                resource_type="bridge_link",
                resource_id=link.link_id,
                decision=DecisionType.ALLOW,
                reason_code="bridge_relay_ok",
                user_id=authenticated_user.user_id,
                room_id=room_id,
                metadata={
                    "connector_id": normalized_connector_id,
                    "external_room_id": external_room_id,
                    "event_id": event_id,
                    "telegram_update_id": update_id,
                },
            ),
        )

    if max_seen_update_id is not None and max_seen_update_id != last_update_id:
        next_metadata = dict(metadata)
        next_metadata["telegram_last_update_id"] = max_seen_update_id
        try:
            await store.update_connector(
                user_id=authenticated_user.user_id,
                connector_id=normalized_connector_id,
                request=BridgeConnectorUpdateRequest(metadata=next_metadata),
            )
        except BridgeStoreError as exc:
            raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.SERVICE,
            actor_id="bridge_runtime",
            action_type="bridge_telegram_poll",
            resource_type="bridge_connector",
            resource_id=normalized_connector_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_telegram_poll_ok",
            user_id=authenticated_user.user_id,
            room_id=room_override or None,
            metadata={
                "processed": processed,
                "skipped": skipped,
                "last_update_id": max_seen_update_id,
            },
        ),
    )

    return BridgeTelegramPollResponse(
        status="ok",
        connector_id=normalized_connector_id,
        processed=processed,
        skipped=skipped,
        last_update_id=max_seen_update_id,
        room_event_ids=room_event_ids,
    )


@router.post("/telegram/send", response_model=BridgeTelegramSendResponse)
async def telegram_send_to_external(
    payload: BridgeTelegramSendRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
    telegram_client: TelegramBridgeClient = Depends(get_telegram_bridge_client),
) -> BridgeTelegramSendResponse:
    store = _store(request, opa_client)
    matrix_client = _matrix_client(request)
    settings = request.app.state.settings

    normalized_connector_id = payload.connector_id.strip()
    normalized_room_id = payload.room_id.strip()
    external_room_input = payload.external_room_id.strip() if isinstance(payload.external_room_id, str) else ""

    try:
        connector = await store.get_connector(authenticated_user.user_id, normalized_connector_id)
    except BridgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    if connector.platform != BridgePlatform.TELEGRAM:
        raise HTTPException(status_code=409, detail="bridge_connector_not_telegram")
    if not connector.enabled:
        raise HTTPException(status_code=409, detail="bridge_connector_disabled")
    if not _connector_supports_outbound(connector):
        raise HTTPException(status_code=409, detail="bridge_connector_outbound_not_supported")

    try:
        links = await store.list_links(
            user_id=authenticated_user.user_id,
            connector_id=normalized_connector_id,
        )
    except BridgeStoreError as exc:
        raise HTTPException(status_code=503, detail=f"bridge_store_failed: {exc}") from exc

    external_room_id = _resolve_external_room_for_send(
        links=links,
        room_id=normalized_room_id,
        external_room_id=external_room_input,
    )

    bot_token = _resolve_telegram_bot_token(connector)
    api_base_url = _resolve_telegram_api_base_url(connector)

    text_input = payload.text.strip() if isinstance(payload.text, str) else ""
    if text_input != "":
        messages = [text_input]
    else:
        requested_limit = max(1, min(payload.limit, 20))
        fallback_limit = max(1, int(settings.telegram_outbound_default_limit))
        read_limit = requested_limit if requested_limit > 0 else fallback_limit
        try:
            messages = await matrix_client.read_room_messages(
                access_token=authenticated_user.access_token,
                room_id=normalized_room_id,
                limit=read_limit,
            )
        except MatrixClientError as exc:
            mapped_status = _map_matrix_error_status(exc)
            await _append_audit(
                immudb_client=immudb_client,
                event=AuditEventCreate(
                    actor_type=ActorType.SERVICE,
                    actor_id="bridge_runtime",
                    action_type="bridge_telegram_send",
                    resource_type="bridge_connector",
                    resource_id=normalized_connector_id,
                    decision=DecisionType.DENY,
                    reason_code="bridge_matrix_read_failed",
                    user_id=authenticated_user.user_id,
                    room_id=normalized_room_id,
                    metadata={"error": str(exc)},
                ),
            )
            raise HTTPException(status_code=mapped_status, detail=f"bridge_telegram_send_failed: {exc}") from exc

    normalized_messages = [item.strip() for item in messages if isinstance(item, str) and item.strip() != ""]
    if not normalized_messages:
        raise HTTPException(status_code=404, detail="bridge_no_messages_to_send")

    sent_ids: list[int] = []
    sent_texts: list[str] = []
    for text in normalized_messages:
        try:
            send_payload = await telegram_client.send_message(
                bot_token=bot_token,
                chat_id=external_room_id,
                text=text,
                api_base_url=api_base_url,
            )
        except TelegramBridgeClientError as exc:
            mapped_status = _map_telegram_error_status(exc)
            await _append_audit(
                immudb_client=immudb_client,
                event=AuditEventCreate(
                    actor_type=ActorType.SERVICE,
                    actor_id="bridge_runtime",
                    action_type="bridge_telegram_send",
                    resource_type="bridge_connector",
                    resource_id=normalized_connector_id,
                    decision=DecisionType.DENY,
                    reason_code="bridge_telegram_send_failed",
                    user_id=authenticated_user.user_id,
                    room_id=normalized_room_id,
                    metadata={
                        "external_room_id": external_room_id,
                        "error": str(exc),
                    },
                ),
            )
            raise HTTPException(status_code=mapped_status, detail=f"bridge_telegram_send_failed: {exc}") from exc

        message_id_raw = send_payload.get("message_id")
        if isinstance(message_id_raw, int):
            sent_ids.append(message_id_raw)
        sent_texts.append(text)

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.SERVICE,
            actor_id="bridge_runtime",
            action_type="bridge_telegram_send",
            resource_type="bridge_connector",
            resource_id=normalized_connector_id,
            decision=DecisionType.ALLOW,
            reason_code="bridge_telegram_send_ok",
            user_id=authenticated_user.user_id,
            room_id=normalized_room_id,
            metadata={
                "external_room_id": external_room_id,
                "sent_count": len(sent_texts),
                "telegram_message_ids": sent_ids,
            },
        ),
    )

    return BridgeTelegramSendResponse(
        status="ok",
        connector_id=normalized_connector_id,
        external_room_id=external_room_id,
        sent_count=len(sent_texts),
        telegram_message_ids=sent_ids,
        sent_texts=sent_texts,
    )
