import 'package:flutter/material.dart';
import 'package:xterm/xterm.dart';
import '../../theme/agent_studio_theme.dart';
import '../../services/api_client.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  // ignore: unused_field
  Map<String, dynamic> _config = {};

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    try {
      final config = await ApiClient().health();
      setState(() => _config = config);
    } catch (_) {}
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AgentStudioTheme.border))),
          child: const Row(children: [
            Icon(Icons.settings, size: 20, color: AgentStudioTheme.textPrimary),
            SizedBox(width: 8),
            Text('Sistema', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
          ]),
        ),
        TabBar(
          controller: _tabController,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          tabs: const [
            Tab(text: 'Conexiones'),
            Tab(text: 'Modelos'),
            Tab(text: 'Variables'),
            Tab(text: 'Debug'),
            Tab(text: 'Docker'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _ConnectionsTab(),
              _ModelsTab(),
              _VariablesTab(),
              _DebugTab(),
              _DockerTab(),
            ],
          ),
        ),
      ],
    );
  }
}

class _ConnectionsTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _statusRow('Redis', 'redis://redis:6379', true),
        _statusRow('PostgreSQL', 'postgresql://agentic@postgres:5432/agentic', true),
        _statusRow('FalkorDB', 'redis://falkordb:6380', true),
        _statusRow('MCP Bridge', 'Not configured', false),
      ],
    );
  }

  Widget _statusRow(String name, String url, bool connected) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AgentStudioTheme.card, border: Border.all(color: AgentStudioTheme.border), borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(Icons.circle, size: 8, color: connected ? AgentStudioTheme.success : AgentStudioTheme.error),
          const SizedBox(width: 12),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
            Text(url, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
          ]),
          const Spacer(),
          Text(connected ? 'Connected' : 'Offline', style: TextStyle(color: connected ? AgentStudioTheme.success : AgentStudioTheme.error, fontSize: 12)),
        ],
      ),
    );
  }
}

class _ModelsTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _modelRow('Default', 'anthropic / claude-sonnet-4-6', true),
        _modelRow('Embedding', 'google / text-embedding-004', false),
      ],
    );
  }

  Widget _modelRow(String label, String model, bool active) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AgentStudioTheme.card, border: Border.all(color: AgentStudioTheme.border), borderRadius: BorderRadius.circular(8)),
      child: Row(children: [
        Text(label, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
        const SizedBox(width: 16),
        Text(model, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14)),
        const Spacer(),
        if (active) Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(color: const Color(0xFF1a2e1a), borderRadius: BorderRadius.circular(4)),
          child: const Text('Active', style: TextStyle(color: AgentStudioTheme.success, fontSize: 10)),
        ),
      ]),
    );
  }
}

class _VariablesTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final vars = {'AGENTIC_MODE': 'standalone', 'AGENTIC_WS_PORT': '8765', 'AGENTIC_RATE_LIMIT_RPM': '60', 'AGENTIC_PII_REDACTION_ENABLED': 'true'};
    return ListView(
      padding: const EdgeInsets.all(20),
      children: vars.entries.map((e) => Container(
        margin: const EdgeInsets.only(bottom: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(color: AgentStudioTheme.card, borderRadius: BorderRadius.circular(4)),
        child: Row(children: [
          Text(e.key, style: const TextStyle(color: AgentStudioTheme.primary, fontSize: 13, fontFamily: 'monospace')),
          const SizedBox(width: 8),
          const Text('=', style: TextStyle(color: AgentStudioTheme.textSecondary)),
          const SizedBox(width: 8),
          Text(e.value, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13, fontFamily: 'monospace')),
        ]),
      )).toList(),
    );
  }
}

class _DebugTab extends StatefulWidget {
  @override
  State<_DebugTab> createState() => _DebugTabState();
}

class _DebugTabState extends State<_DebugTab> {
  late Terminal _terminal;

