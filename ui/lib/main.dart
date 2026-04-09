import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'theme/agent_studio_theme.dart';
import 'routing/router.dart';
import 'features/onboarding/onboarding_dialog.dart';

void main() => runApp(const AgentStudioApp());

class AgentStudioApp extends StatefulWidget {
  const AgentStudioApp({super.key});
  @override
  State<AgentStudioApp> createState() => _AgentStudioAppState();
}

// Global theme notifier so sidebar can toggle it
final themeNotifier = ValueNotifier<bool>(true); // true = dark

class _AgentStudioAppState extends State<AgentStudioApp> {
  bool _checkingSetup = true;
  bool _needsOnboarding = false;

  @override
  void initState() {
    super.initState();
    _checkSetup();
  }

  Future<void> _checkSetup() async {
    try {
      final resp = await http.get(Uri.parse('/api/studio/setup-status'));
      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        setState(() {
          _needsOnboarding = !(data['has_agents'] as bool? ?? false);
          _checkingSetup = false;
        });
        return;
      }
    } catch (_) {
      // Backend not available — skip onboarding
    }
    setState(() => _checkingSetup = false);
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<bool>(
      valueListenable: themeNotifier,
      builder: (context, isDark, _) => MaterialApp.router(
      title: 'Agent Studio',
      debugShowCheckedModeBanner: false,
      theme: isDark ? AgentStudioTheme.darkTheme : AgentStudioTheme.lightTheme,
      routerConfig: router,
      builder: (context, child) {
        if (_checkingSetup) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator(color: AgentStudioTheme.primary)),
          );
        }
        return Stack(
          children: [
            child ?? const SizedBox.shrink(),
            if (_needsOnboarding)
              ColoredBox(
                color: Colors.black54,
                child: Center(
                  child: OnboardingDialog(
                    onComplete: () => setState(() => _needsOnboarding = false),
                  ),
                ),
              ),
          ],
        );
      },
    ));
  }
}
