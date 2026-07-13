<template>
  <div class="card">
    <h3>📹 实时检测</h3>
    <ModelMetricsPanel :settings="props.settings" :availableModels="props.availableModels" />
    
    <!-- Source Selection -->
    <div class="source-selector">
      <label>
        <input type="radio" value="webcam" v-model="source" @change="handleSourceChange">
        📷 本地摄像头
      </label>
      <label>
        <input type="radio" value="rtsp" v-model="source" @change="handleSourceChange">
        📡 RTMP流（OBS推流）
      </label>
    </div>
    
    <!-- Webcam Section -->
    <div v-if="source === 'webcam'" class="webcam-section">
      <div class="video-container">
        <video ref="webcamVideo" autoplay playsinline v-show="isStreaming"></video>
        <canvas ref="canvas" style="display: none;"></canvas>
        
        <div v-if="!isStreaming" class="placeholder">
          <p>点击下方按钮启动摄像头</p>
        </div>
      </div>
      
      <div class="button-group">
        <button v-if="!isStreaming" class="btn btn-success" @click="startWebcam">▶️ 启动摄像头</button>
        <button v-else class="btn btn-danger" @click="stopWebcam">⏹️ 停止检测</button>
      </div>

      <div class="detection-list">
        <span
          v-for="(det, index) in webcamDetections"
          :key="index"
          class="detection-badge"
          :style="getClassStyle(det.class)"
        >
          {{ det.class }} ({{ (det.confidence * 100).toFixed(1) }}%)
        </span>
      </div>
    </div>
    
    <!-- RTSP Section -->
    <div v-if="source === 'rtsp'" class="rtsp-section">
      <div class="info-box-blue">
        <h4 style="font-size: 30px;">💡 使用说明</h4>
        <p>1. 确保OBS Studio已启动并开始推流</p>
        <p>2. 默认推流地址: rtmp://127.0.0.1:1935/live</p>
        <p>3. 点击"启动推流检测"开始实时检测</p>
      </div>
      
      <div class="input-group">
        <label style="font-size: 30px;">推流地址:</label>
        <input type="text" style="font-size: 25px;" v-model="rtspUrl" placeholder="rtmp://127.0.0.1:1935/live">
      </div>
      
      <div class="video-container">
        <img v-if="rtspStreaming" :src="rtspFeedUrl" alt="RTSP Stream" class="rtsp-stream">
        <div v-else class="placeholder">
          <p style="font-size: 30px;">📡 等待启动推流检测...</p>
        </div>
      </div>
      
      <div class="button-group">
        <button v-if="!rtspStreaming" class="btn btn-success" @click="startRTSP">▶️ 启动推流检测</button>
        <button v-else class="btn btn-danger" @click="stopRTSP">⏹️ 停止检测</button>
      </div>
      
      <!-- RTSP Stats -->
      <div v-if="rtspStreaming && rtspStats" class="detection-info">
        <div class="info-box">
          <h4>总帧数</h4>
          <p>{{ rtspStats.frame_count || 0 }}</p>
        </div>
        <div class="info-box">
          <h4>事故检测次数</h4>
          <p>{{ rtspStats.fire_count || 0 }}</p>
        </div>
        <div class="info-box">
          <h4>当前检测数</h4>
          <p>{{ currentRtspDetections.length }}</p>
        </div>
        <div class="info-box">
          <h4>最后更新</h4>
          <p>{{ lastUpdateTime }}</p>
        </div>
      </div>
      
      <div class="detection-list">
        <span 
          v-for="(det, index) in currentRtspDetections" 
          :key="index" 
          class="detection-badge"
          :style="getClassStyle(det.class)"
        >
          {{ det.class }} ({{ (det.confidence * 100).toFixed(1) }}%)
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted, computed } from 'vue'
import ModelMetricsPanel from './ModelMetricsPanel.vue'
import { getClassStyle } from '../utils/classColors'

const props = defineProps({
  settings: Object,
  availableModels: {
    type: Array,
    default: () => []
  },
  safeFetch: Function,
  apiUrl: String
})

const source = ref('webcam')
const isStreaming = ref(false)
const webcamVideo = ref(null)
const canvas = ref(null)
const webcamDetections = ref([])
let webcamInterval = null
let stream = null

const DEFAULT_STREAM_URL = 'rtmp://127.0.0.1:1935/live'
const savedStreamUrl = localStorage.getItem('realtimeDetection.rtspUrl')
const legacyStreamUrls = ['rtsp://localhost:8554/live', 'rtmp://127.0.0.1:2003/live']
const rtspUrl = ref(!savedStreamUrl || legacyStreamUrls.includes(savedStreamUrl) ? DEFAULT_STREAM_URL : savedStreamUrl)
const rtspStreaming = ref(false)
const rtspStats = ref(null)
const currentRtspDetections = ref([])
const RTSP_STREAM_ID = 'rtsp_cam_01'
let rtspInterval = null

