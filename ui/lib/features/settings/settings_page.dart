import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
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

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
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

// ---------------------------------------------------------------------------
// Connections Tab -- pings /api/health for real status
// ---------------------------------------------------------------------------

class _ConnectionsTab extends StatefulWidget {
  @override
  State<_ConnectionsTab> createState() => _ConnectionsTabState();
}

class _ConnectionsTabState extends State<_ConnectionsTab> {
  final _api = ApiClient();
  bool _loading = true;

  // Default services with unknown status
  final List<Map<String, dynamic>> _services = [
    {'name': 'Redis', 'url': 'redis://redis:6379', 'connected': false},
    {'name': 'PostgreSQL', 'url': 'postgresql://agentic@postgres:5432/agentic', 'connected': false},
    {'name': 'FalkorDB', 'url': 'redis://falkordb:6380', 'connected': false},
    {'name': 'MCP Bridge', 'url': 'Not configured', 'connected': false},
  ];

  Map<String, dynamic> _rateLimits = {};

  @override
  void initState() {
    super.initState();
    _checkConnections();
  }

  Future<void> _checkConnections() async {
    try {
      final health = await _api.health();

      setState(() {
        // Update service status from health response
        final services = health['services'];
        if (services is Map) {
          for (final svc in _services) {
            final name = (svc['name'] as String).toLowerCase();
            if (services.containsKey(name)) {
              final svcData = services[name];
              if (svcData is Map) {
                svc['connected'] = svcData['status'] == 'ok' || svcData['connected'] == true;
                if (svcData.containsKey('url')) {
                  svc['url'] = svcData['url'];
                }
              } else if (svcData is bool) {
                svc['connected'] = svcData;
              }
            }
          }
        }

        // Rate limits from health
        if (health.containsKey('rate_limits')) {
          _rateLimits = health['rate_limits'] as Map<String, dynamic>? ?? {};
        }

        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        if (_loading) const LinearProgressIndicator(color: AgentStudioTheme.primary),
        ..._services.map((svc) => _statusRow(
          svc['name'] as String,
          svc['url'] as String,
          svc['connected'] as bool,
        )),
        const SizedBox(height: 24),
        const Text('RATE LIMITS', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 1)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AgentStudioTheme.card,
            border: Border.all(color: AgentStudioTheme.border),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            children: [
              _rateLimitRow('Queries/minuto', _rateLimits['rpm']?.toString() ?? '10'),
              const SizedBox(height: 8),
              _rateLimitRow('Queries/hora', _rateLimits['rph']?.toString() ?? '120'),
              const SizedBox(height: 8),
              _rateLimitRow('Queries/dia', _rateLimits['rpd']?.toString() ?? '1000'),
              const Divider(height: 24, color: AgentStudioTheme.border),
              Row(children: [
                const Text('Circuit breaker', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
                const Spacer(),
                Text(
                  _rateLimits['circuit_breaker'] as String? ?? '3 consecutive / 5 in window \u2192 60s cooldown',
                  style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 11),
                ),
              ]),
            ],
          ),
        ),
        const SizedBox(height: 24),
        const Text('COMPLIANCE', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 1)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AgentStudioTheme.card,
            border: Border.all(color: AgentStudioTheme.border),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            children: [
              Row(children: [
                const Icon(Icons.check_circle, size: 14, color: AgentStudioTheme.success),
                const SizedBox(width: 8),
                const Text('AI Disclosure', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13)),
                const Spacer(),
                Switch(value: true, onChanged: null, activeColor: AgentStudioTheme.success),
              ]),
              Row(children: [
                const Icon(Icons.check_circle, size: 14, color: AgentStudioTheme.success),
                const SizedBox(width: 8),
                const Text('Destructive Confirmation', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13)),
                const Spacer(),
                Switch(value: true, onChanged: null, activeColor: AgentStudioTheme.success),
              ]),
              Row(children: [
                const Icon(Icons.check_circle, size: 14, color: AgentStudioTheme.success),
                const SizedBox(width: 8),
                const Text('High-Risk Domain Refusal', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13)),
                const Spacer(),
                Switch(value: true, onChanged: null, activeColor: AgentStudioTheme.success),
              ]),
            ],
          ),
        ),
      ],
    );
  }

  Widget _rateLimitRow(String label, String value) {
    return Row(children: [
      Text(label, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
      const Spacer(),
      Text(value, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.bold)),
    ]);
  }

  Widget _statusRow(String name, String url, bool connected) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        border: Border.all(color: AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(8),
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
          if (_loading)
            const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: AgentStudioTheme.textSecondary))
          else
            Text(connected ? 'Connected' : 'Offline',
              style: TextStyle(color: connected ? AgentStudioTheme.success : AgentStudioTheme.error, fontSize: 12)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Models Tab -- unchanged
// ---------------------------------------------------------------------------

class _ModelsTab extends StatefulWidget {
  @override
  State<_ModelsTab> createState() => _ModelsTabState();
}

class _ModelsTabState extends State<_ModelsTab> {
  final List<Map<String, String>> _providers = [
    {'name': 'Anthropic', 'type': 'anthropic', 'model': 'claude-sonnet-4-6', 'baseUrl': 'https://api.anthropic.com', 'status': 'active'},
  ];

  void _addProvider(Map<String, String> provider) {
    setState(() => _providers.add(provider));
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Row(
          children: [
            const Text('Inference Providers', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
            const Spacer(),
            FilledButton.icon(
              onPressed: () => _showAddProviderDialog(context),
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Agregar provider', style: TextStyle(fontSize: 12)),
              style: FilledButton.styleFrom(backgroundColor: AgentStudioTheme.primary),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text('Configura providers de inferencia LLM. Todos los compatibles con OpenAI API funcionan.',
          style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
        const SizedBox(height: 16),
        const Text('PRESETS', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 1)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8, runSpacing: 8,
          children: [
            _presetChip('Ollama (local)', 'http://localhost:11434/v1', 'llama3.1'),
            _presetChip('LMStudio', 'http://localhost:1234/v1', 'loaded-model'),
            _presetChip('Fireworks.ai', 'https://api.fireworks.ai/inference/v1', 'accounts/fireworks/models/kimi-k2p5'),
            _presetChip('NVIDIA NIM', 'https://integrate.api.nvidia.com/v1', 'meta/llama-3.1-70b-instruct'),
            _presetChip('OpenRouter', 'https://openrouter.ai/api/v1', 'anthropic/claude-sonnet-4'),
            _presetChip('Together AI', 'https://api.together.xyz/v1', 'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo'),
          ],
        ),
        const SizedBox(height: 24),
        const Text('CONFIGURADOS', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 1)),
        const SizedBox(height: 8),
        ..._providers.map((p) => _providerCard(p)),
      ],
    );
  }

  Widget _presetChip(String name, String baseUrl, String model) {
    return ActionChip(
      label: Text(name, style: const TextStyle(fontSize: 11, color: AgentStudioTheme.textPrimary)),
      avatar: const Icon(Icons.add_circle_outline, size: 14, color: AgentStudioTheme.primary),
      backgroundColor: AgentStudioTheme.card,
      side: const BorderSide(color: AgentStudioTheme.border),
      onPressed: () {
        _addProvider({'name': name, 'type': 'openai', 'model': model, 'baseUrl': baseUrl, 'status': 'configured'});
      },
    );
  }

  Widget _providerCard(Map<String, String> p) {
    final isActive = p['status'] == 'active';
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        border: Border.all(color: isActive ? AgentStudioTheme.primary : AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(isActive ? Icons.check_circle : Icons.circle_outlined, size: 16,
              color: isActive ? AgentStudioTheme.success : AgentStudioTheme.textSecondary),
            const SizedBox(width: 8),
            Text(p['name']!, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
              decoration: BoxDecoration(color: AgentStudioTheme.content, borderRadius: BorderRadius.circular(4)),
              child: Text(p['type']!, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 10)),
            ),
            const Spacer(),
            if (isActive) Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: const Color(0xFF1a2e1a), borderRadius: BorderRadius.circular(4)),
              child: const Text('Default', style: TextStyle(color: AgentStudioTheme.success, fontSize: 10)),
            ),
            if (!isActive) TextButton(
              onPressed: () {},
              child: const Text('Set Default', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 11)),
            ),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            const Text('Model: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
            Text(p['model']!, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 12, fontFamily: 'monospace')),
          ]),
          Row(children: [
            const Text('Base URL: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
            Text(p['baseUrl']!, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12, fontFamily: 'monospace')),
          ]),
        ],
      ),
    );
  }

  void _showAddProviderDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final urlCtrl = TextEditingController();
    final modelCtrl = TextEditingController();
    final keyCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AgentStudioTheme.card,
        title: const Text('Agregar Inference Provider', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 16)),
        content: SizedBox(
          width: 400,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: nameCtrl, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
                decoration: const InputDecoration(labelText: 'Nombre', labelStyle: TextStyle(color: AgentStudioTheme.textSecondary))),
              const SizedBox(height: 8),
              TextField(controller: urlCtrl, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
                decoration: const InputDecoration(labelText: 'Base URL (OpenAI compatible)', hintText: 'http://localhost:11434/v1',
                  labelStyle: TextStyle(color: AgentStudioTheme.textSecondary), hintStyle: TextStyle(color: AgentStudioTheme.border))),
              const SizedBox(height: 8),
              TextField(controller: modelCtrl, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
                decoration: const InputDecoration(labelText: 'Modelo', hintText: 'llama3.1',
                  labelStyle: TextStyle(color: AgentStudioTheme.textSecondary), hintStyle: TextStyle(color: AgentStudioTheme.border))),
              const SizedBox(height: 8),
              TextField(controller: keyCtrl, obscureText: true, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
                decoration: const InputDecoration(labelText: 'API Key (opcional para local)', labelStyle: TextStyle(color: AgentStudioTheme.textSecondary))),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancelar', style: TextStyle(color: AgentStudioTheme.textSecondary))),
          FilledButton(
            onPressed: () {
              if (nameCtrl.text.isNotEmpty && urlCtrl.text.isNotEmpty) {
                _addProvider({'name': nameCtrl.text, 'type': 'openai', 'model': modelCtrl.text, 'baseUrl': urlCtrl.text, 'status': 'configured'});
                Navigator.pop(ctx);
              }
            },
            style: FilledButton.styleFrom(backgroundColor: AgentStudioTheme.primary),
            child: const Text('Agregar'),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Variables Tab -- loads from /api/config
// ---------------------------------------------------------------------------

class _VariablesTab extends StatefulWidget {
  @override
  State<_VariablesTab> createState() => _VariablesTabState();
}

class _VariablesTabState extends State<_VariablesTab> {
  final _api = ApiClient();
  Map<String, String> _vars = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    try {
      final config = await _api.getConfig();
      final Map<String, String> parsed = {};
      for (final entry in config.entries) {
        parsed[entry.key] = entry.value?.toString() ?? '';
      }
      setState(() {
        _vars = parsed;
        _loading = false;
      });
    } catch (_) {
      // Fallback to defaults when API unavailable
      setState(() {
        _vars = {
          'AGENTIC_MODE': 'standalone',
          'AGENTIC_WS_PORT': '8765',
          'AGENTIC_RATE_LIMIT_RPM': '60',
          'AGENTIC_PII_REDACTION_ENABLED': 'true',
        };
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: AgentStudioTheme.primary));
    }
    if (_vars.isEmpty) {
      return const Center(
        child: Text('No hay variables de configuracion.', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 13)),
      );
    }
    return ListView(
      padding: const EdgeInsets.all(20),
      children: _vars.entries.map((e) => Container(
        margin: const EdgeInsets.only(bottom: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(color: AgentStudioTheme.card, borderRadius: BorderRadius.circular(4)),
        child: Row(children: [
          Text(e.key, style: const TextStyle(color: AgentStudioTheme.primary, fontSize: 13, fontFamily: 'monospace')),
          const SizedBox(width: 8),
          const Text('=', style: TextStyle(color: AgentStudioTheme.textSecondary)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(e.value, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13, fontFamily: 'monospace')),
          ),
        ]),
      )).toList(),
    );
  }
}

