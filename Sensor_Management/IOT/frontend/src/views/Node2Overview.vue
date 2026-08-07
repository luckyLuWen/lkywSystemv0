<script setup>
import { nextTick, onMounted, onUnmounted, ref, computed } from 'vue'
import * as echarts from 'echarts'
import { store } from '../store.js'
import {
  buildGatewayApiUrl,
  buildGatewayExportUrl,
  buildGatewayHistoryUrl,
} from '../gateway-config.js'

// DOM Refs
const pageRef = ref(null)
const chartTempRef = ref(null)
const chartHumRef = ref(null)
const chartSmokeRef = ref(null)
const chartTvocRef = ref(null)
const chartCoRef = ref(null)

// State
const nodeState = computed(() => store.nodes.node2 || { online: false, address: '' })
const isSystemRunning = ref(false)
const isAutoRefresh = ref(true)
const queryStart = ref('')
const queryEnd = ref('')

let refreshTimer = null
let resizeObserver = null
let tempChart = null
let humChart = null
let smokeChart = null
let tvocChart = null
let coChart = null

// 环境传感器配置
const envSensors = [
  { key: 'smoke', label: '☁ 烟雾浓度', unit: 'ug/m3', field: 'n2_smoke', color: '#6b7280', threshold: 600000 },
  { key: 'tvoc', label: '🧪 挥发物 (TVOC)', unit: 'mg/m3', field: 'n2_tvoc', color: '#7c3aed', threshold: 2.0 },
  { key: 'co', label: '⚠️ 一氧化碳 (CO)', unit: 'ppm', field: 'n2_co', color: '#ef4444', threshold: 50 },
]

