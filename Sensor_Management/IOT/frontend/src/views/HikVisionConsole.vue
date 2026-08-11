<template>
  <div class="pure-engineering-console">
    
    <main class="video-main">
      <div class="video-container">
        <!-- WebSocket 视频流直接渲染在 Canvas 上 -->
        <canvas
          ref="videoCanvasEl"
          class="video-stream"
          :class="{ 'stream-active': isPlaying && isStreamReceived }"
        ></canvas>

        <div v-if="!isStreamReceived" class="video-overlay">
          <div class="overlay-content">
            <div v-if="isPlaying" class="spinner"></div>
            <div v-else class="static-icon">⏸</div>
            <p class="overlay-tips">{{ isPlaying ? "正在建立 WebSocket 视频流连接..." : "监控通道未开启" }}</p>
          </div>
        </div>

        <div class="osd-overlay" v-if="isPlaying && isStreamReceived">
          <div class="osd-top-left">
            <span class="osd-live">HIKVISION LIVE</span>
            <span class="osd-signal">TCP 转 WS | 延迟: ~200ms</span>
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
          {{ isPlaying ? "⏹ 断开海康监控节点" : "▶ 接入海康实时监控 (WebSocket)" }}
        </button>
        <span class="status-indicator" :class="statusClass">{{ statusText }}</span>
      </div>
    </main>

    <aside class="side-panel">
      <div class="task-card">
        <div class="card-title">📸 智能抓拍 (海康节点)</div>
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
        <div class="card-title">🎥 监控现场视频证据采集</div>
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
        <div class="log-header">系统运行日志 (HIK-01)</div>
        <div class="log-content" ref="sysLogContainer">
          <p v-for="(log, index) in sysLogs" :key="index" :class="log.type">
            <span class="time">[{{ log.time }}]</span> {{ log.msg }}
          </p>
        </div>
      </div>
    </aside>

  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, nextTick } from "vue"
import axios from "axios"
import JSMpeg from '@cycjimmy/jsmpeg-player'

// ================= 严格对齐后端 server.js 的配置 =================
const CAMERA_ID = 'cam-01';
const HIK_SERVER_PORT = 3000;
const NODE_SERVER_IP = '127.0.0.1'; 

// 💡 1. 修正 WebSocket 地址为后端指定的路由
const WS_STREAM_URL = `ws://${NODE_SERVER_IP}:${HIK_SERVER_PORT}/stream/hik`; 
const API_BASE = "http://localhost:8000/api";

// 💡 2. 调用后端的 /sensor/camera/connect 来解锁视频流
const connectCameraAPI = async () => {
  try {
    const res = await axios.post(`http://${NODE_SERVER_IP}:${HIK_SERVER_PORT}/sensor/camera/connect`, {}, { timeout: 3000 });
    return res?.data?.code === 0;
  } catch (error) {
    return false;
  }
};

// 💡 3. 断开时调用后端的 disconnect
const disconnectCameraAPI = async () => {
  try {
    await axios.post(`http://${NODE_SERVER_IP}:${HIK_SERVER_PORT}/sensor/camera/disconnect`);
  } catch (error) {}
};
// =========================================================================

const videoCanvasEl = ref(null)
const isPlaying = ref(false)
const isStreamReceived = ref(false)
const statusText = ref("通道关闭")

const sysLogs = ref([{ time: new Date().toLocaleTimeString(), msg: "海康监控站初始化就绪...", type: "info" }])
const sysLogContainer = ref(null)

const isAutoCapturing = ref(false)
const isRecording = ref(false)
const recordingTime = ref(0)
const uploadStatus = ref('')

let jsmpegPlayer = null
let reconnectTimer = null
let captureTimer = null
let recordInterval = null
let mediaRecorder = null
let recordedChunks = []

const statusClass = computed(() => {
  if (statusText.value.includes("接收中") || statusText.value.includes("成功")) return "text-success"
  if (statusText.value.includes("中")) return "text-warning"
  return "text-muted"
})

