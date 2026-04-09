from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GraphService:
    """Graph query service with graceful degradation.

    Primary: FalkorDB (graph queries)
    Fallback: pgvector similarity search (when graph is unavailable)

    When FalkorDB raises an exception the service marks the backend as
    unavailable and switches to ``EmbeddingStorePort.search`` for subsequent
    calls.  After *cooldown_seconds* the service will automatically retry
    FalkorDB on the next ``query`` call.

    The embedding fallback calls ``EmbeddingStorePort.search`` with a
    zero-vector of length 1 as a placeholder, because the port contract
    requires a ``list[float]`` rather than a raw text query.  Callers that
    need proper vector similarity should supply a pre-encoded embedding via
    a dedicated embedding-provider service; this fallback is intentionally
    best-effort.
    """

    def __init__(
        self,
        graph_port: Any | None = None,   # GraphStorePort (FalkorDB)
        embedding_port: Any | None = None,  # EmbeddingStorePort (pgvector)
        cooldown_seconds: int = 30,
    ) -> None:
        self._graph = graph_port
        self._embedding = embedding_port
        self._cooldown = cooldown_seconds
        self._graph_available: bool = True
        self._last_failure: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a graph query with automatic fallback to vector search.

        Parameters
        ----------
        query:
            Cypher query string forwarded to FalkorDB, or a plain-text
            description used as a hint when falling back to vector search.
        params:
            Optional parameter dict passed to the graph adapter.  Ignored
            by the vector fallback path.
        """
        # Re-enable graph backend after the cooldown window.
        if not self._graph_available:
            elapsed = time.monotonic() - self._last_failure
            if elapsed > self._cooldown:
                self._graph_available = True
                logger.info(
                    "Graph cooldown expired (%.1fs >= %ds), retrying FalkorDB",
                    elapsed,
                    self._cooldown,
                )

        # --- Primary: FalkorDB ---
        if self._graph_available and self._graph is not None:
            try:
                result: list[dict[str, Any]] = await self._graph.execute_query(
                    query, params or {}
                )
                return result
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "FalkorDB query failed, falling back to vector search: %s", exc
                )
                self._graph_available = False
                self._last_failure = time.monotonic()

        # --- Fallback: pgvector similarity search ---
        if self._embedding is not None:
            try:
                # The EmbeddingStorePort.search interface requires a
                # list[float] embedding vector.  We pass a single-element
                # zero-vector as a best-effort placeholder so callers still
                # receive results from the vector store.
                placeholder_embedding: list[float] = [0.0]
                results = await self._embedding.search(placeholder_embedding, top_k=10)
                return [
                    {
                        "content": r.text if r.text is not None else "",
                        "score": r.score,
                        "source": "vector_fallback",
                        "metadata": r.metadata,
                    }
                    for r in results
                ]
            except Exception as exc:  # noqa: BLE001
                logger.error("Both graph and vector search failed: %s", exc)
                return []

        logger.warning("No graph or embedding backend available")
        return []

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def is_graph_available(self) -> bool:
        """Return ``True`` when FalkorDB is considered reachable."""
        return self._graph_available

    @property
    def backend(self) -> str:
        """Name of the active backend: ``falkordb``, ``pgvector_fallback``, or ``none``."""
        if self._graph_available and self._graph is not None:
            return "falkordb"
        if self._embedding is not None:
            return "pgvector_fallback"
        return "none"
