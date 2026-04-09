import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

class InputsTab extends StatelessWidget {
  const InputsTab({super.key, required this.agent});
  final Map<String, dynamic> agent;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildCard(
          icon: Icons.theater_comedy,
          title: 'Personalidad',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _labeledField('Nombre del agente', agent['name'] ?? ''),
              const SizedBox(height: 12),
              _labeledField('System prompt', agent['system_prompt'] ?? '',
                  multiline: true),
              const SizedBox(height: 12),
              _label('Tono'),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                children: ['Profesional', 'Casual', 'Tecnico']
                    .map(
                      (t) => ChoiceChip(
                        label: Text(t, style: const TextStyle(fontSize: 12)),
                        selected: t == 'Profesional',
                        selectedColor: AgentStudioTheme.primary,
                        backgroundColor: AgentStudioTheme.card,
                        side:
                            const BorderSide(color: AgentStudioTheme.border),
                      ),
                    )
                    .toList(),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        _buildCard(
          icon: Icons.psychology,
          title: 'Modelo & Template',
          child: Row(
            children: [
              Expanded(
                child: _labeledField('Proveedor / Modelo',
                    agent['model'] ?? 'anthropic / claude-sonnet-4-6'),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _labeledField(
                    'Graph template', agent['graph_template'] ?? 'react'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        _buildCard(
          icon: Icons.build,
          title: 'Herramientas asignadas',
          trailing: TextButton(
            onPressed: () {},
            child: const Text('+ Agregar',
                style: TextStyle(
                    color: AgentStudioTheme.primary, fontSize: 12)),
          ),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: ((agent['tools'] as List?) ?? [])
                .map<Widget>(
                  (tool) => Chip(
                    label: Text(tool.toString(),
                        style: const TextStyle(
                            fontSize: 12,
                            color: AgentStudioTheme.textPrimary)),
                    deleteIcon: const Icon(Icons.close,
                        size: 14, color: AgentStudioTheme.textSecondary),
                    onDeleted: () {},
                    backgroundColor: AgentStudioTheme.content,
                    side:
                        const BorderSide(color: AgentStudioTheme.border),
                    avatar: const Icon(Icons.circle,
                        size: 8, color: AgentStudioTheme.success),
                  ),
                )
                .toList(),
          ),
        ),
      ],
    );
  }

  Widget _buildCard({
    required IconData icon,
    required String title,
    required Widget child,
    Widget? trailing,
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
                const Spacer(),
                if (trailing != null) trailing,
              ],
            ),
          ),
          Padding(padding: const EdgeInsets.all(16), child: child),
        ],
      ),
    );
  }

  Widget _label(String text) => Text(text,
      style: const TextStyle(
          color: AgentStudioTheme.textSecondary, fontSize: 11));

  Widget _labeledField(String label, String value,
      {bool multiline = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label(label),
        const SizedBox(height: 4),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AgentStudioTheme.content,
            border: Border.all(color: AgentStudioTheme.border),
            borderRadius: BorderRadius.circular(6),
          ),
          constraints:
              multiline ? const BoxConstraints(minHeight: 60) : null,
          child: Text(value,
              style: const TextStyle(
                  color: AgentStudioTheme.textPrimary, fontSize: 13)),
        ),
      ],
    );
  }
}
