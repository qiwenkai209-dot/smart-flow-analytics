import threading
import time
import queue
import logging
import base64
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def build_brand_rtsp_url(
    brand: str,
    ip: str,
    port: int = 554,
    username: str = "admin",
    password: str = "",
    channel: int = 1,
    subtype: int = 0,
) -> str:
    """
    根据私有/主流设备品牌规则自动合成 RTSP 播放地址
    - 海康威视 (hikvision): 主码流 /Streaming/Channels/{channel}01, 子码流 02
    - 大华 (dahua): /cam/realmonitor?channel={channel}&subtype={subtype}
    - 宇视 (uniview): /media/video{channel} 或 /unicast/c{channel}/s{subtype}/live
    - 通用 (generic): 直连
    """
    auth = f"{username}:{password}@" if username or password else ""
    ip_port = f"{ip}:{port}" if port and port != 554 else ip

    brand_lower = (brand or "generic").lower()
    if brand_lower == "hikvision":
        # 101 为第1通道主码流，102 为第1通道子码流
        stream_code = f"{channel}0{subtype + 1}"
        return f"rtsp://{auth}{ip_port}/Streaming/Channels/{stream_code}"
    elif brand_lower == "dahua":
        return f"rtsp://{auth}{ip_port}/cam/realmonitor?channel={channel}&subtype={subtype}"
    elif brand_lower == "uniview":
        return f"rtsp://{auth}{ip_port}/unicast/c{channel}/s{subtype}/live"
    else:
        # 通用
        return f"rtsp://{auth}{ip_port}/live/ch{channel}"


@dataclass
class CameraConfig:
    id: str
    name: str
    rtsp_url: str = ""
    brand: str = "generic"            # generic | hikvision | dahua | uniview
    fps_limit: int = 10               # 抽帧率（控制算力消耗）
    reconnect_interval: float = 5.0
    frame_buffer_size: int = 1        # 只保留最新 1 帧，保证实时性

    # 业务分类与功能勾选（进出、驻留、年龄性别）
    features: List[str] = field(default_factory=lambda: ["in_out", "dwell", "attribute"])

    # 详细设备参数（用于私有协议表单回显与保存）
    ip: str = ""
    port: int = 554
    username: str = "admin"
    password: str = ""
    channel: int = 1
    subtype: int = 0                  # 0: 主码流, 1: 子码流

    # 绑定的多边形区域
    rois: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        # 若未提供完整的 rtsp_url 但提供了 ip，自动合成
        if not self.rtsp_url and self.ip:
            self.rtsp_url = build_brand_rtsp_url(
                brand=self.brand,
                ip=self.ip,
                port=self.port,
                username=self.username,
                password=self.password,
                channel=self.channel,
                subtype=self.subtype,
            )


