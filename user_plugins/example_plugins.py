"""
示例用户插件 - 图像翻转
将此文件放在 user_plugins 目录下，重启应用即可在工具箱中看到此工具。

自定义插件开发指南：
1. 继承 PluginBase
2. 设置 plugin_id（唯一标识）、plugin_name、plugin_category、plugin_description
3. 定义 input_ports()、output_ports()、input_params()
4. 实现 execute() 方法
"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class FlipPlugin(PluginBase):
    """图像翻转插件"""

    plugin_id = "user_flip"
    plugin_name = "图像翻转"
    plugin_category = "用户插件"
    plugin_description = "对图像进行水平/垂直翻转"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.IMAGE, "翻转结果")]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("flip_mode", "翻转模式", "choice", "水平翻转",
                     choices=["水平翻转", "垂直翻转", "水平+垂直翻转"],
                     description="选择翻转方向"),
        ]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            return False

        mode = self.get_param("flip_mode")
        flip_map = {
            "水平翻转": 1,
            "垂直翻转": 0,
            "水平+垂直翻转": -1,
        }

        try:
            result = cv2.flip(img, flip_map.get(mode, 1))
            self._outputs["output"] = result
            return True
        except Exception:
            return False


class InvertPlugin(PluginBase):
    """图像反色插件"""

    plugin_id = "user_invert"
    plugin_name = "图像反色"
    plugin_category = "用户插件"
    plugin_description = "对图像进行反色处理"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.IMAGE, "反色结果")]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            return False

        try:
            result = cv2.bitwise_not(img)
            self._outputs["output"] = result
            return True
        except Exception:
            return False
class number_plugin(PluginBase):
    """数学插件"""
    plugin_id = "user_number"
    plugin_name = "比较"
    plugin_category = "用户插件"
    plugin_description = "对数字进行比较"
    
    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.NUMBER, "输入数字")]
        
    @classmethod
    def output_ports(cls):
        return [PortDef("output", PortType.BOOL, "比较结果")]
        
    @classmethod
    def input_params(cls):
        return [
            ParamDef("compare_mode", "比较模式", "choice", "大于",
                     choices=["大于", "小于", "等于"],
                     description="选择比较模式"),
            ParamDef("NUM", "数字", "float", 0,
                     description="输入数字"),
        ]
    
    def execute(self) -> bool:
        num1 = self._inputs.get("input")
        if num1 is None:
            return False
        
        mode = self.get_param("compare_mode")
        compare_map = {
            "大于": lambda x, y: x > y,
            "小于": lambda x, y: x < y,
            "等于": lambda x, y: x == y,
        }

        num2 = self.get_param("NUM")
        try:
            result = compare_map.get(mode, lambda x, y: False)(num1, num2)
            self._outputs["output"] = result
            return True
        except Exception:
            return False

    