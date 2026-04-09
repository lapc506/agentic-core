# Changelog

All notable changes to agentic-core are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-04-08

### Added

#### Backend — Core Infrastructure

- **HTTP API adapter** (aiohttp) with 16+ REST endpoints covering agent CRUD, gate management, metrics, health check, studio config, and onboarding status (`src/agentic_core/adapters/primary/http_api.py`)
- **WebSocket chat handler** with real LLM streaming via LangChain OpenAI-compatible providers (`src/agentic_core/adapters/primary/websocket.py`)
- **Ollama-compatible API** endpoints: `/api/chat`, `/api/generate`, `/api/tags`, `/api/show` — enables any Ollama client to talk to agentic-core (`src/agentic_core/adapters/primary/http_api.py`)
- **A2A Protocol** (Google Agent-to-Agent): Agent Cards, JSON-RPC 2.0 transport, and full task lifecycle (submitted → working → completed/failed) (`src/agentic_core/adapters/primary/a2a.py`)
- **Bootstrap service registry** — wires all adapters and services to the runtime with graceful degradation; missing optional dependencies degrade cleanly without crashing the process (`src/agentic_core/bootstrap.py`)
- **Studio config persistence** — `studio_config.json` with sensible defaults and fallback when file is absent (`src/agentic_core/config/settings.py`)
- **Onboarding flow** — `/api/setup-status` endpoint and `OnboardingDialog` coordination layer
- **Standalone mode runtime** — async entrypoint that starts HTTP and WebSocket servers on separate ports (`src/agentic_core/runtime.py`)
- **Separate HTTP/WS ports** — backend now listens on port 8000 (REST) and port 8001 (WebSocket) in standalone mode
- **SPA static-file serving** — Flutter Web build assets are served from the same HTTP process with proper SPA fallback; static routes are registered before the fallback catch-all

#### Backend — Domain Model

- **Gate value object** wired into the Persona entity; gates represent guardrail thresholds (min confidence, max cost, allowed tools) that shape agent behavior at dispatch time (`src/agentic_core/domain/value_objects/gate.py`)
- **Agent CRUD commands** with YAML persistence: create, update, delete agents; stored to `~/.agentic-core/agents/` (`src/agentic_core/application/commands/`)
- **Agent queries**: list agents, list tools, get metrics per agent (`src/agentic_core/application/queries/`)
- **Persona entity** extended with gate collection, provider configuration, and SOUL.md export (`src/agentic_core/domain/entities/persona.py`)
- **Skill entity** for self-created procedural skills persisted alongside agent definitions (`src/agentic_core/domain/entities/skill.py`)

#### Backend — Agent Intelligence

