"""Welcome page — clean modern landing."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..resources.icons import brand_logo_text


class WelcomePage(QWidget):
    """Clean modern welcome page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("WelcomePage")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo
        logo_label = QLabel()
        logo_pixmap = brand_logo_text(180)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText("FlowPy")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet("font-size: 48px; font-weight: 700; color: #f59e0b;")
        layout.addWidget(logo_label)

        # Title
        title = QLabel("FlowPy")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: 600; color: #f59e0b; margin-top: 16px;")
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Python & FlowingTR arasında eş zamanlı derleme")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #999999; margin-top: 8px;")
        layout.addWidget(subtitle)

        # Description
        desc = QLabel(
            "Yazdığınız Python kodunu görsel akış diyagramlarına dönüştürür. "
            "Diyagramı düzenlerseniz Python kodu anlık olarak güncellenir."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("font-size: 13px; color: #cccccc; line-height: 1.6; margin-top: 24px; max-width: 500px;")
        layout.addWidget(desc)

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(12)

        new_btn = QPushButton("Yeni Proje")
        new_btn.setObjectName("PrimaryBtn")
        new_btn.setFixedHeight(36)
        new_btn.clicked.connect(self._on_new_project)

        open_btn = QPushButton("Proje Aç")
        open_btn.setObjectName("ToolBtn")
        open_btn.setFixedHeight(36)
        open_btn.clicked.connect(self._on_open_project)

        actions.addWidget(new_btn)
        actions.addWidget(open_btn)
        layout.addLayout(actions)

        layout.addStretch(1)

    def _on_new_project(self) -> None:
        main_window = self.window()
        if hasattr(main_window, '_new_project'):
            main_window._new_project()

    def _on_open_project(self) -> None:
        main_window = self.window()
        if hasattr(main_window, '_open_project_dialog'):
            main_window._open_project_dialog()
