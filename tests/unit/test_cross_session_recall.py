from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agentic_core.application.ports.recall import RecallMatch, RecallPort
from agentic_core.application.services.cross_session_recall import (
    CrossSessionRecall,
    RecallQuery,
    RecallResult,
)

# ---------------------------------------------------------------------------
# Fake adapter
# ---------------------------------------------------------------------------

class FakeRecallPort(RecallPort):
    """In-memory implementation for testing."""

    def __init__(self, canned: list[RecallMatch] | None = None) -> None:
        self.canned = canned or []
        self.stored: list[dict[str, object]] = []

    async def search_sessions(
        self,
        query: str,
        persona_id: str | None = None,
        limit: int = 10,
    ) -> list[RecallMatch]:
        results = self.canned
        if persona_id is not None:
            results = [r for r in results if True]  # fake: no persona filtering
        return results[:limit]

    async def store_message(
        self,
        session_id: str,
        persona_id: str,
        content: str,
        timestamp: datetime,
    ) -> None:
        self.stored.append(
            {
                "session_id": session_id,
                "persona_id": persona_id,
                "content": content,
                "timestamp": timestamp,
            }
        )


# ---------------------------------------------------------------------------
# Value-object construction
# ---------------------------------------------------------------------------

_TS = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)


def _match(session_id: str = "s1", content: str = "hello", score: float = 0.9) -> RecallMatch:
    return RecallMatch(
        session_id=session_id,
        content=content,
        relevance_score=score,
        timestamp=_TS,
    )


class TestRecallQueryConstruction:
    def test_defaults(self) -> None:
        q = RecallQuery(query="test")
        assert q.query == "test"
        assert q.session_id is None
        assert q.persona_id is None
        assert q.limit == 10

    def test_with_filters(self) -> None:
        q = RecallQuery(query="x", session_id="s1", persona_id="p1", limit=5)
        assert q.session_id == "s1"
        assert q.persona_id == "p1"
        assert q.limit == 5


class TestRecallResultConstruction:
    def test_empty(self) -> None:
        r = RecallResult()
        assert r.is_empty
        assert r.matches == []

    def test_with_matches(self) -> None:
        m = _match()
        r = RecallResult(matches=[m])
        assert not r.is_empty
        assert r.matches[0].session_id == "s1"


class TestRecallMatchFrozen:
    def test_immutable(self) -> None:
        m = _match()
        with pytest.raises(Exception):
            m.content = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CrossSessionRecall.search
# ---------------------------------------------------------------------------

class TestCrossSessionRecallSearch:
    @pytest.mark.asyncio
    async def test_basic_search(self) -> None:
        port = FakeRecallPort(canned=[_match()])
        recall = CrossSessionRecall(port)
        result = await recall.search(RecallQuery(query="hello"))
        assert len(result.matches) == 1
        assert result.matches[0].content == "hello"

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        port = FakeRecallPort(canned=[])
        recall = CrossSessionRecall(port)
        result = await recall.search(RecallQuery(query="nothing"))
        assert result.is_empty

    @pytest.mark.asyncio
    async def test_session_id_filter(self) -> None:
        port = FakeRecallPort(
            canned=[
                _match(session_id="s1", content="a"),
                _match(session_id="s2", content="b"),
            ]
        )
        recall = CrossSessionRecall(port)
        result = await recall.search(RecallQuery(query="x", session_id="s1"))
        assert len(result.matches) == 1
        assert result.matches[0].session_id == "s1"

    @pytest.mark.asyncio
    async def test_limit_respected(self) -> None:
        port = FakeRecallPort(
            canned=[_match(content=f"m{i}") for i in range(20)]
        )
        recall = CrossSessionRecall(port)
        result = await recall.search(RecallQuery(query="x", limit=3))
        assert len(result.matches) == 3


# ---------------------------------------------------------------------------
# CrossSessionRecall.summarize
# ---------------------------------------------------------------------------

class TestCrossSessionRecallSummarize:
    @pytest.mark.asyncio
    async def test_empty_sessions_list(self) -> None:
        port = FakeRecallPort()
        recall = CrossSessionRecall(port)
        summary = await recall.summarize([])
        assert summary == ""

    @pytest.mark.asyncio
    async def test_no_matching_messages(self) -> None:
        port = FakeRecallPort(canned=[])
        recall = CrossSessionRecall(port)
        summary = await recall.summarize(["s1"])
        assert summary == ""

    @pytest.mark.asyncio
    async def test_placeholder_summary(self) -> None:
        port = FakeRecallPort(
            canned=[
                _match(session_id="s1", content="First message"),
                _match(session_id="s1", content="Second message"),
            ]
        )
        recall = CrossSessionRecall(port)
        summary = await recall.summarize(["s1"])
        assert "placeholder" in summary.lower()
        assert "1 session" in summary
        assert "First message" in summary


# ---------------------------------------------------------------------------
# RecallPort.store_message via fake
# ---------------------------------------------------------------------------

class TestRecallPortStore:
    @pytest.mark.asyncio
    async def test_store_message(self) -> None:
        port = FakeRecallPort()
        await port.store_message("s1", "p1", "hi", _TS)
        assert len(port.stored) == 1
        assert port.stored[0]["content"] == "hi"
