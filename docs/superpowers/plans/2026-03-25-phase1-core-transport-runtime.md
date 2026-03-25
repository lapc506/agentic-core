# Phase 1: Core + Transport + Runtime — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational layers of agentic-core: shared kernel, domain, application ports, primary adapters (WebSocket + gRPC), config, and runtime composition root.

**Architecture:** Explicit Architecture (Hexagonal + DDD + CQRS). Domain layer is pure (zero deps). Application layer defines ports (ABCs). Primary adapters translate protocols into commands/queries. Runtime is the composition root.

**Tech Stack:** Python 3.12+, Pydantic v2, websockets, grpcio, structlog, uuid-utils, simpleeval, pytest, ruff, mypy

**Spec:** `docs/superpowers/specs/2026-03-25-agentic-core-phase1-design.md`

**GitHub Issues:** #1-#15 on `lapc506/agentic-core`, Milestone "Phase 1: Core + Transport + Runtime"

---

## Dependency Order

```
Task 1 (scaffolding)
  -> Task 2 (shared kernel)
    -> Task 3 (enums)
    -> Task 4 (value objects) [depends on 2,3]
      -> Task 5 (entities) [depends on 3,4]
      -> Task 6 (domain events) [depends on 2,4]
      -> Task 7 (domain services) [depends on 4,5]
    -> Task 8 (ports) [depends on 4,5]
      -> Task 9 (handlers) [depends on 8]
      -> Task 10 (middleware) [depends on 8]
    -> Task 11 (config) [depends on 4]
    -> Task 12 (proto) [standalone]
      -> Task 13 (websocket adapter) [depends on 4,8,10]
      -> Task 14 (grpc adapter) [depends on 8,10,12]
        -> Task 15 (runtime) [depends on 9,10,11,13,14]
```

Tasks 3, 6, 12 can run in parallel after their deps complete.
Tasks 13, 14 can run in parallel after task 10.

---

## Task 1: Project Scaffolding (Issue #1)

**Files:**
- Create: `pyproject.toml`
- Create: `ruff.toml`
- Create: `.github/workflows/ci.yaml`
- Create: all `__init__.py` files

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "agentic-core"
version = "0.1.0"
description = "Production-ready Python library for AI agent orchestration"
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "websockets>=13.0",
    "grpcio>=1.60",
    "grpcio-tools>=1.60",
    "structlog>=24.0",
    "pyyaml>=6.0",
    "uuid-utils>=0.9",
    "simpleeval>=1.0",
]

