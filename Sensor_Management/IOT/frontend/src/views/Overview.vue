<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { setGatewaySampling } from '../gateway-api'
import { buildGatewayApiUrl, buildGatewayVideoUrl } from '../gateway-config'
import { store } from '../store.js'
// 当前任务态势
// 动态获取当天日期并格式化为 YYYYMMDD
const today = new Date()
const yyyy = today.getFullYear()
const mm = String(today.getMonth() + 1).padStart(2, '0')
const dd = String(today.getDate()).padStart(2, '0')
const dynamicDate = `${yyyy}${mm}${dd}`

// 当前任务态势
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

// 感知网络统计：严格匹配实际 4 个物理节点 (2台UGV, 1台UAV, 1个气象站)
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
  if (wind > THRESHOLDS.WIND_SPREAD) {
    return { msg: '扩散风险高', color: '#e53e3e' }
  }
  return { msg: '风势平稳', color: '#38a169' }
})

const envAnalysis = computed(() => {
  if (maxVals.value.hum > THRESHOLDS.HUM_INTERFERENCE) {
    return { isInterference: true, msg: '环境干扰偏高' }
  }
  return { isInterference: false, msg: '环境状态稳定' }
})

const systemState = computed(() => {
  if (fireStatus.value.active) return fireStatus.value
  if (warningStatus.value.active) return warningStatus.value
  return { msg: '系统正常运行', level: 'success' }
})

const gatewayHeadline = computed(() => {

  if (!store.gatewayOnline) {
    return '边缘计算节点失联'
  }

  if(store.gatewayMode === 'simulation'){
    return '边缘计算节点（仿真模式）'
  }

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
const sysLogs = ref([
  { time: new Date().toLocaleTimeString(), type: 'info', msg: '系统初始化完成，等待边缘端状态...' },
])

let mediaRecorder = null
let recordedChunks = []
let captureTimer = null
let drawFrameId = null
let lastAlertTime = 0

const addLog = (msg, type = 'info') => {
  const time = new Date().toLocaleTimeString()
  sysLogs.value.unshift({ time, type, msg })
  if (sysLogs.value.length > 50) sysLogs.value.pop()
}

watch(() => store.lastSampleAt, () => {
  if (store.samplingRunning) {
    totalPackets.value += 1
  }
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
    ].join(' / ')
    addLog(msg, gatewayOnline ? 'info' : 'warning')
  },
  { immediate: true }
)

const toggleSampling = async () => {
  try {
    const data = await setGatewaySampling(!store.samplingRunning)
    store.samplingRunning = Boolean(data.running)
    store.lastSampleAt = data.last_sample_at || store.lastSampleAt
    addLog(store.samplingRunning ? '已发送2Hz采集命令' : '已发送停止采集命令', 'success')
  } catch (error) {
    addLog('采集控制命令发送失败', 'danger')
  }
}

const togglePlay = () => {
  if (isPlaying.value) {
    videoUrl.value = ''
    isPlaying.value = false
    addLog('视频流连接已断开', 'warning')
    stopAllActions()
    return
  }

  videoUrl.value = PYTHON_STREAM_URL()
  isPlaying.value = true
  addLog('视频流连接已建立', 'success')
}

const stopAllActions = () => {
  if (isAutoCapturing.value) {
    isAutoCapturing.value = false
    clearInterval(captureTimer)
    addLog('自动抓拍已停止', 'info')
  }
  if (isRecording.value) stopRecording()
}

const manualSnapshot = () => captureAndUpload('手动')

const toggleAutoCapture = () => {
  isAutoCapturing.value = !isAutoCapturing.value
  if (isAutoCapturing.value) {
    captureTimer = setInterval(() => captureAndUpload('自动'), 500)
    addLog('自动抓拍已开启 (0.5s)', 'info')
  } else {
    clearInterval(captureTimer)
    addLog('自动抓拍已停止', 'info')
  }
}

const captureAndUpload = async (mode) => {
  if (!videoElement.value || !canvasElement.value) return
  if (videoElement.value.naturalWidth === 0) return

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
      uploadStatus.value = `截图已保存 ${new Date().toLocaleTimeString()}`
      addLog('手动抓拍成功，已关联传感器数据', 'success')
      setTimeout(() => {
        if (!isRecording.value) uploadStatus.value = ''
      }, 2000)
    }
  } catch (error) {
    addLog(`抓拍失败: ${error.message}`, 'danger')
  }
}

const toggleRecording = () => {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

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
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) recordedChunks.push(event.data)
  }
  mediaRecorder.onstop = uploadVideo
  mediaRecorder.start()

  uploadStatus.value = '正在录像...'
  addLog('录像任务已启动', 'info')
}

