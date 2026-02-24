from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Protocol
from uuid import uuid4

import httpx
from pydantic import ValidationError

from app.agent.assistant_models import (
    AgentMemoryAppendResult,
    AgentMemoryEntry,
    MemorySourceType,
    now_utc,
)
from app.policy.opa_client import OPAClient, OPAClientError, OPANotFoundError


class AgentMemoryBackendError(RuntimeError):
    """Raised when the memory backend fails."""


class AgentMemoryBackend(Protocol):
    async def append_memory_entries(
        self,
        *,
        user_id: str,
        agent_id: str,
        entries: list[AgentMemoryEntry],
    ) -> AgentMemoryAppendResult:
        ...

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
        ...

    async def list_memory_entries(
        self, *, user_id: str, agent_id: str, limit: int = 100
    ) -> list[AgentMemoryEntry]:
        ...

    async def search_memory_entries(
        self,
        *,
        user_id: str,
        agent_id: str,
        query: str,
        limit: int,
    ) -> list[AgentMemoryEntry]:
        ...


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", value) if token]


class OPADocumentMemoryBackend:
    """Memory backend persisted in OPA documents."""

    def __init__(
        self,
        *,
        opa_client: OPAClient,
        opa_data_root: str,
        max_memories_per_agent: int = 2000,
        registry_name: str = "agent_memory",
    ) -> None:
        root = opa_data_root.rstrip("/")
        self._opa = opa_client
        self._memory_registry_path = f"{root}/{registry_name}"
        self._max_memories_per_agent = max(100, max_memories_per_agent)

    async def _read_json_document(self, path: str) -> dict[str, Any]:
        try:
            payload = await self._opa.get_document(path)
            if isinstance(payload, dict):
                return payload
            return {}
        except OPANotFoundError:
            return {}
        except OPAClientError as exc:
            raise AgentMemoryBackendError(str(exc)) from exc

    async def _write_json_document(self, path: str, payload: dict[str, Any]) -> None:
        try:
            await self._opa.put_document(path, payload)
        except OPAClientError as exc:
            raise AgentMemoryBackendError(str(exc)) from exc

    async def _load_memory_registry(self) -> dict[str, Any]:
        return await self._read_json_document(self._memory_registry_path)

    async def _save_memory_registry(self, payload: dict[str, Any]) -> None:
        await self._write_json_document(self._memory_registry_path, payload)

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
            raise AgentMemoryBackendError("empty_memory_content")

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

        query_tokens = _tokenize(query_text)
        query_chars = {char for char in query_text.lower() if not char.isspace()}

        scored: list[tuple[float, AgentMemoryEntry]] = []
        for idx, entry in enumerate(entries):
            body = entry.content.lower()
            overlap = sum(1 for token in query_tokens if token in body)
            body_chars = {char for char in body if not char.isspace()}
            char_overlap = len(query_chars.intersection(body_chars))
            if overlap == 0 and char_overlap == 0:
                continue
            recency_bonus = max(0.0, 0.3 - (0.005 * idx))
            score = float(overlap) + (0.04 * float(char_overlap)) + recency_bonus + entry.importance
            scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:limit]]


@dataclass(slots=True)
class OpenVikingConfig:
    base_url: str
    api_key: str | None = None
    agent_id: str | None = None
    timeout_seconds: float = 6.0
    retry_attempts: int = 2


