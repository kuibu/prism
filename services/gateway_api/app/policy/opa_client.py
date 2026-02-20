from __future__ import annotations

import asyncio
from typing import Any

import httpx


class OPAClientError(RuntimeError):
    """Raised when an OPA API request fails."""


class OPANotFoundError(OPAClientError):
    """Raised when an OPA data document is missing."""


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

    @staticmethod
    def _normalize_endpoint(path: str) -> str:
        return path if path.startswith("/") else f"/{path}"

    async def _request_json(
        self,
        *,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> dict[str, Any]:
        last_error: str | None = None
        normalized_endpoint = self._normalize_endpoint(endpoint)

        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = await self._client.request(method, normalized_endpoint, json=payload)
                if allow_not_found and response.status_code == 404:
                    raise OPANotFoundError(f"opa_document_not_found:{normalized_endpoint}")

                response.raise_for_status()
                if not response.content:
                    return {}

                raw_data = response.json()
                if isinstance(raw_data, dict):
                    return raw_data
                raise OPAClientError("opa_invalid_json_payload")
            except OPANotFoundError:
                raise
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, OPAClientError) as exc:
                last_error = str(exc)
                if attempt < self.retry_attempts:
                    await asyncio.sleep(0.2 * attempt)

        raise OPAClientError(last_error or "opa_request_failed")

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

    async def get_document(self, document_path: str) -> dict[str, Any]:
        raw_data = await self._request_json(
            method="GET",
            endpoint=document_path,
            allow_not_found=True,
        )
        result = raw_data.get("result")
        if isinstance(result, dict):
            return result
        if result is None:
            return {}
        raise OPAClientError("opa_document_result_is_not_object")

    async def put_document(self, document_path: str, payload: dict[str, Any]) -> None:
        await self._request_json(
            method="PUT",
            endpoint=document_path,
            payload=payload,
        )

    async def delete_document(self, document_path: str) -> None:
        await self._request_json(
            method="DELETE",
            endpoint=document_path,
            allow_not_found=True,
        )

    async def evaluate(self, policy_path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            raw_data = await self._request_json(
                method="POST",
                endpoint=policy_path,
                payload={"input": payload},
            )
            result = raw_data.get("result")
            if isinstance(result, dict):
                return result
            return {"allow": False, "reason": "invalid_opa_result"}
        except OPAClientError as exc:
            return {"allow": False, "reason": str(exc) or "opa_request_failed"}
