"""Toolbar — minimal modern action bar."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from ..resources.icons import icon


class ToolBar(QWidget):
    """Minimal modern toolbar with essential actions only."""

    newProject = Signal()
    openProject = Signal()
    save = Signal()
    run = Signal()
    stop = Signal()
    more = Signal()
    blockModeToggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ToolBar")
        self.setFixedHeight(44)
        self._build()

    def _btn(self, name: str, tip: str, obj: str = "ToolBtn", primary: bool = False) -> QPushButton:
        b = QPushButton()
        b.setObjectName("PrimaryBtn" if primary else obj)
        ic = icon(name, "#ffffff" if primary else "#cccccc", 16)
        if not ic.isNull():
            b.setIcon(ic)
            b.setIconSize(b.sizeHint())
        b.setText(tip)
        b.setFixedHeight(32)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        return b

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)

        self.btn_new = self._btn("new", "Yeni", "PrimaryBtn", True)
        self.btn_open = self._btn("open", "Aç")
        self.btn_save = self._btn("save", "Kaydet")
        self.btn_run = self._btn("run", "Çalıştır", "RunBtn", True)
        self.btn_stop = self._btn("stop", "Durdur")
        self.btn_more = self._btn("more", "Hakkında")
        self.btn_blocks = self._btn("code_to_flow", "Blok Editör")
        self.btn_blocks.setCheckable(True)

        self.btn_new.clicked.connect(self.newProject.emit)
        self.btn_open.clicked.connect(self.openProject.emit)
        self.btn_save.clicked.connect(self.save.emit)
        self.btn_run.clicked.connect(self.run.emit)
        self.btn_stop.clicked.connect(self.stop.emit)
        self.btn_more.clicked.connect(self.more.emit)
        self.btn_blocks.toggled.connect(self.blockModeToggled.emit)

        for b in (
            self.btn_new, self.btn_open, self.btn_save, self.btn_run,
            self.btn_stop, self.btn_more, self.btn_blocks,
        ):
            layout.addWidget(b)
        layout.addStretch(1)
