<template>
  <div class="cam-page">
    <div class="page-header">
      <h1 class="page-title">📹 摄像头管理</h1>
      <div class="flex-gap-8">
        <button class="btn btn-secondary" @click="startOnvifScan">
          🔍 {{ scanning ? '扫描中...' : 'ONVIF 扫描' }}
        </button>
        <button class="btn btn-primary" @click="showAddForm = true">+ 新增摄像头</button>
      </div>
    </div>

    <!-- 摄像头列表 -->
    <div class="cam-grid">
      <div class="card cam-card" v-for="cam in cameras" :key="cam.id">
        <div class="flex-between mb-16">
          <div>
            <div class="cam-name">{{ cam.name }}</div>
            <div class="cam-id">ID: {{ cam.id }}</div>
          </div>
          <span class="badge" :class="cam.connected ? 'badge-online' : 'badge-offline'">
            {{ cam.connected ? '● 在线' : '○ 离线' }}
          </span>
        </div>

        <div class="cam-stats">
          <div class="cam-stat">
            <div class="cam-stat-val">{{ cam.fps_actual }}</div>
            <div class="cam-stat-label">实时 FPS</div>
          </div>
          <div class="cam-stat">
            <div class="cam-stat-val">{{ cam.fps_limit }}</div>
            <div class="cam-stat-label">限定 FPS</div>
          </div>
        </div>

        <button class="btn btn-danger" style="width:100%;margin-top:12px" @click="removeCamera(cam.id)">
          🗑️ 移除
        </button>
      </div>

      <!-- 新增摄像头占位卡 -->
      <div class="card cam-add-card" @click="showAddForm = true">
        <div class="add-icon">+</div>
        <div class="add-text">添加摄像头</div>
      </div>
    </div>

    <!-- ── ONVIF 扫描结果 ──────────────────────── -->
    <div v-if="onvifDevices.length" class="onvif-section">
      <div class="section-title">🔌 已发现的 ONVIF 设备（{{ onvifDevices.length }}）</div>
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

          <!-- 设备通道列表 -->
          <div v-if="dev._channels && dev._channels.length" class="channel-list">
            <div class="channel-item" v-for="ch in dev._channels" :key="ch.token">
              <div class="channel-info">
                <div class="channel-name">{{ ch.channel_name }}</div>
                <div class="channel-meta">
                  {{ ch.width }}×{{ ch.height }} · {{ ch.encoding }}
                </div>
                <div class="channel-url" :title="ch.rtsp_url">{{ ch.rtsp_url }}</div>
              </div>
              <button class="btn btn-primary btn-sm" @click="addFromOnvif(dev, ch)">
                ➕ 添加
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 手动新增弹窗 ────────────────────────── -->
    <div class="modal-overlay" v-if="showAddForm" @click.self="showAddForm = false">
      <div class="modal card">
        <div class="card-title">新增摄像头</div>

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">摄像头 ID</label>
            <input v-model="form.id" class="input" placeholder="cam_003" />
          </div>
          <div class="form-group">
            <label class="form-label">名称</label>
            <input v-model="form.name" class="input" placeholder="侧厅监控" />
          </div>
          <div class="form-group" style="grid-column: span 2">
            <label class="form-label">RTSP 地址</label>
            <input v-model="form.rtsp_url" class="input" placeholder="rtsp://admin:password@192.168.1.x:554/stream1" />
          </div>
          <div class="form-group">
            <label class="form-label">品牌</label>
            <select v-model="form.brand" class="input">
              <option value="generic">通用 RTSP</option>
              <option value="hikvision">海康威视</option>
              <option value="dahua">大华</option>
              <option value="uniview">宇视</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">取帧率 (fps)</label>
            <input v-model.number="form.fps_limit" type="number" min="1" max="25" class="input" />
          </div>
        </div>

        <div class="flex-gap-8 mt-16">
          <button class="btn btn-primary" style="flex:1" @click="addCamera">确认添加</button>
          <button class="btn btn-ghost" @click="showAddForm = false">取消</button>
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

    <!-- ── Toast 提示 ──────────────────────────── -->
    <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const cameras = ref([])
const showAddForm = ref(false)
const form = ref({ id: '', name: '', rtsp_url: '', brand: 'generic', fps_limit: 10 })

// ONVIF 相关状态
const scanning = ref(false)
const onvifDevices = ref([])
const showOnvifAuth = ref(false)
const authTarget = ref(null)
const onvifAuth = reactive({ username: 'admin', password: '' })

