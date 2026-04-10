import 'dart:async';

import 'package:flutter/material.dart';
import 'package:genui/genui.dart';
import 'package:logging/logging.dart';

import '../../services/api_client.dart';
import '../../services/ws_client.dart';
import '../../theme/agent_studio_theme.dart';
import 'widgets/debug_panel.dart';

/// Chat page powered by Flutter GenUI — renders dynamic AI-generated widgets
/// instead of plain text bubbles. Connects to agentic-core via the existing
/// WebSocket transport and bridges responses through [A2uiTransportAdapter].
class GenUiChatPage extends StatefulWidget {
  const GenUiChatPage({super.key});

  @override
  State<GenUiChatPage> createState() => _GenUiChatPageState();
}

class _GenUiChatPageState extends State<GenUiChatPage> {
  static final _log = Logger('GenUiChatPage');
  late final SurfaceController _controller;
  final _textController = TextEditingController();
  final _surfaceIds = <String>[];
  final _textMessages = <_ChatEntry>[];
  final _scrollController = ScrollController();
  final _apiClient = ApiClient();
  final _wsClient = WsClient();

  A2uiTransportAdapter? _transport;
  Conversation? _conversation;
  StreamSubscription<ConversationEvent>? _eventSub;
  StreamSubscription<Map<String, dynamic>>? _wsSub;

  List<Map<String, dynamic>> _agents = [];
  String? _selectedAgent;
  String? _sessionId;
  bool _isWaiting = false;
  String _statusText = 'Selecciona un agente';

  // Debug panel state
  bool _debugOpen = false;
  final List<DebugEntry> _debugEntries = [];
  DateTime? _streamStartTime;

  @override
  void initState() {
    super.initState();
    _controller = SurfaceController(
      catalogs: [BasicCatalogItems.asCatalog()],
    );
    _loadAgents();
  }

  // ---------------------------------------------------------------------------
  // Agent loading
  // ---------------------------------------------------------------------------

