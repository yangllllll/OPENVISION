"""节点图形项 - 流程图中的工具节点"""

from __future__ import annotations
import time
from typing import Callable, Optional

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem, QWidget, QGraphicsSceneMouseEvent,
)

from app.flowchart.port import PortItem
from app.plugin_system.base import PluginBase


class NodeItem(QGraphicsItem):
    """流程图节点（QGraphicsItem 不支持 Signal，使用回调代替）"""

    def __init__(self, plugin: PluginBase, node_id: str):
        super().__init__()
        self.plugin = plugin
        self.node_id = node_id
        self.plugin_id = plugin.plugin_id
        self.plugin_name = plugin.plugin_name

        self.input_ports: list[PortItem] = []
        self.output_ports: list[PortItem] = []
        self._text_item: QGraphicsTextItem | None = None

        # 回调函数（由场景设置）
        self.on_selected: Optional[Callable] = None
        self.on_moved: Optional[Callable] = None
        self.on_double_clicked: Optional[Callable] = None

        self._width = 140
        self._header_height = 28
        self._port_row_height = 22
        self._port_spacing = 4

        self._last_click_time = 0.0
        self._status: Optional[bool] = None  # None=未执行, True=OK, False=NG

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(2)
        self.setAcceptHoverEvents(True)

        self._build_ports()
        self._update_geometry()

    def _build_ports(self):
        in_ports = self.plugin.input_ports()
        out_ports = self.plugin.output_ports()

        for pdef in in_ports:
            port = PortItem(pdef.name, pdef.port_type.value, True, self)
            self.input_ports.append(port)

        for pdef in out_ports:
            port = PortItem(pdef.name, pdef.port_type.value, False, self)
            self.output_ports.append(port)

    def _update_geometry(self):
        max_ports = max(len(self.input_ports), len(self.output_ports), 1)
        self._height = self._header_height + max_ports * self._port_row_height + self._port_spacing * 2

        # 设置端口位置（在初始化时确定，不依赖 paint 延迟调用）
        for i, port in enumerate(self.input_ports):
            y = self._header_height + self._port_spacing + i * self._port_row_height + self._port_row_height / 2
            port.setPos(0, y)
        for i, port in enumerate(self.output_ports):
            y = self._header_height + self._port_spacing + i * self._port_row_height + self._port_row_height / 2
            port.setPos(self._width, y)

    def set_status(self, ok: Optional[bool]):
        """设置执行状态指示灯: None=未执行, True=绿点, False=红点"""
        self._status = ok
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isSelected():
            header_color = QColor(0, 120, 215)
            body_color = QColor(45, 45, 50)
            border_color = QColor(0, 160, 255)
            border_width = 2.0
        else:
            header_color = QColor(60, 60, 65)
            body_color = QColor(35, 35, 38)
            border_color = QColor(80, 80, 85)
            border_width = 1.0

        # 阴影
        shadow_path = QPainterPath()
        shadow_rect = QRectF(3, 3, self._width, self._height)
        shadow_path.addRoundedRect(shadow_rect, 6, 6)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 60))

        # 主体背景
        body_path = QPainterPath()
        body_path.addRoundedRect(QRectF(0, 0, self._width, self._height), 6, 6)
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(body_color)
        painter.drawPath(body_path)

        # 标题栏
        header_path = QPainterPath()
        header_path.moveTo(6, self._header_height)
        header_path.lineTo(0, self._header_height)
        header_path.lineTo(0, 6)
        header_path.arcTo(0, 0, 12, 12, 180, -90)
        header_path.lineTo(self._width - 6, 0)
        header_path.arcTo(self._width - 12, 0, 12, 12, 90, -90)
        header_path.lineTo(self._width, self._header_height)
        header_path.closeSubpath()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(header_color)
        painter.drawPath(header_path)

        # 标题文字
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        name = self.node_id[:12]
        painter.drawText(QRectF(6, 0, self._width - 24, self._header_height),
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)

        # 状态指示灯（右上角）
        if self._status is not None:
            r = 5
            cx = self._width - 14
            cy = self._header_height / 2
            dot_color = QColor(76, 175, 80) if self._status else QColor(244, 67, 54)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # 输入/输出标签和端口
        font = QFont("Microsoft YaHei", 8)
        painter.setFont(font)

        for i, port in enumerate(self.input_ports):
            y = self._header_height + self._port_spacing + i * self._port_row_height + self._port_row_height / 2
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(QRectF(14, y - 9, self._width / 2 - 18, 18),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, port.port_name)

        for i, port in enumerate(self.output_ports):
            y = self._header_height + self._port_spacing + i * self._port_row_height + self._port_row_height / 2
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(QRectF(self._width / 2 + 4, y - 9, self._width / 2 - 18, 18),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, port.port_name)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.on_moved:
                self.on_moved(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            now = time.time()
            if now - self._last_click_time < 0.4:
                if self.on_double_clicked:
                    self.on_double_clicked(self)
            else:
                if self.on_selected:
                    self.on_selected(self)
            self._last_click_time = now