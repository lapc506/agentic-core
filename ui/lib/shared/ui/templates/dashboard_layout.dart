import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';
import '../organisms/sidebar_rail.dart';
import '../organisms/sidebar_panel.dart';

class DashboardLayout extends StatefulWidget {
  const DashboardLayout({
    super.key,
    required this.child,
    required this.selectedSection,
    required this.onSectionChanged,
    this.panelContent,
  });
  final Widget child;
  final int selectedSection;
  final ValueChanged<int> onSectionChanged;
  final Widget? panelContent;

  @override
  State<DashboardLayout> createState() => _DashboardLayoutState();
}

class _DashboardLayoutState extends State<DashboardLayout> {
  bool _panelExpanded = true;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final showPanel = width > 768 && _panelExpanded && widget.panelContent != null;
    return Scaffold(
      body: Row(
        children: [
          SidebarRail(
            selectedIndex: widget.selectedSection,
            onSelected: (i) {
              if (i == widget.selectedSection) {
                setState(() => _panelExpanded = !_panelExpanded);
              } else {
                widget.onSectionChanged(i);
                setState(() => _panelExpanded = true);
              }
            },
          ),
          if (showPanel)
            Container(
              decoration: const BoxDecoration(
                border: Border(right: BorderSide(color: AgentStudioTheme.border)),
              ),
              child: SidebarPanel(selectedSection: widget.selectedSection, child: widget.panelContent!),
            ),
          Expanded(child: widget.child),
        ],
      ),
    );
  }
}
