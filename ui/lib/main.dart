import 'package:flutter/material.dart';
import 'theme/agent_studio_theme.dart';

void main() => runApp(const AgentStudioApp());

class AgentStudioApp extends StatelessWidget {
  const AgentStudioApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agent Studio',
      debugShowCheckedModeBanner: false,
      theme: AgentStudioTheme.darkTheme,
      home: const Scaffold(
        body: Center(
          child: Text('Agent Studio', style: TextStyle(fontSize: 18)),
        ),
      ),
    );
  }
}
