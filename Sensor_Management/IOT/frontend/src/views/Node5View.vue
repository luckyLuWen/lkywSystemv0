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
          <h2>环境感知单元-003</h2>
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
/* ================= 核心色板与全局设定 ================= */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');

.page-container { 
  min-height: 100vh; 
  padding: 20px; 
  background: #050b14 radial-gradient(circle at 50% 0%, #0a192f 0%, #050b14 100%); 
  overflow-y: auto; 
  font-family: 'Rajdhani', system-ui, -apple-system, sans-serif;
  color: #e2e8f0;
}

/* ================= 卡片通用样式 (深色玻璃拟态) ================= */
.header-bar, .query-bar, .metric-card, .chart-card { 
  background: rgba(10, 25, 47, 0.6); 
  border-radius: 8px; 
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5); 
  border: 1px solid #1e3a8a; 
  backdrop-filter: blur(10px); 
}

/* 顶部标题栏 */
.header-bar, .query-bar { 
  display: flex; align-items: center; justify-content: space-between; 
  gap: 12px; padding: 16px 20px; margin-bottom: 18px; flex-wrap: wrap; 
}
.header-left, .header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.header-left h2 { 
  margin: 0; color: #64ffda; font-family: 'Orbitron', sans-serif; 
  letter-spacing: 1.5px; text-shadow: 0 0 10px rgba(100, 255, 218, 0.4); 
}
.subtitle { margin: 4px 0 0; color: #94a3b8; font-size: 0.9rem; font-weight: 600; }

/* ================= 按钮样式 (幽灵科技风) ================= */
.back-btn, .action-btn { 
  border-radius: 4px; padding: 8px 16px; cursor: pointer; font-size: 0.85rem; 
  font-weight: bold; transition: all 0.2s ease; letter-spacing: 0.5px; 
  display: inline-flex; align-items: center; justify-content: center; 
  border: 1px solid transparent; 
}
.back-btn:active, .action-btn:active { transform: scale(0.96); }

.back-btn { color: #cbd5e1; background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); }
.back-btn:hover { border-color: #64ffda; color: #64ffda; }

.action-btn.primary { color: #c084fc; background: rgba(192, 132, 252, 0.2); border-color: #c084fc; }
.action-btn.primary:hover { background: rgba(192, 132, 252, 0.3); box-shadow: 0 0 10px rgba(192,132,252,0.3); }

.action-btn.success, .action-btn.success.active { color: #10b981; background: rgba(16, 185, 129, 0.2); border-color: #10b981; }
.action-btn.success:hover { background: rgba(16, 185, 129, 0.3); box-shadow: 0 0 10px rgba(16,185,129,0.3); }

.action-btn.secondary { color: #cbd5e1; background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); }
.action-btn.secondary:hover { border-color: #60a5fa; color: #60a5fa; }
.action-btn.secondary.active { color: #60a5fa; background: rgba(96, 165, 250, 0.2); border-color: #60a5fa; box-shadow: 0 0 10px rgba(96,165,250,0.2); }

.action-btn.danger { color: #ef4444; background: rgba(239, 68, 68, 0.2); border-color: #ef4444; }
.action-btn.danger:hover { background: rgba(239, 68, 68, 0.3); box-shadow: 0 0 10px rgba(239,68,68,0.3); }

/* 状态徽章 */
.status-badge { padding: 4px 12px; border-radius: 4px; font-size: 0.85rem; font-weight: 700; border: 1px solid; }
.status-badge.online { color: #10b981; background: rgba(16, 185, 129, 0.1); border-color: #10b981; }
.status-badge.offline { color: #ef4444; background: rgba(239, 68, 68, 0.1); border-color: #ef4444; }

/* ================= 查询栏与输入框 ================= */
.query-label, .query-separator { color: #94a3b8; font-weight: 600; font-size: 0.9rem; }
.date-input { 
  padding: 8px 12px; background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); 
  border-radius: 4px; font-size: 0.9rem; color: #e2e8f0; outline: none; 
  transition: all 0.2s; font-family: 'Orbitron', monospace; 
}
.date-input:focus { border-color: #60a5fa; box-shadow: 0 0 8px rgba(96, 165, 250, 0.4); }
::-webkit-calendar-picker-indicator { filter: invert(1); opacity: 0.6; cursor: pointer; }

/* ================= 数据卡片网格 ================= */
.realtime-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 18px; }
.metric-card { 
  padding: 20px; text-align: center; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
  border-top: 2px solid rgba(255,255,255,0.1); 
}
.metric-card:hover { 
  border-color: #60a5fa; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), inset 0 0 15px rgba(96, 165, 250, 0.1); 
  transform: translateY(-2px); background: rgba(15, 30, 60, 0.8); border-top-color: #64ffda; 
}

.metric-label { display: block; color: #cbd5e1; margin-bottom: 12px; font-weight: 700; letter-spacing: 1px; }
.metric-value { 
  display: block; font-size: 2.8rem; color: #60a5fa; font-family: 'Orbitron', monospace; 
  font-weight: 700; text-shadow: 0 0 10px rgba(96, 165, 250, 0.3); line-height: 1; 
}
.metric-unit { display: block; margin-top: 10px; color: #64748b; font-weight: 600; font-size: 0.9rem; }

/* ================= 指南针特效 (深色发光雷达风重构) ================= */
.compass-shell { display: flex; justify-content: center; margin: 14px 0 10px; }
.compass-dial { 
  position: relative; width: 150px; height: 150px; border-radius: 50%; 
  border: 4px solid #1e3a8a; 
  background: radial-gradient(circle, rgba(10,25,47,0.8) 40%, rgba(0,0,0,0.8) 100%); 
  box-shadow: inset 0 0 20px rgba(96, 165, 250, 0.2), 0 0 15px rgba(0,0,0,0.5); 
}
.dir { position: absolute; color: #cbd5e1; font-weight: 700; font-family: 'Orbitron', sans-serif; text-shadow: 0 0 5px rgba(255,255,255,0.2); }
.dir.n { top: 8px; left: 50%; transform: translateX(-50%); color: #ef4444; text-shadow: 0 0 8px rgba(239, 68, 68, 0.6); }
.dir.e { right: 12px; top: 50%; transform: translateY(-50%); }
.dir.s { bottom: 8px; left: 50%; transform: translateX(-50%); }
.dir.w { left: 12px; top: 50%; transform: translateY(-50%); }

.needle { 
  position: absolute; top: 50%; left: 50%; width: 6px; height: 74px; 
  background: linear-gradient(to top, #3b82f6 50%, #ef4444 50%); 
  border-radius: 999px; transform-origin: center center; 
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1); 
  box-shadow: 0 0 8px rgba(255,255,255,0.2); 
}
.needle::after { 
  content: ''; position: absolute; top: 50%; left: 50%; width: 12px; height: 12px; 
  border-radius: 50%; background: #050b14; border: 2px solid #64ffda; 
  transform: translate(-50%, -50%); box-shadow: 0 0 8px rgba(100,255,218,0.5); 
}
.direction-text { 
  display: block; color: #64ffda; font-size: 1.4rem; font-family: 'Orbitron', monospace; 
  font-weight: 700; text-shadow: 0 0 8px rgba(100, 255, 218, 0.3); margin-top: 10px; 
}

/* ================= 图表区 ================= */
.chart-card { padding: 16px; }
.chart-host { width: 100%; height: 400px; }

@media (max-width: 1024px) { .realtime-grid { grid-template-columns: 1fr; } }
</style>
