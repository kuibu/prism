from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.bridge.models import (
    BridgeConnector,
    BridgeConnectorCreateRequest,
    BridgeConnectorUpdateRequest,
    BridgeRoomLink,
    BridgeRoomLinkCreateRequest,
    BridgeRoomLinkUpdateRequest,
    now_utc,
)
from app.policy.opa_client import OPAClient, OPAClientError, OPANotFoundError


class BridgeStoreError(RuntimeError):
    """Raised when bridge persistence fails."""


class BridgeNotFoundError(BridgeStoreError):
    """Raised when connector or link cannot be found."""


class BridgeConflictError(BridgeStoreError):
    """Raised when connector or link conflicts with existing records."""


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    if lowered == "":
        return "bridge"
    safe = re.sub(r"[^a-z0-9_-]+", "-", lowered)
    safe = re.sub(r"-+", "-", safe).strip("-")
    return safe or "bridge"


class OPABridgeStore:
    def __init__(
        self,
        *,
        opa_client: OPAClient,
        opa_data_root: str,
        connectors_registry_name: str = "bridge_connectors",
        links_registry_name: str = "bridge_links",
    ) -> None:
        root = opa_data_root.rstrip("/")
        self._opa = opa_client
        self._connectors_path = f"{root}/{connectors_registry_name}"
        self._links_path = f"{root}/{links_registry_name}"

    async def _read_json_document(self, path: str) -> dict[str, Any]:
        try:
            payload = await self._opa.get_document(path)
            if isinstance(payload, dict):
                return payload
            return {}
        except OPANotFoundError:
            return {}
        except OPAClientError as exc:
            raise BridgeStoreError(str(exc)) from exc

    async def _write_json_document(self, path: str, payload: dict[str, Any]) -> None:
        try:
            await self._opa.put_document(path, payload)
        except OPAClientError as exc:
            raise BridgeStoreError(str(exc)) from exc

    async def _load_connector_registry(self) -> dict[str, Any]:
        return await self._read_json_document(self._connectors_path)

    async def _save_connector_registry(self, payload: dict[str, Any]) -> None:
        await self._write_json_document(self._connectors_path, payload)

    async def _load_link_registry(self) -> dict[str, Any]:
        return await self._read_json_document(self._links_path)

    async def _save_link_registry(self, payload: dict[str, Any]) -> None:
        await self._write_json_document(self._links_path, payload)

    @staticmethod
    def _user_bucket(payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        value = payload.get(user_id)
        if isinstance(value, dict):
            return dict(value)
        return {}

    async def list_connectors(self, user_id: str) -> list[BridgeConnector]:
        registry = await self._load_connector_registry()
        user_bucket = self._user_bucket(registry, user_id)
        out: list[BridgeConnector] = []
        for raw in user_bucket.values():
            if not isinstance(raw, dict):
                continue
            try:
                out.append(BridgeConnector.model_validate(raw))
            except ValidationError:
                continue
        out.sort(key=lambda item: item.updated_at, reverse=True)
        return out

    async def get_connector(self, user_id: str, connector_id: str) -> BridgeConnector:
        connectors = await self.list_connectors(user_id)
        for connector in connectors:
            if connector.connector_id == connector_id:
                return connector
        raise BridgeNotFoundError(f"bridge_connector_not_found:{connector_id}")

    async def create_connector(
        self,
        *,
        user_id: str,
        request: BridgeConnectorCreateRequest,
    ) -> BridgeConnector:
        registry = await self._load_connector_registry()
        user_bucket = self._user_bucket(registry, user_id)

        requested_id = request.connector_id.strip() if isinstance(request.connector_id, str) else ""
        connector_id = requested_id
        if connector_id == "":
            suffix = uuid4().hex[:8]
            connector_id = f"bridge.{_slugify(request.platform.value)}.{suffix}"
        if connector_id in user_bucket:
            raise BridgeConflictError(f"bridge_connector_exists:{connector_id}")

        now = now_utc()
        connector = BridgeConnector(
            connector_id=connector_id,
            owner_user_id=user_id,
            platform=request.platform,
            display_name=request.display_name.strip(),
            direction=request.direction,
            enabled=request.enabled,
            config=dict(request.config),
            secret_refs=[item.strip() for item in request.secret_refs if item.strip() != ""],
            metadata=dict(request.metadata),
            created_at=now,
            updated_at=now,
        )
        user_bucket[connector_id] = connector.model_dump(mode="json")
        registry[user_id] = user_bucket
        await self._save_connector_registry(registry)
        return connector

    async def update_connector(
        self,
        *,
        user_id: str,
        connector_id: str,
        request: BridgeConnectorUpdateRequest,
    ) -> BridgeConnector:
        registry = await self._load_connector_registry()
        user_bucket = self._user_bucket(registry, user_id)
        raw = user_bucket.get(connector_id)
        if not isinstance(raw, dict):
            raise BridgeNotFoundError(f"bridge_connector_not_found:{connector_id}")
        try:
            current = BridgeConnector.model_validate(raw)
        except ValidationError as exc:
            raise BridgeStoreError(f"bridge_connector_invalid:{connector_id}") from exc

        patch: dict[str, Any] = {}
        if request.display_name is not None:
            patch["display_name"] = request.display_name.strip()
        if request.direction is not None:
            patch["direction"] = request.direction
        if request.enabled is not None:
            patch["enabled"] = request.enabled
        if request.config is not None:
            patch["config"] = dict(request.config)
        if request.secret_refs is not None:
            patch["secret_refs"] = [item.strip() for item in request.secret_refs if item.strip() != ""]
        if request.metadata is not None:
            patch["metadata"] = dict(request.metadata)

        updated = current.model_copy(update={**patch, "updated_at": now_utc()})
        user_bucket[connector_id] = updated.model_dump(mode="json")
        registry[user_id] = user_bucket
        await self._save_connector_registry(registry)
        return updated

    async def delete_connector(self, *, user_id: str, connector_id: str) -> None:
        connector_registry = await self._load_connector_registry()
        user_connector_bucket = self._user_bucket(connector_registry, user_id)
        if connector_id not in user_connector_bucket:
            raise BridgeNotFoundError(f"bridge_connector_not_found:{connector_id}")
        del user_connector_bucket[connector_id]
        connector_registry[user_id] = user_connector_bucket
        await self._save_connector_registry(connector_registry)

        link_registry = await self._load_link_registry()
        user_link_bucket = self._user_bucket(link_registry, user_id)
        filtered: dict[str, Any] = {}
        for link_id, raw in user_link_bucket.items():
            if not isinstance(raw, dict):
                continue
            if raw.get("connector_id") == connector_id:
                continue
            filtered[link_id] = raw
        link_registry[user_id] = filtered
        await self._save_link_registry(link_registry)

    async def list_links(
        self,
        *,
        user_id: str,
        connector_id: str | None = None,
    ) -> list[BridgeRoomLink]:
        registry = await self._load_link_registry()
        user_bucket = self._user_bucket(registry, user_id)
        out: list[BridgeRoomLink] = []
        for raw in user_bucket.values():
            if not isinstance(raw, dict):
                continue
            try:
                parsed = BridgeRoomLink.model_validate(raw)
            except ValidationError:
                continue
            if connector_id is not None and parsed.connector_id != connector_id:
                continue
            out.append(parsed)
        out.sort(key=lambda item: item.updated_at, reverse=True)
        return out

    async def get_link(self, *, user_id: str, link_id: str) -> BridgeRoomLink:
        links = await self.list_links(user_id=user_id)
        for link in links:
            if link.link_id == link_id:
                return link
        raise BridgeNotFoundError(f"bridge_link_not_found:{link_id}")

    async def create_link(
        self,
        *,
        user_id: str,
        request: BridgeRoomLinkCreateRequest,
    ) -> BridgeRoomLink:
        await self.get_connector(user_id, request.connector_id)
        registry = await self._load_link_registry()
        user_bucket = self._user_bucket(registry, user_id)

        for raw in user_bucket.values():
            if not isinstance(raw, dict):
                continue
            same_connector = raw.get("connector_id") == request.connector_id
            same_room = raw.get("room_id") == request.room_id
            same_external = raw.get("external_room_id") == request.external_room_id
            if same_connector and same_room and same_external:
                raise BridgeConflictError("bridge_link_exists")

        requested_id = request.link_id.strip() if isinstance(request.link_id, str) else ""
        link_id = requested_id or f"bridge_link_{uuid4().hex[:10]}"
        if link_id in user_bucket:
            raise BridgeConflictError(f"bridge_link_exists:{link_id}")

        now = now_utc()
        relay_prefix_raw = request.relay_prefix.strip() if isinstance(request.relay_prefix, str) else ""
        relay_prefix = relay_prefix_raw if relay_prefix_raw != "" else "[Bridge]"
        external_room_name = (
            request.external_room_name.strip()
            if isinstance(request.external_room_name, str)
            and request.external_room_name.strip() != ""
            else None
        )

        link = BridgeRoomLink(
            link_id=link_id,
            owner_user_id=user_id,
            connector_id=request.connector_id,
            room_id=request.room_id.strip(),
            external_room_id=request.external_room_id.strip(),
            external_room_name=external_room_name,
            relay_prefix=relay_prefix,
            enabled=request.enabled,
            metadata=dict(request.metadata),
            created_at=now,
            updated_at=now,
        )
        user_bucket[link_id] = link.model_dump(mode="json")
        registry[user_id] = user_bucket
        await self._save_link_registry(registry)
        return link

    async def update_link(
        self,
        *,
        user_id: str,
        link_id: str,
        request: BridgeRoomLinkUpdateRequest,
    ) -> BridgeRoomLink:
        registry = await self._load_link_registry()
        user_bucket = self._user_bucket(registry, user_id)
        raw = user_bucket.get(link_id)
        if not isinstance(raw, dict):
            raise BridgeNotFoundError(f"bridge_link_not_found:{link_id}")
        try:
            current = BridgeRoomLink.model_validate(raw)
        except ValidationError as exc:
            raise BridgeStoreError(f"bridge_link_invalid:{link_id}") from exc

        patch: dict[str, Any] = {}
        if request.external_room_name is not None:
            normalized = request.external_room_name.strip()
            patch["external_room_name"] = normalized if normalized != "" else None
        if request.relay_prefix is not None:
            normalized_prefix = request.relay_prefix.strip()
            patch["relay_prefix"] = normalized_prefix if normalized_prefix != "" else "[Bridge]"
        if request.enabled is not None:
            patch["enabled"] = request.enabled
        if request.metadata is not None:
            patch["metadata"] = dict(request.metadata)

        updated = current.model_copy(update={**patch, "updated_at": now_utc()})
        user_bucket[link_id] = updated.model_dump(mode="json")
        registry[user_id] = user_bucket
        await self._save_link_registry(registry)
        return updated

    async def delete_link(self, *, user_id: str, link_id: str) -> None:
        registry = await self._load_link_registry()
        user_bucket = self._user_bucket(registry, user_id)
        if link_id not in user_bucket:
            raise BridgeNotFoundError(f"bridge_link_not_found:{link_id}")
        del user_bucket[link_id]
        registry[user_id] = user_bucket
        await self._save_link_registry(registry)

