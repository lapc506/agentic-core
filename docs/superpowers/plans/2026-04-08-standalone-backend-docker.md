# Standalone Backend + Docker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add REST API, static file serving, and docker-compose to enable `docker compose up` → `localhost:8765` with a working Agent Studio backend.

**Architecture:** New `aiohttp` primary adapter handles REST + static + WebSocket in standalone mode. Existing `websockets` adapter continues for sidecar mode. Domain layer gets Gate value object. CQRS commands/queries for agent CRUD. Agent config persisted as YAML files (matching existing PersonaRegistry pattern).

**Tech Stack:** Python 3.12, aiohttp, Pydantic, pytest-asyncio, Docker multi-stage

**Spec:** `docs/superpowers/specs/2026-04-08-standalone-agent-studio-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|---|---|
| `src/agentic_core/domain/value_objects/gate.py` | Gate value object (immutable, Pydantic frozen) |
| `src/agentic_core/application/commands/create_agent.py` | CreateAgent command + handler |
| `src/agentic_core/application/commands/update_agent.py` | UpdateAgent command + handler |
| `src/agentic_core/application/commands/update_gates.py` | UpdateGates command + handler |
| `src/agentic_core/application/queries/list_agents.py` | ListAgents query + handler |
| `src/agentic_core/application/queries/list_tools.py` | ListTools query + handler |
| `src/agentic_core/application/queries/get_metrics.py` | GetMetrics query + handler |
| `src/agentic_core/adapters/primary/http_api.py` | aiohttp app: REST + static + WebSocket |
| `docker-compose.yml` | Full standalone compose (root level) |
| `tests/unit/domain/test_gate.py` | Gate value object tests |
| `tests/unit/application/test_agent_commands.py` | Agent CRUD command tests |
| `tests/unit/application/test_agent_queries.py` | Agent query tests |
| `tests/unit/adapters/test_http_api.py` | HTTP API adapter tests |

### Modified Files
| File | Change |
|---|---|
| `src/agentic_core/domain/entities/persona.py` | Add `gates: list[Gate]` field |
| `src/agentic_core/config/settings.py` | Add `static_dir` and `api_enabled` settings |
| `src/agentic_core/runtime.py` | Start http_api in standalone mode |
| `deployment/docker/Dockerfile` | Add Flutter Web build stage |
| `pyproject.toml` | Add `aiohttp` to optional dependencies |

---

## Task 1: Gate Value Object

**Files:**
- Create: `src/agentic_core/domain/value_objects/gate.py`
- Modify: `src/agentic_core/domain/entities/persona.py`
- Test: `tests/unit/domain/test_gate.py`

- [ ] **Step 1: Write failing test for Gate creation**

```python
# tests/unit/domain/test_gate.py
from agentic_core.domain.value_objects.gate import Gate, GateAction


def test_gate_creation():
    gate = Gate(
        name="PII Filter",
        content="## PII Filter\nRedact personal information.",
        action=GateAction.BLOCK,
        order=0,
    )
    assert gate.name == "PII Filter"
    assert gate.action == GateAction.BLOCK
    assert gate.order == 0


def test_gate_is_frozen():
    gate = Gate(name="Test", content="body", action=GateAction.WARN, order=0)
    try:
        gate.name = "changed"
        assert False, "Should raise"
    except Exception:
        pass


def test_gate_action_enum():
    assert GateAction.BLOCK.value == "block"
    assert GateAction.WARN.value == "warn"
    assert GateAction.REWRITE.value == "rewrite"
    assert GateAction.HITL.value == "hitl"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/kvttvrsis/Documentos/GitHub/agentic-core && python -m pytest tests/unit/domain/test_gate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentic_core.domain.value_objects.gate'`

- [ ] **Step 3: Implement Gate value object**

```python
# src/agentic_core/domain/value_objects/gate.py
"""Gate value object — immutable guardrail step in an agent's pipeline."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class GateAction(str, Enum):
    """What happens when a gate check fails."""

    BLOCK = "block"
    WARN = "warn"
    REWRITE = "rewrite"
    HITL = "hitl"


class Gate(BaseModel, frozen=True):
    """A single guardrail step. Immutable value object within Persona."""

    name: str
    content: str  # Markdown body with guardrail rules
    action: GateAction
    order: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/domain/test_gate.py -v`
Expected: 3 passed

