"""Core utilities — dosya, yollar, Python yardımcıları."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def get_python_executable() -> str:
    """Mevcut Python yorumlayıcısının tam yolunu döndürür."""
    return sys.executable


def find_command(name: str) -> str | None:
    """Verilen komutun sistemdeki tam yolunu bulur, yoksa None döner."""
    return shutil.which(name)


def ensure_pyinstaller() -> tuple[bool, str]:
    """PyInstaller'ın kurulu olup olmadığını kontrol eder.

    Döndürür: (kurulu_mu, çalıştırılabilir_yol)
    """
    try:
        import PyInstaller  # noqa: F401
        return True, "PyInstaller"
    except ImportError:
        pass
    exe = find_command("pyinstaller")
    if exe:
        return True, exe
    return False, ""


def human_size(num: float) -> str:
    """Bayt cinsinden boyutu okunabilir formata çevirir."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def list_py_files(root: Path, limit: int = 5000) -> list[Path]:
    """Bir klasördeki tüm Python dosyalarını döndürür."""
    result: list[Path] = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        result.append(path)
        if len(result) >= limit:
            break
    return result