- **Event-based hook pipeline** — lifecycle hooks fired at `before_agent_start`, `before_tool_call`, `after_tool_call`, `after_agent_end`, enabling middleware-style side effects without coupling (`src/agentic_core/application/hooks.py`)
- **Memory extraction service** — heuristic extraction of facts, decisions, and entity mentions from conversation turns with deduplication (`src/agentic_core/application/services/memory_extraction.py`)
- **Dual-layer memory manager** — hot layer in Redis for recent context, cold layer in FalkorDB/pgvector for long-term recall, with automatic promotion/demotion (`src/agentic_core/application/services/memory_manager.py`)
- **Procedural memory / skill self-creation** — agents can define, store, and invoke new skills discovered during task execution (`src/agentic_core/application/services/skill_creation.py`)
- **FalkorDB → pgvector graceful degradation** — graph memory falls back to pgvector similarity search when FalkorDB is unavailable (`src/agentic_core/adapters/secondary/falkordb_adapter.py`)
- **Persona router** — routes incoming messages by channel type, keyword match, or explicit agent ID; falls back to default persona (`src/agentic_core/application/services/persona_router.py`)
- **HTN planning** — hierarchical task network planner that decomposes high-level goals into primitive task sequences (`src/agentic_core/application/services/gsd_sequencer.py`)
- **Trajectory scoring** — scores agent action sequences against expected trajectories to detect drift (`src/agentic_core/domain/services/trajectory_evaluator.py`)
- **Progressive gates** — gates that tighten automatically when an agent nears cost or iteration budgets (`src/agentic_core/application/services/deployment_gates.py`)
- **Iteration budget enforcer** — hard cap on LLM calls per session with configurable per-agent limits (`src/agentic_core/application/services/iteration_budget.py`)
- **Context budget manager** — tracks token usage per turn and trims context window when approaching model limits (`src/agentic_core/application/services/context_budget.py`)
- **Cross-session recall** — retrieves relevant memories from past sessions using embedding similarity (`src/agentic_core/application/services/cross_session_recall.py`)
- **Context imports** — imports structured context blocks (files, URLs, snippets) into the active session context (`src/agentic_core/application/services/context_imports.py`)
- **Model steering** — per-turn model selection based on task complexity, cost envelope, and capability requirements (`src/agentic_core/application/services/model_steering.py`)
- **Cost enforcer** — tracks cumulative spend per session and hard-stops generation when a budget is exceeded (`src/agentic_core/application/services/cost_enforcer.py`)
- **Auto-research service** — background service that researches topics and stores findings in long-term memory (`src/agentic_core/application/services/auto_research.py`)
- **Behavioral monitor** — detects anomalous agent behavior patterns and emits alerts (`src/agentic_core/application/services/behavioral_monitor.py`)
- **Tool cache** — caches deterministic tool results by input hash to avoid redundant external calls (`src/agentic_core/application/services/tool_cache.py`)
- **Tool views** — typed response schemas that normalize tool output for rendering in UI and TUI (`src/agentic_core/application/services/tool_views.py`)
- **Coding primitives** — built-in tools for file read/write, shell execution, and diff generation wired into the tool registry (`src/agentic_core/application/services/coding_tools.py`)
- **Human-in-the-loop (HITL) confirmation** — suspends agent execution and waits for human approval before proceeding with flagged actions (`src/agentic_core/application/services/hitl_confirmation.py`, `src/agentic_core/application/commands/resume_hitl.py`)
- **Todo tracker** — lightweight task list maintained inside the session context, updated by agents as tasks complete (`src/agentic_core/application/services/todo_tracker.py`)
- **Policy engine** — evaluates declarative rules against proposed agent actions before execution (`src/agentic_core/application/services/policy_engine.py`)
- **Skill disclosure** — agents surface available skills to users and other agents on request (`src/agentic_core/application/services/skill_disclosure.py`)
- **Tool masking** — hides tools from the LLM context based on persona configuration and current task scope (`src/agentic_core/application/services/tool_masking.py`)
- **User modeling** — tracks user preferences and interaction patterns to personalize agent responses (`src/agentic_core/application/services/user_modeling.py`)
- **Cron scheduler** — schedules recurring agent tasks using cron expressions (`src/agentic_core/application/services/cron_scheduler.py`)
- **Media pipeline** — handles image and audio input preprocessing before passing to multimodal models (`src/agentic_core/application/services/media_pipeline.py`)
- **Programmatic tool executor** — allows external callers to invoke tools via REST without a running session (`src/agentic_core/application/services/programmatic_tools.py`)
- **Voice service** — speech-to-text and text-to-speech integration for voice-enabled agent interactions (`src/agentic_core/application/services/voice.py`)
- **SOUL.md export** — generates a portable agent persona document from entity state

#### Backend — MCP (Model Context Protocol)

- **OAuth 2.1 with PKCE** — full authorization code flow for MCP server connections with PKCE challenge/verifier (`src/agentic_core/adapters/secondary/mcp_auth.py`)
- **MCP server auto-discovery** — discovers MCP servers advertised via well-known URIs without manual configuration (`src/agentic_core/adapters/secondary/mcp_bridge_adapter.py`)

#### Backend — Multi-Agent Coordination

