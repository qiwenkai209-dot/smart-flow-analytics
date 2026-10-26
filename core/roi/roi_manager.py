"""
ROI 多边形区域管理 + 驻留时长计时器
- 支持多个命名多边形区域
- 以人体 BBox 脚部接地点作为判定依据
- 加入防抖机制（连续 N 帧才算进入/离开）
"""
import time
import logging
import json
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np
import cv2

logger = logging.getLogger(__name__)


@dataclass
class ROIConfig:
    name: str                          # 展台名称，如"展台A"
    polygon: List[List[float]]         # 多边形顶点坐标 [[x1,y1],[x2,y2],...]
    min_dwell_seconds: float = 5.0     # 最短有效驻留时长（过滤穿堂人员）
    color: Tuple[int, int, int] = (0, 255, 128)


@dataclass
class DwellRecord:
    global_id: str                     # 全局唯一 ID（Re-ID 去重后）
    camera_id: str
    roi_name: str
    enter_time: float
    leave_time: Optional[float] = None
    dwell_seconds: float = 0.0
    gender: Optional[str] = None
    age_group: Optional[str] = None


class ROIManager:
    """多边形 ROI 管理器"""

    def __init__(self, rois: List[ROIConfig]):
        self.rois = {roi.name: roi for roi in rois}
        # 将多边形顶点转为 numpy 格式（cv2 要求）
        self._contours = {
            name: np.array(roi.polygon, dtype=np.int32)
            for name, roi in self.rois.items()
        }
        logger.info(f"ROI 区域加载完成：{list(self.rois.keys())}")

    def point_in_roi(self, roi_name: str, point: List[float]) -> bool:
        """判断点是否在指定 ROI 多边形内"""
        contour = self._contours.get(roi_name)
        if contour is None:
            return False
        result = cv2.pointPolygonTest(contour, (float(point[0]), float(point[1])), False)
        return result >= 0

    def get_point_rois(self, point: List[float]) -> List[str]:
        """返回点所在的所有 ROI 名称（可能同时属于多个区域）"""
        return [name for name in self.rois if self.point_in_roi(name, point)]

    def draw_rois(self, frame: np.ndarray, alpha: float = 0.25) -> np.ndarray:
        """在画面上绘制 ROI 多边形（半透明覆盖层）"""
        overlay = frame.copy()
        for name, roi in self.rois.items():
            contour = self._contours[name]
            cv2.fillPoly(overlay, [contour], roi.color)
            cv2.polylines(frame, [contour], True, roi.color, 2)
            # 在多边形重心处写名称
            cx = int(contour[:, 0].mean())
            cy = int(contour[:, 1].mean())
            cv2.putText(frame, name, (cx - 30, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, roi.color, 2)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        return frame

    def add_roi(self, roi: ROIConfig):
        """动态新增 ROI（不需要重启）"""
        self.rois[roi.name] = roi
        self._contours[roi.name] = np.array(roi.polygon, dtype=np.int32)
        logger.info(f"新增 ROI：{roi.name}")

    def remove_roi(self, name: str):
        """动态移除 ROI"""
        self.rois.pop(name, None)
        self._contours.pop(name, None)
        logger.info(f"移除 ROI：{name}")


class DwellTracker:
    """
    驻留时长跟踪器
    - 以 global_id + roi_name 为单位计时
    - 支持进出事件回调
    """

    def __init__(self, roi_manager: ROIManager, debounce_frames: int = 5):
        self.roi_manager = roi_manager
        self.debounce_frames = debounce_frames  # 连续 N 帧才触发进出事件（防抖）

        # {global_id: {roi_name: {"enter_time": float, "frame_count": int}}}
        self._state: Dict[str, Dict[str, dict]] = {}
        # 已完成的驻留记录（等待写入数据库）
        self.completed_records: List[DwellRecord] = []
        # 进入帧计数（防抖）
        self._enter_buffer: Dict[str, Dict[str, int]] = {}

    def update(self, global_id: str, camera_id: str, foot_point: List[float],
               gender: Optional[str] = None, age_group: Optional[str] = None):
        """
        每帧更新某个人的位置，自动触发进出事件
        """
        current_rois = set(self.roi_manager.get_point_rois(foot_point))
        now = time.time()

        if global_id not in self._state:
            self._state[global_id] = {}
        if global_id not in self._enter_buffer:
            self._enter_buffer[global_id] = {}

        prev_rois = set(self._state[global_id].keys())

        # 处理新进入的 ROI（防抖计数）
        for roi_name in current_rois - prev_rois:
            self._enter_buffer[global_id][roi_name] = self._enter_buffer[global_id].get(roi_name, 0) + 1
            if self._enter_buffer[global_id][roi_name] >= self.debounce_frames:
                self._state[global_id][roi_name] = {"enter_time": now, "camera_id": camera_id,
                                                     "gender": gender, "age_group": age_group}
                self._enter_buffer[global_id].pop(roi_name, None)
                logger.debug(f"[进入] {global_id} -> {roi_name}")

        # 处理离开的 ROI
        for roi_name in prev_rois - current_rois:
            state = self._state[global_id].pop(roi_name, None)
            self._enter_buffer[global_id].pop(roi_name, None)
            if state:
                dwell_seconds = now - state["enter_time"]
                roi_config = self.roi_manager.rois.get(roi_name)
                min_dwell = roi_config.min_dwell_seconds if roi_config else 5.0
                if dwell_seconds >= min_dwell:
                    record = DwellRecord(
                        global_id=global_id,
                        camera_id=state["camera_id"],
                        roi_name=roi_name,
                        enter_time=state["enter_time"],
                        leave_time=now,
                        dwell_seconds=round(dwell_seconds, 1),
                        gender=state.get("gender"),
                        age_group=state.get("age_group"),
                    )
                    self.completed_records.append(record)
                    logger.info(f"[驻留完成] {global_id} @ {roi_name} 停留 {dwell_seconds:.1f}s "
                                f"| 性别: {state.get('gender')} 年龄段: {state.get('age_group')}")

    def flush_records(self) -> List[DwellRecord]:
        """取出并清空待写入的驻留记录列表"""
        records = self.completed_records.copy()
        self.completed_records.clear()
        return records

    def remove_person(self, global_id: str):
        """某人长时间消失时，清理其追踪状态"""
        self._state.pop(global_id, None)
        self._enter_buffer.pop(global_id, None)
