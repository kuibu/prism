from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from app.agent.skills.models import SkillExecutionResult


@dataclass(frozen=True)
class SkillExecutionContext:
    query: str
    room_messages: list[str]
    memory_snippets: list[str]


def _compact_line(value: str, max_chars: int = 140) -> str:
    cleaned = " ".join(value.strip().split())
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[:max_chars]}..."


def _top_topics(messages: list[str], limit: int = 5) -> list[tuple[str, int]]:
    tokens: list[str] = []
    for message in messages:
        parts = re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", message.lower())
        for part in parts:
            if len(part) < 2:
                continue
            if part in {
                "the",
                "and",
                "for",
                "with",
                "that",
                "this",
                "请",
                "我们",
                "今天",
                "已经",
                "需要",
            }:
                continue
            tokens.append(part)
    counts = Counter(tokens)
    return counts.most_common(limit)


def _extract_todos(messages: list[str], limit: int = 8) -> list[str]:
    todos: list[str] = []
    todo_patterns = [
        r"\btodo\b",
        r"\baction\b",
        r"\bnext\b",
        r"待办",
        r"需要",
        r"请",
        r"follow-up",
    ]
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in todo_patterns]

    for message in messages:
        if any(pattern.search(message) for pattern in compiled):
            todos.append(_compact_line(message))
            if len(todos) >= limit:
                break
    return todos


class SkillExecutor:
    def execute(self, skill_id: str, context: SkillExecutionContext) -> SkillExecutionResult:
        if skill_id == "secretary.daily_digest":
            return self._run_daily_digest(context)
        if skill_id == "specialist.todo_extractor":
            return self._run_todo_extractor(context)
        if skill_id == "specialist.topic_summary":
            return self._run_topic_summary(context)
        raise ValueError(f"unsupported_skill:{skill_id}")

    def _run_daily_digest(self, context: SkillExecutionContext) -> SkillExecutionResult:
        combined = [*context.room_messages, *context.memory_snippets]
        latest = [_compact_line(item) for item in combined[:6]]
        topics = _top_topics(combined, limit=5)
        todos = _extract_todos(combined, limit=5)

        text_lines = ["Daily digest"]
        if latest:
            text_lines.append("Recent highlights:")
            text_lines.extend([f"- {line}" for line in latest])
        if topics:
            text_lines.append("Top topics:")
            text_lines.extend([f"- {name}: {count}" for name, count in topics])
        if todos:
            text_lines.append("Suggested follow-up:")
            text_lines.extend([f"- {line}" for line in todos])
        if len(text_lines) == 1:
            text_lines.append("- No recent context found.")

        output_text = "\n".join(text_lines)
        return SkillExecutionResult(
            skill_id="secretary.daily_digest",
            output_text=output_text,
            output_data={
                "highlights": latest,
                "topics": [{"topic": name, "count": count} for name, count in topics],
                "todos": todos,
            },
        )

    def _run_todo_extractor(self, context: SkillExecutionContext) -> SkillExecutionResult:
        combined = [*context.room_messages, *context.memory_snippets]
        todos = _extract_todos(combined, limit=12)
        if not todos:
            todos = ["No explicit todo found; clarify next actions with the room."]

        output_text = "Todo extractor\n" + "\n".join([f"- {item}" for item in todos])
        return SkillExecutionResult(
            skill_id="specialist.todo_extractor",
            output_text=output_text,
            output_data={"todos": todos, "count": len(todos)},
        )

    def _run_topic_summary(self, context: SkillExecutionContext) -> SkillExecutionResult:
        combined = [*context.room_messages, *context.memory_snippets]
        topics = _top_topics(combined, limit=8)
        summary_lines = [f"- {name}: {count}" for name, count in topics]
        if not summary_lines:
            summary_lines = ["- No recurring topic found."]

        output_text = "Topic summary\n" + "\n".join(summary_lines)
        return SkillExecutionResult(
            skill_id="specialist.topic_summary",
            output_text=output_text,
            output_data={"topics": [{"topic": name, "count": count} for name, count in topics]},
        )
