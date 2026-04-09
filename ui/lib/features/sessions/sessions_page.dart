import 'package:flutter/material.dart';
import '../../theme/agent_studio_theme.dart';

class SessionsPage extends StatelessWidget {
  const SessionsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final sessions = [
      {'id': 'sess_01JK7...', 'agent': 'Asistente Aduanero', 'status': 'completed', 'messages': 12, 'duration': '4m 23s'},
      {'id': 'sess_01JK8...', 'agent': 'Doc Reviewer', 'status': 'active', 'messages': 3, 'duration': '1m 10s'},
      {'id': 'sess_01JK6...', 'agent': 'Asistente Aduanero', 'status': 'escalated', 'messages': 8, 'duration': '2m 45s'},
    ];
    final statusColors = {'completed': AgentStudioTheme.success, 'active': AgentStudioTheme.primary, 'escalated': AgentStudioTheme.warning};

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Sesiones', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.builder(
              itemCount: sessions.length,
              itemBuilder: (_, i) {
                final s = sessions[i];
                final statusColor = statusColors[s['status']] ?? AgentStudioTheme.textSecondary;
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: AgentStudioTheme.card, border: Border.all(color: AgentStudioTheme.border), borderRadius: BorderRadius.circular(8)),
                  child: Row(children: [
                    Text(s['id']! as String, style: const TextStyle(color: AgentStudioTheme.primaryLight, fontSize: 12, fontFamily: 'monospace')),
                    const SizedBox(width: 16),
                    Text(s['agent']! as String, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13)),
                    const Spacer(),
                    Text('${s['messages']} msgs', style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                    const SizedBox(width: 12),
                    Text(s['duration']! as String, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                    const SizedBox(width: 12),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(color: statusColor.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
                      child: Text(s['status']! as String, style: TextStyle(color: statusColor, fontSize: 10)),
                    ),
                  ]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
