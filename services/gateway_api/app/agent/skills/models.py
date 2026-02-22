from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    display_name: str
    description: str
    triggers: tuple[str, ...]
    permissions: tuple[str, ...]
    risk_level: RiskLevel


@dataclass(frozen=True)
class SkillRouteResult:
    manifest: SkillManifest
    rewritten_query: str
    reason: str


@dataclass(frozen=True)
class SkillExecutionResult:
    skill_id: str
    output_text: str
    output_data: dict[str, Any]
