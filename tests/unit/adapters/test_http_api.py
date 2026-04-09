"""Tests for the HTTP API adapter (aiohttp)."""

from __future__ import annotations

import pytest

from agentic_core.adapters.primary.http_api import create_app


@pytest.fixture
async def client(tmp_path, aiohttp_client):
    app = create_app(agents_dir=str(tmp_path), static_dir=None)
    return await aiohttp_client(app)


async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"


async def test_config_endpoint_no_settings(client):
    resp = await client.get("/api/config")
    assert resp.status == 200
    data = await resp.json()
    assert data == {}


async def test_config_endpoint_with_settings(tmp_path, aiohttp_client):
    settings = {"mode": "standalone", "ws_port": 8765, "personas_dir": "/tmp/p", "pii_redaction_enabled": True, "secret_key": "SHOULD_NOT_LEAK"}
    app = create_app(agents_dir=str(tmp_path), settings=settings)
    cl = await aiohttp_client(app)
    resp = await cl.get("/api/config")
    assert resp.status == 200
    data = await resp.json()
    assert data["mode"] == "standalone"
    assert data["ws_port"] == 8765
    assert "secret_key" not in data


async def test_create_and_list_agents(client):
    resp = await client.post("/api/agents", json={"name": "My Agent", "role": "assistant", "description": "Test agent"})
    assert resp.status == 201
    resp = await client.get("/api/agents")
    assert resp.status == 200
    agents = await resp.json()
    assert len(agents) == 1
    assert agents[0]["slug"] == "my-agent"


async def test_get_agent_detail(client):
    await client.post("/api/agents", json={"name": "Detail Agent", "role": "test", "description": "d"})
    resp = await client.get("/api/agents/detail-agent")
    assert resp.status == 200
    data = await resp.json()
    assert data["name"] == "Detail Agent"


async def test_get_agent_not_found(client):
    resp = await client.get("/api/agents/nonexistent")
    assert resp.status == 404


async def test_update_agent(client):
    await client.post("/api/agents", json={"name": "Updatable", "role": "test", "description": "old"})
    resp = await client.put("/api/agents/updatable", json={"description": "new description"})
    assert resp.status == 200
    data = await resp.json()
    assert data["description"] == "new description"


async def test_update_gates(client):
    await client.post("/api/agents", json={"name": "Gate Agent", "role": "test", "description": "d"})
    resp = await client.put("/api/agents/gate-agent/gates", json={"gates": [
        {"name": "PII", "content": "Filter PII", "action": "block", "order": 0},
    ]})
    assert resp.status == 200
    gates = await resp.json()
    assert len(gates) == 1
    assert gates[0]["name"] == "PII"
    # Verify persisted
    resp = await client.get("/api/agents/gate-agent/gates")
    assert resp.status == 200
    gates = await resp.json()
    assert len(gates) == 1


async def test_delete_agent(client):
    await client.post("/api/agents", json={"name": "Delete Me", "role": "test", "description": "d"})
    resp = await client.delete("/api/agents/delete-me")
    assert resp.status == 200
    resp = await client.get("/api/agents/delete-me")
    assert resp.status == 404


async def test_get_metrics(client):
    resp = await client.get("/api/metrics/latency?window=5m")
    assert resp.status == 200
    data = await resp.json()
    assert data["metric_type"] == "latency"
    assert data["window"] == "5m"


async def test_spa_fallback_no_static_dir(client):
    resp = await client.get("/some/random/path")
    # Without static_dir the catch-all is not registered, so 404
    assert resp.status == 404


async def test_spa_fallback_with_static_dir(tmp_path, aiohttp_client):
    static = tmp_path / "static"
    static.mkdir()
    index = static / "index.html"
    index.write_text("<html><body>SPA</body></html>")
    app = create_app(agents_dir=str(tmp_path / "agents"), static_dir=str(static))
    cl = await aiohttp_client(app)
    resp = await cl.get("/any/flutter/route")
    assert resp.status == 200
    text = await resp.text()
    assert "SPA" in text
