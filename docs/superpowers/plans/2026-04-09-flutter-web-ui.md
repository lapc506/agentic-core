# Flutter Web UI (Agent Studio) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full Agent Studio Flutter Web UI with sidebar navigation, chat home, agent editor with WYSIWYG gates, debug terminal, and metrics charts.

**Architecture:** Port aduanext's proven navigation shell (sidebar rail + panel + dashboard layout + GoRouter), customize theme, build feature pages on top. Atomic design with atoms/ molecules/ organisms/ templates/ pages/ directories.

**Tech Stack:** Flutter Web, go_router, graphic, flutter_quill + markdown_quill, xterm, web_socket_channel

**Spec:** `docs/superpowers/specs/2026-04-08-standalone-agent-studio-design.md`

---

## File Structure

All files under `ui/lib/`:

```
ui/lib/
├── main.dart                              # App entry, MaterialApp.router
├── theme/
│   └── agent_studio_theme.dart            # Dark theme tokens (from aduanext)
├── routing/
│   └── router.dart                        # GoRouter + ShellRoute
├── shared/
│   └── ui/
│       ├── atoms/
│       │   ├── status_badge.dart          # StatusBadge (green/yellow/red/blue)
│       │   ├── gate_badge.dart            # GateBadge (semaphore numbered)
│       │   └── counter_button.dart        # +/- counter
│       ├── molecules/
│       │   ├── agent_list_item.dart       # Agent in sidebar panel
│       │   ├── conversation_item.dart     # Chat history item
│       │   └── gate_header.dart           # Collapsed gate card header
│       ├── organisms/
│       │   ├── sidebar_rail.dart          # 56px icon rail (from aduanext)
│       │   └── sidebar_panel.dart         # 210px contextual panel
│       └── templates/
│           └── dashboard_layout.dart      # Rail + Panel + Content
├── features/
│   ├── chat/
│   │   └── chat_page.dart                 # Home: chat + agent selector
│   ├── agents/
│   │   ├── agent_editor_page.dart         # Tabs: Inputs/Guardrails/Outputs
│   │   ├── widgets/
│   │   │   ├── inputs_tab.dart            # Personalidad, Modelo, Tools cards
│   │   │   ├── guardrails_tab.dart        # Gates editor + Restricciones
│   │   │   ├── outputs_tab.dart           # Formato + Canales cards
│   │   │   └── gate_editor_card.dart      # Single gate with WYSIWYG
│   │   └── rules_page.dart               # Business rules editor
│   ├── sessions/
│   │   └── sessions_page.dart             # History + HITL escalations
│   ├── tools/
│   │   └── tools_page.dart                # MCP servers + health
│   ├── settings/
│   │   └── settings_page.dart             # Tabs: Conexiones, Modelos, Debug, Docker
│   └── metrics/
│       └── metrics_page.dart              # Charts dashboard (graphic)
└── services/
    └── api_client.dart                    # HTTP + WebSocket client
```

---

## Phase 1: Foundation (Shell navegable)

### Task 1: Theme System

**Files:**
- Create: `ui/lib/theme/agent_studio_theme.dart`

Port AduaNext's theme system, customized for Agent Studio:

- [ ] **Step 1: Create theme file**

```dart
// ui/lib/theme/agent_studio_theme.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AgentStudioTheme {
  AgentStudioTheme._();

  // Surfaces
  static const rail = Color(0xFF080810);
  static const panel = Color(0xFF0F0F1E);
  static const content = Color(0xFF12121E);
  static const card = Color(0xFF1A1A2E);
  static const border = Color(0xFF2A2A40);

  // Primary
  static const primary = Color(0xFF3B6FE0);
  static const primaryLight = Color(0xFF6B9FFF);

  // Text
  static const textPrimary = Color(0xFFE0E0F0);
  static const textSecondary = Color(0xFF666680);

  // Status
  static const success = Color(0xFF4CAF50);
  static const warning = Color(0xFF FF9800);
  static const error = Color(0xFFEF5350);
  static const info = Color(0xFF64B5F6);

  // Gate semaphore
  static const gateGreen = Color(0xFF4CAF50);
  static const gateYellow = Color(0xFFFF9800);
  static const gateBlue = Color(0xFF3B6FE0);
  static const gateRed = Color(0xFFEF5350);

  static ThemeData get darkTheme {
    return ThemeData.dark(useMaterial3: true).copyWith(
      scaffoldBackgroundColor: content,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        surface: card,
        onSurface: textPrimary,
        outline: border,
      ),
      textTheme: GoogleFonts.ubuntuTextTheme(ThemeData.dark().textTheme),
      dividerColor: border,
      cardTheme: const CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          side: BorderSide(color: border),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: content,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(color: border),
        ),
      ),
      tabBarTheme: const TabBarThemeData(
        labelColor: primary,
        unselectedLabelColor: textSecondary,
        indicatorColor: primary,
      ),
    );
  }
}
```

