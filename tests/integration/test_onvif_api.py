"""
集成测试：ONVIF 设备发现与通道查询 API
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from backend.main import app
from core.stream.onvif_discovery import OnvifDevice, OnvifChannel


@pytest.mark.asyncio
async def test_onvif_scan_mocked():
    """测试 ONVIF 扫描接口（Mock 模拟发现设备）"""
    mock_device = OnvifDevice(
        address="192.168.1.108",
        name="Hikvision NVR",
        manufacturer="Hikvision",
        model="DS-7608N-I2",
        hardware_id="DS7608NI2",
    )

    with patch("core.stream.onvif_discovery.OnvifDiscovery.discover", return_value=[mock_device]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/onvif/scan", json={"timeout": 1.0})
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["address"] == "192.168.1.108"
            assert data[0]["manufacturer"] == "Hikvision"


@pytest.mark.asyncio
async def test_onvif_channels_failed_connect():
    """测试 ONVIF 连接不可达设备的错误返回"""
    with patch("core.stream.onvif_discovery.OnvifClient.connect", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/onvif/channels", json={
                "address": "192.168.1.250",
                "username": "admin",
                "password": "wrongpassword",
            })
            assert resp.status_code == 400
            assert "连接失败" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_onvif_channels_mocked_success():
    """测试 ONVIF 成功解析通道列表与 RTSP 地址"""
    mock_channel = OnvifChannel(
        token="Profile_1",
        channel_name="展厅大门通道",
        width=1920,
        height=1080,
        encoding="H264",
        rtsp_url="rtsp://admin:123456@192.168.1.108:554/Streaming/Channels/101",
    )

    with patch("core.stream.onvif_discovery.OnvifClient.connect", return_value=True), \
         patch("core.stream.onvif_discovery.OnvifClient.get_channels", return_value=[mock_channel]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/onvif/channels", json={
                "address": "192.168.1.108",
                "username": "admin",
                "password": "password",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["token"] == "Profile_1"
            assert data[0]["rtsp_url"].startswith("rtsp://")
