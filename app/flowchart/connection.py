"""连接线图形项 - 节点之间的连线"""

from __future__ import annotations
import math
from typing import Optional

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsPathItem,
    QStyleOptionGraphicsItem, QWidget, QGraphicsSceneMouseEvent,
)

from app.flowchart.port import PortItem


class ConnectionItem(QGraphicsPathItem):
    """连接线图形项"""

    def __init__(self, source_port: PortItem, target_port: Optional[PortItem] = None):
        super().__init__()
        self.source_port = source_port
        self.target_port = target_port
        self._temp_end = QPointF()
        self._is_temp = target_port is None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(0)

        self.setPen(QPen(QColor(200, 200, 200, 180), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))

        self.update_path()

    def set_temp_end(self, pos: QPointF):
        self._temp_end = pos
        self.update_path()

    def finalize(self, target_port: PortItem):
        self.target_port = target_port
        self._is_temp = False
        self.update_path()

    def update_path(self):
        start = self.source_port.center_in_scene()
        self.setPos(0, 0)

        if self._is_temp:
            end = self._temp_end
        elif self.target_port:
            end = self.target_port.center_in_scene()
        else:
            return

        path = QPainterPath()
        path.moveTo(start)

        dx = abs(end.x() - start.x()) * 0.5
        ctrl1 = QPointF(start.x() + dx, start.y())
        ctrl2 = QPointF(end.x() - dx, end.y())
        path.cubicTo(ctrl1, ctrl2, end)

        self.setPath(path)

        if self._is_temp:
            self.setPen(QPen(QColor(255, 255, 255, 120), 2, Qt.PenStyle.DashLine))
        elif self.isSelected():
            self.setPen(QPen(QColor(0, 180, 255), 2.5))
        else:
            self.setPen(QPen(QColor(200, 200, 200, 180), 2))

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        super().paint(painter, option, widget)

    def shape(self):
        path = self.path()
        if path:
            stroker = QPainterPath()
            stroker.addPath(path)
            return stroker
        return super().shape()

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-5, -5, 5, 5)