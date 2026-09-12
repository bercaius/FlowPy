"""Flowchart view — professional, large, high-contrast nodes.

Node sizes: 220×90 px, bold labels, hover glow, icons.
Colors: WCAG AA compliant dark theme.
"""

from __future__ import annotations

import math
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, QTimer, Signal
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
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import (
    QLineF,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    Signal,
    QPoint,
)

from ..core.pytoflow import FlowGraph

# ISO 5807 / ANSI X3.5 renk paleti (WCAG AA uyumlu, yüksek kontrast)
KIND_COLOR = {
    "terminator":  "#2ea043",  # Başla (yeşil)
    "process":     "#8b949e",  # İşlem (gri)
    "decision":    "#d29922",  # Karar (amber)
    "io":          "#2f81f7",  # Girdi/Çıktı (mavi)
    "subroutine":  "#a371f7",  # Önceden tanımlı işlem (mor)
    "preparation": "#58a6ff",  # Hazırlık (açık mavi)
    "merge":       "#6e7681",  # Birleştirme (gri)
    "connector":   "#6e7681",  # Bağlayıcı (gri)
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

# Düğüm boyutları (px)
SIZE_STANDARD = (220, 90)
SIZE_SMALL = (48, 48)  # merge / connector


class NodeItem(QGraphicsItem):
    """Professional flowchart node — large, high-contrast, readable."""

    def __init__(self, node) -> None:
        super().__init__()
        self.node = node
        self.kind = node.kind
        # Başla/Bitiş ayırt etmek için etikete bak
        if node.kind == "terminator":
            self.base_color = QColor("#da3633") if node.label == "Bitiş" else QColor(KIND_COLOR["terminator"])
        else:
            self.base_color = QColor(KIND_COLOR.get(node.kind, "#8b949e"))
        self.small = node.kind in ("merge", "connector")
        self.w, self.h = SIZE_SMALL if self.small else SIZE_STANDARD
        self.setPos(node.x - self.w / 2, node.y - self.h / 2)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self._hover = False

    def boundingRect(self) -> QRectF:
        pad = 8
        return QRectF(-pad, -pad, self.w + 2 * pad, self.h + 2 * pad)

    def paint(self, painter, option, widget) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(0, 0, self.w, self.h)
        shape = self._shape_path(rect)

        # Hover/selection glow
        if self._hover or self.isSelected():
            glow = QColor(self.base_color)
            glow.setAlpha(60)
            painter.setPen(QPen(glow, 4))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.drawPath(shape)

        # Main fill
        painter.setPen(QPen(self.base_color, 2.4))
        painter.setBrush(QBrush(QColor("#161b22")))
        painter.drawPath(shape)

        # Küçük düğümler (merge / connector) yalnızca daire
        if self.small:
            return

        # Alt-yordam çift kenar görseli
        if self.kind == "subroutine":
            inner = QRectF(rect.x() + 6, rect.y() + 6, rect.width() - 12, rect.height() - 12)
            path2 = QPainterPath()
            path2.addRoundedRect(inner, 10, 10)
            painter.setPen(QPen(self.base_color, 1.2))
            painter.drawPath(path2)

        # Icon
        icon = KIND_ICON.get(self.kind, "")
        painter.setPen(self.base_color)
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        icon_rect = QRectF(12, 8, 32, 32)
        painter.drawText(icon_rect, Qt.AlignCenter, icon)

        # Title
        title = self.node.label or self.kind.capitalize()
        words = title.split(" ")
        first_line = words[0] if words else title
        second_line = " ".join(words[1:]) if len(words) > 1 else ""

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_rect = QRectF(52, 6, self.w - 62, 24)
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, self._elide(first_line, title_rect, painter))

        # Subtitle
        if second_line:
            painter.setPen(QColor("#c9d1d9"))
            painter.setFont(QFont("Segoe UI", 11))
            sub_rect = QRectF(52, 30, self.w - 62, 20)
            painter.drawText(sub_rect, Qt.AlignVCenter | Qt.AlignLeft, self._elide(second_line, sub_rect, painter))

        # Line number
        if self.node.line:
            painter.setPen(QColor("#484f58"))
            painter.setFont(QFont("Segoe UI", 9))
            info_rect = QRectF(12, self.h - 20, self.w - 24, 16)
            painter.drawText(info_rect, Qt.AlignRight | Qt.AlignVCenter, f"Ln {self.node.line}")

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
            skew = 24
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
        path.addRoundedRect(rect, 14, 14)
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
    """Professional flowchart view — large nodes, high contrast, zoom/fit/reset."""

    nodeClicked = Signal(int)
    nodeDoubleClicked = Signal(int, str)
    graphToPython = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setInteractive(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self._graph: FlowGraph | None = None
        self._pan_active = False
        self._pan_start: QPoint | None = None
        self._drag_mode = False
        self._build_tools()

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.1 if delta > 0 else 1.0 / 1.1
        self._apply_zoom(factor)

    def _apply_zoom(self, factor: float) -> None:
        cur = self.transform()
        new_scale = cur.m11() * factor
        if 0.2 <= new_scale <= 6.0:
            self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._pan_active = True
            self._pan_start = event.position().toPoint()
            self._drag_mode = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
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

    def _build_tools(self) -> None:
        from ..resources.icons import icon

        self._tools = QWidget(self)
        lay = QVBoxLayout(self._tools)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)
        for name, slot, tip in (
            ("zoom_in",  self.zoom_in,  "Yakınlaştır"),
            ("zoom_out", self.zoom_out, "Uzaklaştır"),
            ("fit",      self.fit_view, "Sığdır"),
            ("reset",    self.reset_view,"Sıfırla"),
            ("code_to_flow", self._to_python, "Flowchart → Python"),
        ):
            b = QPushButton()
            b.setObjectName("Flat")
            b.setIcon(icon(name, "#c9d1d9", 20))
            b.setFixedSize(38, 38)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            lay.addWidget(b)
        self._tools.setStyleSheet("""
            QWidget { background-color: #161b22; border: 1px solid #21262d; border-radius: 8px; }
            QPushButton#Flat { background-color: transparent; border: none; border-radius: 6px; padding: 6px; }
            QPushButton#Flat:hover { background-color: #21262d; }
        """)
        self._tools.setGeometry(self.width() - 52, self.height() - 220, 38, 200)
        self._tools.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_tools"):
            self._tools.setGeometry(self.width() - 52, self.height() - 220, 38, 200)

    def drawBackground(self, painter, rect) -> None:
        super().drawBackground(painter, rect)
        painter.fillRect(rect, QColor("#0d1117"))
        grid = 32
        pen = QPen(QColor("#161b22"))
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
        for n in graph.nodes:
            item = NodeItem(n)
            self.scene().addItem(item)
            items[n.id] = item

        for e in graph.edges:
            src = items.get(e.src)
            dst = items.get(e.dst)
            if not src or not dst:
                continue
            self._add_edge(src, dst, e.label, e.back)

        r = self.scene().itemsBoundingRect().adjusted(-80, -80, 80, 80)
        self.scene().setSceneRect(r)
        QTimer.singleShot(50, self.fit_view)

    def _add_edge(self, src: NodeItem, dst: NodeItem, label: str, back: bool) -> None:
        if back:
            start = QPointF(src.x() + 2, src.y() + src.h / 2)
            end = QPointF(dst.x() + 2, dst.y() - dst.h / 2)
            path = QPainterPath(start)
            midx = min(start.x(), end.x()) - 80
            ctrl1 = QPointF(midx, start.y())
            ctrl2 = QPointF(midx, end.y())
            path.cubicTo(ctrl1, ctrl2, end)
            self.scene().addPath(path, QPen(QColor("#6e7681"), 2.0))
            self._arrow(end, ctrl2, QColor("#6e7681"))
        else:
            start = QPointF(src.x() + src.w / 2, src.y() + src.h)
            end = QPointF(dst.x() + dst.w / 2, dst.y())
            line = QLineF(start, end)
            self.scene().addLine(line, QPen(QColor("#6e7681"), 2.0))
            self._arrow(end, start, QColor("#6e7681"))
        if label:
            mid = (start + end) / 2
            txt = self.scene().addText(label)
            txt.setDefaultTextColor(QColor("#c9d1d9"))
            txt.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            txt.setPos(mid.x() + 8, mid.y() - 10)
            txt.setZValue(1)

    def _arrow(self, tip: QPointF, from_point: QPointF, color: QColor) -> None:
        angle = math.atan2(tip.y() - from_point.y(), tip.x() - from_point.x())
        size = 12
        a1 = angle + math.radians(150)
        a2 = angle - math.radians(150)
        p1 = tip - QPointF(size * math.cos(a1), size * math.sin(a1))
        p2 = tip - QPointF(size * math.cos(a2), size * math.sin(a2))
        poly = QPolygonF([tip, p1, p2])
        self.scene().addPolygon(poly, QPen(color, 1.6), QBrush(color))

    def zoom_in(self) -> None:
        self.scale(1.2, 1.2)

    def zoom_out(self) -> None:
        self.scale(1 / 1.2, 1 / 1.2)

    def reset_view(self) -> None:
        self.resetTransform()
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

    def _to_python(self) -> None:
        self.graphToPython.emit()

    def select_node_by_line(self, line: int) -> None:
        if self._graph is None:
            return
        for item in self.scene().items():
            if hasattr(item, "node") and getattr(item.node, "line", 0) == line:
                self.scene().clearSelection()
                item.setSelected(True)
                self.ensureCursorVisible(item)
                return
