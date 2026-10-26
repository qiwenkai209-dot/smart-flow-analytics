<template>
  <div class="dashboard">

    <!-- ── 顶部 KPI 指标卡 ──────────────────── -->
    <section class="kpi-row">
      <div class="card kpi-card" v-for="kpi in kpiCards" :key="kpi.label">
        <div class="kpi-icon">{{ kpi.icon }}</div>
        <div>
          <div class="stat-value count-up">{{ kpi.value }}</div>
          <div class="stat-label">{{ kpi.label }}</div>
        </div>
        <div class="kpi-trend" :class="kpi.trendClass">{{ kpi.trend }}</div>
      </div>
    </section>

    <!-- ── 主图表区 ──────────────────────────── -->
    <section class="charts-grid">

      <!-- 客流时序折线图 -->
      <div class="card chart-wide">
        <div class="card-title">📈 今日客流走势（每小时）</div>
        <div ref="lineRef" class="chart-container"></div>
      </div>

      <!-- 性别比例饼图 -->
      <div class="card chart-sm">
        <div class="card-title">👥 性别分布</div>
        <div ref="genderRef" class="chart-container-sm"></div>
        <div class="legend-row">
          <span class="legend-dot" style="background:#00b4ff"></span>男性
          <span class="legend-val">{{ data.gender.male }}</span>
          <span class="legend-dot" style="background:#a855f7"></span>女性
          <span class="legend-val">{{ data.gender.female }}</span>
        </div>
      </div>

      <!-- 年龄层柱状图 -->
      <div class="card chart-sm">
        <div class="card-title">🎂 年龄层分布</div>
        <div ref="ageRef" class="chart-container-sm"></div>
      </div>

      <!-- 展台驻留排行 -->
      <div class="card chart-wide">
        <div class="card-title">🏆 展台吸引力排行（平均驻留时长）</div>
        <div ref="dwellRef" class="chart-container"></div>
      </div>

    </section>

    <!-- ── 底部展台实时状态 ─────────────────── -->
    <section class="zone-status-row">
      <div class="card zone-card" v-for="zone in zoneList" :key="zone.name">
        <div class="zone-name">{{ zone.name }}</div>
        <div class="zone-visitors">
          <span class="stat-value" style="font-size:28px">{{ zone.current_visitors }}</span>
          <span class="zone-unit">人在场</span>
        </div>
        <div class="zone-meta">
          平均驻留 <b>{{ zone.avg_dwell }}s</b>
        </div>
        <div class="zone-bar">
          <div class="zone-bar-fill" :style="{ width: Math.min(zone.avg_dwell / 120 * 100, 100) + '%' }"></div>
        </div>
      </div>
    </section>

    <!-- WS 连接状态指示 -->
    <div class="ws-status" :class="connected ? 'ws-online' : 'ws-offline'">
      {{ connected ? '● 实时数据' : '○ 重连中...' }}
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRealtimeData } from '../composables/useRealtimeData'
import { useECharts } from '../composables/useECharts'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── 实时数据 ───────────────────────────────────
const { data, connected } = useRealtimeData()

const kpiCards = computed(() => [
  {
    icon: '🚶',
    value: data.value.current_in_venue,
    label: '当前在场人数',
    trend: '+3 较昨日',
    trendClass: 'trend-up',
  },
  {
    icon: '📥',
    value: data.value.total_in_today,
    label: '今日累计入场',
    trend: '+12% 较昨日',
    trendClass: 'trend-up',
  },
  {
    icon: '📤',
    value: data.value.total_out_today,
    label: '今日累计离场',
    trend: '',
    trendClass: '',
  },
  {
    icon: '⏱️',
    value: avgDwell.value + 's',
    label: '展台平均驻留',
    trend: '+8s 较昨日',
    trendClass: 'trend-up',
  },
])

