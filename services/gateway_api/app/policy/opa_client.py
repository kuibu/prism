import asyncio
from typing import Any

import httpx


class OPAClient:
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
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> dict[str, Any]:
        last_error: str | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = await self._client.get("/health")
                return {
                    "reachable": response.status_code == 200,
                    "status_code": response.status_code,
                    "attempt": attempt,
                }
            except httpx.RequestError as exc:
                last_error = str(exc)
                if attempt < self.retry_attempts:
                    await asyncio.sleep(0.2 * attempt)

        return {
            "reachable": False,
            "error": last_error or "opa_unreachable",
            "attempt": self.retry_attempts,
        }

    async def evaluate(self, policy_path: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: str | None = None
        endpoint = policy_path if policy_path.startswith("/") else f"/{policy_path}"

        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = await self._client.post(endpoint, json={"input": payload})
                response.raise_for_status()
                raw_data: dict[str, Any] = response.json()
                result = raw_data.get("result")
                if isinstance(result, dict):
                    return result
                return {"allow": False, "reason": "invalid_opa_result"}
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = str(exc)
                if attempt < self.retry_attempts:
                    await asyncio.sleep(0.2 * attempt)

        return {"allow": False, "reason": last_error or "opa_request_failed"}
