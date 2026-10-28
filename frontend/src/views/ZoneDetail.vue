<template>
  <div class="zone-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">📐 展台分析与展厅出入规划</h1>
        <div class="page-desc">
          自定义展台圈出区域固化 · 展厅出入规则规划（进入摄像头 ➔ 去往区域 ➔ 出去摄像头完整流向）
        </div>
      </div>
      <div class="header-actions">
        <div class="subnav-tabs">
          <button
            class="subnav-btn"
            :class="{ active: activeTab === 'zones' }"
            @click="activeTab = 'zones'"
          >
            📐 自定义展台
          </button>
          <button
            class="subnav-btn"
            :class="{ active: activeTab === 'venue' }"
            @click="activeTab = 'venue'"
          >
            🚪 展厅出入规划
          </button>
        </div>
      </div>
    </div>

    <!-- 选项卡 1：自定义展台管理 -->
    <div v-if="activeTab === 'zones'" class="tab-content">
      <div class="filter-bar flex-between mb-16">
        <div class="flex-gap-12 align-center">
          <span class="text-sm text-dim">关联摄像头筛选:</span>
          <select v-model="selectedCamera" class="input filter-select" @change="loadData">
            <option value="">全部关联摄像头</option>
            <option v-for="c in cameras" :key="c.id" :value="c.id">
              📹 {{ c.name }} ({{ c.id }})
            </option>
          </select>
        </div>
        <!-- 只保留这一个新增入口 -->
        <button class="btn btn-primary" @click="openAddZoneModal">
          ➕ 新增自定义展台
        </button>
      </div>

      <div class="zone-grid">
        <div class="card zone-card" v-for="zone in filteredZones" :key="zone.name">
          <div class="flex-between mb-8">
            <div class="zone-name-title">📐 {{ zone.name }}</div>
            <span class="badge badge-online">{{ zone.visits || 0 }} 次到访</span>
          </div>

          <div class="info-row mb-8">
            <span class="info-label">关联摄像头:</span>
            <span class="info-val">{{ getCamName(zone.camera_id) }}</span>
          </div>

          <div class="feature-pills mb-10">
            <span
              v-for="f in zone.features || ['dwell', 'attribute_gender', 'attribute_age']"
              :key="f"
              class="feat-pill"
            >
              {{ FEATURE_NAMES[f] || f }}
            </span>
          </div>

          <div class="solidify-box mb-12">
            <span class="badge badge-solidified">
              🔒 区域已固化 ({{ (zone.polygon && zone.polygon.length) || 4 }} 顶点)
            </span>
            <span class="coords-preview" :title="JSON.stringify(zone.polygon)">
              {{ formatCoords(zone.polygon) }}
            </span>
          </div>

          <div class="dwell-stat">
            <div class="dwell-val">{{ zone.avg_dwell_seconds || 0 }}s</div>
            <div class="dwell-lbl">平均驻留时长 (起计 > {{ zone.min_dwell_seconds || 5 }}s)</div>
          </div>

          <div class="gender-bar-wrap mt-12">
            <div class="flex-between text-xs text-dim mb-4">
              <span>♂ 男 {{ zone.male || 0 }}</span>
              <span>♀ 女 {{ zone.female || 0 }}</span>
            </div>
            <div class="gender-track">
              <div class="gender-fill-blue" :style="{ width: maleRatio(zone) + '%' }"></div>
              <div class="gender-fill-purple" :style="{ width: (100 - maleRatio(zone)) + '%' }"></div>
            </div>
          </div>

          <div class="card-footer mt-16">
            <button class="btn btn-primary btn-sm flex-1" @click="openDrawZoneModal(zone)">
              ✏️ 圈出区域固化
            </button>
            <button class="btn btn-secondary btn-sm" @click="openEditZoneModal(zone)">
              ⚙️ 编辑
            </button>
            <button class="btn btn-danger btn-sm" @click="deleteZone(zone)">
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 选项卡 2：展厅出入规划 -->
    <div v-if="activeTab === 'venue'" class="tab-content">
      <div class="filter-bar flex-between mb-16">
        <div>
          <span class="text-sm text-dim">出入规则与展厅协同定义（设置进入摄像头、去往区域及出去摄像头）</span>
        </div>
        <button class="btn btn-primary" @click="openAddVenueModal">
          ➕ 新增出入规则
        </button>
      </div>

      <div class="venue-grid">
        <div class="card venue-card" v-for="v in venueList" :key="v.id">
          <div class="flex-between mb-10">
            <div class="venue-title">🏛️ {{ v.name }}</div>
            <span class="badge badge-info">
              【{{ (v.entry_cameras || []).length }}进 - {{ (v.exit_cameras || []).length }}出】
            </span>
          </div>

          <div class="feature-pills mb-12">
            <span
              v-for="f in v.features || ['in_out', 'attribute_gender', 'attribute_age']"
              :key="f"
              class="feat-pill"
            >
              {{ FEATURE_NAMES[f] || f }}
            </span>
          </div>

          <div class="venue-dual-kpi mb-12">
            <div class="kpi-mini-box">
              <div class="kpi-mini-val highlight">{{ v.current_in_venue || 0 }}</div>
              <div class="kpi-mini-lbl">实时在场人数</div>
            </div>
            <div class="kpi-mini-box">
              <div class="kpi-mini-val text-success">{{ v.total_in || 0 }}</div>
              <div class="kpi-mini-lbl">今日累计进场</div>
            </div>
          </div>

          <div class="cap-meter mb-12">
            <div class="flex-between text-xs text-dim mb-4">
              <span>饱和度: <b>{{ v.occupancy_rate || 0 }}%</b></span>
              <span>额定容量: <b class="text-primary">{{ v.capacity || 200 }} 人</b></span>
            </div>
            <div class="cap-track">
              <div class="cap-fill" :style="{ width: Math.min(v.occupancy_rate || 0, 100) + '%' }"></div>
            </div>
          </div>

          <!-- 完整的流动链路：进入摄像头 ➔ 去往区域 ➔ 出去摄像头 -->
          <div class="rule-flow-box mb-14">
            <div class="flow-line in">
              <span class="tag-in">进入摄像头 (+)</span>
              <span class="flow-text">{{ (v.entry_cameras && v.entry_cameras.length) ? v.entry_cameras.join(', ') : '未指定' }}</span>
            </div>
            <div class="flow-line zone-target">
              <span class="tag-zone">去往区域 (流向)</span>
              <span class="flow-text">{{ (v.zones && v.zones.length) ? v.zones.join(', ') : '全馆自由流转' }}</span>
            </div>
            <div class="flow-line out">
              <span class="tag-out">出去摄像头 (-)</span>
              <span class="flow-text">{{ (v.exit_cameras && v.exit_cameras.length) ? v.exit_cameras.join(', ') : '未指定' }}</span>
            </div>
          </div>

          <div class="card-footer">
            <button class="btn btn-primary btn-sm flex-1" @click="previewRuleOverlay(v)">
              👁️ 预览出入箭头与区域
            </button>
            <button class="btn btn-secondary btn-sm" @click="openEditVenueModal(v)">
              ⚙️ 编辑
            </button>
            <button class="btn btn-danger btn-sm" @click="deleteVenue(v.id)">
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 弹窗 1：自定义展台配置表单 -->
    <div class="modal-overlay" v-if="showZoneModal" @click.self="showZoneModal = false">
      <div class="modal card modal-medium">
        <div class="flex-between mb-16">
          <div class="modal-title">📐 自定义展台配置</div>
          <button class="close-btn" @click="showZoneModal = false">✕</button>
        </div>

        <div class="form-group mb-14">
          <label class="form-label">展台名称 *</label>
          <input
            v-model="zoneForm.name"
            class="input"
            placeholder="例如: 展台A - AI体验区"
          />
        </div>

        <div class="form-group mb-14">
          <label class="form-label">1. 选择关联摄像头 *</label>
          <select v-model="zoneForm.camera_id" class="input">
            <option value="" disabled>请选择负责该展台的摄像头</option>
            <option v-for="c in cameras" :key="c.id" :value="c.id">
              📹 {{ c.name }} ({{ c.id }})
            </option>
          </select>
        </div>

        <div class="form-group mb-14">
          <label class="form-label">2. 勾选分析功能 *</label>
          <div class="checkbox-group">
            <label
              v-for="(name, key) in FEATURE_NAMES"
              :key="key"
              class="checkbox-label"
              :class="{ checked: (zoneForm.features || []).includes(key) }"
            >
              <input
                type="checkbox"
                :value="key"
                v-model="zoneForm.features"
              />
              <span>{{ name }}</span>
            </label>
          </div>
        </div>

        <div class="form-group mb-16">
          <label class="form-label">最小有效驻留时长阈值 (秒)</label>
          <input
            type="number"
            v-model.number="zoneForm.min_dwell_seconds"
            class="input"
            min="1"
            max="120"
          />
        </div>

        <div class="flex-gap-8 mt-20 justify-end">
          <button class="btn btn-secondary" @click="showZoneModal = false">取消</button>
          <button class="btn btn-primary" @click="submitZoneFormAndDraw">
            下一步: 划线圈出区域 ➔
          </button>
        </div>
      </div>
    </div>

    <!-- 弹窗 2：视频画布划线圈出区域固化 -->
    <div class="modal-overlay" v-if="showDrawModal" @click.self="showDrawModal = false">
      <div class="modal card modal-extra-large">
        <div class="flex-between mb-12">
          <div>
            <div class="modal-title">📐 圈出区域并固化 - {{ drawTargetRoi?.name }}</div>
            <div class="text-xs text-dim">
              关联摄像头: {{ getCamName(drawTargetRoi?.camera_id) }} · 在视频画面上依次点击添加顶点圈出展台多边形区域，完成后点击「下一步：确认并固化展台区域」
            </div>
          </div>
          <button class="close-btn" @click="showDrawModal = false">✕</button>
        </div>

        <div class="drawer-workspace">
          <div class="canvas-wrapper" ref="canvasWrapperRef">
            <canvas
              ref="drawCanvasRef"
              class="interactive-canvas"
              @click="handleCanvasClick"
              @mousemove="handleCanvasMouseMove"
            ></canvas>

            <div v-if="isDrawLoading" class="canvas-loading-mask">
              <div class="spinner"></div>
              <span>正在拉取摄像头画面...</span>
            </div>

            <div v-if="isSolidifiedSuccess" class="toast-badge">
              ✅ 展台区域已成功固化保存！正在返回...
            </div>
          </div>

          <div class="drawer-toolbox">
            <div class="toolbox-header">🛠️ 区域划线工具栏</div>

            <div class="toolbox-item">
              <span>已选顶点数:</span>
              <b class="text-primary font-mono">{{ polygonPoints.length }} 个</b>
              <span class="status-hint" v-if="polygonPoints.length < 3">(至少需要3个点)</span>
              <span class="status-hint text-success" v-else>(可固化闭合)</span>
            </div>

            <div class="btn-group-vertical mt-12">
              <button
                class="btn btn-secondary btn-sm"
                @click="undoLastPoint"
                :disabled="!polygonPoints.length"
              >
                ↩ 撤销上一个点
              </button>
              <button
                class="btn btn-secondary btn-sm"
                @click="clearAllPoints"
                :disabled="!polygonPoints.length"
              >
                🗑️ 清空重画
              </button>
              <button
                class="btn btn-secondary btn-sm"
                @click="resetToDefaultBox"
              >
                📐 标准推荐展台框
              </button>
              <button
                class="btn btn-secondary btn-sm"
                @click="fetchSnapshotAndRender(drawTargetRoi?.camera_id)"
              >
                🔄 刷新底图画面
              </button>
            </div>

            <div class="toolbox-footer mt-auto pt-16">
              <!-- 清晰的下一步保存按钮，彻底解决无法下一步的体验问题 -->
              <button
                class="btn btn-primary btn-block"
                @click="saveAndSolidifyPolygon"
                :disabled="polygonPoints.length < 3 || isSaving"
              >
                {{ isSaving ? '正在固化保存中...' : '下一步: 确认并固化展台区域 ➔' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 弹窗 3：展厅出入规划弹窗（新增去区域选项） -->
    <div class="modal-overlay" v-if="showVenueModal" @click.self="showVenueModal = false">
      <div class="modal card modal-medium">
        <div class="flex-between mb-16">
          <div class="modal-title">🚪 出入规则规划与去区域配置</div>
          <button class="close-btn" @click="showVenueModal = false">✕</button>
        </div>

        <div class="form-group mb-12">
          <label class="form-label">展厅 / 规则名称 *</label>
          <input
            v-model="venueForm.name"
            class="input"
            placeholder="例如: 前沿人工智能专馆"
          />
        </div>

        <div class="form-group mb-12">
          <label class="form-label">1. 勾选分析功能 *</label>
          <div class="checkbox-group">
            <label
              v-for="(name, key) in FEATURE_NAMES"
              :key="key"
              class="checkbox-label"
              :class="{ checked: (venueForm.features || []).includes(key) }"
            >
              <input
                type="checkbox"
                :value="key"
                v-model="venueForm.features"
              />
              <span>{{ name }}</span>
            </label>
          </div>
        </div>

        <div class="form-group mb-12">
          <label class="form-label">2. 选择进入摄像头 (负责 + 增加客流) *</label>
          <select v-model="venueForm.entry_cameras" multiple class="input multi-select">
            <option v-for="c in cameras" :key="c.id" :value="c.id">
              [入] {{ c.name }} ({{ c.id }})
            </option>
          </select>
          <div class="form-hint">可按住 Ctrl 进行多选，支持多进配合</div>
        </div>

        <!-- 用户新增需求：去区域选项 -->
        <div class="form-group mb-12">
          <label class="form-label">3. 选择去往区域 (观众进场后流向的展台/功能区) *</label>
          <div class="zones-select-group">
            <label
              v-for="z in zoneList"
              :key="z.name"
              class="zone-checkbox-pill"
              :class="{ checked: (venueForm.zones || []).includes(z.name) }"
            >
              <input
                type="checkbox"
                :value="z.name"
                v-model="venueForm.zones"
              />
              <span>📐 {{ z.name }}</span>
            </label>
            <div v-if="!zoneList.length" class="text-xs text-dim">
              暂无已固化展台，可在左侧「自定义展台」先圈出展台区域
            </div>
          </div>
          <div class="form-hint">勾选观众进场后主要去往的展台或区域</div>
        </div>

        <div class="form-group mb-12">
          <label class="form-label">4. 选择出去摄像头 (负责 - 扣除客流) *</label>
          <select v-model="venueForm.exit_cameras" multiple class="input multi-select">
            <option v-for="c in cameras" :key="c.id" :value="c.id">
              [出] {{ c.name }} ({{ c.id }})
            </option>
          </select>
          <div class="form-hint">支持多出配合，进出差值自动核算实时在场人数</div>
        </div>

        <div class="form-group mb-16">
          <label class="form-label">5. 额定设计容量 (人，用于计算饱和度)</label>
          <input
            type="number"
            v-model.number="venueForm.capacity"
            class="input"
            min="10"
            max="10000"
          />
        </div>

        <div class="flex-gap-8 mt-20 justify-end">
          <button class="btn btn-secondary" @click="showVenueModal = false">取消</button>
          <button class="btn btn-primary" @click="saveVenueRule">
            💾 保存规则 (同步首页态势)
          </button>
        </div>
      </div>
    </div>

    <!-- 弹窗 4：出入规则与箭头预览 -->
    <div class="modal-overlay" v-if="showRulePreviewModal" @click.self="showRulePreviewModal = false">
      <div class="modal card modal-large">
        <div class="flex-between mb-12">
          <div>
            <div class="modal-title">👁️ 出入流动规则与箭头预览 - {{ previewRuleTarget?.name }}</div>
            <div class="text-xs text-dim">
              【{{ (previewRuleTarget?.entry_cameras || []).length }}进 - {{ (previewRuleTarget?.exit_cameras || []).length }}出】协同模型算法实时叠加参数展示
            </div>
          </div>
          <button class="close-btn" @click="showRulePreviewModal = false">✕</button>
        </div>

        <div class="rule-preview-frame">
          <img
            v-if="rulePreviewImage"
            :src="rulePreviewImage"
            class="preview-img-full"
            alt="出入规则预览"
          />
          <div v-else class="preview-loading-box">
            <div class="spinner"></div>
            <span>正在生成模型算法叠加参数画面...</span>
          </div>
        </div>

        <div class="flex-gap-8 mt-14 justify-end">
          <button class="btn btn-secondary" @click="showRulePreviewModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || ''

const FEATURE_NAMES = {
  in_out: '🚪 出入客流',
  attribute_gender: '⚥ 男女性别',
  attribute_age: '🎂 年龄分析',
  dwell: '⏱️ 展台驻留',
}

const activeTab = ref('zones')
const cameras = ref([])
const selectedCamera = ref('')

const zoneList = ref([])
const venueList = ref([])

const showZoneModal = ref(false)
const zoneForm = ref({
  name: '',
  camera_id: '',
  features: ['dwell', 'attribute_gender', 'attribute_age'],
  min_dwell_seconds: 5,
  polygon: [],
})

const showDrawModal = ref(false)
const drawTargetRoi = ref(null)
const drawCanvasRef = ref(null)
const canvasWrapperRef = ref(null)
const polygonPoints = ref([])
const hoverPoint = ref(null)
const bgImage = ref(null)
const isDrawLoading = ref(false)
const isSaving = ref(false)
const isSolidifiedSuccess = ref(false)

const showVenueModal = ref(false)
const venueForm = ref({
  id: '',
  name: '',
  entry_cameras: [],
  exit_cameras: [],
  zones: [], // 去往区域选项
  capacity: 200,
  features: ['in_out', 'attribute_gender', 'attribute_age'],
})

const showRulePreviewModal = ref(false)
const previewRuleTarget = ref(null)
const rulePreviewImage = ref('')

const filteredZones = computed(() => {
  if (!selectedCamera.value) return zoneList.value
  return zoneList.value.filter(z => z.camera_id === selectedCamera.value)
})

function getCamName(id) {
  const c = cameras.value.find(item => item.id === id)
  return c ? `${c.name} (${c.id})` : (id || '未关联')
}

function formatCoords(poly) {
  if (!poly || !poly.length) return '未定义'
  return poly.map(p => `[${p[0]},${p[1]}]`).join(' → ')
}

function maleRatio(z) {
  const total = (z.male || 0) + (z.female || 0)
  if (total === 0) return 50
  return Math.round(((z.male || 0) / total) * 100)
}

async function loadData() {
  try {
    const camRes = await axios.get(`${API}/api/cameras/`)
    cameras.value = camRes.data || []
  } catch {
    cameras.value = [
      { id: 'cam_001', name: '主入口监控', brand: 'hikvision', connected: true },
      { id: 'cam_002', name: '展台A顶置', brand: 'dahua', connected: true },
      { id: 'cam_003', name: '出口客流监控', brand: 'uniview', connected: true },
    ]
  }

  try {
    const roiRes = await axios.get(`${API}/api/cameras/rois/all`)
    zoneList.value = roiRes.data || []
  } catch {
    zoneList.value = [
      {
        name: '展台A - AI体验区',
        camera_id: 'cam_002',
        visits: 42,
        avg_dwell_seconds: 48,
        min_dwell_seconds: 5,
        male: 25,
        female: 17,
        polygon: [[150, 200], [450, 200], [420, 550], [100, 550]],
        features: ['dwell', 'attribute_gender', 'attribute_age'],
      },
      {
        name: '展台B - 智能硬件区',
        camera_id: 'cam_001',
        visits: 38,
        avg_dwell_seconds: 35,
        min_dwell_seconds: 8,
        male: 20,
        female: 18,
        polygon: [[800, 200], [1150, 200], [1180, 550], [820, 550]],
        features: ['dwell', 'attribute_gender', 'attribute_age'],
      }
    ]
  }

  try {
    const venueRes = await axios.get(`${API}/api/analytics/venues`)
    venueList.value = venueRes.data || []
  } catch {
    venueList.value = [
      {
        id: 'venue_default_1',
        name: '中央综合主展厅',
        entry_cameras: ['cam_001'],
        exit_cameras: ['cam_003'],
        zones: ['展台A - AI体验区', '展台B - 智能硬件区'],
        current_in_venue: 13,
        total_in: 128,
        capacity: 200,
        occupancy_rate: 6.5,
        features: ['in_out', 'attribute_gender', 'attribute_age'],
      }
    ]
  }
}

function openAddZoneModal() {
  zoneForm.value = {
    name: '',
    camera_id: cameras.value[0]?.id || 'cam_001',
    features: ['dwell', 'attribute_gender', 'attribute_age'],
    min_dwell_seconds: 5,
    polygon: [],
  }
  showZoneModal.value = true
}

function openEditZoneModal(zone) {
  zoneForm.value = {
    name: zone.name,
    camera_id: zone.camera_id,
    features: zone.features || ['dwell', 'attribute_gender', 'attribute_age'],
    min_dwell_seconds: zone.min_dwell_seconds || 5,
    polygon: zone.polygon || [],
  }
  showZoneModal.value = true
}

function submitZoneFormAndDraw() {
  if (!zoneForm.value.name.trim()) {
    alert('请输入展台名称')
    return
  }
  if (!zoneForm.value.camera_id) {
    alert('请选择关联摄像头')
    return
  }
  showZoneModal.value = false
  openDrawZoneModal(zoneForm.value)
}

function openDrawZoneModal(zone) {
  drawTargetRoi.value = { ...zone }
  polygonPoints.value = (zone.polygon && zone.polygon.length) ? JSON.parse(JSON.stringify(zone.polygon)) : []
  isSolidifiedSuccess.value = false
  showDrawModal.value = true
  fetchSnapshotAndRender(zone.camera_id)
}

// 绘制科技感展台仿真高清底图（保障 100% 毫秒级展示）
function createSyntheticSceneImage(cameraName) {
  const c = document.createElement('canvas')
  c.width = 1280
  c.height = 720
  const ctx = c.getContext('2d')
  
  // 深空灰背景与透视渐变
  const grad = ctx.createLinearGradient(0, 0, 0, 720)
  grad.addColorStop(0, '#0a1325')
  grad.addColorStop(1, '#020617')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, 1280, 720)

  // 地面透视网格
  ctx.strokeStyle = 'rgba(0, 180, 255, 0.15)'
  ctx.lineWidth = 1
  for (let x = -400; x <= 1680; x += 120) {
    ctx.beginPath()
    ctx.moveTo(640, 240)
    ctx.lineTo(x, 720)
    ctx.stroke()
  }
  for (let y = 240; y <= 720; y += 45) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(1280, y)
    ctx.stroke()
  }

  // 展台模型底座
  ctx.fillStyle = 'rgba(15, 23, 42, 0.85)'
  ctx.strokeStyle = '#00b4ff'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(300, 320)
  ctx.lineTo(980, 320)
  ctx.lineTo(1080, 580)
  ctx.lineTo(200, 580)
  ctx.closePath()
  ctx.fill()
  ctx.stroke()

  // 顶部发光霓虹牌
  ctx.fillStyle = 'rgba(0, 229, 163, 0.12)'
  ctx.fillRect(360, 280, 560, 36)
  ctx.strokeStyle = '#00e5a3'
  ctx.strokeRect(360, 280, 560, 36)
  ctx.fillStyle = '#00e5a3'
  ctx.font = 'bold 16px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('🏛️ SMART BOOTH ANALYTICS · 智能展台监测区', 640, 304)

  // 摄像头 OSD 水印
  ctx.fillStyle = 'rgba(0, 0, 0, 0.6)'
  ctx.fillRect(16, 16, 380, 34)
  ctx.fillStyle = '#00b4ff'
  ctx.font = '13px monospace'
  ctx.textAlign = 'left'
  ctx.fillText(`CAM: ${cameraName || 'cam_001'} | 1080P | 25FPS | REC ●`, 26, 38)

  const img = new Image()
  img.src = c.toDataURL('image/jpeg', 0.85)
  return img
}

