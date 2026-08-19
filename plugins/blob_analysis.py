"""斑点分析插件 - Blob检测与分析"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class BlobAnalysisPlugin(PluginBase):
    plugin_id = "blob_analysis"
    plugin_name = "斑点分析"
    plugin_category = "检测定位"
    plugin_description = "检测图像中的斑点/连通区域，并提取特征"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像（二值图）")]

    @classmethod
    def output_ports(cls):
        return [
            PortDef("output", PortType.IMAGE, "标注图像"),
            PortDef("blob_count", PortType.NUMBER, "斑点数量"),
        ]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("min_area", "最小面积", "int", 100, 0, 100000, 10, description="过滤的最小面积"),
            ParamDef("max_area", "最大面积", "int", 100000, 0, 1000000, 100, description="过滤的最大面积"),
            ParamDef("min_circularity", "最小圆度", "float", 0.0, 0.0, 1.0, 0.01, description="最小圆度"),
            ParamDef("draw_contours", "绘制轮廓", "bool", True, description="是否绘制轮廓"),
            ParamDef("contour_color", "轮廓颜色", "choice", "绿色", choices=["绿色", "红色", "蓝色", "黄色", "青色", "白色"], description="轮廓颜色"),
            ParamDef("fill_contours", "填充轮廓", "bool", False, description="是否填充轮廓"),
        ]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            return False

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # 确保是二值图
        if gray.max() > 1 and gray.dtype != np.uint8:
            gray = gray.astype(np.uint8)
        if len(np.unique(gray)) > 2:
            _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        min_area = self.get_param("min_area")
        max_area = self.get_param("max_area")
        min_circularity = self.get_param("min_circularity")
        draw_contours = self.get_param("draw_contours")
        fill_contours = self.get_param("fill_contours")

        color_map = {
            "绿色": (0, 255, 0), "红色": (0, 0, 255), "蓝色": (255, 0, 0),
            "黄色": (0, 255, 255), "青色": (255, 255, 0), "白色": (255, 255, 255),
        }
        contour_color = color_map.get(self.get_param("contour_color"), (0, 255, 0))

        try:
            contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if len(img.shape) == 2:
                output = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else:
                output = img.copy()

            valid_count = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area or area > max_area:
                    continue

                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                else:
                    circularity = 0

                if circularity < min_circularity:
                    continue

                valid_count += 1

                if draw_contours:
                    if fill_contours:
                        cv2.drawContours(output, [cnt], -1, contour_color, -1)
                    else:
                        cv2.drawContours(output, [cnt], -1, contour_color, 2)

                    # 绘制中心点
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        cv2.circle(output, (cx, cy), 3, (0, 0, 255), -1)

            self._outputs["output"] = output
            self._outputs["blob_count"] = valid_count
            return True
        except Exception:
            return False