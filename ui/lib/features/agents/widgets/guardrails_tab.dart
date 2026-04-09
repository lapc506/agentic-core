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
            const Text('Cantidad de Gates',
                style: TextStyle(
                    color: AgentStudioTheme.textPrimary,
                    fontSize: 14,
                    fontWeight: FontWeight.w600)),
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
      ],
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
