<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { store } from '../store.js'
import * as echarts from 'echarts'

// --- 1. 图表引用 ---
const chartSmokeRef = ref(null)
const chartTvocRef = ref(null)
const chartCoRef = ref(null)
let myChartSmoke = null
let myChartTvoc = null
let myChartCo = null

// --- 2. 控制状态 ---
const isSystemRunning = ref(true)
const isAutoRefresh = ref(true)
let refreshInterval = null
const queryStart = ref('')
const queryEnd = ref('')

// --- 3. 传感器定义 (已更新单位和最大值) ---
const sensors = [
  // 🟢 [修改] 单位 ug/m³，最大值 100万
  { key: 'smoke', name: '烟雾浓度', icon: '🌫️', unit: 'ug/m³', max: 1000000 },
  { key: 'tvoc', name: 'TVOC', icon: '🧪', unit: 'mg/m³', max: 2.0 },
  { key: 'co', name: '一氧化碳', icon: '⚠️', unit: 'ppm', max: 100 }
]

// --- 4. 初始化图表 (已更新标题) ---
const initCharts = () => {
  const commonGrid = { left: '3%', right: '5%', bottom: '15%', containLabel: true }
  const commonZoom = [{ type: 'slider', show: true, bottom: 5 }, { type: 'inside' }]

  if (chartSmokeRef.value) {
    myChartSmoke = echarts.init(chartSmokeRef.value)
    myChartSmoke.setOption({
      // 🟢 [修改] 标题带单位
      title: { text: '🌫️ 烟雾趋势 (ug/m³)', left: 'center', textStyle: { color: '#606266' } },
      tooltip: { trigger: 'axis' },
      grid: commonGrid,
      dataZoom: commonZoom,
      xAxis: { type: 'category', boundaryGap: false, data: [] },
      yAxis: { type: 'value' },
      series: [{ name: '烟雾', type: 'line', smooth: true, data: [], itemStyle: { color: '#606266' }, areaStyle: { opacity: 0.2 } }]
    })
  }
  if (chartTvocRef.value) {
    myChartTvoc = echarts.init(chartTvocRef.value)
    myChartTvoc.setOption({
      title: { text: '🧪 TVOC 趋势 (mg/m³)', left: 'center', textStyle: { color: '#805ad5' } },
      tooltip: { trigger: 'axis' },
      grid: commonGrid,
      dataZoom: commonZoom,
      xAxis: { type: 'category', boundaryGap: false, data: [] },
      yAxis: { type: 'value' },
      series: [{ name: 'TVOC', type: 'line', smooth: true, data: [], itemStyle: { color: '#805ad5' }, areaStyle: { opacity: 0.2 } }]
    })
  }
  if (chartCoRef.value) {
    myChartCo = echarts.init(chartCoRef.value)
    myChartCo.setOption({
      title: { text: '⚠️ CO 趋势 (ppm)', left: 'center', textStyle: { color: '#F56C6C' } },
      tooltip: { trigger: 'axis' },
      grid: commonGrid,
      dataZoom: commonZoom,
      xAxis: { type: 'category', boundaryGap: false, data: [] },
      yAxis: { type: 'value' },
      series: [{ name: 'CO', type: 'line', smooth: true, data: [], itemStyle: { color: '#F56C6C' }, areaStyle: { opacity: 0.2 } }]
    })
  }
}

// --- 5. 获取历史数据 ---
const fetchHistory = async (params = {}) => {
  try {
    let url = 'http://localhost:8000/api/history'
    const queryParams = new URLSearchParams()
    
    if (params.start && params.end) { 
        queryParams.append('start', params.start.replace('T', ' '))
        queryParams.append('end', params.end.replace('T', ' '))
        isAutoRefresh.value = false
        clearInterval(refreshInterval) 
    } else { 
        queryParams.append('limit', params.limit || 100) 
    }

    const res = await fetch(`${url}?${queryParams.toString()}`)
    const data = await res.json()
    if (!data || data.length === 0) return

    const times = data.map(item => item.timestamp.length > 10 ? item.timestamp.substring(11, 19) : item.timestamp)
    
    // 保持 Node2 的数据映射
    const smokes = data.map(item => item.n2_smoke)
    const tvocs = data.map(item => item.n2_tvoc)
    const cos = data.map(item => item.n2_co)
    
    if (myChartSmoke) myChartSmoke.setOption({ xAxis: { data: times }, series: [{ data: smokes }] })
    if (myChartTvoc) myChartTvoc.setOption({ xAxis: { data: times }, series: [{ data: tvocs }] })
    if (myChartCo) myChartCo.setOption({ xAxis: { data: times }, series: [{ data: cos }] })

  } catch (err) { console.error("History Error:", err) }
}