// ---------------------------------------------------------------------------
// Debug Tab -- polls /api/health and accepts keyboard input
// ---------------------------------------------------------------------------

class _DebugTab extends StatefulWidget {
  @override
  State<_DebugTab> createState() => _DebugTabState();
}

class _DebugTabState extends State<_DebugTab> {
  late Terminal _terminal;
  final _api = ApiClient();
  Timer? _pollTimer;
  String _inputBuffer = '';

  @override
  void initState() {
    super.initState();
    _terminal = Terminal(maxLines: 1000);
    _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  Debug terminal ready. Polling /api/health every 5s...\r\n');
    _terminal.write('\r\n');

    // Set up keyboard input handler
    _terminal.onOutput = (data) {
      for (final char in data.codeUnits) {
        if (char == 13) {
          // Enter key
          _terminal.write('\r\n');
          _handleCommand(_inputBuffer.trim());
          _inputBuffer = '';
          _writePrompt();
        } else if (char == 127 || char == 8) {
          // Backspace
          if (_inputBuffer.isNotEmpty) {
            _inputBuffer = _inputBuffer.substring(0, _inputBuffer.length - 1);
            _terminal.write('\b \b');
          }
        } else {
          _inputBuffer += String.fromCharCode(char);
          _terminal.write(String.fromCharCode(char));
        }
      }
    };

    _pollHealth();
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) => _pollHealth());
    _writePrompt();
  }

  void _writePrompt() {
    _terminal.write('\x1B[32m\$ \x1B[0m');
  }

  void _handleCommand(String cmd) {
    if (cmd.isEmpty) return;
    if (cmd == 'health' || cmd == 'status') {
      _terminal.write('agentic-core | \x1B[34mINFO\x1B[0m  Fetching health...\r\n');
      _pollHealth();
    } else if (cmd == 'clear') {
      _terminal.write('\x1B[2J\x1B[H');
    } else if (cmd == 'help') {
      _terminal.write('Available commands: health, status, clear, help\r\n');
    } else {
      _terminal.write('Unknown command: $cmd (type "help" for available commands)\r\n');
    }
  }

  Future<void> _pollHealth() async {
    try {
      final health = await _api.health();
      final status = health['status'] ?? 'unknown';
      final services = health['services'];
      final ts = DateTime.now().toIso8601String().substring(11, 19);
      _terminal.write('[$ts] \x1B[34mHEALTH\x1B[0m status=$status');
      if (services is Map) {
        for (final entry in services.entries) {
          final svcStatus = entry.value is Map ? (entry.value as Map)['status'] ?? '?' : entry.value;
          _terminal.write(' ${entry.key}=$svcStatus');
        }
      }
      _terminal.write('\r\n');
    } catch (e) {
      final ts = DateTime.now().toIso8601String().substring(11, 19);
      _terminal.write('[$ts] \x1B[31mERROR\x1B[0m  Health check failed: $e\r\n');
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
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
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AgentStudioTheme.border))),
            child: Row(
              children: [
                const Text('Terminal', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13, fontWeight: FontWeight.w600)),
                const SizedBox(width: 8),
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
                  child: const Text('\u25CF Polling', style: TextStyle(color: AgentStudioTheme.success, fontSize: 10)),
                ),
                const Spacer(),
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
              textStyle: TerminalStyle(
                fontFamily: GoogleFonts.ubuntuMono().fontFamily!,
                fontSize: 13,
              ),
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

