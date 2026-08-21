"""大华相机插件 - 通过 MVSDK 连接大华工业相机，支持实时预览"""

import os
import sys
import traceback

import cv2
import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QGroupBox,
)

from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef

# 添加 SDK 路径
mv_sdk_path = os.path.join(os.path.dirname(__file__), 'MVSDK')
sys.path.insert(0, mv_sdk_path)
from IMV_service import DahuaCamera, CameraError


class MVCameraDialog(QDialog):
    """大华相机设置对话框 - 预览 + 参数设置"""

    def __init__(self, plugin: "MVCameraPlugin", input_image, parent=None):
        super().__init__(parent)
        self._plugin = plugin
        self._camera: DahuaCamera | None = None
        self._connected = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_preview)

        self.setWindowTitle("大华相机 - 预览与设置")
        self.resize(800, 600)
        self.setMinimumSize(640, 480)

        self._setup_ui()
        self._load_params()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # ---- 相机选择 ----
        cam_group = QGroupBox("相机选择")
        cam_layout = QHBoxLayout(cam_group)
        self._cam_combo = QComboBox()
        self._cam_combo.setMinimumWidth(300)
        cam_layout.addWidget(QLabel("可用相机:"))
        cam_layout.addWidget(self._cam_combo, 1)

        self._btn_refresh = QPushButton("刷新列表")
        self._btn_refresh.clicked.connect(self._refresh_camera_list)
        cam_layout.addWidget(self._btn_refresh)

        self._btn_connect = QPushButton("连接")
        self._btn_connect.setStyleSheet("background: #2e7d32; color: #fff;")
        self._btn_connect.clicked.connect(self._toggle_connection)
        cam_layout.addWidget(self._btn_connect)
        main_layout.addWidget(cam_group)

        # ---- 图像预览 ----
        preview_group = QGroupBox("实时预览")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_label = QLabel("未连接相机")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(
            "background: #1e1e1e; border: 1px solid #3e3e42; color: #666; font-size: 14px;"
        )
        self._preview_label.setMinimumSize(640, 360)
        preview_layout.addWidget(self._preview_label)

        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #888; font-size: 11px;")
        preview_layout.addWidget(self._status_label)
        main_layout.addWidget(preview_group, 1)

        # ---- 底部按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._btn_ok = QPushButton("确定")
        self._btn_ok.clicked.connect(self._on_accept)
        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_ok)
        btn_layout.addWidget(self._btn_cancel)
        main_layout.addLayout(btn_layout)

    def _load_params(self):
        saved_idx = self._plugin.get_param("camera_index")
        self._refresh_camera_list()
        if saved_idx < self._cam_combo.count():
            self._cam_combo.setCurrentIndex(saved_idx)

    def _refresh_camera_list(self):
        """枚举大华相机列表"""
        self._cam_combo.clear()
        try:
            device_list = DahuaCamera.get_device_list()
            for i in range(device_list.nDevNum):
                info = device_list.pDevInfo[i]
                vendor = "".join(chr(c) for c in info.vendorName if c != 0)
                model = "".join(chr(c) for c in info.modelName if c != 0)
                sn = "".join(chr(c) for c in info.serialNumber if c != 0)
                label = f"[{i}] {vendor} {model} ({sn})"
                self._cam_combo.addItem(label, i)
            self._status_label.setText(f"发现 {device_list.nDevNum} 台相机")
        except CameraError as e:
            self._status_label.setText(f"枚举失败: {e}")
        except Exception as e:
            self._status_label.setText(f"错误: {e}")

    def _toggle_connection(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        idx = self._cam_combo.currentData()
        if idx is None:
            QMessageBox.warning(self, "提示", "请先选择一台相机")
            return
        try:
            self._camera = DahuaCamera()
            self._camera.connect(idx)
            self._connected = True
            self._timer.start(33)  # ~30 fps
            self._btn_connect.setText("断开")
            self._btn_connect.setStyleSheet("background: #c62828; color: #fff;")
            self._cam_combo.setEnabled(False)
            self._btn_refresh.setEnabled(False)
            self._status_label.setText("已连接")
        except CameraError as e:
            QMessageBox.critical(self, "连接失败", str(e))
            self._camera = None
        except Exception as e:
            QMessageBox.critical(self, "错误", f"{type(e).__name__}: {e}")
            self._camera = None

    def _disconnect(self):
        self._timer.stop()
        if self._camera:
            try:
                self._camera.close()
            except Exception:
                pass
            self._camera = None
        self._connected = False
        self._preview_label.setText("未连接相机")
        self._preview_label.setPixmap(QPixmap())
        self._btn_connect.setText("连接")
        self._btn_connect.setStyleSheet("background: #2e7d32; color: #fff;")
        self._cam_combo.setEnabled(True)
        self._btn_refresh.setEnabled(True)
        self._status_label.setText("已断开")

    def _update_preview(self):
        if not self._connected or self._camera is None:
            return
        try:
            frame = self._camera.get_frame(timeout=100)
            if frame is None:
                return
            # 转为 RGB 供 Qt 显示
            if len(frame.shape) == 2:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            else:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(
                self._preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview_label.setPixmap(scaled)
        except CameraError:
            self._status_label.setText("取帧超时")
        except Exception as e:
            self._status_label.setText(f"预览异常: {e}")

    def _on_accept(self):
        """保存设置并关闭"""
        if self._cam_combo.currentData() is not None:
            self._plugin.set_param("camera_index", self._cam_combo.currentData())
        self._disconnect()
        self.accept()

    def reject(self):
        self._disconnect()
        super().reject()

    def closeEvent(self, event):
        self._disconnect()
        super().closeEvent(event)


class MVCameraPlugin(PluginBase):
    """大华相机插件 - 通过 MVSDK 连接大华工业相机"""

    plugin_id = "mv_camera"
    plugin_name = "大华相机"
    plugin_category = "图像采集"
    plugin_description = "连接大华工业相机，通过 MVSDK 采集图像"

    def __init__(self):
        super().__init__()
        self._camera: DahuaCamera | None = None
        self._connected = False

    @classmethod
    def input_ports(cls):
        return []

    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.IMAGE, "采集图像")]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("camera_index", "相机序号", "int", 0, 0, 99, 1,
                     description="相机列表中的序号"),
            ParamDef("timeout", "取帧超时(ms)", "int", 2000, 100, 10000, 100,
                     description="获取帧的超时时间"),
        ]

    def get_dialog_class(self):
        return MVCameraDialog

    def execute(self) -> bool:
        try:
            # 每次执行时重新连接取一帧
            cam = DahuaCamera()
            idx = self.get_param("camera_index")
            timeout = self.get_param("timeout")
            cam.connect(idx)
            try:
                frame = cam.get_frame(timeout=timeout)
                if frame is None:
                    self._last_error = "获取图像失败"
                    return False
                self._outputs["output"] = frame
                return True
            finally:
                cam.close()
        except CameraError as e:
            self._last_error = f"相机错误: {e}"
            return False
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            return False

    def get_last_error(self) -> str:
        return getattr(self, '_last_error', '')