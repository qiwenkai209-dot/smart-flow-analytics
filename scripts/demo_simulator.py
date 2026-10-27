"""
智慧展厅客流分析系统 —— 动态数据仿真模拟器
用于开发调试、无摄像头环境下的大屏实时演示与压力测试。

用法：
    python scripts/demo_simulator.py [--interval 1.5] [--database-url ...]
"""
import asyncio
import random
import time
import argparse
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Simulator")

ZONES = ["展台A-AI数字人", "展台B-智能座舱", "展台C-机器人演示区", "入口文创区"]
GENDERS = ["male", "female"]
AGE_GROUPS = ["child", "young", "adult", "elder"]
CAMERAS = ["cam_001", "cam_002"]


class FlowSimulator:
    """模拟展厅人员的完整行为轨迹：进入 -> 展台驻留 -> 离开"""

    def __init__(self, db_url: str = None):
        self.db_url = db_url
        self.active_visitors = {}  # gid -> {enter_time, zone, gender, age, camera_id}
        self.total_generated = 0

    async def run(self, interval: float = 2.0):
        logger.info(f"🚀 客流动态仿真器启动，事件频率: {interval}s")
        from backend.db.database import insert_flow_event

        while True:
            try:
                # 随机生成行为动作：70% 产生新进入/驻留，30% 离开
                action = random.choices(["enter_and_dwell", "leave"], weights=[0.7, 0.3])[0]

                if action == "enter_and_dwell" or len(self.active_visitors) < 3:
                    gid = f"G-{random.randint(1000, 9999)}"
                    gender = random.choice(GENDERS)
                    age = random.choices(AGE_GROUPS, weights=[0.1, 0.5, 0.3, 0.1])[0]
                    cam = random.choice(CAMERAS)
                    zone = random.choice(ZONES)

                    self.active_visitors[gid] = {
                        "enter_time": time.time(),
                        "gender": gender,
                        "age_group": age,
                        "camera_id": cam,
                        "roi_name": zone,
                    }
                    self.total_generated += 1

                    # 写入进入事件
                    event_data = {
                        "event_time": datetime.now(timezone.utc),
                        "event_type": "enter",
                        "global_id": gid,
                        "camera_id": cam,
                        "roi_name": zone,
                        "gender": gender,
                        "age_group": age,
                        "dwell_seconds": 0.0,
                    }
                    try:
                        await insert_flow_event(event_data)
                    except Exception as e:
                        logger.debug(f"模拟事件未入库 (数据库未连接): {e}")

                    logger.info(f"🚶 人员入场: [{gid}] {gender}/{age} 前往 {zone}")

                elif self.active_visitors:
                    # 随机选择一个在场人员完成驻留并离开
                    gid, info = random.choice(list(self.active_visitors.items()))
                    del self.active_visitors[gid]

                    dwell = round(random.uniform(5.0, 90.0), 1)

                    # 写入驻留完成事件
                    event_data = {
                        "event_time": datetime.now(timezone.utc),
                        "event_type": "dwell_complete",
                        "global_id": gid,
                        "camera_id": info["camera_id"],
                        "roi_name": info["roi_name"],
                        "gender": info["gender"],
                        "age_group": info["age_group"],
                        "dwell_seconds": dwell,
                    }
                    try:
                        await insert_flow_event(event_data)
                    except Exception:
                        pass

                    logger.info(f"⏱️ 展台驻留完成: [{gid}] 在 {info['roi_name']} 驻留 {dwell}s 并离场")

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"仿真异常: {e}")
                await asyncio.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="智慧展厅客流动态数据仿真器")
    parser.add_argument("--interval", type=float, default=2.0, help="事件生成间隔（秒）")
    args = parser.parse_args()

    simulator = FlowSimulator()
    try:
        asyncio.run(simulator.run(interval=args.interval))
    except KeyboardInterrupt:
        logger.info("🛑 仿真器已退出")
