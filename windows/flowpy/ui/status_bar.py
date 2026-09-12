"""Status bar — bottom info bar with stats and language."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar


class StatusBar(QStatusBar):
    """Professional status bar with stats and info."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ready = QLabel("Ready")
        self._ready.setObjectName("Stat")
        self._errors = QLabel("Errors: 0")
        self._warnings = QLabel("Warnings: 0")
        self._nodes = QLabel("Nodes: 0")
        self._lines = QLabel("Ln: 1")
        self._col = QLabel("Col: 1")
        self._lang = QLabel("Python")

        self.addPermanentWidget(self._ready, 0)
        for w in (self._errors, self._warnings, self._nodes,
                  self._lines, self._col, self._lang):
            self.addPermanentWidget(w, 0)

    def set_ready(self, text: str = "Ready") -> None:
        self._ready.setText(text)

    def set_stats(self, errors: int = 0, warnings: int = 0, nodes: int = 0, lines: int = 0) -> None:
        self._errors.setText(f"Errors: {errors}")
        self._warnings.setText(f"Warnings: {warnings}")
        self._nodes.setText(f"Nodes: {nodes}")
        if lines:
            self._lines.setText(f"Ln: {lines}")

    def set_cursor(self, line: int, col: int) -> None:
        self._lines.setText(f"Ln: {line}")
        self._col.setText(f"Col: {col}")

    def set_language(self, lang: str) -> None:
        self._lang.setText(lang.capitalize())

    def show_message(self, text: str, timeout: int = 3000) -> None:
        self.showMessage(text, timeout)
