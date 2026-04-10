<script setup>
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { store } from '../store.js'
import * as echarts from 'echarts'

// --- 1. 数据源 (双节点融合取最大值) ---
const currentNodeName = "双节点融合 (Node 1 + Node 2)"

const data = computed(() => {
  const n1 = store.data.node1 || { hum: 0, tvoc: 0, co: 0 }
  const n2 = store.data.node2 || { hum: 0, tvoc: 0, co: 0 }
  return {
    hum: Math.max(Number(n1.hum), Number(n2.hum)),
    tvoc: Math.max(Number(n1.tvoc), Number(n2.tvoc)),
    co: Math.max(Number(n1.co), Number(n2.co))
  }
})

// 断网控制
const forceOffline = ref(false)
const isLinkActive = computed(() => store.connected && !forceOffline.value)

// 💧 模拟高湿干扰
const isTestInterference = ref(false)

// 阈值 (湿度 > 80% 触发清洗逻辑)
const LIMITS = { hum: 80 }

// 状态判决
const status = computed(() => ({
  isWet: isTestInterference.value || data.value.hum > LIMITS.hum
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
  const isWet = status.value.isWet

  // 🛡️ 配色：干扰清洗主题
  const theme = {
    bg: isWet ? '#0c2e4e' : '#064e3b',          // 背景：深蓝(湿) vs 深绿(干)
    pipe: isWet ? '#1e3a8a' : '#065f46',        // 管道底色
    line: !active ? '#334155' : (isWet ? '#3b82f6' : '#34d399'), // 激活色：蓝 vs 绿
    nodeBorder: isWet ? '#60a5fa' : '#6ee7b7'
  }

  // 坐标配置 (3个节点垂直分布)
  const startX = 120, midX = 600, endX = 950
  const colors = { hum: '#38bdf8', tvoc: '#a78bfa', co: '#fbbf24' }

  // A. 节点样式
  const makeNodeStyle = (color) => ({
    color: active ? color : '#1e293b', 
    borderColor: theme.nodeBorder, borderWidth: 2, 
    shadowBlur: active ? 10 : 0, shadowColor: color
  })

  // 3个传感器节点
  const nodes = [
    { name: '💧 环境湿度 (Interference)', value: (active ? data.value.hum : '--') + ' %', x: startX, y: 100, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.hum) },
    { name: '🧪 TVOC (Target 1)', value: (active ? data.value.tvoc : '--') + ' mg', x: startX, y: 220, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.tvoc) },
    { name: '☠️ CO (Target 2)', value: (active ? data.value.co : '--') + ' ppm', x: startX, y: 340, symbol: 'roundRect', itemStyle: makeNodeStyle(colors.co) },
    
    // 算法中心
    { 
      name: '🛡️ 干扰清洗算法\n(Humidity Suppression)', x: midX, y: 220, symbol: 'diamond', symbolSize: [180, 100],
      itemStyle: { 
        color: isWet ? '#1e3a8a' : '#065f46', 
        borderColor: theme.line, borderWidth: 4, 
        shadowBlur: active ? 30 : 0, shadowColor: theme.line 
      },
      label: { color: active ? '#fff' : '#64748b', fontSize: 14, fontWeight: 'bold' }
    },
    // 输出状态
    { 
      name: !active ? '🚫 信号中断' : (isWet ? '💧 数据已清洗 (Cleaned)' : '☀️ 原始数据 (Raw)'), 
      x: endX, y: 220, symbol: isWet ? 'path://M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64z m0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372zM464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0z m72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z' : 'circle', 
      symbolSize: 80,
      itemStyle: { color: theme.line, shadowBlur: active ? 20 : 0 }
    }
  ]

  // B. 线路生成器
  const makeLine = (labelName, startY) => {
    let speed = 0
    let symbolSize = [0, 0]
    
    if (active) {
      if (isWet) {
        speed = 300 // 清洗模式：快速处理
        symbolSize = [25, 8]
      } else {
        speed = 150 // 标准模式：正常流动
        symbolSize = [20, 6]
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
          constantSpeed: speed, trailLength: 0.1, symbol: 'roundRect', symbolSize: symbolSize, color: '#fff', shadowBlur: 10, shadowColor: theme.line, loop: true
        },
        label: { show: true, formatter: labelName, position: 'middle', fontSize: 11, fontWeight: 'bold', color: theme.line, distance: 10 }
      }] : [])
    ]
  }

  // 生成3条线
  const allLines = [
    ...makeLine('Humidity Ref', 100),
    ...makeLine('TVOC Raw', 220),
    ...makeLine('CO Raw', 340)
  ]

  const outputLines = [
    { coords: [[midX, 220], [endX, 220]], lineStyle: { color: theme.pipe, width: 8, curveness: 0 } }, 
    ...(active ? [{ 
      coords: [[midX, 220], [endX, 220]], lineStyle: { width: 0, curveness: 0 },
      effect: { 
        show: true, constantSpeed: isWet ? 300 : 150, trailLength: 0.1, 
        symbol: 'roundRect', symbolSize: [40, 10], color: '#fff',
        shadowBlur: 15, shadowColor: theme.line
      },
      label: { show: true, formatter: isWet ? 'CLEANED DATA' : 'RAW DATA', position: 'middle', color: theme.line, fontWeight: 'bold' }
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

watch([data, forceOffline, isTestInterference, () => store.connected], () => { updateChartOption() }, { deep: true })

const handleResize = () => myChart && myChart.resize()
const toggleOffline = () => { forceOffline.value = !forceOffline.value }
const toggleTestInterference = () => { isTestInterference.value = !isTestInterference.value }

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
  <div class="logic-page" :class="{ 'wet-mode': status.isWet }">
    <div class="header" :class="status.isWet ? 'clean-bg' : 'safe-bg'">
      <h2>{{ status.isWet ? '💧 状态：高湿干扰清洗中 (CLEANING)' : '🛡️ 辅助决策：环境干扰清洗' }}</h2>
      <p>融合逻辑：<b>Humidity (湿度)</b> 补偿算法，修正 <b>TVOC/CO</b> 误报</p>
      
      <div class="source-badge">
        📡 数据源: {{ currentNodeName }}
      </div>
    </div>

    <div class="content-grid">
      <div class="card topo-card dark-theme" :class="{ 'wet-border': status.isWet }">
        <div class="card-header">
          <h3 style="color:white">🧬 清洗逻辑拓扑 (Cleaning Topology)</h3>
          <div class="status-tags">
            <span class="tag" :class="{ active: !isLinkActive }">⚪ 离线</span>
            <span class="tag green" :class="{ active: isLinkActive && !status.isWet }">☀️ 原始透传</span>
            <span class="tag blue" :class="{ active: status.isWet }">💧 算法清洗</span>
          </div>
        </div>
        <div ref="chartRef" style="width: 100%; height: 500px;"></div>
      </div>

      <div class="bottom-panel">
        <div class="card log-box" :class="{ 'wet-log-bg': status.isWet }">
          <h4>📝 算法决策日志</h4>
          <div class="log-content">
            <p v-if="!isLinkActive" class="log-line static">
              [SYSTEM] 信号丢失或手动断开连接。
            </p>
            <p v-else-if="isTestInterference" class="log-line info-blue">
              [TEST] 模拟高湿环境 (Simulated Wet Environment)。
            </p>
            <p v-else-if="status.isWet" class="log-line info-blue">
              [CLEAN] 湿度超标 ({{ data.hum }}%) -> 触发抑制算法。<br>
              操作：降低 TVOC/CO 灵敏度因子 (Sensitivity *= 0.6)。
            </p>
            <p v-else class="log-line info-green">
              [PASS] 湿度正常 ({{ data.hum }}%) -> 数据直通。<br>
              操作：保持传感器原始读数 (Raw Data)。
            </p>
          </div>
          <div class="btn-group">
            <button @click="toggleTestInterference" class="test-btn" :class="isTestInterference ? 'blue-btn' : 'green-btn'">
              {{ isTestInterference ? '🔕 取消模拟' : '💧 模拟高湿' }}
            </button>
            <button @click="toggleOffline" class="test-btn gray-btn">
              {{ forceOffline ? '🔌 恢复连接' : '🔌 模拟断网' }}
            </button>
          </div>
        </div>
        <div class="card code-box">
           <h4>🧮 干扰清洗算法</h4>
          <pre>IF (Humidity > 80%):
  STATUS = WET_MODE
  TVOC_VAL = FILTER(TVOC_RAW)
  CO_VAL = FILTER(CO_RAW)
ELSE:
  STATUS = DRY_MODE
  TVOC_VAL = TVOC_RAW</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.logic-page { padding: 20px; height: 100%; display: flex; flex-direction: column; overflow-y: auto; background: #022c22; transition: background 0.5s; }
.logic-page.wet-mode { background: #0c2e4e; }

.header { padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); flex-shrink: 0; transition: background 0.5s; position: relative; }
.safe-bg { background: linear-gradient(135deg, #059669, #047857); } /* 绿色系 */
.clean-bg { background: linear-gradient(135deg, #2563eb, #1e40af); animation: pulse-header 1s infinite; } /* 蓝色系 */

.source-badge { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.3); padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; border: 1px solid rgba(255,255,255,0.3); }

.content-grid { display: flex; flex-direction: column; gap: 20px; flex: 1; }
.card { background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); padding: 20px; border: 1px solid #eee; transition: all 0.5s; }
.dark-theme { background: #022c22; border: 1px solid #064e3b; }
.wet-border { border-color: #3b82f6 !important; box-shadow: 0 0 30px rgba(59, 130, 246, 0.6) !important; animation: pulse-border 1s infinite; }
.wet-log-bg { background: #eff6ff; border-color: #93c5fd; }

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.status-tags { display: flex; gap: 8px; }
.tag { font-size: 0.75rem; padding: 3px 10px; border-radius: 4px; background: #064e3b; color: #94a3b8; border: 1px solid #065f46; opacity: 0.5; }
.tag.active { opacity: 1; font-weight: bold; transform: scale(1.1); }
.tag.green.active { background: #064e3b; color: #34d399; border-color: #34d399; box-shadow: 0 0 5px #34d399; }
.tag.blue.active { background: #1e3a8a; color: #60a5fa; border-color: #60a5fa; box-shadow: 0 0 15px #60a5fa; }

.bottom-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.log-box h4, .code-box h4 { margin: 0 0 10px 0; color: #666; }
.log-content { background: #fff; padding: 10px; border-radius: 6px; font-size: 0.9rem; min-height: 60px; }
.log-line.info-blue { color: #2563eb; font-weight: bold; }
.log-line.info-green { color: #059669; }
.log-line.static { color: #94a3b8; font-style: italic; }
.code-box pre { margin: 0; background: #022c22; color: #e2e8f0; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 0.85rem; border-left: 3px solid #34d399; }

.btn-group { display: flex; gap: 10px; margin-top: 10px; }
.test-btn { padding: 8px 15px; border: none; cursor: pointer; border-radius: 20px; font-size: 0.8rem; color: white; }
.green-btn { background: linear-gradient(to right, #059669, #047857); }
.blue-btn { background: linear-gradient(to right, #3b82f6, #2563eb); }
.gray-btn { background: #64748b; }

@keyframes pulse-border { 0% { box-shadow: 0 0 10px rgba(59, 130, 246, 0.3); } 50% { box-shadow: 0 0 30px rgba(59, 130, 246, 0.8); } 100% { box-shadow: 0 0 10px rgba(59, 130, 246, 0.3); } }
@keyframes pulse-header { 0% { background: linear-gradient(135deg, #2563eb, #1e40af); } 50% { background: linear-gradient(135deg, #3b82f6, #1d4ed8); } 100% { background: linear-gradient(135deg, #2563eb, #1e40af); } }
</style>