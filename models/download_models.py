"""
一键下载所有开源预训练模型
"""
import os
import urllib.request
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.dirname(__file__)

MODELS = {
    "yolo11m.pt": {
        "url": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m.pt",
        "desc": "YOLO11m 人体检测模型",
        "benchmark_only": False,
    },
    "reid/fast_reid_r50.pth": {
        "url": "https://github.com/facebookresearch/fastreid/releases/download/v1.4.0/market_bot_R50.pth",
        "desc": "FastReID ResNet50 行人重识别模型",
        "benchmark_only": False,
    },
    # PP-Human 属性识别模型（PaddlePaddle ONNX 格式，需手动转换或从官方下载）
    "attribute/pphumans_attribute.onnx": {
        "url": "https://paddledet.bj.bcebos.com/models/pipeline/PPLCNet_x1_0_pedestrian_attribute_945_infer.tar",
        "desc": "PP-Human 全身属性识别模型 (ONNX)",
        "benchmark_only": False,
    },
}

BENCHMARK_VIDEOS = {
    "benchmark/datasets/sample_crowd.mp4": {
        "url": "https://github.com/ultralytics/assets/releases/download/v0.0.0/crowd.mp4",
        "desc": "人群测试视频（benchmark 用）",
    }
}


def download(url: str, dest: str, desc: str):
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    if os.path.exists(dest):
        logger.info(f"[跳过] {desc} 已存在: {dest}")
        return
    logger.info(f"[下载] {desc} -> {dest}")
    urllib.request.urlretrieve(url, dest)
    logger.info(f"[完成] {desc} ✅")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载预训练模型")
    parser.add_argument("--benchmark-only", action="store_true", help="只下载 benchmark 所需资源")
    args = parser.parse_args()

    if not args.benchmark_only:
        for filename, info in MODELS.items():
            dest = os.path.join(MODELS_DIR, filename)
            download(info["url"], dest, info["desc"])

    # 下载 benchmark 测试视频
    for filename, info in BENCHMARK_VIDEOS.items():
        download(info["url"], filename, info["desc"])

    logger.info("所有模型下载完成 🎉")