// ---------------------------------------------------------------------------
// Docker Tab -- loads from /api/docker/status or shows CLI hint
// ---------------------------------------------------------------------------

class _DockerTab extends StatefulWidget {
  @override
  State<_DockerTab> createState() => _DockerTabState();
}

class _DockerTabState extends State<_DockerTab> {
  final _api = ApiClient();
  List<Map<String, dynamic>> _containers = [];
  bool _loading = true;
  bool _apiAvailable = false;

  @override
  void initState() {
    super.initState();
    _loadDockerStatus();
  }

  Future<void> _loadDockerStatus() async {
    try {
      final resp = await _api.getDockerStatus();
      final containers = resp['containers'];
      if (containers is List) {
        setState(() {
          _containers = containers.cast<Map<String, dynamic>>();
          _apiAvailable = true;
          _loading = false;
        });
        return;
      }
    } catch (_) {}

    // Fallback: API not available
    setState(() {
      _loading = false;
      _apiAvailable = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: AgentStudioTheme.primary));
    }

    if (!_apiAvailable) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.info_outline, size: 32, color: AgentStudioTheme.textSecondary),
            const SizedBox(height: 12),
            const Text(
              'Docker status no disponible desde el navegador.',
              style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AgentStudioTheme.card,
                border: Border.all(color: AgentStudioTheme.border),
                borderRadius: BorderRadius.circular(6),
              ),
              child: const SelectableText(
                'podman ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"',
                style: TextStyle(color: AgentStudioTheme.primary, fontSize: 13, fontFamily: 'monospace'),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Ejecuta el comando anterior en tu terminal para ver el estado de los contenedores.',
              style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12),
            ),
          ],
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(20),
      children: _containers.map((c) {
        final name = c['name'] as String? ?? 'unknown';
        final status = c['status'] as String? ?? 'unknown';
        final port = c['port'] as String? ?? '';
        final isRunning = status == 'running';
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AgentStudioTheme.card,
            border: Border.all(color: AgentStudioTheme.border),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(children: [
            const Icon(Icons.inventory_2, size: 18, color: AgentStudioTheme.textSecondary),
            const SizedBox(width: 12),
            Text(name, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
            const Spacer(),
            if (port.isNotEmpty)
              Text(':$port', style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12, fontFamily: 'monospace')),
            const SizedBox(width: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: isRunning ? const Color(0xFF1a2e1a) : const Color(0xFF2e1a1a),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                '\u25CF $status',
                style: TextStyle(color: isRunning ? AgentStudioTheme.success : AgentStudioTheme.error, fontSize: 10),
              ),
            ),
          ]),
        );
      }).toList(),
    );
  }
}
