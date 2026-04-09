from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryCategory(str, Enum):
    PREFERENCE = "preference"
    GOAL = "goal"
    SKILL = "skill"
    PROJECT = "project"
    CONTEXT = "context"
    FEEDBACK = "feedback"


@dataclass
class ExtractedMemory:
    content: str
    category: MemoryCategory
    importance: float  # 0-1
    source_session_id: str


class MemoryExtractionService:
    """Extracts memorable facts from conversation turns and stores them with deduplication.

    In production, extraction would delegate to an LLM. This implementation
    uses keyword-based heuristics so the service can run without any external
    model dependency.
    """

    _PREFERENCE_SIGNALS: tuple[str, ...] = (
        "prefiero",
        "me gusta",
        "no me gusta",
        "quiero",
        "necesito",
        "prefer",
        "like",
        "want",
    )

    _GOAL_SIGNALS: tuple[str, ...] = (
        "mi objetivo",
        "estoy trabajando en",
        "necesito lograr",
        "my goal",
        "working on",
    )

    _SKILL_SIGNALS: tuple[str, ...] = (
        "sé programar",
        "soy experto",
        "i know how to",
        "i can",
        "skilled in",
        "experienced with",
    )

    _PROJECT_SIGNALS: tuple[str, ...] = (
        "mi proyecto",
        "el proyecto",
        "my project",
        "building",
        "developing",
        "implementing",
    )

    _FEEDBACK_SIGNALS: tuple[str, ...] = (
        "eso estuvo bien",
        "eso estuvo mal",
        "that was",
        "good answer",
        "bad answer",
        "not helpful",
        "very helpful",
    )

    def __init__(
        self,
        similarity_threshold: float = 0.9,
        max_memories: int = 100,
    ) -> None:
        self._threshold = similarity_threshold
        self._max = max_memories
        self._memories: list[ExtractedMemory] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def extract_from_turn(
        self,
        user_msg: str,
        assistant_msg: str,
        session_id: str,
    ) -> list[ExtractedMemory]:
        """Extract memorable facts from a conversation turn.

        In production, this would call an LLM to extract facts.
        For standalone use, heuristic extraction is applied instead.

        Returns at most 3 new (non-duplicate) memories per turn.
        """
        extracted: list[ExtractedMemory] = []
        lower = user_msg.lower()

        # Each category is tried in priority order; we stop appending once we
        # have 3 candidates so the docstring contract is respected.
        _checks: list[tuple[tuple[str, ...], MemoryCategory, float]] = [
            (self._GOAL_SIGNALS, MemoryCategory.GOAL, 0.8),
            (self._PREFERENCE_SIGNALS, MemoryCategory.PREFERENCE, 0.7),
            (self._SKILL_SIGNALS, MemoryCategory.SKILL, 0.75),
            (self._PROJECT_SIGNALS, MemoryCategory.PROJECT, 0.65),
            (self._FEEDBACK_SIGNALS, MemoryCategory.FEEDBACK, 0.6),
        ]

        for signals, category, importance in _checks:
            if len(extracted) >= 3:
                break
            for signal in signals:
                if signal in lower:
                    extracted.append(
                        ExtractedMemory(
                            content=user_msg,
                            category=category,
                            importance=importance,
                            source_session_id=session_id,
                        )
                    )
                    break  # one memory per category per turn

        # Deduplicate against already-stored memories
        deduped = [m for m in extracted if not self._is_duplicate(m)]

        # Persist (respecting the cap)
        for m in deduped:
            if len(self._memories) < self._max:
                self._memories.append(m)
                logger.debug(
                    "Stored memory category=%s session=%s",
                    m.category,
                    m.source_session_id,
                )

        return deduped

    def get_relevant_memories(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[ExtractedMemory]:
        """Return the most relevant memories for context injection.

        Uses keyword-overlap weighted by importance score. In production
        this should be replaced with vector/embedding similarity search.
        """
        query_words = set(query.lower().split())
        scored: list[tuple[float, ExtractedMemory]] = []

        for m in self._memories:
            mem_words = set(m.content.lower().split())
            overlap = len(query_words & mem_words)
            scored.append((overlap * m.importance, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]

    def clear(self) -> None:
        """Remove all stored memories (useful for testing / session resets)."""
        self._memories.clear()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def memory_count(self) -> int:
        """Total number of stored memories."""
        return len(self._memories)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_duplicate(self, new: ExtractedMemory) -> bool:
        """Return True when *new* is too similar to an already-stored memory.

        Uses Jaccard similarity on word sets as a simple proxy for semantic
        overlap. In production, embedding cosine similarity should be used.
        """
        for existing in self._memories:
            if existing.category != new.category:
                continue
            words_a = set(existing.content.lower().split())
            words_b = set(new.content.lower().split())
            if not words_a or not words_b:
                continue
            similarity = len(words_a & words_b) / len(words_a | words_b)
            if similarity >= self._threshold:
                return True
        return False
