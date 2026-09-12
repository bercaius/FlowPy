"""Custom title bar — clean modern design."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ..resources.icons import icon


class TitleBar(QWidget):
    """Clean modern title bar with search and theme toggle."""

    searchChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(42)
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(12)

        # Logo
        self.title_label = QLabel("FlowPy")
        self.title_label.setObjectName("AppTitle")
        layout.addWidget(self.title_label)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("Ara...")
        self.search_input.setFixedHeight(30)
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self.searchChanged)
        layout.addWidget(self.search_input)

        layout.addStretch(1)

        # Theme toggle
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("TitleBtn")
        self.theme_btn.setIcon(icon("sun", "#ffffff", 14))
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setToolTip("Tema değiştir")
        layout.addWidget(self.theme_btn)

        # Window controls
        for name, obj in (
            ("minimize", "TitleBtn"),
            ("maximize", "TitleBtn"),
            ("close", "CloseBtn"),
        ):
            b = QPushButton()
            b.setObjectName(obj)
            ic = icon(name, "#ffffff", 14)
            if not ic.isNull():
                b.setIcon(ic)
            b.setIconSize(QSize(14, 14))
            b.setFixedSize(36, 36)
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