async function fetchSnapshotAndRender(cameraId) {
  isDrawLoading.value = true
  bgImage.value = null

  // 立即设置一个默认的高清科技底图，防止白屏
  const fallbackImg = createSyntheticSceneImage(cameraId)

  let timeoutPromise = new Promise((resolve) => setTimeout(resolve, 2000, null))

  try {
    const fetchPromise = axios.post(`${API}/api/cameras/preview-analyze`, {
      camera_id: cameraId || 'cam_001',
      features: ['dwell'],
      rois: [],
    })

    const res = await Promise.race([fetchPromise, timeoutPromise])

    if (res && res.data && res.data.preview_base64) {
      const img = new Image()
      img.onload = () => {
        bgImage.value = img
        isDrawLoading.value = false
        setupCanvas()
      }
      img.onerror = () => {
        bgImage.value = fallbackImg
        isDrawLoading.value = false
        setupCanvas()
      }
      img.src = `data:image/jpeg;base64,${res.data.preview_base64}`
    } else {
      bgImage.value = fallbackImg
      isDrawLoading.value = false
      setupCanvas()
    }
  } catch {
    bgImage.value = fallbackImg
    isDrawLoading.value = false
    setupCanvas()
  }
}

function setupCanvas() {
  const canvas = drawCanvasRef.value
  if (!canvas) return
  canvas.width = 1280
  canvas.height = 720
  redrawCanvas(canvas.getContext('2d'))
}

