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
/* ================= 核心色板与全局设定 (绝不使用松散的外部字体) ================= */

.page-container { 
  min-height: 100vh; 
  padding: 20px; 
  /* 统一深邃暗空背景，配合底部微微泛起的蓝色光晕 */
  background: #030710 radial-gradient(circle at 50% 0%, rgba(0, 114, 255, 0.12) 0%, rgba(6, 14, 28, 1) 100%);
  overflow-y: auto; 
  /* 极其克制的极客级无衬线字体栈 */
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: rgba(186, 230, 253, 0.88);
}

/* ================= 卡片通用样式 (极致科幻玻璃体) ================= */
.header-bar, .query-bar, .metric-card, .chart-card { 
  background: rgba(6, 14, 28, 0.82); 
  border-radius: 10px; 
  box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 16px rgba(0, 242, 254, 0.06); 
  border: 1px solid rgba(0, 242, 254, 0.25); 
  backdrop-filter: blur(16px) saturate(160%); 
}

/* 顶部标题栏 */
.header-bar, .query-bar { 
  display: flex; align-items: center; justify-content: space-between; 
  gap: 12px; padding: 16px 20px; margin-bottom: 18px; flex-wrap: wrap; 
  /* 增加顶部微光渐变，强化立体感 */
  background: linear-gradient(180deg, rgba(0, 242, 254, 0.05) 0%, rgba(6, 14, 28, 0.82) 100%);
}
.header-left, .header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.header-left h2 { 
  margin: 0; color: #00f2fe; 
  font-size: 22px; font-weight: 800; 
  letter-spacing: 1.5px; text-shadow: 0 0 12px rgba(0, 242, 254, 0.6); 
}
.subtitle { margin: 4px 0 0; color: rgba(186, 230, 253, 0.7); font-size: 12px; font-weight: 600; font-family: "JetBrains Mono", monospace; }

/* ================= 按钮样式 (幽灵光效体系) ================= */
.back-btn, .action-btn { 
  border-radius: 6px; padding: 8px 16px; cursor: pointer; 
  font-size: 13px; font-weight: bold; transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1); 
  letter-spacing: 0.5px; display: inline-flex; align-items: center; justify-content: center; 
  font-family: inherit;
}
.back-btn:active, .action-btn:active { transform: scale(0.96); }

/* 返回按钮与次要按钮（幽灵态） */
.back-btn, .action-btn.secondary { 
  color: rgba(186, 230, 253, 0.88); background: transparent; border: 1px solid rgba(0, 242, 254, 0.3); 
}
.back-btn:hover, .action-btn.secondary:hover { 
  border-color: #00f2fe; color: #fff; background: rgba(0, 242, 254, 0.12); box-shadow: 0 0 10px rgba(0, 242, 254, 0.3); 
}
.action-btn.secondary.active { 
  color: #fff; background: rgba(0, 242, 254, 0.25); border-color: #00f2fe; box-shadow: 0 0 12px rgba(0, 242, 254, 0.5); 
}

/* 主操作按钮 */
.action-btn.primary { 
  color: #00f2fe; background: rgba(0, 242, 254, 0.15); border: 1px solid #00f2fe; box-shadow: 0 0 8px rgba(0, 242, 254, 0.3); 
}
.action-btn.primary:hover { background: rgba(0, 242, 254, 0.25); box-shadow: 0 0 15px rgba(0, 242, 254, 0.5); }

/* 成功与警报按钮 */
.action-btn.success, .action-btn.success.active { 
  color: #10b981; background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.3); 
}
.action-btn.success:hover { background: rgba(16, 185, 129, 0.25); box-shadow: 0 0 15px rgba(16, 185, 129, 0.5); }

.action-btn.danger { 
  color: #ef4444; background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.3); 
}
.action-btn.danger:hover { background: rgba(239, 68, 68, 0.25); box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }

