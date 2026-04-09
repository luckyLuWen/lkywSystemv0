<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { store } from '../store.js'

// ==========================================
// Part A: 传感器融合决策逻辑
// ==========================================
const THRESHOLDS = {
  TEMP_WARN: 50.0,
  TVOC_WARN: 2.0,
  SMOKE_ALARM: 600000, 
  CO_ALARM: 50,
  WIND_SPREAD: 5.0,
  HUM_INTERFERENCE: 80
}

const maxVals = computed(() => {
  const n1 = store.data.node1
  const n2 = store.data.node2
  return {
    temp: Math.max(n1.temp, n2.temp),
    hum: Math.max(n1.hum, n2.hum),
    smoke: Math.max(n1.smoke, n2.smoke),
    tvoc: Math.max(n1.tvoc, n2.tvoc),
    co: Math.max(n1.co, n2.co)
  }
})

const fireStatus = computed(() => {
  if (maxVals.value.smoke > THRESHOLDS.SMOKE_ALARM || maxVals.value.co > THRESHOLDS.CO_ALARM) {
    return { active: true, msg: '🔥 确认火灾警情', level: 'danger' }
  }
  return { active: false }
})

const warningStatus = computed(() => {
  if (fireStatus.value.active) return { active: false }
  if (maxVals.value.temp > THRESHOLDS.TEMP_WARN || maxVals.value.tvoc > THRESHOLDS.TVOC_WARN) {
    return { active: true, msg: '⚠️ 早期隐患预警', level: 'warning' }
  }
  return { active: false }
})

const spreadAnalysis = computed(() => {
  const wind = store.data.node3.wind
  if (wind > THRESHOLDS.WIND_SPREAD) return { msg: '💨 扩散风险高', color: '#e53e3e' }
  return { msg: '🍃 风势平稳', color: '#38a169' }
})

const envAnalysis = computed(() => {
  if (maxVals.value.hum > THRESHOLDS.HUM_INTERFERENCE) return { isInterference: true, msg: '💧 高湿干扰' }
  return { isInterference: false, msg: '☀️ 环境干燥' }
})

const systemState = computed(() => {
  if (fireStatus.value.active) return fireStatus.value
  if (warningStatus.value.active) return warningStatus.value
  return { msg: '✅ 系统正常运行', level: 'success' }
})

// ==========================================
// Part B: 无人机视频 & 录像逻辑
// ==========================================
const PYTHON_STREAM_URL = 'http://localhost:8000/api/video_feed'
const API_BASE = 'http://localhost:8000/api'

const videoElement = ref(null)
const canvasElement = ref(null)
const isPlaying = ref(false)
const videoUrl = ref('')
const isRecording = ref(false)
const isAutoCapturing = ref(false)
const uploadStatus = ref('') 

const sysLogs = ref([
  { time: new Date().toLocaleTimeString(), type: 'info', msg: '系统初始化完成，等待指令...' }
])

const addLog = (msg, type = 'info') => {
  const time = new Date().toLocaleTimeString()
  sysLogs.value.unshift({ time, type, msg })
  if (sysLogs.value.length > 50) sysLogs.value.pop()
}

let lastAlertTime = 0
watch(fireStatus, (newVal) => {
  if (newVal.active && Date.now() - lastAlertTime > 5000) {
    addLog(`系统自动告警: ${newVal.msg}`, 'danger')
    lastAlertTime = Date.now()
  }
})

let mediaRecorder = null
let recordedChunks = []
let captureTimer = null
let drawFrameId = null

const togglePlay = () => {
  if (isPlaying.value) {
    videoUrl.value = ''
    isPlaying.value = false
    addLog('视频流连接已断开', 'warning')
    stopAllActions()
  } else {
    videoUrl.value = `${PYTHON_STREAM_URL}?t=${Date.now()}` 
    isPlaying.value = true
    addLog('视频流连接建立成功', 'success')
  }
}

const stopAllActions = () => {
  if (isAutoCapturing.value) {
    isAutoCapturing.value = false
    clearInterval(captureTimer)
    addLog('自动抓拍任务已停止')
  }
  if (isRecording.value) stopRecording()
}

const manualSnapshot = () => captureAndUpload('手动')

const toggleAutoCapture = () => {
  isAutoCapturing.value = !isAutoCapturing.value
  if (isAutoCapturing.value) {
    captureTimer = setInterval(() => captureAndUpload('自动'), 500)
    addLog('开启自动连续抓拍 (0.5s/张)', 'info')
  } else {
    clearInterval(captureTimer)
    addLog('停止自动抓拍', 'info')
  }
}

