"""
内嵌模型包初始化
提供免PyTorch、免外置依赖的内嵌深度学习模型（基于OpenCV DNN原生推理）
"""
import os
import sys

EMBEDDED_MODELS_DIR = os.path.dirname(os.path.abspath(__file__))

# 确保本目录在系统路径中
if EMBEDDED_MODELS_DIR not in sys.path:
    sys.path.insert(0, EMBEDDED_MODELS_DIR)

DETECTOR_ONNX_PATH = os.path.join(EMBEDDED_MODELS_DIR, "person_detection_mediapipe_2023mar.onnx")
GENDERAGE_ONNX_PATH = os.path.join(EMBEDDED_MODELS_DIR, "genderage.onnx")
