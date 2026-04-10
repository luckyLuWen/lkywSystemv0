<script setup>
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { store } from '../store.js'
import * as echarts from 'echarts'

// --- 1. 数据源选择 (双节点融合) ---
const currentNodeName = "双节点融合 (Node 1 + Node 2)"

// 🟢 [核心逻辑] 获取两台车的数据，取最大值 (Max Pooling)
const data = computed(() => {
  const n1 = store.data.node1 || { temp: 0, tvoc: 0, smoke: 0, co: 0 }
  const n2 = store.data.node2 || { temp: 0, tvoc: 0, smoke: 0, co: 0 }
  
  return {
    temp: Math.max(n1.temp, n2.temp),
    tvoc: Math.max(n1.tvoc, n2.tvoc),
    smoke: Math.max(n1.smoke, n2.smoke),
    co: Math.max(n1.co, n2.co)
  }
})

// 🔌 断网控制
const forceOffline = ref(false)
const isLinkActive = computed(() => store.connected && !forceOffline.value)

// 🔥 模拟报警控制 (新增)
const isTestAlarm = ref(false)

// 模拟红外数据 (基于温度)
const irVal = computed(() => Number((Number(data.value.temp) * 1.2).toFixed(1)))
const numData = computed(() => ({
  temp: Number(data.value.temp),
  tvoc: Number(data.value.tvoc),
  smoke: Number(data.value.smoke),
  co: Number(data.value.co)
}))

// 🚨 确证阶段阈值
const LIMITS = { smoke: 800000, co: 100, tvoc: 3.0, temp: 60, ir: 75 }

// 状态判决 (包含手动测试逻辑)
const status = computed(() => ({
  global: isTestAlarm.value || // 手动触发优先
          numData.value.smoke > LIMITS.smoke || 
          numData.value.co > LIMITS.co || 
          numData.value.tvoc > LIMITS.tvoc || 
          numData.value.temp > LIMITS.temp || 
          irVal.value > LIMITS.ir
}))

const chartRef = ref(null)
let myChart = null

const initChart = () => {
  if (!chartRef.value) return
  myChart = echarts.init(chartRef.value)
  updateChartOption()
}

