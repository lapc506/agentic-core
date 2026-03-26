# Nice-to-Have Features Roadmap

Features inspired by Hermes Agent and OpenClaw that would enhance agentic-core.
Organized by priority and effort. Each links to a GitHub issue for tracking.

## Tier 1: High Impact, Medium Effort

### Voice Integration (TTS/STT)
**Inspired by:** Hermes Agent voice mode
**What exists:** WebSocket binary frames for audio, ElevenLabs placeholder
**What's missing:** Actual TTS engine integration (Edge TTS, NeuTTS, ElevenLabs), STT transcription (Whisper local, Google, Deepgram), voice recording config, auto-TTS toggle

```yaml
# Hermes config pattern to adopt:
voice:
  record_key: "ctrl+b"
  max_recording_seconds: 120
  auto_tts: false
stt:
  provider: "local"  # or: google, deepgram
  local:
    model: "base"  # whisper model
tts:
  provider: "edge"  # or: elevenlabs, neutts
  edge:
    voice: "en-US-AriaNeural"
```

### Scheduled Tasks / Cron Jobs
**Inspired by:** OpenClaw cron jobs + heartbeat, Hermes scheduled tasks
**What exists:** Nothing
**What's missing:** CronScheduler that triggers persona executions on schedule, heartbeat system for periodic checks, cron expression parsing

### Hooks System (PreToolUse, PostToolUse, Stop)
**Inspired by:** OpenClaw hooks architecture
**What exists:** Middleware chain (similar but different pattern)
**What's missing:** Event-driven hooks at granular points: before/after each tool call, on session stop, on agent error. Hooks can block execution (unlike middleware which wraps).

### MCP Tool Filtering (include/exclude per server)
**Inspired by:** Hermes MCP config
**What exists:** MCPBridgeAdapter with tool_prefix, healthcheck
**What's missing:** Per-server `include` and `exclude` lists for tools, ability to disable specific MCP utilities (prompts, resources)

```yaml
# Pattern to adopt:
mcp:
  servers:
    github:
      tools:
        include: [create_issue, list_issues]
        prompts: false
    stripe:
      tools:
        exclude: [delete_customer]
        resources: false
```

### Model Fallback Chains
**Inspired by:** OpenClaw model fallback + alias system
**What exists:** ModelConfig with single provider/model, 3-level cascade
**What's missing:** Fallback chain: try claude-opus -> if rate limited try gemini-pro -> if unavailable try local. Model aliases for convenience.

## Tier 2: Medium Impact, Medium Effort

### Execution Environments (Docker, SSH, Remote)
**Inspired by:** Hermes terminal backends
**What exists:** Local execution only
**What's missing:** Tool execution in isolated Docker containers, SSH remote execution, cloud execution (Daytona, Modal). Security: sandboxed command execution.

```yaml
# Pattern to adopt:
terminal:
  backend: docker  # local | docker | ssh | modal | daytona
  docker_image: python:3.12-slim
  timeout: 180
```

### Cross-Session Recall (Full-Text Search)
**Inspired by:** Hermes FTS5 cross-session recall with LLM summarization
**What exists:** Redis conversation cache (per-session), pgvector semantic search
**What's missing:** Full-text search across ALL sessions (PostgreSQL FTS or SQLite FTS5), LLM-powered summarization of past conversations for context injection

### Personality System (SOUL.md)
**Inspired by:** Hermes SOUL.md + personality presets
**What exists:** Persona YAML with role/description
**What's missing:** Rich personality definition file (SOUL.md) per persona with tone, style, constraints, example responses. Built-in presets (professional, casual, technical).

### Webhook Endpoints
**Inspired by:** OpenClaw POST /hooks/<name>
**What exists:** WebSocket + gRPC + CLI adapters
**What's missing:** HTTP webhook adapter: receive events from external systems (GitHub, Stripe, etc.), map to agent actions, template-based payload transformation

### Media Understanding Pipeline
**Inspired by:** OpenClaw media understanding config
**What exists:** MultimodalContent value object, Gemini multimodal embeddings
**What's missing:** Actual media processing: image description, audio transcription, video summarization. Model routing per media type. Byte limits and format validation.

```json
{
  "tools": {
    "media": {
      "image": {
        "enabled": true,
        "maxBytes": 10485760,
        "models": [
          {"provider": "google", "model": "gemini-2.5-pro"}
        ]
      }
    }
  }
}
```

### Plugin Architecture
**Inspired by:** OpenClaw plugins system
**What exists:** PersonaRegistry, MCP bridge
**What's missing:** Formal plugin system: plugin manifest, plugin lifecycle (activate/deactivate), plugin config, plugin marketplace discovery

## Tier 3: Lower Priority, Variable Effort

### Programmatic Tool Calling (execute_code)
**Inspired by:** Hermes execute_code tool
**What exists:** ToolPort.execute() for individual tools
**What's missing:** Ability for agent to write and execute Python scripts that chain multiple tool calls with logic between them. Useful when 3+ sequential tool calls with conditional branching needed.

### User Modeling (Dialectic)
**Inspired by:** Hermes Honcho dialectic user modeling
**What exists:** Session metadata
**What's missing:** User preference learning over time, behavioral patterns, communication style adaptation. Stored in FalkorDB knowledge graph.

### Platform Gateways (Telegram, Discord, Slack, WhatsApp)
**Inspired by:** Hermes unified gateway, OpenClaw multi-platform
**What exists:** WebSocket (Flutter), gRPC (backend), CLI
**What's missing:** Native adapters for messaging platforms. Each would be a new primary adapter implementing the same callback pattern.

### Terminal UI (TUI)
**Inspired by:** OpenClaw TUI
**What exists:** CLI adapter with streaming
**What's missing:** Rich terminal interface with panels (conversation, tools, status), keyboard shortcuts, session management

### Agent-to-Agent Communication
**Inspired by:** OpenClaw agent send CLI
**What exists:** Supervisor template delegates to sub-agents
**What's missing:** Direct inter-agent messaging: one agent sends a message to another by name, async response handling, agent discovery

### Context Files Injection
**Inspired by:** Hermes context files (AGENTS.md, SOUL.md, .cursorrules)
**What exists:** AGENTS.md for AI coding assistants
**What's missing:** Auto-injection of context files into agent prompts. Support for .cursorrules, project-specific knowledge files, persona-specific context.

### Autonomous Skill Creation
**Inspired by:** Hermes autonomous skill creation + agentskills.io
**What exists:** AutoResearchLoop for skill optimization, Skill entity
**What's missing:** Agent can CREATE new skills from successful task patterns, publish to skill registry, import community skills
