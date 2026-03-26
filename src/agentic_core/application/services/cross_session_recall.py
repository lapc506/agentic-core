from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from agentic_core.application.ports.recall import RecallMatch, RecallPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecallQuery:
    """Parameters for a cross-session recall search."""

    query: str
    session_id: str | None = None
    persona_id: str | None = None
    limit: int = 10


@dataclass(frozen=True)
class RecallResult:
    """Aggregated result from a cross-session recall search."""

    matches: list[RecallMatch] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.matches) == 0


class CrossSessionRecall:
    """Cross-session recall via full-text search and LLM summarization."""

    def __init__(self, recall_port: RecallPort) -> None:
        self._port = recall_port

    async def search(self, query: RecallQuery) -> RecallResult:
        """Search across all sessions using the recall port (FTS)."""
        matches = await self._port.search_sessions(
            query=query.query,
            persona_id=query.persona_id,
            limit=query.limit,
        )

        # Apply optional session_id filter client-side
        if query.session_id is not None:
            matches = [m for m in matches if m.session_id == query.session_id]

        return RecallResult(matches=matches)

    async def summarize(self, session_ids: list[str]) -> str:
        """LLM-powered summarization of past conversations.

        This is a placeholder that will be wired to an LLM provider
        once the summarization adapter is implemented.
        """
        if not session_ids:
            return ""

        logger.info(
            "Summarization requested for %d session(s): %s",
            len(session_ids),
            ", ".join(session_ids[:5]),
        )

        # Placeholder: collect snippets from each session and return stub
        all_matches: list[RecallMatch] = []
        for sid in session_ids:
            hits = await self._port.search_sessions(
                query="*",
                persona_id=None,
                limit=50,
            )
            all_matches.extend(m for m in hits if m.session_id == sid)

        if not all_matches:
            return ""

        # Stub summary until LLM adapter is wired
        sorted_matches = sorted(all_matches, key=lambda m: m.timestamp)
        snippets = [m.content[:200] for m in sorted_matches[:10]]
        return (
            f"[Summary placeholder for {len(session_ids)} session(s), "
            f"{len(all_matches)} message(s)]\n"
            + "\n---\n".join(snippets)
        )
