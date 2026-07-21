<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { setGatewaySampling } from '../gateway-api'
import { buildGatewayApiUrl, buildGatewayVideoUrl } from '../gateway-config'
import { store } from '../store.js'

// 当前任务态势
const today = new Date()
const yyyy = today.getFullYear()
const mm = String(today.getMonth() + 1).padStart(2, '0')
const dd = String(today.getDate()).padStart(2, '0')
const dynamicDate = `${yyyy}${mm}${dd}`

const taskStatus = ref({
  name: '环境风险巡检任务',
  id: `TASK-${dynamicDate}-001`,
  state: '等待调度',
  area: '监测区域A',
  units: 'UAV-001 / UGV-001'
})
const THRESHOLDS = {
  TEMP_WARN: 50.0,
  TVOC_WARN: 2.0,
  SMOKE_ALARM: 600000,
  CO_ALARM: 50,
  WIND_SPREAD: 5.0,
  HUM_INTERFERENCE: 80,
}

const totalPackets = ref(15240)

// 感知网络统计
const networkStats = computed(() => {
  const nodes = store.nodes || {}
  const status = {
    ugv1: !!nodes.node1?.online,
    ugv2: !!nodes.node2?.online,
    uav: !!store.videoOnline,
    weather: !!nodes.node3?.online
  }
  const onlineCount = Object.values(status).filter(Boolean).length
  const totalNodes = 4
  return {
    aliveRatio: `${onlineCount}/${totalNodes}`,
    alivePercent: Math.round((onlineCount / totalNodes) * 100),
    networkType: '异构多链路直连',
    throughput: '2Hz (0.5s) 周期采集',
    sensingDimensions: 7,
  }
})

// 实体资源连接状态映射
const resourceStatus = computed(() => {
  return {
    ugv1: store.nodes?.node1?.online || false,
    ugv2: store.nodes?.node2?.online || false,
    uav: store.videoOnline || false,
    weather: store.nodes?.node3?.online || false
  }
})

const maxVals = computed(() => {
  const n1 = store.data.node1 || { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 }
  const n2 = store.data.node2 || { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 }
  return {
    temp: Math.max(n1.temp, n2.temp),
    hum: Math.max(n1.hum, n2.hum),
    smoke: Math.max(n1.smoke, n2.smoke),
    tvoc: Math.max(n1.tvoc, n2.tvoc),
    co: Math.max(n1.co, n2.co),
  }
})

const fireStatus = computed(() => {
  if (maxVals.value.smoke > THRESHOLDS.SMOKE_ALARM || maxVals.value.co > THRESHOLDS.CO_ALARM) {
    return { active: true, msg: '确认火灾警情', level: 'danger' }
  }
  return { active: false }
})

const warningStatus = computed(() => {
  if (fireStatus.value.active) return { active: false }
  if (maxVals.value.temp > THRESHOLDS.TEMP_WARN || maxVals.value.tvoc > THRESHOLDS.TVOC_WARN) {
    return { active: true, msg: '早期隐患预警', level: 'warning' }
  }
  return { active: false }
})

const spreadAnalysis = computed(() => {
  const wind = store.data.node3?.wind || 0
  if (wind > THRESHOLDS.WIND_SPREAD) return { msg: '扩散风险高', color: '#e53e3e' }
  return { msg: '风势平稳', color: '#38a169' }
})

const envAnalysis = computed(() => {
  if (maxVals.value.hum > THRESHOLDS.HUM_INTERFERENCE) return { isInterference: true, msg: '环境干扰偏高' }
  return { isInterference: false, msg: '环境状态稳定' }
})

const systemState = computed(() => {
  if (fireStatus.value.active) return fireStatus.value
  if (warningStatus.value.active) return warningStatus.value
  return { msg: '系统正常运行', level: 'success' }
})

const gatewayHeadline = computed(() => {
  if (!store.gatewayOnline) return '边缘计算节点失联'
  if (store.gatewayMode === 'simulation') return '边缘计算节点（仿真模式）'
  return '边缘计算节点在线'
})

const samplingStatusText = computed(() => (store.samplingRunning ? '数据采集中' : '采集已暂停'))
const realtimeStatusText = computed(() => (store.connected ? '实时通道在线' : '实时通道断开'))
const videoStatusText = computed(() => (store.videoOnline ? '视频在线' : '视频离线'))
const databaseStatusText = computed(() => (store.databaseOnline ? '数据库正常' : '数据库异常'))

const lastRealtimeLabel = computed(() => {
  if (!store.lastRealtimeAt) return '暂无'
  return store.lastRealtimeAt.replace('T', ' ')
})

const PYTHON_STREAM_URL = buildGatewayVideoUrl
const API_BASE = buildGatewayApiUrl()

const videoElement = ref(null)
const canvasElement = ref(null)
const isPlaying = ref(false)
const videoUrl = ref('')
const isRecording = ref(false)
const isAutoCapturing = ref(false)
const uploadStatus = ref('')

let mediaRecorder = null
let recordedChunks = []
let captureTimer = null
let drawFrameId = null
let lastAlertTime = 0
let mockTelemetryTimer = null

