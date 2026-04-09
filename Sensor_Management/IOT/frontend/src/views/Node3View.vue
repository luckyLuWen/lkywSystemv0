<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { store } from '../store.js' // 确保这里引入了你的全局 store
import * as echarts from 'echarts'

const chartWindRef = ref(null)
let myChartWind = null

const isSystemRunning = ref(true)
const isAutoRefresh = ref(true)
let refreshInterval = null
const queryStart = ref('')
const queryEnd = ref('')

const goBack = () => window.history.back()

// 计算风向角度
const windRotation = computed(() => {
  const dir = store.data.node3.wind_dir; // 注意：这里数据源是 node3
  if (!dir || dir === '--') return 0;
  const map = {
    "北": 0, "北偏东": 22.5, "东北": 45, "东偏北": 67.5,
    "东": 90, "东偏南": 112.5, "东南": 135, "南偏东": 157.5,
    "南": 180, "南偏西": 202.5, "西南": 225, "西偏南": 247.5,
    "西": 270, "西偏北": 292.5, "西北": 315, "北偏西": 337.5
  };
  return map[dir] !== undefined ? map[dir] : 0;
})

// 初始化图表
const initCharts = () => {
  if (chartWindRef.value) {
    myChartWind = echarts.init(chartWindRef.value)
    myChartWind.setOption({
      title: { text: '🌬️ 风速趋势 (24h)', left: 'center', textStyle: { color: '#3182ce', fontSize: 16 } },
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
      dataZoom: [
        { type: 'slider', show: true, xAxisIndex: 0, start: 0, end: 100, bottom: 10 },
        { type: 'inside', xAxisIndex: 0, start: 0, end: 100 }
      ],
      xAxis: { type: 'category', boundaryGap: false, data: [] },
      yAxis: { type: 'value', name: 'm/s', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [{ 
        name: '风速', type: 'line', smooth: true, 
        data: [], 
        itemStyle: { color: '#3182ce' }, 
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{offset: 0, color: 'rgba(49,130,206,0.3)'}, {offset: 1, color: 'rgba(49,130,206,0.0)'}]) } 
      }]
    })
  }
}

// 获取历史数据
const fetchHistory = async (params = {}) => {
  try {
    let url = 'http://localhost:8000/api/history'
    const queryParams = new URLSearchParams()
    
    if (params.start && params.end) {
      queryParams.append('start', params.start)
      queryParams.append('end', params.end)
      isAutoRefresh.value = false
      if (refreshInterval) clearInterval(refreshInterval)
    } else {
      queryParams.append('limit', params.limit || 100)
    }

    const res = await fetch(`${url}?${queryParams.toString()}`)
    const data = await res.json()
    
    const times = data.map(item => item.timestamp.substring(11, 19))
    const winds = data.map(item => item.wind_speed) // 后端返回字段是 wind_speed
    
    if (myChartWind) myChartWind.setOption({ xAxis: { data: times }, series: [{ data: winds }] })

  } catch (err) { console.error(err) }
}

const handleTimeQuery = () => { fetchHistory({ start: queryStart.value, end: queryEnd.value }) }
const handleExport = () => {
  let url = 'http://localhost:8000/api/export'
  if (queryStart.value && queryEnd.value) { url += `?start=${queryStart.value}&end=${queryEnd.value}` }
  window.open(url, '_blank')
}

const toggleAutoRefresh = () => {
  isAutoRefresh.value = !isAutoRefresh.value
  if (isAutoRefresh.value) { 
    fetchHistory({ limit: 100 }); 
    refreshInterval = setInterval(() => fetchHistory({ limit: 100 }), 3000) 
  } else { 
    clearInterval(refreshInterval) 
  }
}

const toggleSystem = async () => {
  try {
    const newState = !isSystemRunning.value
    await fetch('http://localhost:8000/api/control', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({active: newState}) })
    isSystemRunning.value = newState
  } catch (e) { alert("后端连接失败") }
}

const checkSystemStatus = async () => { try { const res = await fetch('http://localhost:8000/api/status'); const d = await res.json(); isSystemRunning.value = d.running } catch (e){} }
const handleResize = () => { myChartWind && myChartWind.resize() }