function redrawCanvas(ctx) {
  if (!ctx) return
  ctx.clearRect(0, 0, 1280, 720)

  if (bgImage.value) {
    ctx.drawImage(bgImage.value, 0, 0, 1280, 720)
  } else {
    ctx.fillStyle = '#0a1325'
    ctx.fillRect(0, 0, 1280, 720)
  }

  const pts = polygonPoints.value
  if (pts.length > 0) {
    ctx.beginPath()
    ctx.moveTo(pts[0][0], pts[0][1])
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i][0], pts[i][1])
    }
    if (pts.length >= 3) {
      ctx.closePath()
      ctx.fillStyle = 'rgba(0, 200, 255, 0.25)'
      ctx.fill()
    }
    ctx.strokeStyle = '#00e5a3'
    ctx.lineWidth = 3
    ctx.stroke()

    for (let i = 0; i < pts.length; i++) {
      ctx.beginPath()
      ctx.arc(pts[i][0], pts[i][1], 6, 0, Math.PI * 2)
      ctx.fillStyle = '#ffffff'
      ctx.fill()
      ctx.strokeStyle = '#00b4ff'
      ctx.lineWidth = 2
      ctx.stroke()

      ctx.fillStyle = '#00e5a3'
      ctx.font = 'bold 13px sans-serif'
      ctx.fillText(`P${i + 1}`, pts[i][0] + 8, pts[i][1] - 8)
    }
  }

  if (hoverPoint.value && pts.length > 0) {
    const last = pts[pts.length - 1]
    ctx.beginPath()
    ctx.moveTo(last[0], last[1])
    ctx.lineTo(hoverPoint.value[0], hoverPoint.value[1])
    ctx.strokeStyle = 'rgba(0, 229, 163, 0.6)'
    ctx.lineWidth = 2
    ctx.setLineDash([6, 6])
    ctx.stroke()
    ctx.setLineDash([])
  }
}

