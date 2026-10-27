<template>
  <div class="cam-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">📹 摄像头管理</h1>
        <div class="page-desc">支持私有协议（海康/大华/宇视）快捷录入、分析功能勾选分类、实时画面预览及关联展台配置</div>
      </div>
      <div class="flex-gap-8">
        <button class="btn btn-secondary" @click="startOnvifScan">
          🔍 {{ scanning ? '扫描中...' : 'ONVIF 自动发现' }}
        </button>
        <button class="btn btn-primary" @click="openAddModal">
          ➕ 新增摄像头
        </button>
      </div>
    </div>

    <!-- 摄像头列表卡片 -->
    <div class="cam-grid">
      <div class="card cam-card" v-for="cam in cameras" :key="cam.id">
        <div class="flex-between mb-12">
          <div>
            <div class="cam-name">{{ cam.name }}</div>
            <div class="cam-id">ID: {{ cam.id }} · {{ formatBrand(cam.brand) }}</div>
          </div>
          <span class="badge" :class="cam.connected ? 'badge-online' : 'badge-offline'">
            {{ cam.connected ? '● 在线' : '○ 离线' }}
          </span>
        </div>

        <!-- 启用的分析功能标签 -->
        <div class="feature-tags mb-12">
          <span
            v-for="f in cam.features || ['in_out', 'dwell', 'attribute']"
            :key="f"
            class="tag"
            :class="'tag-' + f"
          >
            {{ FEATURE_NAMES[f] || f }}
          </span>
        </div>

        <div class="cam-stats">
          <div class="cam-stat">
            <div class="cam-stat-val">{{ cam.fps_actual || 0 }}</div>
            <div class="cam-stat-label">实时 FPS</div>
          </div>
          <div class="cam-stat">
            <div class="cam-stat-val">{{ cam.fps_limit || 10 }}</div>
            <div class="cam-stat-label">限定 FPS</div>
          </div>
          <div class="cam-stat">
            <div class="cam-stat-val" style="font-size:14px">{{ cam.resolution || '1080P' }}</div>
            <div class="cam-stat-label">分辨率</div>
          </div>
        </div>

        <!-- RTSP 流地址显示 -->
        <div class="cam-stream-url" :title="cam.rtsp_url">
          {{ cam.rtsp_url || '未配置 RTSP' }}
        </div>

        <!-- 关联展台信息 -->
        <div v-if="cam.rois && cam.rois.length" class="cam-rois-info">
          <span>📐 关联展台: </span>
          <b v-for="r in cam.rois" :key="r.name" class="roi-chip">{{ r.name }}</b>
        </div>

        <!-- 卡片操作按钮 -->
        <div class="cam-card-actions">
          <button class="btn btn-secondary btn-sm" @click="viewSnapshot(cam)">
            🖼️ 画面快照
          </button>
          <button class="btn btn-secondary btn-sm" @click="openEditModal(cam)">
            ✏️ 编辑
          </button>
          <button class="btn btn-danger btn-sm" @click="removeCamera(cam.id)">
            🗑️ 移除
          </button>
        </div>
      </div>

      <!-- 快速添加卡片 -->
      <div class="card cam-add-card" @click="openAddModal">
        <div class="add-icon">+</div>
        <div class="add-text">新增摄像头</div>
        <div class="add-sub">支持海康/大华/宇视直接输入 IP 密码</div>
      </div>
    </div>

    <!-- ── ONVIF 扫描结果展示 ──────────────────── -->
    <div v-if="onvifDevices.length" class="onvif-section mt-24">
      <div class="section-title">🔌 局域网已发现设备（{{ onvifDevices.length }}）</div>
      <div class="onvif-grid">
        <div class="card onvif-device-card" v-for="(dev, idx) in onvifDevices" :key="idx">
          <div class="device-header">
            <div class="device-name">{{ dev.name || '未命名设备' }}</div>
            <span class="badge badge-info">{{ dev.manufacturer || 'Unknown' }}</span>
          </div>
          <div class="device-meta">
            <div>📍 {{ dev.address }}</div>
            <div v-if="dev.model">📦 型号: {{ dev.model }}</div>
          </div>
          <div class="flex-gap-8 mt-12">
            <button class="btn btn-secondary" style="flex:1" @click="loadChannels(dev)">
              📡 获取通道
            </button>
          </div>

          <div v-if="dev._channels && dev._channels.length" class="channel-list">
            <div class="channel-item" v-for="ch in dev._channels" :key="ch.token">
              <div class="channel-info">
                <div class="channel-name">{{ ch.channel_name }}</div>
                <div class="channel-meta">{{ ch.width }}×{{ ch.height }} · {{ ch.encoding }}</div>
                <div class="channel-url" :title="ch.rtsp_url">{{ ch.rtsp_url }}</div>
              </div>
              <button class="btn btn-primary btn-sm" @click="addFromOnvif(dev, ch)">
                ➕ 导入
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 新增 / 编辑摄像头模态弹窗 ─────────────── -->
    <div class="modal-overlay" v-if="showModal" @click.self="showModal = false">
      <div class="modal card modal-large">
        <div class="flex-between mb-16">
          <div class="card-title">{{ isEdit ? '✏️ 编辑摄像头' : '➕ 新增摄像头' }}</div>
          <button class="close-btn" @click="showModal = false">✕</button>
        </div>

        <div class="modal-body">
          <div class="form-grid">
            <!-- 基础标识 -->
            <div class="form-group">
              <label class="form-label">摄像头唯一 ID <span class="req">*</span></label>
              <input v-model="form.id" class="input" :disabled="isEdit" placeholder="例如: cam_001" />
            </div>
            <div class="form-group">
              <label class="form-label">摄像头名称 <span class="req">*</span></label>
              <input v-model="form.name" class="input" placeholder="例如: 展厅东门主入口" />
            </div>

            <!-- 品牌选择 -->
            <div class="form-group">
              <label class="form-label">设备协议 / 品牌</label>
              <select v-model="form.brand" class="input" @change="onBrandChange">
                <option value="hikvision">海康威视 (Hikvision 私有规则)</option>
                <option value="dahua">大华股份 (Dahua 私有规则)</option>
                <option value="uniview">宇视科技 (Uniview 私有规则)</option>
                <option value="generic">通用标准 RTSP 地址</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">取帧频率 (FPS限制)</label>
              <input v-model.number="form.fps_limit" type="number" min="1" max="30" class="input" />
            </div>

            <!-- 私有协议表单（海康/大华/宇视直接输入IP、端口、账号、密码） -->
            <template v-if="form.brand !== 'generic'">
              <div class="form-group">
                <label class="form-label">设备 IP 地址 <span class="req">*</span></label>
                <input v-model="form.ip" class="input" placeholder="例如: 192.168.1.64" @input="updateSynthesizedUrl" />
              </div>

              <div class="form-group">
                <label class="form-label">RTSP 端口</label>
                <input v-model.number="form.port" type="number" class="input" placeholder="默认 554" @input="updateSynthesizedUrl" />
              </div>

              <div class="form-group">
                <label class="form-label">通道号</label>
                <input v-model.number="form.channel" type="number" min="1" max="64" class="input" placeholder="默认 1" @input="updateSynthesizedUrl" />
              </div>

              <div class="form-group">
                <label class="form-label">码流规格</label>
                <select v-model.number="form.subtype" class="input" @change="updateSynthesizedUrl">
                  <option :value="0">主码流（高清分析）</option>
                  <option :value="1">子码流（低带宽/省算力）</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">登录用户名</label>
                <input v-model="form.username" class="input" placeholder="admin" @input="updateSynthesizedUrl" />
              </div>

              <div class="form-group">
                <label class="form-label">登录密码</label>
                <input v-model="form.password" type="password" class="input" placeholder="设备密码" @input="updateSynthesizedUrl" />
              </div>
            </template>

            <!-- 通用 RTSP 输入 -->
            <div class="form-group full-width" v-if="form.brand === 'generic'">
              <label class="form-label">RTSP 完整视频流地址 <span class="req">*</span></label>
              <input v-model="form.rtsp_url" class="input" placeholder="rtsp://admin:password@192.168.1.100:554/live/ch1" />
            </div>

            <!-- 自动合成的 RTSP 预览显示 -->
            <div class="form-group full-width" v-else>
              <label class="form-label">自动生成 RTSP 播放地址</label>
              <div class="rtsp-preview-box">{{ form.rtsp_url || '请填写 IP 和密码自动拼装' }}</div>
            </div>

            <!-- 业务分类勾选 -->
            <div class="form-group full-width">
              <label class="form-label">🎯 启用分析分类（支持多选勾选）</label>
              <div class="features-checkboxes">
                <label class="checkbox-item">
                  <input type="checkbox" value="in_out" v-model="form.features" />
                  <span>🚪 <b>进出客流</b>（用于客流进出计数与实时在场人数核算）</span>
                </label>
                <label class="checkbox-item">
                  <input type="checkbox" value="dwell" v-model="form.features" />
                  <span>⏱️ <b>展台驻留</b>（用于多边形 ROI 展台驻留时长与热度分析）</span>
                </label>
                <label class="checkbox-item">
                  <input type="checkbox" value="attribute" v-model="form.features" />
                  <span>👥 <b>年龄性别</b>（PP-Human 全身体态属性识别）</span>
                </label>
              </div>
            </div>
          </div>

          <!-- ── 即时画面预览区域 ──────────────────── -->
          <div class="preview-panel mt-16">
            <div class="flex-between mb-8">
              <span class="preview-title">📹 摄像头画面即时预览验证</span>
              <button
                class="btn btn-secondary btn-sm"
                :disabled="previewLoading"
                @click="testAndPreviewStream"
              >
                {{ previewLoading ? '连接拉流中...' : '📷 测试连接并预览画面' }}
              </button>
            </div>

            <div class="preview-viewport">
              <div v-if="previewLoading" class="preview-placeholder">
                <div class="spinner"></div>
                <div>正在尝试连接 RTSP 并解码第 1 帧画面...</div>
              </div>
              <div v-else-if="previewResult.error" class="preview-error">
                ⚠️ {{ previewResult.error }}
              </div>
              <div v-else-if="previewResult.preview_base64" class="preview-success">
                <img :src="previewResult.preview_base64" alt="视频帧预览" class="preview-img" />
                <div class="preview-badge">分辨率: {{ previewResult.resolution }} · 画面正常 ✅</div>
              </div>
              <div v-else class="preview-placeholder">
                点击上方「测试连接并预览画面」可实时抓取摄像头画面帧，确认画面角度与账号有效
              </div>
            </div>
          </div>
        </div>

        <div class="flex-gap-8 mt-20">
          <button class="btn btn-primary" style="flex:1" @click="saveCamera">
            {{ isEdit ? '💾 保存配置' : '✅ 确认添加' }}
          </button>
          <button class="btn btn-ghost" @click="showModal = false">取消</button>
        </div>
      </div>
    </div>

    <!-- ── 实时画面快照弹窗 ──────────────────────── -->
    <div class="modal-overlay" v-if="showSnapshotModal" @click.self="showSnapshotModal = false">
      <div class="modal card modal-large">
        <div class="flex-between mb-16">
          <div class="card-title">🖼️ 摄像头实时画面快照 - {{ snapshotTarget?.name }}</div>
          <button class="close-btn" @click="showSnapshotModal = false">✕</button>
        </div>
        <div class="snapshot-container">
          <img :src="snapshotUrl" class="snapshot-img" alt="实时快照" />
        </div>
        <div class="flex-between mt-12 text-sm text-dim">
          <span>摄像头 ID: {{ snapshotTarget?.id }}</span>
          <button class="btn btn-secondary btn-sm" @click="refreshSnapshot">🔄 刷新快照</button>
        </div>
      </div>
    </div>

    <!-- ── ONVIF 认证弹窗 ──────────────────────── -->
    <div class="modal-overlay" v-if="showOnvifAuth" @click.self="showOnvifAuth = false">
      <div class="modal card">
        <div class="card-title">🔐 ONVIF 设备认证</div>
        <div class="device-meta mb-16">{{ authTarget?.address }}</div>

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input v-model="onvifAuth.username" class="input" placeholder="admin" />
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <input v-model="onvifAuth.password" type="password" class="input" />
          </div>
        </div>

        <div class="flex-gap-8 mt-16">
          <button class="btn btn-primary" style="flex:1" @click="submitOnvifAuth">连接并获取通道</button>
          <button class="btn btn-ghost" @click="showOnvifAuth = false">取消</button>
        </div>
      </div>
    </div>

    <!-- Toast 提示 -->
    <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || ''

