import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';
import 'gate_editor_card.dart';

class GuardrailsTab extends StatefulWidget {
  const GuardrailsTab({super.key, required this.gates, this.onGatesChanged});
  final List<Map<String, dynamic>> gates;
  final ValueChanged<List<Map<String, dynamic>>>? onGatesChanged;

  @override
  State<GuardrailsTab> createState() => _GuardrailsTabState();
}

class _GuardrailsTabState extends State<GuardrailsTab> {
  late List<Map<String, dynamic>> _gates;

  @override
  void initState() {
    super.initState();
    _gates = List.from(widget.gates);
  }

  void _addGate() {
    setState(() {
      _gates.add({
        'name': 'New Gate',
        'content': '',
        'action': 'warn',
        'order': _gates.length,
      });
    });
    widget.onGatesChanged?.call(_gates);
  }

  void _removeGate(int index) {
    setState(() => _gates.removeAt(index));
    widget.onGatesChanged?.call(_gates);
  }

  void _updateGate(int index, Map<String, dynamic> gate) {
    setState(() => _gates[index] = gate);
    widget.onGatesChanged?.call(_gates);
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // Gate counter
        Row(
          children: [
            const Icon(Icons.traffic,
                size: 18, color: AgentStudioTheme.textPrimary),
            const SizedBox(width: 8),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Evaluators (Gates)',
                    style: TextStyle(
                        color: AgentStudioTheme.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w600)),
                Text('Post-response checks — ElizaOS evaluator pattern',
                    style: TextStyle(
                        color: AgentStudioTheme.textSecondary, fontSize: 10)),
              ],
            ),
            const SizedBox(width: 16),
            _counterButton(Icons.remove, () {
              if (_gates.isNotEmpty) _removeGate(_gates.length - 1);
            }),
            Container(
              width: 48,
              height: 48,
              margin: const EdgeInsets.symmetric(horizontal: 8),
              decoration: BoxDecoration(
                color: AgentStudioTheme.primary,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Text('${_gates.length}',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.bold)),
              ),
            ),
            _counterButton(Icons.add, _addGate),
          ],
        ),
        const SizedBox(height: 20),
        // Gate cards with arrows
        for (var i = 0; i < _gates.length; i++) ...[
          GateEditorCard(
            index: i,
            gate: _gates[i],
            onChanged: (g) => _updateGate(i, g),
            onDelete: () => _removeGate(i),
          ),
          if (i < _gates.length - 1)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 4),
              child: Center(
                child: Icon(Icons.arrow_downward,
                    size: 18, color: AgentStudioTheme.border),
              ),
            ),
        ],
        const SizedBox(height: 12),
        InkWell(
          onTap: _addGate,
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: AgentStudioTheme.border),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Center(
              child: Text('+ Agregar Gate',
                  style: TextStyle(
                      color: AgentStudioTheme.primary, fontSize: 13)),
            ),
          ),
        ),
        const SizedBox(height: 24),

        // --- LLM Judge (openclaw pattern) ---
        Container(
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
                child: const Row(
                  children: [
                    Icon(Icons.gavel, size: 18, color: AgentStudioTheme.textPrimary),
                    SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('LLM Judge', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
                          Text('Evalúa calidad de resultados de tools — openclaw pattern', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 10)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      children: [
                        const Text('Habilitar', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13)),
                        const Spacer(),
                        Switch(value: false, onChanged: null, activeColor: AgentStudioTheme.primary),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Text('Modo: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('Observe', style: TextStyle(fontSize: 11)), selected: true, selectedColor: AgentStudioTheme.primary, backgroundColor: AgentStudioTheme.content, side: const BorderSide(color: AgentStudioTheme.primary)),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('Enforce', style: TextStyle(fontSize: 11)), selected: false, backgroundColor: AgentStudioTheme.content, side: const BorderSide(color: AgentStudioTheme.border)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Text('Sample rate: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                        const Text('100%', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 12)),
                        const SizedBox(width: 16),
                        const Text('Timeout: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                        const Text('5000ms', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 12, fontFamily: 'monospace')),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Boundaries (openclaw: explicit deny list) ---
        Container(
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
                child: const Row(
                  children: [
                    Icon(Icons.block, size: 18, color: AgentStudioTheme.error),
                    SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Boundaries (Deny List)', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
                          Text('Lo que el agente NO puede hacer — SOUL.md Section 3', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 10)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    _boundaryRow('No proporcionar asesoría legal, médica ni financiera', true),
                    _boundaryRow('No ejecutar código ni acceder al sistema de archivos', true),
                    _boundaryRow('No revelar nombres internos de herramientas ni tablas', true),
                    _boundaryRow('No generar contenido que viole las políticas de Anthropic', true),
                    const SizedBox(height: 8),
                    InkWell(
                      onTap: () {},
                      child: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          border: Border.all(color: AgentStudioTheme.border, style: BorderStyle.solid),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Center(child: Text('+ Agregar boundary', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 12))),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _boundaryRow(String text, bool active) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AgentStudioTheme.content,
        border: Border.all(color: active ? AgentStudioTheme.error.withValues(alpha: 0.3) : AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        children: [
          Icon(Icons.do_not_disturb, size: 14, color: active ? AgentStudioTheme.error : AgentStudioTheme.textSecondary),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: TextStyle(color: active ? AgentStudioTheme.textPrimary : AgentStudioTheme.textSecondary, fontSize: 12))),
          IconButton(icon: const Icon(Icons.close, size: 14, color: AgentStudioTheme.textSecondary), onPressed: () {}),
        ],
      ),
    );
  }

  Widget _counterButton(IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: AgentStudioTheme.card,
          border: Border.all(color: AgentStudioTheme.border),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Icon(icon, size: 18, color: AgentStudioTheme.textPrimary),
      ),
    );
  }
}
