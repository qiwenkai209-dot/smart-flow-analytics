<template>
  <div class="zone-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">📐 展台驻留分析与区域管理</h1>
        <div class="page-desc">自定义新增/编辑展台区域、指定关联摄像头并精准统计驻留时长与客流画像</div>
      </div>
      <div class="header-actions">
        <select v-model="selectedCamera" class="input filter-select" @change="loadData">
          <option value="">全部关联摄像头</option>
          <option v-for="c in cameras" :key="c.id" :value="c.id">
            📹 {{ c.name }} ({{ c.id }})
          </option>
        </select>
        <button class="btn btn-secondary" @click="openAddRoiModal">
          ➕ 新增展台区域
        </button>
        <button class="btn btn-primary" @click="exportExcel">
          ⬇️ 导出明细报表
        </button>
      </div>
    </div>

    <!-- 展台统计卡片网格 -->
    <div class="zone-grid">
      <div class="card zone-detail-card" v-for="zone in filteredZones" :key="zone.name">
        <div class="flex-between mb-8">
          <div class="zone-detail-name">📐 {{ zone.name }}</div>
          <span class="badge badge-online">{{ zone.visits || 0 }} 次到访</span>
        </div>

        <!-- 关联摄像头标签 -->
        <div class="cam-binding-row mb-12">
          <span class="binding-label">📹 关联摄像头:</span>
          <span class="binding-cam">{{ getCamName(zone.camera_id) }}</span>
          <span class="binding-threshold">{{ zone.min_dwell_seconds || 5 }}s 驻留起计</span>
        </div>

        <!-- 驻留时长 -->
        <div class="dwell-meter">
          <div class="stat-value" style="font-size:32px">{{ zone.avg_dwell_seconds || 0 }}s</div>
          <div class="stat-label">平均驻留时长</div>
        </div>

        <!-- 性别比例 -->
        <div class="attr-row mt-16">
          <span class="attr-label">♂ 男性</span>
          <div class="attr-bar">
            <div class="attr-fill blue" :style="{ width: maleRatio(zone) + '%' }"></div>
          </div>
          <span class="attr-pct">{{ zone.male || 0 }}</span>
        </div>
        <div class="attr-row mt-8">
          <span class="attr-label">♀ 女性</span>
          <div class="attr-bar">
            <div class="attr-fill purple" :style="{ width: (100 - maleRatio(zone)) + '%' }"></div>
          </div>
          <span class="attr-pct">{{ zone.female || 0 }}</span>
        </div>

        <!-- 操作按钮 -->
        <div class="zone-card-footer mt-16">
          <button class="btn btn-secondary btn-sm" @click="openEditRoiModal(zone)">
            ✏️ 编辑展台与关联
          </button>
          <button class="btn btn-danger btn-sm" @click="deleteRoi(zone.name)">
            🗑️ 删除
          </button>
        </div>
      </div>

      <!-- 添加展台占位卡片 -->
      <div class="card zone-add-card" @click="openAddRoiModal">
        <div class="add-icon">+</div>
        <div class="add-text">新增自定义展台</div>
        <div class="add-sub">关联指定摄像头设置多边形监控区域</div>
      </div>
    </div>

    <!-- 全部事件明细表 -->
    <div class="card mt-24">
      <div class="flex-between mb-16">
        <div class="card-title">📋 展台驻留事件流水（最新）</div>
        <span class="text-sm text-dim">仅显示有效驻留时长的完整到访事件</span>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>展台区域</th>
            <th>捕获摄像头</th>
            <th>性别画像</th>
            <th>年龄段</th>
            <th>有效驻留(秒)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in tableData" :key="i">
            <td>{{ row.event_time }}</td>
            <td><span class="badge badge-warning">{{ row.roi_name || '全域' }}</span></td>
            <td>{{ getCamName(row.camera_id) }}</td>
            <td>{{ row.gender === 'male' ? '♂ 男' : (row.gender === 'female' ? '♀ 女' : '未识别') }}</td>
            <td>{{ ageLabel(row.age_group) }}</td>
            <td><b style="color:var(--primary)">{{ row.dwell_seconds }}s</b></td>
          </tr>
          <tr v-if="!tableData.length">
            <td colspan="6" style="text-align:center;color:var(--text-dim);padding:24px">
              暂无驻留流水记录
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── 新增 / 编辑展台模态弹窗 ─────────────── -->
    <div class="modal-overlay" v-if="showRoiModal" @click.self="showRoiModal = false">
      <div class="modal card">
        <div class="flex-between mb-16">
          <div class="card-title">{{ isEditRoi ? '✏️ 编辑展台' : '➕ 新增展台区域' }}</div>
          <button class="close-btn" @click="showRoiModal = false">✕</button>
        </div>

        <div class="form-grid">
          <div class="form-group full-width">
            <label class="form-label">展台 / 区域名称 <span class="req">*</span></label>
            <input v-model="roiForm.name" class="input" placeholder="例如: 展台A-AI数字人专区" :disabled="isEditRoi" />
          </div>

          <div class="form-group full-width">
            <label class="form-label">关联监控摄像头 <span class="req">*</span></label>
            <select v-model="roiForm.camera_id" class="input">
              <option value="" disabled>请选择负责该展台的摄像头</option>
              <option v-for="c in cameras" :key="c.id" :value="c.id">
                📹 {{ c.name }} ({{ c.id }})
              </option>
            </select>
          </div>

          <div class="form-group full-width">
            <label class="form-label">最小有效驻留阈值（秒）</label>
            <input v-model.number="roiForm.min_dwell_seconds" type="number" min="1" max="120" class="input" />
            <div class="form-hint">行人停留超过此阈值才记为有效展台到访，可精准过滤过道穿堂行人</div>
          </div>

          <div class="form-group full-width">
            <label class="form-label">多边形区域坐标定义（JSON格式）</label>
            <textarea v-model="roiForm.polygonJson" class="input" rows="3" placeholder="[[100, 200], [500, 200], [500, 600], [100, 600]]"></textarea>
            <div class="flex-gap-8 mt-6">
              <button class="btn btn-ghost btn-sm" @click="applyPresetPolygon('center')">填充预设居中展台</button>
              <button class="btn btn-ghost btn-sm" @click="applyPresetPolygon('left')">填充预设左侧展台</button>
              <button class="btn btn-ghost btn-sm" @click="applyPresetPolygon('right')">填充预设右侧展台</button>
            </div>
          </div>
        </div>

        <div class="flex-gap-8 mt-20">
          <button class="btn btn-primary" style="flex:1" @click="saveRoi">
            {{ isEditRoi ? '💾 保存展台' : '✅ 确认添加' }}
          </button>
          <button class="btn btn-ghost" @click="showRoiModal = false">取消</button>
        </div>
      </div>
    </div>

    <!-- Toast 提示 -->
    <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || ''

