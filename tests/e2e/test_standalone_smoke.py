"""Smoke test: start HTTP API, hit endpoints, verify responses."""

import pytest

from agentic_core.adapters.primary.http_api import create_app


@pytest.fixture
async def client(tmp_path, aiohttp_client):
    app = create_app(agents_dir=str(tmp_path), static_dir=None)
    return await aiohttp_client(app)


async def test_full_agent_lifecycle(client):
    # 1. Health check
    resp = await client.get("/api/health")
    assert resp.status == 200

    # 2. Create agent
    resp = await client.post("/api/agents", json={
        "name": "Smoke Test Agent",
        "role": "tester",
        "description": "E2E smoke test agent",
        "graph_template": "react",
        "tools": ["rimm-classifier"],
    })
    assert resp.status == 201

    # 3. List agents
    resp = await client.get("/api/agents")
    agents = await resp.json()
    assert len(agents) == 1

    # 4. Get agent detail
    resp = await client.get("/api/agents/smoke-test-agent")
    assert resp.status == 200
    data = await resp.json()
    assert data["role"] == "tester"

    # 5. Update gates
    resp = await client.put("/api/agents/smoke-test-agent/gates", json={
        "gates": [
            {"name": "PII Filter", "content": "## PII\nRedact personal info", "action": "block", "order": 0},
            {"name": "Tone Check", "content": "## Tone\nBe professional", "action": "rewrite", "order": 1},
        ]
    })
    assert resp.status == 200
    gates = await resp.json()
    assert len(gates) == 2

    # 6. Verify gates persisted
    resp = await client.get("/api/agents/smoke-test-agent/gates")
    gates = await resp.json()
    assert gates[0]["name"] == "PII Filter"
    assert gates[1]["name"] == "Tone Check"

    # 7. Update agent
    resp = await client.put("/api/agents/smoke-test-agent", json={
        "description": "Updated description",
    })
    assert resp.status == 200

    # 8. Delete agent
    resp = await client.delete("/api/agents/smoke-test-agent")
    assert resp.status == 200

    # 9. Verify deleted
    resp = await client.get("/api/agents/smoke-test-agent")
    assert resp.status == 404