// --- 渲染逻辑 ---
const updateChartOption = () => {
  if (!myChart) return

  const active = isLinkActive.value
  const alarm = status.value.global

  const theme = {
    bg: alarm ? '#2b0505' : '#0f1114',
    pipe: alarm ? '#5c1919' : '#2D3748',
    line: !active ? '#555' : (alarm ? '#FF0055' : '#00F0FF'), // 保持原有的蓝/红配色
    nodeBorder: alarm ? '#ff4d4f' : '#fff'
  }

  // 坐标配置 (5个节点)
  const startX = 120, midX = 550, endX = 900
  const colors = { ir: '#FF4500', temp: '#FF8C00', smoke: '#A9A9A9', co: '#FFD700', tvoc: '#8A2BE2' }

  const makeNodeStyle = (color) => ({
    color: active ? color : '#555',
    borderColor: theme.nodeBorder, borderWidth: 2, 
    shadowBlur: active ? 10 : 0, shadowColor: color
  })

  // 5个传感器节点 (增加 Temp 和 TVOC)
  const nodes = [
    { name: '📷 红外 (IR)', value: (active ? irVal.value : '--') + ' ℃', x: startX, y: 60, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.ir) },
    { name: '🌡️ 温度 (Temp)', value: (active ? numData.value.temp : '--') + ' ℃', x: startX, y: 140, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.temp) },
    { name: '🌫️ 烟雾', value: (active ? (numData.value.smoke/10000).toFixed(1) : '--') + '万', x: startX, y: 220, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.smoke) },
    { name: '☠️ 气体 (CO)', value: (active ? numData.value.co : '--') + ' ppm', x: startX, y: 300, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.co) },
    { name: '🧪 挥发物', value: (active ? numData.value.tvoc : '--') + ' mg', x: startX, y: 380, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.tvoc) },
    
    { 
      name: '🧠 五维融合确证', x: midX, y: 220, symbol: 'diamond', symbolSize: [160, 100],
      itemStyle: { 
        color: alarm ? '#4a0f0f' : '#2b3a4a', 
        borderColor: theme.line, borderWidth: 4, 
        shadowBlur: active ? 30 : 0, shadowColor: theme.line 
      },
      label: { color: '#fff', fontSize: 14, fontWeight: 'bold' }
    },
    { 
      name: !active ? '🚫 信号中断' : (alarm ? '🔥 确认起火' : '✅ 无明火'), 
      x: endX, y: 220, symbol: alarm ? 'pin' : 'circle', symbolSize: 70,
      itemStyle: { color: theme.line, shadowBlur: active ? 20 : 0 }
    }
  ]

  const makeLine = (labelName, startY) => {
    let speed = 0
    let symbolSize = [0, 0]
    let opacity = 0.1

    if (active) {
      if (alarm) {
        speed = 300
        symbolSize = [20, 6]
        opacity = 1
      } else {
        speed = 150
        symbolSize = [15, 4]
        opacity = 0.8
      }
    } else {
      speed = 0
      symbolSize = [0, 0]
      opacity = 0
    }

    const coords = [[startX, startY], [midX, 220]]

    return [
      { coords: coords, lineStyle: { color: theme.pipe, width: 8, opacity: 1, curveness: 0.1 } },
      { coords: coords, lineStyle: { color: theme.line, width: 2, opacity: active ? 0.3 : 0.1, curveness: 0.1 } },
      {
        name: labelName, coords: coords, lineStyle: { width: 0, curveness: 0.1 },
        effect: {
          show: active, // 保持您要求的断网隐藏逻辑
          constantSpeed: speed, trailLength: 0.1, symbol: 'rect', symbolSize: symbolSize, color: '#fff', shadowBlur: 10, shadowColor: theme.line, loop: true
        },
        label: { show: true, formatter: labelName, position: 'middle', fontSize: 11, fontWeight: 'bold', color: theme.line, distance: 10 }
      }
    ]
  }

  // 生成 5 条线
  const allLines = [
    ...makeLine('IR Signal', 60),
    ...makeLine('Temp Data', 140),
    ...makeLine('Smoke Sig', 220),
    ...makeLine('CO Level',  300),
    ...makeLine('TVOC Data', 380)
  ]

  const outputLines = [
    { coords: [[midX, 220], [endX, 220]], lineStyle: { color: theme.pipe, width: 8, curveness: 0 } }, 
    { 
      coords: [[midX, 220], [endX, 220]], lineStyle: { width: 0, curveness: 0 },
      effect: { 
        show: active, constantSpeed: alarm ? 300 : 150, trailLength: 0.1, 
        symbol: 'rect', symbolSize: [30, 8], color: '#fff',
        shadowBlur: 15, shadowColor: theme.line
      },
      label: { show: true, formatter: 'FIRE STATUS', position: 'middle', color: theme.line, fontWeight: 'bold' }
    }
  ]

  const option = {
    backgroundColor: theme.bg,
    grid: { top: 0, bottom: 0, left: 0, right: 0 },
    xAxis: { show: false, min: 0, max: 1000 },
    yAxis: { show: false, min: 0, max: 450 }, // 🟢 高度增加以容纳5个节点
    series: [
      { type: 'lines', coordinateSystem: 'cartesian2d', zlevel: 2, polyline: false, effect: { show: true, period: 4, trailLength: 0 }, data: [...allLines, ...outputLines] },
      { type: 'effectScatter', coordinateSystem: 'cartesian2d', zlevel: 3, rippleEffect: { brushType: 'stroke', scale: 4, period: 2 }, symbolSize: 40, itemStyle: { color: theme.line }, data: active ? [[midX, 220]] : [] },
      { type: 'graph', coordinateSystem: 'cartesian2d', zlevel: 10, symbolSize: [120, 50], label: { show: true, formatter: (p) => `{title|${p.name}}\n{val|${p.data.value || ''}}`, rich: { title: { fontSize: 12, color: '#ccc' }, val: { fontSize: 13, fontWeight: 'bold', color: '#fff', padding: [3, 0, 0, 0] } } }, data: nodes }
    ]
  }

  myChart.setOption(option)
}

watch([data, forceOffline, isTestAlarm, () => store.connected], () => { updateChartOption() }, { deep: true })

const handleResize = () => myChart && myChart.resize()
const toggleOffline = () => { forceOffline.value = !forceOffline.value }
const toggleTestAlarm = () => { isTestAlarm.value = !isTestAlarm.value }

onMounted(async () => {
  await nextTick()
  initChart()
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (myChart) myChart.dispose()
})
</script>

