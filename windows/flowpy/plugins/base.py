"""Base plugin class for FlowPy.

Pattern: angr-management BasePlugin
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flowpy.app import FlowPyWindow


class BasePlugin:
    """Base class for all FlowPy plugins."""

    DISPLAY_NAME: str | None = None
    __i_hold_this_abstraction_token = True

    def __init__(self, window: FlowPyWindow) -> None:
        self.window: FlowPyWindow | None = window

    @classmethod
    def get_display_name(cls) -> str:
        display_name = getattr(cls, "DISPLAY_NAME", None)
        if display_name:
            return display_name
        return cls.__name__

    def on_activate(self) -> None:
        """Called when the plugin is activated."""
        pass

    def on_deactivate(self) -> None:
        """Called when the plugin is deactivated."""
        pass

    def get_toolbar_buttons(self) -> list[tuple[str, str]]:
        """Return list of (icon_path, tooltip) for toolbar buttons."""
        return []

    def get_menu_buttons(self) -> list[str]:
        """Return list of menu button labels."""
        return []