const FEATURE_NAMES = {
  in_out: '🚪 进出客流',
  dwell: '⏱️ 展台驻留',
  attribute: '👥 年龄性别',
}

const cameras = ref([])
const showModal = ref(false)
const isEdit = ref(false)

const form = ref({
  id: '',
  name: '',
  brand: 'hikvision',
  rtsp_url: '',
  ip: '',
  port: 554,
  username: 'admin',
  password: '',
  channel: 1,
  subtype: 0,
  fps_limit: 10,
  features: ['in_out', 'dwell', 'attribute'],
  rois: [],
})

// 预览状态
const previewLoading = ref(false)
const previewResult = reactive({
  success: false,
  error: null,
  preview_base64: null,
  resolution: '未知',
})

// 快照查看
const showSnapshotModal = ref(false)
const snapshotTarget = ref(null)
const snapshotUrl = ref('')

// ONVIF 状态
const scanning = ref(false)
const onvifDevices = ref([])
const showOnvifAuth = ref(false)
const authTarget = ref(null)
const onvifAuth = reactive({ username: 'admin', password: '' })

// Toast
const toast = reactive({ show: false, msg: '', type: '' })
function showToast(msg, type = 'success') {
  toast.msg = msg
  toast.type = type
  toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

function formatBrand(b) {
  const map = {
    hikvision: '海康威视',
    dahua: '大华',
    uniview: '宇视',
    generic: '通用RTSP',
  }
  return map[b] || b
}

// 自动拼装各品牌私有协议 RTSP 地址
function updateSynthesizedUrl() {
  if (form.value.brand === 'generic') return
  const ip = form.value.ip.trim()
  if (!ip) {
    form.value.rtsp_url = ''
    return
  }
  const user = form.value.username || 'admin'
  const pass = form.value.password || ''
  const auth = user || pass ? `${user}:${pass}@` : ''
  const port = form.value.port && form.value.port !== 554 ? `:${form.value.port}` : ''
  const ch = form.value.channel || 1
  const sub = form.value.subtype || 0

  if (form.value.brand === 'hikvision') {
    const streamCode = `${ch}0${sub + 1}`
    form.value.rtsp_url = `rtsp://${auth}${ip}${port}/Streaming/Channels/${streamCode}`
  } else if (form.value.brand === 'dahua') {
    form.value.rtsp_url = `rtsp://${auth}${ip}${port}/cam/realmonitor?channel=${ch}&subtype=${sub}`
  } else if (form.value.brand === 'uniview') {
    form.value.rtsp_url = `rtsp://${auth}${ip}${port}/unicast/c${ch}/s${sub}/live`
  }
}

function onBrandChange() {
  updateSynthesizedUrl()
}

async function loadCameras() {
  try {
    const res = await axios.get(`${API}/api/cameras/`)
    cameras.value = res.data || []
  } catch {
    cameras.value = []
  }
}

function openAddModal() {
  isEdit.value = false
  form.value = {
    id: `cam_${String(cameras.value.length + 1).padStart(3, '0')}`,
    name: '',
    brand: 'hikvision',
    rtsp_url: '',
    ip: '',
    port: 554,
    username: 'admin',
    password: '',
    channel: 1,
    subtype: 0,
    fps_limit: 10,
    features: ['in_out', 'dwell', 'attribute'],
    rois: [],
  }
  previewResult.preview_base64 = null
  previewResult.error = null
  showModal.value = true
}

function openEditModal(cam) {
  isEdit.value = true
  form.value = {
    id: cam.id,
    name: cam.name,
    brand: cam.brand || 'generic',
    rtsp_url: cam.rtsp_url || '',
    ip: cam.ip || '',
    port: cam.port || 554,
    username: cam.username || 'admin',
    password: cam.password || '',
    channel: cam.channel || 1,
    subtype: cam.subtype || 0,
    fps_limit: cam.fps_limit || 10,
    features: cam.features ? [...cam.features] : ['in_out', 'dwell', 'attribute'],
    rois: cam.rois || [],
  }
  previewResult.preview_base64 = null
  previewResult.error = null
  showModal.value = true
}

// 预览测试
async function testAndPreviewStream() {
  previewLoading.value = true
  previewResult.error = null
  previewResult.preview_base64 = null

  try {
    const res = await axios.post(`${API}/api/cameras/preview-test`, {
      brand: form.value.brand,
      ip: form.value.ip,
      port: form.value.port,
      username: form.value.username,
      password: form.value.password,
      channel: form.value.channel,
      subtype: form.value.subtype,
      rtsp_url: form.value.rtsp_url,
    })

    if (res.data.success) {
      previewResult.success = true
      previewResult.preview_base64 = res.data.preview_base64
      previewResult.resolution = res.data.resolution
      showToast('取流成功，画面正常！')
    } else {
      previewResult.success = false
      previewResult.error = res.data.error
      showToast(res.data.error, 'warning')
    }
  } catch (err) {
    previewResult.error = err.response?.data?.detail || err.message || '连接测试异常'
  } finally {
    previewLoading.value = false
  }
}

// 保存摄像头
async function saveCamera() {
  if (!form.value.id || !form.value.name) {
    showToast('请完整填写摄像头 ID 和名称', 'warning')
    return
  }

  updateSynthesizedUrl()
  if (!form.value.rtsp_url && !form.value.ip) {
    showToast('请输入 IP 地址或完整的 RTSP 地址', 'warning')
    return
  }

  try {
    if (isEdit.value) {
      await axios.put(`${API}/api/cameras/${form.value.id}`, form.value)
      showToast(`摄像头 [${form.value.name}] 更新成功`)
    } else {
      await axios.post(`${API}/api/cameras/`, form.value)
      showToast(`摄像头 [${form.value.name}] 添加成功`)
    }
    showModal.value = false
    await loadCameras()
  } catch (err) {
    showToast(err.response?.data?.detail || '保存失败', 'error')
  }
}

async function removeCamera(id) {
  if (!confirm(`确认移除摄像头 [${id}]？`)) return
  try {
    await axios.delete(`${API}/api/cameras/${id}`)
    showToast(`摄像头 [${id}] 已移除`)
    await loadCameras()
  } catch (err) {
    showToast('移除失败', 'error')
  }
}

function viewSnapshot(cam) {
  snapshotTarget.value = cam
  snapshotUrl.value = `${API}/api/cameras/${cam.id}/snapshot?t=${Date.now()}`
  showSnapshotModal.value = true
}

function refreshSnapshot() {
  if (snapshotTarget.value) {
    snapshotUrl.value = `${API}/api/cameras/${snapshotTarget.value.id}/snapshot?t=${Date.now()}`
  }
}

// ── ONVIF 扫描 ──────────────────────────────────
async function startOnvifScan() {
  scanning.value = true
  onvifDevices.value = []
  try {
    const res = await axios.post(`${API}/api/onvif/scan`, { timeout: 5.0 })
    onvifDevices.value = res.data.map(d => ({ ...d, _channels: [] }))
    if (res.data.length === 0) {
      showToast('未发现 ONVIF 设备，请确认摄像头与服务器在同一网段', 'warning')
    } else {
      showToast(`已发现 ${res.data.length} 台设备`)
    }
  } catch (err) {
    showToast('ONVIF 扫描异常: ' + (err.response?.data?.detail || err.message), 'error')
  }
  scanning.value = false
}

function loadChannels(dev) {
  authTarget.value = dev
  onvifAuth.username = 'admin'
  onvifAuth.password = ''
  showOnvifAuth.value = true
}

async function submitOnvifAuth() {
  const dev = authTarget.value
  showOnvifAuth.value = false
  try {
    const res = await axios.post(`${API}/api/onvif/channels`, {
      address: dev.address,
      username: onvifAuth.username,
      password: onvifAuth.password,
    })
    dev._channels = res.data
    showToast(`成功获取 ${res.data.length} 个通道`)
  } catch (err) {
    showToast('获取通道失败: ' + (err.response?.data?.detail || err.message), 'error')
  }
}

function addFromOnvif(dev, channel) {
  openAddModal()
  form.value.name = `${dev.name || 'NVR'} - ${channel.channel_name || '通道'}`
  form.value.rtsp_url = channel.rtsp_url
  form.value.brand = 'generic'
}

onMounted(loadCameras)
</script>

<style scoped>
.cam-page {
  padding: 24px 32px;
  max-width: 1440px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 6px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-dim);
}

