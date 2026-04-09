from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Skill:
    name: str
    instructions: str
    version: int = 1
    score_history: list[float] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def record_score(self, score: float) -> None:
        self.score_history.append(score)
        self.updated_at = datetime.now(UTC)

    def evolve(self, new_instructions: str) -> None:
        self.instructions = new_instructions
        self.version += 1
        self.updated_at = datetime.now(UTC)