// --- 6. 交互逻辑 ---
const handleTimeQuery = () => { fetchHistory({ start: queryStart.value, end: queryEnd.value }) }
const handleExport = () => { 
    let url = 'http://localhost:8000/api/export'
    if (queryStart.value && queryEnd.value) url += `?start=${queryStart.value}&end=${queryEnd.value}`
    window.open(url, '_blank') 
}
const toggleAutoRefresh = () => { 
    isAutoRefresh.value = !isAutoRefresh.value
    if (isAutoRefresh.value) { 
        fetchHistory({limit:100})
        refreshInterval = setInterval(() => fetchHistory({limit:100}), 3000) 
    } else { clearInterval(refreshInterval) } 
}
const toggleSystem = async () => { 
    try { 
        const ns = !isSystemRunning.value
        await fetch('http://localhost:8000/api/control', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({active: ns}) })
        isSystemRunning.value = ns 
    } catch(e){} 
}
const checkSystemStatus = async () => { 
    try { const r = await fetch('http://localhost:8000/api/status'); const d = await r.json(); isSystemRunning.value = d.running } catch(e){} 
}
const handleResize = () => { 
    myChartSmoke && myChartSmoke.resize()
    myChartTvoc && myChartTvoc.resize() 
    myChartCo && myChartCo.resize()
}

// --- 7. 卡片状态样式 (关键修改: 阈值适配) ---
const getStatus = (key, val) => {
  let isDanger = false
  // 🟢 [修改] 烟雾报警阈值 600,000
  if (key === 'smoke' && val > 600000) isDanger = true
  if (key === 'tvoc' && val > 1.0) isDanger = true
  if (key === 'co' && val > 50) isDanger = true
  
  // 🟢 [修改] 进度条分母适配
  let maxDivisor = 1000
  if (key === 'smoke') maxDivisor = 1000000 // 100万
  if (key === 'tvoc') maxDivisor = 2.0
  if (key === 'co') maxDivisor = 100

  return {
    class: isDanger ? 'card-danger' : 'card-normal',
    text: isDanger ? '⚠️ 异常' : '✅ 正常',
    color: isDanger ? '#F56C6C' : '#67C23A',
    percent: Math.min((val / maxDivisor) * 100, 100) + '%'
  }
}

// --- 8. 生命周期 ---
onMounted(async () => { 
    await nextTick()
    initCharts()
    fetchHistory({limit: 100})
    checkSystemStatus()
    refreshInterval = setInterval(() => fetchHistory({limit: 100}), 3000)
    window.addEventListener('resize', handleResize) 
})
onUnmounted(() => { 
    clearInterval(refreshInterval)
    window.removeEventListener('resize', handleResize)
    if (myChartSmoke) myChartSmoke.dispose()
    if (myChartTvoc) myChartTvoc.dispose()
    if (myChartCo) myChartCo.dispose()
})
</script>

<template>
  <div class="full-page">
    
    <div class="header-bar">
      <div class="left">
        <button class="back-btn" @click="$router.push('/')">← 返回</button>
        <div class="titles">
          <h2>📍 节点 B - 空气质量监测</h2>
          <span class="subtitle">集成控制面板 | 实验室</span>
        </div>
      </div>
      <div class="right-controls">
        <div class="status-badge" :class="store.connected ? 'bg-green' : 'bg-red'">
          {{ store.connected ? '🟢 在线' : '🔴 离线' }}
        </div>
        <button class="ctrl-btn" :class="isSystemRunning ? 'stop-btn' : 'start-btn'" @click="toggleSystem">
          {{ isSystemRunning ? '🛑 停止采集' : '▶️ 开始采集' }}
        </button>
        <button class="ctrl-btn refresh-btn" :class="{ active: isAutoRefresh }" @click="toggleAutoRefresh">
          {{ isAutoRefresh ? '🔄 自动' : '⏸️ 暂停' }}
        </button>
      </div>
    </div>

    <div class="query-bar">
      <span class="query-label">📅 历史范围:</span>
      <input type="datetime-local" v-model="queryStart" class="date-input"> 
      <span class="to">至</span> 
      <input type="datetime-local" v-model="queryEnd" class="date-input">
      <button class="query-btn" @click="handleTimeQuery">🔍 查询</button>
      <button class="export-btn" @click="handleExport">📥 导出 Excel</button>
      <button class="reset-btn" @click="toggleAutoRefresh">↩️ 重置</button>
    </div>

    <div class="monitor-row">
      <div 
        v-for="item in sensors" 
        :key="item.key" 
        class="big-card"
        :class="getStatus(item.key, store.data.node2[item.key]).class"
      >
        <div class="card-header">
          <span class="icon">{{ item.icon }}</span>
          <span class="name">{{ item.name }}</span>
          <span class="status-tag" :style="{ color: getStatus(item.key, store.data.node2[item.key]).color }">
            {{ getStatus(item.key, store.data.node2[item.key]).text }}
          </span>
        </div>
        <div class="card-body">
          <div class="value">
            {{ store.data.node2[item.key] }}
            <span class="unit">{{ item.unit }}</span>
          </div>
          <div class="progress-bg">
            <div class="progress-fill" :style="{ width: getStatus(item.key, store.data.node2[item.key]).percent, backgroundColor: getStatus(item.key, store.data.node2[item.key]).color }"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="charts-container">
      <div class="chart-box"><div ref="chartSmokeRef" style="width: 100%; height: 300px;"></div></div>
      <div class="chart-box"><div ref="chartTvocRef" style="width: 100%; height: 300px;"></div></div>
      <div class="chart-box"><div ref="chartCoRef" style="width: 100%; height: 300px;"></div></div>
    </div>

    <div class="info-section">
      <h3>📋 实验室安全分级参考</h3>
      <table>
        <thead>
          <tr><th>项目</th><th>优</th><th>良</th><th>危险阈值</th><th>危害</th></tr>
        </thead>
        <tbody>
          <tr><td>🌫️ 烟雾</td><td>0-12万</td><td>12万-36万</td><td class="danger-cell">> 60万</td><td>火灾预警</td></tr>
          <tr><td>🧪 TVOC</td><td>0-0.5</td><td>0.5-0.8</td><td class="danger-cell">> 1.0</td><td>头痛嗜睡</td></tr>
          <tr><td>⚠️ CO</td><td>0-10</td><td>10-24</td><td class="danger-cell">> 50</td><td>缺氧窒息</td></tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<style scoped>
