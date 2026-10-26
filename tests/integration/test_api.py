"""
集成测试：FastAPI 摄像头管理接口
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
        # 新增摄像头
        resp = await client.post("/api/cameras/", json={
            "id": "test_cam_001",
            "name": "测试摄像头",
            "rtsp_url": "rtsp://localhost/test",
            "brand": "generic",
            "fps_limit": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        # 列出摄像头
        resp = await client.get("/api/cameras/")
        assert resp.status_code == 200
        cam_ids = [c["id"] for c in resp.json()]
        assert "test_cam_001" in cam_ids

        # 移除摄像头
        resp = await client.delete("/api/cameras/test_cam_001")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_in" in data
    assert "gender" in data


@pytest.mark.asyncio
async def test_export_excel():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/export/excel")
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats" in resp.headers["content-type"]
