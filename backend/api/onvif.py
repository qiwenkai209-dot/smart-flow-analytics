"""
ONVIF 设备发现与管理 API
- 扫描局域网内 NVR / IP Camera
- 获取设备通道列表和 RTSP 流地址
- 一键添加已发现的摄像头到系统
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class OnvifScanRequest(BaseModel):
    timeout: float = 5.0


class OnvifConnectRequest(BaseModel):
    address: str
    username: str = "admin"
    password: str = ""


class OnvifAddChannelRequest(BaseModel):
    """从 ONVIF 设备一键添加通道为摄像头"""
    device_address: str
    username: str = "admin"
    password: str = ""
    profile_token: str
    camera_id: str
    camera_name: str
    fps_limit: int = 10


class DeviceResponse(BaseModel):
    address: str
    name: str = ""
    manufacturer: str = ""
    model: str = ""
    hardware_id: str = ""


class ChannelResponse(BaseModel):
    token: str
    channel_name: str = ""
    width: int = 0
    height: int = 0
    encoding: str = ""
    rtsp_url: str = ""


@router.post("/scan", response_model=List[DeviceResponse], summary="扫描局域网 ONVIF 设备")
async def scan_devices(req: OnvifScanRequest):
    """
    使用 WS-Discovery 协议扫描局域网内的 NVR / IP Camera
    超时后返回所有已发现的设备
    """
    try:
        from core.stream.onvif_discovery import OnvifDiscovery
        devices = await OnvifDiscovery.discover(timeout=req.timeout)
        return [
            DeviceResponse(
                address=d.address,
                name=d.name,
                manufacturer=d.manufacturer,
                model=d.model,
                hardware_id=d.hardware_id,
            )
            for d in devices
        ]
    except Exception as e:
        logger.error(f"ONVIF 扫描异常: {e}")
        raise HTTPException(status_code=500, detail=f"设备扫描失败: {str(e)}")


@router.post("/channels", response_model=List[ChannelResponse], summary="获取 ONVIF 设备通道列表")
async def get_device_channels(req: OnvifConnectRequest):
    """
    连接到指定 ONVIF 设备，获取所有视频通道信息及 RTSP 流地址
    """
    try:
        from core.stream.onvif_discovery import OnvifClient
        client = OnvifClient(req.address, req.username, req.password)
        connected = await client.connect()
        if not connected:
            raise HTTPException(status_code=400, detail="ONVIF 设备连接失败，请检查地址和认证信息")

        channels = await client.get_channels()
        return [
            ChannelResponse(
                token=ch.token,
                channel_name=ch.channel_name,
                width=ch.width,
                height=ch.height,
                encoding=ch.encoding,
                rtsp_url=ch.rtsp_url,
            )
            for ch in channels
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取通道失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取通道失败: {str(e)}")


@router.post("/device-info", summary="获取 ONVIF 设备详细信息")
async def get_device_info(req: OnvifConnectRequest):
    """获取设备制造商、型号、固件版本等信息"""
    try:
        from core.stream.onvif_discovery import OnvifClient
        client = OnvifClient(req.address, req.username, req.password)
        connected = await client.connect()
        if not connected:
            raise HTTPException(status_code=400, detail="设备连接失败")

        return await client.get_device_info()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-channel", summary="将 ONVIF 通道添加为系统摄像头")
async def add_onvif_channel(req: OnvifAddChannelRequest):
    """
    一键将 ONVIF 设备中的某个通道添加到系统中
    自动获取该通道的 RTSP 地址并注册为摄像头
    """
    try:
        from core.stream.onvif_discovery import OnvifClient
        client = OnvifClient(req.device_address, req.username, req.password)
        connected = await client.connect()
        if not connected:
            raise HTTPException(status_code=400, detail="设备连接失败")

        channels = await client.get_channels()
        target = next((ch for ch in channels if ch.token == req.profile_token), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"通道 [{req.profile_token}] 不存在")

        if not target.rtsp_url:
            raise HTTPException(status_code=400, detail="该通道无法获取 RTSP 流地址")

        # 调用摄像头管理 API 注册
        from core.stream.rtsp_reader import CameraConfig
        from .cameras import get_manager

        config = CameraConfig(
            id=req.camera_id,
            name=req.camera_name,
            rtsp_url=target.rtsp_url,
            brand="generic",
            fps_limit=req.fps_limit,
        )
        success = get_manager().add_camera(config)
        if not success:
            raise HTTPException(status_code=409, detail=f"摄像头 [{req.camera_id}] 已存在")

        return {
            "message": f"摄像头 [{req.camera_name}] 已从 ONVIF 通道添加",
            "camera_id": req.camera_id,
            "rtsp_url": target.rtsp_url,
            "resolution": f"{target.width}x{target.height}",
            "encoding": target.encoding,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加 ONVIF 通道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
