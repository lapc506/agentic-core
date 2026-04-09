"""Progressive skill disclosure — lazy-load skills to save context tokens."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SkillSummary:
    name: str
    description: str
    tier: str  # workspace, user, extension


@dataclass
class SkillContent:
    name: str
    full_instructions: str
    tier: str


class SkillDisclosureService:
    def __init__(self) -> None:
        self._summaries: dict[str, SkillSummary] = {}
        self._content: dict[str, SkillContent] = {}
        self._activated: set[str] = set()

    def register(
        self,
        name: str,
        description: str,
        full_instructions: str,
        tier: str = "workspace",
    ) -> None:
        self._summaries[name] = SkillSummary(
            name=name, description=description, tier=tier
        )
        self._content[name] = SkillContent(
            name=name, full_instructions=full_instructions, tier=tier
        )

    def get_context_prompt(self) -> str:
        lines = ["Available skills (use activate_skill to load full instructions):"]
        for s in sorted(self._summaries.values(), key=lambda x: x.name):
            active = " [ACTIVE]" if s.name in self._activated else ""
            lines.append(f"- {s.name}: {s.description}{active}")
        return "\n".join(lines)

    def activate(self, name: str) -> str | None:
        if name not in self._content:
            return None
        self._activated.add(name)
        logger.info("Skill activated: %s", name)
        return self._content[name].full_instructions

    def deactivate(self, name: str) -> None:
        self._activated.discard(name)

    def get_active_content(self) -> str:
        parts = []
        for name in sorted(self._activated):
            if name in self._content:
                parts.append(
                    f"## Skill: {name}\n\n{self._content[name].full_instructions}"
                )
        return "\n\n".join(parts)

    def context_token_estimate(self) -> dict[str, int]:
        summary_tokens = len(self.get_context_prompt().split()) * 2
        active_tokens = len(self.get_active_content().split()) * 2
        return {
            "summary": summary_tokens,
            "active": active_tokens,
            "total": summary_tokens + active_tokens,
        }

    @property
    def available_count(self) -> int:
        return len(self._summaries)

    @property
    def active_count(self) -> int:
        return len(self._activated)
