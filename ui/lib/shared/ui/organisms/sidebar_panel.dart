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
        _sectionHeader('RECIENTES'),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Text('No hay conversaciones aún',
            style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12, fontStyle: FontStyle.italic)),
        ),
      ],
    );
  }
}

class AgentsPanelContent extends StatelessWidget {
  const AgentsPanelContent({super.key, this.agents = const []});
  final List<Map<String, dynamic>> agents;
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader('AGENT PERSONAS'),
        for (final agent in agents)
          _panelItem(agent['name'] as String? ?? 'Agent',
            subtitle: agent['graph_template'] as String? ?? 'react'),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            border: Border.all(color: AgentStudioTheme.border),
            borderRadius: BorderRadius.circular(4),
          ),
          child: const Center(
            child: Text('+ Nuevo agente', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 12)),
          ),
        ),
      ],
    );
  }
}

Widget _sectionHeader(String text) => Padding(
  padding: const EdgeInsets.only(bottom: 8),
  child: Text(text, style: const TextStyle(
    color: AgentStudioTheme.primary, fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 1)),
);

Widget _panelItem(String label, {bool selected = false, String? subtitle}) => Container(
  margin: const EdgeInsets.only(bottom: 4),
  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
  decoration: BoxDecoration(
    color: selected ? AgentStudioTheme.card : Colors.transparent,
    border: selected ? const Border(left: BorderSide(color: AgentStudioTheme.primary, width: 3)) : null,
    borderRadius: BorderRadius.circular(4),
  ),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: TextStyle(
        color: selected ? AgentStudioTheme.textPrimary : AgentStudioTheme.textSecondary, fontSize: 13),
        overflow: TextOverflow.ellipsis),
      if (subtitle != null)
        Text(subtitle, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 10)),
    ],
  ),
);