class OpenVikingMemoryBackend:
    """OpenViking-backed memory manager using the official Session API pattern.

    The backend keeps canonical structured memory entries in a local backend for deterministic
    API responses, while mirroring entries to OpenViking sessions and committing each batch to
    trigger long-term memory extraction in OpenViking.
    """

    def __init__(
        self,
        *,
        primary: AgentMemoryBackend,
        config: OpenVikingConfig,
    ) -> None:
        base_url = config.base_url.strip().rstrip("/")
        if base_url == "":
            raise ValueError("openviking_base_url_required")
        self._primary = primary
        self._base_url = base_url
        self._api_key = config.api_key.strip() if isinstance(config.api_key, str) else ""
        self._agent_id = config.agent_id.strip() if isinstance(config.agent_id, str) else ""
        self._timeout_seconds = max(1.0, float(config.timeout_seconds))
        self._retry_attempts = max(1, int(config.retry_attempts))

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        if self._agent_id:
            headers["X-OpenViking-Agent"] = self._agent_id
        return headers

    async def _request_result(
        self,
        *,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        normalized = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        headers = self._headers()
        last_error: str | None = None
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            headers=headers,
        ) as client:
            for attempt in range(1, self._retry_attempts + 1):
                try:
                    response = await client.request(method, normalized, json=payload)
                    response.raise_for_status()
                    raw = response.json()
                    if not isinstance(raw, dict):
                        raise AgentMemoryBackendError("openviking_invalid_json")
                    if raw.get("status") == "error":
                        error = raw.get("error")
                        if isinstance(error, dict):
                            code = str(error.get("code", "UNKNOWN"))
                            message = str(error.get("message", "openviking_error"))
                            raise AgentMemoryBackendError(f"openviking_error:{code}:{message}")
                        raise AgentMemoryBackendError("openviking_error")
                    return raw.get("result")
                except (
                    httpx.RequestError,
                    httpx.HTTPStatusError,
                    ValueError,
                    AgentMemoryBackendError,
                ) as exc:
                    last_error = str(exc)
                    if attempt < self._retry_attempts:
                        await asyncio.sleep(0.25 * attempt)
        raise AgentMemoryBackendError(last_error or "openviking_request_failed")

    @staticmethod
    def _render_session_memory(entry: AgentMemoryEntry) -> str:
        tags = ", ".join(entry.tags)
        metadata = entry.metadata or {}
        room_id = entry.room_id or "-"
        sender_id = entry.sender_id or "-"
        return (
            "[PRISM_AGENT_MEMORY]\n"
            f"memory_id: {entry.memory_id}\n"
            f"user_id: {entry.user_id}\n"
            f"agent_id: {entry.agent_id}\n"
            f"source_type: {entry.source_type.value}\n"
            f"source_id: {entry.source_id}\n"
            f"room_id: {room_id}\n"
            f"sender_id: {sender_id}\n"
            f"importance: {entry.importance:.3f}\n"
            f"tags: {tags}\n"
            f"metadata: {metadata}\n"
            f"content: {entry.content}"
        )

    async def _mirror_entries(self, entries: list[AgentMemoryEntry]) -> None:
        if not entries:
            return
        session_payload = {"user": entries[0].user_id}
        session_result = await self._request_result(
            method="POST",
            endpoint="/api/v1/sessions",
            payload=session_payload,
        )
        if not isinstance(session_result, dict):
            raise AgentMemoryBackendError("openviking_create_session_failed")
        session_id = session_result.get("session_id")
        if not isinstance(session_id, str) or session_id.strip() == "":
            raise AgentMemoryBackendError("openviking_session_id_missing")
        for entry in entries:
            await self._request_result(
                method="POST",
                endpoint=f"/api/v1/sessions/{session_id}/messages",
                payload={"role": "user", "content": self._render_session_memory(entry)},
            )
        await self._request_result(
            method="POST",
            endpoint=f"/api/v1/sessions/{session_id}/commit",
            payload={},
        )

    async def append_memory_entries(
        self,
        *,
        user_id: str,
        agent_id: str,
        entries: list[AgentMemoryEntry],
    ) -> AgentMemoryAppendResult:
        existing_source_ids: set[str] = set()
        if entries:
            existing_rows = await self._primary.list_memory_entries(
                user_id=user_id,
                agent_id=agent_id,
                limit=max(2000, len(entries) * 8),
            )
            existing_source_ids = {item.source_id for item in existing_rows}

        mirror_candidates: list[AgentMemoryEntry] = []
        seen_source_ids = set(existing_source_ids)
        for entry in entries:
            if entry.source_id in seen_source_ids:
                continue
            mirror_candidates.append(entry)
            seen_source_ids.add(entry.source_id)

        result = await self._primary.append_memory_entries(
            user_id=user_id,
            agent_id=agent_id,
            entries=entries,
        )
        if result.stored_count > 0 and mirror_candidates:
            await self._mirror_entries(mirror_candidates)
        return result

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
        return await self._primary.create_memory_entry(
            user_id=user_id,
            agent_id=agent_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
            room_id=room_id,
            sender_id=sender_id,
            tags=tags,
            importance=importance,
            metadata=metadata,
        )

    async def list_memory_entries(
        self, *, user_id: str, agent_id: str, limit: int = 100
    ) -> list[AgentMemoryEntry]:
        return await self._primary.list_memory_entries(
            user_id=user_id,
            agent_id=agent_id,
            limit=limit,
        )

    async def search_memory_entries(
        self,
        *,
        user_id: str,
        agent_id: str,
        query: str,
        limit: int,
    ) -> list[AgentMemoryEntry]:
        query_text = query.strip()
        if query_text == "":
            return await self._primary.list_memory_entries(
                user_id=user_id,
                agent_id=agent_id,
                limit=limit,
            )

        # Canonical memory rows come from the local backend for stable response fields.
        local_hits = await self._primary.search_memory_entries(
            user_id=user_id,
            agent_id=agent_id,
            query=query_text,
            limit=max(limit * 6, 60),
        )
        if not local_hits:
            return []

        try:
            memory_terms: set[str] = set()
            for target_uri in ("viking://user/memories", "viking://agent/memories"):
                result = await self._request_result(
                    method="POST",
                    endpoint="/api/v1/search/find",
                    payload={
                        "query": query_text,
                        "target_uri": target_uri,
                        "limit": max(limit, 10),
                    },
                )
                if not isinstance(result, dict):
                    continue
                for row in result.get("memories", []):
                    if not isinstance(row, dict):
                        continue
                    abstract = row.get("abstract")
                    uri = row.get("uri")
                    if isinstance(abstract, str):
                        memory_terms.update(_tokenize(abstract))
                    if isinstance(uri, str):
                        memory_terms.update(_tokenize(uri))
            if not memory_terms:
                return local_hits[:limit]

            query_tokens = _tokenize(query_text)
            ranked: list[tuple[float, AgentMemoryEntry]] = []
            for idx, entry in enumerate(local_hits):
                body_tokens = set(_tokenize(entry.content))
                query_overlap = sum(1 for token in query_tokens if token in body_tokens)
                memory_overlap = len(body_tokens.intersection(memory_terms))
                recency_bonus = max(0.0, 0.2 - (0.004 * idx))
                score = (
                    float(query_overlap)
                    + (0.08 * float(memory_overlap))
                    + recency_bonus
                    + entry.importance
                )
                ranked.append((score, entry))
            ranked.sort(key=lambda item: item[0], reverse=True)
            return [entry for _, entry in ranked[:limit]]
        except AgentMemoryBackendError:
            # Keep service responsive if the OpenViking retrieval API is temporarily unavailable.
            return local_hits[:limit]
