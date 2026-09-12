"""Visual block editor — drag-and-drop code blocks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from PySide6.QtCore import QMimeData, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QDrag, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSceneDragDropEvent,
    QGraphicsView,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

BlockType = Literal[
    "event",
    "action",
    "variable",
    "control",
    "sensor",
    "operator",
    "logic",
    "flow",
]

KIND_COLORS = {
    "event": "#0078d4",
    "action": "#107c10",
    "variable": "#d4a017",
    "control": "#c586c0",
    "sensor": "#4ec9b0",
    "operator": "#d97706",
    "logic": "#dc2626",
    "flow": "#888888",
}


@dataclass
class BlockSpec:
    id: str
    type: BlockType
    label: str
    color: str
    fields: list[dict[str, Any]] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: int = 1


SPECS: list[BlockSpec] = [
    BlockSpec("start", "event", "Başla", "#0078d4"),
    BlockSpec("print", "action", "Yazdır", "#107c10", fields=[{"name": "text", "type": "string"}]),
    BlockSpec("input", "action", "Girdi", "#107c10", fields=[{"name": "var", "type": "string"}], inputs=["prompt"]),
    BlockSpec("assign", "variable", "Ata", "#d4a017", fields=[{"name": "name", "type": "string"}, {"name": "value", "type": "expression"}], inputs=["value"]),
    BlockSpec("if", "control", "Eğer", "#c586c0", fields=[{"name": "condition", "type": "boolean"}], outputs=2),
    BlockSpec("while", "control", "Döngü", "#c586c0", fields=[{"name": "condition", "type": "boolean"}]),
    BlockSpec("for", "control", "Döngü (for)", "#c586c0", fields=[{"name": "var", "type": "string"}, {"name": "iter", "type": "expression"}]),
    BlockSpec("add", "operator", "Topla", "#d97706", inputs=["a", "b"]),
    BlockSpec("sub", "operator", "Çıkar", "#d97706", inputs=["a", "b"]),
    BlockSpec("mul", "operator", "Çarp", "#d97706", inputs=["a", "b"]),
    BlockSpec("div", "operator", "Böl", "#d97706", inputs=["a", "b"]),
    BlockSpec("equals", "logic", "Eşit", "#dc2626", inputs=["a", "b"]),
    BlockSpec("gt", "logic", "Büyük", "#dc2626", inputs=["a", "b"]),
    BlockSpec("lt", "logic", "Küçük", "#dc2626", inputs=["a", "b"]),
    BlockSpec("and", "logic", "VE", "#dc2626", inputs=["a", "b"]),
    BlockSpec("or", "logic", "VEYA", "#dc2626", inputs=["a", "b"]),
    BlockSpec("not", "logic", "DEĞİL", "#dc2626", inputs=["a"]),
    BlockSpec("string", "sensor", "Metin", "#4ec9b0", fields=[{"name": "value", "type": "string"}]),
    BlockSpec("number", "sensor", "Sayı", "#4ec9b0", fields=[{"name": "value", "type": "number"}]),
]


class _BlockItem(QGraphicsItem):
    """Visual block on canvas."""

    WIDTH = 140
    HEADER_H = 26
    FIELD_H = 24
    PADDING = 6
    PORT_R = 6

    def __init__(self, spec: BlockSpec, parent=None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.fields_values: dict[str, str] = {f["name"]: "" for f in spec.fields}
        self.input_values: dict[str, str] = {name: "" for name in spec.inputs}
        self._hover = False
        self._selected = False
        self._connectors: list[_ConnectorItem] = []
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        h = self._total_height()
        return QRectF(-self.PORT_R, -self.PORT_R, self.WIDTH + 2 * self.PORT_R, h + 2 * self.PORT_R)

    def _total_height(self) -> int:
        return self.HEADER_H + self.FIELD_H * max(len(self.spec.fields), len(self.spec.inputs))

    def paint(self, painter: QPainter, option, widget) -> None:  # noqa: ARG002
        painter.setRenderHint(QPainter.Antialiasing)
        h = self._total_height()
        base = QColor(self.spec.color)
        dark = QColor(self.spec.color)
        dark.setAlpha(180)

        path = self._body_path(h)
        painter.setPen(QPen(dark, 2))
        painter.setBrush(QBrush(base))
        painter.drawPath(path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRect(0, 0, self.WIDTH, self.HEADER_H)
        painter.setPen(QColor("#1a1a1a"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(self.PADDING, 2, self.WIDTH - self.PADDING, self.HEADER_H - 2, Qt.AlignCenter, self.spec.label)

        painter.setFont(QFont("Segoe UI", 8))
        field_y = self.HEADER_H + 4
        for f in self.spec.fields:
            painter.setPen(QColor("#cccccc"))
            painter.drawText(self.PADDING, field_y, 60, self.FIELD_H, Qt.AlignVCenter, f["name"] + ":")
            val = self.fields_values.get(f["name"], "")
            painter.setPen(QColor("#ffffff"))
            painter.drawText(64, field_y, self.WIDTH - 68, self.FIELD_H, Qt.AlignVCenter | Qt.AlignRight, val or "...")
            field_y += self.FIELD_H

        for name in self.spec.inputs:
            painter.setPen(QColor("#cccccc"))
            painter.drawText(self.PADDING, field_y, 60, self.FIELD_H, Qt.AlignVCenter, name + ":")
            val = self.input_values.get(name, "")
            painter.setPen(QColor("#ffffff"))
            painter.drawText(64, field_y, self.WIDTH - 68, self.FIELD_H, Qt.AlignVCenter | Qt.AlignRight, val or "...")
            field_y += self.FIELD_H

        if self._selected:
            painter.setPen(QPen(QColor("#0078d4"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(0, 0, self.WIDTH, h)

    def _body_path(self, h: int) -> QPainterPath:
        r = 8
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.WIDTH, h, r, r)
        return path

    def hoverEnterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):  # noqa: ANN001
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for c in self._connectors:
                c.update_path()
        return super().itemChange(change, value)


class _ConnectorItem(QGraphicsPathItem):
    """Connection line between blocks."""

    def __init__(self, src: _BlockItem, dst: _BlockItem) -> None:
        super().__init__()
        self.src = src
        self.dst = dst
        src._connectors.append(self)
        dst._connectors.append(self)
        self.setPen(QPen(QColor("#555555"), 2))
        self.setZValue(-1)
        self.update_path()

    def update_path(self) -> None:
        if self.scene() is None:
            return
        start = self.src.scenePos() + QPointF(self.src.WIDTH / 2, self.src._total_height())
        end = self.dst.scenePos() + QPointF(self.dst.WIDTH / 2, 0)
        path = QPainterPath()
        mid = (start.y() + end.y()) / 2
        path.moveTo(start)
        path.cubicTo(start.x(), mid, end.x(), mid, end.x(), end.y())
        self.setPath(path)

    def paint(self, painter: QPainter, option, widget) -> None:  # noqa: ARG002
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(self.pen())
        painter.drawPath(self.path())


class BlockCanvas(QGraphicsView):
    """Drag-drop canvas for code blocks."""

    codeChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setAcceptDrops(True)
        self._block_specs = {s.id: s for s in SPECS}
        self._items: list[_BlockItem] = []
        self._start_item: _BlockItem | None = None
        self._last_code: str = ""

    def add_block(self, spec_id: str, pos: QPointF) -> _BlockItem | None:
        spec = self._block_specs.get(spec_id)
        if spec is None:
            return None
        item = _BlockItem(spec)
        item.setPos(pos)
        self.scene().addItem(item)
        self._items.append(item)
        if spec.id == "start":
            self._start_item = item
        self._update_code()
        return item

    def dragEnterEvent(self, event):  # noqa: ANN001
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):  # noqa: ANN001
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):  # noqa: ANN001
        text = event.mimeData().text()
        pos = self.mapToScene(event.position().toPoint())
        self.add_block(text, pos)
        event.acceptProposedAction()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, _BlockItem):
                for c in list(item._connectors):
                    self.scene().removeItem(c)
                item._connectors.clear()
                self.scene().removeItem(item)
                self._items.remove(item)
                if item is self._start_item:
                    self._start_item = None
                self._update_code()
                event.accept()
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event) -> None:
        factor = 1.08 if event.angleDelta().y() > 0 else 1.0 / 1.08
        self.scale(factor, factor)
        event.accept()

    def _update_code(self) -> None:
        if self._start_item is None:
            self._last_code = ""
            self.codeChanged.emit("")
            return
        code = self._generate_from(self._start_item, set())
        self._last_code = code
        self.codeChanged.emit(code)

    def _generate_from(self, item: _BlockItem, visited: set[str], indent: int = 0) -> str:
        if id(item) in visited:
            return ""
        visited.add(id(item))
        pad = "    " * indent
        lines: list[str] = []
        spec = item.spec

        if spec.id == "start":
            children = self._children_of(item)
            for child in children:
                lines.append(self._generate_from(child, visited, indent))
            return "\n".join(lines)

        if spec.id == "print":
            text = item.fields_values.get("text", "")
            if text.startswith('"') or text.startswith("'"):
                lines.append(f'{pad}print({text})')
            else:
                lines.append(f'{pad}print({text})')
            return "\n".join(lines) if lines else ""

        if spec.id == "assign":
            name = item.fields_values.get("name", "x")
            val = item.input_values.get("value", "0")
            lines.append(f'{pad}{name} = {val}')
            return "\n".join(lines)

        if spec.id == "if":
            cond = item.fields_values.get("condition", "True")
            lines.append(f"{pad}if {cond}:")
            children = self._children_of(item)
            for child in children:
                lines.append(self._generate_from(child, visited, indent + 1))
            return "\n".join(lines)

        if spec.id == "while":
            cond = item.fields_values.get("condition", "True")
            lines.append(f"{pad}while {cond}:")
            children = self._children_of(item)
            for child in children:
                lines.append(self._generate_from(child, visited, indent + 1))
            return "\n".join(lines)

        if spec.id == "for":
            var = item.fields_values.get("var", "x")
            iterable = item.input_values.get("iter", "range(10)")
            lines.append(f"{pad}for {var} in {iterable}:")
            children = self._children_of(item)
            for child in children:
                lines.append(self._generate_from(child, visited, indent + 1))
            return "\n".join(lines)

        if spec.id == "input":
            var = item.fields_values.get("var", "x")
            prompt = item.input_values.get("prompt", '""')
            lines.append(f'{pad}{var} = input({prompt})')
            return "\n".join(lines)

        if spec.id == "add":
            a = item.input_values.get("a", "0")
            b = item.input_values.get("b", "0")
            lines.append(f"{pad}{a} + {b}")
            return "\n".join(lines)

        if spec.id == "sub":
            a = item.input_values.get("a", "0")
            b = item.input_values.get("b", "0")
            lines.append(f"{pad}{a} - {b}")
            return "\n".join(lines)

        if spec.id == "mul":
            a = item.input_values.get("a", "0")
            b = item.input_values.get("b", "0")
            lines.append(f"{pad}{a} * {b}")
            return "\n".join(lines)

        if spec.id == "div":
            a = item.input_values.get("a", "0")
            b = item.input_values.get("b", "0")
            lines.append(f"{pad}{a} / {b}")
            return "\n".join(lines)

        if spec.id == "equals":
            a = item.input_values.get("a", "0")
            b = item.input_values.get("b", "0")
            lines.append(f"{pad}{a} == {b}")
            return "\n".join(lines)

        if spec.id == "gt":
            a = item.input_values.get("a", "0")
            b = item.input_values.get("b", "0")
            lines.append(f"{pad}{a} > {b}")
            return "\n".join(lines)

        if spec.id == "lt":
            a = item.input_values.get("a", "0")
            b = item.input_values.get("b", "0")
            lines.append(f"{pad}{a} < {b}")
            return "\n".join(lines)

        if spec.id == "and":
            a = item.input_values.get("a", "True")
            b = item.input_values.get("b", "True")
            lines.append(f"{pad}{a} and {b}")
            return "\n".join(lines)

        if spec.id == "or":
            a = item.input_values.get("a", "True")
            b = item.input_values.get("b", "True")
            lines.append(f"{pad}{a} or {b}")
            return "\n".join(lines)

        if spec.id == "not":
            a = item.input_values.get("a", "True")
            lines.append(f"{pad}not {a}")
            return "\n".join(lines)

        if spec.id == "string":
            val = item.fields_values.get("value", "")
            lines.append(f'{pad}"{val}"')
            return "\n".join(lines)

        if spec.id == "number":
            val = item.fields_values.get("value", "0")
            lines.append(f"{pad}{val}")
            return "\n".join(lines)

        return ""

    def _children_of(self, parent: _BlockItem) -> list[_BlockItem]:
        children: list[_BlockItem] = []
        px = parent.scenePos().x()
        py = parent.scenePos().y() + parent._total_height()
        for item in self._items:
            if item is parent:
                continue
            ip = item.scenePos()
            if abs(ip.x() - px) < 30 and ip.y() > py:
                children.append(item)
        children.sort(key=lambda it: it.scenePos().y())
        return children


class BlockPalette(QListWidget):
    """Draggable block types."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setViewMode(QListWidget.ListMode)
        for spec in SPECS:
            item = QListWidgetItem(spec.label)
            item.setData(Qt.ItemDataRole.UserRole, spec.id)
            item.setBackground(QBrush(QColor(spec.color)))
            item.setForeground(QBrush(QColor("#ffffff")))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.addItem(item)

    def startDrag(self, supportedActions):  # noqa: ANN001
        drag = QDrag(self)
        item = self.currentItem()
        mime = QMimeData()
        mime.setText(item.data(Qt.ItemDataRole.UserRole))
        drag.setMimeData(mime)
        drag.exec(supportedActions)


class BlockEditorWidget(QWidget):
    """Combined palette + canvas block editor."""

    codeChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.palette = BlockPalette()
        self.canvas = BlockCanvas()
        self.canvas.codeChanged.connect(self.codeChanged)
        lay.addWidget(self.palette, 1)
        lay.addWidget(self.canvas, 4)

    def generate_code(self) -> str:
        return getattr(self.canvas, "_last_code", "") or ""

    def set_code(self, code: str) -> None:
        self.canvas.scene().clear()
        self.canvas._items.clear()
        self.canvas._start_item = None
