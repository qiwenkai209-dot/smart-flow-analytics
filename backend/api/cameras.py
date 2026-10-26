"""
摄像头管理 API
- 动态增减摄像头（无需重启服务）
- 查询所有摄像头状态
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class CameraAddRequest(BaseModel):
    id: str
    name: str
    rtsp_url: str
    brand: str = "generic"
    fps_limit: int = 10
    rois: Optional[List[dict]] = []


class CameraStatusResponse(BaseModel):
    id: str
    name: str
    connected: bool
    fps_actual: float
    fps_limit: int


# 全局摄像头管理器（由 lifespan 注入，此处简化为模块级变量）
_camera_manager = None


def get_manager():
    from core.stream.camera_manager import CameraManager
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = CameraManager()
    return _camera_manager


@router.get("/", response_model=List[CameraStatusResponse], summary="获取所有摄像头状态")
async def list_cameras():
    return get_manager().list_cameras()


@router.post("/", summary="动态新增摄像头")
async def add_camera(req: CameraAddRequest):
    from core.stream.rtsp_reader import CameraConfig
    config = CameraConfig(
        id=req.id, name=req.name, rtsp_url=req.rtsp_url,
        brand=req.brand, fps_limit=req.fps_limit
    )
    success = get_manager().add_camera(config)
    if not success:
        raise HTTPException(status_code=409, detail=f"摄像头 [{req.id}] 已存在")
    return {"message": f"摄像头 [{req.id}] 已添加", "total": get_manager().count}


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
