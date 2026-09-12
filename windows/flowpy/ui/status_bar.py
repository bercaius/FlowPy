"""Status bar — professional status with compile indicator."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar


class StatusBar(QStatusBar):
    """Professional status bar with compile status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ready = QLabel("Hazır")
        self._ready.setObjectName("Stat")
        self._compile = QLabel("✓ Hazır")
        self._compile.setObjectName("CompileStatus")
        self._errors = QLabel("Hatalar: 0")
        self._warnings = QLabel("Uyarılar: 0")
        self._nodes = QLabel("Düğümler: 0")
        self._lines = QLabel("Satır: 1")
        self._col = QLabel("Sütun: 1")
        self._lang = QLabel("Python")

        self.addPermanentWidget(self._ready, 0)
        self.addPermanentWidget(self._compile, 0)
        for w in (self._errors, self._warnings, self._nodes,
                  self._lines, self._col, self._lang):
            self.addPermanentWidget(w, 0)

    def set_ready(self, text: str = "Hazır") -> None:
        self._ready.setText(text)

    def set_compile_status(self, status: str = "ready") -> None:
        """Set compile status indicator.
        
        Args:
            status: "ready", "compiling", "error", "warning"
        """
        if status == "ready":
            self._compile.setText("[OK] Hazır")
            self._compile.setProperty("error", "false")
            self._compile.setProperty("warning", "false")
        elif status == "compiling":
            self._compile.setText("[...] Derleniyor...")
            self._compile.setProperty("error", "false")
            self._compile.setProperty("warning", "false")
        elif status == "error":
            self._compile.setText("[ERR] Hata")
            self._compile.setProperty("error", "true")
            self._compile.setProperty("warning", "false")
        elif status == "warning":
            self._compile.setText("[WARN] Uyarı")
            self._compile.setProperty("error", "false")
            self._compile.setProperty("warning", "true")
        self._compile.style().unpolish(self._compile)
        self._compile.style().polish(self._compile)

    def set_stats(self, errors: int = 0, warnings: int = 0, nodes: int = 0, lines: int = 0) -> None:
        self._errors.setText(f"Hatalar: {errors}")
        self._warnings.setText(f"Uyarılar: {warnings}")
        self._nodes.setText(f"Düğümler: {nodes}")
        if lines:
            self._lines.setText(f"Satır: {lines}")

    def set_cursor(self, line: int, col: int) -> None:
        self._lines.setText(f"Satır: {line}")
        self._col.setText(f"Sütun: {col}")

    def set_language(self, lang: str) -> None:
        self._lang.setText(lang.capitalize())

    def show_message(self, text: str, timeout: int = 3000) -> None:
        self.showMessage(text, timeout)
