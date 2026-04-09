"""Skill self-creation service — agents create reusable procedures from completed tasks."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ProceduralSkill:
    """A learned procedure that the agent can reuse."""

    name: str
    description: str
    steps: list[str]
    tools_used: list[str] = field(default_factory=list)
    success_rate: float = 1.0
    times_used: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used: str | None = None
    tags: list[str] = field(default_factory=list)


class SkillCreationService:
    """Creates and manages procedural skills from completed agent tasks.

    Skills are stored as YAML files in the skills directory.
    After every 15 tasks, the service evaluates and refines stored skills.
    """

    REFINEMENT_INTERVAL = 15

    def __init__(self, skills_dir: str = "skills/procedural") -> None:
        self._skills_dir = Path(skills_dir)
        self._task_count = 0
        self._skills: dict[str, ProceduralSkill] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        """Load existing procedural skills from YAML files."""
        if not self._skills_dir.exists():
            return
        for path in sorted(self._skills_dir.glob("*.yaml")):
            try:
                with open(path) as f:
                    data = yaml.safe_load(f) or {}
                skill = ProceduralSkill(
                    name=data.get("name", path.stem),
                    description=data.get("description", ""),
                    steps=data.get("steps", []),
                    tools_used=data.get("tools_used", []),
                    success_rate=data.get("success_rate", 1.0),
                    times_used=data.get("times_used", 0),
                    created_at=data.get("created_at", ""),
                    last_used=data.get("last_used"),
                    tags=data.get("tags", []),
                )
                self._skills[skill.name] = skill
            except Exception:
                logger.warning("Failed to load skill: %s", path)

    async def create_from_task(
        self,
        task_description: str,
        steps_taken: list[str],
        tools_used: list[str],
        success: bool,
        tags: list[str] | None = None,
    ) -> ProceduralSkill | None:
        """Create a new procedural skill from a completed task.

        Only creates if the task was successful and involved 2+ steps.
        """
        if not success or len(steps_taken) < 2:
            return None

        # Generate skill name from description
        name = self._slugify(task_description[:60])

        # Check if similar skill exists
        existing = self._find_similar(steps_taken)
        if existing:
            # Update existing skill's success rate
            existing.times_used += 1
            existing.last_used = datetime.now(timezone.utc).isoformat()
            self._save_skill(existing)
            return existing

        skill = ProceduralSkill(
            name=name,
            description=task_description,
            steps=steps_taken,
            tools_used=tools_used,
            tags=tags or [],
        )

        self._skills[name] = skill
        self._save_skill(skill)

        self._task_count += 1
        if self._task_count >= self.REFINEMENT_INTERVAL:
            await self._refine_skills()
            self._task_count = 0

        return skill

    def find_relevant(self, query: str, top_k: int = 3) -> list[ProceduralSkill]:
        """Find skills relevant to a query using keyword matching."""
        query_words = set(query.lower().split())
        scored: list[tuple[float, ProceduralSkill]] = []

        for skill in self._skills.values():
            skill_words = set(skill.description.lower().split())
            skill_words.update(t.lower() for t in skill.tags)
            overlap = len(query_words & skill_words)
            score = overlap * skill.success_rate * (1 + skill.times_used * 0.1)
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k]]

    async def _refine_skills(self) -> None:
        """Evaluate and refine stored skills every REFINEMENT_INTERVAL tasks.

        In production, this would use an LLM to:
        1. Merge similar skills
        2. Generalize overly specific skills
        3. Remove low-success-rate skills
        """
        to_remove: list[str] = []
        for name, skill in self._skills.items():
            if skill.success_rate < 0.3 and skill.times_used > 3:
                to_remove.append(name)
                logger.info(
                    "Removing low-performance skill: %s (%.0f%% success)",
                    name,
                    skill.success_rate * 100,
                )

        for name in to_remove:
            del self._skills[name]
            path = self._skills_dir / f"{name}.yaml"
            if path.exists():
                path.unlink()

    def _save_skill(self, skill: ProceduralSkill) -> None:
        """Persist skill to YAML file."""
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "name": skill.name,
            "description": skill.description,
            "steps": skill.steps,
            "tools_used": skill.tools_used,
            "success_rate": skill.success_rate,
            "times_used": skill.times_used,
            "created_at": skill.created_at,
            "last_used": skill.last_used,
            "tags": skill.tags,
        }
        path = self._skills_dir / f"{skill.name}.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def _find_similar(self, steps: list[str]) -> ProceduralSkill | None:
        """Find existing skill with similar steps (>70% overlap)."""
        step_set = set(s.lower() for s in steps)
        for skill in self._skills.values():
            existing_set = set(s.lower() for s in skill.steps)
            if not existing_set:
                continue
            overlap = len(step_set & existing_set) / max(len(step_set | existing_set), 1)
            if overlap > 0.7:
                return skill
        return None

    @staticmethod
    def _slugify(text: str) -> str:
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        return slug.strip("-")[:60]

    @property
    def skill_count(self) -> int:
        return len(self._skills)
