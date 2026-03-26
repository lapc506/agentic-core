from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SkillDefinition(BaseModel, frozen=True):
    """A learned skill that can be published to and imported from a registry."""

    name: str
    description: str
    instructions: str
    version: int = 1
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    usage_count: int = Field(ge=0, default=0)


class SkillRegistry:
    """Registry for autonomous skill creation, tracking, and community sharing."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        """Register a new skill definition."""
        self._skills[skill.name] = skill
        logger.info("Registered skill: %s (v%d)", skill.name, skill.version)

    def get(self, name: str) -> SkillDefinition | None:
        """Return a skill by name, or None if not found."""
        return self._skills.get(name)

    def list_skills(self, tag: str | None = None) -> list[SkillDefinition]:
        """List all skills, optionally filtered by tag."""
        skills = list(self._skills.values())
        if tag is not None:
            skills = [s for s in skills if tag in s.tags]
        return skills

    def update_stats(self, name: str, success: bool) -> None:
        """Update success_rate and usage_count for a skill after execution.

        Uses a running average: new_rate = (old_rate * old_count + outcome) / new_count
        """
        old = self._skills.get(name)
        if old is None:
            logger.warning("Cannot update stats for unknown skill: %s", name)
            return

        new_count = old.usage_count + 1
        outcome = 1.0 if success else 0.0
        new_rate = (old.success_rate * old.usage_count + outcome) / new_count

        self._skills[name] = SkillDefinition(
            name=old.name,
            description=old.description,
            instructions=old.instructions,
            version=old.version,
            author=old.author,
            tags=list(old.tags),
            success_rate=new_rate,
            usage_count=new_count,
        )
        logger.info(
            "Updated stats for skill %s: rate=%.2f, count=%d",
            name, new_rate, new_count,
        )

    def export_skill(self, name: str) -> dict[str, Any] | None:
        """Serialize a skill for publishing to an external registry."""
        skill = self._skills.get(name)
        if skill is None:
            return None
        return skill.model_dump()

    def import_skill(self, data: dict[str, Any]) -> SkillDefinition:
        """Deserialize a skill from community data and register it."""
        skill = SkillDefinition.model_validate(data)
        self._skills[skill.name] = skill
        logger.info("Imported skill: %s (v%d)", skill.name, skill.version)
        return skill
