import 'package:flutter/material.dart';

class RulesPage extends StatelessWidget {
  const RulesPage({super.key, required this.agentSlug});
  final String agentSlug;
  @override
  Widget build(BuildContext context) {
    return Center(child: Text('Rules: $agentSlug', style: const TextStyle(fontSize: 18)));
  }
}
