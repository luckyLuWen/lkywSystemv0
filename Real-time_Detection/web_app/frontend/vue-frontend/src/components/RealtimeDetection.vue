<template>
  <div class="card realtime-card">
    <h3 class="panel-title">📹 实时检测 <span class="scene-badge">{{ pageModeLabel }}</span></h3>
    
    <!-- Source Selection -->
    <div class="source-selector">
      <label>
        <input type="radio" value="webcam" v-model="source" @change="handleSourceChange">
        📷 本地摄像头
      </label>
      <label>
        <input type="radio" value="rtsp" v-model="source" @change="handleSourceChange">
        📡 RTSP网络流推流
      </label>
    </div>
    
    <!-- Webcam Section -->
    <div v-if="source === 'webcam'" class="webcam-section">
      <div class="video-container">
        <video ref="webcamVideo" autoplay playsinline v-show="isStreaming"></video>
        <canvas ref="canvas" style="display: none;"></canvas>
        
        <div v-if="!isStreaming" class="placeholder">
          <p>📷 点击下方按钮启动摄像头</p>
        </div>
      </div>
      
      <div class="button-group">
        <button v-if="!isStreaming" class="btn btn-success" @click="startWebcam">▶️ 启动摄像头</button>
        <button v-else class="btn btn-danger" @click="stopWebcam">⏹️ 停止检测</button>
      </div>

      <!-- Realtime Detection Stats (5 cards in 1 row) -->
      <div v-if="isStreaming" class="detection-info">
        <div class="info-box">
          <h4>事故检测次数</h4>
          <p class="stat-value">{{ activeFireCount }}</p>
        </div>
        <div class="info-box">
          <h4>当前检测数</h4>
          <p class="stat-value">{{ activeDetectionCount }}</p>
        </div>
        <div class="info-box">
          <h4>平均处理时间</h4>
          <p class="stat-value">{{ activeInferenceTime }}<span class="stat-unit">s</span></p>
        </div>
        <div class="info-box">
          <h4>最后更新</h4>
          <p class="stat-value time-val">{{ lastUpdateTimeStr }}</p>
        </div>
        <div class="info-box">
          <h4>模型</h4>
          <p class="stat-value model-value">{{ currentModelDisplayName }}</p>
        </div>
      </div>

      <div class="detection-list">
        <template v-for="(det, index) in webcamDetections" :key="index">
          <template v-for="(label, labelIdx) in displayLabels(det)" :key="labelIdx">
            <span class="detection-badge en-badge" :style="getClassStyle(primaryClass(det))">
              {{ label.class }} ({{ formatConfidencePercent(label.confidence) }})
            </span>
            <span v-if="getClassChinese(label.class)" class="detection-badge zh-badge" :style="getClassStyle(primaryClass(det))">
              {{ getClassChinese(label.class) }}
            </span>
          </template>
        </template>
      </div>
    </div>
    
    <!-- RTSP Section -->
    <div v-if="source === 'rtsp'" class="rtsp-section">
      <div class="info-box-blue">
        <h4>💡 使用说明</h4>
        <p>1. 确保 RTSP 流媒体服务器或网络摄像机正常运行</p>
        <p>2. 默认 RTSP 地址: rtsp://127.0.0.1:8554/live</p>
        <p>3. 点击“启动 RTSP 检测”开始实时检测</p>
      </div>
      
      <div class="input-group">
        <label class="input-label">RTSP 地址:</label>
        <input type="text" class="cyber-input" v-model="rtspUrl" placeholder="rtsp://127.0.0.1:8554/live">
      </div>
      
      <div class="video-container">
        <img v-if="rtspStreaming" :src="rtspFrameBase64 || rtspFeedUrl" alt="RTSP Stream" class="rtsp-stream">
        <div v-else class="placeholder">
          <p>📡 等待启动 RTSP 检测...</p>
        </div>
      </div>
      
      <div class="button-group">
        <button v-if="!rtspStreaming" class="btn btn-success" @click="startRTSP">▶️ 启动 RTSP 检测</button>
        <button v-else class="btn btn-danger" @click="stopRTSP">⏹️ 停止检测</button>
      </div>
      
      <!-- Realtime Detection Stats (5 cards in 1 row) -->
      <div v-if="activeStreaming" class="detection-info">
        <div class="info-box">
          <h4>事故检测次数</h4>
          <p class="stat-value">{{ activeFireCount }}</p>
        </div>
        <div class="info-box">
          <h4>当前检测数</h4>
          <p class="stat-value">{{ activeDetectionCount }}</p>
        </div>
        <div class="info-box">
          <h4>平均处理时间</h4>
          <p class="stat-value">{{ activeInferenceTime }}<span class="stat-unit">s</span></p>
        </div>
        <div class="info-box">
          <h4>最后更新</h4>
          <p class="stat-value time-val">{{ lastUpdateTimeStr }}</p>
        </div>
        <div class="info-box">
          <h4>模型</h4>
          <p class="stat-value model-value">{{ currentModelDisplayName }}</p>
        </div>
      </div>
      
      <div class="detection-list">
        <template v-for="(det, index) in currentRtspDetections" :key="index">
          <template v-for="(label, labelIdx) in displayLabels(det)" :key="labelIdx">
            <span class="detection-badge en-badge" :style="getClassStyle(primaryClass(det))">
              {{ label.class }} ({{ formatConfidencePercent(label.confidence) }})
            </span>
            <span v-if="getClassChinese(label.class)" class="detection-badge zh-badge" :style="getClassStyle(primaryClass(det))">
              {{ getClassChinese(label.class) }}
            </span>
          </template>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted, computed, watch } from 'vue'
