"""
单元测试：PP-Human 属性识别与单次触发调度器
"""
import numpy as np
from core.attribute.attribute_model import AttributeModel, AttributeScheduler


def test_attribute_model_too_small_crop_filtered():
    """裁剪图高度过小（低于 min_body_height）应跳过识别"""
    model = AttributeModel(min_body_height=60)
    small_crop = np.zeros((30, 20, 3), dtype=np.uint8)
    res = model.predict(small_crop)
    assert res is None


def test_attribute_model_valid_crop():
    """正常人体裁剪图应能预测或降级返回属性"""
    model = AttributeModel(min_body_height=60)
    crop = np.zeros((120, 50, 3), dtype=np.uint8)
    res = model.predict(crop)
    assert res is not None
    assert res.gender in ["male", "female"]
    assert res.age_group in ["child", "young", "adult", "elder"]
    assert 0 <= res.gender_conf <= 1.0


def test_attribute_scheduler_trigger_once():
    """测试 AttributeScheduler 稳定帧触发：每个 Global ID 仅触发一次"""
    model = AttributeModel(min_body_height=50)
    scheduler = AttributeScheduler(model, stable_frames=3)

    frame = np.zeros((300, 300, 3), dtype=np.uint8)
    bbox = [10.0, 10.0, 60.0, 110.0]  # 高度 100 > 50

    # 第 1, 2 帧：未达到稳定帧阈值
    r1 = scheduler.submit(global_id="G-001", frame=frame, bbox=bbox)
    r2 = scheduler.submit(global_id="G-001", frame=frame, bbox=bbox)
    assert r1 is None
    assert r2 is None

    # 第 3 帧：达到阈值，触发识别并返回结果
    r3 = scheduler.submit(global_id="G-001", frame=frame, bbox=bbox)
    assert r3 is not None
    assert r3.gender in ["male", "female"]

    # 第 4 帧：已经识别过，直接返回已有缓存结果
    r4 = scheduler.submit(global_id="G-001", frame=frame, bbox=bbox)
    assert r4 is not None
    assert r4 == r3
