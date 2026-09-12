"""FlowPy application entrypoint — professional startup sequence.

FlowPy, TurcoDevelopStudio tarafından geliştirilen profesyonel bir Python IDE'dir.
Başlangıç sırası:
1. Uygulama metadata'sı (marka, sürüm, organizasyon)
2. Loglama (rotating file + console)
3. Global exception hook (çöküş raporu)
4. Splash screen (logo ile)
5. Ana pencere
6. Event loop
"""

from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QSplashScreen,
    QVBoxLayout,
    QWidget,
)

from flowpy.ui.main_window import MainWindow

# ---------------------------------------------------------------------------
# Application metadata — TurcoDevelopStudio / FlowPy brand
# ---------------------------------------------------------------------------
APP_NAME = "FlowPy"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "TurcoDevelopStudio"
APP_DOMAIN = "https://bercaius.github.io/turcodevelop-studio/"
APP_AUTHOR = "Berkay Özdemir"
APP_URL = "https://bercaius.github.io/FlowPy/"
APP_GITHUB = "https://github.com/bercaius/FlowPy"

# ---------------------------------------------------------------------------
# Logging setup — professional rotating file + console
# ---------------------------------------------------------------------------
_LOG_DIR = (
    Path.home() / "AppData" / "Roaming" / "TurcoDevelopStudio" / "FlowPy" / "logs"
)
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "flowpy.log"


def _setup_logging() -> None:
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = RotatingFileHandler(
        _LOG_FILE, maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(ch)

    logging.info("Logging initialized. Log file: %s", _LOG_FILE)


# ---------------------------------------------------------------------------
# Exception handling — crash reporter
# ---------------------------------------------------------------------------
def _global_exception_hook(exc_type, exc_value, exc_tb) -> None:
    logger = logging.getLogger("flowpy")
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    try:
        from PySide6.QtWidgets import QMessageBox
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        QMessageBox.critical(
            None,
            "Beklenmeyen Hata",
            f"FlowPy beklenmeyen bir hata ile karşılaştı.\n\n"
            f"Detaylar log dosyasına kaydedildi:\n{_LOG_FILE}\n\n"
            f"{tb_text[-500:]}",
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Splash screen — brand logo ile
# ---------------------------------------------------------------------------
class _SplashWidget(QWidget):
    """Branded splash screen widget."""

    def __init__(self, parent: QSplashScreen) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(8)

        title = QLabel(APP_NAME)
        title.setStyleSheet("color:#2f81f7;font-size:32px;font-weight:bold;")
        lay.addWidget(title)

        sub = QLabel(f"v{APP_VERSION}  ·  Professional Python IDE")
        sub.setStyleSheet("color:#8b949e;font-size:12px;")
        lay.addWidget(sub)

        author = QLabel(f"by {APP_AUTHOR}  ·  {APP_ORGANIZATION}")
        author.setStyleSheet("color:#484f58;font-size:10px;")
        lay.addWidget(author)
        lay.addStretch(1)


def _show_splash() -> tuple[QSplashScreen, _SplashWidget]:
    pixmap = QPixmap(480, 240)
    pixmap.fill(Qt.GlobalColor.transparent)
    splash = QSplashScreen(pixmap, Qt.WindowType.SplashScreen)
    widget = _SplashWidget(splash)
    widget.resize(480, 240)
    splash.show()
    QApplication.processEvents()
    return splash, widget


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    _setup_logging()
    logging.info("=" * 60)
    logging.info("FlowPy v%s starting — %s", APP_VERSION, APP_ORGANIZATION)
    logging.info("Developer: %s <%s>", APP_AUTHOR, APP_URL)

    sys.excepthook = _global_exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setOrganizationDomain(APP_DOMAIN)

    splash, _ = _show_splash()

    splash.showMessage(
        "Ana pencere hazırlanıyor...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
    )
    QApplication.processEvents()

    window = MainWindow()
    window.setWindowTitle(f"{APP_NAME} v{APP_VERSION} — {APP_ORGANIZATION}")

    splash.showMessage(
        "Başlatılıyor...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
    )
    QApplication.processEvents()

    window.show()

    QTimer.singleShot(600, splash.close)

    logging.info("FlowPy ready — %s", APP_URL)
    rc = app.exec()

    logging.info("FlowPy exited with code %d", rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
