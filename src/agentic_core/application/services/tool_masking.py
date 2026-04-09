"""Tool output masking — summarize verbose outputs to save context tokens."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ToolOutputMasker:
    def __init__(self, max_tokens: int = 2000, summary_tokens: int = 500) -> None:
        self._max = max_tokens
        self._summary = summary_tokens
        self._tool_configs: dict[str, int] = {}

    def configure_tool(self, tool_name: str, max_tokens: int) -> None:
        self._tool_configs[tool_name] = max_tokens

    def mask(self, tool_name: str, output: str) -> str:
        max_tokens = self._tool_configs.get(tool_name, self._max)
        estimated_tokens = len(output.split())
        if estimated_tokens <= max_tokens:
            return output

        logger.info(
            "Masking output for %s: %d tokens → %d",
            tool_name,
            estimated_tokens,
            self._summary,
        )
        return self._truncate_smart(output, max_tokens)

    def _truncate_smart(self, text: str, max_tokens: int) -> str:
        lines = text.split("\n")
        if len(lines) <= 3:
            words = text.split()
            return " ".join(words[:max_tokens]) + "\n[... output truncated]"

        # Keep first and last portions
        keep_lines = max(max_tokens // 10, 5)
        head = lines[:keep_lines]
        tail = lines[-keep_lines:]
        omitted = len(lines) - 2 * keep_lines
        return (
            "\n".join(head)
            + f"\n\n[... {omitted} lines omitted ...]\n\n"
            + "\n".join(tail)
        )

    def should_mask(self, tool_name: str, output: str) -> bool:
        max_tokens = self._tool_configs.get(tool_name, self._max)
        return len(output.split()) > max_tokens
