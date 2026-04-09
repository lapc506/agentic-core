import 'dart:async';
import 'package:flutter/material.dart';
import '../../services/api_client.dart';
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
  final _api = ApiClient();
  late TabController _tabController;
  Map<String, dynamic> _agent = {};
  List<Map<String, dynamic>> _gates = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadAgent();
  }

  Future<void> _loadAgent() async {
    try {
      final agent = await _api.getAgent(widget.agentSlug);
      final gates = await _api.getGates(widget.agentSlug);
      setState(() {
        _agent = agent;
        _gates = gates.cast<Map<String, dynamic>>();
        _loading = false;
      });
    } catch (_) {
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

  Future<void> _saveGates(List<Map<String, dynamic>> gates) async {
    try {
      await _api.updateGates(widget.agentSlug, gates);
    } catch (_) {
      // Silently fail — offline-first approach
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
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
                onPressed: () {},
                style: FilledButton.styleFrom(
                    backgroundColor: AgentStudioTheme.primary),
                child:
                    const Text('Guardar', style: TextStyle(fontSize: 12)),
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
              InputsTab(agent: _agent),
              GuardrailsTab(
                  gates: _gates, onGatesChanged: _saveGates),
              const OutputsTab(),
            ],
          ),
        ),
      ],
    );
  }
}
