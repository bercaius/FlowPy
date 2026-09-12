"""Crash reporter dialog — shown after unhandled exceptions."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class CrashReporterDialog(QDialog):
    """Crash reporter dialog."""

    def __init__(self, parent: QWidget | None = None, exc_text: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Beklenmeyen Hata")
        self.setModal(True)
        self.resize(520, 340)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "<h2 style='color:#f85149'>Beklenmeyen Hata</h2>"
            "<p>FlowPy beklenmeyen bir hata ile karşılaştı ve kapanmak zorunda kalıyor.</p>"
            "<p>Hata detayları aşağıda listelenmiştir.</p>"
        ))

        details = QTextEdit()
        details.setReadOnly(True)
        details.setStyleSheet("font-family:Consolas,Monaco,monospace;font-size:11px;")
        details.setText(exc_text[-3000:] if len(exc_text) > 3000 else exc_text)
        layout.addWidget(details)

        log_path = Path.home() / "AppData" / "Roaming" / "TurcoDevelopStudio" / "FlowPy" / "logs" / "flowpy.log"
        layout.addWidget(QLabel(
            f"<span style='color:#8b949e'>Log: {log_path}</span>"
        ))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)