// 格式化高精度时间（带毫秒），增加科技感
const getFormattedTime = () => {
  const now = new Date()
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}.${String(now.getMilliseconds()).padStart(3, '0')}`
}

const sysLogs = ref([
  { time: getFormattedTime(), type: 'info', source: 'SYS', msg: '系统初始化完成，等待边缘端组网...' },
])

const addLog = (msg, type = 'info', source = 'SYS') => {
  sysLogs.value.unshift({ time: getFormattedTime(), type, source, msg })
  if (sysLogs.value.length > 80) sysLogs.value.pop() // 增加容量以容纳网络流
}

// ================= 新增：模拟组网 MQTT/WS 遥测数据流 =================
const startMockTelemetry = () => {
  const topics = [
    { protocol: 'MQTT', topic: '/ugv/node1/env', type: 'ugv' },
    { protocol: 'MQTT', topic: '/ugv/node2/env', type: 'ugv' },
    { protocol: 'WS', topic: '/uav/stream/status', type: 'uav' },
    { protocol: 'MQTT', topic: '/sys/broker/heartbeat', type: 'broker' }
  ]

  mockTelemetryTimer = setInterval(() => {
    // 暂停采集时放缓数据流刷新
    if (!store.samplingRunning && Math.random() > 0.3) return

    const target = topics[Math.floor(Math.random() * topics.length)]
    let payloadStr = ''

    if (target.type === 'ugv') {
      const nodeData = target.topic.includes('node1') ? store.data.node1 : store.data.node2;
      const t = nodeData?.temp || (20 + Math.random() * 5).toFixed(1)
      const h = nodeData?.hum || (40 + Math.random() * 10).toFixed(1)
      const s = nodeData?.smoke || Math.floor(Math.random() * 100)
      payloadStr = `{"T":${t},"H":${h},"Smoke":${s}}`
    } else if (target.type === 'uav') {
      payloadStr = `FrameSync: ${Date.now().toString().slice(-6)} | QoS: 1 | FPS: 30`
    } else {
      payloadStr = `{"status": "ONLINE", "latency": "${Math.floor(Math.random() * 15 + 5)}ms"}`
    }

    sysLogs.value.unshift({
      time: getFormattedTime(),
      type: 'telemetry',
      source: target.protocol,
      topic: target.topic,
      msg: payloadStr
    })

    if (sysLogs.value.length > 80) sysLogs.value.pop()
  }, 600) // 极快的数据流刷新率
}
// ==============================================================

watch(() => store.lastSampleAt, () => {
  if (store.samplingRunning) totalPackets.value += 1
})

watch(fireStatus, (nextValue) => {
  if (nextValue.active && Date.now() - lastAlertTime > 5000) {
    addLog(`自动告警: ${nextValue.msg}`, 'danger')
    lastAlertTime = Date.now()
  }
})

watch(
  () => [store.gatewayOnline, store.samplingRunning, store.connected, store.videoOnline],
  ([gatewayOnline, samplingRunning, connected, videoOnline]) => {
    const msg = [
      gatewayOnline ? '网关在线' : '网关离线',
      samplingRunning ? '采集运行中' : '采集暂停',
      connected ? '实时通道在线' : '实时通道已断',
      videoOnline ? '视频在线' : '视频离线',
    ].join(' | ')
    addLog(msg, gatewayOnline ? 'info' : 'warning')
  },
  { immediate: true }
)

const toggleSampling = async () => {
  try {
    const data = await setGatewaySampling(!store.samplingRunning)
    store.samplingRunning = Boolean(data.running)
    store.lastSampleAt = data.last_sample_at || store.lastSampleAt
    addLog(store.samplingRunning ? '已下发全局同步采集指令 (2Hz)' : '已下发链路采集挂起指令', 'success')
  } catch (error) {
    addLog('组网控制指令下发失败，请检查边缘节点', 'danger')
  }
}

const togglePlay = () => {
  if (isPlaying.value) {
    videoUrl.value = ''
    isPlaying.value = false
    addLog('已切断 UAV 图传 WebSocket 链路', 'warning')
    stopAllActions()
    return
  }
  videoUrl.value = PYTHON_STREAM_URL()
  isPlaying.value = true
  addLog('UAV 图传 WebSocket 链路已建立', 'success')
}

const stopAllActions = () => {
  if (isAutoCapturing.value) {
    isAutoCapturing.value = false
    clearInterval(captureTimer)
    addLog('自动抓拍任务终止', 'info')
  }
  if (isRecording.value) stopRecording()
}

const manualSnapshot = () => captureAndUpload('手动')

const toggleAutoCapture = () => {
  isAutoCapturing.value = !isAutoCapturing.value
  if (isAutoCapturing.value) {
    captureTimer = setInterval(() => captureAndUpload('自动'), 500)
    addLog('自动感知扫描开启 (0.5s/次)', 'info')
  } else {
    clearInterval(captureTimer)
    addLog('自动感知扫描已停止', 'info')
  }
}

const captureAndUpload = async (mode) => {
  if (!videoElement.value || !canvasElement.value || videoElement.value.naturalWidth === 0) return
  const ctx = canvasElement.value.getContext('2d')
  canvasElement.value.width = videoElement.value.naturalWidth
  canvasElement.value.height = videoElement.value.naturalHeight
  ctx.drawImage(videoElement.value, 0, 0)
  try {
    const dataUrl = canvasElement.value.toDataURL('image/jpeg', 0.8)
    await fetch(`${API_BASE}/save_drone_image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataUrl }),
    })
    if (mode === '手动') {
      uploadStatus.value = `特征已提取 ${new Date().toLocaleTimeString()}`
      addLog('手动特征抓取成功，已推入融合库', 'success')
      setTimeout(() => { if (!isRecording.value) uploadStatus.value = '' }, 2000)
    }
  } catch (error) {
    addLog(`特征抓取失败: ${error.message}`, 'danger')
  }
}

const toggleRecording = () => isRecording.value ? stopRecording() : startRecording()

const startRecording = () => {
  if (!videoElement.value || !canvasElement.value || videoElement.value.naturalWidth === 0) return
  const ctx = canvasElement.value.getContext('2d')
  canvasElement.value.width = videoElement.value.naturalWidth
  canvasElement.value.height = videoElement.value.naturalHeight
  const drawLoop = () => {
    if (!isRecording.value) return
    ctx.drawImage(videoElement.value, 0, 0)
    drawFrameId = requestAnimationFrame(drawLoop)
  }
  isRecording.value = true
  drawLoop()
  const stream = canvasElement.value.captureStream(30)
  mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' })
  recordedChunks = []
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data) }
  mediaRecorder.onstop = uploadVideo
  mediaRecorder.start()
  uploadStatus.value = '正在录像...'
  addLog('全局流录制任务已启动', 'info')
}

