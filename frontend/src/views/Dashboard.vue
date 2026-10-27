<template>
  <div class="dashboard-fullscreen">
    <section class="global-kpi-bar">
      <div class="kpi-card live-card">
        <div class="kpi-meta">
          <span class="live-dot"></span>
          <span class="kpi-title">当前在场人数</span>
        </div>
        <div class="kpi-num count-up">{{ globalCurrentVisitors }}</div>
        <div class="kpi-tip">全域实时动态监测</div>
      </div>

      <div class="kpi-card total-card">
        <div class="kpi-meta">
          <span class="kpi-badge-icon">📥</span>
          <span class="kpi-title">今日累计客流</span>
        </div>
        <div class="kpi-num text-success count-up">{{ globalTotalIn }}</div>
        <div class="kpi-tip">今日进场总人次汇总</div>
      </div>

      <div class="kpi-card occupancy-card">
        <div class="kpi-meta">
          <span class="kpi-badge-icon">⚡</span>
          <span class="kpi-title">全域饱和度</span>
          <span class="status-pill" :class="'pill-' + globalOccupancyStatus">
            {{ globalOccupancyLabel }}
          </span>
        </div>
        <div class="kpi-num font-mono">{{ globalOccupancyRate }}%</div>
        <div class="kpi-progress">
          <div class="kpi-progress-bar" :style="{ width: Math.min(globalOccupancyRate, 100) + '%' }"></div>
        </div>
      </div>
    </section>

    <div class="dashboard-body">
      <div class="body-left">
        <div class="card chart-box trend-box">
          <div class="panel-header">
            <span class="panel-title">📈 今日客流走势（每小时）</span>
            <span class="panel-tag">全天人流动向</span>
          </div>
          <div ref="lineRef" class="chart-canvas"></div>
        </div>

        <div class="bi-charts-row">
          <div class="card chart-box half-box">
            <div class="panel-header">
              <span class="panel-title">👥 性别分布</span>
            </div>
            <div ref="genderRef" class="chart-canvas-sm"></div>
            <div class="legend-bar">
              <span class="legend-item"><i class="dot blue"></i>男性 {{ data.gender.male }}</span>
              <span class="legend-item"><i class="dot purple"></i>女性 {{ data.gender.female }}</span>
            </div>
          </div>

          <div class="card chart-box half-box">
            <div class="panel-header">
              <span class="panel-title">🎂 年龄层分布</span>
            </div>
            <div ref="ageRef" class="chart-canvas-sm"></div>
          </div>
        </div>
      </div>

      <div class="body-right">
        <div class="card venue-carousel-panel">
          <div class="panel-header flex-between">
            <div class="flex-align-center">
              <span class="panel-title">🏛️ 展厅出入实时态势</span>
              <span class="rule-mode-tag ml-8">{{ activeVenue.rule_mode }}</span>
            </div>
            <div class="carousel-nav">
              <button class="nav-arrow-btn" @click="prevVenue" title="上一个展厅">‹</button>
              <div class="carousel-dots">
                <span
                  v-for="(v, idx) in venueList"
                  :key="v.id"
                  class="carousel-dot"
                  :class="{ active: currentVenueIdx === idx }"
                  @click="currentVenueIdx = idx"
                ></span>
              </div>
              <button class="nav-arrow-btn" @click="nextVenue" title="下一个展厅">›</button>
            </div>
          </div>

          <div class="venue-showcase mt-10">
            <div class="venue-main-name">{{ activeVenue.name }}</div>

            <div class="venue-three-metrics">
              <div class="v-metric-item">
                <div class="v-metric-lbl">当前在场</div>
                <div class="v-metric-val highlight">{{ activeVenue.current_in_venue }}</div>
                <div class="v-metric-sub">实时动态核算</div>
              </div>
              <div class="v-metric-item">
                <div class="v-metric-lbl">累计接待</div>
                <div class="v-metric-val text-success">{{ activeVenue.total_in }}</div>
                <div class="v-metric-sub">入口累计打卡</div>
              </div>
              <div class="v-metric-item">
                <div class="v-metric-lbl">展厅饱和度</div>
                <div class="v-metric-val font-mono">{{ activeVenue.occupancy_rate }}%</div>
                <div class="v-metric-sub">容量 {{ activeVenue.capacity }} 人</div>
              </div>
            </div>

            <div class="venue-bar-wrap mt-10">
              <div class="venue-bar-track">
                <div
                  class="venue-bar-fill"
                  :style="{ width: Math.min(activeVenue.occupancy_rate, 100) + '%' }"
                ></div>
              </div>
            </div>

            <div class="rule-indicator-card mt-12">
              <div class="indicator-row">
                <span class="indicator-badge in">进</span>
                <span class="indicator-text">进入摄像头: {{ activeVenue.entry_cams_display }}</span>
              </div>
              <div class="indicator-arrow">➔ 场内流转 ➔</div>
              <div class="indicator-row">
                <span class="indicator-badge out">出</span>
                <span class="indicator-text">出去摄像头: {{ activeVenue.exit_cams_display }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card chart-box dwell-box mt-12">
          <div class="panel-header">
            <span class="panel-title">🏆 展台驻留时长排行</span>
          </div>
          <div ref="dwellRef" class="chart-canvas"></div>
        </div>
      </div>
    </div>

    <div class="ws-status-bubble" :class="connected ? 'is-online' : 'is-offline'">
      {{ connected ? '● 数据流实时连接' : '○ 通信连接中...' }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRealtimeData } from '../composables/useRealtimeData'
import { useECharts } from '../composables/useECharts'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || ''
const { data, connected } = useRealtimeData()

const globalCurrentVisitors = computed(() => {
  return data.value.current_in_venue || data.value.current_visitors || 13
})

const globalTotalIn = computed(() => {
  return data.value.total_in_today || 128
})

const globalOccupancyRate = computed(() => {
  const cap = 350
  const cur = globalCurrentVisitors.value
  return Math.round((cur / cap) * 1000) / 10
})

const globalOccupancyStatus = computed(() => {
  const r = globalOccupancyRate.value
  if (r < 50) return 'comfort'
  if (r < 80) return 'moderate'
  return 'crowded'
})

const globalOccupancyLabel = computed(() => {
  const r = globalOccupancyRate.value
  if (r < 50) return '畅通舒适'
  if (r < 80) return '客流适中'
  return '人流拥挤'
})

const venuesFromApi = ref([])
const currentVenueIdx = ref(0)
let carouselTimer = null

async function fetchVenues() {
  try {
    const res = await axios.get(`${API}/api/analytics/venues`)
    venuesFromApi.value = res.data || []
  } catch {
    venuesFromApi.value = []
  }
}

const venueList = computed(() => {
  if (data.value.venues && data.value.venues.length) {
    return data.value.venues
  }
  if (venuesFromApi.value.length) {
    return venuesFromApi.value
  }
  return [
    {
      id: 'venue_default_1',
      name: '中央综合主展厅',
      entry_cameras: ['cam_001'],
      exit_cameras: ['cam_003'],
      current_in_venue: 13,
      total_in: 128,
      capacity: 200,
      occupancy_rate: 6.5,
      zones: ['展台A', '展台B'],
    },
    {
      id: 'venue_default_2',
      name: '前沿人工智能专馆',
      entry_cameras: ['cam_001'],
      exit_cameras: ['cam_002'],
      current_in_venue: 9,
      total_in: 86,
      capacity: 150,
      occupancy_rate: 6.0,
      zones: ['AI体验区'],
    }
  ]
})

const activeVenue = computed(() => {
  const list = venueList.value
  if (!list.length) {
    return {
      name: '全馆总览',
      current_in_venue: globalCurrentVisitors.value,
      total_in: globalTotalIn.value,
      capacity: 350,
      occupancy_rate: globalOccupancyRate.value,
      rule_mode: '【1进 - 1出】',
      entry_cams_display: 'cam_001',
      exit_cams_display: 'cam_003',
    }
  }
  const safeIdx = currentVenueIdx.value % list.length
  const v = list[safeIdx]
  const inC = (v.entry_cameras || []).length || 1
  const outC = (v.exit_cameras || []).length || 1
  return {
    ...v,
    rule_mode: `【${inC}进 - ${outC}出】`,
    entry_cams_display: (v.entry_cameras && v.entry_cameras.length) ? v.entry_cameras.join(', ') : '未指定',
    exit_cams_display: (v.exit_cameras && v.exit_cameras.length) ? v.exit_cameras.join(', ') : '未指定',
  }
})

function nextVenue() {
  const len = venueList.value.length
  if (len > 0) {
    currentVenueIdx.value = (currentVenueIdx.value + 1) % len
  }
}

function prevVenue() {
  const len = venueList.value.length
  if (len > 0) {
    currentVenueIdx.value = (currentVenueIdx.value - 1 + len) % len
  }
}

function startCarousel() {
  stopCarousel()
  carouselTimer = setInterval(() => {
    nextVenue()
  }, 5000)
}

function stopCarousel() {
  if (carouselTimer) {
    clearInterval(carouselTimer)
    carouselTimer = null
  }
}

const lineRef   = ref(null)
const genderRef = ref(null)
const ageRef    = ref(null)
const dwellRef  = ref(null)

const { setOptions: setLine }   = useECharts(lineRef)
const { setOptions: setGender } = useECharts(genderRef)
const { setOptions: setAge }    = useECharts(ageRef)
const { setOptions: setDwell }  = useECharts(dwellRef)

const C = {
  blue: '#00b4ff',
  green: '#00e5a3',
  purple: '#a855f7',
  orange: '#f59e0b',
  text: '#8ba3c7',
  grid: '#1a2e4a',
}

async function renderTimeseriesChart() {
  let labels = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']
  let vals = [18, 42, 65, 50, 72, 95, 88, 60, 35]

  try {
    const res = await axios.get(`${API}/api/analytics/timeseries?interval=hour`)
    if (res.data && res.data.timeseries && res.data.timeseries.length) {
      labels = res.data.timeseries.map(d => (d.time || '').slice(-5))
      vals = res.data.timeseries.map(d => d.count)
    }
  } catch {}

  setLine({
    backgroundColor: 'transparent',
    grid: { top: 20, right: 20, bottom: 25, left: 45 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0a1628',
      borderColor: C.blue,
      textStyle: { color: '#ffffff' }
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: C.grid } },
      axisLabel: { color: C.text, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: C.grid, type: 'dashed' } },
      axisLabel: { color: C.text, fontSize: 11 },
    },
    series: [{
      name: '客流量',
      type: 'line',
      smooth: true,
      data: vals,
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: C.blue },
      lineStyle: { width: 3, color: C.blue },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(0,180,255,0.38)' },
            { offset: 1, color: 'rgba(0,180,255,0.02)' }
          ],
        },
      },
    }],
  })
}

