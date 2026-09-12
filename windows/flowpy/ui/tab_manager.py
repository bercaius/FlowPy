"""Tab manager — multi-file editor with tabs."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QTabWidget,
    QWidget,
)

logger = logging.getLogger(__name__)


class TabManager(QTabWidget):
    """Multi-file editor with tab support."""

    currentPathChanged = Signal(str)
    fileSaved = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self._on_close)
        self.currentChanged.connect(self._on_changed)

    def open_file(self, path: Path) -> None:
        path = Path(path)
        if not path.exists():
            return
        for i in range(self.count()):
            w = self.widget(i)
            if getattr(w, "_file_path", None) == path:
                self.setCurrentIndex(i)
                return
        editor = QPlainTextEdit()
        editor._file_path = path  # type: ignore[attr-defined]
        try:
            editor.setPlainText(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Failed to read %s: %s", path, exc)
            editor.setPlainText("")
        idx = self.addTab(editor, path.name)
        self.setCurrentIndex(idx)
        self.currentPathChanged.emit(str(path))

    def open_code(self, code: str, title: str = "untitled.py") -> None:
        """Kaydedilmemiş bir Python tamponu açar (köprüden gelen kod)."""
        for i in range(self.count()):
            w = self.widget(i)
            if getattr(w, "_file_path", None) is None and getattr(w, "_untitled", False):
                w.setPlainText(code)
                self.setCurrentIndex(i)
                return
        editor = QPlainTextEdit()
        editor._file_path = None  # type: ignore[attr-defined]
        editor._untitled = True  # type: ignore[attr-defined]
        editor.setPlainText(code)
        idx = self.addTab(editor, title)
        self.setCurrentIndex(idx)
        self.currentPathChanged.emit("")

    def save_current(self) -> None:
        editor = self.current_editor()
        if editor is None:
            return
        path = getattr(editor, "_file_path", None)
        if path is None:
            return
        try:
            path.write_text(editor.toPlainText(), encoding="utf-8")
            self.fileSaved.emit(path)
        except Exception as exc:
            logger.error("Failed to save %s: %s", path, exc)

    def current_editor(self) -> QPlainTextEdit | None:
        w = self.currentWidget()
        return w if isinstance(w, QPlainTextEdit) else None

    def current_path(self) -> str:
        editor = self.current_editor()
        if editor is None:
            return ""
        return str(getattr(editor, "_file_path", ""))

    def _on_close(self, idx: int) -> None:
        self.removeTab(idx)

    def _on_changed(self, idx: int) -> None:
        editor = self.current_editor()
        path = ""
        if editor is not None:
            path = str(getattr(editor, "_file_path", ""))
        self.currentPathChanged.emit(path)
