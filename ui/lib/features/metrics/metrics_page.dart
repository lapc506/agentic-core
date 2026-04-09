import 'package:flutter/material.dart';
import 'package:graphic/graphic.dart';
import '../../theme/agent_studio_theme.dart';

// ── Mock data ────────────────────────────────────────────────────────────────

final _latencyData = [
  {'time': '10:00', 'percentile': 'p50', 'value': 120},
  {'time': '10:00', 'percentile': 'p95', 'value': 250},
  {'time': '10:00', 'percentile': 'p99', 'value': 320},
  {'time': '11:00', 'percentile': 'p50', 'value': 115},
  {'time': '11:00', 'percentile': 'p95', 'value': 230},
  {'time': '11:00', 'percentile': 'p99', 'value': 305},
  {'time': '12:00', 'percentile': 'p50', 'value': 130},
  {'time': '12:00', 'percentile': 'p95', 'value': 270},
  {'time': '12:00', 'percentile': 'p99', 'value': 345},
  {'time': '13:00', 'percentile': 'p50', 'value': 110},
  {'time': '13:00', 'percentile': 'p95', 'value': 220},
  {'time': '13:00', 'percentile': 'p99', 'value': 290},
  {'time': '14:00', 'percentile': 'p50', 'value': 140},
  {'time': '14:00', 'percentile': 'p95', 'value': 280},
  {'time': '14:00', 'percentile': 'p99', 'value': 360},
  {'time': '15:00', 'percentile': 'p50', 'value': 125},
  {'time': '15:00', 'percentile': 'p95', 'value': 245},
  {'time': '15:00', 'percentile': 'p99', 'value': 315},
  {'time': '16:00', 'percentile': 'p50', 'value': 135},
  {'time': '16:00', 'percentile': 'p95', 'value': 265},
  {'time': '16:00', 'percentile': 'p99', 'value': 340},
  {'time': '17:00', 'percentile': 'p50', 'value': 118},
  {'time': '17:00', 'percentile': 'p95', 'value': 235},
  {'time': '17:00', 'percentile': 'p99', 'value': 300},
  {'time': '18:00', 'percentile': 'p50', 'value': 145},
  {'time': '18:00', 'percentile': 'p95', 'value': 290},
  {'time': '18:00', 'percentile': 'p99', 'value': 370},
  {'time': '19:00', 'percentile': 'p50', 'value': 112},
  {'time': '19:00', 'percentile': 'p95', 'value': 225},
  {'time': '19:00', 'percentile': 'p99', 'value': 295},
];

final _tokenData = [
  {'period': 'Lun', 'agent': 'Asistente', 'tokens': 4200},
  {'period': 'Lun', 'agent': 'Reviewer', 'tokens': 1800},
  {'period': 'Mar', 'agent': 'Asistente', 'tokens': 3800},
  {'period': 'Mar', 'agent': 'Reviewer', 'tokens': 2100},
  {'period': 'Mié', 'agent': 'Asistente', 'tokens': 5100},
  {'period': 'Mié', 'agent': 'Reviewer', 'tokens': 1600},
  {'period': 'Jue', 'agent': 'Asistente', 'tokens': 4600},
  {'period': 'Jue', 'agent': 'Reviewer', 'tokens': 2400},
  {'period': 'Vie', 'agent': 'Asistente', 'tokens': 3900},
  {'period': 'Vie', 'agent': 'Reviewer', 'tokens': 1900},
];

final _gateData = [
  {'gate': 'Safety', 'result': 'Pass', 'count': 187},
  {'gate': 'Safety', 'result': 'Fail', 'count': 13},
  {'gate': 'Quality', 'result': 'Pass', 'count': 162},
  {'gate': 'Quality', 'result': 'Fail', 'count': 38},
  {'gate': 'Policy', 'result': 'Pass', 'count': 194},
  {'gate': 'Policy', 'result': 'Fail', 'count': 6},
];

final _sessionData = [
  {'hour': '08:00', 'sessions': 3},
  {'hour': '09:00', 'sessions': 7},
  {'hour': '10:00', 'sessions': 12},
  {'hour': '11:00', 'sessions': 18},
  {'hour': '12:00', 'sessions': 14},
  {'hour': '13:00', 'sessions': 9},
  {'hour': '14:00', 'sessions': 16},
  {'hour': '15:00', 'sessions': 21},
  {'hour': '16:00', 'sessions': 19},
  {'hour': '17:00', 'sessions': 11},
  {'hour': '18:00', 'sessions': 6},
  {'hour': '19:00', 'sessions': 4},
];

// ── Custom axis style helpers ─────────────────────────────────────────────────

AxisGuide _hAxis() => AxisGuide(
      line: PaintStyle(strokeColor: AgentStudioTheme.border, strokeWidth: 1),
      label: LabelStyle(
        textStyle: const TextStyle(fontSize: 9, color: AgentStudioTheme.textSecondary),
        offset: const Offset(0, 6),
      ),
    );

