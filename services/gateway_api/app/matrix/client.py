from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx


class MatrixClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        errcode: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.errcode = errcode


class MatrixClient:
    def __init__(self, *, homeserver_url: str, timeout_seconds: float, retry_attempts: int) -> None:
        self.homeserver_url = homeserver_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = max(1, retry_attempts)

    async def whoami(self, *, access_token: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = await self._request_json(
            method="GET",
            path="/_matrix/client/v3/account/whoami",
            headers=headers,
        )

        user_id = payload.get("user_id")
        if not isinstance(user_id, str) or user_id == "":
            raise MatrixClientError("matrix_whoami_invalid_response")
        return payload

    async def register(self, *, username: str, password: str) -> dict[str, Any]:
        return await self._request_json(
            method="POST",
            path="/_matrix/client/v3/register",
            body={
                "username": username,
                "password": password,
                "auth": {"type": "m.login.dummy"},
            },
        )

    async def login(self, *, username: str, password: str) -> dict[str, Any]:
        return await self._request_json(
            method="POST",
            path="/_matrix/client/v3/login",
            body={
                "type": "m.login.password",
                "identifier": {"type": "m.id.user", "user": username},
                "password": password,
            },
        )

    async def create_room(
        self,
        *,
        access_token: str,
        name: str | None,
        invite: list[str],
        preset: str,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"preset": preset}
        if name:
            body["name"] = name
        if invite:
            body["invite"] = invite

        headers = {"Authorization": f"Bearer {access_token}"}
        return await self._request_json(
            method="POST",
            path="/_matrix/client/v3/createRoom",
            headers=headers,
            body=body,
        )

    async def join_room(self, *, access_token: str, room_id: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        encoded_room_id = quote(room_id, safe="")
        return await self._request_json(
            method="POST",
            path=f"/_matrix/client/v3/rooms/{encoded_room_id}/join",
            headers=headers,
            body={},
        )

    async def invite_user(self, *, access_token: str, room_id: str, user_id: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        encoded_room_id = quote(room_id, safe="")
        return await self._request_json(
            method="POST",
            path=f"/_matrix/client/v3/rooms/{encoded_room_id}/invite",
            headers=headers,
            body={"user_id": user_id},
        )

    async def get_joined_members(
        self,
        *,
        access_token: str,
        room_id: str,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        encoded_room_id = quote(room_id, safe="")
        return await self._request_json(
            method="GET",
            path=f"/_matrix/client/v3/rooms/{encoded_room_id}/joined_members",
            headers=headers,
        )

    async def send_text_message(
        self,
        *,
        access_token: str,
        room_id: str,
        body: str,
        txn_id: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        encoded_room_id = quote(room_id, safe="")
        safe_txn = txn_id or f"tx_{uuid4().hex}"
        return await self._request_json(
            method="PUT",
            path=f"/_matrix/client/v3/rooms/{encoded_room_id}/send/m.room.message/{safe_txn}",
            headers=headers,
            body={"msgtype": "m.text", "body": body},
        )

    async def upload_media(
        self,
        *,
        access_token: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
        }
        return await self._request_json(
            method="POST",
            path="/_matrix/media/v3/upload",
            params={"filename": filename},
            headers=headers,
            content=content,
        )

    async def send_file_message(
        self,
        *,
        access_token: str,
        room_id: str,
        filename: str,
        content_uri: str,
        content_type: str,
        size_bytes: int,
        txn_id: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        encoded_room_id = quote(room_id, safe="")
        safe_txn = txn_id or f"tx_{uuid4().hex}"
        return await self._request_json(
            method="PUT",
            path=f"/_matrix/client/v3/rooms/{encoded_room_id}/send/m.room.message/{safe_txn}",
            headers=headers,
            body={
                "msgtype": "m.file",
                "body": filename,
                "url": content_uri,
                "info": {
                    "mimetype": content_type,
                    "size": size_bytes,
                },
            },
        )

    async def read_room_messages(
        self,
        *,
        access_token: str,
        room_id: str,
        limit: int,
    ) -> list[str]:
        sync_payload = await self.sync(
            access_token=access_token,
            since=None,
            timeout_ms=0,
            full_state=False,
        )

        joined_rooms = sync_payload.get("rooms", {}).get("join", {})
        room_data = joined_rooms.get(room_id)
        if not isinstance(room_data, dict):
            return []

        timeline_events = room_data.get("timeline", {}).get("events", [])
        if not isinstance(timeline_events, list):
            return []

        messages: list[str] = []
        for event in timeline_events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "m.room.message":
                continue
            content = event.get("content", {})
            if not isinstance(content, dict):
                continue
            body = content.get("body")
            if not isinstance(body, str):
                continue
            text = body.strip()
            if text != "":
                messages.append(text)

        if limit <= 0:
            return []
        return messages[-limit:]

    async def sync(
        self,
        *,
        access_token: str,
        since: str | None,
        timeout_ms: int,
        full_state: bool,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "timeout": timeout_ms,
            "full_state": "true" if full_state else "false",
        }
        if since:
            params["since"] = since

        headers = {"Authorization": f"Bearer {access_token}"}
        return await self._request_json(
            method="GET",
            path="/_matrix/client/v3/sync",
            params=params,
            headers=headers,
            request_timeout_seconds=max(self.timeout_seconds, (float(timeout_ms) / 1000.0) + 2.0),
        )

    async def _request_json(
        self,
        *,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        content: bytes | None = None,
        request_timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        if body is not None and content is not None:
            raise MatrixClientError("invalid_request_payload")

        last_error: str | None = None
        last_status_code: int | None = None
        last_errcode: str | None = None
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for attempt in range(self.retry_attempts):
                try:
                    response = await client.request(
                        method=method,
                        url=f"{self.homeserver_url}{path}",
                        params=params,
                        headers=headers,
                        json=body,
                        content=content,
                        timeout=request_timeout_seconds or self.timeout_seconds,
                    )
                    response.raise_for_status()
                    payload: dict[str, Any] = response.json()
                    return payload
                except httpx.RequestError as exc:
                    last_error = str(exc)
                    last_status_code = None
                    last_errcode = None
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    last_status_code = status
                    try:
                        payload = exc.response.json()
                    except ValueError:
                        payload = {}
                    errcode_raw = payload.get("errcode")
                    error_raw = payload.get("error")
                    last_errcode = str(errcode_raw) if isinstance(errcode_raw, str) else None
                    detail = str(error_raw) if isinstance(error_raw, str) else str(exc)
                    last_error = detail
                    if status == 429 and attempt + 1 < self.retry_attempts:
                        await asyncio.sleep(self._retry_delay_from_response(exc.response, attempt))
                        continue
                    if 500 <= status < 600 and attempt + 1 < self.retry_attempts:
                        await asyncio.sleep(self._default_backoff_delay(attempt))
                        continue
                    break
                except ValueError as exc:
                    last_error = str(exc)
                    break

                if attempt + 1 < self.retry_attempts:
                    await asyncio.sleep(self._default_backoff_delay(attempt))

        raise MatrixClientError(
            last_error or "matrix_request_failed",
            status_code=last_status_code,
            errcode=last_errcode,
        )

    @staticmethod
    def _default_backoff_delay(attempt: int) -> float:
        delay = 0.25 * float(2**attempt)
        return 2.0 if delay > 2.0 else delay

    @classmethod
    def _retry_delay_from_response(cls, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                parsed = float(retry_after)
                if parsed > 0:
                    return 30.0 if parsed > 30.0 else parsed
            except ValueError:
                pass

        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            retry_after_ms = payload.get("retry_after_ms")
            if isinstance(retry_after_ms, (int, float)) and retry_after_ms > 0:
                parsed_ms = float(retry_after_ms) / 1000.0
                return 30.0 if parsed_ms > 30.0 else parsed_ms

        fallback = cls._default_backoff_delay(attempt)
        return 1.0 if fallback < 1.0 else fallback
