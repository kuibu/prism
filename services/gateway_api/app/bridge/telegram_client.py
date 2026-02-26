from __future__ import annotations

import asyncio
from typing import Any

import httpx


class TelegramBridgeClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TelegramBridgeClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        retry_attempts: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = max(1, retry_attempts)

    async def get_updates(
        self,
        *,
        bot_token: str,
        offset: int | None,
        limit: int,
        timeout_seconds: int,
        api_base_url: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, object] = {
            "limit": max(1, min(limit, 100)),
            "timeout": max(0, min(timeout_seconds, 50)),
        }
        if isinstance(offset, int):
            params["offset"] = offset

        payload = await self._call_api(
            bot_token=bot_token,
            method="getUpdates",
            params=params,
            api_base_url=api_base_url,
            timeout_override_seconds=max(self.timeout_seconds, float(timeout_seconds + 5)),
        )
        result = payload.get("result")
        if not isinstance(result, list):
            raise TelegramBridgeClientError("telegram_get_updates_invalid_response")
        out: list[dict[str, Any]] = []
        for item in result:
            if isinstance(item, dict):
                out.append(item)
        return out

    async def send_message(
        self,
        *,
        bot_token: str,
        chat_id: str,
        text: str,
        api_base_url: str | None = None,
    ) -> dict[str, Any]:
        payload = await self._call_api(
            bot_token=bot_token,
            method="sendMessage",
            body={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            api_base_url=api_base_url,
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise TelegramBridgeClientError("telegram_send_message_invalid_response")
        return result

    async def _call_api(
        self,
        *,
        bot_token: str,
        method: str,
        params: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
        api_base_url: str | None = None,
        timeout_override_seconds: float | None = None,
    ) -> dict[str, Any]:
        token = bot_token.strip()
        if token == "":
            raise TelegramBridgeClientError("telegram_bot_token_missing")

        base_url = self._resolve_base_url(api_base_url)
        url = f"{base_url}/bot{token}/{method}"
        timeout_value = timeout_override_seconds or self.timeout_seconds
        last_error: str | None = None
        last_status_code: int | None = None

        async with httpx.AsyncClient(timeout=timeout_value) as client:
            for attempt in range(self.retry_attempts):
                try:
                    response = await client.request(
                        method="POST",
                        url=url,
                        params=params,
                        json=body,
                        timeout=timeout_value,
                    )
                    status_code = response.status_code
                    payload: dict[str, Any]
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        last_error = "telegram_non_json_response"
                        last_status_code = status_code
                        if attempt < self.retry_attempts - 1 and status_code >= 500:
                            await asyncio.sleep(0.2 * (attempt + 1))
                            continue
                        raise TelegramBridgeClientError(
                            "telegram_non_json_response",
                            status_code=status_code,
                        ) from exc

                    if status_code >= 500 and attempt < self.retry_attempts - 1:
                        last_error = self._telegram_error_message(payload, status_code=status_code)
                        last_status_code = status_code
                        await asyncio.sleep(0.2 * (attempt + 1))
                        continue

                    if status_code >= 400:
                        error_message = self._telegram_error_message(payload, status_code=status_code)
                        raise TelegramBridgeClientError(error_message, status_code=status_code)

                    ok_value = payload.get("ok")
                    if ok_value is not True:
                        error_message = self._telegram_error_message(payload, status_code=status_code)
                        raise TelegramBridgeClientError(error_message, status_code=status_code)
                    return payload
                except httpx.RequestError as exc:
                    last_error = str(exc)
                    last_status_code = None
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(0.2 * (attempt + 1))
                        continue

        raise TelegramBridgeClientError(
            f"telegram_api_request_failed:{last_error or 'unknown_error'}",
            status_code=last_status_code,
        )

    def _resolve_base_url(self, api_base_url: str | None) -> str:
        if isinstance(api_base_url, str) and api_base_url.strip() != "":
            return api_base_url.strip().rstrip("/")
        return self.base_url

    @staticmethod
    def _telegram_error_message(payload: dict[str, Any], *, status_code: int) -> str:
        description = payload.get("description")
        if isinstance(description, str) and description.strip() != "":
            return f"telegram_api_error:{status_code}:{description.strip()}"
        error_code = payload.get("error_code")
        if isinstance(error_code, int):
            return f"telegram_api_error:{status_code}:error_code={error_code}"
        return f"telegram_api_error:{status_code}"
