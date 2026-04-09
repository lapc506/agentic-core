import 'package:flutter/material.dart';
import '../../theme/agent_studio_theme.dart';

class ToolsPage extends StatelessWidget {
  const ToolsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final tools = [
      {'name': 'rimm-classifier', 'desc': 'RIMM tariff classification', 'healthy': true},
      {'name': 'sac-lookup', 'desc': 'SAC code lookup', 'healthy': true},
      {'name': 'exchange-rate', 'desc': 'Currency exchange rates', 'healthy': false},
    ];

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Herramientas', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          const Text('MCP Servers & Skills', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
          const SizedBox(height: 16),
          ...tools.map((t) => Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: AgentStudioTheme.card, border: Border.all(color: AgentStudioTheme.border), borderRadius: BorderRadius.circular(8)),
            child: Row(children: [
              Icon(Icons.circle, size: 8, color: t['healthy'] as bool ? AgentStudioTheme.success : AgentStudioTheme.error),
              const SizedBox(width: 12),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(t['name']! as String, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
                Text(t['desc']! as String, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
              ]),
              const Spacer(),
              Text(t['healthy'] as bool ? 'Healthy' : 'Degraded',
                style: TextStyle(color: t['healthy'] as bool ? AgentStudioTheme.success : AgentStudioTheme.error, fontSize: 12)),
            ]),
          )),
        ],
      ),
    );
  }
}
