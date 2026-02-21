from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

from app.matrix.client import MatrixClient, MatrixClientError


class AgentBotManagerError(RuntimeError):
    """Raised when bot account bootstrap or authentication fails."""


@dataclass
class AgentBotIdentity:
    user_id: str
    access_token: str


class AgentBotManager:
    """Ensures a deterministic Matrix bot account exists per agent_id."""

    def __init__(
        self,
        *,
        matrix_client: MatrixClient,
        username_prefix: str,
        password_secret: str,
    ) -> None:
        self._matrix_client = matrix_client
        self._username_prefix = self._normalize_prefix(username_prefix)
        self._password_secret = password_secret
        self._cache: dict[str, AgentBotIdentity] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _normalize_prefix(raw: str) -> str:
        cleaned = "".join(ch for ch in raw.lower() if ch.isalnum() or ch in "._=-")
        return cleaned or "prism_agent"

    def _username_for_agent(self, agent_id: str) -> str:
        digest = hashlib.sha256(agent_id.encode("utf-8")).hexdigest()[:16]
        return f"{self._username_prefix}_{digest}"

    def _password_for_agent(self, agent_id: str) -> str:
        material = f"{self._password_secret}:{agent_id}".encode()
        return hashlib.sha256(material).hexdigest()

    async def ensure_identity(self, *, agent_id: str) -> AgentBotIdentity:
        async with self._lock:
            cached = self._cache.get(agent_id)
            if cached is not None:
                try:
                    whoami = await self._matrix_client.whoami(access_token=cached.access_token)
                except MatrixClientError:
                    self._cache.pop(agent_id, None)
                else:
                    if whoami.get("user_id") == cached.user_id:
                        return cached
                    self._cache.pop(agent_id, None)

            username = self._username_for_agent(agent_id)
            password = self._password_for_agent(agent_id)
            identity = await self._login_or_register(username=username, password=password)
            self._cache[agent_id] = identity
            return identity

    async def _login_or_register(self, *, username: str, password: str) -> AgentBotIdentity:
        register_error: MatrixClientError | None = None
        try:
            await self._matrix_client.register(username=username, password=password)
        except MatrixClientError as exc:
            # Existing account or registration-disabled deployments should still be
            # able to continue by authenticating an already-provisioned bot account.
            register_error = exc

        try:
            login_payload = await self._matrix_client.login(username=username, password=password)
        except MatrixClientError as login_exc:
            if register_error is None:
                raise AgentBotManagerError(f"agent_bot_login_failed:{login_exc}") from login_exc
            raise AgentBotManagerError(
                f"agent_bot_register_failed:{register_error};agent_bot_login_failed:{login_exc}"
            ) from login_exc

        user_id = login_payload.get("user_id")
        access_token = login_payload.get("access_token")
        if (
            not isinstance(user_id, str)
            or user_id == ""
            or not isinstance(access_token, str)
            or access_token == ""
        ):
            raise AgentBotManagerError("agent_bot_invalid_login_payload")

        return AgentBotIdentity(user_id=user_id, access_token=access_token)
