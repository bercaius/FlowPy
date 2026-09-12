"""Project vault and management — AppData/FlowPy storage."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    from os import environ
    _APPDATA = Path(environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
except Exception:
    _APPDATA = Path.home() / "AppData" / "Roaming"

APP_ROOT = _APPDATA / "TurcoDevelopStudio" / "FlowPy"
VAULT = APP_ROOT / "vault"
CACHE = APP_ROOT / "cache"
CONFIG_FILE = APP_ROOT / "config.json"

META_NAME = "flowpy.json"


@dataclass
class Project:
    """Project metadata."""
    name: str
    path: str
    description: str = ""
    entry: str = "main.py"
    created: str = ""

    @property
    def folder(self) -> Path:
        return Path(self.path)

    def meta_path(self) -> Path:
        return self.folder / META_NAME

    def save_meta(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in asdict(self).items() if k != "path"}
        self.meta_path().write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def load(path: Path) -> "Project":
        meta = path / META_NAME
        if meta.exists():
            d = json.loads(meta.read_text(encoding="utf-8"))
        else:
            d = {}
        return Project(
            name=d.get("name", path.name),
            path=str(path),
            description=d.get("description", ""),
            entry=d.get("entry", "main.py"),
            created=d.get("created", ""),
        )


class Vault:
    """Project vault — manages all user projects in AppData."""

    def __init__(self) -> None:
        APP_ROOT.mkdir(parents=True, exist_ok=True)
        VAULT.mkdir(parents=True, exist_ok=True)
        CACHE.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    @staticmethod
    def _load_config() -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"projects": [], "recent": [], "entry": "main.py"}

    def save_config(self) -> None:
        CONFIG_FILE.write_text(
            json.dumps(self._config, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def create_project(
        self, name: str, description: str = "", location: Path | None = None
    ) -> Project:
        base = location or VAULT
        folder = base / _safe(name)
        folder.mkdir(parents=True, exist_ok=True)
        proj = Project(
            name=name,
            path=str(folder),
            description=description,
            entry="main.py",
            created=time.strftime("%Y-%m-%d %H:%M"),
        )
        proj.save_meta()
        main = folder / "main.py"
        if not main.exists():
            # Hazır örnek/kod enjekte EDİLMEZ; kullanıcı kendi kodunu yazar.
            main.write_text("", encoding="utf-8")
        self._register(str(folder))
        return proj

    def open_project(self, folder: Path) -> Project:
        proj = Project.load(folder)
        self._register(str(folder))
        return proj

    def _register(self, path: str) -> None:
        paths = self._config.setdefault("projects", [])
        if path not in paths:
            paths.append(path)
        self.save_config()

    def list_projects(self) -> list[Project]:
        out: list[Project] = []
        for p in self._config.get("projects", []):
            fp = Path(p)
            if fp.exists():
                out.append(Project.load(fp))
        for child in sorted(VAULT.iterdir()):
            if child.is_dir() and str(child) not in self._config.get("projects", []):
                out.append(Project.load(child))
        return out

    def add_recent(self, path: str) -> None:
        rec = self._config.setdefault("recent", [])
        if path in rec:
            rec.remove(path)
        rec.insert(0, path)
        self._config["recent"] = rec[:12]
        self.save_config()

    def recents(self) -> list[str]:
        return [r for r in self._config.get("recent", []) if Path(r).exists()]

    def set_entry(self, entry: str) -> None:
        self._config["entry"] = entry
        self.save_config()


def _safe(name: str) -> str:
    bad = '<>:"/\\|?*'
    for ch in bad:
        name = name.replace(ch, "_")
    return name.strip() or "proje"
