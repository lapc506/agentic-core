from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

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
    def __init__(self, session_id: _Optional[str] = ..., persona_id: _Optional[str] = ..., content: _Optional[str] = ..., user_id: _Optional[str] = ..., trace_id: _Optional[str] = ...) -> None: ...

class CreateSessionRequest(_message.Message):
    __slots__ = ("persona_id", "user_id")
    PERSONA_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    persona_id: str
    user_id: str
    def __init__(self, persona_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class GetSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class HumanResponse(_message.Message):
    __slots__ = ("session_id", "content")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    content: str
    def __init__(self, session_id: _Optional[str] = ..., content: _Optional[str] = ...) -> None: ...

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
    def __init__(self, session_id: _Optional[str] = ..., persona_id: _Optional[str] = ..., user_id: _Optional[str] = ..., state: _Optional[str] = ..., created_at: _Optional[str] = ...) -> None: ...

class PersonaList(_message.Message):
    __slots__ = ("personas",)
    PERSONAS_FIELD_NUMBER: _ClassVar[int]
    personas: _containers.RepeatedCompositeFieldContainer[PersonaInfo]
    def __init__(self, personas: _Optional[_Iterable[_Union[PersonaInfo, _Mapping]]] = ...) -> None: ...

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
    def __init__(self, name: _Optional[str] = ..., role: _Optional[str] = ..., description: _Optional[str] = ..., graph_template: _Optional[str] = ...) -> None: ...

class HealthStatus(_message.Message):
    __slots__ = ("healthy", "version", "active_sessions")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    version: str
    active_sessions: int
    def __init__(self, healthy: bool = ..., version: _Optional[str] = ..., active_sessions: _Optional[int] = ...) -> None: ...

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
    def __init__(self, token: _Optional[_Union[StreamToken, _Mapping]] = ..., end: _Optional[_Union[StreamEnd, _Mapping]] = ..., escalation: _Optional[_Union[HumanEscalation, _Mapping]] = ..., audio: _Optional[_Union[AudioChunk, _Mapping]] = ..., error: _Optional[_Union[ErrorDetail, _Mapping]] = ...) -> None: ...

class StreamToken(_message.Message):
    __slots__ = ("session_id", "token")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    token: str
    def __init__(self, session_id: _Optional[str] = ..., token: _Optional[str] = ...) -> None: ...

class StreamEnd(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class HumanEscalation(_message.Message):
    __slots__ = ("session_id", "prompt")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    prompt: str
    def __init__(self, session_id: _Optional[str] = ..., prompt: _Optional[str] = ...) -> None: ...

class AudioChunk(_message.Message):
    __slots__ = ("session_id", "data")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    data: bytes
    def __init__(self, session_id: _Optional[str] = ..., data: _Optional[bytes] = ...) -> None: ...

class ErrorDetail(_message.Message):
    __slots__ = ("session_id", "code", "message")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    code: str
    message: str
    def __init__(self, session_id: _Optional[str] = ..., code: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...
