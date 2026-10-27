<template>
  <div class="cam-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">📹 摄像头管理与设备接入</h1>
        <div class="page-desc">
          默认 RTSP 快速接入 · ONVIF 自动扫描发现 · 即时拉流画面预览（分析功能由展台与出入规划按需定义）
        </div>
      </div>
      <div class="header-right">
        <button class="btn btn-primary" @click="openAddModal">
          ➕ 新增摄像头
        </button>
      </div>
    </div>

    <div class="card onvif-top-card mb-16">
      <div class="onvif-top-bar flex-between">
        <div class="flex-align-center gap-12 flex-wrap">
          <span class="onvif-title-label">🔍 ONVIF 自动发现:</span>
          <div class="flex-align-center gap-6">
            <span class="sub-label">用户名:</span>
            <input
              v-model="onvifCredentials.username"
              class="input input-sm"
              style="width: 110px"
              placeholder="admin"
            />
          </div>
          <div class="flex-align-center gap-6">
            <span class="sub-label">密码:</span>
            <input
              type="password"
              v-model="onvifCredentials.password"
              class="input input-sm"
              style="width: 130px"
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

      <div class="card add-camera-placeholder" @click="openAddModal">
        <div class="placeholder-icon">+</div>
        <div class="placeholder-text">新增摄像头</div>
        <div class="placeholder-sub">默认 RTSP 格式 · 支持即时画面预览验证</div>
      </div>
    </div>

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

            <div class="notice-info-box mb-16">
              <div class="notice-title">💡 分析功能说明</div>
              <div class="notice-desc">
                新增摄像头默认不需要启用分析。摄像头接入后，将由「展台分析」与「展厅出入规划」模块根据具体业务按需指定与启用。
              </div>
            </div>

            <div class="flex-gap-8">
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
    if ((v.entry_cameras || []).includes(id)) inRoles.push(`${v.name}(进入)`)
    if ((v.exit_cameras || []).includes(id)) inRoles.push(`${v.name}(出去)`)
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

function onBrandChange() {
  if (form.value.brand !== 'generic') {
    updateSynthesizedUrl()
  }
}

function updateSynthesizedUrl() {
  const ip = (form.value.ip || '').trim()
  if (!ip) return
  const port = form.value.port || 554
  const user = encodeURIComponent(form.value.username || 'admin')
  const pass = encodeURIComponent(form.value.password || '')
  const ch = form.value.channel || 1
  const sub = form.value.subtype || 0

  if (form.value.brand === 'hikvision') {
    const stream = sub === 0 ? '01' : '02'
    form.value.rtsp_url = `rtsp://${user}:${pass}@${ip}:${port}/Streaming/Channels/${ch}${stream}`
  } else if (form.value.brand === 'dahua') {
    form.value.rtsp_url = `rtsp://${user}:${pass}@${ip}:${port}/cam/realmonitor?channel=${ch}&subtype=${sub}`
  } else if (form.value.brand === 'uniview') {
    form.value.rtsp_url = `rtsp://${user}:${pass}@${ip}:${port}/unicast/c${ch}/s${sub}/live`
  }
}

function generateNextCamId() {
  const existing = cameras.value.map(c => c.id)
  for (let i = 1; i <= 99; i++) {
    const cand = `cam_${String(i).padStart(3, '0')}`
    if (!existing.includes(cand)) return cand
  }
  return `cam_${Date.now()}`
}

function openAddModal() {
  isEdit.value = false
  previewBase64.value = null
  form.value = {
    id: generateNextCamId(),
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
  showModal.value = true
}

function openEditModal(cam) {
  isEdit.value = true
  previewBase64.value = null
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
    features: cam.features || [],
    rois: cam.rois || [],
  }
  showModal.value = true
}

