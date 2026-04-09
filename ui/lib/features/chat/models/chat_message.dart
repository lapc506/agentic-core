enum MessageRole { user, assistant, system, tool }

class ChatMessage {
  ChatMessage({
    required this.role,
    required this.content,
    this.toolName,
    this.toolInput,
    this.isStreaming = false,
  });

  final MessageRole role;
  String content;
  final String? toolName;
  final String? toolInput;
  bool isStreaming;
}
