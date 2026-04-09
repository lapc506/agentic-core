import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

/// Inputs tab — Character file editor.
/// Fields: Personalidad (name, bio, system prompt), Lore & Style,
/// Modelo & Template, Actions (tools), Context Providers (knowledge sources).
class InputsTab extends StatelessWidget {
  const InputsTab({super.key, required this.agent});
  final Map<String, dynamic> agent;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // --- Personalidad ---
        _buildCard(
          icon: Icons.theater_comedy,
          title: 'Personalidad',
          subtitle: 'Character file — SOUL.md',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _labeledField('Nombre del agente', agent['name'] ?? ''),
              const SizedBox(height: 12),
              _labeledField('Bio', agent['bio'] ?? 'Un asistente experto en su dominio.',
                  hint: 'Descripción corta del agente — quién es y qué hace'),
              const SizedBox(height: 12),
              _labeledField('System prompt', agent['system_prompt'] ?? '', multiline: true,
                  hint: 'Instrucciones completas del agente'),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Lore & Style ---
        _buildCard(
          icon: Icons.auto_stories,
          title: 'Lore & Style',
          subtitle: 'Personalidad profunda del agente',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _labeledField('Lore', agent['lore'] ?? '', multiline: true,
                  hint: 'Contexto de fondo, historia, valores del agente. Embebido como conocimiento base.'),
              const SizedBox(height: 12),
              _label('Estilo de respuesta'),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                children: ['Profesional', 'Casual', 'Técnico', 'Empático', 'Conciso'].map((t) =>
                  ChoiceChip(
                    label: Text(t, style: const TextStyle(fontSize: 12)),
                    selected: t == (agent['style'] ?? 'Profesional'),
                    selectedColor: AgentStudioTheme.primary,
                    backgroundColor: AgentStudioTheme.card,
                    side: const BorderSide(color: AgentStudioTheme.border),
                  ),
                ).toList(),
              ),
              const SizedBox(height: 12),
              _labeledField('Vocabulario / Tono', agent['vocabulary'] ?? '',
                  hint: 'Palabras o frases que el agente debería usar o evitar. Ej: "Usar usted, evitar jerga técnica"'),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Modelo & Template ---
        _buildCard(
          icon: Icons.psychology,
          title: 'Modelo & Template',
          child: Row(
            children: [
              Expanded(child: _labeledField('Proveedor / Modelo',
                  agent['model'] ?? 'Configurado en Settings → Modelos')),
              const SizedBox(width: 16),
              Expanded(child: _labeledField('Graph template',
                  agent['graph_template'] ?? 'react')),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Actions (tools) ---
        _buildCard(
          icon: Icons.bolt,
          title: 'Actions (Tools)',
          subtitle: 'Herramientas que el agente puede ejecutar',
          trailing: TextButton(
            onPressed: () {},
            child: const Text('+ Agregar', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 12)),
          ),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: ((agent['tools'] as List?) ?? []).map<Widget>((tool) =>
              Chip(
                label: Text(tool.toString(), style: const TextStyle(fontSize: 12, color: AgentStudioTheme.textPrimary)),
                deleteIcon: const Icon(Icons.close, size: 14, color: AgentStudioTheme.textSecondary),
                onDeleted: () {},
                backgroundColor: AgentStudioTheme.content,
                side: const BorderSide(color: AgentStudioTheme.border),
                avatar: const Icon(Icons.bolt, size: 12, color: AgentStudioTheme.warning),
              ),
            ).toList(),
          ),
        ),
        const SizedBox(height: 16),

        // --- Context Providers ---
        _buildCard(
          icon: Icons.library_books,
          title: 'Context Providers',
          subtitle: 'Fuentes de conocimiento dinámico',
          trailing: TextButton(
            onPressed: () {},
            child: const Text('+ Agregar', style: TextStyle(color: AgentStudioTheme.primary, fontSize: 12)),
          ),
          child: Column(
            children: [
              _providerRow('RAG Documents', 'Búsqueda semántica en documentos', true),
              _providerRow('Session History', 'Conversaciones pasadas del usuario', true),
              _providerRow('Time & Date', 'Contexto temporal actual', false),
              _providerRow('User Profile', 'Datos del usuario conectado', false),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // --- Memory ---
        _buildCard(
          icon: Icons.memory,
          title: 'Memory',
          subtitle: 'Auto-extract facts from conversations',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('Habilitar memoria', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13)),
                  const Spacer(),
                  Switch(value: true, onChanged: null, activeColor: AgentStudioTheme.primary),
                ],
              ),
              const SizedBox(height: 8),
              const Text('Categorías de memoria:', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: ['preferences', 'goals', 'skills', 'projects', 'context', 'feedback'].map((cat) =>
                  FilterChip(
                    label: Text(cat, style: const TextStyle(fontSize: 11)),
                    selected: ['preferences', 'goals', 'skills', 'context'].contains(cat),
                    onSelected: (_) {},
                    selectedColor: AgentStudioTheme.primary.withValues(alpha: 0.2),
                    backgroundColor: AgentStudioTheme.content,
                    side: BorderSide(color: ['preferences', 'goals', 'skills', 'context'].contains(cat) ? AgentStudioTheme.primary : AgentStudioTheme.border),
                    checkmarkColor: AgentStudioTheme.primary,
                  ),
                ).toList(),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Text('Dedup threshold: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
                  const Text('0.9', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 11, fontFamily: 'monospace')),
                  const SizedBox(width: 8),
                  const Text('Max memories: ', style: TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
                  const Text('100', style: TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 11, fontFamily: 'monospace')),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _providerRow(String name, String desc, bool enabled) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AgentStudioTheme.content,
        border: Border.all(color: enabled ? AgentStudioTheme.primary.withValues(alpha: 0.3) : AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        children: [
          Icon(enabled ? Icons.check_circle : Icons.circle_outlined, size: 16,
            color: enabled ? AgentStudioTheme.success : AgentStudioTheme.textSecondary),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: TextStyle(
                  color: enabled ? AgentStudioTheme.textPrimary : AgentStudioTheme.textSecondary, fontSize: 13, fontWeight: FontWeight.w500)),
                Text(desc, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCard({required IconData icon, required String title, required Widget child, Widget? trailing, String? subtitle}) {
    return Container(
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        border: Border.all(color: AgentStudioTheme.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AgentStudioTheme.border))),
            child: Row(
              children: [
                Icon(icon, size: 18, color: AgentStudioTheme.textPrimary),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
                      if (subtitle != null)
                        Text(subtitle, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 10)),
                    ],
                  ),
                ),
                if (trailing != null) trailing,
              ],
            ),
          ),
          Padding(padding: const EdgeInsets.all(16), child: child),
        ],
      ),
    );
  }

  Widget _label(String text) => Text(text, style: const TextStyle(color: AgentStudioTheme.textSecondary, fontSize: 11));

  Widget _labeledField(String label, String value, {bool multiline = false, String? hint}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label(label),
        const SizedBox(height: 4),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AgentStudioTheme.content,
            border: Border.all(color: AgentStudioTheme.border),
            borderRadius: BorderRadius.circular(6),
          ),
          constraints: multiline ? const BoxConstraints(minHeight: 60) : null,
          child: value.isNotEmpty
            ? Text(value, style: const TextStyle(color: AgentStudioTheme.textPrimary, fontSize: 13))
            : Text(hint ?? '', style: const TextStyle(color: AgentStudioTheme.border, fontSize: 12, fontStyle: FontStyle.italic)),
        ),
      ],
    );
  }
}
