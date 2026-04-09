<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { store } from '../store.js'
import * as echarts from 'echarts'

const chartTempRef = ref(null)
const chartHumRef = ref(null)
let myChartTemp = null; let myChartHum = null
const isSystemRunning = ref(true); const isAutoRefresh = ref(true); let refreshInterval = null
const queryStart = ref(''); const queryEnd = ref('')
const goBack = () => window.history.back()

const initCharts = () => {
  // 温度表配置 dataZoom
  if (chartTempRef.value) {
    myChartTemp = echarts.init(chartTempRef.value)
    myChartTemp.setOption({
      title: { text: '🌡️ 温度趋势', left: 'center', textStyle: { color: '#ed8936' } },
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true }, // 留空间
      dataZoom: [{ type: 'slider', show: true, bottom: 5 }, { type: 'inside' }], // 👈 滑块
      xAxis: { type: 'category', boundaryGap: false, data: [] },
      yAxis: { type: 'value' },
      series: [{ name: '温度', type: 'line', smooth: true, data: [], itemStyle: { color: '#ed8936' }, areaStyle: { opacity: 0.2 } }]
    })
  }
  // 湿度表配置 dataZoom
  if (chartHumRef.value) {
    myChartHum = echarts.init(chartHumRef.value)
    myChartHum.setOption({
      title: { text: '💧 湿度趋势', left: 'center', textStyle: { color: '#4299e1' } },
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true }, // 留空间
      dataZoom: [{ type: 'slider', show: true, bottom: 5 }, { type: 'inside' }], // 👈 滑块
      xAxis: { type: 'category', boundaryGap: false, data: [] },
      yAxis: { type: 'value' },
      series: [{ name: '湿度', type: 'line', smooth: true, data: [], itemStyle: { color: '#4299e1' }, areaStyle: { opacity: 0.2 } }]
    })
  }
}

const fetchHistory = async (params = {}) => {
  try {
    let url = 'http://localhost:8000/api/history'
    const queryParams = new URLSearchParams()
    if (params.start && params.end) { queryParams.append('start', params.start); queryParams.append('end', params.end); isAutoRefresh.value = false; clearInterval(refreshInterval) } 
    else { queryParams.append('limit', params.limit || 100) }

    const res = await fetch(`${url}?${queryParams.toString()}`)
    const data = await res.json()
    
    const times = data.map(item => item.timestamp.substring(11, 19))
    const temps = data.map(item => item.n1_temp)
    const hums = data.map(item => item.n1_hum)
    
    if (myChartTemp) myChartTemp.setOption({ xAxis: { data: times }, series: [{ data: temps }] })
    if (myChartHum) myChartHum.setOption({ xAxis: { data: times }, series: [{ data: hums }] })
  } catch (err) { console.error(err) }
}

const handleTimeQuery = () => { fetchHistory({ start: queryStart.value, end: queryEnd.value }) }
const handleExport = () => { let url = 'http://localhost:8000/api/export'; if (queryStart.value && queryEnd.value) { url += `?start=${queryStart.value}&end=${queryEnd.value}` } window.open(url, '_blank') }
const toggleAutoRefresh = () => { isAutoRefresh.value = !isAutoRefresh.value; if (isAutoRefresh.value) { fetchHistory({limit:100}); refreshInterval=setInterval(()=>fetchHistory({limit:100}),3000) } else { clearInterval(refreshInterval) } }
const toggleSystem = async () => { try { const ns = !isSystemRunning.value; await fetch('http://localhost:8000/api/control', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({active:ns})}); isSystemRunning.value=ns } catch(e){} }
const checkSystemStatus = async () => { try{const r=await fetch('http://localhost:8000/api/status');const d=await r.json();isSystemRunning.value=d.running}catch(e){} }
const handleResize = () => { myChartTemp && myChartTemp.resize(); myChartHum && myChartHum.resize() }

onMounted(async () => { await nextTick(); initCharts(); fetchHistory({limit:100}); checkSystemStatus(); refreshInterval=setInterval(()=>fetchHistory({limit:100}),3000); window.addEventListener('resize', handleResize) })
onUnmounted(() => { clearInterval(refreshInterval); window.removeEventListener('resize', handleResize); if (myChartTemp) myChartTemp.dispose(); if (myChartHum) myChartHum.dispose() })
</script>

<template>
  <div class="page-container">
    <div class="header-bar">
      <div class="left"><button @click="goBack" class="back-btn">← 返回</button><h2>🌡️ 环境监控</h2></div>
      <div class="right-controls">
        <button class="ctrl-btn" :class="isSystemRunning ? 'stop-btn' : 'start-btn'" @click="toggleSystem">{{ isSystemRunning ? '🛑 停止采集' : '▶️ 开始采集' }}</button>
        <button class="ctrl-btn refresh-btn" :class="{ active: isAutoRefresh }" @click="toggleAutoRefresh">{{ isAutoRefresh ? '🔄 自动刷新' : '⏸️ 暂停刷新' }}</button>
      </div>
    </div>
    <div class="query-bar">
      <span class="query-label">📅 历史范围:</span>
      <input type="datetime-local" v-model="queryStart" class="date-input"> <span class="to">至</span> <input type="datetime-local" v-model="queryEnd" class="date-input">
      <button class="query-btn" @click="handleTimeQuery">🔍 查询</button>
      <button class="export-btn" @click="handleExport">📥 导出 Excel</button>
      <button class="reset-btn" @click="toggleAutoRefresh">↩️ 重置实时</button>
    </div>
    <div class="realtime-cards">
      <div class="card temp-card"><div class="label">实时温度</div><div class="value">{{ store.data.node1.temp }} <small>℃</small></div></div>
      <div class="card hum-card"><div class="label">实时湿度</div><div class="value">{{ store.data.node1.hum }} <small>%</small></div></div>
    </div>
    <div class="charts-container">
      <div class="chart-box"><div ref="chartTempRef" style="width: 100%; height: 350px;"></div></div>
      <div class="chart-box"><div ref="chartHumRef" style="width: 100%; height: 350px;"></div></div>
    </div>
  </div>
</template>

<style scoped>
/* 样式复用 */
.page-container { padding: 20px; height: 100vh; overflow-y: auto; background: #f7fafc; }
.header-bar, .query-bar { display: flex; align-items: center; background: white; padding: 15px; border-radius: 12px; margin-bottom: 20px; gap: 10px; flex-wrap: wrap; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
.header-bar { justify-content: space-between; }
.back-btn, .ctrl-btn, .query-btn, .export-btn, .reset-btn { padding: 8px 15px; border: none; border-radius: 6px; cursor: pointer; }
.back-btn { background: #edf2f7; }
.start-btn { background: #48bb78; color: white; } .stop-btn { background: #f56565; color: white; }
.refresh-btn { background: #e2e8f0; } .refresh-btn.active { background: #4299e1; color: white; }
.query-btn { background: #805ad5; color: white; } .export-btn { background: #38a169; color: white; } .reset-btn { background: transparent; border: 1px solid #ddd; }
.realtime-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.card { background: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }
.value { font-size: 2.5rem; font-weight: bold; color: #2d3748; }
.temp-card .value { color: #dd6b20; } .hum-card .value { color: #3182ce; }
.charts-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.chart-box { background: white; padding: 15px; border-radius: 12px; }
</style>