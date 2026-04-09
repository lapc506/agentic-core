import 'package:flutter/material.dart';
import 'theme/agent_studio_theme.dart';
import 'routing/router.dart';

void main() => runApp(const AgentStudioApp());

class AgentStudioApp extends StatelessWidget {
  const AgentStudioApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Agent Studio',
      debugShowCheckedModeBanner: false,
      theme: AgentStudioTheme.darkTheme,
      routerConfig: router,
    );
  }
}