.cam-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.cam-card {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}

.cam-name {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.cam-id {
  font-size: 12px;
  color: var(--text-dim);
  margin-top: 2px;
}

.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.tag-in_out {
  background: rgba(0, 180, 255, 0.15);
  color: #00b4ff;
  border: 1px solid rgba(0, 180, 255, 0.3);
}
.tag-dwell {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}
.tag-attribute {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.cam-stats {
  display: flex;
  justify-content: space-around;
  background: rgba(0, 0, 0, 0.25);
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.cam-stat {
  text-align: center;
}

.cam-stat-val {
  font-size: 18px;
  font-weight: 700;
  color: #00b4ff;
}

.cam-stat-label {
  font-size: 11px;
  color: var(--text-dim);
  margin-top: 2px;
}

.cam-stream-url {
  font-size: 11px;
  color: var(--text-dim);
  background: rgba(0, 0, 0, 0.3);
  padding: 6px 10px;
  border-radius: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 12px;
  font-family: monospace;
}

.cam-rois-info {
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.roi-chip {
  background: rgba(0, 180, 255, 0.1);
  color: #00b4ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.cam-card-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
}
.cam-card-actions .btn {
  flex: 1;
}

.cam-add-card {
  min-height: 220px;
  border: 2px dashed rgba(0, 180, 255, 0.3);
  background: rgba(0, 180, 255, 0.02);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 12px;
  transition: all 0.2s;
}
.cam-add-card:hover {
  border-color: #00b4ff;
  background: rgba(0, 180, 255, 0.08);
}
.add-icon {
  font-size: 36px;
  color: #00b4ff;
  margin-bottom: 6px;
}
.add-text {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}
.add-sub {
  font-size: 12px;
  color: var(--text-dim);
  margin-top: 4px;
}

/* 模态弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  width: 90%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 24px;
  background: #111d2e;
  border: 1px solid var(--border);
  border-radius: 14px;
}
.modal-large {
  max-width: 760px;
}
.close-btn {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 18px;
  cursor: pointer;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.full-width {
  grid-column: span 2;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-label {
  font-size: 12px;
  color: var(--text-dim);
}
.req {
  color: #ef4444;
}

.rtsp-preview-box {
  background: rgba(0, 0, 0, 0.4);
  border: 1px dashed var(--border);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #00b4ff;
  font-family: monospace;
  word-break: break-all;
}

.features-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(0, 0, 0, 0.2);
  padding: 12px;
  border-radius: 8px;
}
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  color: #e2e8f0;
}

/* 画面预览区域 */
.preview-panel {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px;
}
.preview-title {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}
.preview-viewport {
  min-height: 180px;
  background: #090e17;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}
.preview-placeholder {
  font-size: 12px;
  color: var(--text-dim);
  text-align: center;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.preview-error {
  color: #f87171;
  font-size: 13px;
  padding: 16px;
  text-align: center;
}
.preview-success {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.preview-img {
  width: 100%;
  max-height: 320px;
  object-fit: contain;
}
.preview-badge {
  background: rgba(0, 0, 0, 0.7);
  padding: 4px 10px;
  font-size: 11px;
  color: #10b981;
  border-radius: 4px;
  margin-top: 6px;
}

/* 快照容器 */
.snapshot-container {
  width: 100%;
  min-height: 260px;
  background: #000;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.snapshot-img {
  max-width: 100%;
  max-height: 480px;
  object-fit: contain;
}

/* 通道列表与 ONVIF */
.onvif-section {
  border-top: 1px solid var(--border);
  padding-top: 20px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 16px;
}
.onvif-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.channel-list {
  margin-top: 12px;
  border-top: 1px solid var(--border);
  padding-top: 8px;
}
.channel-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.channel-info {
  overflow: hidden;
  max-width: 80%;
}
.channel-name {
  font-weight: 600;
  color: #e2e8f0;
}
.channel-meta {
  color: var(--text-dim);
  font-size: 11px;
}
.channel-url {
  color: #00b4ff;
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 13px;
  color: #fff;
  background: #1e293b;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  z-index: 9999;
}
.toast.success { background: #065f46; border: 1px solid #10b981; }
.toast.error   { background: #7f1d1d; border: 1px solid #ef4444; }
.toast.warning { background: #78350f; border: 1px solid #f59e0b; }

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(0, 180, 255, 0.3);
  border-top-color: #00b4ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