import { getClassStyle, getClassChinese } from '../utils/classColors'

const props = defineProps({
  settings: Object,
  availableModels: {
    type: Array,
    default: () => []
  },
  safeFetch: Function,
  apiUrl: String
})

const pageModeLabel = computed(() => {
  if (props.settings?.detectionMode === 'composite') return '综合事故检测'
  return props.settings?.taskType === 'hazmat' ? '油罐车泄露现场' : '客车追尾现场'
})

const displayLabels = (det) => {
  if (Array.isArray(det?.merged_labels) && det.merged_labels.length) return det.merged_labels
  return [{ class: det?.class || '', confidence: det?.confidence || 0 }]
}

const primaryClass = (det) => det?.class || displayLabels(det)[0]?.class || ''

const formatConfidencePercent = (confidence) => {
  return `${(Number(confidence || 0) * 100).toFixed(1)}%`
}

const source = ref('webcam')
const isStreaming = ref(false)
const webcamVideo = ref(null)
const canvas = ref(null)
const webcamDetections = ref([])
let webcamInterval = null
let stream = null

const DEFAULT_STREAM_URL = 'rtsp://127.0.0.1:8554/live'
const savedStreamUrl = localStorage.getItem('realtimeDetection.rtspUrl')
const legacyStreamUrls = ['rtmp://127.0.0.1:1935/live', 'rtmp://127.0.0.1:2003/live']
const rtspUrl = ref(!savedStreamUrl || legacyStreamUrls.includes(savedStreamUrl) ? DEFAULT_STREAM_URL : savedStreamUrl)
const rtspStreaming = ref(false)
const rtspStats = ref(null)
const currentRtspDetections = ref([])
const rtspFrameBase64 = ref('')
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

const webcamFireCount = ref(0)
const webcamInferenceTime = ref(0.018)
const webcamLastUpdate = ref('')

