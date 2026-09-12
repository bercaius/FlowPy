"""PyInstaller build configuration and worker thread."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from .utils import ensure_pyinstaller


@dataclass
class BuildConfig:
    """PyInstaller build configuration."""
    entry_script: Path
    project_root: Path
    output_name: str = "FlowPy"
    distpath: Optional[Path] = None
    workpath: Optional[Path] = None
    specpath: Optional[Path] = None

    onefile: bool = True
    windowed: bool = False
    console: bool = True

    icon: Optional[Path] = None
    add_data: list[tuple[str, str]] = field(default_factory=list)
    hidden_imports: list[str] = field(default_factory=list)
    collect_submodules: list[str] = field(default_factory=list)
    collect_data: list[str] = field(default_factory=list)
    exclude_modules: list[str] = field(default_factory=list)
    search_paths: list[Path] = field(default_factory=list)

    upx: bool = True
    upx_dir: Optional[Path] = None
    clean: bool = True
    strip: bool = False
    optimize: int = 0
    encrypt_key: Optional[str] = None

    log_level: str = "INFO"
    bootloader_ignore_signals: bool = False
    runtime_tmpdir: Optional[Path] = None
    disable_windowed_traceback: bool = False
    uac_admin: bool = False
    uac_uiaccess: bool = False
    debug: bool = False

    auto_install: bool = True
    extra_args: str = ""


class BuildWorker(QThread):
    """PyInstaller'ı arka planda çalıştıran işçi thread."""

    log = Signal(str)
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, config: BuildConfig):
        super().__init__()
        self.config = config

    def _build_command(self, pyinstaller: str) -> list[str]:
        c = self.config
        cmd: list[str] = [pyinstaller]

        if c.onefile:
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")

        if c.windowed:
            cmd.append("--windowed")
        if c.console and not c.windowed:
            cmd.append("--console")

        cmd += ["--name", c.output_name]

        if c.distpath:
            cmd += ["--distpath", str(c.distpath)]
        if c.workpath:
            cmd += ["--workpath", str(c.workpath)]
        if c.specpath:
            cmd += ["--specpath", str(c.specpath)]

        if c.icon:
            cmd += ["--icon", str(c.icon)]

        for src, dest in c.add_data:
            cmd += ["--add-data", f"{src}{_sep()}{dest}"]

        for imp in c.hidden_imports:
            if imp.strip():
                cmd += ["--hidden-import", imp.strip()]

        for mod in c.collect_submodules:
            if mod.strip():
                cmd += ["--collect-submodules", mod.strip()]
        for pkg in c.collect_data:
            if pkg.strip():
                cmd += ["--collect-data", pkg.strip()]
        for mod in c.exclude_modules:
            if mod.strip():
                cmd += ["--exclude-module", mod.strip()]

        for p in c.search_paths:
            cmd += ["--paths", str(p)]

        if not c.upx:
            cmd.append("--noupx")
        if c.upx_dir:
            cmd += ["--upx-dir", str(c.upx_dir)]

        if c.clean:
            cmd.append("--clean")
        if c.strip:
            cmd.append("--strip")
        if c.optimize:
            cmd += ["--optimize", str(c.optimize)]
        if c.encrypt_key:
            cmd += ["--key", c.encrypt_key]

        if c.bootloader_ignore_signals:
            cmd.append("--bootloader-ignore-signals")
        if c.runtime_tmpdir:
            cmd += ["--runtime-tmpdir", str(c.runtime_tmpdir)]
        if c.disable_windowed_traceback:
            cmd.append("--disable-windowed-traceback")
        if c.uac_admin:
            cmd.append("--uac-admin")
        if c.uac_uiaccess:
            cmd.append("--uac-uiaccess")
        if c.debug:
            cmd += ["--debug", "all"]

        cmd += ["--log-level", c.log_level.upper()]

        cmd.append(str(c.entry_script))

        if c.extra_args.strip():
            cmd += c.extra_args.split()

        return cmd

    def run(self) -> None:
        c = self.config
        self.log.emit("[*] Derleme başlatılıyor...")
        self.progress.emit(2)

        installed, pyinstaller = ensure_pyinstaller()
        if not installed:
            if c.auto_install:
                self.log.emit("[*] PyInstaller bulunamadı, yükleniyor...")
                ok = self._pip_install("pyinstaller")
                if not ok:
                    self.finished.emit(False, "PyInstaller yüklenemedi.")
                    return
                installed, pyinstaller = ensure_pyinstaller()
                if not installed:
                    self.finished.emit(False, "PyInstaller yine de bulunamadı.")
                    return
            else:
                self.finished.emit(False, "PyInstaller yüklü değil.")
                return

        cmd = self._build_command(pyinstaller)
        self.log.emit("[>] Komut:\n  " + " ".join(cmd))
        self.progress.emit(8)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(c.project_root),
                bufsize=1,
            )
        except Exception as exc:
            self.finished.emit(False, f"Başlatma hatası: {exc}")
            return

        last_progress = 8
        assert proc.stdout is not None
        for line in proc.stdout:
            self.log.emit(line.rstrip("\n"))
            p = _estimate_progress(line)
            if p > last_progress:
                last_progress = p
                self.progress.emit(p)

        rc = proc.wait()
        if rc == 0:
            out = _resolve_output(c)
            self.progress.emit(100)
            self.log.emit(f"[✓] Derleme tamamlandı: {out}")
            self.finished.emit(True, str(out))
        else:
            self.finished.emit(False, f"PyInstaller çıkış kodu: {rc}")

    def _pip_install(self, package: str) -> bool:
        try:
            proc = subprocess.run(
                [self._python(), "-m", "pip", "install", "--upgrade", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in proc.stdout.splitlines():
                self.log.emit(line)
            return proc.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _python() -> str:
        return sys.executable


def _sep() -> str:
    return ";" if sys.platform.startswith("win") else ":"


def _resolve_output(c: BuildConfig) -> Path:
    base = c.distpath or (c.project_root / "dist")
    if c.onefile:
        ext = ".exe" if sys.platform.startswith("win") else ""
        return Path(base) / f"{c.output_name}{ext}"
    return Path(base) / c.output_name


def _estimate_progress(line: str) -> int:
    low = line.lower()
    if "looking for" in low or "examining" in low:
        return 20
    if "building because" in low or "building pkgs" in low:
        return 35
    if "building exe" in low or "building col" in low:
        return 55
    if "copying" in low or "appending" in low:
        return 75
    if "completed" in low or "building successfully" in low:
        return 90
    return 0
