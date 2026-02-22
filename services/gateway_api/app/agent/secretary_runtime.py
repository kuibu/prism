from __future__ import annotations

import json
import re
from typing import Any

from app.agent.assistant_models import AgentLLMConfig, AssistantInsightChannel
from app.agent.llm_gateway import AgentLLMError, chat_completion


SECRETARY_AUTO_REPLY_MARKER = "（数字秘书自动回复 / Auto-replied by Digital Secretary）"


def build_secretary_suggestion(source_text: str) -> str:
    cleaned = " ".join(source_text.strip().split())
    if cleaned == "":
        return "收到消息。请确认下一步。"

    lowered = cleaned.lower()
    if any(token in lowered for token in ["todo", "待办", "follow up", "follow-up", "next"]):
        return f"我整理了待办：{cleaned}。是否由我拆成可执行的清单并分配优先级？"
    if "?" in cleaned or "吗" in cleaned or "是否" in cleaned:
        return f"你提了一个问题：{cleaned}。建议先确认目标和截止时间，我可以代拟回复。"
    return f"我理解你的重点是：{cleaned}。建议先回复“已收到，稍后给出详细计划”。"


async def build_secretary_response_bundle(
    *,
    source_text: str,
    context_messages: list[str],
    llm_config: AgentLLMConfig | None,
) -> tuple[str, list[tuple[AssistantInsightChannel, str]], str]:
    fallback_suggestion = build_secretary_suggestion(source_text)
    fallback_insights = build_secretary_insights(source_text)

    if llm_config is None or not llm_config.enabled:
        return fallback_suggestion, fallback_insights, "rule"

    try:
        generated = await _generate_secretary_json(
            source_text=source_text,
            context_messages=context_messages,
            llm_config=llm_config,
        )
    except AgentLLMError:
        return fallback_suggestion, fallback_insights, "rule"

    suggestion_value = _safe_text(generated.get("suggestion"), max_chars=3800)
    if suggestion_value == "":
        suggestion_value = fallback_suggestion

    insights_raw = generated.get("insights")
    insight_defaults = {channel: text for channel, text in fallback_insights}
    insight_pairs: list[tuple[AssistantInsightChannel, str]] = []
    key_map = {
        AssistantInsightChannel.REALTIME_ANALYSIS: ["realtime_analysis", "real_time_analysis"],
        AssistantInsightChannel.DEEP_THINKING: ["deep_thinking", "deepthinking"],
        AssistantInsightChannel.IMPLIED_MEANING: ["implied_meaning", "implicit_meaning"],
        AssistantInsightChannel.ROAST: ["roast", "light_roast"],
    }

    for channel, keys in key_map.items():
        selected = ""
        if isinstance(insights_raw, dict):
            for key in keys:
                selected = _safe_text(insights_raw.get(key), max_chars=3800)
                if selected != "":
                    break
        if selected == "":
            selected = insight_defaults[channel]
        insight_pairs.append((channel, selected))
    return suggestion_value, insight_pairs, "llm"


def build_secretary_insights(source_text: str) -> list[tuple[AssistantInsightChannel, str]]:
    cleaned = " ".join(source_text.strip().split())
    if cleaned == "":
        return [
            (AssistantInsightChannel.REALTIME_ANALYSIS, "暂无可分析内容。"),
            (AssistantInsightChannel.DEEP_THINKING, "等待新的上下文后再推理。"),
            (AssistantInsightChannel.IMPLIED_MEANING, "当前没有明显隐含诉求。"),
            (AssistantInsightChannel.ROAST, "今天很安静，秘书先待命。"),
        ]

    short = cleaned if len(cleaned) <= 220 else f"{cleaned[:220]}..."
    intent = _extract_intent(cleaned)
    risk = _extract_risk(cleaned)
    implied = _extract_implied(cleaned)
    roast = _build_roast(cleaned)

    return [
        (
            AssistantInsightChannel.REALTIME_ANALYSIS,
            f"实时分析：消息核心意图偏向“{intent}”，原文：{short}",
        ),
        (
            AssistantInsightChannel.DEEP_THINKING,
            f"深度思考：潜在风险是“{risk}”。建议先澄清范围、责任人和截止时间。",
        ),
        (
            AssistantInsightChannel.IMPLIED_MEANING,
            f"言外之意：{implied}",
        ),
        (
            AssistantInsightChannel.ROAST,
            roast,
        ),
    ]


