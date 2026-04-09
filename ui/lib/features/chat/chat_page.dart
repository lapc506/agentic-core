import 'dart:async';
import 'package:flutter/material.dart';
import '../../services/api_client.dart';
import '../../services/ws_client.dart';
import 'models/chat_message.dart';
import 'widgets/agent_selector.dart';
import 'widgets/chat_input_bar.dart';
import 'widgets/message_bubble.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});
  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final _apiClient = ApiClient();
  final _wsClient = WsClient();
  final _scrollController = ScrollController();
  final _messages = <ChatMessage>[];

  List<Map<String, dynamic>> _agents = [];
  String? _selectedAgent;
  String? _sessionId;
  StreamSubscription<Map<String, dynamic>>? _wsSub;
  bool _isStreaming = false;

  @override
  void initState() {
    super.initState();
    _loadAgents();
  }

  Future<void> _loadAgents() async {
    try {
      final agents = await _apiClient.listAgents();
      setState(() => _agents = agents);
      // Auto-select first agent if only one exists (or default)
      if (agents.isNotEmpty && _selectedAgent == null) {
        final slug = agents.first['slug'] as String?;
        if (slug != null) {
          _connectAndCreateSession(slug);
        }
      }
    } catch (_) {
      // Backend not available yet — that's OK for demo
    }
  }

  void _connectAndCreateSession(String agentSlug) {
    _wsClient.connect();
    _wsSub?.cancel();
    _wsSub = _wsClient.messages.listen(_onWsMessage);
    _wsClient.createSession(agentSlug);
    setState(() => _selectedAgent = agentSlug);
  }

  void _onWsMessage(Map<String, dynamic> msg) {
    final type = msg['type'] as String?;
    switch (type) {
      case 'session_created':
        setState(() => _sessionId = msg['session_id'] as String?);
      case 'stream_start':
        setState(() {
          _isStreaming = true;
          _messages.add(ChatMessage(
            role: MessageRole.assistant,
            content: '',
            isStreaming: true,
          ));
        });
      case 'stream_token':
        setState(() {
          if (_messages.isNotEmpty &&
              _messages.last.role == MessageRole.assistant) {
            _messages.last.content += msg['token'] as String? ?? '';
          }
        });
        _scrollToBottom();
      case 'stream_end':
        setState(() {
          _isStreaming = false;
          if (_messages.isNotEmpty) _messages.last.isStreaming = false;
        });
      case 'human_escalation':
        setState(() {
          _messages.add(ChatMessage(
            role: MessageRole.system,
            content:
                'Escalation: ${msg['reason'] ?? 'Human intervention required'}',
          ));
        });
      case 'error':
        setState(() {
          _messages.add(ChatMessage(
            role: MessageRole.system,
            content: 'Error: ${msg['message'] ?? 'Unknown error'}',
          ));
        });
    }
  }

  void _sendMessage(String content) {
    if (_sessionId == null || _selectedAgent == null) return;
    setState(() {
      _messages.add(ChatMessage(role: MessageRole.user, content: content));
    });
    _wsClient.sendMessage(_sessionId!, _selectedAgent!, content);
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _wsSub?.cancel();
    _wsClient.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AgentSelector(
          agents: _agents,
          selectedAgent: _selectedAgent,
          onChanged: (slug) {
            if (slug != null) _connectAndCreateSession(slug);
          },
          isConnected: _wsClient.isConnected && _sessionId != null,
        ),
        Expanded(
          child: _messages.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.chat_bubble_outline,
                          size: 48,
                          color: Colors.white.withValues(alpha: 0.1)),
                      const SizedBox(height: 12),
                      Text(
                        _selectedAgent == null
                            ? 'Selecciona un agente para comenzar'
                            : 'Envia un mensaje para iniciar la conversacion',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.3),
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16),
                  itemCount: _messages.length,
                  itemBuilder: (_, i) =>
                      MessageBubble(message: _messages[i]),
                ),
        ),
        ChatInputBar(
          onSend: _sendMessage,
          enabled: _sessionId != null && !_isStreaming,
        ),
      ],
    );
  }
}
