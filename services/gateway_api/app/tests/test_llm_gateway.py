from __future__ import annotations

from typing import Any

import pytest

from app.agent.assistant_models import AgentLLMConfig, AgentLLMProvider
from app.agent.llm_gateway import AgentLLMError, chat_completion


class _DummyResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


@pytest.mark.asyncio
async def test_chat_completion_openai_compatible_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_headers: dict[str, str] = {}

    class _DummyClient:
        async def __aenter__(self) -> "_DummyClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
            _ = exc_type, exc, tb
            return False

        async def post(self, url: str, json: dict[str, Any], headers: dict[str, str]) -> _DummyResponse:
            _ = url, json
            observed_headers.update(headers)
            return _DummyResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "学习是不断吸收与实践新知识的过程。"
                            }
                        }
                    ]
                }
            )

    monkeypatch.setattr("app.agent.llm_gateway.httpx.AsyncClient", lambda timeout: _DummyClient())

    config = AgentLLMConfig(
        enabled=True,
        provider=AgentLLMProvider.OPENAI_COMPATIBLE,
        model="qwen2.5-32b",
        base_url="https://32b.qwen.rag8.cn/v1",
        api_key=None,
        api_path="/chat/completions",
    )
    output = await chat_completion(
        config=config,
        system_prompt="you are a helper",
        user_prompt="what is learning",
    )

    assert output == "学习是不断吸收与实践新知识的过程。"
    assert "Content-Type" in observed_headers
    assert observed_headers["Content-Type"] == "application/json"
    assert "Authorization" not in observed_headers


@pytest.mark.asyncio
async def test_chat_completion_openrouter_requires_api_key() -> None:
    config = AgentLLMConfig(
        enabled=True,
        provider=AgentLLMProvider.OPENROUTER,
        model="openai/gpt-4o-mini",
        api_key=None,
    )
    with pytest.raises(AgentLLMError, match="llm_api_key_required_for_openrouter"):
        await chat_completion(
            config=config,
            system_prompt="x",
            user_prompt="y",
        )