watch(() => data.value.gender, (g) => {
  setGender({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#0a1628',
      borderColor: C.blue,
      textStyle: { color: '#fff' }
    },
    series: [{
      type: 'pie',
      radius: ['52%', '76%'],
      center: ['50%', '50%'],
      data: [
        { value: g.male, name: '男性', itemStyle: { color: C.blue } },
        { value: g.female, name: '女性', itemStyle: { color: C.purple } },
      ],
      label: { show: false },
    }],
  })
}, { immediate: true })

watch(() => data.value.age_group, (ag) => {
  const labels = ['儿童', '青年', '成年', '老年']
  const vals = [ag.child, ag.young, ag.adult, ag.elder]
  const colors = [C.green, C.blue, C.purple, C.orange]
  setAge({
    backgroundColor: 'transparent',
    grid: { top: 15, right: 15, bottom: 22, left: 35 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0a1628',
      borderColor: C.blue,
      textStyle: { color: '#fff' }
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: C.grid } },
      axisLabel: { color: C.text, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: C.grid, type: 'dashed' } },
      axisLabel: { color: C.text, fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: vals.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: [3, 3, 0, 0] } })),
      barWidth: '42%',
    }],
  })
}, { immediate: true })

async function renderDwellChart() {
  let zones = [
    { name: '展台A - AI体验区', avg_dwell_seconds: 48 },
    { name: '展台B - 智能硬件', avg_dwell_seconds: 36 },
    { name: '主舞台演播区', avg_dwell_seconds: 29 },
    { name: '生态合作展位', avg_dwell_seconds: 22 },
  ].reverse()

  try {
    const res = await axios.get(`${API}/api/analytics/dwell`)
    if (res.data && res.data.zones && res.data.zones.length) {
      zones = res.data.zones.slice(0, 5).reverse()
    }
  } catch {}

  setDwell({
    backgroundColor: 'transparent',
    grid: { top: 15, right: 40, bottom: 15, left: 95 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0a1628',
      borderColor: C.blue,
      textStyle: { color: '#fff' },
      formatter: '{b}: {c}s'
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: C.grid, type: 'dashed' } },
      axisLabel: { color: C.text, fontSize: 10, formatter: '{value}s' },
    },
    yAxis: {
      type: 'category',
      data: zones.map(z => z.name),
      axisLine: { lineStyle: { color: C.grid } },
      axisLabel: { color: '#cbd5e1', fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: zones.map(z => ({
        value: z.avg_dwell_seconds,
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [{ offset: 0, color: 'rgba(0,180,255,0.3)' }, { offset: 1, color: C.blue }],
          },
          borderRadius: [0, 4, 4, 0],
        },
      })),
      barWidth: '46%',
      label: { show: true, position: 'right', color: C.blue, formatter: '{c}s', fontSize: 11 },
    }],
  })
}