const avgDwell = computed(() => {
  const zones = data.value.zone_dwell || []
  if (!zones.length) return 0
  return Math.round(zones.reduce((s, z) => s + z.avg_dwell, 0) / zones.length)
})

const zoneList = computed(() => data.value.zone_dwell || [])

// ── 图表 ────────────────────────────────────────
const lineRef   = ref(null)
const genderRef = ref(null)
const ageRef    = ref(null)
const dwellRef  = ref(null)

const { setOption: setLine   } = useECharts(lineRef)
const { setOption: setGender } = useECharts(genderRef)
const { setOption: setAge    } = useECharts(ageRef)
const { setOption: setDwell  } = useECharts(dwellRef)

// 颜色系统
const C = {
  blue:   '#00b4ff',
  purple: '#a855f7',
  green:  '#10d97a',
  orange: '#f59e0b',
  red:    '#ef4444',
  text:   '#7ea8c4',
  grid:   'rgba(0,180,255,0.08)',
}

// ── 时序折线图 ─────────────────────────────────
async function loadTimeseries() {
  const res = await axios.get(`${API}/api/analytics/timeseries`).catch(() => ({ data: { series: [] } }))
  const series = res.data.series || []
  setLine({
    backgroundColor: 'transparent',
    grid: { top: 20, right: 20, bottom: 30, left: 50 },
    tooltip: { trigger: 'axis', backgroundColor: '#0a1628', borderColor: C.blue, textStyle: { color: C.text } },
    legend: { data: ['入场', '离场'], textStyle: { color: C.text }, right: 0, top: 0 },
    xAxis: {
      type: 'category',
      data: series.map(s => s.time),
      axisLine: { lineStyle: { color: C.grid } },
      axisLabel: { color: C.text },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: C.grid } },
      axisLabel: { color: C.text },
    },
    series: [
      {
        name: '入场', type: 'line', smooth: true,
        data: series.map(s => s.in),
        lineStyle: { color: C.blue, width: 2 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,180,255,0.3)' }, { offset: 1, color: 'transparent' }] } },
        symbol: 'circle', symbolSize: 5, itemStyle: { color: C.blue },
      },
      {
        name: '离场', type: 'line', smooth: true,
        data: series.map(s => s.out),
        lineStyle: { color: C.purple, width: 2 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(168,85,247,0.2)' }, { offset: 1, color: 'transparent' }] } },
        symbol: 'circle', symbolSize: 5, itemStyle: { color: C.purple },
      },
    ],
  })
}

// ── 性别饼图 ────────────────────────────────────
watch(() => data.value.gender, (g) => {
  setGender({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: '#0a1628', borderColor: C.blue, textStyle: { color: C.text } },
    series: [{
      type: 'pie', radius: ['50%', '75%'], center: ['50%', '50%'],
      data: [
        { value: g.male,   name: '男性', itemStyle: { color: C.blue   } },
        { value: g.female, name: '女性', itemStyle: { color: C.purple } },
      ],
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: C.blue } },
    }],
  })
}, { immediate: true })

// ── 年龄层柱状图 ────────────────────────────────
watch(() => data.value.age_group, (ag) => {
  const labels = ['儿童', '青年', '成年', '老年']
  const vals   = [ag.child, ag.young, ag.adult, ag.elder]
  const colors = [C.green, C.blue, C.purple, C.orange]
  setAge({
    backgroundColor: 'transparent',
    grid: { top: 10, right: 10, bottom: 30, left: 45 },
    tooltip: { trigger: 'axis', backgroundColor: '#0a1628', borderColor: C.blue, textStyle: { color: C.text } },
    xAxis: { type: 'category', data: labels, axisLabel: { color: C.text }, axisLine: { lineStyle: { color: C.grid } } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: C.grid } }, axisLabel: { color: C.text } },
    series: [{
      type: 'bar', data: vals.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: [4, 4, 0, 0] } })),
    }],
  })
}, { immediate: true })

