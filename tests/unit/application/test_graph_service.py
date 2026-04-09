"""Unit tests for GraphService graceful degradation.

All mocks are plain Python objects — no FalkorDB or pgvector packages needed.
"""
from __future__ import annotations

import time
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

from agentic_core.application.services.graph_service import GraphService

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph_port(result: list[dict[str, Any]] | None = None, raises: Exception | None = None) -> MagicMock:
    """Return a mock graph port whose ``execute_query`` is an AsyncMock."""
    port = MagicMock()
    if raises is not None:
        port.execute_query = AsyncMock(side_effect=raises)
    else:
        port.execute_query = AsyncMock(return_value=result or [])
    return port


def _make_embedding_port(
    results: list[Any] | None = None, raises: Exception | None = None
) -> MagicMock:
    """Return a mock embedding port whose ``search`` is an AsyncMock.

    Each item in *results* should expose ``.text``, ``.score``, and
    ``.metadata`` attributes (mirrors ``SearchResult``).
    """
    port = MagicMock()
    if raises is not None:
        port.search = AsyncMock(side_effect=raises)
    else:
        items = results or []
        port.search = AsyncMock(return_value=items)
    return port


def _make_search_result(text: str, score: float, metadata: dict[str, Any] | None = None) -> SimpleNamespace:
    """Minimal SearchResult-like object."""
    return SimpleNamespace(text=text, score=score, metadata=metadata or {})


# ---------------------------------------------------------------------------
# 1. Graph query succeeds normally
# ---------------------------------------------------------------------------


async def test_graph_query_success() -> None:
    expected = [{"id": "node1", "label": "Entity"}]
    graph = _make_graph_port(result=expected)
    svc = GraphService(graph_port=graph)

    result = await svc.query("MATCH (n) RETURN n")

    assert result == expected
    graph.execute_query.assert_awaited_once_with("MATCH (n) RETURN n", {})


async def test_graph_query_passes_params() -> None:
    graph = _make_graph_port(result=[{"x": 1}])
    svc = GraphService(graph_port=graph)

    await svc.query("MATCH (n {id: $id}) RETURN n", params={"id": "abc"})

    graph.execute_query.assert_awaited_once_with("MATCH (n {id: $id}) RETURN n", {"id": "abc"})


async def test_graph_query_returns_empty_list_on_no_results() -> None:
    graph = _make_graph_port(result=[])
    svc = GraphService(graph_port=graph)

    result = await svc.query("MATCH (n) RETURN n")

    assert result == []


# ---------------------------------------------------------------------------
# 2. Fallback to vector search when graph fails
# ---------------------------------------------------------------------------


async def test_fallback_to_vector_on_graph_error() -> None:
    graph = _make_graph_port(raises=ConnectionError("falkordb down"))
    vec_results = [_make_search_result("some text", 0.9)]
    embedding = _make_embedding_port(results=vec_results)

    svc = GraphService(graph_port=graph, embedding_port=embedding)

    result = await svc.query("MATCH (n) RETURN n")

    assert len(result) == 1
    assert result[0]["source"] == "vector_fallback"
    assert result[0]["content"] == "some text"
    assert result[0]["score"] == 0.9


async def test_fallback_result_maps_none_text_to_empty_string() -> None:
    graph = _make_graph_port(raises=RuntimeError("oops"))
    vec_results = [_make_search_result(None, 0.5)]  # type: ignore[arg-type]
    embedding = _make_embedding_port(results=vec_results)

    svc = GraphService(graph_port=graph, embedding_port=embedding)

    result = await svc.query("q")

    assert result[0]["content"] == ""


async def test_graph_marked_unavailable_after_failure() -> None:
    graph = _make_graph_port(raises=OSError("connection refused"))
    svc = GraphService(graph_port=graph, cooldown_seconds=60)

    await svc.query("MATCH (n) RETURN n")

    assert svc.is_graph_available is False


async def test_subsequent_call_uses_vector_without_retrying_graph() -> None:
    graph = _make_graph_port(raises=OSError("down"))
    embedding = _make_embedding_port(results=[_make_search_result("doc", 0.7)])

    svc = GraphService(graph_port=graph, embedding_port=embedding, cooldown_seconds=60)

    # First call triggers the failure.
    await svc.query("q1")
    # Second call: graph still in cooldown, should NOT call execute_query again.
    await svc.query("q2")

    # execute_query was only called once (on the first attempt).
    assert graph.execute_query.await_count == 1
    assert embedding.search.await_count == 2


# ---------------------------------------------------------------------------
# 3. Cooldown and auto-reconnect
# ---------------------------------------------------------------------------