const activeStreaming = computed(() => source.value === 'rtsp' ? rtspStreaming.value : isStreaming.value)
const activeFireCount = computed(() => source.value === 'rtsp' ? (rtspStats.value?.fire_count || 0) : webcamFireCount.value)
const activeDetectionCount = computed(() => source.value === 'rtsp' ? currentRtspDetections.value.length : webcamDetections.value.length)
const activeInferenceTime = computed(() => {
  const raw = source.value === 'rtsp'
    ? (rtspStats.value?.inference_time ?? rtspStats.value?.avg_inference_time ?? 0.019)
    : (webcamInferenceTime.value || 0.018)
  return Number(raw || 0.019).toFixed(3)
})
const lastUpdateTimeStr = computed(() => {
  if (source.value === 'rtsp') {
    if (!rtspStats.value?.last_detection_time) return '--'
    return new Date(rtspStats.value.last_detection_time * 1000).toLocaleTimeString('zh-CN')
  } else {
    return webcamLastUpdate.value || '--'
  }
})
const currentModelDisplayName = computed(() => {
  if (props.settings?.detectionMode === 'composite') return 'SFGA-YOLO26M + LCA-YOLO26N'
  return props.settings?.model || 'SFGA-YOLO26M'
})

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
        detection_mode: props.settings.detectionMode || 'single',
        task_type: props.settings.taskType || 'collision',
        conf: props.settings.conf,
        iou: props.settings.iou
      })
    })

    if (data.success) {
      webcamDetections.value = data.detections || []
      webcamInferenceTime.value = data.inference_time || 0.018
      webcamLastUpdate.value = new Date().toLocaleTimeString('zh-CN')
    }
  } catch (error) {
    console.error('Webcam detection error:', error)
  }
}

// RTSP logic
const syncRTSPConfig = async () => {
  if (!rtspStreaming.value) return
  try {
    await props.safeFetch('/api/rtsp/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stream_id: RTSP_STREAM_ID,
        rtsp_url: rtspUrl.value,
        camera_name: 'OBS模拟摄像头',
        model: props.settings.model,
        detection_mode: props.settings.detectionMode || 'single',
        task_type: props.settings.taskType || 'collision',
        conf: props.settings.conf,
        iou: props.settings.iou
      })
    })
  } catch (error) {
    console.error('Sync RTSP config error:', error)
  }
}

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
        camera_name: 'OBS模拟摄像头',
        model: props.settings.model,
        detection_mode: props.settings.detectionMode || 'single',
        task_type: props.settings.taskType || 'collision',
        conf: props.settings.conf,
        iou: props.settings.iou
      })
    })
    
    if (data.success) {
      rtspStreaming.value = true
      if (rtspInterval) clearInterval(rtspInterval)
      rtspInterval = setInterval(updateRTSPStatus, 300)
    } else {
      alert('启动失败: ' + (data.error || '未知错误'))
    }
  } catch (error) {
    alert('连接失败: ' + error.message)
  }
}

watch(
  () => [props.settings?.conf, props.settings?.iou, props.settings?.model, props.settings?.detectionMode, props.settings?.taskType],
  () => {
    if (rtspStreaming.value) {
      syncRTSPConfig()
    }
  }
)

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
    rtspFrameBase64.value = ''
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
      if (data.image) {
        rtspFrameBase64.value = data.image
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
.realtime-card {
  min-height: calc(100vh - 206px);
  padding: 30px;
}

.panel-title {
  font-size: 38px;
  line-height: 1.2;
  margin-bottom: 28px;
  color: var(--primary-cyan);
  font-weight: 700;
  display: flex;
  align-items: center;
}

.panel-title .scene-badge {
  display: inline-flex;
  align-items: center;
  min-height: 48px;
  margin-left: 18px;
  padding: 4px 22px;
  border: 2px solid rgba(0, 229, 255, 0.5);
  background: rgba(0, 229, 255, 0.1);
  color: var(--primary-cyan);
  font-size: 26px;
  font-weight: 800;
  border-radius: 6px;
}

.source-selector {
  margin-bottom: 28px;
  display: flex;
  justify-content: center;
  gap: 36px;
}

.source-selector label {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
  cursor: pointer;
  padding: 12px 24px;
  border-radius: 8px;
  background: rgba(0, 229, 255, 0.05);
  border: 2px solid rgba(0, 229, 255, 0.25);
  transition: all 0.2s ease;
}

.source-selector label:hover {
  border-color: var(--primary-cyan);
  background: rgba(0, 229, 255, 0.12);
}

.source-selector input[type="radio"] {
  width: 22px;
  height: 22px;
  accent-color: var(--primary-cyan);
  cursor: pointer;
}

.info-box-blue {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.08), rgba(3, 20, 36, 0.85));
  border: 2px solid var(--border-cyan);
  border-left: 6px solid var(--primary-cyan);
  border-radius: 10px;
  padding: 24px 30px;
  margin-bottom: 28px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.info-box-blue h4 {
  font-size: 30px;
  color: var(--primary-cyan);
  font-weight: 700;
  margin-bottom: 14px;
}