class RTSPReader:
    """
    单路 RTSP 摄像头读取器
    - 独立线程持续拉流，只缓存最新帧（丢弃旧帧保证实时性）
    - 断线自动重连
    - 抽帧限制与最新画面快照抓取
    """

    def __init__(self, config: CameraConfig):
        self.config = config
        self._frame_queue: queue.Queue = queue.Queue(maxsize=config.frame_buffer_size)
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.is_connected = False
        self.fps_actual = 0.0
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._latest_frame: Optional[np.ndarray] = None
        self.resolution: Tuple[int, int] = (0, 0)

    def _connect(self) -> bool:
        url = self.config.rtsp_url
        logger.info(f"[{self.config.id}] 正在连接: {url}")
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000)

        if cap.isOpened():
            with self._lock:
                self._cap = cap
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
                self.resolution = (w, h)
            self.is_connected = True
            logger.info(f"[{self.config.id}] 连接成功 ✅ ({w}x{h})")
            return True
        else:
            cap.release()
            logger.warning(f"[{self.config.id}] 连接失败，{self.config.reconnect_interval}s 后重试")
            return False

    def _release(self):
        with self._lock:
            if self._cap:
                self._cap.release()
                self._cap = None
        self.is_connected = False

    def _read_loop(self):
        """持续读帧主循环"""
        frame_interval = 1.0 / max(self.config.fps_limit, 1)
        last_frame_time = 0.0

        while self._running:
            if not self.is_connected:
                if not self._connect():
                    time.sleep(self.config.reconnect_interval)
                    continue

            now = time.time()
            if now - last_frame_time < frame_interval:
                with self._lock:
                    if self._cap:
                        self._cap.grab()
                time.sleep(0.01)
                continue

            with self._lock:
                cap = self._cap

            if cap is None:
                continue

            ret, frame = cap.read()
            if not ret:
                logger.warning(f"[{self.config.id}] 读帧失败，触发重连")
                self._release()
                continue

            last_frame_time = now
            self._latest_frame = frame

            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self._frame_queue.put_nowait(frame)

            self._frame_count += 1
            elapsed = now - self._last_fps_time
            if elapsed >= 5.0:
                self.fps_actual = self._frame_count / elapsed
                self._frame_count = 0
                self._last_fps_time = now

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True, name=f"rtsp-{self.config.id}")
        self._thread.start()
        logger.info(f"[{self.config.id}] 取流线程启动")

    def stop(self):
        self._running = False
        self._release()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info(f"[{self.config.id}] 取流线程停止")

    def read(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_snapshot_jpeg(self) -> Optional[bytes]:
        """抓取当前最新帧并编码为 JPEG 二进制字节流"""
        frame = self._latest_frame
        if frame is None:
            # 离线或模拟模式，生成一张信息卡片作为快照
            frame = self._generate_placeholder_frame()

        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buffer.tobytes() if ret else None

    def _generate_placeholder_frame(self) -> np.ndarray:
        """生成带时间与信息的测试占位图"""
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        # 背景暗色渐变
        img[:, :] = (20, 24, 33)
        # 绘制网格
        for x in range(0, 1280, 80):
            cv2.line(img, (x, 0), (x, 720), (32, 38, 50), 1)
        for y in range(0, 720, 60):
            cv2.line(img, (0, y), (1280, y), (32, 38, 50), 1)

        cv2.putText(img, f"CAMERA: {self.config.name} ({self.config.id})", (60, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 180, 255), 2)
        cv2.putText(img, f"URL: {self.config.rtsp_url or 'N/A'}", (60, 280),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 175, 200), 2)
        cv2.putText(img, f"FEATURES: {', '.join(self.config.features)}", (60, 350),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 230, 150), 2)
        cv2.putText(img, f"TIME: {time.strftime('%Y-%m-%d %H:%M:%S')}", (60, 420),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(img, "SMART FLOW ANALYTICS LIVE PREVIEW", (60, 520),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 130, 150), 1)
        return img

    @property
    def status(self) -> dict:
        return {
            "id": self.config.id,
            "name": self.config.name,
            "brand": self.config.brand,
            "rtsp_url": self.config.rtsp_url,
            "connected": self.is_connected,
            "fps_actual": round(self.fps_actual, 1),
            "fps_limit": self.config.fps_limit,
            "features": self.config.features,
            "ip": self.config.ip,
            "port": self.config.port,
            "channel": self.config.channel,
            "subtype": self.config.subtype,
            "rois": self.config.rois,
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}" if self.resolution[0] > 0 else "未知",
        }


def test_stream_connection(rtsp_url: str, timeout_sec: float = 4.0) -> Dict[str, Any]:
    """
    独立测试 RTSP 流连通性并抓取第 1 帧画面供前端弹窗即时预览
    """
    logger.info(f"正在测试取流预览: {rtsp_url}")
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout_sec * 1000))
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(timeout_sec * 1000))

    if not cap.isOpened():
        cap.release()
        return {
            "success": False,
            "error": "无法连接到摄像头，请检查网络 IP、端口 554 及账号密码是否正确",
            "preview_base64": None,
            "resolution": "未知",
        }

    ret, frame = cap.read()
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or (frame.shape[1] if ret else 0))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or (frame.shape[0] if ret else 0))
    cap.release()

    if not ret or frame is None or frame.size == 0:
        return {
            "success": False,
            "error": "已建立 RTSP 连接，但未能成功解码视频帧（可能码流未推送或编码格式不支持）",
            "preview_base64": None,
            "resolution": f"{w}x{h}" if w > 0 else "未知",
        }

    # 缩放到合适大小返回 base64 预览图
    scale = min(640 / max(w, 1), 1.0)
    if scale < 1.0:
        preview_frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    else:
        preview_frame = frame

    _, buffer = cv2.imencode('.jpg', preview_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    b64_str = base64.b64encode(buffer).decode('utf-8')

    return {
        "success": True,
        "error": None,
        "preview_base64": f"data:image/jpeg;base64,{b64_str}",
        "resolution": f"{w}x{h}",
    }
