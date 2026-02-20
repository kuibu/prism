from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ActorType(StrEnum):
    USER = "user"
    AGENT = "agent"
    SERVICE = "service"


class DecisionType(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class AuditEventCreate(BaseModel):
    actor_type: ActorType
    actor_id: str = Field(min_length=1, max_length=255)
    action_type: str = Field(min_length=1, max_length=128)
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: str = Field(min_length=1, max_length=255)
    decision: DecisionType
    reason_code: str | None = Field(default=None, max_length=128)
    input_data: dict[str, Any] | list[Any] | str | None = None
    output_data: dict[str, Any] | list[Any] | str | None = None
    input_hash: str | None = Field(default=None, max_length=128)
    output_hash: str | None = Field(default=None, max_length=128)
    signature: str | None = Field(default=None, max_length=512)
    user_id: str | None = Field(default=None, max_length=255)
    room_id: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    event_id: str
    ts: datetime
    ts_ms: int
    actor_type: ActorType
    actor_id: str
    action_type: str
    resource_type: str
    resource_id: str
    decision: DecisionType
    reason_code: str | None = None
    input_hash: str
    output_hash: str
    prev_hash: str | None = None
    chain_hash: str
    signature: str | None = None
    user_id: str | None = None
    room_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    immudb_tx_id: int | None = None


class AuditQuery(BaseModel):
    actor_id: str | None = None
    user_id: str | None = None
    room_id: str | None = None
    action_type: str | None = None
    decision: DecisionType | None = None
    start_ts: datetime | None = None
    end_ts: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)

    @field_validator("end_ts")
    @classmethod
    def validate_range(cls, end_ts: datetime | None, info: Any) -> datetime | None:
        start_ts = info.data.get("start_ts")
        if start_ts is not None and end_ts is not None and end_ts < start_ts:
            raise ValueError("end_ts must be greater than or equal to start_ts")
        return end_ts

    @property
    def start_ts_ms(self) -> int | None:
        if self.start_ts is None:
            return None
        return int(self.start_ts.timestamp() * 1000)

    @property
    def end_ts_ms(self) -> int | None:
        if self.end_ts is None:
            return None
        return int(self.end_ts.timestamp() * 1000)


class AuditListResponse(BaseModel):
    events: list[AuditEvent]


class AuditVerifyResponse(BaseModel):
    verified: bool
    checked_events: int
    first_event_id: str | None = None
    last_event_id: str | None = None
    broken_event_id: str | None = None
    reason: str | None = None
    state_tx_id: int | None = None
    state_tx_hash: str | None = None


def now_utc() -> datetime:
    return datetime.now(UTC)
