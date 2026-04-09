# Agent Studio TUI

Terminal user interface for agentic-core, built with [Bubble Tea](https://github.com/charmbracelet/bubbletea).

## Usage

```bash
cd tui
go run . --url http://localhost:8080
```

## Keyboard shortcuts

- **Tab** / **Shift+Tab** -- Switch between Chat, Agents, Settings
- **Enter** -- Send message
- **j/k** -- Navigate agent list
- **r** -- Refresh agent list
- **Ctrl+C** -- Quit

## Build

```bash
go build -o agentic-tui .
./agentic-tui --url http://localhost:8080
```
