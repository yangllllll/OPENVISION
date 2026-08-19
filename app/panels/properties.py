"""属性面板 - 显示和编辑选中节点的参数"""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QFormLayout, QSpinBox, QDoubleSpinBox, QLineEdit,
    QCheckBox, QComboBox, QSlider, QPushButton,
    QFileDialog, QHBoxLayout, QGroupBox, QSizePolicy,
)

from app.flowchart.node import NodeItem
from app.plugin_system.base import ParamDef


class PropertiesPanel(QWidget):
    """属性面板"""

    param_changed = Signal(str, str, object)  # node_id, param_name, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_node: NodeItem | None = None
        self._widgets: dict[str, Any] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("  属性")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        title.setStyleSheet("""
            QLabel {
                background: #2d2d30; color: #e0e0e0;
                padding: 8px 4px; border-bottom: 1px solid #3e3e42;
            }
        """)
        layout.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { background: #252526; border: none; }")

        self._content = QWidget()
        self._content.setStyleSheet("background: #252526;")
        self._form_layout = QFormLayout(self._content)
        self._form_layout.setContentsMargins(8, 8, 8, 8)
        self._form_layout.setSpacing(6)

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

        self._no_selection = QLabel("  (未选中节点)")
        self._no_selection.setFont(QFont("Microsoft YaHei", 9))
        self._no_selection.setStyleSheet("color: #888; padding: 16px;")
        self._form_layout.addWidget(self._no_selection)

    def set_node(self, node: NodeItem | None):
        """设置当前节点"""
        self._current_node = node
        self._clear_form()

        if node is None:
            self._no_selection = QLabel("  (未选中节点)")
            self._no_selection.setFont(QFont("Microsoft YaHei", 9))
            self._no_selection.setStyleSheet("color: #888; padding: 16px;")
            self._form_layout.addWidget(self._no_selection)
            return

        params = node.plugin.input_params()
        if not params:
            label = QLabel(f"  工具: {node.plugin_name}\n  无参数")
            label.setFont(QFont("Microsoft YaHei", 9))
            label.setStyleSheet("color: #aaa; padding: 8px;")
            self._form_layout.addWidget(label)
            return

        # 工具名称
        name_label = QLabel(f"  {node.plugin_name}")
        name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #4fc3f7; padding: 4px 0 8px 0;")
        self._form_layout.addWidget(name_label)

        for pdef in params:
            self._add_param_widget(pdef)

    def _clear_form(self):
        self._widgets.clear()
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_param_widget(self, pdef: ParamDef):
        # 获取插件的当前值（优先）或默认值
        current_val = self._current_node.plugin.get_param(pdef.name)
        if current_val is None:
            current_val = pdef.default

        if pdef.param_type == "int":
            w = QSpinBox()
            if pdef.min_val is not None:
                w.setMinimum(int(pdef.min_val))
            if pdef.max_val is not None:
                w.setMaximum(int(pdef.max_val))
            if current_val is not None:
                w.setValue(int(current_val))
            w.valueChanged.connect(lambda v, n=pdef.name: self._on_change(n, v))

        elif pdef.param_type == "float":
            w = QDoubleSpinBox()
            w.setDecimals(3)
            if pdef.min_val is not None:
                w.setMinimum(pdef.min_val)
            else:
                w.setMinimum(-99999)
            if pdef.max_val is not None:
                w.setMaximum(pdef.max_val)
            else:
                w.setMaximum(99999)
            if pdef.step is not None:
                w.setSingleStep(pdef.step)
            else:
                w.setSingleStep(0.1)
            if current_val is not None:
                w.setValue(float(current_val))
            w.valueChanged.connect(lambda v, n=pdef.name: self._on_change(n, v))

        elif pdef.param_type == "slider":
            container = QWidget()
            hl = QHBoxLayout(container)
            hl.setContentsMargins(0, 0, 0, 0)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(int(pdef.min_val or 0))
            slider.setMaximum(int(pdef.max_val or 100))
            if current_val is not None:
                slider.setValue(int(current_val))
            val_label = QLabel(str(slider.value()))
            val_label.setStyleSheet("color: #ccc; min-width: 30px;")
            val_label.setFont(QFont("Microsoft YaHei", 9))
            slider.valueChanged.connect(lambda v, l=val_label: l.setText(str(v)))
            slider.valueChanged.connect(lambda v, n=pdef.name: self._on_change(n, v))
            hl.addWidget(slider)
            hl.addWidget(val_label)
            w = container

        elif pdef.param_type == "bool":
            w = QCheckBox()
            if current_val is not None:
                w.setChecked(bool(current_val))
            w.toggled.connect(lambda v, n=pdef.name: self._on_change(n, v))

        elif pdef.param_type == "choice":
            w = QComboBox()
            if pdef.choices:
                w.addItems(pdef.choices)
            if current_val is not None and current_val in (pdef.choices or []):
                w.setCurrentText(str(current_val))
            w.currentTextChanged.connect(lambda v, n=pdef.name: self._on_change(n, v))

        elif pdef.param_type == "file":
            container = QWidget()
            hl = QHBoxLayout(container)
            hl.setContentsMargins(0, 0, 0, 0)
            le = QLineEdit()
            le.setReadOnly(True)
            le.setStyleSheet("background: #333; color: #ccc; border: 1px solid #555; padding: 2px;")
            if current_val:
                le.setText(str(current_val))
            btn = QPushButton("...")
            btn.setMaximumWidth(30)
            btn.setStyleSheet("QPushButton { background: #3e3e42; color: #ccc; border: 1px solid #555; } QPushButton:hover { background: #505050; }")
            btn.clicked.connect(lambda: self._browse_file(le, pdef.name))
            hl.addWidget(le)
            hl.addWidget(btn)
            self._widgets[pdef.name + "_le"] = le
            w = container

        elif pdef.param_type == "str":
            w = QLineEdit()
            if current_val is not None:
                w.setText(str(current_val))
            w.setStyleSheet("background: #333; color: #ccc; border: 1px solid #555; padding: 2px;")
            w.textChanged.connect(lambda v, n=pdef.name: self._on_change(n, v))

        else:
            w = QLineEdit()
            if current_val is not None:
                w.setText(str(current_val))
            w.setStyleSheet("background: #333; color: #ccc; border: 1px solid #555; padding: 2px;")
            w.textChanged.connect(lambda v, n=pdef.name: self._on_change(n, v))

        w.setStyleSheet(w.styleSheet() + " font-family: 'Microsoft YaHei'; font-size: 11px;")

        label = QLabel(pdef.display_name)
        label.setFont(QFont("Microsoft YaHei", 9))
        label.setStyleSheet("color: #aaa;")
        if pdef.description:
            label.setToolTip(pdef.description)

        self._form_layout.addRow(label, w)
        self._widgets[pdef.name] = w

    def _browse_file(self, line_edit: QLineEdit, param_name: str):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "图片文件 (*.png *.jpg *.bmp *.tiff *.tif);;所有文件 (*.*)")
        if filepath:
            line_edit.setText(filepath)
            self._on_change(param_name, filepath)

    def _on_change(self, param_name: str, value):
        if self._current_node:
            self._current_node.plugin.set_param(param_name, value)
            self.param_changed.emit(self._current_node.node_id, param_name, value)