onMounted(() => {
  fetchVenues()
  renderTimeseriesChart()
  renderDwellChart()
  startCarousel()
})

onUnmounted(() => {
  stopCarousel()
})
</script>

<style scoped>
.dashboard-fullscreen {
  width: 100%;
  height: calc(100vh - 56px);
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  box-sizing: border-box;
}

.global-kpi-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  flex-shrink: 0;
  height: 98px;
}

.kpi-card {
  background: rgba(13, 27, 46, 0.85);
  border: 1px solid rgba(0, 180, 255, 0.2);
  border-radius: 8px;
  padding: 10px 18px;
  display: flex;
  flex-direction: column;
  justifyContent: space-between;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  position: relative;
  overflow: hidden;
}

.kpi-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 180, 255, 0.8), transparent);
}

.kpi-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #00e5a3;
  box-shadow: 0 0 8px #00e5a3;
  animation: pulse 1.6s infinite;
}

.kpi-badge-icon {
  font-size: 15px;
}

.kpi-title {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 500;
}

.kpi-num {
  font-size: 32px;
  font-weight: 800;
  color: #ffffff;
  line-height: 1.1;
  letter-spacing: -0.5px;
}

.kpi-num.highlight {
  color: #00e5a3;
  text-shadow: 0 0 16px rgba(0, 229, 163, 0.4);
}

