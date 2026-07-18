<script setup>
import { nextTick, onMounted, onUnmounted, ref, computed } from 'vue'
import * as echarts from 'echarts'
import { store } from '../store.js'
import {
  buildGatewayApiUrl,
  buildGatewayExportUrl,
  buildGatewayHistoryUrl,
} from '../gateway-config.js'

// DOM Refs for Charts
const chartTempRef = ref(null)
const chartHumRef = ref(null)
const chartSmokeRef = ref(null)
const chartTvocRef = ref(null)
const chartCoRef = ref(null)

// State
const nodeState = computed(() => store.nodes.node1 || { online: false, address: '' })
const isSystemRunning = ref(false)
const isAutoRefresh = ref(true)
const queryStart = ref('')
const queryEnd = ref('')

let refreshTimer = null
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
  top: 8, // 让标题距离顶部有一定呼吸感
  textStyle: { color, fontSize: 16, fontWeight: '700' } // 提升字号与字重
},
tooltip: { trigger: 'axis' },
grid: { left: '5%', right: '5%', top: 55, bottom: '15%', containLabel: true }, // 显式增加 top 间距，防止标题与图表重叠
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
  const value = Number(store.data.node1?.[sensor.key] ?? 0)
  return value >= sensor.threshold ? 'abnormal' : 'normal'
}

