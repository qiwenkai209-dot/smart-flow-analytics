"""
FastAPI 主入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import cameras, analytics, export, websocket
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Smart Flow Analytics 后端启动")
    yield
    logger.info("🛑 后端关闭")


app = FastAPI(
    title="Smart Flow Analytics API",
    description="智慧展厅多路客流分析系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cameras.router,   prefix="/api/cameras",   tags=["摄像头管理"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["客流统计"])
app.include_router(export.router,    prefix="/api/export",    tags=["报表导出"])
app.include_router(websocket.router, prefix="/ws",            tags=["实时推流"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "smart-flow-analytics"}
