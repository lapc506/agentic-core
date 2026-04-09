import 'package:flutter/material.dart';
import '../../theme/agent_studio_theme.dart';
import '../../services/api_client.dart';

class SessionsPage extends StatefulWidget {
  const SessionsPage({super.key});

  @override
  State<SessionsPage> createState() => _SessionsPageState();
}

class _SessionsPageState extends State<SessionsPage> {
  final _api = ApiClient();
  List<Map<String, dynamic>> _sessions = [];
  bool _loading = true;
  String? _error;

  static const _statusColors = {
    'completed': AgentStudioTheme.success,
    'active': AgentStudioTheme.primary,
    'escalated': AgentStudioTheme.warning,
  };

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions() async {
    try {
      final sessions = await _api.listSessions();
      setState(() {
        _sessions = sessions;
        _loading = false;
      });
    } catch (_) {
      setState(() {
        _loading = false;
        _error = 'No se pudo conectar al API.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text('Sesiones', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 18, fontWeight: FontWeight.w600)),
              ),
              IconButton(
                icon: const Icon(Icons.refresh, size: 18, color: AgentStudioTheme.textSecondary),
                tooltip: 'Recargar',
                onPressed: () {
                  setState(() {
                    _loading = true;
                    _error = null;
                  });
                  _loadSessions();
                },
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_loading)
            const Expanded(
              child: Center(child: CircularProgressIndicator(color: AgentStudioTheme.primary)),
            )
          else if (_error != null)
            Expanded(
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.cloud_off, size: 48, color: AgentStudioTheme.textSecondary),
                    const SizedBox(height: 12),
                    Text(_error!, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 13)),
                  ],
                ),
              ),
            )
          else if (_sessions.isEmpty)
            const Expanded(
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.chat_bubble_outline, size: 48, color: AgentStudioTheme.textSecondary),
                    SizedBox(height: 12),
                    Text('No hay sesiones aun.', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 13)),
                  ],
                ),
              ),
            )
          else
            Expanded(
              child: ListView.builder(
                itemCount: _sessions.length,
                itemBuilder: (_, i) {
                  final s = _sessions[i];
                  final id = s['id'] as String? ?? '';
                  final agent = s['agent'] as String? ?? '';
                  final status = s['status'] as String? ?? '';
                  final messages = s['messages'] ?? 0;
                  final duration = s['duration'] as String? ?? '';
                  final statusColor = _statusColors[status] ?? AgentStudioTheme.textSecondary;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AgentStudioTheme.card,
                      border: Border.all(color: AgentStudioTheme.border),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(children: [
                      Text(id, style: const TextStyle(color: AgentStudioTheme.primaryLight, fontSize: 12, fontFamily: 'monospace')),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Text(agent, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13)),
                      ),
                      Text('$messages msgs', style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                      const SizedBox(width: 12),
                      Text(duration, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                      const SizedBox(width: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(status, style: TextStyle(color: statusColor, fontSize: 10)),
                      ),
                    ]),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}
