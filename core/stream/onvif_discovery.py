"""
ONVIF 设备发现与通道获取模块
- WS-Discovery 自动发现局域网内 NVR / 摄像头
- 通过 ONVIF 协议获取设备通道列表和 RTSP 流地址
- 支持海康、大华、宇视等主流品牌
"""
import logging
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class OnvifDevice:
    """发现的 ONVIF 设备"""
    address: str                   # 设备 IP:Port
    name: str = ""                 # 设备名称
    manufacturer: str = ""         # 制造商
    model: str = ""                # 型号
    firmware: str = ""             # 固件版本
    hardware_id: str = ""          # 硬件ID
    serial_number: str = ""        # 序列号
    scopes: List[str] = field(default_factory=list)


@dataclass
class OnvifChannel:
    """设备上的某路视频通道"""
    token: str                     # Profile Token
    channel_name: str = ""         # 通道名称
    width: int = 0                 # 分辨率宽
    height: int = 0                # 分辨率高
    encoding: str = ""             # 编码格式（H264 / H265）
    rtsp_url: str = ""             # 该通道的 RTSP 流地址


class OnvifDiscovery:
    """
    ONVIF WS-Discovery 局域网设备发现
    使用 WS-Discovery 广播 UDP 报文扫描局域网内支持 ONVIF 的设备
    """

    @staticmethod
    async def discover(timeout: float = 5.0) -> List[OnvifDevice]:
        """
        发现局域网内所有 ONVIF 设备
        Returns: OnvifDevice 列表
        """
        devices: List[OnvifDevice] = []

        try:
            from wsdiscovery import WSDiscovery
            from wsdiscovery import QName, Scope

            wsd = WSDiscovery()
            wsd.start()

            # 搜索 ONVIF 设备类型
            services = wsd.searchServices(
                types=[QName("http://www.onvif.org/ver10/network/wsdl", "NetworkVideoTransmitter")],
                timeout=int(timeout),
            )

            for service in services:
                xaddrs = service.getXAddrs()
                scopes = [str(s) for s in (service.getScopes() or [])]

                # 从 scopes 中解析设备信息
                name = _extract_scope(scopes, "onvif://www.onvif.org/name/")
                manufacturer = _extract_scope(scopes, "onvif://www.onvif.org/manufacturer/")
                model = _extract_scope(scopes, "onvif://www.onvif.org/model/")
                hardware_id = _extract_scope(scopes, "onvif://www.onvif.org/hardware/")

                for addr in xaddrs:
                    devices.append(OnvifDevice(
                        address=addr,
                        name=name,
                        manufacturer=manufacturer,
                        model=model,
                        hardware_id=hardware_id,
                        scopes=scopes,
                    ))

            wsd.stop()
            logger.info(f"ONVIF 发现完成，共找到 {len(devices)} 个设备")

        except ImportError:
            logger.warning("WS-Discovery 未安装（pip install wsdiscovery），使用手动扫描模式")
            # 降级：手动端口扫描
            devices = await OnvifDiscovery._fallback_scan(timeout)

        except Exception as e:
            logger.error(f"ONVIF 发现异常: {e}")

        return devices

    @staticmethod
    async def _fallback_scan(timeout: float = 3.0) -> List[OnvifDevice]:
        """降级方案：扫描常见 ONVIF 端口（80, 8000, 8080）"""
        import socket
        devices = []
        # 获取本机 IP 段
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "192.168.1.1"

        subnet = ".".join(local_ip.split(".")[:3])
        onvif_ports = [80, 8000, 8080, 554]

        logger.info(f"降级扫描子网: {subnet}.0/24，端口: {onvif_ports}")

        async def _probe(ip: str, port: int):
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=timeout,
                )
                writer.close()
                await writer.wait_closed()
                return OnvifDevice(address=f"http://{ip}:{port}/onvif/device_service")
            except Exception:
                return None

        tasks = [_probe(f"{subnet}.{i}", port) for i in range(1, 255) for port in onvif_ports]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        devices = [r for r in results if isinstance(r, OnvifDevice)]

        logger.info(f"端口扫描完成，发现 {len(devices)} 个可能的 ONVIF 端点")
        return devices


