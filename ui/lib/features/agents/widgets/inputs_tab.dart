import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

/// Inputs tab — Character file editor.
/// Fields: Personalidad (name, bio, system prompt), Lore & Style,
/// Modelo & Template, Actions (tools), Context Providers (knowledge sources).
class InputsTab extends StatefulWidget {
  const InputsTab({super.key, required this.agent, this.onChanged});
  final Map<String, dynamic> agent;
  final ValueChanged<Map<String, dynamic>>? onChanged;

  @override
  State<InputsTab> createState() => _InputsTabState();
}

class _InputsTabState extends State<InputsTab> {
  late final TextEditingController _nameCtrl;
  late final TextEditingController _bioCtrl;
  late final TextEditingController _systemPromptCtrl;
  late final TextEditingController _loreCtrl;
  late final TextEditingController _vocabularyCtrl;
  late final TextEditingController _modelCtrl;
  late final TextEditingController _graphTemplateCtrl;

  late String _selectedStyle;
  late bool _memoryEnabled;
  late Set<String> _selectedMemoryCategories;
  late Set<String> _enabledProviders;

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.agent['name'] as String? ?? '');
    _bioCtrl = TextEditingController(text: widget.agent['bio'] as String? ?? 'Un asistente experto en su dominio.');
    _systemPromptCtrl = TextEditingController(text: widget.agent['system_prompt'] as String? ?? '');
    _loreCtrl = TextEditingController(text: widget.agent['lore'] as String? ?? '');
    _vocabularyCtrl = TextEditingController(text: widget.agent['vocabulary'] as String? ?? '');
    _modelCtrl = TextEditingController(text: widget.agent['model'] as String? ?? '');
    _graphTemplateCtrl = TextEditingController(text: widget.agent['graph_template'] as String? ?? 'react');

    _selectedStyle = widget.agent['style'] as String? ?? 'Profesional';
    _memoryEnabled = widget.agent['memory_enabled'] as bool? ?? true;
    _selectedMemoryCategories = Set<String>.from(
      (widget.agent['memory_categories'] as List?) ?? ['preferences', 'goals', 'skills', 'context'],
    );
    _enabledProviders = Set<String>.from(
      (widget.agent['context_providers'] as List?) ?? ['RAG Documents', 'Session History'],
    );

    // Listen for changes on all controllers
    for (final ctrl in [_nameCtrl, _bioCtrl, _systemPromptCtrl, _loreCtrl, _vocabularyCtrl, _modelCtrl, _graphTemplateCtrl]) {
      ctrl.addListener(_notifyChanged);
    }
  }

  void _notifyChanged() {
    widget.onChanged?.call(_collectData());
  }

  Map<String, dynamic> _collectData() {
    return {
      ...widget.agent,
      'name': _nameCtrl.text,
      'bio': _bioCtrl.text,
      'system_prompt': _systemPromptCtrl.text,
      'lore': _loreCtrl.text,
      'vocabulary': _vocabularyCtrl.text,
      'style': _selectedStyle,
      'model': _modelCtrl.text,
      'graph_template': _graphTemplateCtrl.text,
      'memory_enabled': _memoryEnabled,
      'memory_categories': _selectedMemoryCategories.toList(),
      'context_providers': _enabledProviders.toList(),
    };
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _bioCtrl.dispose();
    _systemPromptCtrl.dispose();
    _loreCtrl.dispose();
    _vocabularyCtrl.dispose();
    _modelCtrl.dispose();
    _graphTemplateCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // --- Personalidad ---
        _buildCard(
          icon: Icons.theater_comedy,
          title: 'Personalidad',
          subtitle: 'Character file — SOUL.md',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _editableField('Nombre del agente', _nameCtrl),
              const SizedBox(height: 12),
              _editableField('Bio', _bioCtrl,
                  hint: 'Descripcion corta del agente — quien es y que hace'),
              const SizedBox(height: 12),
              _editableField('System prompt', _systemPromptCtrl, multiline: true,
                  hint: 'Instrucciones completas del agente'),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Lore & Style ---
        _buildCard(
          icon: Icons.auto_stories,
          title: 'Lore & Style',
          subtitle: 'Personalidad profunda del agente',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _editableField('Lore', _loreCtrl, multiline: true,
                  hint: 'Contexto de fondo, historia, valores del agente. Embebido como conocimiento base.'),
              const SizedBox(height: 12),
              _label('Estilo de respuesta'),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                children: ['Profesional', 'Casual', 'Tecnico', 'Empatico', 'Conciso'].map((t) =>
                  ChoiceChip(
                    label: Text(t, style: const TextStyle(fontSize: 12)),
                    selected: t == _selectedStyle,
                    selectedColor: AgentStudioTheme.primary,
                    backgroundColor: AgentStudioTheme.card,
                    side: const BorderSide(color: AgentStudioTheme.border),
                    onSelected: (selected) {
                      if (selected) {
                        setState(() => _selectedStyle = t);
                        _notifyChanged();
                      }
                    },
                  ),
                ).toList(),
              ),
              const SizedBox(height: 12),
              _editableField('Vocabulario / Tono', _vocabularyCtrl,
                  hint: 'Palabras o frases que el agente deberia usar o evitar. Ej: "Usar usted, evitar jerga tecnica"'),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Modelo & Template ---
        _buildCard(
          icon: Icons.psychology,
          title: 'Modelo & Template',
          child: Row(
            children: [
              Expanded(child: _editableField('Proveedor / Modelo', _modelCtrl,
                  hint: 'Configurado en Settings')),
              const SizedBox(width: 16),
              Expanded(child: _editableField('Graph template', _graphTemplateCtrl,
                  hint: 'react')),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Actions (tools) ---
        _buildCard(
          icon: Icons.bolt,
          title: 'Actions (Tools)',
          subtitle: 'Herramientas que el agente puede ejecutar',
          trailing: TextButton(
            onPressed: () {},
            child: const Text('+ Agregar', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 12)),
          ),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: ((widget.agent['tools'] as List?) ?? []).map<Widget>((tool) =>
              Chip(
                label: Text(tool.toString(), style: const TextStyle(fontSize: 12, color: AgentStudioTheme.textPrimary)),
                deleteIcon: const Icon(Icons.close, size: 14, color: AgentStudioTheme.textSecondary),
                onDeleted: () {},
                backgroundColor: AgentStudioTheme.content,
                side: const BorderSide(color: AgentStudioTheme.border),
                avatar: const Icon(Icons.bolt, size: 12, color: AgentStudioTheme.warning),
              ),
            ).toList(),
          ),
        ),
        const SizedBox(height: 16),

        // --- Context Providers ---
        _buildCard(
          icon: Icons.library_books,
          title: 'Context Providers',
          subtitle: 'Fuentes de conocimiento dinamico',
          trailing: TextButton(
            onPressed: () {},
            child: const Text('+ Agregar', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 12)),
          ),
          child: Column(
            children: [
              _providerRow('RAG Documents', 'Busqueda semantica en documentos'),
              _providerRow('Session History', 'Conversaciones pasadas del usuario'),
              _providerRow('Time & Date', 'Contexto temporal actual'),
              _providerRow('User Profile', 'Datos del usuario conectado'),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Memory ---
        _buildCard(
          icon: Icons.memory,
          title: 'Memory',
          subtitle: 'Auto-extract facts from conversations',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('Habilitar memoria', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13)),
                  const Spacer(),
                  Switch(
                    value: _memoryEnabled,
                    onChanged: (val) {
                      setState(() => _memoryEnabled = val);
                      _notifyChanged();
                    },
                    activeColor: AgentStudioTheme.primary,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Text('Categorias de memoria:', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: ['preferences', 'goals', 'skills', 'projects', 'context', 'feedback'].map((cat) =>
                  FilterChip(
                    label: Text(cat, style: const TextStyle(fontSize: 11)),
                    selected: _selectedMemoryCategories.contains(cat),
                    onSelected: (selected) {
                      setState(() {
                        if (selected) {
                          _selectedMemoryCategories.add(cat);
                        } else {
                          _selectedMemoryCategories.remove(cat);
                        }
                      });
                      _notifyChanged();
                    },
                    selectedColor: AgentStudioTheme.primary.withValues(alpha: 0.2),
                    backgroundColor: AgentStudioTheme.content,
                    side: BorderSide(color: _selectedMemoryCategories.contains(cat) ? AgentStudioTheme.primary : AgentStudioTheme.border),
                    checkmarkColor: AgentStudioTheme.primary,
                  ),
                ).toList(),
              ),
              const SizedBox(height: 8),
              const Row(
                children: [
                  Text('Dedup threshold: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
                  Text('0.9', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 11, fontFamily: 'monospace')),
                  SizedBox(width: 8),
                  Text('Max memories: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
                  Text('100', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 11, fontFamily: 'monospace')),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _providerRow(String name, String desc) {
    final enabled = _enabledProviders.contains(name);
    return GestureDetector(
      onTap: () {
        setState(() {
          if (enabled) {
            _enabledProviders.remove(name);
          } else {
            _enabledProviders.add(name);
          }
        });
        _notifyChanged();
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 6),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: AgentStudioTheme.content,
          border: Border.all(color: enabled ? AgentStudioTheme.primary.withValues(alpha: 0.3) : AgentStudioTheme.border),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          children: [
            Icon(enabled ? Icons.check_circle : Icons.circle_outlined, size: 16,
              color: enabled ? AgentStudioTheme.success : AgentStudioTheme.textSecondary),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: TextStyle(
                    color: enabled ? AgentStudioTheme.textPrimary : AgentStudioTheme.textSecondary, fontSize: 13, fontWeight: FontWeight.w500)),
                  Text(desc, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCard({required IconData icon, required String title, required Widget child, Widget? trailing, String? subtitle}) {
    return Container(
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        border: Border.all(color: AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AgentStudioTheme.border))),
            child: Row(
              children: [
                Icon(icon, size: 18, color: AgentStudioTheme.textPrimary),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
                      if (subtitle != null)
                        Text(subtitle, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 10)),
                    ],
                  ),
                ),
                if (trailing != null) trailing,
              ],
            ),
          ),
          Padding(padding: const EdgeInsets.all(16), child: child),
        ],
      ),
    );
  }

  Widget _label(String text) => Text(text, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11));

  Widget _editableField(String label, TextEditingController controller, {bool multiline = false, String? hint}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label(label),
        const SizedBox(height: 4),
        TextField(
          controller: controller,
          maxLines: multiline ? 5 : 1,
          style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
          decoration: InputDecoration(
            hintText: hint ?? '',
            hintStyle: const TextStyle(color: AgentStudioTheme.border, fontSize: 12),
            contentPadding: const EdgeInsets.all(8),
          ),
        ),
      ],
    );
  }
}
