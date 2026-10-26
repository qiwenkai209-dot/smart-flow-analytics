"""
PP-Human 全身属性识别模块
- 不依赖人脸，使用全身体态进行性别/年龄段识别
- 采用"稳定帧单次触发"策略，极度省算力
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict
import numpy as np
import cv2

logger = logging.getLogger(__name__)

GENDER_LABELS = {0: "female", 1: "male"}
AGE_LABELS = {0: "child", 1: "young", 2: "adult", 3: "elder"}


@dataclass
class AttributeResult:
    gender: str              # "male" | "female"
    age_group: str           # "child" | "young" | "adult" | "elder"
    gender_conf: float
    age_conf: float
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class AttributeModel:
    """
    PP-Human PULC 全身属性识别
    输入：人体 BBox 裁剪图
    输出：性别 + 年龄段
    """

    def __init__(self, model_path: str = "models/attribute/pphumans_attribute.onnx",
                 device: str = "cpu",
                 min_body_height: int = 60):
        self.device = device
        self.min_body_height = min_body_height  # 裁剪图高度过小时跳过识别
        self._model = None
        self._load_model(model_path)

    def _load_model(self, model_path: str):
        try:
            import onnxruntime as ort
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if self.device != "cpu" \
                else ["CPUExecutionProvider"]
            self._model = ort.InferenceSession(model_path, providers=providers)
            self._input_name = self._model.get_inputs()[0].name
            logger.info(f"属性识别模型加载完成: {model_path} ✅")
        except Exception as e:
            logger.warning(f"属性识别模型加载失败（将使用占位符）: {e}")

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        img = cv2.resize(crop, (128, 256))
        img = img.astype(np.float32) / 255.0
        img = (img - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
        img = img.transpose(2, 0, 1)[np.newaxis, ...]  # NCHW
        return img

    def predict(self, crop: np.ndarray) -> Optional[AttributeResult]:
        """
        输入：BGR 人体裁剪图
        输出：AttributeResult 或 None（图像质量不足时）
        """
        h, w = crop.shape[:2]
        if h < self.min_body_height:
            return None

        if self._model is None:
            # 占位符：返回随机结果（仅开发调试用）
            import random
            return AttributeResult(
                gender=random.choice(["male", "female"]),
                age_group=random.choice(["child", "young", "adult", "elder"]),
                gender_conf=random.uniform(0.7, 0.95),
                age_conf=random.uniform(0.6, 0.9),
            )

        inp = self._preprocess(crop)
        outputs = self._model.run(None, {self._input_name: inp})
        gender_probs, age_probs = outputs[0][0], outputs[1][0]

        gender_idx = int(np.argmax(gender_probs))
        age_idx = int(np.argmax(age_probs))

        return AttributeResult(
            gender=GENDER_LABELS[gender_idx],
            age_group=AGE_LABELS[age_idx],
            gender_conf=float(gender_probs[gender_idx]),
            age_conf=float(age_probs[age_idx]),
        )


class AttributeScheduler:
    """
    属性识别触发调度器
    - 每个 Global ID 只在追踪稳定后识别 1 次
    - 确保裁剪图像面积最大时才触发
    - 防止算力浪费
    """

    def __init__(self, model: AttributeModel, stable_frames: int = 5):
        self.model = model
        self.stable_frames = stable_frames
        # {global_id: {"frames": int, "best_crop": np.ndarray, "best_area": float}}
        self._buffer: Dict[str, dict] = {}
        # {global_id: AttributeResult}
        self._results: Dict[str, AttributeResult] = {}

    def submit(self, global_id: str, frame: np.ndarray, bbox: list) -> Optional[AttributeResult]:
        """
        提交一帧人体位置，调度器决定是否触发识别
        返回：属性结果（若已完成）或 None
        """
        # 已有结果直接返回
        if global_id in self._results:
            return self._results[global_id]

        x1, y1, x2, y2 = [int(v) for v in bbox]
        area = (x2 - x1) * (y2 - y1)

        if global_id not in self._buffer:
            self._buffer[global_id] = {"frames": 0, "best_crop": None, "best_area": 0}

        buf = self._buffer[global_id]
        buf["frames"] += 1

        # 记录面积最大的裁剪图
        if area > buf["best_area"]:
            crop = frame[max(0, y1):y2, max(0, x1):x2]
            if crop.size > 0:
                buf["best_crop"] = crop.copy()
                buf["best_area"] = area

        # 稳定帧数达到后，触发一次属性识别
        if buf["frames"] >= self.stable_frames and buf["best_crop"] is not None:
            result = self.model.predict(buf["best_crop"])
            if result:
                self._results[global_id] = result
                del self._buffer[global_id]
                logger.debug(f"属性识别完成: {global_id} -> {result.gender}/{result.age_group}")
                return result

        return None

    def get_result(self, global_id: str) -> Optional[AttributeResult]:
        return self._results.get(global_id)

    def cleanup(self, global_id: str):
        self._buffer.pop(global_id, None)
        # 注意：结果保留一段时间，在 Re-ID 重识别时仍然有用