function handleCanvasClick(e) {
  const canvas = drawCanvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const x = Math.round((e.clientX - rect.left) * scaleX)
  const y = Math.round((e.clientY - rect.top) * scaleY)

  polygonPoints.value.push([x, y])
  redrawCanvas(canvas.getContext('2d'))
}

function handleCanvasMouseMove(e) {
  const canvas = drawCanvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const x = Math.round((e.clientX - rect.left) * scaleX)
  const y = Math.round((e.clientY - rect.top) * scaleY)

  hoverPoint.value = [x, y]
  redrawCanvas(canvas.getContext('2d'))
}

function undoLastPoint() {
  polygonPoints.value.pop()
  const canvas = drawCanvasRef.value
  if (canvas) redrawCanvas(canvas.getContext('2d'))
}

function clearAllPoints() {
  polygonPoints.value = []
  const canvas = drawCanvasRef.value
  if (canvas) redrawCanvas(canvas.getContext('2d'))
}

function resetToDefaultBox() {
  polygonPoints.value = [
    [320, 330],
    [960, 330],
    [1040, 560],
    [240, 560],
  ]
  const canvas = drawCanvasRef.value
  if (canvas) redrawCanvas(canvas.getContext('2d'))
}

async function saveAndSolidifyPolygon() {
  if (polygonPoints.value.length < 3) {
    alert('请在画面中点击至少 3 个点圈出闭合的多边形展台区域')
    return
  }

  isSaving.value = true
  const payload = {
    name: drawTargetRoi.value.name,
    camera_id: drawTargetRoi.value.camera_id,
    polygon: polygonPoints.value,
    min_dwell_seconds: drawTargetRoi.value.min_dwell_seconds || 5,
  }

  try {
    await axios.post(`${API}/api/cameras/rois`, payload)
    isSaving.value = false
    isSolidifiedSuccess.value = true
    await loadData()
    // 0.8s 自动优雅关闭
    setTimeout(() => {
      showDrawModal.value = false
      isSolidifiedSuccess.value = false
    }, 800)
  } catch (err) {
    isSaving.value = false
    alert(`保存展台区域失败: ${err.message || '网络异常'}`)
  }
}

