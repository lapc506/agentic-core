# Changelog — agentic-tui (Go TUI)

All notable changes to the agentic-tui Go terminal user interface are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-04-08

### Added

#### Core TUI Framework

- **Bubble Tea TUI application** — full terminal UI built with `charm.land/bubbletea/v2`. The root `App` model manages global state, routes key events, and delegates rendering to child view models (`internal/ui/app.go`)
- **Dark lipgloss theme** — cohesive dark color palette using `charm.land/lipgloss/v2`. Defines border styles, selected/unselected item colors, accent colors, status indicators, and panel widths for consistent rendering across all views (`internal/ui/themes.go`, `internal/ui/styles.go`)
- **Tabbed layout** — four top-level tabs (Chat, Dashboard, Agents, Settings) navigable with number keys (`1`–`4`) or `Tab`/`Shift+Tab`; active tab highlighted in the status bar (`internal/ui/app.go`)
- **Single-key navigation** — vim-style bindings throughout: `j`/`k` to move up/down in lists, `g`/`G` to jump to top/bottom, `Enter` to select, `q`/`Esc` to go back, `/` to filter (`internal/ui/`)
- **Status bar** — persistent bottom bar showing current tab, active agent, session cost, and iteration count; updates on every model tick

#### Chat View

- **Chat view** — scrollable message history with role-based styling (user messages right-aligned in accent color, agent responses left-aligned in muted text). Streams tokens from the backend WebSocket as they arrive (`internal/ui/chat.go`)
- **HITL confirmation modal** — when the backend suspends execution for human approval, a blocking modal dialog appears in the chat view listing the proposed action and offering `[y]es` / `[n]o` / `[e]dit` choices (`internal/ui/chat.go`)
- **Tool call display** — inline tool call blocks show the tool name, argument table, and result or error beneath the agent turn that invoked the tool

#### Dashboard View

- **Dashboard view** — full-screen split-panel overview: left panel shows running agents with per-agent status (idle/thinking/tool-call/error), right panel shows a live event log with timestamps (`internal/ui/dashboard.go`)
- **System metrics panel** — embedded in the dashboard; shows backend health, total session cost, tokens consumed, and iteration budget remaining
- **Agent tree** — hierarchical tree widget that expands/collapses sub-agents spawned by a parent. Uses `lipgloss` tree rendering with indented connectors (`internal/ui/tree.go`)

#### Settings View

- **Settings view** — form-based configuration for backend URL, default model, cost limit, and iteration budget; changes are written to the TOML config file on save (`internal/ui/settings.go`)

#### Execution Engine

- **Execution engine** — drives multi-step agent task loops: sends a message to the backend, streams the response, detects tool calls, invokes tools, feeds results back, and repeats until completion or a budget limit is hit (`internal/engine/executor.go`)
- **Completion detector** — heuristic model that classifies each agent turn as intermediate or terminal using keyword patterns, response length, and absence of pending tool calls (`internal/engine/detector.go`)
- **Event system** — typed `Event` interface with concrete types for `AgentStarted`, `TurnCompleted`, `ToolCalled`, `ToolResult`, `HITLRequired`, `SessionCost`, `ErrorOccurred`, and `TaskDone`; dispatched through a buffered channel consumed by the TUI update loop (`internal/engine/events.go`)
- **Iteration logger** — writes a structured JSONL log entry for each iteration: turn index, model used, input/output token counts, cost, duration, and tool calls (`internal/engine/logger.go`)

#### Parallel Execution

- **Parallel task runner** — launches multiple agent tasks as goroutines, each with its own execution engine instance and event channel; results fan in to a merged display in the dashboard (`internal/engine/parallel.go`)
- **Per-task status display** — each parallel task has an individual status line in the dashboard showing its current state, cost, and most recent turn summary

#### Session Management

