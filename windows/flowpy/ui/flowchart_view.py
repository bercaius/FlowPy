"""Flowchart view — professional IDE flowchart with compile/run integration."""

from __future__ import annotations

import math
from PySide6.QtCore import QLineF, QPointF, QRectF, QSize, Qt, QTimer, Signal, QPoint
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.pytoflow import FlowGraph

# Professional color palette
KIND_COLOR = {
    "terminator":  "#0078d4",
    "process":     "#569cd6",
    "decision":    "#c586c0",
    "io":          "#4ec9b0",
    "subroutine":  "#dcdcaa",
    "preparation": "#ce9178",
    "merge":       "#888888",
    "connector":   "#888888",
}

KIND_ICON = {
    "terminator":  "⬭",
    "process":     "▭",
    "decision":    "◆",
    "io":          "⌨",
    "subroutine":  "⧉",
    "preparation": "⬡",
    "merge":       "●",
    "connector":   "●",
}

BASE_NODE_W = 220
BASE_NODE_H = 80
MIN_SCALE = 0.3
MAX_SCALE = 3.0


class NodeItem(QGraphicsItem):
    """Professional flowchart node."""

    def __init__(self, node, scale: float = 1.0) -> None:
        super().__init__()
        self.node = node
        self.kind = node.kind
        if node.kind == "terminator":
            self.base_color = QColor("#dc2626") if node.label == "Bitiş" else QColor(KIND_COLOR["terminator"])
        else:
            self.base_color = QColor(KIND_COLOR.get(self.kind, "#569cd6"))
        self.small = node.kind in ("merge", "connector")
        self._scale = scale
        self.w = (48 if self.small else BASE_NODE_W) * scale
        self.h = (48 if self.small else BASE_NODE_H) * scale
        self.setPos(node.x - self.w / 2, node.y - self.h / 2)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self._hover = False

    def boundingRect(self) -> QRectF:
        pad = 6 * self._scale
        return QRectF(-pad, -pad, self.w + 2 * pad, self.h + 2 * pad)

    def paint(self, painter, option, widget) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(0, 0, self.w, self.h)
        shape = self._shape_path(rect)

        # Hover/selection glow
        if self._hover or self.isSelected():
            glow = QColor(self.base_color)
            glow.setAlpha(100)
            painter.setPen(QPen(glow, 3 * self._scale))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.drawPath(shape)

        # Main fill
        painter.setPen(QPen(self.base_color, 2 * self._scale))
        painter.setBrush(QBrush(QColor("#2d2d2d")))
        painter.drawPath(shape)

        if self.small:
            return

        # Icon
        icon_text = KIND_ICON.get(self.kind, "")
        painter.setPen(self.base_color)
        painter.setFont(QFont("Segoe UI", int(14 * self._scale), QFont.Weight.Bold))
        icon_rect = QRectF(10 * self._scale, 8 * self._scale, 28 * self._scale, 28 * self._scale)
        painter.drawText(icon_rect, Qt.AlignCenter, icon_text)

        # Title
        title = self.node.label or self.kind.capitalize()
        words = title.split(" ")
        first_line = words[0] if words else title
        second_line = " ".join(words[1:]) if len(words) > 1 else ""

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", int(11 * self._scale), QFont.Weight.Bold))
        title_rect = QRectF(46 * self._scale, 6 * self._scale, self.w - 56 * self._scale, 22 * self._scale)
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, self._elide(first_line, title_rect, painter))

        # Subtitle
        if second_line:
            painter.setPen(QColor("#cccccc"))
            painter.setFont(QFont("Segoe UI", int(10 * self._scale)))
            sub_rect = QRectF(46 * self._scale, 28 * self._scale, self.w - 56 * self._scale, 18 * self._scale)
            painter.drawText(sub_rect, Qt.AlignVCenter | Qt.AlignLeft, self._elide(second_line, sub_rect, painter))

        # Line number
        if self.node.line:
            painter.setPen(QColor("#888888"))
            painter.setFont(QFont("Segoe UI", int(9 * self._scale)))
            info_rect = QRectF(10 * self._scale, self.h - 18 * self._scale, self.w - 20 * self._scale, 14 * self._scale)
            painter.drawText(info_rect, Qt.AlignRight | Qt.AlignVCenter, f"L{self.node.line}")

    def _shape_path(self, rect: QRectF) -> QPainterPath:
        w, h = rect.width(), rect.height()
        if self.kind in ("merge", "connector"):
            path = QPainterPath()
            path.addEllipse(rect)
            return path
        if self.kind == "terminator":
            r = h / 2
            path = QPainterPath()
            path.addRoundedRect(rect, r, r)
            return path
        if self.kind == "decision":
            path = QPainterPath()
            path.moveTo(w / 2, 0)
            path.lineTo(w, h / 2)
            path.lineTo(w / 2, h)
            path.lineTo(0, h / 2)
            path.closeSubpath()
            return path
        if self.kind == "io":
            skew = 20 * self._scale
            path = QPainterPath()
            path.moveTo(skew, 0)
            path.lineTo(w, 0)
            path.lineTo(w - skew, h)
            path.lineTo(0, h)
            path.closeSubpath()
            return path
        if self.kind == "preparation":
            inset = h / 2
            path = QPainterPath()
            path.moveTo(inset, 0)
            path.lineTo(w - inset, 0)
            path.lineTo(w, h / 2)
            path.lineTo(w - inset, h)
            path.lineTo(inset, h)
            path.lineTo(0, h / 2)
            path.closeSubpath()
            return path
        path = QPainterPath()
        path.addRoundedRect(rect, 10 * self._scale, 10 * self._scale)
        return path

    @staticmethod
    def _elide(text: str, rect: QRectF, painter: QPainter) -> str:
        metrics = painter.fontMetrics()
        if metrics.horizontalAdvance(text) <= rect.width():
            return text
        words = text.split(" ")
        lines: list[str] = []
        cur = ""
        for w in words:
            if metrics.horizontalAdvance(cur + " " + w) > rect.width() and cur:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        if len(lines) > 2:
            lines = lines[:2]
            lines[-1] = lines[-1][: max(0, len(lines[-1]) - 1)] + "…"
        return "\n".join(lines)

    def hoverEnterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)


