import 'package:flutter/material.dart';
import '../../theme/agent_studio_theme.dart';

class RulesPage extends StatefulWidget {
  const RulesPage({super.key, required this.agentSlug});
  final String agentSlug;

  @override
  State<RulesPage> createState() => _RulesPageState();
}

class _RulesPageState extends State<RulesPage> {
  final List<Map<String, dynamic>> _rules = [
    {
      'name': 'Idioma de respuesta',
      'description': 'Siempre responder en el idioma del usuario',
      'type': 'output',
      'enabled': true,
    },
    {
      'name': 'Límite de scope',
      'description': 'No responder preguntas fuera del dominio configurado',
      'type': 'restriction',
      'enabled': true,
    },
    {
      'name': 'Citar fuentes',
      'description': 'Incluir referencias cuando se usen datos de herramientas',
      'type': 'output',
      'enabled': false,
    },
  ];

  static const _typeColors = {
    'output': AgentStudioTheme.primary,
    'restriction': AgentStudioTheme.error,
    'behavior': AgentStudioTheme.warning,
    'escalation': Color(0xFF9C27B0),
  };

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: AgentStudioTheme.border)),
          ),
          child: Row(
            children: [
              const Icon(Icons.rule, size: 20, color: AgentStudioTheme.textPrimary),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Reglas del Negocio',
                      style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
                  Text('Agente: ${widget.agentSlug}',
                      style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
                ],
              ),
              const Spacer(),
              const Text('Estas reglas se exportan al SOUL.md del agente',
                  style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11, fontStyle: FontStyle.italic)),
              const SizedBox(width: 16),
              FilledButton.icon(
                onPressed: _addRule,
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Agregar regla', style: TextStyle(fontSize: 12)),
                style: FilledButton.styleFrom(backgroundColor: AgentStudioTheme.primary),
              ),
            ],
          ),
        ),
        // Rule type filters
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          child: Row(
            children: [
              const Text('Filtrar: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
              const SizedBox(width: 8),
              ..._typeColors.entries.map((e) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(e.key, style: TextStyle(fontSize: 11, color: e.value)),
                  selected: true,
                  onSelected: (_) {},
                  selectedColor: e.value.withValues(alpha: 0.15),
                  checkmarkColor: e.value,
                  side: BorderSide(color: e.value.withValues(alpha: 0.3)),
                  backgroundColor: AgentStudioTheme.card,
                ),
              )),
            ],
          ),
        ),
        // Rules list
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(20),
            itemCount: _rules.length,
            itemBuilder: (_, i) => _ruleCard(i),
          ),
        ),
      ],
    );
  }

  Widget _ruleCard(int index) {
    final rule = _rules[index];
    final type = rule['type'] as String;
    final color = _typeColors[type] ?? AgentStudioTheme.textSecondary;
    final enabled = rule['enabled'] as bool;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        border: Border.all(color: enabled ? color.withValues(alpha: 0.4) : AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Switch(
            value: enabled,
            activeColor: color,
            onChanged: (v) => setState(() => _rules[index]['enabled'] = v),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Text(rule['name'] as String,
                      style: TextStyle(
                        color: enabled ? AgentStudioTheme.textPrimary : AgentStudioTheme.textSecondary,
                        fontSize: 14, fontWeight: FontWeight.w600,
                      )),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(type, style: TextStyle(color: color, fontSize: 10)),
                  ),
                ]),
                const SizedBox(height: 4),
                Text(rule['description'] as String,
                    style: TextStyle(
                      color: enabled ? AgentStudioTheme.textSecondary : AgentStudioTheme.border,
                      fontSize: 12,
                    )),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.edit_outlined, size: 16, color: AgentStudioTheme.textSecondary),
            onPressed: () {},
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline, size: 16, color: AgentStudioTheme.error),
            onPressed: () => setState(() => _rules.removeAt(index)),
          ),
        ],
      ),
    );
  }

  void _addRule() {
    final nameCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    String selectedType = 'behavior';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: AgentStudioTheme.card,
          title: const Text('Nueva regla de negocio',
              style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 16)),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameCtrl,
                  style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Nombre de la regla',
                    labelStyle: TextStyle(color: AgentStudioTheme.textSecondary),
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: descCtrl,
                  maxLines: 3,
                  style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Descripción / instrucción',
                    labelStyle: TextStyle(color: AgentStudioTheme.textSecondary),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: ['output', 'restriction', 'behavior', 'escalation'].map((t) {
                    final color = _typeColors[t]!;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(t, style: TextStyle(fontSize: 11, color: color)),
                        selected: selectedType == t,
                        selectedColor: color.withValues(alpha: 0.2),
                        backgroundColor: AgentStudioTheme.content,
                        side: BorderSide(color: selectedType == t ? color : AgentStudioTheme.border),
                        onSelected: (_) => setDialogState(() => selectedType = t),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancelar', style: TextStyle(color: AgentStudioTheme.textSecondary)),
            ),
            FilledButton(
              onPressed: () {
                if (nameCtrl.text.isNotEmpty) {
                  setState(() {
                    _rules.add({
                      'name': nameCtrl.text,
                      'description': descCtrl.text,
                      'type': selectedType,
                      'enabled': true,
                    });
                  });
                  Navigator.pop(ctx);
                }
              },
              style: FilledButton.styleFrom(backgroundColor: AgentStudioTheme.primary),
              child: const Text('Agregar'),
            ),
          ],
        ),
      ),
    );
  }
}
