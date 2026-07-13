<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { setGatewaySampling } from '../gateway-api'
import { buildGatewayApiUrl, buildGatewayVideoUrl } from '../gateway-config'
import { store } from '../store.js'
// 当前任务态势
const taskStatus = ref({
  name: '环境风险巡检任务',
  id: 'TASK-20260710-001',
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
  <div class="dashboard-container">
    <h1 class="page-title">协同指挥中心</h1>

    <div class="top-section">
      <div class="decision-panel" :class="systemState.level">
        <div class="status-header">
          <div class="status-main-row">
            <div class="status-icon">
              {{ systemState.level === 'danger' ? '▲' : (systemState.level === '!' ? '!' : '●') }}
            </div>
            <div class="status-text">

<h2>{{ gatewayHeadline }}</h2>

<p>
  多源感知协同系统运行状态
</p>


<div class="status-mini-row">

<span>
计算:
<b :class="store.gatewayOnline?'ok':'bad'">
{{store.gatewayOnline?'正常':'异常'}}
</b>
</span>


<span>
采集:
<b :class="store.samplingRunning?'ok':'bad'">
{{store.samplingRunning?'运行':'停止'}}
</b>
</span>


<span>
链路:
<b :class="store.connected?'ok':'bad'">
{{store.connected?'在线':'断开'}}
</b>
</span>


<span>
视频:
<b :class="store.videoOnline?'ok':'bad'">
{{store.videoOnline?'在线':'离线'}}
</b>
</span>

</div>


</div>
            <div class="edge-status-row">


<span>
计算:
<b>
{{store.gatewayOnline?'正常':'异常'}}
</b>
</span>


<span>
采集:
<b>
{{store.samplingRunning?'运行':'停止'}}
</b>
</span>


<span>
链路:
<b>
{{store.connected?'在线':'断开'}}
</b>
</span>


<span>
视频:
<b>
{{store.videoOnline?'在线':'离线'}}
</b>
</span>


</div>
          </div>
          <div class="status-actions">
            <button class="ctrl-link-btn" :class="store.samplingRunning ? 'btn-stop' : 'btn-start'" @click="toggleSampling">
              {{ store.samplingRunning ? '停止采集' : '开始采集' }}
            </button>
            <button class="link-btn" @click="$router.push('/logic')">查看协同关系 →</button>
          </div>
        </div>
        <div class="task-overview">


<div class="task-title">
当前任务态势
</div>


<div class="task-content">


<div>
<span>任务名称</span>
<b>{{taskStatus.name}}</b>
</div>


<div>
<span>任务状态</span>
<b class="green">
{{taskStatus.state}}
</b>
</div>


<div>
<span>执行单元</span>
<b>
{{taskStatus.units}}
</b>
</div>


<div>
<span>覆盖区域</span>
<b>
{{taskStatus.area}}
</b>
</div>


</div>


</div>
        <div class="logic-grid" style="margin-top: 30px;">
          <div class="logic-item">
            <div class="bar-label"><span>早期预警 (TVOC/温)</span><span class="val">{{ maxVals.temp }}°C</span></div>
            <div class="logic-bar"><div class="fill" :style="{ width: Math.min((maxVals.temp / 80) * 100, 100) + '%', background: '#ecc94b' }"></div></div>
          </div>
          <div class="logic-item">
            <div class="bar-label"><span>火灾确认 (烟雾/CO)</span><span class="val">{{ maxVals.smoke }} ug</span></div>
            <div class="logic-bar"><div class="fill" :style="{ width: Math.min((maxVals.smoke / 1000000) * 100, 100) + '%', background: '#f56565' }"></div></div>
          </div>
        </div>

        <div class="logic-footer">
          <span class="mini-tag">态势分析: <b :style="{ color: spreadAnalysis.color }">{{ spreadAnalysis.msg }}</b></span>
          <span class="mini-tag">环境状态: <b :style="{ color: envAnalysis.isInterference ? '#3182ce' : '#718096' }">{{ envAnalysis.msg }}</b></span>
          <span class="mini-tag">
资源状态:
<b>可调度</b>
</span>


<span class="mini-tag">
任务模式:
<b>协同巡检</b>
</span>


<span class="mini-tag">
数据链路:
<b>
{{store.connected?'正常':'异常'}}
</b>
</span>
        </div>
      </div>

      <div class="drone-panel">
        <div class="drone-header">
          <h3>空中机动监测点 (UAV) 实时图传</h3>
          <span class="status-indicator">{{ uploadStatus || (isPlaying ? '链路连接中' : videoStatusText) }}</span>
        </div>
        <div class="drone-body">
          <div class="video-container">
            <img v-if="isPlaying" ref="videoElement" :src="videoUrl" class="video-feed" crossorigin="anonymous" />
            <div v-else class="no-signal">无视频链路信号</div>
            <div v-if="isRecording" class="rec-badge">REC</div>
          </div>
          <div class="drone-controls">
            <button @click="togglePlay" class="mini-btn" :class="isPlaying ? 'btn-stop' : 'btn-start'">{{ isPlaying ? '断开图传' : '接管图传' }}</button>
            <button @click="manualSnapshot" :disabled="!isPlaying" class="mini-btn btn-blue">环境信息</button>
            <button @click="toggleAutoCapture" :disabled="!isPlaying" class="mini-btn" :class="isAutoCapturing ? 'btn-active' : 'btn-gray'">{{ isAutoCapturing ? '自动扫描中' : '自动扫描' }}</button>
            <button @click="toggleRecording" :disabled="!isPlaying" class="mini-btn" :class="isRecording ? 'btn-stop' : 'btn-red'">{{ isRecording ? '停止归档' : '录像归档' }}</button>
          </div>
        </div>
      </div>
    </div>

    <div class="resource-overview-panel">
      <div class="ro-header-box">
        <h3 class="ro-title">全局实体资源编队与调度详情</h3>
      </div>
      <div class="ro-grid">

<!-- 边缘计算 -->
<div class="ro-card">
  <div class="ro-card-header">
    <span class="ro-icon">💻</span>
    边缘计算枢纽
  </div>

  <div class="ro-list">

    <div class="ro-item">
      <span class="lbl">链路状态</span>
      <span class="val highlight">
        {{store.gatewayOnline?'在线':'离线'}}
      </span>
    </div>

    <div class="ro-item">
      <span class="lbl">采集周期</span>
      <span class="val blue">
        2Hz
      </span>
    </div>


    <div class="ro-item">
      <span class="lbl">调度模式</span>
      <span class="val">
        协同调度
      </span>
    </div>

  </div>
</div>


<!-- UAV -->
<div class="ro-card">

<div class="ro-card-header">
<span class="ro-icon">🚁</span>
空中机动监测单元
</div>


<div class="ro-list">

<div class="ro-item">
<span class="lbl">资源总量</span>
<span class="val">
17 套
</span>
</div>


<div class="ro-item">
<span class="lbl">可调度</span>
<span class="val highlight">
3 套
</span>
</div>


<div class="ro-item">
<span class="lbl">执行任务</span>
<span class="val blue">
1 套
</span>
</div>


<div class="ro-item">
<span class="lbl">在库资源</span>
<span class="val gray">
14 套
</span>
</div>


<div class="ro-item">
<span class="lbl">任务能力</span>
<span class="val">
空域巡检
</span>
</div>


</div>
</div>

<!-- 视频视觉监测单元 -->

<div class="ro-card">

<div class="ro-card-header">
<span class="ro-icon">📷</span>
视频视觉监测单元
</div>


<div class="ro-list">


<div class="ro-item">
<span class="lbl">摄像资源</span>
<span class="val">
6 路
</span>
</div>


<div class="ro-item">
<span class="lbl">在线监测</span>
<span class="val highlight">
4 路
</span>
</div>


<div class="ro-item">
<span class="lbl">可调度</span>
<span class="val blue">
2 路
</span>
</div>


<div class="ro-item">
<span class="lbl">录像归档</span>
<span class="val">
正常
</span>
</div>


<div class="ro-item">
<span class="lbl">监测能力</span>
<span class="val">
实时视频监测
</span>
</div>


</div>

</div>

<!-- UGV -->

<div class="ro-card">

<div class="ro-card-header">
<span class="ro-icon">🚙</span>
地面机动监测单元
</div>


<div class="ro-list">


<div class="ro-item">
<span class="lbl">资源总量</span>
<span class="val">
12 台
</span>
</div>


<div class="ro-item">
<span class="lbl">可调度</span>
<span class="val highlight">
5 台
</span>
</div>


<div class="ro-item">
<span class="lbl">执行任务</span>
<span class="val blue">
2 台
</span>
</div>


<div class="ro-item">
<span class="lbl">在库资源</span>
<span class="val gray">
5 台
</span>
</div>


<div class="ro-item">
<span class="lbl">任务能力</span>
<span class="val">
近地巡检
</span>
</div>


</div>

</div>




<!-- 气象站 -->

<div class="ro-card">

<div class="ro-card-header">
<span class="ro-icon">🗼</span>
固定气象检测单元
</div>


<div class="ro-list">


<div class="ro-item">
<span class="lbl">部署数量</span>
<span class="val">
8 座
</span>
</div>


<div class="ro-item">
<span class="lbl">在线数量</span>
<span class="val highlight">
8 座
</span>
</div>


<div class="ro-item">
<span class="lbl">可调用</span>
<span class="val blue">
8 座
</span>
</div>


<div class="ro-item">
<span class="lbl">运行状态</span>
<span class="val">
正常
</span>
</div>


<div class="ro-item">
<span class="lbl">任务能力</span>
<span class="val">
气象背景场
</span>
</div>


</div>

</div>


</div>
    </div>
    <div class="capability-panel">
      <div class="panel-header">
        <h3>感知网络与组网效能</h3>
      </div>
      <div class="capability-grid">
        <div class="cap-group">
          <div class="cap-title">通信与链路效能</div>
          <div class="cap-items">
             <div class="cap-item row-flex">
               <span class="c-lbl">网络拓扑结构</span>
               <span class="c-val tag-blue">{{ networkStats.networkType }}</span>
             </div>
             <div class="cap-item row-flex">
               <span class="c-lbl">网内节点存活率</span>
               <div class="progress-wrap">
                 <div class="progress-bar"><div class="progress-fill" :style="{width: networkStats.alivePercent + '%'}"></div></div>
                 <span class="c-val">{{ networkStats.aliveRatio }}</span>
               </div>
             </div>
             <div class="cap-item row-flex">
               <span class="c-lbl">传感吞吐频率</span>
               <span class="c-val highlight">{{ networkStats.throughput }}</span>
             </div>
          </div>
        </div>

        <div class="cap-group">
          <div class="cap-title">多源感知数据态势</div>
          <div class="cap-items data-stats">
            <div class="stat-box">
              <span class="s-lbl">全量感知维度</span>
              <span class="s-val">{{ networkStats.sensingDimensions }} <small>项</small></span>
              <span class="s-desc">温/湿/烟/TVOC/CO/风向/风速</span>
            </div>
            <div class="stat-box">
              <span class="s-lbl">累计数据吞吐量</span>
              <span class="s-val">{{ totalPackets }} <small>包</small></span>
              <span class="s-desc">边缘端实时解析</span>
            </div>
          </div>
        </div>

      </div>
    </div>

    <div class="cards-grid">
      <div class="card env-card" @click="$router.push('/node1')">
        <div class="card-header">
          <h2 class="card-title">机动监测点-001 (UGV)</h2>
          <span class="tag" :class="store.nodes?.node1?.online ? 'tag-online' : 'tag-offline'">
            {{ store.nodes?.node1?.online ? '在线' : '离线' }}
          </span>
        </div>
        <div class="card-body">
          <div class="sensor-list">
            <div class="sensor-inline-item">
              <span class="lbl">温度</span>
              <span class="val">{{ store.data.node1?.temp || 0 }}</span>
            </div>
            <div class="sensor-inline-item">
              <span class="lbl">湿度</span>
              <span class="val">{{ store.data.node1?.hum || 0 }}%</span>
            </div>
            <div class="sensor-inline-item">
              <span class="lbl">烟雾</span>
              <span class="val">{{ store.data.node1?.smoke || 0 }} ug</span>
            </div>
            <div class="sensor-inline-item">
              <span class="lbl">TVOC</span>
              <span class="val">{{ store.data.node1?.tvoc || 0 }}</span>
            </div>
            <div class="sensor-inline-item">
              <span class="lbl">CO</span>
              <span class="val">{{ store.data.node1?.co || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="card-footer">点击查看详情 →</div>
      </div>

      <div class="card env-card" @click="$router.push('/node2')">
        <div class="card-header">
          <h2 class="card-title">机动监测点-002 (UGV)</h2>
          <span class="tag" :class="store.nodes?.node2?.online ? 'tag-online' : 'tag-offline'">
            {{ store.nodes?.node2?.online ? '在线' : '离线' }}
          </span>
        </div>
        <div class="card-body">
          <div class="sensor-list">
            <div class="sensor-inline-item">
              <span class="lbl">温度</span>
              <span class="val">{{ store.data.node2?.temp || 0 }}</span>
            </div>
            <div class="sensor-inline-item">
              <span class="lbl">湿度</span>
              <span class="val">{{ store.data.node2?.hum || 0 }}%</span>
            </div>
            <div class="sensor-inline-item">
              <span class="lbl">烟雾</span>
              <span class="val">{{ store.data.node2?.smoke || 0 }} ug</span>
            </div>
            <div class="sensor-inline-item">
              <span class="lbl">TVOC</span>
              <span class="val">{{ store.data.node2?.tvoc || 0 }}</span>
            </div>
            <div class="sensor-inline-item">
              <span class="lbl">CO</span>
              <span class="val">{{ store.data.node2?.co || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="card-footer">点击查看详情 →</div>
      </div>

      <div class="card weather-card" @click="$router.push('/node3')">
        <div class="card-header">
          <h2 class="card-title">固定气象监测站</h2>
          <span class="tag" :class="store.nodes?.node3?.online ? 'tag-online blue' : 'tag-offline'">
            {{ store.nodes?.node3?.online ? '在线' : '离线' }}
          </span>
        </div>
        <div class="card-body">
          <div class="weather-list">
            <div class="sensor-inline-item highlight-item">
              <span class="lbl">风速 (m/s)</span>
              <span class="val big-val">{{ store.data.node3?.wind || 0 }}</span>
            </div>
            <div class="sensor-inline-item highlight-item">
              <span class="lbl">风向</span>
              <span class="val big-val">{{ store.data.node3?.wind_dir || 0 }}</span>
            </div>
          </div>
          <div class="wind-grade-box">
            <span class="lbl">当前风力等级评估</span>
            <span class="val grade-val">
              {{ (store.data.node3?.wind || 0) > 10.7 ? '强风 (严防扩散)' : ((store.data.node3?.wind || 0) > 5.4 ? '和风' : '微风') }}
            </span>
          </div>
        </div>
        <div class="card-footer">点击查看详情 →</div>
      </div>
    </div>

    <div class="bottom-panel">
      <div class="log-section">
        <div class="log-header">
          <span>实时协同日志</span>
          <span class="count">{{ sysLogs.length }} 条记录</span>
        </div>
        <div class="log-list">
          <div v-for="(log, index) in sysLogs" :key="index" class="log-row" :class="log.type">
            <span class="log-time">[{{ log.time }}]</span>
            <span class="log-msg">{{ log.msg }}</span>
          </div>
        </div>
      </div>

      <div class="system-status-section">
        <div class="sys-item">
          <span class="sys-label">边缘端</span>
          <span class="sys-val" :class="store.gatewayOnline ? 'good' : 'bad'">{{ store.gatewayOnline ? '在线' : '离线' }}</span>
        </div>
        <div class="sys-item">
          <span class="sys-label">数据库</span>
          <span class="sys-val" :class="store.databaseOnline ? 'good' : 'bad'">{{ databaseStatusText }}</span>
        </div>
        <div class="sys-item">
          <span class="sys-label">视频流</span>
          <span class="sys-val" :class="store.videoOnline ? 'good' : 'bad'">{{ videoStatusText }}</span>
        </div>
        <div class="sys-item">
          <span class="sys-label">实时通道</span>
          <span class="sys-val" :class="store.connected ? 'good' : 'bad'">{{ realtimeStatusText }}</span>
        </div>
        <div class="sys-item">
          <span class="sys-label">最近实时包</span>
          <span class="sys-val">{{ lastRealtimeLabel }}</span>
        </div>
      </div>
    </div>

    <canvas ref="canvasElement" style="display: none;"></canvas>
  </div>
</template>
<style scoped>
/* ================= 全局 & 原有页面基础样式 ================= */
.status-mini-row{
  display:flex;
  gap:12px;
  margin-top:6px;
  font-size:0.72rem;
  color:#718096;
}


.status-mini-row b{
  margin-left:3px;
}


.status-mini-row .ok{
  color:#38a169;
}


.status-mini-row .bad{
  color:#e53e3e;
}



.task-overview{

margin-top:15px;
padding:10px;
background:rgba(255,255,255,0.7);
border-radius:8px;
border:1px solid #edf2f7;

}


.task-title{

font-size:0.8rem;
font-weight:bold;
color:#4a5568;
margin-bottom:8px;

}



.task-content{

display:grid;
grid-template-columns:1fr 1fr;
gap:8px;

}



.task-content div{

display:flex;
justify-content:space-between;
font-size:0.72rem;

}


.task-content span{

color:#718096;

}


.task-content b{

color:#2d3748;

}


.task-content .green{

color:#38a169;

}
.dashboard-container { padding: 15px 25px; max-width: 1600px; margin: 0 auto; height: 100vh; display: flex; flex-direction: column; overflow-y: auto; }
.page-title { color: #2c3e50; margin: 0 0 10px 0; font-weight: 700; font-size: 1.3rem; }

/* 优化：去掉固定的 height: 240px，改为 height: auto 让内容自然撑开，保留 min-height */
.top-section { display: flex; gap: 15px; margin-bottom: 15px; min-height: 240px; height: auto; flex-shrink: 0; }

/* 全局公用标签与文本属性 */
.lbl { font-size: 0.75rem; color: #909399; margin-bottom: 2px; }
.val { font-size: 0.95rem; font-weight: bold; color: #2c3e50; }

/* ================= 决策与状态面板 ================= */
.decision-panel { flex: 5; background: white; border-radius: 10px; padding: 12px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 4px solid #ccc; }
.decision-panel.success { border-left-color: #48bb78; background: #f0fff4; }
.decision-panel.warning { border-left-color: #ecc94b; background: #fffff0; }
.decision-panel.danger { border-left-color: #f56565; background: #fff5f5; }

.status-header { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 8px; }
.status-main-row { display: flex; align-items: center; min-width: 0; }
.status-icon { font-size: 1.8rem; margin-right: 10px; }
.status-text h2 { margin: 0; font-size: 1.1rem; color: #2d3748; }
.status-text p { margin: 0; font-size: 0.75rem; color: #718096; }
.status-actions { display: flex; align-items: center; gap: 8px; }

.link-btn, .ctrl-link-btn { border: 1px solid #dcdfe6; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem; cursor: pointer; transition: 0.2s; }
.link-btn { background: none; color: #606266; }
.link-btn:hover { color: #409eff; border-color: #409eff; background: #ecf5ff; }
.ctrl-link-btn { color: white; border-color: transparent; }

.gateway-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 10px; }
.gateway-pill { padding: 10px 12px; border-radius: 8px; background: rgba(255,255,255,0.7); border: 1px solid rgba(0,0,0,0.05); display: flex; flex-direction: column; gap: 4px; }
.gateway-pill.wide { grid-column: span 1; }
.gateway-pill span { font-size: 0.72rem; color: #718096; }
.gateway-pill strong { font-size: 0.85rem; color: #2d3748; }

.logic-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.logic-item { font-size: 0.8rem; }
.bar-label { display: flex; justify-content: space-between; margin-bottom: 3px; color: #4a5568; font-weight: bold; }
.logic-bar { height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
.fill { height: 100%; transition: width 0.5s ease; }
.logic-footer { display: flex; gap: 10px; margin-top: auto; flex-wrap: wrap; }
.mini-tag { background: rgba(255,255,255,0.7); padding: 1px 6px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.05); font-size: 0.75rem; color: #4a5568; }

/* ================= 无人机面板 ================= */
.drone-panel { flex: 4; background: white; border-radius: 10px; padding: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); display: flex; flex-direction: column; }
.drone-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 0.9rem; font-weight: bold; color: #2c3e50; }
.status-indicator { font-size: 0.7rem; color: #718096; font-weight: normal; }
.drone-body { flex: 1; display: flex; gap: 8px; min-height: 0; }
.video-container { flex: 3; background: #000; border-radius: 5px; overflow: hidden; position: relative; display: flex; align-items: center; justify-content: center; }
.video-feed { width: 100%; height: 100%; object-fit: contain; }
.no-signal { color: #555; font-size: 0.8rem; }
.rec-badge { position: absolute; top: 5px; right: 5px; background: rgba(220, 38, 38, 0.9); color: white; padding: 1px 4px; border-radius: 3px; font-size: 0.6rem; animation: pulse 1s infinite; }
.drone-controls { flex: 1; display: flex; flex-direction: column; gap: 5px; justify-content: center; }
.mini-btn { padding: 4px 0; border: none; border-radius: 4px; font-size: 0.7rem; cursor: pointer; color: white; transition: 0.2s; }
.btn-start { background: #48bb78; }
.btn-stop { background: #e53e3e; }
.btn-blue { background: #3182ce; }
.btn-red { background: #e53e3e; }
.btn-gray { background: #e2e8f0; color: #666; }
.btn-active { background: #3182ce; animation: pulse 2s infinite; }
.mini-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ================= 全局实体资源编队与调度详情 (新增补齐样式) ================= */
.resource-overview-panel { background: #fff; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #eee; display: flex; flex-direction: column; flex-shrink: 0; }
.ro-header-box { padding: 10px 15px; background: #f8f9fa; border-bottom: 1px solid #eee; border-radius: 10px 10px 0 0; }
.ro-title { margin: 0; font-size: 0.95rem; color: #2c3e50; font-weight: bold; border-left: 3px solid #3182ce; padding-left: 8px; }
.ro-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; padding: 15px; }
.ro-card { background: #f9fafc; border: 1px solid #e2e8f0; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; }
.ro-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-color: #cbd5e0; }
.ro-card-header { background: #edf2f7; padding: 8px 12px; font-size: 0.85rem; font-weight: bold; color: #2d3748; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; gap: 8px; }
.ro-icon { font-size: 1.1rem; }
.ro-list { padding: 12px; display: flex; flex-direction: column; gap: 8px; }
.ro-item { display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; border-bottom: 1px dashed #edf2f7; padding-bottom: 4px; }
.ro-item:last-child { border-bottom: none; padding-bottom: 0; }
.ro-item .lbl { color: #718096; }
.ro-item .val { font-weight: bold; color: #2d3748; }
.ro-item .val.highlight { color: #38a169; }
.ro-item .val.blue { color: #3182ce; }
.ro-item .val.green { color: #48bb78; }
.ro-item .val.gray { color: #a0aec0; }

/* ================= 实体资源与效能状态 ================= */
.flex-1 { flex: 1; }
.capability-panel { background: #fff; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #eee; display: flex; flex-direction: column; flex-shrink: 0; }
.panel-header { padding: 10px 15px; background: #f8f9fa; border-bottom: 1px solid #eee; border-radius: 10px 10px 0 0; }
.panel-header h3 { margin: 0; font-size: 0.95rem; color: #2c3e50; font-weight: bold; }
.capability-grid { display: grid; grid-template-columns: 1.3fr 1fr; gap: 20px; padding: 15px; }
.cap-group { display: flex; flex-direction: column; gap: 10px; }
.cap-title { font-size: 0.8rem; color: #718096; font-weight: bold; border-left: 3px solid #3182ce; padding-left: 8px; margin-bottom: 4px; }
.cap-items { display: flex; flex-direction: column; gap: 8px; }
.cap-item { background: #f9fafc; border: 1px solid #f0f2f5; border-radius: 6px; padding: 8px 12px; }
.row-flex { display: flex; justify-content: space-between; align-items: center; }
.c-lbl { font-size: 0.75rem; color: #4a5568; }
.c-val { font-size: 0.85rem; color: #2d3748; font-weight: bold; }
.tag-blue { background: #ebf8ff; color: #3182ce; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; }
.highlight { color: #38a169; }
.progress-wrap { display: flex; align-items: center; gap: 8px; width: 120px; }
.progress-bar { flex: 1; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: #48bb78; transition: width 0.3s; }

.data-stats { flex-direction: row; height: 100%; }
.stat-box { flex: 1; background: #f0f4f8; border-radius: 6px; padding: 10px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #e2e8f0; }
.s-lbl { font-size: 0.75rem; color: #718096; margin-bottom: 4px; }
.s-val { font-size: 1.4rem; color: #2b6cb0; font-weight: bold; line-height: 1.2; }
.s-val small { font-size: 0.8rem; color: #4a5568; font-weight: normal; }
.s-desc { font-size: 0.7rem; color: #a0aec0; margin-top: 4px; }

/* ================= 传感器卡片模块 ================= */
.cards-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
  gap: 20px; 
  margin-bottom: 15px; 
  flex-shrink: 0; 
  font-size: 16px; 
}

/* 优化：将原有的 .node-card 与 .card 合并，防止 HTML 与 CSS 类名不匹配 */
.card, .node-card { 
  background: white; 
  border-radius: 12px; 
  box-shadow: 0 4px 12px rgba(0,0,0,0.08); 
  cursor: pointer; 
  transition: transform 0.2s, box-shadow 0.2s; 
  border: 1px solid #eee; 
  display: flex; 
  flex-direction: column; 
}
.card:hover, .node-card:hover { 
  transform: translateY(-5px); 
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  border-color: #42b983; 
}

.env-card { border-top: 5px solid #4CAF50; }
.weather-card { 
  background: linear-gradient(145deg, #f0f7ff 0%, #e6f0fa 100%); 
  border-top: 5px solid #2196F3; 
}

.card-header { 
  padding: 12px 15px; 
  background: #f8f9fa; 
  border-bottom: 1px solid #eee; 
  border-radius: 11px 11px 0 0; 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
}
.card-title { margin: 0; font-size: 1.6rem; color: #333; font-weight: bold; }

.tag { padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: bold; }
.tag-online { background: #e6fffa; color: #38a169; }
.tag-online.blue { background: #ebf8ff; color: #3182ce; }
.tag-offline { background: #fff5f5; color: #e53e3e; }

.card-body { padding: 15px; flex: 1; }
.sensor-list { display: flex; flex-direction: column; gap: 12px; }

.sensor-inline-item {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 1.35rem; background: rgba(0,0,0,0.02); padding: 12px 15px; border-radius: 8px;
}
.sensor-inline-item .lbl { color: #666; font-weight: 500; margin-bottom: 0; font-size: inherit; }
.sensor-inline-item .val { color: #222; font-weight: bold; font-size: inherit; }

.weather-list { display: flex; flex-direction: column; gap: 16px; margin-bottom: 16px; }
.weather-card .highlight-item { background: #ffffff; box-shadow: 0 2px 6px rgba(33, 150, 243, 0.1); }
.weather-card .big-val { font-size: 1.5rem; color: #1976D2; }

.wind-grade-box {
  display: flex; justify-content: space-between; align-items: center;
  background-color: #1976D2; color: white; padding: 12px 15px; border-radius: 8px; font-size: 1.35rem; 
}
.wind-grade-box .lbl { color: rgba(255,255,255,0.9); margin-bottom: 0; font-size: inherit;}
.wind-grade-box .grade-val { font-weight: bold; font-size: 1.45rem; }

.card-footer { padding: 10px 15px; font-size: 0.9rem; color: #999; text-align: right; border-top: 1px solid #eee; margin-top: auto; }
.card:hover .card-footer, .node-card:hover .card-footer { color: #2196F3; }

/* ================= 底部日志与系统面板 ================= */
.bottom-panel { background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); display: flex; gap: 20px; padding: 15px; border: 1px solid #eee; height: 180px; flex-shrink: 0; margin-bottom: 20px; }
.log-section { flex: 3; display: flex; flex-direction: column; }
.log-header { font-size: 0.85rem; font-weight: bold; color: #4a5568; margin-bottom: 8px; display: flex; justify-content: space-between; }
.log-header .count { font-weight: normal; color: #a0aec0; }
.log-list { flex: 1; background: #1e1e1e; border-radius: 6px; overflow-y: auto; padding: 8px; font-family: 'Consolas', monospace; font-size: 0.75rem; }
.log-row { margin-bottom: 4px; color: #d4d4d4; }
.log-time { color: #569cd6; margin-right: 8px; }
.log-row.success .log-msg { color: #6a9955; }
.log-row.warning .log-msg { color: #dcdcaa; }
.log-row.danger .log-msg { color: #f44747; }
.log-row.info .log-msg { color: #9cdcfe; }

.system-status-section { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 12px; border-left: 1px solid #eee; padding-left: 20px; }
.sys-item { display: flex; align-items: center; justify-content: space-between; gap: 10px; font-size: 0.8rem; color: #4a5568; }
.sys-label { flex: 0 0 72px; }
.sys-val { text-align: right; font-weight: bold; font-size: 0.76rem; color: #2d3748; }
.sys-val.good { color: #48bb78; }
.sys-val.bad { color: #e53e3e; }

/* ================= 动画与响应式 ================= */
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }

@media (max-width: 1200px) {
  .top-section { height: auto; flex-direction: column; }
  .decision-panel, .drone-panel { width: 100%; height: auto; }
  .drone-body { height: 200px; }
  .capability-grid { grid-template-columns: 1fr; }
  .ro-grid { grid-template-columns: repeat(2, 1fr); } /* 在中等屏幕变为两列 */
  .cards-grid { grid-template-columns: 1fr; }
  .bottom-panel { flex-direction: column; height: auto; }
  .system-status-section { border-left: none; padding-left: 0; border-top: 1px solid #eee; padding-top: 15px; }
  .gateway-strip { grid-template-columns: 1fr 1fr; }
}

@media (max-width: 768px) {
  .ro-grid { grid-template-columns: 1fr; } /* 在手机端变为一列 */
}
</style>