"""HandleMessage command: streams agent responses through a LangGraph graph.

This is the main entry point for user messages.  It resolves the persona's
graph template, compiles it, and streams execution events back as
``AgentMessage`` value objects.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import uuid_utils

from agentic_core.domain.value_objects.messages import AgentMessage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from agentic_core.application.ports.memory import MemoryPort
    from agentic_core.application.ports.session import SessionPort
    from agentic_core.shared_kernel.events import EventBus

logger = logging.getLogger(__name__)


class HandleMessageCommand:
    __slots__ = ("session_id", "persona_id", "content", "user_id", "trace_id")

    def __init__(
        self,
        session_id: str,
        persona_id: str,
        content: str,
        user_id: str,
        trace_id: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.persona_id = persona_id
        self.content = content
        self.user_id = user_id
        self.trace_id = trace_id


class HandleMessageHandler:
    """Processes an incoming user message by streaming it through LangGraph.

    When a compiled graph is available (via ``graph_port``), the handler
    streams execution events and yields ``AgentMessage`` tokens.  Without
    a graph it gracefully yields nothing (Phase-1 / test mode).
    """

    def __init__(
        self,
        memory_port: MemoryPort,
        session_port: SessionPort,
        event_bus: EventBus,
        *,
        graph_builder: Any | None = None,
    ) -> None:
        self._memory = memory_port
        self._session = session_port
        self._event_bus = event_bus
        self._graph_builder = graph_builder

    async def execute(self, cmd: HandleMessageCommand) -> AsyncIterator[AgentMessage]:
        session = await self._session.get(cmd.session_id)
        if session is None:
            raise ValueError(f"Session {cmd.session_id} not found")

        # Retrieve conversation history from memory
        history = await self._memory.get_context_window(cmd.session_id, max_tokens=4096)

        # Build initial messages list from history + new user message
        messages: list[dict[str, Any]] = [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]
        messages.append({"role": "user", "content": cmd.content})

        # Store the incoming user message
        user_msg = AgentMessage(
            id=str(uuid_utils.uuid7()),
            session_id=cmd.session_id,
            persona_id=cmd.persona_id,
            role="user",
            content=cmd.content,
            metadata={},
            timestamp=datetime.now(UTC),
            trace_id=cmd.trace_id,
        )
        await self._memory.store_message(user_msg)

        # If no graph builder is wired, yield nothing (Phase-1 / test mode)
        if self._graph_builder is None:
            return

        # Build and compile the graph
        compiled = self._graph_builder.build_graph()
        if isinstance(compiled, dict):
            # Fallback dict descriptor -- no streaming possible
            logger.warning("Graph returned fallback dict; streaming unavailable")
            return

        # Stream execution through the compiled LangGraph
        input_state = {
            "messages": messages,
            "iterations": 0,
            "max_iterations": 25,
            "done": False,
        }

        async for chunk in self._stream_graph(compiled, input_state, cmd):
            yield chunk

    async def _stream_graph(
        self,
        compiled: Any,
        input_state: dict[str, Any],
        cmd: HandleMessageCommand,
    ) -> AsyncIterator[AgentMessage]:
        """Stream tokens from the compiled LangGraph.

        Uses ``astream`` with ``stream_mode="messages"`` when available
        for per-token streaming.  Falls back to node-level ``astream``
        for coarser output.
        """
        try:
            # Try streaming with messages mode for token-level granularity
            async for chunk in compiled.astream(
                input_state,
                stream_mode="messages",
                version="v2",
            ):
                if chunk.get("type") == "messages":
                    msg_chunk, metadata = chunk["data"]
                    content = getattr(msg_chunk, "content", "")
                    if content:
                        token_msg = AgentMessage(
                            id=str(uuid_utils.uuid7()),
                            session_id=cmd.session_id,
                            persona_id=cmd.persona_id,
                            role="assistant",
                            content=content,
                            metadata={
                                "stream_token": True,
                                "node": metadata.get("langgraph_node", ""),
                            },
                            timestamp=datetime.now(UTC),
                            trace_id=cmd.trace_id,
                        )
                        yield token_msg
        except (TypeError, ValueError):
            # Fallback: node-level streaming
            logger.debug("Falling back to node-level astream")
            async for event in compiled.astream(input_state):
                # Each event is a dict keyed by node name
                for node_name, node_state in event.items():
                    node_messages = node_state.get("messages", [])
                    if not node_messages:
                        continue
                    last = node_messages[-1]
                    content = last.get("content", "") if isinstance(last, dict) else getattr(last, "content", "")
                    if content:
                        yield AgentMessage(
                            id=str(uuid_utils.uuid7()),
                            session_id=cmd.session_id,
                            persona_id=cmd.persona_id,
                            role="assistant",
                            content=content,
                            metadata={
                                "stream_token": False,
                                "node": node_name,
                            },
                            timestamp=datetime.now(UTC),
                            trace_id=cmd.trace_id,
                        )
