"""
多路摄像头 Pipeline 调度器
- 统一管理所有路摄像头的 Pipeline 生命周期
- 所有路共享同一个 CrossCameraTracker（Re-ID 全局去重）
- 动态增减摄像头无需重启
"""
import logging
import threading
from typing import Dict, List, Optional, Callable

from .pipeline import CameraPipeline, PipelineConfig, FlowEvent
from .roi.roi_manager import ROIManager, ROIConfig
from .reid.cross_cam_tracker import CrossCameraTracker, ReIDModel
from .stream.rtsp_reader import CameraConfig

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    多路 Pipeline 总调度器
    所有摄像头共享：
      - CrossCameraTracker（跨镜头 Re-ID 全局去重）
      - ROIManager（统一管理所有展台区域）
    """

    def __init__(
        self,
        roi_configs: List[ROIConfig],
        reid_model_path: str = "models/reid/fast_reid_r50.pth",
        device: str = "cpu",
        on_event: Optional[Callable[[FlowEvent], None]] = None,
        snapshot_dir: str = "snapshots",
    ):
        self.device = device
        self.on_event = on_event
        self.snapshot_dir = snapshot_dir

        # 共享组件（跨所有摄像头）
        self.roi_manager = ROIManager(roi_configs)
        reid_model = ReIDModel(model_path=reid_model_path, device=device)
        self.cross_cam_tracker = CrossCameraTracker(reid_model)

        self._pipelines: Dict[str, CameraPipeline] = {}
        self._lock = threading.RLock()

        logger.info(f"PipelineOrchestrator 初始化完成 | ROI 数量: {len(roi_configs)} | 设备: {device}")

    def add_camera(
        self,
        camera_config: CameraConfig,
        detector_model: str = "models/yolo11m.pt",
        attribute_model: str = "models/attribute/pphumans_attribute.onnx",
        draw_debug: bool = False,
    ) -> bool:
        with self._lock:
            if camera_config.id in self._pipelines:
                logger.warning(f"[{camera_config.id}] Pipeline 已存在")
                return False

            config = PipelineConfig(
                camera=camera_config,
                detector_model=detector_model,
                attribute_model=attribute_model,
                device=self.device,
                draw_debug=draw_debug,
            )
            pipeline = CameraPipeline(
                config=config,
                roi_manager=self.roi_manager,
                cross_cam_tracker=self.cross_cam_tracker,
                on_event=self.on_event,
                snapshot_dir=self.snapshot_dir,
            )
            pipeline.start()
            self._pipelines[camera_config.id] = pipeline
            logger.info(f"✅ 新增摄像头 Pipeline: [{camera_config.id}] | 当前共 {len(self._pipelines)} 路")
            return True

    def remove_camera(self, camera_id: str) -> bool:
        with self._lock:
            pipeline = self._pipelines.pop(camera_id, None)
            if not pipeline:
                logger.warning(f"[{camera_id}] Pipeline 不存在")
                return False
            pipeline.stop()
            logger.info(f"🗑️ 移除摄像头 Pipeline: [{camera_id}] | 当前共 {len(self._pipelines)} 路")
            return True

    def get_pipeline(self, camera_id: str) -> Optional[CameraPipeline]:
        with self._lock:
            return self._pipelines.get(camera_id)

    def get_all_stats(self) -> List[dict]:
        with self._lock:
            return [
                {
                    "camera_id": cid,
                    "connected": p.reader.is_connected,
                    "fps": round(p.reader.fps_actual, 1),
                    "active_tracks": p.stats["active_tracks"],
                    "frames_processed": p.stats["frames_processed"],
                    "events_fired": p.stats["events_fired"],
                    "reid_active": self.cross_cam_tracker.active_count,
                }
                for cid, p in self._pipelines.items()
            ]

    def stop_all(self):
        with self._lock:
            for pipeline in self._pipelines.values():
                pipeline.stop()
            self._pipelines.clear()
        logger.info("所有 Pipeline 已停止")

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._pipelines)