class FlowChartView(QGraphicsView):
    """Professional flowchart view with compile/run integration."""

    nodeClicked = Signal(int)
    nodeDoubleClicked = Signal(int, str)
    graphToPython = Signal()
    compileRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setInteractive(True)
        self._graph: FlowGraph | None = None
        self._pan_active = False
        self._pan_start: QPoint | None = None
        self._drag_mode = False
        self._current_scale = 1.0
        self._build_controls()

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.08 if delta > 0 else 1.0 / 1.08
        self._apply_zoom(factor)

    def _apply_zoom(self, factor: float) -> None:
        cur = self.transform()
        new_scale = cur.m11() * factor
        if MIN_SCALE <= new_scale <= MAX_SCALE:
            self.scale(factor, factor)
            self._current_scale = new_scale

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None and hasattr(item, "node"):
                node = item.node
                line = getattr(node, "line", 0)
                code = getattr(node, "code", "") or getattr(node, "label", "")
                self.nodeClicked.emit(line)
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.nodeDoubleClicked.emit(line, code)
                event.accept()
                return
            # Sol tık ile pan
            self._pan_active = True
            self._pan_start = event.position().toPoint()
            self._drag_mode = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._pan_active = True
            self._pan_start = event.position().toPoint()
            self._drag_mode = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._pan_active and self._pan_start is not None:
            mouse_delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - mouse_delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - mouse_delta.y()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._pan_active:
            self._pan_active = False
            self._drag_mode = False
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None and hasattr(item, "node"):
                node = item.node
                line = getattr(node, "line", 0)
                code = getattr(node, "code", "") or getattr(node, "label", "")
                self.nodeDoubleClicked.emit(line, code)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def _build_controls(self) -> None:
        from ..resources.icons import icon

        self._controls = QWidget(self)
        lay = QVBoxLayout(self._controls)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        # Compile/Run button
        compile_btn = QPushButton("▶ Derle")
        compile_btn.setObjectName("RunBtn")
        compile_btn.setFixedHeight(32)
        compile_btn.setCursor(Qt.PointingHandCursor)
        compile_btn.clicked.connect(self.compileRequested.emit)
        lay.addWidget(compile_btn)

        # Zoom controls
        zoom_in = QToolButton()
        zoom_in.setObjectName("Flat")
        ic = icon("zoom_in", "#cccccc", 16)
        if not ic.isNull():
            zoom_in.setIcon(ic)
            zoom_in.setIconSize(QSize(16, 16))
        zoom_in.setFixedSize(32, 32)
        zoom_in.setCursor(Qt.PointingHandCursor)
        zoom_in.setToolTip("Yakınlaştır")
        zoom_in.clicked.connect(lambda: self._apply_zoom(1.2))
        lay.addWidget(zoom_in)

        zoom_out = QToolButton()
        zoom_out.setObjectName("Flat")
        ic = icon("zoom_out", "#cccccc", 16)
        if not ic.isNull():
            zoom_out.setIcon(ic)
            zoom_out.setIconSize(QSize(16, 16))
        zoom_out.setFixedSize(32, 32)
        zoom_out.setCursor(Qt.PointingHandCursor)
        zoom_out.setToolTip("Uzaklaştır")
        zoom_out.clicked.connect(lambda: self._apply_zoom(1.0 / 1.2))
        lay.addWidget(zoom_out)

        fit_btn = QToolButton()
        fit_btn.setObjectName("Flat")
        ic = icon("fit", "#cccccc", 16)
        if not ic.isNull():
            fit_btn.setIcon(ic)
            fit_btn.setIconSize(QSize(16, 16))
        fit_btn.setFixedSize(32, 32)
        fit_btn.setCursor(Qt.PointingHandCursor)
        fit_btn.setToolTip("Sığdır")
        fit_btn.clicked.connect(self.fit_view)
        lay.addWidget(fit_btn)

        self._controls.setStyleSheet("""
            QWidget { background-color: #252525; border: 1px solid #3e3e42; border-radius: 6px; }
            QPushButton#RunBtn { background-color: #107c10; color: #ffffff; border: none; border-radius: 4px; padding: 4px 12px; font-weight: 600; font-size: 12px; }
            QPushButton#RunBtn:hover { background-color: #0b8a0b; }
            QToolButton#Flat { background-color: transparent; border: none; border-radius: 4px; padding: 4px; }
            QToolButton#Flat:hover { background-color: #3e3e42; }
        """)
        self._controls.setGeometry(self.width() - 52, self.height() - 200, 38, 180)
        self._controls.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_controls"):
            self._controls.setGeometry(self.width() - 52, self.height() - 200, 38, 180)

    def drawBackground(self, painter, rect) -> None:
        super().drawBackground(painter, rect)
        painter.fillRect(rect, QColor("#1a1a1a"))
        grid = 24
        pen = QPen(QColor("#2d2d2d"))
        pen.setWidth(1)
        painter.setPen(pen)
        left = int(rect.left()) - (int(rect.left()) % grid)
        top = int(rect.top()) - (int(rect.top()) % grid)
        for x in range(left, int(rect.right()), grid):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(top, int(rect.bottom()), grid):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

    def set_graph(self, graph: FlowGraph) -> None:
        self._graph = graph
        self.scene().clear()
        items: dict[str, NodeItem] = {}

        # Calculate optimal scale based on scene size
        view_rect = self.viewport().rect()
        view_w = view_rect.width() - 100
        view_h = view_rect.height() - 100

        if graph.nodes:
            xs = [n.x for n in graph.nodes]
            ys = [n.y for n in graph.nodes]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            graph_w = max(max_x - min_x, 1)
            graph_h = max(max_y - min_y, 1)

            scale_x = view_w / (graph_w + 200)
            scale_y = view_h / (graph_h + 200)
            optimal_scale = min(scale_x, scale_y, 1.5)
            optimal_scale = max(MIN_SCALE, min(MAX_SCALE, optimal_scale))
        else:
            optimal_scale = 1.0

        self._current_scale = optimal_scale

        for n in graph.nodes:
            item = NodeItem(n, scale=optimal_scale)
            self.scene().addItem(item)
            items[n.id] = item

        for e in graph.edges:
            src = items.get(e.src)
            dst = items.get(e.dst)
            if not src or not dst:
                continue
            self._add_edge(src, dst, e.label, e.back)

        r = self.scene().itemsBoundingRect().adjusted(-60, -60, 60, 60)
        self.scene().setSceneRect(r)
        QTimer.singleShot(50, self.fit_view)

    def _add_edge(self, src: NodeItem, dst: NodeItem, label: str, back: bool) -> None:
        if back:
            start = QPointF(src.x() + 2, src.y() + src.h / 2)
            end = QPointF(dst.x() + 2, dst.y() - dst.h / 2)
            path = QPainterPath(start)
            midx = min(start.x(), end.x()) - 60
            ctrl1 = QPointF(midx, start.y())
            ctrl2 = QPointF(midx, end.y())
            path.cubicTo(ctrl1, ctrl2, end)
            self.scene().addPath(path, QPen(QColor("#555555"), 1.8))
            self._arrow(end, ctrl2, QColor("#555555"))
        else:
            start = QPointF(src.x() + src.w / 2, src.y() + src.h)
            end = QPointF(dst.x() + dst.w / 2, dst.y())
            line = QLineF(start, end)
            self.scene().addLine(line, QPen(QColor("#555555"), 1.8))
            self._arrow(end, start, QColor("#555555"))
        if label:
            mid = (start + end) / 2
            txt = self.scene().addText(label)
            txt.setDefaultTextColor(QColor("#888888"))
            txt.setFont(QFont("Segoe UI", 9))
            txt.setPos(mid.x() + 6, mid.y() - 10)
            txt.setZValue(1)

    def _arrow(self, tip: QPointF, from_point: QPointF, color: QColor) -> None:
        angle = math.atan2(tip.y() - from_point.y(), tip.x() - from_point.x())
        size = 10
        a1 = angle + math.radians(150)
        a2 = angle - math.radians(150)
        p1 = tip - QPointF(size * math.cos(a1), size * math.sin(a1))
        p2 = tip - QPointF(size * math.cos(a2), size * math.sin(a2))
        poly = QPolygonF([tip, p1, p2])
        self.scene().addPolygon(poly, QPen(color, 1.4), QBrush(color))

    def zoom_in(self) -> None:
        self._apply_zoom(1.2)

    def zoom_out(self) -> None:
        self._apply_zoom(1.0 / 1.2)

    def reset_view(self) -> None:
        self.resetTransform()
        self._current_scale = 1.0
        self.fit_view()

    def fit_view(self) -> None:
        if self.scene().items():
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    def to_python(self) -> str:
        """Akış şemasını Python metnine dönüştürür."""
        if self._graph is None:
            return ""
        from ..core.pytoflow import graph_to_python
        return graph_to_python(self._graph)

    def select_node_by_line(self, line: int) -> None:
        if self._graph is None:
            return
        for item in self.scene().items():
            if hasattr(item, "node") and getattr(item.node, "line", 0) == line:
                self.scene().clearSelection()
                item.setSelected(True)
                self.centerOn(item)
                return
