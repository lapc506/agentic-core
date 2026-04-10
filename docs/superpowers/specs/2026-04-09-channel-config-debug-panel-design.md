# Channel Config Dialogs + Debug Split Panel — Design Spec

**Date:** 2026-04-09
**Status:** Approved

## 1. Channel Config — Inline Expand

Each channel tile in the Outputs tab expands on click to show configuration fields.

### Interaction
- Click tile → animates expand vertically, showing config fields below
- Toggle switch (colored) for active/inactive state
- Collapse by clicking the tile header again
- Pattern: same as gate editor cards and business rules

### Per-Channel Fields

| Channel | Fields |
|---|---|
| **WebSocket** | Port (default 8080), Path (/ws) — read-only, always active |
| **Telegram** | Bot Token, Webhook URL or Polling mode toggle |
| **Slack** | Bot Token, App-Level Token, Socket Mode / Events API toggle, Default Channel |
| **Discord** | Bot Token, Guild ID, Default Channel |
| **Voice** | Provider (ElevenLabs/OpenAI), API Key, Voice ID, Language |
| **WhatsApp** | Phone Number ID, Access Token, Verify Token |

### Save
- Each channel config saves to the agent's YAML via `PUT /api/agents/:slug`
- Channels stored in `agent.channels` dict

## 2. Debug Split Panel

Right-side panel showing real-time LLM thinking, tool calls, and gate results.

### Toggle
- Button "🔍 Debug ◂/▸" inline in the chat top bar, next to "● Conectado" pill
- Click toggles 320px right panel
- Panel slides with animation

### Content
- Session ID badge
- Live indicator "● live"
- Streaming log entries:
  - `[think]` (blue) — LLM reasoning/thinking
  - `[tool_call]` (orange) — tool name + args
  - `[tool_result]` (green) — result + timing
  - `[gate:Name]` (purple) — PASS/FAIL + timing
  - `[response]` (white) — final token count + latency
- Metrics card at bottom: tokens, latency, gates passed

### Data Source
- WebSocket messages: `stream_token` with metadata about type (think/tool/gate)
- Backend needs to send structured debug events alongside regular tokens
- Fallback: parse token content for patterns if backend doesn't send structured events

## Visual Mockups
Interactive mockups in `.superpowers/brainstorm/*/content/`:
- `channel-config-options.html` — 3 layout options (inline chosen)
- `debug-split-v2.html` — final approved design with toggle in top bar