AxisGuide _vAxis() => AxisGuide(
      label: LabelStyle(
        textStyle: const TextStyle(fontSize: 9, color: AgentStudioTheme.textSecondary),
        offset: const Offset(-6, 0),
      ),
      grid: PaintStyle(strokeColor: AgentStudioTheme.border, strokeWidth: 1),
    );

// ── Page ─────────────────────────────────────────────────────────────────────

class MetricsPage extends StatelessWidget {
  const MetricsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text(
          'Métricas',
          style: TextStyle(
            color: AgentStudioTheme.textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        const Text(
          'Monitoreo de rendimiento en tiempo real',
          style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12),
        ),
        const SizedBox(height: 20),
        // ── KPI row ──────────────────────────────────────────────────────────
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
        // ── Latency line chart ────────────────────────────────────────────────
        _chartCard(
          title: 'Latencia por agente',
          subtitle: 'p50 / p95 / p99 — ms',
          child: Chart(
            data: _latencyData,
            variables: {
              'time': Variable(
                accessor: (Map map) => map['time'] as String,
                scale: OrdinalScale(inflate: true),
              ),
              'value': Variable(
                accessor: (Map map) => map['value'] as num,
                scale: LinearScale(min: 0),
              ),
              'percentile': Variable(
                accessor: (Map map) => map['percentile'] as String,
              ),
            },
            marks: [
              LineMark(
                position: Varset('time') * Varset('value') / Varset('percentile'),
                color: ColorEncode(
                  variable: 'percentile',
                  values: [
                    AgentStudioTheme.primary,
                    AgentStudioTheme.warning,
                    AgentStudioTheme.error,
                  ],
                ),
                size: SizeEncode(value: 2),
              ),
            ],
            axes: [_hAxis(), _vAxis()],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Token usage stacked bar ───────────────────────────────────────
            Expanded(
              child: _chartCard(
                title: 'Token usage',
                subtitle: 'Tokens por agente',
                child: Chart(
                  data: _tokenData,
                  variables: {
                    'period': Variable(
                      accessor: (Map map) => map['period'] as String,
                      scale: OrdinalScale(inflate: true),
                    ),
                    'tokens': Variable(
                      accessor: (Map map) => map['tokens'] as num,
                      scale: LinearScale(min: 0),
                    ),
                    'agent': Variable(
                      accessor: (Map map) => map['agent'] as String,
                    ),
                  },
                  marks: [
                    IntervalMark(
                      position: Varset('period') * Varset('tokens') / Varset('agent'),
                      color: ColorEncode(
                        variable: 'agent',
                        values: [
                          AgentStudioTheme.primary,
                          AgentStudioTheme.info,
                        ],
                      ),
                      modifiers: [StackModifier()],
                    ),
                  ],
                  axes: [_hAxis(), _vAxis()],
                ),
              ),
            ),
            const SizedBox(width: 16),
            // ── Gate pass/fail bar ────────────────────────────────────────────
            Expanded(
              child: _chartCard(
                title: 'Gate pass/fail',
                subtitle: 'Conteo por gate',
                child: Chart(
                  data: _gateData,
                  variables: {
                    'gate': Variable(
                      accessor: (Map map) => map['gate'] as String,
                      scale: OrdinalScale(inflate: true),
                    ),
                    'count': Variable(
                      accessor: (Map map) => map['count'] as num,
                      scale: LinearScale(min: 0),
                    ),
                    'result': Variable(
                      accessor: (Map map) => map['result'] as String,
                    ),
                  },
                  marks: [
                    IntervalMark(
                      position: Varset('gate') * Varset('count') / Varset('result'),
                      color: ColorEncode(
                        variable: 'result',
                        values: [
                          AgentStudioTheme.success,
                          AgentStudioTheme.error,
                        ],
                      ),
                      modifiers: [StackModifier()],
                    ),
                  ],
                  axes: [_hAxis(), _vAxis()],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        // ── Sessions per hour bar ─────────────────────────────────────────────
        _chartCard(
          title: 'Sesiones por hora',
          subtitle: 'Conteo de sesiones',
          child: Chart(
            data: _sessionData,
            variables: {
              'hour': Variable(
                accessor: (Map map) => map['hour'] as String,
                scale: OrdinalScale(inflate: true),
              ),
              'sessions': Variable(
                accessor: (Map map) => map['sessions'] as num,
                scale: LinearScale(min: 0),
              ),
            },
            marks: [
              IntervalMark(
                color: ColorEncode(value: AgentStudioTheme.primary),
              ),
            ],
            axes: [_hAxis(), _vAxis()],
          ),
        ),
      ],
    );
  }

  Widget _kpiCard(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AgentStudioTheme.card,
          border: Border.all(color: AgentStudioTheme.border),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(icon, size: 16, color: color),
              const Spacer(),
              Text(
                value,
                style: TextStyle(
                  color: color,
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ]),
            const SizedBox(height: 4),
            Text(
              label,
              style: const TextStyle(
                color: AgentStudioTheme.textSecondary,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chartCard({
    required String title,
    required String subtitle,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        border: Border.all(color: AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: AgentStudioTheme.textPrimary,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: const TextStyle(
              color: AgentStudioTheme.textSecondary,
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(height: 160, child: child),
        ],
      ),
    );
  }
}
