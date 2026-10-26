# 🎯 Smart Flow Analytics

> 基于 AI 视觉的智慧展厅多路客流分析系统

[![CI](https://github.com/qiwenkai209-dot/smart-flow-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/qiwenkai209-dot/smart-flow-analytics/actions)
[![Docker](https://github.com/qiwenkai209-dot/smart-flow-analytics/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/qiwenkai209-dot/smart-flow-analytics/actions)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## ✨ 核心功能

- 📹 **多路 RTSP 摄像头**：动态增减摄像头，自动断线重连，支持通用 RTSP 及私有流格式适配
- 🧍 **人体检测与追踪**：YOLO11m + ByteTrack，高精度多目标追踪
- 🔁 **跨摄像头 Re-ID 去重**：FastReID 全局行人重识别，同一人不重复计数
- 👥 **全身属性识别**：性别（男/女）、年龄段（儿童/青年/中年/老年），无需人脸正面
- 📐 **多边形 ROI 分析**：自定义展台区域，精准驻留时长统计
- 🔌 **NVR 打通**：ONVIF 标准协议对接主流 NVR 录像系统
- 📊 **大屏报表**：Vue3 + ECharts 实时看板，支持 Excel/CSV 导出
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

### 方式一：Docker 一键启动（推荐）

```bash
# CPU 版
docker-compose -f docker/docker-compose.yml up -d

# GPU 版
docker-compose -f docker/docker-compose.gpu.yml up -d
```

访问 `http://localhost:5173` 查看大屏

### 方式二：本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/qiwenkai209-dot/smart-flow-analytics.git
cd smart-flow-analytics

# 2. 安装 Python 依赖
pip install poetry
poetry install

# 3. 下载预训练模型
python models/download_models.py

# 4. 配置摄像头
cp configs/cameras.example.yaml configs/cameras.yaml
# 编辑 cameras.yaml 填入你的 RTSP 地址

# 5. 启动后端
uvicorn backend.main:app --reload

# 6. 启动前端（新终端）
cd frontend && npm install && npm run dev
```

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
