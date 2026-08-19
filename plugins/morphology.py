"""形态学处理插件"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class MorphologyPlugin(PluginBase):
    plugin_id = "morphology"
    plugin_name = "形态学处理"
    plugin_category = "图像处理"
    plugin_description = "膨胀/腐蚀/开运算/闭运算等形态学操作"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.IMAGE, "处理结果")]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("operation", "操作", "choice", "ERODE", choices=["ERODE", "DILATE", "OPEN", "CLOSE", "GRADIENT", "TOPHAT", "BLACKHAT"], description="形态学操作类型"),
            ParamDef("kernel_shape", "核形状", "choice", "RECT", choices=["RECT", "ELLIPSE", "CROSS"], description="结构元素形状"),
            ParamDef("kernel_size", "核大小", "int", 3, 1, 31, 2, description="结构元素大小"),
            ParamDef("iterations", "迭代次数", "int", 1, 1, 10, 1, description="操作迭代次数"),
        ]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            return False

        shape_map = {"RECT": cv2.MORPH_RECT, "ELLIPSE": cv2.MORPH_ELLIPSE, "CROSS": cv2.MORPH_CROSS}
        ks = self.get_param("kernel_size")
        kernel = cv2.getStructuringElement(shape_map.get(self.get_param("kernel_shape"), cv2.MORPH_RECT),
                                           (ks, ks))
        op = self.get_param("operation")
        iters = self.get_param("iterations")

        op_map = {
            "ERODE": cv2.MORPH_ERODE,
            "DILATE": cv2.MORPH_DILATE,
            "OPEN": cv2.MORPH_OPEN,
            "CLOSE": cv2.MORPH_CLOSE,
            "GRADIENT": cv2.MORPH_GRADIENT,
            "TOPHAT": cv2.MORPH_TOPHAT,
            "BLACKHAT": cv2.MORPH_BLACKHAT,
        }

        try:
            result = cv2.morphologyEx(img, op_map.get(op, cv2.MORPH_ERODE), kernel, iterations=iters)
            self._outputs["output"] = result
            return True
        except Exception:
            return False