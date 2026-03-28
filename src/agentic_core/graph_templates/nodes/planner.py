"""Planner node: generates a reasoning step (thought) from the current state.

Used by the ReAct template's ``think`` phase and by plan-execute / orchestrator
templates that need an initial planning step.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class PlannerNode:
    """Generates a multi-step plan or a single reasoning thought from user input.

    When an LLM is bound (via ``model``), the planner invokes the model to
    produce the thought.  Without a model it falls back to a pass-through
    that simply increments the iteration counter -- useful for testing.
    """

    def __init__(self, model: Any | None = None, system_prompt: str = "") -> None:
        self._model = model
        self._system_prompt = system_prompt

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        state.setdefault("iterations", 0)
        state["iterations"] = state.get("iterations", 0) + 1

        messages: list[BaseMessage] = list(state.get("messages", []))

        if self._model is not None:
            # Build the prompt: system instruction + conversation history
            prompt: list[BaseMessage] = []
            if self._system_prompt:
                prompt.append(SystemMessage(content=self._system_prompt))
            prompt.extend(messages)

            if not prompt:
                prompt.append(HumanMessage(content="What should I do?"))

            response: AIMessage = await self._model.ainvoke(prompt)

            # Append the assistant response to messages
            messages.append(response)
            state["messages"] = messages

            # Extract tool_calls if present (for ReAct routing)
            if hasattr(response, "tool_calls") and response.tool_calls:
                state["tool_calls"] = response.tool_calls
            else:
                state["tool_calls"] = []

            # Extract plan steps if the model produced them
            if hasattr(response, "content") and response.content:
                state.setdefault("plan", [])
                state["thought"] = response.content
        else:
            # Fallback: no model -- pass-through for tests
            state.setdefault("plan", [])
            state.setdefault("thought", "")
            state.setdefault("tool_calls", [])

        return state
