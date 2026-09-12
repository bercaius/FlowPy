"""Tab manager — multi-file editor with tabs, line numbers, and syntax highlighting."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QRect, QSize, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QTextCursor,
    QTextFormat,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
    QPlainTextEdit,
    QTabWidget,
    QTextEdit,
    QWidget,
)

logger = logging.getLogger(__name__)


class _PythonHighlighter(QSyntaxHighlighter):
    """Minimal Python syntax highlighter."""

    KEYWORDS = {
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else", "except",
        "finally", "for", "from", "global", "if", "import", "in", "is",
        "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
        "try", "while", "with", "yield",
    }

    def __init__(self, doc: QTextDocument) -> None:
        super().__init__(doc)
        self._keyword_fmt = QTextCharFormat()
        self._keyword_fmt.setForeground(QColor("#569cd6"))
        self._keyword_fmt.setFontWeight(QFont.Weight.Bold)

        self._string_fmt = QTextCharFormat()
        self._string_fmt.setForeground(QColor("#ce9178"))

        self._comment_fmt = QTextCharFormat()
        self._comment_fmt.setForeground(QColor("#6a9955"))

        self._number_fmt = QTextCharFormat()
        self._number_fmt.setForeground(QColor("#b5cea8"))

        self._decorator_fmt = QTextCharFormat()
        self._decorator_fmt.setForeground(QColor("#dcdcaa"))

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        self._highlight_keywords(text)
        self._highlight_strings(text)
        self._highlight_comments(text)
        self._highlight_numbers(text)
        self._highlight_decorators(text)

    def _highlight_keywords(self, text: str) -> None:
        for word in self.KEYWORDS:
            idx = 0
            while True:
                i = text.find(word, idx)
                if i < 0:
                    break
                end = i + len(word)
                if (i == 0 or not text[i - 1].isalnum() and text[i - 1] != "_") and (
                    end >= len(text) or not text[end].isalnum() and text[end] != "_"
                ):
                    self.setFormat(i, len(word), self._keyword_fmt)
                idx = end

    def _highlight_strings(self, text: str) -> None:
        i = 0
        while i < len(text):
            if text[i] in ('"', "'"):
                quote = text[i]
                j = i + 1
                while j < len(text) and text[j] != quote:
                    if text[j] == "\\":
                        j += 1
                    j += 1
                if j < len(text):
                    self.setFormat(i, j - i + 1, self._string_fmt)
                    i = j + 1
                    continue
            i += 1

    def _highlight_comments(self, text: str) -> None:
        i = text.find("#")
        if i >= 0:
            self.setFormat(i, len(text) - i, self._comment_fmt)

    def _highlight_numbers(self, text: str) -> None:
        i = 0
        while i < len(text):
            if text[i].isdigit():
                j = i
                while j < len(text) and (text[j].isdigit() or text[j] == "."):
                    j += 1
                self.setFormat(i, j - i, self._number_fmt)
                i = j
                continue
            i += 1

    def _highlight_decorators(self, text: str) -> None:
        i = text.find("@")
        if i >= 0:
            j = i + 1
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            self.setFormat(i, j - i, self._decorator_fmt)


class _LineNumberArea(QWidget):
    """Line number area for the code editor."""

    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#252526"))

        block = self._editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self._editor.blockBoundingGeometry(block).translated(self._editor.contentOffset()).top()
        bottom = top + self._editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = block_number + 1
                painter.setPen(QColor("#858585"))
                painter.setFont(QFont("Consolas", 10))
                painter.drawText(
                    0, int(top), self.width() - 4, self._editor.fontMetrics().height(),
                    Qt.AlignRight, str(number)
                )
            block = block.next()
            top = bottom
            bottom = top + self._editor.blockBoundingRect(block).height()
            block_number += 1


class CodeEditor(QPlainTextEdit):
    """Professional code editor with line numbers and syntax highlighting."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._file_path: Path | None = None
        self._untitled: bool = False
        self._dirty: bool = False
        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.textChanged.connect(self._on_text_changed)
        self._update_line_number_area_width(0)
        self._highlight_current_line()

        self._highlighter = _PythonHighlighter(self.document())

        self.setFont(QFont("Consolas", 14))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(4 * QFontMetrics(self.font()).horizontalAdvance(' '))

    def _on_text_changed(self) -> None:
        if not self._dirty:
            self._dirty = True
            self._update_tab_title()

    def _update_tab_title(self) -> None:
        tab_widget = self.parent()
        while tab_widget is not None and not isinstance(tab_widget, QTabWidget):
            tab_widget = tab_widget.parent()
        if tab_widget is None:
            return
        for i in range(tab_widget.count()):
            if tab_widget.widget(i) is self:
                base = self._file_path.name if self._file_path else (self._untitled and "untitled.py" or "Document")
                tab_widget.setTabText(i, f"*{base}" if self._dirty else base)
                break

    def line_number_width(self) -> int:
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val /= 10
            digits += 1
        return 3 + self.fontMetrics().horizontalAdvance('9') * digits

    def _update_line_number_area_width(self, _) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_width(), cr.height())
        )

    def _highlight_current_line(self) -> None:
        extra = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2d2d2d")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra.append(selection)
        self.setExtraSelections(extra)

    def language_for_suffix(self, suffix: str) -> str:
        return "Python" if suffix == ".py" else "Text"

    def highlight_source_line(self, line: int) -> None:
        if line <= 0:
            return
        doc = self.document()
        block = doc.findBlockByNumber(line - 1)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def is_dirty(self) -> bool:
        return self._dirty

    def mark_saved(self) -> None:
        self._dirty = False
        self._update_tab_title()


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
        editor = CodeEditor()
        editor._file_path = path
        editor._untitled = False
        try:
            editor.setPlainText(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Failed to read %s: %s", path, exc)
            editor.setPlainText("")
        idx = self.addTab(editor, path.name)
        self.setCurrentIndex(idx)
        self.currentPathChanged.emit(str(path))

    def open_code(self, code: str, title: str = "untitled.py") -> None:
        editor = CodeEditor()
        editor._file_path = None
        editor._untitled = True
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
            editor.mark_saved()
            self.fileSaved.emit(path)
        except Exception as exc:
            logger.error("Failed to save %s: %s", path, exc)

    def current_editor(self) -> CodeEditor | None:
        w = self.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def current_path(self) -> str:
        editor = self.current_editor()
        if editor is None:
            return ""
        return str(getattr(editor, "_file_path", ""))

    def _on_close(self, idx: int) -> None:
        editor = self.widget(idx)
        if isinstance(editor, CodeEditor) and editor.is_dirty():
            r = QMessageBox.question(
                self,
                "Kaydedilmemiş Değişiklikler",
                "Bu sekmedeki değişiklikleri kaydetmek istiyor musunuz?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if r == QMessageBox.StandardButton.Save:
                path = getattr(editor, "_file_path", None)
                if path is not None:
                    try:
                        path.write_text(editor.toPlainText(), encoding="utf-8")
                        self.fileSaved.emit(path)
                    except Exception as exc:
                        logger.error("Failed to save %s: %s", path, exc)
                elif editor.toPlainText().strip():
                    self.save_current()
            elif r == QMessageBox.StandardButton.Cancel:
                return
        self.removeTab(idx)

    def _on_changed(self, idx: int) -> None:
        editor = self.current_editor()
        path = ""
        if editor is not None:
            path = str(getattr(editor, "_file_path", ""))
        self.currentPathChanged.emit(path)