.kpi-tip {
  font-size: 11px;
  color: #64748b;
}

.status-pill {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  margin-left: auto;
}

.pill-comfort {
  background: rgba(0, 229, 163, 0.15);
  color: #00e5a3;
  border: 1px solid rgba(0, 229, 163, 0.4);
}

.pill-moderate {
  background: rgba(0, 180, 255, 0.15);
  color: #00b4ff;
  border: 1px solid rgba(0, 180, 255, 0.4);
}

.pill-crowded {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.kpi-progress {
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 4px;
}

.kpi-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #00b4ff, #00e5a3);
  transition: width 0.4s ease;
}

.dashboard-body {
  flex: 1;
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 14px;
  min-height: 0;
}

.body-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.body-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.card {
  background: rgba(13, 27, 46, 0.78);
  border: 1px solid rgba(0, 180, 255, 0.18);
  border-radius: 8px;
  padding: 12px 16px;
  box-sizing: border-box;
  backdrop-filter: blur(10px);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}

.panel-tag {
  font-size: 11px;
  color: #64748b;
}

.chart-box {
  display: flex;
  flex-direction: column;
}

.trend-box {
  flex: 1.2;
  min-height: 0;
}

.chart-canvas {
  flex: 1;
  width: 100%;
  min-height: 0;
}