// 统一拉取所有历史数据
async function fetchHistory(params = {}) {
  try {
    const response = await fetch(buildGatewayHistoryUrl(params), { cache: 'no-store' })
    const data = await response.json()
    const rows = Array.isArray(data) ? data : []

    const times = rows.map((item) => formatTimeLabel(item.timestamp))
    
    // 更新所有图表
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

// 修复后的采集开关逻辑
async function toggleSystem() {
  const nextState = !isSystemRunning.value
  isSystemRunning.value = nextState // 乐观更新 UI
  
  try {
    const response = await fetch(buildGatewayApiUrl('control'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: nextState }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
  } catch (error) {
    // 失败则回退状态
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

function handleResize() {
  tempChart?.resize()
  humChart?.resize()
  smokeChart?.resize()
  tvocChart?.resize()
  coChart?.resize()
}

onMounted(async () => {
  await nextTick()
  // 初始化气象图表
  tempChart = createChart(chartTempRef.value, '环境温度变化趋势', '#ed8936')
  humChart = createChart(chartHumRef.value, '相对湿度变化趋势', '#3182ce')
  // 初始化环境图表
  smokeChart = createChart(chartSmokeRef.value, '烟雾浓度趋势', '#6b7280')
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
  tempChart?.dispose()
  humChart?.dispose()
  smokeChart?.dispose()
  tvocChart?.dispose()
  coChart?.dispose()
})
</script>

<template>
  <div class="page-container">
    
    <div class="header-bar">
      <div class="title-wrapper">
        <h2>多源数据感知单元-003</h2>
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

    <h3 class="section-title">气象核心指标</h3>
    <div class="realtime-grid">
      <div class="metric-card warm">
        <span class="metric-label huge-label">🌡️ 实时温度</span>
        <div class="metric-body">
          <strong class="metric-value huge-value">{{ store.data.node1?.temp ?? '--' }}</strong>
          <span class="metric-unit">°C</span>
        </div>
      </div>
      <div class="metric-card cool">
        <span class="metric-label huge-label">💧 实时湿度</span>
        <div class="metric-body">
          <strong class="metric-value huge-value">{{ store.data.node1?.hum ?? '--' }}</strong>
          <span class="metric-unit">%</span>
        </div>
      </div>
    </div>

    <h3 class="section-title">环境质量评估</h3>
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
          <strong class="metric-value">{{ store.data.node1?.[sensor.key] ?? '--' }}</strong>
          <span class="metric-unit">{{ sensor.unit }}</span>
        </div>
      </div>
    </div>

    <h3 class="section-title">全要素趋势分析</h3>
    
    <div class="chart-grid weather-charts">
      <div class="chart-card"><div ref="chartTempRef" class="chart-host"></div></div>
      <div class="chart-card"><div ref="chartHumRef" class="chart-host"></div></div>
    </div>
    
    <div class="chart-grid env-charts">
      <div class="chart-card"><div ref="chartSmokeRef" class="chart-host"></div></div>
      <div class="chart-card"><div ref="chartTvocRef" class="chart-host"></div></div>
      <div class="chart-card"><div ref="chartCoRef" class="chart-host"></div></div>
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
</template>

<style scoped>
/* 基础与布局 */
.page-container {
  min-height: 100vh;
  padding: 24px 32px;
  /* 统一深色科技背景 */
  background: #050b14 radial-gradient(circle at 50% 0%, #0a192f 0%, #050b14 100%);
  overflow-y: auto;
  font-family: 'Rajdhani', system-ui, -apple-system, sans-serif;
  color: #e2e8f0;
}

.section-title {
  margin: 28px 0 16px 4px;
  font-size: 1.25rem;
  font-weight: 700;
  color: #64ffda; /* 科技青色 */
  border-left: 4px solid #3b82f6;
  padding-left: 10px;
  text-shadow: 0 0 8px rgba(100, 255, 218, 0.3);
  letter-spacing: 1px;
}

/* 卡片通用样式 (深色玻璃拟态) */
.header-bar, .query-bar, .metric-card, .chart-card, .reference-card {
  background: rgba(10, 25, 47, 0.6);
  border-radius: 8px;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);
  border: 1px solid #1e3a8a;
  backdrop-filter: blur(10px);
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
}

.title-wrapper {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-wrapper h2 {
  margin: 0;
  color: #64ffda;
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: 2px;
  font-family: 'Orbitron', sans-serif;
  text-shadow: 0 0 10px rgba(100, 255, 218, 0.4);
}

.status-badge {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  border: 1px solid;
}

.status-badge.online {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  border-color: #10b981;
}

.status-badge.offline {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 按钮样式 (幽灵科技风) */
.action-btn {
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: bold;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.5px;
}
.action-btn:active { transform: scale(0.96); }

.action-btn.primary { color: #60a5fa; background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6; }
.action-btn.primary:hover { background: rgba(59, 130, 246, 0.3); box-shadow: 0 0 10px rgba(59,130,246,0.3); }

.action-btn.success { color: #10b981; background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; }
.action-btn.success:hover { background: rgba(16, 185, 129, 0.3); box-shadow: 0 0 10px rgba(16,185,129,0.3); }

.action-btn.danger { color: #ef4444; background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; }
.action-btn.danger:hover { background: rgba(239, 68, 68, 0.3); box-shadow: 0 0 10px rgba(239,68,68,0.3); }

.action-btn.export { color: #c084fc; background: rgba(192, 132, 252, 0.2); border: 1px solid #c084fc; }
.action-btn.export:hover { background: rgba(192, 132, 252, 0.3); box-shadow: 0 0 10px rgba(192,132,252,0.3); }

.action-btn.secondary { color: #cbd5e1; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); }
.action-btn.secondary:hover { border-color: #64ffda; color: #64ffda; }
.action-btn.secondary.active { color: #60a5fa; background: rgba(96, 165, 250, 0.2); border-color: #60a5fa; box-shadow: 0 0 10px rgba(96,165,250,0.2); }

/* 查询栏 */
.query-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}
.query-left, .query-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.query-label { font-weight: 600; color: #94a3b8; font-size: 0.9rem; }
.query-separator { color: #475569; }
.date-input {
  padding: 8px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  font-size: 0.9rem;
  color: #e2e8f0;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  font-family: 'Orbitron', monospace;
}
.date-input:focus { border-color: #60a5fa; box-shadow: 0 0 8px rgba(96, 165, 250, 0.4); }
/* 修复深色模式下 Webkit 浏览器原生日历图标颜色 */
::-webkit-calendar-picker-indicator { filter: invert(1); opacity: 0.6; cursor: pointer; }

/* 数据卡片网格布局 */
.realtime-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 24px; }
.env-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 30px; }

.metric-card {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.metric-card:hover {
  border-color: #60a5fa;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), inset 0 0 15px rgba(96, 165, 250, 0.1);
  transform: translateY(-2px);
  background: rgba(15, 30, 60, 0.8);
}

/* 核心指标专属样式 */
.metric-card.warm { border-top: 2px solid #f59e0b; }
.metric-card.cool { border-top: 2px solid #3b82f6; }

.huge-label {
  font-size: 1.1rem !important; 
  font-weight: 700;
  color: #cbd5e1;
  margin-bottom: 8px;
  letter-spacing: 1px;
}
.metric-body { display: flex; align-items: baseline; margin-top: 8px; }
.huge-value {
  font-size: 3rem !important; 
  font-weight: 700;
  line-height: 1;
  font-family: 'Orbitron', monospace;
  text-shadow: 0 0 10px rgba(255,255,255,0.1);
}
.metric-card.warm .huge-value { color: #f59e0b; text-shadow: 0 0 10px rgba(245, 158, 11, 0.3); }
.metric-card.cool .huge-value { color: #60a5fa; text-shadow: 0 0 10px rgba(96, 165, 250, 0.3); }

/* 环境质量卡片样式 */
.env-card { border-top: 2px solid rgba(255, 255, 255, 0.1); }
.env-card:hover { border-top-color: #64ffda; box-shadow: 0 0 15px rgba(100,255,218,0.15) inset; }
.env-card.abnormal { border-color: #ef4444; background: rgba(239, 68, 68, 0.05); }
.env-card.abnormal:hover { box-shadow: 0 0 15px rgba(239,68,68,0.2) inset; }

.metric-head { display: flex; align-items: center; justify-content: space-between; }
.env-label { font-size: 1rem; font-weight: 700; color: #94a3b8; }

.metric-tag {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.4);
  color: #64748b;
  border: 1px solid rgba(255,255,255,0.05);
}
.metric-tag.abnormal { background: rgba(239, 68, 68, 0.2); color: #ef4444; border-color: #ef4444; }

.env-card .metric-value {
  font-size: 2.2rem;
  font-weight: 700;
  color: #e2e8f0;
  font-family: 'Orbitron', monospace;
}
.env-card.abnormal .metric-value { color: #ef4444; text-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }

.metric-unit { margin-left: 8px; color: #64748b; font-size: 0.9rem; font-weight: 600; font-family: sans-serif; }

/* 图表区 */
.chart-grid { display: grid; gap: 16px; margin-bottom: 24px; }
.weather-charts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.env-charts { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.chart-card { padding: 16px; }
.chart-host { width: 100%; height: 340px; }

/* 底部表格 (深色重构) */
.reference-card { padding: 20px; margin-bottom: 40px;}
.reference-card h3 { margin: 0 0 16px 0; color: #60a5fa; font-size: 1.1rem; letter-spacing: 1px; }
table { width: 100%; border-collapse: collapse; background: rgba(0, 0, 0, 0.2); border-radius: 6px; overflow: hidden; }
th, td { padding: 12px 16px; border-bottom: 1px dashed rgba(255, 255, 255, 0.05); text-align: left; font-size: 0.85rem; color: #cbd5e1; }
thead th { color: #64ffda; background: rgba(10, 25, 47, 0.8); font-weight: 700; border-bottom: 1px solid #1e3a8a; letter-spacing: 0.5px; }
tbody tr { transition: background 0.2s; }
tbody tr:hover { background-color: rgba(96, 165, 250, 0.1); }
tbody tr:last-child td { border-bottom: none; }

/* 响应式调整 */
@media (max-width: 1200px) {
  .env-grid, .env-charts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .realtime-grid, .weather-charts, .env-grid, .env-charts { grid-template-columns: 1fr; }
  .title-wrapper h2 { font-size: 1.3rem; }
  .huge-value { font-size: 2.5rem !important; }
}
</style>