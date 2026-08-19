"""模板匹配插件"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class PatternMatchPlugin(PluginBase):
    plugin_id = "pattern_match"
    plugin_name = "模板匹配"
    plugin_category = "检测定位"
    plugin_description = "在图像中查找模板位置"

    @classmethod
    def input_ports(cls):
        return [
            PortDef("input", PortType.IMAGE, "输入图像"),
            PortDef("template", PortType.IMAGE, "模板图像"),
        ]

    @classmethod
    def output_ports(cls):
        return [
            PortDef("output", PortType.IMAGE, "匹配结果图像"),
            PortDef("match_count", PortType.NUMBER, "匹配数量"),
        ]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("method", "匹配方法", "choice", "CCOEFF_NORMED",
                     choices=["CCOEFF", "CCOEFF_NORMED", "CCORR", "CCORR_NORMED", "SQDIFF", "SQDIFF_NORMED"],
                     description="模板匹配方法"),
            ParamDef("threshold", "匹配阈值", "float", 0.8, 0.0, 1.0, 0.01, description="匹配置信度阈值"),
            ParamDef("max_matches", "最大匹配数", "int", 10, 1, 100, 1, description="最多返回的匹配数"),
        ]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        template = self._inputs.get("template")
        if img is None or template is None:
            return False

        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img

            if len(template.shape) == 3:
                tpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                tpl_gray = template

            if tpl_gray.shape[0] > gray.shape[0] or tpl_gray.shape[1] > gray.shape[1]:
                self._outputs["output"] = img
                self._outputs["match_count"] = 0
                return True

            method_map = {
                "CCOEFF": cv2.TM_CCOEFF, "CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
                "CCORR": cv2.TM_CCORR, "CCORR_NORMED": cv2.TM_CCORR_NORMED,
                "SQDIFF": cv2.TM_SQDIFF, "SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
            }
            method = method_map.get(self.get_param("method"), cv2.TM_CCOEFF_NORMED)
            threshold = self.get_param("threshold")
            max_matches = self.get_param("max_matches")

            result = cv2.matchTemplate(gray, tpl_gray, method)
            h, w = tpl_gray.shape

            if len(img.shape) == 2:
                output = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else:
                output = img.copy()

            match_count = 0
            temp_result = result.copy()

            for _ in range(max_matches):
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(temp_result)

                if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                    if min_val > threshold:
                        break
                    top_left = min_loc
                else:
                    if max_val < threshold:
                        break
                    top_left = max_loc

                match_count += 1
                cv2.rectangle(output, top_left, (top_left[0] + w, top_left[1] + h), (0, 255, 0), 2)
                cv2.putText(output, f"{match_count}", (top_left[0], top_left[1] - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                # 抑制已匹配区域
                cv2.rectangle(temp_result, top_left, (top_left[0] + w, top_left[1] + h), 0, -1)

            self._outputs["output"] = output
            self._outputs["match_count"] = match_count
            return True
        except Exception:
            return False