/* 状态徽章 */
.status-badge { 
  padding: 4px 12px; border-radius: 4px; font-size: 11.5px; font-family: "JetBrains Mono", monospace; 
  font-weight: 700; border: 1px solid; 
}
.status-badge.online { color: #10b981; background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.5); box-shadow: 0 0 10px rgba(16, 185, 129, 0.2); }
.status-badge.offline { color: #ef4444; background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.5); box-shadow: 0 0 10px rgba(239, 68, 68, 0.2); }

/* ================= 查询栏与输入框 ================= */
.query-label, .query-separator { color: rgba(186, 230, 253, 0.7); font-weight: 600; font-size: 13.5px; }
.date-input { 
  padding: 8px 12px; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(0, 242, 254, 0.2); 
  border-radius: 6px; font-size: 13px; color: #fff; outline: none; 
  transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1); font-family: "JetBrains Mono", monospace; 
  box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.05); 
}
.date-input:focus { border-color: #00f2fe; box-shadow: 0 0 12px rgba(0, 242, 254, 0.4), inset 0 0 10px rgba(0, 242, 254, 0.1); background: rgba(0, 242, 254, 0.05); }
::-webkit-calendar-picker-indicator { filter: invert(1) sepia(1) saturate(5) hue-rotate(175deg); opacity: 0.8; cursor: pointer; }

/* ================= 数据卡片网格 ================= */
.realtime-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 18px; }
.metric-card { 
  padding: 20px; text-align: center; transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1); 
  border-top: 2px solid rgba(0, 242, 254, 0.15); 
}
.metric-card:hover { 
  border-color: #00f2fe; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 242, 254, 0.2) inset, 0 0 15px rgba(0, 242, 254, 0.3); 
  transform: translateY(-2px); background: rgba(0, 242, 254, 0.05); border-top-color: #00f2fe; 
}

.metric-label { display: block; color: rgba(186, 230, 253, 0.9); margin-bottom: 12px; font-weight: 700; letter-spacing: 1px; font-size: 14.5px; }
.metric-value { 
  display: block; font-size: 38px; color: #00f2fe; font-family: "JetBrains Mono", monospace; 
  font-weight: 700; text-shadow: 0 0 15px rgba(0, 242, 254, 0.5); line-height: 1; 
}
.metric-unit { display: block; margin-top: 10px; color: rgba(0, 242, 254, 0.6); font-weight: 600; font-size: 13px; font-family: -apple-system, sans-serif; }

/* ================= 指南针特效 (全息雷达降维重构) ================= */
.compass-shell { display: flex; justify-content: center; margin: 14px 0 10px; }
.compass-dial { 
  position: relative; width: 150px; height: 150px; border-radius: 50%; 
  /* 剔除沉闷深蓝，改用细致的青色发光雷达外圈 */
  border: 1px solid rgba(0, 242, 254, 0.4); 
  background: radial-gradient(circle, rgba(0, 242, 254, 0.05) 10%, rgba(0, 0, 0, 0.6) 100%); 
  box-shadow: inset 0 0 25px rgba(0, 242, 254, 0.15), 0 0 15px rgba(0,0,0,0.8), 0 0 10px rgba(0, 242, 254, 0.1); 
}
/* 雷达内嵌十字瞄准线 */
.compass-dial::before, .compass-dial::after {
  content: ''; position: absolute; background: rgba(0, 242, 254, 0.15);
}
.compass-dial::before { top: 0; bottom: 0; left: 50%; width: 1px; transform: translateX(-50%); }
.compass-dial::after { left: 0; right: 0; top: 50%; height: 1px; transform: translateY(-50%); }

.dir { 
  position: absolute; color: rgba(186, 230, 253, 0.7); font-weight: 700; 
  font-family: "JetBrains Mono", monospace; font-size: 13px; 
  text-shadow: 0 0 5px rgba(186, 230, 253, 0.4); 
  z-index: 2; /* 确保文字在十字线之上 */
}
/* 北向维持高危预警红色，契合赛博感 */
.dir.n { top: 8px; left: 50%; transform: translateX(-50%); color: #ef4444; text-shadow: 0 0 8px rgba(239, 68, 68, 0.8); }
.dir.e { right: 12px; top: 50%; transform: translateY(-50%); }
.dir.s { bottom: 8px; left: 50%; transform: translateX(-50%); }
.dir.w { left: 12px; top: 50%; transform: translateY(-50%); }

/* 极其凌厉的光剑质感指针 */
.needle { 
  position: absolute; top: 50%; left: 50%; width: 4px; height: 80px; 
  background: linear-gradient(to top, rgba(0, 242, 254, 0.8) 50%, #ef4444 50%); 
  border-radius: 999px; transform-origin: center center; 
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); 
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.6); 
  z-index: 3;
}
.needle::after { 
  content: ''; position: absolute; top: 50%; left: 50%; width: 14px; height: 14px; 
  border-radius: 50%; background: #030710; border: 2px solid #00f2fe; 
  transform: translate(-50%, -50%); box-shadow: 0 0 10px rgba(0, 242, 254, 0.8); 
}

.direction-text { 
  display: block; color: #00f2fe; font-size: 22px; font-family: "JetBrains Mono", monospace; 
  font-weight: 700; text-shadow: 0 0 12px rgba(0, 242, 254, 0.5); margin-top: 14px; 
}

/* ================= 图表区 ================= */
.chart-card { padding: 16px; }
.chart-host { width: 100%; height: 400px; }

@media (max-width: 1024px) { .realtime-grid { grid-template-columns: 1fr; } }
</style>