// 统一图表初始化工厂函数
function createChart(element, title, color) {
  const chart = echarts.init(element)
  chart.setOption({
    title: { 
      text: title, 
      left: 'center', 
      top: 8, 
      textStyle: { color, fontSize: 16, fontWeight: '700' } 
    },
    tooltip: { trigger: 'axis' },
    // 动态间距，防止挤压
    grid: { left: '5%', right: '5%', top: 55, bottom: '15%', containLabel: true }, 
    dataZoom: [{ type: 'slider', show: true, bottom: 4, height: 16 }, { type: 'inside' }],
    xAxis: { type: 'category', boundaryGap: false, data: [] },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'line',
        smooth: true,
        data: [],
        itemStyle: { color },
        areaStyle: { color: `${color}15` },
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

function getMetricStatus(sensor) {
  const value = Number(store.data.node2?.[sensor.key] ?? 0)
  return value >= sensor.threshold ? 'abnormal' : 'normal'
}

// 统一拉取所有历史数据
async function fetchHistory(params = {}) {
  try {
    const response = await fetch(buildGatewayHistoryUrl(params), { cache: 'no-store' })
    const data = await response.json()
    const rows = Array.isArray(data) ? data : []
    const times = rows.map((item) => formatTimeLabel(item.timestamp))
    
    tempChart?.setOption({ xAxis: { data: times }, series: [{ data: rows.map(i => Number(i.n2_temp ?? 0)) }] })
    humChart?.setOption({ xAxis: { data: times }, series: [{ data: rows.map(i => Number(i.n2_hum ?? 0)) }] })
    smokeChart?.setOption({ xAxis: { data: times }, series: [{ data: rows.map(i => Number(i.n2_smoke ?? 0)) }] })
    tvocChart?.setOption({ xAxis: { data: times }, series: [{ data: rows.map(i => Number(i.n2_tvoc ?? 0)) }] })
    coChart?.setOption({ xAxis: { data: times }, series: [{ data: rows.map(i => Number(i.n2_co ?? 0)) }] })
  } catch (error) {
    console.error('History fetch error:', error)
  }
}

async function refreshSystemStatus() {
  try {
    const response = await fetch(buildGatewayApiUrl('status'), { cache: 'no-store' })
    const data = await response.json()
    isSystemRunning.value = Boolean(data.running)
  } catch (error) {
    console.error('Status fetch error:', error)
  }
}

async function toggleSystem() {
  const nextState = !isSystemRunning.value
  isSystemRunning.value = nextState 
  try {
    const response = await fetch(buildGatewayApiUrl('control'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: nextState }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
  } catch (error) {
    isSystemRunning.value = !nextState
    console.error('Control command error:', error)
    alert('操作失败，请检查网络连接或后端服务状态。')
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

// 提取 Resize 逻辑
function handleResize() {
  tempChart?.resize()
  humChart?.resize()
  smokeChart?.resize()
  tvocChart?.resize()
  coChart?.resize()
}

onMounted(async () => {
  await nextTick()
  tempChart = createChart(chartTempRef.value, '环境温度变化趋势', '#ed8936')
  humChart = createChart(chartHumRef.value, '相对湿度变化趋势', '#3182ce')
  smokeChart = createChart(chartSmokeRef.value, '烟雾浓度趋势', '#6b7280')
  tvocChart = createChart(chartTvocRef.value, 'TVOC 趋势', '#7c3aed')
  coChart = createChart(chartCoRef.value, 'CO 趋势', '#ef4444')

  fetchHistory({ limit: 100 })
  refreshSystemStatus()
  startAutoRefresh()

  // 监听容器大小变化（比 window.resize 更精准）
  resizeObserver = new ResizeObserver(() => {
    requestAnimationFrame(handleResize)
  })
  if (pageRef.value) {
    resizeObserver.observe(pageRef.value)
  }
})

onUnmounted(() => {
  clearInterval(refreshTimer)
  if (resizeObserver) resizeObserver.disconnect()
  tempChart?.dispose()
  humChart?.dispose()
  smokeChart?.dispose()
  tvocChart?.dispose()
  coChart?.dispose()
})
</script>

<template>
  <div class="page-container" ref="pageRef">
    
    <div class="header-bar">
      <div class="title-wrapper">
        <h2>多源数据感知单元-002</h2>
        <span class="status-badge" :class="nodeState.online ? 'online' : 'offline'">
          {{ nodeState.online ? '● 设备在线' : '○ 设备离线' }}
        </span>
      </div>
      <div class="header-actions">
        <button 
          class="action-btn" 
          :class="isSystemRunning ? 'danger' : 'success'" 
          @click="toggleSystem"
        >
          {{ isSystemRunning ? '⏹ 停止采集' : '▶ 开始采集' }}
        </button>
        <button 
          class="action-btn secondary" 
          :class="{ active: isAutoRefresh }" 
          @click="toggleAutoRefresh"
        >
          {{ isAutoRefresh ? '动态刷新中 (3s)' : '动态刷新已停' }}
        </button>
      </div>
    </div>

    <div class="query-bar">
      <div class="query-left">
        <span class="query-label">全局时间范围：</span>
        <input v-model="queryStart" type="datetime-local" class="date-input" />
        <span class="query-separator">至</span>
        <input v-model="queryEnd" type="datetime-local" class="date-input" />
      </div>
      <div class="query-right">
        <button class="action-btn primary" @click="handleTimeQuery">🔍 查询历史</button>
        <button class="action-btn export" @click="handleExport">📊 导出报表</button>
        <button class="action-btn secondary" @click="toggleAutoRefresh">恢复实时监控</button>
      </div>
    </div>

    <!-- 数据指标区 (固定高度) -->
    <div class="metrics-area">
      <div class="realtime-grid">
        <div class="metric-card warm">
          <span class="metric-label huge-label">🌡️ 实时温度</span>
          <div class="metric-body">
            <strong class="metric-value huge-value">{{ store.data.node2?.temp ?? '--' }}</strong>
            <span class="metric-unit">°C</span>
          </div>
        </div>
        <div class="metric-card cool">
          <span class="metric-label huge-label">💧 实时湿度</span>
          <div class="metric-body">
            <strong class="metric-value huge-value">{{ store.data.node2?.hum ?? '--' }}</strong>
            <span class="metric-unit">%</span>
          </div>
        </div>
      </div>

      <div class="env-grid">
        <div
          v-for="sensor in envSensors"
          :key="sensor.key"
          class="metric-card env-card"
          :class="getMetricStatus(sensor)"
        >
          <div class="metric-head">
            <span class="env-label">{{ sensor.label }}</span>
            <span class="metric-tag" :class="getMetricStatus(sensor)">
              {{ getMetricStatus(sensor) === 'abnormal' ? '异常预警' : '状态正常' }}
            </span>
          </div>
          <div class="metric-body">
            <strong class="metric-value">{{ store.data.node2?.[sensor.key] ?? '--' }}</strong>
            <span class="metric-unit">{{ sensor.unit }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表和表格弹性伸缩区 (填满剩余高度) -->
    <div class="elastic-content-area">
      <div class="charts-wrapper">
        <div class="chart-grid weather-charts">
          <div class="chart-card"><div ref="chartTempRef" class="chart-host"></div></div>
          <div class="chart-card"><div ref="chartHumRef" class="chart-host"></div></div>
        </div>
        
        <div class="chart-grid env-charts">
          <div class="chart-card"><div ref="chartSmokeRef" class="chart-host"></div></div>
          <div class="chart-card"><div ref="chartTvocRef" class="chart-host"></div></div>
          <div class="chart-card"><div ref="chartCoRef" class="chart-host"></div></div>
        </div>
      </div>

      <div class="reference-card">
        <h3>指标健康阈值参考字典</h3>
        <table>
          <thead>
            <tr>
              <th>监控指标</th>
              <th>标准健康作业范围</th>
              <th>预警报警阈值</th>
              <th>隐患关联说明</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>烟雾浓度</td>
              <td>0 - 600,000 ug/m³</td>
              <td>&ge; 600,000 ug/m³</td>
              <td>疑似火情或局部重度烟雾粉尘积聚</td>
            </tr>
            <tr>
              <td>挥发物 (TVOC)</td>
              <td>0 - 2.0 mg/m³</td>
              <td>&ge; 2.0 mg/m³</td>
              <td>环境有机挥发物超标，长期暴露影响作业人员健康</td>
            </tr>
            <tr>
              <td>一氧化碳 (CO)</td>
              <td>0 - 50 ppm</td>
              <td>&ge; 50 ppm</td>
              <td>不完全燃烧副产物，高浓度积聚存在严重窒息中毒风险</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
  </div>
</template>

<style scoped>
/* ================= 全局重置，消除边缘留白 ================= */
:global(body), :global(html), :global(#app) {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
}

/* 基础与布局 - 引入 Flex 使得容器强制撑满 */
.page-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 24px 32px;
  background: #030710 radial-gradient(circle at 50% 0%, rgba(0, 114, 255, 0.12) 0%, rgba(6, 14, 28, 1) 100%);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: rgba(186, 230, 253, 0.88);
  box-sizing: border-box;
  overflow-x: hidden;
}

/* ================= 弹性伸缩布局核心 ================= */
.metrics-area {
  flex: 0 0 auto;
}

.elastic-content-area {
  flex: 1; /* 核心：让该区域占据剩余的全部垂直空间，解决留白 */
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.charts-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1; /* 让图表区域能够向下弹开填满空间 */
}

/* 卡片通用样式 */
.header-bar, .query-bar, .metric-card, .chart-card, .reference-card {
  background: rgba(6, 14, 28, 0.82);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 16px rgba(0, 242, 254, 0.06);
  border: 1px solid rgba(0, 242, 254, 0.25);
  backdrop-filter: blur(16px) saturate(160%);
  box-sizing: border-box;
}

/* 顶部标题栏 */
.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
  background: linear-gradient(180deg, rgba(0, 242, 254, 0.05) 0%, rgba(6, 14, 28, 0.82) 100%);
}

.title-wrapper { display: flex; align-items: center; gap: 16px; }
.title-wrapper h2 { margin: 0; color: #00f2fe; font-size: 22px; font-weight: 800; letter-spacing: 1.5px; text-shadow: 0 0 12px rgba(0, 242, 254, 0.6); }

.status-badge {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-family: "JetBrains Mono", monospace;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  border: 1px solid;
}
.status-badge.online { color: #10b981; background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.5); box-shadow: 0 0 10px rgba(16, 185, 129, 0.2); }
.status-badge.offline { color: #ef4444; background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.5); box-shadow: 0 0 10px rgba(239, 68, 68, 0.2); }

.header-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.action-btn {
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  font-weight: bold;
  transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.action-btn.primary { color: #00f2fe; background: rgba(0, 242, 254, 0.15); border: 1px solid #00f2fe; }
.action-btn.success { color: #10b981; background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; }
.action-btn.danger { color: #ef4444; background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; }
.action-btn.export { color: #d946ef; background: rgba(217, 70, 239, 0.15); border: 1px solid #d946ef; }
.action-btn.secondary { color: rgba(186, 230, 253, 0.88); background: transparent; border: 1px solid rgba(0, 242, 254, 0.3); }

/* 查询栏 */
.query-bar { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; margin-bottom: 24px; flex-wrap: wrap; gap: 16px; }
.query-left, .query-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.query-label { font-weight: 600; color: rgba(186, 230, 253, 0.7); font-size: 13.5px; }
.query-separator { color: rgba(0, 242, 254, 0.5); }
.date-input { padding: 8px 14px; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(0, 242, 254, 0.2); border-radius: 6px; font-size: 13.5px; color: #fff; font-family: "JetBrains Mono", monospace; outline: none; }
::-webkit-calendar-picker-indicator { filter: invert(1) sepia(1) saturate(5) hue-rotate(175deg); opacity: 0.8; cursor: pointer; }

/* 数据卡片网格布局 */
.realtime-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; }
.env-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 24px; }

.metric-card { padding: 20px 24px; display: flex; flex-direction: column; justify-content: center; }
.metric-card.warm { border-top: 2px solid #f59e0b; }
.metric-card.cool { border-top: 2px solid #00f2fe; }
.huge-label { font-size: 15px !important; font-weight: 700; color: rgba(186, 230, 253, 0.9); margin-bottom: 8px; }
.metric-body { display: flex; align-items: baseline; margin-top: 8px; }
.huge-value { font-size: 38px !important; font-weight: 700; line-height: 1; font-family: "JetBrains Mono", monospace; }
.metric-card.warm .huge-value { color: #f59e0b; }
.metric-card.cool .huge-value { color: #00f2fe; }

.env-card { border-top: 2px solid rgba(0, 242, 254, 0.15); }
.env-card.abnormal { border-color: rgba(239, 68, 68, 0.5); background: rgba(239, 68, 68, 0.05); }
.metric-head { display: flex; align-items: center; justify-content: space-between; }
.env-label { font-size: 14.5px; font-weight: 700; color: rgba(186, 230, 253, 0.88); }
.metric-tag { font-size: 11px; font-family: "JetBrains Mono", monospace; padding: 3px 8px; border-radius: 4px; background: rgba(0, 0, 0, 0.5); color: #00f2fe; border: 1px solid rgba(0, 242, 254, 0.2); }
.metric-tag.abnormal { background: rgba(239, 68, 68, 0.15); color: #ef4444; border-color: rgba(239, 68, 68, 0.4); }
.env-card .metric-value { font-size: 32px; font-weight: 700; color: #fff; font-family: "JetBrains Mono", monospace; }
.env-card.abnormal .metric-value { color: #ef4444; }
.metric-unit { margin-left: 8px; color: rgba(0, 242, 254, 0.6); font-size: 13px; font-weight: 600; font-family: -apple-system, sans-serif; }

/* ================= 弹性图表区 ================= */
.chart-grid { 
  display: grid; 
  gap: 16px; 
  flex: 1; /* 让 Grid 在容器内扩展 */
}
.weather-charts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.env-charts { grid-template-columns: repeat(3, minmax(0, 1fr)); }

.chart-card { 
  padding: 16px; 
  display: flex;
  flex-direction: column;
}
.chart-host { 
  width: 100%; 
  flex: 1; /* 核心：取代固定的 height:340px，自适应卡片高度 */
  min-height: 250px; /* 保证缩放时的最小高度 */
}

/* 底部表格 */
.reference-card { padding: 20px; flex: 0 0 auto; }
.reference-card h3 { margin: 0 0 16px 0; color: #00f2fe; font-size: 16px; letter-spacing: 1px; }
table { width: 100%; border-collapse: collapse; background: rgba(0, 0, 0, 0.3); border-radius: 6px; overflow: hidden; }
th, td { padding: 12px 16px; border-bottom: 1px dashed rgba(0, 242, 254, 0.15); text-align: left; font-size: 13px; color: rgba(186, 230, 253, 0.88); }
thead th { color: #00f2fe; background: linear-gradient(90deg, rgba(0, 242, 254, 0.15), rgba(0, 114, 255, 0.05)); border-bottom: 1px solid rgba(0, 242, 254, 0.4); }
tbody tr:hover { background-color: rgba(0, 242, 254, 0.1); }
tbody tr:last-child td { border-bottom: none; }

/* 响应式调整 */
@media (max-width: 1200px) {
  .env-grid, .env-charts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .realtime-grid, .weather-charts, .env-grid, .env-charts { grid-template-columns: 1fr; }
  .elastic-content-area { flex: none; height: auto; } /* 移动端取消高度强行铺满，允许滚动 */
  .title-wrapper h2 { font-size: 19px; }
  .huge-value { font-size: 32px !important; }
}
</style>