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
async def test_matrix_sync_uses_long_poll_timeout_buffer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("GET", "http://synapse/_matrix/client/v3/sync")
    captured_timeouts: list[float] = []

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
            _ = args
            timeout = kwargs.get("timeout")
            if isinstance(timeout, (int, float)):
                captured_timeouts.append(float(timeout))
            return httpx.Response(
                status_code=200,
                json={"next_batch": "s1", "rooms": {"join": {}}},
                request=request,
            )

    monkeypatch.setattr(matrix_client_module.httpx, "AsyncClient", _FakeAsyncClient)

    client = MatrixClient(
        homeserver_url="http://synapse:8008",
        timeout_seconds=3.0,
        retry_attempts=1,
    )
    payload = await client.sync(
        access_token="token_alice",
        since=None,
        timeout_ms=12000,
        full_state=False,
    )

    assert payload["next_batch"] == "s1"
    assert captured_timeouts
    assert captured_timeouts[0] >= 14.0


@pytest.mark.asyncio
async def test_matrix_download_media_falls_back_to_legacy_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted_urls: list[str] = []

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
            _ = args
            url = str(kwargs.get("url", ""))
            attempted_urls.append(url)
            request = httpx.Request("GET", url)
            if url.endswith("/_matrix/client/v1/media/download/localhost/media123"):
                return httpx.Response(
                    status_code=404,
                    json={"errcode": "M_NOT_FOUND", "error": "not found"},
                    request=request,
                )
            if url.endswith("/_matrix/media/v3/download/localhost/media123"):
                return httpx.Response(
                    status_code=200,
                    content=b"media-bytes",
                    headers={"content-type": "text/plain"},
                    request=request,
                )
            raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(matrix_client_module.httpx, "AsyncClient", _FakeAsyncClient)

    client = MatrixClient(
        homeserver_url="http://synapse:8008",
        timeout_seconds=2.0,
        retry_attempts=1,
    )
    content, headers = await client.download_media(
        access_token="token_alice",
        mxc_uri="mxc://localhost/media123",
    )

    assert content == b"media-bytes"
    assert headers.get("content-type") == "text/plain"
    assert attempted_urls == [
        "http://synapse:8008/_matrix/client/v1/media/download/localhost/media123",
        "http://synapse:8008/_matrix/media/v3/download/localhost/media123",
    ]


@pytest.mark.asyncio
async def test_matrix_download_media_returns_not_found_when_all_paths_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            _ = args
            url = str(kwargs.get("url", ""))
            request = httpx.Request("GET", url)
            return httpx.Response(
                status_code=404,
                json={"errcode": "M_NOT_FOUND", "error": "not found"},
                request=request,
            )

    monkeypatch.setattr(matrix_client_module.httpx, "AsyncClient", _FakeAsyncClient)

    client = MatrixClient(
        homeserver_url="http://synapse:8008",
        timeout_seconds=2.0,
        retry_attempts=1,
    )

    with pytest.raises(MatrixClientError) as exc_info:
        await client.download_media(
            access_token="token_alice",
            mxc_uri="mxc://localhost/media123",
        )

    assert exc_info.value.status_code == 404


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
