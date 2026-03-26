from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PluginManifest(BaseModel, frozen=True):
    """Formal plugin manifest, typically loaded from a plugin.json file."""

    name: str
    version: str
    description: str
    author: str
    homepage: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    entry_point: str
    capabilities: list[str] = Field(default_factory=list)


class PluginState(Enum):
    """Lifecycle states for a plugin."""

    DISCOVERED = "discovered"
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class Plugin(BaseModel):
    """Runtime representation of a plugin with state tracking."""

    manifest: PluginManifest
    state: PluginState = PluginState.DISCOVERED
    config: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    installed_at: datetime | None = None


class PluginRegistry:
    """Registry for managing plugin lifecycle: register, activate, deactivate, discover."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, manifest: PluginManifest) -> Plugin:
        """Register a plugin from its manifest. Sets state to INSTALLED."""
        plugin = Plugin(
            manifest=manifest,
            state=PluginState.INSTALLED,
            installed_at=datetime.now(timezone.utc),
        )
        self._plugins[manifest.name] = plugin
        logger.info("Registered plugin: %s v%s", manifest.name, manifest.version)
        return plugin

    def activate(self, name: str) -> bool:
        """Activate an installed or inactive plugin. Returns True on success."""
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning("Cannot activate unknown plugin: %s", name)
            return False
        if plugin.state not in (PluginState.INSTALLED, PluginState.INACTIVE):
            logger.warning(
                "Cannot activate plugin %s in state %s", name, plugin.state.value,
            )
            return False
        plugin.state = PluginState.ACTIVE
        logger.info("Activated plugin: %s", name)
        return True

    def deactivate(self, name: str) -> bool:
        """Deactivate an active plugin. Returns True on success."""
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning("Cannot deactivate unknown plugin: %s", name)
            return False
        if plugin.state != PluginState.ACTIVE:
            logger.warning(
                "Cannot deactivate plugin %s in state %s", name, plugin.state.value,
            )
            return False
        plugin.state = PluginState.INACTIVE
        logger.info("Deactivated plugin: %s", name)
        return True

    def unregister(self, name: str) -> bool:
        """Remove a plugin from the registry. Returns True if it existed."""
        if name not in self._plugins:
            logger.warning("Cannot unregister unknown plugin: %s", name)
            return False
        del self._plugins[name]
        logger.info("Unregistered plugin: %s", name)
        return True

    def get(self, name: str) -> Plugin | None:
        """Return a plugin by name, or None if not found."""
        return self._plugins.get(name)

    def list_plugins(self, state: PluginState | None = None) -> list[Plugin]:
        """List all plugins, optionally filtered by state."""
        plugins = list(self._plugins.values())
        if state is not None:
            plugins = [p for p in plugins if p.state == state]
        return plugins

    def discover(self, directory: str) -> list[PluginManifest]:
        """Scan a directory for plugin.json manifest files.

        Placeholder implementation: logs the directory and returns empty list.
        Will be implemented with actual filesystem scanning in a future release.
        """
        logger.info("Discovering plugins in: %s (placeholder)", directory)
        return []