- [ ] **Step 2: Add google_fonts dependency**

Add to `ui/pubspec.yaml` dependencies:
```yaml
  google_fonts: ^6.0.0
```

Run: `cd ui && flutter pub get`

- [ ] **Step 3: Update main.dart to use theme**

```dart
import 'package:flutter/material.dart';
import 'theme/agent_studio_theme.dart';

void main() => runApp(const AgentStudioApp());

class AgentStudioApp extends StatelessWidget {
  const AgentStudioApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agent Studio',
      debugShowCheckedModeBanner: false,
      theme: AgentStudioTheme.darkTheme,
      home: const Scaffold(body: Center(child: Text('Agent Studio'))),
    );
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add ui/lib/theme/ ui/pubspec.yaml ui/lib/main.dart
git commit -m "feat(ui): add Agent Studio dark theme system"
```

---

### Task 2: Sidebar Rail + Panel

**Files:**
- Create: `ui/lib/shared/ui/organisms/sidebar_rail.dart`
- Create: `ui/lib/shared/ui/organisms/sidebar_panel.dart`

Port from aduanext, customize sections for Agent Studio.

- [ ] **Step 1: Create SidebarRail**

```dart
// ui/lib/shared/ui/organisms/sidebar_rail.dart
import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

class SidebarRail extends StatelessWidget {
  const SidebarRail({
    super.key,
    required this.selectedIndex,
    required this.onSelected,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;

  static const sections = [
    (icon: Icons.chat_bubble_outline, label: 'Chat'),
    (icon: Icons.person_outline, label: 'Cliente'),
    (icon: Icons.rule, label: 'Reglas'),
    (icon: Icons.history, label: 'Sesiones'),
    (icon: Icons.build_outlined, label: 'Herramientas'),
    (icon: Icons.settings_outlined, label: 'Sistema'),
    (icon: Icons.bar_chart, label: 'Métricas'),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      color: AgentStudioTheme.rail,
      child: Column(
        children: [
          const SizedBox(height: 12),
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: AgentStudioTheme.primary,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Center(
              child: Text('A', style: TextStyle(
                color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16,
              )),
            ),
          ),
          const SizedBox(height: 16),
          ...List.generate(sections.length, (i) {
            final section = sections[i];
            final selected = i == selectedIndex;
            return Tooltip(
              message: section.label,
              child: InkWell(
                onTap: () => onSelected(i),
                child: Container(
                  width: 40, height: 40,
                  margin: const EdgeInsets.symmetric(vertical: 2),
                  decoration: BoxDecoration(
                    color: selected ? AgentStudioTheme.card : Colors.transparent,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    section.icon, size: 20,
                    color: selected ? AgentStudioTheme.primary : AgentStudioTheme.textSecondary,
                  ),
                ),
              ),
            );
          }),
          const Spacer(),
          const CircleAvatar(
            radius: 16,
            backgroundColor: AgentStudioTheme.primary,
            child: Text('AP', style: TextStyle(color: Colors.white, fontSize: 11)),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Create SidebarPanel** (contextual, changes per section)

```dart
// ui/lib/shared/ui/organisms/sidebar_panel.dart
import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

class SidebarPanel extends StatelessWidget {
  const SidebarPanel({super.key, required this.selectedSection, required this.child});

  final int selectedSection;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 210,
      color: AgentStudioTheme.panel,
      padding: const EdgeInsets.all(12),
      child: child,
    );
  }
}

/// Panel content for the Chat section
class ChatPanelContent extends StatelessWidget {
  const ChatPanelContent({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader('CONVERSACIONES'),
        _panelItem('+ Nueva conversación', selected: true),
        const SizedBox(height: 16),
        _sectionHeader('HOY'),
        _panelItem('Clasificar partida 8471...', subtitle: 'Asistente · 2m'),
        _panelItem('Calcular CIF importación', subtitle: 'Asistente · 1h'),
      ],
    );
  }
}

/// Panel content for the Agents (Cliente) section
class AgentsPanelContent extends StatelessWidget {
  const AgentsPanelContent({super.key, this.agents = const []});
  final List<Map<String, dynamic>> agents;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader('CLIENTE'),
        for (final agent in agents)
          _panelItem(
            agent['name'] as String? ?? 'Agent',
            subtitle: agent['graph_template'] as String? ?? 'react',
          ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            border: Border.all(color: AgentStudioTheme.border, style: BorderStyle.solid),
            borderRadius: BorderRadius.circular(4),
          ),
          child: const Center(
            child: Text('+ Nuevo agente',
              style: TextStyle(color: AgentStudioTheme.primary, fontSize: 12)),
          ),
        ),
      ],
    );
  }
}

