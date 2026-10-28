<template>
  <div class="dashboard-fullscreen">
    <!-- 顶部核心全局 KPI 状态栏（已删除右上角展馆环境状态，3列均分，更大气） -->
    <section class="global-kpi-bar">
      <div class="kpi-card live-card glow-card">
        <div class="kpi-meta">
          <span class="live-dot pulse"></span>
          <span class="kpi-title">当前在场人数</span>
          <span class="trend-badge text-up">实时净增</span>
        </div>
        <div class="kpi-num count-up font-mono">{{ globalCurrentVisitors }}</div>
        <div class="kpi-detail-row">
          <span>峰值预测: <b>{{ Math.round(globalCurrentVisitors * 1.35) }}</b> 人</span>
          <span>流动速率: <b>{{ flowSpeed }}</b> 人/分</span>
        </div>
      </div>

      <div class="kpi-card total-card glow-card">
        <div class="kpi-meta">
          <span class="kpi-badge-icon">📥</span>
          <span class="kpi-title">今日累计客流</span>
          <span class="trend-badge text-success">进馆总量</span>
        </div>
        <div class="kpi-num text-success count-up font-mono">{{ globalTotalIn }}</div>
        <div class="kpi-detail-row">
          <span>累计出馆: <b>{{ globalTotalOut }}</b> 人</span>
          <span>离场率: <b>{{ exitRate }}%</b></span>
        </div>
      </div>

      <div class="kpi-card occupancy-card glow-card">
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

    <!-- 主仪表盘双栏布局（左右统一高度） -->
    <div class="dashboard-body">
      <!-- 左侧区域：10分钟客流走势 + 调小后的客群画像 -->
      <div class="body-left">
        <!-- 10分钟更新一次的今日客流平滑折线走势图 -->
        <div class="card chart-box trend-box">
          <div class="panel-header flex-between">
            <div class="flex-align-center gap-8">
              <span class="panel-title">📈 今日客流走势</span>
              <span class="sub-tag">10分钟细粒度平滑曲线</span>
            </div>
            <div class="flex-align-center gap-10">
              <span class="auto-refresh-badge">
                <i class="dot green-pulse"></i> 10分钟自动刷新 ({{ refreshCountdown }}s)
              </span>
              <button class="icon-refresh-btn" @click="fetchTimeseriesData(true)" title="立即刷新走势">
                ↻
              </button>
            </div>
          </div>
          <div ref="lineRef" class="chart-canvas-lg"></div>
        </div>

        <!-- 客流分析界面调小（客群属性画像更精致紧凑） -->
        <div class="card compact-attributes-card">
          <div class="panel-header flex-between mb-8">
            <span class="panel-title">👥 客群属性分析</span>
            <span class="sub-tag">画像分布</span>
          </div>

          <div class="attributes-grid">
            <!-- 左侧：性别环形图 + 紧凑胶囊 -->
            <div class="gender-compact-col">
              <div class="gender-content-wrap">
                <div ref="genderRef" class="gender-canvas-mini"></div>
                <div class="gender-stats-pills">
                  <div class="pill-gender male">
                    <span class="ico">♂ 男</span>
                    <span class="val font-mono">{{ data.gender.male }}</span>
                    <span class="pct font-mono">{{ maleRatio }}%</span>
                  </div>
                  <div class="pill-gender female">
                    <span class="ico">♀ 女</span>
                    <span class="val font-mono">{{ data.gender.female }}</span>
                    <span class="pct font-mono">{{ 100 - maleRatio }}%</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="v-divider"></div>

            <!-- 右侧：年龄层紧凑条形分布 -->
            <div class="age-compact-col">
              <div class="age-bars-container">
                <div class="age-bar-row" v-for="item in ageDistributionList" :key="item.label">
                  <div class="age-label-name">{{ item.label }}</div>
                  <div class="age-track">
                    <div class="age-fill" :style="{ width: item.pct + '%', backgroundColor: item.color }"></div>
                  </div>
                  <div class="age-stat-val font-mono">{{ item.value }}人 <small>({{ item.pct }}%)</small></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧区域：展厅态势 + 界面调大且包含未来逐小时的天气预警 + 展馆温湿度 + 驻留时长 -->
      <div class="body-right">
        <!-- 展厅出入实时态势（已删除冗余注释，展现进入->去往展项->出去的完整链条） -->
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

          <div class="venue-showcase mt-6">
            <div class="flex-between">
              <div class="venue-main-name">{{ activeVenue.name }}</div>
              <div class="cap-small-text">容量 <b>{{ activeVenue.capacity }}</b> 人</div>
            </div>

            <!-- 核心三指标 -->
            <div class="venue-three-metrics mt-4">
              <div class="v-metric-item">
                <div class="v-metric-lbl">当前在场</div>
                <div class="v-metric-val highlight font-mono">{{ activeVenue.current_in_venue }}</div>
              </div>
              <div class="v-metric-item">
                <div class="v-metric-lbl">累计进场</div>
                <div class="v-metric-val text-success font-mono">{{ activeVenue.total_in }}</div>
              </div>
              <div class="v-metric-item">
                <div class="v-metric-lbl">饱和度</div>
                <div class="v-metric-val font-mono">{{ activeVenue.occupancy_rate }}%</div>
              </div>
            </div>

            <!-- 极简流动链路（无多余注释）：进入摄像头 ➔ 去往区域 ➔ 出去摄像头 -->
            <div class="clean-flow-pipeline mt-8">
              <div class="flow-step in-node">
                <span class="flow-badge-in">进</span>
                <span class="flow-name">{{ activeVenue.entry_cams_display }}</span>
              </div>
              <div class="flow-arrow-icon">➔</div>
              <div class="flow-step zone-node">
                <span class="flow-badge-zone">区</span>
                <span class="flow-name">{{ activeVenue.zones_display }}</span>
              </div>
              <div class="flow-arrow-icon">➔</div>
              <div class="flow-step out-node">
                <span class="flow-badge-out">出</span>
                <span class="flow-name">{{ activeVenue.exit_cams_display }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 界面调大的实时天气与预警（含未来几个小时逐小时天气） + 展馆温湿度并排 -->
        <div class="env-dual-row">
          <!-- 卡片1：实时天气与预警（界面调大，增加未来几个小时逐小时天气，城市可在配置界面修改） -->
          <div class="card weather-panel-large">
            <div class="panel-header flex-between mb-8">
              <div class="flex-align-center gap-6">
                <span class="panel-title">🌤️ 实时天气与未来预警</span>
                <span class="city-pill">{{ weatherData.city }}</span>
              </div>
              <span class="net-status-pill">● 联网同步</span>
            </div>

            <div class="weather-content">
              <!-- 当前气温与状态大字区 -->
              <div class="weather-top-row">
                <div class="weather-main-icon">{{ weatherData.icon }}</div>
                <div class="weather-temp-wrap">
                  <div class="weather-temp font-mono">{{ weatherData.temperature }}°C</div>
                  <div class="weather-cond">{{ weatherData.weather }} · 湿度 {{ weatherData.humidity }}% · {{ weatherData.wind }}</div>
                </div>
              </div>

              <!-- 未来几个小时逐小时走势横向列表（新增功能） -->
              <div class="hourly-forecast-box mt-8">
                <div class="hourly-forecast-title">未来 6 小时天气走势:</div>
                <div class="hourly-forecast-list">
                  <div class="hourly-item" v-for="h in weatherData.hourly_forecast" :key="h.time">
                    <span class="h-time">{{ h.time }}</span>
                    <span class="h-icon">{{ h.icon }}</span>
                    <span class="h-temp font-mono">{{ h.temp }}°</span>
                    <span class="h-rain">🌧️{{ h.rain_prob }}%</span>
                  </div>
                </div>
              </div>

              <!-- 气象预警监测卡片 -->
              <div class="weather-warning-box mt-8" :class="weatherData.alert_level">
                <div class="warning-title-line">
                  <span class="warning-lamp pulse"></span>
                  <span class="warning-head">{{ weatherData.alert_title }}</span>
                </div>
                <div class="warning-desc">{{ weatherData.alert_content }}</div>
              </div>
            </div>
          </div>

          <!-- 卡片2：展馆室内温湿度模块（旁边紧邻放置） -->
          <div class="card hall-sensor-panel">
            <div class="panel-header flex-between mb-8">
              <span class="panel-title">🏛️ 展馆温湿度监测</span>
              <span class="sensor-count-tag">{{ envData.sensors_online }} 探头在线</span>
            </div>

            <div class="sensor-content">
              <div class="hall-kpi-pair">
                <div class="sensor-kpi-item">
                  <div class="sensor-lbl">室内温度</div>
                  <div class="sensor-val temp-color font-mono">{{ envData.indoor_temperature }}<small>°C</small></div>
                </div>
                <div class="sensor-kpi-item">
                  <div class="sensor-lbl">室内湿度</div>
                  <div class="sensor-val hum-color font-mono">{{ envData.indoor_humidity }}<small>%RH</small></div>
                </div>
              </div>

              <div class="sensor-footer-info mt-8">
                <div class="flex-between text-xs">
                  <span class="text-dim">环境舒适度:</span>
                  <span class="comfort-text" :class="envData.comfort_level">{{ envData.comfort_status }}</span>
                </div>
                <div class="flex-between text-xs mt-4">
                  <span class="text-dim">CO₂ 浓度:</span>
                  <span class="text-warning font-mono">{{ envData.co2_ppm }} ppm</span>
                </div>
                <div class="flex-between text-xs mt-4">
                  <span class="text-dim">通讯协议:</span>
                  <span class="protocols-tag">{{ envData.active_protocols.join(' / ') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 展台驻留时长排行 -->
        <div class="card chart-box dwell-box">
          <div class="panel-header flex-between mb-4">
            <span class="panel-title">🏆 展台驻留时长排行</span>
            <span class="sub-tag">停留兴趣度</span>
          </div>
          <div ref="dwellRef" class="chart-canvas-sm"></div>
        </div>
      </div>
    </div>

    <!-- 底部右下角实时通信状态 -->
    <div class="ws-status-bubble" :class="connected ? 'is-online' : 'is-offline'">
      {{ connected ? '● 引擎推流在线' : '○ 通信连接中...' }}
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

// ── 全局核心客流指标 ──────────────────────────────────────────
const globalCurrentVisitors = computed(() => {
  return data.value.current_in_venue || data.value.current_visitors || 13
})

const globalTotalIn = computed(() => {
  return data.value.total_in_today || 128
})

const globalTotalOut = computed(() => {
  return Math.max(0, globalTotalIn.value - globalCurrentVisitors.value)
})

const exitRate = computed(() => {
  if (globalTotalIn.value === 0) return 0
  return Math.round((globalTotalOut.value / globalTotalIn.value) * 100)
})

const flowSpeed = computed(() => {
  return (Math.max(1, Math.round(globalCurrentVisitors.value * 0.18 * 10) / 10)).toFixed(1)
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

// ── 展厅出入轮播与流向 ────────────────────────────────────────
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
  if (data.value.venues && data.value.venues.length) return data.value.venues
  if (venuesFromApi.value.length) return venuesFromApi.value
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
      zones: ['展项A - AI体验区', '展项B - 智能硬件'],
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
      zones: ['AI互动展项', '算力展示区'],
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
      zones_display: '展项A, 展项B',
    }
  }
  const safeIdx = currentVenueIdx.value % list.length
  const v = list[safeIdx]
  const inC = (v.entry_cameras || []).length || 1
  const outC = (v.exit_cameras || []).length || 1
  return {
    ...v,
    rule_mode: `【${inC}进 - ${outC}出】`,
    entry_cams_display: (v.entry_cameras && v.entry_cameras.length) ? v.entry_cameras.join(', ') : '主入口南',
    exit_cams_display: (v.exit_cameras && v.exit_cameras.length) ? v.exit_cameras.join(', ') : '主出口北',
    zones_display: (v.zones && v.zones.length) ? v.zones.join(', ') : '展项A, 展项B',
  }
})

function nextVenue() {
  const len = venueList.value.length
  if (len > 0) currentVenueIdx.value = (currentVenueIdx.value + 1) % len
}
function prevVenue() {
  const len = venueList.value.length
  if (len > 0) currentVenueIdx.value = (currentVenueIdx.value - 1 + len) % len
}

// ── 天气与未来逐小时走势（增加未来几个小时预报，城市联动配置） ───
const weatherData = ref({
  city: '北京市',
  temperature: 21,
  weather: '晴朗微风',
  humidity: 45,
  wind: '微风 2级',
  icon: '☀️',
  alert_title: '气象预警监测',
  alert_content: '当前暂无极端气象预警，室内外温湿度适宜观展出行',
  alert_level: 'level-normal',
  hourly_forecast: [
    { time: '11:00', temp: 22, icon: '☀️', condition: '晴', rain_prob: 5 },
    { time: '12:00', temp: 23, icon: '☀️', condition: '晴', rain_prob: 5 },
    { time: '13:00', temp: 24, icon: '⛅', condition: '多云', rain_prob: 10 },
    { time: '14:00', temp: 23, icon: '⛅', condition: '多云', rain_prob: 15 },
    { time: '15:00', temp: 22, icon: '🌤️', condition: '晴间多云', rain_prob: 10 },
    { time: '16:00', temp: 20, icon: '🌤️', condition: '晴', rain_prob: 5 },
  ],
})

async function fetchRealWeather() {
  try {
    // 从后端获取当前配置的城市和天气（包含未来逐小时数据）
    const res = await axios.get(`${API}/api/devices/weather`)
    if (res.data) {
      weatherData.value = {
        ...weatherData.value,
        ...res.data,
      }
    }
  } catch {
    // 离线/回退处理
    weatherData.value.city = '北京市'
    weatherData.value.temperature = 22
    weatherData.value.weather = '晴间多云'
  }
}

// ── 展馆室内温湿度模块（联动探头） ───────────────────────────
const envData = ref({
  indoor_temperature: 23.4,
  indoor_humidity: 47.8,
  co2_ppm: 512,
  aqi: 26,
  comfort_status: '舒适优良',
  comfort_level: 'comfort',
  sensors_online: 2,
  active_protocols: ['TCP', 'RS485'],
})

async function fetchHallEnvironment() {
  try {
    const res = await axios.get(`${API}/api/devices/environment/latest`)
    if (res.data) {
      envData.value = {
        ...envData.value,
        ...res.data,
      }
    }
  } catch {}
}

// ── 客群属性（性别与年龄层紧凑调小） ─────────────────────────
const maleRatio = computed(() => {
  const m = data.value.gender.male || 72
  const f = data.value.gender.female || 56
  const tot = m + f
  return tot > 0 ? Math.round((m / tot) * 100) : 56
})

const ageDistributionList = computed(() => {
  const ag = data.value.age_group || { child: 18, young: 55, adult: 42, elder: 13 }
  const tot = (ag.child || 0) + (ag.young || 0) + (ag.adult || 0) + (ag.elder || 0) || 1
  return [
    { label: '儿童(0-14)', value: ag.child || 18, pct: Math.round(((ag.child || 18) / tot) * 100), color: '#00e5a3' },
    { label: '青年(15-30)', value: ag.young || 55, pct: Math.round(((ag.young || 55) / tot) * 100), color: '#00b4ff' },
    { label: '成年(31-55)', value: ag.adult || 42, pct: Math.round(((ag.adult || 42) / tot) * 100), color: '#a855f7' },
    { label: '长者(55+)', value: ag.elder || 13, pct: Math.round(((ag.elder || 13) / tot) * 100), color: '#f59e0b' },
  ]
})

// ── 图表渲染 ────────────────────────────────────────────────
const lineRef = ref(null)
const genderRef = ref(null)
const dwellRef = ref(null)

const { setOptions: setLine } = useECharts(lineRef)
const { setOptions: setGender } = useECharts(genderRef)
const { setOptions: setDwell } = useECharts(dwellRef)

const C = {
  blue: '#00b4ff',
  green: '#00e5a3',
  purple: '#a855f7',
  orange: '#f59e0b',
  text: '#8ba3c7',
  grid: '#1a2e4a',
}

// 10 分钟自动更新走势与倒计时
const refreshCountdown = ref(600)
let countdownTimer = null
let tenMinuteTimer = null

async function fetchTimeseriesData(force = false) {
  let labels = [
    '09:00', '09:10', '09:20', '09:30', '09:40', '09:50',
    '10:00', '10:10', '10:20', '10:30', '10:40', '10:50',
    '11:00', '11:10', '11:20', '11:30', '11:40', '11:50',
    '12:00', '12:10', '12:20', '12:30', '12:40', '12:50',
    '13:00', '13:10', '13:20', '13:30', '13:40', '13:50',
    '14:00', '14:10', '14:20', '14:30', '14:40', '14:50',
    '15:00', '15:10', '15:20', '15:30', '15:40', '15:50',
    '16:00', '16:10', '16:20', '16:30', '16:40', '16:50',
    '17:00'
  ]
  let inVals = [
    6, 9, 14, 18, 22, 25, 29, 32, 35, 38, 34, 31,
    36, 42, 48, 45, 39, 32, 26, 22, 25, 29, 33, 38,
    41, 44, 49, 52, 55, 58, 62, 65, 61, 57, 53, 48,
    44, 40, 36, 32, 28, 25, 21, 18, 15, 12, 10, 8, 6
  ]
  let outVals = inVals.map(v => Math.max(1, Math.round(v * 0.65)))

  try {
    const res = await axios.get(`${API}/api/analytics/timeseries?interval=10m`)
    if (res.data && res.data.series && res.data.series.length) {
      labels = res.data.series.map(d => d.time || '')
      inVals = res.data.series.map(d => d.in || d.count || 0)
      outVals = res.data.series.map(d => d.out || Math.round((d.in || 10) * 0.6))
    }
  } catch {}

  setLine({
    backgroundColor: 'transparent',
    grid: { top: 25, right: 15, bottom: 20, left: 38 },
    legend: {
      data: ['进入人数', '离场人数'],
      right: 15,
      top: 0,
      textStyle: { color: C.text, fontSize: 11 },
      icon: 'roundRect',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(10, 22, 40, 0.95)',
      borderColor: C.blue,
      textStyle: { color: '#ffffff' },
      formatter: (params) => {
        let title = params[0]?.axisValue || ''
        let res = `<div style="font-weight:bold;margin-bottom:4px;color:#00b4ff;">⏰ 时间点 ${title}</div>`
        params.forEach(p => {
          res += `<div style="font-size:12px;color:#cbd5e1;">${p.marker} ${p.seriesName}: <b>${p.value}</b> 人</div>`
        })
        return res
      }
    },
    xAxis: {
      type: 'category',
      data: labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: C.grid } },
      axisLabel: { color: C.text, fontSize: 10, interval: 4 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: C.grid, type: 'dashed' } },
      axisLabel: { color: C.text, fontSize: 10 },
    },
    series: [
      {
        name: '进入人数',
        type: 'line',
        smooth: true,
        data: inVals,
        showSymbol: false,
        symbolSize: 6,
        itemStyle: { color: C.blue },
        lineStyle: { width: 3, color: C.blue },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 180, 255, 0.45)' },
              { offset: 1, color: 'rgba(0, 180, 255, 0.02)' }
            ],
          },
        },
      },
      {
        name: '离场人数',
        type: 'line',
        smooth: true,
        data: outVals,
        showSymbol: false,
        symbolSize: 6,
        itemStyle: { color: C.green },
        lineStyle: { width: 2, color: C.green, type: 'dashed' },
      }
    ],
  })

  refreshCountdown.value = 600
}

