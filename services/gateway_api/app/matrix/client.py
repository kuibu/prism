from __future__ import annotations

from typing import Any

import httpx


class MatrixClientError(RuntimeError):
    pass


class MatrixClient:
    def __init__(self, *, homeserver_url: str, timeout_seconds: float, retry_attempts: int) -> None:
        self.homeserver_url = homeserver_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = max(1, retry_attempts)

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

        last_error: str | None = None
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for _ in range(self.retry_attempts):
                try:
                    response = await client.get(
                        f"{self.homeserver_url}/_matrix/client/r0/sync",
                        params=params,
                        headers=headers,
                    )
                    response.raise_for_status()
                    payload: dict[str, Any] = response.json()
                    return payload
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    last_error = str(exc)

        raise MatrixClientError(last_error or "matrix_sync_failed")
