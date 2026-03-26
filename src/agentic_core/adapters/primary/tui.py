"""Terminal UI: rich TUI with panels, shortcuts, session management (#73)."""
from __future__ import annotations

import logging
import uuid
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TUIPanel(str, Enum):
    """Available TUI panels."""

    CONVERSATION = "conversation"
    TOOLS = "tools"
    STATUS = "status"
    SESSIONS = "sessions"


class TUIConfig(BaseModel):
    """Configuration for the terminal user interface."""

    show_panels: list[TUIPanel] = Field(
        default_factory=lambda: [
            TUIPanel.CONVERSATION,
            TUIPanel.TOOLS,
            TUIPanel.STATUS,
        ],
    )
    show_timestamps: bool = Field(default=True)
    max_history: int = Field(default=1000, ge=1)
    theme: str = Field(default="default")


class TUIKeyBinding(BaseModel, frozen=True):
    """A single keyboard shortcut binding."""

    key: str
    action: str
    description: str


DEFAULT_KEYBINDINGS: list[TUIKeyBinding] = [
    TUIKeyBinding(key="ctrl+c", action="quit", description="Quit the application"),
    TUIKeyBinding(key="ctrl+n", action="new_session", description="Start a new session"),
    TUIKeyBinding(key="tab", action="switch_panel", description="Switch to the next panel"),
    TUIKeyBinding(key="pgup", action="scroll_up", description="Scroll up"),
    TUIKeyBinding(key="pgdn", action="scroll_down", description="Scroll down"),
    TUIKeyBinding(key="ctrl+l", action="clear", description="Clear the current panel"),
]


class TUIState(BaseModel):
    """Mutable runtime state of the TUI."""

    active_panel: TUIPanel = TUIPanel.CONVERSATION
    session_id: str | None = Field(default=None)
    messages: list[str] = Field(default_factory=list)
    tool_outputs: list[str] = Field(default_factory=list)


class TUIAdapter:
    """Rich terminal interface adapter with panels, shortcuts, and session management.

    Provides state management for a TUI that can be driven by a real
    rendering backend (e.g. Textual, Rich Live, curses).  Until a
    concrete renderer is wired this adapter tracks logical state only.
    """

    def __init__(self, config: TUIConfig | None = None) -> None:
        self._config = config or TUIConfig()
        self._state = TUIState(session_id=str(uuid.uuid4()))
        self._keybindings = list(DEFAULT_KEYBINDINGS)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> TUIConfig:
        return self._config

    @property
    def keybindings(self) -> list[TUIKeyBinding]:
        return list(self._keybindings)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self) -> TUIState:
        """Return a copy of the current TUI state."""
        return self._state.model_copy(deep=True)

    def add_message(self, role: str, content: str) -> None:
        """Append a chat message, respecting *max_history*."""
        formatted = f"[{role}] {content}"
        self._state.messages.append(formatted)
        if len(self._state.messages) > self._config.max_history:
            self._state.messages = self._state.messages[-self._config.max_history :]
        logger.debug("TUI message added: role=%s, total=%d", role, len(self._state.messages))

    def add_tool_output(self, tool_name: str, output: str) -> None:
        """Record tool output, respecting *max_history*."""
        formatted = f"[{tool_name}] {output}"
        self._state.tool_outputs.append(formatted)
        if len(self._state.tool_outputs) > self._config.max_history:
            self._state.tool_outputs = self._state.tool_outputs[-self._config.max_history :]
        logger.debug("TUI tool output added: tool=%s, total=%d", tool_name, len(self._state.tool_outputs))

    def switch_panel(self, panel: TUIPanel) -> None:
        """Switch the active panel."""
        self._state.active_panel = panel
        logger.debug("TUI panel switched to %s", panel.value)

    def clear(self) -> None:
        """Clear messages and tool outputs from the current state."""
        self._state.messages.clear()
        self._state.tool_outputs.clear()
        logger.debug("TUI state cleared")