function renderGenderMiniChart() {
  const male = data.value.gender.male || 72
  const female = data.value.gender.female || 56
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
      radius: ['62%', '88%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      data: [
        { value: male, name: '男性', itemStyle: { color: C.blue } },
        { value: female, name: '女性', itemStyle: { color: C.purple } },
      ],
      label: { show: false },
    }],
  })
}

async function renderDwellChart() {
  let zones = [
    { name: '展项A-AI体验', avg_dwell_seconds: 48 },
    { name: '展项B-智能硬件', avg_dwell_seconds: 36 },
    { name: '主舞台演播区', avg_dwell_seconds: 29 },
    { name: '生态合作展位', avg_dwell_seconds: 22 },
  ].reverse()

  try {
    const res = await axios.get(`${API}/api/analytics/dwell`)
    if (res.data && res.data.zones && res.data.zones.length) {
      zones = res.data.zones.slice(0, 4).reverse()
    }
  } catch {}

  setDwell({
    backgroundColor: 'transparent',
    grid: { top: 5, right: 35, bottom: 5, left: 95 },
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
      data: zones.map(z => z.avg_dwell_seconds),
      barWidth: '38%',
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: {
          type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: '#00b4ff' },
            { offset: 1, color: '#00e5a3' }
          ]
        }
      },
    }],
  })
}

