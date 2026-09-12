"""Gerçek Python çalıştırıcısı — QProcess tabanlı, parametre destekli.

FlowPy, açık editör içeriğini ya da bir dosyayı gerçek Python yorumlayıcısı
ile çalıştırır; stdout/stderr/çıkış kodunu canlı olarak iletir. Hazır veya
sahte çıktı üretmez — yalnızca gerçek süreç çıktısı aktarılır.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal


def _python_executable() -> str:
    """Gerçek Python yorumlayıcısını çöz: PyInstaller paketi, sistem
    Python 3.12 veya PATH'teki python'u tercih sırasına göre bul."""
    base = getattr(sys, "_base_executable", None)
    if base and Path(base).exists():
        return str(base)
    if sys.executable and Path(sys.executable).exists():
        return str(sys.executable)
    candidates = [
        r"C:\Users\Ayberk Yiğit Özdemir\AppData\Local\Programs\Python\Python312\python.exe",
        r"C:\Program Files\Python312\python.exe",
        r"C:\Program Files (x86)\Python312\python.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    found = shutil.which("python")
    if found:
        return found
    return sys.executable


def _utf8_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


class Runner(QObject):
    """Python/batch dosyalarını gerçek bir alt süreçte çalıştırır."""

    line = Signal(str)
    started = Signal()
    finished = Signal(int)
    errored = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.proc: QProcess | None = None
        self._temp: Path | None = None

    def run_file(self, path: Path, cwd: Path, args: list[str] | None = None) -> None:
        """Bir dosyayı gerçek yorumlayıcı ile çalıştırır (argv destekli)."""
        self.stop()
        suffix = path.suffix.lower()
        if suffix in (".bat", ".cmd"):
            self._spawn(["cmd.exe", "/c", str(path)], cwd, args)
        elif suffix in (".py", ".pyw"):
            self._spawn([_python_executable(), str(path), *(args or [])], cwd, None)
        else:
            self.line.emit(f"[FlowPy] '{suffix or 'dosya'}' doğrudan çalıştırılamaz.")
            self.finished.emit(0)

    def run_code(self, code: str, cwd: Path, args: list[str] | None = None) -> None:
        """Kaydedilmemiş editör içeriğini geçici bir dosyaya yazıp çalıştırır."""
        self.stop()
        try:
            fd, tmp = tempfile.mkstemp(suffix=".py", prefix="flowpy_")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(code)
            self._temp = Path(tmp)
        except Exception as exc:  # noqa: BLE001
            self.errored.emit(f"[FlowPy] Geçici dosya oluşturulamadı: {exc}")
            return
        self._spawn([_python_executable(), str(self._temp), *(args or [])], cwd, None)

    def _spawn(self, command: list[str], cwd: Path, _args) -> None:
        proc = QProcess()
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.setWorkingDirectory(str(cwd))
        proc.setProcessEnvironment(_utf8_env())
        proc.readyReadStandardOutput.connect(lambda: self._drain(proc))
        proc.readyReadStandardError.connect(lambda: self._drain(proc))
        proc.started.connect(self.started.emit)
        proc.finished.connect(self._on_finished)
        self.proc = proc
        proc.start(command[0], command[1:])
        if not proc.waitForStarted(3000):
            self.errored.emit("[FlowPy] Süreç başlatılamadı.")
            self.finished.emit(-1)

    def _on_finished(self, code: int, _status) -> None:
        self._cleanup_temp()
        self.finished.emit(code)

    def _cleanup_temp(self) -> None:
        if self._temp is not None:
            try:
                self._temp.unlink(missing_ok=True)
            except Exception:
                pass
            self._temp = None

    def _drain(self, proc: QProcess) -> None:
        data = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        for ln in data.splitlines():
            self.line.emit(ln)

    def write(self, text: str) -> None:
        """Çalışan sürece interaktif girdi gönderir (input() için)."""
        if self.proc and self.proc.state() == QProcess.Running:
            self.proc.write(text.encode("utf-8"))

    def stop(self) -> None:
        if self.proc and self.proc.state() != QProcess.NotRunning:
            self.proc.kill()
            self.proc.waitForFinished(1000)
        self._cleanup_temp()
        self.proc = None
