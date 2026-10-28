from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_list_devices():
    resp = client.get("/api/devices/")
    assert resp.status_code == 200
    devices = resp.json()
    assert isinstance(devices, list)
    assert len(devices) >= 1


def test_add_and_delete_device():
    new_dev = {
        "name": "测试展台温湿度探头",
        "type": "temperature_humidity",
        "protocol": "tcp",
        "ip": "192.168.1.188",
        "port": 5002,
        "serial_port": "COM4",
        "baudrate": 9600,
        "poll_interval": 5,
    }
    resp = client.post("/api/devices/", json=new_dev)
    assert resp.status_code == 200
    data = resp.json()
    assert "device" in data
    dev_id = data["device"]["id"]

    # 测试读取环境综合数据
    env_resp = client.get("/api/devices/environment/latest")
    assert env_resp.status_code == 200
    env_data = env_resp.json()
    assert "indoor_temperature" in env_data
    assert "indoor_humidity" in env_data

    # 测试轮询
    test_poll_resp = client.post(f"/api/devices/test-poll/{dev_id}")
    assert test_poll_resp.status_code == 200
    assert test_poll_resp.json()["success"] is True

    # 删除设备
    del_resp = client.delete(f"/api/devices/{dev_id}")
    assert del_resp.status_code == 200


def test_analysis_config():
    get_resp = client.get("/api/devices/analysis-config")
    assert get_resp.status_code == 200
    cfg = get_resp.json()
    assert "conf_threshold" in cfg

    # 更新配置
    cfg["conf_threshold"] = 0.52
    post_resp = client.post("/api/devices/analysis-config", json=cfg)
    assert post_resp.status_code == 200
    assert post_resp.json()["config"]["conf_threshold"] == 0.52