- **Lane orchestrator** — assigns agents to execution lanes to avoid resource contention and enforce sequencing (`src/agentic_core/application/services/lane_orchestrator.py`)
- **Green contracts** — typed capability contracts between agents that specify what each agent will produce and consume (`src/agentic_core/application/services/green_contract.py`)
- **Recovery recipes** — declarative error-recovery playbooks that trigger when an agent enters a failure state (`src/agentic_core/application/services/recovery_recipes.py`)
- **Stale branch detection** — detects when a multi-agent conversation branch has not made progress and prunes or escalates it (`src/agentic_core/application/services/stale_branch.py`)
- **Task packets** — structured task handoff format for passing work between agents with full provenance (`src/agentic_core/application/services/task_packet.py`)
- **Agent communications service** — typed message bus for inter-agent messages with delivery guarantees (`src/agentic_core/application/services/agent_comms.py`)
- **Secure agent communications** — signed and encrypted inter-agent messages with sender verification (`src/agentic_core/application/services/secure_agent_comms.py`)
- **Superpowers flow** — orchestration harness for coordinating multiple specialized sub-agents on a shared goal (`src/agentic_core/application/services/superpowers_flow.py`)

#### Backend — Security

- **Sandbox executor** — runs untrusted tool code inside a restricted subprocess with filesystem and network isolation (`src/agentic_core/application/services/sandbox_executor.py`, `src/agentic_core/adapters/secondary/` sandbox support)
- **Privacy router** — routes messages through PII redaction before logging or storing (`src/agentic_core/application/services/privacy_router.py`)
- **Credential vault** — encrypted at-rest storage for API keys and secrets; agents access credentials by name, never directly (`src/agentic_core/application/services/credential_vault.py`, `src/agentic_core/application/services/secure_credentials.py`)
- **Network egress policy** — allowlist-based outbound network control; tool calls to unlisted hosts are blocked (`src/agentic_core/application/services/network_egress.py`)
- **WebSocket origin validation** — validates `Origin` header on WebSocket upgrade requests to prevent cross-site WebSocket hijacking (analogous to CVE-2026-25253)
- **Plugin integrity verification** — verifies plugin manifests against SHA-256 checksums before loading; rejects tampered plugins (`src/agentic_core/application/services/plugin_integrity.py`)
- **Security audit trail** — append-only log of all security-relevant events (auth attempts, policy violations, tool blocks) (`src/agentic_core/application/middleware/audit_trail.py`)
- **5-scanner prompt injection detector** — ensemble of five independent detectors (pattern match, entropy, semantic, structural, token-frequency) with majority-vote decision (`src/agentic_core/application/middleware/injection_detector.py`)
- **Output filter** — scans LLM output for PII, credentials, and policy-violating content before delivery (`src/agentic_core/application/middleware/output_filter.py`)
- **Inter-agent message authentication** — HMAC-signed messages between agents; forged messages are rejected (`src/agentic_core/application/services/secure_agent_comms.py`)
- **Kill switch** — emergency stop that halts all running agents and blocks new sessions when triggered (`src/agentic_core/application/services/kill_switch.py`)
- **Command parser hardening** — input sanitization for shell-style agent commands to prevent injection via crafted tool arguments (`src/agentic_core/application/services/command_parser.py`)
- **Tool argument validation** — schema-based validation of all tool call arguments before execution (`src/agentic_core/application/services/tool_arg_validator.py`)
- **MCP shadow detection** — detects rogue MCP servers that shadow legitimate tool names (`src/agentic_core/application/services/mcp_shadow_detector.py`)
- **Memory integrity checks** — detects and rejects tampered memory records using content hashing (`src/agentic_core/application/services/memory_integrity.py`)
- **PII redaction middleware** — strips personally identifiable information from logs and stored messages (`src/agentic_core/application/middleware/pii_redaction.py`)
- **Context guard middleware** — enforces context window size limits and token budget policies (`src/agentic_core/application/middleware/context_guard.py`)
- **Auth middleware** — API key and bearer token validation for all REST and WebSocket endpoints (`src/agentic_core/application/middleware/auth.py`)
- **Rate limit middleware** — per-client rate limiting on REST and WebSocket endpoints (`src/agentic_core/application/middleware/rate_limit.py`)

#### Backend — Observability

