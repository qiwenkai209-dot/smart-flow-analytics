<template>
  <div class="cam-page">
    <div class="page-header">
      <h1 class="page-title">📹 摄像头管理</h1>
      <button class="btn btn-primary" @click="showAddForm = true">+ 新增摄像头</button>
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

    <!-- 新增弹窗 -->
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

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const cameras = ref([])
const showAddForm = ref(false)
const form = ref({ id: '', name: '', rtsp_url: '', brand: 'generic', fps_limit: 10 })

async function loadCameras() {
  const res = await axios.get(`${API}/api/cameras/`).catch(() => ({ data: [] }))
  cameras.value = res.data
}

async function addCamera() {
  await axios.post(`${API}/api/cameras/`, form.value).catch(console.error)
  showAddForm.value = false
  form.value = { id: '', name: '', rtsp_url: '', brand: 'generic', fps_limit: 10 }
  await loadCameras()
}

async function removeCamera(id) {
  if (!confirm(`确认移除摄像头 [${id}]？`)) return
  await axios.delete(`${API}/api/cameras/${id}`).catch(console.error)
  await loadCameras()
}

onMounted(loadCameras)
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

/* ── 弹窗 ────────────────────────────── */
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
</style>