const captureAndUpload = async (type) => {
  if (!videoElement.value || !canvasElement.value) return
  const ctx = canvasElement.value.getContext('2d')
  if (videoElement.value.naturalWidth === 0) return

  canvasElement.value.width = videoElement.value.naturalWidth
  canvasElement.value.height = videoElement.value.naturalHeight
  ctx.drawImage(videoElement.value, 0, 0)

  try {
    const dataUrl = canvasElement.value.toDataURL('image/jpeg', 0.8)
    await fetch(`${API_BASE}/save_drone_image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataUrl })
    })
    
    if (type === '手动') {
      uploadStatus.value = `📸 已存: ${new Date().toLocaleTimeString()}.jpg`
      addLog(`手动抓拍成功，已同步传感器数据`, 'success')
      setTimeout(() => { if(!isRecording.value) uploadStatus.value = '' }, 2000)
    } 
  } catch (e) {
    addLog(`抓拍失败: ${e.message}`, 'danger')
  }
}

const toggleRecording = () => {
  if (isRecording.value) stopRecording()
  else startRecording()
}

const startRecording = () => {
  if (!videoElement.value || !canvasElement.value) return
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
  
  mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data) }
  mediaRecorder.onstop = uploadVideo
  mediaRecorder.start()
  
  uploadStatus.value = '⏺️ 正在录像...'
  addLog('开始实时录像任务', 'info')
}

const stopRecording = () => {
  if (mediaRecorder) mediaRecorder.stop()
  cancelAnimationFrame(drawFrameId)
  isRecording.value = false
  addLog('录像结束，正在封包上传...', 'warning')
}

const uploadVideo = async () => {
  uploadStatus.value = '⏳ 上传中...'
  const blob = new Blob(recordedChunks, { type: 'video/webm' })
  const formData = new FormData()
  formData.append('file', blob, 'record.webm')

  try {
    const res = await fetch(`${API_BASE}/save_drone_video`, { method: 'POST', body: formData })
    const data = await res.json()
    if (data.status === 'success') {
        uploadStatus.value = '✅ 录像已归档'
        addLog(`录像归档成功: ${data.path}`, 'success')
    } else {
        uploadStatus.value = '❌ 失败'
        addLog('录像上传失败', 'danger')
    }
  } catch (e) {
    uploadStatus.value = '❌ 网络错误'
    addLog('录像上传网络异常', 'danger')
  }
  setTimeout(() => uploadStatus.value = '', 3000)
}

onBeforeUnmount(() => {
  stopAllActions()
})
</script>

<template>
  <div class="dashboard-container">
    <h1 class="page-title">📊 协同指挥中心</h1>

    <div class="top-section">
      <div class="decision-panel" :class="systemState.level">
        <div class="status-header">
          <div class="status-main-row">
            <div class="status-icon">
              {{ systemState.level === 'danger' ? '🚨' : (systemState.level === 'warning' ? '⚡' : '🛡️') }}
            </div>
            <div class="status-text">
              <h2>{{ systemState.msg }}</h2>
              <p>多传感器融合判定</p>
            </div>
          </div>
          <button class="link-btn" @click="$router.push('/logic')">查看逻辑图谱 ➔</button>
        </div>

        <div class="logic-grid">
          <div class="logic-item">
            <div class="bar-label"><span>早期预警</span><span class="val">{{ maxVals.temp }}℃</span></div>
            <div class="logic-bar"><div class="fill" :style="{ width: Math.min((maxVals.temp / 80) * 100, 100) + '%', background: '#ecc94b' }"></div></div>
          </div>
          <div class="logic-item">
            <div class="bar-label"><span>火灾确证</span><span class="val">{{ maxVals.smoke }} ug</span></div>
            <div class="logic-bar"><div class="fill" :style="{ width: Math.min((maxVals.smoke / 1000000) * 100, 100) + '%', background: '#f56565' }"></div></div>
          </div>
        </div>
        <div class="logic-footer">
          <span class="mini-tag">态势: <b :style="{ color: spreadAnalysis.color }">{{ spreadAnalysis.msg }}</b></span>
          <span class="mini-tag">环境: <b :style="{ color: envAnalysis.isInterference ? '#3182ce' : '#718096' }">{{ envAnalysis.msg }}</b></span>
        </div>
      </div>

      <div class="drone-panel">
        <div class="drone-header">
          <h3>🚁 实时侦查</h3>
          <span class="status-indicator">{{ uploadStatus || (isPlaying ? '实时图传中' : '等待连接') }}</span>
        </div>
        <div class="drone-body">
          <div class="video-container">
            <img v-if="isPlaying" ref="videoElement" :src="videoUrl" class="video-feed" crossorigin="anonymous" />
            <div v-else class="no-signal">📶 无信号</div>
            <div v-if="isRecording" class="rec-badge">REC</div>
          </div>
          <div class="drone-controls">
            <button @click="togglePlay" class="mini-btn" :class="isPlaying ? 'btn-stop' : 'btn-start'">{{ isPlaying ? '断开' : '连接' }}</button>
            <button @click="manualSnapshot" :disabled="!isPlaying" class="mini-btn btn-blue">抓拍</button>
            <button @click="toggleAutoCapture" :disabled="!isPlaying" class="mini-btn" :class="isAutoCapturing ? 'btn-active' : 'btn-gray'">{{ isAutoCapturing ? '自动中' : '自动' }}</button>
            <button @click="toggleRecording" :disabled="!isPlaying" class="mini-btn" :class="isRecording ? 'btn-stop' : 'btn-red'">{{ isRecording ? '停止' : '录像' }}</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="cards-grid">
      <div class="card node-card" @click="$router.push('/node1')">
        <div class="card-header"><h3>📍 无人车 A</h3><span class="tag">在线</span></div>
        <div class="card-body">
          <div class="sensor-grid">
            <div class="sensor-item"><span class="lbl">🌡️ 温度</span><span class="val">{{ store.data.node1.temp }}</span></div>
            <div class="sensor-item"><span class="lbl">💧 湿度</span><span class="val">{{ store.data.node1.hum }}%</span></div>
            <div class="sensor-item full-width"><span class="lbl">🌫️ 烟雾</span><span class="val">{{ store.data.node1.smoke }} ug</span></div>
            <div class="sensor-item"><span class="lbl">🧪 TVOC</span><span class="val">{{ store.data.node1.tvoc }}</span></div>
            <div class="sensor-item"><span class="lbl">⚠️ CO</span><span class="val">{{ store.data.node1.co }}</span></div>
          </div>
        </div>
        <div class="card-footer">点击查看详情 -></div>
      </div>

      <div class="card node-card" @click="$router.push('/node2')">
        <div class="card-header"><h3>📍 无人车 B</h3><span class="tag">在线</span></div>
        <div class="card-body">
          <div class="sensor-grid">
            <div class="sensor-item"><span class="lbl">🌡️ 温度</span><span class="val">{{ store.data.node2.temp }}</span></div>
            <div class="sensor-item"><span class="lbl">💧 湿度</span><span class="val">{{ store.data.node2.hum }}%</span></div>
            <div class="sensor-item full-width"><span class="lbl">🌫️ 烟雾</span><span class="val">{{ store.data.node2.smoke }} ug</span></div>
            <div class="sensor-item"><span class="lbl">🧪 TVOC</span><span class="val">{{ store.data.node2.tvoc }}</span></div>
            <div class="sensor-item"><span class="lbl">⚠️ CO</span><span class="val">{{ store.data.node2.co }}</span></div>
          </div>
        </div>
        <div class="card-footer">点击查看详情 -></div>
      </div>

      <div class="card node-card" @click="$router.push('/node3')">
        <div class="card-header"><h3>📍 固定杆</h3><span class="tag" style="background:#ebf8ff;color:#3182ce;">在线</span></div>
        <div class="card-body">
          <div class="sensor-grid two-rows">
            <div class="sensor-item large-item">
              <span class="lbl">🌬️ 风速 (m/s)</span>
              <span class="val big-val">{{ store.data.node3.wind }}</span>
            </div>
            <div class="sensor-item large-item">
              <span class="lbl">🧭 风向</span>
              <span class="val big-val">{{ store.data.node3.wind_dir }}</span>
            </div>
          </div>
          <div class="wind-grade">
            等级: {{ store.data.node3.wind > 10.7 ? '强风' : (store.data.node3.wind > 5.4 ? '和风' : '微风') }}
          </div>
        </div>
        <div class="card-footer">点击查看详情 -></div>
      </div>
    </div>

    <div class="bottom-panel">
      <div class="log-section">
        <div class="log-header">
          <span>📝 实时协同日志</span>
          <span class="count">{{ sysLogs.length }} 条记录</span>
        </div>
        <div class="log-list">
          <div v-for="(log, i) in sysLogs" :key="i" class="log-row" :class="log.type">
            <span class="log-time">[{{ log.time }}]</span>
            <span class="log-msg">{{ log.msg }}</span>
          </div>
        </div>
      </div>
      <div class="system-status-section">
        <div class="sys-item">
          <span class="sys-label">💾 存储</span>
          <div class="sys-bar"><div class="sys-fill" style="width: 45%"></div></div>
          <span class="sys-val">45%</span>
        </div>
        <div class="sys-item">
          <span class="sys-label">🧠 负载</span>
          <div class="sys-bar"><div class="sys-fill warn" style="width: 12%"></div></div>
          <span class="sys-val">12%</span>
        </div>
        <div class="sys-item">
          <span class="sys-label">📡 延迟</span>
          <span class="sys-val good">14ms</span>
        </div>
      </div>
    </div>

    <canvas ref="canvasElement" style="display: none;"></canvas>
  </div>
</template>

<style scoped>
.dashboard-container { padding: 15px 25px; max-width: 1600px; margin: 0 auto; height: 100vh; display: flex; flex-direction: column; overflow-y: auto; }
.page-title { color: #2c3e50; margin: 0 0 10px 0; font-weight: 700; font-size: 1.3rem; }

/* === Top Section === */
.top-section { display: flex; gap: 15px; margin-bottom: 15px; height: 200px; min-height: 200px; flex-shrink: 0; }

.decision-panel { flex: 5; background: white; border-radius: 10px; padding: 12px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 4px solid #ccc; }
.decision-panel.success { border-left-color: #48bb78; background: #f0fff4; }
.decision-panel.warning { border-left-color: #ecc94b; background: #fffff0; }
.decision-panel.danger { border-left-color: #f56565; background: #fff5f5; }

/* Header with Link Button */
.status-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; }
.status-main-row { display: flex; align-items: center; }
.status-icon { font-size: 1.8rem; margin-right: 10px; }
.status-text h2 { margin: 0; font-size: 1.1rem; color: #2d3748; }
.status-text p { margin: 0; font-size: 0.75rem; color: #718096; }

.link-btn { 
  background: none; border: 1px solid #dcdfe6; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem; color: #606266; cursor: pointer; transition: 0.2s;
}
.link-btn:hover { color: #409eff; border-color: #409eff; background: #ecf5ff; }

.logic-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.logic-item { font-size: 0.8rem; }
.bar-label { display: flex; justify-content: space-between; margin-bottom: 3px; color: #4a5568; font-weight: bold; }
.logic-bar { height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
.fill { height: 100%; transition: width 0.5s ease; }
.logic-footer { display: flex; gap: 10px; margin-top: auto; }
.mini-tag { background: rgba(255,255,255,0.7); padding: 1px 6px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.05); font-size: 0.75rem; color: #4a5568; }

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
.btn-start { background: #48bb78; } .btn-stop { background: #e53e3e; } .btn-blue { background: #3182ce; } .btn-red { background: #e53e3e; } .btn-gray { background: #e2e8f0; color: #666; } .btn-active { background: #3182ce; animation: pulse 2s infinite; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* === Cards Grid === */
.cards-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 15px; flex-shrink: 0; } 
.node-card { background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); cursor: pointer; transition: transform 0.2s; border: 1px solid #eee; display: flex; flex-direction: column; }
.node-card:hover { transform: translateY(-3px); border-color: #42b983; }
.card-header { padding: 10px 15px; background: #f8f9fa; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.card-header h3 { margin: 0; font-size: 1rem; color: #333; }
.tag { background: #e6fffa; color: #38a169; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
.card-body { padding: 12px; flex: 1; }

.sensor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.sensor-item { background: #f9fafc; padding: 6px 8px; border-radius: 6px; display: flex; flex-direction: column; align-items: flex-start; justify-content: center; border: 1px solid #f0f2f5; }
.sensor-item.full-width { grid-column: span 2; flex-direction: row; justify-content: space-between; align-items: center; }
.lbl { font-size: 0.75rem; color: #909399; margin-bottom: 2px; }
.full-width .lbl { margin-bottom: 0; }
.val { font-size: 0.95rem; font-weight: bold; color: #2c3e50; }

.two-rows { grid-template-columns: 1fr 1fr; height: 100%; align-content: center; }
.large-item { align-items: center; padding: 15px 5px; }
.big-val { font-size: 1.4rem; color: #3182ce; }
.wind-grade { text-align: center; margin-top: 10px; font-size: 0.8rem; color: #999; background: #f4f4f5; padding: 4px; border-radius: 4px; }
.card-footer { padding: 8px 15px; font-size: 0.75rem; color: #999; text-align: right; border-top: 1px solid #f8f9fa; }

/* === Bottom Panel === */
.bottom-panel { background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); display: flex; gap: 20px; padding: 15px; border: 1px solid #eee; height: 160px; flex-shrink: 0; margin-bottom: 20px; }
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
.sys-item { display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; color: #4a5568; }
.sys-bar { flex: 1; height: 6px; background: #edf2f7; border-radius: 3px; margin: 0 10px; overflow: hidden; }
.sys-fill { height: 100%; background: #4299e1; border-radius: 3px; }
.sys-fill.warn { background: #ecc94b; }
.sys-val { width: 40px; text-align: right; font-weight: bold; }
.sys-val.good { width: auto; color: #48bb78; }

@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }

@media (max-width: 1200px) {
  .top-section { height: auto; flex-direction: column; }
  .decision-panel, .drone-panel { width: 100%; height: auto; }
  .drone-body { height: 200px; }
  .cards-grid { grid-template-columns: 1fr; }
  .bottom-panel { flex-direction: column; height: auto; }
  .system-status-section { border-left: none; padding-left: 0; border-top: 1px solid #eee; padding-top: 15px; }
}
</style>