from __future__ import annotations

import re

from app.agent.skills.models import SkillManifest, SkillRouteResult
from app.agent.skills.registry import SkillRegistry


class SkillRouter:
    EXPLICIT_PATTERN = re.compile(r"^\s*skill:([a-zA-Z0-9_.-]+)\b", re.IGNORECASE)

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def route(self, query: str) -> SkillRouteResult | None:
        raw = query.strip()
        if raw == "":
            return None

        explicit = self.EXPLICIT_PATTERN.match(raw)
        if explicit is not None:
            skill_id = explicit.group(1)
            manifest = self.registry.get(skill_id)
            if manifest is None:
                return None
            rewritten = raw[explicit.end() :].strip() or raw
            return SkillRouteResult(
                manifest=manifest, rewritten_query=rewritten, reason="explicit_skill_prefix"
            )

        query_lc = raw.lower()
        scores: list[tuple[int, SkillManifest]] = []
        for manifest in self.registry.all():
            score = 0
            for trigger in manifest.triggers:
                trigger_text = trigger.strip().lower()
                if trigger_text != "" and trigger_text in query_lc:
                    score += 1
            if score > 0:
                scores.append((score, manifest))

        if not scores:
            return None

        scores.sort(key=lambda item: (-item[0], item[1].skill_id))
        winner = scores[0][1]
        return SkillRouteResult(
            manifest=winner, rewritten_query=raw, reason="trigger_keyword_match"
        )
