"""FlowPy application entrypoint — clean modern startup."""

from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
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
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "FlowPy"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "TurcoDevelopStudio"
APP_DOMAIN = "turcodevelopstudio.com"
APP_AUTHOR = "Berkay Özdemir"
APP_URL = "https://bercaius.github.io/turcodevelop-studio/"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = (
    Path.home() / "AppData" / "Roaming" / "TurcoDevelopStudio" / "FlowPy" / "logs"
)


def _setup_logging() -> None:
    global _LOG_DIR, _LOG_FILE
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        import tempfile
        _LOG_DIR = Path(tempfile.gettempdir()) / "FlowPy" / "logs"
        _LOG_DIR.mkdir(parents=True, exist_ok=True)

    _LOG_FILE = _LOG_DIR / "flowpy.log"

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
# Exception handling
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
# Splash screen
# ---------------------------------------------------------------------------
class _SplashWidget(QWidget):
    """Branded splash screen widget."""

    def __init__(self, parent: QSplashScreen) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(12)

        from flowpy.resources.icons import brand_logo_text
        logo = QLabel()
        logo_pixmap = brand_logo_text(180)
        if not logo_pixmap.isNull():
            logo.setPixmap(logo_pixmap)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo.setText("FlowPy")
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setStyleSheet("font-size: 36px; font-weight: 700; color: #f59e0b;")
        lay.addWidget(logo)

        sub = QLabel(f"v{APP_VERSION}  ·  Professional Python IDE")
        sub.setStyleSheet("color:#f59e0b;font-size:13px;")
        lay.addWidget(sub)

        author = QLabel(f"by {APP_AUTHOR}  ·  {APP_ORGANIZATION}")
        author.setStyleSheet("color:#888888;font-size:11px;")
        lay.addWidget(author)
        lay.addStretch(1)


def _show_splash() -> tuple[QSplashScreen, _SplashWidget]:
    pixmap = QPixmap(520, 260)
    pixmap.fill(Qt.GlobalColor.white)
    splash = QSplashScreen(pixmap, Qt.WindowType.SplashScreen)
    widget = _SplashWidget(splash)
    widget.resize(520, 260)
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
        "Loading...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
    )
    QApplication.processEvents()

    window = MainWindow()
    window.setWindowTitle(f"{APP_NAME} v{APP_VERSION} — {APP_ORGANIZATION}")

    # Start services
    from flowpy.core.services import Services

    services = Services()
    window.attach_services(services)
    services.start()

    splash.showMessage(
        "Starting...",
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