[project.optional-dependencies]
all = [
    "langgraph>=0.3",
    "langchain-core>=0.3",
    "redis>=5.0",
    "asyncpg>=0.30",
    "pgvector>=0.3",
    "falkordb>=1.0",
    "opentelemetry-api>=1.20",
    "opentelemetry-sdk>=1.20",
    "opentelemetry-exporter-otlp>=1.20",
    "opentelemetry-exporter-prometheus>=0.45",
    "langfuse>=2.0",
    "httpx>=0.27",
    "google-genai>=1.0",
    "presidio-analyzer>=2.2",
    "mcp>=1.0",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.8",
    "mypy>=1.13",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
```

- [ ] **Step 2: Create ruff.toml**

```toml
target-version = "py312"
line-length = 100

[lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "TCH"]

[lint.isort]
known-first-party = ["agentic_core"]
```

- [ ] **Step 3: Create all directories and __init__.py files**

```bash
dirs=(
  "src/agentic_core/shared_kernel"
  "src/agentic_core/domain/value_objects"
  "src/agentic_core/domain/entities"
  "src/agentic_core/domain/events"
  "src/agentic_core/domain/services"
  "src/agentic_core/application/ports"
  "src/agentic_core/application/commands"
  "src/agentic_core/application/queries"
  "src/agentic_core/application/middleware"
  "src/agentic_core/adapters/primary/grpc/generated"
  "src/agentic_core/adapters/secondary"
  "src/agentic_core/config"
  "src/agentic_core/graph_templates/nodes"
  "proto"
  "tests/unit/shared_kernel"
  "tests/unit/domain"
  "tests/unit/application"
  "tests/unit/config"
  "tests/unit/adapters"
)
for d in "${dirs[@]}"; do mkdir -p "$d"; done
find src/agentic_core -type d -exec touch {}/__init__.py \;
find tests -type d -exec touch {}/__init__.py \;
touch tests/conftest.py
```

- [ ] **Step 4: Create .github/workflows/ci.yaml**

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  lint-type-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: mypy src/agentic_core/
      - run: pytest --cov=agentic_core --cov-report=xml -v
```

- [ ] **Step 5: Verify clean install**

Run: `pip install -e ".[dev]" && ruff check src/ && pytest -v`
Expected: 0 tests collected, no errors.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: scaffold project structure, pyproject.toml, CI workflow (#1)"
```

---

## Task 2: Shared Kernel (Issue #2)

**Files:**
- Create: `src/agentic_core/shared_kernel/types.py`
- Create: `src/agentic_core/shared_kernel/events.py`
- Test: `tests/unit/shared_kernel/test_types.py`, `tests/unit/shared_kernel/test_events.py`

- [ ] **Step 1: Write failing tests for types**

```python
# tests/unit/shared_kernel/test_types.py
from agentic_core.shared_kernel.types import SessionId, PersonaId, TraceId

def test_session_id_is_str():
    sid = SessionId("sess_123")
    assert isinstance(sid, str)

def test_persona_id_is_str():
    pid = PersonaId("support-agent")
    assert isinstance(pid, str)
```

- [ ] **Step 2: Run — verify FAIL**

Run: `pytest tests/unit/shared_kernel/test_types.py -v`

- [ ] **Step 3: Implement types.py**

```python
# src/agentic_core/shared_kernel/types.py
from typing import NewType

SessionId = NewType("SessionId", str)
PersonaId = NewType("PersonaId", str)
TraceId = NewType("TraceId", str)
```

- [ ] **Step 4: Run — verify PASS**

- [ ] **Step 5: Write failing tests for EventBus**

```python
# tests/unit/shared_kernel/test_events.py
from datetime import datetime, timezone
from agentic_core.shared_kernel.events import DomainEvent, EventBus

class FakeEvent(DomainEvent):
    data: str

async def test_publish_calls_handler():
    bus = EventBus()
    received = []
    async def handler(event: DomainEvent) -> None:
        received.append(event)
    bus.subscribe(FakeEvent, handler)
    evt = FakeEvent(data="hello", timestamp=datetime.now(timezone.utc))
    await bus.publish(evt)
    assert len(received) == 1
    assert received[0].data == "hello"

async def test_error_does_not_block_next_handler():
    bus = EventBus()
    calls = []
    async def bad(event: DomainEvent) -> None:
        raise RuntimeError("boom")
    async def good(event: DomainEvent) -> None:
        calls.append("ok")
    bus.subscribe(FakeEvent, bad)
    bus.subscribe(FakeEvent, good)
    await bus.publish(FakeEvent(data="x", timestamp=datetime.now(timezone.utc)))
    assert calls == ["ok"]

async def test_no_subscribers():
    bus = EventBus()
    await bus.publish(FakeEvent(data="lonely", timestamp=datetime.now(timezone.utc)))
```

- [ ] **Step 6: Run — verify FAIL**

- [ ] **Step 7: Implement events.py**

```python
# src/agentic_core/shared_kernel/events.py
from __future__ import annotations
import logging
from abc import ABC
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DomainEvent(BaseModel, frozen=True):
    timestamp: datetime
    trace_id: str | None = None

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[
            type[DomainEvent], list[Callable[[DomainEvent], Awaitable[None]]]
        ] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent],
                  handler: Callable[[DomainEvent], Awaitable[None]]) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            try:
                await handler(event)
            except Exception:
                logger.exception("Handler failed for %s", type(event).__name__)
```

- [ ] **Step 8: Run — verify PASS**

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: shared kernel types, DomainEvent, EventBus (#2)"
```

---

## Task 3: Domain Enums (Issue #3)

**Files:**
- Create: `src/agentic_core/domain/enums.py`
- Test: `tests/unit/domain/test_enums.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/domain/test_enums.py
import json
from agentic_core.domain.enums import SessionState, GraphTemplate, EmbeddingTaskType

def test_session_states():
    assert SessionState.ACTIVE == "active"
    assert SessionState.COMPLETED == "completed"

def test_graph_templates():
    assert GraphTemplate.REACT == "react"
    assert GraphTemplate.ORCHESTRATOR == "orchestrator"

def test_embedding_task_types_count():
    assert len(EmbeddingTaskType) == 8

def test_json_serializable():
    assert json.dumps(SessionState.ACTIVE) == '"active"'
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement**

```python
# src/agentic_core/domain/enums.py
from enum import Enum

