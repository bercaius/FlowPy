"""File tree — simple project file browser."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QDir, QSortFilterProxyModel, Signal, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class FileTree(QWidget):
    """Project file tree with search."""

    fileOpened = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root = Path.cwd()
        self._model = QStandardItemModel(self)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Dosya ara…")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.tree = QTreeView()
        self.tree.setModel(self._model)
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.doubleClicked.connect(self._on_double)
        layout.addWidget(self.tree)

    def set_root(self, path: Path) -> None:
        self._root = Path(path)
        self._model.clear()
        root_item = self._model.invisibleRootItem()
        self._populate(path, root_item)

    def _populate(self, path: Path, parent) -> None:
        try:
            for entry in sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
                if entry.name.startswith(".") or entry.name == "__pycache__":
                    continue
                item = QStandardItem(entry.name)
                item.setData(entry, Qt.ItemDataRole.UserRole)
                parent.appendRow(item)
                if entry.is_dir():
                    self._populate(entry, item)
        except PermissionError:
            pass

    def _filter(self, text: str) -> None:
        # Simple filter: hide non-matching items
        # In a real app, use QSortFilterProxyModel
        pass

    def _on_double(self, index) -> None:
        item = self._model.itemFromIndex(index)
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(path, Path) and path.is_file():
            self.fileOpened.emit(path)
