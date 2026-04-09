"""Internal todo tracker — agent manages its own subtask list during complex tasks."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TodoItem:
    id: int
    text: str
    done: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TodoTracker:
    def __init__(self) -> None:
        self._sessions: dict[str, list[TodoItem]] = {}
        self._counter: dict[str, int] = {}

    def add(self, session_id: str, text: str) -> TodoItem:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            self._counter[session_id] = 0
        self._counter[session_id] += 1
        item = TodoItem(id=self._counter[session_id], text=text)
        self._sessions[session_id].append(item)
        return item

    def complete(self, session_id: str, item_id: int) -> bool:
        for item in self._sessions.get(session_id, []):
            if item.id == item_id:
                item.done = True
                return True
        return False

    def remove(self, session_id: str, item_id: int) -> bool:
        items = self._sessions.get(session_id, [])
        for i, item in enumerate(items):
            if item.id == item_id:
                items.pop(i)
                return True
        return False

    def list_todos(self, session_id: str) -> list[TodoItem]:
        return self._sessions.get(session_id, [])

    def format_for_context(self, session_id: str) -> str:
        items = self.list_todos(session_id)
        if not items:
            return ""
        lines = ["[Internal task tracker:]"]
        for item in items:
            mark = "x" if item.done else " "
            lines.append(f"- [{mark}] #{item.id}: {item.text}")
        done = sum(1 for i in items if i.done)
        lines.append(f"Progress: {done}/{len(items)}")
        return "\n".join(lines)

    def progress(self, session_id: str) -> tuple[int, int]:
        items = self.list_todos(session_id)
        done = sum(1 for i in items if i.done)
        return done, len(items)

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._counter.pop(session_id, None)
