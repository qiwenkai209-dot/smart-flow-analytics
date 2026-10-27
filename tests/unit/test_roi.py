"""
单元测试：ROI 多边形驻留逻辑
"""
import pytest
from core.roi.roi_manager import ROIConfig, ROIManager, DwellTracker


@pytest.fixture
def roi_manager():
    rois = [
        ROIConfig(
            name="展台A",
            polygon=[[100, 100], [400, 100], [400, 400], [100, 400]],
            min_dwell_seconds=2.0,
        )
    ]
    return ROIManager(rois)


@pytest.fixture
def dwell_tracker(roi_manager):
    return DwellTracker(roi_manager, debounce_frames=2)


def test_point_inside_roi(roi_manager):
    """点在多边形内部，应返回 True"""
    assert roi_manager.point_in_roi("展台A", [250, 250]) is True


def test_point_outside_roi(roi_manager):
    """点在多边形外部，应返回 False"""
    assert roi_manager.point_in_roi("展台A", [500, 500]) is False


def test_point_on_boundary(roi_manager):
    """点在边界上，应返回 True"""
    assert roi_manager.point_in_roi("展台A", [100, 250]) is True


def test_get_point_rois_multiple(roi_manager):
    """添加第二个 ROI 后，重叠区域的点应属于两个 ROI"""
    from core.roi.roi_manager import ROIConfig
    roi_manager.add_roi(ROIConfig(
        name="展台B",
        polygon=[[200, 200], [500, 200], [500, 500], [200, 500]],
    ))
    rois = roi_manager.get_point_rois([300, 300])
    assert "展台A" in rois
    assert "展台B" in rois


def test_dwell_enter_and_leave(dwell_tracker):
    """模拟人员进入、驻留、离开，应生成驻留记录"""
    gid = "G-TEST001"
    # 进入区域（防抖：需连续2帧）
    dwell_tracker.update(gid, "cam_001", [250, 250])
    dwell_tracker.update(gid, "cam_001", [250, 250])
    assert "展台A" in dwell_tracker._state.get(gid, {})

    # 等待超过 min_dwell_seconds
    dwell_tracker._state[gid]["展台A"]["enter_time"] -= 3.0

    # 离开区域
    dwell_tracker.update(gid, "cam_001", [600, 600])  # 离开多边形

    records = dwell_tracker.flush_records()
    assert len(records) == 1
    assert records[0].roi_name == "展台A"
    assert records[0].dwell_seconds >= 2.0


def test_dwell_too_short_filtered(dwell_tracker):
    """驻留时间不足 min_dwell_seconds，不应生成记录（过滤穿堂人员）"""
    gid = "G-TEST002"
    dwell_tracker.update(gid, "cam_001", [250, 250])
    dwell_tracker.update(gid, "cam_001", [250, 250])
    # 立刻离开（不等待 2 秒）
    dwell_tracker.update(gid, "cam_001", [600, 600])

    records = dwell_tracker.flush_records()
    assert len(records) == 0, "驻留时间过短，不应有记录"
