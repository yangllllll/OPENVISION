"""图像保存插件 - 保存图像到文件"""

import cv2
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class ImageOutputPlugin(PluginBase):
    plugin_id = "image_output"
    plugin_name = "图像输出"
    plugin_category = "输入输出"
    plugin_description = "将图像保存到文件"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("file_path", "保存路径", "file", "", description="图像保存路径"),
        ]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        filepath = self.get_param("file_path")
        if img is None or not filepath:
            return False
        try:
            cv2.imwrite(filepath, img)
            return True
        except Exception:
            return False