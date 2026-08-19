"""主窗口 - VisionMaster风格界面"""

import json
import os
import numpy as np

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QKeySequence, QFont
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar,
    QDockWidget, QWidget, QVBoxLayout,
    QSplitter, QMessageBox, QFileDialog,
)

from app.flowchart.canvas import FlowchartScene, FlowchartView
from app.flowchart.node import NodeItem
from app.flowchart.engine import ExecutionEngine
from app.panels.toolbox import ToolboxPanel
from app.panels.properties import PropertiesPanel
from app.panels.preview import PreviewPanel
from app.panels.output import OutputPanel
from app.dialogs.line_finder_dialog import LineFinderDialog


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenVision - 工业视觉检测平台")
        self.resize(1400, 900)
        self.setMinimumSize(1024, 600)

        # 暗色主题
        self.setStyleSheet("""
            QMainWindow { background: #1e1e1e; }
            QMainWindow::separator { background: #3e3e42; width: 1px; height: 1px; }
            QDockWidget { background: #252526; titlebar-close-icon: url(none); }
            QDockWidget::title { background: #2d2d30; padding: 6px; border-bottom: 1px solid #3e3e42; }
            QToolBar { background: #2d2d30; border-bottom: 1px solid #3e3e42; spacing: 4px; padding: 2px; }
            QMenuBar { background: #2d2d30; color: #e0e0e0; border-bottom: 1px solid #3e3e42; }
            QMenuBar::item:selected { background: #094771; }
            QMenu { background: #2d2d30; color: #e0e0e0; border: 1px solid #3e3e42; }
            QMenu::item:selected { background: #094771; }
            QStatusBar { background: #007acc; color: white; font-family: "Microsoft YaHei"; }
            QSplitter::handle { background: #3e3e42; }
            QToolTip { background: #333; color: #ccc; border: 1px solid #555; }
        """)

        self._engine = ExecutionEngine()
        self._last_image: dict[str, any] = {}
        self._current_file: str | None = None

        self._setup_actions()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_central()
        self._setup_dock_widgets()
        self._setup_statusbar()

    def _setup_actions(self):
        self._act_new = QAction("新建(&N)", self)
        self._act_new.setShortcut(QKeySequence.StandardKey.New)
        self._act_new.triggered.connect(self._on_new)

        self._act_open = QAction("打开(&O)", self)
        self._act_open.setShortcut(QKeySequence.StandardKey.Open)
        self._act_open.triggered.connect(self._on_open)

        self._act_save = QAction("保存(&S)", self)
        self._act_save.setShortcut(QKeySequence.StandardKey.Save)
        self._act_save.triggered.connect(self._on_save)

        self._act_save_as = QAction("另存为...", self)
        self._act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._act_save_as.triggered.connect(self._on_save_as)

        self._act_run = QAction("运行(&R)", self)
        self._act_run.setShortcut(QKeySequence("F5"))
        self._act_run.triggered.connect(self._on_run)

        self._act_stop = QAction("停止", self)
        self._act_stop.setShortcut(QKeySequence("Shift+F5"))
        self._act_stop.triggered.connect(self._on_stop)

        self._act_delete = QAction("删除选中", self)
        self._act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self._act_delete.triggered.connect(self._on_delete)

        self._act_zoom_in = QAction("放大", self)
        self._act_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self._act_zoom_in.triggered.connect(lambda: self._view.scale(1.15, 1.15))

        self._act_zoom_out = QAction("缩小", self)
        self._act_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self._act_zoom_out.triggered.connect(lambda: self._view.scale(1 / 1.15, 1 / 1.15))

        self._act_fit = QAction("适应窗口", self)
        self._act_fit.setShortcut(QKeySequence("Ctrl+0"))
        self._act_fit.triggered.connect(self._on_fit)

        self._act_about = QAction("关于", self)
        self._act_about.triggered.connect(self._on_about)

        self._act_refresh_plugins = QAction("刷新插件", self)
        self._act_refresh_plugins.triggered.connect(self._on_refresh_plugins)

    def _setup_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件(&F)")
        file_menu.addAction(self._act_new)
        file_menu.addAction(self._act_open)
        file_menu.addAction(self._act_save)
        file_menu.addAction(self._act_save_as)
        file_menu.addSeparator()
        file_menu.addAction("退出(&X)", self.close)

        edit_menu = menu_bar.addMenu("编辑(&E)")
        edit_menu.addAction(self._act_delete)
        edit_menu.addSeparator()
        edit_menu.addAction(self._act_zoom_in)
        edit_menu.addAction(self._act_zoom_out)
        edit_menu.addAction(self._act_fit)

        run_menu = menu_bar.addMenu("运行(&R)")
        run_menu.addAction(self._act_run)
        run_menu.addAction(self._act_stop)

        tools_menu = menu_bar.addMenu("工具(&T)")
        tools_menu.addAction(self._act_refresh_plugins)

        help_menu = menu_bar.addMenu("帮助(&H)")
        help_menu.addAction(self._act_about)

    def _setup_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())

        for act in [self._act_new, self._act_open, self._act_save, None, self._act_run, self._act_stop, None, self._act_delete]:
            if act is None:
                toolbar.addSeparator()
            else:
                toolbar.addAction(act)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def _setup_central(self):
        self._scene = FlowchartScene()
        self._view = FlowchartView(self._scene, self)

        self._scene.node_selected.connect(self._on_node_selected)
        self._scene.node_deselected.connect(self._on_node_deselected)
        self._scene.node_added.connect(self._on_node_added)

        self.setCentralWidget(self._view)

    def _setup_dock_widgets(self):
        # 工具箱（左侧）
        self._toolbox = ToolboxPanel()
        toolbox_dock = QDockWidget("工具箱", self)
        toolbox_dock.setWidget(self._toolbox)
        toolbox_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        toolbox_dock.setMinimumWidth(180)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, toolbox_dock)

        # 属性面板（右侧）
        self._properties = PropertiesPanel()
        prop_dock = QDockWidget("属性", self)
        prop_dock.setWidget(self._properties)
        prop_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        prop_dock.setMinimumWidth(220)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, prop_dock)

        # 预览和输出（底部）
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._preview = PreviewPanel()
        self._output = OutputPanel()
        splitter.addWidget(self._preview)
        splitter.addWidget(self._output)
        splitter.setSizes([700, 300])
        bottom_layout.addWidget(splitter)

        bottom_dock = QDockWidget("预览与输出", self)
        bottom_dock.setWidget(bottom_widget)
        bottom_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        bottom_dock.setMinimumHeight(200)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, bottom_dock)

        # 工具箱双击添加节点
        self._toolbox.plugin_double_clicked.connect(self._add_node_to_center)

    def _setup_statusbar(self):
        self._statusbar = QStatusBar()
        self._statusbar.showMessage("就绪")
        self.setStatusBar(self._statusbar)

    def _add_node_to_center(self, plugin_id: str):
        view_center = self._view.mapToScene(self._view.viewport().rect().center())
        offset = len(self._scene.get_nodes()) * 30
        pos = QPointF(view_center.x() - 70 + offset, view_center.y() - 50 + offset)
        self._scene.add_plugin_node(plugin_id, pos)
        self._statusbar.showMessage(f"已添加工具: {plugin_id}")

    def _on_node_selected(self, node: NodeItem):
        self._properties.set_node(node)

    def _on_node_deselected(self):
        self._properties.set_node(None)

    def _on_node_added(self, node: NodeItem):
        self._output.log_info(f"添加节点: {node.plugin_name} [{node.node_id}]")
        node.on_double_clicked = self._on_node_double_clicked

    def _on_node_double_clicked(self, node: NodeItem):
        """双击节点：打开专用编辑对话框"""
        if node.plugin_id == "line_finder":
            self._open_line_finder_dialog(node)
        else:
            self._output.log_info(f"节点 [{node.plugin_name}] 没有专用编辑界面")

    def _open_line_finder_dialog(self, node: NodeItem):
        """打开线查找对话框"""
        # 获取输入图像：执行上游节点
        input_image = self._get_input_image_for_node(node)

        dialog = LineFinderDialog(node.plugin, input_image, self)
        if dialog.exec() == LineFinderDialog.DialogCode.Accepted:
            self._output.log_info(f"线查找ROI已更新: {len(node.plugin.get_rois())} 个ROI区域")
            self._statusbar.showMessage("线查找参数已保存")

    def _get_input_image_for_node(self, node: NodeItem) -> np.ndarray | None:
        """获取节点的输入图像（执行上游节点）"""
        # 查找连接到该节点输入端口的源节点
        connections = self._scene.get_connections()
        for conn in connections:
            if conn.target_port and conn.target_port.parent_node is node:
                src_node = conn.source_port.parent_node
                # 执行源节点
                try:
                    src_node.plugin.reset()
                    # 递归获取源节点的输入
                    src_input = self._get_input_image_for_node(src_node)
                    if src_input is not None:
                        src_node.plugin.set_input("input", src_input)
                    if src_node.plugin.execute():
                        outputs = src_node.plugin.get_outputs()
                        for name, val in outputs.items():
                            if isinstance(val, np.ndarray) and len(val.shape) >= 2:
                                return val
                except Exception:
                    pass
        return None

    def _on_run(self):
        self._output.log_info("开始执行流程图...")
        self._act_run.setEnabled(False)

        nodes = self._scene.get_nodes()
        connections = self._scene.get_connections()

        if not nodes:
            self._output.log_warning("流程图为空，请先添加工具节点")
            self._act_run.setEnabled(True)
            return

        self._engine.setup(nodes, connections)
        results = self._engine.execute()

        if "_error" in results:
            self._output.log_error(results["_error"])
        else:
            self._output.log_success("流程图执行完成")
            self._output.update_results(results)

            # 查找最后一个有image输出的节点并在预览中显示
            order = self._engine.topological_sort()
            if order:
                for node_id in reversed(order):
                    node_results = self._engine.get_node_results(node_id)
                    for port_name, value in node_results.items():
                        if value is not None and hasattr(value, 'shape') and len(value.shape) >= 2:
                            self._preview.set_image(value)
                            self._output.log_info(f"预览: {nodes[node_id].plugin_name} -> {port_name}")
                            break
                    else:
                        continue
                    break

        self._act_run.setEnabled(True)
        self._statusbar.showMessage("执行完成")

    def _on_stop(self):
        self._engine._running = False
        self._output.log_warning("执行已停止")
        self._act_run.setEnabled(True)

    def _on_delete(self):
        self._scene.remove_selected()
        self._properties.set_node(None)

    def _on_new(self):
        reply = QMessageBox.question(self, "新建", "确定要新建吗？当前流程图将被清除。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._scene.clear_all()
            self._preview.set_image(None)
            self._output._clear()
            self._current_file = None
            self.setWindowTitle("OpenVision - 工业视觉检测平台")
            self._statusbar.showMessage("新建流程图")

    def _on_open(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "",
            "OpenVision 项目文件 (*.ovp);;JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._scene.from_dict(data)
            self._preview.set_image(None)
            self._output._clear()
            self._current_file = filepath
            self.setWindowTitle(f"OpenVision - {os.path.basename(filepath)}")
            self._output.log_success(f"已打开: {filepath}")
            self._statusbar.showMessage(f"已加载: {os.path.basename(filepath)}")
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"无法加载项目文件：\n{e}")
            self._output.log_error(f"打开失败: {e}")

    def _on_save(self):
        if self._current_file:
            self._save_to_file(self._current_file)
        else:
            self._on_save_as()

    def _on_save_as(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存项目", "untitled.ovp",
            "OpenVision 项目文件 (*.ovp);;JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not filepath:
            return
        self._save_to_file(filepath)

    def _save_to_file(self, filepath: str):
        try:
            data = self._scene.to_dict()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._current_file = filepath
            self.setWindowTitle(f"OpenVision - {os.path.basename(filepath)}")
            self._output.log_success(f"已保存: {filepath}")
            self._statusbar.showMessage(f"已保存: {os.path.basename(filepath)}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存项目文件：\n{e}")
            self._output.log_error(f"保存失败: {e}")

    def _on_fit(self):
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _on_about(self):
        QMessageBox.about(self, "关于 OpenVision",
                          "<h3>OpenVision</h3>"
                          "<p>工业视觉检测平台 v1.0</p>"
                          "<p>基于 PySide6 + OpenCV 构建</p>"
                          "<p>开源免费，无授权限制</p>")

    def _on_refresh_plugins(self):
        self._toolbox.refresh()
        self._output.log_info("插件列表已刷新")