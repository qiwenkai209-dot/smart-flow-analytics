"""
WebSocket 实时推流 API（大屏用）
"""
import asyncio
import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, ws: WebSocket):
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
            self.active_connections.remove(ws)


manager = ConnectionManager()


@router.websocket("/realtime")
async def realtime_stream(ws: WebSocket):
    """
    实时推送客流数据到大屏
    每秒推送一次当前客流快照
    """
    await manager.connect(ws)
    try:
        while True:
            # TODO: 替换为真实数据源
            payload = {
                "timestamp": time.time(),
                "current_in_venue": 13,
                "total_in_today": 128,
                "total_out_today": 115,
                "gender": {"male": 72, "female": 56},
                "age_group": {"child": 18, "young": 55, "adult": 42, "elder": 13},
                "zone_dwell": [
                    {"name": "展台A", "avg_dwell": 38.5, "current_visitors": 3},
                    {"name": "展台B", "avg_dwell": 22.1, "current_visitors": 1},
                ],
            }
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(ws)