Widget _sectionHeader(String text) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(text, style: const TextStyle(
      color: AgentStudioTheme.primary,
      fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 1,
    )),
  );
}

Widget _panelItem(String label, {bool selected = false, String? subtitle}) {
  return Container(
    margin: const EdgeInsets.only(bottom: 4),
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    decoration: BoxDecoration(
      color: selected ? AgentStudioTheme.card : Colors.transparent,
      borderLeft: selected ? const BorderSide(color: AgentStudioTheme.primary, width: 3) : null,
      borderRadius: BorderRadius.circular(4),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(
          color: selected ? AgentStudioTheme.textPrimary : AgentStudioTheme.textSecondary,
          fontSize: 13,
        ), overflow: TextOverflow.ellipsis),
        if (subtitle != null)
          Text(subtitle, style: const TextStyle(
            color: AgentStudioTheme.textSecondary, fontSize: 10)),
      ],
    ),
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add ui/lib/shared/
git commit -m "feat(ui): add SidebarRail and SidebarPanel organisms"
```

---

### Task 3: Dashboard Layout Template

**Files:**
- Create: `ui/lib/shared/ui/templates/dashboard_layout.dart`

- [ ] **Step 1: Create DashboardLayout**

```dart
// ui/lib/shared/ui/templates/dashboard_layout.dart
import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';
import '../organisms/sidebar_rail.dart';
import '../organisms/sidebar_panel.dart';

class DashboardLayout extends StatefulWidget {
  const DashboardLayout({
    super.key,
    required this.child,
    required this.selectedSection,
    required this.onSectionChanged,
    this.panelContent,
  });

  final Widget child;
  final int selectedSection;
  final ValueChanged<int> onSectionChanged;
  final Widget? panelContent;

  @override
  State<DashboardLayout> createState() => _DashboardLayoutState();
}

class _DashboardLayoutState extends State<DashboardLayout> {
  bool _panelExpanded = true;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final showPanel = width > 768 && _panelExpanded && widget.panelContent != null;

