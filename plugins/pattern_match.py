"""模板匹配插件 - 支持ROI框选训练模板，缓存到tmp目录"""

import os
import traceback

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class PatternMatchPlugin(PluginBase):
    """模板匹配工具 - 支持在图像上框选ROI训练模板，模板缓存到tmp目录"""

    plugin_id = "pattern_match"
    plugin_name = "模板匹配"
    plugin_category = "检测定位"
    plugin_description = "在图像中框选ROI训练模板并匹配，模板缓存到tmp目录"

    def __init__(self):
        super().__init__()
        # 模板ROI: (x, y, w, h)
        self._template_roi: tuple[int, int, int, int] | None = None
        # 训练好的模板图像（灰度）
        self._template_image: np.ndarray | None = None
        # 模板缓存路径
        self._template_cache_path: str = ""

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [
            PortDef("output", PortType.IMAGE, "匹配结果图像"),
            PortDef("match_count", PortType.NUMBER, "匹配数量"),
            PortDef("match_positions", PortType.ANY, "匹配位置列表 [(x,y),...]"),
        ]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("method", "匹配方法", "choice", "CCOEFF_NORMED",
                     choices=["CCOEFF", "CCOEFF_NORMED", "CCORR", "CCORR_NORMED", "SQDIFF", "SQDIFF_NORMED"],
                     description="模板匹配方法"),
            ParamDef("threshold", "匹配阈值", "float", 0.8, 0.0, 1.0, 0.01, description="匹配置信度阈值"),
            ParamDef("max_matches", "最大匹配数", "int", 10, 1, 100, 1, description="最多返回的匹配数"),
            ParamDef("draw_color", "标记颜色", "choice", "绿色",
                     choices=["绿色", "红色", "蓝色", "黄色", "青色", "白色"],
                     description="绘制匹配框的颜色"),
            ParamDef("line_thickness", "线宽", "int", 2, 1, 5, 1, description="标注线宽"),
        ]

    # ---- 模板训练 ----

    def train_template(self, img: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray | None:
        """从ROI中提取模板图像并缓存到tmp目录"""
        rx, ry, rw, rh = roi
        if rw < 5 or rh < 5:
            return None

        # 提取ROI
        if len(img.shape) == 3:
            template = img[ry:ry + rh, rx:rx + rw].copy()
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = img[ry:ry + rh, rx:rx + rw].copy()

        self._template_roi = (rx, ry, rw, rh)
        self._template_image = template_gray

        # 缓存到 tmp 目录
        tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        cache_path = os.path.join(tmp_dir, f"template_{self.plugin_id}.png")
        cv2.imwrite(cache_path, template_gray)
        self._template_cache_path = cache_path

        return template_gray

    def get_template_image(self) -> np.ndarray | None:
        """获取训练好的模板图像"""
        return self._template_image

    def get_template_roi(self) -> tuple | None:
        return self._template_roi

    # ---- 序列化 ----

    def get_extra_data(self) -> dict:
        data = {}
        if self._template_roi:
            data["template_roi"] = list(self._template_roi)
        if self._template_cache_path:
            data["template_cache_path"] = self._template_cache_path
        return data

    def set_extra_data(self, data: dict):
        if "template_roi" in data and isinstance(data["template_roi"], list) and len(data["template_roi"]) == 4:
            self._template_roi = tuple(data["template_roi"])
        if "template_cache_path" in data:
            self._template_cache_path = data["template_cache_path"]
            # 尝试从缓存恢复模板图像
            if os.path.exists(self._template_cache_path):
                self._template_image = cv2.imread(self._template_cache_path, cv2.IMREAD_GRAYSCALE)

    def get_dialog_class(self):
        from app.dialogs.pattern_match_dialog import PatternMatchDialog
        return PatternMatchDialog

    # ---- 执行 ----

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            self._last_error = "没有输入图像"
            return False

        # 获取模板：优先使用训练好的模板，其次从输入端口获取
        template = self._template_image
        if template is None:
            self._last_error = "没有模板图像，请先双击节点框选ROI训练模板"
            return False

        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img

            if template.shape[0] > gray.shape[0] or template.shape[1] > gray.shape[1]:
                self._outputs["output"] = img if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                self._outputs["match_count"] = 0
                self._outputs["match_positions"] = []
                return True

            color_map = {
                "绿色": (0, 255, 0), "红色": (0, 0, 255), "蓝色": (255, 0, 0),
                "黄色": (0, 255, 255), "青色": (255, 255, 0), "白色": (255, 255, 255),
            }
            draw_color = color_map.get(self.get_param("draw_color"), (0, 255, 0))
            line_thickness = self.get_param("line_thickness")

            method_map = {
                "CCOEFF": cv2.TM_CCOEFF, "CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
                "CCORR": cv2.TM_CCORR, "CCORR_NORMED": cv2.TM_CCORR_NORMED,
                "SQDIFF": cv2.TM_SQDIFF, "SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
            }
            method = method_map.get(self.get_param("method"), cv2.TM_CCOEFF_NORMED)
            threshold = self.get_param("threshold")
            max_matches = self.get_param("max_matches")

            result = cv2.matchTemplate(gray, template, method)
            h, w = template.shape

            if len(img.shape) == 2:
                output = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else:
                output = img.copy()

            # ---- 收集所有超过阈值的候选位置 ----
            is_sqdiff = method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]
            if is_sqdiff:
                ys, xs = np.where(result <= threshold)
            else:
                ys, xs = np.where(result >= threshold)

            candidates = [(x, y, result[y, x]) for x, y in zip(xs, ys)]

            # 按置信度排序
            reverse = not is_sqdiff
            candidates.sort(key=lambda c: c[2], reverse=reverse)

            # ---- NMS 非极大值抑制 ----
            positions = []
            for x, y, score in candidates:
                if len(positions) >= max_matches:
                    break
                # 检查是否与已选中的匹配重叠
                overlap = False
                for px, py in positions:
                    if abs(x - px) < w and abs(y - py) < h:
                        overlap = True
                        break
                if not overlap:
                    positions.append((x, y))

            # ---- 绘制结果 ----
            for i, (x, y) in enumerate(positions):
                cv2.rectangle(output, (x, y), (x + w, y + h), draw_color, line_thickness)
                cv2.putText(output, f"{i + 1}", (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, draw_color, 1)

            match_count = len(positions)

            self._outputs["output"] = output
            self._outputs["match_count"] = match_count
            self._outputs["match_positions"] = positions
            return True
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            return False

    def get_last_error(self) -> str:
        return getattr(self, '_last_error', '')