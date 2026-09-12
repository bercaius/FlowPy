"""Sidebar — left navigation with icon buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..resources.icons import icon


class SideBar(QWidget):
    """Left sidebar navigation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SideBar")
        self.buttons: list[QPushButton] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        items = [
            ("workspace", "Çalışma Alanı", 0),
            ("projects", "Projeler", 1),
            ("files", "Dosyalar", 2),
            ("settings", "Ayarlar", 3),
        ]

        for name, tooltip, idx in items:
            b = QPushButton()
            b.setObjectName("NavBtn")
            b.setIcon(icon(name, "#8b949e", 22))
            b.setToolTip(tooltip)
            b.setFixedSize(56, 48)
            b.setCursor(Qt.PointingHandCursor)
            layout.addWidget(b)
            self.buttons.append(b)

        layout.addStretch(1)

    def set_active(self, idx: int) -> None:
        for i, b in enumerate(self.buttons):
            b.setProperty("active", "true" if i == idx else "false")
            b.setStyle(b.style())
