import 'package:flutter/material.dart';
import 'package:graphic/graphic.dart';
import 'package:logging/logging.dart';
import '../../theme/agent_studio_theme.dart';
import '../../services/api_client.dart';

// -- Fallback empty data used when API returns nothing -----------------------

const List<Map<String, Object>> _emptyLatency = [];
const List<Map<String, Object>> _emptyTokens = [];
const List<Map<String, Object>> _emptyGates = [];
const List<Map<String, Object>> _emptySessions = [];

// -- Axis helpers -----------------------------------------------------------

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

// -- Page -------------------------------------------------------------------

class MetricsPage extends StatefulWidget {
  const MetricsPage({super.key});

  @override
  State<MetricsPage> createState() => _MetricsPageState();
}

class _MetricsPageState extends State<MetricsPage> {
  static final _log = Logger('MetricsPage');
  final _api = ApiClient();
  bool _loading = true;

  // KPI values
  String _activeSessions = '\u2014';
  String _latencyP99 = '\u2014';
  String _gatesPassRate = '\u2014';
  String _tokensPerHour = '\u2014';

  // Chart data
  List<Map<String, Object>> _latencyData = [];
  List<Map<String, Object>> _tokenData = [];
  List<Map<String, Object>> _gateData = [];
  List<Map<String, Object>> _sessionData = [];

  @override
  void initState() {
    super.initState();
    _loadMetrics();
  }

  Future<void> _loadMetrics() async {
    _log.info('Loading metrics...');
    try {
      final results = await Future.wait([
        _api.getMetrics('latency').catchError((_) => <String, dynamic>{}),
        _api.getMetrics('tokens').catchError((_) => <String, dynamic>{}),
        _api.getMetrics('gates').catchError((_) => <String, dynamic>{}),
        _api.getMetrics('sessions').catchError((_) => <String, dynamic>{}),
      ]);

      final latencyResp = results[0];
      final tokensResp = results[1];
      final gatesResp = results[2];
      final sessionsResp = results[3];

      setState(() {
        // KPIs
        if (sessionsResp.containsKey('active')) {
          _activeSessions = '${sessionsResp['active']}';
        }
        if (latencyResp.containsKey('p99')) {
          _latencyP99 = '${latencyResp['p99']}ms';
        }
        if (gatesResp.containsKey('pass_rate')) {
          _gatesPassRate = '${gatesResp['pass_rate']}%';
        }
        if (tokensResp.containsKey('per_hour')) {
          _tokensPerHour = '${tokensResp['per_hour']}';
        }

        // Chart series
        if (latencyResp.containsKey('series')) {
          _latencyData = _castList(latencyResp['series']);
        }
        if (tokensResp.containsKey('series')) {
          _tokenData = _castList(tokensResp['series']);
        }
        if (gatesResp.containsKey('series')) {
          _gateData = _castList(gatesResp['series']);
        }
        if (sessionsResp.containsKey('series')) {
          _sessionData = _castList(sessionsResp['series']);
        }

        _loading = false;
      });
      _log.fine('Metrics loaded: sessions=$_activeSessions latency=$_latencyP99 gates=$_gatesPassRate tokens=$_tokensPerHour');
    } catch (e) {
      _log.warning('Failed to load metrics: $e');
      setState(() => _loading = false);
    }
  }

