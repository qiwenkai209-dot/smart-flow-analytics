"""
摄像头管理 API
- 动态增删改查摄像头（无需重启服务）
- 私有协议参数（海康/大华/宇视直接输入 IP、用户名、密码自动生成 RTSP）
- 业务分类功能勾选（进出客流、展台驻留、年龄性别识别）
- 摄像头实时画面抓取与添加前即时预览测试
- 展台区域（ROI）与摄像头的自定义新增、编辑与绑定
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from core.stream.rtsp_reader import CameraConfig, test_stream_connection, build_brand_rtsp_url

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局摄像头管理器
_camera_manager = None


def get_manager():
    from core.stream.camera_manager import CameraManager
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = CameraManager()
    return _camera_manager


# ─── 数据结构 ─────────────────────────────────────────────────────────

class CameraAddOrUpdateRequest(BaseModel):
    id: str = Field(..., description="摄像头唯一标识")
    name: str = Field(..., description="摄像头名称")
    brand: str = Field("generic", description="品牌: generic | hikvision | dahua | uniview")
    rtsp_url: Optional[str] = Field("", description="完整 RTSP 地址，若填了 IP 则可留空自动生成")

    # 私有协议/设备参数
    ip: Optional[str] = Field("", description="摄像头 IP 地址")
    port: Optional[int] = Field(554, description="RTSP 端口")
    username: Optional[str] = Field("admin", description="设备用户名")
    password: Optional[str] = Field("", description="设备密码")
    channel: Optional[int] = Field(1, description="通道号")
    subtype: Optional[int] = Field(0, description="码流类型: 0=主码流, 1=子码流")

    fps_limit: int = Field(10, description="抽帧率")
    features: List[str] = Field(
        default=["in_out", "dwell", "attribute"],
        description="勾选分析功能: in_out(进出), dwell(驻留), attribute(年龄性别)"
    )
    rois: Optional[List[Dict[str, Any]]] = Field(default=[], description="关联的展台多边形区域")


class PreviewTestRequest(BaseModel):
    brand: str = "generic"
    rtsp_url: Optional[str] = ""
    ip: Optional[str] = ""
    port: Optional[int] = 554
    username: Optional[str] = "admin"
    password: Optional[str] = ""
    channel: Optional[int] = 1
    subtype: Optional[int] = 0


class RoiManageRequest(BaseModel):
    name: str = Field(..., description="展台/区域名称")
    camera_id: str = Field(..., description="关联的摄像头ID")
    polygon: List[List[float]] = Field(..., description="多边形顶点坐标 [[x1,y1], [x2,y2], ...]")
    min_dwell_seconds: float = Field(5.0, description="最小有效驻留时长(秒)")


# ─── 摄像头 API ───────────────────────────────────────────────────────

@router.get("/", summary="获取所有摄像头列表与状态")
async def list_cameras():
    return get_manager().list_cameras()


@router.post("/", summary="新增摄像头（支持私有协议合成与功能勾选）")
async def add_camera(req: CameraAddOrUpdateRequest):
    # 若未传完整 rtsp_url 则自动根据品牌和设备参数生成
    rtsp_url = req.rtsp_url.strip() if req.rtsp_url else ""
    if not rtsp_url and req.ip:
        rtsp_url = build_brand_rtsp_url(
            brand=req.brand,
            ip=req.ip,
            port=req.port or 554,
            username=req.username or "admin",
            password=req.password or "",
            channel=req.channel or 1,
            subtype=req.subtype or 0,
        )

    if not rtsp_url:
        raise HTTPException(status_code=400, detail="必须提供完整的 RTSP 地址或提供设备 IP 进行自动合成")

    config = CameraConfig(
        id=req.id,
        name=req.name,
        rtsp_url=rtsp_url,
        brand=req.brand,
        fps_limit=req.fps_limit,
        features=req.features or ["in_out", "dwell", "attribute"],
        ip=req.ip or "",
        port=req.port or 554,
        username=req.username or "admin",
        password=req.password or "",
        channel=req.channel or 1,
        subtype=req.subtype or 0,
        rois=req.rois or [],
    )
    success = get_manager().add_camera(config)
    if not success:
        raise HTTPException(status_code=409, detail=f"摄像头 [{req.id}] 已存在")
    return {"message": f"摄像头 [{req.id}] 已添加", "total": get_manager().count, "rtsp_url": rtsp_url}


@router.put("/{camera_id}", summary="修改摄像头配置与关联展台")
async def update_camera(camera_id: str, req: CameraAddOrUpdateRequest):
    rtsp_url = req.rtsp_url.strip() if req.rtsp_url else ""
    if not rtsp_url and req.ip:
        rtsp_url = build_brand_rtsp_url(
            brand=req.brand,
            ip=req.ip,
            port=req.port or 554,
            username=req.username or "admin",
            password=req.password or "",
            channel=req.channel or 1,
            subtype=req.subtype or 0,
        )

    config = CameraConfig(
        id=camera_id,
        name=req.name,
        rtsp_url=rtsp_url,
        brand=req.brand,
        fps_limit=req.fps_limit,
        features=req.features or ["in_out", "dwell", "attribute"],
        ip=req.ip or "",
        port=req.port or 554,
        username=req.username or "admin",
        password=req.password or "",
        channel=req.channel or 1,
        subtype=req.subtype or 0,
        rois=req.rois or [],
    )
    success = get_manager().update_camera(config)
    if not success:
        raise HTTPException(status_code=404, detail=f"摄像头 [{camera_id}] 不存在")
    return {"message": f"摄像头 [{camera_id}] 已更新", "total": get_manager().count}


@router.delete("/{camera_id}", summary="移除指定摄像头")
async def remove_camera(camera_id: str):
    success = get_manager().remove_camera(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"摄像头 [{camera_id}] 不存在")
    return {"message": f"摄像头 [{camera_id}] 已移除", "total": get_manager().count}


@router.get("/{camera_id}/status", summary="获取单路摄像头状态")
async def camera_status(camera_id: str):
    reader = get_manager().get_reader(camera_id)
    if not reader:
        raise HTTPException(status_code=404, detail=f"摄像头 [{camera_id}] 不存在")
    return reader.status


# ─── 预览与快照 API ───────────────────────────────────────────────────

@router.post("/preview-test", summary="新增前测试连接与获取即时预览画面")
async def preview_test(req: PreviewTestRequest):
    """根据参数自动拼装 RTSP 并测试抓取第 1 帧画面供弹窗预览"""
    rtsp_url = (req.rtsp_url or "").strip()
    if not rtsp_url and req.ip:
        rtsp_url = build_brand_rtsp_url(
            brand=req.brand,
            ip=req.ip,
            port=req.port or 554,
            username=req.username or "admin",
            password=req.password or "",
            channel=req.channel or 1,
            subtype=req.subtype or 0,
        )

    if not rtsp_url:
        return {
            "success": False,
            "error": "请输入摄像头 IP 地址或完整的 RTSP 地址",
            "preview_base64": None,
            "resolution": "未知",
            "rtsp_url": "",
        }

    res = test_stream_connection(rtsp_url, timeout_sec=3.5)
    res["rtsp_url"] = rtsp_url
    return res


@router.get("/{camera_id}/snapshot", summary="获取摄像头当前实时快照画面")
async def get_camera_snapshot(camera_id: str):
    reader = get_manager().get_reader(camera_id)
    if not reader:
        raise HTTPException(status_code=404, detail=f"摄像头 [{camera_id}] 不存在")

    jpeg_bytes = reader.get_snapshot_jpeg()
    if not jpeg_bytes:
        raise HTTPException(status_code=500, detail="生成快照失败")

    return Response(content=jpeg_bytes, media_type="image/jpeg")


# ─── 展台与区域自定义管理 API ──────────────────────────────────────────

@router.get("/rois/all", summary="获取所有展台区域及关联摄像头")
async def list_all_rois():
    return get_manager().list_rois()


@router.post("/rois", summary="自定义新增或更新展台关联摄像头")
async def save_roi(req: RoiManageRequest):
    success = get_manager().add_or_update_roi(
        name=req.name,
        camera_id=req.camera_id,
        polygon=req.polygon,
        min_dwell_seconds=req.min_dwell_seconds,
    )
    return {"message": f"展台 [{req.name}] 已保存并关联到摄像头 [{req.camera_id}]", "success": success}


@router.delete("/rois/{roi_name}", summary="删除指定展台")
async def delete_roi(roi_name: str):
    success = get_manager().delete_roi(roi_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"展台 [{roi_name}] 不存在")
    return {"message": f"展台 [{roi_name}] 已删除"}
