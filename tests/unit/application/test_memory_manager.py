"""Tests for MemoryManager — dual-layer (hot/cold) with graph entity extraction."""

from __future__ import annotations

import pytest

from agentic_core.application.services.memory_manager import (
    Entity,
    MemoryContext,
    MemoryManager,
    Relationship,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

SESSION = "session-test-001"
SESSION_B = "session-test-002"


def make_manager(**kwargs: object) -> MemoryManager:
    return MemoryManager(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# add_message — hot path writes
# ---------------------------------------------------------------------------


def test_add_message_single_message_stored():
    mgr = make_manager()
    mgr.add_message(SESSION, "user", "Hello!")
    hot = mgr.get_hot_context(SESSION)
    assert len(hot) == 1
    assert hot[0] == {"role": "user", "content": "Hello!"}


def test_add_message_multiple_messages_ordered():
    mgr = make_manager()
    mgr.add_message(SESSION, "user", "First")
    mgr.add_message(SESSION, "assistant", "Second")
    mgr.add_message(SESSION, "user", "Third")
    hot = mgr.get_hot_context(SESSION)
    assert [m["content"] for m in hot] == ["First", "Second", "Third"]


def test_add_message_role_preserved():
    mgr = make_manager()
    mgr.add_message(SESSION, "user", "Ping")
    mgr.add_message(SESSION, "assistant", "Pong")
    hot = mgr.get_hot_context(SESSION)
    assert hot[0]["role"] == "user"
    assert hot[1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# get_hot_context — retrieval
# ---------------------------------------------------------------------------


def test_get_hot_context_unknown_session_returns_empty_list():
    mgr = make_manager()
    assert mgr.get_hot_context("nonexistent-session") == []


def test_get_hot_context_independent_per_session():
    mgr = make_manager()
    mgr.add_message(SESSION, "user", "Alpha")
    mgr.add_message(SESSION_B, "user", "Beta")
    assert mgr.get_hot_context(SESSION)[0]["content"] == "Alpha"
    assert mgr.get_hot_context(SESSION_B)[0]["content"] == "Beta"


# ---------------------------------------------------------------------------
# Hot context trimming
# ---------------------------------------------------------------------------


def test_hot_context_trimmed_at_max():
    mgr = make_manager()
    limit = MemoryManager.MAX_HOT_MESSAGES
    for i in range(limit + 5):
        mgr.add_message(SESSION, "user", f"msg-{i}")
    hot = mgr.get_hot_context(SESSION)
    assert len(hot) == limit


def test_hot_context_keeps_most_recent_after_trim():
    mgr = make_manager()
    limit = MemoryManager.MAX_HOT_MESSAGES
    for i in range(limit + 3):
        mgr.add_message(SESSION, "user", f"msg-{i}")
    hot = mgr.get_hot_context(SESSION)
    # The last message index is (limit+2); first retained index is 3
    assert hot[-1]["content"] == f"msg-{limit + 2}"
    assert hot[0]["content"] == "msg-3"


# ---------------------------------------------------------------------------
# session_count property
# ---------------------------------------------------------------------------


def test_session_count_starts_at_zero():
    mgr = make_manager()
    assert mgr.session_count == 0


def test_session_count_increments_per_new_session():
    mgr = make_manager()
    mgr.add_message(SESSION, "user", "hi")
    mgr.add_message(SESSION_B, "user", "hey")
    assert mgr.session_count == 2


def test_session_count_does_not_increment_for_same_session():
    mgr = make_manager()
    mgr.add_message(SESSION, "user", "first")
    mgr.add_message(SESSION, "user", "second")
    assert mgr.session_count == 1


# ---------------------------------------------------------------------------
# Entity extraction — capitalized names
# ---------------------------------------------------------------------------


def test_extract_entities_detects_person_names():
    mgr = make_manager()
    entities = mgr._extract_entities("John Smith and Mary Johnson were talking")
    names = [e.name for e in entities]
    assert "John Smith" in names
    assert "Mary Johnson" in names


def test_extract_entities_person_type():
    mgr = make_manager()
    entities = mgr._extract_entities("Peter Pan visited Never Land")
    person_entities = [e for e in entities if e.entity_type == "person"]
    assert len(person_entities) >= 1


def test_extract_entities_detects_tool_names():
    mgr = make_manager()
    entities = mgr._extract_entities("We use langchain-core and open-ai in this project")
    names = [e.name for e in entities]
    assert "langchain-core" in names
    assert "open-ai" in names


def test_extract_entities_tool_type():
    mgr = make_manager()
    entities = mgr._extract_entities("using falkor-db for storage")
    tool_entities = [e for e in entities if e.entity_type == "tool"]
    assert len(tool_entities) >= 1


def test_extract_entities_filters_short_tool_names():
    mgr = make_manager()
    # "a-b" has length 3 — should be filtered out
    entities = mgr._extract_entities("the a-b component is irrelevant")
    tool_entities = [e for e in entities if e.entity_type == "tool"]
    short_names = [e for e in tool_entities if e.name == "a-b"]
    assert len(short_names) == 0


def test_extract_entities_detects_urls():
    mgr = make_manager()
    entities = mgr._extract_entities("Check https://example.com/api for docs")
    ref_entities = [e for e in entities if e.entity_type == "reference"]
    assert len(ref_entities) == 1
    assert "https://example.com/api" in ref_entities[0].name


# ---------------------------------------------------------------------------
# Entity extraction — deduplication
# ---------------------------------------------------------------------------


def test_extract_entities_deduplicates_case_insensitive():
    mgr = make_manager()
    # "langchain-core" appears twice; should appear once in result
    entities = mgr._extract_entities("langchain-core is great; I love langchain-core")
    tool_entities = [e for e in entities if e.name == "langchain-core"]
    assert len(tool_entities) == 1


def test_extract_entities_deduplicates_capitalized_names():
    mgr = make_manager()
    entities = mgr._extract_entities("John Smith talked to John Smith again")
    person_entities = [e for e in entities if e.name == "John Smith"]
    assert len(person_entities) == 1


def test_extract_entities_empty_text_returns_empty():
    mgr = make_manager()
    entities = mgr._extract_entities("")
    assert entities == []


# ---------------------------------------------------------------------------
# Relationship extraction
# ---------------------------------------------------------------------------


def test_extract_relationships_detects_uses():
    mgr = make_manager()
    text = "Alice Smith uses langchain-core for her project"
    entities = mgr._extract_entities(text)
    relationships = mgr._extract_relationships(entities, text)
    relations = [r.relation for r in relationships]
    assert "uses" in relations


def test_extract_relationships_detects_depends_on():
    mgr = make_manager()
    text = "agentic-core depends on langchain-core library"
    entities = mgr._extract_entities(text)
    relationships = mgr._extract_relationships(entities, text)
    relations = [r.relation for r in relationships]
    assert "depends_on" in relations


def test_extract_relationships_source_and_target_set():
    mgr = make_manager()
    text = "John Smith created open-source software"
    entities = mgr._extract_entities(text)
    relationships = mgr._extract_relationships(entities, text)
    if relationships:
        rel = relationships[0]
        assert rel.source != ""
        assert rel.target != ""


def test_extract_relationships_no_entities_returns_empty():
    mgr = make_manager()
    relationships = mgr._extract_relationships([], "some text without entities")
    assert relationships == []


def test_extract_relationships_single_entity_returns_empty():
    mgr = make_manager()
    entities = [Entity(name="solo-entity", entity_type="tool")]
    relationships = mgr._extract_relationships(entities, "solo-entity uses nothing")
    assert relationships == []


# ---------------------------------------------------------------------------
# process_turn_async — entity accumulation
# ---------------------------------------------------------------------------


async def test_process_turn_async_accumulates_entities():
    mgr = make_manager()
    await mgr.process_turn_async(SESSION, "John Smith asked about langchain-core", "Sure!")
    session_entities = mgr._entities.get(SESSION, {})
    assert "John Smith" in session_entities


async def test_process_turn_async_increments_mention_count():
    mgr = make_manager()
    await mgr.process_turn_async(SESSION, "langchain-core is a tool", "Yes.")
    await mgr.process_turn_async(SESSION, "langchain-core rocks", "Agreed.")
    count = mgr._entities[SESSION]["langchain-core"].mentions
    assert count >= 2


async def test_process_turn_async_initializes_session_entities():
    mgr = make_manager()
    assert SESSION not in mgr._entities
    await mgr.process_turn_async(SESSION, "John Smith arrived", "Hello John Smith!")
    assert SESSION in mgr._entities


# ---------------------------------------------------------------------------
# process_turn_async — graceful degradation
# ---------------------------------------------------------------------------


async def test_process_turn_async_graph_failure_is_non_fatal():
    class FailingGraph:
        async def store_entity(self, *a: object, **kw: object) -> None:
            raise RuntimeError("graph down")

    mgr = make_manager(graph_store=FailingGraph())
    # Must not raise despite graph failure
    await mgr.process_turn_async(SESSION, "John Smith uses open-api", "OK")


async def test_process_turn_async_memory_service_failure_is_non_fatal():
    class FailingMemory:
        async def extract_from_turn(self, *a: object, **kw: object) -> None:
            raise RuntimeError("memory service down")

    mgr = make_manager(memory_service=FailingMemory())
    # Must not raise despite memory service failure
    await mgr.process_turn_async(SESSION, "I prefer Python", "Good choice!")


# ---------------------------------------------------------------------------
# get_full_context — hot+cold assembly
# ---------------------------------------------------------------------------


async def test_get_full_context_returns_memory_context():
    mgr = make_manager()
    mgr.add_message(SESSION, "user", "Hello")
    ctx = await mgr.get_full_context(SESSION, "Hello")
    assert isinstance(ctx, MemoryContext)


async def test_get_full_context_hot_messages_populated():
    mgr = make_manager()
    mgr.add_message(SESSION, "user", "Tell me about Python")
    mgr.add_message(SESSION, "assistant", "Python is a language")
    ctx = await mgr.get_full_context(SESSION, "Python")
    assert len(ctx.hot_messages) == 2
    assert ctx.hot_messages[0]["content"] == "Tell me about Python"


async def test_get_full_context_entities_populated_after_process_turn():
    mgr = make_manager()
    await mgr.process_turn_async(SESSION, "John Smith works at open-corp", "Got it!")
    ctx = await mgr.get_full_context(SESSION, "John Smith")
    entity_names = [e.name for e in ctx.entities]
    assert "John Smith" in entity_names


async def test_get_full_context_cold_facts_empty_without_stores():
    mgr = make_manager()
    ctx = await mgr.get_full_context(SESSION, "anything")
    assert ctx.cold_facts == []


async def test_get_full_context_summary_defaults_to_empty_string():
    mgr = make_manager()
    ctx = await mgr.get_full_context(SESSION, "query")
    assert ctx.summary == ""


async def test_get_full_context_vector_store_failure_degrades_gracefully():
    class FailingVectorStore:
        async def search(self, *a: object, **kw: object) -> None:
            raise RuntimeError("vector store down")

        async def _retrieve_vector_override(self, query: str) -> list[str]:
            raise RuntimeError("vector store down")

    class FailingManager(MemoryManager):
        async def _retrieve_vector(self, query: str) -> list[str]:
            raise RuntimeError("vector store down")

    mgr = FailingManager()
    mgr._vector = object()  # truthy, so cold_tasks includes _retrieve_vector
    # Should not raise; cold_facts should be empty
    ctx = await mgr.get_full_context(SESSION, "query")
    assert isinstance(ctx, MemoryContext)
    assert ctx.cold_facts == []


async def test_get_full_context_graph_store_failure_degrades_gracefully():
    class FailingManager(MemoryManager):
        async def _retrieve_graph(self, query: str) -> list[str]:
            raise RuntimeError("graph store down")

    mgr = FailingManager()
    mgr._graph = object()  # truthy
    ctx = await mgr.get_full_context(SESSION, "query")
    assert isinstance(ctx, MemoryContext)
    assert ctx.cold_facts == []


# ---------------------------------------------------------------------------
# MemoryContext dataclass
# ---------------------------------------------------------------------------


def test_memory_context_default_summary_is_empty_string():
    ctx = MemoryContext(hot_messages=[], cold_facts=[], entities=[])
    assert ctx.summary == ""


def test_memory_context_fields_accessible():
    entity = Entity(name="Test Corp", entity_type="organization")
    ctx = MemoryContext(
        hot_messages=[{"role": "user", "content": "hi"}],
        cold_facts=["fact one"],
        entities=[entity],
        summary="A brief summary",
    )
    assert ctx.hot_messages[0]["role"] == "user"
    assert ctx.cold_facts[0] == "fact one"
    assert ctx.entities[0].name == "Test Corp"
    assert ctx.summary == "A brief summary"


# ---------------------------------------------------------------------------
# Entity and Relationship dataclasses
# ---------------------------------------------------------------------------


def test_entity_default_mentions_is_one():
    e = Entity(name="Some Tool", entity_type="tool")
    assert e.mentions == 1


def test_relationship_default_weight_is_one():
    r = Relationship(source="A", target="B", relation="uses")
    assert r.weight == pytest.approx(1.0)