- [ ] **Step 5: Add gates field to Persona**

Add to `src/agentic_core/domain/entities/persona.py`:

```python
# Add import at top
from agentic_core.domain.value_objects.gate import Gate

# Add field to Persona dataclass (after escalation_rules)
    gates: list[Gate] = field(default_factory=list)
```

- [ ] **Step 6: Write test for Persona with gates**

Append to `tests/unit/domain/test_gate.py`:

```python
from agentic_core.domain.entities.persona import Persona
from agentic_core.domain.value_objects.gate import Gate, GateAction


def test_persona_with_gates():
    gates = [
        Gate(name="PII", content="Filter PII", action=GateAction.BLOCK, order=0),
        Gate(name="Tone", content="Check tone", action=GateAction.REWRITE, order=1),
    ]
    persona = Persona(name="Test", role="assistant", description="test", gates=gates)
    assert len(persona.gates) == 2
    assert persona.gates[0].name == "PII"
    assert persona.gates[1].order == 1
```

- [ ] **Step 7: Run all gate tests**

Run: `python -m pytest tests/unit/domain/test_gate.py -v`
Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add src/agentic_core/domain/value_objects/gate.py \
        src/agentic_core/domain/entities/persona.py \
        tests/unit/domain/test_gate.py
git commit -m "feat(domain): add Gate value object and wire to Persona"
```

---

## Task 2: Agent CRUD Commands

**Files:**
- Create: `src/agentic_core/application/commands/create_agent.py`
- Create: `src/agentic_core/application/commands/update_agent.py`
- Create: `src/agentic_core/application/commands/update_gates.py`
- Test: `tests/unit/application/test_agent_commands.py`

- [ ] **Step 1: Write failing tests for CreateAgent**

```python
# tests/unit/application/test_agent_commands.py
import os
import tempfile

import pytest
import yaml

from agentic_core.application.commands.create_agent import (
    CreateAgentCommand,
    CreateAgentHandler,
)
from agentic_core.domain.enums import GraphTemplate


@pytest.fixture
def agents_dir(tmp_path):
    return str(tmp_path)


async def test_create_agent_writes_yaml(agents_dir):
    handler = CreateAgentHandler(agents_dir=agents_dir)
    cmd = CreateAgentCommand(
        name="Test Agent",
        role="assistant",
        description="A test agent",
        graph_template="react",
    )
    persona = await handler.execute(cmd)

    assert persona.name == "Test Agent"
    assert persona.graph_template == GraphTemplate.REACT

    # Verify YAML file written
    yaml_path = os.path.join(agents_dir, "test-agent.yaml")
    assert os.path.exists(yaml_path)
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    assert data["name"] == "Test Agent"
    assert data["role"] == "assistant"


