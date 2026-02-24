from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def now_utc() -> datetime:
    return datetime.now(UTC)


class BridgePlatform(StrEnum):
    SLACK = "slack"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WECOM = "wecom"
    WHATSAPP = "whatsapp"
    SIGNAL = "signal"
    CUSTOM = "custom"


class BridgeDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class BridgeConnector(BaseModel):
    connector_id: str = Field(min_length=1, max_length=128)
    owner_user_id: str = Field(min_length=1, max_length=255)
    platform: BridgePlatform
    display_name: str = Field(min_length=1, max_length=255)
    direction: BridgeDirection = BridgeDirection.BIDIRECTIONAL
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    secret_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class BridgeConnectorCreateRequest(BaseModel):
    connector_id: str | None = Field(default=None, max_length=128)
    platform: BridgePlatform
    display_name: str = Field(min_length=1, max_length=255)
    direction: BridgeDirection = BridgeDirection.BIDIRECTIONAL
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    secret_refs: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BridgeConnectorUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    direction: BridgeDirection | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    secret_refs: list[str] | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] | None = None


class BridgeConnectorListResponse(BaseModel):
    connectors: list[BridgeConnector]


class BridgeRoomLink(BaseModel):
    link_id: str = Field(min_length=1, max_length=128)
    owner_user_id: str = Field(min_length=1, max_length=255)
    connector_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=255)
    external_room_id: str = Field(min_length=1, max_length=255)
    external_room_name: str | None = Field(default=None, max_length=255)
    relay_prefix: str = Field(default="[Bridge]", max_length=128)
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class BridgeRoomLinkCreateRequest(BaseModel):
    link_id: str | None = Field(default=None, max_length=128)
    connector_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=255)
    external_room_id: str = Field(min_length=1, max_length=255)
    external_room_name: str | None = Field(default=None, max_length=255)
    relay_prefix: str | None = Field(default="[Bridge]", max_length=128)
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class BridgeRoomLinkUpdateRequest(BaseModel):
    external_room_name: str | None = Field(default=None, max_length=255)
    relay_prefix: str | None = Field(default=None, max_length=128)
    enabled: bool | None = None
    metadata: dict[str, Any] | None = None


class BridgeRoomLinkListResponse(BaseModel):
    links: list[BridgeRoomLink]


class BridgePlatformDescriptor(BaseModel):
    platform: BridgePlatform
    display_name: str
    direction_support: list[BridgeDirection]
    notes: str


class BridgePlatformListResponse(BaseModel):
    platforms: list[BridgePlatformDescriptor]


class BridgeInboundRelayRequest(BaseModel):
    connector_id: str = Field(min_length=1, max_length=128)
    external_room_id: str = Field(min_length=1, max_length=255)
    external_sender: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=4000)
    room_id: str | None = Field(default=None, max_length=255)


class BridgeInboundRelayResponse(BaseModel):
    status: str
    connector_id: str
    room_id: str
    event_id: str
    relayed_body: str


class BridgeOutboundPreviewRequest(BaseModel):
    connector_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=255)
    external_room_id: str | None = Field(default=None, max_length=255)
    limit: int = Field(default=20, ge=1, le=100)


class BridgeOutboundPreviewItem(BaseModel):
    external_room_id: str
    payload_text: str


class BridgeOutboundPreviewResponse(BaseModel):
    connector_id: str
    room_id: str
    preview_items: list[BridgeOutboundPreviewItem]

