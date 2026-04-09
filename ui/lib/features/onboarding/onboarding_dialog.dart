import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../../services/api_client.dart';
import '../../theme/agent_studio_theme.dart';

String _url(String path) => '${ApiClient.baseUrl}$path';

class OnboardingDialog extends StatefulWidget {
  const OnboardingDialog({super.key, required this.onComplete});
  final VoidCallback onComplete;

  @override
  State<OnboardingDialog> createState() => _OnboardingDialogState();
}

class _OnboardingDialogState extends State<OnboardingDialog> {
  int _step = 0; // 0 = welcome, 1 = provider, 2 = agent, 3 = done
  String _selectedProvider = 'openrouter_free';
  final _apiKeyCtrl = TextEditingController();
  final _agentNameCtrl = TextEditingController(text: 'Asistente Demo');
  final _agentDescCtrl = TextEditingController(text: 'Agente de demostración');
  bool _saving = false;

  static const _presets = {
    'openrouter_free': {
      'name': 'OpenRouter (free tier)',
      'baseUrl': 'https://openrouter.ai/api/v1',
      'model': 'meta-llama/llama-3.2-3b-instruct:free',
      'needsKey': true,
      'hint': 'Gratis. Registrate en openrouter.ai para obtener tu API key.',
    },
    'ollama': {
      'name': 'Ollama (local)',
      'baseUrl': 'http://host.docker.internal:11434/v1',
      'model': 'llama3.1',
      'needsKey': false,
      'hint': 'Requiere Ollama corriendo en tu máquina: ollama run llama3.1',
    },
    'lmstudio': {
      'name': 'LM Studio (local)',
      'baseUrl': 'http://host.docker.internal:1234/v1',
      'model': 'loaded-model',
      'needsKey': false,
      'hint': 'Requiere LM Studio corriendo con un modelo cargado.',
    },
    'fireworks': {
      'name': 'Fireworks.ai',
      'baseUrl': 'https://api.fireworks.ai/inference/v1',
      'model': 'accounts/fireworks/models/kimi-k2p5',
      'needsKey': true,
      'hint': 'Alto rendimiento. API key desde fireworks.ai',
    },
    'custom': {
      'name': 'Custom (OpenAI compatible)',
      'baseUrl': '',
      'model': '',
      'needsKey': true,
      'hint': 'Cualquier endpoint compatible con la API de OpenAI.',
    },
  };

  Future<void> _saveAndFinish() async {
    setState(() => _saving = true);
    final preset = _presets[_selectedProvider]!;

    // Save config
    try {
      await http.post(
        Uri.parse(_url('/api/studio/config')),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'onboarded': true,
          'providers': [
            {
              'name': preset['name'],
              'type': 'openai',
              'model': preset['model'],
              'baseUrl': preset['baseUrl'],
              'apiKey': _apiKeyCtrl.text,
              'status': 'active',
            }
          ],
          'default_agent': {
            'name': _agentNameCtrl.text,
            'role': 'assistant',
            'description': _agentDescCtrl.text,
            'graph_template': 'react',
            'tools': [],
            'system_prompt': 'Eres un asistente útil y profesional. Responde en el idioma del usuario.',
          },
        }),
      );