- **Session persistence** — serializes the full session state (messages, agent ID, cost totals, iteration count, config) to a TOML file in `~/.agentic-tui/sessions/`. Sessions are listed in the Sessions picker and can be resumed by name (`internal/engine/session.go`)
- **Checkpointing** — saves an execution snapshot after every N iterations (configurable). Checkpoints are stored alongside the session file and indexed by iteration number (`internal/engine/checkpoint.go`)
- **Rewind** — rolls execution back to any checkpoint from the TUI's checkpoint picker; restores message history, cost totals, and iteration counter to the checkpoint state (`internal/engine/rewind.go`)

#### Task Planning

- **Plan mode** — before executing a multi-step task, the agent produces a numbered plan. The TUI renders the plan in a dedicated pane and pauses for the user to confirm or edit individual steps before execution begins (`internal/engine/plan_mode.go`)
- **PRD task management** — import a Product Requirements Document (Markdown file) from disk. The TUI parses tasks from the PRD's checklist items and displays them as a managed task list with `[ ]` / `[x]` status; completing a task in the engine checks it off (`internal/engine/prd.go`)
- **Agent scratchpad** — per-agent ephemeral text area visible in the chat pane below the message history. The agent can write intermediate reasoning or notes to the scratchpad; content is preserved in the session file (`internal/engine/scratchpad.go`)

#### Model & Cost Management

- **Cost-aware model tiering** — assigns tasks to model tiers (fast/cheap, balanced, powerful/expensive) based on a complexity estimate derived from task length, tool count, and required reasoning depth. Tier thresholds and model names are user-configurable (`internal/engine/cost.go`)
- **Session cost tracker** — accumulates input and output token costs per turn using per-model pricing tables; surfaces the running total in the status bar and dashboard

#### Headless & CI Mode

- **Headless mode** — `--headless` flag runs the execution engine without any TUI rendering. Outputs structured JSONL to stdout for consumption by scripts and CI pipelines (`internal/engine/headless.go`)
- **Iteration logging in headless mode** — same structured JSONL log format as interactive mode; each line is a self-contained JSON object safe for `jq` processing

#### Extensibility

- **Plugin support** — at startup the TUI scans `~/.agentic-tui/plugins/` for `.so` shared libraries implementing the `TUIPlugin` interface; loaded plugins can register new commands and event handlers (`internal/engine/plugins.go`)
- **Custom commands** — user-defined slash commands configured in the TOML file. Each command maps a `/name` to either a backend REST endpoint (called with optional body interpolation) or a shell script (`internal/engine/commands.go`)
- **Task templates** — pre-built task templates selectable from the new-task dialog; templates populate the task description and optionally set a default model tier (`internal/engine/templates.go`)

#### Configuration

- **TOML config system** — all TUI settings live in `~/.agentic-tui/config.toml`. `Config` struct covers backend HTTP URL, WebSocket URL, default model, cost per token overrides, max iterations, checkpoint interval, keybinding overrides, and custom commands (`internal/config/config.go`)
- **Config manager** — loads config on startup with defaults; writes changes from the Settings view atomically to avoid partial writes (`internal/config/manager.go`)

#### Backend Integration

- **Typed Go API client** — wraps all agentic-core REST endpoints: list agents, get agent, create/update/delete agent, list tools, get metrics, send message (non-streaming), and get session. Uses `net/http` with a configurable timeout and retry on 429/503 (`internal/api/client.go`)
- **Remote session types** — Go structs matching the backend's JSON wire format for agents, sessions, tools, and metrics; used by both the API client and session persistence layer (`internal/types/`)

### Dependencies

| Module | Version | Purpose |
|--------|---------|---------|
| `charm.land/bubbletea/v2` | v2.0.2 | TUI event loop and component model |
| `charm.land/bubbles/v2` | v2.1.0 | Pre-built TUI components (textinput, list, spinner, table) |
| `charm.land/lipgloss/v2` | v2.0.2 | Terminal style and layout primitives |
| `github.com/pelletier/go-toml/v2` | v2.3.0 | TOML config and session file serialization |
| `golang.org/x/sync` | v0.19.0 | `errgroup` for parallel task management |
