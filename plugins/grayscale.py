"""灰度化插件"""

import cv2
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class GrayscalePlugin(PluginBase):
    plugin_id = "grayscale"
    plugin_name = "灰度化"
    plugin_category = "图像处理"
    plugin_description = "将彩色图像转换为灰度图像"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.IMAGE, "灰度图像")]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            return False
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        self._outputs["output"] = gray
        return True