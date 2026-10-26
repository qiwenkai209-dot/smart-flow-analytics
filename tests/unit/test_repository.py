"""
单元测试：FlowRepository 数据访问层
使用 Mock 异步数据库会话验证查询逻辑与聚合结果
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from backend.db.repository import FlowRepository


@pytest.mark.asyncio
async def test_repository_get_summary():
    """验证 get_summary 聚合逻辑"""
    mock_session = AsyncMock()
    mock_session.scalar.side_effect = [150, 120]  # total_in, total_out

    # Mock gender & age queries
    mock_gender_res = MagicMock()
    mock_gender_res.all.return_value = [("male", 80), ("female", 70)]

    mock_age_res = MagicMock()
    mock_age_res.all.return_value = [("child", 20), ("young", 60), ("adult", 50), ("elder", 20)]

    mock_session.execute.side_effect = [mock_gender_res, mock_age_res]

    with patch("backend.db.repository.AsyncSessionLocal") as mock_session_ctx:
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        res = await FlowRepository.get_summary(camera_id="cam_001")
        assert res["total_in"] == 150
        assert res["total_out"] == 120
        assert res["current_in_venue"] == 30
        assert res["gender"]["male"] == 80
        assert res["gender"]["female"] == 70
        assert res["age_group"]["young"] == 60


@pytest.mark.asyncio
async def test_repository_get_dwell_stats():
    """验证 get_dwell_stats 展台驻留聚合"""
    mock_session = AsyncMock()
    mock_row = MagicMock()
    mock_row.roi_name = "展台A"
    mock_row.visits = 45
    mock_row.avg_dwell_seconds = 23.5
    mock_row.male = 25
    mock_row.female = 20

    mock_res = MagicMock()
    mock_res.all.return_value = [mock_row]
    mock_session.execute.return_value = mock_res

    with patch("backend.db.repository.AsyncSessionLocal") as mock_session_ctx:
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        res = await FlowRepository.get_dwell_stats(camera_id="cam_001")
        assert "zones" in res
        assert len(res["zones"]) == 1
        assert res["zones"][0]["name"] == "展台A"
        assert res["zones"][0]["avg_dwell_seconds"] == 23.5


@pytest.mark.asyncio
async def test_repository_get_dwell_detail():
    """验证 get_dwell_detail 驻留明细查询"""
    mock_session = AsyncMock()
    mock_record = MagicMock()
    mock_record.global_id = "G-001"
    mock_record.camera_id = "cam_001"
    mock_record.roi_name = "展台A"
    mock_record.event_time = datetime(2026, 10, 26, 10, 0, 0, tzinfo=timezone.utc)
    mock_record.dwell_seconds = 18.5
    mock_record.gender = "male"
    mock_record.age_group = "young"

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_record]
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_res

    with patch("backend.db.repository.AsyncSessionLocal") as mock_session_ctx:
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        records = await FlowRepository.get_dwell_detail()
        assert len(records) == 1
        assert records[0]["global_id"] == "G-001"
        assert records[0]["roi_name"] == "展台A"
        assert records[0]["dwell_seconds"] == 18.5


@pytest.mark.asyncio
async def test_repository_get_realtime_snapshot():
    """验证 get_realtime_snapshot 实时看板快照"""
    mock_session = AsyncMock()
    mock_session.scalar.side_effect = [200, 160]  # total_in, total_out

    mock_gender_res = MagicMock()
    mock_gender_res.all.return_value = [("male", 110), ("female", 90)]

    mock_age_res = MagicMock()
    mock_age_res.all.return_value = [("young", 120), ("adult", 80)]

    mock_zone_row = MagicMock()
    mock_zone_row.roi_name = "展台B"
    mock_zone_row.avg_dwell = 15.0
    mock_zone_row.visits = 50

    mock_zone_res = MagicMock()
    mock_zone_res.all.return_value = [mock_zone_row]

    mock_session.execute.side_effect = [mock_gender_res, mock_age_res, mock_zone_res]

    with patch("backend.db.repository.AsyncSessionLocal") as mock_session_ctx:
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        snap = await FlowRepository.get_realtime_snapshot()
        assert snap["current_in_venue"] == 40
        assert snap["total_in_today"] == 200
        assert snap["gender"]["male"] == 110
        assert len(snap["zone_dwell"]) == 1
        assert snap["zone_dwell"][0]["name"] == "展台B"
