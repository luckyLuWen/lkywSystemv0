<script setup>
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { store } from '../store.js'
import * as echarts from 'echarts'

// --- 1. 数据源选择 (双节点融合) ---
const currentNodeName = "双节点融合 (Node 1 + Node 2)"

// 🟢 [核心修改] 同时获取两个节点的数据，取最大值进行保守报警
const data = computed(() => {
  const n1 = store.data.node1 || { temp: 0, tvoc: 0, smoke: 0, co: 0 }
  const n2 = store.data.node2 || { temp: 0, tvoc: 0, smoke: 0, co: 0 }
  
  // 融合策略：MAX (安全领域通常取最大值，宁可误报不可漏报)
  return {
    temp: Math.max(n1.temp, n2.temp),
    tvoc: Math.max(n1.tvoc, n2.tvoc),
    smoke: Math.max(n1.smoke, n2.smoke),
    co: Math.max(n1.co, n2.co)
  }
})

// 模拟断网控制
const forceOffline = ref(false)
const isLinkActive = computed(() => store.connected && !forceOffline.value)

// 模拟红外数据 (基于温度)
const irVal = computed(() => Number((Number(data.value.temp) * 1.2).toFixed(1)))
const numData = computed(() => ({
  temp: Number(data.value.temp),
  tvoc: Number(data.value.tvoc),
  smoke: Number(data.value.smoke),
  co: Number(data.value.co)
}))

const LIMITS = { smoke: 600000, co: 50, tvoc: 2.0, ir: 80.0 }

const status = computed(() => ({
  global: numData.value.smoke > LIMITS.smoke || numData.value.co > LIMITS.co || numData.value.tvoc > LIMITS.tvoc || irVal.value > LIMITS.ir
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

  // 状态判断
  const active = isLinkActive.value
  const alarm = status.value.global

  const theme = {
    bg: alarm ? '#2b0505' : '#0f1114',
    pipe: alarm ? '#5c1919' : '#2D3748', // 管道底色
    line: !active ? '#555' : (alarm ? '#FF0055' : '#00F0FF'), // 线条颜色：断网灰 / 报警红 / 正常青
    nodeBorder: alarm ? '#ff4d4f' : '#fff'
  }

  // 坐标配置
  const startX = 120, midX = 550, endX = 900
  const colors = { ir: '#FF6B6B', tvoc: '#D6A2E8', smoke: '#CBD5E0', co: '#F6AD55' }

  // A. 节点样式
  const makeNodeStyle = (color) => ({
    color: active ? color : '#555', // 断网时节点变灰
    borderColor: theme.nodeBorder, borderWidth: 2, 
    shadowBlur: active ? 10 : 0, shadowColor: color
  })

  const nodes = [
    { name: '📷 红外', value: (active ? irVal.value : '--') + ' ℃', x: startX, y: 50, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.ir) },
    { name: '🧪 TVOC', value: (active ? numData.value.tvoc : '--') + ' mg', x: startX, y: 150, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.tvoc) },
    { name: '🌫️ 烟雾', value: (active ? (numData.value.smoke/10000).toFixed(1) : '--') + '万', x: startX, y: 250, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.smoke) },
    { name: '⚠️ CO', value: (active ? numData.value.co : '--') + ' ppm', x: startX, y: 350, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.co) },
    
    // 融合中心
    { 
      name: '🧠 多维融合算法', x: midX, y: 200, symbol: 'diamond', symbolSize: [160, 100],
      itemStyle: { 
        color: alarm ? '#4a0f0f' : '#2b3a4a', 
        borderColor: theme.line, borderWidth: 4, 
        shadowBlur: active ? 30 : 0, shadowColor: theme.line 
      },
      label: { color: '#fff', fontSize: 14, fontWeight: 'bold' }
    },
    // 输出
    { 
      name: !active ? '🚫 信号中断' : (alarm ? '🚫 确认隐患' : '✅ 安全'), 
      x: endX, y: 200, symbol: alarm ? 'pin' : 'circle', symbolSize: 70,
      itemStyle: { color: theme.line, shadowBlur: active ? 20 : 0 }
    }
  ]

  // B. 线路生成器
  const makeLine = (labelName, startY) => {
    // 动画配置
    let speed = 0
    let symbolSize = [0, 0]
    let opacity = 0.1

    if (active) {
      if (alarm) {
        speed = 300 // 报警极速
        symbolSize = [20, 6]
        opacity = 1
      } else {
        speed = 150 // 正常匀速
        symbolSize = [15, 4]
        opacity = 0.8
      }
    } else {
      // 断网：无动画
      speed = 0
      symbolSize = [0, 0]
      opacity = 0
    }

    const coords = [[startX, startY], [midX, 200]]

    return [
      // 1. 管道底座
      { coords: coords, lineStyle: { color: theme.pipe, width: 8, opacity: 1, curveness: 0.1 } },
      // 2. 静态轨迹线 (断网时只显示这个)
      { coords: coords, lineStyle: { color: theme.line, width: 2, opacity: active ? 0.3 : 0.1, curveness: 0.1 } },
      // 3. 动态数据块 (断网时隐藏)
      {
        name: labelName, coords: coords, lineStyle: { width: 0, curveness: 0.1 },
        effect: {
          show: active, // 🟢 关键：断网不显示特效
          constantSpeed: speed, trailLength: 0.1, symbol: 'rect', symbolSize: symbolSize, color: '#fff', shadowBlur: 10, shadowColor: theme.line, loop: true
        },
        label: { show: true, formatter: labelName, position: 'middle', fontSize: 11, fontWeight: 'bold', color: theme.line, distance: 10 }
      }
    ]
  }

  const allLines = [
    ...makeLine('IR Signal', 50),
    ...makeLine('TVOC Data', 150),
    ...makeLine('Smoke Sig', 250),
    ...makeLine('CO Level',  350)
  ]

  const outputLines = [
    { coords: [[midX, 200], [endX, 200]], lineStyle: { color: theme.pipe, width: 8, curveness: 0 } }, 
    { 
      coords: [[midX, 200], [endX, 200]], lineStyle: { width: 0, curveness: 0 },
      effect: { 
        show: active, constantSpeed: alarm ? 300 : 150, trailLength: 0.1, 
        symbol: 'rect', symbolSize: [30, 8], color: '#fff',
        shadowBlur: 15, shadowColor: theme.line
      },
      label: { show: true, formatter: 'FINAL DECISION', position: 'middle', color: theme.line, fontWeight: 'bold' }
    }
  ]

  const option = {
    backgroundColor: theme.bg,
    grid: { top: 0, bottom: 0, left: 0, right: 0 },
    xAxis: { show: false, min: 0, max: 1000 },
    yAxis: { show: false, min: 0, max: 400 },
    series: [
      { type: 'lines', coordinateSystem: 'cartesian2d', zlevel: 2, polyline: false, effect: { show: true, period: 4, trailLength: 0 }, data: [...allLines, ...outputLines] },
      { type: 'effectScatter', coordinateSystem: 'cartesian2d', zlevel: 3, rippleEffect: { brushType: 'stroke', scale: 4, period: 2 }, symbolSize: 40, itemStyle: { color: theme.line }, data: active ? [[midX, 200]] : [] },
      { type: 'graph', coordinateSystem: 'cartesian2d', zlevel: 10, symbolSize: [120, 50], label: { show: true, formatter: (p) => `{title|${p.name}}\n{val|${p.data.value || ''}}`, rich: { title: { fontSize: 12, color: '#ccc' }, val: { fontSize: 13, fontWeight: 'bold', color: '#fff', padding: [3, 0, 0, 0] } } }, data: nodes }
    ]
  }

  myChart.setOption(option)
}