function addSysLog(msg, type = "info") {
  statusText.value = msg
  sysLogs.value.push({ time: new Date().toLocaleTimeString(), msg, type })
  if (sysLogs.value.length > 20) sysLogs.value.shift()
  nextTick(() => { if (sysLogContainer.value) sysLogContainer.value.scrollTop = sysLogContainer.value.scrollHeight })
}

async function start() {
  try {
    isPlaying.value = true
    addSysLog("请求接入摄像头数据总线...", "info")
    
    // 发送 POST 请求解锁后端推流状态
    const isConnected = await connectCameraAPI()
    if (!isConnected) {
      throw new Error("摄像头接入失败：设备离线或网络异常")
    }
    
    addSysLog("API 解锁成功，开始建立 WebSocket 推流隧道...", "info")

    if (JSMpeg) {
      jsmpegPlayer = new JSMpeg.Player(WS_STREAM_URL, {
        canvas: videoCanvasEl.value,
        audio: false, 
        autoplay: true,
        onVideoDecode: () => {
          if (!isStreamReceived.value) {
            isStreamReceived.value = true;
            addSysLog("视频轨道挂载成功，画面解析中...", "success");
          }
        },
        onStalled: () => {
           addSysLog("视频流发生卡顿或中断", "warning");
        }
      });
    } else {
       throw new Error("解码库加载失败，请检查是否已正确安装插件");
    }

  } catch (e) {
    addSysLog(e.message, "error")
    reconnect()
  }
}

function stop() {
  isPlaying.value = false
  isStreamReceived.value = false
  addSysLog("监控通道已关闭", "warning")
  
  if (jsmpegPlayer) {
    jsmpegPlayer.destroy()
    jsmpegPlayer = null
  }
  
  // 释放后端的锁
  disconnectCameraAPI()
  
  clearTimeout(reconnectTimer)
  if (isAutoCapturing.value) { isAutoCapturing.value = false; clearInterval(captureTimer) }
  if (isRecording.value) stopRecording()
}

function reconnect() {
  stop()
  isPlaying.value = true
  addSysLog("触发重连机制...", "warning")
  reconnectTimer = setTimeout(() => start(), 3000)
}

function toggle() { isPlaying.value ? stop() : start() }

const manualSnapshot = () => captureAndUpload("手动")

const handleAutoCapture = () => {
  if (isAutoCapturing.value) {
    captureTimer = setInterval(() => captureAndUpload("自动"), 500)
  } else {
    clearInterval(captureTimer)
  }
}