class SessionState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ESCALATED = "escalated"
    COMPLETED = "completed"

class GraphTemplate(str, Enum):
    REACT = "react"
    PLAN_EXECUTE = "plan-and-execute"
    REFLEXION = "reflexion"
    LLM_COMPILER = "llm-compiler"
    SUPERVISOR = "supervisor"
    ORCHESTRATOR = "orchestrator"

class EmbeddingTaskType(str, Enum):
    SEMANTIC_SIMILARITY = "SEMANTIC_SIMILARITY"
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    CODE_RETRIEVAL_QUERY = "CODE_RETRIEVAL_QUERY"
    CLASSIFICATION = "CLASSIFICATION"
    CLUSTERING = "CLUSTERING"
    QUESTION_ANSWERING = "QUESTION_ANSWERING"
    FACT_VERIFICATION = "FACT_VERIFICATION"

class PersonaCapability(str, Enum):
    GSD = "gsd"
    SUPERPOWERS = "superpowers"
    AUTO_RESEARCH = "auto_research"
```

- [ ] **Step 4: Run — PASS. Commit.**

```bash
git add -A && git commit -m "feat: domain enums (#3)"
```

---

## Task 4: Value Objects (Issue #4)

**Files:**
- Create: `src/agentic_core/domain/value_objects/messages.py`
- Create: `src/agentic_core/domain/value_objects/model_config.py`
- Create: `src/agentic_core/domain/value_objects/tools.py`
- Create: `src/agentic_core/domain/value_objects/multimodal.py`
- Create: `src/agentic_core/domain/value_objects/slo.py`
- Create: `src/agentic_core/domain/value_objects/eval.py`
- Test: `tests/unit/domain/test_messages.py`, `tests/unit/domain/test_model_config.py`, `tests/unit/domain/test_tools.py`

- [ ] **Step 1: Write failing tests for AgentMessage**

```python
# tests/unit/domain/test_messages.py
import pytest
from datetime import datetime, timezone
from collections.abc import Mapping
import uuid_utils
from agentic_core.domain.value_objects.messages import AgentMessage

def test_valid_message():
    msg = AgentMessage(
        id=str(uuid_utils.uuid7()), session_id="s1", persona_id="p1",
        role="user", content="hello", metadata={"k": "v"},
        timestamp=datetime.now(timezone.utc),
    )
    assert msg.role == "user"
    assert isinstance(msg.metadata, Mapping)

def test_invalid_uuid_rejected():
    with pytest.raises(Exception):
        AgentMessage(
            id="not-a-uuid", session_id="s", persona_id="p",
            role="user", content="x", metadata={},
            timestamp=datetime.now(timezone.utc),
        )

def test_invalid_role_rejected():
    with pytest.raises(Exception):
        AgentMessage(
            id=str(uuid_utils.uuid7()), session_id="s", persona_id="p",
            role="invalid", content="x", metadata={},
            timestamp=datetime.now(timezone.utc),
        )

