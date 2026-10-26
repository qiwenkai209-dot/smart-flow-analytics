"""
ByteTrack 多目标追踪器封装
依赖：ultralytics 内置 ByteTrack（无需单独安装）
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Track:
    track_id: int
    bbox: List[float]          # [x1, y1, x2, y2]
    confidence: float
    # 脚部接地点（用于 ROI 多边形判定）
    foot_point: List[float] = field(default_factory=list)
    # 属性（延迟填充，不是每帧都有）
    gender: Optional[str] = None          # "male" | "female"
    age_group: Optional[str] = None       # "child" | "young" | "adult" | "elder"
    attribute_done: bool = False          # 是否已完成属性识别

    def __post_init__(self):
        if not self.foot_point:
            # 取 BBox 底边中点作为脚部接地坐标
            x1, y1, x2, y2 = self.bbox
            self.foot_point = [(x1 + x2) / 2, y2]


class ByteTracker:
    """
    ByteTrack 追踪器封装
    - 为每个 Detection 分配持久化 Track ID
    - 使用 ultralytics 内置的 ByteTrack，无需额外安装
    """

    def __init__(self, track_high_thresh: float = 0.5, track_low_thresh: float = 0.1,
                 new_track_thresh: float = 0.6, track_buffer: int = 30, match_thresh: float = 0.8):
        self.args = {
            "track_high_thresh": track_high_thresh,
            "track_low_thresh": track_low_thresh,
            "new_track_thresh": new_track_thresh,
            "track_buffer": track_buffer,
            "match_thresh": match_thresh,
        }
        self._tracker = None
        self._init_tracker()

    def _init_tracker(self):
        try:
            from ultralytics.trackers.byte_tracker import BYTETracker
            import argparse
            args = argparse.Namespace(**self.args)
            self._tracker = BYTETracker(args, frame_rate=10)
            logger.info("ByteTrack 追踪器初始化完成 ✅")
        except ImportError:
            logger.error("无法导入 ByteTrack，请确保 ultralytics >= 8.0 已安装")
            raise

    def update(self, detections: List, frame_shape: tuple) -> List[Track]:
        """
        输入：DetectionList，输出：Track 列表（含 track_id）
        """
        if not detections:
            return []

        # 转换为 ByteTrack 要求的格式 [x1, y1, x2, y2, conf]
        dets_np = np.array([[*d.bbox, d.confidence] for d in detections], dtype=np.float32)

        tracks_raw = self._tracker.update(dets_np, frame_shape[:2])

        tracks: List[Track] = []
        for t in tracks_raw:
            x1, y1, x2, y2 = t.tlbr
            tracks.append(Track(
                track_id=int(t.track_id),
                bbox=[float(x1), float(y1), float(x2), float(y2)],
                confidence=float(t.score),
            ))
        return tracks