/* 全屏布局 */
.full-page { height: 100vh; display: flex; flex-direction: column; padding: 20px 30px; background-color: #f5f7fa; overflow-y: auto; }

/* 头部栏 */
.header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; background: white; padding: 15px 25px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.03); }
.left { display: flex; align-items: center; gap: 20px; }
.back-btn { padding: 8px 16px; background: #f0f2f5; border: none; border-radius: 6px; cursor: pointer; color: #606266; font-weight: bold; }
.back-btn:hover { background: #e6e8eb; color: #409eff; }
.titles h2 { margin: 0; color: #303133; font-size: 1.4rem; }
.subtitle { color: #909399; font-size: 0.85rem; }

/* 按钮组 */
.right-controls { display: flex; align-items: center; gap: 10px; }
.status-badge { padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 0.9rem; color: white; }
.bg-green { background: #67C23A; } .bg-red { background: #F56C6C; }
.ctrl-btn { padding: 8px 15px; border: none; border-radius: 6px; cursor: pointer; color: white; transition: 0.2s; }
.start-btn { background: #48bb78; } .stop-btn { background: #f56565; }
.refresh-btn { background: #e2e8f0; color: #606266; } .refresh-btn.active { background: #409eff; color: white; }

/* 查询栏 */
.query-bar { display: flex; align-items: center; background: white; padding: 12px 20px; border-radius: 10px; margin-bottom: 20px; gap: 10px; flex-wrap: wrap; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
.date-input { padding: 5px 10px; border: 1px solid #dcdfe6; border-radius: 4px; }
.query-btn { background: #805ad5; color: white; border: none; padding: 6px 15px; border-radius: 4px; cursor: pointer; }
.export-btn { background: #67C23A; color: white; border: none; padding: 6px 15px; border-radius: 4px; cursor: pointer; }
.reset-btn { background: transparent; border: 1px solid #dcdfe6; cursor: pointer; padding: 6px 15px; border-radius: 4px; }

/* 实时卡片 */
.monitor-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }
.big-card { background: white; border-radius: 12px; padding: 20px; border: 1px solid #ebeef5; box-shadow: 0 4px 12px rgba(0,0,0,0.03); transition: transform 0.2s; }
.big-card:hover { transform: translateY(-3px); }
.card-normal { border-left: 4px solid #67C23A; } .card-danger { border-left: 4px solid #F56C6C; background: #fef0f0; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.name { font-weight: bold; color: #606266; margin-left: 8px; flex: 1; }
.value { font-size: 2.8rem; font-weight: bold; color: #303133; text-align: center; margin: 10px 0; }
.unit { font-size: 1rem; color: #909399; font-weight: normal; }
.progress-bg { height: 6px; background: #f0f2f5; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }

/* 图表区 */
.charts-container { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }
.chart-box { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }

/* 底部表格 */
.info-section { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }
table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }
th, td { text-align: left; padding: 10px; border-bottom: 1px solid #ebeef5; }
th { background: #fafafa; font-weight: bold; }
.danger-cell { color: #F56C6C; font-weight: bold; }

@media (max-width: 1024px) {
  .monitor-row, .charts-container { grid-template-columns: 1fr; }
}
</style>