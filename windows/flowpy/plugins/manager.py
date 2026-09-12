"""Plugin manager — discovery, activation, deactivation lifecycle.

Pattern: angr-management PluginManager
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import BasePlugin
from .discovery import discover_plugins

if TYPE_CHECKING:
    from flowpy.app import FlowPyWindow

log = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin lifecycle."""

    def __init__(self, window: FlowPyWindow | None = None) -> None:
        self.window: FlowPyWindow | None = window
        self.loaded_plugins: dict[str, type] = {}
        self.active_plugins: dict[str, BasePlugin] = {}
        self.enabled_plugins: set[str] = set()

    def discover(self) -> dict[str, type]:
        """Discover all available plugins."""
        self.loaded_plugins = discover_plugins(self.window)
        return self.loaded_plugins

    def activate_plugin(self, name: str) -> bool:
        """Activate a plugin by name. Returns True on success."""
        if name in self.active_plugins:
            return True

        plugin_cls = self.loaded_plugins.get(name)
        if plugin_cls is None:
            log.warning("Plugin %r not found", name)
            return False

        if not issubclass(plugin_cls, BasePlugin):
            log.error("Cannot load plugin %r: not a BasePlugin subclass", name)
            return False

        try:
            plugin_obj = plugin_cls(self.window)
            plugin_obj.on_activate()
            self.active_plugins[name] = plugin_obj
            self.enabled_plugins.add(name)
            log.info("Activated plugin %s", plugin_cls.get_display_name())
            return True
        except Exception:
            log.warning("Plugin %r failed to activate:", name, exc_info=True)
            return False

    def deactivate_plugin(self, name: str) -> None:
        """Deactivate a plugin by name."""
        if name not in self.active_plugins:
            return

        plugin_obj = self.active_plugins.pop(name)
        self.enabled_plugins.discard(name)
        try:
            plugin_obj.on_deactivate()
        except Exception:
            log.warning("Plugin %r failed to deactivate:", name, exc_info=True)

    def discover_and_initialize(self) -> None:
        """Discover plugins and initialize based on user settings."""
        self.discover()

        if self.window is not None:
            settings = self.window.settings
            enabled_str = settings.value("plugins/enabled", "", type=str)
            if enabled_str:
                for name in enabled_str.split(","):
                    name = name.strip()
                    if name:
                        self.activate_plugin(name)

    def get_active_plugins(self) -> dict[str, BasePlugin]:
        """Return dict of name -> active plugin instance."""
        return self.active_plugins
