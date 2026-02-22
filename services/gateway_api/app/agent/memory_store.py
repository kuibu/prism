from __future__ import annotations

import re
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.agent.assistant_models import (
    AgentKind,
    AgentMemoryAppendResult,
    AgentMemoryEntry,
    AgentProfile,
    AgentStatus,
    AgentUpdateRequest,
    AgentUpsertRequest,
    AssistantInsightChannel,
    AssistantInsightRecord,
    MemorySourceType,
    SecretaryRoomMode,
    SecretaryRoomModeRecord,
    SecretarySuggestionRecord,
    SecretarySuggestionStatus,
    now_utc,
)
from app.policy.opa_client import OPAClient, OPAClientError, OPANotFoundError


class AgentStoreError(RuntimeError):
    """Raised when loading or persisting assistant state fails."""


class AgentNotFoundError(AgentStoreError):
    """Raised when an agent profile does not exist for a user."""


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    if lowered == "":
        return "agent"
    safe = re.sub(r"[^a-z0-9_-]+", "-", lowered)
    safe = re.sub(r"-+", "-", safe).strip("-")
    return safe or "agent"


class OPAAgentStore:
    def __init__(
        self,
        *,
        opa_client: OPAClient,
        opa_data_root: str,
        max_memories_per_agent: int = 2000,
        max_suggestions_per_user: int = 2000,
        max_insights_per_user: int = 4000,
    ) -> None:
        root = opa_data_root.rstrip("/")
        self._opa = opa_client
        self._agent_registry_path = f"{root}/agent_registry"
        self._memory_registry_path = f"{root}/agent_memory"
        self._mode_registry_path = f"{root}/agent_secretary_modes"
        self._suggestion_registry_path = f"{root}/agent_secretary_suggestions"
        self._insight_registry_path = f"{root}/agent_secretary_insights"
        self._max_memories_per_agent = max(100, max_memories_per_agent)
        self._max_suggestions_per_user = max(100, max_suggestions_per_user)
        self._max_insights_per_user = max(200, max_insights_per_user)

    async def _read_json_document(self, path: str) -> dict[str, Any]:
        try:
            payload = await self._opa.get_document(path)
            if isinstance(payload, dict):
                return payload
            return {}
        except OPANotFoundError:
            return {}
        except OPAClientError as exc:
            raise AgentStoreError(str(exc)) from exc

    async def _write_json_document(self, path: str, payload: dict[str, Any]) -> None:
        try:
            await self._opa.put_document(path, payload)
        except OPAClientError as exc:
            raise AgentStoreError(str(exc)) from exc

    async def _load_agent_registry(self) -> dict[str, Any]:
        return await self._read_json_document(self._agent_registry_path)

    async def _save_agent_registry(self, payload: dict[str, Any]) -> None:
        await self._write_json_document(self._agent_registry_path, payload)

    async def _load_memory_registry(self) -> dict[str, Any]:
        return await self._read_json_document(self._memory_registry_path)

    async def _save_memory_registry(self, payload: dict[str, Any]) -> None:
        await self._write_json_document(self._memory_registry_path, payload)

    async def _load_mode_registry(self) -> dict[str, Any]:
        return await self._read_json_document(self._mode_registry_path)

    async def _save_mode_registry(self, payload: dict[str, Any]) -> None:
        await self._write_json_document(self._mode_registry_path, payload)

    async def _load_suggestion_registry(self) -> dict[str, Any]:
        return await self._read_json_document(self._suggestion_registry_path)

    async def _save_suggestion_registry(self, payload: dict[str, Any]) -> None:
        await self._write_json_document(self._suggestion_registry_path, payload)

    async def _load_insight_registry(self) -> dict[str, Any]:
        return await self._read_json_document(self._insight_registry_path)

    async def _save_insight_registry(self, payload: dict[str, Any]) -> None:
        await self._write_json_document(self._insight_registry_path, payload)

    @staticmethod
    def _normalize_user_bucket(payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        value = payload.get(user_id)
        if isinstance(value, dict):
            return dict(value)
        return {}

    @staticmethod
    def _sort_profiles(profiles: list[AgentProfile]) -> list[AgentProfile]:
        return sorted(
            profiles,
            key=lambda item: (
                0 if item.kind == AgentKind.SECRETARY else 1,
                item.display_name.lower(),
                item.agent_id,
            ),
        )

    @staticmethod
    def _normalize_parent_policy_mode(raw: str) -> str:
        normalized = raw.strip().lower()
        if normalized not in {"inherit", "custom"}:
            raise AgentStoreError("invalid_parent_policy_mode")
        return normalized

    @staticmethod
    def _find_secretary_id(profiles: list[AgentProfile]) -> str | None:
        for item in profiles:
            if item.kind == AgentKind.SECRETARY:
                return item.agent_id
        return None

    @staticmethod
    def _validate_specialist_manager(
        *,
        profiles: list[AgentProfile],
        manager_agent_id: str,
    ) -> None:
        for item in profiles:
            if item.agent_id != manager_agent_id:
                continue
            if item.kind != AgentKind.SECRETARY:
                raise AgentStoreError("manager_must_be_secretary")
            return
        raise AgentStoreError("manager_agent_not_found")

    async def list_agents(self, user_id: str) -> list[AgentProfile]:
        registry = await self._load_agent_registry()
        user_bucket = self._normalize_user_bucket(registry, user_id)
        out: list[AgentProfile] = []
        for raw in user_bucket.values():
            if not isinstance(raw, dict):
                continue
            try:
                out.append(AgentProfile.model_validate(raw))
            except ValidationError:
                continue
        return self._sort_profiles(out)

    async def get_agent(self, user_id: str, agent_id: str) -> AgentProfile:
        agents = await self.list_agents(user_id)
        for profile in agents:
            if profile.agent_id == agent_id:
                return profile
        raise AgentNotFoundError(f"agent_not_found:{agent_id}")

    async def ensure_secretary(self, user_id: str) -> AgentProfile:
        agents = await self.list_agents(user_id)
        for profile in agents:
            if profile.kind == AgentKind.SECRETARY:
                return profile

        default_request = AgentUpsertRequest(
            agent_id=f"agent.secretary.{_slugify(user_id)}",
            kind=AgentKind.SECRETARY,
            display_name="Digital Secretary",
            purpose="secretary_collect",
            description="Personal digital secretary for collecting and organizing user context.",
            system_prompt=(
                "You are the user's digital secretary. Keep concise, factual memory, "
                "track pending tasks, and summarize important room updates."
            ),
            skill_ids=["secretary.daily_digest", "specialist.todo_extractor"],
            room_ids=[],
            auto_collect_enabled=True,
            metadata={"auto_bootstrap": True},
        )
        return await self.upsert_agent(user_id, default_request)

    async def upsert_agent(self, user_id: str, request: AgentUpsertRequest) -> AgentProfile:
        registry = await self._load_agent_registry()
        user_bucket = self._normalize_user_bucket(registry, user_id)

        now = now_utc()
        requested_id = request.agent_id.strip() if request.agent_id is not None else ""
        agent_id = requested_id
        if agent_id == "":
            if request.kind == AgentKind.SECRETARY:
                agent_id = f"agent.secretary.{_slugify(user_id)}"
            else:
                suffix = uuid4().hex[:8]
                agent_id = f"agent.specialist.{_slugify(request.display_name)}.{suffix}"

        existing_profiles: list[AgentProfile] = []
        for raw in user_bucket.values():
            if not isinstance(raw, dict):
                continue
            try:
                existing_profiles.append(AgentProfile.model_validate(raw))
            except ValidationError:
                continue

        if request.kind == AgentKind.SECRETARY:
            for existing in existing_profiles:
                if existing.kind == AgentKind.SECRETARY and existing.agent_id != agent_id:
                    raise AgentStoreError("secretary_already_exists")

        previous = user_bucket.get(agent_id)
        created_at = now
        if isinstance(previous, dict):
            try:
                previous_profile = AgentProfile.model_validate(previous)
                created_at = previous_profile.created_at
            except ValidationError:
                created_at = now

        parent_policy_mode = self._normalize_parent_policy_mode(request.parent_policy_mode)
        manager_agent_id: str | None = None
        if request.kind == AgentKind.SECRETARY:
            manager_agent_id = None
            parent_policy_mode = "inherit"
        else:
            requested_manager = ""
            if isinstance(request.manager_agent_id, str):
                requested_manager = request.manager_agent_id.strip()
            if requested_manager != "":
                manager_agent_id = requested_manager
            elif isinstance(previous, dict):
                try:
                    previous_profile = AgentProfile.model_validate(previous)
                    if isinstance(previous_profile.manager_agent_id, str):
                        manager_agent_id = previous_profile.manager_agent_id
                except ValidationError:
                    manager_agent_id = None
            if manager_agent_id is None:
                manager_agent_id = self._find_secretary_id(existing_profiles)
            if manager_agent_id is None:
                raise AgentStoreError("secretary_required_for_specialist")
            self._validate_specialist_manager(
                profiles=existing_profiles,
                manager_agent_id=manager_agent_id,
            )

        profile = AgentProfile(
            agent_id=agent_id,
            owner_user_id=user_id,
            kind=request.kind,
            display_name=request.display_name,
            purpose=request.purpose,
            description=request.description,
            system_prompt=request.system_prompt,
            skill_ids=[item.strip() for item in request.skill_ids if item.strip() != ""],
            room_ids=[item.strip() for item in request.room_ids if item.strip() != ""],
            auto_collect_enabled=request.auto_collect_enabled,
            manager_agent_id=manager_agent_id,
            parent_policy_mode=parent_policy_mode,
            llm=request.llm,
            status=AgentStatus.ACTIVE,
            created_at=created_at,
            updated_at=now,
            metadata=request.metadata,
        )

        user_bucket[agent_id] = profile.model_dump(mode="json")
        registry[user_id] = user_bucket
        await self._save_agent_registry(registry)
        return profile

    async def update_agent(
        self, user_id: str, agent_id: str, request: AgentUpdateRequest
    ) -> AgentProfile:
        registry = await self._load_agent_registry()
        user_bucket = self._normalize_user_bucket(registry, user_id)
        raw_profile = user_bucket.get(agent_id)
        if not isinstance(raw_profile, dict):
            raise AgentNotFoundError(f"agent_not_found:{agent_id}")

        try:
            current = AgentProfile.model_validate(raw_profile)
        except ValidationError as exc:
            raise AgentStoreError(f"invalid_agent_profile:{agent_id}") from exc

        payload: dict[str, Any] = {}
        if request.display_name is not None:
            payload["display_name"] = request.display_name
        if request.purpose is not None:
            payload["purpose"] = request.purpose
        if request.description is not None:
            payload["description"] = request.description
        if request.system_prompt is not None:
            payload["system_prompt"] = request.system_prompt
        if request.skill_ids is not None:
            payload["skill_ids"] = [
                item.strip() for item in request.skill_ids if item.strip() != ""
            ]
        if request.room_ids is not None:
            payload["room_ids"] = [item.strip() for item in request.room_ids if item.strip() != ""]
        if request.auto_collect_enabled is not None:
            payload["auto_collect_enabled"] = request.auto_collect_enabled
        if request.parent_policy_mode is not None:
            payload["parent_policy_mode"] = self._normalize_parent_policy_mode(
                request.parent_policy_mode
            )
        if request.llm is not None:
            payload["llm"] = request.llm
        if request.manager_agent_id is not None:
            if current.kind != AgentKind.SPECIALIST:
                raise AgentStoreError("manager_agent_only_for_specialist")
            manager_agent_id = request.manager_agent_id.strip()
            if manager_agent_id == "":
                raise AgentStoreError("manager_agent_id_empty")
            all_profiles = await self.list_agents(user_id)
            self._validate_specialist_manager(
                profiles=all_profiles,
                manager_agent_id=manager_agent_id,
            )
            payload["manager_agent_id"] = manager_agent_id
        if request.status is not None:
            payload["status"] = request.status
        if request.metadata is not None:
            payload["metadata"] = request.metadata

        updated = current.model_copy(update={**payload, "updated_at": now_utc()})
        user_bucket[agent_id] = updated.model_dump(mode="json")
        registry[user_id] = user_bucket
        await self._save_agent_registry(registry)
        return updated

    async def append_memory_entries(
        self,
        *,
        user_id: str,
        agent_id: str,
        entries: list[AgentMemoryEntry],
    ) -> AgentMemoryAppendResult:
        memory_registry = await self._load_memory_registry()
        user_bucket_raw = memory_registry.get(user_id)
        if not isinstance(user_bucket_raw, dict):
            user_bucket_raw = {}

        existing_rows = user_bucket_raw.get(agent_id)
        if not isinstance(existing_rows, list):
            existing_rows = []

        normalized_existing: list[AgentMemoryEntry] = []
        seen_source_ids: set[str] = set()
        for raw in existing_rows:
            if not isinstance(raw, dict):
                continue
            try:
                parsed = AgentMemoryEntry.model_validate(raw)
            except ValidationError:
                continue
            normalized_existing.append(parsed)
            seen_source_ids.add(parsed.source_id)

        stored_count = 0
        skipped_count = 0
        merged = list(normalized_existing)

        for entry in entries:
            if entry.source_id in seen_source_ids:
                skipped_count += 1
                continue
            merged.append(entry)
            seen_source_ids.add(entry.source_id)
            stored_count += 1

        merged.sort(key=lambda item: item.ts)
        if len(merged) > self._max_memories_per_agent:
            merged = merged[-self._max_memories_per_agent :]

        user_bucket_raw[agent_id] = [row.model_dump(mode="json") for row in merged]
        memory_registry[user_id] = user_bucket_raw
        await self._save_memory_registry(memory_registry)

        return AgentMemoryAppendResult(stored_count=stored_count, skipped_count=skipped_count)

    async def create_memory_entry(
        self,
        *,
        user_id: str,
        agent_id: str,
        source_type: MemorySourceType,
        source_id: str,
        content: str,
        room_id: str | None,
        sender_id: str | None,
        tags: list[str] | None,
        importance: float,
        metadata: dict[str, Any] | None,
    ) -> AgentMemoryEntry:
        content_clean = content.strip()
        if content_clean == "":
            raise AgentStoreError("empty_memory_content")

        source_id_clean = source_id.strip()
        if source_id_clean == "":
            source_id_clean = sha256(
                f"{user_id}:{agent_id}:{source_type.value}:{content_clean}".encode()
            ).hexdigest()

        return AgentMemoryEntry(
            memory_id=str(uuid4()),
            user_id=user_id,
            agent_id=agent_id,
            source_type=source_type,
            source_id=source_id_clean,
            room_id=room_id,
            sender_id=sender_id,
            content=content_clean,
            tags=[item.strip() for item in (tags or []) if item.strip() != ""],
            importance=importance,
            ts=now_utc(),
            metadata=metadata or {},
        )

    async def list_memory_entries(
        self, *, user_id: str, agent_id: str, limit: int = 100
    ) -> list[AgentMemoryEntry]:
        memory_registry = await self._load_memory_registry()
        user_bucket = memory_registry.get(user_id)
        if not isinstance(user_bucket, dict):
            return []

        rows = user_bucket.get(agent_id)
        if not isinstance(rows, list):
            return []

        parsed: list[AgentMemoryEntry] = []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            try:
                parsed.append(AgentMemoryEntry.model_validate(raw))
            except ValidationError:
                continue

        parsed.sort(key=lambda item: item.ts, reverse=True)
        return parsed[: max(1, limit)]

    @staticmethod
    def _tokenize(value: str) -> list[str]:
        return [
            token.lower() for token in re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", value) if token
        ]

    async def search_memory_entries(
        self,
        *,
        user_id: str,
        agent_id: str,
        query: str,
        limit: int,
    ) -> list[AgentMemoryEntry]:
        entries = await self.list_memory_entries(user_id=user_id, agent_id=agent_id, limit=600)
        query_text = query.strip()
        if query_text == "":
            return entries[:limit]

        query_tokens = self._tokenize(query_text)
        query_chars = {char for char in query_text.lower() if not char.isspace()}

        scored: list[tuple[float, AgentMemoryEntry]] = []
        for idx, entry in enumerate(entries):
            body = entry.content.lower()
            overlap = sum(1 for token in query_tokens if token in body)
            char_overlap = len(
                query_chars.intersection({char for char in body if not char.isspace()})
            )
            if overlap == 0 and char_overlap == 0:
                continue
            recency_bonus = max(0.0, 0.3 - (0.005 * idx))
            score = float(overlap) + (0.04 * float(char_overlap)) + recency_bonus + entry.importance
            scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    @staticmethod
    def _mode_key(secretary_agent_id: str, room_id: str) -> str:
        return f"{secretary_agent_id}|{room_id}"

    async def set_room_mode(
        self,
        *,
        user_id: str,
        secretary_agent_id: str,
        room_id: str,
        mode: SecretaryRoomMode,
        updated_by: str,
    ) -> SecretaryRoomModeRecord:
        registry = await self._load_mode_registry()
        user_bucket_raw = registry.get(user_id)
        if not isinstance(user_bucket_raw, dict):
            user_bucket_raw = {}

        record = SecretaryRoomModeRecord(
            owner_user_id=user_id,
            secretary_agent_id=secretary_agent_id,
            room_id=room_id,
            mode=mode,
            updated_at=now_utc(),
            updated_by=updated_by,
        )
        user_bucket_raw[self._mode_key(secretary_agent_id, room_id)] = record.model_dump(
            mode="json"
        )
        registry[user_id] = user_bucket_raw
        await self._save_mode_registry(registry)
        return record

    async def list_room_modes(
        self,
        *,
        user_id: str,
        secretary_agent_id: str | None = None,
    ) -> list[SecretaryRoomModeRecord]:
        registry = await self._load_mode_registry()
        user_bucket_raw = registry.get(user_id)
        if not isinstance(user_bucket_raw, dict):
            return []

        out: list[SecretaryRoomModeRecord] = []
        for value in user_bucket_raw.values():
            if not isinstance(value, dict):
                continue
            try:
                parsed = SecretaryRoomModeRecord.model_validate(value)
            except ValidationError:
                continue
            if secretary_agent_id is not None and parsed.secretary_agent_id != secretary_agent_id:
                continue
            out.append(parsed)

        out.sort(key=lambda item: (item.room_id, item.updated_at))
        return out

    async def get_room_mode(
        self,
        *,
        user_id: str,
        secretary_agent_id: str,
        room_id: str,
    ) -> SecretaryRoomModeRecord | None:
        registry = await self._load_mode_registry()
        user_bucket_raw = registry.get(user_id)
        if not isinstance(user_bucket_raw, dict):
            return None

        value = user_bucket_raw.get(self._mode_key(secretary_agent_id, room_id))
        if not isinstance(value, dict):
            return None
        try:
            return SecretaryRoomModeRecord.model_validate(value)
        except ValidationError:
            return None

    async def create_suggestion(
        self,
        *,
        user_id: str,
        secretary_agent_id: str,
        room_id: str,
        source_text: str,
        suggested_text: str,
        source_event_id: str | None,
        source_sender_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> SecretarySuggestionRecord:
        registry = await self._load_suggestion_registry()
        user_bucket_raw = registry.get(user_id)
        if not isinstance(user_bucket_raw, list):
            user_bucket_raw = []

        now = now_utc()
        record = SecretarySuggestionRecord(
            suggestion_id=f"suggest_{uuid4().hex[:24]}",
            owner_user_id=user_id,
            secretary_agent_id=secretary_agent_id,
            room_id=room_id,
            source_event_id=source_event_id,
            source_sender_id=source_sender_id,
            source_text=source_text.strip(),
            suggested_text=suggested_text.strip(),
            status=SecretarySuggestionStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        user_bucket_raw.append(record.model_dump(mode="json"))
        if len(user_bucket_raw) > self._max_suggestions_per_user:
            user_bucket_raw = user_bucket_raw[-self._max_suggestions_per_user :]
        registry[user_id] = user_bucket_raw
        await self._save_suggestion_registry(registry)
        return record

    async def list_suggestions(
        self,
        *,
        user_id: str,
        room_id: str | None = None,
        secretary_agent_id: str | None = None,
        status: SecretarySuggestionStatus | None = None,
        limit: int = 100,
    ) -> list[SecretarySuggestionRecord]:
        registry = await self._load_suggestion_registry()
        user_bucket_raw = registry.get(user_id)
        if not isinstance(user_bucket_raw, list):
            return []

        out: list[SecretarySuggestionRecord] = []
        for row in user_bucket_raw:
            if not isinstance(row, dict):
                continue
            try:
                parsed = SecretarySuggestionRecord.model_validate(row)
            except ValidationError:
                continue
            if room_id is not None and parsed.room_id != room_id:
                continue
            if secretary_agent_id is not None and parsed.secretary_agent_id != secretary_agent_id:
                continue
            if status is not None and parsed.status != status:
                continue
            out.append(parsed)

        out.sort(key=lambda item: item.created_at, reverse=True)
        return out[: max(1, limit)]

    async def get_suggestion(
        self,
        *,
        user_id: str,
        suggestion_id: str,
    ) -> SecretarySuggestionRecord:
        suggestions = await self.list_suggestions(
            user_id=user_id,
            limit=self._max_suggestions_per_user,
        )
        for item in suggestions:
            if item.suggestion_id == suggestion_id:
                return item
        raise AgentNotFoundError(f"suggestion_not_found:{suggestion_id}")

    async def update_suggestion_status(
        self,
        *,
        user_id: str,
        suggestion_id: str,
        status: SecretarySuggestionStatus,
        metadata_patch: dict[str, Any] | None = None,
    ) -> SecretarySuggestionRecord:
        registry = await self._load_suggestion_registry()
        user_bucket_raw = registry.get(user_id)
        if not isinstance(user_bucket_raw, list):
            raise AgentNotFoundError(f"suggestion_not_found:{suggestion_id}")

        updated_record: SecretarySuggestionRecord | None = None
        for index, row in enumerate(user_bucket_raw):
            if not isinstance(row, dict):
                continue
            try:
                parsed = SecretarySuggestionRecord.model_validate(row)
            except ValidationError:
                continue
            if parsed.suggestion_id != suggestion_id:
                continue
            merged_metadata = dict(parsed.metadata)
            if isinstance(metadata_patch, dict):
                merged_metadata.update(metadata_patch)
            updated_record = parsed.model_copy(
                update={
                    "status": status,
                    "updated_at": now_utc(),
                    "metadata": merged_metadata,
                }
            )
            user_bucket_raw[index] = updated_record.model_dump(mode="json")
            break

        if updated_record is None:
            raise AgentNotFoundError(f"suggestion_not_found:{suggestion_id}")
        registry[user_id] = user_bucket_raw
        await self._save_suggestion_registry(registry)
        return updated_record

    async def append_insights(
        self,
        *,
        user_id: str,
        secretary_agent_id: str,
        room_id: str,
        source_event_id: str | None,
        insights: list[tuple[AssistantInsightChannel, str]],
        metadata: dict[str, Any] | None = None,
    ) -> list[AssistantInsightRecord]:
        registry = await self._load_insight_registry()
        user_bucket_raw = registry.get(user_id)
        if not isinstance(user_bucket_raw, list):
            user_bucket_raw = []

        appended: list[AssistantInsightRecord] = []
        for channel, content in insights:
            content_clean = content.strip()
            if content_clean == "":
                continue
            record = AssistantInsightRecord(
                insight_id=f"insight_{uuid4().hex[:24]}",
                owner_user_id=user_id,
                secretary_agent_id=secretary_agent_id,
                room_id=room_id,
                channel=channel,
                content=content_clean,
                source_event_id=source_event_id,
                created_at=now_utc(),
                metadata=metadata or {},
            )
            user_bucket_raw.append(record.model_dump(mode="json"))
            appended.append(record)

        if len(user_bucket_raw) > self._max_insights_per_user:
            user_bucket_raw = user_bucket_raw[-self._max_insights_per_user :]
        registry[user_id] = user_bucket_raw
        await self._save_insight_registry(registry)
        return appended

    async def list_insights(
        self,
        *,
        user_id: str,
        room_id: str | None = None,
        secretary_agent_id: str | None = None,
        channel: AssistantInsightChannel | None = None,
        limit: int = 100,
    ) -> list[AssistantInsightRecord]:
        registry = await self._load_insight_registry()
        user_bucket_raw = registry.get(user_id)
        if not isinstance(user_bucket_raw, list):
            return []

        out: list[AssistantInsightRecord] = []
        for row in user_bucket_raw:
            if not isinstance(row, dict):
                continue
            try:
                parsed = AssistantInsightRecord.model_validate(row)
            except ValidationError:
                continue
            if room_id is not None and parsed.room_id != room_id:
                continue
            if secretary_agent_id is not None and parsed.secretary_agent_id != secretary_agent_id:
                continue
            if channel is not None and parsed.channel != channel:
                continue
            out.append(parsed)

        out.sort(key=lambda item: item.created_at, reverse=True)
        return out[: max(1, limit)]
