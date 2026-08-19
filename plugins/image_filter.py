"""图像滤波插件"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class ImageFilterPlugin(PluginBase):
    plugin_id = "image_filter"
    plugin_name = "图像滤波"
    plugin_category = "图像处理"
    plugin_description = "对图像进行平滑/锐化/去噪等滤波操作"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.IMAGE, "滤波结果")]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("filter_type", "滤波类型", "choice", "高斯模糊",
                     choices=["均值模糊", "高斯模糊", "中值滤波", "双边滤波", "锐化", "非局部均值去噪"],
                     description="滤波类型"),
            ParamDef("kernel_size", "核大小", "int", 5, 1, 31, 2, description="滤波核大小（奇数）"),
            ParamDef("sigma", "Sigma", "float", 1.0, 0.0, 10.0, 0.1, description="高斯Sigma"),
            ParamDef("bilateral_sigma_color", "双边-颜色Sigma", "float", 75.0, 1.0, 200.0, 1.0, description="双边滤波颜色空间Sigma"),
            ParamDef("bilateral_sigma_space", "双边-空间Sigma", "float", 75.0, 1.0, 200.0, 1.0, description="双边滤波空间Sigma"),
        ]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            return False

        filter_type = self.get_param("filter_type")
        ks = self.get_param("kernel_size")
        if ks % 2 == 0:
            ks += 1
        sigma = self.get_param("sigma")

        try:
            if filter_type == "均值模糊":
                result = cv2.blur(img, (ks, ks))
            elif filter_type == "高斯模糊":
                result = cv2.GaussianBlur(img, (ks, ks), sigma)
            elif filter_type == "中值滤波":
                result = cv2.medianBlur(img, ks)
            elif filter_type == "双边滤波":
                sc = self.get_param("bilateral_sigma_color")
                ss = self.get_param("bilateral_sigma_space")
                result = cv2.bilateralFilter(img, ks, sc, ss)
            elif filter_type == "锐化":
                kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
                result = cv2.filter2D(img, -1, kernel)
            elif filter_type == "非局部均值去噪":
                h = sigma * 10
                result = cv2.fastNlMeansDenoising(img, None, h, ks, 21)
            else:
                result = img

            self._outputs["output"] = result
            return True
        except Exception:
            return False