import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

class AgentSelector extends StatelessWidget {
  const AgentSelector({
    super.key,
    required this.agents,
    required this.selectedAgent,
    required this.onChanged,
    this.isConnected = false,
  });

  final List<Map<String, dynamic>> agents;
  final String? selectedAgent;
  final ValueChanged<String?> onChanged;
  final bool isConnected;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AgentStudioTheme.border)),
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: AgentStudioTheme.primary,
              borderRadius: BorderRadius.circular(6),
            ),
            child:
                const Icon(Icons.smart_toy, size: 16, color: Colors.white),
          ),
          const SizedBox(width: 8),
          DropdownButton<String>(
            value: selectedAgent,
            hint: const Text(
              'Seleccionar agente',
              style: TextStyle(
                color: AgentStudioTheme.textSecondary,
                fontSize: 13,
              ),
            ),
            dropdownColor: AgentStudioTheme.card,
            underline: const SizedBox(),
            style: const TextStyle(
              color: AgentStudioTheme.textPrimary,
              fontSize: 13,
            ),
            items: agents.map((a) {
              final slug = a['slug'] as String? ?? '';
              final name = a['name'] as String? ?? slug;
              return DropdownMenuItem(value: slug, child: Text(name));
            }).toList(),
            onChanged: onChanged,
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: isConnected
                  ? const Color(0xFF1a2e1a)
                  : const Color(0xFF2e1a1a),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              isConnected ? '● connected' : '○ disconnected',
              style: TextStyle(
                color: isConnected
                    ? AgentStudioTheme.success
                    : AgentStudioTheme.error,
                fontSize: 11,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
