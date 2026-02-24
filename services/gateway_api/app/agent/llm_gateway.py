from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.agent.assistant_models import AgentLLMConfig, AgentLLMProvider


class AgentLLMError(RuntimeError):
    """Raised when an LLM call fails or configuration is invalid."""


def _resolve_base_url(config: AgentLLMConfig) -> str:
    if config.base_url is not None and config.base_url.strip() != "":
        return config.base_url.strip().rstrip("/")
    if config.provider == AgentLLMProvider.OPENROUTER:
        return "https://openrouter.ai/api/v1"
    if config.provider == AgentLLMProvider.QWEN:
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    raise AgentLLMError("llm_base_url_required")


def _extract_text_from_chat_completion(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AgentLLMError("llm_invalid_response_choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise AgentLLMError("llm_invalid_response_choice")

    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                part_type = str(item.get("type", ""))
                if part_type != "text":
                    continue
                raw_text = item.get("text")
                if isinstance(raw_text, str):
                    cleaned = raw_text.strip()
                    if cleaned:
                        parts.append(cleaned)
            if parts:
                return "\n".join(parts)

    text = first.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    raise AgentLLMError("llm_invalid_response_content")


def _build_headers(config: AgentLLMConfig) -> dict[str, str]:
    api_key = (config.api_key or "").strip()
    headers: dict[str, str] = {
        "Content-Type": "application/json",
    }
    if api_key != "":
        headers["Authorization"] = f"Bearer {api_key}"
    elif config.provider == AgentLLMProvider.OPENROUTER:
        raise AgentLLMError("llm_api_key_required_for_openrouter")
    if config.provider == AgentLLMProvider.OPENROUTER:
        headers.setdefault("HTTP-Referer", "http://localhost:8080/web/")
        headers.setdefault("X-Title", "Prism Digital Secretary")
    for key, value in config.extra_headers.items():
        normalized_key = key.strip()
        if normalized_key == "":
            continue
        headers[normalized_key] = value
    return headers


async def chat_completion(
    *,
    config: AgentLLMConfig,
    system_prompt: str,
    user_prompt: str,
) -> str:
    if not config.enabled:
        raise AgentLLMError("llm_disabled")

    headers = _build_headers(config)
    base_url = _resolve_base_url(config)
    url = f"{base_url}{config.api_path}"
    request_payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(config.temperature),
        "max_tokens": int(config.max_tokens),
    }

    last_error: str | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.post(
                    url,
                    json=request_payload,
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise AgentLLMError("llm_invalid_response_root")
                return _extract_text_from_chat_completion(payload)
        except (httpx.HTTPError, ValueError, AgentLLMError) as exc:
            last_error = str(exc)
            if attempt >= 1:
                break
            await asyncio.sleep(0.25)
    raise AgentLLMError(f"llm_request_failed: {last_error or 'unknown_error'}")
