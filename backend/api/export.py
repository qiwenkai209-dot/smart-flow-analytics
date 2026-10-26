"""
报表导出 API（Excel / CSV）
"""
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import pandas as pd

router = APIRouter()


def _mock_dwell_data() -> pd.DataFrame:
    """占位数据，实际从数据库查询"""
    return pd.DataFrame([
        {"global_id": "G-A1B2C3D4", "camera_id": "cam_001", "roi_name": "展台A",
         "enter_time": "2026-10-26 09:15:32", "leave_time": "2026-10-26 09:16:18",
         "dwell_seconds": 46.0, "gender": "male", "age_group": "young"},
        {"global_id": "G-E5F6G7H8", "camera_id": "cam_001", "roi_name": "展台B",
         "enter_time": "2026-10-26 09:20:10", "leave_time": "2026-10-26 09:20:45",
         "dwell_seconds": 35.0, "gender": "female", "age_group": "adult"},
    ])


@router.get("/excel", summary="导出驻留明细报表（Excel）")
async def export_excel(
    camera_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    df = _mock_dwell_data()

    # 列名汉化
    df.rename(columns={
        "global_id": "全局ID", "camera_id": "摄像头", "roi_name": "展台区域",
        "enter_time": "进入时间", "leave_time": "离开时间",
        "dwell_seconds": "驻留时长(秒)", "gender": "性别", "age_group": "年龄段",
    }, inplace=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="驻留明细")
    buf.seek(0)

    filename = f"客流报表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/csv", summary="导出驻留明细报表（CSV）")
async def export_csv(
    camera_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    df = _mock_dwell_data()
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")  # utf-8-sig 确保 Excel 打开中文不乱码
    buf.seek(0)

    filename = f"客流报表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
