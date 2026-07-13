<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { store } from '../store.js'
import { buildGatewayApiUrl, buildGatewayExportUrl, buildGatewayHistoryUrl } from '../gateway-config'

const router = useRouter()

const chartWindRef = ref(null)
const isSystemRunning = ref(true)
const isAutoRefresh = ref(true)
const queryStart = ref('')
const queryEnd = ref('')

let refreshTimer = null
let windChart = null

const windRotation = computed(() => {
  const direction = String(store.data.node3.wind_dir || '--').trim()
  const directionMap = {
    N: 0, NNE: 22.5, NE: 45, ENE: 67.5, E: 90, ESE: 112.5, SE: 135, SSE: 157.5,
    S: 180, SSW: 202.5, SW: 225, WSW: 247.5, W: 270, WNW: 292.5, NW: 315, NNW: 337.5,
    北: 0, 东北: 45, 东: 90, 东南: 135, 南: 180, 西南: 225, 西: 270, 西北: 315,
  }
  return directionMap[direction] ?? 0
})

function createChart(element) {
  const chart = echarts.init(element)
  chart.setOption({
    title: { text: '风速趋势', left: 'center', textStyle: { color: '#2563eb' } },
    tooltip: { trigger: 'axis' },
    grid: { left: '4%', right: '4%', bottom: '14%', containLabel: true },
    dataZoom: [{ type: 'slider', show: true, bottom: 6 }, { type: 'inside' }],
    xAxis: { type: 'category', boundaryGap: false, data: [] },
    yAxis: { type: 'value', name: 'm/s' },
    series: [{ type: 'line', smooth: true, data: [], itemStyle: { color: '#2563eb' }, areaStyle: { color: 'rgba(37, 99, 235, 0.12)' } }],
  })
  return chart
}

function formatTimeLabel(value) {
  if (!value) return '--'
  return String(value).replace('T', ' ').slice(11, 19)
}

function toBackendDateTime(value) {
  return value ? value.replace('T', ' ') : ''
}

async function fetchHistory(params = {}) {
  try {
    const response = await fetch(buildGatewayHistoryUrl(params), { cache: 'no-store' })
    const data = await response.json()
    const rows = Array.isArray(data) ? data : []
    const times = rows.map((item) => formatTimeLabel(item.timestamp))
    const speeds = rows.map((item) => Number(item.wind_speed ?? 0))
    windChart?.setOption({ xAxis: { data: times }, series: [{ data: speeds }] })
  } catch (error) {
    console.error('Node3 history error:', error)
  }
}

async function refreshSystemStatus() {
  try {
    const response = await fetch(buildGatewayApiUrl('status'), { cache: 'no-store' })
    const data = await response.json()
    isSystemRunning.value = Boolean(data.running)
  } catch (error) {
    console.error('Node3 status error:', error)
  }
}

