"""端口图形项 - 节点上的输入/输出端口"""

from typing import Callable, Optional

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QGraphicsItem, QGraphicsSceneMouseEvent, QStyleOptionGraphicsItem, QWidget


class PortItem(QGraphicsItem):
    """端口图形项（QGraphicsItem 不支持 Signal，使用回调代替）"""

    PORT_RADIUS = 6.0

    def __init__(self, port_name: str, port_type_str: str, is_input: bool, parent_node: "NodeItem"):
        super().__init__(parent_node)
        self.port_name = port_name
        self.port_type = port_type_str
        self.is_input = is_input
        self.parent_node = parent_node
        self.connected_ports: list["PortItem"] = []
        self.on_drag_started: Optional[Callable] = None
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setZValue(1)

    def boundingRect(self) -> QRectF:
        return QRectF(-self.PORT_RADIUS - 2, -self.PORT_RADIUS - 2,
                      (self.PORT_RADIUS + 2) * 2, (self.PORT_RADIUS + 2) * 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        type_colors = {
            "image": QColor(0, 180, 0),
            "region": QColor(0, 120, 200),
            "number": QColor(200, 120, 0),
            "string": QColor(150, 50, 200),
            "point": QColor(0, 160, 160),
            "matrix": QColor(160, 0, 100),
            "any": QColor(128, 128, 128),
        }

        color = type_colors.get(self.port_type, QColor(128, 128, 128))

        rect = QRectF(-self.PORT_RADIUS, -self.PORT_RADIUS, self.PORT_RADIUS * 2, self.PORT_RADIUS * 2)

        if self.connected_ports:
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(130), 1.5))
        else:
            painter.setBrush(QBrush(color.lighter(160)))
            painter.setPen(QPen(color, 1.5))

        painter.drawEllipse(rect)

        if self.isUnderMouse():
            painter.setBrush(QBrush(color.lighter(180)))
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawEllipse(rect)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.on_drag_started:
                self.on_drag_started(self)
            event.accept()
        else:
            super().mousePressEvent(event)

    def center_in_scene(self) -> QPointF:
        return self.mapToScene(QPointF(0, 0))

    def is_connectable_with(self, other: "PortItem") -> bool:
        if other is self:
            return False
        if other.parent_node is self.parent_node:
            return False
        if self.is_input == other.is_input:
            return False
        if self.port_type != other.port_type and self.port_type != "any" and other.port_type != "any":
            return False
        return True