- **Security auditor service** — runs periodic automated audits of agent configuration and tool access patterns (`src/agentic_core/application/services/security_auditor.py`)
- **Compliance service** — evaluates agent behavior against configurable compliance rulesets (`src/agentic_core/application/services/compliance.py`)
- **Tracing middleware** — OpenTelemetry trace propagation across all service calls (`src/agentic_core/application/middleware/tracing.py`)
- **Metrics middleware** — Prometheus-compatible counters and histograms for request latency, token usage, and error rates (`src/agentic_core/application/middleware/metrics.py`)
- **OpenTelemetry adapter** — exports traces and metrics to OTEL collectors (`src/agentic_core/adapters/secondary/otel_adapter.py`)
- **Langfuse adapter** — sends LLM traces to Langfuse for prompt analytics and cost monitoring (`src/agentic_core/adapters/secondary/langfuse_adapter.py`)
- **Alertmanager adapter** — routes SLO breach alerts to Prometheus Alertmanager (`src/agentic_core/adapters/secondary/alertmanager_adapter.py`)
- **SLO tracker** — tracks service level objectives and emits breach events (`src/agentic_core/sre/slo_tracker.py`)
- **Chaos service** — injects controlled failures for resilience testing (`src/agentic_core/sre/chaos.py`)

#### Backend — Infrastructure Adapters

- **FalkorDB adapter** — graph database adapter for entity and relationship storage (`src/agentic_core/adapters/secondary/falkordb_adapter.py`)
- **pgvector adapter** — PostgreSQL pgvector adapter for semantic similarity search (`src/agentic_core/adapters/secondary/pgvector_adapter.py`)
- **Redis adapter** — hot-tier memory and session state cache (`src/agentic_core/adapters/secondary/redis_adapter.py`)
- **PostgreSQL adapter** — relational storage for agent definitions, sessions, and audit logs (`src/agentic_core/adapters/secondary/postgres_adapter.py`)
- **Gemini embedding adapter** — embedding generation via Gemini embedding API (`src/agentic_core/adapters/secondary/gemini_embedding_adapter.py`)
- **OpenAI embedding adapter** — embedding generation via OpenAI embedding API (`src/agentic_core/adapters/secondary/openai_embedding_adapter.py`)
- **Local embedding adapter** — local embedding generation for offline/air-gapped deployments (`src/agentic_core/adapters/secondary/local_embedding_adapter.py`)
- **MCP bridge adapter** — bridges Model Context Protocol servers into the tool registry (`src/agentic_core/adapters/secondary/mcp_bridge_adapter.py`)
- **Session cleanup adapter** — background job that expires and archives old sessions (`src/agentic_core/adapters/secondary/session_cleanup.py`)
- **Structlog adapter** — structured JSON logging with request-scoped context fields (`src/agentic_core/adapters/secondary/structlog_adapter.py`)

#### Flutter Web UI (Agent Studio)

- **Dark theme system** — custom `AgentStudioTheme` based on Google Fonts (Inter) with a deep-blue/slate palette (`ui/lib/theme/agent_studio_theme.dart`)
- **SidebarRail + SidebarPanel layout** — persistent icon rail with an expanding contextual panel; `DashboardLayout` template composes both with a main content area (`ui/lib/shared/ui/`)
- **GoRouter navigation shell** with 7 pages: Chat, Agents, Sessions, Tools, Metrics, Settings, Onboarding (`ui/lib/routing/router.dart`)
- **API client service** — typed Dart HTTP client for all agentic-core REST endpoints with error handling (`ui/lib/services/api_client.dart`)
- **WebSocket client** — reconnecting WebSocket client with stream-based message delivery for chat streaming (`ui/lib/services/ws_client.dart`)
- **Chat page** with real-time LLM streaming, agent selector dropdown, and message history (`ui/lib/features/chat/chat_page.dart`)
- **GenUI Chat page** — rewritten Chat page using Flutter GenUI library with A2A protocol for generative UI rendering; agent responses can include rich UI components (`ui/lib/features/chat/genui_chat_page.dart`)
- **Agent editor page** — form-based agent creation and editing with gate configuration (`ui/lib/features/agents/agent_editor_page.dart`)
- **Rules page** — manage agent rules and behavioral constraints (`ui/lib/features/agents/rules_page.dart`)
- **Gate editor card** — `flutter_quill` WYSIWYG rich-text editor embedded in gate configuration cards (`ui/lib/features/agents/widgets/gate_editor_card.dart`)
- **Guardrails, Inputs, Outputs tabs** — dedicated tabs in the agent editor for gate-level configuration (`ui/lib/features/agents/widgets/`)
- **Settings page** with Debug tab containing an embedded `xterm.js` terminal emulator for live backend log streaming (`ui/lib/features/settings/settings_page.dart`)
- **Metrics page** — displays per-agent token usage, cost, latency histograms using the `graphic` charting library (`ui/lib/features/metrics/metrics_page.dart`)
- **Sessions page** — lists active and historical sessions with filterable table (`ui/lib/features/sessions/sessions_page.dart`)
- **Tools page** — displays registered tools with schema details and live invocation status (`ui/lib/features/tools/tools_page.dart`)
- **Onboarding dialog** — first-run setup wizard that polls `/api/setup-status` and guides through provider configuration (`ui/lib/features/onboarding/onboarding_dialog.dart`)
- **SOUL.md generator service** — generates portable persona documents from agent state for sharing (`ui/lib/services/soul_md_generator.dart`)
- **Agent Studio favicon** — custom blue "A" favicon and Open Graph meta tags for the web app
- **Providers UI** — manage LLM provider configurations (API keys, endpoints, model IDs) from within the Studio

