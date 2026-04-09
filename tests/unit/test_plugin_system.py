from __future__ import annotations

from agentic_core.application.services.plugin_system import (
    PluginManifest,
    PluginRegistry,
    PluginState,
)


def _make_manifest(name: str = "test-plugin", version: str = "1.0.0") -> PluginManifest:
    return PluginManifest(
        name=name,
        version=version,
        description="A test plugin",
        author="tester",
        entry_point="test_plugin.main",
        capabilities=["search"],
    )


def test_manifest_construction() -> None:
    m = _make_manifest()
    assert m.name == "test-plugin"
    assert m.version == "1.0.0"
    assert m.author == "tester"
    assert m.homepage is None
    assert m.dependencies == []
    assert m.entry_point == "test_plugin.main"
    assert m.capabilities == ["search"]


def test_manifest_frozen() -> None:
    m = _make_manifest()
    try:
        m.name = "other"  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except Exception:
        pass


def test_manifest_with_optional_fields() -> None:
    m = PluginManifest(
        name="full",
        version="2.0.0",
        description="Full plugin",
        author="author",
        homepage="https://example.com",
        dependencies=["dep-a", "dep-b"],
        entry_point="full.main",
        capabilities=["read", "write"],
    )
    assert m.homepage == "https://example.com"
    assert len(m.dependencies) == 2


def test_register_plugin() -> None:
    registry = PluginRegistry()
    plugin = registry.register(_make_manifest())
    assert plugin.state == PluginState.INSTALLED
    assert plugin.manifest.name == "test-plugin"
    assert plugin.installed_at is not None
    assert plugin.error is None
    assert plugin.config == {}


def test_activate_plugin() -> None:
    registry = PluginRegistry()
    registry.register(_make_manifest())
    result = registry.activate("test-plugin")
    assert result is True
    plugin = registry.get("test-plugin")
    assert plugin is not None
    assert plugin.state == PluginState.ACTIVE


def test_deactivate_plugin() -> None:
    registry = PluginRegistry()
    registry.register(_make_manifest())
    registry.activate("test-plugin")
    result = registry.deactivate("test-plugin")
    assert result is True
    plugin = registry.get("test-plugin")
    assert plugin is not None
    assert plugin.state == PluginState.INACTIVE


def test_reactivate_after_deactivate() -> None:
    registry = PluginRegistry()
    registry.register(_make_manifest())
    registry.activate("test-plugin")
    registry.deactivate("test-plugin")
    result = registry.activate("test-plugin")
    assert result is True
    plugin = registry.get("test-plugin")
    assert plugin is not None
    assert plugin.state == PluginState.ACTIVE


def test_unregister_plugin() -> None:
    registry = PluginRegistry()
    registry.register(_make_manifest())
    result = registry.unregister("test-plugin")
    assert result is True
    assert registry.get("test-plugin") is None


def test_unregister_unknown_returns_false() -> None:
    registry = PluginRegistry()
    assert registry.unregister("nonexistent") is False


def test_get_unknown_returns_none() -> None:
    registry = PluginRegistry()
    assert registry.get("nonexistent") is None


def test_activate_unknown_returns_false() -> None:
    registry = PluginRegistry()
    assert registry.activate("nonexistent") is False


def test_deactivate_non_active_returns_false() -> None:
    registry = PluginRegistry()
    registry.register(_make_manifest())
    # Plugin is INSTALLED, not ACTIVE
    assert registry.deactivate("test-plugin") is False


def test_list_plugins_all() -> None:
    registry = PluginRegistry()
    registry.register(_make_manifest("a"))
    registry.register(_make_manifest("b"))
    registry.register(_make_manifest("c"))
    assert len(registry.list_plugins()) == 3


def test_list_plugins_by_state() -> None:
    registry = PluginRegistry()
    registry.register(_make_manifest("a"))
    registry.register(_make_manifest("b"))
    registry.activate("a")
    assert len(registry.list_plugins(state=PluginState.ACTIVE)) == 1
    assert len(registry.list_plugins(state=PluginState.INSTALLED)) == 1


def test_discover_placeholder() -> None:
    registry = PluginRegistry()
    result = registry.discover("/some/directory")
    assert result == []
