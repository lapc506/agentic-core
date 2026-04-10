import 'dart:async';
import 'dart:convert';
import 'dart:math' show min;
import 'package:logging/logging.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class WsClient {
  static final _log = Logger('WsClient');
  WsClient({String? wsUrl}) : _wsUrl = wsUrl ?? _defaultWsUrl();

  /// Resolve WebSocket URL. Web uses same-origin, desktop uses localhost.
  static String _defaultWsUrl() {
    try {
      final uri = Uri.base;
      // Only use Uri.base if it's a real HTTP origin (web mode)
      if ((uri.scheme == 'http' || uri.scheme == 'https') && uri.host.isNotEmpty) {
        final scheme = uri.scheme == 'https' ? 'wss' : 'ws';
        return '$scheme://${uri.host}:${uri.port}/ws';
      }
    } catch (_) {}
    // Desktop / mobile fallback
    return 'ws://localhost:8080/ws';
  }

  final String _wsUrl;
  WebSocketChannel? _channel;
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  bool get isConnected => _channel != null;

  void connect() {
    _log.info('Connecting to $_wsUrl');
    _channel = WebSocketChannel.connect(Uri.parse(_wsUrl));
    _channel!.stream.listen(
      (data) {
        final raw = data as String;
        _log.fine('WS recv: ${raw.substring(0, min(100, raw.length))}...');
        final msg = jsonDecode(raw) as Map<String, dynamic>;
        _messageController.add(msg);
      },
      onError: (error) {
        _log.severe('WS error: $error');
        _messageController.addError(error);
      },
      onDone: () {
        _log.info('WS closed');
        _channel = null;
      },
    );
  }

  void send(Map<String, dynamic> message) {
    _log.fine('WS send: ${message['type']}');
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
    _log.info('Disposing WsClient');
    _channel?.sink.close();
    _messageController.close();
  }
}
