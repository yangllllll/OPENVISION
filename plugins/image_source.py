"""图像源插件 - 加载图像文件"""

import cv2
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class ImageSourcePlugin(PluginBase):
    plugin_id = "image_source"
    plugin_name = "图像源"
    plugin_category = "输入输出"
    plugin_description = "从文件加载图像"

    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.IMAGE, "输出图像")]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("file_path", "图像路径", "file", "", description="选择要加载的图像文件"),
        ]

    def execute(self) -> bool:
        filepath = self.get_param("file_path")
        if not filepath:
            self._outputs["output"] = None
            return False
        try:
            img = cv2.imread(filepath)
            if img is None:
                return False
            self._outputs["output"] = img
            return True
        except Exception:
            return False