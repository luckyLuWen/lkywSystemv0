<script setup>
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { store } from '../store.js'
import * as echarts from 'echarts'

// --- 1. 数据源 (Node 3: 气象环境站) ---
const currentNodeName = "气象环境站 (Node 3)"

const data = computed(() => store.data.node3 || { wind: 0, wind_dir: 'N', hum: 0 })

// 断网控制
const forceOffline = ref(false)
const isLinkActive = computed(() => store.connected && !forceOffline.value)

// 模拟报警控制 (强风模式)
const isTestAlarm = ref(false)

// 格式化数据
const numData = computed(() => ({
  wind: Number(data.value.wind), // 风速 m/s
  dir: data.value.wind_dir,      // 风向 (文字)
  hum: Number(data.value.hum || 45) // 湿度 (如果没有则默认45)
}))

// 🚨 蔓延阈值 (风速大于 5m/s 视为易扩散高危)
const LIMITS = { wind: 5.0 }

// 状态判决
const status = computed(() => ({
  global: isTestAlarm.value || numData.value.wind > LIMITS.wind
}))

const chartRef = ref(null)
let myChart = null

const initChart = () => {
  if (!chartRef.value) return
  myChart = echarts.init(chartRef.value)
  updateChartOption()
}

// --- 渲染逻辑 (数据包传输风格) ---
const updateChartOption = () => {
  if (!myChart) return

  const active = isLinkActive.value
  const isSpread = status.value.global

  // 💨 配色：蔓延分析主题 (蓝/紫)
  const theme = {
    bg: isSpread ? '#1e1b4b' : '#0f172a',       // 背景：深紫 vs 深蓝
    pipe: isSpread ? '#4c1d95' : '#1e293b',     // 管道底色
    line: !active ? '#334155' : (isSpread ? '#a855f7' : '#38bdf8'), // 激活色：亮紫 vs 天蓝
    nodeBorder: isSpread ? '#d8b4fe' : '#7dd3fc'
  }

  const startX = 120, midX = 600, endX = 950
  const colors = { wind: '#38bdf8', dir: '#818cf8', hum: '#60a5fa' }

  // A. 节点样式
  const makeNodeStyle = (color) => ({
    color: active ? color : '#1e293b', 
    borderColor: theme.nodeBorder, borderWidth: 2, 
    shadowBlur: active ? 10 : 0, shadowColor: color
  })

  // 3个传感器节点
  const nodes = [
    { name: '💨 风速 (Speed)', value: (active ? numData.value.wind : '--') + ' m/s', x: startX, y: 100, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.wind) },
    { name: '🧭 风向 (Dir)', value: (active ? numData.value.dir : '--'), x: startX, y: 220, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.dir) },
    { name: '💧 湿度 (Hum)', value: (active ? numData.value.hum : '--') + ' %', x: startX, y: 340, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.hum) },
    
    // 决策中心
    { 
      name: '🌪️ 态势蔓延模型\n(Spread Analysis)', x: midX, y: 220, symbol: 'diamond', symbolSize: [180, 100],
      itemStyle: { 
        color: isSpread ? '#4c1d95' : '#1e293b', 
        borderColor: theme.line, borderWidth: 4, 
        shadowBlur: active ? 30 : 0, shadowColor: theme.line 
      },
      label: { color: active ? '#fff' : '#64748b', fontSize: 14, fontWeight: 'bold' }
    },
    // 输出
    { 
      name: !active ? '🚫 信号中断' : (isSpread ? '⚠️ 高速扩散风险' : '✅ 低速稳定'), 
      x: endX, y: 220, symbol: isSpread ? 'path://M880 112H144c-17.7 0-32 14.3-32 32v736c0 17.7 14.3 32 32 32h736c17.7 0 32-14.3 32-32V144c0-17.7-14.3-32-32-32z m-40 728H184V184h656v656zM492 400h40v160h-40z m0 216h40v40h-40z' : 'circle', 
      symbolSize: 80,
      itemStyle: { color: theme.line, shadowBlur: active ? 20 : 0 }
    }
  ]

  // B. 线路生成器
  const makeLine = (labelName, startY) => {
    let speed = 0
    let symbolSize = [0, 0]
    
    if (active) {
      if (isSpread) {
        speed = 400 // 强风时极速流动
        symbolSize = [35, 8]
      } else {
        speed = 100 // 微风时缓慢流动
        symbolSize = [15, 4]
      }
    } else {
      speed = 0
      symbolSize = [0, 0]
    }

    const coords = [[startX, startY], [midX, 220]]

    return [
      // 1. 管道底座
      { coords: coords, lineStyle: { color: theme.pipe, width: 8, opacity: 1, curveness: 0.1 } },
      // 2. 静态轨迹
      { coords: coords, lineStyle: { color: theme.line, width: 2, opacity: active ? 0.3 : 0.1, curveness: 0.1 } },
      // 3. 动态数据包 (断网为空)
      ...(active ? [{
        name: labelName, coords: coords, lineStyle: { width: 0, curveness: 0.1 },
        effect: {
          show: true, 
          constantSpeed: speed, trailLength: 0.1, symbol: 'rect', symbolSize: symbolSize, color: '#fff', shadowBlur: 10, shadowColor: theme.line, loop: true
        },
        label: { show: true, formatter: labelName, position: 'middle', fontSize: 11, fontWeight: 'bold', color: theme.line, distance: 10 }
      }] : [])
    ]
  }

  const allLines = [
    ...makeLine('Wind Speed', 100),
    ...makeLine('Direction', 220),
    ...makeLine('Humidity', 340)
  ]

  const outputLines = [
    { coords: [[midX, 220], [endX, 220]], lineStyle: { color: theme.pipe, width: 8, curveness: 0 } }, 
    ...(active ? [{ 
      coords: [[midX, 220], [endX, 220]], lineStyle: { width: 0, curveness: 0 },
      effect: { 
        show: true, constantSpeed: isSpread ? 300 : 100, trailLength: 0.1, 
        symbol: 'rect', symbolSize: [40, 10], color: '#fff',
        shadowBlur: 15, shadowColor: theme.line
      },
      label: { show: true, formatter: 'SPREAD RISK', position: 'middle', color: theme.line, fontWeight: 'bold' }
    }] : [])
  ]

  const option = {
    backgroundColor: theme.bg,
    grid: { top: 0, bottom: 0, left: 0, right: 0 },
    xAxis: { show: false, min: 0, max: 1000 },
    yAxis: { show: false, min: 0, max: 450 },
    series: [
      { type: 'lines', coordinateSystem: 'cartesian2d', zlevel: 2, polyline: false, effect: { show: true, period: 4, trailLength: 0 }, data: allLines.flat().concat(outputLines.flat()) },
      { type: 'effectScatter', coordinateSystem: 'cartesian2d', zlevel: 3, rippleEffect: { brushType: 'stroke', scale: 4, period: 2 }, symbolSize: 50, itemStyle: { color: theme.line }, data: active ? [[midX, 220]] : [] },
      { type: 'graph', coordinateSystem: 'cartesian2d', zlevel: 10, symbolSize: [120, 50], label: { show: true, formatter: (p) => `{title|${p.name}}\n{val|${p.data.value || ''}}`, rich: { title: { fontSize: 12, color: active ? '#cbd5e1' : '#475569' }, val: { fontSize: 13, fontWeight: 'bold', color: active ? '#fff' : '#64748b', padding: [3, 0, 0, 0] } } }, data: nodes }
    ]
  }

  myChart.setOption(option, { notMerge: false })
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
  <div class="logic-page" :class="{ 'spread-mode': status.global }">
    <div class="header" :class="status.global ? 'danger-bg' : 'spread-bg'">
      <h2>{{ status.global ? '💨 警报：高危扩散风险 (HIGH RISK)' : '💨 后期决策：态势蔓延分析' }}</h2>
      <p>融合逻辑：基于 <b>风场(Wind) + 湿度(Hum)</b> 的气象扩散模型</p>
      
      <div class="source-badge">
        📡 数据源: {{ currentNodeName }}
      </div>
    </div>

    <div class="content-grid">
      <div class="card topo-card dark-theme" :class="{ 'spread-border': status.global }">
        <div class="card-header">
          <h3 style="color:white">🧬 扩散逻辑拓扑 (Spread Topology)</h3>
          <div class="status-tags">
            <span class="tag" :class="{ active: !isLinkActive }">⚪ 离线</span>
            <span class="tag blue" :class="{ active: isLinkActive && !status.global }">🌬️ 稳定扩散</span>
            <span class="tag purple" :class="{ active: status.global }">🌪️ 极速蔓延</span>
          </div>
        </div>
        <div ref="chartRef" style="width: 100%; height: 500px;"></div>
      </div>

      <div class="bottom-panel">
        <div class="card log-box" :class="{ 'spread-log-bg': status.global }">
          <h4>📝 蔓延决策日志</h4>
          <div class="log-content">
            <p v-if="!isLinkActive" class="log-line static">
              [SYSTEM] 信号丢失或手动断开连接。
            </p>
            <p v-else-if="isTestAlarm" class="log-line error">
              [TEST] 模拟强风环境 (Simulated High Wind)。
            </p>
            <p v-else-if="status.global" class="log-line error">
              [WARNING] 风速过大 ({{ numData.wind }} m/s)！<br>
              污染物/火势将向 {{ numData.dir }} 方向快速扩散，建议立即疏散下风口。
            </p>
            <p v-else class="log-line info">
              [INFO] 气象条件稳定。<br>
              当前风速 {{ numData.wind }} m/s，扩散风险较低。
            </p>
          </div>
          <div class="btn-group">
            <button @click="toggleTestAlarm" class="test-btn" :class="isTestAlarm ? 'purple-btn' : 'blue-btn'">
              {{ isTestAlarm ? '🔕 取消模拟' : '🌪️ 模拟强风' }}
            </button>
            <button @click="toggleOffline" class="test-btn gray-btn">
              {{ forceOffline ? '🔌 恢复连接' : '🔌 模拟断网' }}
            </button>
          </div>
        </div>
        <div class="card code-box">
           <h4>🧮 扩散评估算法</h4>
          <pre>IF (WindSpeed > 5.0m/s):
  RISK = HIGH
  DIRECTION = Vector(WindDir)
  ALERT_DOWNWIND_AREA(DIRECTION)