  Future<void> _loadAgents() async {
    _log.info('Loading agents...');
    try {
      var agents = await _apiClient.listAgents();
      if (agents.isEmpty) {
        _log.info('No agents found, auto-creating demo agent');
        // Auto-create demo agent
        await _apiClient.createAgent({
          'name': 'Asistente Demo',
          'role': 'assistant',
          'description': 'Agente de demostración',
          'graph_template': 'react',
        });
        agents = await _apiClient.listAgents();
      }
      _log.info('Loaded ${agents.length} agents');
      setState(() => _agents = agents);
      if (agents.isNotEmpty && _selectedAgent == null) {
        _selectAgent(agents.first['slug'] as String);
      }
    } catch (e) {
      // Backend may not be available yet
      _log.warning('Failed to load agents: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Agent selection — creates a new Conversation + wires WebSocket
  // ---------------------------------------------------------------------------

  void _selectAgent(String slug) {
    // Don't reconnect if already connected to this agent
    if (_selectedAgent == slug && _sessionId != null) {
      _log.fine('Already connected to $slug, skipping reconnect');
      return;
    }
    _log.info('Selecting agent: $slug');
    // Tear down any previous conversation
    _eventSub?.cancel();
    _conversation?.dispose();
    _transport?.dispose();
    _wsSub?.cancel();

    setState(() {
      _selectedAgent = slug;
      _surfaceIds.clear();
      _textMessages.clear();
      _debugEntries.clear();
      _sessionId = null;
      _streamStartTime = null;
      _statusText = 'Conectando a $slug...';
    });

    // Build the GenUI transport — onSend bridges user text to the WebSocket
    _transport = A2uiTransportAdapter(
      onSend: _sendToAgent,
    );

    // Build conversation (orchestrates controller <-> transport)
    _conversation = Conversation(
      controller: _controller,
      transport: _transport!,
    );

    // Listen to conversation events
    _eventSub = _conversation!.events.listen(_onConversationEvent);

    // Connect the WebSocket and create a session
    _wsClient.connect();
    _wsSub = _wsClient.messages.listen(_onWsMessage);
    _wsClient.createSession(slug);
  }

  // ---------------------------------------------------------------------------
  // Conversation event handler
  // ---------------------------------------------------------------------------

  void _onConversationEvent(ConversationEvent event) {
    switch (event) {
      case ConversationSurfaceAdded(:final surfaceId):
        setState(() {
          if (!_surfaceIds.contains(surfaceId)) {
            _surfaceIds.add(surfaceId);
          }
        });
        _scrollToBottom();
      case ConversationSurfaceRemoved(:final surfaceId):
        setState(() => _surfaceIds.remove(surfaceId));
      case ConversationComponentsUpdated():
        setState(() {}); // trigger rebuild for surface updates
        _scrollToBottom();
      case ConversationContentReceived(:final text):
        setState(() {
          _isWaiting = false;
          if (text.isNotEmpty) {
            _textMessages.add(_ChatEntry(role: _Role.assistant, text: text));
          }
        });
        _scrollToBottom();
      case ConversationWaiting():
        setState(() => _isWaiting = true);
      case ConversationError(:final error):
        setState(() {
          _isWaiting = false;
          _statusText = 'Error: $error';
        });
    }
  }

  // ---------------------------------------------------------------------------
  // WebSocket message handler — feed chunks into A2uiTransportAdapter
  // ---------------------------------------------------------------------------

  void _onWsMessage(Map<String, dynamic> msg) {
    final type = msg['type'] as String?;
    _log.fine('WS message: $type');
    switch (type) {
      case 'session_created':
        setState(() {
          _sessionId = msg['session_id'] as String?;
          _statusText = 'Conectado a $_selectedAgent';
        });
      case 'stream_start':
        _streamStartTime = DateTime.now();
        setState(() {
          _debugEntries.add(DebugEntry(
            type: 'think',
            content: 'Processing...',
          ));
        });
      case 'stream_token':
        // Feed the raw token to the A2UI parser which extracts JSON blocks
        // for surfaces and passes plain text through as chat content.
        final token = msg['token'] as String? ?? '';
        _transport?.addChunk(token);

        // Populate debug entries from structured metadata if present,
        // otherwise fall back to content-based detection.
        final debugType = msg['debug_type'] as String?;
        if (debugType != null) {
          setState(() {
            _debugEntries.add(DebugEntry(
              type: debugType,
              content: msg['debug_content'] as String? ?? token,
              timing: msg['debug_timing'] as String?,
            ));
          });
        } else if (token.contains('tool_call:') || token.contains('Calling ')) {
          setState(() {
            _debugEntries.add(DebugEntry(
              type: 'tool_call',
              content: token.trim(),
            ));
          });
        } else if (token.contains('tool_result:') || token.contains('Result:')) {
          setState(() {
            _debugEntries.add(DebugEntry(
              type: 'tool_result',
              content: token.trim(),
            ));
          });
        } else if (token.contains('gate:') || token.contains('PASS') || token.contains('FAIL')) {
          setState(() {
            _debugEntries.add(DebugEntry(
              type: 'gate',
              content: token.trim(),
            ));
          });
        }
      case 'stream_end':
        final elapsed = _streamStartTime != null
            ? DateTime.now().difference(_streamStartTime!).inMilliseconds
            : 0;
        setState(() {
          _isWaiting = false;
          _debugEntries.add(DebugEntry(
            type: 'response',
            content: 'Complete',
            timing: '${elapsed}ms',
          ));
        });
      case 'human_escalation':
        setState(() {
          _textMessages.add(_ChatEntry(
            role: _Role.system,
            text: 'Escalation: ${msg['reason'] ?? 'Human intervention required'}',
          ));
        });
      case 'error':
        setState(() {
          _textMessages.add(_ChatEntry(
            role: _Role.system,
            text: 'Error: ${msg['message'] ?? 'Unknown error'}',
          ));
          _isWaiting = false;
        });
    }
  }

  // ---------------------------------------------------------------------------
  // Sending a message
  // ---------------------------------------------------------------------------

  Future<void> _sendToAgent(ChatMessage message) async {
    // Forward the GenUI ChatMessage through the WebSocket session
    if (_sessionId == null || _selectedAgent == null) return;
    _wsClient.sendMessage(_sessionId!, _selectedAgent!, message.text);
  }

  void _sendMessage() {
    final text = _textController.text.trim();
    if (text.isEmpty || _selectedAgent == null) return;
    _log.info('Sending message to $_selectedAgent (${text.length} chars)');

    // Record the user message locally
    setState(() {
      _textMessages.add(_ChatEntry(role: _Role.user, text: text));
      _isWaiting = true;
    });
    _textController.clear();
    _scrollToBottom();

    // Route through the Conversation facade so transport gets it
    _conversation?.sendRequest(ChatMessage.user(text));
  }

  // ---------------------------------------------------------------------------
  // Scroll helper
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    _eventSub?.cancel();
    _conversation?.dispose();
    _transport?.dispose();
    _wsSub?.cancel();
    _wsClient.dispose();
    _controller.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final chatContent = Column(
      children: [
        Expanded(
          child: _hasContent ? _buildConversation() : _buildEmptyState(),
        ),
        _buildInputBar(),
      ],
    );

    return Column(
      children: [
        _buildHeader(),
        Expanded(
          child: Row(
            children: [
              Expanded(child: chatContent),
              if (_debugOpen)
                Container(
                  width: 320,
                  decoration: const BoxDecoration(
                    color: Color(0xFF0E1018),
                    border: Border(
                      left: BorderSide(
                        color: AgentStudioTheme.primary,
                        width: 2,
                      ),
                    ),
                  ),
                  child: DebugPanel(
                    entries: _debugEntries,
                    sessionId: _sessionId,
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  bool get _hasContent =>
      _textMessages.isNotEmpty || _surfaceIds.isNotEmpty || _isWaiting;

  /// Interleaves plain-text chat bubbles with GenUI surfaces in a single list.
  Widget _buildConversation() {
    // Build an ordered list of render items: text bubbles + surface widgets.
    final items = <_RenderItem>[];

    for (final entry in _textMessages) {
      items.add(_RenderItem.text(entry));
    }
    for (final sid in _surfaceIds) {
      items.add(_RenderItem.surface(sid));
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(16),
      itemCount: items.length + (_isWaiting ? 1 : 0),
      itemBuilder: (context, index) {
        // Trailing spinner
        if (index == items.length && _isWaiting) {
          return const Padding(
            padding: EdgeInsets.all(16),
            child: Center(
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AgentStudioTheme.primary,
                ),
              ),
            ),
          );
        }

        final item = items[index];
        if (item.isSurface) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Surface(
              surfaceContext: _controller.contextFor(item.surfaceId!),
              defaultBuilder: (_) => _surfacePlaceholder(),
              actionDelegate: const _AgentStudioActionDelegate(),
            ),
          );
        }

        // Plain text bubble
        return _buildBubble(item.chatEntry!);
      },
    );
  }

  Widget _surfacePlaceholder() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AgentStudioTheme.card,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AgentStudioTheme.border),
      ),
      child: const Text(
        'Rendering...',
        style: TextStyle(color: AgentStudioTheme.textSecondary),
      ),
    );
  }

  Widget _buildBubble(_ChatEntry entry) {
    final isUser = entry.role == _Role.user;
    final isSystem = entry.role == _Role.system;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: isSystem
                    ? AgentStudioTheme.warning
                    : AgentStudioTheme.primary,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Icon(
                isSystem ? Icons.warning_amber : Icons.smart_toy,
                size: 14,
                color: Colors.white,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isUser
                    ? AgentStudioTheme.primary
                    : isSystem
                        ? const Color(0xFF2e2a1a)
                        : AgentStudioTheme.card,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(8),
                  topRight: const Radius.circular(8),
                  bottomLeft: Radius.circular(isUser ? 8 : 0),
                  bottomRight: Radius.circular(isUser ? 0 : 8),
                ),
              ),
              child: Text(
                entry.text,
                style: TextStyle(
                  color:
                      isUser ? Colors.white : AgentStudioTheme.textPrimary,
                  fontSize: 13,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Header with agent selector and GenUI status badge
  // ---------------------------------------------------------------------------

  Widget _buildHeader() {
    final connected = _selectedAgent != null && _sessionId != null;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AgentStudioTheme.border)),
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: AgentStudioTheme.primary,
              borderRadius: BorderRadius.circular(6),
            ),
            child:
                const Icon(Icons.smart_toy, size: 16, color: Colors.white),
          ),
          const SizedBox(width: 8),
          DropdownButton<String>(
            value: _selectedAgent,
            hint: const Text(
              'Seleccionar agente',
              style: TextStyle(
                color: AgentStudioTheme.textSecondary,
                fontSize: 13,
              ),
            ),
            dropdownColor: AgentStudioTheme.card,
            underline: const SizedBox(),
            style: const TextStyle(
              color: AgentStudioTheme.textPrimary,
              fontSize: 13,
            ),
            items: _agents.map((a) {
              final slug = a['slug'] as String? ?? '';
              final name = a['name'] as String? ?? slug;
              return DropdownMenuItem(value: slug, child: Text(name));
            }).toList(),
            onChanged: (slug) {
              if (slug != null) _selectAgent(slug);
            },
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: connected
                  ? const Color(0xFF1a2e1a)
                  : const Color(0xFF2e1a1a),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              connected ? '\u25CF $_statusText' : '\u25CB $_statusText',
              style: TextStyle(
                color: connected
                    ? AgentStudioTheme.success
                    : AgentStudioTheme.error,
                fontSize: 11,
              ),
            ),
          ),
          const SizedBox(width: 8),
          InkWell(
            onTap: () => setState(() => _debugOpen = !_debugOpen),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AgentStudioTheme.primary,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('\u{1F50D} Debug',
                      style: TextStyle(color: Colors.white, fontSize: 11)),
                  const SizedBox(width: 4),
                  Text(_debugOpen ? '\u25C2' : '\u25B8',
                      style:
                          const TextStyle(color: Colors.white, fontSize: 9)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Empty state
  // ---------------------------------------------------------------------------

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.auto_awesome,
            size: 48,
            color: AgentStudioTheme.primary.withValues(alpha: 0.3),
          ),
          const SizedBox(height: 12),
          Text(
            _selectedAgent == null
                ? 'Selecciona un agente para comenzar'
                : 'Envia un mensaje — el agente genera UI interactiva',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.3),
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Powered by Flutter GenUI + A2A Protocol',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.15),
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Input bar
  // ---------------------------------------------------------------------------

  Widget _buildInputBar() {
    final enabled = _selectedAgent != null && _sessionId != null && !_isWaiting;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AgentStudioTheme.border)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              enabled: enabled,
              style: const TextStyle(
                color: AgentStudioTheme.textPrimary,
                fontSize: 13,
              ),
              decoration: const InputDecoration(
                hintText: 'Escribe un mensaje...',
                hintStyle: TextStyle(color: AgentStudioTheme.textSecondary),
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              ),
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          const SizedBox(width: 8),
          InkWell(
            onTap: enabled ? _sendMessage : null,
            child: Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: enabled
                    ? AgentStudioTheme.primary
                    : AgentStudioTheme.border,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(
                Icons.arrow_upward,
                size: 18,
                color: Colors.white,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// Action delegate — handles HITL confirmation requests from GenUI surfaces
// =============================================================================

class _AgentStudioActionDelegate implements ActionDelegate {
  const _AgentStudioActionDelegate();

  @override
  bool handleEvent(
    BuildContext context,
    UiEvent event,
    SurfaceContext genUiContext,
    Widget Function(SurfaceDefinition, Catalog, String, DataContext)
        buildWidget,
  ) {
    if (event is UserActionEvent && event.name == 'confirm') {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: AgentStudioTheme.card,
          title: const Text(
            'Confirmacion requerida',
            style: TextStyle(color: AgentStudioTheme.textPrimary),
          ),
          content: Text(
            event.context['message']?.toString() ??
                'Confirmar esta accion?',
            style:
                const TextStyle(color: AgentStudioTheme.textSecondary),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text(
                'Cancelar',
                style:
                    TextStyle(color: AgentStudioTheme.textSecondary),
              ),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(ctx);
                genUiContext.handleUiEvent(UserActionEvent(
                  name: 'confirmed',
                  sourceComponentId: event.sourceComponentId,
                  context: event.context,
                ));
              },
              style: FilledButton.styleFrom(
                backgroundColor: AgentStudioTheme.primary,
              ),
              child: const Text('Confirmar'),
            ),
          ],
        ),
      );
      return true;
    }
    return false;
  }
}

// =============================================================================
// Internal helpers
// =============================================================================

enum _Role { user, assistant, system }

class _ChatEntry {
  _ChatEntry({required this.role, required this.text});
  final _Role role;
  final String text;
}

/// A tagged-union for items rendered in the conversation list.
class _RenderItem {
  _RenderItem.text(this.chatEntry) : surfaceId = null;
  _RenderItem.surface(this.surfaceId) : chatEntry = null;

  final _ChatEntry? chatEntry;
  final String? surfaceId;

  bool get isSurface => surfaceId != null;
}
