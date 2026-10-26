"""
FastAPI 主入口
- 注册所有 API 路由（摄像头、统计、导出、WebSocket、ONVIF）
- 启动时初始化数据库、加载摄像头配置
- 管理 Pipeline Orchestrator 生命周期
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .api import cameras, analytics, export, websocket, onvif

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# 全局 Orchestrator 引用（供 API 访问运行状态）
_orchestrator = None


def get_orchestrator():
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator

    logger.info("🚀 Smart Flow Analytics 后端启动")

    # ── 1. 初始化数据库 ──────────────────────────────────────────────
    try:
        from .db.database import init_db
        await init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.warning(f"⚠️ 数据库初始化失败（将使用演示数据）: {e}")

    # ── 2. 加载摄像头配置 & 启动 Orchestrator ─────────────────────────
    try:
        config_path = os.getenv("CAMERAS_CONFIG", "configs/cameras.yaml")
        if os.path.exists(config_path):
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            from core.roi.roi_manager import ROIConfig
            from core.stream.rtsp_reader import CameraConfig
            from core.orchestrator import PipelineOrchestrator
            from .db.database import insert_flow_event
            from datetime import datetime, timezone

            # 解析 ROI 配置
            roi_configs = []
            for cam_cfg in config.get("cameras", []):
                for roi in cam_cfg.get("rois", []):
                    roi_configs.append(ROIConfig(
                        name=roi["name"],
                        polygon=roi["polygon"],
                        min_dwell_seconds=roi.get("min_dwell_seconds", 5.0),
                    ))

            # 事件入库回调
            async def on_flow_event(event):
                try:
                    await insert_flow_event({
                        "event_time": datetime.fromtimestamp(event.timestamp, tz=timezone.utc),
                        "event_type": event.event_type,
                        "global_id": event.global_id,
                        "camera_id": event.camera_id,
                        "roi_name": event.roi_name,
                        "gender": event.gender,
                        "age_group": event.age_group,
                        "dwell_seconds": event.dwell_seconds,
                        "snapshot_path": event.snapshot_path,
                    })
                except Exception as e:
                    logger.error(f"事件入库失败: {e}")

            device = os.getenv("DEVICE", "cpu")
            _orchestrator = PipelineOrchestrator(
                roi_configs=roi_configs,
                device=device,
                on_event=lambda e: __import__("asyncio").ensure_future(on_flow_event(e)),
            )

            # 逐个添加摄像头
            for cam_cfg in config.get("cameras", []):
                camera_config = CameraConfig(
                    id=cam_cfg["id"],
                    name=cam_cfg["name"],
                    rtsp_url=cam_cfg["rtsp_url"],
                    brand=cam_cfg.get("brand", "generic"),
                    fps_limit=cam_cfg.get("fps_limit", 10),
                )
                _orchestrator.add_camera(camera_config)

            logger.info(f"✅ Orchestrator 启动完成，共 {_orchestrator.count} 路摄像头")
        else:
            logger.info(f"未找到摄像头配置文件 [{config_path}]，等待通过 API 动态添加")

    except Exception as e:
        logger.warning(f"⚠️ Orchestrator 启动失败: {e}")

    yield

    # ── 清理 ───────────────────────────────────────────────────────────
    if _orchestrator:
        _orchestrator.stop_all()
        logger.info("🛑 所有 Pipeline 已停止")

    logger.info("🛑 后端关闭")


app = FastAPI(
    title="Smart Flow Analytics API",
    description="智慧展厅多路客流分析系统",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 路由注册 ──────────────────────────────────────────────────────────
app.include_router(cameras.router,   prefix="/api/cameras",   tags=["摄像头管理"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["客流统计"])
app.include_router(export.router,    prefix="/api/export",    tags=["报表导出"])
app.include_router(onvif.router,     prefix="/api/onvif",     tags=["ONVIF 设备发现"])
app.include_router(websocket.router, prefix="/ws",            tags=["实时推流"])


@app.get("/api/health")
async def health():
    orch = get_orchestrator()
    return {
        "status": "ok",
        "service": "smart-flow-analytics",
        "version": "0.2.0",
        "pipelines": orch.count if orch else 0,
    }


@app.get("/api/pipelines/stats", summary="获取所有 Pipeline 运行状态")
async def pipeline_stats():
    """返回所有摄像头 Pipeline 的实时运行统计"""
    orch = get_orchestrator()
    if not orch:
        return {"pipelines": [], "message": "Orchestrator 未启动"}
    return {"pipelines": orch.get_all_stats()}


# ── 托管前端静态资源（一体化可执行软件支持） ─────────────────────────────
import sys
from fastapi.responses import FileResponse

if getattr(sys, "frozen", False):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    frontend_dist = os.path.join(base_dir, "frontend", "dist")
else:
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_frontend(full_path: str):
        target = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(target):
            return FileResponse(target)
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Smart Flow Analytics API 正在运行，前端页面未找到"}