  List<Map<String, Object>> _castList(dynamic raw) {
    if (raw is! List) return [];
    return raw.map<Map<String, Object>>((item) {
      if (item is Map) {
        return item.map((k, v) => MapEntry(k.toString(), v as Object));
      }
      return <String, Object>{};
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Row(
          children: [
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Metricas', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 18, fontWeight: FontWeight.w600)),
                  SizedBox(height: 4),
                  Text('Monitoreo de rendimiento en tiempo real', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                ],
              ),
            ),
            if (_loading)
              const SizedBox(
                width: 16, height: 16,
                child: CircularProgressIndicator(strokeWidth: 2, color: AgentStudioTheme.primary),
              )
            else
              IconButton(
                icon: const Icon(Icons.refresh, size: 18, color: AgentStudioTheme.textSecondary),
                tooltip: 'Recargar',
                onPressed: () {
                  setState(() => _loading = true);
                  _loadMetrics();
                },
              ),
          ],
        ),
        const SizedBox(height: 20),
        // -- KPI row --
        Row(
          children: [
            _kpiCard('Sesiones Activas', _activeSessions, Icons.people, AgentStudioTheme.primary),
            const SizedBox(width: 12),
            _kpiCard('Latencia p99', _latencyP99, Icons.speed, AgentStudioTheme.success),
            const SizedBox(width: 12),
            _kpiCard('Gates Pass Rate', _gatesPassRate, Icons.verified, AgentStudioTheme.warning),
            const SizedBox(width: 12),
            _kpiCard('Tokens/hora', _tokensPerHour, Icons.token, AgentStudioTheme.info),
          ],
        ),
        const SizedBox(height: 20),
        // -- Latency line chart --
        _chartCard(
          title: 'Latencia por agente',
          subtitle: 'p50 / p95 / p99 \u2014 ms',
          data: _latencyData,
          emptyFallback: _emptyLatency,
          builder: (data) => Chart(
            data: data,
            variables: {
              'time': Variable(accessor: (Map map) => map['time'] as String, scale: OrdinalScale(inflate: true)),
              'value': Variable(accessor: (Map map) => map['value'] as num, scale: LinearScale(min: 0)),
              'percentile': Variable(accessor: (Map map) => map['percentile'] as String),
            },
            marks: [
              LineMark(
                position: Varset('time') * Varset('value') / Varset('percentile'),
                color: ColorEncode(variable: 'percentile', values: [AgentStudioTheme.primary, AgentStudioTheme.warning, AgentStudioTheme.error]),
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
            // -- Token usage stacked bar --
            Expanded(
              child: _chartCard(
                title: 'Token usage',
                subtitle: 'Tokens por agente',
                data: _tokenData,
                emptyFallback: _emptyTokens,
                builder: (data) => Chart(
                  data: data,
                  variables: {
                    'period': Variable(accessor: (Map map) => map['period'] as String, scale: OrdinalScale(inflate: true)),
                    'tokens': Variable(accessor: (Map map) => map['tokens'] as num, scale: LinearScale(min: 0)),
                    'agent': Variable(accessor: (Map map) => map['agent'] as String),
                  },
                  marks: [
                    IntervalMark(
                      position: Varset('period') * Varset('tokens') / Varset('agent'),
                      color: ColorEncode(variable: 'agent', values: [AgentStudioTheme.primary, AgentStudioTheme.info]),
                      modifiers: [StackModifier()],
                    ),
                  ],
                  axes: [_hAxis(), _vAxis()],
                ),
              ),
            ),
            const SizedBox(width: 16),
            // -- Gate pass/fail bar --
            Expanded(
              child: _chartCard(
                title: 'Gate pass/fail',
                subtitle: 'Conteo por gate',
                data: _gateData,
                emptyFallback: _emptyGates,
                builder: (data) => Chart(
                  data: data,
                  variables: {
                    'gate': Variable(accessor: (Map map) => map['gate'] as String, scale: OrdinalScale(inflate: true)),
                    'count': Variable(accessor: (Map map) => map['count'] as num, scale: LinearScale(min: 0)),
                    'result': Variable(accessor: (Map map) => map['result'] as String),
                  },
                  marks: [
                    IntervalMark(
                      position: Varset('gate') * Varset('count') / Varset('result'),
                      color: ColorEncode(variable: 'result', values: [AgentStudioTheme.success, AgentStudioTheme.error]),
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
        // -- Sessions per hour bar --
        _chartCard(
          title: 'Sesiones por hora',
          subtitle: 'Conteo de sesiones',
          data: _sessionData,
          emptyFallback: _emptySessions,
          builder: (data) => Chart(
            data: data,
            variables: {
              'hour': Variable(accessor: (Map map) => map['hour'] as String, scale: OrdinalScale(inflate: true)),
              'sessions': Variable(accessor: (Map map) => map['sessions'] as num, scale: LinearScale(min: 0)),
            },
            marks: [
              IntervalMark(color: ColorEncode(value: AgentStudioTheme.primary)),
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
              Text(value, style: TextStyle(color: color, fontSize: 22, fontWeight: FontWeight.bold)),
            ]),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
          ],
        ),
      ),
    );
  }

  Widget _chartCard({
    required String title,
    required String subtitle,
    required List<Map<String, Object>> data,
    required List<Map<String, Object>> emptyFallback,
    required Widget Function(List<Map<String, Object>>) builder,
  }) {
    final hasData = data.isNotEmpty;
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
          Text(title, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 2),
          Text(subtitle, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
          const SizedBox(height: 12),
          SizedBox(
            height: 160,
            child: hasData
                ? builder(data)
                : const Center(
                    child: Text(
                      'Sin datos disponibles. Conecta al backend para ver metricas.',
                      style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
