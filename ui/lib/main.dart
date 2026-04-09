import 'package:flutter/material.dart';

void main() {
  runApp(const AgentStudioApp());
}

class AgentStudioApp extends StatelessWidget {
  const AgentStudioApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agent Studio',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        scaffoldBackgroundColor: const Color(0xFF12121E),
        colorScheme: ColorScheme.dark(
          primary: const Color(0xFF3B6FE0),
          surface: const Color(0xFF1A1A2E),
        ),
      ),
      home: const Scaffold(
        body: Center(
          child: Text(
            'Agent Studio\nBackend running — UI coming in Plan 2',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 18, color: Color(0xFFE0E0F0)),
          ),
        ),
      ),
    );
  }
}
