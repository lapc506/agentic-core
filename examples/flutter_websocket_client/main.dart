import 'dart:convert';
import 'dart:io';

/// Minimal Flutter/Dart WebSocket client for agentic-core.
/// Run: dart run examples/flutter_websocket_client/main.dart
void main() async {
  final wsUrl = 'ws://localhost:8765';
  print('Connecting to $wsUrl...');

  final ws = await WebSocket.connect(wsUrl);
  print('Connected!\n');

  // Listen for server messages
  ws.listen(
    (data) {
      final msg = jsonDecode(data as String) as Map<String, dynamic>;
      switch (msg['type']) {
        case 'session_created':
          print('[SESSION] Created: ${msg['session_id']}');
          // Send a message once session is created
          ws.add(jsonEncode({
            'type': 'message',
            'session_id': msg['session_id'],
            'persona_id': 'support-agent',
            'content': 'I need help with my order #12345',
          }));
        case 'stream_start':
          stdout.write('[AGENT] ');
        case 'stream_token':
          stdout.write(msg['token']);
        case 'stream_end':
          print('\n[AGENT] -- end of response --');
        case 'human_escalation':
          print('\n[HITL] Agent asks: ${msg['prompt']}');
          // In a real app, show a dialog and send human_response back
          ws.add(jsonEncode({
            'type': 'human_response',
            'session_id': msg['session_id'],
            'content': 'Yes, approved.',
          }));
        case 'error':
          print('[ERROR] ${msg['code']}: ${msg['message']}');
        case 'session_closed':
          print('[SESSION] Closed: ${msg['session_id']}');
        default:
          print('[UNKNOWN] $msg');
      }
    },
    onDone: () => print('Disconnected.'),
    onError: (e) => print('Error: $e'),
  );

  // Create a session
  ws.add(jsonEncode({
    'type': 'create_session',
    'persona_id': 'support-agent',
    'user_id': 'flutter_user_1',
  }));

  // Keep alive for 30 seconds then close
  await Future.delayed(Duration(seconds: 30));
  await ws.close();
  print('Client closed.');
}
