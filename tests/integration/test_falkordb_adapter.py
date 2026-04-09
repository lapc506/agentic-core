"""Integration tests for FalkorDBAdapter. Requires FalkorDB at localhost:6499."""
from __future__ import annotations

import contextlib

import pytest

from agentic_core.adapters.secondary.falkordb_adapter import FalkorDBAdapter
from tests.integration.conftest import FALKORDB_URL, integration


@integration
class TestFalkorDBAdapter:
    @pytest.fixture
    async def adapter(self):
        a = FalkorDBAdapter(FALKORDB_URL, graph_name="test_knowledge")
        await a.connect()
        # Clean graph
        with contextlib.suppress(Exception):
            a._graph.query("MATCH (n) DETACH DELETE n")
        yield a
        await a.close()

    async def test_store_entity(self, adapter: FalkorDBAdapter):
        await adapter.store_entity(
            {"id": "user_1", "type": "User", "name": "Alice"},
            [],
        )
        results = await adapter.query('MATCH (u:User {id: "user_1"}) RETURN u.name')
        assert len(results) >= 1

    async def test_store_with_relations(self, adapter: FalkorDBAdapter):
        await adapter.store_entity(
            {"id": "user_2", "type": "User", "name": "Bob"},
            [{"target_id": "team_1", "target_type": "Team", "relation": "BELONGS_TO"}],
        )
        results = await adapter.query(
            'MATCH (u:User)-[:BELONGS_TO]->(t:Team) RETURN u.name, t.id'
        )
        assert len(results) >= 1

    async def test_query_empty(self, adapter: FalkorDBAdapter):
        results = await adapter.query('MATCH (x:NonExistent) RETURN x')
        assert results == []