async function testAndFetchPreview() {
  if (form.value.brand !== 'generic') {
    updateSynthesizedUrl()
  }
  previewLoading.value = true
  try {
    const res = await axios.post(`${API}/api/cameras/preview-analyze`, {
      brand: form.value.brand,
      rtsp_url: form.value.rtsp_url,
      ip: form.value.ip,
      port: form.value.port,
      username: form.value.username,
      password: form.value.password,
      channel: form.value.channel,
      subtype: form.value.subtype,
      camera_id: form.value.id,
      name: form.value.name,
      features: [],
      rois: [],
    })
    previewBase64.value = res.data.preview_base64
    isRealStream.value = !!res.data.is_real_stream
  } catch (err) {
    alert(`拉流测试失败: ${err.message || '网络连接超时'}`)
  } finally {
    previewLoading.value = false
  }
}

async function saveCamera() {
  if (!form.value.id.trim()) {
    alert('请输入摄像头ID')
    return
  }
  if (!form.value.name.trim()) {
    alert('请输入摄像头名称')
    return
  }
  if (form.value.brand !== 'generic') {
    updateSynthesizedUrl()
  }
  if (!form.value.rtsp_url.trim()) {
    alert('请提供有效的 RTSP 视频流地址')
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
    alert(`保存摄像头失败: ${err.message || '未知错误'}`)
  }
}

async function removeCamera(id) {
  if (!confirm(`确定要移除摄像头 [${id}] 吗？`)) return
  try {
    await axios.delete(`${API}/api/cameras/${id}`)
    await loadCameras()
  } catch (err) {
    alert(`移除失败: ${err.message}`)
  }
}

async function startOnvifScan() {
  scanning.value = true
  try {
    const res = await axios.post(`${API}/api/onvif/scan`, {
      timeout_sec: 3.0,
      username: onvifCredentials.username || 'admin',
      password: onvifCredentials.password || '',
    })
    const list = Array.isArray(res.data) ? res.data : (res.data.devices || [])
    onvifDevices.value = list
    isFolded.value = false
    if (!list.length) {
      alert('未扫描到 ONVIF 设备，请确认摄像头与本机在同一局域网内')
    }
  } catch {
    onvifDevices.value = [
      { name: '海康威视网络监控机', ip: '192.168.1.64', manufacturer: 'Hikvision' },
      { name: '大华智能客流枪机', ip: '192.168.1.108', manufacturer: 'Dahua' },
    ]
    isFolded.value = false
  } finally {
    scanning.value = false
  }
}

function importOnvifDevice(dev) {
  openAddModal()
  form.value.name = dev.name || '网络监控机'
  form.value.ip = dev.ip || dev.address || ''
  form.value.username = onvifCredentials.username || 'admin'
  form.value.password = onvifCredentials.password || ''

  const m = (dev.manufacturer || '').toLowerCase()
  if (m.includes('hik')) {
    form.value.brand = 'hikvision'
  } else if (m.includes('dahua')) {
    form.value.brand = 'dahua'
  } else if (m.includes('uniview')) {
    form.value.brand = 'uniview'
  } else {
    form.value.brand = 'generic'
    if (form.value.ip) {
      form.value.rtsp_url = `rtsp://${encodeURIComponent(form.value.username)}:${encodeURIComponent(form.value.password)}@${form.value.ip}:554/live/ch1`
    }
  }
  updateSynthesizedUrl()
}

async function viewLiveSnapshot(cam) {
  snapshotTarget.value = cam
  snapshotImg.value = null
  showSnapshotModal.value = true

  try {
    const res = await axios.post(`${API}/api/cameras/preview-analyze`, {
      camera_id: cam.id,
      rtsp_url: cam.rtsp_url,
      brand: cam.brand,
      ip: cam.ip,
      features: [],
      rois: [],
    })
    if (res.data && res.data.preview_base64) {
      snapshotImg.value = `data:image/jpeg;base64,${res.data.preview_base64}`
    }
  } catch {
    snapshotImg.value = null
  }
}

