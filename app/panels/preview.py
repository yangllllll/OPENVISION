"""图像预览面板 - 显示处理结果图像"""

import cv2
import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QFont,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QHBoxLayout, QPushButton, QSizePolicy,
)


def cv2_to_qpixmap(cv_img: np.ndarray) -> QPixmap:
    """将OpenCV图像转换为QPixmap"""
    if cv_img is None:
        return QPixmap()

    if len(cv_img.shape) == 2:
        h, w = cv_img.shape
        bytes_per_line = w
        qimg = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
    elif cv_img.shape[2] == 3:
        h, w, ch = cv_img.shape
        bytes_per_line = ch * w
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    elif cv_img.shape[2] == 4:
        h, w, ch = cv_img.shape
        bytes_per_line = ch * w
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2RGBA)
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
    else:
        return QPixmap()

    return QPixmap.fromImage(qimg)


class ImageViewer(QWidget):
    """可缩放图像查看器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._fit = True
        self.setMinimumSize(200, 150)
        self.setStyleSheet("background: #1e1e1e;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_image(self, cv_img: np.ndarray | None):
        if cv_img is None:
            self._pixmap = None
        else:
            self._pixmap = cv2_to_qpixmap(cv_img)
        self._fit = True
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(30, 30, 30))

        if self._pixmap is None or self._pixmap.isNull():
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont("Microsoft YaHei", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "无图像")
            return

        if self._fit:
            scaled = self._pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            scaled = self._pixmap.scaled(
                self._pixmap.width() * self._zoom,
                self._pixmap.height() * self._zoom,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

    def wheelEvent(self, event: QWheelEvent):
        if self._pixmap is None:
            return
        self._fit = False
        if event.angleDelta().y() > 0:
            self._zoom = min(10.0, self._zoom * 1.15)
        else:
            self._zoom = max(0.05, self._zoom / 1.15)
        self.update()


class PreviewPanel(QWidget):
    """预览面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QWidget()
        header.setStyleSheet("background: #2d2d30; border-bottom: 1px solid #3e3e42;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel("  图像预览")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e0e0;")

        self._fit_btn = QPushButton("适应窗口")
        self._fit_btn.setStyleSheet("""
            QPushButton { background: #3e3e42; color: #ccc; border: 1px solid #555;
            padding: 3px 10px; font-size: 11px; }
            QPushButton:hover { background: #505050; }
        """)
        self._fit_btn.clicked.connect(self._on_fit)

        self._zoom_100_btn = QPushButton("1:1")
        self._zoom_100_btn.setStyleSheet(self._fit_btn.styleSheet())
        self._zoom_100_btn.clicked.connect(self._on_zoom_100)

        self._info_label = QLabel("")
        self._info_label.setFont(QFont("Microsoft YaHei", 9))
        self._info_label.setStyleSheet("color: #888;")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self._info_label)
        header_layout.addWidget(self._fit_btn)
        header_layout.addWidget(self._zoom_100_btn)

        layout.addWidget(header)

        self._viewer = ImageViewer()
        layout.addWidget(self._viewer)

    def set_image(self, cv_img: np.ndarray | None):
        self._viewer.set_image(cv_img)
        if cv_img is not None:
            h, w = cv_img.shape[:2]
            c = cv_img.shape[2] if len(cv_img.shape) > 2 else 1
            self._info_label.setText(f"{w} x {h}  通道: {c}")

    def _on_fit(self):
        self._viewer._fit = True
        self._viewer.update()

    def _on_zoom_100(self):
        self._viewer._fit = False
        self._viewer._zoom = 1.0
        self._viewer.update()