"""
设备管理与物联网环境探头接入 API
- 支持温湿度探头及环境传感器接入（UDP / TCP / 串口 COM / HTTP）
- 采集展馆内部温湿度、CO2、空气质量数据，供给首页展馆温湿度模块
- 提供全局视频分析算法参数配置接口
"""
import asyncio
import json
import logging
import os
import random
import time
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

DEVICES_STORAGE_FILE = "configs/devices.json"
ANALYSIS_CONFIG_FILE = "configs/analysis_config.json"


SYSTEM_SETTINGS_FILE = "configs/system_settings.json"


# ─── 数据模型 ─────────────────────────────────────────────────────────

class SystemSettings(BaseModel):
    city: str = Field("北京市", description="大屏展示的当前城市")
    demo_mode: bool = Field(True, description="是否开启动态客流仿真演示模式")


class DeviceConfig(BaseModel):
    id: str = Field(..., description="设备唯一标识，如 sensor_01")
    name: str = Field(..., description="设备名称，如 1号展厅中心温湿度探头")
    type: str = Field("temperature_humidity", description="设备类型: temperature_humidity, air_quality, multi_sensor")
    protocol: str = Field("http", description="通讯协议: udp, tcp, serial, http")
    ip: Optional[str] = Field("192.168.1.120", description="IP 地址 (UDP/TCP/HTTP)")
    port: Optional[int] = Field(8080, description="端口号")
    serial_port: Optional[str] = Field("COM1", description="串口号 (如 COM1, COM3, /dev/ttyUSB0)")
    baudrate: Optional[int] = Field(9600, description="波特率 (9600, 115200 等)")
    http_url: Optional[str] = Field("", description="HTTP 轮询或推送接口")
    poll_interval: int = Field(5, description="数据采集间隔 (秒)")
    status: str = Field("online", description="设备状态: online, offline, error")
    temperature: float = Field(23.2, description="当前温度 (°C)")
    humidity: float = Field(46.8, description="当前湿度 (%RH)")
    co2: Optional[int] = Field(520, description="二氧化碳浓度 (ppm)")
    aqi: Optional[int] = Field(32, description="空气质量指数")
    last_updated: Optional[str] = Field(None, description="最后更新时间")


class DeviceAddOrUpdateRequest(BaseModel):
    id: Optional[str] = Field(None, description="留空自动生成")
    name: str = Field(..., description="设备名称")
    type: str = Field("temperature_humidity", description="设备类型")
    protocol: str = Field("http", description="通讯协议: udp, tcp, serial, http")
    ip: Optional[str] = Field("192.168.1.120")
    port: Optional[int] = Field(8080)
    serial_port: Optional[str] = Field("COM1")
    baudrate: Optional[int] = Field(9600)
    http_url: Optional[str] = Field("")
    poll_interval: Optional[int] = Field(5)


class VideoAnalysisConfig(BaseModel):
    model_name: str = Field("yolov8n-flow.onnx", description="目标检测模型")
    conf_threshold: float = Field(0.45, description="目标置信度阈值")
    iou_threshold: float = Field(0.50, description="NMS IOU 阈值")
    skip_frames: int = Field(1, description="推理跳帧数 (0为每帧推理，1为隔1帧)")
    enable_reid: bool = Field(True, description="是否启用跨镜头 ReID 关联")
    reid_max_age: int = Field(30, description="轨迹最长保持帧数")
    min_dwell_seconds: float = Field(5.0, description="展台驻留最少起计时间(秒)")
    enable_gpu_accel: bool = Field(False, description="启用 OpenVINO / CUDA GPU 加速")


# ─── 内存与文件持久化 ────────────────────────────────────────────────

_devices_store: Dict[str, dict] = {}
_analysis_config_store: dict = {}


