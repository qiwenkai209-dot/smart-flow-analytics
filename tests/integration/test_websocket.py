"""
集成测试：WebSocket 实时推流接口
"""
import json
from fastapi.testclient import TestClient
from backend.main import app


def test_websocket_realtime_stream():
    """测试客户端连接 /ws/realtime 并能收到格式正确的客流快照"""
    client = TestClient(app)
    with client.websocket_connect("/ws/realtime") as websocket:
        data = websocket.receive_text()
        payload = json.loads(data)

        assert "current_in_venue" in payload
        assert "total_in_today" in payload
        assert "total_out_today" in payload
        assert "gender" in payload
        assert "age_group" in payload
        assert "zone_dwell" in payload
        assert isinstance(payload["zone_dwell"], list)