const selectedCamera = ref('')
const cameras = ref([])
const rawZones = ref([])
const tableData = ref([])

// 弹窗状态
const showRoiModal = ref(false)
const isEditRoi = ref(false)
const roiForm = ref({
  name: '',
  camera_id: '',
  min_dwell_seconds: 5.0,
  polygonJson: '[[200, 300], [600, 300], [600, 700], [200, 700]]',
})

// Toast
const toast = reactive({ show: false, msg: '', type: '' })
function showToast(msg, type = 'success') {
  toast.msg = msg
  toast.type = type
  toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

const AGE_MAP = { child: '儿童', young: '青年', adult: '成年', elder: '老年' }
const ageLabel = (g) => AGE_MAP[g] || g || '未识别'

const maleRatio = (zone) => {
  const m = zone.male || 0
  const f = zone.female || 0
  const total = m + f
  return total ? Math.round(m / total * 100) : 50
}

function getCamName(camId) {
  const c = cameras.value.find(item => item.id === camId)
  return c ? `${c.name} (${camId})` : (camId || '未绑定')
}

// 展台列表筛选（根据所选摄像头）
const filteredZones = computed(() => {
  if (!selectedCamera.value) return rawZones.value
  return rawZones.value.filter(z => z.camera_id === selectedCamera.value)
})

async function loadData() {
  try {
    const camUrl = `${API}/api/cameras/`
    const dwellUrl = `${API}/api/analytics/dwell` + (selectedCamera.value ? `?camera_id=${selectedCamera.value}` : '')
    const roisUrl = `${API}/api/cameras/rois/all`

    const [camRes, dwellRes, roisRes] = await Promise.all([
      axios.get(camUrl).catch(() => ({ data: [] })),
      axios.get(dwellUrl).catch(() => ({ data: { zones: [] } })),
      axios.get(roisUrl).catch(() => ({ data: [] })),
    ])

    cameras.value = camRes.data || []
    const dwellZones = dwellRes.data.zones || []
    const configuredRois = roisRes.data || []

    // 合并配置的展台与统计数据
    const merged = []
    const visitedMap = new Map()
    for (const dz of dwellZones) {
      visitedMap.set(dz.name, dz)
    }

    // 先加入已配置的展台
    for (const r of configuredRois) {
      const stats = visitedMap.get(r.name) || {}
      merged.push({
        name: r.name,
        camera_id: r.camera_id,
        min_dwell_seconds: r.min_dwell_seconds || 5,
        polygon: r.polygon,
        visits: stats.visits || 0,
        avg_dwell_seconds: stats.avg_dwell_seconds || 0,
        male: stats.male || 0,
        female: stats.female || 0,
      })
      visitedMap.delete(r.name)
    }

    // 如果还有其他未在 rois 列表中的历史数据，也追加展示
    for (const [name, dz] of visitedMap.entries()) {
      merged.push({
        name: name,
        camera_id: '',
        min_dwell_seconds: 5,
        polygon: [],
        visits: dz.visits || 0,
        avg_dwell_seconds: dz.avg_dwell_seconds || 0,
        male: dz.male || 0,
        female: dz.female || 0,
      })
    }

    rawZones.value = merged

    // 加载流水明细
    try {
      const detailRes = await axios.get(`${API}/api/analytics/recent-events?limit=20`)
      tableData.value = detailRes.data || []
    } catch {
      tableData.value = []
    }
  } catch (err) {
    console.error('加载展台数据异常:', err)
  }
}

function openAddRoiModal() {
  isEditRoi.value = false
  roiForm.value = {
    name: `展台-${rawZones.value.length + 1}`,
    camera_id: cameras.value[0]?.id || '',
    min_dwell_seconds: 5.0,
    polygonJson: '[[200, 300], [600, 300], [600, 700], [200, 700]]',
  }
  showRoiModal.value = true
}

function openEditRoiModal(zone) {
  isEditRoi.value = true
  roiForm.value = {
    name: zone.name,
    camera_id: zone.camera_id || (cameras.value[0]?.id || ''),
    min_dwell_seconds: zone.min_dwell_seconds || 5.0,
    polygonJson: JSON.stringify(zone.polygon && zone.polygon.length ? zone.polygon : [[100, 200], [500, 200], [500, 600], [100, 600]]),
  }
  showRoiModal.value = true
}

function applyPresetPolygon(type) {
  if (type === 'center') {
    roiForm.value.polygonJson = '[[300, 300], [700, 300], [700, 700], [300, 700]]'
  } else if (type === 'left') {
    roiForm.value.polygonJson = '[[50, 200], [450, 200], [450, 650], [50, 650]]'
  } else if (type === 'right') {
    roiForm.value.polygonJson = '[[550, 200], [950, 200], [950, 650], [550, 650]]'
  }
}

async function saveRoi() {
  if (!roiForm.value.name.trim()) {
    showToast('请输入展台名称', 'warning')
    return
  }
  if (!roiForm.value.camera_id) {
    showToast('请选择关联的监控摄像头', 'warning')
    return
  }

  let poly = []
  try {
    poly = JSON.parse(roiForm.value.polygonJson)
    if (!Array.isArray(poly) || poly.length < 3) {
      throw new Error('多边形至少需要 3 个顶点坐标')
    }
  } catch (err) {
    showToast('多边形坐标格式错误: ' + err.message, 'warning')
    return
  }

  try {
    await axios.post(`${API}/api/cameras/rois`, {
      name: roiForm.value.name.trim(),
      camera_id: roiForm.value.camera_id,
      min_dwell_seconds: roiForm.value.min_dwell_seconds,
      polygon: poly,
    })
    showToast(`展台 [${roiForm.value.name}] 已保存并关联到摄像头`)
    showRoiModal.value = false
    await loadData()
  } catch (err) {
    showToast(err.response?.data?.detail || '保存展台失败', 'error')
  }
}

async function deleteRoi(name) {
  if (!confirm(`确认删除展台 [${name}] 及其摄像头关联配置？`)) return
  try {
    await axios.delete(`${API}/api/cameras/rois/${encodeURIComponent(name)}`)
    showToast(`展台 [${name}] 已删除`)
    await loadData()
  } catch (err) {
    showToast('删除失败', 'error')
  }
}

function exportExcel() {
  const url = `${API}/api/export/excel` + (selectedCamera.value ? `?camera_id=${selectedCamera.value}` : '')
  window.open(url, '_blank')
}

onMounted(loadData)
</script>

<style scoped>
.zone-page {
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-select {
  min-width: 180px;
}

.zone-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.zone-detail-card {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}

.zone-detail-name {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.cam-binding-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  flex-wrap: wrap;
}

.binding-label {
  color: var(--text-dim);
}

.binding-cam {
  background: rgba(0, 180, 255, 0.15);
  color: #00b4ff;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.binding-threshold {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.dwell-meter {
  background: rgba(0, 0, 0, 0.25);
  padding: 16px;
  border-radius: 8px;
  text-align: center;
}

.zone-card-footer {
  display: flex;
  gap: 8px;
  margin-top: auto;
}
.zone-card-footer .btn {
  flex: 1;
}

.zone-add-card {
  min-height: 240px;
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
.zone-add-card:hover {
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

.attr-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.attr-label { width: 50px; color: var(--text-dim); }
.attr-bar {
  flex: 1; height: 8px;
  background: rgba(255,255,255,0.06);
  border-radius: 4px;
  overflow: hidden;
}
.attr-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.attr-fill.blue { background: #00b4ff; }
.attr-fill.purple { background: #a855f7; }
.attr-pct { width: 28px; text-align: right; font-weight: 600; color: #fff; }

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
  max-width: 540px;
  padding: 24px;
  background: #111d2e;
  border: 1px solid var(--border);
  border-radius: 14px;
}
.close-btn {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 18px;
  cursor: pointer;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
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
.form-hint {
  font-size: 11px;
  color: var(--text-dim);
  line-height: 1.4;
}
.req { color: #ef4444; }

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
</style>
