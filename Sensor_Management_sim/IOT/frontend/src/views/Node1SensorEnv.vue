<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { store } from '../store.js'
import { buildGatewayApiUrl, buildGatewayExportUrl, buildGatewayHistoryUrl } from '../gateway-config'

const router = useRouter()

const chartSmokeRef = ref(null)
const chartTvocRef = ref(null)
const chartCoRef = ref(null)
const isSystemRunning = ref(true)
const isAutoRefresh = ref(true)
const queryStart = ref('')
const queryEnd = ref('')

const sensors = [
  { key: 'smoke', label: '烟雾浓度', unit: 'ug/m3', field: 'n1_smoke', color: '#6b7280', threshold: 600000 },
  { key: 'tvoc', label: 'TVOC', unit: 'mg/m3', field: 'n1_tvoc', color: '#7c3aed', threshold: 2.0 },
  { key: 'co', label: '一氧化碳', unit: 'ppm', field: 'n1_co', color: '#ef4444', threshold: 50 },
]

let refreshTimer = null
let smokeChart = null
let tvocChart = null
let coChart = null

function createChart(element, title, color) {
  const chart = echarts.init(element)
  chart.setOption({
    title: { text: title, left: 'center', textStyle: { color } },
    tooltip: { trigger: 'axis' },
    grid: { left: '4%', right: '4%', bottom: '14%', containLabel: true },
    dataZoom: [{ type: 'slider', show: true, bottom: 6 }, { type: 'inside' }],
    xAxis: { type: 'category', boundaryGap: false, data: [] },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, data: [], itemStyle: { color }, areaStyle: { color: `${color}22` } }],
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

function getMetricStatus(sensor) {
  const value = Number(store.data.node1[sensor.key] ?? 0)
  return value >= sensor.threshold ? 'abnormal' : 'normal'
}

async function fetchHistory(params = {}) {
  try {
    const response = await fetch(buildGatewayHistoryUrl(params), { cache: 'no-store' })
    const data = await response.json()
    const rows = Array.isArray(data) ? data : []
    const times = rows.map((item) => formatTimeLabel(item.timestamp))
    smokeChart?.setOption({ xAxis: { data: times }, series: [{ data: rows.map((item) => Number(item.n1_smoke ?? 0)) }] })
    tvocChart?.setOption({ xAxis: { data: times }, series: [{ data: rows.map((item) => Number(item.n1_tvoc ?? 0)) }] })
    coChart?.setOption({ xAxis: { data: times }, series: [{ data: rows.map((item) => Number(item.n1_co ?? 0)) }] })
  } catch (error) {
    console.error('Node1 env history error:', error)
  }
}

async function refreshSystemStatus() {
  try {
    const response = await fetch(buildGatewayApiUrl('status'), { cache: 'no-store' })
    const data = await response.json()
    isSystemRunning.value = Boolean(data.running)
  } catch (error) {
    console.error('Node1 env status error:', error)
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
    console.error('Node1 env control error:', error)
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
  smokeChart?.resize()
  tvocChart?.resize()
  coChart?.resize()
}

onMounted(async () => {
  await nextTick()
  smokeChart = createChart(chartSmokeRef.value, '烟雾趋势', '#6b7280')
  tvocChart = createChart(chartTvocRef.value, 'TVOC 趋势', '#7c3aed')
  coChart = createChart(chartCoRef.value, 'CO 趋势', '#ef4444')
  fetchHistory({ limit: 100 })
  refreshSystemStatus()
  startAutoRefresh()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
  window.removeEventListener('resize', handleResize)
  smokeChart?.dispose()
  tvocChart?.dispose()
  coChart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <div class="header-bar">
      <div class="header-left">
        <button class="back-btn" @click="router.back()">返回</button>
        <div>
          <h2>节点 A 空气质量监测</h2>
          <p class="subtitle">查看烟雾、TVOC 与一氧化碳变化趋势</p>
        </div>
      </div>
      <div class="header-actions">
        <span class="status-badge" :class="store.nodes.node1.online ? 'online' : 'offline'">
          {{ store.nodes.node1.online ? '节点在线' : '节点离线' }}
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

    <div class="metric-grid">
      <div
        v-for="sensor in sensors"
        :key="sensor.key"
        class="metric-card"
        :class="getMetricStatus(sensor)"
      >
        <div class="metric-head">
          <span>{{ sensor.label }}</span>
          <span class="metric-tag">{{ getMetricStatus(sensor) === 'abnormal' ? '异常' : '正常' }}</span>
        </div>
        <strong class="metric-value">{{ store.data.node1[sensor.key] }}</strong>
        <span class="metric-unit">{{ sensor.unit }}</span>
      </div>
    </div>

    <div class="chart-grid">
      <div class="chart-card"><div ref="chartSmokeRef" class="chart-host"></div></div>
      <div class="chart-card"><div ref="chartTvocRef" class="chart-host"></div></div>
      <div class="chart-card"><div ref="chartCoRef" class="chart-host"></div></div>
    </div>

    <div class="reference-card">
      <h3>阈值参考</h3>
      <table>
        <thead>
          <tr><th>指标</th><th>正常范围</th><th>预警阈值</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr><td>烟雾浓度</td><td>0 - 600000 ug/m3</td><td>&ge; 600000 ug/m3</td><td>疑似火情或烟雾积聚</td></tr>
          <tr><td>TVOC</td><td>0 - 2.0 mg/m3</td><td>&ge; 2.0 mg/m3</td><td>挥发性有机物偏高</td></tr>
          <tr><td>一氧化碳</td><td>0 - 50 ppm</td><td>&ge; 50 ppm</td><td>存在中毒风险</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page-container { min-height: 100vh; padding: 20px; background: #f7fafc; overflow-y: auto; }
.header-bar, .query-bar, .metric-card, .chart-card, .reference-card { background: #fff; border-radius: 12px; box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06); }
.header-bar, .query-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px; margin-bottom: 18px; flex-wrap: wrap; }
.header-left, .header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.header-left h2, .reference-card h3 { margin: 0; color: #1f2937; }
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
.metric-grid, .chart-grid { display: grid; gap: 18px; margin-bottom: 18px; }
.metric-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.chart-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.metric-card { padding: 20px; border-left: 4px solid #16a34a; }
.metric-card.abnormal { border-left-color: #ef4444; background: #fff1f2; }
.metric-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: #475569; }
.metric-tag { color: #64748b; font-size: 0.85rem; }
.metric-value { display: block; margin: 18px 0 8px; font-size: 2.3rem; color: #111827; }
.metric-unit { color: #94a3b8; }
.chart-card { padding: 14px; }
.chart-host { width: 100%; height: 320px; }
.reference-card { padding: 20px; }
table { width: 100%; border-collapse: collapse; margin-top: 14px; }
th, td { padding: 12px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; color: #334155; }
thead th { color: #0f172a; background: #f8fafc; }
@media (max-width: 1200px) { .metric-grid, .chart-grid { grid-template-columns: 1fr; } }
</style>