async def test_graph_retried_after_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = _make_graph_port(raises=OSError("down"))
    svc = GraphService(graph_port=graph, cooldown_seconds=10)

    # Trigger failure.
    await svc.query("q")
    assert svc.is_graph_available is False

    # Fix the graph mock so it succeeds on retry.
    graph.execute_query = AsyncMock(return_value=[{"recovered": True}])

    # Simulate time passing beyond the cooldown.
    future_time = svc._last_failure + 11.0
    monkeypatch.setattr(time, "monotonic", lambda: future_time)

    result = await svc.query("q2")

    assert svc.is_graph_available is True
    assert result == [{"recovered": True}]


async def test_graph_not_retried_before_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = _make_graph_port(raises=OSError("down"))
    embedding = _make_embedding_port(results=[])
    svc = GraphService(graph_port=graph, embedding_port=embedding, cooldown_seconds=30)

    # Trigger failure.
    await svc.query("q")

    # Advance time by only 5 seconds (within cooldown).
    near_time = svc._last_failure + 5.0
    monkeypatch.setattr(time, "monotonic", lambda: near_time)

    await svc.query("q2")

    # execute_query still only called once — cooldown not yet expired.
    assert graph.execute_query.await_count == 1
    assert svc.is_graph_available is False


async def test_graph_failure_on_reconnect_resets_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the retry after cooldown also fails, cooldown clock resets."""
    graph = _make_graph_port(raises=OSError("still down"))
    embedding = _make_embedding_port(results=[])
    svc = GraphService(graph_port=graph, embedding_port=embedding, cooldown_seconds=10)

    # First failure.
    await svc.query("q1")
    first_failure = svc._last_failure

    # Advance past cooldown so retry is attempted.
    monkeypatch.setattr(time, "monotonic", lambda: first_failure + 15.0)

    # Retry — graph still fails.
    await svc.query("q2")

    # Cooldown clock should have been reset to the new failure time.
    assert svc._last_failure > first_failure
    assert svc.is_graph_available is False


# ---------------------------------------------------------------------------
# 4. Both backends down — return empty list
# ---------------------------------------------------------------------------


async def test_both_backends_down_returns_empty() -> None:
    graph = _make_graph_port(raises=OSError("graph down"))
    embedding = _make_embedding_port(raises=RuntimeError("vector down"))

    svc = GraphService(graph_port=graph, embedding_port=embedding)

    result = await svc.query("q")

    assert result == []


async def test_no_backends_configured_returns_empty() -> None:
    svc = GraphService()

    result = await svc.query("q")

    assert result == []


async def test_graph_only_no_embedding_on_failure_returns_empty() -> None:
    graph = _make_graph_port(raises=OSError("down"))
    svc = GraphService(graph_port=graph, embedding_port=None)

    result = await svc.query("q")

    assert result == []


# ---------------------------------------------------------------------------
# 5. Backend property reflects current state
# ---------------------------------------------------------------------------


def test_backend_is_falkordb_when_graph_available() -> None:
    svc = GraphService(graph_port=MagicMock(), embedding_port=MagicMock())
    assert svc.backend == "falkordb"


def test_backend_is_pgvector_fallback_when_graph_unavailable() -> None:
    svc = GraphService(graph_port=MagicMock(), embedding_port=MagicMock())
    svc._graph_available = False
    assert svc.backend == "pgvector_fallback"


def test_backend_is_none_when_no_ports() -> None:
    svc = GraphService()
    assert svc.backend == "none"


def test_backend_is_none_when_graph_unavailable_and_no_embedding() -> None:
    svc = GraphService(graph_port=MagicMock(), embedding_port=None)
    svc._graph_available = False
    assert svc.backend == "none"


def test_backend_is_falkordb_when_graph_available_and_no_embedding() -> None:
    svc = GraphService(graph_port=MagicMock(), embedding_port=None)
    assert svc.backend == "falkordb"


def test_is_graph_available_default_true() -> None:
    svc = GraphService()
    assert svc.is_graph_available is True


# ---------------------------------------------------------------------------
# 6. Logging is emitted on degradation events
# ---------------------------------------------------------------------------


async def test_degradation_warning_logged(caplog: pytest.LogCaptureFixture) -> None:
    graph = _make_graph_port(raises=RuntimeError("boom"))
    embedding = _make_embedding_port(results=[])
    svc = GraphService(graph_port=graph, embedding_port=embedding)

    with caplog.at_level("WARNING", logger="agentic_core.application.services.graph_service"):
        await svc.query("q")

    assert any("FalkorDB" in record.message for record in caplog.records)


async def test_reconnect_info_logged(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    graph = _make_graph_port(raises=OSError("down"))
    svc = GraphService(graph_port=graph, cooldown_seconds=5)

    await svc.query("q1")

    # Fix mock so retry succeeds.
    graph.execute_query = AsyncMock(return_value=[])
    monkeypatch.setattr(time, "monotonic", lambda: svc._last_failure + 10.0)

    with caplog.at_level("INFO", logger="agentic_core.application.services.graph_service"):
        await svc.query("q2")

    assert any("cooldown" in record.message.lower() for record in caplog.records)
