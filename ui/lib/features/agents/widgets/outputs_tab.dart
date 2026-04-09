import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

class OutputsTab extends StatefulWidget {
  const OutputsTab({super.key, this.agent = const {}, this.onChanged});
  final Map<String, dynamic> agent;
  final ValueChanged<Map<String, dynamic>>? onChanged;

  @override
  State<OutputsTab> createState() => _OutputsTabState();
}

class _OutputsTabState extends State<OutputsTab> {
  late String _outputFormat;
  late Set<String> _includedItems;
  late Set<String> _activeChannels;

  @override
  void initState() {
    super.initState();
    _outputFormat = widget.agent['output_format'] as String? ?? 'Markdown';
    _includedItems = Set<String>.from(
      (widget.agent['output_includes'] as List?) ?? ['Fuentes', 'Confianza'],
    );
    _activeChannels = Set<String>.from(
      (widget.agent['output_channels'] as List?) ?? ['WebSocket'],
    );
  }

  void _notifyChanged() {
    widget.onChanged?.call({
      ...widget.agent,
      'output_format': _outputFormat,
      'output_includes': _includedItems.toList(),
      'output_channels': _activeChannels.toList(),
    });
  }

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
                        selected: f == _outputFormat,
                        selectedColor: AgentStudioTheme.primary,
                        backgroundColor: AgentStudioTheme.card,
                        side: const BorderSide(
                            color: AgentStudioTheme.border),
                        onSelected: (selected) {
                          if (selected) {
                            setState(() => _outputFormat = f);
                            _notifyChanged();
                          }
                        },
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
                children: ['Fuentes', 'Confianza', 'Tool calls'].map((item) {
                  final selected = _includedItems.contains(item);
                  return FilterChip(
                    label: Text(item,
                        style: const TextStyle(fontSize: 12)),
                    selected: selected,
                    onSelected: (val) {
                      setState(() {
                        if (val) {
                          _includedItems.add(item);
                        } else {
                          _includedItems.remove(item);
                        }
                      });
                      _notifyChanged();
                    },
                    selectedColor:
                        AgentStudioTheme.primary.withValues(alpha: 0.2),
                    side: BorderSide(
                        color: selected
                            ? AgentStudioTheme.primary
                            : AgentStudioTheme.border),
                  );
                }).toList(),
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
              _channelTile(Icons.language, 'WebSocket'),
              _channelTile(Icons.send, 'Telegram'),
              _channelTile(Icons.chat, 'Slack'),
              _channelTile(Icons.mic, 'Voice'),
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

  Widget _channelTile(IconData icon, String label) {
    final active = _activeChannels.contains(label);
    return GestureDetector(
      onTap: () {
        setState(() {
          if (active) {
            _activeChannels.remove(label);
          } else {
            _activeChannels.add(label);
          }
        });
        _notifyChanged();
      },
      child: Container(
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
      ),
    );
  }
}
