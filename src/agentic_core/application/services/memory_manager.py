"""Memory Manager — dual-layer (hot/cold) with graph entity extraction."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """An entity extracted from conversation."""

    name: str
    entity_type: str  # person, organization, tool, concept, location
    mentions: int = 1


@dataclass
class Relationship:
    """A relationship between two entities."""

    source: str
    target: str
    relation: str  # uses, works_at, knows, created, depends_on
    weight: float = 1.0


@dataclass
class MemoryContext:
    """Combined memory context for injection into LLM prompt."""

    hot_messages: list[dict[str, str]]  # Recent conversation turns
    cold_facts: list[str]  # Retrieved from vector/graph DB
    entities: list[Entity]  # Known entities for this user
    summary: str = ""  # Compressed context summary


class MemoryManager:
    """Manages dual-layer memory with graph entity extraction.

    Hot path: recent messages, kept in-memory per session.
    Cold path: retrieved from external stores (async, never blocks).
    Graph path: entities and relationships extracted and stored.
    """

    MAX_HOT_MESSAGES = 20
    SUMMARY_THRESHOLD = 15  # Summarize when hot messages exceed this

    def __init__(
        self,
        graph_store: Any = None,  # GraphStorePort
        vector_store: Any = None,  # EmbeddingStorePort
        memory_service: Any = None,  # MemoryExtractionService
    ) -> None:
        self._graph = graph_store
        self._vector = vector_store
        self._memory = memory_service
        self._sessions: dict[str, list[dict[str, str]]] = {}
        self._entities: dict[str, dict[str, Entity]] = {}  # session_id -> {name: Entity}
        self._summaries: dict[str, str] = {}

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to the hot path (synchronous, fast)."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": role, "content": content})

        # Trim hot messages if needed
        if len(self._sessions[session_id]) > self.MAX_HOT_MESSAGES:
            self._sessions[session_id] = self._sessions[session_id][-self.MAX_HOT_MESSAGES :]

    def get_hot_context(self, session_id: str) -> list[dict[str, str]]:
        """Get recent messages (hot path, instant)."""
        return self._sessions.get(session_id, [])

    async def get_full_context(self, session_id: str, query: str) -> MemoryContext:
        """Get combined hot + cold context (async retrieval)."""
        hot = self.get_hot_context(session_id)

        # Cold path: retrieve in parallel (never blocks if stores unavailable)
        cold_facts: list[str] = []

        cold_tasks = []
        if self._vector:
            cold_tasks.append(self._retrieve_vector(query))
        if self._graph:
            cold_tasks.append(self._retrieve_graph(query))

        if cold_tasks:
            results = await asyncio.gather(*cold_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    cold_facts.extend(result)
                elif isinstance(result, Exception):
                    logger.warning("Cold path retrieval failed: %s", result)

        # Get known entities for this session
        session_entities = list(self._entities.get(session_id, {}).values())

        return MemoryContext(
            hot_messages=hot,
            cold_facts=cold_facts,
            entities=session_entities,
            summary=self._summaries.get(session_id, ""),
        )

    async def process_turn_async(
        self, session_id: str, user_msg: str, assistant_msg: str
    ) -> None:
        """Async post-turn processing: entity extraction + memory storage.

        This should be called fire-and-forget from the hook pipeline.
        NEVER blocks the response to the user.
        """
        try:
            # Extract entities
            entities = self._extract_entities(user_msg + " " + assistant_msg)
            if session_id not in self._entities:
                self._entities[session_id] = {}
            for entity in entities:
                if entity.name in self._entities[session_id]:
                    self._entities[session_id][entity.name].mentions += 1
                else:
                    self._entities[session_id][entity.name] = entity

            # Extract relationships
            relationships = self._extract_relationships(
                entities, user_msg + " " + assistant_msg
            )

            # Store to graph (fire-and-forget)
            if self._graph and (entities or relationships):
                try:
                    await self._store_graph(entities, relationships)
                except Exception:
                    logger.warning("Graph storage failed (graceful degradation)")

            # Extract memories via memory service
            if self._memory:
                try:
                    await self._memory.extract_from_turn(user_msg, assistant_msg, session_id)
                except Exception:
                    logger.warning("Memory extraction failed (graceful degradation)")

        except Exception:
            logger.exception("Async turn processing failed")

    def _extract_entities(self, text: str) -> list[Entity]:
        """Heuristic entity extraction (production: use NER model)."""
        entities: list[Entity] = []

        # Detect capitalized multi-word names (simple heuristic)
        name_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
        for match in name_pattern.finditer(text):
            entities.append(Entity(name=match.group(), entity_type="person"))

        # Detect tool names (lowercase-with-hyphens pattern)
        tool_pattern = re.compile(r"\b([a-z]+-[a-z]+(?:-[a-z]+)*)\b")
        for match in tool_pattern.finditer(text):
            name = match.group()
            if len(name) > 4:  # Filter short matches
                entities.append(Entity(name=name, entity_type="tool"))

        # Detect URLs as entities
        url_pattern = re.compile(r"https?://[^\s]+")
        for match in url_pattern.finditer(text):
            entities.append(Entity(name=match.group(), entity_type="reference"))

        # Deduplicate
        seen: set[str] = set()
        deduped: list[Entity] = []
        for e in entities:
            key = e.name.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(e)

        return deduped

    def _extract_relationships(
        self, entities: list[Entity], text: str
    ) -> list[Relationship]:
        """Heuristic relationship extraction between entities."""
        relationships: list[Relationship] = []
        text_lower = text.lower()

        relation_signals: dict[str, list[str]] = {
            "uses": ["uses", "using", "used", "utiliza", "usa"],
            "knows": ["knows", "familiar with", "conoce"],
            "works_at": ["works at", "employed by", "trabaja en"],
            "depends_on": ["depends on", "requires", "needs", "depende de", "necesita"],
            "created": ["created", "built", "made", "creó", "construyó"],
        }

        for i, src in enumerate(entities):
            for j, tgt in enumerate(entities):
                if i >= j:
                    continue
                for relation, signals in relation_signals.items():
                    for signal in signals:
                        if (
                            signal in text_lower
                            and src.name.lower() in text_lower
                            and tgt.name.lower() in text_lower
                        ):
                            relationships.append(
                                Relationship(
                                    source=src.name,
                                    target=tgt.name,
                                    relation=relation,
                                )
                            )
                            break

        return relationships

    async def _retrieve_vector(self, query: str) -> list[str]:
        """Retrieve relevant facts from vector store."""
        # Placeholder — in production, embed query and search pgvector
        return []

    async def _retrieve_graph(self, query: str) -> list[str]:
        """Retrieve relevant facts from graph store."""
        # Placeholder — in production, extract entities from query and traverse graph
        return []

    async def _store_graph(
        self, entities: list[Entity], relationships: list[Relationship]
    ) -> None:
        """Store entities and relationships in graph DB."""
        # Placeholder — in production, create/merge nodes and edges in FalkorDB
        logger.debug(
            "Would store %d entities and %d relationships",
            len(entities),
            len(relationships),
        )

    @property
    def session_count(self) -> int:
        return len(self._sessions)
