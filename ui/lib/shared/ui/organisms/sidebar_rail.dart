import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

class SidebarRail extends StatelessWidget {
  const SidebarRail({
    super.key,
    required this.selectedIndex,
    required this.onSelected,
    this.isDarkMode = true,
    this.onThemeToggle,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final bool isDarkMode;
  final VoidCallback? onThemeToggle;

  static const sections = [
    (icon: Icons.chat_bubble_outline, label: 'Chat'),
    (icon: Icons.person_outline, label: 'Agent Personas'),
    (icon: Icons.rule, label: 'Reglas'),
    (icon: Icons.history, label: 'Sesiones'),
    (icon: Icons.build_outlined, label: 'Herramientas'),
    (icon: Icons.settings_outlined, label: 'Sistema'),
    (icon: Icons.bar_chart, label: 'Métricas'),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      color: AgentStudioTheme.rail,
      child: Column(
        children: [
          const SizedBox(height: 12),
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: AgentStudioTheme.primary,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Center(
              child: Text('A', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
            ),
          ),
          const SizedBox(height: 16),
          ...List.generate(sections.length, (i) {
            final section = sections[i];
            final selected = i == selectedIndex;
            return Tooltip(
              message: section.label,
              child: InkWell(
                onTap: () => onSelected(i),
                child: Container(
                  width: 40, height: 40,
                  margin: const EdgeInsets.symmetric(vertical: 2),
                  decoration: BoxDecoration(
                    color: selected ? AgentStudioTheme.card : Colors.transparent,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(section.icon, size: 20,
                    color: selected ? AgentStudioTheme.primary : AgentStudioTheme.textSecondary),
                ),
              ),
            );
          }),
          const Spacer(),
          // Theme toggle (sol/luna)
          Tooltip(
            message: isDarkMode ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro',
            child: InkWell(
              onTap: onThemeToggle,
              child: Container(
                width: 36, height: 36,
                margin: const EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  color: AgentStudioTheme.card,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  isDarkMode ? Icons.light_mode : Icons.dark_mode,
                  size: 18,
                  color: isDarkMode ? AgentStudioTheme.warning : AgentStudioTheme.primary,
                ),
              ),
            ),
          ),
          // User avatar
          const CircleAvatar(
            radius: 16,
            backgroundColor: AgentStudioTheme.primary,
            child: Text('AP', style: TextStyle(color: Colors.white, fontSize: 11)),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}