  @override
  void initState() {
    super.initState();
    _terminal = Terminal(maxLines: 1000);
    // Write sample log output
    _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  Runtime starting on 0.0.0.0:8765 (ws) + 0.0.0.0:50051 (grpc)\r\n');
    _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  Mode: standalone\r\n');
    _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  Redis connected: redis://redis:6379\r\n');
    _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  PostgreSQL connected: postgresql://agentic@postgres:5432/agentic\r\n');
    _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  FalkorDB connected: redis://falkordb:6380\r\n');
    _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  Loaded 3 personas from agents/\r\n');
    _terminal.write('agentic-core | \x1B[33mWARN\x1B[0m  MCP server \'exchange-rate\' health check timeout (3s)\r\n');
    _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  HTTP API started on port 8765\r\n');
    _terminal.write('\r\n\x1B[32m\$ \x1B[0m');
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0A0A14),
        border: Border.all(color: AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        children: [
          // Header with controls
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AgentStudioTheme.border)),
            ),
            child: Row(
              children: [
                const Text('Terminal', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13, fontWeight: FontWeight.w600)),
                const SizedBox(width: 8),
                // Container selector
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AgentStudioTheme.card,
                    border: Border.all(color: AgentStudioTheme.border),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: DropdownButton<String>(
                    value: 'agentic-core',
                    isDense: true,
                    underline: const SizedBox(),
                    dropdownColor: AgentStudioTheme.card,
                    style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11),
                    items: ['agentic-core', 'redis', 'postgres', 'falkordb'].map((c) =>
                      DropdownMenuItem(value: c, child: Text(c)),
                    ).toList(),
                    onChanged: (_) {},
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(color: const Color(0xFF1a2e1a), borderRadius: BorderRadius.circular(4)),
                  child: const Text('● Connected', style: TextStyle(color: AgentStudioTheme.success, fontSize: 10)),
                ),
                const Spacer(),
                // Log level filters
                ...['ALL', 'INFO', 'WARN', 'ERROR'].map((level) => Padding(
                  padding: const EdgeInsets.only(left: 4),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: level == 'ALL' ? AgentStudioTheme.primary.withValues(alpha: 0.2) : AgentStudioTheme.card,
                      border: Border.all(color: level == 'ALL' ? AgentStudioTheme.primary : AgentStudioTheme.border),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(level, style: TextStyle(
                      color: level == 'ALL' ? AgentStudioTheme.primary : AgentStudioTheme.textSecondary, fontSize: 10)),
                  ),
                )),
              ],
            ),
          ),
          // Terminal view
          Expanded(
            child: TerminalView(
              _terminal,
              theme: const TerminalTheme(
                cursor: Color(0xFF3B6FE0),
                selection: Color(0x403B6FE0),
                foreground: Color(0xFFE0E0F0),
                background: Color(0xFF0A0A14),
                black: Color(0xFF000000),
                red: Color(0xFFEF5350),
                green: Color(0xFF4CAF50),
                yellow: Color(0xFFFF9800),
                blue: Color(0xFF3B6FE0),
                magenta: Color(0xFF9C27B0),
                cyan: Color(0xFF00BCD4),
                white: Color(0xFFE0E0F0),
                brightBlack: Color(0xFF666680),
                brightRed: Color(0xFFEF5350),
                brightGreen: Color(0xFF4CAF50),
                brightYellow: Color(0xFFFF9800),
                brightBlue: Color(0xFF6B9FFF),
                brightMagenta: Color(0xFFCE93D8),
                brightCyan: Color(0xFF4DD0E1),
                brightWhite: Color(0xFFFFFFFF),
                searchHitBackground: Color(0xFFFF9800),
                searchHitBackgroundCurrent: Color(0xFFEF5350),
                searchHitForeground: Color(0xFF000000),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DockerTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final containers = [
      {'name': 'agentic-core', 'status': 'running', 'port': '8765'},
      {'name': 'redis', 'status': 'running', 'port': '6379'},
      {'name': 'postgres', 'status': 'running', 'port': '5432'},
      {'name': 'falkordb', 'status': 'running', 'port': '6380'},
    ];
    return ListView(
      padding: const EdgeInsets.all(20),
      children: containers.map((c) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: AgentStudioTheme.card, border: Border.all(color: AgentStudioTheme.border), borderRadius: BorderRadius.circular(8)),
        child: Row(children: [
          const Icon(Icons.inventory_2, size: 18, color: AgentStudioTheme.textSecondary),
          const SizedBox(width: 12),
          Text(c['name']!, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
          const Spacer(),
          Text(':${c['port']}', style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12, fontFamily: 'monospace')),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(color: const Color(0xFF1a2e1a), borderRadius: BorderRadius.circular(4)),
            child: Text('● ${c['status']}', style: const TextStyle(color: AgentStudioTheme.success, fontSize: 10)),
          ),
        ]),
      )).toList(),
    );
  }
}
