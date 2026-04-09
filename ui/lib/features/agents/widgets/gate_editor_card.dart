import 'package:flutter/material.dart';
import 'package:flutter_quill/flutter_quill.dart';
import '../../../theme/agent_studio_theme.dart';

class GateEditorCard extends StatefulWidget {
  const GateEditorCard({
    super.key,
    required this.index,
    required this.gate,
    this.onChanged,
    this.onDelete,
  });
  final int index;
  final Map<String, dynamic> gate;
  final ValueChanged<Map<String, dynamic>>? onChanged;
  final VoidCallback? onDelete;

  @override
  State<GateEditorCard> createState() => _GateEditorCardState();
}

class _GateEditorCardState extends State<GateEditorCard> {
  bool _expanded = false;
  late QuillController _quillController;

  static const _actionColors = {
    'block': AgentStudioTheme.error,
    'warn': AgentStudioTheme.warning,
    'rewrite': AgentStudioTheme.primary,
    'hitl': Color(0xFF9C27B0),
  };

  static const _gateColors = [
    AgentStudioTheme.gateGreen,
    AgentStudioTheme.gateYellow,
    AgentStudioTheme.gateBlue,
    AgentStudioTheme.gateRed,
  ];

  @override
  void initState() {
    super.initState();
    final content = widget.gate['content'] as String? ?? '';
    _quillController = QuillController(
      document: content.isEmpty
          ? Document()
          : (Document()..insert(0, content)),
      selection: const TextSelection.collapsed(offset: 0),
    );
    _quillController.addListener(_onQuillChanged);
  }

  void _onQuillChanged() {
    final plainText = _quillController.document.toPlainText();
    // Quill adds a trailing newline; strip it for storage
    final trimmed =
        plainText.endsWith('\n') ? plainText.substring(0, plainText.length - 1) : plainText;
    widget.onChanged?.call({...widget.gate, 'content': trimmed});
  }

  @override
  void dispose() {
    _quillController.removeListener(_onQuillChanged);
    _quillController.dispose();
    super.dispose();
  }

  Color get _borderColor => _gateColors[widget.index % _gateColors.length];

  @override
  Widget build(BuildContext context) {
    final name = widget.gate['name'] as String? ?? 'Gate ${widget.index + 1}';
    final action = widget.gate['action'] as String? ?? 'block';

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
      decoration: BoxDecoration(
        color: AgentStudioTheme.content,
        border: Border.all(color: _borderColor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          // Header (always visible)
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  const Icon(Icons.drag_indicator,
                      size: 14, color: AgentStudioTheme.textSecondary),
                  const SizedBox(width: 8),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: _borderColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text('Gate ${widget.index + 1}',
                        style: TextStyle(
                            color: _borderColor,
                            fontSize: 11,
                            fontWeight: FontWeight.w600)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(name,
                        style: const TextStyle(
                            color: AgentStudioTheme.textPrimary,
                            fontSize: 13)),
                  ),
                  if (_expanded)
                    IconButton(
                      icon: const Icon(Icons.delete_outline,
                          size: 16, color: AgentStudioTheme.error),
                      onPressed: widget.onDelete,
                    ),
                  Icon(
                      _expanded ? Icons.expand_less : Icons.chevron_right,
                      size: 18,
                      color: AgentStudioTheme.textSecondary),
                ],
              ),
            ),
          ),
          // Expanded editor
          if (_expanded) ...[
            const Divider(height: 1, color: AgentStudioTheme.border),
            // Toolbar
            Theme(
              data: ThemeData.dark().copyWith(
                iconTheme: const IconThemeData(
                    color: AgentStudioTheme.textPrimary, size: 18),
                canvasColor: AgentStudioTheme.card,
              ),
              child: QuillSimpleToolbar(
                controller: _quillController,
                config: const QuillSimpleToolbarConfig(
                  showAlignmentButtons: false,
                  showBackgroundColorButton: false,
                  showClearFormat: false,
                  showColorButton: false,
                  showFontFamily: false,
                  showFontSize: false,
                  showIndent: false,
                  showLink: true,
                  showSearchButton: false,
                  showSubscript: false,
                  showSuperscript: false,
                  multiRowsDisplay: false,
                ),
              ),
            ),
            const Divider(height: 1, color: AgentStudioTheme.border),
            // Editor
            SizedBox(
              height: 180,
              child: QuillEditor.basic(
                controller: _quillController,
                config: const QuillEditorConfig(
                  padding: EdgeInsets.all(12),
                  placeholder: 'Escribe las reglas del gate...',
                  customStyles: DefaultStyles(
                    paragraph: DefaultTextBlockStyle(
                      TextStyle(
                          color: AgentStudioTheme.textPrimary,
                          fontSize: 13,
                          height: 1.6),
                      HorizontalSpacing(0, 0),
                      VerticalSpacing(0, 0),
                      VerticalSpacing(0, 0),
                      null,
                    ),
                  ),
                ),
              ),
            ),
            // Action selector
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: const BoxDecoration(
                border: Border(
                  top: BorderSide(color: AgentStudioTheme.border),
                ),
              ),
              child: Row(
                children: ['block', 'warn', 'rewrite', 'hitl'].map((a) {
                  final active = a == action;
                  final color =
                      _actionColors[a] ?? AgentStudioTheme.textSecondary;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: InkWell(
                      onTap: () => widget.onChanged
                          ?.call({...widget.gate, 'action': a}),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: active
                              ? color.withValues(alpha: 0.15)
                              : Colors.transparent,
                          border: Border.all(
                              color:
                                  active ? color : AgentStudioTheme.border),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                            '${a[0].toUpperCase()}${a.substring(1)}',
                            style:
                                TextStyle(color: color, fontSize: 11)),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
