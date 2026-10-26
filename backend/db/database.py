"""
数据库模型与 TimescaleDB 时序表定义
使用 SQLAlchemy 2.0 异步模式
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://sfa:sfa123@localhost:5432/smartflow"
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class FlowEventRecord(Base):
    """
    客流事件明细表（TimescaleDB 时序表）
    每条记录代表一次完整的驻留事件（进入 → 离开）
    """
    __tablename__ = "flow_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_type: Mapped[str] = mapped_column(String(32))     # dwell_complete | enter | leave
    global_id: Mapped[str] = mapped_column(String(64))
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    roi_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    age_group: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    dwell_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    snapshot_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_flow_events_camera_time", "camera_id", "event_time"),
    )


class HourlyFlowStat(Base):
    """
    小时级聚合统计表（预计算，加速大屏查询）
    由后台定时任务每小时写入一次
    """
    __tablename__ = "hourly_flow_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hour_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    roi_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    total_visits: Mapped[int] = mapped_column(Integer, default=0)
    avg_dwell_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    male_count: Mapped[int] = mapped_column(Integer, default=0)
    female_count: Mapped[int] = mapped_column(Integer, default=0)
    child_count: Mapped[int] = mapped_column(Integer, default=0)
    young_count: Mapped[int] = mapped_column(Integer, default=0)
    adult_count: Mapped[int] = mapped_column(Integer, default=0)
    elder_count: Mapped[int] = mapped_column(Integer, default=0)


# ── 数据库操作工具函数 ─────────────────────────────────────────────

async def get_db():
    """FastAPI 依赖注入用"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """初始化数据库表（开发 / 首次部署时使用）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 将 flow_events 转换为 TimescaleDB 超级表（若已安装 TimescaleDB）
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                __import__("sqlalchemy").text(
                    "SELECT create_hypertable('flow_events', 'event_time', if_not_exists => TRUE);"
                )
            )
            await session.commit()
    except Exception:
        pass  # 未安装 TimescaleDB 时降级为普通 PostgreSQL 表


async def insert_flow_event(event_data: dict):
    """插入一条客流事件记录"""
    async with AsyncSessionLocal() as session:
        record = FlowEventRecord(**event_data)
        session.add(record)
        await session.commit()