async def test_create_agent_slugifies_name(agents_dir):
    handler = CreateAgentHandler(agents_dir=agents_dir)
    cmd = CreateAgentCommand(
        name="Asistente Aduanero",
        role="customs",
        description="Customs assistant",
        graph_template="react",
    )
    await handler.execute(cmd)
    assert os.path.exists(os.path.join(agents_dir, "asistente-aduanero.yaml"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/application/test_agent_commands.py::test_create_agent_writes_yaml -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement CreateAgentCommand + Handler**

```python
# src/agentic_core/application/commands/create_agent.py
"""Command to create a new agent (Persona) and persist as YAML."""

from __future__ import annotations

import os
import re
from dataclasses import field

import yaml

from agentic_core.domain.entities.persona import Persona
from agentic_core.domain.enums import GraphTemplate


class CreateAgentCommand:
    __slots__ = ("name", "role", "description", "graph_template", "tools", "system_prompt")

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        graph_template: str = "react",
        tools: list[str] | None = None,
        system_prompt: str = "",
    ) -> None:
        self.name = name
        self.role = role
        self.description = description
        self.graph_template = graph_template
        self.tools = tools or []
        self.system_prompt = system_prompt


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")


class CreateAgentHandler:
    def __init__(self, agents_dir: str) -> None:
        self._agents_dir = agents_dir

    async def execute(self, cmd: CreateAgentCommand) -> Persona:
        template = GraphTemplate(cmd.graph_template)
        persona = Persona(
            name=cmd.name,
            role=cmd.role,
            description=cmd.description,
            graph_template=template,
            tools=cmd.tools,
        )

        data = {
            "name": cmd.name,
            "role": cmd.role,
            "description": cmd.description,
            "graph_template": cmd.graph_template,
            "tools": cmd.tools,
            "system_prompt": cmd.system_prompt,
            "gates": [],
        }
        slug = _slugify(cmd.name)
        path = os.path.join(self._agents_dir, f"{slug}.yaml")
        os.makedirs(self._agents_dir, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        return persona
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/application/test_agent_commands.py -v -k "create"`
Expected: 2 passed

- [ ] **Step 5: Write failing tests for UpdateGates**

Append to `tests/unit/application/test_agent_commands.py`:

```python
from agentic_core.application.commands.update_gates import (
    UpdateGatesCommand,
    UpdateGatesHandler,
)
from agentic_core.domain.value_objects.gate import Gate, GateAction


async def test_update_gates_persists_to_yaml(agents_dir):
    # Setup: create agent first
    create_handler = CreateAgentHandler(agents_dir=agents_dir)
    await create_handler.execute(
        CreateAgentCommand(name="Test Agent", role="test", description="test")
    )

    # Update gates
    handler = UpdateGatesHandler(agents_dir=agents_dir)
    gates = [
        {"name": "PII", "content": "Filter PII", "action": "block", "order": 0},
        {"name": "Tone", "content": "Check tone", "action": "rewrite", "order": 1},
    ]
    cmd = UpdateGatesCommand(agent_slug="test-agent", gates=gates)
    result = await handler.execute(cmd)

    assert len(result) == 2
    assert result[0].name == "PII"
    assert result[1].action == GateAction.REWRITE

    # Verify persisted
    with open(os.path.join(agents_dir, "test-agent.yaml")) as f:
        data = yaml.safe_load(f)
    assert len(data["gates"]) == 2
    assert data["gates"][0]["name"] == "PII"
```

- [ ] **Step 6: Implement UpdateGatesCommand + Handler**

```python
# src/agentic_core/application/commands/update_gates.py
"""Command to update gates for an agent and persist to YAML."""

from __future__ import annotations

import os
from typing import Any

import yaml

from agentic_core.domain.value_objects.gate import Gate, GateAction


class UpdateGatesCommand:
    __slots__ = ("agent_slug", "gates")

    def __init__(self, agent_slug: str, gates: list[dict[str, Any]]) -> None:
        self.agent_slug = agent_slug
        self.gates = gates


class UpdateGatesHandler:
    def __init__(self, agents_dir: str) -> None:
        self._agents_dir = agents_dir

    async def execute(self, cmd: UpdateGatesCommand) -> list[Gate]:
        path = os.path.join(self._agents_dir, f"{cmd.agent_slug}.yaml")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Agent not found: {cmd.agent_slug}")

        gate_objects = [
            Gate(
                name=g["name"],
                content=g["content"],
                action=GateAction(g["action"]),
                order=g["order"],
            )
            for g in cmd.gates
        ]

        with open(path) as f:
            data = yaml.safe_load(f)

        data["gates"] = [
            {"name": g.name, "content": g.content, "action": g.action.value, "order": g.order}
            for g in gate_objects
        ]

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        return gate_objects
```

- [ ] **Step 7: Implement UpdateAgent command (same pattern)**

```python
# src/agentic_core/application/commands/update_agent.py
"""Command to update an existing agent's config and persist to YAML."""

from __future__ import annotations

import os
from typing import Any

import yaml


class UpdateAgentCommand:
    __slots__ = ("agent_slug", "updates")

    def __init__(self, agent_slug: str, updates: dict[str, Any]) -> None:
        self.agent_slug = agent_slug
        self.updates = updates


class UpdateAgentHandler:
    def __init__(self, agents_dir: str) -> None:
        self._agents_dir = agents_dir

    async def execute(self, cmd: UpdateAgentCommand) -> dict[str, Any]:
        path = os.path.join(self._agents_dir, f"{cmd.agent_slug}.yaml")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Agent not found: {cmd.agent_slug}")

        with open(path) as f:
            data = yaml.safe_load(f)

        allowed = {"name", "role", "description", "graph_template", "tools", "system_prompt"}
        for key, value in cmd.updates.items():
            if key in allowed:
                data[key] = value

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        return data
```

- [ ] **Step 8: Run all command tests**

Run: `python -m pytest tests/unit/application/test_agent_commands.py -v`
Expected: 3 passed

- [ ] **Step 9: Commit**

```bash
git add src/agentic_core/application/commands/create_agent.py \
        src/agentic_core/application/commands/update_agent.py \
        src/agentic_core/application/commands/update_gates.py \
        tests/unit/application/test_agent_commands.py
git commit -m "feat(application): add agent CRUD commands with YAML persistence"
```

---

## Task 3: Agent Queries

**Files:**
- Create: `src/agentic_core/application/queries/list_agents.py`
- Create: `src/agentic_core/application/queries/list_tools.py`
- Create: `src/agentic_core/application/queries/get_metrics.py`
- Test: `tests/unit/application/test_agent_queries.py`

- [ ] **Step 1: Write failing tests for ListAgents**

```python
# tests/unit/application/test_agent_queries.py
import os

import pytest
import yaml

from agentic_core.application.queries.list_agents import (
    ListAgentsHandler,
    ListAgentsQuery,
)


@pytest.fixture
def agents_dir(tmp_path):
    # Write two agent YAML files
    for name, role in [("agent-one", "assistant"), ("agent-two", "reviewer")]:
        data = {"name": name, "role": role, "description": "test", "gates": [], "tools": []}
        with open(tmp_path / f"{name}.yaml", "w") as f:
            yaml.dump(data, f)
    return str(tmp_path)


async def test_list_agents_returns_all(agents_dir):
    handler = ListAgentsHandler(agents_dir=agents_dir)
    result = await handler.execute(ListAgentsQuery())
    assert len(result) == 2
    names = {a["name"] for a in result}
    assert names == {"agent-one", "agent-two"}


async def test_list_agents_includes_slug(agents_dir):
    handler = ListAgentsHandler(agents_dir=agents_dir)
    result = await handler.execute(ListAgentsQuery())
    slugs = {a["slug"] for a in result}
    assert "agent-one" in slugs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/application/test_agent_queries.py::test_list_agents_returns_all -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement ListAgents query**

```python
# src/agentic_core/application/queries/list_agents.py
"""Query to list all agents from YAML files."""

from __future__ import annotations

import os
from typing import Any

import yaml


class ListAgentsQuery:
    pass


class ListAgentsHandler:
    def __init__(self, agents_dir: str) -> None:
        self._agents_dir = agents_dir

    async def execute(self, query: ListAgentsQuery) -> list[dict[str, Any]]:
        agents: list[dict[str, Any]] = []
        if not os.path.isdir(self._agents_dir):
            return agents

        for filename in sorted(os.listdir(self._agents_dir)):
            if not filename.endswith(".yaml"):
                continue
            slug = filename.removesuffix(".yaml")
            path = os.path.join(self._agents_dir, filename)
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            data["slug"] = slug
            agents.append(data)

        return agents
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/application/test_agent_queries.py -v -k "list"`
Expected: 2 passed

- [ ] **Step 5: Implement ListTools query**

```python
# src/agentic_core/application/queries/list_tools.py
"""Query to list available tools and their health status."""

from __future__ import annotations

from typing import Any

from agentic_core.application.ports.tool import ToolPort


class ListToolsQuery:
    pass


class ListToolsHandler:
    def __init__(self, tool_port: ToolPort) -> None:
        self._tool = tool_port

    async def execute(self, query: ListToolsQuery) -> list[dict[str, Any]]:
        tools = await self._tool.list_tools()
        result = []
        for tool in tools:
            health = await self._tool.healthcheck_tool(tool.name)
            result.append({
                "name": tool.name,
                "description": tool.description,
                "healthy": health,
            })
        return result
```

- [ ] **Step 6: Implement GetMetrics query (stub for now)**

```python
# src/agentic_core/application/queries/get_metrics.py
"""Query to retrieve metrics for the dashboard charts."""

from __future__ import annotations

from typing import Any


class GetMetricsQuery:
    __slots__ = ("metric_type", "window")

    def __init__(self, metric_type: str, window: str = "1h") -> None:
        self.metric_type = metric_type
        self.window = window


class GetMetricsHandler:
    """Returns metrics data. Reads from in-memory counters for standalone mode.

    In production, this would read from Prometheus/VictoriaMetrics.
    For the standalone demo, we return data from the runtime's internal counters.
    """

    def __init__(self, metrics_store: dict[str, Any] | None = None) -> None:
        self._store = metrics_store or {}

    async def execute(self, query: GetMetricsQuery) -> dict[str, Any]:
        return {
            "metric_type": query.metric_type,
            "window": query.window,
            "data": self._store.get(query.metric_type, []),
        }
```

- [ ] **Step 7: Run all query tests**

Run: `python -m pytest tests/unit/application/test_agent_queries.py -v`
Expected: 2 passed

- [ ] **Step 8: Commit**

```bash
git add src/agentic_core/application/queries/list_agents.py \
        src/agentic_core/application/queries/list_tools.py \
        src/agentic_core/application/queries/get_metrics.py \
        tests/unit/application/test_agent_queries.py
git commit -m "feat(application): add agent queries (list agents, tools, metrics)"
```

---

## Task 4: HTTP API Adapter (aiohttp)

**Files:**
- Modify: `pyproject.toml`
- Create: `src/agentic_core/adapters/primary/http_api.py`
- Test: `tests/unit/adapters/test_http_api.py`

- [ ] **Step 1: Add aiohttp dependency**

In `pyproject.toml`, add to `[project.optional-dependencies]`:

```toml
standalone = [
    "aiohttp>=3.9",
]
```

And add `"aiohttp>=3.9"` to the `all` extras list as well.

Run: `pip install -e ".[standalone]"`

- [ ] **Step 2: Write failing test for health endpoint**

```python
# tests/unit/adapters/test_http_api.py
import pytest
from aiohttp.test_utils import AioHTTPTestCase, TestClient

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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pip install aiohttp pytest-aiohttp && python -m pytest tests/unit/adapters/test_http_api.py::test_health_endpoint -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement HTTP API adapter — core structure**

```python
# src/agentic_core/adapters/primary/http_api.py
"""HTTP API adapter for standalone mode: REST + static file serving."""

from __future__ import annotations

import os
from typing import Any

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


# --- Route handlers ---


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def list_agents(request: web.Request) -> web.Response:
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    result = await handler.execute(ListAgentsQuery())
    return web.json_response(result)


async def create_agent(request: web.Request) -> web.Response:
    body = await request.json()
    handler: CreateAgentHandler = request.app["create_agent_handler"]
    cmd = CreateAgentCommand(
        name=body["name"],
        role=body.get("role", "assistant"),
        description=body.get("description", ""),
        graph_template=body.get("graph_template", "react"),
        tools=body.get("tools", []),
        system_prompt=body.get("system_prompt", ""),
    )
    persona = await handler.execute(cmd)
    return web.json_response({"name": persona.name, "slug": cmd.name.lower().replace(" ", "-")}, status=201)


async def get_agent(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await handler.execute(ListAgentsQuery())
    for agent in agents:
        if agent["slug"] == slug:
            return web.json_response(agent)
    return web.json_response({"error": "not found"}, status=404)


async def update_agent(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    body = await request.json()
    handler: UpdateAgentHandler = request.app["update_agent_handler"]
    cmd = UpdateAgentCommand(agent_slug=slug, updates=body)
    result = await handler.execute(cmd)
    return web.json_response(result)


async def delete_agent(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    agents_dir: str = request.app["agents_dir"]
    path = os.path.join(agents_dir, f"{slug}.yaml")
    if not os.path.exists(path):
        return web.json_response({"error": "not found"}, status=404)
    os.remove(path)
    return web.json_response({"deleted": slug})


async def get_agent_gates(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await handler.execute(ListAgentsQuery())
    for agent in agents:
        if agent["slug"] == slug:
            return web.json_response(agent.get("gates", []))
    return web.json_response({"error": "not found"}, status=404)


async def update_agent_gates(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    body = await request.json()
    handler: UpdateGatesHandler = request.app["update_gates_handler"]
    cmd = UpdateGatesCommand(agent_slug=slug, gates=body.get("gates", []))
    gates = await handler.execute(cmd)
    return web.json_response([{"name": g.name, "action": g.action.value, "order": g.order} for g in gates])


async def get_metrics(request: web.Request) -> web.Response:
    metric_type = request.match_info["metric_type"]
    window = request.query.get("window", "1h")
    handler: GetMetricsHandler = request.app["get_metrics_handler"]
    result = await handler.execute(GetMetricsQuery(metric_type=metric_type, window=window))
    return web.json_response(result)


async def get_config(request: web.Request) -> web.Response:
    settings = request.app["settings"]
    return web.json_response({
        "mode": settings.mode,
        "ws_port": settings.ws_port,
        "personas_dir": settings.personas_dir,
        "pii_redaction_enabled": settings.pii_redaction_enabled,
    })


# --- SPA fallback for Flutter Web ---


async def spa_fallback(request: web.Request) -> web.Response:
    """Serve index.html for any non-API, non-static route (SPA routing)."""
    static_dir: str | None = request.app.get("static_dir")
    if not static_dir:
        return web.json_response({"error": "UI not available"}, status=404)
    index = os.path.join(static_dir, "index.html")
    if os.path.exists(index):
        return web.FileResponse(index)
    return web.json_response({"error": "index.html not found"}, status=404)


# --- App factory ---


def create_app(
    agents_dir: str,
    static_dir: str | None = None,
    settings: Any = None,
) -> web.Application:
    app = web.Application()

    # Store dependencies
    app["agents_dir"] = agents_dir
    app["static_dir"] = static_dir
    app["settings"] = settings
    app["list_agents_handler"] = ListAgentsHandler(agents_dir=agents_dir)
    app["create_agent_handler"] = CreateAgentHandler(agents_dir=agents_dir)
    app["update_agent_handler"] = UpdateAgentHandler(agents_dir=agents_dir)
    app["update_gates_handler"] = UpdateGatesHandler(agents_dir=agents_dir)
    app["get_metrics_handler"] = GetMetricsHandler()

    # API routes
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/config", get_config)
    app.router.add_get("/api/agents", list_agents)
    app.router.add_post("/api/agents", create_agent)
    app.router.add_get("/api/agents/{slug}", get_agent)
    app.router.add_put("/api/agents/{slug}", update_agent)
    app.router.add_delete("/api/agents/{slug}", delete_agent)
    app.router.add_get("/api/agents/{slug}/gates", get_agent_gates)
    app.router.add_put("/api/agents/{slug}/gates", update_agent_gates)
    app.router.add_get("/api/metrics/{metric_type}", get_metrics)

    # Static files (Flutter Web build)
    if static_dir and os.path.isdir(static_dir):
        app.router.add_static("/static", static_dir)
        # SPA fallback: non-API routes serve index.html
        app.router.add_get("/{path:.*}", spa_fallback)
    else:
        app.router.add_get("/", spa_fallback)

    return app
```

- [ ] **Step 5: Run health test to verify it passes**

Run: `python -m pytest tests/unit/adapters/test_http_api.py::test_health_endpoint -v`
Expected: PASS

- [ ] **Step 6: Write and run CRUD endpoint tests**

Append to `tests/unit/adapters/test_http_api.py`:

```python
async def test_create_and_list_agents(client):
    # Create
    resp = await client.post("/api/agents", json={
        "name": "My Agent",
        "role": "assistant",
        "description": "Test agent",
    })
    assert resp.status == 201
    data = await resp.json()
    assert data["name"] == "My Agent"

    # List
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


async def test_update_gates(client):
    await client.post("/api/agents", json={"name": "Gate Agent", "role": "test", "description": "d"})
    resp = await client.put("/api/agents/gate-agent/gates", json={
        "gates": [
            {"name": "PII", "content": "Filter PII", "action": "block", "order": 0},
        ]
    })
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
```

- [ ] **Step 7: Run all HTTP API tests**

Run: `python -m pytest tests/unit/adapters/test_http_api.py -v`
Expected: 6 passed

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml \
        src/agentic_core/adapters/primary/http_api.py \
        tests/unit/adapters/test_http_api.py
git commit -m "feat(adapters): add HTTP API adapter with REST + static serving for standalone mode"
```

---

## Task 5: Wire HTTP API into Runtime

**Files:**
- Modify: `src/agentic_core/config/settings.py`
- Modify: `src/agentic_core/runtime.py`
- Test: `tests/unit/test_runtime.py` (add test)

- [ ] **Step 1: Add settings for standalone HTTP**

Add to `src/agentic_core/config/settings.py` in `AgenticSettings`:

```python
    # Standalone HTTP (REST + static)
    http_port: int = 8765
    static_dir: str = "/app/web"
    api_enabled: bool = True
```

- [ ] **Step 2: Write failing test for standalone mode startup**

Append to `tests/unit/test_runtime.py`:

```python
async def test_runtime_standalone_starts_http():
    settings = AgenticSettings(mode="standalone", ws_port=0, grpc_port=0, http_port=0)
    runtime = AgentRuntime(settings)
    assert settings.api_enabled is True
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_runtime.py::test_runtime_standalone_starts_http -v`
Expected: PASS (settings field exists)

- [ ] **Step 4: Modify runtime.py to start HTTP API in standalone mode**

Add import at top of `src/agentic_core/runtime.py`:

```python
from agentic_core.adapters.primary.http_api import create_app
from aiohttp import web
```

Add method to `AgentRuntime` class:

```python
    async def _start_http(self) -> None:
        """Start aiohttp server for REST API + static file serving."""
        self._http_app = create_app(
            agents_dir=self._settings.personas_dir,
            static_dir=self._settings.static_dir,
            settings=self._settings,
        )
        self._http_runner = web.AppRunner(self._http_app)
        await self._http_runner.setup()
        site = web.TCPSite(
            self._http_runner,
            self._settings.ws_host,
            self._settings.http_port,
        )
        await site.start()
        self._log.info("HTTP API started", port=self._settings.http_port)
```

Modify the `start()` method to conditionally start HTTP:

```python
    async def start(self) -> None:
        servers = [self._ws.start(), self._grpc.start()]
        if self._settings.mode == "standalone" and self._settings.api_enabled:
            servers.append(self._start_http())
        await asyncio.gather(*servers)
        self._running = True
```

- [ ] **Step 5: Run existing runtime tests to verify no regression**

Run: `python -m pytest tests/unit/test_runtime.py -v`
Expected: All existing tests pass

- [ ] **Step 6: Commit**

```bash
git add src/agentic_core/config/settings.py \
        src/agentic_core/runtime.py \
        tests/unit/test_runtime.py
git commit -m "feat(runtime): start HTTP API in standalone mode"
```

---

## Task 6: Docker Compose + Dockerfile Update

**Files:**
- Create: `docker-compose.yml`
- Modify: `deployment/docker/Dockerfile`

- [ ] **Step 1: Create docker-compose.yml at project root**

```yaml
# docker-compose.yml
# Standalone Agent Studio — docker compose up → localhost:8765
services:
  agentic-core:
    build:
      context: .
      dockerfile: deployment/docker/Dockerfile
    ports:
      - "8765:8765"
    environment:
      AGENTIC_MODE: standalone
      AGENTIC_REDIS_URL: redis://redis:6379
      AGENTIC_POSTGRES_DSN: postgresql://agentic:agentic@postgres:5432/agentic
      AGENTIC_FALKORDB_URL: redis://falkordb:6380
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
      falkordb:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: agentic
      POSTGRES_PASSWORD: agentic
      POSTGRES_DB: agentic
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agentic"]
      interval: 5s
      timeout: 3s
      retries: 3
    volumes:
      - pgdata:/var/lib/postgresql/data

  falkordb:
    image: falkordb/falkordb:latest
    healthcheck:
      test: ["CMD", "redis-cli", "-p", "6379", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

volumes:
  pgdata:
```

- [ ] **Step 2: Update Dockerfile with Flutter Web build stage**

Replace `deployment/docker/Dockerfile` with:

```dockerfile
# Stage 1: Flutter Web build (only if ui/ directory exists)
FROM ghcr.io/cirruslabs/flutter:stable AS flutter-build
WORKDIR /app
COPY ui/pubspec.* ./
RUN flutter pub get
COPY ui/ .
RUN flutter build web --release

# Stage 2: Python build
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
COPY proto/ proto/
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir "dist/*.whl[standalone]"

# Stage 3: Production image
FROM gcr.io/distroless/python3-debian12
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src /app/src
COPY --from=flutter-build /app/build/web /app/web

WORKDIR /app
ENV PYTHONPATH=/app/src:/usr/local/lib/python3.12/site-packages
ENV AGENTIC_MODE=standalone
ENV AGENTIC_STATIC_DIR=/app/web
ENV AGENTIC_WS_PORT=8765
ENV AGENTIC_GRPC_PORT=50051

EXPOSE 8765 50051 9090
USER nonroot:nonroot
ENTRYPOINT ["python", "-m", "agentic_core.runtime"]
```

- [ ] **Step 3: Verify compose file is valid**

Run: `cd /home/kvttvrsis/Documentos/GitHub/agentic-core && docker compose config --quiet && echo "Valid"`
Expected: `Valid` (no errors)

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml deployment/docker/Dockerfile
git commit -m "feat(infra): add docker-compose.yml and update Dockerfile for standalone mode"
```

---

## Task 7: Placeholder Flutter Web App

**Files:**
- Create: `ui/pubspec.yaml`
- Create: `ui/lib/main.dart`
- Create: `ui/web/index.html`

This creates a minimal Flutter Web app so the Docker build works. The full UI is Plan 2.

- [ ] **Step 1: Create minimal pubspec.yaml**

```yaml
# ui/pubspec.yaml
name: agent_studio
description: Agent Studio — Flutter Web UI for agentic-core
version: 0.1.0
publish_to: none

environment:
  sdk: ">=3.4.0 <4.0.0"

dependencies:
  flutter:
    sdk: flutter

dev_dependencies:
  flutter_test:
    sdk: flutter

flutter:
  uses-material-design: true
```

- [ ] **Step 2: Create minimal main.dart**

```dart
// ui/lib/main.dart
import 'package:flutter/material.dart';

void main() {
  runApp(const AgentStudioApp());
}

class AgentStudioApp extends StatelessWidget {
  const AgentStudioApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agent Studio',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        scaffoldBackgroundColor: const Color(0xFF12121E),
        colorScheme: ColorScheme.dark(
          primary: const Color(0xFF3B6FE0),
          surface: const Color(0xFF1A1A2E),
        ),
      ),
      home: const Scaffold(
        body: Center(
          child: Text(
            'Agent Studio\nBackend running — UI coming in Plan 2',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 18, color: Color(0xFFE0E0F0)),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 3: Create web/index.html**

```html
<!DOCTYPE html>
<html>
<head>
  <base href="/">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agent Studio</title>
  <style>body { background: #12121E; margin: 0; }</style>
</head>
<body>
  <script src="flutter_bootstrap.js" async></script>
</body>
</html>
```

- [ ] **Step 4: Verify Flutter project is valid**

Run: `cd /home/kvttvrsis/Documentos/GitHub/agentic-core/ui && flutter pub get && flutter analyze`
Expected: No issues found

- [ ] **Step 5: Commit**

```bash
git add ui/
git commit -m "feat(ui): add placeholder Flutter Web app for standalone mode"
```

---

## Task 8: End-to-End Smoke Test

**Files:**
- Create: `tests/e2e/test_standalone_smoke.py`

- [ ] **Step 1: Write smoke test that hits REST API directly (no Docker)**

```python
# tests/e2e/test_standalone_smoke.py
"""Smoke test: start HTTP API, hit endpoints, verify responses."""

import pytest
from aiohttp.test_utils import TestClient

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
```

- [ ] **Step 2: Run smoke test**

Run: `python -m pytest tests/e2e/test_standalone_smoke.py -v`
Expected: 1 passed

- [ ] **Step 3: Run full test suite to verify no regressions**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests pass (existing 67 + new tests)

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_standalone_smoke.py
git commit -m "test(e2e): add standalone API smoke test for full agent lifecycle"
```

---

## Summary

| Task | What | Tests | Commits |
|---|---|---|---|
| 1 | Gate Value Object + Persona integration | 4 tests | 1 |
| 2 | Agent CRUD Commands (Create, Update, UpdateGates) | 3 tests | 1 |
| 3 | Agent Queries (List, Tools, Metrics) | 2 tests | 1 |
| 4 | HTTP API Adapter (aiohttp, all REST routes) | 6 tests | 1 |
| 5 | Wire HTTP into Runtime (standalone mode) | 1 test | 1 |
| 6 | docker-compose.yml + Dockerfile update | 1 validation | 1 |
| 7 | Placeholder Flutter Web app | 1 validation | 1 |
| 8 | E2E Smoke Test (full lifecycle) | 1 test | 1 |

**Total: 8 tasks, 18+ tests, 8 commits**

After this plan, `docker compose up` will serve the placeholder UI at `localhost:8765` with a fully functional REST API. Plan 2 builds the real Flutter Web UI.
