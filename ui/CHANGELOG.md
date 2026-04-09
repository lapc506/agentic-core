# Changelog — Agent Studio (Flutter Web UI)

All notable changes to the Agent Studio Flutter Web application are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-04-08

### Added

#### Theme & Layout

- **Dark theme system** — `AgentStudioTheme` provides a consistent deep-blue/slate color palette built on Google Fonts (Inter). Includes `ColorScheme`, `TextTheme`, `InputDecorationTheme`, and `ElevatedButtonThemeData` so every widget inherits the Studio brand without per-widget overrides (`lib/theme/agent_studio_theme.dart`)
- **SidebarRail** — slim icon rail on the far left for top-level navigation between Studio sections; highlights the active destination and responds to keyboard focus (`lib/shared/ui/organisms/sidebar_rail.dart`)
- **SidebarPanel** — expanding contextual panel that slides in alongside the rail to show section-specific secondary navigation or filters (`lib/shared/ui/organisms/sidebar_panel.dart`)
- **DashboardLayout template** — composites `SidebarRail`, `SidebarPanel`, and the main content area into a stable shell; pages slot into the content area without reimplementing chrome (`lib/shared/ui/templates/dashboard_layout.dart`)
- **Agent Studio favicon** — custom blue "A" icon set as the web app's favicon; Open Graph meta tags added to `web/index.html` for correct link previews

#### Navigation

- **GoRouter navigation shell** — declarative routing with `ShellRoute`; 7 top-level destinations each render inside `DashboardLayout` without a full page transition: Chat, Agents, Sessions, Tools, Metrics, Settings, Onboarding (`lib/routing/router.dart`)
- Deep-link support for all routes; browser back/forward navigation works correctly with the SPA fallback on the backend

#### Services

- **API client** — typed Dart HTTP client covering all agentic-core REST endpoints (agents CRUD, tools list, metrics, config, setup-status). Handles JSON serialization, error unwrapping, and retry on transient 5xx responses (`lib/services/api_client.dart`)
- **WebSocket client** — persistent, auto-reconnecting WebSocket connection to the backend chat port. Exposes a `Stream<String>` for incoming chunks and a `send(String)` method for outgoing messages; reconnects with exponential back-off after disconnect (`lib/services/ws_client.dart`)
- **SOUL.md generator** — converts an agent's in-memory state into a portable Markdown persona document suitable for sharing or version control (`lib/services/soul_md_generator.dart`)

#### Chat

- **Chat page** — real-time streaming chat interface: agent selector dropdown, scrollable message history, and an input bar. Messages stream token-by-token over WebSocket and render incrementally in the message list (`lib/features/chat/chat_page.dart`)
- **GenUI Chat page** — full rewrite of the chat page using the `genui` package and A2A protocol. Agent responses may contain rich generative UI components (cards, tables, forms, charts) rendered inline alongside plain text. Falls back gracefully to plain text for non-UI responses (`lib/features/chat/genui_chat_page.dart`)
- **Agent selector widget** — dropdown populated from the API client's agent list; selection is persisted in the session and shown in the app bar (`lib/features/chat/widgets/agent_selector.dart`)
- **Chat input bar** — multiline text field with send button and keyboard shortcut (Shift+Enter for newline, Enter to send); disabled while a response is streaming (`lib/features/chat/widgets/chat_input_bar.dart`)
- **Message bubble** — renders individual chat turns with role-based styling (user vs. agent), markdown rendering for agent messages, and copy-to-clipboard action (`lib/features/chat/widgets/message_bubble.dart`)
- **ChatMessage model** — immutable Dart class for a single chat turn with role, content, timestamp, and optional generative UI payload (`lib/features/chat/models/chat_message.dart`)

#### Agent Management

- **Agent editor page** — full CRUD form for creating and editing agents; fields cover name, model, system prompt, provider, and gate configuration. Changes are persisted via the API client on save (`lib/features/agents/agent_editor_page.dart`)
- **Rules page** — manage behavioral rules attached to an agent; rules are ordered list items that are appended to the system prompt at dispatch time (`lib/features/agents/rules_page.dart`)
- **Gate editor card** — individual gate configuration card. Uses `flutter_quill` for rich-text editing of gate descriptions and YAML threshold values; supports add/remove/reorder (`lib/features/agents/widgets/gate_editor_card.dart`)
- **Guardrails tab** — gate-focused tab within the agent editor showing all configured gates in a `GateEditorCard` list (`lib/features/agents/widgets/guardrails_tab.dart`)
- **Inputs tab** — configures allowed input modalities (text, image, audio) and required input schema for the agent (`lib/features/agents/widgets/inputs_tab.dart`)
- **Outputs tab** — configures expected output formats (Markdown, JSON, tool call) and output schema validation (`lib/features/agents/widgets/outputs_tab.dart`)

#### Settings

- **Settings page** with tabbed layout: General (provider config, model defaults), Appearance (theme toggle placeholder), Debug (`lib/features/settings/settings_page.dart`)
- **Debug tab with xterm terminal** — embedded `xterm.js` terminal widget (via the `xterm` Flutter package) that streams live backend logs over WebSocket. Terminal font corrected to a monospace stack; character width rendering fixed
- **Providers UI** — sub-section within Settings for managing LLM provider entries (name, base URL, API key, default model); changes saved to `studio_config.json` via the config endpoint

#### Observability Pages

- **Metrics page** — per-agent analytics dashboard: token usage over time, cost breakdown, and request latency histograms rendered with the `graphic` charting library (`lib/features/metrics/metrics_page.dart`)
- **Sessions page** — paginated, filterable table of active and historical sessions with session ID, agent, start time, duration, and status columns (`lib/features/sessions/sessions_page.dart`)
- **Tools page** — lists all tools registered with the backend; each row shows the tool name, description, input schema (JSON), and most recent invocation status (`lib/features/tools/tools_page.dart`)

#### Onboarding

- **Onboarding dialog** — first-run wizard displayed when `/api/setup-status` reports incomplete configuration. Guides the user through setting a provider API key and default model before reaching the main Studio UI (`lib/features/onboarding/onboarding_dialog.dart`)

### Changed

- Chat destination renamed from "Cliente" to "Agent Personas" in the sidebar rail labels and GoRouter path names to better reflect its purpose
- Terminal font stack in the xterm widget updated from a custom font to system monospace fonts to fix rendering on Linux/Windows browsers

### Fixed

- xterm terminal widget displayed characters at incorrect width on non-macOS browsers — resolved by removing the custom bitmap font reference and letting xterm use the system monospace font
- GoRouter redirect loop on first launch when `setup-status` was incomplete — fixed by adding an explicit `redirect` guard in the router that only fires once
- WebSocket client reconnect caused duplicate message delivery — fixed by clearing the in-flight message buffer on disconnect before reconnecting

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `go_router` | ^14.0.0 | Declarative routing with `ShellRoute` |
| `web_socket_channel` | ^3.0.0 | WebSocket client |
| `flutter_quill` | ^11.0.0 | Rich-text WYSIWYG editor in gate cards |
| `xterm` | ^4.0.0 | Terminal emulator in Settings Debug tab |
| `graphic` | ^2.0.0 | Charts on the Metrics page |
| `genui` | ^0.8.0 | Generative UI rendering in GenUI Chat page |
| `google_fonts` | ^6.0.0 | Inter font for the Studio theme |
| `http` | ^1.0.0 | HTTP client underlying the API client service |
