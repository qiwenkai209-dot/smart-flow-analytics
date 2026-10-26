"""
单元测试：PipelineOrchestrator 多路管线协调器
"""
import pytest
from core.orchestrator import PipelineOrchestrator
from core.stream.rtsp_reader import CameraConfig
from core.roi.roi_manager import ROIConfig


def test_orchestrator_add_and_remove_camera():
    """测试多路摄像头动态增删与统计查询"""
    roi_configs = [
        ROIConfig(name="入口展台", polygon=[[10, 10], [50, 10], [50, 50], [10, 50]])
    ]
    orchestrator = PipelineOrchestrator(roi_configs=roi_configs, device="cpu")

    cam1 = CameraConfig(id="cam_001", name="大门", rtsp_url="rtsp://dummy/1", fps_limit=5)
    cam2 = CameraConfig(id="cam_002", name="展厅", rtsp_url="rtsp://dummy/2", fps_limit=5)

    assert orchestrator.add_camera(cam1) is True
    assert orchestrator.count == 1

    # 重复添加同一摄像头应失败
    assert orchestrator.add_camera(cam1) is False

    assert orchestrator.add_camera(cam2) is True
    assert orchestrator.count == 2

    # 获取全部管线状态
    stats = orchestrator.get_all_stats()
    assert len(stats) == 2
    cam_ids = [s["camera_id"] for s in stats]
    assert "cam_001" in cam_ids
    assert "cam_002" in cam_ids

    # 移除摄像头
    assert orchestrator.remove_camera("cam_001") is True
    assert orchestrator.count == 1
    assert orchestrator.remove_camera("cam_non_exist") is False

    # 停止所有管线
    orchestrator.stop_all()
    assert orchestrator.count == 0
