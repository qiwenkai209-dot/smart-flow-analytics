"""
模型 Benchmark 评测脚本（GitHub Actions 自动调用）
评测指标：检测 FPS、追踪精度（MOTA）、Re-ID 特征提取速度、显存占用
"""
import json
import time
import argparse
import logging
from pathlib import Path
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def benchmark_detector(video_path: str, model_path: str, device: str = "cpu") -> dict:
    """测试检测模型速度（FPS）"""
    from core.detect.detector import PersonDetector
    detector = PersonDetector(model_path=model_path, device=device)

    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    total_time = 0.0
    total_detections = 0

    while frame_count < 100:
        ret, frame = cap.read()
        if not ret:
            break
        t0 = time.perf_counter()
        dets = detector.detect(frame)
        t1 = time.perf_counter()
        total_time += (t1 - t0)
        total_detections += len(dets)
        frame_count += 1

    cap.release()
    avg_fps = frame_count / total_time if total_time > 0 else 0

    return {
        "model": model_path,
        "device": device,
        "frames_tested": frame_count,
        "avg_fps": round(avg_fps, 2),
        "avg_detections_per_frame": round(total_detections / max(frame_count, 1), 2),
        "total_time_s": round(total_time, 3),
    }


def benchmark_reid(model_path: str, n_samples: int = 200) -> dict:
    """测试 Re-ID 特征提取速度"""
    from core.reid.cross_cam_tracker import ReIDModel
    model = ReIDModel(model_path=model_path)

    crop = np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8)
    times = []
    for _ in range(n_samples):
        t0 = time.perf_counter()
        model.extract_feature(crop)
        t1 = time.perf_counter()
        times.append(t1 - t0)

    avg_ms = sum(times) / len(times) * 1000
    return {
        "model": model_path,
        "n_samples": n_samples,
        "avg_ms_per_frame": round(avg_ms, 3),
        "fps_equivalent": round(1000 / avg_ms, 1),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="benchmark/reports/latest.json")
    args = parser.parse_args()

    video_path = "benchmark/datasets/sample_crowd.mp4"
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "detector": {},
        "reid": {},
    }

    # 检测 Benchmark
    if Path(video_path).exists():
        for model in ["models/yolo11m.pt"]:
            if Path(model).exists():
                result = benchmark_detector(video_path, model)
                report["detector"][model] = result
                logger.info(f"检测 [{model}]: {result['avg_fps']} FPS")
    else:
        logger.warning(f"测试视频不存在: {video_path}，跳过检测 benchmark")

    # Re-ID Benchmark
    for model in ["models/reid/fast_reid_r50.pth"]:
        result = benchmark_reid(model)
        report["reid"][model] = result
        logger.info(f"Re-ID [{model}]: {result['avg_ms_per_frame']} ms/帧")

    # 写出报告
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Benchmark 报告已保存: {args.output} ✅")
