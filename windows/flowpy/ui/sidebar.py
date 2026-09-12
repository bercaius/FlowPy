"""Sidebar — minimal modern navigation."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..resources.icons import icon


class SideBar(QWidget):
    """Minimal modern sidebar navigation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SideBar")
        self.buttons: list[QPushButton] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(6)

        items = [
            ("workspace", "Çalışma Alanı", 0),
            ("projects", "Projeler", 1),
            ("files", "Dosyalar", 2),
            ("settings", "Ayarlar", 3),
        ]

        for name, tooltip, idx in items:
            btn = QPushButton()
            btn.setObjectName("NavBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setProperty("navIndex", str(idx))

            ic = icon(name, "#cccccc", 20)
            if not ic.isNull():
                btn.setIcon(ic)
                btn.setIconSize(QSize(20, 20))

            lbl = QLabel(tooltip)
            lbl.setObjectName("NavLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            inner = QVBoxLayout()
            inner.setContentsMargins(0, 0, 0, 0)
            inner.setSpacing(2)
            inner.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            inner.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)

            layout.addLayout(inner)
            self.buttons.append(btn)

        layout.addStretch(1)

    def set_active(self, idx: int) -> None:
        for i, b in enumerate(self.buttons):
            b.setProperty("active", "true" if i == idx else "false")
            b.style().unpolish(b)
            b.style().polish(b)
