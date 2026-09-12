"""Create new project dialog — professional UX."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from ..core.project import Project, Vault


class NewProjectDialog(QDialog):
    """Professional new project creation dialog."""

    def __init__(self, vault: Vault, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Yeni Proje")
        self.setModal(True)
        self.resize(520, 320)
        self.vault = vault
        self.project: Project | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("Yeni Proje Oluştur")
        header.setStyleSheet("font-size:18px;font-weight:600;color:#f0f6fc;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(12)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Proje adını girin")
        self.name.setMinimumHeight(36)
        form.addRow("Proje adı:", self.name)

        self.desc = QPlainTextEdit()
        self.desc.setPlaceholderText("Proje açıklaması (opsiyonel)")
        self.desc.setMaximumHeight(80)
        form.addRow("Açıklama:", self.desc)

        layout.addLayout(form)

        self.vault_rb = QRadioButton("Kasada oluştur (güvenli, otomatik yedeklemeli)")
        self.custom_rb = QRadioButton("Özel klasör seç")
        self.vault_rb.setChecked(True)
        layout.addWidget(self.vault_rb)
        layout.addWidget(self.custom_rb)

        row = QHBoxLayout()
        self.custom_path = QLineEdit()
        self.custom_path.setReadOnly(True)
        self.custom_path.setPlaceholderText("Özel proje klasörü seçin")
        self.browse = QPushButton("Gözat")
        self.browse.setObjectName("Flat")
        self.browse.clicked.connect(self._browse)
        row.addWidget(self.custom_path, 1)
        row.addWidget(self.browse)
        layout.addLayout(row)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("İptal")
        cancel.setObjectName("Flat")
        cancel.clicked.connect(self.reject)
        create = QPushButton("Oluştur")
        create.setObjectName("PrimaryBtn")
        create.clicked.connect(self._create)
        actions.addWidget(cancel)
        actions.addWidget(create)
        layout.addLayout(actions)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Proje Klasörü Seç")
        if d:
            self.custom_path.setText(d)
            self.custom_rb.setChecked(True)

    def _create(self) -> None:
        name = self.name.text().strip()
        if not name:
            self.name.setFocus()
            return
        location = None
        if self.custom_rb.isChecked() and self.custom_path.text().strip():
            location = Path(self.custom_path.text().strip())
        self.project = self.vault.create_project(
            name, self.desc.toPlainText().strip(), location
        )
        self.accept()
