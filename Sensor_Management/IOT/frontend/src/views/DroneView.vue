<template>
  <div class="pure-engineering-console">
    
    <main class="video-main">
      <div class="video-container">
        <video
          ref="videoEl"
          autoplay
          muted
          playsinline
          class="video-stream"
          :class="{ 'stream-active': isPlaying && isStreamReceived }"
        ></video>

        <div v-if="!isStreamReceived" class="video-overlay">
          <div class="overlay-content">
            <div v-if="isPlaying" class="spinner"></div>
            <div v-else class="static-icon">⏸</div>
            <p class="overlay-tips">{{ isPlaying ? "正在建立 P2P 连接..." : "图传通道未开启" }}</p>
          </div>
        </div>

        <div class="osd-overlay" v-if="isPlaying && isStreamReceived">
          <div class="osd-top-left">
            <span class="osd-live">LIVE</span>
            <span class="osd-signal">2Hz 采样 | 延迟: ~120ms</span>
          </div>
          <div class="osd-top-right" v-if="isRecording">
            <span class="osd-rec">● REC {{ formatTime(recordingTime) }}</span>
          </div>
        </div>
      </div>

      <div class="connection-bar">
        <button 
          :class="['action-btn', isPlaying ? 'btn-disconnect' : 'btn-connect']" 
          @click="toggle"
        >
          {{ isPlaying ? "⏹ 断开 WebRTC 图传" : "▶ 启动 WebRTC 连接" }}
        </button>
        <span class="status-indicator" :class="statusClass">{{ statusText }}</span>
      </div>
    </main>

    <aside class="side-panel">
      <div class="task-card">
        <div class="card-title">📸 智能抓拍</div>
        <div class="action-row">
          <button @click="manualSnapshot" :disabled="!isStreamReceived" class="btn-tool btn-blue">单帧提取</button>
          <div class="toggle-group">
            <span class="label">自动(2Hz):</span>
            <label class="switch">
              <input type="checkbox" v-model="isAutoCapturing" @change="handleAutoCapture" :disabled="!isStreamReceived">
              <span class="slider round"></span>
            </label>
          </div>
        </div>
      </div>

      <div class="task-card">
        <div class="card-title">🎥 录像存证</div>
        <button 
          @click="toggleRecording" 
          :disabled="!isStreamReceived" 
          class="btn-tool btn-block"
          :class="isRecording ? 'btn-red-active' : 'btn-dark'"
        >
          {{ isRecording ? '⏹ 结束录制并上传' : '● 启动录像任务' }}
        </button>
        <div class="upload-status" :class="{ 'text-error': uploadStatus.includes('失败'), 'text-success': uploadStatus.includes('成功') }">
          {{ uploadStatus || '就绪' }}
        </div>
      </div>

      <div class="mini-terminal">
        <div class="log-header">系统运行日志</div>
        <div class="log-content" ref="sysLogContainer">
          <p v-for="(log, index) in sysLogs" :key="index" :class="log.type">
            <span class="time">[{{ log.time }}]</span> {{ log.msg }}
          </p>
        </div>
      </div>
    </aside>

    <canvas ref="canvasEl" style="display: none;"></canvas>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, nextTick } from "vue"

// ================= 状态与配置 =================
const videoEl = ref(null)
const canvasEl = ref(null)

const isPlaying = ref(false)
const isStreamReceived = ref(false)
const statusText = ref("通道关闭")

const sysLogs = ref([{ time: new Date().toLocaleTimeString(), msg: "监控站初始化就绪...", type: "info" }])
const sysLogContainer = ref(null)

const isAutoCapturing = ref(false)
const isRecording = ref(false)
const recordingTime = ref(0)
const uploadStatus = ref('')

let pc = null
let reconnectTimer = null
let captureTimer = null
let recordInterval = null
let mediaRecorder = null
let recordedChunks = []

const STREAM_URL = "http://192.168.0.242:8889/drone/whep"
const API_BASE = "http://localhost:8000/api"

const statusClass = computed(() => {
  if (statusText.value.includes("接收中")) return "text-success"
  if (statusText.value.includes("中")) return "text-warning"
  return "text-muted"
})

// ================= 核心：WebRTC 连接 =================
function addSysLog(msg, type = "info") {
  statusText.value = msg
  sysLogs.value.push({ time: new Date().toLocaleTimeString(), msg, type })
  if (sysLogs.value.length > 20) sysLogs.value.shift()
  nextTick(() => { if (sysLogContainer.value) sysLogContainer.value.scrollTop = sysLogContainer.value.scrollHeight })
}

