import os
import sys
import logging
from dataclasses import dataclass
from typing import List
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger(__name__)


def get_embedded_model_path(filename: str) -> str:
    """获取内嵌模型的绝对路径（兼容开发环境与 PyInstaller 打包环境）"""
    if hasattr(sys, "_MEIPASS"):
        p = os.path.join(sys._MEIPASS, "embedded_models", filename)
        if os.path.exists(p):
            return p
    # 开发环境
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    p = os.path.join(root_dir, "embedded_models", filename)
    if os.path.exists(p):
        return p
    return filename


@dataclass
class Detection:
    bbox: List[float]        # [x1, y1, x2, y2]
    confidence: float
    class_id: int = 0        # 0 = person


class PersonDetector:
    """
    全场景人体检测器：
    1. 优先加载内嵌深度学习模型（embedded_models/person_detection_mediapipe_2023mar.onnx，免装大型依赖）
    2. 支持可选 YOLO11 / YOLOv8 模型加速部署
    3. OpenCV 原生 HOG+SVM 行人检测作为兜底守护
    """

    def __init__(
        self,
        model_path: str = "models/yolo11m.pt",
        device: str = "cpu",
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        imgsz: int = 640,
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.device = device
        self.yolo_model = None
        self.embedded_detector = None
        self.hog = None

        # 1. 尝试加载 YOLO (若安装了 ultralytics 且存在权重)
        if YOLO is not None:
            try:
                if os.path.exists(model_path):
                    logger.info(f"正在加载 YOLO 检测模型: {model_path} @ {device}")
                    self.yolo_model = YOLO(model_path)
                    self.yolo_model.to(device)
                    logger.info("YOLO 检测模型加载完成 ✅")
            except Exception as e:
                logger.warning(f"YOLO 模型加载异常: {e}")
                self.yolo_model = None

        # 2. 尝试加载内嵌深度学习 ONNX 模型（免安装任何外部框架，原生 C++ 推理）
        embedded_onnx = get_embedded_model_path("person_detection_mediapipe_2023mar.onnx")
        if os.path.exists(embedded_onnx):
            try:
                from embedded_models.mp_persondet import MPPersonDet
                self.embedded_detector = MPPersonDet(
                    modelPath=embedded_onnx,
                    scoreThreshold=self.conf_threshold,
                    nmsThreshold=self.iou_threshold,
                )
                logger.info(f"✅ 内嵌深度学习人体检测模型已就绪: {embedded_onnx}")
            except Exception as e:
                logger.warning(f"内嵌 ONNX 深度模型加载失败（{e}），将降级到机器视觉检测")
                self.embedded_detector = None

        # 3. 初始化 OpenCV 自带 HOG 行人检测器兜底
        try:
            import cv2
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            logger.info("✅ OpenCV 原生 HOG+SVM 行人检测引擎已就绪")
        except Exception as e:
            logger.warning(f"初始化 HOG 失败: {e}")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        对单帧图像进行人体检测
        自动优先使用 YOLO11 或 内嵌深度学习模型；降级使用 OpenCV HOG
        """
        if frame is None or frame.size == 0:
            return []

        # 链路一：YOLO 深度学习检测
        if self.yolo_model is not None:
            try:
                results = self.yolo_model.predict(
                    frame,
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    imgsz=self.imgsz,
                    classes=[0],
                    verbose=False,
                )
                detections: List[Detection] = []
                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = float(box.conf[0])
                        detections.append(Detection(bbox=[x1, y1, x2, y2], confidence=conf))
                return detections
            except Exception as e:
                logger.debug(f"YOLO 推理异常，降级到内嵌模型: {e}")

        # 链路二：内嵌 ONNX 深度学习模型（原生毫秒级推理）
        if self.embedded_detector is not None:
            try:
                res = self.embedded_detector.infer(frame)
                if res is not None and len(res) > 0:
                    detections: List[Detection] = []
                    for row in res:
                        x1, y1, x2, y2 = float(row[0]), float(row[1]), float(row[2]), float(row[3])
                        conf = float(row[12])
                        detections.append(Detection(bbox=[x1, y1, x2, y2], confidence=round(conf, 2)))
                    return detections
            except Exception as e:
                logger.debug(f"内嵌 ONNX 深度模型推理异常: {e}")

        # 链路三：OpenCV 原生 HOG 机器视觉行人检测兜底
        if self.hog is not None:
            import cv2
            h, w = frame.shape[:2]
            scale = 640.0 / max(w, 1)
            resized = cv2.resize(frame, (640, int(h * scale))) if scale < 1.0 else frame

            boxes, weights = self.hog.detectMultiScale(
                resized,
                winStride=(8, 8),
                padding=(4, 4),
                scale=1.05
            )

            inv_scale = 1.0 / scale if scale < 1.0 else 1.0
            detections: List[Detection] = []
            for (bx, by, bw, bh), weight in zip(boxes, weights):
                conf = float(weight[0]) if hasattr(weight, '__iter__') else float(weight)
                x1 = float(bx * inv_scale)
                y1 = float(by * inv_scale)
                x2 = float((bx + bw) * inv_scale)
                y2 = float((by + bh) * inv_scale)
                detections.append(Detection(bbox=[x1, y1, x2, y2], confidence=round(conf, 2)))

            return detections

        return []
