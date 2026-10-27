# 🎯 Smart Flow Analytics

> 基于 AI 视觉的智慧展厅多路客流分析系统

[![CI](https://github.com/qiwenkai209-dot/smart-flow-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/qiwenkai209-dot/smart-flow-analytics/actions)
[![Docker](https://github.com/qiwenkai209-dot/smart-flow-analytics/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/qiwenkai209-dot/smart-flow-analytics/actions)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## ✨ 核心功能

- 📹 **摄像头私有协议与多路管理**：海康威视、大华、宇视私有协议一键合成，自动断线重连，支持 ONVIF 局域网设备自动发现
- 🎯 **分类功能实时算法叠加**：增添摄像头时支持勾选出入客流、男女性别、年龄分析、展台驻留，并在视频预览画面上根据深度学习模型算法实时叠加参数（警戒线、进出计数、属性标牌、驻留网格）
- 🏛️ **首页展厅功能与出入规划**：支持各展厅独立与全馆总览，配置入口与出口摄像头协同配合计算实时在场人数与今日累计接待人数，带饱和度态势仪表
- 📐 **划线圈出区域并固化**：在展台分析中拉取摄像头实时监控画面，交互划线圈出多边形监控区域并一键固化持久化
- 🧍 **人体检测与追踪**：YOLO11m + ByteTrack，高精度多目标追踪
- 🔁 **跨摄像头 Re-ID 去重**：FastReID 全局行人重识别，同一人不重复计数
- 📊 **大屏报表**：Vue3 + ECharts 实时态势大屏，支持 Excel/CSV 明细报表导出
- 🐳 **Docker 一键部署**：CPU 版（OpenVINO）+ GPU 版（CUDA）双镜像


## 🏗️ 系统架构

```
RTSP 流 ──> 取流引擎 ──> YOLO11m 检测 ──> ByteTrack 追踪
                                                │
                         Re-ID 全局去重 <────────┤
                                                │
                         PP-Human 属性识别 <─────┤
                                                │
                         多边形 ROI 驻留计时 <───┘
                                                │
                         FastAPI 后端 + TimescaleDB
                                                │
                         Vue3 大屏 / Excel 导出
```

## 🚀 快速开始

### 方式一：Windows 独立运行版（免环境配置，双击即用）

进入 [Releases](https://github.com/qiwenkai209-dot/smart-flow-analytics/releases) 页面，下载最新的 `SmartFlowAnalytics-Windows-x64.zip`：
1. 解压到任意目录；
2. 双击运行 `启动系统.bat`（正式接入摄像头）或 `启动系统(带客流仿真演示).bat`（离线动态演示模式）；
3. 系统将自动唤起默认浏览器并打开可视化智能分析大屏（`http://localhost:8000`）。

---

### 方式二：Docker 一键启动（推荐生产部署）

```bash
# CPU 版（基于 OpenVINO 加速，轻量运行）
docker-compose -f docker/docker-compose.yml up -d

# GPU 版（基于 NVIDIA CUDA 加速）
docker-compose -f docker/docker-compose.gpu.yml up -d
```

---

### 方式三：GitHub Codespaces 云端算力一键运行

无需本地配置，直接使用 GitHub 免费云端虚拟机算力（包含完整的 Python 3.10、Node.js 20、Docker 环境）：
1. 在仓库主页点击绿色的 **Code** 按钮，切换到 **Codespaces** 选项卡；
2. 点击 **Create codespace on main**；
3. 云端容器自动准备完毕后，端口 `8000`、`5173` 自动转发并在浏览器内弹窗直接体验！

---

### 方式四：本地源码开发

```bash
# 1. 克隆仓库
git clone https://github.com/qiwenkai209-dot/smart-flow-analytics.git
cd smart-flow-analytics

# 2. 安装 Python 依赖
pip install poetry
poetry install

# 3. 下载预训练模型
python models/download_models.py

# 4. 启动服务（单入口自适应前后端）
python run_server.py --demo

# 5. 运行全量自动化测试（28 项单元与集成测试）
pytest -v
```

---

## ⚡ 充分利用 GitHub 算力工作体系

本项目已深度接入 GitHub 云端计算生态：
1. **GitHub Actions 自动化 CI 守护（Ubuntu 算力）**：
   - 每次提交代码或提交 PR，GitHub 云端算力机自动触发 `ci.yml`，执行依赖检查、Ruff 代码规范检查、Mypy 类型校验以及全套 28 项自动化单元与集成测试。
2. **GitHub Actions 自动构建与发布（Windows 算力）**：
   - 当推送标签（如 `v1.0.0`）或在 Actions 页面点击“Run workflow”时，GitHub Windows 算力机将全自动完成前端 Vite 编译和 PyInstaller 独立打包，并自动将生成的 `SmartFlowAnalytics-Windows-x64.zip` 发布至 GitHub Releases 供用户下载。
3. **GitHub Container Registry 镜像自动编译（Docker 云算力）**：
   - 自动编译包含 OpenVINO 和 CUDA 的 CPU/GPU 镜像，推送至 `ghcr.io`，免除在本地机器拉取庞大 CUDA 镜像与编译的资源消耗。
4. **GitHub 云端 Benchmark 自动基准评测**：
   - 定时使用云端算力对 YOLO11 和 ReID 特征提取进行推理时延和 FPS 压测，并将报告自动更新部署至 GitHub Pages。

## ⚙️ 摄像头配置示例

```yaml
cameras:
  - id: cam_001
    name: "展厅入口"
    rtsp_url: "rtsp://admin:password@192.168.1.100:554/stream1"
    brand: generic   # generic | hikvision | dahua | uniview
    fps_limit: 10    # 抽帧率（省算力）
    rois:
      - name: "展台A"
        polygon: [[100, 200], [300, 200], [300, 400], [100, 400]]
        min_dwell_seconds: 5
```

## 📂 项目结构

```
smart-flow-analytics/
├── core/          # 核心算法引擎
├── backend/       # FastAPI 后端
├── frontend/      # Vue3 大屏前端
├── models/        # 模型下载与管理
├── benchmark/     # 模型评估套件
├── docker/        # Docker 镜像与编排
├── configs/       # 系统配置文件
├── tests/         # 单元 & 集成测试
└── docs/          # 文档
```

## 🔬 模型说明

| 任务 | 模型 | License |
|------|------|---------|
| 人体检测 | YOLO11m | AGPL-3.0 |
| 多目标追踪 | ByteTrack | MIT |
| 全身属性 | PP-Human PULC | Apache-2.0 |
| 跨镜 Re-ID | FastReID | Apache-2.0 |
| 视频底座(CPU) | OpenVINO | Apache-2.0 |

## 📄 License

Apache License 2.0 — 详见 [LICENSE](LICENSE)
