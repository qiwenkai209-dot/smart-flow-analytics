import logging
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    bbox: List[float]        # [x1, y1, x2, y2]
    confidence: float
    class_id: int = 0        # 0 = person


class PersonDetector:
    """
    人体检测器（基于 YOLO11 / YOLOv8，只保留 person 类别）
    支持 ONNX / TensorRT 加速部署
    """

    def __init__(
        self,
        model_path: str = "models/yolo11m.pt",
        device: str = "cpu",           # "cpu" | "cuda:0" | "0"
        conf_threshold: float = 0.45,
        iou_threshold: float = 0.5,
        imgsz: int = 640,
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.device = device
        self.model = None

        if YOLO is None:
            logger.warning("未检测到 ultralytics 库，检测器将以仿真模式运行")
            return

        try:
            logger.info(f"正在加载检测模型: {model_path} @ {device}")
            self.model = YOLO(model_path)
            self.model.to(device)
            logger.info("检测模型加载完成 ✅")
        except Exception as e:
            logger.warning(f"检测模型加载失败（{e}），以仿真模式运行")
            self.model = None

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        对单帧图像进行人体检测
        返回画面中所有 person 的检测结果
        """
        if self.model is None:
            return []

        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            imgsz=self.imgsz,
            classes=[0],           # 只检测 person 类别
            verbose=False,
        )

        detections: List[Detection] = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append(Detection(bbox=[x1, y1, x2, y2], confidence=conf))

        return detections
