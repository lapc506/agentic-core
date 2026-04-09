# WebSocket Protocol

The WebSocket interface is the primary real-time channel for agent communication. It supports session management, message streaming, human-in-the-loop escalation, and tool call visibility.

---

## Connection

```
ws://localhost:8765
wss://your-agent-studio.example.com   # TLS in production
```

The connection is established with no authentication headers in standalone mode. In sidecar mode, pass a bearer token via the `Authorization` subprotocol or query parameter.

---

## Message Format

All messages are JSON objects with a `type` field that determines the payload shape.

---

## Client → Server Messages

### `create_session`

Start a new conversation session for a given agent.

```json
{
  "type": "create_session",
  "persona_id": "support-agent",
  "user_id": "user_123",
  "metadata": {
    "channel": "web",
    "locale": "en-US"
  }
}
```

**Server response:** [`session_created`](#session_created)

---

### `message`

Send a user message to an active session.

```json
{
  "type": "message",
  "session_id": "sess_abc123",
  "persona_id": "support-agent",
  "content": "I need help with my order #9876",
  "attachments": []
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | yes | Session ID from `create_session` |
| `persona_id` | string | yes | Agent persona to route to |
| `content` | string | yes | User message text |
| `attachments` | array | no | Base64-encoded files (images, PDFs) |

**Server responses:** one or more [`stream_token`](#stream_token), then [`message_complete`](#message_complete)

---

### `resume_hitl`

Resume a session that is waiting for a human decision.

```json
{
  "type": "resume_hitl",
  "session_id": "sess_abc123",
  "decision": "approved",
  "comment": "Approved — escalate to Tier 2"
}
```

---

### `end_session`

Explicitly close a session.

```json
{
  "type": "end_session",
  "session_id": "sess_abc123"
}
```

---

## Server → Client Messages

### `session_created`

Confirms session creation.

```json
{
  "type": "session_created",
  "session_id": "sess_abc123",
  "persona_id": "support-agent",
  "created_at": "2026-04-08T12:00:00Z"
}
```

---

### `stream_token`

A single streaming token from the LLM. Concatenate these in order to reconstruct the full response.

```json
{
  "type": "stream_token",
  "session_id": "sess_abc123",
  "token": "I can",
  "sequence": 1
}
```

---

### `message_complete`

Signals the end of a streaming response.

```json
{
  "type": "message_complete",
  "session_id": "sess_abc123",
  "message_id": "msg_xyz789",
  "usage": {
    "prompt_tokens": 512,
    "completion_tokens": 128,
    "total_tokens": 640
  }
}
```

---

### `tool_call`

Emitted when the agent invokes a tool (visible to the UI for transparency).

```json
{
  "type": "tool_call",
  "session_id": "sess_abc123",
  "tool_name": "mcp_zendesk_create_ticket",
  "arguments": {
    "subject": "Order #9876 issue",
    "priority": "normal"
  }
}
```

---

### `tool_result`

The result of a tool call.

```json
{
  "type": "tool_result",
  "session_id": "sess_abc123",
  "tool_name": "mcp_zendesk_create_ticket",
  "result": {
    "ticket_id": "ZD-4521",
    "status": "created"
  }
}
```

---

### `human_escalation`

Sent when the agent hits a Human-in-the-Loop node and requires a decision before continuing.

```json
{
  "type": "human_escalation",
  "session_id": "sess_abc123",
  "prompt": "The customer is requesting a full refund of $450. Approve?",
  "options": ["approved", "rejected", "escalate"],
  "timeout_seconds": 300
}
```

Respond with [`resume_hitl`](#resume_hitl).

---

### `error`

Sent when a recoverable error occurs.

```json
{
  "type": "error",
  "session_id": "sess_abc123",
  "code": "TOOL_UNAVAILABLE",
  "message": "MCP server 'zendesk' is not responding",
  "recoverable": true
}
```

---

## Flutter Client Example

```dart
final channel = WebSocketChannel.connect(Uri.parse('ws://localhost:8765'));

// Create session
channel.sink.add(jsonEncode({
  'type': 'create_session',
  'persona_id': 'support-agent',
  'user_id': 'user_123',
}));

// Listen for events
channel.stream.listen((data) {
  final msg = jsonDecode(data);
  switch (msg['type']) {
    case 'session_created':
      sessionId = msg['session_id'];
    case 'stream_token':
      appendToken(msg['token']);
    case 'message_complete':
      finalizeMessage(msg['usage']);
    case 'human_escalation':
      showEscalationDialog(msg['prompt'], msg['options']);
    case 'error':
      handleError(msg['code'], msg['message']);
  }
});
```
