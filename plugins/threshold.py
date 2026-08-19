"""阈值分割插件"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class ThresholdPlugin(PluginBase):
    plugin_id = "threshold"
    plugin_name = "阈值分割"
    plugin_category = "图像处理"
    plugin_description = "对图像进行阈值分割"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [
            PortDef("output", PortType.IMAGE, "二值图像"),
            PortDef("threshold_value", PortType.NUMBER, "使用的阈值"),
        ]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("threshold", "阈值", "slider", 128, 0, 255, 1, description="分割阈值"),
            ParamDef("max_value", "最大值", "slider", 255, 0, 255, 1, description="最大值"),
            ParamDef("method", "方法", "choice", "BINARY", choices=["BINARY", "BINARY_INV", "OTSU", "TRIANGLE", "ADAPTIVE_MEAN", "ADAPTIVE_GAUSSIAN"], description="阈值方法"),
            ParamDef("block_size", "自适应块大小", "int", 11, 3, 99, 2, description="自适应阈值块大小（奇数）"),
            ParamDef("c", "常数C", "float", 2.0, -50, 50, 0.5, description="自适应阈值常数"),
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
        thresh = self.get_param("threshold")
        max_val = self.get_param("max_value")
        block_size = self.get_param("block_size")
        c = self.get_param("c")

        if block_size % 2 == 0:
            block_size += 1

        try:
            if method == "BINARY":
                ret, result = cv2.threshold(gray, thresh, max_val, cv2.THRESH_BINARY)
                self._outputs["threshold_value"] = float(ret)
            elif method == "BINARY_INV":
                ret, result = cv2.threshold(gray, thresh, max_val, cv2.THRESH_BINARY_INV)
                self._outputs["threshold_value"] = float(ret)
            elif method == "OTSU":
                ret, result = cv2.threshold(gray, 0, max_val, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                self._outputs["threshold_value"] = float(ret)
            elif method == "TRIANGLE":
                ret, result = cv2.threshold(gray, 0, max_val, cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE)
                self._outputs["threshold_value"] = float(ret)
            elif method == "ADAPTIVE_MEAN":
                result = cv2.adaptiveThreshold(gray, max_val, cv2.ADAPTIVE_THRESH_MEAN_C,
                                               cv2.THRESH_BINARY, block_size, c)
                self._outputs["threshold_value"] = 0.0
            elif method == "ADAPTIVE_GAUSSIAN":
                result = cv2.adaptiveThreshold(gray, max_val, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                               cv2.THRESH_BINARY, block_size, c)
                self._outputs["threshold_value"] = 0.0
            else:
                result = gray
                self._outputs["threshold_value"] = 0.0

            self._outputs["output"] = result
            return True
        except Exception:
            return False