"""Custom title bar — frameless window with min/max/close buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ..resources.icons import icon


class TitleBar(QWidget):
    """Custom frameless window title bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(42)
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(0)

        self.title_label = QLabel("FlowPy")
        self.title_label.setObjectName("AppTitle")
        layout.addWidget(self.title_label)
        layout.addStretch(1)

        for name, slot, obj in (
            ("minimize", None, "TitleBtn"),
            ("maximize", None, "TitleBtn"),
            ("close", None, "CloseBtn"),
        ):
            b = QPushButton()
            b.setObjectName(obj)
            b.setIcon(icon(name, "#c9d1d9", 14))
            b.setFixedSize(38, 38)
            b.setCursor(Qt.PointingHandCursor)
            layout.addWidget(b)

        self.min_btn = layout.itemAt(layout.count() - 3).widget()
        self.max_btn = layout.itemAt(layout.count() - 2).widget()
        self.close_btn = layout.itemAt(layout.count() - 1).widget()

        self.min_btn.clicked.connect(self.parent().showMinimized if self.parent() else None)
        self.max_btn.clicked.connect(self._toggle_max)
        self.close_btn.clicked.connect(self.parent().close if self.parent() else None)

    def _toggle_max(self) -> None:
        parent = self.parent()
        if parent is None:
            return
        if parent.isMaximized():
            parent.showNormal()
        else:
            parent.showMaximized()

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)