<template>
  <div class="logic-page" :class="{ 'alarm-mode': status.global }">
    <div class="header" :class="status.global ? 'danger-bg' : 'normal-bg'">
      <h2>{{ status.global ? '🔥 警报：火灾确证 (FIRE CONFIRMED)' : '🔥 中期决策：火灾确证' }}</h2>
      <p>融合逻辑：基于 <b>热(Temp) + 烟(Smoke) + 气(CO/TVOC) + 像(IR)</b> 的五维确证模型</p>
      
      <div class="source-badge">
        📡 数据源: {{ currentNodeName }}
      </div>
    </div>

    <div class="content-grid">
      <div class="card topo-card dark-theme" :class="{ 'alarm-border': status.global }">
        <div class="card-header">
          <h3 style="color:white">🧬 确证逻辑拓扑 (Verification Topology)</h3>
          <div class="status-tags">
            <span class="tag" :class="{ active: !isLinkActive }">⚪ 离线 (Static)</span>
            <span class="tag blue" :class="{ active: isLinkActive && !status.global }">🌊 正常流 (Active)</span>
            <span class="tag red" :class="{ active: status.global }">🔥 确认起火 (Alarm)</span>
          </div>
        </div>
        <div ref="chartRef" style="width: 100%; height: 500px;"></div>
      </div>

      <div class="bottom-panel">
        <div class="card log-box" :class="{ 'alarm-bg': status.global }">
          <h4>📝 确证决策日志</h4>
          <div class="log-content">
            <p v-if="!isLinkActive" class="log-line static">
              [SYSTEM] 信号丢失或手动断开连接。系统待机中...
            </p>
            <p v-else-if="isTestAlarm" class="log-line error">
              [TEST] 用户手动触发模拟报警 (Manual Test Triggered)。
            </p>
            <p v-else-if="status.global" class="log-line error">
              [CRITICAL] 检测到燃烧特征！<br>
              触发源: {{ numData.smoke > LIMITS.smoke ? '浓烟 ' : '' }}{{ numData.temp > LIMITS.temp ? '高温 ' : '' }}{{ irVal > LIMITS.ir ? '红外 ' : '' }} -> 判定为实体火灾。
            </p>
            <p v-else class="log-line info">
              [INFO] 燃烧产物监测中 (5-Sensor Active)。<br>
              当前环境：未检测到显著火灾特征。
            </p>
          </div>
          <div class="btn-group">
            <button @click="toggleTestAlarm" class="test-btn" :class="isTestAlarm ? 'orange-btn' : 'red-btn'">
              {{ isTestAlarm ? '🔕 取消模拟' : '🔥 模拟报警' }}
            </button>
            <button @click="toggleOffline" class="test-btn gray-btn">
              {{ forceOffline ? '🔌 恢复连接' : '🔌 模拟断网' }}
            </button>
          </div>
        </div>
        <div class="card code-box">
           <h4>🧮 燃烧确证算法</h4>
          <pre>IF (IR > 75) OR (Temp > 60): FIRE
ELIF (Smoke > 800k) OR (CO > 100): FIRE
ELIF (TVOC > 3.0): WARNING
ELSE: SAFE</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 样式与您提供的完全一致，仅增加 red-btn/orange-btn */
.logic-page { padding: 20px; height: 100%; display: flex; flex-direction: column; overflow-y: auto; background: #f0f2f5; transition: background 0.5s; }
.logic-page.alarm-mode { background: #2b0505; }

.header { padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); flex-shrink: 0; transition: background 0.5s; position: relative; }
.normal-bg { background: linear-gradient(135deg, #d69e2e, #b7791f); }
.danger-bg { background: linear-gradient(135deg, #ff0000, #990000); animation: pulse-header 1s infinite; }

.source-badge { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.3); padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; border: 1px solid rgba(255,255,255,0.3); }

.content-grid { display: flex; flex-direction: column; gap: 20px; flex: 1; }
.card { background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); padding: 20px; border: 1px solid #eee; transition: all 0.5s; }
.dark-theme { background: #0f1114; border: 1px solid #333; }
.alarm-border { border-color: #ff0000 !important; box-shadow: 0 0 20px rgba(255, 0, 0, 0.5) !important; animation: pulse-border 1s infinite; }
.alarm-bg { background: #fff1f0; border-color: #ff4d4f; }

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.status-tags { display: flex; gap: 8px; }
.tag { font-size: 0.75rem; padding: 3px 10px; border-radius: 4px; background: #333; color: #999; border: 1px solid #555; opacity: 0.5; }
.tag.active { opacity: 1; font-weight: bold; transform: scale(1.1); }
.tag.blue.active { background: #003333; color: #00F0FF; border-color: #00F0FF; box-shadow: 0 0 5px #00F0FF; }
.tag.red.active { background: #330000; color: #FF0000; border-color: #FF0000; box-shadow: 0 0 10px #FF0000; }

.bottom-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.log-box h4, .code-box h4 { margin: 0 0 10px 0; color: #666; }
.log-content { background: #f9f9f9; padding: 10px; border-radius: 6px; font-size: 0.9rem; min-height: 60px; }
.log-line.error { color: #f56c6c; font-weight: bold; }
.log-line.info { color: #67c23a; }
.log-line.static { color: #999; font-style: italic; }
.code-box pre { margin: 0; background: #282c34; color: #abb2bf; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 0.85rem; }

.btn-group { display: flex; gap: 10px; margin-top: 10px; }
.test-btn { padding: 8px 15px; border: none; cursor: pointer; border-radius: 20px; font-size: 0.8rem; color: white; }
.red-btn { background: linear-gradient(to right, #ff4d4f, #f5222d); }
.orange-btn { background: linear-gradient(to right, #fa8c16, #d46b08); }
.gray-btn { background: #666; }

@keyframes pulse-border { 0% { box-shadow: 0 0 10px rgba(255, 0, 0, 0.3); } 50% { box-shadow: 0 0 30px rgba(255, 0, 0, 0.8); } 100% { box-shadow: 0 0 10px rgba(255, 0, 0, 0.3); } }
@keyframes pulse-header { 0% { background: linear-gradient(135deg, #ff0000, #990000); } 50% { background: linear-gradient(135deg, #ff3333, #cc0000); } 100% { background: linear-gradient(135deg, #ff0000, #990000); } }
</style>