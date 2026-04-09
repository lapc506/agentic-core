import 'package:flutter/material.dart';

class AgentEditorPage extends StatelessWidget {
  const AgentEditorPage({super.key, required this.agentSlug});
  final String agentSlug;
  @override
  Widget build(BuildContext context) {
    return Center(child: Text('Agent Editor: $agentSlug', style: const TextStyle(fontSize: 18)));
  }
}
