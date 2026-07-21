<template>
  <div class="card">
    <h3>🎬 视频抽帧检测</h3>
    <ModelMetricsPanel :settings="props.settings" :availableModels="props.availableModels" />
    
    <div class="upload-area" @click="fileInput.click()">
      <div class="upload-icon">🎥</div>
      <p style="font-size: 18px; margin-bottom: 10px;">点击上传视频文件</p>
      <p style="color: #888;">支持 MP4, AVI, MOV 格式</p>
      <input 
        type="file" 
        ref="fileInput" 
        accept="video/*" 
        style="display: none;" 
        @change="handleVideoUpload"
      >
    </div>

    <!-- Video Preview -->
    <div v-if="pendingVideoUrl" class="video-preview-section">
      <h4>📹 视频预览</h4>
      <video :src="pendingVideoUrl" controls class="preview-video"></video>
      <div v-if="!loading && !result" class="video-options">
        <label class="option-field">
          <span>抽帧间隔</span>
          <input v-model.number="frameInterval" type="number" min="1" max="600" step="1">
        </label>
        <div class="option-summary">
          当前模型：{{ props.settings.model || '未选择' }}，每 {{ normalizedInterval }} 帧检测一次
        </div>
      </div>
      <div v-if="!loading && !result" class="button-group">
        <button class="btn btn-primary" @click="startDetection">🚀 开始检测</button>
        <button class="btn btn-danger" @click="cancelUpload">❌ 取消</button>
      </div>
      <div v-if="result" class="button-group">
        <button class="btn btn-primary" @click="resetDetection">🔄 重新检测</button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>正在抽帧检测中，请稍候...</p>
    </div>

    <!-- Result State -->
    <div v-if="result && !loading" class="result-section">
      <h4>✅ 检测完成</h4>
      <div class="detection-info">
        <div class="info-box">
          <h4>视频总帧数</h4>
          <p class="stat-value">{{ result.total_frames }}</p>
        </div>
        <div class="info-box">
          <h4>抽样帧数</h4>
          <p class="stat-value">{{ result.sampled_frames }}</p>
        </div>
        <div class="info-box">
          <h4>平均帧处理时间</h4>
          <p class="stat-value">{{ result.avg_frame_time }} s</p>
        </div>
        <div class="info-box">
          <h4>检测到目标</h4>
          <p class="stat-value">{{ totalDetections }}</p>
        </div>
      </div>

      <div class="video-meta">
        <span>模型：{{ result.model || props.settings.model }}</span>
        <span>视频 FPS：{{ result.fps }}</span>
        <span>抽帧间隔：{{ result.interval }} 帧</span>
      </div>

      <h4 style="margin-top: 30px;">检测结果帧:</h4>
      <div class="frames-container">
        <div v-for="(frame, index) in result.frames" :key="index" class="frame-card">
          <h5>📸 第 {{ index + 1 }} 帧 (帧号: {{ frame.frame_number }})</h5>
          <div class="frame-info">
            <span>⏱️ 时间: {{ frame.time }}</span>
            <span>🎯 检测数: {{ frame.detection_count }}</span>
          </div>
          <img :src="frame.image" :alt="'Frame ' + frame.frame_number">
          <div v-if="frame.detections.length > 0" class="detection-list">
            <span 
              v-for="(det, detIdx) in frame.detections" 
              :key="detIdx" 
              class="detection-badge"
              :style="getClassStyle(det.class)"
            >
              {{ det.class }} ({{ (det.confidence * 100).toFixed(1) }}%)
            </span>
          </div>
          <p v-else class="no-detection">未检测到目标</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { getClassStyle } from '../utils/classColors'

const props = defineProps({
  settings: Object,
  availableModels: {
    type: Array,
    default: () => []
  },
  safeFetch: Function
})

const fileInput = ref(null)
const pendingVideoFile = ref(null)
const pendingVideoUrl = ref('')
const loading = ref(false)
const result = ref(null)
const frameInterval = ref(30)

const normalizedInterval = computed(() => {
  const value = Number(frameInterval.value) || 30
  return Math.min(Math.max(Math.floor(value), 1), 600)
})

const totalDetections = computed(() => {
  if (!result.value) return 0
  return result.value.frames.reduce((sum, frame) => sum + frame.detection_count, 0)
})

const handleVideoUpload = (e) => {
  const file = e.target.files[0]
  if (!file) return
  
  pendingVideoFile.value = file
  pendingVideoUrl.value = URL.createObjectURL(file)
  result.value = null
}

const cancelUpload = () => {
  pendingVideoFile.value = null
  pendingVideoUrl.value = ''
  fileInput.value.value = ''
}

const resetDetection = () => {
  cancelUpload()
  result.value = null
}

const startDetection = async () => {
  if (!pendingVideoFile.value) return

  loading.value = true
  result.value = null

  const formData = new FormData()
  formData.append('file', pendingVideoFile.value)
  formData.append('model', props.settings.model)
  formData.append('conf', props.settings.conf)
  formData.append('iou', props.settings.iou)
  formData.append('interval', normalizedInterval.value)

  try {
    const data = await props.safeFetch('/api/detect/video', {
      method: 'POST',
      body: formData
    })
    
    if (data.success) {
      result.value = data
    } else {
      alert('视频处理失败: ' + data.error)
    }
  } catch (error) {
    alert('视频处理失败: ' + error.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.video-preview-section {
  margin-top: 20px;
}

.preview-video {
  width: 100%;
  max-height: 400px;
  border-radius: 8px;
  margin: 10px 0;
}

.button-group {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.video-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 12px 0 18px;
  padding: 14px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.option-field {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
}

.option-field input {
  width: 96px;
  padding: 8px 10px;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
  font-size: 14px;
}

.option-summary,
.video-meta {
  color: #6b7280;
  font-size: 13px;
}

.video-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
}

.detection-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin: 20px 0;
}

.info-box {
  background: #f0f9ff;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #667eea;
}

.info-box h4 {
  color: #1f3a8a;
  margin-bottom: 5px;
  font-size: 14px;
}

.detection-info .info-box .stat-value {
  color: #000000 !important;
  font-size: 24px;
  font-weight: 800;
  text-shadow: none;
}

.frames-container {
  margin-top: 20px;
}

.frame-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.frame-card h5 {
  color: #667eea;
  margin-bottom: 10px;
  font-size: 16px;
}

.frame-card img {
  width: 100%;
  border-radius: 6px;
  margin-bottom: 10px;
}

.frame-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: #f9fafb;
  border-radius: 4px;
  margin-bottom: 10px;
  font-size: 14px;
  color: #666;
}

.detection-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.detection-badge {
  color: white;
  padding: 4px 12px;
  border: 1px solid transparent;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
}

.no-detection {
  color: #888;
  font-size: 14px;
}

.upload-area {
  border: 2px dashed #cbd5e0;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #667eea;
  background: #f7fafc;
}

.upload-icon {
  font-size: 60px;
  color: #cbd5e0;
  margin-bottom: 15px;
}
</style>