const stopRecording = () => {
  if (mediaRecorder) mediaRecorder.stop()
  cancelAnimationFrame(drawFrameId)
  isRecording.value = false
  addLog('录像结束，正在上传归档', 'warning')
}

const uploadVideo = async () => {
  uploadStatus.value = '视频上传中...'
  const formData = new FormData()
  formData.append('file', new Blob(recordedChunks, { type: 'video/webm' }), 'record.webm')

  try {
    const response = await fetch(`${API_BASE}/save_drone_video`, { method: 'POST', body: formData })
    const data = await response.json()
    if (data.status === 'success') {
      uploadStatus.value = '录像归档成功'
      addLog(`录像归档成功: ${data.path}`, 'success')
    } else {
      uploadStatus.value = '录像归档失败'
      addLog('录像上传失败', 'danger')
    }
  } catch (error) {
    uploadStatus.value = '录像上传异常'
    addLog('录像上传异常', 'danger')
  }

  setTimeout(() => {
    uploadStatus.value = ''
  }, 3000)
}

onBeforeUnmount(() => {
  stopAllActions()
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
        <span class="sys-time">{{ new Date().toLocaleDateString() }} {{ sysLogs[0]?.time || '' }}</span>
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
            <div class="title-with-icon"><span class="blink-dot"></span>空域监测移动节点点 (UAV) 实时图传</div>
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

        <div class="cc-panel log-panel">
          <div class="panel-header">实时协同指令日志 <span class="log-count">Total: {{ sysLogs.length }}</span></div>
          <div class="log-viewport">
            <div v-for="(log, index) in sysLogs" :key="index" class="log-row" :class="log.type">
              <span class="log-time">[{{ log.time }}]</span>
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

        <!-- 底部通道状态：去除了flex-fill，极限压缩高度 -->
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
/* ================= 核心色板与全局设定 ================= */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');

.command-center-container {
  background: #050b14 radial-gradient(circle at 50% 0%, #0a192f 0%, #050b14 100%);
  color: #e2e8f0;
  height: 100vh;
  width: 100%;
  max-width: 1800px;
  margin: 0 auto;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, 'Rajdhani', sans-serif;
  box-sizing: border-box;
}
* { box-sizing: border-box; }

/* ================= 顶部全局头部 ================= */
.cc-header {
  height: 50px; 
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 20px; background: rgba(6, 13, 26, 0.8);
  border-bottom: 1px solid #1a365d; box-shadow: 0 4px 15px rgba(0,0,0,0.5); z-index: 10;
}
.header-left, .header-right { flex: 1; display: flex; align-items: center; }
.header-right { justify-content: flex-end; gap: 12px; }
.cc-title { flex: 2; text-align: center; margin: 0; font-size: 1.3rem; font-weight: 700; letter-spacing: 2px; color: #64ffda; text-shadow: 0 0 10px rgba(100, 255, 218, 0.4); font-family: 'Orbitron', sans-serif; }

.sys-badge { padding: 3px 10px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid; }
.sys-badge.online { background: rgba(16, 185, 129, 0.1); color: #10b981; border-color: #10b981; }
.sys-badge.offline { background: rgba(239, 68, 68, 0.1); color: #ef4444; border-color: #ef4444; }

.sys-time { font-family: 'Orbitron', monospace; font-size: 0.85rem; color: #94a3b8; }
.sys-status-mini { display: flex; gap: 6px; font-size: 0.7rem; font-weight: bold; }
.sys-status-mini span { padding: 2px 5px; border-radius: 3px; border: 1px solid; }
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
.cc-column::-webkit-scrollbar-thumb { background: rgba(30, 58, 138, 0.5); border-radius: 2px; }

/* 面板通用 */
.cc-panel { background: rgba(10, 25, 47, 0.6); border: 1px solid #1e3a8a; border-radius: 6px; display: flex; flex-direction: column; flex-shrink: 0; }
.panel-header { padding: 8px 12px; background: linear-gradient(90deg, rgba(30, 58, 138, 0.4) 0%, transparent 100%); border-bottom: 1px solid rgba(30, 58, 138, 0.5); font-size: 0.9rem; font-weight: 700; color: #60a5fa; display: flex; justify-content: space-between; align-items: center; }
.panel-body { padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; }
.compact-body { padding: 8px 12px; gap: 8px; }
.flex-fill { flex: 1; min-height: 0; }

/* ================= 左侧：态势预警 ================= */
.alert-box { display: flex; gap: 10px; padding: 8px; border-radius: 6px; border-left: 4px solid; background: rgba(0,0,0,0.2); }
.alert-icon { font-size: 1.3rem; }
.alert-info h4 { margin: 0 0 2px 0; font-size: 1rem; color: #fff; }
.alert-info p { margin: 0; font-size: 0.75rem; color: #94a3b8; }
.alert-danger { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
.alert-warning { border-left-color: #f59e0b; background: rgba(245, 158, 11, 0.1); }
.alert-success { border-left-color: #10b981; background: rgba(16, 185, 129, 0.1); }

.logic-bars { display: flex; flex-direction: column; gap: 8px; }
.logic-item { font-size: 0.75rem; }
.bar-label { display: flex; justify-content: space-between; margin-bottom: 3px; color: #cbd5e1; }
.logic-bar { height: 5px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; }
.fill { height: 100%; transition: width 0.5s; }
.warning-fill { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
.danger-fill { background: #ef4444; box-shadow: 0 0 8px #ef4444; }
.tech-fill { background: #3b82f6; box-shadow: 0 0 8px #3b82f6; }

.warning-text { color: #f59e0b; font-weight: bold; }
.danger-text { color: #ef4444; font-weight: bold; text-shadow: 0 0 6px rgba(239,68,68,0.4); }
.tech-text { color: #64ffda; font-weight: bold; font-family: 'Orbitron', monospace; text-shadow: 0 0 6px rgba(100,255,218,0.3);}

.analysis-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.cc-tag { padding: 3px 6px; border: 1px solid; border-radius: 4px; font-size: 0.7rem; background: rgba(0,0,0,0.3); }
.tag-warn { border-color: #f59e0b; color: #f59e0b; }
.tag-safe { border-color: #10b981; color: #10b981; }
.tag-blue { border-color: #3b82f6; color: #60a5fa; }

.control-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 2px; }

/* ================= 左侧：资源矩阵 ================= */
.highlight-panel { border-color: rgba(96, 165, 250, 0.4); box-shadow: 0 0 15px rgba(59, 130, 246, 0.1) inset; }
.res-header { background: linear-gradient(90deg, rgba(59, 130, 246, 0.3) 0%, transparent 100%); border-bottom-color: rgba(96, 165, 250, 0.4); }
.res-live-tag { font-size: 0.65rem; color: #10b981; animation: pulse 1.5s infinite; background: rgba(16,185,129,0.1); padding: 2px 4px; border-radius: 4px;}

.resource-body { padding: 8px; }
.resource-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.res-card { background: rgba(15, 30, 60, 0.5); border: 1px solid rgba(96, 165, 250, 0.2); border-radius: 6px; padding: 8px 4px; display: flex; flex-direction: column; align-items: center; justify-content: center; transition: all 0.2s; }
.res-icon { font-size: 1.6rem; margin-bottom: 4px; }
.res-title { font-size: 0.75rem; font-weight: bold; color: #f8fafc; margin-bottom: 6px; }
.res-divide { width: 50%; height: 2px; background: linear-gradient(90deg, transparent, rgba(96,165,250,0.4), transparent); margin-bottom: 6px; }
.res-data-row { display: flex; width: 100%; justify-content: space-around; }
.r-data { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.r-data span { font-size: 0.65rem; color: #94a3b8; }
.r-data strong { font-size: 1rem; font-family: 'Orbitron', monospace; color: #cbd5e1; line-height: 1;}

.alive-ratio .lbl-row { display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 4px; color: #cbd5e1; }
.progress-bar { height: 5px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; }
.net-info-row { display: flex; gap: 8px; margin-top: 6px; }

/* ================= 中央：视频与指令 ================= */
.task-banner { display: flex; justify-content: space-between; background: rgba(10, 25, 47, 0.8); border: 1px solid #1e3a8a; border-radius: 6px; padding: 6px 15px; }
.tb-item { display: flex; flex-direction: column; gap: 2px; }
.tb-item span { font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; }
.tb-item strong { font-size: 0.85rem; color: #e2e8f0; }

.drone-console { flex: 1; display: flex; flex-direction: column; background: #000; border: 1px solid #1e3a8a; border-radius: 6px; overflow: hidden; min-height: 200px; position: relative; }
.dc-header { position: absolute; top: 0; left: 0; right: 0; padding: 8px 12px; background: linear-gradient(180deg, rgba(0,0,0,0.8) 0%, transparent 100%); display: flex; justify-content: space-between; align-items: center; z-index: 2; }
.title-with-icon { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; font-weight: bold; }
.blink-dot { width: 6px; height: 6px; background: #ef4444; border-radius: 50%; box-shadow: 0 0 6px #ef4444; animation: pulse 1.5s infinite; }
.dc-status { font-size: 0.7rem; color: #64ffda; }
.dc-viewport { flex: 1; position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.video-feed { width: 100%; height: 100%; object-fit: contain; }
.no-signal { text-align: center; color: #475569; }
.signal-icon { font-size: 2.5rem; margin-bottom: 5px; opacity: 0.5; }
.rec-badge { position: absolute; top: 10px; right: 10px; background: rgba(239,68,68,0.9); color: white; padding: 3px 6px; border-radius: 3px; font-size: 0.7rem; font-weight: bold; animation: pulse 1s infinite; z-index: 2;}

.hud-overlay { position: absolute; width: 20px; height: 20px; border: 2px solid #60a5fa; z-index: 2; opacity: 0.5; }
.top-left { top: 15px; left: 15px; border-right: none; border-bottom: none; }
.top-right { top: 15px; right: 15px; border-left: none; border-bottom: none; }
.bottom-left { bottom: 15px; left: 15px; border-right: none; border-top: none; }
.bottom-right { bottom: 15px; right: 15px; border-left: none; border-top: none; }

.dc-controls { padding: 6px; background: rgba(10, 25, 47, 0.9); border-top: 1px solid #1e3a8a; display: flex; gap: 8px; justify-content: center; }

/* 缩小日志高度 */
.log-panel { height: 120px; flex-shrink: 0; }
.log-count { float: right; font-size: 0.7rem; color: #94a3b8; font-weight: normal; }
.log-viewport { flex: 1; overflow-y: auto; padding: 6px 8px; background: rgba(0,0,0,0.3); border-radius: 4px; font-family: 'Consolas', monospace; font-size: 0.7rem; }
.log-row { margin-bottom: 2px; line-height: 1.2; border-bottom: 1px dashed rgba(255,255,255,0.05); padding-bottom: 2px; }
.log-time { color: #64ffda; margin-right: 6px; }

/* ================= 右侧：节点详情 (同一行左右对齐，垂直向下排列) ================= */
.node-card { cursor: pointer; transition: 0.2s; display: flex; flex-direction: column;}
.node-card:hover { border-color: #60a5fa; box-shadow: 0 0 12px rgba(96,165,250,0.3); }
.node-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.node-header h3 { margin: 0; font-size: 0.8rem; color: #e2e8f0; }
.node-header small { color: #94a3b8; font-size: 0.65rem;}
.node-status { font-size: 0.6rem; padding: 2px 4px; border-radius: 3px; background: rgba(239,68,68,0.2); color: #ef4444; }
.node-status.online { background: rgba(16,185,129,0.2); color: #10b981; }
.node-status.tech.online { background: rgba(59,130,246,0.2); color: #60a5fa; }

/* 容器：Flex垂直排布 */
.dashboard-grid { 
  display: flex; 
  flex-direction: column; 
  gap: 4px; 
  padding: 8px 10px; 
}

/* 子元素：Flex水平排布，标签在左，数值在右 */
.n-box { 
  background: rgba(0,0,0,0.3); 
  border: 1px solid rgba(255,255,255,0.02); 
  border-radius: 4px; 
  padding: 5px 10px; 
  display: flex; 
  flex-direction: row; 
  align-items: center; 
  justify-content: space-between; 
}

/* 取消原有的宽列设定，因为现在是一行一个 */
.wide-box { }

.n-lbl { font-size: 0.7rem; color: #94a3b8; margin-bottom: 0; }
.n-val { font-size: 0.85rem; color: #f8fafc; font-family: 'Orbitron', monospace; line-height: 1; }
.n-val small { font-size: 0.65rem; margin-left: 4px; color: #64748b; font-family: sans-serif; }

/* 极限压缩底部的系统状态栏高度 */
.sys-status-panel { padding: 6px 10px; display: flex; flex-direction: column; justify-content: center; }
.sys-grid { display: flex; flex-direction: column; gap: 4px; }
.s-row { display: flex; justify-content: space-between; font-size: 0.7rem; padding-bottom: 2px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.s-row:last-child { border-bottom: none; padding-bottom: 0; }
.s-row span { color: #94a3b8; }
.s-row b { font-family: monospace; color: #e2e8f0; }
.s-row .ok { color: #10b981; }
.s-row .err { color: #ef4444; }

/* 按钮及动画 */
.cc-btn { padding: 4px 8px; border: none; border-radius: 3px; font-size: 0.7rem; font-weight: bold; cursor: pointer; transition: all 0.2s; }
.btn-primary { background: #3b82f6; color: white; }
.btn-danger { background: #ef4444; color: white; }
.btn-tech { background: rgba(16,185,129,0.2); color: #10b981; border: 1px solid #10b981; }
.btn-ghost { background: rgba(255,255,255,0.05); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1); }
.btn-active { background: rgba(96,165,250,0.2); color: #60a5fa; border: 1px solid #60a5fa; animation: pulse 2s infinite; }
.cc-btn:disabled { opacity: 0.5; cursor: not-allowed; filter: grayscale(1); }

@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

/* 响应式降级 */
@media (max-width: 1400px) { 
  .cc-main { grid-template-columns: 2.8fr 4.2fr 3.0fr; } 
}
</style>