import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class WsClient {
  WsClient({String? wsUrl}) : _wsUrl = wsUrl ?? _defaultWsUrl();

  /// Use same origin as the page (works in Docker and local dev)
  static String _defaultWsUrl() {
    // In browser: derive from window.location
    // ignore: avoid_dynamic_calls
    try {
      final uri = Uri.base;
      final scheme = uri.scheme == 'https' ? 'wss' : 'ws';
      return '$scheme://${uri.host}:${uri.port}/ws';
    } catch (_) {
      return 'ws://localhost:8080/ws';
    }
  }

  final String _wsUrl;
  WebSocketChannel? _channel;
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  bool get isConnected => _channel != null;

  void connect() {
    _channel = WebSocketChannel.connect(Uri.parse(_wsUrl));
    _channel!.stream.listen(
      (data) {
        final msg = jsonDecode(data as String) as Map<String, dynamic>;
        _messageController.add(msg);
      },
      onError: (error) => _messageController.addError(error),
      onDone: () => _channel = null,
    );
  }

  void send(Map<String, dynamic> message) {
    _channel?.sink.add(jsonEncode(message));
  }

  void createSession(String personaId, {String userId = 'demo'}) {
    send({
      'type': 'create_session',
      'persona_id': personaId,
      'user_id': userId,
    });
  }

  void sendMessage(String sessionId, String personaId, String content) {
    send({
      'type': 'message',
      'session_id': sessionId,
      'persona_id': personaId,
      'content': content,
    });
  }

  void closeSession(String sessionId) {
    send({'type': 'close_session', 'session_id': sessionId});
  }

  void dispose() {
    _channel?.sink.close();
    _messageController.close();
  }
}
