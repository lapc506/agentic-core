# Go TUI

Agent Studio ships with a terminal UI written in Go. It provides a lightweight, keyboard-driven interface for interacting with agents when a browser is not available — useful for SSH sessions, CI pipelines, or headless servers.

---

## Starting the TUI

With the backend running (either via `make up` or the development workflow):

```bash
cd tui
go run . --url ws://localhost:8765
```

Or build a binary:

```bash
cd tui
go build -o agent-studio-tui .
./agent-studio-tui --url ws://localhost:8765
```

---

## Key Bindings

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Tab` | Switch between panels |
| `Ctrl+N` | New session |
| `Ctrl+A` | Select agent / persona |
| `Ctrl+L` | Clear chat history (display only) |
| `Ctrl+C` | Quit |
| `↑` / `↓` | Scroll message history |
| `PgUp` / `PgDn` | Scroll by page |

---

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | `ws://localhost:8765` | WebSocket endpoint |
| `--persona` | _(interactive)_ | Persona ID to use (skips agent selection screen) |
| `--session` | _(new)_ | Resume an existing session by ID |
| `--no-color` | `false` | Disable ANSI color output |

---

## Features

- **Streaming tokens** — responses stream character-by-character just like the web UI
- **HITL prompts** — human-in-the-loop escalation dialogs render inline
- **Tool call display** — shows tool names and arguments as the agent executes them
- **Session resume** — pass `--session <id>` to continue a previous conversation

---

## Ralph Patterns

The TUI implements 20 Ralph patterns across four categories.

### Core Engine

| Pattern | Description |
|---------|-------------|
| TUI-01 | Autonomous execution loop (5 phases: plan → act → observe → reflect → respond) |
| TUI-02 | Session persistence and crash recovery |
| TUI-03 | Completion token detection (stream end, error, HITL gate) |
| TUI-04 | Event-driven architecture — 22 typed event kinds |

### UI Views

| Pattern | Description |
|---------|-------------|
| TUI-05 | Single-key navigation (no mouse required) |
| TUI-06 | Dashboard view showing live status, progress bar, and running cost |
| TUI-07 | Agent tree visualisation for multi-agent workflows |

### Configuration

| Pattern | Description |
|---------|-------------|
| TUI-08 | Hierarchical config — 5-tier TOML (global → project → agent → session → flag) |
| TUI-09 | Prompt templates using Go `text/template` |
| TUI-10 | Theme system with 5 built-in themes |
| TUI-11 | Pluggable error strategies: retry, skip, or abort |

### Advanced Execution

| Pattern | Description |
|---------|-------------|
| TUI-12 | Parallel execution via git worktrees for isolated sub-agent runs |
| TUI-13 | Headless mode — structured JSON logs for CI pipelines |
| TUI-14 | Iteration logging to JSONL for offline analysis |

### Remote Management

| Pattern | Description |
|---------|-------------|
| TUI-15 | Remote instance management with HMAC-SHA256 authentication |
| TUI-16 | Plugin registry supporting Agent and Tracker plugin types |
| TUI-17 | Connection status indicators (connected / reconnecting / offline) |

### Task Management

| Pattern | Description |
|---------|-------------|
| TUI-18 | PRD-as-Fuel task format — feed a product spec directly as the agent's goal |
| TUI-19 | Cost-aware model tiering — automatically selects cheaper models for routine steps |
| TUI-20 | Agent scratchpad backed by a persistent `TODO.md` file |

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Language | Go 1.22+ |
| TUI framework | Bubble Tea (Charm) |
| Configuration | TOML (5-level inheritance) |
| Authentication | HMAC-SHA256 for remote instances |
| Logging | Structured JSONL |
| Parallelism | git worktrees for isolation |

---

## Connecting to a Remote Instance

```bash
./agent-studio-tui --url wss://your-agent-studio.example.com
```

The TUI uses the same WebSocket protocol as the Flutter UI — see [WebSocket Protocol](api/websocket.md) for message format details.
