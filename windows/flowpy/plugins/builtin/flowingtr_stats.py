"""Builtin plugin: FlowingTR parameter statistics tracker."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flowpy.plugins.base import BasePlugin

if TYPE_CHECKING:
    from flowpy.app import FlowPyWindow

logger = logging.getLogger(__name__)


class FlowingtrStatsPlugin(BasePlugin):
    """Track flowingtr converter parameter statistics."""

    DISPLAY_NAME = "FlowingTR Stats"

    def __init__(self, window: FlowPyWindow) -> None:
        super().__init__(window)
        self._stats: dict[str, int] = {}

    def on_activate(self) -> None:
        logger.info("FlowingtrStatsPlugin activated")
        if self.window is not None:
            self.window.status_bar.showMessage("FlowingTR Stats active", 3000)

    def on_deactivate(self) -> None:
        logger.info("FlowingtrStatsPlugin deactivated")

    def record_parameter(self, name: str) -> None:
        """Record a parameter usage event."""
        self._stats[name] = self._stats.get(name, 0) + 1

    def get_stats(self) -> dict[str, int]:
        """Return parameter usage statistics."""
        return dict(self._stats)
