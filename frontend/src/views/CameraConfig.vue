<template>
  <div class="cam-page">
    <!-- 顶部标题与多标签导航 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">⚙️ 系统配置中心</h1>
        <div class="page-desc">
          摄像头管理 · 物联网设备探头接入 (UDP/TCP/串口/HTTP) · 全局视频分析算法配置
        </div>
      </div>
      <div class="header-right">
        <div class="subnav-tabs">
          <button
            class="subnav-btn"
            :class="{ active: currentTab === 'cameras' }"
            @click="currentTab = 'cameras'"
          >
            📹 摄像头管理
          </button>
          <button
            class="subnav-btn"
            :class="{ active: currentTab === 'devices' }"
            @click="currentTab = 'devices'"
          >
            🌡️ 设备添加 (温湿度探头)
          </button>
          <button
            class="subnav-btn"
            :class="{ active: currentTab === 'analysis' }"
            @click="currentTab = 'analysis'"
          >
            🧠 视频分析配置
          </button>
        </div>
      </div>
    </div>

    <!-- ── 选项卡 1：摄像头管理 ────────────────────────────── -->
    <div v-if="currentTab === 'cameras'" class="tab-content">
      <!-- 顶部操作条：只保留这一个新增摄像头按钮 -->
      <div class="filter-action-bar mb-14 flex-between">
        <div class="flex-align-center gap-8">
          <span class="text-sm text-dim">已接入摄像头: <b>{{ cameras.length }}</b> 路</span>
        </div>
        <button class="btn btn-primary" @click="openAddModal">
          ➕ 新增摄像头
        </button>
      </div>

      <!-- ONVIF 扫描面板 -->
      <div class="card onvif-top-card mb-16">
        <div class="onvif-top-bar flex-between">
          <div class="flex-align-center gap-12 flex-wrap">
            <span class="onvif-title-label">🔍 ONVIF 自动发现:</span>
            <div class="flex-align-center gap-6">
              <span class="sub-label">用户名:</span>
              <input
                v-model="onvifCredentials.username"
                class="input input-sm"
                style="width: 100px"
                placeholder="admin"
              />
            </div>
            <div class="flex-align-center gap-6">
              <span class="sub-label">密码:</span>
              <input
                type="password"
                v-model="onvifCredentials.password"
                class="input input-sm"
                style="width: 120px"
                placeholder="设备密码"
              />
            </div>
            <button
              class="btn btn-secondary btn-sm"
              @click="startOnvifScan"
              :disabled="scanning"
            >
              {{ scanning ? '正在全网段扫描...' : '开始扫描局域网' }}
            </button>
          </div>

          <div v-if="onvifDevices.length" class="flex-align-center gap-8">
            <span class="badge badge-info">已发现 {{ onvifDevices.length }} 台设备</span>
            <button class="btn btn-ghost btn-xs fold-toggle-btn" @click="isFolded = !isFolded">
              {{ isFolded ? '▶ 展开结果列表' : '▼ 折叠结果' }}
            </button>
          </div>
        </div>

        <div v-if="onvifDevices.length && !isFolded" class="onvif-results-body mt-12">
          <div class="onvif-device-grid">
            <div class="card onvif-item-card" v-for="(dev, idx) in onvifDevices" :key="idx">
              <div class="flex-between">
                <span class="dev-name">{{ dev.name || '网络监控摄像机' }}</span>
                <span class="badge badge-online">{{ dev.manufacturer || 'ONVIF' }}</span>
              </div>
              <div class="dev-meta mt-6">IP: {{ dev.ip || dev.address }}</div>
              <div class="card-footer mt-10">
                <button class="btn btn-primary btn-xs flex-1" @click="importOnvifDevice(dev)">
                  一键导入此设备
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 摄像头列表网格（只展示摄像头卡片，已移除末尾重复占位卡片） -->
      <div class="cam-grid">
        <div class="card cam-card" v-for="cam in cameras" :key="cam.id">
          <div class="flex-between mb-10">
            <div>
              <div class="cam-card-name">{{ cam.name }}</div>
              <div class="cam-card-sub">ID: {{ cam.id }} · {{ formatBrand(cam.brand) }}</div>
            </div>
            <span class="badge" :class="cam.connected ? 'badge-online' : 'badge-offline'">
              {{ cam.connected ? '● 在线' : '○ 待机' }}
            </span>
          </div>

          <div class="cam-kpis mb-10">
            <div class="cam-kpi-item">
              <div class="cam-kpi-num">{{ cam.fps_actual || 10 }}</div>
              <div class="cam-kpi-lbl">帧率 FPS</div>
            </div>
            <div class="cam-kpi-item">
              <div class="cam-kpi-num" style="font-size: 13px">{{ cam.resolution || '1080P' }}</div>
              <div class="cam-kpi-lbl">清晰度</div>
            </div>
          </div>

          <div class="rtsp-badge-box mb-12" :title="cam.rtsp_url">
            {{ cam.rtsp_url || '未配置 RTSP' }}
          </div>

          <div class="assigned-roles-box mb-12">
            <span class="roles-label">业务定义: </span>
            <span class="roles-desc">{{ getCameraRoleDesc(cam.id) }}</span>
          </div>

          <div class="card-footer">
            <button class="btn btn-primary btn-sm flex-1" @click="viewLiveSnapshot(cam)">
              👁️ 查看实时画面
            </button>
            <button class="btn btn-secondary btn-sm" @click="openEditModal(cam)">
              ✏️ 修改
            </button>
            <button class="btn btn-danger btn-sm" @click="removeCamera(cam.id)">
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 选项卡 2：新增设备添加（温湿度探头接入） ────────────── -->
    <div v-if="currentTab === 'devices'" class="tab-content">
      <div class="filter-action-bar mb-14 flex-between">
        <div>
          <span class="text-sm text-dim">
            接入环境传感器与温湿度探头，支持 <b>UDP、TCP、串口 (COM/RS485)、HTTP</b> 等通讯协议，实时数据直供首页展馆温湿度模块
          </span>
        </div>
        <button class="btn btn-primary" @click="openAddDeviceModal">
          ➕ 接入环境设备 (温湿度探头)
        </button>
      </div>

      <div class="device-grid">
        <div class="card device-card" v-for="dev in devicesList" :key="dev.id">
          <div class="flex-between mb-8">
            <div class="dev-title-row">
              <span class="sensor-icon">🌡️</span>
              <span class="dev-name-text">{{ dev.name }}</span>
            </div>
            <span class="badge" :class="dev.status === 'online' ? 'badge-online' : 'badge-offline'">
              {{ dev.status === 'online' ? '● 探头在线' : '○ 探头离线' }}
            </span>
          </div>

          <!-- 通讯协议标识 -->
          <div class="protocol-bar mb-10">
            <span class="protocol-badge" :class="'proto-' + dev.protocol">
              {{ dev.protocol.toUpperCase() }} 通讯
            </span>
            <span class="protocol-detail-text">
              <template v-if="dev.protocol === 'serial'">串口: {{ dev.serial_port }} ({{ dev.baudrate }}bps)</template>
              <template v-else-if="dev.protocol === 'http'">HTTP: {{ dev.http_url || (dev.ip + ':' + dev.port) }}</template>
              <template v-else>{{ dev.protocol.toUpperCase() }}://{{ dev.ip }}:{{ dev.port }}</template>
            </span>
          </div>

          <!-- 实时监测数据指标 -->
          <div class="sensor-readings-row mb-12">
            <div class="reading-box temp">
              <div class="reading-lbl">室内温度</div>
              <div class="reading-val font-mono">{{ dev.temperature }}<small>°C</small></div>
            </div>
            <div class="reading-box hum">
              <div class="reading-lbl">室内湿度</div>
              <div class="reading-val font-mono">{{ dev.humidity }}<small>%RH</small></div>
            </div>
            <div class="reading-box co2">
              <div class="reading-lbl">CO₂ 浓度</div>
              <div class="reading-val font-mono">{{ dev.co2 || 510 }}<small>ppm</small></div>
            </div>
          </div>

          <div class="reading-footer-row mb-12">
            <span>最后遥测更新: <b class="font-mono text-dim">{{ dev.last_updated || '刚刚' }}</b></span>
          </div>

          <div class="card-footer">
            <button class="btn btn-primary btn-sm flex-1" @click="testPollDevice(dev)">
              ⚡ 测试通讯拉取
            </button>
            <button class="btn btn-secondary btn-sm" @click="openEditDeviceModal(dev)">
              ✏️ 配置
            </button>
            <button class="btn btn-danger btn-sm" @click="deleteDevice(dev.id)">
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 选项卡 3：视频分析配置接口 ────────────────────────── -->
    <div v-if="currentTab === 'analysis'" class="tab-content">
      <div class="card analysis-config-card">
        <div class="panel-header mb-16">
          <span class="panel-title">🧠 全局视频分析算法与推理参数配置</span>
        </div>

        <div class="form-grid-2 mb-16">
          <div class="form-group">
            <label class="form-label">目标检测模型 (ONNX / OpenVINO)</label>
            <input v-model="analysisConfig.model_name" class="input" placeholder="yolov8n-flow.onnx" />
            <div class="form-hint">轻量化客流检测权重，兼顾高帧率与高精度</div>
          </div>

          <div class="form-group">
            <label class="form-label">推理硬件加速引擎</label>
            <select v-model="analysisConfig.enable_gpu_accel" class="input">
              <option :value="false">CPU 高效线程池多核推理 (默认兼容所有机器)</option>
              <option :value="true">OpenVINO / NVIDIA CUDA GPU 硬件加速</option>
            </select>
          </div>
        </div>

        <div class="form-grid-3 mb-16">
          <div class="form-group">
            <label class="form-label">目标检测置信度阈值 (Conf Threshold)</label>
            <input
              type="number"
              step="0.05"
              min="0.1"
              max="0.9"
              v-model.number="analysisConfig.conf_threshold"
              class="input font-mono"
            />
            <div class="form-hint">数值越大误检越少，推荐 0.40 - 0.55</div>
          </div>

          <div class="form-group">
            <label class="form-label">NMS IOU 抑制重叠阈值</label>
            <input
              type="number"
              step="0.05"
              min="0.1"
              max="0.9"
              v-model.number="analysisConfig.iou_threshold"
              class="input font-mono"
            />
            <div class="form-hint">密集人群防重复计数，推荐 0.45 - 0.60</div>
          </div>

          <div class="form-group">
            <label class="form-label">推理跳帧优化 (Skip Frames)</label>
            <select v-model.number="analysisConfig.skip_frames" class="input">
              <option :value="0">0 (每帧均推理，超高清低延迟)</option>
              <option :value="1">1 (隔1帧推理+光流跟踪，降低CPU消耗)</option>
              <option :value="2">2 (隔2帧推理，极限低配模式)</option>
            </select>
          </div>
        </div>

        <div class="form-grid-2 mb-20">
          <div class="form-group">
            <label class="form-label">跨镜头 ReID 关联跟踪</label>
            <select v-model="analysisConfig.enable_reid" class="input">
              <option :value="true">启用 (智能识别重复进出与跨展厅流转)</option>
              <option :value="false">禁用 (仅单镜头独立计数)</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">展台驻留最少起计时间 (秒)</label>
            <input
              type="number"
              min="1"
              max="60"
              v-model.number="analysisConfig.min_dwell_seconds"
              class="input font-mono"
            />
            <div class="form-hint">人在展台内驻留停留超过此时长方纳入有效统计</div>
          </div>
        </div>

        <div class="card-footer flex-gap-12 justify-end">
          <button class="btn btn-secondary" @click="resetAnalysisConfig">
            🔄 恢复推荐默认值
          </button>
          <button class="btn btn-primary" @click="saveAnalysisConfig" :disabled="analysisSaving">
            {{ analysisSaving ? '保存中...' : '💾 保存视频分析算法参数' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 模态框 1：摄像头添加与修改 ────────────────────────── -->
    <div class="modal-overlay" v-if="showModal" @click.self="showModal = false">
      <div class="modal card modal-wide">
        <div class="flex-between mb-16">
          <div class="modal-title">{{ isEdit ? '✏️ 修改摄像头配置' : '➕ 新增摄像头 (默认 RTSP)' }}</div>
          <button class="close-btn" @click="showModal = false">✕</button>
        </div>

        <div class="modal-two-columns">
          <div class="form-column">
            <div class="form-group mb-12">
              <label class="form-label">摄像头唯一标识 (ID) *</label>
              <input v-model="form.id" class="input" :disabled="isEdit" placeholder="例如: cam_004" />
            </div>

            <div class="form-group mb-12">
              <label class="form-label">摄像头名称 *</label>
              <input v-model="form.name" class="input" placeholder="例如: 主入口南门监控" />
            </div>

            <div class="form-group mb-12">
              <label class="form-label">接入协议 / 品牌 *</label>
              <select v-model="form.brand" class="input" @change="onBrandChange">
                <option value="generic">标准 RTSP 视频流直连 (推荐 · 默认)</option>
                <option value="hikvision">海康威视 (按 IP/账号拼装)</option>
                <option value="dahua">大华股份 (按 IP/账号拼装)</option>
                <option value="uniview">宇视科技 (按 IP/账号拼装)</option>
              </select>
            </div>

            <div class="form-group mb-12" v-if="form.brand === 'generic'">
              <label class="form-label">完整 RTSP 视频流地址 *</label>
              <input
                v-model="form.rtsp_url"
                class="input"
                placeholder="rtsp://admin:password@192.168.1.100:554/live/ch1"
              />
            </div>

            <template v-else>
              <div class="form-grid-2 mb-10">
                <div class="form-group">
                  <label class="form-label">设备 IP 地址 *</label>
                  <input v-model="form.ip" class="input" placeholder="192.168.1.64" @input="updateSynthesizedUrl" />
                </div>
                <div class="form-group">
                  <label class="form-label">端口</label>
                  <input v-model.number="form.port" type="number" class="input" placeholder="554" @input="updateSynthesizedUrl" />
                </div>
              </div>
              <div class="form-grid-2 mb-10">
                <div class="form-group">
                  <label class="form-label">用户名</label>
                  <input v-model="form.username" class="input" placeholder="admin" @input="updateSynthesizedUrl" />
                </div>
                <div class="form-group">
                  <label class="form-label">密码</label>
                  <input type="password" v-model="form.password" class="input" placeholder="设备密码" @input="updateSynthesizedUrl" />
                </div>
              </div>
              <div class="synthesized-box mb-12">
                <span>生成地址: </span>
                <code>{{ form.rtsp_url || '请填写参数自动生成' }}</code>
              </div>
            </template>

            <div class="flex-gap-8 mt-14">
              <button class="btn btn-secondary flex-1" @click="testAndFetchPreview" :disabled="previewLoading">
                {{ previewLoading ? '拉取画面中...' : '📹 测试拉流并预览画面' }}
              </button>
            </div>
          </div>

          <div class="preview-column">
            <div class="preview-header flex-between mb-8">
              <span class="preview-title">画面即时预览</span>
              <span class="badge badge-info" v-if="previewBase64">
                {{ isRealStream ? '● 真实摄像头拉流' : '⚡ 信号连通' }}
              </span>
            </div>

            <div class="preview-viewport">
              <img
                v-if="previewBase64"
                :src="'data:image/jpeg;base64,' + previewBase64"
                class="viewport-img"
                alt="摄像头画面预览"
              />
              <div v-else class="viewport-placeholder">
                <div class="placeholder-cam-icon">📹</div>
                <div class="placeholder-tip">点击左侧「测试拉流并预览画面」检验连通性</div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer flex-gap-8 mt-16 justify-end">
          <button class="btn btn-secondary" @click="showModal = false">取消</button>
          <button class="btn btn-primary" @click="saveCamera">
            {{ isEdit ? '💾 保存配置' : '✅ 确认添加摄像头' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 模态框 2：设备添加与修改 (温湿度探头) ─────────────── -->
    <div class="modal-overlay" v-if="showDeviceModal" @click.self="showDeviceModal = false">
      <div class="modal card modal-medium">
        <div class="flex-between mb-16">
          <div class="modal-title">{{ isDeviceEdit ? '✏️ 修改环境探头配置' : '➕ 接入环境设备 (温湿度探头)' }}</div>
          <button class="close-btn" @click="showDeviceModal = false">✕</button>
        </div>

        <div class="form-group mb-12">
          <label class="form-label">设备名称 *</label>
          <input v-model="deviceForm.name" class="input" placeholder="例如: 1号展厅中心温湿度探头" />
        </div>

        <div class="form-group mb-12">
          <label class="form-label">设备类型 *</label>
          <select v-model="deviceForm.type" class="input">
            <option value="temperature_humidity">温湿度传感器探头</option>
            <option value="air_quality">多合一空气质量与温湿度采集仪</option>
          </select>
        </div>

        <!-- 通讯协议选择（支持 UDP、TCP、串口、HTTP） -->
        <div class="form-group mb-12">
          <label class="form-label">通讯协议 *</label>
          <select v-model="deviceForm.protocol" class="input">
            <option value="tcp">TCP 客户端/服务端协议</option>
            <option value="udp">UDP 广播与数据报协议</option>
            <option value="serial">串口协议 (COM / RS485 / Modbus RTU)</option>
            <option value="http">HTTP Webhook / 定时轮询接口</option>
          </select>
        </div>

        <!-- 根据协议展示不同的配置输入项 -->
        <template v-if="deviceForm.protocol === 'tcp' || deviceForm.protocol === 'udp'">
          <div class="form-grid-2 mb-12">
            <div class="form-group">
              <label class="form-label">设备 IP 地址 *</label>
              <input v-model="deviceForm.ip" class="input" placeholder="192.168.1.150" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ deviceForm.protocol.toUpperCase() }} 端口 *</label>
              <input v-model.number="deviceForm.port" type="number" class="input" placeholder="5002" />
            </div>
          </div>
        </template>

        <template v-else-if="deviceForm.protocol === 'serial'">
          <div class="form-grid-2 mb-12">
            <div class="form-group">
              <label class="form-label">串口号 (COM / Device) *</label>
              <input v-model="deviceForm.serial_port" class="input" placeholder="COM1 或 /dev/ttyUSB0" />
            </div>
            <div class="form-group">
              <label class="form-label">波特率 (Baudrate) *</label>
              <select v-model.number="deviceForm.baudrate" class="input">
                <option :value="9600">9600 bps (常用推荐)</option>
                <option :value="19200">19200 bps</option>
                <option :value="115200">115200 bps</option>
              </select>
            </div>
          </div>
        </template>

        <template v-else-if="deviceForm.protocol === 'http'">
          <div class="form-group mb-12">
            <label class="form-label">HTTP 采集接口 URL *</label>
            <input v-model="deviceForm.http_url" class="input" placeholder="http://192.168.1.150/api/sensor/metrics" />
          </div>
        </template>

        <div class="form-group mb-16">
          <label class="form-label">采集轮询间隔 (秒)</label>
          <input v-model.number="deviceForm.poll_interval" type="number" min="1" max="60" class="input" />
        </div>

        <div class="modal-footer flex-gap-8 mt-16 justify-end">
          <button class="btn btn-secondary" @click="showDeviceModal = false">取消</button>
          <button class="btn btn-primary" @click="saveDevice">
            {{ isDeviceEdit ? '💾 保存配置' : '✅ 确认接入设备' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 快照模态框 -->
    <div class="modal-overlay" v-if="showSnapshotModal" @click.self="showSnapshotModal = false">
      <div class="modal card modal-medium">
        <div class="flex-between mb-12">
          <div class="modal-title">👁️ 实时画面快照 - {{ snapshotTarget?.name }}</div>
          <button class="close-btn" @click="showSnapshotModal = false">✕</button>
        </div>
        <div class="snapshot-box">
          <img v-if="snapshotImg" :src="snapshotImg" class="snapshot-view" alt="实时快照" />
          <div v-else class="snapshot-loading">
            <div class="spinner"></div>
            <span>正在截取视频帧...</span>
          </div>
        </div>
        <div class="flex-gap-8 mt-12 justify-end">
          <button class="btn btn-secondary" @click="showSnapshotModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || ''

const currentTab = ref('cameras')

// ── 摄像头相关状态 ──────────────────────────────────────────
const cameras = ref([])
const showModal = ref(false)
const isEdit = ref(false)

const onvifCredentials = reactive({
  username: 'admin',
  password: '',
})
const scanning = ref(false)
const isFolded = ref(false)
const onvifDevices = ref([])

const form = ref({
  id: '',
  name: '',
  brand: 'generic',
  rtsp_url: '',
  ip: '',
  port: 554,
  username: 'admin',
  password: '',
  channel: 1,
  subtype: 0,
  fps_limit: 10,
  features: [],
  rois: [],
})

const previewLoading = ref(false)
const previewBase64 = ref(null)
const isRealStream = ref(false)

const showSnapshotModal = ref(false)
const snapshotTarget = ref(null)
const snapshotImg = ref(null)

const assignedVenues = ref([])
const assignedZones = ref([])

// ── 设备管理相关状态 ────────────────────────────────────────
const devicesList = ref([])
const showDeviceModal = ref(false)
const isDeviceEdit = ref(false)
const deviceForm = ref({
  id: '',
  name: '',
  type: 'temperature_humidity',
  protocol: 'tcp',
  ip: '192.168.1.150',
  port: 5002,
  serial_port: 'COM1',
  baudrate: 9600,
  http_url: '',
  poll_interval: 5,
})

// ── 视频分析配置相关状态 ────────────────────────────────────
const analysisConfig = ref({
  model_name: 'yolov8n-flow.onnx',
  conf_threshold: 0.45,
  iou_threshold: 0.50,
  skip_frames: 1,
  enable_reid: true,
  reid_max_age: 30,
  min_dwell_seconds: 5.0,
  enable_gpu_accel: false,
})
const analysisSaving = ref(false)

function formatBrand(b) {
  const map = {
    generic: '标准 RTSP',
    hikvision: '海康威视',
    dahua: '大华股份',
    uniview: '宇视科技',
  }
  return map[b] || 'RTSP'
}

function getCameraRoleDesc(id) {
  const inRoles = []
  assignedVenues.value.forEach(v => {
    if ((v.entry_cameras || []).includes(id)) inRoles.push(`${v.name}(进)`)
    if ((v.exit_cameras || []).includes(id)) inRoles.push(`${v.name}(出)`)
  })
  assignedZones.value.forEach(z => {
    if (z.camera_id === id) inRoles.push(`展台[${z.name}]`)
  })
  return inRoles.length ? inRoles.join(' · ') : '待规划绑定'
}

async function loadCameras() {
  try {
    const res = await axios.get(`${API}/api/cameras/`)
    cameras.value = res.data || []
  } catch {
    cameras.value = []
  }
  try {
    const vRes = await axios.get(`${API}/api/analytics/venues`)
    assignedVenues.value = vRes.data || []
  } catch {
    assignedVenues.value = []
  }
  try {
    const zRes = await axios.get(`${API}/api/cameras/rois/all`)
    assignedZones.value = zRes.data || []
  } catch {
    assignedZones.value = []
  }
}

async function loadDevices() {
  try {
    const res = await axios.get(`${API}/api/devices/`)
    devicesList.value = res.data || []
  } catch {
    devicesList.value = []
  }
}

async function loadAnalysisConfig() {
  try {
    const res = await axios.get(`${API}/api/devices/analysis-config`)
    if (res.data) {
      analysisConfig.value = { ...analysisConfig.value, ...res.data }
    }
  } catch {}
}

function onBrandChange() {
  if (form.value.brand !== 'generic') {
    updateSynthesizedUrl()
  }
}

function updateSynthesizedUrl() {
  const f = form.value
  const user = f.username || 'admin'
  const pass = f.password ? `:${f.password}` : ''
  const ip = f.ip || '192.168.1.64'
  const port = f.port || 554

  if (f.brand === 'hikvision') {
    f.rtsp_url = `rtsp://${user}${pass}@${ip}:${port}/Streaming/Channels/${f.channel || 1}0${f.subtype || 1}`
  } else if (f.brand === 'dahua') {
    f.rtsp_url = `rtsp://${user}${pass}@${ip}:${port}/cam/realmonitor?channel=${f.channel || 1}&subtype=${f.subtype || 0}`
  } else if (f.brand === 'uniview') {
    f.rtsp_url = `rtsp://${user}${pass}@${ip}:${port}/unicast/c${f.channel || 1}/s${f.subtype || 0}/live`
  }
}

function openAddModal() {
  isEdit.value = false
  form.value = {
    id: `cam_${String(cameras.value.length + 1).padStart(3, '0')}`,
    name: '',
    brand: 'generic',
    rtsp_url: '',
    ip: '',
    port: 554,
    username: 'admin',
    password: '',
    channel: 1,
    subtype: 0,
    fps_limit: 10,
    features: [],
    rois: [],
  }
  previewBase64.value = null
  showModal.value = true
}

function openEditModal(cam) {
  isEdit.value = true
  form.value = { ...cam }
  previewBase64.value = null
  showModal.value = true
}

async function testAndFetchPreview() {
  if (!form.value.rtsp_url && !form.value.ip) {
    alert('请提供完整 RTSP 地址或 IP 参数')
    return
  }
  previewLoading.value = true
  try {
    const res = await axios.post(`${API}/api/cameras/preview-analyze`, {
      camera_id: form.value.id,
      name: form.value.name || '摄像头预览',
      brand: form.value.brand,
      rtsp_url: form.value.rtsp_url,
      ip: form.value.ip,
      port: form.value.port,
      username: form.value.username,
      password: form.value.password,
      channel: form.value.channel,
      subtype: form.value.subtype,
      features: ['dwell'],
      rois: [],
    })
    if (res.data && res.data.preview_base64) {
      previewBase64.value = res.data.preview_base64
      isRealStream.value = !!res.data.is_real_stream
    }
  } catch (err) {
    alert(`测试拉流失败: ${err.message || '网络连接异常'}`)
  } finally {
    previewLoading.value = false
  }
}

async function saveCamera() {
  if (!form.value.id.trim() || !form.value.name.trim()) {
    alert('请填写完整摄像头 ID 与名称')
    return
  }
  try {
    if (isEdit.value) {
      await axios.put(`${API}/api/cameras/${form.value.id}`, form.value)
    } else {
      await axios.post(`${API}/api/cameras/`, form.value)
    }
    showModal.value = false
    await loadCameras()
  } catch (err) {
    alert(`保存失败: ${err.response?.data?.detail || err.message}`)
  }
}

async function removeCamera(id) {
  if (!confirm(`确定要移除摄像头 [${id}] 吗？`)) return
  try {
    await axios.delete(`${API}/api/cameras/${id}`)
    await loadCameras()
  } catch (err) {
    alert(`删除失败: ${err.message}`)
  }
}

async function viewLiveSnapshot(cam) {
  snapshotTarget.value = cam
  snapshotImg.value = null
  showSnapshotModal.value = true
  try {
    const res = await axios.post(`${API}/api/cameras/preview-analyze`, {
      camera_id: cam.id,
      name: cam.name,
      rtsp_url: cam.rtsp_url,
      features: ['dwell'],
    })
    if (res.data && res.data.preview_base64) {
      snapshotImg.value = `data:image/jpeg;base64,${res.data.preview_base64}`
    }
  } catch {}
}

async function startOnvifScan() {
  scanning.value = true
  onvifDevices.value = []
  try {
    const res = await axios.post(`${API}/api/onvif/scan`, {
      username: onvifCredentials.username || 'admin',
      password: onvifCredentials.password || '',
      timeout: 3,
    })
    onvifDevices.value = res.data?.devices || []
    isFolded.value = false
  } catch (err) {
    alert(`扫描异常: ${err.message}`)
  } finally {
    scanning.value = false
  }
}

function importOnvifDevice(dev) {
  isEdit.value = false
  form.value = {
    id: `cam_${String(cameras.value.length + 1).padStart(3, '0')}`,
    name: dev.name || 'ONVIF 网络摄像头',
    brand: 'generic',
    rtsp_url: dev.stream_uri || '',
    ip: dev.ip || '',
    port: dev.port || 554,
    username: onvifCredentials.username || 'admin',
    password: onvifCredentials.password || '',
    channel: 1,
    subtype: 0,
    fps_limit: 10,
    features: [],
    rois: [],
  }
  showModal.value = true
}

// ── 设备操作函数 ────────────────────────────────────────────
function openAddDeviceModal() {
  isDeviceEdit.value = false
  deviceForm.value = {
    id: `sensor_${Date.now().toString().slice(-4)}`,
    name: '',
    type: 'temperature_humidity',
    protocol: 'tcp',
    ip: '192.168.1.150',
    port: 5002,
    serial_port: 'COM1',
    baudrate: 9600,
    http_url: '',
    poll_interval: 5,
  }
  showDeviceModal.value = true
}

function openEditDeviceModal(dev) {
  isDeviceEdit.value = true
  deviceForm.value = { ...dev }
  showDeviceModal.value = true
}

async function saveDevice() {
  if (!deviceForm.value.name.trim()) {
    alert('请输入设备名称')
    return
  }
  try {
    await axios.post(`${API}/api/devices/`, deviceForm.value)
    showDeviceModal.value = false
    await loadDevices()
  } catch (err) {
    alert(`保存设备失败: ${err.message || '网络异常'}`)
  }
}

async function deleteDevice(devId) {
  if (!confirm('确定要移除此设备吗？')) return
  try {
    await axios.delete(`${API}/api/devices/${devId}`)
    await loadDevices()
  } catch (err) {
    alert(`删除设备失败: ${err.message}`)
  }
}

async function testPollDevice(dev) {
  try {
    const res = await axios.post(`${API}/api/devices/test-poll/${dev.id}`)
    if (res.data && res.data.success) {
      alert(`✅ [${res.data.protocol.toUpperCase()}] 通讯握手成功！\n实时温度: ${res.data.data.temperature}°C\n实时湿度: ${res.data.data.humidity}%\nCO₂: ${res.data.data.co2} ppm`)
      await loadDevices()
    }
  } catch (err) {
    alert(`测试失败: ${err.message || '设备响应超时'}`)
  }
}

// ── 视频分析配置操作函数 ────────────────────────────────────
async function saveAnalysisConfig() {
  analysisSaving.value = true
  try {
    await axios.post(`${API}/api/devices/analysis-config`, analysisConfig.value)
    alert('✅ 视频分析算法参数已保存并即时生效！')
  } catch (err) {
    alert(`保存失败: ${err.message}`)
  } finally {
    analysisSaving.value = false
  }
}

function resetAnalysisConfig() {
  analysisConfig.value = {
    model_name: 'yolov8n-flow.onnx',
    conf_threshold: 0.45,
    iou_threshold: 0.50,
    skip_frames: 1,
    enable_reid: true,
    reid_max_age: 30,
    min_dwell_seconds: 5.0,
    enable_gpu_accel: false,
  }
}

onMounted(() => {
  loadCameras()
  loadDevices()
  loadAnalysisConfig()
})
</script>

<style scoped>
.cam-page {
  padding: 16px 22px;
  height: 100%;
  overflow-y: auto;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
  margin: 0;
}
.page-desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.subnav-tabs {
  display: flex;
  gap: 6px;
  background: rgba(15, 23, 42, 0.6);
  padding: 4px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.subnav-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.subnav-btn.active {
  background: #00b4ff;
  color: #030712;
  font-weight: 700;
}

.filter-action-bar {
  display: flex;
  align-items: center;
}

.card {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(0, 180, 255, 0.18);
  border-radius: 12px;
  padding: 16px;
  backdrop-filter: blur(8px);
}

/* ── 摄像头网格 ────────────────────────────── */
.cam-grid, .device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.cam-card-name, .dev-name-text {
  font-size: 15px;
  font-weight: 700;
  color: #00b4ff;
}
.cam-card-sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.cam-kpis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.cam-kpi-item {
  background: rgba(30, 41, 59, 0.5);
  padding: 8px;
  border-radius: 6px;
  text-align: center;
}
.cam-kpi-num {
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
}
.cam-kpi-lbl {
  font-size: 10px;
  color: #64748b;
}

.rtsp-badge-box {
  background: rgba(10, 18, 32, 0.75);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-family: monospace;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.assigned-roles-box {
  font-size: 11px;
  color: #cbd5e1;
}
.roles-label { color: #64748b; }
.roles-desc { color: #00e5a3; font-weight: 600; }

/* ── 设备添加与探头卡片 ─────────────────────── */
.dev-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sensor-icon { font-size: 18px; }

.protocol-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(10, 18, 32, 0.6);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
}
.protocol-badge {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}
.proto-tcp { background: #00b4ff; color: #030712; }
.proto-udp { background: #a855f7; color: #ffffff; }
.proto-serial { background: #f59e0b; color: #030712; }
.proto-http { background: #00e5a3; color: #030712; }
.protocol-detail-text { color: #94a3b8; font-family: monospace; }

.sensor-readings-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.reading-box {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
  padding: 8px;
  text-align: center;
}
.reading-lbl { font-size: 10px; color: #64748b; }
.reading-val { font-size: 18px; font-weight: 800; margin-top: 2px; }
.reading-val small { font-size: 10px; font-weight: normal; margin-left: 2px; }
.reading-box.temp .reading-val { color: #00b4ff; }
.reading-box.hum .reading-val { color: #00e5a3; }
.reading-box.co2 .reading-val { color: #f59e0b; }

.reading-footer-row {
  font-size: 11px;
  color: #64748b;
}

/* ── 视频分析配置卡片 ───────────────────────── */
.analysis-config-card {
  max-width: 860px;
  margin: 0 auto;
}

/* ── 基础布局与通用组件 ─────────────────────── */
.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.form-group { margin-bottom: 12px; }
.form-label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 5px; }
.form-hint { font-size: 11px; color: #64748b; margin-top: 4px; }
.input {
  width: 100%;
  padding: 8px 10px;
  border-radius: 6px;
  background: #0f172a;
  border: 1px solid rgba(0, 180, 255, 0.3);
  color: #ffffff;
  font-size: 13px;
  box-sizing: border-box;
}
.input:focus { outline: none; border-color: #00b4ff; }
.input-sm { padding: 4px 8px; font-size: 12px; }

.btn {
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  font-weight: 600;
  transition: all 0.2s;
}
.btn-primary { background: #00b4ff; color: #030712; }
.btn-primary:hover { background: #38bdf8; }
.btn-secondary { background: rgba(255, 255, 255, 0.1); color: #ffffff; }
.btn-secondary:hover { background: rgba(255, 255, 255, 0.18); }
.btn-danger { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
.btn-sm { padding: 4px 8px; font-size: 12px; }
.btn-xs { padding: 2px 6px; font-size: 11px; }
.btn-ghost { background: transparent; color: #00b4ff; }

.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; backdrop-filter: blur(4px);
}
.modal-medium { width: 520px; max-width: 90vw; }
.modal-wide { width: 880px; max-width: 95vw; }
.modal-two-columns {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
}
.preview-viewport {
  width: 100%; height: 260px;
  background: #000; border-radius: 8px;
  overflow: hidden; display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(0, 180, 255, 0.3);
}
.viewport-img { width: 100%; height: 100%; object-fit: contain; }
.viewport-placeholder { text-align: center; color: #64748b; font-size: 12px; }
.placeholder-cam-icon { font-size: 36px; margin-bottom: 6px; }

.snapshot-box {
  width: 100%; height: 280px;
  background: #000; border-radius: 8px;
  overflow: hidden; display: flex; align-items: center; justify-content: center;
}
.snapshot-view { width: 100%; height: 100%; object-fit: contain; }
.snapshot-loading { color: #00b4ff; font-size: 13px; display: flex; align-items: center; gap: 8px; }

.spinner {
  width: 20px; height: 20px;
  border: 3px solid rgba(0, 180, 255, 0.2);
  border-top-color: #00b4ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.badge-online { background: rgba(0, 229, 163, 0.15); color: #00e5a3; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
.badge-offline { background: rgba(148, 163, 184, 0.15); color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
.badge-info { background: rgba(0, 180, 255, 0.15); color: #00b4ff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }

.synthesized-box {
  background: rgba(10, 18, 32, 0.8); padding: 6px 8px; border-radius: 6px;
  font-size: 11px; color: #94a3b8;
}
.synthesized-box code { color: #00b4ff; word-break: break-all; }

.flex-between { display: flex; justify-content: space-between; align-items: center; }
.flex-align-center { display: flex; align-items: center; }
.flex-1 { flex: 1; }
.flex-gap-8 { display: flex; gap: 8px; }
.flex-gap-12 { display: flex; gap: 12px; }
.justify-end { justify-content: flex-end; }
.gap-6 { gap: 6px; }
.gap-8 { gap: 8px; }
.gap-12 { gap: 12px; }
.mb-8 { margin-bottom: 8px; }
.mb-10 { margin-bottom: 10px; }
.mb-12 { margin-bottom: 12px; }
.mb-14 { margin-bottom: 14px; }
.mb-16 { margin-bottom: 16px; }
.mb-20 { margin-bottom: 20px; }
.mt-6 { margin-top: 6px; }
.mt-10 { margin-top: 10px; }
.mt-12 { margin-top: 12px; }
.mt-14 { margin-top: 14px; }
.mt-16 { margin-top: 16px; }
.text-sm { font-size: 12px; }
.text-dim { color: #64748b; }
</style>
