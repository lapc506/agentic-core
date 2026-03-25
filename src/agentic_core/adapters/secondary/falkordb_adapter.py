from __future__ import annotations

import logging
from typing import Any

from agentic_core.application.ports.graph_store import GraphStorePort

logger = logging.getLogger(__name__)


class FalkorDBAdapter(GraphStorePort):
    """FalkorDB-backed knowledge graph for entity relations."""

    def __init__(self, url: str, graph_name: str = "agent_knowledge") -> None:
        self._url = url
        self._graph_name = graph_name
        self._client: Any = None
        self._graph: Any = None

    async def connect(self) -> None:
        from falkordb import FalkorDB
        self._client = FalkorDB.from_url(self._url)
        self._graph = self._client.select_graph(self._graph_name)
        logger.info("FalkorDB connected: %s (graph: %s)", self._url, self._graph_name)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            logger.info("FalkorDB connection closed")

    async def store_entity(self, entity: dict[str, Any], relations: list[dict[str, Any]]) -> None:
        entity_id = entity.get("id", "unknown")
        entity_type = entity.get("type", "Entity")
        props = {k: v for k, v in entity.items() if k not in ("id", "type")}
        props_str = ", ".join(f'{k}: "{v}"' for k, v in props.items())

        self._graph.query(
            f'MERGE (e:{entity_type} {{id: "{entity_id}", {props_str}}})'
        )

        for rel in relations:
            target_id = rel.get("target_id", "unknown")
            target_type = rel.get("target_type", "Entity")
            rel_type = rel.get("relation", "RELATED_TO")
            self._graph.query(
                f'MATCH (a:{entity_type} {{id: "{entity_id}"}}) '
                f'MERGE (b:{target_type} {{id: "{target_id}"}}) '
                f'MERGE (a)-[:{rel_type}]->(b)'
            )

    async def query(self, cypher: str) -> list[dict[str, Any]]:
        result = self._graph.query(cypher)
        rows: list[dict[str, Any]] = []
        if result.result_set:
            headers = result.header
            for row in result.result_set:
                rows.append(dict(zip(headers, row)))
        return rows
