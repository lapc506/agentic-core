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

## Connecting to a Remote Instance

```bash
./agent-studio-tui --url wss://your-agent-studio.example.com
```

The TUI uses the same WebSocket protocol as the Flutter UI — see [WebSocket Protocol](api/websocket.md) for message format details.