watch([data, forceOffline, () => store.connected], () => { updateChartOption() }, { deep: true })

const handleResize = () => myChart && myChart.resize()
const toggleOffline = () => { forceOffline.value = !forceOffline.value } // 切换模拟状态

// 🟢 [已移除] testAnim 测试按钮函数

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
      <h2>{{ status.global ? '🚨 紧急状态：检测到火灾隐患' : '⚠️ 前期决策：早期隐患预警' }}</h2>
      <p>融合逻辑：基于 <b>红外 + TVOC + 烟雾 + CO</b> 的四维异构数据判决模型</p>
      
      <div class="source-badge">
        📡 数据源: {{ currentNodeName }}
      </div>
    </div>

    <div class="content-grid">
      <div class="card topo-card dark-theme" :class="{ 'alarm-border': status.global }">
        <div class="card-header">
          <h3 style="color:white">🧬 实时逻辑拓扑 (Live Topology)</h3>
          <div class="status-tags">
            <span class="tag" :class="{ active: !isLinkActive }">⚪ 离线 (Static)</span>
            <span class="tag blue" :class="{ active: isLinkActive && !status.global }">🌊 正常流 (Active)</span>
            <span class="tag red" :class="{ active: status.global }">🔥 报警流 (Alarm)</span>
          </div>
        </div>
        <div ref="chartRef" style="width: 100%; height: 500px;"></div>
      </div>

      <div class="bottom-panel">
        <div class="card log-box" :class="{ 'alarm-bg': status.global }">
          <h4>📝 实时决策日志</h4>
          <div class="log-content">
            <p v-if="!isLinkActive" class="log-line static">
              [SYSTEM] 信号丢失或手动断开连接。系统待机中...
            </p>
            <p v-else-if="status.global" class="log-line error">
              [CRITICAL] 综合判决触发！<br>全系统进入红色警戒模式 (RED ALERT MODE)。
            </p>
            <p v-else class="log-line info">
              [INFO] 链路通畅。数据包传输中... (Data Packets Active)<br>
              正在实时监控双车 (Node 1 & 2) 传感器数据。
            </p>
          </div>
          <div class="btn-group">
            <button @click="toggleOffline" class="test-btn gray-btn">
              {{ forceOffline ? '🔌 恢复连接' : '🔌 模拟断网(静止)' }}
            </button>
          </div>
        </div>
        <div class="card code-box">
           <h4>🧮 核心算法 (Max Pooling)</h4>
          <pre>DATA = MAX(Node1, Node2)
IF (!Connected): STATUS = STATIC
ELSE IF (DATA > Limit): STATUS = ALARM
ELSE: STATUS = NORMAL_FLOW</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 样式保持不变 */
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
.test-btn { padding: 8px 15px; background: linear-gradient(to right, #ff7e5f, #feb47b); color: white; border: none; cursor: pointer; border-radius: 20px; font-size: 0.8rem; }
.gray-btn { background: #666; }

@keyframes pulse-border { 0% { box-shadow: 0 0 10px rgba(255, 0, 0, 0.3); } 50% { box-shadow: 0 0 30px rgba(255, 0, 0, 0.8); } 100% { box-shadow: 0 0 10px rgba(255, 0, 0, 0.3); } }
@keyframes pulse-header { 0% { background: linear-gradient(135deg, #ff0000, #990000); } 50% { background: linear-gradient(135deg, #ff3333, #cc0000); } 100% { background: linear-gradient(135deg, #ff0000, #990000); } }
</style>