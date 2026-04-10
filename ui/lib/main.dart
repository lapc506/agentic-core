import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:logging/logging.dart';
import 'services/api_client.dart';
import 'services/app_logger.dart';
import 'theme/agent_studio_theme.dart';
import 'routing/router.dart';
import 'features/onboarding/onboarding_dialog.dart';

void main() {
  AppLogger.init(level: Level.FINE, logFile: '/tmp/agent-studio.log');
  runApp(const AgentStudioApp());
}

class AgentStudioApp extends StatefulWidget {
  const AgentStudioApp({super.key});
  @override
  State<AgentStudioApp> createState() => _AgentStudioAppState();
}

// Global theme notifier so sidebar can toggle it
final themeNotifier = ValueNotifier<bool>(true); // true = dark

class _AgentStudioAppState extends State<AgentStudioApp> {
  static final _log = Logger('AgentStudioApp');
  bool _checkingSetup = true;
  bool _needsOnboarding = false;

  @override
  void initState() {
    super.initState();
    _checkSetup();
  }

  Future<void> _checkSetup() async {
    _log.info('Checking setup status...');
    try {
      final resp = await http.get(Uri.parse('${ApiClient.baseUrl}/api/studio/setup-status'));
      _log.fine('Setup status: ${resp.statusCode}');
      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final hasAgents = data['has_agents'] as bool? ?? false;
        _log.info('Setup check complete: has_agents=$hasAgents');
        setState(() {
          _needsOnboarding = !hasAgents;
          _checkingSetup = false;
        });
        return;
      }
    } catch (e) {
      // Backend not available — skip onboarding
      _log.warning('Setup check failed, skipping onboarding: $e');
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
