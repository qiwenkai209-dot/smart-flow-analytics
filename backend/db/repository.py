"""
后端数据访问层（Repository）
将 API 层的 TODO 占位数据替换为真实 TimescaleDB / PostgreSQL 查询
兼容未安装 TimescaleDB 时降级为标准 PostgreSQL 查询
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, text, and_, case

from .database import AsyncSessionLocal, FlowEventRecord

logger = logging.getLogger(__name__)


class FlowRepository:
    """客流数据仓库 —— 后端 API 的唯一数据来源"""

    # ─── 汇总统计 ────────────────────────────────────────────────────

    @staticmethod
    async def get_summary(
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        返回客流汇总统计（全量或按摄像头 / 时间段过滤）
        """
        async with AsyncSessionLocal() as session:
            filters = []
            if camera_id:
                if "," in camera_id:
                    cams = [c.strip() for c in camera_id.split(",") if c.strip()]
                    filters.append(FlowEventRecord.camera_id.in_(cams))
                else:
                    filters.append(FlowEventRecord.camera_id == camera_id)
            if start_time:
                filters.append(FlowEventRecord.event_time >= start_time)
            if end_time:
                filters.append(FlowEventRecord.event_time <= end_time)

            where_clause = and_(*filters) if filters else True

            # 总入场 / 总离场
            total_in = await session.scalar(
                select(func.count()).where(
                    and_(where_clause, FlowEventRecord.event_type.in_(["enter", "dwell_complete"]))
                )
            ) or 0

            total_out = await session.scalar(
                select(func.count()).where(
                    and_(where_clause, FlowEventRecord.event_type == "leave")
                )
            ) or 0

            # 性别统计
            gender_rows = (await session.execute(
                select(
                    FlowEventRecord.gender,
                    func.count().label("cnt"),
                ).where(
                    and_(where_clause, FlowEventRecord.gender.isnot(None))
                ).group_by(FlowEventRecord.gender)
            )).all()
            gender = {row[0]: row[1] for row in gender_rows}

            # 年龄段统计
            age_rows = (await session.execute(
                select(
                    FlowEventRecord.age_group,
                    func.count().label("cnt"),
                ).where(
                    and_(where_clause, FlowEventRecord.age_group.isnot(None))
                ).group_by(FlowEventRecord.age_group)
            )).all()
            age_group = {row[0]: row[1] for row in age_rows}

            return {
                "total_in": total_in,
                "total_out": total_out,
                "current_in_venue": max(total_in - total_out, 0),
                "gender": {
                    "male": gender.get("male", 0),
                    "female": gender.get("female", 0),
                },
                "age_group": {
                    "child": age_group.get("child", 0),
                    "young": age_group.get("young", 0),
                    "adult": age_group.get("adult", 0),
                    "elder": age_group.get("elder", 0),
                },
                "camera_id": camera_id or "all",
            }

    # ─── 展台驻留统计 ────────────────────────────────────────────────

    @staticmethod
    async def get_dwell_stats(
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            filters = [FlowEventRecord.event_type == "dwell_complete"]
            if camera_id:
                if "," in camera_id:
                    cams = [c.strip() for c in camera_id.split(",") if c.strip()]
                    filters.append(FlowEventRecord.camera_id.in_(cams))
                else:
                    filters.append(FlowEventRecord.camera_id == camera_id)
            if start_time:
                filters.append(FlowEventRecord.event_time >= start_time)
            if end_time:
                filters.append(FlowEventRecord.event_time <= end_time)

            where_clause = and_(*filters)

            rows = (await session.execute(
                select(
                    FlowEventRecord.roi_name,
                    func.count().label("visits"),
                    func.avg(FlowEventRecord.dwell_seconds).label("avg_dwell_seconds"),
                    func.sum(case((FlowEventRecord.gender == "male", 1), else_=0)).label("male"),
                    func.sum(case((FlowEventRecord.gender == "female", 1), else_=0)).label("female"),
                ).where(where_clause)
                .group_by(FlowEventRecord.roi_name)
                .order_by(func.avg(FlowEventRecord.dwell_seconds).desc())
            )).all()

            zones = [
                {
                    "name": row.roi_name or "未命名区域",
                    "visits": row.visits,
                    "avg_dwell_seconds": round(float(row.avg_dwell_seconds or 0), 1),
                    "male": row.male,
                    "female": row.female,
                }
                for row in rows
            ]
            return {"zones": zones}

    # ─── 时间序列 ─────────────────────────────────────────────────────

    @staticmethod
    async def get_timeseries(
        camera_id: Optional[str] = None,
        interval: str = "1h",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        返回每个时间粒度的进出人数
        尝试 TimescaleDB time_bucket → 降级为标准 PostgreSQL date_trunc
        """
        # 映射间隔到 PostgreSQL date_trunc / TimescaleDB time_bucket 格式
        interval_map = {
            "5m": ("5 minutes", "minute"),
            "15m": ("15 minutes", "minute"),
            "1h": ("1 hour", "hour"),
            "1d": ("1 day", "day"),
        }
        ts_interval, pg_trunc = interval_map.get(interval, ("1 hour", "hour"))

        if not start_time:
            start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_time:
            end_time = datetime.now(timezone.utc)

        cam_filter = "AND camera_id = :cam" if camera_id else ""

        # 先尝试 TimescaleDB time_bucket
        try:
            query = text(f"""
                SELECT
                    time_bucket(:interval, event_time) AS bucket,
                    COUNT(*) FILTER (WHERE event_type IN ('enter', 'dwell_complete')) AS in_count,
                    COUNT(*) FILTER (WHERE event_type = 'leave') AS out_count
                FROM flow_events
                WHERE event_time BETWEEN :start AND :end {cam_filter}
                GROUP BY bucket
                ORDER BY bucket
            """)
            params = {"interval": ts_interval, "start": start_time, "end": end_time}
            if camera_id:
                params["cam"] = camera_id

            async with AsyncSessionLocal() as session:
                rows = (await session.execute(query, params)).all()

        except Exception:
            # 降级为标准 PostgreSQL date_trunc
            query = text(f"""
                SELECT
                    date_trunc(:trunc, event_time) AS bucket,
                    COUNT(*) FILTER (WHERE event_type IN ('enter', 'dwell_complete')) AS in_count,
                    COUNT(*) FILTER (WHERE event_type = 'leave') AS out_count
                FROM flow_events
                WHERE event_time BETWEEN :start AND :end {cam_filter}
                GROUP BY bucket
                ORDER BY bucket
            """)
            params = {"trunc": pg_trunc, "start": start_time, "end": end_time}
            if camera_id:
                params["cam"] = camera_id

            async with AsyncSessionLocal() as session:
                rows = (await session.execute(query, params)).all()

        series = [
            {
                "time": row.bucket.strftime("%H:%M") if hasattr(row.bucket, "strftime") else str(row.bucket),
                "in": row.in_count,
                "out": row.out_count,
            }
            for row in rows
        ]
        return {"interval": interval, "series": series}

    # ─── 驻留明细（导出用） ──────────────────────────────────────────

    @staticmethod
    async def get_dwell_detail(
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """返回驻留明细列表（用于 Excel / CSV 导出）"""
        async with AsyncSessionLocal() as session:
            filters = [FlowEventRecord.event_type == "dwell_complete"]
            if camera_id:
                filters.append(FlowEventRecord.camera_id == camera_id)
            if start_time:
                filters.append(FlowEventRecord.event_time >= start_time)
            if end_time:
                filters.append(FlowEventRecord.event_time <= end_time)

            rows = (await session.execute(
                select(FlowEventRecord)
                .where(and_(*filters))
                .order_by(FlowEventRecord.event_time.desc())
                .limit(5000)
            )).scalars().all()

            return [
                {
                    "global_id": r.global_id,
                    "camera_id": r.camera_id,
                    "roi_name": r.roi_name or "",
                    "event_time": r.event_time.strftime("%Y-%m-%d %H:%M:%S") if r.event_time else "",
                    "dwell_seconds": r.dwell_seconds or 0,
                    "gender": r.gender or "",
                    "age_group": r.age_group or "",
                }
                for r in rows
            ]

    # ─── 实时快照（WebSocket 用） ─────────────────────────────────────

    @staticmethod
    async def get_realtime_snapshot() -> Dict[str, Any]:
        """获取今日实时快照数据（WebSocket 每秒推送）"""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        async with AsyncSessionLocal() as session:
            total_in = await session.scalar(
                select(func.count()).where(
                    and_(
                        FlowEventRecord.event_time >= today_start,
                        FlowEventRecord.event_type.in_(["enter", "dwell_complete"]),
                    )
                )
            ) or 0

            total_out = await session.scalar(
                select(func.count()).where(
                    and_(
                        FlowEventRecord.event_time >= today_start,
                        FlowEventRecord.event_type == "leave",
                    )
                )
            ) or 0

            # 性别
            gender_rows = (await session.execute(
                select(
                    FlowEventRecord.gender,
                    func.count().label("cnt"),
                ).where(
                    and_(
                        FlowEventRecord.event_time >= today_start,
                        FlowEventRecord.gender.isnot(None),
                    )
                ).group_by(FlowEventRecord.gender)
            )).all()
            gender = {r[0]: r[1] for r in gender_rows}

            # 年龄段
            age_rows = (await session.execute(
                select(
                    FlowEventRecord.age_group,
                    func.count().label("cnt"),
                ).where(
                    and_(
                        FlowEventRecord.event_time >= today_start,
                        FlowEventRecord.age_group.isnot(None),
                    )
                ).group_by(FlowEventRecord.age_group)
            )).all()
            age_group = {r[0]: r[1] for r in age_rows}

            # 展台驻留快照
            zone_rows = (await session.execute(
                select(
                    FlowEventRecord.roi_name,
                    func.avg(FlowEventRecord.dwell_seconds).label("avg_dwell"),
                    func.count().label("visits"),
                ).where(
                    and_(
                        FlowEventRecord.event_time >= today_start,
                        FlowEventRecord.event_type == "dwell_complete",
                        FlowEventRecord.roi_name.isnot(None),
                    )
                ).group_by(FlowEventRecord.roi_name)
            )).all()

            zone_dwell = [
                {
                    "name": r.roi_name,
                    "avg_dwell": round(float(r.avg_dwell or 0), 1),
                    "current_visitors": 0,  # 后续接入 Orchestrator 实时数据
                }
                for r in zone_rows
            ]

        return {
            "current_in_venue": max(total_in - total_out, 0),
            "total_in_today": total_in,
            "total_out_today": total_out,
            "gender": {"male": gender.get("male", 0), "female": gender.get("female", 0)},
            "age_group": {
                "child": age_group.get("child", 0),
                "young": age_group.get("young", 0),
                "adult": age_group.get("adult", 0),
                "elder": age_group.get("elder", 0),
            },
            "zone_dwell": zone_dwell,
        }
