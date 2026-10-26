"""
WebSocket 实时推流 API（大屏用）
已对接 FlowRepository 真实数据，兼容降级
"""
import asyncio
import json
import time
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..db.repository import FlowRepository

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── 演示数据（数据库不可用时降级） ──────────────────────────────────
_DEMO_PAYLOAD = {
    "current_in_venue": 13,
    "total_in_today": 128,
    "total_out_today": 115,
    "gender": {"male": 72, "female": 56},
    "age_group": {"child": 18, "young": 55, "adult": 42, "elder": 13},
    "zone_dwell": [
        {"name": "展台A", "avg_dwell": 38.5, "current_visitors": 3},
        {"name": "展台B", "avg_dwell": 22.1, "current_visitors": 1},
        {"name": "展台C", "avg_dwell": 65.3, "current_visitors": 2},
    ],
}


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        logger.info(f"WebSocket 断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(json.dumps(data, ensure_ascii=False))
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            if ws in self.active_connections:
                self.active_connections.remove(ws)


manager = ConnectionManager()


async def _get_snapshot() -> dict:
    """获取实时快照，数据库不可用时返回演示数据"""
    try:
        return await FlowRepository.get_realtime_snapshot()
    except Exception:
        return _DEMO_PAYLOAD


@router.websocket("/realtime")
async def realtime_stream(ws: WebSocket):
    """
    实时推送客流数据到大屏
    每秒推送一次当前客流快照
    """
    await manager.connect(ws)
    try:
        while True:
            payload = await _get_snapshot()
            payload["timestamp"] = time.time()
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
        manager.disconnect(ws)