const stopRecording = () => {
  if (mediaRecorder) mediaRecorder.stop()
  cancelAnimationFrame(drawFrameId)
  isRecording.value = false
  addLog('录制结束，正在向中心节点归档', 'warning')
}

const uploadVideo = async () => {
  uploadStatus.value = '归档上传中...'
  const formData = new FormData()
  formData.append('file', new Blob(recordedChunks, { type: 'video/webm' }), 'record.webm')
  try {
    const response = await fetch(`${API_BASE}/save_drone_video`, { method: 'POST', body: formData })
    const data = await response.json()
    if (data.status === 'success') {
      uploadStatus.value = '归档成功'
      addLog(`视频流归档成功: ${data.path}`, 'success')
    } else {
      uploadStatus.value = '归档失败'
      addLog('归档上传失败', 'danger')
    }
  } catch (error) {
    uploadStatus.value = '归档异常'
    addLog('归档节点异常', 'danger')
  }
  setTimeout(() => { uploadStatus.value = '' }, 3000)
}

onMounted(() => {
  startMockTelemetry()
})

onBeforeUnmount(() => {
  stopAllActions()
  if (mockTelemetryTimer) clearInterval(mockTelemetryTimer)
})
</script>

<template>
  <div class="command-center-container">
    <!-- ================= 顶部全局头部 ================= -->
    <header class="cc-header">
      <div class="header-left">
        <span class="sys-badge" :class="store.gatewayOnline ? 'online' : 'offline'">
          {{ gatewayHeadline }}
        </span>
      </div>
      <h1 class="cc-title">协同指挥中心平台</h1>
      <div class="header-right">
        <span class="sys-time">{{ new Date().toLocaleDateString() }} {{ getFormattedTime().split('.')[0] }}</span>
        <div class="sys-status-mini">
          <span :class="store.databaseOnline ? 'ok' : 'err'">DB</span>
          <span :class="store.connected ? 'ok' : 'err'">LINK</span>
          <span :class="store.videoOnline ? 'ok' : 'err'">VDO</span>
        </div>
      </div>
    </header>

    <main class="cc-main">
      <!-- ================= 左侧：宏观态势与核心资源 ================= -->
      <aside class="cc-column cc-left">
        <div class="cc-panel">
          <div class="panel-header">态势与安全预警</div>
          <div class="panel-body">
            <div class="alert-box" :class="'alert-' + systemState.level">
              <div class="alert-icon">{{ systemState.level === 'danger' ? '⚠️' : '🛡️' }}</div>
              <div class="alert-info">
                <h4>{{ systemState.msg || '系统正常运行' }}</h4>
                <p>当前任务模式：协同巡检</p>
              </div>
            </div>
            
            <div class="logic-bars">
              <div class="logic-item">
                <div class="bar-label"><span>早期预警 (TVOC/温)</span><span class="val warning-text">{{ maxVals.temp }}°C</span></div>
                <div class="logic-bar"><div class="fill warning-fill" :style="{ width: Math.min((maxVals.temp / 80) * 100, 100) + '%' }"></div></div>
              </div>
              <div class="logic-item">
                <div class="bar-label"><span>火灾确认 (烟雾/CO)</span><span class="val danger-text">{{ maxVals.smoke }} ug</span></div>
                <div class="logic-bar"><div class="fill danger-fill" :style="{ width: Math.min((maxVals.smoke / 1000000) * 100, 100) + '%' }"></div></div>
              </div>
            </div>

            <div class="analysis-tags">
              <span class="cc-tag" :style="{ borderColor: spreadAnalysis.color, color: spreadAnalysis.color }">{{ spreadAnalysis.msg }}</span>
              <span class="cc-tag" :class="envAnalysis.isInterference ? 'tag-warn' : 'tag-safe'">{{ envAnalysis.msg }}</span>
            </div>
            
            <div class="control-actions">
              <button class="cc-btn" :class="store.samplingRunning ? 'btn-danger' : 'btn-primary'" @click="toggleSampling">
                {{ store.samplingRunning ? '⏹ 停止协同采集' : '▶ 启动协同采集' }}
              </button>
              <button class="cc-btn btn-ghost" @click="$router.push('/logic')">协同关系拓扑 ⎘</button>
            </div>
          </div>
        </div>

        <div class="cc-panel highlight-panel">
          <div class="panel-header res-header">
            <span>全局实体资源编队</span>
            <span class="res-live-tag">● 实时调度中</span>
          </div>
          <div class="panel-body resource-body">
            <div class="resource-grid">
              <div class="res-card">
                <div class="res-icon uav-glow">🚁</div>
                <div class="res-title">空域监测移动节点 (UAV)</div>
                <div class="res-divide"></div>
                <div class="res-data-row">
                  <div class="r-data"><span>就绪</span><strong class="tech-text">3</strong></div>
                  <div class="r-data"><span>总量</span><strong>17</strong></div>
                </div>
              </div>
              <div class="res-card">
                <div class="res-icon ugv-glow">🚙</div>
                <div class="res-title">地面监测移动节点 (UGV)</div>
                <div class="res-divide"></div>
                <div class="res-data-row">
                  <div class="r-data"><span>就绪</span><strong class="tech-text">5</strong></div>
                  <div class="r-data"><span>总量</span><strong>12</strong></div>
                </div>
              </div>
              <div class="res-card">
                <div class="res-icon station-glow">🗼</div>
                <div class="res-title">固定环境感知节点</div>
                <div class="res-divide"></div>
                <div class="res-data-row">
                  <div class="r-data"><span>在线</span><strong class="tech-text">8</strong></div>
                  <div class="r-data"><span>部署</span><strong>8</strong></div>
                </div>
              </div>
              <div class="res-card">
                <div class="res-icon video-glow">📷</div>
                <div class="res-title">视频视觉节点</div>
                <div class="res-divide"></div>
                <div class="res-data-row">
                  <div class="r-data"><span>在线</span><strong class="tech-text">4</strong></div>
                  <div class="r-data"><span>总量</span><strong>6</strong></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="cc-panel">
          <div class="panel-header">感知网络状态</div>
          <div class="panel-body compact-body">
            <div class="alive-ratio">
              <div class="lbl-row">
                <span>节点存活率 ({{ networkStats.aliveRatio }})</span>
                <span class="tech-text">{{ networkStats.alivePercent }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill tech-fill" :style="{width: networkStats.alivePercent + '%'}"></div>
              </div>
            </div>
            <div class="net-info-row">
              <span class="cc-tag tag-blue">组网: {{ networkStats.networkType }}</span>
              <span class="cc-tag tag-blue">感知维度: {{ networkStats.sensingDimensions }} 项</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- ================= 中央：核心视图 ================= -->
      <section class="cc-column cc-center">
        <div class="task-banner">
          <div class="tb-item"><span>任务ID</span><strong>{{ taskStatus.id }}</strong></div>
          <div class="tb-item"><span>任务名称</span><strong>{{ taskStatus.name }}</strong></div>
          <div class="tb-item"><span>执行单元</span><strong>{{ taskStatus.units }}</strong></div>
          <div class="tb-item"><span>覆盖区域</span><strong>{{ taskStatus.area }}</strong></div>
          <div class="tb-item status"><span>状态</span><strong class="tech-text">{{ taskStatus.state }}</strong></div>
        </div>

        <div class="drone-console">
          <div class="dc-header">
            <div class="title-with-icon"><span class="blink-dot"></span>空域监测节点 (UAV) 实时图传</div>
            <div class="dc-status">{{ uploadStatus || (isPlaying ? '📡 链路已连接' : videoStatusText) }}</div>
          </div>
          
          <div class="dc-viewport">
            <img v-if="isPlaying" ref="videoElement" :src="videoUrl" class="video-feed" crossorigin="anonymous" />
            <div v-else class="no-signal">
              <div class="signal-icon">⚠️</div>
              <p>NO VIDEO SIGNAL</p>
            </div>
            <div v-if="isRecording" class="rec-badge">🔴 REC</div>
            
            <div class="hud-overlay top-left"></div>
            <div class="hud-overlay top-right"></div>
            <div class="hud-overlay bottom-left"></div>
            <div class="hud-overlay bottom-right"></div>
          </div>

          <div class="dc-controls">
            <button @click="togglePlay" class="cc-btn" :class="isPlaying ? 'btn-danger' : 'btn-tech'">
              {{ isPlaying ? '⏹ 断开图传' : '▶ 接管图传' }}
            </button>
            <button @click="manualSnapshot" :disabled="!isPlaying" class="cc-btn btn-ghost">📸 抓拍环境</button>
            <button @click="toggleAutoCapture" :disabled="!isPlaying" class="cc-btn" :class="isAutoCapturing ? 'btn-active' : 'btn-ghost'">
              {{ isAutoCapturing ? '🔄 自动扫描中' : '⟳ 自动扫描' }}
            </button>
            <button @click="toggleRecording" :disabled="!isPlaying" class="cc-btn" :class="isRecording ? 'btn-danger' : 'btn-ghost'">
              {{ isRecording ? '⏹ 停止录像' : '⏺ 录像归档' }}
            </button>
          </div>
        </div>

        <!-- ================= 升级版：传感网组网通信遥测面板 ================= -->
        <div class="cc-panel log-panel">
          <div class="panel-header">
            <div class="title-with-icon">
              <span class="blink-dot" style="background:#10b981;box-shadow:0 0 6px #10b981;"></span>
              组网通信与系统指令
            </div>
            <div class="network-nodes-mini">
              <span class="n-node"><i class="node-dot sys"></i>Broker</span>
              <span class="n-node"><i class="node-dot uav"></i>UAV (WS)</span>
              <span class="n-node"><i class="node-dot ugv"></i>UGV (MQTT)</span>
            </div>
          </div>
          <div class="log-viewport">
            <!-- 融合了 SYS系统指令 和 MQTT/WS 遥测数据的流 -->
            <div v-for="(log, index) in sysLogs" :key="index" class="log-row" :class="log.type">
              <span class="log-time">[{{ log.time }}]</span>
              <span class="log-source" :class="log.source.toLowerCase()">{{ log.source }}</span>
              <span class="log-topic" v-if="log.topic">[{{ log.topic }}]</span>
              <span class="log-msg">{{ log.msg }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= 右侧：节点详情 ================= -->
      <aside class="cc-column cc-right">
        <!-- UGV 001 -->
        <div class="cc-panel node-card" @click="$router.push('/node1')">
          <div class="node-header">
            <h3>监测点-001 <small>(UGV)</small></h3>
            <span class="node-status" :class="{online: store.nodes?.node1?.online}">{{ store.nodes?.node1?.online ? 'ONLINE' : 'OFFLINE' }}</span>
          </div>
          <div class="dashboard-grid">
            <div class="n-box"><span class="n-lbl">温度</span><strong class="n-val">{{ store.data.node1?.temp || 0 }}<small>°C</small></strong></div>
            <div class="n-box"><span class="n-lbl">湿度</span><strong class="n-val">{{ store.data.node1?.hum || 0 }}<small>%</small></strong></div>
            <div class="n-box"><span class="n-lbl">TVOC</span><strong class="n-val">{{ store.data.node1?.tvoc || 0 }}</strong></div>
            <div class="n-box"><span class="n-lbl">CO浓度</span><strong class="n-val">{{ store.data.node1?.co || 0 }}</strong></div>
            <div class="n-box wide-box"><span class="n-lbl">烟雾浓度 (ug)</span><strong class="n-val danger-text">{{ store.data.node1?.smoke || 0 }}</strong></div>
          </div>
        </div>

        <!-- UGV 002 -->
        <div class="cc-panel node-card" @click="$router.push('/node2')">
          <div class="node-header">
            <h3>监测点-002 <small>(UGV)</small></h3>
            <span class="node-status" :class="{online: store.nodes?.node2?.online}">{{ store.nodes?.node2?.online ? 'ONLINE' : 'OFFLINE' }}</span>
          </div>
          <div class="dashboard-grid">
            <div class="n-box"><span class="n-lbl">温度</span><strong class="n-val">{{ store.data.node2?.temp || 0 }}<small>°C</small></strong></div>
            <div class="n-box"><span class="n-lbl">湿度</span><strong class="n-val">{{ store.data.node2?.hum || 0 }}<small>%</small></strong></div>
            <div class="n-box"><span class="n-lbl">TVOC</span><strong class="n-val">{{ store.data.node2?.tvoc || 0 }}</strong></div>
            <div class="n-box"><span class="n-lbl">CO浓度</span><strong class="n-val">{{ store.data.node2?.co || 0 }}</strong></div>
            <div class="n-box wide-box"><span class="n-lbl">烟雾浓度 (ug)</span><strong class="n-val danger-text">{{ store.data.node2?.smoke || 0 }}</strong></div>
          </div>
        </div>

        <!-- 固定环境感知节点 -->
        <div class="cc-panel node-card" @click="$router.push('/node3')">
          <div class="node-header">
            <h3>固定环境感知节点</h3>
            <span class="node-status tech" :class="{online: store.nodes?.node3?.online}">{{ store.nodes?.node3?.online ? 'ONLINE' : 'OFFLINE' }}</span>
          </div>
          <div class="dashboard-grid">
            <div class="n-box"><span class="n-lbl">风速</span><strong class="n-val tech-text">{{ store.data.node3?.wind || 0 }}<small>m/s</small></strong></div>
            <div class="n-box"><span class="n-lbl">风向</span><strong class="n-val tech-text">{{ store.data.node3?.wind_dir || 0 }}</strong></div>
            <div class="n-box"><span class="n-lbl">评估</span><strong class="n-val warning-text">{{ (store.data.node3?.wind || 0) > 10.7 ? '强风' : ((store.data.node3?.wind || 0) > 5.4 ? '和风' : '微风') }}</strong></div>
          </div>
        </div>

        <!-- 底部通道状态 -->
        <div class="cc-panel sys-status-panel">
          <div class="sys-grid">
            <div class="s-row"><span>实时数据通道</span> <b :class="store.connected ? 'ok' : 'err'">{{ realtimeStatusText }}</b></div>
            <div class="s-row"><span>网络心跳回传</span> <b>{{ lastRealtimeLabel }}</b></div>
          </div>
        </div>
      </aside>
    </main>

    <canvas ref="canvasElement" style="display: none;"></canvas>
  </div>
</template>

<style scoped>
/* ================= 核心色板与全局设定 (彻底移除旧版外部字体引入) ================= */

.command-center-container {
  /* 使用更深邃的暗空背景，配合一点点底层的蓝色光晕 */
  background: #030710 radial-gradient(circle at 50% 0%, rgba(0, 114, 255, 0.1) 0%, rgba(6, 14, 28, 1) 100%);
  color: rgba(186, 230, 253, 0.88); 
  height: 100vh;
  width: 100%;
  max-width: 1800px;
  margin: 0 auto;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  /* 严格对标参考标准：高级无衬线系统字体栈 */
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  box-sizing: border-box;
}
* { box-sizing: border-box; }

/* ================= 顶部全局头部 ================= */
.cc-header {
  height: 50px; 
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 20px; 
  background: rgba(6, 14, 28, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 242, 254, 0.3); 
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.7), 0 0 15px rgba(0, 242, 254, 0.1); 
  z-index: 10;
}
.header-left, .header-right { flex: 1; display: flex; align-items: center; }
.header-right { justify-content: flex-end; gap: 12px; }

/* 标题：改用精准px，增加等宽感 */
.cc-title { 
  flex: 2; text-align: center; margin: 0; 
  font-size: 19px; 
  font-weight: 700; 
  letter-spacing: 1.5px; 
  color: #00f2fe; 
  text-shadow: 0 0 12px rgba(0, 242, 254, 0.6); 
}

.sys-badge { padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; border: 1px solid; }
.sys-badge.online { background: rgba(16, 185, 129, 0.1); color: #10b981; border-color: rgba(16, 185, 129, 0.5); box-shadow: 0 0 8px rgba(16, 185, 129, 0.2); }
.sys-badge.offline { background: rgba(239, 68, 68, 0.1); color: #ef4444; border-color: rgba(239, 68, 68, 0.5); box-shadow: 0 0 8px rgba(239, 68, 68, 0.2); }

/* 时间和数字：严格使用 JetBrains Mono 等宽字体规范 */
.sys-time { 
  font-family: "JetBrains Mono", monospace; 
  font-size: 13.5px; 
  color: rgba(0, 242, 254, 0.7); 
}
.sys-status-mini { display: flex; gap: 6px; font-size: 11px; font-weight: bold; }
.sys-status-mini span { 
  padding: 2px 5px; border-radius: 3px; border: 1px solid; background: rgba(0,0,0,0.3); 
  font-family: "JetBrains Mono", monospace;
}
.sys-status-mini .ok { color: #10b981; border-color: rgba(16, 185, 129, 0.5); }
.sys-status-mini .err { color: #ef4444; border-color: rgba(239, 68, 68, 0.5); }

/* ================= 核心栅格布局 ================= */
.cc-main {
  flex: 1; display: grid;
  grid-template-columns: 2.6fr 4.2fr 3.2fr; 
  gap: 12px; padding: 12px; 
  overflow: hidden;
}

.cc-column { display: flex; flex-direction: column; gap: 12px; height: 100%; overflow-y: auto; overflow-x: hidden; }
.cc-column::-webkit-scrollbar { width: 4px; }
.cc-column::-webkit-scrollbar-thumb { background: rgba(0, 242, 254, 0.3); border-radius: 2px; }

/* 面板通用 */
.cc-panel { 
  background: rgba(6, 14, 28, 0.82); 
  backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid rgba(0, 242, 254, 0.25); 
  border-radius: 10px; 
  box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 16px rgba(0, 242, 254, 0.06);
  display: flex; flex-direction: column; flex-shrink: 0; 
  overflow: hidden;
}
.panel-header { 
  padding: 10px 12px; 
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.14), rgba(0, 114, 255, 0.08));
  border-bottom: 1px solid rgba(0, 242, 254, 0.18); 
  font-size: 14.5px; font-weight: 700; color: #00f2fe; letter-spacing: 0.5px;
  display: flex; justify-content: space-between; align-items: center; 
}
.panel-body { padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; }
.compact-body { padding: 8px 12px; gap: 8px; }

/* ================= 左侧：态势预警 ================= */
.alert-box { display: flex; gap: 10px; padding: 8px; border-radius: 6px; border-left: 4px solid; background: rgba(0,0,0,0.4); backdrop-filter: blur(5px); }
.alert-icon { font-size: 17px; }
.alert-info h4 { margin: 0 0 2px 0; font-size: 13.5px; color: #fff; text-shadow: 0 0 5px rgba(255,255,255,0.3); }
.alert-info p { margin: 0; font-size: 11px; color: rgba(186, 230, 253, 0.6); line-height: 1.4;}
.alert-danger { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.12); box-shadow: inset 0 0 15px rgba(239, 68, 68, 0.05); }
.alert-warning { border-left-color: #f59e0b; background: rgba(245, 158, 11, 0.12); box-shadow: inset 0 0 15px rgba(245, 158, 11, 0.05); }
.alert-success { border-left-color: #10b981; background: rgba(16, 185, 129, 0.12); box-shadow: inset 0 0 15px rgba(16, 185, 129, 0.05); }

.logic-bars { display: flex; flex-direction: column; gap: 8px; }
.logic-item { font-size: 11px; }
.bar-label { display: flex; justify-content: space-between; margin-bottom: 3px; color: rgba(148, 163, 184, 0.9); }
.logic-bar { height: 5px; background: rgba(0, 242, 254, 0.08); border: 1px solid rgba(0, 242, 254, 0.15); border-radius: 3px; overflow: hidden; }
.fill { height: 100%; transition: width 0.5s cubic-bezier(0.25, 1, 0.5, 1); }
.warning-fill { background: #f59e0b; box-shadow: 0 0 10px #f59e0b; }
.danger-fill { background: #ef4444; box-shadow: 0 0 10px #ef4444; }
.tech-fill { background: #00f2fe; box-shadow: 0 0 10px rgba(0, 242, 254, 0.8); }

.warning-text { color: #f59e0b; font-weight: bold; text-shadow: 0 0 6px rgba(245, 158, 11, 0.4); }
.danger-text { color: #ef4444; font-weight: bold; text-shadow: 0 0 8px rgba(239, 68, 68, 0.6); }
.tech-text { color: #00f2fe; font-weight: bold; font-family: "JetBrains Mono", monospace; text-shadow: 0 0 8px rgba(0, 242, 254, 0.5);}

.analysis-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.cc-tag { padding: 3px 6px; border: 1px solid; border-radius: 4px; font-size: 10px; font-family: "JetBrains Mono", monospace; background: rgba(0,0,0,0.4); }
.tag-warn { border-color: rgba(245, 158, 11, 0.5); color: #f59e0b; }
.tag-safe { border-color: rgba(16, 185, 129, 0.5); color: #10b981; }
.tag-blue { border-color: rgba(0, 242, 254, 0.3); color: #00f2fe; background: rgba(0, 242, 254, 0.05); }

.control-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 2px; }

/* ================= 左侧：资源矩阵 ================= */
.highlight-panel { border-color: rgba(0, 242, 254, 0.6); box-shadow: 0 0 20px rgba(0, 242, 254, 0.15) inset, 0 8px 32px rgba(0,0,0,0.6); }
.res-header { background: linear-gradient(135deg, rgba(0, 242, 254, 0.25), rgba(0, 114, 255, 0.05)); border-bottom-color: rgba(0, 242, 254, 0.4); }
.res-live-tag { font-size: 10px; font-family: monospace; color: #10b981; animation: pulse 1.5s infinite; background: rgba(16, 185, 129, 0.15); padding: 2px 4px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.3); }

.resource-body { padding: 8px; }
.resource-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.res-card { 
  background: rgba(0, 242, 254, 0.03); 
  border: 1px solid rgba(0, 242, 254, 0.15); 
  border-radius: 6px; padding: 8px 4px; 
  display: flex; flex-direction: column; align-items: center; justify-content: center; 
  transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1); 
}
.res-card:hover { border-color: rgba(0, 242, 254, 0.7); background: rgba(0, 242, 254, 0.08); box-shadow: 0 0 15px rgba(0, 242, 254, 0.2); }
.res-icon { font-size: 22px; margin-bottom: 4px; filter: drop-shadow(0 0 5px rgba(0, 242, 254, 0.5)); }
.res-title { font-size: 11.5px; font-weight: bold; color: #fff; margin-bottom: 6px; }
.res-divide { width: 50%; height: 2px; background: linear-gradient(90deg, transparent, rgba(0, 242, 254, 0.6), transparent); margin-bottom: 6px; }
.res-data-row { display: flex; width: 100%; justify-content: space-around; }
.r-data { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.r-data span { font-size: 9.5px; color: rgba(148, 163, 184, 0.8); }
.r-data strong { font-size: 15px; font-weight: bold; font-family: "JetBrains Mono", monospace; color: #e2e8f0; line-height: 1;}

.alive-ratio .lbl-row { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; color: rgba(186, 230, 253, 0.88); }
.progress-bar { height: 5px; background: rgba(0, 242, 254, 0.08); border: 1px solid rgba(0, 242, 254, 0.15); border-radius: 3px; overflow: hidden; }
.net-info-row { display: flex; gap: 8px; margin-top: 6px; }

/* ================= 中央：视频与指令 ================= */
.task-banner { 
  display: flex; justify-content: space-between; 
  background: rgba(6, 14, 28, 0.85); backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 242, 254, 0.3); 
  box-shadow: 0 4px 15px rgba(0,0,0,0.5), 0 0 10px rgba(0, 242, 254, 0.05);
  border-radius: 8px; padding: 6px 15px; 
}
.tb-item { display: flex; flex-direction: column; gap: 2px; }
.tb-item span { font-size: 10px; color: rgba(0, 242, 254, 0.6); font-family: "JetBrains Mono", monospace; }
.tb-item strong { font-size: 13.5px; color: #fff; font-weight: 700; }

.drone-console { 
  flex: 1; display: flex; flex-direction: column; 
  background: #000; 
  border: 1px solid rgba(0, 242, 254, 0.3); 
  border-radius: 8px; overflow: hidden; min-height: 200px; position: relative; 
  box-shadow: 0 8px 32px rgba(0,0,0,0.8), 0 0 15px rgba(0, 242, 254, 0.1);
}
.dc-header { position: absolute; top: 0; left: 0; right: 0; padding: 8px 12px; background: linear-gradient(180deg, rgba(0,0,0,0.9) 0%, transparent 100%); display: flex; justify-content: space-between; align-items: center; z-index: 2; }
.title-with-icon { display: flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: bold; color: #00f2fe; }
.blink-dot { width: 6px; height: 6px; background: #ef4444; border-radius: 50%; box-shadow: 0 0 8px #ef4444; animation: pulse 1.5s infinite; }
.dc-status { font-size: 11px; color: #00f2fe; font-family: "JetBrains Mono", monospace; }
.dc-viewport { flex: 1; position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.video-feed { width: 100%; height: 100%; object-fit: contain; }
.no-signal { text-align: center; color: rgba(0, 242, 254, 0.3); }
.signal-icon { font-size: 32px; margin-bottom: 5px; opacity: 0.5; }
.rec-badge { position: absolute; top: 10px; right: 10px; background: rgba(239,68,68,0.9); color: white; padding: 3px 6px; border-radius: 3px; font-size: 10px; font-family: monospace; font-weight: bold; animation: pulse 1s infinite; z-index: 2; box-shadow: 0 0 10px rgba(239, 68, 68, 0.5); }

.hud-overlay { position: absolute; width: 25px; height: 25px; border: 2px solid #00f2fe; z-index: 2; opacity: 0.6; box-shadow: 0 0 10px rgba(0, 242, 254, 0.4); }
.top-left { top: 15px; left: 15px; border-right: none; border-bottom: none; }
.top-right { top: 15px; right: 15px; border-left: none; border-bottom: none; }
.bottom-left { bottom: 15px; left: 15px; border-right: none; border-top: none; }
.bottom-right { bottom: 15px; right: 15px; border-left: none; border-top: none; }

.dc-controls { padding: 6px; background: rgba(6, 14, 28, 0.9); border-top: 1px solid rgba(0, 242, 254, 0.3); display: flex; gap: 8px; justify-content: center; backdrop-filter: blur(10px); }

/* ================= 升级：组网通信遥测日志面板 ================= */
.log-panel { height: 210px; flex-shrink: 0; } 
.network-nodes-mini { display: flex; gap: 12px; font-size: 10.5px; font-family: "JetBrains Mono", monospace; color: rgba(186, 230, 253, 0.7); align-items: center;}
.n-node { display: flex; align-items: center; gap: 4px; }
.node-dot { width: 6px; height: 6px; border-radius: 50%; }
.node-dot.sys { background: #00f2fe; box-shadow: 0 0 6px #00f2fe; }
.node-dot.uav { background: #fbbf24; box-shadow: 0 0 6px #fbbf24; }
.node-dot.ugv { background: #10b981; box-shadow: 0 0 6px #10b981; }

.log-viewport { 
  flex: 1; overflow-y: hidden; padding: 8px 10px; 
  background: rgba(0, 0, 0, 0.5); 
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.8);
  border-radius: 6px; 
  font-family: "JetBrains Mono", 'Consolas', monospace; 
  font-size: 11px; 
  display: flex; flex-direction: column;
}
.log-row { margin-bottom: 4px; line-height: 1.4; border-bottom: 1px dashed rgba(0, 242, 254, 0.1); padding-bottom: 3px; word-break: break-all; }

.log-time { color: rgba(0, 242, 254, 0.7); margin-right: 6px; }
.log-topic { color: rgba(186, 230, 253, 0.88); margin-right: 6px; font-size: 10px;}

.log-source { padding: 1px 5px; border-radius: 3px; margin-right: 6px; font-weight: bold; font-size: 9.5px; display: inline-block; min-width: 38px; text-align: center;}
.log-source.sys { background: rgba(0, 242, 254, 0.15); color: #00f2fe; border: 1px solid rgba(0, 242, 254, 0.4); }
.log-source.mqtt { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); }
.log-source.ws { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }

.log-row.telemetry .log-msg { color: rgba(186, 230, 253, 0.7); }
.log-row.info .log-msg { color: #fff; text-shadow: 0 0 5px rgba(255,255,255,0.3); }
.log-row.warning .log-msg { color: #f59e0b; text-shadow: 0 0 5px rgba(245, 158, 11, 0.4); }
.log-row.danger .log-msg { color: #ef4444; text-shadow: 0 0 5px rgba(239, 68, 68, 0.4); }
.log-row.success .log-msg { color: #10b981; text-shadow: 0 0 5px rgba(16, 185, 129, 0.4); }

/* ================= 右侧：节点详情 ================= */
.node-card { cursor: pointer; transition: 0.3s cubic-bezier(0.25, 1, 0.5, 1); display: flex; flex-direction: column;}
.node-card:hover { border-color: #00f2fe; box-shadow: 0 0 16px rgba(0, 242, 254, 0.3); background: rgba(0, 242, 254, 0.05); }
.node-header { 
  display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; 
  border-bottom: 1px solid rgba(0, 242, 254, 0.15); 
  background: linear-gradient(90deg, rgba(0, 242, 254, 0.08) 0%, transparent 100%);
}
.node-header h3 { margin: 0; font-size: 13.5px; color: #fff; font-weight: bold; }
.node-header small { color: rgba(0, 242, 254, 0.6); font-size: 10px; font-family: "JetBrains Mono", monospace;}
.node-status { font-size: 9.5px; padding: 2px 4px; border-radius: 3px; background: rgba(239,68,68,0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #ef4444; font-family: monospace; font-weight: bold;}
.node-status.online { background: rgba(16,185,129,0.15); border-color: rgba(16, 185, 129, 0.4); color: #10b981; }
.node-status.tech.online { background: rgba(0, 242, 254, 0.15); border-color: rgba(0, 242, 254, 0.4); color: #00f2fe; }

.dashboard-grid { display: flex; flex-direction: column; gap: 6px; padding: 10px 12px; }
.n-box { 
  background: rgba(0, 0, 0, 0.4); 
  border: 1px solid rgba(0, 242, 254, 0.1); 
  box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.02);
  border-radius: 6px; padding: 6px 12px; 
  display: flex; flex-direction: row; align-items: center; justify-content: space-between; 
}

.n-lbl { font-size: 11px; color: rgba(186, 230, 253, 0.7); margin-bottom: 0; }
.n-val { font-size: 15px; color: #fff; font-weight: bold; font-family: "JetBrains Mono", monospace; line-height: 1; text-shadow: 0 0 5px rgba(255,255,255,0.4); }
.n-val small { font-size: 10px; margin-left: 4px; color: rgba(0, 242, 254, 0.6); font-family: -apple-system, sans-serif; text-shadow: none; font-weight: normal; }

.sys-status-panel { padding: 8px 12px; display: flex; flex-direction: column; justify-content: center; }
.sys-grid { display: flex; flex-direction: column; gap: 6px; }
.s-row { display: flex; justify-content: space-between; font-size: 11.5px; padding-bottom: 4px; border-bottom: 1px dashed rgba(0, 242, 254, 0.15); }
.s-row:last-child { border-bottom: none; padding-bottom: 0; }
.s-row span { color: rgba(186, 230, 253, 0.7); }
.s-row b { font-family: "JetBrains Mono", monospace; color: #fff; }
.s-row .ok { color: #10b981; text-shadow: 0 0 5px rgba(16, 185, 129, 0.5); }
.s-row .err { color: #ef4444; text-shadow: 0 0 5px rgba(239, 68, 68, 0.5); }

/* 按钮及动画 (幽灵光效体系) */
.cc-btn { 
  padding: 6px 10px; border: none; border-radius: 6px; font-size: 11.5px; font-weight: bold; cursor: pointer; 
  transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1); 
  font-family: inherit;
}
.btn-primary { 
  background: rgba(0, 242, 254, 0.15); color: #00f2fe; 
  border: 1px solid #00f2fe; box-shadow: 0 0 8px rgba(0, 242, 254, 0.3);
  text-shadow: 0 0 5px rgba(0, 242, 254, 0.5);
}
.btn-primary:hover { background: rgba(0, 242, 254, 0.25); box-shadow: 0 0 15px rgba(0, 242, 254, 0.5); }

.btn-danger { 
  background: rgba(239, 68, 68, 0.15); color: #ef4444; 
  border: 1px solid #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
}
.btn-danger:hover { background: rgba(239, 68, 68, 0.25); box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }

.btn-tech { 
  background: rgba(16, 185, 129, 0.15); color: #10b981; 
  border: 1px solid #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.3); 
}

.btn-ghost { 
  background: transparent; color: rgba(186, 230, 253, 0.88); 
  border: 1px solid rgba(0, 242, 254, 0.3); 
}
.btn-ghost:hover { background: rgba(0, 242, 254, 0.12); color: #fff; border-color: #00f2fe; box-shadow: 0 0 10px rgba(0, 242, 254, 0.3); }

.btn-active { 
  background: rgba(0, 242, 254, 0.25); color: #fff; 
  border: 1px solid #00f2fe; box-shadow: 0 0 12px rgba(0, 242, 254, 0.5); 
  animation: pulse-cyan 2s infinite; 
}
.cc-btn:disabled { opacity: 0.4; cursor: not-allowed; filter: grayscale(1); box-shadow: none; }

@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
@keyframes pulse-cyan { 
  0% { box-shadow: 0 0 8px rgba(0, 242, 254, 0.4); } 
  50% { box-shadow: 0 0 16px rgba(0, 242, 254, 0.8); } 
  100% { box-shadow: 0 0 8px rgba(0, 242, 254, 0.4); } 
}

@media (max-width: 1400px) { 
  .cc-main { grid-template-columns: 2.8fr 4.2fr 3.0fr; } 
}
</style>