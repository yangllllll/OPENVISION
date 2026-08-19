"""工具箱面板 - 显示可用插件列表，支持拖拽到画布"""

from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag, QFont, QColor, QPixmap, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QHeaderView, QApplication,
)

from app.plugin_system.manager import PluginManager

MIME_PLUGIN_ID = "application/x-openvision-plugin-id"


class DraggableTreeWidget(QTreeWidget):
    """支持拖拽插件ID到画布的树形控件"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item is None:
            return

        plugin_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not plugin_id:
            return

        # 创建拖拽
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_PLUGIN_ID, plugin_id.encode())
        drag.setMimeData(mime)

        # 拖拽预览
        pixmap = QPixmap(140, 28)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 120, 215))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 140, 28, 6, 6)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        painter.drawText(0, 0, 140, 28, Qt.AlignmentFlag.AlignCenter, item.text(0))
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        drag.exec(Qt.DropAction.CopyAction)


class ToolboxPanel(QWidget):
    """工具箱面板"""

    plugin_double_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_plugins()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("  工具箱")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        title.setStyleSheet("""
            QLabel {
                background: #2d2d30; color: #e0e0e0;
                padding: 8px 4px; border-bottom: 1px solid #3e3e42;
            }
        """)
        layout.addWidget(title)

        self._tree = DraggableTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setDragEnabled(True)
        self._tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self._tree.setStyleSheet("""
            QTreeWidget {
                background: #252526; color: #cccccc; border: none;
                font-size: 12px; font-family: "Microsoft YaHei";
            }
            QTreeWidget::item {
                padding: 4px 2px;
            }
            QTreeWidget::item:hover {
                background: #2a2d2e;
            }
            QTreeWidget::item:selected {
                background: #094771;
            }
        """)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._tree)

    def _load_plugins(self):
        manager = PluginManager()
        manager.reload_all()

        for category in manager.get_categories():
            cat_item = QTreeWidgetItem(self._tree)
            cat_item.setText(0, category)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            cat_item.setFont(0, QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            cat_item.setForeground(0, QColor(200, 200, 200))

            plugins = manager.get_plugins_by_category(category)
            for pc in plugins:
                item = QTreeWidgetItem(cat_item)
                item.setText(0, pc.plugin_name)
                item.setToolTip(0, pc.plugin_description)
                item.setData(0, Qt.ItemDataRole.UserRole, pc.plugin_id)
                item.setFont(0, QFont("Microsoft YaHei", 9))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)

            self._tree.expandItem(cat_item)

    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        plugin_id = item.data(0, Qt.ItemDataRole.UserRole)
        if plugin_id:
            self.plugin_double_clicked.emit(plugin_id)

    def refresh(self):
        self._tree.clear()
        self._load_plugins()