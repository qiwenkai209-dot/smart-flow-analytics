"""
单元测试：跨摄像头 Re-ID 去重与全局 ID 映射
"""
import time
import pytest
import numpy as np
from core.reid.cross_cam_tracker import ReIDModel, CrossCameraTracker, PersonFeature


class DummyReIDModel(ReIDModel):
    """用于测试的 Mock Re-ID 模型，按指定特征输出"""
    def __init__(self):
        self.device = "cpu"
        self._model = None
        self._next_feat = None

    def set_feature(self, vec: np.ndarray):
        vec = vec.astype(np.float32)
        self._next_feat = vec / np.linalg.norm(vec)

    def extract_feature(self, crop: np.ndarray):
        if self._next_feat is not None:
            return self._next_feat
        # 默认随机单位向量
        vec = np.random.randn(2048).astype(np.float32)
        return vec / np.linalg.norm(vec)


def test_cross_cam_same_person():
    """同一人在不同摄像头出现，特征高度相似，应分配相同的 Global ID"""
    reid = DummyReIDModel()
    tracker = CrossCameraTracker(reid_model=reid, similarity_threshold=0.85)

    feat_a = np.ones(2048, dtype=np.float32)
    reid.set_feature(feat_a)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)

    # 摄像头 1 首次识别
    gid1 = tracker.register_or_match("cam_001", track_id=1, crop=crop)
    assert gid1 is not None

    # 同一摄像头后续帧直接查本地缓存
    gid1_again = tracker.register_or_match("cam_001", track_id=1, crop=crop)
    assert gid1_again == gid1

    # 摄像头 1 丢失该目标
    tracker.on_track_lost("cam_001", track_id=1)

    # 摄像头 2 出现高度相似特征（特征向量夹角极小，余弦相似度 > 0.99）
    feat_b = feat_a + np.random.normal(0, 0.01, size=2048).astype(np.float32)
    reid.set_feature(feat_b)

    gid2 = tracker.register_or_match("cam_002", track_id=99, crop=crop)
    assert gid2 == gid1, "同一人跨摄像头应分配相同的全局 ID"


def test_cross_cam_different_persons():
    """特征正交/不相似的两人，应分配不同的 Global ID"""
    reid = DummyReIDModel()
    tracker = CrossCameraTracker(reid_model=reid, similarity_threshold=0.85)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)

    # 向量 1：前半部分为 1
    v1 = np.zeros(2048, dtype=np.float32)
    v1[:1024] = 1.0
    reid.set_feature(v1)
    gid1 = tracker.register_or_match("cam_001", track_id=1, crop=crop)
    tracker.on_track_lost("cam_001", track_id=1)

    # 向量 2：后半部分为 1（正交，余弦相似度为 0）
    v2 = np.zeros(2048, dtype=np.float32)
    v2[1024:] = 1.0
    reid.set_feature(v2)
    gid2 = tracker.register_or_match("cam_002", track_id=2, crop=crop)

    assert gid1 != gid2, "不同人应分配不同的全局 ID"


def test_cross_cam_feature_cleanup():
    """测试过期特征向量自动淘汰清理"""
    reid = DummyReIDModel()
    tracker = CrossCameraTracker(reid_model=reid, feature_ttl=0.1)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)

    gid = tracker.register_or_match("cam_001", track_id=1, crop=crop)
    assert gid in tracker._global_features

    # 等待超过 TTL
    time.sleep(0.15)
    tracker.cleanup_expired()

    assert gid not in tracker._global_features, "超时特征应被清理"
