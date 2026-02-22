from __future__ import annotations

from app.agent.skills.models import SkillManifest


class SkillRegistry:
    def __init__(self, manifests: dict[str, SkillManifest]):
        self._manifests = manifests

    @classmethod
    def default(cls) -> SkillRegistry:
        manifests = {
            "secretary.daily_digest": SkillManifest(
                skill_id="secretary.daily_digest",
                display_name="Daily Digest",
                description=(
                    "Summarize recent room activity and memory context " "into a concise briefing."
                ),
                triggers=("digest", "summary", "daily", "总结", "简报"),
                permissions=("room_messages_read", "memory_read"),
                risk_level="low",
            ),
            "specialist.todo_extractor": SkillManifest(
                skill_id="specialist.todo_extractor",
                display_name="Todo Extractor",
                description="Extract todo items from recent messages and memory notes.",
                triggers=("todo", "tasks", "待办", "action items", "follow-up"),
                permissions=("room_messages_read", "memory_read"),
                risk_level="low",
            ),
            "specialist.topic_summary": SkillManifest(
                skill_id="specialist.topic_summary",
                display_name="Topic Summary",
                description="Identify recurring topics and summarize key updates.",
                triggers=("topics", "trend", "议题", "主题", "focus"),
                permissions=("room_messages_read", "memory_read"),
                risk_level="low",
            ),
        }
        return cls(manifests=manifests)

    def get(self, skill_id: str) -> SkillManifest | None:
        return self._manifests.get(skill_id)

    def all(self) -> list[SkillManifest]:
        return [self._manifests[key] for key in sorted(self._manifests.keys())]

    def names(self) -> list[str]:
        return sorted(self._manifests.keys())
