"""Tests for the Ollama-compatible API endpoints."""

from __future__ import annotations

import json

import pytest
import yaml

from agentic_core.adapters.primary.http_api import create_app


@pytest.fixture
async def client(tmp_path, aiohttp_client):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    app = create_app(agents_dir=str(agents_dir), static_dir=None)
    return await aiohttp_client(app)


@pytest.fixture
async def client_with_agents(tmp_path, aiohttp_client):
    """Client with two pre-created agent YAML files."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    (agents_dir / "asistente-demo.yaml").write_text(yaml.dump({
        "name": "Asistente Demo",
        "role": "assistant",
        "description": "A demo assistant",
        "system_prompt": "You are a helpful demo assistant.",
    }))
    (agents_dir / "code-reviewer.yaml").write_text(yaml.dump({
        "name": "Code Reviewer",
        "role": "reviewer",
        "description": "Reviews pull requests",
        "system_prompt": "You are a code reviewer.",
    }))

    app = create_app(agents_dir=str(agents_dir), static_dir=None)
    return await aiohttp_client(app)


# -----------------------------------------------------------------------
# GET /api/tags
# -----------------------------------------------------------------------


async def test_tags_empty(client):
    resp = await client.get("/api/tags")
    assert resp.status == 200
    data = await resp.json()
    assert data["models"] == []


async def test_tags_lists_agents(client_with_agents):
    resp = await client_with_agents.get("/api/tags")
    assert resp.status == 200
    data = await resp.json()
    models = data["models"]
    assert len(models) == 2
    slugs = sorted(m["name"] for m in models)
    assert slugs == ["asistente-demo", "code-reviewer"]

    # Verify Ollama model object shape
    m = models[0]
    assert "model" in m
    assert "modified_at" in m
    assert m["size"] == 0
    assert m["digest"] == ""
    assert m["details"]["family"] == "agentic-core"
    assert m["details"]["parameter_size"] == "N/A"
    assert m["details"]["quantization_level"] == "N/A"


# -----------------------------------------------------------------------
# POST /api/show
# -----------------------------------------------------------------------


async def test_show_existing_model(client_with_agents):
    resp = await client_with_agents.post("/api/show", json={"name": "asistente-demo"})
    assert resp.status == 200
    data = await resp.json()
    assert "modelfile" in data
    assert "FROM agentic-core" in data["modelfile"]
    assert "You are a helpful demo assistant." in data["modelfile"]
    assert data["parameters"] == ""
    assert data["template"] == ""
    assert data["details"]["family"] == "agentic-core"
    assert data["details"]["description"] == "A demo assistant"
    assert data["details"]["role"] == "assistant"


async def test_show_nonexistent_model(client):
    """Non-existent model still returns 200 with default prompt (Ollama behaviour)."""
    resp = await client.post("/api/show", json={"name": "does-not-exist"})
    assert resp.status == 200
    data = await resp.json()
    assert "You are a helpful assistant." in data["modelfile"]
    assert data["details"]["description"] == ""


# -----------------------------------------------------------------------
# POST /api/chat  (stream=false, no provider configured)
# -----------------------------------------------------------------------


async def test_chat_non_streaming_no_provider(tmp_path, aiohttp_client, monkeypatch):
    """Without a provider, /api/chat stream=false returns a fallback message."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "asistente-demo.yaml").write_text(yaml.dump({
        "name": "Asistente Demo",
        "role": "assistant",
        "description": "A demo assistant",
        "system_prompt": "You are a helpful demo assistant.",
    }))
    # Write an empty studio_config so defaults file is not used
    (tmp_path / "studio_config.json").write_text(json.dumps({
        "providers": [], "default_agent": None, "onboarded": False,
    }))

    app = create_app(agents_dir=str(agents_dir), static_dir=None)
    cl = await aiohttp_client(app)

    resp = await cl.post("/api/chat", json={
        "model": "asistente-demo",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    })
    assert resp.status == 200
    data = await resp.json()
    assert data["model"] == "asistente-demo"
    assert data["done"] is True
    assert data["message"]["role"] == "assistant"
    assert "No inference provider configured" in data["message"]["content"]
    assert "total_duration" in data
    assert "eval_count" in data
    assert "created_at" in data


# -----------------------------------------------------------------------
# POST /api/generate  (stream=false, no provider configured)
# -----------------------------------------------------------------------


async def test_generate_non_streaming_no_provider(tmp_path, aiohttp_client):
    """Without a provider, /api/generate stream=false returns a fallback message."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "asistente-demo.yaml").write_text(yaml.dump({
        "name": "Asistente Demo",
        "role": "assistant",
        "description": "A demo assistant",
        "system_prompt": "You are a helpful demo assistant.",
    }))
    # Write an empty studio_config so defaults file is not used
    (tmp_path / "studio_config.json").write_text(json.dumps({
        "providers": [], "default_agent": None, "onboarded": False,
    }))

    app = create_app(agents_dir=str(agents_dir), static_dir=None)
    cl = await aiohttp_client(app)

    resp = await cl.post("/api/generate", json={
        "model": "asistente-demo",
        "prompt": "Hello",
        "stream": False,
    })
    assert resp.status == 200
    data = await resp.json()
    assert data["model"] == "asistente-demo"
    assert data["done"] is True
    # /api/generate uses "response" key, not "message"
    assert "response" in data
    assert "No inference provider configured" in data["response"]
    assert "total_duration" in data


# -----------------------------------------------------------------------
# POST /api/chat  (streaming, no provider configured)
# -----------------------------------------------------------------------


async def test_chat_streaming_no_provider(tmp_path, aiohttp_client):
    """Streaming chat returns ndjson lines ending with done=true."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "asistente-demo.yaml").write_text(yaml.dump({
        "name": "Asistente Demo",
        "role": "assistant",
        "description": "A demo assistant",
        "system_prompt": "You are a helpful demo assistant.",
    }))
    # Write an empty studio_config so defaults file is not used
    (tmp_path / "studio_config.json").write_text(json.dumps({
        "providers": [], "default_agent": None, "onboarded": False,
    }))

    app = create_app(agents_dir=str(agents_dir), static_dir=None)
    cl = await aiohttp_client(app)

    resp = await cl.post("/api/chat", json={
        "model": "asistente-demo",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    })
    assert resp.status == 200
    assert resp.content_type == "application/x-ndjson"

    body = await resp.read()
    lines = [json.loads(line) for line in body.strip().split(b"\n") if line.strip()]
    assert len(lines) >= 2  # at least one content line + done line

    # Last line must be done=true with timing stats
    last = lines[-1]
    assert last["done"] is True
    assert "total_duration" in last
    assert "eval_count" in last
    assert last["message"]["content"] == ""

    # Earlier lines must be done=false
    for line in lines[:-1]:
        assert line["done"] is False
        assert line["model"] == "asistente-demo"
        assert line["message"]["role"] == "assistant"