watch(() => data.value.gender, () => {
  renderGenderMiniChart()
}, { deep: true })

onMounted(() => {
  fetchVenues()
  fetchTimeseriesData()
  fetchRealWeather()
  fetchHallEnvironment()
  renderGenderMiniChart()
  renderDwellChart()

  tenMinuteTimer = setInterval(() => {
    fetchTimeseriesData()
  }, 10 * 60 * 1000)

  countdownTimer = setInterval(() => {
    if (refreshCountdown.value > 0) {
      refreshCountdown.value--
    }
  }, 1000)

  carouselTimer = setInterval(nextVenue, 5000)

  const envTimer = setInterval(() => {
    fetchHallEnvironment()
  }, 15000)

  onUnmounted(() => {
    if (tenMinuteTimer) clearInterval(tenMinuteTimer)
    if (countdownTimer) clearInterval(countdownTimer)
    if (carouselTimer) clearInterval(carouselTimer)
    clearInterval(envTimer)
  })
})
</script>

<style scoped>
.dashboard-fullscreen {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 14px 18px;
  gap: 14px;
  overflow-y: auto;
  box-sizing: border-box;
}

/* ── 顶部全局 3 列 KPI 栏 ───────────────────── */
.global-kpi-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.kpi-card {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(0, 180, 255, 0.18);
  border-radius: 12px;
  padding: 12px 18px;
  backdrop-filter: blur(8px);
  position: relative;
  transition: transform 0.25s ease, border-color 0.25s ease;
}
.kpi-card:hover {
  transform: translateY(-2px);
  border-color: rgba(0, 180, 255, 0.45);
}

