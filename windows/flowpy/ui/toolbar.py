"""Toolbar — top action bar with buttons."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from ..resources.icons import icon


class ToolBar(QWidget):
    """Top toolbar with action buttons."""

    newProject = Signal()
    openProject = Signal()
    save = Signal()
    run = Signal()
    stop = Signal()
    sync = Signal()
    export = Signal()
    plugins = Signal()
    more = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ToolBar")
        self.setFixedHeight(44)
        self._build()

    def _btn(self, name: str, tip: str, obj: str = "ToolBtn", primary: bool = False) -> QPushButton:
        b = QPushButton()
        b.setObjectName("PrimaryBtn" if primary else obj)
        b.setIcon(icon(name, "#f0f6fc" if primary else "#c9d1d9", 18))
        b.setText(tip)
        b.setFixedHeight(34)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        return b

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self.btn_new = self._btn("new", "Yeni Proje", "PrimaryBtn", True)
        self.btn_open = self._btn("open", "Proje Aç")
        self.btn_save = self._btn("save", "Kaydet")
        self.btn_run = self._btn("run", "Çalıştır", "RunBtn", True)
        self.btn_stop = self._btn("stop", "Durdur")
        self.btn_sync = self._btn("sync", "Akış Şeması", "PrimaryBtn", True)
        self.btn_export = self._btn("export", "Dışa Aktar")
        self.btn_plugins = self._btn("plugins", "Eklentiler")
        self.btn_more = self._btn("more", "Hakkında")

        self.btn_new.clicked.connect(self.newProject.emit)
        self.btn_open.clicked.connect(self.openProject.emit)
        self.btn_save.clicked.connect(self.save.emit)
        self.btn_run.clicked.connect(self.run.emit)
        self.btn_stop.clicked.connect(self.stop.emit)
        self.btn_sync.clicked.connect(self.sync.emit)
        self.btn_export.clicked.connect(self.export.emit)
        self.btn_plugins.clicked.connect(self.plugins.emit)
        self.btn_more.clicked.connect(self.more.emit)

        for b in (
            self.btn_new, self.btn_open, self.btn_save, self.btn_run,
            self.btn_stop, self.btn_sync, self.btn_export,
            self.btn_plugins, self.btn_more,
        ):
            layout.addWidget(b)
        layout.addStretch(1)