// Toast 提示
const toast = reactive({ show: false, msg: '', type: '' })
function showToast(msg, type = 'success') {
  toast.msg = msg
  toast.type = type
  toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

async function loadCameras() {
  const res = await axios.get(`${API}/api/cameras/`).catch(() => ({ data: [] }))
  cameras.value = res.data
}

async function addCamera() {
  try {
    await axios.post(`${API}/api/cameras/`, form.value)
    showToast(`摄像头 [${form.value.name}] 添加成功`)
  } catch (err) {
    showToast(err.response?.data?.detail || '添加失败', 'error')
  }
  showAddForm.value = false
  form.value = { id: '', name: '', rtsp_url: '', brand: 'generic', fps_limit: 10 }
  await loadCameras()
}

async function removeCamera(id) {
  if (!confirm(`确认移除摄像头 [${id}]？`)) return
  await axios.delete(`${API}/api/cameras/${id}`).catch(console.error)
  showToast(`摄像头 [${id}] 已移除`)
  await loadCameras()
}

// ── ONVIF 扫描 ──────────────────────────────────
async function startOnvifScan() {
  scanning.value = true
  onvifDevices.value = []
  try {
    const res = await axios.post(`${API}/api/onvif/scan`, { timeout: 5.0 })
    onvifDevices.value = res.data.map(d => ({ ...d, _channels: [] }))
    if (res.data.length === 0) {
      showToast('未发现 ONVIF 设备，请检查网络', 'warning')
    } else {
      showToast(`发现 ${res.data.length} 个设备`)
    }
  } catch (err) {
    showToast('ONVIF 扫描失败: ' + (err.response?.data?.detail || err.message), 'error')
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
    dev._auth = { username: onvifAuth.username, password: onvifAuth.password }
    showToast(`获取到 ${res.data.length} 个视频通道`)
  } catch (err) {
    showToast('连接设备失败: ' + (err.response?.data?.detail || err.message), 'error')
  }
}

async function addFromOnvif(dev, channel) {
  const camId = `onvif_${Date.now()}`
  const camName = `${dev.name || 'NVR'} - ${channel.channel_name}`
  try {
    await axios.post(`${API}/api/onvif/add-channel`, {
      device_address: dev.address,
      username: dev._auth?.username || 'admin',
      password: dev._auth?.password || '',
      profile_token: channel.token,
      camera_id: camId,
      camera_name: camName,
      fps_limit: 10,
    })
    showToast(`${camName} 添加成功`)
    await loadCameras()
  } catch (err) {
    showToast(err.response?.data?.detail || '添加失败', 'error')
  }
}

onMounted(() => {
  loadCameras()
  // 每 10 秒刷新摄像头状态
  setInterval(loadCameras, 10000)
})
</script>

<style scoped>
.cam-page { height: 100%; overflow-y: auto; padding: 16px 20px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title  { font-size: 20px; font-weight: 700; }

.cam-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.cam-card { padding: 18px; }
.cam-name { font-size: 15px; font-weight: 600; }
.cam-id   { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

.cam-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
.cam-stat  { text-align: center; padding: 8px; background: var(--bg-base); border-radius: 8px; }
.cam-stat-val   { font-size: 20px; font-weight: 700; color: var(--primary); }
.cam-stat-label { font-size: 10px; color: var(--text-muted); margin-top: 2px; }

.cam-add-card {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  min-height: 180px; cursor: pointer;
  border: 2px dashed var(--border); background: transparent;
  transition: all var(--transition);
}
.cam-add-card:hover { border-color: var(--primary); background: var(--primary-dim); }
.add-icon { font-size: 32px; color: var(--text-muted); }
.add-text  { font-size: 13px; color: var(--text-muted); margin-top: 8px; }

/* ── ONVIF 扫描结果 ──────────────── */
.onvif-section { margin-top: 24px; }
.section-title {
  font-size: 16px; font-weight: 700;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.onvif-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}
.onvif-device-card { padding: 18px; }

.device-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.device-name { font-size: 15px; font-weight: 600; }
.device-meta { font-size: 12px; color: var(--text-muted); line-height: 1.8; }
.badge-info {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(0,180,255,0.15);
  color: var(--primary);
}
.mt-12 { margin-top: 12px; }

/* ── 通道列表 ─────────────────────── */
.channel-list {
  margin-top: 12px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
.channel-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.channel-item:last-child { border-bottom: none; }
.channel-info { flex: 1; min-width: 0; }
.channel-name { font-size: 13px; font-weight: 600; }
.channel-meta { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.channel-url {
  font-size: 10px; color: var(--primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-top: 2px; max-width: 240px;
}
.btn-sm { font-size: 12px; padding: 4px 12px; }

/* ── 弹窗 ─────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 200;
}
.modal { width: 520px; padding: 28px; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: 12px; color: var(--text-secondary); }

/* ── Toast ─────────────────────────── */
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  padding: 10px 24px; border-radius: 10px;
  font-size: 13px; font-weight: 500;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  z-index: 300;
  animation: toast-in 0.3s ease;
}
.toast.success { background: rgba(16,217,122,0.15); color: #10d97a; border: 1px solid rgba(16,217,122,0.3); }
.toast.error   { background: rgba(239,68,68,0.15);  color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
.toast.warning { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }

@keyframes toast-in {
  from { opacity: 0; transform: translateX(-50%) translateY(20px); }
  to   { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* ── 按钮次要 ──────────────────────── */
.btn-secondary {
  background: rgba(0,180,255,0.1);
  color: var(--primary);
  border: 1px solid rgba(0,180,255,0.2);
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition);
}
.btn-secondary:hover {
  background: rgba(0,180,255,0.2);
  border-color: rgba(0,180,255,0.4);
}
</style>