#### Go TUI (agentic-tui)

- **Bubble Tea TUI** with tabbed layout (Chat, Dashboard, Agents, Settings), dark lipgloss theme, and full keyboard navigation (`tui/`)
- **Execution engine** — drives multi-step agent task execution with status tracking and event emission (`tui/internal/engine/executor.go`)
- **Session persistence** — saves and restores TUI sessions to disk using TOML; sessions survive process restarts (`tui/internal/engine/session.go`)
- **Completion detection** — heuristic detector that identifies when an agent task has reached a terminal state (`tui/internal/engine/detector.go`)
- **Event system** — typed event bus for decoupled communication between TUI components (`tui/internal/engine/events.go`)
- **Parallel execution** — runs multiple agent tasks concurrently with per-task status display (`tui/internal/engine/parallel.go`)
- **Headless mode** — runs the execution engine without the TUI for CI/CD and scripted use (`tui/internal/engine/headless.go`)
- **Iteration logging** — structured per-iteration logs with timestamps, token counts, and costs (`tui/internal/engine/logger.go`)
- **Dashboard view** — full-screen overview of running agents, system metrics, and recent events (`tui/internal/ui/dashboard.go`)
- **Agent tree** — hierarchical display of agent/sub-agent relationships and task status (`tui/internal/ui/tree.go`)
- **Single-key navigation** — vim-style key bindings for navigating the TUI without arrow keys
- **PRD task management** — import a Product Requirements Document and manage its tasks as a checklist within the TUI (`tui/internal/engine/prd.go`)
- **Cost-aware model tiering** — automatically selects cheaper models for low-complexity tasks based on a configurable cost envelope (`tui/internal/engine/cost.go`)
- **Agent scratchpad** — per-agent ephemeral notepad visible in the TUI for tracking intermediate reasoning (`tui/internal/engine/scratchpad.go`)
- **HITL confirmation UI** — TUI modal for human-in-the-loop approval of flagged agent actions (`tui/internal/ui/chat.go`)
- **Tool views in TUI** — structured display of tool call arguments and results inside the chat pane
- **Checkpointing** — saves execution state at configurable intervals; allows resuming from the last checkpoint after failure (`tui/internal/engine/checkpoint.go`)
- **Plan mode** — displays the agent's current task plan before execution begins and allows human editing (`tui/internal/engine/plan_mode.go`)
- **Custom commands** — user-defined slash commands that invoke backend endpoints or shell scripts from within the TUI (`tui/internal/engine/commands.go`)
- **Rewind** — rolls execution back to any saved checkpoint from the TUI (`tui/internal/engine/rewind.go`)
- **Plugin support** — loads TUI plugins from the plugins directory at startup (`tui/internal/engine/plugins.go`)
- **Config system** — TOML-based configuration for backend URL, default model, cost limits, and keybindings (`tui/internal/config/config.go`)
- **API client** — typed Go HTTP client for all agentic-core REST endpoints used by the TUI (`tui/internal/api/client.go`)
- **Templates** — pre-built task templates selectable from the TUI's new-task dialog (`tui/internal/engine/templates.go`)

