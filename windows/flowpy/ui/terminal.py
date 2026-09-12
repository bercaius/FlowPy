"""Terminal — embedded terminal with QProcess output."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.runner import Runner

logger = logging.getLogger(__name__)


class Terminal(QWidget):
    """Embedded terminal for running scripts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.runner = Runner()
        self.runner.line.connect(self._append)
        self.runner.started.connect(lambda: self._append("[Started]"))
        self.runner.finished.connect(lambda c: self._append(f"[Finished] exit={c}"))
        self._cwd = Path.cwd()
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.output = QPlainTextEdit()
        self.output.setObjectName("Terminal")
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Komut girin (Enter ile gönder)…")
        self.input.returnPressed.connect(self._send)
        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.setObjectName("Flat")
        self.clear_btn.clicked.connect(self.output.clear)
        row.addWidget(self.input, 1)
        row.addWidget(self.clear_btn)
        layout.addLayout(row)

    def set_cwd(self, path: Path) -> None:
        self._cwd = path

    def run_file(self, path: Path) -> None:
        self._append(f">> {path.name}")
        self.runner.run_file(path, self._cwd)

    def run_code(self, code: str) -> None:
        self._append(">> (untitled)")
        self.runner.run_code(code, self._cwd)

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self._append(f">> {text}")
        self.runner.write(text + "\n")
        self.input.clear()

    def _append(self, text: str) -> None:
        self.output.appendPlainText(text)

    def stop(self) -> None:
        self.runner.stop()
        self._append("[Stopped]")