async function toggleSystem() {
  const nextState = !isSystemRunning.value
  try {
    const response = await fetch(buildGatewayApiUrl('control'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: nextState }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    isSystemRunning.value = nextState
  } catch (error) {
    console.error('Node3 control error:', error)
  }
}

function startAutoRefresh() {
  clearInterval(refreshTimer)
  refreshTimer = window.setInterval(() => {
    fetchHistory({ limit: 100 })
    refreshSystemStatus()
  }, 3000)
}

function handleTimeQuery() {
  isAutoRefresh.value = false
  clearInterval(refreshTimer)
  fetchHistory({ start: toBackendDateTime(queryStart.value), end: toBackendDateTime(queryEnd.value) })
}

function handleExport() {
  window.open(buildGatewayExportUrl({ start: toBackendDateTime(queryStart.value), end: toBackendDateTime(queryEnd.value) }), '_blank')
}

function toggleAutoRefresh() {
  isAutoRefresh.value = !isAutoRefresh.value
  if (isAutoRefresh.value) {
    fetchHistory({ limit: 100 })
    startAutoRefresh()
  } else {
    clearInterval(refreshTimer)
  }
}

function handleResize() {
  windChart?.resize()
}

onMounted(async () => {
  await nextTick()
  windChart = createChart(chartWindRef.value)
  fetchHistory({ limit: 100 })
  refreshSystemStatus()
  startAutoRefresh()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
  window.removeEventListener('resize', handleResize)
  windChart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <div class="header-bar">
      <div class="header-left">
        <button class="back-btn" @click="router.back()">返回</button>
        <div>
          <h2>环境感知单元-005</h2>
          <p class="subtitle">查看实时风速、风向与历史趋势</p>
        </div>
      </div>
      <div class="header-actions">
        <span class="status-badge" :class="store.nodes.node3.online ? 'online' : 'offline'">
          {{ store.nodes.node3.online ? '节点在线' : '节点离线' }}
        </span>
        <button class="action-btn" :class="isSystemRunning ? 'danger' : 'success'" @click="toggleSystem">
          {{ isSystemRunning ? '停止采集' : '开始采集' }}
        </button>
        <button class="action-btn secondary" :class="{ active: isAutoRefresh }" @click="toggleAutoRefresh">
          {{ isAutoRefresh ? '自动刷新中' : '自动刷新已停' }}
        </button>
      </div>
    </div>

    <div class="query-bar">
      <span class="query-label">时间范围</span>
      <input v-model="queryStart" type="datetime-local" class="date-input" />
      <span class="query-separator">至</span>
      <input v-model="queryEnd" type="datetime-local" class="date-input" />
      <button class="action-btn primary" @click="handleTimeQuery">查询</button>
      <button class="action-btn success" @click="handleExport">导出</button>
      <button class="action-btn secondary" @click="toggleAutoRefresh">恢复实时</button>
    </div>

    <div class="realtime-grid">
      <div class="metric-card speed">
        <span class="metric-label">实时风速</span>
        <strong class="metric-value">{{ store.data.node3.wind }}</strong>
        <span class="metric-unit">m/s</span>
      </div>

      <div class="metric-card compass">
        <span class="metric-label">实时风向</span>
        <div class="compass-shell">
          <div class="compass-dial">
            <span class="dir n">N</span>
            <span class="dir e">E</span>
            <span class="dir s">S</span>
            <span class="dir w">W</span>
            <div class="needle" :style="{ transform: `translate(-50%, -50%) rotate(${windRotation}deg)` }"></div>
          </div>
        </div>
        <strong class="direction-text">{{ store.data.node3.wind_dir }}</strong>
      </div>
    </div>

    <div class="chart-card">
      <div ref="chartWindRef" class="chart-host"></div>
    </div>
  </div>
</template>

<style scoped>
.page-container { min-height: 100vh; padding: 20px; background: #f7fafc; overflow-y: auto; }
.header-bar, .query-bar, .metric-card, .chart-card { background: #fff; border-radius: 12px; box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06); }
.header-bar, .query-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px; margin-bottom: 18px; flex-wrap: wrap; }
.header-left, .header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.header-left h2 { margin: 0; color: #1f2937; }
.subtitle { margin: 4px 0 0; color: #64748b; font-size: 0.9rem; }
.back-btn, .action-btn { border: none; border-radius: 8px; padding: 9px 16px; cursor: pointer; font-size: 0.95rem; }
.back-btn { color: #334155; background: #e2e8f0; }
.action-btn.primary { color: #fff; background: #7c3aed; }
.action-btn.success, .action-btn.success.active { color: #fff; background: #16a34a; }
.action-btn.secondary { color: #334155; background: #e2e8f0; }
.action-btn.secondary.active { color: #fff; background: #2563eb; }
.action-btn.danger { color: #fff; background: #ef4444; }
.status-badge { padding: 8px 14px; border-radius: 999px; font-size: 0.9rem; font-weight: 600; }
.status-badge.online { color: #047857; background: #d1fae5; }
.status-badge.offline { color: #b91c1c; background: #fee2e2; }
.query-label, .query-separator { color: #475569; }
.date-input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; }
.realtime-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-bottom: 18px; }
.metric-card { padding: 20px; text-align: center; }
.metric-label { display: block; color: #64748b; margin-bottom: 12px; }
.metric-value { display: block; font-size: 2.6rem; color: #2563eb; }
.metric-unit { display: block; margin-top: 10px; color: #94a3b8; }
.compass-shell { display: flex; justify-content: center; margin: 14px 0 10px; }
.compass-dial { position: relative; width: 150px; height: 150px; border-radius: 50%; border: 4px solid #dbeafe; background: radial-gradient(circle, #fff 40%, #eff6ff 100%); }
.dir { position: absolute; color: #64748b; font-weight: 600; }
.dir.n { top: 8px; left: 50%; transform: translateX(-50%); color: #dc2626; }
.dir.e { right: 12px; top: 50%; transform: translateY(-50%); }
.dir.s { bottom: 8px; left: 50%; transform: translateX(-50%); }
.dir.w { left: 12px; top: 50%; transform: translateY(-50%); }
.needle { position: absolute; top: 50%; left: 50%; width: 8px; height: 68px; background: linear-gradient(to top, #475569 50%, #ef4444 50%); border-radius: 999px; transform-origin: center center; transition: transform 0.4s ease; }
.needle::after { content: ''; position: absolute; top: 50%; left: 50%; width: 14px; height: 14px; border-radius: 50%; background: #0f172a; border: 2px solid #fff; transform: translate(-50%, -50%); }
.direction-text { display: block; color: #1f2937; font-size: 1.4rem; }
.chart-card { padding: 14px; }
.chart-host { width: 100%; height: 400px; }
@media (max-width: 1024px) { .realtime-grid { grid-template-columns: 1fr; } }
</style>
