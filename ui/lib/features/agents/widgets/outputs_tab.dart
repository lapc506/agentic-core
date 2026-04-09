import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

class OutputsTab extends StatelessWidget {
  const OutputsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // Formato de respuesta
        _card(
          icon: Icons.output,
          title: 'Formato de respuesta',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Formato de salida',
                  style: TextStyle(
                      color: AgentStudioTheme.textSecondary, fontSize: 11)),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                children: ['Markdown', 'JSON', 'Plain text']
                    .map(
                      (f) => ChoiceChip(
                        label: Text(f, style: const TextStyle(fontSize: 12)),
                        selected: f == 'Markdown',
                        selectedColor: AgentStudioTheme.primary,
                        backgroundColor: AgentStudioTheme.card,
                        side: const BorderSide(
                            color: AgentStudioTheme.border),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 12),
              const Text('Incluir en respuesta',
                  style: TextStyle(
                      color: AgentStudioTheme.textSecondary, fontSize: 11)),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                children: [
                  FilterChip(
                    label: const Text('Fuentes',
                        style: TextStyle(fontSize: 12)),
                    selected: true,
                    onSelected: (_) {},
                    selectedColor:
                        AgentStudioTheme.primary.withValues(alpha: 0.2),
                    side: const BorderSide(
                        color: AgentStudioTheme.primary),
                  ),
                  FilterChip(
                    label: const Text('Confianza',
                        style: TextStyle(fontSize: 12)),
                    selected: true,
                    onSelected: (_) {},
                    selectedColor:
                        AgentStudioTheme.primary.withValues(alpha: 0.2),
                    side: const BorderSide(
                        color: AgentStudioTheme.primary),
                  ),
                  FilterChip(
                    label: const Text('Tool calls',
                        style: TextStyle(fontSize: 12)),
                    selected: false,
                    onSelected: (_) {},
                    side: const BorderSide(
                        color: AgentStudioTheme.border),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        // Canales de salida
        _card(
          icon: Icons.cell_tower,
          title: 'Canales de salida',
          child: Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _channelTile(Icons.language, 'WebSocket', true),
              _channelTile(Icons.send, 'Telegram', false),
              _channelTile(Icons.chat, 'Slack', false),
              _channelTile(Icons.mic, 'Voice', false),
            ],
          ),
        ),
      ],
    );
  }

  Widget _card({
    required IconData icon,
    required String title,
    required Widget child,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        border: Border.all(color: AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: const BoxDecoration(
              border: Border(
                bottom: BorderSide(color: AgentStudioTheme.border),
              ),
            ),
            child: Row(
              children: [
                Icon(icon,
                    size: 18, color: AgentStudioTheme.textPrimary),
                const SizedBox(width: 8),
                Text(title,
                    style: const TextStyle(
                        color: AgentStudioTheme.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          Padding(padding: const EdgeInsets.all(16), child: child),
        ],
      ),
    );
  }

  Widget _channelTile(IconData icon, String label, bool active) {
    return Container(
      width: 90,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AgentStudioTheme.content,
        border: Border.all(
            color:
                active ? AgentStudioTheme.success : AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Icon(icon,
              size: 24,
              color: active
                  ? AgentStudioTheme.textPrimary
                  : AgentStudioTheme.textSecondary),
          const SizedBox(height: 4),
          Text(label,
              style: TextStyle(
                  color: active
                      ? AgentStudioTheme.textPrimary
                      : AgentStudioTheme.textSecondary,
                  fontSize: 11)),
          Text(active ? 'Activo' : 'No config',
              style: TextStyle(
                  color: active
                      ? AgentStudioTheme.success
                      : AgentStudioTheme.textSecondary,
                  fontSize: 9)),
        ],
      ),
    );
  }
}