onMounted(async () => {
  await nextTick(); 
  initCharts(); 
  fetchHistory({ limit: 100 }); 
  checkSystemStatus()
  refreshInterval = setInterval(() => fetchHistory({ limit: 100 }), 3000)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => { 
  if (refreshInterval) clearInterval(refreshInterval); 
  window.removeEventListener('resize', handleResize); 
  if (myChartWind) myChartWind.dispose() 
})
</script>

<template>
  <div class="page-container">
    <div class="header-bar">
      <div class="left">
        <button @click="goBack" class="back-btn">← 返回首页</button>
        <h2>🌬️ 节点3 - 风速风向监测</h2>
      </div>
      <div class="right-controls">
        <button class="ctrl-btn" :class="isSystemRunning ? 'stop-btn' : 'start-btn'" @click="toggleSystem">{{ isSystemRunning ? '🛑 停止采集' : '▶️ 开始采集' }}</button>
        <button class="ctrl-btn refresh-btn" :class="{ active: isAutoRefresh }" @click="toggleAutoRefresh">{{ isAutoRefresh ? '🔄 自动刷新' : '⏸️ 暂停刷新' }}</button>
      </div>
    </div>

    <div class="query-bar">
      <span class="query-label">📅 历史范围:</span>
      <input type="datetime-local" v-model="queryStart" class="date-input"> 
      <span class="to">至</span> 
      <input type="datetime-local" v-model="queryEnd" class="date-input">
      <button class="query-btn" @click="handleTimeQuery">🔍 查询</button>
      <button class="export-btn" @click="handleExport">📥 导出 Excel</button>
      <button class="reset-btn" @click="toggleAutoRefresh">↩️ 重置实时</button>
    </div>

    <div class="realtime-cards">
      <div class="card wind-card">
        <div class="label">实时风速</div>
        <div class="value">{{ store.data.node3.wind }} <small>m/s</small></div>
        <div class="sub-info">
          等级: {{ store.data.node3.wind > 10.7 ? '强风' : (store.data.node3.wind > 5.4 ? '和风' : '微风') }}
        </div>
      </div>
      
      <div class="card compass-card">
        <div class="label">实时风向</div>
        <div class="compass-box">
          <div class="compass-dial">
            <span class="dir-n">N</span><span class="dir-e">E</span><span class="dir-s">S</span><span class="dir-w">W</span>
            <div class="needle" :style="{ transform: `translate(-50%, -50%) rotate(${windRotation}deg)` }"></div>
          </div>
        </div>
        <div class="value text-value">{{ store.data.node3.wind_dir }}</div>
      </div>
    </div>

    <div class="chart-box">
      <div ref="chartWindRef" style="width: 100%; height: 400px;"></div>
    </div>
  </div>
</template>

<style scoped>
/* 这里直接复用了你提供的样式，保证风格一致 */
.page-container { padding: 20px; height: 100vh; overflow-y: auto; background: #f7fafc; }
.header-bar, .query-bar { display: flex; align-items: center; background: white; padding: 15px 20px; border-radius: 12px; margin-bottom: 20px; gap: 10px; flex-wrap: wrap; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
.header-bar { justify-content: space-between; }
.back-btn, .ctrl-btn, .query-btn, .export-btn, .reset-btn { padding: 8px 15px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.back-btn { background: #edf2f7; color: #4a5568; }
.start-btn { background: #48bb78; color: white; } .stop-btn { background: #f56565; color: white; }
.refresh-btn { background: #e2e8f0; color: #4a5568; } .refresh-btn.active { background: #4299e1; color: white; }
.query-btn { background: #805ad5; color: white; } .export-btn { background: #38a169; color: white; } .reset-btn { background: transparent; border: 1px solid #cbd5e0; color: #718096; margin-left: auto; }
.date-input { padding: 8px; border: 1px solid #e2e8f0; border-radius: 6px; }
.realtime-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.card { background: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.03); display: flex; flex-direction: column; justify-content: center; align-items: center; }
.label { color: #718096; font-size: 0.9rem; margin-bottom: 10px; }
.value { font-size: 2.5rem; font-weight: bold; color: #2d3748; margin: 5px 0; }
.text-value { font-size: 1.8rem; color: #4a5568; }
.wind-card .value { color: #3182ce; } .sub-info { font-size: 0.9rem; color: #a0aec0; }
.compass-box { width: 140px; height: 140px; position: relative; margin: 10px 0; }
.compass-dial { width: 100%; height: 100%; border-radius: 50%; border: 4px solid #e2e8f0; position: relative; background: radial-gradient(circle, #ffffff 40%, #f7fafc 100%); box-shadow: inset 0 2px 8px rgba(0,0,0,0.05); }
.dir-n, .dir-e, .dir-s, .dir-w { position: absolute; font-size: 1rem; font-weight: bold; color: #cbd5e0; }
.dir-n { top: 5px; left: 50%; transform: translateX(-50%); color: #e53e3e; } .dir-s { bottom: 5px; left: 50%; transform: translateX(-50%); } .dir-e { right: 10px; top: 50%; transform: translateY(-50%); } .dir-w { left: 10px; top: 50%; transform: translateY(-50%); }
.needle { position: absolute; top: 50%; left: 50%; width: 8px; height: 70%; background: linear-gradient(to top, #718096 50%, #e53e3e 50%); transform-origin: center center; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1); z-index: 10; }
.needle::after { content: ''; position: absolute; top: 50%; left: 50%; width: 12px; height: 12px; background: #2d3748; border-radius: 50%; transform: translate(-50%, -50%); border: 2px solid white; }
.chart-box { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
</style>