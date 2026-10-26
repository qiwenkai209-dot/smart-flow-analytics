<template>
  <div class="zone-page">
    <div class="page-header">
      <h1 class="page-title">展台驻留分析</h1>
      <div class="header-actions">
        <select v-model="selectedCamera" class="input" style="width:160px">
          <option value="">全部摄像头</option>
          <option v-for="c in cameras" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <button class="btn btn-primary" @click="exportExcel">
          ⬇️ 导出 Excel
        </button>
      </div>
    </div>

    <!-- 展台卡片网格 -->
    <div class="zone-grid">
      <div class="card zone-detail-card" v-for="zone in zones" :key="zone.name">
        <div class="flex-between mb-16">
          <div class="zone-detail-name">📐 {{ zone.name }}</div>
          <span class="badge badge-online">{{ zone.visits }} 次到访</span>
        </div>

        <!-- 驻留时长 -->
        <div class="dwell-meter">
          <div class="stat-value" style="font-size:32px">{{ zone.avg_dwell_seconds }}s</div>
          <div class="stat-label">平均驻留时长</div>
        </div>

        <!-- 性别条形图 -->
        <div class="attr-row mt-16">
          <span class="attr-label">♂ 男性</span>
          <div class="attr-bar">
            <div class="attr-fill blue" :style="{ width: maleRatio(zone) + '%' }"></div>
          </div>
          <span class="attr-pct">{{ zone.male }}</span>
        </div>
        <div class="attr-row mt-8">
          <span class="attr-label">♀ 女性</span>
          <div class="attr-bar">
            <div class="attr-fill purple" :style="{ width: (100 - maleRatio(zone)) + '%' }"></div>
          </div>
          <span class="attr-pct">{{ zone.female }}</span>
        </div>
      </div>
    </div>

    <!-- 全部事件明细表 -->
    <div class="card mt-16">
      <div class="card-title">📋 驻留事件明细</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th><th>区域</th><th>摄像头</th>
            <th>性别</th><th>年龄段</th><th>驻留(秒)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in tableData" :key="i">
            <td>{{ row.enter_time }}</td>
            <td><span class="badge badge-warning">{{ row.roi_name }}</span></td>
            <td>{{ row.camera_id }}</td>
            <td>{{ row.gender === 'male' ? '♂ 男' : '♀ 女' }}</td>
            <td>{{ ageLabel(row.age_group) }}</td>
            <td><b style="color:var(--primary)">{{ row.dwell_seconds }}s</b></td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const selectedCamera = ref('')
const cameras = ref([])
const zones = ref([])
const tableData = ref([])

const AGE_MAP = { child: '儿童', young: '青年', adult: '成年', elder: '老年' }
const ageLabel = (g) => AGE_MAP[g] || g

const maleRatio = (zone) => {
  const total = zone.male + zone.female
  return total ? Math.round(zone.male / total * 100) : 50
}

async function loadData() {
  const [camRes, dwellRes] = await Promise.all([
    axios.get(`${API}/api/cameras/`).catch(() => ({ data: [] })),
    axios.get(`${API}/api/analytics/dwell`).catch(() => ({ data: { zones: [] } })),
  ])
  cameras.value = camRes.data
  zones.value = dwellRes.data.zones || []
  // Mock table data
  tableData.value = [
    { enter_time: '09:15:32', roi_name: '展台A', camera_id: 'cam_001', gender: 'male',   age_group: 'young', dwell_seconds: 46 },
    { enter_time: '09:20:10', roi_name: '展台B', camera_id: 'cam_001', gender: 'female', age_group: 'adult', dwell_seconds: 35 },
    { enter_time: '09:31:05', roi_name: '展台A', camera_id: 'cam_002', gender: 'male',   age_group: 'elder', dwell_seconds: 88 },
    { enter_time: '10:02:44', roi_name: '展台C', camera_id: 'cam_002', gender: 'female', age_group: 'child', dwell_seconds: 120 },
  ]
}

async function exportExcel() {
  const url = `${API}/api/export/excel${selectedCamera.value ? '?camera_id=' + selectedCamera.value : ''}`
  window.open(url, '_blank')
}

onMounted(loadData)
</script>

<style scoped>
.zone-page { height: 100%; overflow-y: auto; padding: 16px 20px; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.header-actions { display: flex; gap: 10px; align-items: center; }

.zone-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}
.zone-detail-card { padding: 20px; }
.zone-detail-name { font-size: 14px; font-weight: 600; }
.dwell-meter { text-align: center; padding: 10px 0; }

.attr-row { display: flex; align-items: center; gap: 10px; }
.attr-label { font-size: 12px; color: var(--text-muted); width: 38px; }
.attr-bar { flex: 1; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
.attr-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.attr-fill.blue   { background: var(--primary); }
.attr-fill.purple { background: #a855f7; }
.attr-pct { font-size: 12px; color: var(--text-secondary); width: 24px; text-align: right; }

/* ── 数据表格 ─────────────────────────── */
.data-table {
  width: 100%; border-collapse: collapse;
}
.data-table th {
  text-align: left; padding: 8px 12px;
  font-size: 11px; font-weight: 500;
  color: var(--text-muted); text-transform: uppercase;
  border-bottom: 1px solid var(--border);
}
.data-table td {
  padding: 10px 12px; font-size: 13px;
  color: var(--text-secondary);
  border-bottom: 1px solid rgba(0,180,255,0.05);
}
.data-table tr:hover td { background: var(--bg-card-hover); }
</style>