#### Documentation

- **Standalone Agent Studio design spec** — architectural overview and component breakdown for the standalone deployment mode
- **Standalone Backend + Docker implementation plan** (Plan 1) — step-by-step plan with task tracking
- **Flutter Web UI implementation plan** (Plan 2) — phased plan for Agent Studio; all tasks marked complete
- **OpenSpec ADRs** — Architecture Decision Records for all major session decisions (5 ADRs covering domain model, memory architecture, security model, TUI design, multi-agent coordination)
- **100+ tracked tasks** in OpenSpec across all feature areas
- **Standalone demo instructions** and integration diagram in README
- **Competitive comparison table** in README covering feature parity with comparable open-source frameworks
- **GitHub Pages deployment workflow** for the project documentation site (`docs/`)
- **Zensical project docs** and MyST specs infrastructure (`docs/myst.yml`)
- **AGENTS.md** — agent protocol specification for this repository

#### Docker / DevOps

- **`docker-compose.yml`** — production compose file with agentic-core backend, PostgreSQL, Redis, FalkorDB, and Nginx reverse proxy
- **`docker-compose.test.yaml`** — test compose file for integration and e2e test runs
- **Dockerfile** updated for standalone mode: multi-stage build, copies pre-built Flutter Web assets, exposes ports 8000 and 8001
- **Flutter SDK removed from Docker build** — Flutter Web is pre-built locally and copied as static assets, reducing image size significantly
- **E2E smoke test** for the full agent lifecycle: create agent, send message, verify streaming response, delete agent (`tests/`)
- **GitHub Actions CD** — Flutter Web build step added to the continuous delivery workflow; ruff lint rules relaxed for CI and auto-fix enabled

### Changed

- `runtime.py` — refactored to use an async entrypoint (`asyncio.run`) and launch HTTP and WebSocket servers as concurrent tasks on separate ports
- `http_api.py` — static asset serving moved before SPA fallback route to prevent Flutter assets from matching the catch-all handler
- `bootstrap.py` — all adapters and services now registered through `ServiceRegistry` with dependency-ordered initialization and teardown
- Chat page renamed from "Cliente" to "Agent Personas" throughout the UI and routing layer
- Ruff lint configuration relaxed for generated code patterns; auto-fix applied to existing violations

### Fixed

- Docker build failure caused by Flutter SDK not being available in the CI image — resolved by pre-building Flutter Web locally
- Async entrypoint missing in `runtime.py` caused `RuntimeError: no running event loop` on startup
- Flutter Web static assets returned 404 when the SPA fallback catch-all was registered before the static file middleware
- Agent Studio terminal font not loading — xterm font stack corrected to use monospace system fonts
- Terminal emulator in Settings Debug tab rendered with incorrect character width — display width library updated

### Security

- **WebSocket origin validation** added to prevent cross-site WebSocket hijacking (addresses the class of vulnerability equivalent to CVE-2026-25253)
- **Prompt injection ensemble detector** (5 independent scanners) added to the middleware pipeline; all LLM inputs are screened before reaching the model
- **Output filter** screens all LLM-generated text for PII and policy violations before delivery to clients
- **Plugin integrity verification** rejects plugins whose manifests do not match their recorded SHA-256 checksums
- **Inter-agent message authentication** uses HMAC-SHA256 signatures; unsigned or incorrectly signed messages are dropped
- **Kill switch** allows operators to immediately halt all agent execution in response to a security incident
- **Credential vault** ensures agent secrets are never exposed in logs, traces, or API responses
- **Sandbox executor** isolates tool code execution with filesystem and network restrictions
- **Network egress policy** blocks outbound connections to hosts not on the per-agent allowlist
- **Command parser hardening** and **tool argument validation** close injection vectors via crafted tool inputs
- **MCP shadow detection** prevents rogue MCP servers from hijacking legitimate tool names