const rtspFeedUrl = computed(() => {
  return `${props.apiUrl}/api/rtsp/video_feed/${RTSP_STREAM_ID}?t=${Date.now()}`
})

const lastUpdateTime = computed(() => {
  if (!rtspStats.value?.last_detection_time) return '--'
  return new Date(rtspStats.value.last_detection_time * 1000).toLocaleTimeString('zh-CN')
})

const handleSourceChange = () => {
  if (source.value === 'rtsp') stopWebcam()
  else stopRTSP()
}

// Webcam logic
const startWebcam = async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ 
      video: { width: 640, height: 480 } 
    })
    webcamVideo.value.srcObject = stream
    isStreaming.value = true
    webcamInterval = setInterval(detectWebcamFrame, 1000)
  } catch (error) {
    alert('无法访问摄像头: ' + error.message)
  }
}

const stopWebcam = () => {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
  if (webcamInterval) {
    clearInterval(webcamInterval)
    webcamInterval = null
  }
  isStreaming.value = false
  webcamDetections.value = []
}

const detectWebcamFrame = async () => {
  if (!isStreaming.value) return
  
  const video = webcamVideo.value
  const cvs = canvas.value
  cvs.width = video.videoWidth
  cvs.height = video.videoHeight
  const ctx = cvs.getContext('2d')
  ctx.drawImage(video, 0, 0)
  
  const imageData = cvs.toDataURL('image/jpeg')

  try {
    const data = await props.safeFetch('/api/detect/webcam', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image: imageData,
        model: props.settings.model,
        conf: props.settings.conf,
        iou: props.settings.iou
      })
    })

    if (data.success) {
      webcamDetections.value = data.detections
    }
  } catch (error) {
    console.error('Webcam detection error:', error)
  }
}

// RTSP logic
const startRTSP = async () => {
  if (!rtspUrl.value) return alert('请输入推流地址')
  localStorage.setItem('realtimeDetection.rtspUrl', rtspUrl.value)

  try {
    const data = await props.safeFetch('/api/rtsp/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stream_id: RTSP_STREAM_ID,
        rtsp_url: rtspUrl.value,
        camera_name: 'OBS模拟摄像头'
      })
    })
    
    if (data.success) {
      rtspStreaming.value = true
      rtspInterval = setInterval(updateRTSPStatus, 1000)
    } else {
      alert('启动失败: ' + (data.error || '未知错误'))
    }
  } catch (error) {
    alert('连接失败: ' + error.message)
  }
}

const stopRTSP = async () => {
  try {
    await props.safeFetch(`/api/rtsp/stop/${RTSP_STREAM_ID}`, { method: 'POST' })
    rtspStreaming.value = false
    if (rtspInterval) {
      clearInterval(rtspInterval)
      rtspInterval = null
    }
    rtspStats.value = null
    currentRtspDetections.value = []
  } catch (error) {
    console.error('Stop RTSP failed:', error)
  }
}

const updateRTSPStatus = async () => {
  try {
    const data = await props.safeFetch(`/api/rtsp/detection/${RTSP_STREAM_ID}`)
    if (data.success) {
      rtspStats.value = data.stats
      if (data.detection) {
        currentRtspDetections.value = data.detection.detections || []
      }
    }
  } catch (error) {
    console.error('Update RTSP status failed:', error)
  }
}

onUnmounted(() => {
  stopWebcam()
  stopRTSP()
})
</script>

<style scoped>
.source-selector {
  margin-bottom: 20px;
  text-align: center;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.video-container {
  position: relative;
  background: #f3f4f6;
  border-radius: 8px;
  margin: 20px 0;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

video, .rtsp-stream {
  width: 100%;
  max-height: 600px;
  border-radius: 8px;
}

.placeholder {
  color: #888;
  font-size: 18px;
}

.button-group {
  text-align: center;
  margin-bottom: 20px;
}

.input-group {
  margin-bottom: 20px;
}

.input-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.input-group input {
  width: 100%;
  padding: 10px;
  border: 2px solid #ddd;
  border-radius: 5px;
}

.info-box-blue {
  background: #dbeafe;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 20px;
  color: #1e40af;
}

.info-box-blue h4 {
  margin-bottom: 5px;
}

.detection-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 20px;
}

.info-box {
  background: #f0f9ff;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #667eea;
}

.info-box h4 {
  color: #0c0c0c;
  margin-bottom: 5px;
  font-size: 14px;
}

.info-box p {
  font-size: 20px;
  font-weight: bold;
  color: #0c0c0c;
}

.detection-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.detection-badge {
  background: #10b981;
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
}
</style>
