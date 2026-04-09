"""Hierarchical Task Network planner — decomposes goals into subtask trees."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class TaskNode:
    id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    children: list[TaskNode] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # IDs of tasks that must complete first
    tools_required: list[str] = field(default_factory=list)
    result: str | None = None

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def is_ready(self) -> bool:
        return self.status == TaskStatus.PENDING and not self.dependencies

    def complete(self, result: str = "") -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result

    def fail(self, reason: str = "") -> None:
        self.status = TaskStatus.FAILED
        self.result = reason

class HTNPlanner:
    """Decomposes high-level goals into hierarchical task trees."""

    def __init__(self) -> None:
        self._task_counter = 0

    def _next_id(self) -> str:
        self._task_counter += 1
        return f"task-{self._task_counter}"

    def create_plan(self, goal: str, subtasks: list[dict]) -> TaskNode:
        root = TaskNode(id=self._next_id(), name=goal, description=f"Goal: {goal}")
        for st in subtasks:
            child = TaskNode(
                id=self._next_id(),
                name=st.get("name", ""),
                description=st.get("description", ""),
                dependencies=st.get("dependencies", []),
                tools_required=st.get("tools", []),
            )
            root.children.append(child)
        return root

    def get_ready_tasks(self, root: TaskNode) -> list[TaskNode]:
        ready = []
        completed_ids = self._get_completed_ids(root)
        self._find_ready(root, completed_ids, ready)
        return ready

    def _find_ready(self, node: TaskNode, completed: set[str], ready: list[TaskNode]) -> None:
        if node.is_leaf and node.status == TaskStatus.PENDING:
            if all(d in completed for d in node.dependencies):
                ready.append(node)
        for child in node.children:
            self._find_ready(child, completed, ready)

    def _get_completed_ids(self, node: TaskNode) -> set[str]:
        ids: set[str] = set()
        if node.status == TaskStatus.COMPLETED:
            ids.add(node.id)
        for child in node.children:
            ids.update(self._get_completed_ids(child))
        return ids

    def update_parent_status(self, root: TaskNode) -> None:
        for child in root.children:
            self.update_parent_status(child)
        if root.children:
            if all(c.status == TaskStatus.COMPLETED for c in root.children):
                root.status = TaskStatus.COMPLETED
            elif any(c.status == TaskStatus.FAILED for c in root.children):
                root.status = TaskStatus.FAILED
            elif any(c.status == TaskStatus.RUNNING for c in root.children):
                root.status = TaskStatus.RUNNING
