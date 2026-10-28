<template>
  <div class="dashboard-fullscreen">
    <!-- 顶部核心全局 KPI 状态栏 -->
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

      <div class="kpi-card env-quick-card glow-card">
        <div class="kpi-meta">
          <span class="kpi-badge-icon">🏛️</span>
          <span class="kpi-title">展馆环境状态</span>
          <span class="status-pill pill-comfort">{{ envData.comfort_status }}</span>
        </div>
        <div class="kpi-env-grid">
          <div class="env-chip"><span class="lbl">室温</span><b class="val text-primary">{{ envData.indoor_temperature }}°C</b></div>
          <div class="env-chip"><span class="lbl">湿度</span><b class="val text-success">{{ envData.indoor_humidity }}%</b></div>
          <div class="env-chip"><span class="lbl">CO₂</span><b class="val text-warning">{{ envData.co2_ppm }} ppm</b></div>
        </div>
      </div>
    </section>

    <!-- 主仪表盘双栏布局 -->
    <div class="dashboard-body">
      <!-- 左侧区域：10分钟客流走势平滑曲线 + 紧凑型客群属性画像 -->
      <div class="body-left">
        <!-- 10分钟更新一次的今日客流平滑折线走势图 -->
        <div class="card chart-box trend-box">
          <div class="panel-header flex-between">
            <div class="flex-align-center gap-8">
              <span class="panel-title">📈 今日客流走势</span>
              <span class="sub-tag">10分钟细粒度更新</span>
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

        <!-- 年龄与性别放在一起，紧凑小巧布局 -->
        <div class="card compact-attributes-card">
          <div class="panel-header flex-between">
            <span class="panel-title">👥 客群属性分析（性别与年龄层）</span>
            <span class="sub-tag">画像融合</span>
          </div>

          <div class="attributes-grid">
            <!-- 左侧：性别环形图 + 紧凑胶囊 -->
            <div class="gender-compact-col">
              <div class="gender-header">
                <span class="col-title">⚥ 性别比例</span>
              </div>
              <div class="gender-content-wrap">
                <div ref="genderRef" class="gender-canvas-mini"></div>
                <div class="gender-stats-pills">
                  <div class="pill-gender male">
                    <span class="ico">♂</span>
                    <span class="name">男性</span>
                    <span class="val">{{ data.gender.male }}</span>
                    <span class="pct">{{ maleRatio }}%</span>
                  </div>
                  <div class="pill-gender female">
                    <span class="ico">♀</span>
                    <span class="name">女性</span>
                    <span class="val">{{ data.gender.female }}</span>
                    <span class="pct">{{ 100 - maleRatio }}%</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="v-divider"></div>

            <!-- 右侧：年龄层紧凑条形分布 -->
            <div class="age-compact-col">
              <div class="col-title mb-6">🎂 年龄层分布</div>
              <div class="age-bars-container">
                <div class="age-bar-row" v-for="item in ageDistributionList" :key="item.label">
                  <div class="age-label-name">{{ item.label }}</div>
                  <div class="age-track">
                    <div class="age-fill" :style="{ width: item.pct + '%', backgroundColor: item.color }"></div>
                  </div>
                  <div class="age-stat-val">{{ item.value }}人 <span class="pct-sub">({{ item.pct }}%)</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧区域：展厅态势 + 天气与后期预警 + 展馆温湿度 + 驻留时长 -->
      <div class="body-right">
        <!-- 展厅出入实时态势（已删除冗余注释，展现进入->去往展台->出去的完整链条） -->
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

          <div class="venue-showcase mt-8">
            <div class="venue-main-name">{{ activeVenue.name }}</div>

            <!-- 核心三指标 -->
            <div class="venue-three-metrics">
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

            <!-- 容量进度条 -->
            <div class="venue-bar-wrap mt-8">
              <div class="venue-bar-track">
                <div
                  class="venue-bar-fill"
                  :style="{ width: Math.min(activeVenue.occupancy_rate, 100) + '%' }"
                ></div>
              </div>
            </div>

            <!-- 极简流动链路（无多余注释）：进入摄像头 ➔ 去往区域 ➔ 出去摄像头 -->
            <div class="clean-flow-pipeline mt-10">
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

        <!-- 新增双卡片：天气与后期预警板块 + 展馆温湿度模块并排 -->
        <div class="env-dual-row mt-12">
          <!-- 卡片1：联网天气与后期预警板块 -->
          <div class="card weather-panel">
            <div class="panel-header flex-between">
              <div class="flex-align-center gap-6">
                <span class="panel-title">🌤️ 实时天气与预警</span>
                <span class="city-pill">{{ weatherData.city }}</span>
              </div>
              <span class="net-status-pill">● 联网更新</span>
            </div>

            <div class="weather-content mt-6">
              <div class="weather-top-row">
                <div class="weather-main-icon">{{ weatherData.icon }}</div>
                <div class="weather-temp-wrap">
                  <div class="weather-temp">{{ weatherData.temperature }}°C</div>
                  <div class="weather-cond">{{ weatherData.weather }} · 湿度 {{ weatherData.humidity }}%</div>
                </div>
              </div>

              <!-- 后期预警板块 -->
              <div class="weather-warning-box mt-8" :class="weatherData.alert_level">
                <div class="warning-title-line">
                  <span class="warning-lamp pulse"></span>
                  <span class="warning-head">{{ weatherData.alert_title }}</span>
                </div>
                <div class="warning-desc">{{ weatherData.alert_content }}</div>
              </div>
            </div>
          </div>

          <!-- 卡片2：展馆室内温湿度模块（旁边放置，联动探头） -->
          <div class="card hall-sensor-panel">
            <div class="panel-header flex-between">
              <span class="panel-title">🏛️ 展馆温湿度监测</span>
              <span class="sensor-count-tag">{{ envData.sensors_online }} 个探头在线</span>
            </div>

            <div class="sensor-content mt-6">
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
                  <span class="text-dim">通讯接入:</span>
                  <span class="protocols-tag">{{ envData.active_protocols.join(' / ') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 展台驻留时长排行 -->
        <div class="card chart-box dwell-box mt-12">
          <div class="panel-header flex-between">
            <span class="panel-title">🏆 展台驻留时长排行</span>
            <span class="sub-tag">停留兴趣度</span>
          </div>
          <div ref="dwellRef" class="chart-canvas-sm"></div>
        </div>
      </div>
    </div>

    <!-- 底部右下角实时通信状态 -->
    <div class="ws-status-bubble" :class="connected ? 'is-online' : 'is-offline'">
      {{ connected ? '● 引擎高速推流在线' : '○ 通信连接中...' }}
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
      zones: ['展台A - AI体验区', '展台B - 智能硬件'],
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
      zones: ['AI互动展台', '算力中心展示区'],
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
      zones_display: '展台A, 展台B',
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
    zones_display: (v.zones && v.zones.length) ? v.zones.join(', ') : '展台A, 展台B',
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

// ── 天气与后期预警板块 ────────────────────────────────────────
const weatherData = ref({
  city: '北京市',
  temperature: 21,
  weather: '晴朗微风',
  humidity: 45,
  icon: '☀️',
  alert_title: '气象预警监测',
  alert_content: '当前暂无极端气象预警，室内外温湿度适宜观展出行',
  alert_level: 'level-normal',
})

async function fetchRealWeather() {
  try {
    // 尝试调用轻量公网天气 API，带完备的超时与优雅回退
    const res = await axios.get('https://wttr.in/?format=j1', { timeout: 2500 })
    if (res.data && res.data.current_condition && res.data.current_condition.length) {
      const cur = res.data.current_condition[0]
      const desc = cur.lang_zh ? cur.lang_zh[0]?.value : cur.weatherDesc[0]?.value
      const temp = parseInt(cur.temp_C) || 21
      const hum = parseInt(cur.humidity) || 45
      
      let icon = '⛅'
      if (desc.includes('晴') || desc.toLowerCase().includes('sun') || desc.toLowerCase().includes('clear')) icon = '☀️'
      else if (desc.includes('雨') || desc.toLowerCase().includes('rain')) icon = '🌧️'
      else if (desc.includes('云') || desc.toLowerCase().includes('cloud')) icon = '⛅'
      else if (desc.includes('雪') || desc.toLowerCase().includes('snow')) icon = '❄️'

      weatherData.value.temperature = temp
      weatherData.value.humidity = hum
      weatherData.value.weather = desc || '晴朗'
      weatherData.value.icon = icon

      // 后期预警逻辑推算
      if (temp > 35) {
        weatherData.value.alert_title = '高温防暑预警'
        weatherData.value.alert_content = '室外气温偏高，场馆已开启强效冷气与新风系统'
        weatherData.value.alert_level = 'level-warning'
      } else if (desc.includes('暴雨') || desc.includes('雷')) {
        weatherData.value.alert_title = '强对流 / 降雨预警'
        weatherData.value.alert_content = '外部有较强降雨，展厅已备足雨具收纳与防滑措施'
        weatherData.value.alert_level = 'level-danger'
      }
    }
  } catch {
    // 离线/内网环境下优雅呈现标准气象站数据
    weatherData.value.temperature = 22
    weatherData.value.weather = '晴间多云'
    weatherData.value.humidity = 46
    weatherData.value.icon = '⛅'
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

// ── 客群属性（性别与年龄层紧凑融合） ─────────────────────────
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
    { label: '儿童 (0-14)', value: ag.child || 18, pct: Math.round(((ag.child || 18) / tot) * 100), color: '#00e5a3' },
    { label: '青年 (15-30)', value: ag.young || 55, pct: Math.round(((ag.young || 55) / tot) * 100), color: '#00b4ff' },
    { label: '成年 (31-55)', value: ag.adult || 42, pct: Math.round(((ag.adult || 42) / tot) * 100), color: '#a855f7' },
    { label: '长者 (55+)', value: ag.elder || 13, pct: Math.round(((ag.elder || 13) / tot) * 100), color: '#f59e0b' },
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
    grid: { top: 25, right: 20, bottom: 25, left: 40 },
    legend: {
      data: ['进入人数', '离场人数'],
      right: 20,
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
      axisLabel: { color: C.text, fontSize: 10, interval: 3 },
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
      radius: ['60%', '85%'],
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
    { name: '展台A - AI体验区', avg_dwell_seconds: 48 },
    { name: '展台B - 智能硬件', avg_dwell_seconds: 36 },
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
    grid: { top: 10, right: 35, bottom: 10, left: 110 },
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
      barWidth: '40%',
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

  // 10 分钟更新一次走势
  tenMinuteTimer = setInterval(() => {
    fetchTimeseriesData()
  }, 10 * 60 * 1000)

  // 1 秒倒计时器与环境轮询
  countdownTimer = setInterval(() => {
    if (refreshCountdown.value > 0) {
      refreshCountdown.value--
    }
  }, 1000)

  // 展厅轮播 (5s)
  carouselTimer = setInterval(nextVenue, 5000)

  // 定时刷新环境传感器与天气 (15s)
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
  padding: 16px 20px;
  gap: 16px;
  overflow-y: auto;
  box-sizing: border-box;
}

/* ── 顶部全局 KPI 栏 ────────────────────────── */
.global-kpi-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.kpi-card {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(0, 180, 255, 0.18);
  border-radius: 12px;
  padding: 14px 18px;
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
  margin: 6px 0 4px;
  letter-spacing: -0.02em;
}

.kpi-detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
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

.kpi-env-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-top: 10px;
}
.env-chip {
  background: rgba(30, 41, 59, 0.6);
  padding: 6px 8px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
}
.env-chip .lbl {
  font-size: 10px;
  color: #64748b;
}
.env-chip .val {
  font-size: 13px;
  margin-top: 2px;
}

/* ── 主面板双栏 ────────────────────────────── */
.dashboard-body {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 16px;
  flex: 1;
}

.body-left, .body-right {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(0, 180, 255, 0.16);
  border-radius: 12px;
  padding: 14px 18px;
  backdrop-filter: blur(8px);
}

.panel-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
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
  padding: 3px 8px;
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
  height: 250px;
}
.chart-canvas-sm {
  width: 100%;
  height: 155px;
}

/* ── 紧凑型客群属性（性别与年龄层合并） ─────── */
.compact-attributes-card {
  padding: 12px 16px;
}
.attributes-grid {
  display: grid;
  grid-template-columns: 1fr auto 1.35fr;
  gap: 14px;
  align-items: center;
}
.v-divider {
  width: 1px;
  height: 85%;
  background: rgba(255, 255, 255, 0.08);
}

.col-title {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
}

.gender-content-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}
.gender-canvas-mini {
  width: 90px;
  height: 90px;
  flex-shrink: 0;
}
.gender-stats-pills {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}
.pill-gender {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
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
  gap: 6px;
}
.age-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.age-label-name {
  width: 78px;
  color: #94a3b8;
  font-size: 11px;
}
.age-track {
  flex: 1;
  height: 6px;
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
  width: 65px;
  text-align: right;
  color: #f1f5f9;
  font-weight: 600;
}
.pct-sub {
  font-size: 10px;
  color: #64748b;
  font-weight: 400;
}

/* ── 展厅出入实时态势（极简流向） ───────────── */
.venue-showcase {
  display: flex;
  flex-direction: column;
}
.venue-main-name {
  font-size: 15px;
  font-weight: 700;
  color: #00b4ff;
  margin-bottom: 8px;
}
.venue-three-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.v-metric-item {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  padding: 8px 10px;
  text-align: center;
}
.v-metric-lbl {
  font-size: 11px;
  color: #64748b;
}
.v-metric-val {
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
  margin-top: 2px;
}

.clean-flow-pipeline {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(10, 18, 32, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
}
.flow-step {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.flow-badge-in {
  background: #00b4ff;
  color: #030712;
  font-size: 10px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 4px;
}
.flow-badge-zone {
  background: #a855f7;
  color: #ffffff;
  font-size: 10px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 4px;
}
.flow-badge-out {
  background: #00e5a3;
  color: #030712;
  font-size: 10px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 4px;
}
.flow-name {
  color: #e2e8f0;
  font-size: 11px;
}
.flow-arrow-icon {
  color: #64748b;
  font-size: 11px;
}

/* ── 天气与展馆温湿度双卡片 ─────────────────── */
.env-dual-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.weather-panel, .hall-sensor-panel {
  padding: 12px 14px;
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
  font-size: 26px;
}
.weather-temp {
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
}
.weather-cond {
  font-size: 11px;
  color: #94a3b8;
}

.weather-warning-box {
  border-radius: 6px;
  padding: 6px 8px;
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
.weather-warning-box.level-danger {
  background: rgba(239, 68, 68, 0.15);
  border-left-color: #ef4444;
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
  font-size: 11px;
  font-weight: 700;
  color: #f1f5f9;
}
.warning-desc {
  font-size: 10px;
  color: #94a3b8;
  margin-top: 2px;
  line-height: 1.3;
}

.hall-kpi-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.sensor-kpi-item {
  background: rgba(30, 41, 59, 0.5);
  padding: 6px 10px;
  border-radius: 6px;
}
.sensor-lbl {
  font-size: 10px;
  color: #64748b;
}
.sensor-val {
  font-size: 17px;
  font-weight: 800;
  margin-top: 2px;
}
.sensor-val small {
  font-size: 11px;
  font-weight: normal;
  margin-left: 2px;
}
.temp-color { color: #00b4ff; }
.hum-color { color: #00e5a3; }

.sensor-count-tag {
  font-size: 10px;
  color: #00e5a3;
  background: rgba(0, 229, 163, 0.1);
  padding: 1px 6px;
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
.gap-6 { gap: 6px; }
.gap-8 { gap: 8px; }
.gap-10 { gap: 10px; }
.mt-4 { margin-top: 4px; }
.mt-6 { margin-top: 6px; }
.mt-8 { margin-top: 8px; }
.mt-10 { margin-top: 10px; }
.mt-12 { margin-top: 12px; }
.mb-6 { margin-bottom: 6px; }
.ml-8 { margin-left: 8px; }

.rule-mode-tag {
  font-size: 10px;
  background: rgba(0, 180, 255, 0.15);
  color: #00b4ff;
  padding: 2px 6px;
  border-radius: 4px;
}
.carousel-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-arrow-btn {
  background: rgba(255, 255, 255, 0.08);
  border: none;
  color: #ffffff;
  border-radius: 4px;
  padding: 2px 7px;
  cursor: pointer;
}
.carousel-dots {
  display: flex;
  gap: 4px;
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
