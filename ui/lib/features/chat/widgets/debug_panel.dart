import 'package:flutter/material.dart';
import '../../../theme/agent_studio_theme.dart';

/// A single debug log entry produced during an LLM streaming session.
class DebugEntry {
  DebugEntry({
    required this.type,
    required this.content,
    this.timing,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  /// One of: think, tool_call, tool_result, gate, response
  final String type;
  final String content;
  final String? timing;
  final DateTime timestamp;
}

/// Right-side debug panel that renders a scrollable list of [DebugEntry] items
/// with color-coded prefixes matching the design spec.
class DebugPanel extends StatelessWidget {
  const DebugPanel({super.key, required this.entries, this.sessionId});

  final List<DebugEntry> entries;
  final String? sessionId;

  static const _typeColors = <String, Color>{
    'think': AgentStudioTheme.primary,
    'tool_call': AgentStudioTheme.warning,
    'tool_result': AgentStudioTheme.success,
    'gate': Color(0xFF9C27B0),
    'response': AgentStudioTheme.textPrimary,
  };

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: const BoxDecoration(
            border: Border(
              bottom: BorderSide(color: AgentStudioTheme.border),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.bug_report,
                      size: 14, color: AgentStudioTheme.primary),
                  const SizedBox(width: 6),
                  const Text('Debug',
                      style: TextStyle(
                          color: AgentStudioTheme.textPrimary,
                          fontSize: 13,
                          fontWeight: FontWeight.w600)),
                  const Spacer(),
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: AgentStudioTheme.success,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Text('live',
                      style: TextStyle(
                          color: AgentStudioTheme.success, fontSize: 10)),
                ],
              ),
              if (sessionId != null) ...[
                const SizedBox(height: 6),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AgentStudioTheme.content,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: AgentStudioTheme.border),
                  ),
                  child: Text(
                    'session: $sessionId',
                    style: const TextStyle(
                      color: AgentStudioTheme.textSecondary,
                      fontSize: 10,
                      fontFamily: 'monospace',
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ],
          ),
        ),

        // Scrollable entry list
        Expanded(
          child: entries.isEmpty
              ? Center(
                  child: Text(
                    'Sin eventos',
                    style: TextStyle(
                      color: AgentStudioTheme.textSecondary.withValues(alpha: 0.5),
                      fontSize: 12,
                    ),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(8),
                  itemCount: entries.length,
                  itemBuilder: (_, i) => _entryTile(entries[i]),
                ),
        ),

        // Metrics footer
        if (entries.isNotEmpty) _metricsBar(),
      ],
    );
  }

  Widget _entryTile(DebugEntry entry) {
    final color = _typeColors[entry.type] ?? AgentStudioTheme.textSecondary;
    final ts =
        '${entry.timestamp.hour.toString().padLeft(2, '0')}:${entry.timestamp.minute.toString().padLeft(2, '0')}:${entry.timestamp.second.toString().padLeft(2, '0')}';

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Colored type prefix
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(3),
            ),
            child: Text(
              '[${entry.type}]',
              style: TextStyle(
                  color: color, fontSize: 10, fontFamily: 'monospace'),
            ),
          ),
          const SizedBox(width: 6),
          // Content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.content,
                  style: const TextStyle(
                    color: AgentStudioTheme.textPrimary,
                    fontSize: 11,
                    fontFamily: 'monospace',
                  ),
                  maxLines: 4,
                  overflow: TextOverflow.ellipsis,
                ),
                if (entry.timing != null)
                  Text(
                    entry.timing!,
                    style: const TextStyle(
                      color: AgentStudioTheme.textSecondary,
                      fontSize: 9,
                      fontFamily: 'monospace',
                    ),
                  ),
              ],
            ),
          ),
          // Timestamp
          Text(
            ts,
            style: const TextStyle(
              color: AgentStudioTheme.textSecondary,
              fontSize: 9,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }

  Widget _metricsBar() {
    final thinkCount = entries.where((e) => e.type == 'think').length;
    final toolCalls = entries.where((e) => e.type == 'tool_call').length;
    final gates = entries.where((e) => e.type == 'gate').length;
    final responses = entries.where((e) => e.type == 'response').length;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AgentStudioTheme.border)),
        color: AgentStudioTheme.content,
      ),
      child: Row(
        children: [
          _metricChip('think', thinkCount, AgentStudioTheme.primary),
          const SizedBox(width: 8),
          _metricChip('tools', toolCalls, AgentStudioTheme.warning),
          const SizedBox(width: 8),
          _metricChip('gates', gates, const Color(0xFF9C27B0)),
          const SizedBox(width: 8),
          _metricChip('resp', responses, AgentStudioTheme.textPrimary),
        ],
      ),
    );
  }

  Widget _metricChip(String label, int count, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(
          '$label: $count',
          style: const TextStyle(
            color: AgentStudioTheme.textSecondary,
            fontSize: 10,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}
