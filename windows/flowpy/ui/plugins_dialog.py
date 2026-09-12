"""Plugins management dialog — professional plugin activation UI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from flowpy.core.services import Services

logger = logging.getLogger(__name__)


class PluginsDialog(QDialog):
    """Professional plugin management dialog."""

    def __init__(self, services: "Services", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Eklentiler")
        self.setModal(True)
        self.resize(640, 420)
        self.services = services
        self._manager = getattr(services, "manager", None)
        if self._manager is not None:
            try:
                self._manager.discover()
            except Exception as exc:  # noqa: BLE001
                log.warning("Plugin keşif hatası: %s", exc)
        self._build()

    @staticmethod
    def _display_name(cls) -> str:
        try:
            return cls.get_display_name()
        except Exception:  # noqa: BLE001
            return getattr(cls, "__name__", str(cls))

    def _build(self) -> None:
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(QLabel("<b>Kurulu Eklentiler</b>"))
        self._list = QListWidget()
        left.addWidget(self._list, 1)
        layout.addLayout(left, 1)

        self._detail = QWidget()
        self._detail_layout = QVBoxLayout(self._detail)
        self._detail_layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(self._detail, 2)

        self._populate()

    def _populate(self) -> None:
        self._list.clear()
        if self._manager is None:
            return
        for name, cls in sorted(getattr(self._manager, "loaded_plugins", {}).items()):
            item = QListWidgetItem(self._display_name(cls))
            active = name in getattr(self._manager, "active_plugins", {})
            item.setData(Qt.ItemDataRole.UserRole, (name, cls))
            if active:
                item.setForeground(Qt.GlobalColor.green)
            self._list.addItem(item)
        self._list.currentRowChanged.connect(self._on_select)

    def _on_select(self, row: int) -> None:
        item = self._list.item(row)
        if item is None:
            return
        name, cls = item.data(Qt.ItemDataRole.UserRole)

        # Clear detail panel
        while self._detail_layout.count():
            child = self._detail_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        title = QLabel(self._display_name(cls))
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#2f81f7;")
        self._detail_layout.addWidget(title)

        desc = QLabel(getattr(cls, "__doc__", "") or "Açıklama yok.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#8b949e;")
        self._detail_layout.addWidget(desc)

        active = name in getattr(self._manager, "active_plugins", {})
        btn = QPushButton("Deaktifleştir" if active else "Aktifleştir")
        btn.setObjectName("PrimaryBtn")
        btn.clicked.connect(lambda: self._toggle(name, btn))
        self._detail_layout.addWidget(btn)

        status = QLabel("<span style='color:#3fb950'>Aktif</span>" if active else "<span style='color:#8b949e'>Deaktif</span>")
        self._detail_layout.addWidget(status)
        self._detail_layout.addStretch(1)

    def _toggle(self, name: str, btn: QPushButton) -> None:
        if name in self._manager.active_plugins:
            self._manager.deactivate_plugin(name)
        else:
            ok = self._manager.activate_plugin(name)
            if not ok:
                QMessageBox.warning(self, "Hata", f"'{name}' aktifleştirilemedi.")
        self._populate()

    def closeEvent(self, event) -> None:
        self._populate()
        super().closeEvent(event)