def test_frozen():
    msg = AgentMessage(
        id=str(uuid_utils.uuid7()), session_id="s", persona_id="p",
        role="user", content="x", metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    with pytest.raises(Exception):
        msg.content = "changed"
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement messages.py**

```python
# src/agentic_core/domain/value_objects/messages.py
from __future__ import annotations
from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType
from typing import Any, Literal
import uuid_utils
from pydantic import BaseModel, field_validator

class AgentMessage(BaseModel, frozen=True):
    id: str
    session_id: str
    persona_id: str
    role: Literal["user", "assistant", "system", "tool", "human_escalation"]
    content: str
    metadata: Mapping[str, Any]
    timestamp: datetime
    trace_id: str | None = None

    @field_validator("id")
    @classmethod
    def validate_uuid_v7(cls, v: str) -> str:
        parsed = uuid_utils.UUID(v)
        if parsed.version != 7:
            raise ValueError(f"Expected UUID v7, got v{parsed.version}")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def freeze_metadata(cls, v: Any) -> Mapping[str, Any]:
        if isinstance(v, dict):
            return MappingProxyType(v)
        return v
```

- [ ] **Step 4: Run — PASS**

- [ ] **Step 5: Implement remaining VOs** (ModelConfig, ToolResult, MultimodalContent, SLOTargets, BinaryEvalRule) — same TDD cycle per spec

- [ ] **Step 6: Run all VO tests — PASS. Commit.**

```bash
git add -A && git commit -m "feat: value objects — AgentMessage, ModelConfig, ToolResult, MultimodalContent (#4)"
```

---

## Task 5: Domain Entities (Issue #5)

**Files:**
- Create: `src/agentic_core/domain/entities/session.py`
- Create: `src/agentic_core/domain/entities/persona.py`
- Create: `src/agentic_core/domain/entities/skill.py`
- Create: `src/agentic_core/domain/entities/roadmap.py`
- Test: `tests/unit/domain/test_session.py`

- [ ] **Step 1: Write failing tests for Session state machine**

```python
# tests/unit/domain/test_session.py
import pytest
from agentic_core.domain.entities.session import Session, InvalidTransitionError
from agentic_core.domain.enums import SessionState

def test_create_active():
    s = Session.create("s1", "support", "u1")
    assert s.state == SessionState.ACTIVE

def test_active_to_paused():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.PAUSED)
    assert s.state == SessionState.PAUSED

def test_active_to_escalated():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.ESCALATED)
    assert s.state == SessionState.ESCALATED

def test_active_to_completed():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.COMPLETED)
    assert s.state == SessionState.COMPLETED

def test_paused_to_active():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.PAUSED)
    s.transition_to(SessionState.ACTIVE)
    assert s.state == SessionState.ACTIVE

def test_escalated_to_active():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.ESCALATED)
    s.transition_to(SessionState.ACTIVE)
    assert s.state == SessionState.ACTIVE

def test_completed_is_terminal():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        s.transition_to(SessionState.ACTIVE)

def test_paused_to_escalated_invalid():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.PAUSED)
    with pytest.raises(InvalidTransitionError):
        s.transition_to(SessionState.ESCALATED)
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement Session**

```python
# src/agentic_core/domain/entities/session.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from agentic_core.domain.enums import SessionState

_VALID = {
    SessionState.ACTIVE: {SessionState.PAUSED, SessionState.ESCALATED, SessionState.COMPLETED},
    SessionState.PAUSED: {SessionState.ACTIVE, SessionState.COMPLETED},
    SessionState.ESCALATED: {SessionState.ACTIVE},
    SessionState.COMPLETED: set(),
}

class InvalidTransitionError(Exception):
    pass

class Session:
    __slots__ = ("id", "persona_id", "user_id", "state", "checkpoint_id",
                 "created_at", "updated_at", "metadata")

    def __init__(self, *, id: str, persona_id: str, user_id: str,
                 state: SessionState, checkpoint_id: str | None,
                 created_at: datetime, updated_at: datetime,
                 metadata: dict[str, Any]) -> None:
        self.id = id
        self.persona_id = persona_id
        self.user_id = user_id
        self.state = state
        self.checkpoint_id = checkpoint_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.metadata = metadata

    @classmethod
    def create(cls, id: str, persona_id: str, user_id: str) -> Session:
        now = datetime.now(timezone.utc)
        return cls(id=id, persona_id=persona_id, user_id=user_id,
                   state=SessionState.ACTIVE, checkpoint_id=None,
                   created_at=now, updated_at=now, metadata={})

    def transition_to(self, new_state: SessionState) -> None:
        if new_state not in _VALID[self.state]:
            raise InvalidTransitionError(
                f"Cannot transition from {self.state.value} to {new_state.value}"
            )
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run — PASS**

- [ ] **Step 5: Implement Persona, Skill, Roadmap** (data classes per spec)

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: domain entities — Session state machine, Persona, Skill, Roadmap (#5)"
```

---

## Tasks 6-7: Domain Events + Services (Issues #6, #7)

Same TDD pattern. Key implementations:

**Task 6:** 8 frozen event types extending DomainEvent. All trivial.
**Task 7:** EscalationService uses `simpleeval.simple_eval()` (safe expression evaluator, NOT Python's built-in code execution). ModelResolver implements 3-level cascade.

- [ ] **Task 6: Commit**
```bash
git add -A && git commit -m "feat: domain events (#6)"
```

- [ ] **Task 7: Commit**
```bash
git add -A && git commit -m "feat: domain services — EscalationService (simpleeval), ModelResolver (#7)"
```

---

## Task 8: Application Ports (Issue #8)

12 ABC files, each with exact method signatures from spec Section 6.1.

- [ ] **Step 1: Write test verifying all ports are abstract**

```python
# tests/unit/application/test_ports.py
import inspect
from agentic_core.application.ports import (
    memory, session, embedding_provider, embedding_store,
    graph_store, tool, graph, tracing, metrics,
    cost_tracking, logging, alert,
)

def test_all_ports_are_abstract():
    modules = [memory, session, embedding_provider, embedding_store,
               graph_store, tool, graph, tracing, metrics,
               cost_tracking, logging, alert]
    for mod in modules:
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if name.endswith("Port"):
                assert inspect.isabstract(cls), f"{name} must be abstract"
```

- [ ] **Step 2: Implement all 12 ports** per spec signatures

- [ ] **Step 3: Commit**
```bash
git add -A && git commit -m "feat: 12 application port ABCs (#8)"
```

---

## Tasks 9-11: Handlers, Middleware, Config (Issues #9-11)

Same TDD pattern. Skeletons that accept ports via DI.

- [ ] **Task 9: Commit**
```bash
git add -A && git commit -m "feat: command/query handler skeletons (#9)"
```

- [ ] **Task 10: Commit**
```bash
git add -A && git commit -m "feat: middleware chain + TracingMiddleware no-op (#10)"
```

- [ ] **Task 11: Commit**
```bash
git add -A && git commit -m "feat: AgenticSettings + sub-configs (#11)"
```

---

## Task 12: gRPC Proto (Issue #12)

- [ ] **Step 1: Write proto/agentic_core.proto** per spec Section 7.2

- [ ] **Step 2: Add Makefile target for codegen**

```makefile
proto:
	python -m grpc_tools.protoc \
		-I proto \
		--python_out=src/agentic_core/adapters/primary/grpc/generated \
		--grpc_python_out=src/agentic_core/adapters/primary/grpc/generated \
		proto/agentic_core.proto
```

- [ ] **Step 3: Run codegen, verify**

- [ ] **Step 4: Commit**
```bash
git add -A && git commit -m "feat: gRPC proto + codegen (#12)"
```

---

## Task 13: WebSocket Adapter (Issue #13) — Size L

The largest task. Full protocol per spec Section 7.1.

- [ ] **Step 1: Tests for basic message roundtrip**
- [ ] **Step 2: Implement core WebSocketTransport (start, stop, on_message)**
- [ ] **Step 3: Run — PASS basic flow**
- [ ] **Step 4: Tests for session lifecycle (create_session, close_session)**
- [ ] **Step 5: Implement session lifecycle**
- [ ] **Step 6: Tests for error protocol**
- [ ] **Step 7: Implement error handling with codes**
- [ ] **Step 8: Tests for heartbeat + connection drop**
- [ ] **Step 9: Implement heartbeat + PAUSED on disconnect**
- [ ] **Step 10: Full test suite — PASS**
- [ ] **Step 11: Commit**
```bash
git add -A && git commit -m "feat: WebSocket adapter — full protocol (#13)"
```

---

## Task 14: gRPC Adapter (Issue #14)

- [ ] **Steps 1-6: TDD for each RPC** (SendMessage, CreateSession, GetSession, ResumeHITL, ListPersonas, HealthCheck)
- [ ] **Step 7: Commit**
```bash
git add -A && git commit -m "feat: gRPC adapter — AgentService (#14)"
```

---

## Task 15: AgentRuntime (Issue #15)

- [ ] **Step 1: Test runtime starts/stops with stubs**

```python
# tests/unit/test_runtime.py (conceptual)
async def test_runtime_lifecycle():
    settings = AgenticSettings(
        redis_url="redis://stub", postgres_dsn="postgresql://stub",
        falkordb_url="redis://stub",
    )
    runtime = AgentRuntime(settings)
    await runtime.start()
    assert runtime.is_running
    await runtime.stop()
    assert not runtime.is_running
```

- [ ] **Step 2: Implement runtime.py** — composition root with stub adapters for Phase 2+ ports
- [ ] **Step 3: Test sidecar mode host override**
- [ ] **Step 4: Commit**
```bash
git add -A && git commit -m "feat: AgentRuntime composition root (#15)"
```

---

## Final Verification

```bash
pytest --cov=agentic_core --cov-report=term-missing --cov-fail-under=80 -v
ruff check src/ tests/
mypy src/agentic_core/
```

Expected: All green, 80%+ coverage, zero mypy errors, zero ruff violations.

Push and close milestone:
```bash
git push origin main
gh issue close 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15
```
