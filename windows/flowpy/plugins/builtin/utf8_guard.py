"""Builtin plugin: UTF-8 encoding guard."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flowpy.plugins.base import BasePlugin

if TYPE_CHECKING:
    from flowpy.app import FlowPyWindow

logger = logging.getLogger(__name__)


class Utf8GuardPlugin(BasePlugin):
    """Ensure UTF-8 encoding for all file operations."""

    DISPLAY_NAME = "UTF-8 Guard"

    def __init__(self, window: FlowPyWindow) -> None:
        super().__init__(window)
        self._enabled = True

    def on_activate(self) -> None:
        logger.info("Utf8GuardPlugin activated")
        if self.window is not None:
            self.window.status_bar.showMessage("UTF-8 Guard active", 3000)

    def on_deactivate(self) -> None:
        logger.info("Utf8GuardPlugin deactivated")

    def validate_encoding(self, filepath: str) -> bool:
        """Check if a file is valid UTF-8."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                f.read()
            return True
        except UnicodeDecodeError:
            logger.warning("Invalid UTF-8 file: %s", filepath)
            return False