async function createPeer() {
  pc = new RTCPeerConnection({ iceServers: [] })
  pc.addTransceiver("video", { direction: "recvonly" })

  pc.ontrack = (event) => {
    addSysLog("视频轨道挂载成功", "success")
    isStreamReceived.value = true
    videoEl.value.srcObject = event.streams[0]
  }

  pc.onconnectionstatechange = () => {
    if (pc.connectionState === "failed" || pc.connectionState === "disconnected") reconnect()
  }

  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)
  addSysLog("发送 SDP 握手请求...", "info")

  const res = await fetch(STREAM_URL, {
    method: "POST",
    headers: { "Content-Type": "application/sdp" },
    body: offer.sdp
  })

  if (!res.ok) throw new Error("WHEP 握手失败")
  const answer = await res.text()
  await pc.setRemoteDescription({ type: "answer", sdp: answer })
}

async function start() {
  try {
    isPlaying.value = true
    addSysLog("启动 WebRTC 协商...", "info")
    await createPeer()
  } catch (e) {
    addSysLog("连接异常，准备重试", "error")
    reconnect()
  }
}

function stop() {
  isPlaying.value = false
  isStreamReceived.value = false
  addSysLog("通道已关闭", "warning")
  
  if (pc) { pc.close(); pc = null }
  if (videoEl.value) videoEl.value.srcObject = null
  clearTimeout(reconnectTimer)

  if (isAutoCapturing.value) { isAutoCapturing.value = false; clearInterval(captureTimer) }
  if (isRecording.value) stopRecording()
}

function reconnect() {
  stop()
  isPlaying.value = true
  addSysLog("触发重连机制...", "warning")
  reconnectTimer = setTimeout(() => start(), 2000)
}

function toggle() { isPlaying.value ? stop() : start() }

// ================= 任务：抓拍功能 =================
const manualSnapshot = () => captureAndUpload("手动")

const handleAutoCapture = () => {
  // 保持你要求的 2Hz 采样率 (500ms)
  if (isAutoCapturing.value) {
    captureTimer = setInterval(() => captureAndUpload("自动"), 500)
  } else {
    clearInterval(captureTimer)
  }
}

