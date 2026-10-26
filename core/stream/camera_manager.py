import logging
import threading
from typing import Dict, Optional, List
from .rtsp_reader import RTSPReader, CameraConfig

logger = logging.getLogger(__name__)


class CameraManager:
    """
    多路摄像头动态管理器
    - 运行时动态增加/移除摄像头（无需重启服务）
    - 统一管理所有摄像头状态
    """

    def __init__(self):
        self._cameras: Dict[str, RTSPReader] = {}
        self._lock = threading.RLock()

    def add_camera(self, config: CameraConfig) -> bool:
        """动态新增一路摄像头"""
        with self._lock:
            if config.id in self._cameras:
                logger.warning(f"摄像头 [{config.id}] 已存在，请先移除再添加")
                return False
            reader = RTSPReader(config)
            reader.start()
            self._cameras[config.id] = reader
            logger.info(f"✅ 新增摄像头: [{config.id}] {config.name} | 当前共 {len(self._cameras)} 路")
            return True

    def remove_camera(self, camera_id: str) -> bool:
        """动态移除一路摄像头"""
        with self._lock:
            if camera_id not in self._cameras:
                logger.warning(f"摄像头 [{camera_id}] 不存在")
                return False
            reader = self._cameras.pop(camera_id)
            reader.stop()
            logger.info(f"🗑️ 移除摄像头: [{camera_id}] | 当前共 {len(self._cameras)} 路")
            return True

    def get_reader(self, camera_id: str) -> Optional[RTSPReader]:
        with self._lock:
            return self._cameras.get(camera_id)

    def list_cameras(self) -> List[dict]:
        with self._lock:
            return [reader.status for reader in self._cameras.values()]

    def camera_ids(self) -> List[str]:
        with self._lock:
            return list(self._cameras.keys())

    def stop_all(self):
        with self._lock:
            for reader in self._cameras.values():
                reader.stop()
            self._cameras.clear()
        logger.info("所有摄像头已停止")

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._cameras)
