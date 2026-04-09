"""HTTP API adapter (aiohttp) for standalone mode.

Provides REST routes for agent CRUD, gates, metrics, health, config,
and optional static-file serving with SPA fallback for Flutter Web.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import aiohttp
import yaml
from aiohttp import web

from agentic_core.application.commands.create_agent import (
    CreateAgentCommand,
    CreateAgentHandler,
)
from agentic_core.application.commands.update_agent import (
    UpdateAgentCommand,
    UpdateAgentHandler,
)
from agentic_core.application.commands.update_gates import (
    UpdateGatesCommand,
    UpdateGatesHandler,
)
from agentic_core.application.queries.get_metrics import (
    GetMetricsHandler,
    GetMetricsQuery,
)
from agentic_core.application.queries.list_agents import (
    ListAgentsHandler,
    ListAgentsQuery,
)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def config(request: web.Request) -> web.Response:
    settings: dict[str, Any] | None = request.app.get("settings")
    if settings is None:
        return web.json_response({})
    safe_keys = {"mode", "ws_port", "personas_dir", "pii_redaction_enabled"}
    subset = {k: v for k, v in settings.items() if k in safe_keys}
    return web.json_response(subset)


async def list_agents(request: web.Request) -> web.Response:
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await handler.execute(ListAgentsQuery())
    return web.json_response(agents)


async def create_agent(request: web.Request) -> web.Response:
    body = await request.json()
    handler: CreateAgentHandler = request.app["create_agent_handler"]
    cmd = CreateAgentCommand(
        name=body["name"],
        role=body.get("role", "assistant"),
        description=body.get("description", ""),
        graph_template=body.get("graph_template", "react"),
        tools=body.get("tools"),
        system_prompt=body.get("system_prompt", ""),
    )
    await handler.execute(cmd)
    return web.json_response({"name": cmd.name}, status=201)


async def get_agent_detail(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await handler.execute(ListAgentsQuery())
    for agent in agents:
        if agent.get("slug") == slug:
            return web.json_response(agent)
    return web.json_response({"error": "not found"}, status=404)


async def update_agent(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    body = await request.json()
    handler: UpdateAgentHandler = request.app["update_agent_handler"]
    try:
        updated = await handler.execute(UpdateAgentCommand(agent_slug=slug, updates=body))
    except FileNotFoundError:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response(updated)


async def delete_agent(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    agents_dir: str = request.app["agents_dir"]
    yaml_path = Path(agents_dir) / f"{slug}.yaml"
    if not yaml_path.exists():
        return web.json_response({"error": "not found"}, status=404)
    os.remove(yaml_path)
    return web.json_response({"deleted": slug})


async def get_gates(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await handler.execute(ListAgentsQuery())
    for agent in agents:
        if agent.get("slug") == slug:
            return web.json_response(agent.get("gates", []))
    return web.json_response({"error": "not found"}, status=404)


async def update_gates(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    body = await request.json()
    handler: UpdateGatesHandler = request.app["update_gates_handler"]
    try:
        gates = await handler.execute(
            UpdateGatesCommand(agent_slug=slug, gates=body["gates"])
        )
    except FileNotFoundError:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response([g.model_dump(mode="json") for g in gates])


async def get_metrics(request: web.Request) -> web.Response:
    metric_type = request.match_info["metric_type"]
    window = request.query.get("window", "1h")
    handler: GetMetricsHandler = request.app["get_metrics_handler"]
    result = await handler.execute(GetMetricsQuery(metric_type=metric_type, window=window))
    return web.json_response(result)


# ---------------------------------------------------------------------------
# Config providers (persistence)
# ---------------------------------------------------------------------------

_CONFIG_FILE = "studio_config.json"


_DEFAULTS_FILE = "defaults/studio_config.json"


def _config_path(app: web.Application) -> Path:
    agents_dir = app.get("agents_dir", ".")
    return Path(agents_dir).parent / _CONFIG_FILE


def _load_or_init_config(app: web.Application) -> dict[str, Any]:
    """Load config from disk, or initialize from defaults if first run."""
    path = _config_path(app)
    if path.exists():
        return json.loads(path.read_text())

    # Try loading defaults from repo
    defaults_path = Path(_DEFAULTS_FILE)
    if defaults_path.exists():
        return json.loads(defaults_path.read_text())

    return {"providers": [], "default_agent": None, "onboarded": False}


async def get_studio_config(request: web.Request) -> web.Response:
    return web.json_response(_load_or_init_config(request.app))


async def save_studio_config(request: web.Request) -> web.Response:
    body = await request.json()
    path = _config_path(request.app)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2))
    return web.json_response({"saved": True})


async def get_setup_status(request: web.Request) -> web.Response:
    """Check if onboarding is complete: has providers + at least one agent."""
    path = _config_path(request.app)
    has_config = path.exists()
    config_data = json.loads(path.read_text()) if has_config else {}
    agents_handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await agents_handler.execute(ListAgentsQuery())
    return web.json_response({
        "onboarded": config_data.get("onboarded", False),
        "has_providers": len(config_data.get("providers", [])) > 0,
        "has_agents": len(agents) > 0,
        "default_agent": config_data.get("default_agent"),
        "agent_count": len(agents),
    })


# ---------------------------------------------------------------------------
# LLM provider helpers
# ---------------------------------------------------------------------------

_log = logging.getLogger(__name__)


def _load_provider_config(app: web.Application) -> dict[str, Any] | None:
    """Load the active provider from studio_config.json or defaults."""
    config = _load_or_init_config(app)
    providers = config.get("providers", [])
    if not providers:
        return None
    # Use the first active or default provider
    for p in providers:
        if p.get("status") in ("active", "default"):
            return p
    return providers[0] if providers else None


def _load_agent_prompt(app: web.Application, persona_id: str) -> str:
    """Load system prompt from agent YAML file."""
    agents_dir = app.get("agents_dir", "agents")
    yaml_path = Path(agents_dir) / f"{persona_id}.yaml"
    if yaml_path.exists():
        with open(yaml_path) as f:
            data = yaml.safe_load(f) or {}
        return data.get("system_prompt", "You are a helpful assistant.")
    return "You are a helpful assistant."


# ---------------------------------------------------------------------------
# WebSocket handler (proxy to same protocol as websockets transport)
# ---------------------------------------------------------------------------


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connections using aiohttp (same port as HTTP)."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    sessions: set[str] = set()
    import uuid_utils

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "code": "invalid_payload", "message": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            if msg_type == "create_session":
                session_id = str(uuid_utils.uuid7())
                sessions.add(session_id)
                await ws.send_json({"type": "session_created", "session_id": session_id})

            elif msg_type == "message":
                session_id = data.get("session_id", "")
                persona_id = data.get("persona_id", "")
                content = data.get("content", "")
                if session_id not in sessions:
                    await ws.send_json({"type": "error", "session_id": session_id,
                                        "code": "invalid_session", "message": "Session not found"})
                    continue

                await ws.send_json({"type": "stream_start", "session_id": session_id})

                provider = _load_provider_config(request.app)
                if provider and provider.get("baseUrl"):
                    try:
                        from langchain_openai import ChatOpenAI
                        from langchain_core.messages import HumanMessage, SystemMessage

                        llm = ChatOpenAI(
                            base_url=provider["baseUrl"],
                            api_key=provider.get("apiKey") or "not-needed",
                            model=provider.get("model", "gpt-3.5-turbo"),
                            streaming=True,
                        )

                        system_prompt = _load_agent_prompt(request.app, persona_id)
                        messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=content),
                        ]

                        async for chunk in llm.astream(messages):
                            if chunk.content:
                                await ws.send_json({
                                    "type": "stream_token",
                                    "session_id": session_id,
                                    "token": chunk.content,
                                })
                    except Exception as e:
                        _log.warning("LLM call failed: %s", e)
                        await ws.send_json({
                            "type": "stream_token",
                            "session_id": session_id,
                            "token": f"Error connecting to LLM: {e}. "
                                     "Configure a provider in Settings \u2192 Modelos.",
                        })
                else:
                    # No provider configured — helpful fallback
                    await ws.send_json({
                        "type": "stream_token",
                        "session_id": session_id,
                        "token": "No inference provider configured. "
                                 "Go to Settings \u2192 Modelos to add OpenRouter, Ollama, or another provider.",
                    })

                await ws.send_json({"type": "stream_end", "session_id": session_id})

            elif msg_type == "close_session":
                session_id = data.get("session_id", "")
                sessions.discard(session_id)
                await ws.send_json({"type": "session_closed", "session_id": session_id})

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    return ws


# ---------------------------------------------------------------------------
# SPA fallback
# ---------------------------------------------------------------------------


async def spa_fallback(request: web.Request) -> web.Response:
    """Serve static file if it exists, otherwise index.html (SPA routing)."""
    static_dir: str | None = request.app.get("static_dir")
    if static_dir is None:
        return web.json_response({"error": "not found"}, status=404)
    base = Path(static_dir).resolve()

    # Try to serve the requested file (e.g. flutter_bootstrap.js, main.dart.js)
    requested = request.match_info.get("path", "")
    if requested:
        file_path = (base / requested).resolve()
        if file_path.is_file() and str(file_path).startswith(str(base)):
            return web.FileResponse(file_path)

    # Fallback to index.html for SPA client-side routing
    index = base / "index.html"
    if not index.exists():
        return web.json_response({"error": "not found"}, status=404)
    return web.FileResponse(index)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(
    agents_dir: str,
    static_dir: str | None = None,
    settings: dict[str, Any] | None = None,
) -> web.Application:
    """Build and return an aiohttp ``Application`` wired to CQRS handlers."""

    app = web.Application()

    # Store references on app dict
    app["agents_dir"] = agents_dir
    app["static_dir"] = static_dir
    app["settings"] = settings
    app["list_agents_handler"] = ListAgentsHandler(agents_dir)
    app["create_agent_handler"] = CreateAgentHandler(agents_dir)
    app["update_agent_handler"] = UpdateAgentHandler(agents_dir)
    app["update_gates_handler"] = UpdateGatesHandler(agents_dir)
    app["get_metrics_handler"] = GetMetricsHandler()

    # --- API routes ---
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/config", config)
    app.router.add_get("/api/agents", list_agents)
    app.router.add_post("/api/agents", create_agent)
    app.router.add_get("/api/agents/{slug}", get_agent_detail)
    app.router.add_put("/api/agents/{slug}", update_agent)
    app.router.add_delete("/api/agents/{slug}", delete_agent)
    app.router.add_get("/api/agents/{slug}/gates", get_gates)
    app.router.add_put("/api/agents/{slug}/gates", update_gates)
    app.router.add_get("/api/metrics/{metric_type}", get_metrics)
    app.router.add_get("/api/studio/config", get_studio_config)
    app.router.add_post("/api/studio/config", save_studio_config)
    app.router.add_get("/api/studio/setup-status", get_setup_status)

    # --- WebSocket ---
    app.router.add_get("/ws", websocket_handler)

    # --- Static files + SPA fallback ---
    if static_dir and Path(static_dir).is_dir():
        app.router.add_get("/", spa_fallback)
        app.router.add_get("/{path:.*}", spa_fallback)

    return app