class OnvifClient:
    """
    ONVIF 设备客户端
    连接到指定 ONVIF 设备获取通道信息和 RTSP 流地址
    """

    def __init__(self, address: str, username: str = "admin", password: str = ""):
        self.address = address
        self.username = username
        self.password = password
        self._camera = None

    async def connect(self) -> bool:
        """连接到 ONVIF 设备"""
        try:
            from onvif import ONVIFCamera
            import urllib.parse

            parsed = urllib.parse.urlparse(self.address)
            host = parsed.hostname or self.address
            port = parsed.port or 80

            self._camera = ONVIFCamera(host, port, self.username, self.password)
            await self._camera.update_xaddrs()
            logger.info(f"ONVIF 连接成功: {host}:{port}")
            return True

        except ImportError:
            logger.error("ONVIF 库未安装，请执行: pip install onvif-zeep")
            return False
        except Exception as e:
            logger.error(f"ONVIF 连接失败 [{self.address}]: {e}")
            return False

    async def get_device_info(self) -> Dict[str, Any]:
        """获取设备基本信息"""
        if not self._camera:
            return {}
        try:
            info = await self._camera.devicemgmt.GetDeviceInformation()
            return {
                "manufacturer": info.Manufacturer,
                "model": info.Model,
                "firmware": info.FirmwareVersion,
                "serial": info.SerialNumber,
                "hardware_id": info.HardwareId,
            }
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
            return {}

    async def get_channels(self) -> List[OnvifChannel]:
        """获取所有视频通道（Profile）及其 RTSP 流地址"""
        channels: List[OnvifChannel] = []
        if not self._camera:
            return channels

        try:
            media_service = self._camera.create_media_service()
            profiles = await media_service.GetProfiles()

            for profile in profiles:
                channel = OnvifChannel(
                    token=profile.token,
                    channel_name=profile.Name or profile.token,
                )

                # 获取视频编码配置
                if hasattr(profile, "VideoEncoderConfiguration") and profile.VideoEncoderConfiguration:
                    vec = profile.VideoEncoderConfiguration
                    channel.encoding = str(vec.Encoding) if vec.Encoding else ""
                    if vec.Resolution:
                        channel.width = vec.Resolution.Width
                        channel.height = vec.Resolution.Height

                # 获取 RTSP 流地址
                try:
                    stream_setup = {
                        "Stream": "RTP-Unicast",
                        "Transport": {"Protocol": "RTSP"},
                    }
                    uri = await media_service.GetStreamUri(
                        StreamSetup=stream_setup,
                        ProfileToken=profile.token,
                    )
                    channel.rtsp_url = uri.Uri

                    # 注入认证信息到 RTSP URL
                    if self.username and channel.rtsp_url:
                        channel.rtsp_url = _inject_rtsp_auth(
                            channel.rtsp_url, self.username, self.password
                        )

                except Exception as e:
                    logger.warning(f"获取 RTSP 流地址失败 [{profile.token}]: {e}")

                channels.append(channel)

            logger.info(f"获取到 {len(channels)} 个视频通道")

        except Exception as e:
            logger.error(f"获取通道列表失败: {e}")

        return channels

    async def get_snapshot_uri(self, profile_token: str) -> Optional[str]:
        """获取某通道的静态抓图地址"""
        if not self._camera:
            return None
        try:
            media_service = self._camera.create_media_service()
            uri = await media_service.GetSnapshotUri(ProfileToken=profile_token)
            return uri.Uri
        except Exception:
            return None


# ─── 工具函数 ──────────────────────────────────────────────────────────

def _extract_scope(scopes: List[str], prefix: str) -> str:
    """从 ONVIF scope 列表中提取指定前缀的值"""
    import urllib.parse
    for scope in scopes:
        if scope.startswith(prefix):
            return urllib.parse.unquote(scope[len(prefix):])
    return ""


def _inject_rtsp_auth(url: str, username: str, password: str) -> str:
    """将认证信息注入 RTSP URL（rtsp://user:pass@host:port/path）"""
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    if not parsed.username:
        netloc = f"{username}:{password}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urllib.parse.urlunparse(parsed._replace(netloc=netloc))
    return url
