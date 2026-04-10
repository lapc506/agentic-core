import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

/// Channel definition with its config fields and color identity.
class _ChannelDef {
  const _ChannelDef({
    required this.key,
    required this.icon,
    required this.color,
    required this.fields,
  });
  final String key;
  final IconData icon;
  final Color color;
  final List<_FieldDef> fields;
}

enum _FieldType { readOnly, text, obscured, toggle, dropdown }

class _FieldDef {
  const _FieldDef({
    required this.key,
    required this.label,
    required this.type,
    this.defaultValue,
    this.options,
  });
  final String key;
  final String label;
  final _FieldType type;
  final String? defaultValue;
  final List<String>? options;
}

const _channels = [
  _ChannelDef(
    key: 'WebSocket',
    icon: Icons.language,
    color: AgentStudioTheme.primary,
    fields: [
      _FieldDef(key: 'port', label: 'Port', type: _FieldType.readOnly, defaultValue: '8080'),
      _FieldDef(key: 'path', label: 'Path', type: _FieldType.readOnly, defaultValue: '/ws'),
    ],
  ),
  _ChannelDef(
    key: 'Telegram',
    icon: Icons.send,
    color: Color(0xFF26A5E4),
    fields: [
      _FieldDef(key: 'bot_token', label: 'Bot Token', type: _FieldType.obscured),
      _FieldDef(key: 'mode', label: 'Mode', type: _FieldType.toggle, options: ['Webhook', 'Polling']),
    ],
  ),
  _ChannelDef(
    key: 'Slack',
    icon: Icons.chat,
    color: Color(0xFF4A154B),
    fields: [
      _FieldDef(key: 'bot_token', label: 'Bot Token', type: _FieldType.obscured),
      _FieldDef(key: 'app_token', label: 'App-Level Token', type: _FieldType.obscured),
      _FieldDef(key: 'mode', label: 'Mode', type: _FieldType.toggle, options: ['Socket Mode', 'Events API']),
      _FieldDef(key: 'default_channel', label: 'Default Channel', type: _FieldType.text),
    ],
  ),
  _ChannelDef(
    key: 'Voice',
    icon: Icons.mic,
    color: AgentStudioTheme.warning,
    fields: [
      _FieldDef(key: 'provider', label: 'Provider', type: _FieldType.dropdown, options: ['ElevenLabs', 'OpenAI']),
      _FieldDef(key: 'api_key', label: 'API Key', type: _FieldType.obscured),
      _FieldDef(key: 'voice_id', label: 'Voice ID', type: _FieldType.text),
    ],
  ),
];

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
  late Map<String, Map<String, String>> _channelConfigs;

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

    // Initialise per-channel config from agent data or defaults.
    final raw = widget.agent['channel_configs'] as Map<String, dynamic>? ?? {};
    _channelConfigs = {};
    for (final ch in _channels) {
      final saved = raw[ch.key] as Map<String, dynamic>? ?? {};
      final map = <String, String>{};
      for (final f in ch.fields) {
        map[f.key] = saved[f.key]?.toString() ?? f.defaultValue ?? (f.options?.first ?? '');
      }
      _channelConfigs[ch.key] = map;
    }
  }

  void _notifyChanged() {
    widget.onChanged?.call({
      ...widget.agent,
      'output_format': _outputFormat,
      'output_includes': _includedItems.toList(),
      'output_channels': _activeChannels.toList(),
      'channel_configs': _channelConfigs,
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
        // Canales de salida — expandable channel cards
        _card(
          icon: Icons.cell_tower,
          title: 'Canales de salida',
          child: Column(
            children: _channels.map((ch) => _channelCard(ch)).toList(),
          ),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Expandable channel card (rules_page.dart visual pattern)
  // ---------------------------------------------------------------------------

  Widget _channelCard(_ChannelDef ch) {
    final active = _activeChannels.contains(ch.key);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeInOut,
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        border: Border.all(
          color: active ? ch.color.withValues(alpha: 0.4) : AgentStudioTheme.border,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          // Header row — icon, name, switch
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: [
                Icon(ch.icon,
                    size: 20,
                    color: active ? ch.color : AgentStudioTheme.textSecondary),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(ch.key,
                          style: TextStyle(
                            color: active
                                ? AgentStudioTheme.textPrimary
                                : AgentStudioTheme.textSecondary,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          )),
                      Text(
                        active ? 'Activo' : 'Inactivo',
                        style: TextStyle(
                          color: active ? ch.color : AgentStudioTheme.textSecondary,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(
                    color: ch.color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    ch.key == 'WebSocket' ? 'siempre activo' : 'canal',
                    style: TextStyle(color: ch.color, fontSize: 10),
                  ),
                ),
                const SizedBox(width: 8),
                Switch(
                  value: active,
                  activeThumbColor: ch.color,
                  onChanged: ch.key == 'WebSocket'
                      ? null // WebSocket is always active
                      : (v) {
                          setState(() {
                            if (v) {
                              _activeChannels.add(ch.key);
                            } else {
                              _activeChannels.remove(ch.key);
                            }
                          });
                          _notifyChanged();
                        },
                ),
              ],
            ),
          ),

          // Expanded config fields — visible only when active
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 200),
            crossFadeState:
                active ? CrossFadeState.showFirst : CrossFadeState.showSecond,
            firstChild: Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              decoration: BoxDecoration(
                border: Border(
                  top: BorderSide(
                    color: ch.color.withValues(alpha: 0.2),
                  ),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 12),
                  ...ch.fields.map((f) => _buildField(ch, f)),
                ],
              ),
            ),
            secondChild: const SizedBox(width: double.infinity, height: 0),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Field renderers
  // ---------------------------------------------------------------------------

  Widget _buildField(_ChannelDef ch, _FieldDef f) {
    final config = _channelConfigs[ch.key]!;
    final value = config[f.key] ?? '';

    switch (f.type) {
      case _FieldType.readOnly:
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            children: [
              SizedBox(
                width: 100,
                child: Text(f.label,
                    style: const TextStyle(
                        color: AgentStudioTheme.textSecondary, fontSize: 12)),
              ),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: AgentStudioTheme.content,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AgentStudioTheme.border),
                  ),
                  child: Text(value,
                      style: const TextStyle(
                          color: AgentStudioTheme.textSecondary,
                          fontSize: 12,
                          fontFamily: 'monospace')),
                ),
              ),
            ],
          ),
        );

      case _FieldType.text:
      case _FieldType.obscured:
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            children: [
              SizedBox(
                width: 100,
                child: Text(f.label,
                    style: const TextStyle(
                        color: AgentStudioTheme.textSecondary, fontSize: 12)),
              ),
              Expanded(
                child: TextField(
                  obscureText: f.type == _FieldType.obscured,
                  controller: TextEditingController(text: value),
                  style: const TextStyle(
                      color: AgentStudioTheme.textPrimary, fontSize: 12),
                  decoration: InputDecoration(
                    isDense: true,
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    hintText: f.label,
                    hintStyle: const TextStyle(
                        color: AgentStudioTheme.textSecondary, fontSize: 12),
                    filled: true,
                    fillColor: AgentStudioTheme.content,
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(6),
                      borderSide:
                          const BorderSide(color: AgentStudioTheme.border),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(6),
                      borderSide: BorderSide(color: ch.color),
                    ),
                  ),
                  onChanged: (v) {
                    _channelConfigs[ch.key]![f.key] = v;
                    _notifyChanged();
                  },
                ),
              ),
            ],
          ),
        );

      case _FieldType.toggle:
        final options = f.options ?? [];
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            children: [
              SizedBox(
                width: 100,
                child: Text(f.label,
                    style: const TextStyle(
                        color: AgentStudioTheme.textSecondary, fontSize: 12)),
              ),
              ...options.map((opt) {
                final selected = value == opt;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(opt, style: TextStyle(fontSize: 11, color: selected ? Colors.white : AgentStudioTheme.textSecondary)),
                    selected: selected,
                    selectedColor: ch.color,
                    backgroundColor: AgentStudioTheme.content,
                    side: BorderSide(
                        color: selected ? ch.color : AgentStudioTheme.border),
                    onSelected: (_) {
                      setState(() => _channelConfigs[ch.key]![f.key] = opt);
                      _notifyChanged();
                    },
                  ),
                );
              }),
            ],
          ),
        );

      case _FieldType.dropdown:
        final options = f.options ?? [];
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            children: [
              SizedBox(
                width: 100,
                child: Text(f.label,
                    style: const TextStyle(
                        color: AgentStudioTheme.textSecondary, fontSize: 12)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: BoxDecoration(
                  color: AgentStudioTheme.content,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AgentStudioTheme.border),
                ),
                child: DropdownButton<String>(
                  value: options.contains(value) ? value : options.first,
                  dropdownColor: AgentStudioTheme.card,
                  underline: const SizedBox(),
                  style: const TextStyle(
                      color: AgentStudioTheme.textPrimary, fontSize: 12),
                  items: options
                      .map((o) => DropdownMenuItem(value: o, child: Text(o)))
                      .toList(),
                  onChanged: (v) {
                    if (v != null) {
                      setState(() => _channelConfigs[ch.key]![f.key] = v);
                      _notifyChanged();
                    }
                  },
                ),
              ),
            ],
          ),
        );
    }
  }

  // ---------------------------------------------------------------------------
  // Shared section card
  // ---------------------------------------------------------------------------

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
}
