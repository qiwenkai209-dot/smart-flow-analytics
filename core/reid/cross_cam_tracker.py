"""
跨摄像头 Re-ID（行人重识别）模块
- 基于 FastReID 提取全身特征向量
- 余弦相似度比对，实现跨摄像头去重
- 全局 ID 分配与管理
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PersonFeature:
    global_id: str
    camera_id: str
    local_track_id: int
    feature_vector: np.ndarray
    last_seen: float = field(default_factory=time.time)
    gender: Optional[str] = None
    age_group: Optional[str] = None


class ReIDModel:
    """
    Re-ID 特征提取模型封装（FastReID）
    提取行人全身外观特征向量（2048-dim）
    """

    def __init__(self, model_path: str = "models/reid/fast_reid.pth",
                 device: str = "cpu"):
        self.device = device
        self.model_path = model_path
        self._model = None
        self._load_model()

    def _load_model(self):
        try:
            import importlib
            if importlib.util.find_spec("torch") is None:
                raise ImportError
            logger.info(f"Re-ID 模型加载: {self.model_path} @ {self.device}")
            # self._model = ...
            logger.warning("Re-ID 模型占位符已初始化，请替换为真实 FastReID 模型")
        except ImportError:
            logger.error("请安装 torch: pip install torch")


    def extract_feature(self, crop: np.ndarray) -> Optional[np.ndarray]:
        """
        输入：人体裁剪图（BGR, H x W x 3）
        输出：归一化特征向量（L2 norm, shape=[2048]）
        """
        if self._model is None:
            # 占位符：返回随机向量（仅用于开发调试）
            vec = np.random.randn(2048).astype(np.float32)
            vec /= np.linalg.norm(vec)
            return vec

        # 真实推理代码（接入 FastReID 后替换此处）
        # ...
        return None


class CrossCameraTracker:
    """
    跨摄像头全局追踪器
    - 维护全局特征库（带 TTL 过期机制）
    - 为每个新出现的人分配全局 Global ID
    - 同一人跨摄像头出现时识别并合并
    """

    def __init__(
        self,
        reid_model: ReIDModel,
        similarity_threshold: float = 0.85,    # 高于此值认为是同一人
        uncertain_threshold: float = 0.60,      # 低于此值认为是不同人
        feature_ttl: float = 1800.0,            # 特征向量 TTL（秒），超时淘汰
        match_window: float = 30.0,             # 同一摄像头消失后 N 秒内才触发跨摄像头比对
    ):
        self.reid_model = reid_model
        self.similarity_threshold = similarity_threshold
        self.uncertain_threshold = uncertain_threshold
        self.feature_ttl = feature_ttl
        self.match_window = match_window

        # 全局特征库：{global_id: PersonFeature}
        self._global_features: Dict[str, PersonFeature] = {}

        # 本地 ID 到全局 ID 的映射：{(camera_id, track_id): global_id}
        self._local_to_global: Dict[Tuple[str, int], str] = {}

        # 上次每个 global_id 在各路摄像头的消失时间：{(camera_id, global_id): disappear_time}
        self._disappear_time: Dict[Tuple[str, str], float] = {}

    def register_or_match(
        self,
        camera_id: str,
        track_id: int,
        crop: np.ndarray,
    ) -> str:
        """
        输入：摄像头ID、本地 track_id、人体裁剪图
        输出：全局 Global ID（同一人跨摄像头返回相同 ID）
        """
        local_key = (camera_id, track_id)

        # 已有映射直接返回
        if local_key in self._local_to_global:
            global_id = self._local_to_global[local_key]
            # 更新最后出现时间
            if global_id in self._global_features:
                self._global_features[global_id].last_seen = time.time()
            return global_id

        # 提取特征向量
        feature = self.reid_model.extract_feature(crop)
        if feature is None:
            # 特征提取失败，分配新 ID
            global_id = self._new_global_id()
            self._local_to_global[local_key] = global_id
            return global_id

        # 执行全局特征库比对
        global_id = self._match_or_create(camera_id, track_id, feature)
        self._local_to_global[local_key] = global_id
        return global_id

    def _match_or_create(self, camera_id: str, track_id: int, feature: np.ndarray) -> str:
        """与全局特征库做余弦相似度比对"""
        self._cleanup_expired()

        best_id: Optional[str] = None
        best_sim: float = 0.0
        now = time.time()

        for gid, pf in self._global_features.items():
            # 只对最近消失过的特征进行比对（省算力）
            # 获取该目标在上一个摄像头的消失时间或最后出现时间
            disappeared_at = self._disappear_time.get((pf.camera_id, gid), pf.last_seen)
            if (now - disappeared_at) > self.match_window and pf.camera_id != camera_id:
                continue  # 超过时间窗口，跳过

            sim = float(np.dot(feature, pf.feature_vector))
            if sim > best_sim:
                best_sim = sim
                best_id = gid

        if best_sim >= self.similarity_threshold and best_id:
            logger.debug(f"Re-ID 匹配成功: ({camera_id},{track_id}) -> {best_id} (sim={best_sim:.3f})")
            self._global_features[best_id].feature_vector = feature  # 更新特征
            self._global_features[best_id].last_seen = now
            self._global_features[best_id].camera_id = camera_id
            return best_id
        elif best_sim >= self.uncertain_threshold and best_id:
            logger.debug(f"Re-ID 不确定: sim={best_sim:.3f}，分配新 ID")

        # 分配新 Global ID
        global_id = self._new_global_id()
        self._global_features[global_id] = PersonFeature(
            global_id=global_id,
            camera_id=camera_id,
            local_track_id=track_id,
            feature_vector=feature,
        )
        logger.debug(f"新 Global ID: {global_id} ({camera_id},{track_id})")
        return global_id

    def on_track_lost(self, camera_id: str, track_id: int):
        """当追踪器丢失某个 track 时调用，记录消失时间"""
        local_key = (camera_id, track_id)
        global_id = self._local_to_global.pop(local_key, None)
        if global_id:
            self._disappear_time[(camera_id, global_id)] = time.time()

    def cleanup_expired(self):
        """清理过期特征向量（公共接口）"""
        self._cleanup_expired()

    def _cleanup_expired(self):
        """清理过期特征向量（TTL 机制）"""
        now = time.time()
        expired = [gid for gid, pf in self._global_features.items()
                   if now - pf.last_seen > self.feature_ttl]
        for gid in expired:
            del self._global_features[gid]
            logger.debug(f"过期清理 Global ID: {gid}")

    @staticmethod
    def _new_global_id() -> str:
        return f"G-{uuid.uuid4().hex[:8].upper()}"

    @property
    def active_count(self) -> int:
        return len(self._global_features)
