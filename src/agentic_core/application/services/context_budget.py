"""Context window token budget manager."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TokenAllocation:
    category: str
    tokens_used: int
    max_tokens: int
    priority: int = 0


class ContextBudgetManager:
    """Manages token allocation across context window sections.

    With 200k advertised tokens, only ~176k are usable after system prompt.
    This manager tracks and enforces allocations.
    """

    def __init__(self, max_context_tokens: int = 176000) -> None:
        self._max = max_context_tokens
        self._allocations: dict[str, TokenAllocation] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._allocations = {
            "system_prompt": TokenAllocation("system_prompt", 0, 4000, priority=0),
            "soul_md": TokenAllocation("soul_md", 0, 2000, priority=1),
            "tool_definitions": TokenAllocation("tool_definitions", 0, 8000, priority=2),
            "memory_hot": TokenAllocation("memory_hot", 0, 4000, priority=3),
            "memory_cold": TokenAllocation("memory_cold", 0, 2000, priority=4),
            "conversation": TokenAllocation("conversation", 0, 100000, priority=5),
            "scratchpad": TokenAllocation("scratchpad", 0, 2000, priority=6),
            "reserved": TokenAllocation("reserved", 0, 54000, priority=99),
        }

    def allocate(self, category: str, tokens: int) -> bool:
        alloc = self._allocations.get(category)
        if not alloc:
            return False
        if tokens > alloc.max_tokens:
            logger.warning("Token allocation for %s exceeds max: %d > %d", category, tokens, alloc.max_tokens)
            return False
        alloc.tokens_used = tokens
        return True

    def available(self) -> int:
        used = sum(a.tokens_used for a in self._allocations.values())
        return max(0, self._max - used)

    def used(self) -> int:
        return sum(a.tokens_used for a in self._allocations.values())

    def utilization(self) -> float:
        return self.used() / self._max

    def can_fit(self, tokens: int) -> bool:
        return tokens <= self.available()

    def should_trim_tools(self, tool_count: int, avg_tokens_per_tool: int = 200) -> bool:
        tool_tokens = tool_count * avg_tokens_per_tool
        return tool_tokens > self._allocations["tool_definitions"].max_tokens

    def max_tools(self, avg_tokens_per_tool: int = 200) -> int:
        return self._allocations["tool_definitions"].max_tokens // avg_tokens_per_tool

    def summary(self) -> dict[str, dict[str, int]]:
        return {
            name: {"used": a.tokens_used, "max": a.max_tokens, "pct": round(a.tokens_used / max(a.max_tokens, 1) * 100)}
            for name, a in sorted(self._allocations.items(), key=lambda x: x[1].priority)
        }

    def set_max(self, category: str, max_tokens: int) -> None:
        if category in self._allocations:
            self._allocations[category].max_tokens = max_tokens
