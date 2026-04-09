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
        GoRoute(path: '/agents/:id', builder: (_, state) => AgentEditorPage(agentSlug: state.pathParameters['id']!)),
        GoRoute(path: '/rules/:id', builder: (_, state) => RulesPage(agentSlug: state.pathParameters['id']!)),
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

String _pathFromSection(int section) => switch (section) {
  0 => '/',
  1 => '/agents/new',
  2 => '/rules/new',
  3 => '/sessions',
  4 => '/tools',
  5 => '/settings',
  6 => '/metrics',
  _ => '/',
};

Widget? _panelForSection(int section) => switch (section) {
  0 => const ChatPanelContent(),
  1 => const AgentsPanelContent(),
  _ => null,
};
