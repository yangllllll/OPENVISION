"""流程图画布 - QGraphicsScene + QGraphicsView"""

from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen, QPainterPath,
)
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView,
    QGraphicsSceneMouseEvent,
)

from app.flowchart.node import NodeItem
from app.flowchart.port import PortItem
from app.flowchart.connection import ConnectionItem
from app.plugin_system.manager import PluginManager
from app.panels.toolbox import MIME_PLUGIN_ID


class FlowchartScene(QGraphicsScene):
    """流程图场景"""

    node_added = Signal(NodeItem)
    node_removed = Signal(str)
    node_selected = Signal(object)
    node_deselected = Signal()
    connection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging_port: Optional[PortItem] = None
        self._temp_connection: Optional[ConnectionItem] = None
        self._connections: list[ConnectionItem] = []
        self._nodes: dict[str, NodeItem] = {}
        self._node_counter: dict[str, int] = {}

        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setBackgroundBrush(QColor(30, 30, 32))

        self._draw_grid()

    def _draw_grid(self):
        """绘制背景网格"""
        pen = QPen(QColor(45, 45, 48), 0.5)
        grid_size = 20

        path = QPainterPath()
        for x in range(-5000, 5001, grid_size):
            path.moveTo(x, -5000)
            path.lineTo(x, 5000)
        for y in range(-5000, 5001, grid_size):
            path.moveTo(-5000, y)
            path.lineTo(5000, y)

        self.addPath(path, pen).setZValue(-10)

    def add_plugin_node(self, plugin_id: str, pos: QPointF = QPointF(0, 0)) -> Optional[NodeItem]:
        """添加一个插件节点到画布"""
        manager = PluginManager()
        pc = manager._plugin_classes.get(plugin_id)
        plugin_name = pc.plugin_name if pc else plugin_id
        self._node_counter[plugin_name] = self._node_counter.get(plugin_name, 0) + 1
        node_id = f"{plugin_name}_{self._node_counter[plugin_name]}"
        return self._add_node(plugin_id, node_id, pos)

    def _add_node(self, plugin_id: str, node_id: str, pos: QPointF) -> Optional[NodeItem]:
        """添加节点（可指定ID，用于加载）"""
        manager = PluginManager()
        plugin = manager.create_instance(plugin_id)
        if plugin is None:
            return None

        node = NodeItem(plugin, node_id)
        node.setPos(pos)
        node.on_selected = self._on_node_selected
        node.on_moved = self._on_node_moved
        node.on_double_clicked = None  # 由外部设置

        for port in node.input_ports + node.output_ports:
            port.on_drag_started = self.port_drag_started

        self.addItem(node)
        self._nodes[node_id] = node
        self.node_added.emit(node)
        return node

    def remove_node(self, node_id: str):
        """移除节点"""
        node = self._nodes.get(node_id)
        if node is None:
            return

        # 移除相关连接
        for conn in list(self._connections):
            if conn.source_port.parent_node is node:
                self._remove_connection(conn)
            elif conn.target_port and conn.target_port.parent_node is node:
                self._remove_connection(conn)

        self.removeItem(node)
        del self._nodes[node_id]
        self.node_removed.emit(node_id)

    def _on_node_selected(self, node: NodeItem):
        self.node_selected.emit(node)

    def _on_node_moved(self, node: NodeItem):
        """节点移动时更新连接线"""
        for conn in self._connections:
            if conn.source_port.parent_node is node:
                conn.update_path()
            if conn.target_port and conn.target_port.parent_node is node:
                conn.update_path()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else None)
            if item is None:
                self.node_deselected.emit()
                for view in self.views():
                    view.clear_selection()

        super().mousePressEvent(event)

    def port_drag_started(self, port: PortItem):
        """开始从端口拖拽创建连接"""
        self._dragging_port = port
        self._temp_connection = ConnectionItem(port, None)
        self._temp_connection.set_temp_end(port.center_in_scene())
        self.addItem(self._temp_connection)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._temp_connection:
            self._temp_connection.set_temp_end(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._dragging_port and self._temp_connection:
            # 查找目标端口
            item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else None)
            target_port = None
            if isinstance(item, PortItem):
                target_port = item

            if target_port and self._dragging_port.is_connectable_with(target_port):
                self._finalize_connection(self._dragging_port, target_port)
            else:
                self._cancel_temp_connection()

        self._dragging_port = None
        self._temp_connection = None
        super().mouseReleaseEvent(event)

    def _finalize_connection(self, source: PortItem, target: PortItem):
        """完成连接"""
        # 检查是否已存在连接
        for conn in self._connections:
            if conn.source_port is source and conn.target_port is target:
                self._cancel_temp_connection()
                return

        # 如果target是输入端口，source必须是输出端口
        if target.is_input and not source.is_input:
            conn = self._temp_connection
            conn.finalize(target)
            source.connected_ports.append(target)
            target.connected_ports.append(source)
            self._connections.append(conn)
            self._temp_connection = None
            self.connection_changed.emit()
        elif source.is_input and not target.is_input:
            conn = self._temp_connection
            conn.finalize(source)
            target.connected_ports.append(source)
            source.connected_ports.append(target)
            self._connections.append(conn)
            self._temp_connection = None
            self.connection_changed.emit()
        else:
            self._cancel_temp_connection()

    def _cancel_temp_connection(self):
        if self._temp_connection:
            self.removeItem(self._temp_connection)
            self._temp_connection = None

    def _remove_connection(self, conn: ConnectionItem):
        if conn.source_port:
            for p in list(conn.source_port.connected_ports):
                if conn.target_port and p is conn.target_port:
                    conn.source_port.connected_ports.remove(p)
        if conn.target_port:
            for p in list(conn.target_port.connected_ports):
                if conn.source_port and p is conn.source_port:
                    conn.target_port.connected_ports.remove(p)
        self.removeItem(conn)
        if conn in self._connections:
            self._connections.remove(conn)
        self.connection_changed.emit()

    def remove_selected(self):
        """删除选中的项目"""
        for item in self.selectedItems():
            if isinstance(item, NodeItem):
                self.remove_node(item.node_id)
            elif isinstance(item, ConnectionItem):
                self._remove_connection(item)

    def get_connections(self) -> list[ConnectionItem]:
        return list(self._connections)

    def get_nodes(self) -> dict[str, NodeItem]:
        return dict(self._nodes)

    def clear_all(self):
        """清除所有内容"""
        self._connections.clear()
        for node_id in list(self._nodes.keys()):
            self.remove_node(node_id)
        self._nodes.clear()
        self._node_counter.clear()

    def to_dict(self) -> dict:
        """序列化整个流程图"""
        nodes_data = []
        for node_id, node in self._nodes.items():
            nodes_data.append({
                "id": node_id,
                "plugin_id": node.plugin_id,
                "x": node.pos().x(),
                "y": node.pos().y(),
                "params": node.plugin.get_params(),
                "extra": node.plugin.get_extra_data(),
            })

        connections_data = []
        for conn in self._connections:
            if conn.source_port and conn.target_port:
                connections_data.append({
                    "source_node": conn.source_port.parent_node.node_id,
                    "source_port": conn.source_port.port_name,
                    "target_node": conn.target_port.parent_node.node_id,
                    "target_port": conn.target_port.port_name,
                })

        return {
            "version": "1.0",
            "nodes": nodes_data,
            "connections": connections_data,
        }

    def from_dict(self, data: dict):
        """从字典加载流程图"""
        self.clear_all()

        # 加载节点
        for nd in data.get("nodes", []):
            node = self._add_node(
                nd["plugin_id"],
                nd["id"],
                QPointF(nd.get("x", 0), nd.get("y", 0))
            )
            if node is None:
                continue

            # 恢复参数
            for k, v in nd.get("params", {}).items():
                node.plugin.set_param(k, v)

            # 恢复扩展数据
            extra = nd.get("extra", {})
            if extra:
                node.plugin.set_extra_data(extra)

            # 同步计数器：解析 node_id 中的序号
            nid = nd["id"]
            if "_" in nid:
                try:
                    name_part, num_part = nid.rsplit("_", 1)
                    num = int(num_part)
                    self._node_counter[name_part] = max(self._node_counter.get(name_part, 0), num)
                except ValueError:
                    pass

        # 加载连接
        for cd in data.get("connections", []):
            src_node = self._nodes.get(cd["source_node"])
            tgt_node = self._nodes.get(cd["target_node"])
            if src_node is None or tgt_node is None:
                continue

            src_port = None
            tgt_port = None
            for p in src_node.output_ports:
                if p.port_name == cd["source_port"]:
                    src_port = p
                    break
            for p in tgt_node.input_ports:
                if p.port_name == cd["target_port"]:
                    tgt_port = p
                    break

            if src_port and tgt_port:
                conn = ConnectionItem(src_port, tgt_port)
                src_port.connected_ports.append(tgt_port)
                tgt_port.connected_ports.append(src_port)
                self._connections.append(conn)
                self.addItem(conn)

        self.connection_changed.emit()


class FlowchartView(QGraphicsView):
    """流程图视图"""

    def __init__(self, scene: FlowchartScene, parent=None):
        super().__init__(scene, parent)
        self._scene = scene
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self._zoom = 1.0

    def clear_selection(self):
        self._scene.clearSelection()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_PLUGIN_ID):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_PLUGIN_ID):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat(MIME_PLUGIN_ID):
            plugin_id = event.mimeData().data(MIME_PLUGIN_ID).data().decode()
            scene_pos = self.mapToScene(event.position().toPoint())
            self._scene.add_plugin_node(plugin_id, scene_pos)
            event.acceptProposedAction()
        else:
            event.ignore()

    def wheelEvent(self, event):
        factor = 1.15
        if event.angleDelta().y() > 0:
            if self._zoom < 3.0:
                self.scale(factor, factor)
                self._zoom *= factor
        else:
            if self._zoom > 0.2:
                self.scale(1 / factor, 1 / factor)
                self._zoom /= factor