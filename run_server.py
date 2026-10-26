"""
Smart Flow Analytics —— 系统独立运行主程序
用于打包 Windows 独立可执行软件（.exe）或便携版绿色启动。
"""
import os
import sys
import time
import argparse
import webbrowser
import threading
import uvicorn
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("Launcher")


def open_browser_delayed(url: str, delay: float = 1.2):
    """延迟自动打开默认浏览器访问大屏"""
    time.sleep(delay)
    try:
        logger.info(f"🌐 正在打开浏览器访问: {url}")
        webbrowser.open(url)
    except Exception as e:
        logger.warning(f"自动打开浏览器失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="Smart Flow Analytics 智慧展厅客流分析平台")
    parser.add_argument("--host", default="0.0.0.0", help="服务监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="服务端口 (默认: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="启动时不自动打开浏览器")
    parser.add_argument("--demo", action="store_true", help="启动时同时开启动态客流仿真演示器")
    args = parser.parse_args()

    # 处理打包后的路径
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        os.chdir(os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # 导入 FastAPI app
    from backend.main import app

    display_url = f"http://localhost:{args.port}"
    logger.info("=" * 60)
    logger.info("  🎯 Smart Flow Analytics 智慧展厅多路客流分析系统")
    logger.info(f"  🚀 服务已就绪: {display_url}")
    logger.info(f"  📖 API 接口文档: {display_url}/docs")
    logger.info("=" * 60)

    # 自动打开浏览器
    if not args.no_browser:
        threading.Thread(target=open_browser_delayed, args=(display_url,), daemon=True).start()

    # 可选：后台启动动态仿真器
    if args.demo:
        def start_simulator():
            import asyncio
            from scripts.demo_simulator import FlowSimulator
            sim = FlowSimulator()
            try:
                asyncio.run(sim.run(interval=2.0))
            except Exception as e:
                logger.debug(f"模拟器退出: {e}")

        threading.Thread(target=start_simulator, daemon=True).start()
        logger.info("✨ 动态客流仿真模拟器已在后台启动！")

    # 启动 Uvicorn 服务器
    config = uvicorn.Config(
        app=app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
