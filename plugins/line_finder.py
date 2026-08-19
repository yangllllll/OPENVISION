"""线查找插件 - 基于亮度/色阶的直线检测，支持自动学习"""

import traceback

import cv2
import numpy as np
from app.plugin_system.base import PluginBase, PortDef, PortType, ParamDef


class LineFinderPlugin(PluginBase):
    """线查找工具 - 基于亮度梯度在ROI区域内检测直线，支持自动学习色差"""

    plugin_id = "line_finder"
    plugin_name = "线查找"
    plugin_category = "检测定位"
    plugin_description = "基于亮度色阶在ROI区域内检测直线，支持自动学习色差，返回单条最优线段"

    def __init__(self):
        super().__init__()
        self._rois: list[tuple[int, int, int, int]] = []
        self._detected_lines: list[tuple[float, float, float, float]] = []
        # 学习结果
        self._learned_line: tuple[float, float, float, float] | None = None
        self._learned_thresholds: tuple[int, int] | None = None

    @classmethod
    def input_ports(cls):
        return [PortDef("input", PortType.IMAGE, "输入图像")]

    @classmethod
    def output_ports(cls):
        return [
            PortDef("output", PortType.IMAGE, "标记图像"),
            PortDef("line_count", PortType.NUMBER, "检测到的线段数量"),
            PortDef("line_coords", PortType.ANY, "线段坐标列表"),
        ]

    @classmethod
    def input_params(cls):
        return [
            ParamDef("search_direction", "搜索方向", "choice", "垂直",
                     choices=["垂直", "水平"],
                     description="ROI内搜索方向：垂直=从上到下找水平线，水平=从左到右找竖直线"),
            ParamDef("edge_polarity", "边缘极性", "choice", "明到暗",
                     choices=["明到暗", "暗到明", "任意"],
                     description="从明到暗=白底黑线，从暗到明=黑底白线"),
            ParamDef("edge_threshold1", "边缘低阈值", "slider", 30, 0, 255, 1, description="Canny边缘检测低阈值"),
            ParamDef("edge_threshold2", "边缘高阈值", "slider", 90, 0, 255, 1, description="Canny边缘检测高阈值"),
            ParamDef("hough_threshold", "霍夫阈值", "slider", 30, 1, 300, 1, description="霍夫直线检测投票阈值"),
            ParamDef("min_line_length", "最小线长", "slider", 30, 5, 500, 1, description="最小线段长度"),
            ParamDef("max_line_gap", "最大断距", "slider", 15, 0, 100, 1, description="线段最大断裂间隙"),
            ParamDef("blur_ksize", "模糊核大小", "int", 3, 1, 15, 2, description="预处理高斯模糊核大小"),
            ParamDef("learn_mode", "自动学习", "bool", False, description="启用后根据ROI内容自动学习色差阈值"),
            ParamDef("draw_color", "标记颜色", "choice", "绿色",
                     choices=["绿色", "红色", "蓝色", "黄色", "青色", "白色"],
                     description="绘制直线的颜色"),
            ParamDef("line_thickness", "线宽", "int", 2, 1, 10, 1, description="标记线宽度"),
        ]

    def set_rois(self, rois: list[tuple[int, int, int, int]]):
        self._rois = rois

    def get_rois(self) -> list[tuple[int, int, int, int]]:
        return list(self._rois)

    def get_detected_lines(self) -> list[tuple[float, float, float, float]]:
        return list(self._detected_lines)

    def get_learned_line(self) -> tuple[float, float, float, float] | None:
        return self._learned_line

    def get_learned_thresholds(self) -> tuple[int, int] | None:
        return self._learned_thresholds

    def get_extra_data(self) -> dict:
        return {"rois": [list(r) for r in self._rois]}

    def set_extra_data(self, data: dict):
        if "rois" in data and isinstance(data["rois"], list):
            self._rois = [tuple(r) for r in data["rois"]]

    def auto_learn(self, img: np.ndarray, roi: tuple[int, int, int, int]) -> tuple | None:
        """
        自动学习ROI内的色差边缘。
        以ROI中间为基准线，扫描两侧色差，找到最优边缘位置。
        返回 (x1, y1, x2, y2, edge_t1, edge_t2) 或 None
        """
        rx, ry, rw, rh = roi
        if rw < 5 or rh < 5:
            return None

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        roi_img = gray[ry:ry + rh, rx:rx + rw]

        search_dir = self.get_param("search_direction")
        polarity = self.get_param("edge_polarity")
        blur_ks = self.get_param("blur_ksize")
        if blur_ks % 2 == 0:
            blur_ks += 1

        # 高斯模糊
        roi_blur = cv2.GaussianBlur(roi_img, (blur_ks, blur_ks), 0)

        if search_dir == "垂直":
            # 从上到下扫描，找水平线
            # 对每一列，计算垂直梯度，找到梯度最大的行
            grad = cv2.Sobel(roi_blur, cv2.CV_64F, 0, 1, ksize=3)
            edge_points = []

            for col in range(0, rw, max(1, rw // 30)):
                col_grad = grad[:, col]
                if polarity == "明到暗":
                    # 找最大负梯度（从亮到暗）
                    best_row = np.argmin(col_grad)
                elif polarity == "暗到明":
                    # 找最大正梯度（从暗到亮）
                    best_row = np.argmax(col_grad)
                else:
                    # 找最大绝对值梯度
                    best_row = np.argmax(np.abs(col_grad))

                grad_val = abs(col_grad[best_row])
                if grad_val > 5:
                    edge_points.append((col, best_row))

            if len(edge_points) < 3:
                return None

            points = np.array(edge_points, dtype=np.float32)
            # RANSAC 拟合直线 (返回 (4,1) 数组)
            result = cv2.fitLine(points, cv2.DIST_HUBER, 0, 0.01, 0.01)
            vx, vy, cx, cy = result[0, 0], result[1, 0], result[2, 0], result[3, 0]

            # 计算直线在ROI内的端点
            if abs(vx) > 1e-6:
                t_left = (0 - cx) / vx
                t_right = (rw - 1 - cx) / vx
                y_left = cy + t_left * vy
                y_right = cy + t_right * vy
            else:
                y_left = cy
                y_right = cy

            x1, y1 = rx + 0, ry + y_left
            x2, y2 = rx + rw - 1, ry + y_right

        else:
            # 从左到右扫描，找竖直线
            grad = cv2.Sobel(roi_blur, cv2.CV_64F, 1, 0, ksize=3)
            edge_points = []

            for row in range(0, rh, max(1, rh // 30)):
                row_grad = grad[row, :]
                if polarity == "明到暗":
                    best_col = np.argmin(row_grad)
                elif polarity == "暗到明":
                    best_col = np.argmax(row_grad)
                else:
                    best_col = np.argmax(np.abs(row_grad))

                grad_val = abs(row_grad[best_col])
                if grad_val > 5:
                    edge_points.append((best_col, row))

            if len(edge_points) < 3:
                return None

            points = np.array(edge_points, dtype=np.float32)
            result = cv2.fitLine(points, cv2.DIST_HUBER, 0, 0.01, 0.01)
            vx, vy, cx, cy = result[0, 0], result[1, 0], result[2, 0], result[3, 0]

            if abs(vy) > 1e-6:
                t_top = (0 - cy) / vy
                t_bottom = (rh - 1 - cy) / vy
                x_top = cx + t_top * vx
                x_bottom = cx + t_bottom * vx
            else:
                x_top = cx
                x_bottom = cx

            x1, y1 = rx + x_top, ry + 0
            x2, y2 = rx + x_bottom, ry + rh - 1

        # 计算梯度统计，自动设置Canny阈值
        grad_abs = np.abs(grad)
        grad_mean = float(np.mean(grad_abs))
        grad_std = float(np.std(grad_abs))
        edge_t1 = max(5, int(grad_mean))
        edge_t2 = max(10, int(grad_mean + grad_std * 1.5))

        self._learned_line = (float(x1), float(y1), float(x2), float(y2))
        self._learned_thresholds = (edge_t1, edge_t2)

        return (float(x1), float(y1), float(x2), float(y2), edge_t1, edge_t2)

    def execute(self) -> bool:
        img = self._inputs.get("input")
        if img is None:
            self._last_error = "没有输入图像"
            return False

        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                output = img.copy()
            else:
                gray = img.copy()
                output = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            color_map = {
                "绿色": (0, 255, 0), "红色": (0, 0, 255), "蓝色": (255, 0, 0),
                "黄色": (0, 255, 255), "青色": (255, 255, 0), "白色": (255, 255, 255),
            }
            draw_color = color_map.get(self.get_param("draw_color"), (0, 255, 0))
            line_thickness = self.get_param("line_thickness")
            learn_mode = self.get_param("learn_mode")

            edge_t1 = self.get_param("edge_threshold1")
            edge_t2 = self.get_param("edge_threshold2")
            hough_t = self.get_param("hough_threshold")
            min_len = self.get_param("min_line_length")
            max_gap = self.get_param("max_line_gap")
            blur_ks = self.get_param("blur_ksize")
            if blur_ks % 2 == 0:
                blur_ks += 1

            self._detected_lines = []

            if self._rois:
                regions = self._rois
            else:
                h, w = gray.shape[:2]
                regions = [(0, 0, w, h)]

            # 学习模式：使用自动学习到的阈值和线
            if learn_mode and self._learned_thresholds:
                edge_t1, edge_t2 = self._learned_thresholds
            elif learn_mode and self._rois:
                # 自动对每个ROI学习
                for roi in self._rois:
                    self.auto_learn(img, roi)
                if self._learned_thresholds:
                    edge_t1, edge_t2 = self._learned_thresholds

            for rx, ry, rw, rh in regions:
                rx = max(0, rx)
                ry = max(0, ry)
                rw = min(rw, gray.shape[1] - rx)
                rh = min(rh, gray.shape[0] - ry)
                if rw <= 0 or rh <= 0:
                    continue

                roi = gray[ry:ry + rh, rx:rx + rw]
                blurred = cv2.GaussianBlur(roi, (blur_ks, blur_ks), 0)
                edges = cv2.Canny(blurred, edge_t1, edge_t2)
                lines = cv2.HoughLinesP(edges, 1, np.pi / 180, hough_t,
                                        minLineLength=min_len, maxLineGap=max_gap)

                if lines is not None:
                    roi_center_x = rx + rw / 2
                    roi_center_y = ry + rh / 2
                    scored_lines = []

                    for line in lines:
                        if line.ndim == 2:
                            x1, y1, x2, y2 = line[0]
                        else:
                            x1, y1, x2, y2 = line
                        gx1, gy1 = rx + x1, ry + y1
                        gx2, gy2 = rx + x2, ry + y2

                        # 计算线段中点到ROI中心的距离
                        mid_x = (gx1 + gx2) / 2
                        mid_y = (gy1 + gy2) / 2
                        dist = np.sqrt((mid_x - roi_center_x) ** 2 + (mid_y - roi_center_y) ** 2)
                        scored_lines.append((dist, (gx1, gy1, gx2, gy2)))

                    if scored_lines:
                        # 只取距离ROI中心最近的一条线
                        scored_lines.sort(key=lambda x: x[0])
                        _, best = scored_lines[0]
                        gx1, gy1, gx2, gy2 = best
                        self._detected_lines.append((float(gx1), float(gy1), float(gx2), float(gy2)))
                        cv2.line(output, (int(gx1), int(gy1)), (int(gx2), int(gy2)),
                                draw_color, line_thickness)

            # 绘制ROI框
            for rx, ry, rw, rh in self._rois:
                cv2.rectangle(output, (rx, ry), (rx + rw, ry + rh), (0, 180, 255), 1)

            self._outputs["output"] = output
            self._outputs["line_count"] = len(self._detected_lines)
            self._outputs["line_coords"] = self._detected_lines
            return True
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            return False

    def get_last_error(self) -> str:
        return getattr(self, '_last_error', '')