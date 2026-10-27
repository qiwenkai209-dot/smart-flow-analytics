"""
集成测试：FastAPI 摄像头与展台管理、即时预览与统计接口
"""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_add_and_list_camera():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 新增通用摄像头
        resp = await client.post("/api/cameras/", json={
            "id": "test_cam_001",
            "name": "测试摄像头",
            "rtsp_url": "rtsp://localhost/test",
            "brand": "generic",
            "fps_limit": 5,
            "features": ["in_out", "dwell"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        # 列出摄像头
        resp = await client.get("/api/cameras/")
        assert resp.status_code == 200
        cams = resp.json()
        cam = next((c for c in cams if c["id"] == "test_cam_001"), None)
        assert cam is not None
        assert "in_out" in cam["features"]

        # 移除摄像头
        resp = await client.delete("/api/cameras/test_cam_001")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_add_hikvision_auto_synthesized_rtsp():
    """测试海康威视直接输入 IP 密码自动合成 RTSP 并保存功能分类"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/cameras/", json={
            "id": "hik_001",
            "name": "展台特写",
            "brand": "hikvision",
            "ip": "192.168.1.64",
            "port": 554,
            "username": "admin",
            "password": "hikpassword",
            "channel": 1,
            "subtype": 0,
            "features": ["dwell", "attribute"],
        })
        assert resp.status_code == 200
        rtsp_url = resp.json()["rtsp_url"]
        assert "admin:hikpassword@192.168.1.64" in rtsp_url
        assert "/Streaming/Channels/101" in rtsp_url

        # 验证快照接口返回 JPEG
        snap_resp = await client.get("/api/cameras/hik_001/snapshot")
        assert snap_resp.status_code == 200
        assert snap_resp.headers["content-type"] == "image/jpeg"

        # 清理
        await client.delete("/api/cameras/hik_001")


@pytest.mark.asyncio
async def test_preview_test_api():
    """测试预览连接测试接口"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/cameras/preview-test", json={
            "brand": "dahua",
            "ip": "192.168.1.100",
            "port": 554,
            "username": "admin",
            "password": "password",
            "channel": 1,
            "subtype": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "rtsp_url" in data
        assert "cam/realmonitor?channel=1&subtype=1" in data["rtsp_url"]


@pytest.mark.asyncio
async def test_roi_custom_manage_and_bind_camera():
    """测试自定义新增展台、关联指定摄像头、编辑与删除"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 先注册一路摄像头
        await client.post("/api/cameras/", json={
            "id": "cam_zone_test",
            "name": "展厅主镜头",
            "rtsp_url": "rtsp://dummy/test",
            "features": ["dwell"],
        })

        # 新增展台并关联摄像头
        resp = await client.post("/api/cameras/rois", json={
            "name": "展台A-AI数字人专区",
            "camera_id": "cam_zone_test",
            "min_dwell_seconds": 6.0,
            "polygon": [[100, 100], [500, 100], [500, 500], [100, 500]],
        })
        assert resp.status_code == 200

        # 查询所有展台
        rois_resp = await client.get("/api/cameras/rois/all")
        assert rois_resp.status_code == 200
        rois = rois_resp.json()
        target = next((r for r in rois if r["name"] == "展台A-AI数字人专区"), None)
        assert target is not None
        assert target["camera_id"] == "cam_zone_test"
        assert target["min_dwell_seconds"] == 6.0

        # 删除展台与清理摄像头
        del_resp = await client.delete("/api/cameras/rois/展台A-AI数字人专区")
        assert del_resp.status_code == 200
        await client.delete("/api/cameras/cam_zone_test")


@pytest.mark.asyncio
async def test_analytics_summary_with_multi_camera_filter():
    """测试按自定义关联摄像头核算在场人数与客流"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/analytics/summary?camera_id=cam_001,cam_002")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_in" in data
        assert "current_in_venue" in data


@pytest.mark.asyncio
async def test_export_excel():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/export/excel")
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats" in resp.headers["content-type"]
