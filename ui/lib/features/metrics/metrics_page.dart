import 'package:flutter/material.dart';
import '../../theme/agent_studio_theme.dart';

class MetricsPage extends StatelessWidget {
  const MetricsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text('Métricas', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 18, fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        const Text('graphic integration coming soon', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
        const SizedBox(height: 20),
        // KPI row
        Row(
          children: [
            _kpiCard('Sesiones Activas', '12', Icons.people, AgentStudioTheme.primary),
            const SizedBox(width: 12),
            _kpiCard('Latencia p99', '320ms', Icons.speed, AgentStudioTheme.success),
            const SizedBox(width: 12),
            _kpiCard('Gates Pass Rate', '94%', Icons.verified, AgentStudioTheme.warning),
            const SizedBox(width: 12),
            _kpiCard('Tokens/hora', '14.2k', Icons.token, AgentStudioTheme.info),
          ],
        ),
        const SizedBox(height: 20),
        // Placeholder chart areas
        _chartPlaceholder('Latencia por agente', 'LineMark — p50 / p95 / p99 over time'),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(child: _chartPlaceholder('Token usage', 'IntervalMark — stacked by agent')),
            const SizedBox(width: 16),
            Expanded(child: _chartPlaceholder('Gate pass/fail', 'IntervalMark + Proportion')),
          ],
        ),
        const SizedBox(height: 16),
        _chartPlaceholder('Sesiones por hora', 'IntervalMark — count per period'),
      ],
    );
  }

  Widget _kpiCard(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AgentStudioTheme.card, border: Border.all(color: AgentStudioTheme.border), borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(icon, size: 16, color: color),
              const Spacer(),
              Text(value, style: TextStyle(color: color, fontSize: 22, fontWeight: FontWeight.bold)),
            ]),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
          ],
        ),
      ),
    );
  }

  Widget _chartPlaceholder(String title, String description) {
    return Container(
      height: 200,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AgentStudioTheme.card, border: Border.all(color: AgentStudioTheme.border), borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(description, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
          const Expanded(
            child: Center(
              child: Text('Chart placeholder\n(graphic integration pending)', textAlign: TextAlign.center,
                style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
            ),
          ),
        ],
      ),
    );
  }
}
