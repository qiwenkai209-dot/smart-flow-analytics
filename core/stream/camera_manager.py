import logging
import threading
from typing import Dict, Optional, List, Any
from .rtsp_reader import RTSPReader, CameraConfig

logger = logging.getLogger(__name__)


class CameraManager:
    """
    多路摄像头与展台关联动态管理器
    - 运行时动态增加/编辑/移除摄像头
    - 统一管理摄像头业务分类（进出、驻留、属性）
    - 统一管理展台区域与摄像头的关联
    """

    def __init__(self):
        self._cameras: Dict[str, RTSPReader] = {}
        self._rois: Dict[str, dict] = {}  # {roi_name: {camera_id, polygon, min_dwell_seconds, ...}}
        self._lock = threading.RLock()
        self._load_defaults_if_empty()

    def _load_defaults_if_empty(self):
        """若无摄像头则初始化三路演示摄像头与固化展台"""
        if self._cameras:
            return
        default_cams = [
            CameraConfig(
                id="cam_001",
                name="展厅东门主入口",
                rtsp_url="rtsp://admin:admin123@192.168.1.64:554/Streaming/Channels/101",
                brand="hikvision",
                fps_limit=10,
                features=["in_out", "attribute_gender", "attribute_age"],
                ip="192.168.1.64",
                port=554,
                channel=1,
                subtype=0,
                rois=[
                    {
                        "name": "入口迎宾区",
                        "polygon": [[120, 240], [480, 240], [480, 520], [120, 520]],
                        "min_dwell_seconds": 3.0,
                    }
                ]
            ),
            CameraConfig(
                id="cam_002",
                name="展台A-AI体验区",
                rtsp_url="rtsp://admin:dahua123@192.168.1.65:554/cam/realmonitor?channel=1&subtype=0",
                brand="dahua",
                fps_limit=10,
                features=["dwell", "attribute_gender", "attribute_age"],
                ip="192.168.1.65",
                port=554,
                channel=1,
                subtype=0,
                rois=[
                    {
                        "name": "展台A",
                        "polygon": [[150, 260], [520, 260], [500, 600], [130, 600]],
                        "min_dwell_seconds": 5.0,
                    }
                ]
            ),
            CameraConfig(
                id="cam_003",
                name="展厅南门出口",
                rtsp_url="rtsp://admin:admin123@192.168.1.66:554/live/ch1",
                brand="generic",
                fps_limit=8,
                features=["in_out", "dwell"],
                ip="192.168.1.66",
                port=554,
                channel=1,
                subtype=0,
                rois=[
                    {
                        "name": "展台B",
                        "polygon": [[700, 260], [1080, 260], [1120, 620], [740, 620]],
                        "min_dwell_seconds": 8.0,
                    }
                ]
            ),
        ]
        for cfg in default_cams:
            self.add_camera(cfg)

    def persist_config(self):
        """将当前摄像头及固化展台写入 YAML 配置文件"""
        try:
            import os, yaml
            os.makedirs("configs", exist_ok=True)
            data = {"cameras": []}
            for cam in self._cameras.values():
                cfg = cam.config
                data["cameras"].append({
                    "id": cfg.id,
                    "name": cfg.name,
                    "brand": cfg.brand,
                    "rtsp_url": cfg.rtsp_url,
                    "fps_limit": cfg.fps_limit,
                    "features": cfg.features,
                    "ip": cfg.ip,
                    "port": cfg.port,
                    "username": cfg.username,
                    "password": cfg.password,
                    "channel": cfg.channel,
                    "subtype": cfg.subtype,
                    "rois": cfg.rois,
                })
            with open("configs/cameras.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            logger.info("💾 摄像头及固化区域已成功持久化至 configs/cameras.yaml")
        except Exception as e:
            logger.warning(f"持久化配置文件失败: {e}")


    def add_camera(self, config: CameraConfig) -> bool:
        """动态新增一路摄像头"""
        with self._lock:
            if config.id in self._cameras:
                logger.warning(f"摄像头 [{config.id}] 已存在，请先移除再添加")
                return False
            reader = RTSPReader(config)
            reader.start()
            self._cameras[config.id] = reader

            # 同步展台
            for r in config.rois:
                self._rois[r["name"]] = {
                    "name": r["name"],
                    "camera_id": config.id,
                    "camera_name": config.name,
                    "polygon": r.get("polygon", []),
                    "min_dwell_seconds": r.get("min_dwell_seconds", 5.0),
                }

            logger.info(f"✅ 新增摄像头: [{config.id}] {config.name} | 当前共 {len(self._cameras)} 路")
            return True

    def update_camera(self, config: CameraConfig) -> bool:
        """更新摄像头配置（名称、码流、功能标签、ROIs等）"""
        with self._lock:
            if config.id not in self._cameras:
                return False
            old_reader = self._cameras[config.id]
            url_changed = old_reader.config.rtsp_url != config.rtsp_url

            if url_changed:
                old_reader.stop()
                new_reader = RTSPReader(config)
                new_reader.start()
                self._cameras[config.id] = new_reader
            else:
                old_reader.config.name = config.name
                old_reader.config.fps_limit = config.fps_limit
                old_reader.config.features = config.features
                old_reader.config.rois = config.rois

            # 更新该摄像头下的展台映射
            for r in config.rois:
                self._rois[r["name"]] = {
                    "name": r["name"],
                    "camera_id": config.id,
                    "camera_name": config.name,
                    "polygon": r.get("polygon", []),
                    "min_dwell_seconds": r.get("min_dwell_seconds", 5.0),
                }

            logger.info(f"✏️ 更新摄像头: [{config.id}] {config.name}")
            return True

    def remove_camera(self, camera_id: str) -> bool:
        """动态移除一路摄像头"""
        with self._lock:
            if camera_id not in self._cameras:
                logger.warning(f"摄像头 [{camera_id}] 不存在")
                return False
            reader = self._cameras.pop(camera_id)
            reader.stop()

            # 清理关联的展台映射
            to_del = [name for name, r in self._rois.items() if r.get("camera_id") == camera_id]
            for name in to_del:
                del self._rois[name]

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

    # ─── 展台 ROI 关联管理 ──────────────────────────────────────────

    def list_rois(self) -> List[dict]:
        with self._lock:
            # 保证返回最新数据
            rois = []
            for name, r in self._rois.items():
                cam = self._cameras.get(r.get("camera_id"))
                cam_name = cam.config.name if cam else r.get("camera_name", "未指定")
                rois.append({
                    "name": name,
                    "camera_id": r.get("camera_id"),
                    "camera_name": cam_name,
                    "polygon": r.get("polygon", []),
                    "min_dwell_seconds": r.get("min_dwell_seconds", 5.0),
                })
            return rois

    def add_or_update_roi(self, name: str, camera_id: str, polygon: list, min_dwell_seconds: float = 5.0) -> bool:
        with self._lock:
            cam = self._cameras.get(camera_id)
            cam_name = cam.config.name if cam else camera_id
            self._rois[name] = {
                "name": name,
                "camera_id": camera_id,
                "camera_name": cam_name,
                "polygon": polygon,
                "min_dwell_seconds": min_dwell_seconds,
            }
            # 同步写回 camera 的 rois 列表
            if cam:
                cam.config.rois = [r for r in cam.config.rois if r.get("name") != name]
                cam.config.rois.append({
                    "name": name,
                    "polygon": polygon,
                    "min_dwell_seconds": min_dwell_seconds,
                })
            self.persist_config()
            return True

    def delete_roi(self, name: str) -> bool:
        with self._lock:
            if name not in self._rois:
                return False
            cam_id = self._rois[name].get("camera_id")
            del self._rois[name]
            if cam_id and cam_id in self._cameras:
                cam = self._cameras[cam_id]
                cam.config.rois = [r for r in cam.config.rois if r.get("name") != name]
            self.persist_config()
            return True

    def stop_all(self):
        with self._lock:
            for reader in self._cameras.values():
                reader.stop()
            self._cameras.clear()
            self._rois.clear()
        logger.info("所有摄像头已停止")

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._cameras)
