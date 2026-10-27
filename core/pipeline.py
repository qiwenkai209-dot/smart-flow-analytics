"""
单路摄像头全流程 Pipeline 编排
流程：取流 → YOLO11 检测 → ByteTrack 追踪 → Re-ID 全局去重
     → PP-Human 属性（单次触发）→ 多边形 ROI 驻留计时 → 事件写入队列
"""
import logging
import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable
import numpy as np
import cv2

from .stream.rtsp_reader import RTSPReader, CameraConfig
from .detect.detector import PersonDetector
from .detect.tracker import ByteTracker
from .attribute.attribute_model import AttributeModel, AttributeScheduler
from .reid.cross_cam_tracker import CrossCameraTracker
from .roi.roi_manager import ROIManager, DwellTracker

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    camera: CameraConfig
    detector_model: str = "models/yolo11m.pt"
    reid_model: str = "models/reid/fast_reid_r50.pth"
    attribute_model: str = "models/attribute/pphumans_attribute.onnx"
    device: str = "cpu"          # "cpu" | "cuda:0"
    conf_threshold: float = 0.45
    draw_debug: bool = False     # 是否在帧上绘制调试信息（开发期用）


@dataclass
class FlowEvent:
    """单次人员进出 / 驻留完成事件（写入数据库）"""
    event_type: str              # "enter" | "leave" | "dwell_complete"
    global_id: str
    camera_id: str
    roi_name: Optional[str]
    timestamp: float
    gender: Optional[str] = None
    age_group: Optional[str] = None
    dwell_seconds: Optional[float] = None
    snapshot_path: Optional[str] = None


