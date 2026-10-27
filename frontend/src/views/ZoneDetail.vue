<template>
  <div class="zone-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">📐 展台分析与展厅出入规划</h1>
        <div class="page-desc">
          自定义展台圈出区域固化 · 展厅出入规则定义（选择进出摄像头、勾选功能与流动箭头）· 首页实时轮播
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

        <div class="card add-placeholder-card" @click="openAddZoneModal">
          <div class="placeholder-icon">+</div>
          <div class="placeholder-text">新增自定义展台</div>
          <div class="placeholder-sub">选择摄像头 · 勾选功能 · 划线圈出区域</div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'venue'" class="tab-content">
      <div class="filter-bar flex-between mb-16">
        <div>
          <span class="text-sm text-dim">出入规则与展厅协同定义（设置完毕后在首页预留区域自动轮播）</span>
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

          <div class="rule-flow-box mb-14">
            <div class="flow-line in">
              <span class="tag-in">进入摄像头 (+)</span>
              <span class="flow-text">{{ (v.entry_cameras && v.entry_cameras.length) ? v.entry_cameras.join(', ') : '未指定' }}</span>
            </div>
            <div class="flow-arrow">➔ 场内流转与驻留 ➔</div>
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
              ✏️ 编辑
            </button>
            <button class="btn btn-danger btn-sm" @click="deleteVenue(v.id)">
              🗑️
            </button>
          </div>
        </div>

        <div class="card add-placeholder-card" @click="openAddVenueModal">
          <div class="placeholder-icon">+</div>
          <div class="placeholder-text">新增展厅出入规则</div>
          <div class="placeholder-sub">定义进入/出去摄像头与流动箭头 · 首页轮播</div>
        </div>
      </div>
    </div>

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

    <div class="modal-overlay" v-if="showDrawModal" @click.self="showDrawModal = false">
      <div class="modal card modal-extra-large">
        <div class="flex-between mb-12">
          <div>
            <div class="modal-title">📐 自定义圈出区域并固化 - {{ drawTargetRoi?.name }}</div>
            <div class="text-xs text-dim">
              当前摄像头: {{ getCamName(drawTargetRoi?.camera_id) }} · 在视频画面上连续点击添加顶点，圈出展台多边形区域后保存固化
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
              ✅ 区域已成功固化保存！
            </div>
          </div>

          <div class="drawer-toolbox">
            <div class="toolbox-header">🛠️ 区域划线工具栏</div>

            <div class="toolbox-item">
              <span>当前顶点数:</span>
              <b class="text-primary">{{ polygonPoints.length }} 个</b>
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
                📐 重置为标准展台框
              </button>
            </div>

            <div class="toolbox-footer mt-auto pt-16">
              <button
                class="btn btn-primary btn-block"
                @click="saveAndSolidifyPolygon"
                :disabled="polygonPoints.length < 3 || isSaving"
              >
                {{ isSaving ? '保存固化中...' : '🔒 保存并固化此区域' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="modal-overlay" v-if="showVenueModal" @click.self="showVenueModal = false">
      <div class="modal card modal-medium">
        <div class="flex-between mb-16">
          <div class="modal-title">🚪 出入规则规划与额定容量配置</div>
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
          <label class="form-label">2. 选择进入摄像头 (负责 + 增加客流)</label>
          <select v-model="venueForm.entry_cameras" multiple class="input multi-select">
            <option v-for="c in cameras" :key="c.id" :value="c.id">
              [入] {{ c.name }} ({{ c.id }})
            </option>
          </select>
          <div class="form-hint">可按住 Ctrl 进行多选，支持多进配合</div>
        </div>

        <div class="form-group mb-12">
          <label class="form-label">3. 选择出去摄像头 (负责 - 扣除客流)</label>
          <select v-model="venueForm.exit_cameras" multiple class="input multi-select">
            <option v-for="c in cameras" :key="c.id" :value="c.id">
              [出] {{ c.name }} ({{ c.id }})
            </option>
          </select>
          <div class="form-hint">支持多出配合，进出差值自动核算实时在场人数</div>
        </div>

        <div class="form-group mb-16">
          <label class="form-label">4. 额定设计容量 (人，用于计算饱和度)</label>
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
            💾 保存规则 (同步首页轮播)
          </button>
        </div>
      </div>
    </div>

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
  capacity: 200,
  features: ['in_out', 'attribute_gender', 'attribute_age'],
  zones: [],
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

async function fetchSnapshotAndRender(cameraId) {
  isDrawLoading.value = true
  try {
    const res = await axios.post(`${API}/api/cameras/preview-analyze`, {
      camera_id: cameraId || 'cam_001',
      features: ['dwell'],
      rois: [],
    })
    if (res.data && res.data.preview_base64) {
      const img = new Image()
      img.onload = () => {
        bgImage.value = img
        isDrawLoading.value = false
        setupCanvas()
      }
      img.src = `data:image/jpeg;base64,${res.data.preview_base64}`
    } else {
      isDrawLoading.value = false
      setupCanvas()
    }
  } catch {
    isDrawLoading.value = false
    setupCanvas()
  }
}

function setupCanvas() {
  const canvas = drawCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  canvas.width = 1280
  canvas.height = 720
  redrawCanvas(ctx)
}

function redrawCanvas(ctx) {
  if (!ctx) return
  ctx.clearRect(0, 0, 1280, 720)

  if (bgImage.value) {
    ctx.drawImage(bgImage.value, 0, 0, 1280, 720)
  } else {
    ctx.fillStyle = '#0f172a'
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
      ctx.fillStyle = 'rgba(0, 200, 255, 0.22)'
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
    ctx.strokeStyle = 'rgba(0, 229, 163, 0.5)'
    ctx.lineWidth = 2
    ctx.setLineDash([5, 5])
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
    [200, 240],
    [500, 240],
    [480, 580],
    [160, 580],
  ]
  const canvas = drawCanvasRef.value
  if (canvas) redrawCanvas(canvas.getContext('2d'))
}

async function saveAndSolidifyPolygon() {
  if (polygonPoints.value.length < 3) {
    alert('请至少在视频画面中点击 3 个点以圈出闭合多边形区域')
    return
  }

  isSaving.value = true
  const payload = {
    name: drawTargetRoi.value.name,
    camera_id: drawTargetRoi.value.camera_id,
    polygon: polygonPoints.value,
    min_dwell_seconds: drawTargetRoi.value.min_dwell_seconds || 5,
    features: drawTargetRoi.value.features || ['dwell'],
  }

  try {
    await axios.post(`${API}/api/cameras/rois`, payload)
    isSaving.value = false
    isSolidifiedSuccess.value = true
    await loadData()
    setTimeout(() => {
      showDrawModal.value = false
    }, 1200)
  } catch (err) {
    isSaving.value = false
    alert(`保存失败: ${err.message || '网络异常'}`)
  }
}

async function deleteZone(zone) {
  if (!confirm(`确定要删除展台 [${zone.name}] 吗？`)) return
  zoneList.value = zoneList.value.filter(z => z.name !== zone.name)
}

function openAddVenueModal() {
  venueForm.value = {
    id: `venue_${Date.now()}`,
    name: '',
    entry_cameras: cameras.value[0]?.id ? [cameras.value[0].id] : ['cam_001'],
    exit_cameras: cameras.value[1]?.id ? [cameras.value[1].id] : ['cam_003'],
    capacity: 200,
    features: ['in_out', 'attribute_gender', 'attribute_age'],
    zones: [],
  }
  showVenueModal.value = true
}

function openEditVenueModal(v) {
  venueForm.value = {
    id: v.id,
    name: v.name,
    entry_cameras: [...(v.entry_cameras || [])],
    exit_cameras: [...(v.exit_cameras || [])],
    capacity: v.capacity || 200,
    features: v.features || ['in_out', 'attribute_gender', 'attribute_age'],
    zones: [...(v.zones || [])],
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
  font-size: 20px;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 12px;
  color: #64748b;
}

.subnav-tabs {
  display: flex;
  background: rgba(10, 22, 40, 0.85);
  border: 1px solid rgba(0, 180, 255, 0.25);
  border-radius: 6px;
  padding: 3px;
  gap: 4px;
}

.subnav-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.subnav-btn.active {
  background: #00b4ff;
  color: #0a1628;
  font-weight: 700;
}

.filter-bar {
  display: flex;
  align-items: center;
}

.filter-select {
  width: 220px;
}

.zone-grid, .venue-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.card {
  background: rgba(13, 27, 46, 0.82);
  border: 1px solid rgba(0, 180, 255, 0.2);
  border-radius: 8px;
  padding: 14px 16px;
  backdrop-filter: blur(10px);
}

.zone-name-title, .venue-title {
  font-size: 15px;
  font-weight: 700;
  color: #e2e8f0;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.info-label {
  color: #64748b;
}

.info-val {
  color: #38bdf8;
  font-weight: 500;
}

.feature-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.feat-pill {
  font-size: 11px;
  background: rgba(0, 180, 255, 0.1);
  color: #00b4ff;
  border: 1px solid rgba(0, 180, 255, 0.25);
  padding: 1px 6px;
  border-radius: 3px;
}

.solidify-box {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.badge-solidified {
  background: rgba(0, 229, 163, 0.15);
  color: #00e5a3;
  border: 1px solid rgba(0, 229, 163, 0.4);
}

.coords-preview {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
  max-width: 130px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dwell-stat {
  text-align: center;
  background: rgba(0, 180, 255, 0.05);
  border-radius: 6px;
  padding: 10px;
}

.dwell-val {
  font-size: 30px;
  font-weight: 800;
  color: #38bdf8;
  line-height: 1;
}

.dwell-lbl {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}

.gender-track, .cap-track {
  height: 5px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  display: flex;
}

.gender-fill-blue {
  background: #00b4ff;
}

.gender-fill-purple {
  background: #a855f7;
}

.cap-fill {
  background: linear-gradient(90deg, #00b4ff, #00e5a3);
  height: 100%;
}

.venue-dual-kpi {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.kpi-mini-box {
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 5px;
  padding: 8px;
  text-align: center;
}

.kpi-mini-val {
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
}

.kpi-mini-val.highlight { color: #00e5a3; }
.kpi-mini-lbl {
  font-size: 10px;
  color: #94a3b8;
}

.rule-flow-box {
  background: rgba(0, 0, 0, 0.3);
  border: 1px dashed rgba(0, 180, 255, 0.3);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.flow-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.tag-in {
  background: rgba(0, 229, 163, 0.15);
  color: #00e5a3;
  padding: 1px 5px;
  border-radius: 3px;
}

.tag-out {
  background: rgba(244, 63, 94, 0.15);
  color: #f43f5e;
  padding: 1px 5px;
  border-radius: 3px;
}

.flow-text {
  color: #cbd5e1;
}

.flow-arrow {
  text-align: center;
  font-size: 10px;
  color: #64748b;
}

.card-footer {
  display: flex;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.add-placeholder-card {
  border: 2px dashed rgba(0, 180, 255, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 220px;
  cursor: pointer;
  transition: all 0.2s;
}

.add-placeholder-card:hover {
  background: rgba(0, 180, 255, 0.08);
  border-color: #00b4ff;
}

.placeholder-icon {
  font-size: 36px;
  color: #00b4ff;
  line-height: 1;
  margin-bottom: 8px;
}

.placeholder-text {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.placeholder-sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-medium {
  width: 500px;
  max-width: 95vw;
}

.modal-large {
  width: 800px;
  max-width: 95vw;
}

.modal-extra-large {
  width: 1050px;
  max-width: 96vw;
  height: 82vh;
  display: flex;
  flex-direction: column;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
}

.close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
}

.close-btn:hover { color: #fff; }

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  color: #94a3b8;
}

.form-hint {
  font-size: 10px;
  color: #64748b;
}

.checkbox-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 6px 10px;
  cursor: pointer;
}

.checkbox-label.checked {
  background: rgba(0, 180, 255, 0.15);
  border-color: #00b4ff;
  color: #00b4ff;
}

.multi-select {
  height: 80px;
}

.drawer-workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 220px;
  gap: 14px;
  min-height: 0;
  overflow: hidden;
}

.canvas-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  background: #0f172a;
  border: 1px solid rgba(0, 180, 255, 0.3);
  border-radius: 6px;
  overflow: hidden;
}

.interactive-canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: crosshair;
}

.canvas-loading-mask {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #00b4ff;
  font-size: 13px;
}

.toast-badge {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: #00e5a3;
  color: #0f172a;
  font-weight: 700;
  font-size: 13px;
  padding: 6px 16px;
  border-radius: 20px;
  box-shadow: 0 4px 16px rgba(0, 229, 163, 0.4);
}

.drawer-toolbox {
  background: rgba(10, 22, 40, 0.7);
  border: 1px solid rgba(0, 180, 255, 0.2);
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
}

.toolbox-header {
  font-size: 13px;
  font-weight: 600;
  color: #38bdf8;
  margin-bottom: 8px;
}

.toolbox-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.btn-group-vertical {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.btn-block { width: 100%; }

.rule-preview-frame {
  width: 100%;
  height: 420px;
  background: #0f172a;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-img-full {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.preview-loading-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #00b4ff;
  font-size: 13px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(0, 180, 255, 0.2);
  border-top-color: #00b4ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.flex-1 { flex: 1; }
.justify-end { justify-content: flex-end; }
.mb-4 { margin-bottom: 4px; }
.mb-8 { margin-bottom: 8px; }
.mb-10 { margin-bottom: 10px; }
.mb-12 { margin-bottom: 12px; }
.mb-14 { margin-bottom: 14px; }
.mb-16 { margin-bottom: 16px; }
.mt-4 { margin-top: 4px; }
.mt-12 { margin-top: 12px; }
.mt-14 { margin-top: 14px; }
.mt-16 { margin-top: 16px; }
.mt-20 { margin-top: 20px; }
.mt-auto { margin-top: auto; }
.pt-12 { padding-top: 12px; }
.pt-16 { padding-top: 16px; }
</style>
