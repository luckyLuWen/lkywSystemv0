<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { store } from '../store.js'
import {
  buildGatewayApiUrl,
  buildGatewayExportUrl,
  buildGatewayHistoryUrl,
} from '../gateway-config'

const router = useRouter()

const chartTempRef = ref(null)
const chartHumRef = ref(null)
const isSystemRunning = ref(true)
const isAutoRefresh = ref(true)
const queryStart = ref('')
const queryEnd = ref('')

let refreshTimer = null
let tempChart = null
let humChart = null

function createChart(element, title, color) {
  const chart = echarts.init(element)
  chart.setOption({
    title: { text: title, left: 'center', textStyle: { color } },
    tooltip: { trigger: 'axis' },
    grid: { left: '4%', right: '4%', bottom: '14%', containLabel: true },
    dataZoom: [{ type: 'slider', show: true, bottom: 6 }, { type: 'inside' }],
    xAxis: { type: 'category', boundaryGap: false, data: [] },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'line',
        smooth: true,
        data: [],
        itemStyle: { color },
        areaStyle: { color: `${color}22` },
      },
    ],
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
    const url = buildGatewayHistoryUrl(params)
    const response = await fetch(url, { cache: 'no-store' })
    const data = await response.json()
    const rows = Array.isArray(data) ? data : []

    const times = rows.map((item) => formatTimeLabel(item.timestamp))
    const temps = rows.map((item) => Number(item.n1_temp ?? 0))
    const hums = rows.map((item) => Number(item.n1_hum ?? 0))

    tempChart?.setOption({ xAxis: { data: times }, series: [{ data: temps }] })
    humChart?.setOption({ xAxis: { data: times }, series: [{ data: hums }] })
  } catch (error) {
    console.error('Node1 weather history error:', error)
  }
}

async function refreshSystemStatus() {
  try {
    const response = await fetch(buildGatewayApiUrl('status'), { cache: 'no-store' })
    const data = await response.json()
    isSystemRunning.value = Boolean(data.running)
  } catch (error) {
    console.error('Node1 status error:', error)
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
    console.error('Node1 control error:', error)
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
  fetchHistory({
    start: toBackendDateTime(queryStart.value),
    end: toBackendDateTime(queryEnd.value),
  })
}

function handleExport() {
  window.open(
    buildGatewayExportUrl({
      start: toBackendDateTime(queryStart.value),
      end: toBackendDateTime(queryEnd.value),
    }),
    '_blank'
  )
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
  tempChart?.resize()
  humChart?.resize()
}

onMounted(async () => {
  await nextTick()
  tempChart = createChart(chartTempRef.value, '温度趋势', '#ed8936')
  humChart = createChart(chartHumRef.value, '湿度趋势', '#3182ce')
  fetchHistory({ limit: 100 })
  refreshSystemStatus()
  startAutoRefresh()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
  window.removeEventListener('resize', handleResize)
  tempChart?.dispose()
  humChart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <div class="header-bar">
      <div class="header-left">
        <button class="back-btn" @click="router.back()">返回</button>
        <div>
          <h2>节点 A 温湿度监测</h2>
          <p class="subtitle">查看实时温度、湿度与历史趋势</p>
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

    <div class="realtime-grid">
      <div class="metric-card warm">
        <span class="metric-label">实时温度</span>
        <strong class="metric-value">{{ store.data.node1.temp }}</strong>
        <span class="metric-unit">°C</span>
      </div>
      <div class="metric-card cool">
        <span class="metric-label">实时湿度</span>
        <strong class="metric-value">{{ store.data.node1.hum }}</strong>
        <span class="metric-unit">%</span>
      </div>
    </div>

    <div class="chart-grid">
      <div class="chart-card">
        <div ref="chartTempRef" class="chart-host"></div>
      </div>
      <div class="chart-card">
        <div ref="chartHumRef" class="chart-host"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  min-height: 100vh;
  padding: 20px;
  background: #f7fafc;
  overflow-y: auto;
}

.header-bar,
.query-bar,
.metric-card,
.chart-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}

.header-bar,
.query-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.header-left,
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.header-left h2 {
  margin: 0;
  color: #1f2937;
  font-size: 1.35rem;
}

.subtitle {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.back-btn,
.action-btn {
  border: none;
  border-radius: 8px;
  padding: 9px 16px;
  cursor: pointer;
  font-size: 0.95rem;
}

.back-btn {
  color: #334155;
  background: #e2e8f0;
}

.action-btn.primary {
  color: #fff;
  background: #7c3aed;
}

.action-btn.success,
.action-btn.success.active {
  color: #fff;
  background: #16a34a;
}

.action-btn.secondary {
  color: #334155;
  background: #e2e8f0;
}

.action-btn.secondary.active {
  color: #fff;
  background: #2563eb;
}

.action-btn.danger {
  color: #fff;
  background: #ef4444;
}

.status-badge {
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 600;
}

.status-badge.online {
  color: #047857;
  background: #d1fae5;
}

.status-badge.offline {
  color: #b91c1c;
  background: #fee2e2;
}

.query-label,
.query-separator {
  color: #475569;
}

.date-input {
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.realtime-grid,
.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.realtime-grid {
  margin-bottom: 18px;
}

.metric-card {
  padding: 24px;
  text-align: center;
}

.metric-label {
  display: block;
  color: #64748b;
  margin-bottom: 10px;
}

.metric-value {
  display: block;
  font-size: 2.6rem;
  line-height: 1;
}

.metric-unit {
  display: block;
  margin-top: 10px;
  color: #94a3b8;
}

.metric-card.warm .metric-value {
  color: #dd6b20;
}

.metric-card.cool .metric-value {
  color: #2563eb;
}

.chart-card {
  padding: 14px;
}

.chart-host {
  width: 100%;
  height: 360px;
}

@media (max-width: 1024px) {
  .realtime-grid,
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
