"""测量插件 - 线段/圆/角度测量"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class MeasurePlugin(PluginBase):
    plugin_id = "measure"
    plugin_name = "测量工具"
    plugin_category = "检测定位"
    plugin_description = "测量图像中的距离、圆、角度等"

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [
            PortDef("output", PortType.IMAGE, "标注图像"),
            PortDef("measure_count", PortType.NUMBER, "测量对象数量"),
        ]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("measure_type", "测量类型", "choice", "线段",
                     choices=["线段", "矩形", "圆形", "最小外接矩形", "最小外接圆"],
                     description="测量类型"),
            ParamDef("line_color", "绘制颜色", "choice", "绿色",
                     choices=["绿色", "红色", "蓝色", "黄色", "白色"],
                     description="绘制颜色"),
        ]

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            return False

        color_map = {
            "绿色": (0, 255, 0), "红色": (0, 0, 255), "蓝色": (255, 0, 0),
            "黄色": (0, 255, 255), "白色": (255, 255, 255),
        }
        color = color_map.get(self.get_param("line_color"), (0, 255, 0))
        measure_type = self.get_param("measure_type")

        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img.copy()

            # 预处理
            if len(np.unique(gray)) > 2:
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            else:
                binary = gray

            if len(img.shape) == 2:
                output = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else:
                output = img.copy()

            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            measure_count = 0

            for cnt in contours:
                if len(cnt) < 5:
                    continue
                area = cv2.contourArea(cnt)
                if area < 50:
                    continue

                if measure_type == "线段":
                    vx, vy, x0, y0 = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01)
                    rows, cols = output.shape[:2]
                    lefty = int((-x0 * vy / vx) + y0) if vx != 0 else 0
                    righty = int(((cols - x0) * vy / vx) + y0) if vx != 0 else 0
                    cv2.line(output, (cols - 1, righty), (0, lefty), color, 2)
                    measure_count += 1

                elif measure_type == "矩形":
                    x, y, w, h = cv2.boundingRect(cnt)
                    cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(output, f"{w}x{h}", (x, y - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    measure_count += 1

                elif measure_type == "圆形":
                    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                    center = (int(cx), int(cy))
                    cv2.circle(output, center, int(radius), color, 2)
                    cv2.circle(output, center, 3, color, -1)
                    cv2.putText(output, f"R={int(radius)}", (center[0] + 10, center[1]),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    measure_count += 1

                elif measure_type == "最小外接矩形":
                    rect = cv2.minAreaRect(cnt)
                    box = cv2.boxPoints(rect)
                    box = np.intp(box)
                    cv2.drawContours(output, [box], 0, color, 2)
                    measure_count += 1

                elif measure_type == "最小外接圆":
                    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                    center = (int(cx), int(cy))
                    cv2.circle(output, center, int(radius), color, 2)
                    measure_count += 1

            self._outputs["output"] = output
            self._outputs["measure_count"] = measure_count
            return True
        except Exception:
            return False