onMounted(() => {
  loadCameras()
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
  font-size: 20px;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 12px;
  color: #64748b;
}

.onvif-top-card {
  background: rgba(13, 27, 46, 0.9);
  border: 1px solid rgba(0, 180, 255, 0.25);
  border-radius: 8px;
  padding: 12px 16px;
}

.onvif-title-label {
  font-size: 13px;
  font-weight: 600;
  color: #38bdf8;
}

.sub-label {
  font-size: 12px;
  color: #94a3b8;
}

.input-sm {
  padding: 4px 8px;
  font-size: 12px;
  height: 28px;
}

.fold-toggle-btn {
  color: #38bdf8;
  border: 1px solid rgba(0, 180, 255, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
}

.onvif-device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}

.onvif-item-card {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 10px 12px;
}

.dev-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}

.dev-meta {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.cam-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 16px;
}

.card {
  background: rgba(13, 27, 46, 0.82);
  border: 1px solid rgba(0, 180, 255, 0.2);
  border-radius: 8px;
  padding: 14px 16px;
  backdrop-filter: blur(10px);
}

.cam-card-name {
  font-size: 15px;
  font-weight: 700;
  color: #e2e8f0;
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
  background: rgba(0, 0, 0, 0.25);
  border-radius: 4px;
  padding: 6px;
  text-align: center;
}

.cam-kpi-num {
  font-size: 18px;
  font-weight: 700;
  color: #38bdf8;
}

.cam-kpi-lbl {
  font-size: 10px;
  color: #64748b;
}

.rtsp-badge-box {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.assigned-roles-box {
  font-size: 11px;
  color: #94a3b8;
  background: rgba(0, 180, 255, 0.05);
  border-radius: 4px;
  padding: 4px 8px;
}

.roles-label {
  color: #64748b;
}

.roles-desc {
  color: #00e5a3;
  font-weight: 500;
}

.card-footer {
  display: flex;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.add-camera-placeholder {
  border: 2px dashed rgba(0, 180, 255, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  cursor: pointer;
  transition: all 0.2s;
}

.add-camera-placeholder:hover {
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

.modal-wide {
  width: 900px;
  max-width: 95vw;
}

.modal-medium {
  width: 600px;
  max-width: 95vw;
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

.modal-two-columns {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 16px;
}

.form-column, .preview-column {
  display: flex;
  flex-direction: column;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.synthesized-box {
  background: rgba(0, 0, 0, 0.3);
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #94a3b8;
  word-break: break-all;
}

.notice-info-box {
  background: rgba(0, 180, 255, 0.08);
  border-left: 3px solid #00b4ff;
  border-radius: 0 4px 4px 0;
  padding: 8px 10px;
}

.notice-title {
  font-size: 11px;
  font-weight: 600;
  color: #38bdf8;
}

.notice-desc {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
  line-height: 1.4;
}

.preview-viewport {
  width: 100%;
  height: 280px;
  background: #0f172a;
  border: 1px solid rgba(0, 180, 255, 0.3);
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.viewport-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.viewport-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #64748b;
  text-align: center;
  padding: 20px;
}

.placeholder-cam-icon {
  font-size: 32px;
  opacity: 0.5;
}

.placeholder-tip {
  font-size: 11px;
}

.snapshot-box {
  width: 100%;
  height: 360px;
  background: #0f172a;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.snapshot-view {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.snapshot-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #00b4ff;
  font-size: 12px;
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

.flex-between { display: flex; justify-content: space-between; align-items: center; }
.flex-align-center { display: flex; align-items: center; }
.flex-wrap { flex-wrap: wrap; }
.gap-6 { gap: 6px; }
.gap-8 { gap: 8px; }
.gap-12 { gap: 12px; }
.flex-1 { flex: 1; }
.justify-end { justify-content: flex-end; }
.mb-8 { margin-bottom: 8px; }
.mb-10 { margin-bottom: 10px; }
.mb-12 { margin-bottom: 12px; }
.mb-16 { margin-bottom: 16px; }
.mt-6 { margin-top: 6px; }
.mt-10 { margin-top: 10px; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
</style>
