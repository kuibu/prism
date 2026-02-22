from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentKind(StrEnum):
    SECRETARY = "secretary"
    SPECIALIST = "specialist"


class AgentStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AgentLLMProvider(StrEnum):
    OPENROUTER = "openrouter"
    QWEN = "qwen"
    OPENAI_COMPATIBLE = "openai_compatible"


class AgentLLMConfig(BaseModel):
    enabled: bool = False
    provider: AgentLLMProvider = AgentLLMProvider.OPENAI_COMPATIBLE
    model: str = Field(default="gpt-4o-mini", min_length=1, max_length=160)
    api_key: str | None = Field(default=None, max_length=512)
    base_url: str | None = Field(default=None, max_length=500)
    api_path: str = Field(default="/chat/completions", min_length=1, max_length=160)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=400, ge=64, le=4096)
    timeout_seconds: float = Field(default=12.0, ge=1.0, le=90.0)
    extra_headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("model", mode="before")
    @classmethod
    def _normalize_model(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError("model_must_be_string")
        cleaned = value.strip()
        if cleaned == "":
            raise ValueError("model_required")
        return cleaned

    @field_validator("api_key", "base_url", mode="before")
    @classmethod
    def _normalize_optional_secret(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("invalid_optional_string")
        cleaned = value.strip()
        return cleaned or None

    @field_validator("api_path", mode="before")
    @classmethod
    def _normalize_api_path(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError("api_path_must_be_string")
        cleaned = value.strip()
        if cleaned == "":
            raise ValueError("api_path_required")
        if not cleaned.startswith("/"):
            return f"/{cleaned}"
        return cleaned

    @field_validator("extra_headers", mode="before")
    @classmethod
    def _normalize_headers(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("extra_headers_must_be_object")
        out: dict[str, str] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                continue
            key = raw_key.strip()
            if key == "":
                continue
            out[key] = "" if raw_value is None else str(raw_value).strip()
        return out


class AgentProfile(BaseModel):
    agent_id: str = Field(min_length=1, max_length=255)
    owner_user_id: str = Field(min_length=1, max_length=255)
    kind: AgentKind
    display_name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    system_prompt: str = Field(default="", max_length=4000)
    skill_ids: list[str] = Field(default_factory=list)
    room_ids: list[str] = Field(default_factory=list)
    auto_collect_enabled: bool = False
    manager_agent_id: str | None = Field(default=None, min_length=1, max_length=255)
    parent_policy_mode: str = Field(default="inherit", max_length=32)
    llm: AgentLLMConfig | None = None
    status: AgentStatus = AgentStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUpsertRequest(BaseModel):
    agent_id: str | None = Field(default=None, min_length=1, max_length=255)
    kind: AgentKind
    display_name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    system_prompt: str = Field(default="", max_length=4000)
    skill_ids: list[str] = Field(default_factory=list)
    room_ids: list[str] = Field(default_factory=list)
    auto_collect_enabled: bool = False
    manager_agent_id: str | None = Field(default=None, min_length=1, max_length=255)
    parent_policy_mode: str = Field(default="inherit", max_length=32)
    llm: AgentLLMConfig | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    purpose: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    skill_ids: list[str] | None = None
    room_ids: list[str] | None = None
    auto_collect_enabled: bool | None = None
    manager_agent_id: str | None = Field(default=None, min_length=1, max_length=255)
    parent_policy_mode: str | None = Field(default=None, max_length=32)
    llm: AgentLLMConfig | None = None
    status: AgentStatus | None = None
    metadata: dict[str, Any] | None = None


class AgentListResponse(BaseModel):
    agents: list[AgentProfile]


class MemorySourceType(StrEnum):
    MATRIX_ROOM_MESSAGE = "matrix_room_message"
    MANUAL_NOTE = "manual_note"
    SKILL_OUTPUT = "skill_output"
    SYSTEM = "system"


class AgentMemoryEntry(BaseModel):
    memory_id: str
    user_id: str
    agent_id: str
    source_type: MemorySourceType
    source_id: str
    room_id: str | None = None
    sender_id: str | None = None
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    ts: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryNoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryCollectRequest(BaseModel):
    room_ids: list[str] | None = None
    limit_per_room: int = Field(default=50, ge=1, le=300)
    include_self_messages: bool = False
    purpose: str = Field(default="secretary_collect", min_length=1, max_length=128)


class MemorySearchResponse(BaseModel):
    hits: list[AgentMemoryEntry]


class SkillRunRequest(BaseModel):
    skill_id: str | None = Field(default=None, max_length=128)
    query: str = Field(default="", max_length=2000)
    purpose: str = Field(default="assistant_run", min_length=1, max_length=128)
    room_id: str | None = Field(default=None, max_length=255)
    room_message_limit: int = Field(default=30, ge=1, le=300)
    memory_limit: int = Field(default=20, ge=1, le=200)
    send_to_room: bool = False


class SkillRunResponse(BaseModel):
    status: str
    agent_id: str
    skill_id: str
    output_text: str
    output_data: dict[str, Any]
    room_event_id: str | None = None
    bot_user_id: str | None = None


class SkillManifestView(BaseModel):
    skill_id: str
    display_name: str
    description: str
    triggers: list[str]
    permissions: list[str]
    risk_level: str


class BootstrapResponse(BaseModel):
    secretary: AgentProfile
    specialists: list[AgentProfile]


class AgentMemoryAppendResult(BaseModel):
    stored_count: int
    skipped_count: int


class SecretaryRoomMode(StrEnum):
    AUTO = "auto"
    SEMI = "semi"
    OFF = "off"


class SecretaryRoomModeRecord(BaseModel):
    owner_user_id: str = Field(min_length=1, max_length=255)
    secretary_agent_id: str = Field(min_length=1, max_length=255)
    room_id: str = Field(min_length=1, max_length=255)
    mode: SecretaryRoomMode
    updated_at: datetime
    updated_by: str = Field(min_length=1, max_length=255)


class SecretaryRoomModeUpsertRequest(BaseModel):
    mode: SecretaryRoomMode


class SecretaryRoomModeListResponse(BaseModel):
    modes: list[SecretaryRoomModeRecord]


class SecretarySuggestionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    POSTED = "posted"


class SecretarySuggestionRecord(BaseModel):
    suggestion_id: str = Field(min_length=1, max_length=64)
    owner_user_id: str = Field(min_length=1, max_length=255)
    secretary_agent_id: str = Field(min_length=1, max_length=255)
    room_id: str = Field(min_length=1, max_length=255)
    source_event_id: str | None = Field(default=None, max_length=255)
    source_sender_id: str | None = Field(default=None, max_length=255)
    source_text: str = Field(min_length=1, max_length=4000)
    suggested_text: str = Field(min_length=1, max_length=4000)
    status: SecretarySuggestionStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecretarySuggestionCreateRequest(BaseModel):
    room_id: str = Field(min_length=1, max_length=255)
    source_text: str = Field(min_length=1, max_length=4000)
    source_event_id: str | None = Field(default=None, max_length=255)
    source_sender_id: str | None = Field(default=None, max_length=255)
    purpose: str = Field(default="assistant_reply", min_length=1, max_length=128)


class SecretarySuggestionListResponse(BaseModel):
    suggestions: list[SecretarySuggestionRecord]


class SecretarySuggestionActionRequest(BaseModel):
    send_to_room: bool = True
    purpose: str = Field(default="assistant_reply", min_length=1, max_length=128)


class SecretarySuggestionActionResponse(BaseModel):
    suggestion: SecretarySuggestionRecord
    room_event_id: str | None = None
    bot_user_id: str | None = None


class AssistantInsightChannel(StrEnum):
    REALTIME_ANALYSIS = "realtime_analysis"
    DEEP_THINKING = "deep_thinking"
    IMPLIED_MEANING = "implied_meaning"
    ROAST = "roast"


class AssistantInsightRecord(BaseModel):
    insight_id: str = Field(min_length=1, max_length=64)
    owner_user_id: str = Field(min_length=1, max_length=255)
    secretary_agent_id: str = Field(min_length=1, max_length=255)
    room_id: str = Field(min_length=1, max_length=255)
    channel: AssistantInsightChannel
    content: str = Field(min_length=1, max_length=4000)
    source_event_id: str | None = Field(default=None, max_length=255)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssistantInsightListResponse(BaseModel):
    insights: list[AssistantInsightRecord]


def now_utc() -> datetime:
    return datetime.now(UTC)