const captureAndUpload = async (type) => {
  if (!videoCanvasEl.value || !isStreamReceived.value) return
  const dataUrl = videoCanvasEl.value.toDataURL('image/jpeg', 0.8)

  try {
    const res = await fetch(`${API_BASE}/save_hik_image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataUrl, cameraId: CAMERA_ID })
    })
    if (res.ok) addSysLog(`${type}单帧抓拍成功`, "success")
  } catch (e) {
    addSysLog("抓拍上传网络异常", "error")
  }
}

const toggleRecording = () => { isRecording.value ? stopRecording() : startRecording() }

const startRecording = () => {
  if (!videoCanvasEl.value || !isStreamReceived.value) return
  
  const stream = videoCanvasEl.value.captureStream(25)
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
  formData.append('file', blob, 'hik_mission_record.webm')
  formData.append('cameraId', CAMERA_ID)

  try {
    const res = await fetch(`${API_BASE}/save_hik_video`, { method: 'POST', body: formData })
    if (res.ok) {
      uploadStatus.value = '✅ 保存成功'
      addSysLog("监控现场视频证据已上传", "success")
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
   极简无感布局 (全息科幻终端风格)
   ============================== */
.pure-engineering-console {
  background-color: transparent; 
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  gap: 16px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: rgba(186, 230, 253, 0.88);
}

.video-main {
  flex: 1; 
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.video-container {
  flex: 1;
  background: #000; 
  border: 1px solid rgba(0, 242, 254, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8), 0 0 15px rgba(0, 242, 254, 0.1);
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  display: flex;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: cover; 
  opacity: 0;
  transition: opacity 0.4s cubic-bezier(0.25, 1, 0.5, 1);
}
.video-stream.stream-active { opacity: 1; }

.video-overlay {
  position: absolute; inset: 0; display: flex; justify-content: center; align-items: center;
  background: rgba(0, 0, 0, 0.6); z-index: 2;
  backdrop-filter: blur(4px);
}
.overlay-content { text-align: center; color: rgba(0, 242, 254, 0.6); font-family: "JetBrains Mono", monospace; font-size: 13px; }
.static-icon { font-size: 32px; margin-bottom: 12px; filter: drop-shadow(0 0 8px rgba(0, 242, 254, 0.5)); color: #00f2fe; }

.spinner { 
  width: 32px; height: 32px; margin: 0 auto 12px; 
  border: 3px solid rgba(0, 242, 254, 0.1); 
  border-top-color: #00f2fe; 
  border-radius: 50%; 
  animation: spin 1s linear infinite; 
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.3);
}
@keyframes spin { 100% { transform: rotate(360deg); } }

.osd-overlay { position: absolute; inset: 0; padding: 16px; pointer-events: none; z-index: 1; display: flex; justify-content: space-between; align-items: flex-start; }
.osd-top-left { display: flex; align-items: center; gap: 10px; font-family: "JetBrains Mono", monospace; }

.osd-live { 
  background: rgba(239, 68, 68, 0.15); padding: 2px 8px; color: #ef4444; 
  border: 1px solid rgba(239, 68, 68, 0.5); border-radius: 4px; 
  font-size: 11px; font-weight: bold; box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}
.osd-signal { 
  background: rgba(0, 242, 254, 0.15); padding: 2px 8px; color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.4); border-radius: 4px; 
  font-size: 11px; box-shadow: 0 0 8px rgba(0, 242, 254, 0.2);
}
.osd-rec { 
  color: #ef4444; font-weight: bold; animation: pulse-rec 2s infinite; 
  text-shadow: 0 0 8px rgba(239, 68, 68, 0.8); font-size: 13px; font-family: "JetBrains Mono", monospace;
}
@keyframes pulse-rec { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.connection-bar { display: flex; align-items: center; gap: 16px; }
.action-btn {
  flex: 1; padding: 10px 12px; font-size: 13px; font-family: inherit;
  border-radius: 6px; cursor: pointer; font-weight: bold; transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
  letter-spacing: 1px;
}
.btn-connect { background: rgba(0, 242, 254, 0.15); border: 1px solid #00f2fe; color: #00f2fe; box-shadow: 0 0 8px rgba(0, 242, 254, 0.3); }
.btn-connect:hover { background: rgba(0, 242, 254, 0.25); box-shadow: 0 0 15px rgba(0, 242, 254, 0.5); }

.btn-disconnect { background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.3); }
.btn-disconnect:hover { background: rgba(239, 68, 68, 0.25); box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }

.status-indicator { font-size: 11.5px; min-width: 120px; text-align: right; font-family: "JetBrains Mono", monospace; color: rgba(186, 230, 253, 0.7); }

.side-panel {
  width: 320px; 
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: rgba(6, 14, 28, 0.85); 
  backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid rgba(0, 242, 254, 0.25);
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.7), inset 0 0 15px rgba(0, 242, 254, 0.05); 
}

.task-card {
  background: rgba(0, 242, 254, 0.03); 
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 14px;
}
.card-title { 
  font-size: 13.5px; 
  color: #00f2fe; 
  margin-bottom: 12px; 
  border-bottom: 1px dashed rgba(0, 242, 254, 0.2); 
  padding-bottom: 8px; 
  font-weight: bold;
  letter-spacing: 0.5px;
  text-shadow: 0 0 8px rgba(0, 242, 254, 0.5);
}

.action-row { display: flex; justify-content: space-between; align-items: center; }
.btn-tool { padding: 6px 12px; font-size: 11.5px; border-radius: 4px; font-family: inherit; font-weight: bold; border: none; cursor: pointer; transition: all 0.3s; }
.btn-tool:disabled { opacity: 0.3; cursor: not-allowed; filter: grayscale(1); }

.btn-blue { background: rgba(0, 242, 254, 0.15); color: #00f2fe; border: 1px solid #00f2fe; box-shadow: 0 0 8px rgba(0, 242, 254, 0.3); }
.btn-blue:hover:not(:disabled) { background: rgba(0, 242, 254, 0.25); box-shadow: 0 0 12px rgba(0, 242, 254, 0.5); }

.btn-block { width: 100%; padding: 10px; font-size: 13px; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; transition: all 0.3s; font-family: inherit;}
.btn-dark { background: transparent; color: rgba(186, 230, 253, 0.88); border: 1px solid rgba(0, 242, 254, 0.3); }
.btn-dark:hover:not(:disabled) { background: rgba(0, 242, 254, 0.15); border-color: #00f2fe; color: #fff; box-shadow: 0 0 12px rgba(0, 242, 254, 0.4); }

.btn-red-active { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; box-shadow: 0 0 10px rgba(239, 68, 68, 0.4); }

.upload-status { margin-top: 12px; font-size: 11px; text-align: center; color: #10b981; font-family: "JetBrains Mono", monospace; text-shadow: 0 0 5px rgba(16, 185, 129, 0.5); }

.toggle-group { display: flex; align-items: center; gap: 8px; font-size: 11.5px; color: rgba(186, 230, 253, 0.88); font-weight: bold;}
.switch { position: relative; width: 34px; height: 18px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; inset: 0; background-color: rgba(255,255,255,0.1); border: 1px solid rgba(0, 242, 254, 0.2); border-radius: 18px; transition: .3s; }
.slider:before { position: absolute; content: ""; height: 12px; width: 12px; left: 2px; bottom: 2px; background-color: rgba(186, 230, 253, 0.7); border-radius: 50%; transition: .3s; }
input:checked + .slider { background-color: rgba(0, 242, 254, 0.2); border-color: #00f2fe; box-shadow: 0 0 8px rgba(0, 242, 254, 0.4); }
input:checked + .slider:before { transform: translateX(16px); background-color: #00f2fe; box-shadow: 0 0 6px #00f2fe; }

.mini-terminal {
  flex: 1; 
  background: rgba(0, 0, 0, 0.6); 
  border: 1px solid rgba(0, 242, 254, 0.2);
  border-radius: 8px;
  display: flex; 
  flex-direction: column; 
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.8);
}
.log-header { 
  padding: 8px 12px; 
  font-size: 11.5px; 
  color: #00f2fe; 
  font-weight: bold;
  background: linear-gradient(90deg, rgba(0, 242, 254, 0.12), transparent);
  border-bottom: 1px solid rgba(0, 242, 254, 0.2); 
}
.log-content { 
  flex: 1; 
  padding: 10px; 
  overflow-y: auto; 
  font-size: 11px; 
  line-height: 1.5; 
}
.log-content p { margin: 0 0 6px 0; font-family: "JetBrains Mono", Consolas, monospace; word-break: break-all;}
.time { color: rgba(0, 242, 254, 0.7); margin-right: 8px; }

.text-success { color: #10b981; text-shadow: 0 0 5px rgba(16, 185, 129, 0.4); }
.text-warning { color: #f59e0b; text-shadow: 0 0 5px rgba(245, 158, 11, 0.4); }
.text-error { color: #ef4444; text-shadow: 0 0 5px rgba(239, 68, 68, 0.4); }
.text-info { color: rgba(186, 230, 253, 0.9); }
.text-muted { color: rgba(148, 163, 184, 0.6); }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
::-webkit-scrollbar-thumb { background: rgba(0, 242, 254, 0.3); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0, 242, 254, 0.6); }
</style>