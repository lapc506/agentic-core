from __future__ import annotations

from agentic_core.adapters.primary.tui import (
    DEFAULT_KEYBINDINGS,
    TUIAdapter,
    TUIConfig,
    TUIKeyBinding,
    TUIPanel,
    TUIState,
)

# ── Panel enum ──────────────────────────────────────────────────


def test_tui_panel_values() -> None:
    assert TUIPanel.CONVERSATION.value == "conversation"
    assert TUIPanel.TOOLS.value == "tools"
    assert TUIPanel.STATUS.value == "status"
    assert TUIPanel.SESSIONS.value == "sessions"


# ── TUIConfig ───────────────────────────────────────────────────


def test_tui_config_defaults() -> None:
    cfg = TUIConfig()
    assert TUIPanel.CONVERSATION in cfg.show_panels
    assert TUIPanel.TOOLS in cfg.show_panels
    assert TUIPanel.STATUS in cfg.show_panels
    assert cfg.show_timestamps is True
    assert cfg.max_history == 1000
    assert cfg.theme == "default"


def test_tui_config_custom() -> None:
    cfg = TUIConfig(
        show_panels=[TUIPanel.CONVERSATION],
        show_timestamps=False,
        max_history=50,
        theme="dark",
    )
    assert cfg.show_panels == [TUIPanel.CONVERSATION]
    assert cfg.show_timestamps is False
    assert cfg.max_history == 50
    assert cfg.theme == "dark"


# ── TUIKeyBinding ───────────────────────────────────────────────


def test_keybinding_frozen() -> None:
    kb = TUIKeyBinding(key="ctrl+c", action="quit", description="Quit")
    try:
        kb.key = "ctrl+q"  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised, "TUIKeyBinding should be frozen"


def test_default_keybindings_count() -> None:
    assert len(DEFAULT_KEYBINDINGS) == 6


def test_default_keybindings_actions() -> None:
    actions = {kb.action for kb in DEFAULT_KEYBINDINGS}
    assert actions == {"quit", "new_session", "switch_panel", "scroll_up", "scroll_down", "clear"}


# ── TUIState ────────────────────────────────────────────────────


def test_tui_state_defaults() -> None:
    state = TUIState()
    assert state.active_panel == TUIPanel.CONVERSATION
    assert state.session_id is None
    assert state.messages == []
    assert state.tool_outputs == []


# ── TUIAdapter ──────────────────────────────────────────────────


def test_adapter_default_config() -> None:
    adapter = TUIAdapter()
    assert adapter.config.theme == "default"


def test_adapter_get_state_returns_copy() -> None:
    adapter = TUIAdapter()
    s1 = adapter.get_state()
    s2 = adapter.get_state()
    assert s1.session_id == s2.session_id
    s1.messages.append("mutate")
    assert "mutate" not in adapter.get_state().messages


def test_adapter_add_message() -> None:
    adapter = TUIAdapter()
    adapter.add_message("user", "Hello")
    adapter.add_message("assistant", "Hi there")
    state = adapter.get_state()
    assert len(state.messages) == 2
    assert "[user] Hello" in state.messages[0]
    assert "[assistant] Hi there" in state.messages[1]


def test_adapter_add_tool_output() -> None:
    adapter = TUIAdapter()
    adapter.add_tool_output("search", "3 results found")
    state = adapter.get_state()
    assert len(state.tool_outputs) == 1
    assert "[search] 3 results found" in state.tool_outputs[0]


def test_adapter_switch_panel() -> None:
    adapter = TUIAdapter()
    assert adapter.get_state().active_panel == TUIPanel.CONVERSATION
    adapter.switch_panel(TUIPanel.TOOLS)
    assert adapter.get_state().active_panel == TUIPanel.TOOLS


def test_adapter_clear() -> None:
    adapter = TUIAdapter()
    adapter.add_message("user", "msg1")
    adapter.add_tool_output("tool", "out1")
    adapter.clear()
    state = adapter.get_state()
    assert state.messages == []
    assert state.tool_outputs == []


def test_adapter_max_history_truncation() -> None:
    cfg = TUIConfig(max_history=3)
    adapter = TUIAdapter(config=cfg)
    for i in range(5):
        adapter.add_message("user", f"msg{i}")
    state = adapter.get_state()
    assert len(state.messages) == 3
    assert "[user] msg2" in state.messages[0]
    assert "[user] msg4" in state.messages[2]


def test_adapter_max_history_truncation_tool_outputs() -> None:
    cfg = TUIConfig(max_history=2)
    adapter = TUIAdapter(config=cfg)
    for i in range(4):
        adapter.add_tool_output("t", f"out{i}")
    state = adapter.get_state()
    assert len(state.tool_outputs) == 2
    assert "[t] out2" in state.tool_outputs[0]
    assert "[t] out3" in state.tool_outputs[1]


def test_adapter_keybindings_property() -> None:
    adapter = TUIAdapter()
    kbs = adapter.keybindings
    assert len(kbs) == 6
    # Modifying the returned list should not affect the adapter
    kbs.pop()
    assert len(adapter.keybindings) == 6