      // Create the default agent
      await http.post(
        Uri.parse(_url('/api/agents')),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': _agentNameCtrl.text,
          'role': 'assistant',
          'description': _agentDescCtrl.text,
          'graph_template': 'react',
        }),
      );
    } catch (_) {
      // If backend is unavailable, still dismiss
    }

    widget.onComplete();
  }

  Future<void> _skipWithDefaults() async {
    setState(() => _saving = true);
    try {
      // Create default agent from defaults
      await http.post(
        Uri.parse(_url('/api/agents')),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': 'Asistente Demo',
          'role': 'assistant',
          'description': 'Agente de demostración',
          'graph_template': 'react',
        }),
      );
    } catch (_) {}
    widget.onComplete();
  }

  @override
  void dispose() {
    _apiKeyCtrl.dispose();
    _agentNameCtrl.dispose();
    _agentDescCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AgentStudioTheme.card,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: SizedBox(
        width: 520,
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: _saving
              ? const SizedBox(
                  height: 200,
                  child: Center(child: CircularProgressIndicator(color: AgentStudioTheme.primary)),
                )
              : switch (_step) {
                  0 => _welcomeStep(),
                  1 => _providerStep(),
                  2 => _agentStep(),
                  _ => const SizedBox.shrink(),
                },
        ),
      ),
    );
  }

  Widget _welcomeStep() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64, height: 64,
          decoration: BoxDecoration(
            color: AgentStudioTheme.primary,
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Center(
            child: Text('A', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 28)),
          ),
        ),
        const SizedBox(height: 16),
        const Text('Agent Studio', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 22, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        const Text(
          'Configura tu primer agente en 2 pasos: elige un inference provider y define la personalidad.',
          textAlign: TextAlign.center,
          style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 13),
        ),
        const SizedBox(height: 24),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            OutlinedButton(
              onPressed: _skipWithDefaults,
              style: OutlinedButton.styleFrom(side: const BorderSide(color: AgentStudioTheme.border)),
              child: const Text('Usar defaults', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 13)),
            ),
            const SizedBox(width: 12),
            FilledButton(
              onPressed: () => setState(() => _step = 1),
              style: FilledButton.styleFrom(backgroundColor: AgentStudioTheme.primary),
              child: const Text('Configurar', style: TextStyle(fontSize: 13)),
            ),
          ],
        ),
      ],
    );
  }

  Widget _providerStep() {
    final preset = _presets[_selectedProvider]!;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Paso 1: Inference Provider', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        const Text('Elige cómo se conecta el agente al LLM.', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _presets.entries.map((e) => ChoiceChip(
            label: Text(e.value['name'] as String, style: const TextStyle(fontSize: 11)),
            selected: _selectedProvider == e.key,
            selectedColor: AgentStudioTheme.primary.withValues(alpha: 0.2),
            backgroundColor: AgentStudioTheme.content,
            side: BorderSide(color: _selectedProvider == e.key ? AgentStudioTheme.primary : AgentStudioTheme.border),
            onSelected: (_) => setState(() => _selectedProvider = e.key),
          )).toList(),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AgentStudioTheme.content,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: AgentStudioTheme.border),
          ),
          child: Text(preset['hint'] as String, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
        ),
        if (preset['needsKey'] == true) ...[
          const SizedBox(height: 12),
          TextField(
            controller: _apiKeyCtrl,
            obscureText: true,
            style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
            decoration: const InputDecoration(
              labelText: 'API Key',
              labelStyle: TextStyle(color: AgentStudioTheme.textSecondary),
              hintText: 'sk-or-...',
              hintStyle: TextStyle(color: AgentStudioTheme.border),
            ),
          ),
        ],
        const SizedBox(height: 20),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              onPressed: () => setState(() => _step = 0),
              child: const Text('Atrás', style: TextStyle(color: AgentStudioTheme.textSecondary)),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: () => setState(() => _step = 2),
              style: FilledButton.styleFrom(backgroundColor: AgentStudioTheme.primary),
              child: const Text('Siguiente'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _agentStep() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Paso 2: Agent Persona', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        const Text('Define tu primer agente. Podés editarlo después.', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 12)),
        const SizedBox(height: 16),
        TextField(
          controller: _agentNameCtrl,
          style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
          decoration: const InputDecoration(
            labelText: 'Nombre del agente',
            labelStyle: TextStyle(color: AgentStudioTheme.textSecondary),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _agentDescCtrl,
          maxLines: 2,
          style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13),
          decoration: const InputDecoration(
            labelText: 'Descripción',
            labelStyle: TextStyle(color: AgentStudioTheme.textSecondary),
          ),
        ),
        const SizedBox(height: 20),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              onPressed: () => setState(() => _step = 1),
              child: const Text('Atrás', style: TextStyle(color: AgentStudioTheme.textSecondary)),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: _saveAndFinish,
              style: FilledButton.styleFrom(backgroundColor: AgentStudioTheme.primary),
              child: const Text('Crear agente y empezar'),
            ),
          ],
        ),
      ],
    );
  }
}
