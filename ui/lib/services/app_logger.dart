import 'dart:io';
import 'package:logging/logging.dart';

/// Central logging configuration for Agent Studio.
/// Logs go to stderr (visible in desktop via tail -f) and can be
/// written to a file for post-mortem analysis.
class AppLogger {
  AppLogger._();

  static bool _initialized = false;
  static IOSink? _fileSink;

  /// Call once in main() before runApp().
  static void init({Level level = Level.INFO, String? logFile}) {
    if (_initialized) return;
    _initialized = true;

    Logger.root.level = level;

    if (logFile != null) {
      try {
        _fileSink = File(logFile).openWrite(mode: FileMode.append);
      } catch (_) {}
    }

    Logger.root.onRecord.listen((record) {
      final msg = '${record.time.toIso8601String().substring(11, 23)} '
          '[${record.level.name.padRight(7)}] '
          '${record.loggerName}: ${record.message}';

      // Always to stderr (visible in desktop terminal)
      stderr.writeln(msg);

      // Optionally to file
      _fileSink?.writeln(msg);

      // Errors include stack trace
      if (record.error != null) {
        stderr.writeln('  Error: ${record.error}');
        _fileSink?.writeln('  Error: ${record.error}');
      }
      if (record.stackTrace != null) {
        stderr.writeln('  ${record.stackTrace}');
      }
    });
  }

  static void dispose() {
    _fileSink?.close();
  }
}