def _extract_intent(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["bug", "故障", "异常", "报错"]):
        return "问题处理"
    if any(token in lowered for token in ["上线", "release", "deploy", "发布"]):
        return "发布推进"
    if any(token in lowered for token in ["todo", "待办", "next", "计划"]):
        return "任务拆解"
    if "?" in text or "吗" in text or "是否" in text:
        return "信息确认"
    return "一般沟通"


def _extract_risk(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(asap|urgent|紧急|马上)\b", lowered):
        return "时间压力高，容易遗漏细节"
    if any(token in lowered for token in ["maybe", "大概", "可能", "暂时"]):
        return "目标边界不清，后续返工概率高"
    if any(token in lowered for token in ["everyone", "都", "全部", "all"]):
        return "责任范围过大，执行可能失焦"
    return "信息基本充分，风险中等"


def _extract_implied(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["please", "请", "麻烦", "帮忙"]):
        return "对方在请求协作，默认期待较快反馈。"
    if "?" in text or "吗" in text or "是否" in text:
        return "对方希望得到明确答复，不希望只收到模糊结论。"
    return "对方更看重执行进度同步，而不是长篇讨论。"


def _build_roast(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", text)
    count = len(words)
    if count < 8:
        return "吐槽：信息太短，秘书都没法发挥。多给点上下文吧。"
    if count > 40:
        return "吐槽：这条消息信息量很大，像把周报塞进了聊天框。"
    return "吐槽：内容刚好，秘书批准你继续高效沟通。"


def _safe_text(value: Any, *, max_chars: int) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    if cleaned == "":
        return ""
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[:max_chars - 3]}..."


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first >= 0 and last > first:
        snippet = cleaned[first : last + 1]
        payload = json.loads(snippet)
        if isinstance(payload, dict):
            return payload
    raise AgentLLMError("llm_response_not_json")


def _build_context_block(context_messages: list[str]) -> str:
    if not context_messages:
        return "(no recent history)"
    compact: list[str] = []
    for row in context_messages[-12:]:
        cleaned = " ".join(row.strip().split())
        if cleaned == "":
            continue
        if len(cleaned) > 220:
            cleaned = f"{cleaned[:220]}..."
        compact.append(cleaned)
    if not compact:
        return "(no recent history)"
    return "\n".join([f"{index + 1}. {item}" for index, item in enumerate(compact)])


async def _generate_secretary_json(
    *,
    source_text: str,
    context_messages: list[str],
    llm_config: AgentLLMConfig,
) -> dict[str, Any]:
    system_prompt = (
        "You are a practical digital secretary. "
        "Generate one concise, polite reply for the user and 4 insight channels. "
        "Return strict JSON only without markdown."
    )
    user_prompt = (
        "Please analyze the latest incoming message with recent room context.\n\n"
        "Latest incoming message:\n"
        f"{source_text.strip()}\n\n"
        "Recent context (oldest to newest):\n"
        f"{_build_context_block(context_messages)}\n\n"
        "Return JSON with this exact schema:\n"
        "{\n"
        '  "suggestion": "string",\n'
        '  "insights": {\n'
        '    "realtime_analysis": "string",\n'
        '    "deep_thinking": "string",\n'
        '    "implied_meaning": "string",\n'
        '    "roast": "string"\n'
        "  }\n"
        "}\n"
        "Do not include any extra keys."
    )
    raw_text = await chat_completion(
        config=llm_config,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    return _extract_json_object(raw_text)