// ── 驻留排行水平条形图 ──────────────────────────
async function loadDwellStats() {
  const res = await axios.get(`${API}/api/analytics/dwell`).catch(() => ({ data: { zones: [] } }))
  const zones = (res.data.zones || []).sort((a, b) => b.avg_dwell_seconds - a.avg_dwell_seconds)
  setDwell({
    backgroundColor: 'transparent',
    grid: { top: 10, right: 80, bottom: 20, left: 80 },
    tooltip: { trigger: 'axis', formatter: '{b}: {c}s', backgroundColor: '#0a1628', borderColor: C.blue, textStyle: { color: C.text } },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: C.grid } }, axisLabel: { color: C.text, formatter: '{value}s' } },
    yAxis: { type: 'category', data: zones.map(z => z.name), axisLabel: { color: C.text } },
    series: [{
      type: 'bar',
      data: zones.map(z => ({
        value: z.avg_dwell_seconds,
        itemStyle: {
          color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: 'rgba(0,180,255,0.4)' }, { offset: 1, color: C.blue }] },
          borderRadius: [0, 4, 4, 0],
        },
      })),
      label: { show: true, position: 'right', formatter: '{c}s', color: C.text },
    }],
  })
}

onMounted(() => {
  loadTimeseries()
  loadDwellStats()
  // 每60秒刷新一次静态图表数据
  setInterval(() => { loadTimeseries(); loadDwellStats() }, 60000)
})
</script>

<style scoped>
.dashboard {
  height: 100%; overflow-y: auto;
  padding: 16px 20px;
  display: flex; flex-direction: column; gap: 14px;
}

/* ── KPI 行 ──────────────────────────── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.kpi-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
}
.kpi-icon { font-size: 28px; }
.kpi-trend {
  margin-left: auto;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
}
.trend-up   { color: var(--success); background: rgba(16,217,122,0.1); }
.trend-down { color: var(--danger);  background: rgba(239,68,68,0.1); }

/* ── 图表网格 ────────────────────────── */
.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  grid-template-rows: 200px 180px;
  gap: 12px;
}
.chart-wide { grid-column: span 1; }
.charts-grid .card:first-child  { grid-column: 1; grid-row: 1; }
.charts-grid .card:nth-child(2) { grid-column: 2; grid-row: 1; }
.charts-grid .card:nth-child(3) { grid-column: 3; grid-row: 1; }
.charts-grid .card:nth-child(4) { grid-column: 1 / 4; grid-row: 2; }

.chart-container    { width: 100%; height: 140px; }
.chart-container-sm { width: 100%; height: 110px; }

.legend-row {
  display: flex; align-items: center; gap: 8px;
  margin-top: 8px; font-size: 12px; color: var(--text-secondary);
}
.legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.legend-val { font-weight: 600; color: var(--text-primary); margin-right: 8px; }

/* ── 展台状态行 ──────────────────────── */
.zone-status-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.zone-card { padding: 14px 16px; }
.zone-name { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
.zone-visitors { display: flex; align-items: baseline; gap: 4px; }
.zone-unit { font-size: 12px; color: var(--text-muted); }
.zone-meta { font-size: 11px; color: var(--text-muted); margin-top: 6px; }
.zone-meta b { color: var(--primary); }
.zone-bar {
  height: 4px; background: var(--border); border-radius: 2px; margin-top: 8px; overflow: hidden;
}
.zone-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(0,180,255,0.5), var(--primary));
  border-radius: 2px;
  transition: width 0.8s ease;
}

/* ── WS 状态角标 ─────────────────────── */
.ws-status {
  position: fixed; bottom: 12px; right: 16px;
  font-size: 11px; padding: 4px 10px; border-radius: 20px;
}
.ws-online  { color: var(--success); background: rgba(16,217,122,0.1); }
.ws-offline { color: var(--warning); background: rgba(245,158,11,0.1); }
</style>