.bi-charts-row {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  min-height: 0;
}

.half-box {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.chart-canvas-sm {
  flex: 1;
  width: 100%;
  min-height: 0;
}

.legend-bar {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 4px;
}

.legend-item {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.dot.blue { background: #00b4ff; }
.dot.purple { background: #a855f7; }

.venue-carousel-panel {
  flex: 1.25;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(16, 32, 58, 0.9) 0%, rgba(10, 22, 40, 0.85) 100%);
  border: 1px solid rgba(0, 180, 255, 0.28);
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.flex-align-center {
  display: flex;
  align-items: center;
}

.ml-8 {
  margin-left: 8px;
}

.mt-10 { margin-top: 10px; }
.mt-12 { margin-top: 12px; }

.rule-mode-tag {
  font-size: 11px;
  color: #00e5a3;
  background: rgba(0, 229, 163, 0.12);
  border: 1px solid rgba(0, 229, 163, 0.3);
  padding: 1px 6px;
  border-radius: 3px;
}

.carousel-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-arrow-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(0, 180, 255, 0.3);
  color: #e2e8f0;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  line-height: 1;
}

.nav-arrow-btn:hover {
  background: rgba(0, 180, 255, 0.25);
  color: #00b4ff;
}

.carousel-dots {
  display: flex;
  gap: 5px;
}

.carousel-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  cursor: pointer;
}

.carousel-dot.active {
  background: #00b4ff;
  box-shadow: 0 0 6px #00b4ff;
  width: 14px;
  border-radius: 3px;
}

.venue-showcase {
  flex: 1;
  display: flex;
  flex-direction: column;
  justifyContent: space-between;
}

.venue-main-name {
  font-size: 17px;
  font-weight: 700;
  color: #38bdf8;
  letter-spacing: 0.3px;
}

.venue-three-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 8px;
}

.v-metric-item {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 8px;
  text-align: center;
}

.v-metric-lbl {
  font-size: 11px;
  color: #94a3b8;
}

.v-metric-val {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin: 3px 0;
}

.v-metric-sub {
  font-size: 10px;
  color: #64748b;
}

.venue-bar-wrap {
  width: 100%;
}

.venue-bar-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.venue-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00b4ff, #a855f7);
  transition: width 0.4s ease;
}

.rule-indicator-card {
  background: rgba(0, 0, 0, 0.35);
  border: 1px dashed rgba(0, 180, 255, 0.3);
  border-radius: 6px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.indicator-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.indicator-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
}

.indicator-badge.in {
  background: rgba(0, 229, 163, 0.2);
  color: #00e5a3;
  border: 1px solid rgba(0, 229, 163, 0.5);
}

.indicator-badge.out {
  background: rgba(244, 63, 94, 0.2);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.5);
}

.indicator-text {
  font-size: 11px;
  color: #cbd5e1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.indicator-arrow {
  font-size: 10px;
  color: #64748b;
  white-space: nowrap;
}

.dwell-box {
  flex: 1;
  min-height: 0;
}

.ws-status-bubble {
  position: fixed;
  bottom: 12px;
  right: 18px;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 12px;
  backdrop-filter: blur(8px);
  z-index: 50;
  pointer-events: none;
}

.ws-status-bubble.is-online {
  background: rgba(0, 229, 163, 0.15);
  color: #00e5a3;
  border: 1px solid rgba(0, 229, 163, 0.4);
}

.ws-status-bubble.is-offline {
  background: rgba(244, 63, 94, 0.15);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.4);
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}
</style>