ELSE:
  RISK = LOW</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.logic-page { padding: 20px; height: 100%; display: flex; flex-direction: column; overflow-y: auto; background: #0f172a; transition: background 0.5s; }
.logic-page.spread-mode { background: #1e1b4b; }

.header { padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); flex-shrink: 0; transition: background 0.5s; position: relative; }
.spread-bg { background: linear-gradient(135deg, #3b82f6, #2563eb); } /* 天蓝色 */
.danger-bg { background: linear-gradient(135deg, #7c3aed, #4c1d95); animation: pulse-header 1s infinite; } /* 紫色 */

.source-badge { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.3); padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; border: 1px solid rgba(255,255,255,0.3); }

.content-grid { display: flex; flex-direction: column; gap: 20px; flex: 1; }
.card { background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); padding: 20px; border: 1px solid #eee; transition: all 0.5s; }
.dark-theme { background: #0f172a; border: 1px solid #1e293b; }
.spread-border { border-color: #a855f7 !important; box-shadow: 0 0 30px rgba(168, 85, 247, 0.6) !important; animation: pulse-border 1s infinite; }
.spread-log-bg { background: #faf5ff; border-color: #d8b4fe; }

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.status-tags { display: flex; gap: 8px; }
.tag { font-size: 0.75rem; padding: 3px 10px; border-radius: 4px; background: #1e293b; color: #94a3b8; border: 1px solid #334155; opacity: 0.5; }
.tag.active { opacity: 1; font-weight: bold; transform: scale(1.1); }
.tag.blue.active { background: #172554; color: #38bdf8; border-color: #38bdf8; box-shadow: 0 0 5px #38bdf8; }
.tag.purple.active { background: #2e1065; color: #a855f7; border-color: #a855f7; box-shadow: 0 0 15px #a855f7; }

.bottom-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.log-box h4, .code-box h4 { margin: 0 0 10px 0; color: #94a3b8; }
.log-content { background: #fff; padding: 10px; border-radius: 6px; font-size: 0.9rem; min-height: 60px; }
.log-line.error { color: #7c3aed; font-weight: bold; }
.log-line.info { color: #0284c7; }
.log-line.static { color: #94a3b8; font-style: italic; }
.code-box pre { margin: 0; background: #1e293b; color: #e2e8f0; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 0.85rem; border-left: 3px solid #3b82f6; }

.btn-group { display: flex; gap: 10px; margin-top: 10px; }
.test-btn { padding: 8px 15px; border: none; cursor: pointer; border-radius: 20px; font-size: 0.8rem; color: white; }
.blue-btn { background: linear-gradient(to right, #3b82f6, #2563eb); }
.purple-btn { background: linear-gradient(to right, #8b5cf6, #7c3aed); }
.gray-btn { background: #64748b; }

@keyframes pulse-border { 0% { box-shadow: 0 0 10px rgba(168, 85, 247, 0.3); } 50% { box-shadow: 0 0 30px rgba(168, 85, 247, 0.8); } 100% { box-shadow: 0 0 10px rgba(168, 85, 247, 0.3); } }
@keyframes pulse-header { 0% { background: linear-gradient(135deg, #7c3aed, #4c1d95); } 50% { background: linear-gradient(135deg, #8b5cf6, #6d28d9); } 100% { background: linear-gradient(135deg, #7c3aed, #4c1d95); } }
</style>