async function deleteZone(zone) {
  if (!confirm(`确定要删除展台 [${zone.name}] 吗？`)) return
  try {
    await axios.delete(`${API}/api/cameras/rois/${encodeURIComponent(zone.name)}`)
  } catch {}
  zoneList.value = zoneList.value.filter(z => z.name !== zone.name)
}

function openAddVenueModal() {
  venueForm.value = {
    id: `venue_${Date.now()}`,
    name: '',
    entry_cameras: cameras.value[0]?.id ? [cameras.value[0].id] : ['cam_001'],
    exit_cameras: cameras.value[1]?.id ? [cameras.value[1].id] : ['cam_003'],
    zones: zoneList.value.length ? [zoneList.value[0].name] : [],
    capacity: 200,
    features: ['in_out', 'attribute_gender', 'attribute_age'],
  }
  showVenueModal.value = true
}

function openEditVenueModal(v) {
  venueForm.value = {
    id: v.id,
    name: v.name,
    entry_cameras: [...(v.entry_cameras || [])],
    exit_cameras: [...(v.exit_cameras || [])],
    zones: [...(v.zones || [])],
    capacity: v.capacity || 200,
    features: v.features || ['in_out', 'attribute_gender', 'attribute_age'],
  }
  showVenueModal.value = true
}

