"""
客流统计查询 API
已对接真实数据库查询层（FlowRepository）
兼容数据库未连接时返回演示数据
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime
import logging

from ..db.repository import FlowRepository

router = APIRouter()
logger = logging.getLogger(__name__)


async def _safe_query(func, fallback):
    """安全查询：数据库不可用时降级返回演示数据"""
    try:
        return await func()
    except Exception as e:
        logger.warning(f"数据库查询失败（降级为演示数据）: {e}")
        return fallback


@router.get("/summary", summary="获取客流汇总统计")
async def get_summary(
    camera_id: Optional[str] = Query(None, description="指定摄像头ID，不传则汇总所有"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
):
    """
    返回指定时间段内的客流汇总：
    - 总进入人数、总离开人数、当前在场人数
    - 男女比例、年龄段分布
    """
    fallback = {
        "total_in": 128,
        "total_out": 115,
        "current_in_venue": 13,
        "gender": {"male": 72, "female": 56},
        "age_group": {"child": 18, "young": 55, "adult": 42, "elder": 13},
        "camera_id": camera_id or "all",
    }
    return await _safe_query(
        lambda: FlowRepository.get_summary(camera_id, start_time, end_time),
        fallback,
    )


@router.get("/dwell", summary="获取展台驻留时长统计")
async def get_dwell_stats(
    camera_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    """
    按展台/ROI 区域聚合驻留时长统计：
    - 平均驻留时长、到访人次、男女/年龄构成
    """
    fallback = {
        "zones": [
            {"name": "展台A", "visits": 45, "avg_dwell_seconds": 38.5, "male": 25, "female": 20},
            {"name": "展台B", "visits": 32, "avg_dwell_seconds": 22.1, "male": 18, "female": 14},
            {"name": "展台C", "visits": 18, "avg_dwell_seconds": 65.3, "male": 10, "female": 8},
        ]
    }
    return await _safe_query(
        lambda: FlowRepository.get_dwell_stats(camera_id, start_time, end_time),
        fallback,
    )


@router.get("/timeseries", summary="获取客流时间序列数据（折线图）")
async def get_timeseries(
    camera_id: Optional[str] = Query(None),
    interval: str = Query("1h", description="时间粒度：5m / 15m / 1h / 1d"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    """返回每个时间粒度的进出人数，用于大屏折线图"""
    fallback = {
        "interval": interval,
        "series": [
            {"time": "09:00", "in": 12, "out": 5},
            {"time": "10:00", "in": 28, "out": 18},
            {"time": "11:00", "in": 35, "out": 29},
            {"time": "12:00", "in": 22, "out": 20},
            {"time": "13:00", "in": 15, "out": 12},
            {"time": "14:00", "in": 42, "out": 35},
            {"time": "15:00", "in": 38, "out": 30},
            {"time": "16:00", "in": 25, "out": 22},
            {"time": "17:00", "in": 18, "out": 16},
        ],
    }
    return await _safe_query(
        lambda: FlowRepository.get_timeseries(camera_id, interval, start_time, end_time),
        fallback,
    )