    return Scaffold(
      body: Row(
        children: [
          SidebarRail(
            selectedIndex: widget.selectedSection,
            onSelected: (i) {
              if (i == widget.selectedSection) {
                setState(() => _panelExpanded = !_panelExpanded);
              } else {
                widget.onSectionChanged(i);
                setState(() => _panelExpanded = true);
              }
            },
          ),
          if (showPanel)
            Container(
              decoration: const BoxDecoration(
                border: Border(right: BorderSide(color: AgentStudioTheme.border)),
              ),
              child: SidebarPanel(
                selectedSection: widget.selectedSection,
                child: widget.panelContent!,
              ),
            ),
          Expanded(child: widget.child),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add ui/lib/shared/ui/templates/
git commit -m "feat(ui): add DashboardLayout template"
```

---

### Task 4: GoRouter + Placeholder Pages

**Files:**
- Create: `ui/lib/routing/router.dart`
- Create: `ui/lib/features/chat/chat_page.dart`
- Create: `ui/lib/features/agents/agent_editor_page.dart`
- Create: `ui/lib/features/sessions/sessions_page.dart`
- Create: `ui/lib/features/tools/tools_page.dart`
- Create: `ui/lib/features/settings/settings_page.dart`
- Create: `ui/lib/features/metrics/metrics_page.dart`
- Create: `ui/lib/features/agents/rules_page.dart`
- Modify: `ui/lib/main.dart`
- Modify: `ui/pubspec.yaml`

- [ ] **Step 1: Add go_router dependency**

In `ui/pubspec.yaml`:
```yaml
  go_router: ^14.0.0
```

Run: `cd ui && flutter pub get`

- [ ] **Step 2: Create placeholder pages** (one per feature, ~15-20 lines each)

Each page is a simple StatelessWidget showing its name. Example pattern:

```dart
// ui/lib/features/chat/chat_page.dart
import 'package:flutter/material.dart';
import '../../theme/agent_studio_theme.dart';

class ChatPage extends StatelessWidget {
  const ChatPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Text('Chat — Coming soon',
        style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 18)),
    );
  }
}
```

Create the same pattern for: AgentEditorPage, RulesPage, SessionsPage, ToolsPage, SettingsPage, MetricsPage.

- [ ] **Step 3: Create router with ShellRoute**

```dart
// ui/lib/routing/router.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../shared/ui/templates/dashboard_layout.dart';
import '../shared/ui/organisms/sidebar_panel.dart';
import '../features/chat/chat_page.dart';
import '../features/agents/agent_editor_page.dart';
import '../features/agents/rules_page.dart';
import '../features/sessions/sessions_page.dart';
import '../features/tools/tools_page.dart';
import '../features/settings/settings_page.dart';
import '../features/metrics/metrics_page.dart';

final router = GoRouter(
  initialLocation: '/',
  routes: [
    ShellRoute(
      builder: (context, state, child) {
        final section = _sectionFromPath(state.uri.path);
        return DashboardLayout(
          selectedSection: section,
          onSectionChanged: (i) => context.go(_pathFromSection(i)),
          panelContent: _panelForSection(section),
          child: child,
        );
      },
      routes: [
        GoRoute(path: '/', builder: (_, __) => const ChatPage()),
        GoRoute(path: '/agents/:id', builder: (_, state) =>
          AgentEditorPage(agentSlug: state.pathParameters['id']!)),
        GoRoute(path: '/rules/:id', builder: (_, state) =>
          RulesPage(agentSlug: state.pathParameters['id']!)),
        GoRoute(path: '/sessions', builder: (_, __) => const SessionsPage()),
        GoRoute(path: '/tools', builder: (_, __) => const ToolsPage()),
        GoRoute(path: '/settings', builder: (_, __) => const SettingsPage()),
        GoRoute(path: '/metrics', builder: (_, __) => const MetricsPage()),
      ],
    ),
  ],
);

int _sectionFromPath(String path) {
  if (path == '/') return 0;
  if (path.startsWith('/agents')) return 1;
  if (path.startsWith('/rules')) return 2;
  if (path.startsWith('/sessions')) return 3;
  if (path.startsWith('/tools')) return 4;
  if (path.startsWith('/settings')) return 5;
  if (path.startsWith('/metrics')) return 6;
  return 0;
}

String _pathFromSection(int section) {
  return switch (section) {
    0 => '/',
    1 => '/agents/new',
    2 => '/rules/new',
    3 => '/sessions',
    4 => '/tools',
    5 => '/settings',
    6 => '/metrics',
    _ => '/',
  };
}

Widget? _panelForSection(int section) {
  return switch (section) {
    0 => const ChatPanelContent(),
    1 => const AgentsPanelContent(),
    _ => null,
  };
}
```

- [ ] **Step 4: Update main.dart to use router**

```dart
// ui/lib/main.dart
import 'package:flutter/material.dart';
import 'theme/agent_studio_theme.dart';
import 'routing/router.dart';

void main() => runApp(const AgentStudioApp());

class AgentStudioApp extends StatelessWidget {
  const AgentStudioApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Agent Studio',
      debugShowCheckedModeBanner: false,
      theme: AgentStudioTheme.darkTheme,
      routerConfig: router,
    );
  }
}
```

- [ ] **Step 5: Verify flutter build**

Run: `cd ui && flutter analyze && flutter build web --release`

- [ ] **Step 6: Commit**

```bash
git add ui/
git commit -m "feat(ui): add GoRouter navigation shell with placeholder pages"
```

---

### Task 5: API Client Service

**Files:**
- Create: `ui/lib/services/api_client.dart`
- Modify: `ui/pubspec.yaml`

- [ ] **Step 1: Add http dependency**

```yaml
  http: ^1.0.0
```

- [ ] **Step 2: Create ApiClient**

```dart
// ui/lib/services/api_client.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  ApiClient({String? baseUrl}) : _baseUrl = baseUrl ?? '';

  final String _baseUrl;

  Future<Map<String, dynamic>> health() async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/health'));
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listAgents() async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents'));
    final list = jsonDecode(resp.body) as List;
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> getAgent(String slug) async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents/$slug'));
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createAgent(Map<String, dynamic> data) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/agents'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateAgent(String slug, Map<String, dynamic> data) async {
    final resp = await http.put(
      Uri.parse('$_baseUrl/api/agents/$slug'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<void> deleteAgent(String slug) async {
    await http.delete(Uri.parse('$_baseUrl/api/agents/$slug'));
  }

  Future<List<dynamic>> getGates(String slug) async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents/$slug/gates'));
    return jsonDecode(resp.body) as List;
  }

  Future<List<dynamic>> updateGates(String slug, List<Map<String, dynamic>> gates) async {
    final resp = await http.put(
      Uri.parse('$_baseUrl/api/agents/$slug/gates'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'gates': gates}),
    );
    return jsonDecode(resp.body) as List;
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add ui/lib/services/ ui/pubspec.yaml
git commit -m "feat(ui): add API client service for agentic-core REST endpoints"
```

---

## Phase 2: Chat Page (Home) — separate plan
## Phase 3: Agent Editor — separate plan
## Phase 4: Settings, Terminal, Metrics — separate plan