const captureAndUpload = async (type) => {
  if (!videoEl.value || !canvasEl.value || !isStreamReceived.value) return
  const canvas = canvasEl.value
  const ctx = canvas.getContext('2d')
  canvas.width = videoEl.value.videoWidth
  canvas.height = videoEl.value.videoHeight
  ctx.drawImage(videoEl.value, 0, 0)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.8)

  try {
    const res = await fetch(`${API_BASE}/save_drone_image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataUrl })
    })
    if (res.ok) addSysLog(`${type}单帧抓拍成功`, "success")
  } catch (e) {
    addSysLog("抓拍上传失败", "error")
  }
}

// ================= 任务：录像功能 =================
const toggleRecording = () => { isRecording.value ? stopRecording() : startRecording() }

const startRecording = () => {
  if (!videoEl.value || !isStreamReceived.value) return
  const stream = videoEl.value.captureStream()
  mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' })
  recordedChunks = []
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data) }
  mediaRecorder.onstop = uploadVideo
  mediaRecorder.start()
  isRecording.value = true
  recordingTime.value = 0
  uploadStatus.value = '正在录像...'
  recordInterval = setInterval(() => recordingTime.value++, 1000)
}

const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop()
  isRecording.value = false
  clearInterval(recordInterval)
}

const uploadVideo = async () => {
  uploadStatus.value = '⏳ 上传至服务端...'
  const blob = new Blob(recordedChunks, { type: 'video/webm' })
  const formData = new FormData()
  formData.append('file', blob, 'mission_record.webm')

  try {
    const res = await fetch(`${API_BASE}/save_drone_video`, { method: 'POST', body: formData })
    if (res.ok) {
      uploadStatus.value = '✅ 保存成功'
      addSysLog("录像存证已上传", "success")
    } else {
      uploadStatus.value = '❌ 保存失败'
    }
  } catch (e) {
    uploadStatus.value = '❌ 网络异常'
  }
}

const formatTime = (s) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

onBeforeUnmount(() => stop())
</script>

<style scoped>
/* ==============================
   极简无感布局 (消除白边与违和感)
   ============================== */
.pure-engineering-console {
  /* 移除硬编码背景色，直接透明，继承父级页面颜色 */
  background-color: transparent; 
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  gap: 16px;
  font-family: "SFMono-Regular", Consolas, monospace;
  color: #d1d5db; /* 柔和文字色 */
}

/* ==============================
   左侧：视频主视图 (占据绝大空间)
   ============================== */
.video-main {
  flex: 1; /* 自动撑满剩余空间 */
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.video-container {
  flex: 1;
  background: rgba(0, 0, 0, 0.6); /* 仅视频底色使用半透明黑，避免突兀 */
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  display: flex;
}

/* 使用 object-fit: cover 强制画面填满整个框，消灭上下左右黑边 */
.video-stream {
  width: 100%;
  height: 100%;
  object-fit: cover; 
  opacity: 0;
  transition: opacity 0.3s;
}
.video-stream.stream-active { opacity: 1; }

.video-overlay {
  position: absolute; inset: 0; display: flex; justify-content: center; align-items: center;
  background: rgba(0, 0, 0, 0.4); z-index: 2;
}
.overlay-content { text-align: center; color: #9ca3af; }
.static-icon { font-size: 2rem; margin-bottom: 12px; }
.spinner { width: 32px; height: 32px; margin: 0 auto 12px; border: 3px solid rgba(255,255,255,0.1); border-top-color: #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; }

/* 视频悬浮 OSD */
.osd-overlay { position: absolute; inset: 0; padding: 16px; pointer-events: none; z-index: 1; display: flex; justify-content: space-between; align-items: flex-start; }
.osd-top-left { display: flex; align-items: center; gap: 10px; }
.osd-live { background: rgba(239, 68, 68, 0.8); padding: 2px 8px; color: #fff; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
.osd-signal { background: rgba(0,0,0,0.5); padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
.osd-rec { color: #ef4444; font-weight: bold; animation: blink 2s infinite; text-shadow: 0 0 4px rgba(239,68,68,0.5); font-size: 0.9rem;}

/* 控制条 */
.connection-bar { display: flex; align-items: center; gap: 16px; }
.action-btn {
  flex: 1; padding: 12px; font-size: 1rem; border: none; border-radius: 6px;
  cursor: pointer; font-weight: bold; transition: 0.2s;
}
.btn-connect { background: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; color: #3b82f6; }
.btn-connect:hover { background: rgba(59, 130, 246, 0.2); }
.btn-disconnect { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #ef4444; }
.btn-disconnect:hover { background: rgba(239, 68, 68, 0.2); }
.status-indicator { font-size: 0.9rem; min-width: 120px; text-align: right; }

/* ==============================
   右侧：控制面板与精简日志
   ============================== */
/* ==============================
   右侧：控制面板 (独立黑色实体版块)
   ============================== */
.side-panel {
  width: 320px; /* 稍微加宽一点，给日志留点空间 */
  display: flex;
  flex-direction: column;
  gap: 16px;
  /* 核心修改：赋予深色实体背景，不再透明 */
  background: #141416; 
  border: 1px solid #2d2d30;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); /* 增加悬浮质感 */
}

/* 任务卡片背景稍微提亮，做出层级 */
.task-card {
  background: #1e1e20; 
  border: 1px solid #333;
  border-radius: 8px;
  padding: 16px;
}
.card-title { 
  font-size: 0.95rem; 
  color: #f3f4f6; /* 高亮白 */
  margin-bottom: 12px; 
  border-bottom: 1px solid #333; 
  padding-bottom: 8px; 
  font-weight: bold;
}

.action-row { display: flex; justify-content: space-between; align-items: center; }
.btn-tool { padding: 8px 12px; font-size: 0.85rem; border-radius: 4px; border: none; cursor: pointer; transition: 0.2s; }
.btn-tool:disabled { opacity: 0.3; cursor: not-allowed; }
.btn-blue { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
.btn-blue:hover:not(:disabled) { background: rgba(59, 130, 246, 0.3); }
.btn-block { width: 100%; padding: 12px; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; }
.btn-dark { background: #2d2d30; color: #d1d5db; transition: 0.2s; }
.btn-dark:hover:not(:disabled) { background: #3f3f46; color: #fff; }
.btn-red-active { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #ef4444; }

.upload-status { margin-top: 12px; font-size: 0.85rem; text-align: center; }

/* 自动抓拍的极简开关 */
.toggle-group { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #d1d5db; }
.switch { position: relative; width: 36px; height: 18px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; inset: 0; background-color: #3f3f46; border-radius: 18px; transition: .3s; }
.slider:before { position: absolute; content: ""; height: 14px; width: 14px; left: 2px; bottom: 2px; background-color: #9ca3af; border-radius: 50%; transition: .3s; }
input:checked + .slider { background-color: rgba(59, 130, 246, 0.3); }
input:checked + .slider:before { transform: translateX(18px); background-color: #3b82f6; }

/* 迷你终端 (纯黑底色，还原真实控制台质感) */
.mini-terminal {
  flex: 1; 
  background: #000000; /* 极客纯黑 */
  border: 1px solid #333;
  border-radius: 8px;
  display: flex; 
  flex-direction: column; 
  overflow: hidden;
}
.log-header { 
  padding: 8px 12px; 
  font-size: 0.8rem; 
  color: #9ca3af; 
  background: #141416; 
  border-bottom: 1px solid #333; 
}
.log-content { 
  flex: 1; 
  padding: 10px; 
  overflow-y: auto; 
  font-size: 0.8rem; 
  line-height: 1.6; 
}
.log-content p { margin: 0 0 6px 0; font-family: "SFMono-Regular", Consolas, monospace;}
.time { color: #6b7280; margin-right: 8px; }
.text-success { color: #10b981; }
.text-warning { color: #f59e0b; }
.text-error { color: #ef4444; }
.text-info { color: #d1d5db; }
.text-muted { color: #6b7280; }

/* 滚动条暗黑化美化 */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #141416; }
::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #52525b; }
</style>