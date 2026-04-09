"""A2A Protocol adapter — Agent-to-Agent communication (Google A2A spec).

Implements JSON-RPC 2.0 over HTTP for agent discovery, task delegation, and
result streaming between agents.

Key concepts:
- AgentCard  — JSON at /.well-known/agent.json describing capabilities
- A2ATask    — Unit of work with lifecycle: submitted → working → completed/failed
- A2AServer  — Handles incoming JSON-RPC 2.0 requests
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class AgentCard:
    """Describes agent capabilities for discovery at /.well-known/agent.json."""

    name: str
    description: str
    url: str
    version: str = "1.0"
    capabilities: list[str] = field(default_factory=list)
    skills: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": self.capabilities,
            "skills": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "description": s.get("description", ""),
                }
                for s in self.skills
            ],
            "protocol": "a2a",
            "protocolVersion": "0.1",
        }


@dataclass
class A2ATask:
    """A unit of work in the A2A protocol."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.SUBMITTED
    messages: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)


class A2AServer:
    """Handles A2A protocol requests via JSON-RPC 2.0."""

    def __init__(self, agent_card: AgentCard) -> None:
        self._card = agent_card
        self._tasks: dict[str, A2ATask] = {}
        self._task_handler: Any = None  # Callable[[A2ATask], Awaitable[dict]]

    def set_task_handler(self, handler: Any) -> None:
        """Register a coroutine that processes tasks and returns a result dict."""
        self._task_handler = handler

    def get_agent_card(self) -> dict[str, Any]:
        return self._card.to_dict()

    async def handle_jsonrpc(self, request: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a JSON-RPC 2.0 request to the appropriate method handler."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        try:
            if method == "a2a.getAgentCard":
                result = self.get_agent_card()
            elif method == "a2a.createTask":
                result = await self._create_task(params)
            elif method == "a2a.getTask":
                result = self._get_task(params.get("taskId", ""))
            elif method == "a2a.cancelTask":
                result = self._cancel_task(params.get("taskId", ""))
            elif method == "a2a.sendMessage":
                result = await self._send_message(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }

            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        except Exception as e:
            logger.exception("A2A request failed: %s", method)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)},
            }

    async def _create_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task = A2ATask(metadata=params.get("metadata", {}))
        if "message" in params:
            task.messages.append(params["message"])
        self._tasks[task.id] = task

        if self._task_handler:
            task.state = TaskState.WORKING
            try:
                result = await self._task_handler(task)
                task.result = result
                task.state = TaskState.COMPLETED
            except Exception as e:
                task.state = TaskState.FAILED
                task.result = {"error": str(e)}

        task.updated_at = datetime.now(timezone.utc).isoformat()
        return {"taskId": task.id, "state": task.state.value}

    def _get_task(self, task_id: str) -> dict[str, Any]:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        return {
            "taskId": task.id,
            "state": task.state.value,
            "messages": task.messages,
            "result": task.result,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
        }

    def _cancel_task(self, task_id: str) -> dict[str, Any]:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        task.state = TaskState.CANCELED
        task.updated_at = datetime.now(timezone.utc).isoformat()
        return {"taskId": task.id, "state": task.state.value}

    async def _send_message(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params.get("taskId", "")
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        task.messages.append(params.get("message", {}))
        task.updated_at = datetime.now(timezone.utc).isoformat()
        return {"taskId": task.id, "messageCount": len(task.messages)}