.info-box-blue p {
  font-size: 22px;
  color: var(--text-dim);
  line-height: 1.6;
  margin-bottom: 8px;
}

.input-group {
  margin-bottom: 28px;
}

.input-label {
  display: block;
  font-size: 30px;
  color: var(--primary-cyan);
  font-weight: 700;
  margin-bottom: 12px;
}

.cyber-input {
  width: 100%;
  padding: 16px 24px;
  font-size: 26px;
  font-weight: 700;
  font-family: monospace;
  background: rgba(0, 229, 255, 0.08);
  border: 2px solid var(--border-cyan);
  border-radius: 8px;
  color: #ffffff;
  outline: none;
  transition: all 0.2s ease;
}

.cyber-input:focus {
  border-color: var(--primary-cyan);
  box-shadow: 0 0 18px rgba(0, 229, 255, 0.5);
  background: rgba(0, 229, 255, 0.18);
}

.video-container {
  position: relative;
  background: #000000;
  border: 2px solid var(--border-cyan);
  border-radius: 12px;
  margin: 28px 0;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
}

video, .rtsp-stream {
  width: 100%;
  max-height: 650px;
  display: block;
}

.placeholder p {
  color: var(--text-dim);
  font-size: 30px;
  font-weight: 700;
  text-align: center;
}

.button-group {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 28px;
}

.button-group .btn {
  min-width: 200px;
  min-height: 58px;
  padding: 14px 38px;
  font-size: 24px;
  font-weight: 700;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  transition: all 0.2s ease;
}

.detection-info {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-top: 24px;
  margin-bottom: 28px;
}

.info-box {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.1), rgba(3, 20, 36, 0.85));
  border: 2px solid rgba(0, 229, 255, 0.35);
  border-left: 5px solid var(--primary-cyan);
  border-radius: 10px;
  padding: 20px 14px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
  transition: transform 0.2s ease, border-color 0.2s ease;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  min-width: 0;
}

.info-box:hover {
  transform: translateY(-3px);
  border-color: rgba(0, 229, 255, 0.6);
  box-shadow: 0 8px 24px rgba(0, 229, 255, 0.15);
}

.info-box h4 {
  color: var(--text-dim);
  margin-bottom: 10px;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.info-box .stat-value {
  color: var(--primary-cyan) !important;
  font-size: 32px;
  font-weight: 800;
  font-family: var(--font-main);
  text-shadow: 0 0 14px rgba(0, 229, 255, 0.45);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.info-box .stat-value.model-value {
  font-size: 24px;
}

.info-box .stat-value.time-val {
  font-size: 26px;
}

.stat-unit {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-dim);
  margin-left: 4px;
}

@media (max-width: 1200px) {
  .detection-info {
    grid-template-columns: repeat(3, 1fr);
  }
}

.detection-list {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  justify-content: center;
  margin-top: 24px;
}

.detection-badge {
  padding: 10px 22px;
  border-radius: 8px;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.4px;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
}

</style>