class CameraPipeline:
    """
    单路摄像头完整 AI 分析 Pipeline
    - 在独立线程中运行，不阻塞主进程
    - 通过 on_event 回调向外推送分析事件
    - 通过 latest_frame 属性获取最新渲染帧（供预览）
    """

    def __init__(
        self,
        config: PipelineConfig,
        roi_manager: ROIManager,
        cross_cam_tracker: CrossCameraTracker,  # 跨摄像头共享同一个实例
        on_event: Optional[Callable[[FlowEvent], None]] = None,
        snapshot_dir: str = "snapshots",
    ):
        self.config = config
        self.camera_id = config.camera.id
        self.on_event = on_event
        self.snapshot_dir = snapshot_dir

        # 组件初始化
        self.reader = RTSPReader(config.camera)
        self.detector = PersonDetector(
            model_path=config.detector_model,
            device=config.device,
            conf_threshold=config.conf_threshold,
        )
        self.tracker = ByteTracker()
        self.attribute_model = AttributeModel(
            model_path=config.attribute_model,
            device=config.device,
        )
        self.attribute_scheduler = AttributeScheduler(self.attribute_model)
        self.cross_cam_tracker = cross_cam_tracker
        self.roi_manager = roi_manager
        self.dwell_tracker = DwellTracker(roi_manager)

        # 运行状态
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()

        # 统计计数
        self.stats = {
            "frames_processed": 0,
            "total_detections": 0,
            "active_tracks": 0,
            "events_fired": 0,
        }

    def start(self):
        self._running = True
        self.reader.start()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name=f"pipeline-{self.camera_id}",
        )
        self._thread.start()
        logger.info(f"[{self.camera_id}] Pipeline 启动 ✅")

    def stop(self):
        self._running = False
        self.reader.stop()
        if self._thread:
            self._thread.join(timeout=10.0)
        logger.info(f"[{self.camera_id}] Pipeline 已停止")

    @property
    def latest_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def _run_loop(self):
        """Pipeline 主循环"""
        logger.info(f"[{self.camera_id}] 开始等待视频帧...")

        while self._running:
            frame = self.reader.read(timeout=2.0)
            if frame is None:
                continue

            t_start = time.perf_counter()
            render_frame = frame.copy() if self.config.draw_debug else frame

            try:
                self._process_frame(frame, render_frame)
            except Exception as e:
                logger.error(f"[{self.camera_id}] 帧处理异常: {e}", exc_info=True)

            # 处理驻留完成事件
            self._flush_dwell_events()

            # 更新预览帧
            if self.config.draw_debug:
                self.roi_manager.draw_rois(render_frame)
                with self._frame_lock:
                    self._latest_frame = render_frame
            else:
                with self._frame_lock:
                    self._latest_frame = frame

            t_end = time.perf_counter()
            self.stats["frames_processed"] += 1

            logger.debug(f"[{self.camera_id}] 帧耗时: {(t_end - t_start)*1000:.1f}ms | "
                         f"追踪目标: {self.stats['active_tracks']}")

    def _process_frame(self, frame: np.ndarray, render_frame: np.ndarray):
        """单帧处理核心逻辑"""

        # ── 1. 人体检测 ─────────────────────────────────────────────
        detections = self.detector.detect(frame)
        self.stats["total_detections"] += len(detections)

        # ── 2. 多目标追踪（ByteTrack）─────────────────────────────
        tracks = self.tracker.update(detections, frame.shape)
        self.stats["active_tracks"] = len(tracks)

        for track in tracks:
            x1, y1, x2, y2 = [int(v) for v in track.bbox]
            crop = frame[max(0, y1):y2, max(0, x1):x2]
            if crop.size == 0:
                continue

            # ── 3. Re-ID 跨摄像头全局去重 ─────────────────────────
            global_id = self.cross_cam_tracker.register_or_match(
                self.camera_id, track.track_id, crop
            )

            # ── 4. 属性识别（单次触发，省算力）─────────────────────
            attr = self.attribute_scheduler.submit(global_id, frame, track.bbox)
            if attr:
                track.gender = attr.gender
                track.age_group = attr.age_group
            else:
                # 复用已有属性结果
                cached = self.attribute_scheduler.get_result(global_id)
                if cached:
                    track.gender = cached.gender
                    track.age_group = cached.age_group

            # ── 5. 多边形 ROI 驻留计时更新 ────────────────────────
            self.dwell_tracker.update(
                global_id=global_id,
                camera_id=self.camera_id,
                foot_point=track.foot_point,
                gender=track.gender,
                age_group=track.age_group,
            )

            # ── 6. 调试绘制 ───────────────────────────────────────
            if self.config.draw_debug:
                self._draw_track(render_frame, track, global_id)

    def _flush_dwell_events(self):
        """将已完成的驻留记录转换为 FlowEvent 推送"""
        for record in self.dwell_tracker.flush_records():
            event = FlowEvent(
                event_type="dwell_complete",
                global_id=record.global_id,
                camera_id=record.camera_id,
                roi_name=record.roi_name,
                timestamp=record.leave_time or time.time(),
                gender=record.gender,
                age_group=record.age_group,
                dwell_seconds=record.dwell_seconds,
            )
            self.stats["events_fired"] += 1
            if self.on_event:
                try:
                    self.on_event(event)
                except Exception as e:
                    logger.error(f"事件回调异常: {e}")

    def _draw_track(self, frame: np.ndarray, track, global_id: str):
        """在画面上绘制追踪框与属性标签（调试用）"""
        x1, y1, x2, y2 = [int(v) for v in track.bbox]
        color = (0, 200, 255)

        # 画框
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # 画脚部接地点
        fx, fy = int(track.foot_point[0]), int(track.foot_point[1])
        cv2.circle(frame, (fx, fy), 4, (0, 0, 255), -1)

        # 标签
        gender_str = {"male": "♂", "female": "♀"}.get(track.gender, "?")
        age_str = {"child": "儿童", "young": "青年", "adult": "成年", "elder": "老年"}.get(
            track.age_group, "?"
        )
        label = f"{global_id[-6:]} {gender_str}{age_str}"
        cv2.putText(frame, label, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
