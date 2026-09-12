"""Application-wide settings — QSettings + JSON fallback.

Professional settings system with:
- QSettings for Qt-native settings (window geometry, recent files)
- JSON file for human-readable/externally-editable settings
- Property accessors for common settings
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


class Settings:
    """Application settings manager."""

    def __init__(self) -> None:
        self._qt_settings = QSettings()
        self._json_path = self._get_json_path()
        self._json_cache: dict[str, Any] = {}
        self._load_json()

    def _get_json_path(self) -> Path:
        appdata = Path.home() / "AppData" / "Roaming" / "TurcoDevelopStudio" / "FlowPy"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata / "settings.json"

    def _load_json(self) -> None:
        if self._json_path.exists():
            try:
                self._json_cache = json.loads(self._json_path.read_text(encoding="utf-8"))
            except Exception:
                logger.exception("Failed to load settings.json")
                self._json_cache = {}

    def _save_json(self) -> None:
        try:
            self._json_path.write_text(
                json.dumps(self._json_cache, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save settings.json")

    # ---- QSettings wrapper ----
    def value(self, key: str, default: Any = None, type_hint: type | None = None) -> Any:
        if type_hint is not None:
            return self._qt_settings.value(key, default, type=type_hint)
        return self._qt_settings.value(key, default)

    def set_value(self, key: str, value: Any) -> None:
        self._qt_settings.setValue(key, value)

    # ---- JSON-backed settings ----
    def get_json(self, key: str, default: Any = None) -> Any:
        return self._json_cache.get(key, default)

    def set_json(self, key: str, value: Any, persist: bool = True) -> None:
        self._json_cache[key] = value
        if persist:
            self._save_json()

    # ---- Convenience properties ----
    @property
    def recent_projects(self) -> list[str]:
        return self.get_json("recent_projects", [])

    @recent_projects.setter
    def recent_projects(self, value: list[str]) -> None:
        self.set_json("recent_projects", value)

    @property
    def window_geometry(self) -> dict[str, Any]:
        return self.get_json("window_geometry", {})

    @window_geometry.setter
    def window_geometry(self, value: dict[str, Any]) -> None:
        self.set_json("window_geometry", value)

    @property
    def enabled_plugins(self) -> list[str]:
        raw = self.value("plugins/enabled", "", type=str)
        return [p.strip() for p in raw.split(",") if p.strip()]

    @enabled_plugins.setter
    def enabled_plugins(self, value: list[str]) -> None:
        self.set_value("plugins/enabled", ",".join(value))
