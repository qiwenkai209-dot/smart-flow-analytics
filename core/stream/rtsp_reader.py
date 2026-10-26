import threading
import time
import queue
import logging
from dataclasses import dataclass, field
from typing import Optional
import cv2

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    id: str
    name: str
    rtsp_url: str
    brand: str = "generic"       # generic | hikvision | dahua | uniview
    fps_limit: int = 10          # 抽帧率（控制算力消耗）
    reconnect_interval: float = 5.0
    frame_buffer_size: int = 1   # 只保留最新 1 帧，保证实时性


BRAND_RTSP_TEMPLATES = {
    "hikvision": "rtsp://{user}:{password}@{host}:{port}/Streaming/Channels/{channel}01",
    "dahua":     "rtsp://{user}:{password}@{host}:{port}/cam/realmonitor?channel={channel}&subtype=0",
    "uniview":   "rtsp://{user}:{password}@{host}:{port}/media/video{channel}",
    "generic":   "{rtsp_url}",  # 直接使用原始 RTSP 地址
}


class RTSPReader:
    """
    单路 RTSP 摄像头读取器
    - 独立线程持续拉流，只缓存最新帧（丢弃旧帧保证实时性）
    - 断线自动重连
    - 支持抽帧（fps_limit）降低算力消耗
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

    def _build_rtsp_url(self) -> str:
        """根据品牌构建正确的 RTSP URL"""
        return self.config.rtsp_url  # 通用模式直接返回，后续可扩展品牌适配

    def _connect(self) -> bool:
        url = self._build_rtsp_url()
        logger.info(f"[{self.config.id}] 正在连接: {url}")
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)    # 最小缓冲，保证实时
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

        if cap.isOpened():
            with self._lock:
                self._cap = cap
            self.is_connected = True
            logger.info(f"[{self.config.id}] 连接成功 ✅")
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
        frame_interval = 1.0 / self.config.fps_limit
        last_frame_time = 0.0

        while self._running:
            if not self.is_connected:
                if not self._connect():
                    time.sleep(self.config.reconnect_interval)
                    continue

            now = time.time()
            if now - last_frame_time < frame_interval:
                # 抽帧：直接 grab() 丢弃，不做 decode，几乎不消耗 CPU
                with self._lock:
                    if self._cap:
                        self._cap.grab()
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

            # 只保留最新帧（队列满则丢弃旧帧）
            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self._frame_queue.put_nowait(frame)

            # 统计实际 FPS
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
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info(f"[{self.config.id}] 取流线程停止")

    def read(self, timeout: float = 1.0) -> Optional[any]:
        """获取最新帧，超时返回 None"""
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def status(self) -> dict:
        return {
            "id": self.config.id,
            "name": self.config.name,
            "connected": self.is_connected,
            "fps_actual": round(self.fps_actual, 1),
            "fps_limit": self.config.fps_limit,
        }
