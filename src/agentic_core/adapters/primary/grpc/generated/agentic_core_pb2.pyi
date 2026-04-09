from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AgentRequest(_message.Message):
    __slots__ = ("session_id", "persona_id", "content", "user_id", "trace_id")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PERSONA_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    persona_id: str
    content: str
    user_id: str
    trace_id: str
    def __init__(self, session_id: str | None = ..., persona_id: str | None = ..., content: str | None = ..., user_id: str | None = ..., trace_id: str | None = ...) -> None: ...

class CreateSessionRequest(_message.Message):
    __slots__ = ("persona_id", "user_id")
    PERSONA_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    persona_id: str
    user_id: str
    def __init__(self, persona_id: str | None = ..., user_id: str | None = ...) -> None: ...

class GetSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: str | None = ...) -> None: ...

class HumanResponse(_message.Message):
    __slots__ = ("session_id", "content")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    content: str
    def __init__(self, session_id: str | None = ..., content: str | None = ...) -> None: ...

class SessionInfo(_message.Message):
    __slots__ = ("session_id", "persona_id", "user_id", "state", "created_at")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PERSONA_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    persona_id: str
    user_id: str
    state: str
    created_at: str
    def __init__(self, session_id: str | None = ..., persona_id: str | None = ..., user_id: str | None = ..., state: str | None = ..., created_at: str | None = ...) -> None: ...

class PersonaList(_message.Message):
    __slots__ = ("personas",)
    PERSONAS_FIELD_NUMBER: _ClassVar[int]
    personas: _containers.RepeatedCompositeFieldContainer[PersonaInfo]
    def __init__(self, personas: _Iterable[PersonaInfo | _Mapping] | None = ...) -> None: ...

class PersonaInfo(_message.Message):
    __slots__ = ("name", "role", "description", "graph_template")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    GRAPH_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    name: str
    role: str
    description: str
    graph_template: str
    def __init__(self, name: str | None = ..., role: str | None = ..., description: str | None = ..., graph_template: str | None = ...) -> None: ...

class HealthStatus(_message.Message):
    __slots__ = ("healthy", "version", "active_sessions")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    version: str
    active_sessions: int
    def __init__(self, healthy: bool = ..., version: str | None = ..., active_sessions: int | None = ...) -> None: ...

class AgentResponse(_message.Message):
    __slots__ = ("token", "end", "escalation", "audio", "error")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    ESCALATION_FIELD_NUMBER: _ClassVar[int]
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    token: StreamToken
    end: StreamEnd
    escalation: HumanEscalation
    audio: AudioChunk
    error: ErrorDetail
    def __init__(self, token: StreamToken | _Mapping | None = ..., end: StreamEnd | _Mapping | None = ..., escalation: HumanEscalation | _Mapping | None = ..., audio: AudioChunk | _Mapping | None = ..., error: ErrorDetail | _Mapping | None = ...) -> None: ...

class StreamToken(_message.Message):
    __slots__ = ("session_id", "token")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    token: str
    def __init__(self, session_id: str | None = ..., token: str | None = ...) -> None: ...

class StreamEnd(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: str | None = ...) -> None: ...

class HumanEscalation(_message.Message):
    __slots__ = ("session_id", "prompt")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    prompt: str
    def __init__(self, session_id: str | None = ..., prompt: str | None = ...) -> None: ...

class AudioChunk(_message.Message):
    __slots__ = ("session_id", "data")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    data: bytes
    def __init__(self, session_id: str | None = ..., data: bytes | None = ...) -> None: ...

class ErrorDetail(_message.Message):
    __slots__ = ("session_id", "code", "message")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    code: str
    message: str
    def __init__(self, session_id: str | None = ..., code: str | None = ..., message: str | None = ...) -> None: ...
