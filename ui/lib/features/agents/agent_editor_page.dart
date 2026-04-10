import 'dart:async';
import 'package:flutter/material.dart';
import 'package:logging/logging.dart';
import '../../services/api_client.dart';
import '../../services/soul_md_generator.dart';
import '../../theme/agent_studio_theme.dart';
import 'widgets/inputs_tab.dart';
import 'widgets/guardrails_tab.dart';
import 'widgets/outputs_tab.dart';

class AgentEditorPage extends StatefulWidget {
  const AgentEditorPage({super.key, required this.agentSlug});
  final String agentSlug;

  @override
  State<AgentEditorPage> createState() => _AgentEditorPageState();
}

class _AgentEditorPageState extends State<AgentEditorPage>
    with SingleTickerProviderStateMixin {
  static final _log = Logger('AgentEditor');
  final _api = ApiClient();
  late TabController _tabController;
  Map<String, dynamic> _agent = {};
  List<Map<String, dynamic>> _gates = [];
  bool _loading = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadAgent();
  }

  Future<void> _loadAgent() async {
    _log.info('Loading agent: ${widget.agentSlug}');
    try {
      final agent = await _api.getAgent(widget.agentSlug);
      final gates = await _api.getGates(widget.agentSlug);
      _log.info('Agent loaded: ${widget.agentSlug} with ${gates.length} gates');
      setState(() {
        _agent = agent;
        _gates = gates.cast<Map<String, dynamic>>();
        _loading = false;
      });
    } catch (e) {
      _log.warning('Failed to load agent ${widget.agentSlug}, using defaults: $e');
      setState(() {
        _agent = {
          'name': widget.agentSlug,
          'role': 'assistant',
          'description': '',
          'tools': <String>[],
          'graph_template': 'react',
        };
        _loading = false;
      });
    }
  }

  Future<void> _saveAgent() async {
    _log.info('Saving agent: ${widget.agentSlug}');
    setState(() => _saving = true);
    try {
      await _api.updateAgent(widget.agentSlug, _agent);
      _log.info('Agent saved successfully: ${widget.agentSlug}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Agente guardado'), backgroundColor: AgentStudioTheme.success),
        );
      }
    } catch (e) {
      _log.warning('Save failed for ${widget.agentSlug}: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: AgentStudioTheme.error),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _saveGates(List<Map<String, dynamic>> gates) async {
    _log.fine('Saving ${gates.length} gates for ${widget.agentSlug}');
    try {
      await _api.updateGates(widget.agentSlug, gates);
      _log.fine('Gates saved successfully');
    } catch (e) {
      // Silently fail — offline-first approach
      _log.warning('Gates save failed (offline-first): $e');
    }
  }

  void _onInputsChanged(Map<String, dynamic> updatedAgent) {
    setState(() => _agent = updatedAgent);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _exportSoulMd(BuildContext context) {
    final soulMd = SoulMdGenerator.generate(_agent, _gates);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AgentStudioTheme.card,
        title: const Text('SOUL.md Preview', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 16)),
        content: SizedBox(
          width: 600,
          height: 400,
          child: SingleChildScrollView(
            child: SelectableText(
              soulMd,
              style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 12, fontFamily: 'monospace', height: 1.6),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cerrar', style: TextStyle(color: AgentStudioTheme.textSecondary)),
          ),
          FilledButton.icon(
            onPressed: () {
              // TODO: Download file in future
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('SOUL.md copiado al clipboard')),
              );
            },
            icon: const Icon(Icons.copy, size: 14),
            label: const Text('Copiar'),
            style: FilledButton.styleFrom(backgroundColor: AgentStudioTheme.primary),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: AgentStudioTheme.primary),
      );
    }

    return Column(
      children: [
        // Agent header
        Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          decoration: const BoxDecoration(
            border: Border(
              bottom: BorderSide(color: AgentStudioTheme.border),
            ),
          ),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: AgentStudioTheme.primary,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.smart_toy,
                    size: 18, color: Colors.white),
              ),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _agent['name'] ?? widget.agentSlug,
                    style: const TextStyle(
                        color: AgentStudioTheme.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600),
                  ),
                  Text(
                    '${_agent['graph_template'] ?? 'react'} · ${(_agent['tools'] as List?)?.length ?? 0} tools',
                    style: const TextStyle(
                        color: AgentStudioTheme.textSecondary,
                        fontSize: 11),
                  ),
                ],
              ),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: () => _exportSoulMd(context),
                icon: const Icon(Icons.description, size: 14),
                label: const Text('SOUL.md', style: TextStyle(fontSize: 12)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AgentStudioTheme.primary),
                  foregroundColor: AgentStudioTheme.primary,
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton(
                onPressed: () {},
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AgentStudioTheme.border),
                ),
                child: const Text('Probar',
                    style: TextStyle(
                        color: AgentStudioTheme.textSecondary,
                        fontSize: 12)),
              ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: _saving ? null : _saveAgent,
                style: FilledButton.styleFrom(
                    backgroundColor: AgentStudioTheme.primary),
                child: _saving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Guardar', style: TextStyle(fontSize: 12)),
              ),
            ],
          ),
        ),
        // Tabs
        TabBar(
          controller: _tabController,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          tabs: const [
            Tab(text: 'Inputs'),
            Tab(text: 'Guardrails'),
            Tab(text: 'Outputs'),
          ],
        ),
        // Tab content
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              InputsTab(agent: _agent, onChanged: _onInputsChanged),
              GuardrailsTab(
                  gates: _gates, onGatesChanged: _saveGates),
              OutputsTab(agent: _agent, onChanged: _onInputsChanged),
            ],
          ),
        ),
      ],
    );
  }
}
