"""Main window — tier-1 professional IDE layout."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import pytoflow
from ..core.project import Project, Vault
from ..core.settings import Settings
from ..core.services import Services
from ..resources.icons import icon
from .file_tree import FileTree
from .flowchart_view import FlowChartView
from .project_dialog import NewProjectDialog
from .sidebar import SideBar
from .status_bar import StatusBar
from .tab_manager import TabManager
from .terminal import Terminal
from .title_bar import TitleBar
from .toolbar import ToolBar
from .welcome_page import WelcomePage
from .block_editor import BlockEditorWidget

if TYPE_CHECKING:
    from flowpy.app import FlowPyWindow

logger = logging.getLogger(__name__)


class _About(QDialog):
    """Professional about dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hakkında")
        self.setModal(True)
        self.resize(420, 300)
        lay = QVBoxLayout(self)
        lay.setSpacing(16)

        from ..resources.icons import brand_logo_text
        logo = QLabel()
        logo_pixmap = brand_logo_text(160)
        if not logo_pixmap.isNull():
            logo.setPixmap(logo_pixmap)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)

        desc = QLabel(
            "<p style='color:#0078d4;font-size:16px;font-weight:600;'>"
            "FlowPy v1.0.0"
            "</p>"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(desc)

        info = QLabel(
            "<p style='color:#cccccc;font-size:12px;line-height:1.7;'>"
            "Professional Python IDE with Live Flowchart<br>"
            "Developed by Berkay Özdemir<br>"
            "TurcoDevelopStudio<br>"
            "MIT License"
            "</p>"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        lay.addWidget(info)

        btn = QPushButton("Kapat")
        btn.setObjectName("PrimaryBtn")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)


class MainWindow(QWidget):
    """Tier-1 professional main application window."""

    def __init__(self, services: Services | None = None) -> None:
        super().__init__()
        self.services = None
        self.settings = Settings()
        self.vault = Vault()

        self._project: Project | None = None
        self._active_editor = None
        self._last_graph = None
        self._sync_timer = QTimer()
        self._sync_timer.setSingleShot(True)
        self._sync_timer.timeout.connect(self._sync_flowchart)
        self._dark_mode = self.settings.dark_mode
        self._compile_status = "ready"  # ready, compiling, error, warning
        self._block_mode = False

        self._apply_theme()
        self._restore_window_state()
        self._build()
        self._setup_shortcuts()

        if services is not None:
            self.attach_services(services)

    def attach_services(self, services: Services) -> None:
        """Connect application backbone bridge."""
        self.services = services
        services.attach(
            get_code=self.get_active_code,
            get_graph=self.get_current_graph,
            log=self.log_to_terminal,
            set_code=self.set_active_code,
        )
        services.runRequested.connect(self._run_path)

    def _restore_window_state(self) -> None:
        geo = self.settings.window_geometry
        if geo:
            from PySide6.QtCore import QByteArray, QPoint, QSize
            self.restoreGeometry(QByteArray.fromBase64(geo.get("geometry", "").encode()))

            if "pos" in geo:
                self.move(QPoint(*geo["pos"]))
            if "size" in geo:
                self.resize(QSize(*geo["size"]))

    def _save_window_state(self) -> None:
        from PySide6.QtCore import QByteArray
        geo = {
            "geometry": bytes(self.saveGeometry()).decode("latin-1"),

            "pos": (self.x(), self.y()),
            "size": (self.width(), self.height()),
        }
        self.settings.window_geometry = geo

    def _setup_shortcuts(self) -> None:
        QShortcut("Ctrl+N", self).activated.connect(self._new_project)
        QShortcut("Ctrl+O", self).activated.connect(self._open_project_dialog)
        QShortcut("Ctrl+S", self).activated.connect(self._save)
        QShortcut("F5", self).activated.connect(self._run)
        QShortcut("Ctrl+Shift+S", self).activated.connect(self._save)

    def _apply_theme(self) -> None:
        qss_path = Path(__file__).resolve().parent.parent / "resources" / ("styles.qss" if self._dark_mode else "styles-light.qss")
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _toggle_theme(self) -> None:
        self._dark_mode = not self._dark_mode
        self.settings.dark_mode = self._dark_mode
        self._apply_theme()
        self.title.theme_btn.setIcon(icon("sun" if self._dark_mode else "moon", "#ffffff", 14))

    def _toggle_block_mode(self, checked: bool) -> None:
        self._block_mode = checked
        self.editor_splitter.setVisible(not checked)
        self.block_editor.setVisible(checked)
        if checked:
            self._on_block_code_changed(self.block_editor.generate_code())

    def _build_menu(self) -> None:
        file_menu = self.menu_bar.addMenu("Dosya")
        file_menu.addAction("Yeni Proje", self._new_project)
        file_menu.addAction("Proje Aç", self._open_project_dialog)
        file_menu.addAction("Kaydet", self._save)
        file_menu.addSeparator()
        file_menu.addAction("Çıkış", self.close)

        view_menu = self.menu_bar.addMenu("Görünüm")
        view_menu.addAction("Çalışma Alanı", lambda: self._nav(0))
        view_menu.addAction("Projeler", lambda: self._nav(1))
        view_menu.addAction("Dosyalar", lambda: self._nav(2))
        view_menu.addAction("Ayarlar", lambda: self._nav(3))

        help_menu = self.menu_bar.addMenu("Yardım")
        help_menu.addAction("Hakkında", lambda: _About(self).exec())

    # ---- kurulum ----
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Menu bar
        self.menu_bar = QMenuBar()
        self.menu_bar.setObjectName("MenuBar")
        self._build_menu()
        root.setMenuBar(self.menu_bar)

        self.title = TitleBar(self)
        self.title.min_btn.clicked.connect(self.showMinimized)
        self.title.max_btn.clicked.connect(self._toggle_max)
        self.title.close_btn.clicked.connect(self.close)
        self.title.theme_btn.clicked.connect(self._toggle_theme)
        root.addWidget(self.title)

        self.toolbar = ToolBar()
        self.toolbar.newProject.connect(self._new_project)
        self.toolbar.openProject.connect(self._open_project_dialog)
        self.toolbar.save.connect(self._save)
        self.toolbar.run.connect(self._run)
        self.toolbar.stop.connect(self._stop)
        self.toolbar.more.connect(lambda: _About(self).exec())
        self.toolbar.blockModeToggled.connect(self._toggle_block_mode)
        root.addWidget(self.toolbar)

        self.sidebar = SideBar()
        for i, btn in enumerate(self.sidebar.buttons):
            btn.clicked.connect(lambda _=False, idx=i: self._nav(idx))

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self._welcome = WelcomePage(self)
        self._workspace = self._build_workspace()
        self._projects = self._build_projects()
        self._files = self._build_files()
        self._settings = self._build_settings()
        self.stack.addWidget(self._welcome)
        self.stack.addWidget(self._workspace)
        self.stack.addWidget(self._projects)
        self.stack.addWidget(self._files)
        self.stack.addWidget(self._settings)
        body.addWidget(self.stack, 1)

        root.addLayout(body, 1)

        self.status = StatusBar()
        root.addWidget(self.status)

        self._open_first_project()
        self._nav(0)

    def _build_workspace(self) -> QWidget:
        w = QWidget()
        vlay = QVBoxLayout(w)
        vlay.setContentsMargins(8, 8, 8, 8)
        vlay.setSpacing(8)

        self.tabs = TabManager()
        self.tabs.currentPathChanged.connect(self._on_active_changed)
        self.tabs.fileSaved.connect(lambda _: self._sync_flowchart())

        self.terminal = Terminal()

        self.editor_container = QWidget()
        ed_lay = QVBoxLayout(self.editor_container)
        ed_lay.setContentsMargins(0, 0, 0, 0)
        ed_lay.setSpacing(0)

        self.editor_splitter = QSplitter(Qt.Orientation.Vertical)
        self.editor_splitter.addWidget(self.tabs)
        self.editor_splitter.addWidget(self.terminal)
        self.editor_splitter.setStretchFactor(0, 3)
        self.editor_splitter.setStretchFactor(1, 1)
        ed_lay.addWidget(self.editor_splitter, 1)

        self.flow = FlowChartView()
        self.flow.nodeClicked.connect(self._on_node_clicked)
        self.flow.nodeDoubleClicked.connect(self._on_node_edit)

        self.block_editor = BlockEditorWidget()
        self.block_editor.codeChanged.connect(self._on_block_code_changed)
        self.block_editor.setVisible(False)
        ed_lay.addWidget(self.block_editor, 1)

        main = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(self.editor_container)
        main.addWidget(self.flow)
        main.setStretchFactor(0, 1)
        main.setStretchFactor(1, 1)
        vlay.addWidget(main, 1)
        return w

    def _build_projects(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(QLabel("<h3 style='color:#0078d4;margin:0'>Projeler</h3>"))
        head.addStretch(1)
        new = QPushButton("Yeni Proje")
        new.setObjectName("PrimaryBtn")
        new.clicked.connect(self._new_project)
        head.addWidget(new)
        v.addLayout(head)
        v.addWidget(QLabel("<span style='color:#888888'>Kasanızdaki projeler.</span>"))
        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self._on_project_item)
        v.addWidget(self.project_list, 1)
        return w

    def _build_files(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        self.file_tree = FileTree()
        self.file_tree.fileOpened.connect(self._open_file)
        v.addWidget(self.file_tree, 1)
        return w

    def _build_settings(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(18, 18, 18, 18)
        v.addWidget(QLabel("<h3 style='color:#0078d4'>Ayarlar</h3>"))
        v.addWidget(QLabel("<span style='color:#888888'>Tema: Koyu (varsayılan)</span>"))
        v.addWidget(QLabel("<span style='color:#888888'>Dil: Türkçe</span>"))
        v.addWidget(QLabel(
            "<span style='color:#888888'>Tüm projeleriniz AppData/FlowPy altında saklanır.</span>"
        ))
        v.addStretch(1)
        return w

    # ---- proje yaşam döngüsü ----
    def _open_first_project(self) -> None:
        projects = self.vault.list_projects()
        if not projects:
            proj = self.vault.create_project("Hoş Geldiniz", "İlk FlowPy projenizi burada başlatın.")
            projects = [proj]
        self._refresh_project_list()
        if projects:
            self._open_project(projects[0])

    def _refresh_project_list(self) -> None:
        self.project_list.clear()
        for p in self.vault.list_projects():
            item = QListWidgetItem(f"{p.name}\n{p.description or p.path}"[:120])
            item.setData(Qt.ItemDataRole.UserRole, p.path)
            self.project_list.addItem(item)

    def _on_project_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self._open_project(self.vault.open_project(Path(path)))

    def _open_project(self, proj: Project) -> None:
        self._project = proj
        self.vault.add_recent(proj.path)
        self.file_tree.set_root(proj.folder)
        self.terminal.set_cwd(proj.folder)
        self._refresh_project_list()
        entry = proj.folder / proj.entry
        if not entry.exists():
            entry = proj.folder / "main.py"
        if entry.exists():
            self.tabs.open_file(entry)
        else:
            self.tabs.open_code("# FlowPy projenizi buraya yazın\n", title="main.py")
        self._schedule_sync()
        self._nav(0)

    def _new_project(self) -> None:
        dlg = NewProjectDialog(self.vault, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.project:
            self._open_project(dlg.project)

    def _open_project_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Proje Klasörü Aç")
        if folder:
            self._open_project(self.vault.open_project(Path(folder)))

    # ---- editör / sekme ----
    def _open_file(self, path: Path) -> None:
        self.tabs.open_file(path)
        self._nav(0)

    def _on_active_changed(self, path: str) -> None:
        ed = self.tabs.current_editor()
        if self._active_editor is not None:
            try:
                self._active_editor.textChanged.disconnect(self._schedule_sync)
            except Exception:
                pass
        self._active_editor = ed
        if ed is not None:
            ed.textChanged.connect(self._schedule_sync)
            ed.cursorPositionChanged.connect(self._on_cursor)
            suffix = Path(path).suffix if path else ""
            lang = ed.language_for_suffix(suffix) if hasattr(ed, "language_for_suffix") else "Python"
            self.status.set_language(lang)
            self._on_cursor()
        self._schedule_sync()

    def _on_cursor(self) -> None:
        ed = self._active_editor
        if ed is None:
            return
        cur = ed.textCursor()
        self.status.set_cursor(cur.blockNumber() + 1, cur.columnNumber() + 1)

    def _schedule_sync(self) -> None:
        self._sync_timer.start(400)

    # ---- akış şeması senkronu ----
    def _sync_flowchart(self) -> None:
        ed = self.tabs.current_editor()
        if ed is None:
            return
        path = self.tabs.current_path()
        code = ed.toPlainText()
        if not code.strip():
            return
        is_python = path.lower().endswith(".py") or not path
        if not is_python:
            self.status.set_ready("Akış şeması yalnızca Python için")
            return

        self._compile_status = "compiling"
        self.status.set_ready("Derleniyor...")
        self.status.set_compile_status("compiling")
        QApplication.processEvents()

        try:
            graph, err = pytoflow.FlowBuilder().build(code)
        except Exception as exc:
            logger.exception("Flowchart build failed")
            graph, err = pytoflow.FlowGraph(), exc
        if err is not None:
            self._compile_status = "error"
            self.status.set_ready("Sözdizimi hatası")
            self.status.set_compile_status("error")
            self.status.set_stats(errors=1)
            return
        try:
            graph = pytoflow.layout_graph(graph)
            self.flow.set_graph(graph)
            self._last_graph = graph
        except Exception as exc:
            logger.exception("Flowchart layout failed")
            self._compile_status = "error"
            self.status.set_ready("Akış şeması hata")
            self.status.set_compile_status("error")
            return

        self._compile_status = "ready"
        self.status.set_compile_status("ready")
        self.status.set_ready("Hazır")
        self.status.set_stats(
            errors=getattr(graph, "errors", 0),
            warnings=getattr(graph, "warnings", 0),
            nodes=len(getattr(graph, "nodes", [])),
            lines=len(code.splitlines()),
        )

    def _on_node_clicked(self, line: int) -> None:
        ed = self._active_editor
        if ed is not None and line > 0:
            if hasattr(ed, "highlight_source_line"):
                ed.highlight_source_line(line)
            self.flow.select_node_by_line(line)

    def _on_node_edit(self, line: int, code: str) -> None:
        ed = self._active_editor
        if ed is None:
            self.tabs.open_code(code)
            ed = self.tabs.current_editor()
        if ed is not None and code:
            ed.setPlainText(code)
            self._schedule_sync()

    # ---- servis köprüsü yardımcıları ----
    def get_active_code(self) -> str:
        ed = self.tabs.current_editor()
        return ed.toPlainText() if ed is not None else ""

    def set_active_code(self, code: str) -> None:
        ed = self.tabs.current_editor()
        if ed is not None:
            ed.setPlainText(code)
            self._schedule_sync()
        else:
            self.tabs.open_code(code)

    def get_current_graph(self):
        return self._last_graph

    def log_to_terminal(self, message: str) -> None:
        self.terminal.output.appendPlainText(message)

    def _run_path(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            ed = self.tabs.current_editor()
            code = ed.toPlainText() if ed is not None else ""
            cur = self.tabs.current_path()
            if cur and Path(cur).exists():
                self.tabs.save_current()
                self.terminal.run_file(Path(cur))
            elif code.strip():
                self.terminal.run_code(code)
            return
        self.terminal.run_file(p)

    def _on_block_code_changed(self, code: str) -> None:
        if not code.strip():
            return
        try:
            graph, err = pytoflow.FlowBuilder().build(code)
            if err is not None:
                self.status.set_ready("Sözdizimi hatası")
                self.status.set_compile_status("error")
                self.status.set_stats(errors=1)
                return
            graph = pytoflow.layout_graph(graph)
            self.flow.set_graph(graph)
            self._last_graph = graph
            self.status.set_compile_status("ready")
            self.status.set_ready("Hazır")
            self.status.set_stats(
                errors=getattr(graph, "errors", 0),
                warnings=getattr(graph, "warnings", 0),
                nodes=len(getattr(graph, "nodes", [])),
                lines=len(code.splitlines()),
            )
        except Exception as exc:
            logger.exception("Block code sync failed")
            self.status.set_ready("Akış şeması hata")

    def _run(self) -> None:
        if self._block_mode:
            code = self.block_editor.generate_code()
            if code.strip():
                self.terminal.run_code(code)
            return
        ed = self.tabs.current_editor()
        path = self.tabs.current_path()
        if not path:
            if ed is not None:
                self.terminal.run_code(ed.toPlainText())
            return
        self.tabs.save_current()
        self.terminal.run_file(Path(path))

    def _stop(self) -> None:
        self.terminal.stop()

    def _save(self) -> None:
        self.tabs.save_current()
        path = self.tabs.current_path()
        if self._project and path:
            self._project.entry = Path(path).name
            self._project.save_meta()

    # ---- navigasyon ----
    def _nav(self, idx: int) -> None:
        if idx == 0:
            if self._project is not None:
                self.stack.setCurrentIndex(1)
            else:
                self.stack.setCurrentIndex(0)
        elif idx == 1:
            self.stack.setCurrentIndex(2)
        elif idx == 2:
            self.stack.setCurrentIndex(3)
        elif idx == 3:
            self.stack.setCurrentIndex(4)
        self.sidebar.set_active(idx)

    def _toggle_max(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def closeEvent(self, event) -> None:
        self._save_window_state()
        super().closeEvent(event)