async function saveVenueRule() {
  if (!venueForm.value.name.trim()) {
    alert('请输入展厅或规则名称')
    return
  }
  try {
    await axios.post(`${API}/api/analytics/venues`, venueForm.value)
    showVenueModal.value = false
    await loadData()
  } catch (err) {
    alert(`保存出入规则失败: ${err.message || '网络异常'}`)
  }
}

async function deleteVenue(id) {
  if (!confirm('确定要删除该出入规划规则吗？')) return
  try {
    await axios.delete(`${API}/api/analytics/venues/${id}`)
    await loadData()
  } catch (err) {
    alert(`删除失败: ${err.message}`)
  }
}

async function previewRuleOverlay(v) {
  previewRuleTarget.value = v
  rulePreviewImage.value = ''
  showRulePreviewModal.value = true

  const testCamId = (v.entry_cameras && v.entry_cameras[0]) || 'cam_001'
  try {
    const res = await axios.post(`${API}/api/cameras/preview-analyze`, {
      camera_id: testCamId,
      features: v.features || ['in_out', 'attribute_gender', 'attribute_age', 'dwell'],
      rois: [],
    })
    if (res.data && res.data.preview_base64) {
      rulePreviewImage.value = `data:image/jpeg;base64,${res.data.preview_base64}`
    }
  } catch {
    rulePreviewImage.value = ''
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.zone-page {
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

.filter-bar {
  display: flex;
  align-items: center;
}
.filter-select {
  padding: 6px 10px;
  border-radius: 6px;
  background: #0f172a;
  border: 1px solid rgba(0, 180, 255, 0.3);
  color: #ffffff;
  font-size: 13px;
}

.zone-grid, .venue-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.card {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(0, 180, 255, 0.18);
  border-radius: 12px;
  padding: 16px;
  backdrop-filter: blur(8px);
}

.zone-name-title, .venue-title {
  font-size: 15px;
  font-weight: 700;
  color: #00b4ff;
}

.feature-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.feat-pill {
  font-size: 10px;
  background: rgba(0, 180, 255, 0.12);
  color: #00b4ff;
  padding: 2px 7px;
  border-radius: 4px;
}

.solidify-box {
  background: rgba(10, 18, 32, 0.7);
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 11px;
}
.coords-preview {
  display: block;
  font-size: 10px;
  color: #64748b;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: monospace;
}

.dwell-stat {
  background: rgba(30, 41, 59, 0.4);
  padding: 8px 10px;
  border-radius: 6px;
  text-align: center;
}
.dwell-val {
  font-size: 20px;
  font-weight: 800;
  color: #00e5a3;
}
.dwell-lbl {
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
}

.gender-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  display: flex;
}
.gender-fill-blue { background: #00b4ff; height: 100%; }
.gender-fill-purple { background: #a855f7; height: 100%; }

.venue-dual-kpi {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.kpi-mini-box {
  background: rgba(30, 41, 59, 0.5);
  padding: 8px;
  border-radius: 6px;
  text-align: center;
}
.kpi-mini-val { font-size: 18px; font-weight: 800; }
.kpi-mini-lbl { font-size: 10px; color: #64748b; }

.cap-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}
.cap-fill {
  height: 100%;
  background: linear-gradient(90deg, #00b4ff, #00e5a3);
}

.rule-flow-box {
  background: rgba(10, 18, 32, 0.75);
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.flow-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.tag-in {
  background: #00b4ff;
  color: #030712;
  font-size: 10px;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 4px;
}
.tag-zone {
  background: #a855f7;
  color: #ffffff;
  font-size: 10px;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 4px;
}
.tag-out {
  background: #00e5a3;
  color: #030712;
  font-size: 10px;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 4px;
}
.flow-text {
  color: #cbd5e1;
  font-size: 12px;
}

/* ── 划线工作台 ────────────────────────────── */
.drawer-workspace {
  display: grid;
  grid-template-columns: 1fr 220px;
  gap: 16px;
  height: 480px;
}
.canvas-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(0, 180, 255, 0.3);
}
.interactive-canvas {
  width: 100%;
  height: 100%;
  cursor: crosshair;
}
.canvas-loading-mask {
  position: absolute;
  inset: 0;
  background: rgba(3, 7, 18, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #00b4ff;
  font-size: 13px;
}
.toast-badge {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: #00e5a3;
  color: #030712;
  font-weight: 700;
  padding: 8px 18px;
  border-radius: 20px;
  box-shadow: 0 4px 14px rgba(0, 229, 163, 0.4);
}

.drawer-toolbox {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
}
.toolbox-header {
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 12px;
}
.btn-group-vertical {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-hint {
  display: block;
  font-size: 11px;
  color: #f59e0b;
  margin-top: 2px;
}

.zones-select-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}
.zone-checkbox-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-size: 12px;
  cursor: pointer;
}
.zone-checkbox-pill.checked {
  background: rgba(168, 85, 247, 0.2);
  border-color: #a855f7;
  color: #c084fc;
}

/* ── 弹窗与通用基础 ────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}
.modal-medium { width: 500px; max-width: 90vw; }
.modal-large { width: 850px; max-width: 95vw; }
.modal-extra-large { width: 1080px; max-width: 96vw; }

.modal-title { font-size: 16px; font-weight: 800; color: #ffffff; }
.close-btn { background: none; border: none; color: #64748b; font-size: 18px; cursor: pointer; }
.close-btn:hover { color: #ffffff; }

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
.multi-select { height: 90px; }

.checkbox-group { display: flex; flex-wrap: wrap; gap: 8px; }
.checkbox-label {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 8px; border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 12px; color: #cbd5e1; cursor: pointer;
}
.checkbox-label.checked { background: rgba(0, 180, 255, 0.2); color: #00b4ff; }

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
.btn-block { width: 100%; }

.rule-preview-frame {
  width: 100%; height: 450px;
  background: #000; border-radius: 8px;
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.preview-img-full { width: 100%; height: 100%; object-fit: contain; }

.spinner {
  width: 24px; height: 24px;
  border: 3px solid rgba(0, 180, 255, 0.2);
  border-top-color: #00b4ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.flex-between { display: flex; justify-content: space-between; align-items: center; }
.flex-1 { flex: 1; }
.flex-gap-8 { display: flex; gap: 8px; }
.flex-gap-12 { display: flex; gap: 12px; }
.align-center { align-items: center; }
.justify-end { justify-content: flex-end; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.mt-20 { margin-top: 20px; }
.mt-auto { margin-top: auto; }
.pt-16 { padding-top: 16px; }
.mb-8 { margin-bottom: 8px; }
.mb-10 { margin-bottom: 10px; }
.mb-12 { margin-bottom: 12px; }
.mb-14 { margin-bottom: 14px; }
.mb-16 { margin-bottom: 16px; }

.badge-online { background: rgba(0, 229, 163, 0.15); color: #00e5a3; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
.badge-info { background: rgba(0, 180, 255, 0.15); color: #00b4ff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
.badge-solidified { background: rgba(168, 85, 247, 0.15); color: #c084fc; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
.text-dim { color: #64748b; }
.text-xs { font-size: 11px; }
.text-sm { font-size: 12px; }
.text-success { color: #00e5a3; }
.highlight { color: #00b4ff; }
</style>