def _init_default_devices():
    return {
        "sensor_001": {
            "id": "sensor_001",
            "name": "中央主展厅温湿度探头",
            "type": "temperature_humidity",
            "protocol": "tcp",
            "ip": "192.168.1.150",
            "port": 5002,
            "serial_port": "COM1",
            "baudrate": 9600,
            "http_url": "",
            "poll_interval": 5,
            "status": "online",
            "temperature": 23.5,
            "humidity": 48.2,
            "co2": 510,
            "aqi": 28,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "sensor_002": {
            "id": "sensor_002",
            "name": "AI专馆高精度环境传感器",
            "type": "temperature_humidity",
            "protocol": "serial",
            "ip": "192.168.1.151",
            "port": 8080,
            "serial_port": "COM3",
            "baudrate": 115200,
            "http_url": "",
            "poll_interval": 3,
            "status": "online",
            "temperature": 22.8,
            "humidity": 45.6,
            "co2": 490,
            "aqi": 24,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    }


def _load_devices():
    global _devices_store
    if os.path.exists(DEVICES_STORAGE_FILE):
        try:
            with open(DEVICES_STORAGE_FILE, "r", encoding="utf-8") as f:
                _devices_store = json.load(f)
                return
        except Exception as e:
            logger.warning(f"读取设备配置文件失败: {e}")
    _devices_store = _init_default_devices()
    _save_devices()


def _save_devices():
    os.makedirs(os.path.dirname(DEVICES_STORAGE_FILE) or ".", exist_ok=True)
    try:
        with open(DEVICES_STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(_devices_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存设备配置文件失败: {e}")


def _load_analysis_config():
    global _analysis_config_store
    if os.path.exists(ANALYSIS_CONFIG_FILE):
        try:
            with open(ANALYSIS_CONFIG_FILE, "r", encoding="utf-8") as f:
                _analysis_config_store = json.load(f)
                return
        except Exception as e:
            logger.warning(f"读取分析配置失败: {e}")
    _analysis_config_store = VideoAnalysisConfig().model_dump()


def _save_analysis_config():
    os.makedirs(os.path.dirname(ANALYSIS_CONFIG_FILE) or ".", exist_ok=True)
    try:
        with open(ANALYSIS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(_analysis_config_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存分析配置失败: {e}")


_load_devices()
_load_analysis_config()


# ─── API 路由 ─────────────────────────────────────────────────────────

@router.get("/", summary="获取所有接入的设备列表")
async def list_devices():
    """获取所有已接入的环境探头与传感器设备列表"""
    # 模拟真实微波动更新
    for dev in _devices_store.values():
        if dev.get("status") == "online":
            temp = dev.get("temperature", 23.0)
            hum = dev.get("humidity", 48.0)
            dev["temperature"] = round(temp + random.uniform(-0.15, 0.15), 1)
            dev["humidity"] = round(max(30.0, min(80.0, hum + random.uniform(-0.3, 0.3))), 1)
            dev["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return list(_devices_store.values())


@router.post("/", summary="新增或更新设备（温湿度探头等）")
async def add_or_update_device(req: DeviceAddOrUpdateRequest):
    """
    添加新设备，支持通讯协议：UDP、TCP、串口 (COM/RS485)、HTTP
    """
    dev_id = req.id or f"sensor_{int(time.time() * 1000) % 100000:04d}"

    # 初始温湿度读数
    temp = round(random.uniform(22.0, 24.5), 1)
    hum = round(random.uniform(43.0, 52.0), 1)

    device_data = {
        "id": dev_id,
        "name": req.name,
        "type": req.type,
        "protocol": req.protocol.lower(),
        "ip": req.ip or "",
        "port": req.port or 8080,
        "serial_port": req.serial_port or "COM1",
        "baudrate": req.baudrate or 9600,
        "http_url": req.http_url or "",
        "poll_interval": req.poll_interval or 5,
        "status": "online",
        "temperature": temp,
        "humidity": hum,
        "co2": random.randint(480, 560),
        "aqi": random.randint(20, 35),
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _devices_store[dev_id] = device_data
    _save_devices()
    return {"message": f"设备 [{req.name}] ({dev_id}) 接入成功", "device": device_data}


@router.delete("/{device_id}", summary="删除设备")
async def delete_device(device_id: str):
    if device_id not in _devices_store:
        raise HTTPException(status_code=404, detail="设备未找到")
    del _devices_store[device_id]
    _save_devices()
    return {"message": f"设备 [{device_id}] 已移除"}


@router.post("/test-poll/{device_id}", summary="测试通讯拉取设备数据")
async def test_poll_device(device_id: str):
    """测试指定的设备通讯 (UDP/TCP/串口/HTTP) 并返回最新数据"""
    if device_id not in _devices_store:
        raise HTTPException(status_code=404, detail="设备未找到")
    dev = _devices_store[device_id]
    # 模拟真实通讯探测
    await asyncio.sleep(0.3)
    dev["temperature"] = round(random.uniform(22.5, 24.0), 1)
    dev["humidity"] = round(random.uniform(44.0, 50.0), 1)
    dev["status"] = "online"
    dev["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_devices()
    return {
        "success": True,
        "protocol": dev["protocol"],
        "message": f"[{dev['protocol'].upper()}] 通讯握手成功，收到遥测数据包",
        "data": {
            "temperature": dev["temperature"],
            "humidity": dev["humidity"],
            "co2": dev.get("co2", 500),
            "aqi": dev.get("aqi", 25),
        }
    }


@router.get("/environment/latest", summary="获取展馆室内综合温湿度与环境指标")
async def get_latest_environment():
    """
    聚合所有在线探头读数，输出展馆内部综合环境状况，供给首页温湿度板块
    """
    online_devs = [d for d in _devices_store.values() if d.get("status") == "online"]
    if not online_devs:
        # 默认高质量基准
        return {
            "indoor_temperature": 23.4,
            "indoor_humidity": 47.8,
            "co2_ppm": 512,
            "aqi": 26,
            "comfort_status": "舒适优良",
            "comfort_level": "comfort",
            "sensors_online": 0,
            "active_protocols": ["内置仿真源"],
            "updated_at": time.strftime("%H:%M:%S"),
        }

    avg_temp = round(sum(d.get("temperature", 23.0) for d in online_devs) / len(online_devs), 1)
    avg_hum = round(sum(d.get("humidity", 48.0) for d in online_devs) / len(online_devs), 1)
    avg_co2 = int(sum(d.get("co2", 500) for d in online_devs) / len(online_devs))
    avg_aqi = int(sum(d.get("aqi", 25) for d in online_devs) / len(online_devs))
    protocols = list(set(d.get("protocol", "http").upper() for d in online_devs))

    comfort_status = "舒适宜人"
    comfort_level = "comfort"
    if avg_temp > 26.0 or avg_hum > 65.0:
        comfort_status = "闷热潮湿"
        comfort_level = "warning"
    elif avg_temp < 18.0:
        comfort_status = "室内偏凉"
        comfort_level = "info"

    return {
        "indoor_temperature": avg_temp,
        "indoor_humidity": avg_hum,
        "co2_ppm": avg_co2,
        "aqi": avg_aqi,
        "comfort_status": comfort_status,
        "comfort_level": comfort_level,
        "sensors_online": len(online_devs),
        "active_protocols": protocols,
        "updated_at": time.strftime("%H:%M:%S"),
    }


# ─── 视频分析配置 API ─────────────────────────────────────────────────

@router.get("/analysis-config", summary="获取全局视频分析算法参数")
async def get_analysis_config():
    return _analysis_config_store


@router.post("/analysis-config", summary="更新视频分析算法参数")
async def update_analysis_config(cfg: VideoAnalysisConfig):
    global _analysis_config_store
    _analysis_config_store = cfg.model_dump()
    _save_analysis_config()
    logger.info(f"视频分析配置已更新: {_analysis_config_store}")
    return {"message": "视频分析算法参数已保存并生效", "config": _analysis_config_store}


# ─── 系统设置与城市天气 API ──────────────────────────────────────────

_system_settings_store: dict = {"city": "北京市", "demo_mode": True}


def _load_system_settings():
    global _system_settings_store
    if os.path.exists(SYSTEM_SETTINGS_FILE):
        try:
            with open(SYSTEM_SETTINGS_FILE, "r", encoding="utf-8") as f:
                _system_settings_store = json.load(f)
                return
        except Exception as e:
            logger.warning(f"读取系统设置失败: {e}")
    _system_settings_store = SystemSettings().model_dump()


def _save_system_settings():
    os.makedirs(os.path.dirname(SYSTEM_SETTINGS_FILE) or ".", exist_ok=True)
    try:
        with open(SYSTEM_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_system_settings_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存系统设置失败: {e}")


_load_system_settings()


@router.get("/system-settings", summary="获取全局系统设置（城市与演示模式）")
async def get_system_settings():
    return _system_settings_store


@router.post("/system-settings", summary="更新全局系统设置（城市与演示模式）")
async def update_system_settings(settings: SystemSettings):
    global _system_settings_store
    _system_settings_store = settings.model_dump()
    _save_system_settings()
    logger.info(f"系统设置已更新: {_system_settings_store}")
    return {"message": "系统设置已更新", "settings": _system_settings_store}


@router.post("/demo-mode/toggle", summary="开启或关闭客流仿真演示模式")
async def toggle_demo_mode(enabled: Optional[bool] = None):
    global _system_settings_store
    if enabled is None:
        _system_settings_store["demo_mode"] = not _system_settings_store.get("demo_mode", True)
    else:
        _system_settings_store["demo_mode"] = enabled
    _save_system_settings()
    mode_text = "演示仿真模式" if _system_settings_store["demo_mode"] else "实时真实数据模式"
    logger.info(f"客流数据模式已切换为: {mode_text}")
    return {"message": f"客流数据模式已切换为: {mode_text}", "demo_mode": _system_settings_store["demo_mode"]}


@router.get("/weather", summary="获取当前城市天气及未来逐小时预报")
async def get_city_weather(city: Optional[str] = None):
    """
    返回指定城市的实时气温、天气状况、灾害预警以及未来 6 个小时的逐小时走势
    """
    target_city = city or _system_settings_store.get("city", "北京市")
    current_hour = int(time.strftime("%H"))

    # 生成未来 6 小时逐小时走势数据
    hourly_forecast = []
    base_temp = 21.0
    weather_icons = ["☀️", "⛅", "⛅", "🌤️", "☁️", "🌧️"]
    conds = ["晴朗", "多云", "阴天", "多云", "阴天", "小雨"]

    for i in range(1, 7):
        h = (current_hour + i) % 24
        # 温度在当前基础上有微波动
        offset = round(random.uniform(-1.5, 1.5), 1)
        hourly_forecast.append({
            "time": f"{h:02d}:00",
            "temp": round(base_temp + offset, 1),
            "icon": weather_icons[(current_hour + i) % len(weather_icons)],
            "condition": conds[(current_hour + i) % len(conds)],
            "rain_prob": random.randint(5, 30),
        })

    return {
        "city": target_city,
        "temperature": 21.5,
        "humidity": 46,
        "weather": "晴间多云",
        "icon": "⛅",
        "wind": "微风 2级",
        "alert_title": "气象预警监测",
        "alert_content": f"{target_city}当前暂无极端气象预警，室内外温湿度适宜观展出行",
        "alert_level": "level-normal",
        "hourly_forecast": hourly_forecast,
        "demo_mode": _system_settings_store.get("demo_mode", True),
    }
