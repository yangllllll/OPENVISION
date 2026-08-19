"""边缘检测插件"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class EdgeDetectionPlugin(PluginBase):
    plugin_id = "edge_detection"
    plugin_name = "边缘检测"
    plugin_category = "图像处理"
    plugin_description = "检测图像边缘（Canny / Sobel / Laplacian）"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.IMAGE, "边缘图像")]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("method", "方法", "choice", "Canny", choices=["Canny", "Sobel", "Laplacian"], description="边缘检测算法"),
            ParamDef("low_threshold", "低阈值", "slider", 50, 0, 255, 1, description="Canny低阈值"),
            ParamDef("high_threshold", "高阈值", "slider", 150, 0, 255, 1, description="Canny高阈值"),
            ParamDef("aperture", "孔径大小", "choice", "3", choices=["3", "5", "7"], description="Sobel/Laplacian孔径"),
            ParamDef("dx", "X方向阶数", "int", 1, 0, 2, 1, description="Sobel X方向导数阶数"),
            ParamDef("dy", "Y方向阶数", "int", 0, 0, 2, 1, description="Sobel Y方向导数阶数"),
        ]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            return False

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        method = self.get_param("method")
        aperture = int(self.get_param("aperture"))

        try:
            if method == "Canny":
                low = self.get_param("low_threshold")
                high = self.get_param("high_threshold")
                result = cv2.Canny(gray, low, high)
            elif method == "Sobel":
                dx = self.get_param("dx")
                dy = self.get_param("dy")
                result = cv2.Sobel(gray, cv2.CV_64F, dx, dy, ksize=aperture)
                result = cv2.convertScaleAbs(result)
            elif method == "Laplacian":
                result = cv2.Laplacian(gray, cv2.CV_64F, ksize=aperture)
                result = cv2.convertScaleAbs(result)
            else:
                result = gray

            self._outputs["output"] = result
            return True
        except Exception:
            return False