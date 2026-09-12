"""Terminal — clean modern terminal with colored output."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
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
    """Clean modern terminal with colored output."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.runner = Runner()
        self.runner.line.connect(self._append)
        self.runner.started.connect(lambda: self._append("[Başlatıldı]", "system"))
        self.runner.finished.connect(lambda c: self._append(f"[Bitti] çıkış={c}", "system"))
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
        self.input.setPlaceholderText("Komut girin...")
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
        self._append(f">> python {path.name}", "command")
        self.runner.run_file(path, self._cwd)

    def run_code(self, code: str) -> None:
        self._append(">> (kaydedilmemiş)", "command")
        self.runner.run_code(code, self._cwd)

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self._append(f">> {text}", "command")
        self.runner.write(text + "\n")
        self.input.clear()

    def _append(self, text: str, msg_type: str = "output") -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = QTextCharFormat()
        if msg_type == "command":
            fmt.setForeground(QColor("#f59e0b"))
        elif msg_type == "system":
            fmt.setForeground(QColor("#569cd6"))
        elif msg_type == "error":
            fmt.setForeground(QColor("#dc2626"))
        elif msg_type == "warning":
            fmt.setForeground(QColor("#d97706"))
        else:
            fmt.setForeground(QColor("#d4d4d4"))
        
        cursor.insertText(text + "\n", fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def stop(self) -> None:
        self.runner.stop()
        self._append("[Durduruldu]", "system")
