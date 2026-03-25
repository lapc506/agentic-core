from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GateCondition:
    description: str
    required_tasks_complete: bool = True


@dataclass
class RoadmapTask:
    id: str
    description: str
    spec: str
    verification_criteria: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Phase:
    name: str
    tasks: list[RoadmapTask] = field(default_factory=list)
    gate: GateCondition = field(default_factory=lambda: GateCondition(description="All tasks complete"))


@dataclass
class Roadmap:
    title: str
    objectives: list[str] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)
