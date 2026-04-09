import 'package:flutter/material.dart';
import '../../theme/agent_studio_theme.dart';
import '../../services/api_client.dart';

class ToolsPage extends StatefulWidget {
  const ToolsPage({super.key});

  @override
  State<ToolsPage> createState() => _ToolsPageState();
}

class _ToolsPageState extends State<ToolsPage> {
  final _api = ApiClient();
  List<Map<String, dynamic>> _tools = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadTools();
  }

  Future<void> _loadTools() async {
    try {
      final tools = await _api.listTools();
      setState(() {
        _tools = tools;
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
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Herramientas', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 18, fontWeight: FontWeight.w600)),
                    SizedBox(height: 4),
                    Text('MCP Servers & Skills', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.refresh, size: 18, color: AgentStudioTheme.textSecondary),
                tooltip: 'Recargar',
                onPressed: () {
                  setState(() {
                    _loading = true;
                    _error = null;
                  });
                  _loadTools();
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
          else if (_tools.isEmpty)
            const Expanded(
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.build_circle_outlined, size: 48, color: AgentStudioTheme.textSecondary),
                    SizedBox(height: 12),
                    Text(
                      'No hay herramientas configuradas.\nAgrega MCP servers en Settings.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 13),
                    ),
                  ],
                ),
              ),
            )
          else
            Expanded(
              child: ListView.builder(
                itemCount: _tools.length,
                itemBuilder: (_, i) {
                  final t = _tools[i];
                  final name = t['name'] as String? ?? 'unnamed';
                  final desc = t['desc'] as String? ?? t['description'] as String? ?? '';
                  final healthy = t['healthy'] as bool? ?? false;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AgentStudioTheme.card,
                      border: Border.all(color: AgentStudioTheme.border),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(children: [
                      Icon(Icons.circle, size: 8, color: healthy ? AgentStudioTheme.success : AgentStudioTheme.error),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(name, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
                          if (desc.isNotEmpty)
                            Text(desc, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                        ]),
                      ),
                      Text(healthy ? 'Healthy' : 'Degraded',
                        style: TextStyle(color: healthy ? AgentStudioTheme.success : AgentStudioTheme.error, fontSize: 12)),
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
