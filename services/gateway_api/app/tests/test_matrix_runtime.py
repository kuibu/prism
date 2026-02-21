from __future__ import annotations

import httpx
import pytest

import app.matrix.client as matrix_client_module
from app.matrix.admin import AgentBotManager
from app.matrix.client import MatrixClient, MatrixClientError


@pytest.mark.asyncio
async def test_matrix_client_retries_429_with_retry_after_ms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("POST", "http://synapse/_matrix/client/v3/login")
    responses = [
        httpx.Response(
            status_code=429,
            json={"errcode": "M_LIMIT_EXCEEDED", "retry_after_ms": 5},
            request=request,
        ),
        httpx.Response(
            status_code=200,
            json={"user_id": "@bot:localhost", "access_token": "token_bot"},
            request=request,
        ),
    ]
    sleep_calls: list[float] = []

    class _FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args, kwargs

        async def __aenter__(self) -> _FakeAsyncClient:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: object,
        ) -> None:
            _ = exc_type, exc, tb
            return None

        async def request(self, *args: object, **kwargs: object) -> httpx.Response:
            _ = args, kwargs
            if not responses:
                raise AssertionError("no fake responses left")
            return responses.pop(0)

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(matrix_client_module.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(matrix_client_module.asyncio, "sleep", _fake_sleep)

    client = MatrixClient(
        homeserver_url="http://synapse:8008",
        timeout_seconds=2.0,
        retry_attempts=2,
    )
    payload = await client.login(username="bot", password="pass")

    assert payload["access_token"] == "token_bot"
    assert len(sleep_calls) == 1
    assert sleep_calls[0] >= 0.001


@pytest.mark.asyncio
async def test_agent_bot_manager_register_before_login() -> None:
    calls: list[str] = []

    class _StubMatrixClient:
        async def whoami(self, *, access_token: str) -> dict[str, object]:
            _ = access_token
            raise MatrixClientError("invalid_token")

        async def register(self, *, username: str, password: str) -> dict[str, object]:
            _ = username, password
            calls.append("register")
            return {"result": "ok"}

        async def login(self, *, username: str, password: str) -> dict[str, object]:
            _ = username, password
            calls.append("login")
            return {"user_id": "@bot:localhost", "access_token": "token_bot"}

    manager = AgentBotManager(
        matrix_client=_StubMatrixClient(),
        username_prefix="agent",
        password_secret="secret",
    )
    identity = await manager.ensure_identity(agent_id="agent.summary")

    assert identity.user_id == "@bot:localhost"
    assert identity.access_token == "token_bot"
    assert calls == ["register", "login"]


@pytest.mark.asyncio
async def test_agent_bot_manager_falls_back_to_login_when_register_fails() -> None:
    calls: list[str] = []

    class _StubMatrixClient:
        async def whoami(self, *, access_token: str) -> dict[str, object]:
            _ = access_token
            raise MatrixClientError("invalid_token")

        async def register(self, *, username: str, password: str) -> dict[str, object]:
            _ = username, password
            calls.append("register")
            raise MatrixClientError("M_USER_IN_USE")

        async def login(self, *, username: str, password: str) -> dict[str, object]:
            _ = username, password
            calls.append("login")
            return {"user_id": "@bot:localhost", "access_token": "token_bot"}

    manager = AgentBotManager(
        matrix_client=_StubMatrixClient(),
        username_prefix="agent",
        password_secret="secret",
    )
    identity = await manager.ensure_identity(agent_id="agent.summary")

    assert identity.user_id == "@bot:localhost"
    assert identity.access_token == "token_bot"
    assert calls == ["register", "login"]
