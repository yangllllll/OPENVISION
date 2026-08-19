"""线间距工具 - 计算两个线查找工具检测到的线之间的垂直和水平距离"""

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class LineDistancePlugin(PluginBase):
    """线间距测量工具"""

    plugin_id = "line_distance"
    plugin_name = "线间距"
    plugin_category = "检测定位"
    plugin_description = "接收两个线查找工具的线坐标，计算垂直距离和水平距离"

    def __init__(self):
        super().__init__()
        self._distances: list[dict] = []

    @classmethod
    def input_ports(cls):
        return [
            PortDef("lines1", PortType.ANY, "线坐标集合1"),
            PortDef("lines2", PortType.ANY, "线坐标集合2"),
            PortDef("image", PortType.IMAGE, "参考图像(可选)"),
        ]

    @classmethod
    def output_ports(cls):
        return [
            PortDef("output", PortType.IMAGE, "标注图像"),
            PortDef("horizontal_dist", PortType.NUMBER, "水平距离"),
            PortDef("vertical_dist", PortType.NUMBER, "垂直距离"),
            PortDef("all_distances", PortType.ANY, "所有距离详情"),
            PortDef("pair_count", PortType.NUMBER, "匹配对数"),
        ]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("draw_color", "标注颜色", "choice", "绿色",
                     choices=["绿色", "红色", "蓝色", "黄色", "青色", "白色"],
                     description="标注线的颜色"),
            ParamDef("line_thickness", "线宽", "int", 2, 1, 5, 1, description="标注线宽"),
            ParamDef("font_scale", "字体大小", "float", 0.6, 0.3, 2.0, 0.1, description="标注文字大小"),
        ]

    def execute(self) -> bool:
        lines1 = self._inputs.get("lines1")
        lines2 = self._inputs.get("lines2")
        image = self._inputs.get("image")

        if lines1 is None or lines2 is None:
            self._last_error = "缺少线坐标输入，请连接两个线查找工具的输出"
            return False

        if not isinstance(lines1, list) or not isinstance(lines2, list):
            self._last_error = "线坐标格式错误，请连接线查找工具的 line_coords 输出"
            return False

        if len(lines1) == 0 or len(lines2) == 0:
            self._last_error = "线坐标为空，请先运行线查找工具"
            return False

        try:
            color_map = {
                "绿色": (0, 255, 0), "红色": (0, 0, 255), "蓝色": (255, 0, 0),
                "黄色": (0, 255, 255), "青色": (255, 255, 0), "白色": (255, 255, 255),
            }
            draw_color = color_map.get(self.get_param("draw_color"), (0, 255, 0))
            line_thickness = self.get_param("line_thickness")
            font_scale = self.get_param("font_scale")

            self._distances = []

            # 创建或使用参考图像
            if image is not None:
                if len(image.shape) == 2:
                    output = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                else:
                    output = image.copy()
            else:
                # 无参考图像时，创建空白画布
                all_lines = list(lines1) + list(lines2)
                max_x = max(max(l[0], l[2]) for l in all_lines) + 50
                max_y = max(max(l[1], l[3]) for l in all_lines) + 50
                output = np.zeros((max(int(max_y), 200), max(int(max_x), 200), 3), dtype=np.uint8)
                output.fill(30)

            total_h = 0.0
            total_v = 0.0
            count = 0

            for i, l1 in enumerate(lines1):
                x1a, y1a, x2a, y2a = l1
                mid_x1 = (x1a + x2a) / 2
                mid_y1 = (y1a + y2a) / 2

                for j, l2 in enumerate(lines2):
                    x1b, y1b, x2b, y2b = l2
                    mid_x2 = (x1b + x2b) / 2
                    mid_y2 = (y1b + y2b) / 2

                    h_dist = abs(mid_x2 - mid_x1)
                    v_dist = abs(mid_y2 - mid_y1)

                    self._distances.append({
                        "pair": f"L1-{i + 1} x L2-{j + 1}",
                        "horizontal": round(h_dist, 2),
                        "vertical": round(v_dist, 2),
                    })

                    total_h += h_dist
                    total_v += v_dist
                    count += 1

                    # 绘制两条线
                    cv2.line(output, (int(x1a), int(y1a)), (int(x2a), int(y2a)),
                            (0, 180, 255), line_thickness)
                    cv2.line(output, (int(x1b), int(y1b)), (int(x2b), int(y2b)),
                            draw_color, line_thickness)

                    # 绘制中点连线（虚线效果用点线）
                    mid_a = (int(mid_x1), int(mid_y1))
                    mid_b = (int(mid_x2), int(mid_y2))
                    cv2.line(output, mid_a, mid_b, (255, 255, 255), 1, cv2.LINE_AA)

                    # 标注距离
                    text_pos = (mid_a[0] + 10, mid_a[1] - 10)
                    cv2.putText(output, f"dH={h_dist:.1f}", text_pos,
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1)
                    cv2.putText(output, f"dV={v_dist:.1f}",
                               (text_pos[0], text_pos[1] + int(20 * font_scale)),
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1)

            avg_h = total_h / count if count > 0 else 0
            avg_v = total_v / count if count > 0 else 0

            self._outputs["output"] = output
            self._outputs["horizontal_dist"] = round(avg_h, 2)
            self._outputs["vertical_dist"] = round(avg_v, 2)
            self._outputs["all_distances"] = self._distances
            self._outputs["pair_count"] = count
            return True
        except Exception as e:
            import traceback
            self._last_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            return False

    def get_last_error(self) -> str:
        return getattr(self, '_last_error', '')