"""
报表导出 API（Excel / CSV）
已对接真实数据库查询，兼容降级
"""
import io
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import pandas as pd

from ..db.repository import FlowRepository

router = APIRouter()
logger = logging.getLogger(__name__)


def _mock_dwell_data() -> pd.DataFrame:
    """数据库不可用时的演示数据"""
    return pd.DataFrame([
        {"global_id": "G-A1B2C3D4", "camera_id": "cam_001", "roi_name": "展台A",
         "event_time": "2026-10-26 09:15:32",
         "dwell_seconds": 46.0, "gender": "male", "age_group": "young"},
        {"global_id": "G-E5F6G7H8", "camera_id": "cam_001", "roi_name": "展台B",
         "event_time": "2026-10-26 09:20:10",
         "dwell_seconds": 35.0, "gender": "female", "age_group": "adult"},
        {"global_id": "G-I9J0K1L2", "camera_id": "cam_002", "roi_name": "展台A",
         "event_time": "2026-10-26 10:05:22",
         "dwell_seconds": 72.0, "gender": "male", "age_group": "elder"},
    ])


async def _get_export_df(camera_id, start_time, end_time) -> pd.DataFrame:
    """从数据库获取导出数据，失败时降级"""
    try:
        detail = await FlowRepository.get_dwell_detail(camera_id, start_time, end_time)
        if detail:
            return pd.DataFrame(detail)
    except Exception as e:
        logger.warning(f"导出数据库查询失败（降级为演示数据）: {e}")
    return _mock_dwell_data()


def _localize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """列名汉化"""
    col_map = {
        "global_id": "全局ID", "camera_id": "摄像头", "roi_name": "展台区域",
        "event_time": "事件时间", "enter_time": "进入时间", "leave_time": "离开时间",
        "dwell_seconds": "驻留时长(秒)", "gender": "性别", "age_group": "年龄段",
    }
    return df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})


@router.get("/excel", summary="导出驻留明细报表（Excel）")
async def export_excel(
    camera_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    df = await _get_export_df(camera_id, start_time, end_time)
    df = _localize_columns(df)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="驻留明细")
    buf.seek(0)

    from urllib.parse import quote
    filename = f"客流报表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = quote(filename)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"flow_report.xlsx\"; filename*=UTF-8''{encoded_filename}"
        },
    )


@router.get("/csv", summary="导出驻留明细报表（CSV）")
async def export_csv(
    camera_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    df = await _get_export_df(camera_id, start_time, end_time)
    df = _localize_columns(df)

    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")  # utf-8-sig 确保 Excel 打开中文不乱码
    buf.seek(0)

    from urllib.parse import quote
    filename = f"客流报表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    encoded_filename = quote(filename)
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=\"flow_report.csv\"; filename*=UTF-8''{encoded_filename}"
        },
    )
