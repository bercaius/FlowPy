"""Icon loader — loads icons from assets or Qt resource system."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

_ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"


def icon(name: str, color: str = "#c9d1d9", size: int = 18) -> QIcon:
    """Load an icon by name. Returns a QIcon (empty if not found)."""
    candidates = [
        _ASSETS / f"{name}.png",
        _ASSETS / f"{name}.svg",
        Path(__file__).parent / "icons" / f"{name}.png",
        Path(__file__).parent / "icons" / f"{name}.svg",
    ]
    for path in candidates:
        if path.exists():
            pixmap = QPixmap(str(path)).scaled(
                size, size,
            )
            return QIcon(pixmap)
    return QIcon()


def brand_logo(size: int = 96) -> QPixmap:
    """FlowPy logosuz marka görseli (assets/logo.png)."""
    p = _ASSETS / "logo.png"
    if p.exists():
        return QPixmap(str(p)).scaled(
            size, size, Qt.AspectRatioMode.KeepAspectRatio
        )
    return QPixmap()


def brand_logo_text(width: int = 220) -> QPixmap:
    """FlowPy yazılı marka görseli (assets/logo-text.png)."""
    p = _ASSETS / "logo-text.png"
    if p.exists():
        return QPixmap(str(p)).scaledToWidth(
            width, Qt.TransformationMode.SmoothTransformation
        )
    return QPixmap()
