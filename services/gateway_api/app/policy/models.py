from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PolicyDecisionInput(BaseModel):
    agent_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    room_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    ts: datetime


class PolicyDecision(BaseModel):
    allow: bool
    reason: str


class GrantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class DataCategory(StrEnum):
    ROOM_MESSAGES = "room_messages"
    MEMORY_NOTES = "memory_notes"


class GrantCreateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    agent_id: str = Field(min_length=1, max_length=255)
    data_category: DataCategory = DataCategory.ROOM_MESSAGES
    purpose: str = Field(min_length=1, max_length=128)
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GrantRecord(BaseModel):
    grant_id: str
    user_id: str
    agent_id: str
    data_category: DataCategory
    purpose: str
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    rate_limit_per_minute: int
    status: GrantStatus
    created_at: datetime
    revoked_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GrantListResponse(BaseModel):
    grants: list[GrantRecord]


class RevokeRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    grant_id: str = Field(min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=128)


class RevokeResponse(BaseModel):
    grant_id: str
    status: GrantStatus
    reason: str
