"""Settings form — professional settings UI with tabs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsForm(QFrame):
    """Professional settings form with tabbed interface."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Ayarlar")
        title.setStyleSheet("font-size:16px;font-weight:600;color:#f0f6fc;")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._general_tab(), "Genel")
        tabs.addTab(self._build_tab(), "Derleme")
        tabs.addTab(self._advanced_tab(), "Gelişmiş")
        layout.addWidget(tabs)

    def _general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.output_name = QLineEdit("FlowPy_App")
        form.addRow("Çıktı adı:", self.output_name)

        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("Simge yok")
        b = QPushButton("…")
        b.setObjectName("Flat")
        b.clicked.connect(lambda: self._pick_file(self.icon_edit, "Icon (*.ico)"))
        row = QHBoxLayout()
        row.addWidget(self.icon_edit, 1)
        row.addWidget(b)
        form.addRow("Simge:", row)

        return w

    def _build_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        self.onefile = QCheckBox("Tek dosya (--onefile)")
        self.onefile.setChecked(True)
        self.console = QCheckBox("Konsol penceresi (--console)")
        self.console.setChecked(True)
        self.clean = QCheckBox("Temiz derleme (--clean)")
        self.clean.setChecked(True)
        self.upx = QCheckBox("UPX sıkıştırma")
        self.upx.setChecked(True)

        v.addWidget(self.onefile)
        v.addWidget(self.console)
        v.addWidget(self.clean)
        v.addWidget(self.upx)
        v.addStretch()
        return w

    def _advanced_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.optimize = QSpinBox()
        self.optimize.setRange(0, 2)
        form.addRow("Optimizasyon:", self.optimize)

        self.extra_args = QLineEdit()
        self.extra_args.setPlaceholderText("--additional args")
        form.addRow("Ekstra argümanlar:", self.extra_args)

        return w

    def _pick_dir(self, edit: QLineEdit) -> None:
        d = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if d:
            edit.setText(d)

    def _pick_file(self, edit: QLineEdit, filt: str) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Dosya Seç", "", filt)
        if f:
            edit.setText(f)