.glow-card::after {
  content: '';
  position: absolute;
  top: 0; left: 15%; right: 15%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 180, 255, 0.5), transparent);
}

.kpi-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #94a3b8;
}

.kpi-num {
  font-size: 32px;
  font-weight: 800;
  color: #ffffff;
  margin: 4px 0 2px;
  letter-spacing: -0.02em;
}

.kpi-detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}
.kpi-detail-row b {
  color: #cbd5e1;
}

.trend-badge {
  margin-left: auto;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0, 180, 255, 0.12);
  color: #00b4ff;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00e5a3;
  box-shadow: 0 0 8px #00e5a3;
}

.kpi-progress {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 8px;
}
.kpi-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #00b4ff, #00e5a3);
  border-radius: 3px;
  transition: width 0.6s ease;
}

/* ── 主面板双栏（统一整体高度） ──────────────── */
.dashboard-body {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 14px;
  flex: 1;
}

.body-left, .body-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(0, 180, 255, 0.16);
  border-radius: 12px;
  padding: 12px 16px;
  backdrop-filter: blur(8px);
}

.panel-header {
  display: flex;
  align-items: center;
}
.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #f1f5f9;
}
.sub-tag {
  font-size: 11px;
  color: #64748b;
  margin-left: 6px;
}

.auto-refresh-badge {
  font-size: 11px;
  color: #00e5a3;
  background: rgba(0, 229, 163, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.green-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00e5a3;
  box-shadow: 0 0 6px #00e5a3;
}

.icon-refresh-btn {
  background: transparent;
  border: 1px solid rgba(0, 180, 255, 0.3);
  color: #00b4ff;
  border-radius: 6px;
  padding: 2px 7px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.icon-refresh-btn:hover {
  background: rgba(0, 180, 255, 0.2);
}

.chart-canvas-lg {
  width: 100%;
  height: 255px;
}
.chart-canvas-sm {
  width: 100%;
  height: 120px;
}

/* ── 客流分析调小（客群属性精致紧凑） ─────────── */
.compact-attributes-card {
  padding: 10px 14px;
}
.attributes-grid {
  display: grid;
  grid-template-columns: 1fr auto 1.35fr;
  gap: 12px;
  align-items: center;
}
.v-divider {
  width: 1px;
  height: 75px;
  background: rgba(255, 255, 255, 0.08);
}

.gender-content-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.gender-canvas-mini {
  width: 78px;
  height: 78px;
  flex-shrink: 0;
}
.gender-stats-pills {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.pill-gender {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 11px;
}
.pill-gender.male {
  background: rgba(0, 180, 255, 0.12);
  color: #00b4ff;
}
.pill-gender.female {
  background: rgba(168, 85, 247, 0.12);
  color: #c084fc;
}
.pill-gender .val {
  font-weight: 700;
  margin-left: auto;
}
.pill-gender .pct {
  font-size: 10px;
  opacity: 0.8;
}

.age-bars-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.age-bar-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
}
.age-label-name {
  width: 68px;
  color: #94a3b8;
  font-size: 10px;
}
.age-track {
  flex: 1;
  height: 5px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}
.age-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}
.age-stat-val {
  width: 64px;
  text-align: right;
  color: #f1f5f9;
  font-size: 10px;
}

/* ── 展厅出入实时态势 ───────────────────────── */
.venue-main-name {
  font-size: 14px;
  font-weight: 700;
  color: #00b4ff;
}
.cap-small-text {
  font-size: 11px;
  color: #64748b;
}
.cap-small-text b { color: #00e5a3; }

.venue-three-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.v-metric-item {
  background: rgba(30, 41, 59, 0.45);
  border-radius: 6px;
  padding: 6px;
  text-align: center;
}
.v-metric-lbl {
  font-size: 10px;
  color: #64748b;
}
.v-metric-val {
  font-size: 16px;
  font-weight: 800;
  color: #ffffff;
}

.clean-flow-pipeline {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(10, 18, 32, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 11px;
}
.flow-step {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.flow-badge-in {
  background: #00b4ff;
  color: #030712;
  font-size: 9px;
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 3px;
}
.flow-badge-zone {
  background: #a855f7;
  color: #ffffff;
  font-size: 9px;
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 3px;
}
.flow-badge-out {
  background: #00e5a3;
  color: #030712;
  font-size: 9px;
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 3px;
}
.flow-name {
  color: #e2e8f0;
  font-size: 10px;
}
.flow-arrow-icon {
  color: #64748b;
  font-size: 10px;
}

/* ── 界面调大的实时天气（含未来几个小时逐小时） ──── */
.env-dual-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 12px;
}

.weather-panel-large, .hall-sensor-panel {
  padding: 10px 14px;
}
.city-pill {
  font-size: 10px;
  background: rgba(0, 180, 255, 0.15);
  color: #00b4ff;
  padding: 1px 6px;
  border-radius: 4px;
}
.net-status-pill {
  font-size: 10px;
  color: #00e5a3;
}

.weather-top-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.weather-main-icon {
  font-size: 28px;
}
.weather-temp {
  font-size: 20px;
  font-weight: 800;
  color: #ffffff;
}
.weather-cond {
  font-size: 11px;
  color: #94a3b8;
}

/* 未来逐小时预报条 */
.hourly-forecast-box {
  background: rgba(10, 18, 32, 0.55);
  border-radius: 6px;
  padding: 6px 8px;
}
.hourly-forecast-title {
  font-size: 10px;
  color: #64748b;
  margin-bottom: 4px;
}
.hourly-forecast-list {
  display: flex;
  justify-content: space-between;
  gap: 4px;
}
.hourly-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex: 1;
}
.h-time {
  font-size: 9px;
  color: #94a3b8;
}
.h-icon {
  font-size: 14px;
}
.h-temp {
  font-size: 11px;
  color: #ffffff;
  font-weight: 700;
}
.h-rain {
  font-size: 9px;
  color: #38bdf8;
}

.weather-warning-box {
  border-radius: 6px;
  padding: 5px 8px;
  border-left: 3px solid;
}
.weather-warning-box.level-normal {
  background: rgba(0, 229, 163, 0.08);
  border-left-color: #00e5a3;
}
.weather-warning-box.level-warning {
  background: rgba(245, 158, 11, 0.12);
  border-left-color: #f59e0b;
}
.warning-title-line {
  display: flex;
  align-items: center;
  gap: 6px;
}
.warning-lamp {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.warning-head {
  font-size: 10px;
  font-weight: 700;
  color: #f1f5f9;
}
.warning-desc {
  font-size: 9px;
  color: #94a3b8;
  margin-top: 1px;
  line-height: 1.25;
}

.hall-kpi-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.sensor-kpi-item {
  background: rgba(30, 41, 59, 0.5);
  padding: 6px 8px;
  border-radius: 6px;
}
.sensor-lbl {
  font-size: 10px;
  color: #64748b;
}
.sensor-val {
  font-size: 16px;
  font-weight: 800;
  margin-top: 2px;
}
.sensor-val small {
  font-size: 10px;
  font-weight: normal;
  margin-left: 2px;
}
.temp-color { color: #00b4ff; }
.hum-color { color: #00e5a3; }

.sensor-count-tag {
  font-size: 10px;
  color: #00e5a3;
  background: rgba(0, 229, 163, 0.1);
  padding: 1px 5px;
  border-radius: 4px;
}
.protocols-tag {
  color: #00b4ff;
  font-weight: 600;
}
.comfort-text.comfort { color: #00e5a3; }
.comfort-text.warning { color: #f59e0b; }

/* ── 轮播控制与通用组件 ─────────────────────── */
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.flex-align-center { display: flex; align-items: center; }
.gap-4 { gap: 4px; }
.gap-6 { gap: 6px; }
.gap-8 { gap: 8px; }
.gap-10 { gap: 10px; }
.mt-2 { margin-top: 2px; }
.mt-4 { margin-top: 4px; }
.mt-6 { margin-top: 6px; }
.mt-8 { margin-top: 8px; }
.mt-10 { margin-top: 10px; }
.mt-12 { margin-top: 12px; }
.mb-4 { margin-bottom: 4px; }
.mb-6 { margin-bottom: 6px; }
.mb-8 { margin-bottom: 8px; }
.ml-8 { margin-left: 8px; }

.rule-mode-tag {
  font-size: 10px;
  background: rgba(0, 180, 255, 0.15);
  color: #00b4ff;
  padding: 1px 5px;
  border-radius: 4px;
}
.carousel-nav {
  display: flex;
  align-items: center;
  gap: 5px;
}
.nav-arrow-btn {
  background: rgba(255, 255, 255, 0.08);
  border: none;
  color: #ffffff;
  border-radius: 4px;
  padding: 1px 6px;
  cursor: pointer;
}
.carousel-dots {
  display: flex;
  gap: 3px;
}
.carousel-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  cursor: pointer;
}
.carousel-dot.active {
  background: #00b4ff;
}

.status-pill {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}
.pill-comfort { background: rgba(0, 229, 163, 0.15); color: #00e5a3; }
.pill-moderate { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.pill-crowded { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

.ws-status-bubble {
  position: fixed;
  bottom: 12px;
  right: 16px;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 12px;
  background: rgba(10, 22, 40, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(6px);
  z-index: 99;
}
.ws-status-bubble.is-online { color: #00e5a3; }
.ws-status-bubble.is-offline { color: #f59e0b; }
</style>
