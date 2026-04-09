"""Tests for the HTTP API adapter (aiohttp)."""

from __future__ import annotations

import os

import pytest

from agentic_core.adapters.primary.http_api import create_app, _get_allowed_origins


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


# ---------------------------------------------------------------------------
# WebSocket origin validation tests (CVE-2026-25253 mitigation)
# ---------------------------------------------------------------------------


def test_get_allowed_origins_defaults():
    """Default origins include localhost variants."""
    from aiohttp import web
    app = web.Application()
    app["settings"] = None
    origins = _get_allowed_origins(app)
    assert "http://localhost" in origins
    assert "http://127.0.0.1" in origins
    assert "http://localhost:8080" in origins
    assert "http://127.0.0.1:8080" in origins


def test_get_allowed_origins_with_settings_dict():
    """Origins include port from settings dict."""
    from aiohttp import web
    app = web.Application()
    app["settings"] = {"http_port": 9090}
    origins = _get_allowed_origins(app)
    assert "http://localhost:9090" in origins
    assert "http://127.0.0.1:9090" in origins


def test_get_allowed_origins_env_override(monkeypatch):
    """Extra origins from AGENTIC_ALLOWED_ORIGINS env var are included."""
    from aiohttp import web
    monkeypatch.setenv("AGENTIC_ALLOWED_ORIGINS", "https://app.example.com, https://admin.example.com")
    app = web.Application()
    app["settings"] = None
    origins = _get_allowed_origins(app)
    assert "https://app.example.com" in origins
    assert "https://admin.example.com" in origins


async def test_websocket_rejects_bad_origin(tmp_path, aiohttp_client):
    """WebSocket upgrade with unauthorized origin returns 403."""
    app = create_app(agents_dir=str(tmp_path), static_dir=None)
    cl = await aiohttp_client(app)
    # Attempt a GET to /ws with a malicious Origin header.
    # aiohttp test client's ws_connect doesn't let us set Origin easily,
    # so we issue a raw GET which triggers the origin check before upgrade.
    resp = await cl.get("/ws", headers={"Origin": "https://evil.attacker.com"})
    assert resp.status == 403
    text = await resp.text()
    assert "Forbidden" in text


async def test_websocket_allows_localhost_origin(tmp_path, aiohttp_client):
    """WebSocket upgrade with localhost origin is permitted."""
    app = create_app(agents_dir=str(tmp_path), static_dir=None)
    cl = await aiohttp_client(app)
    resp = await cl.get("/ws", headers={"Origin": "http://localhost"})
    # Should NOT be 403 -- it proceeds to WS upgrade (which may be 101 or
    # a different status depending on the test client, but not 403).
    assert resp.status != 403
