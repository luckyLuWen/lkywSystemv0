<template>
  <div class="card video-detection-card">
    <h3 class="panel-title">🎬 视频抽帧检测 <span class="scene-badge">{{ pageModeLabel }}</span></h3>
    
    <!-- Upload Area -->
    <div class="upload-area" @click="fileInput.click()">
      <div class="upload-icon">🎥</div>
      <p class="upload-title">点击上传视频文件</p>
      <p class="upload-subtitle">支持 MP4, AVI, MOV 格式</p>
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
      <h4 class="section-subtitle">📹 视频预览</h4>
      <div class="preview-video-container">
        <video :src="pendingVideoUrl" controls class="preview-video"></video>
      </div>
      <div v-if="!loading && !result" class="video-options">
        <label class="option-field">
          <span>抽帧间隔</span>
          <input v-model.number="frameInterval" type="number" min="1" max="600" step="1">
        </label>
        <div class="option-summary">
          当前模型：<strong>{{ props.settings.model || '未选择' }}</strong>，每 <strong>{{ normalizedInterval }}</strong> 帧检测一次
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
      <p class="loading-text">正在抽帧检测中，请稍候...</p>
    </div>

    <!-- Result State -->
    <div v-if="result && !loading" class="result-section">
      <h4 class="section-subtitle cyan-title">✅ 检测完成</h4>
      <div class="detection-info">
        <div class="info-box">
          <h4>抽样帧数</h4>
          <p class="stat-value">{{ result.sampled_frames }}</p>
        </div>
        <div class="info-box">
          <h4>检测到目标的帧数</h4>
          <p class="stat-value">{{ framesWithDetections }}</p>
        </div>
        <div class="info-box">
          <h4>平均帧处理时间</h4>
          <p class="stat-value">{{ result.avg_frame_time }}<span class="stat-unit">s</span></p>
        </div>
        <div class="info-box">
          <h4>模型</h4>
          <p class="stat-value model-value">{{ result.model || props.settings.model }}</p>
        </div>
        <div class="info-box">
          <h4>抽帧间隔</h4>
          <p class="stat-value">{{ result.interval }}<span class="stat-unit">帧</span></p>
        </div>
      </div>

      <h4 class="section-subtitle">📸 检测结果帧:</h4>
      <div class="frames-container">
        <div v-for="(frame, index) in result.frames" :key="index" class="frame-card">
          <div class="frame-header">
            <h5 class="frame-title">🎬 第 {{ index + 1 }} 帧 <span class="frame-num">(帧号: {{ frame.frame_number }})</span></h5>
            <div class="frame-info">
              <span class="frame-info-item">⏱️ 时间: <strong>{{ frame.time }}s</strong></span>
              <span class="frame-info-item">🎯 检测数: <strong class="count-highlight">{{ frame.detection_count }}</strong></span>
            </div>
          </div>
          <div class="frame-image-wrapper">
            <img :src="frame.image" :alt="'Frame ' + frame.frame_number">
          </div>
          <div v-if="frame.detections.length > 0" class="detection-list">
            <template v-for="(det, detIdx) in frame.detections" :key="detIdx">
              <template v-for="(label, labelIdx) in displayLabels(det)" :key="labelIdx">
                <span 
                  class="detection-badge en-badge"
                  :style="getClassStyle(primaryClass(det))"
                >
                  {{ label.class }} ({{ formatConfidencePercent(label.confidence) }})
                </span>
                <span 
                  v-if="getClassChinese(label.class)" 
                  class="detection-badge zh-badge"
                  :style="getClassStyle(primaryClass(det))"
                >
                  {{ getClassChinese(label.class) }}
                </span>
              </template>
            </template>
          </div>
          <p v-else class="no-detection">未检测到目标</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { getClassStyle, getClassChinese } from '../utils/classColors'

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

const totalDetections = computed(() => {
  if (!result.value) return 0
  return result.value.frames.reduce((sum, frame) => sum + frame.detection_count, 0)
})

const framesWithDetections = computed(() => {
  if (!result.value?.frames) return 0
  return result.value.frames.filter(frame => frame.detection_count > 0).length
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
  formData.append('detection_mode', props.settings.detectionMode || 'single')
  formData.append('task_type', props.settings.taskType || 'collision')
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
.video-detection-card {
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

.upload-area {
  border: 3px dashed rgba(0, 229, 255, 0.4);
  background: rgba(0, 229, 255, 0.03);
  border-radius: 12px;
  padding: 60px 30px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-area:hover {
  border-color: var(--primary-cyan);
  background: rgba(0, 229, 255, 0.08);
  box-shadow: 0 0 30px rgba(0, 229, 255, 0.2);
}

.upload-icon {
  font-size: 90px;
  margin-bottom: 20px;
  filter: drop-shadow(0 0 12px rgba(0, 229, 255, 0.5));
}

.upload-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}

.upload-subtitle {
  font-size: 22px;
  color: var(--text-dim);
  letter-spacing: 0.5px;
}

.video-preview-section {
  margin-top: 30px;
}

.section-subtitle {
  font-size: 32px;
  color: var(--primary-cyan);
  font-weight: 700;
  margin: 30px 0 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-subtitle.cyan-title {
  color: var(--primary-cyan);
  text-shadow: 0 0 14px rgba(0, 229, 255, 0.4);
}

.preview-video-container {
  width: 100%;
  background: #000000;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid var(--border-cyan);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
}

.preview-video {
  width: 100%;
  max-height: 520px;
  display: block;
}

.video-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 24px;
  margin: 24px 0 30px;
  padding: 24px 30px;
  background: rgba(3, 20, 36, 0.92);
  border: 2px solid var(--border-cyan);
  border-radius: 10px;
  box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.08);
}

.option-field {
  display: flex;
  align-items: center;
  gap: 16px;
  color: var(--text-main);
  font-size: 24px;
  font-weight: 700;
}

.option-field input {
  width: 140px;
  padding: 10px 16px;
  background: rgba(0, 229, 255, 0.1);
  border: 2px solid var(--border-cyan);
  border-radius: 8px;
  color: #ffffff;
  font-size: 24px;
  font-weight: 700;
  font-family: monospace;
  text-align: center;
  outline: none;
  transition: all 0.2s ease;
}

.option-field input:focus {
  border-color: var(--primary-cyan);
  box-shadow: 0 0 16px rgba(0, 229, 255, 0.5);
  background: rgba(0, 229, 255, 0.2);
}

.option-summary {
  color: var(--text-dim);
  font-size: 22px;
  font-weight: 500;
  letter-spacing: 0.3px;
}

.option-summary strong {
  color: var(--primary-cyan);
  font-size: 24px;
  font-weight: 700;
}

.button-group {
  display: flex;
  gap: 24px;
  justify-content: center;
  margin-top: 24px;
}

.button-group .btn {
  min-width: 180px;
  min-height: 58px;
  padding: 14px 36px;
  font-size: 24px;
  font-weight: 700;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  transition: all 0.2s ease;
}

.loading {
  text-align: center;
  padding: 50px 20px;
}

.loading-text {
  font-family: monospace;
  font-size: 26px;
  color: var(--primary-cyan);
  letter-spacing: 1px;
  margin-top: 20px;
}

.result-section {
  margin-top: 36px;
  animation: fadeIn 0.4s ease-out;
}

.detection-info {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin: 24px 0 30px;
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

.detection-info .info-box .stat-value {
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

.detection-info .info-box .stat-value.model-value {
  font-size: 24px;
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

.frames-container {
  margin-top: 24px;
}

.frame-card {
  background: rgba(3, 20, 36, 0.88);
  border: 2px solid var(--border-cyan);
  border-radius: 12px;
  padding: 28px;
  margin-bottom: 30px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.frame-card:hover {
  border-color: rgba(0, 229, 255, 0.6);
  box-shadow: 0 10px 36px rgba(0, 229, 255, 0.15);
}

.frame-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 18px;
}

.frame-title {
  color: var(--primary-cyan);
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.frame-num {
  font-size: 22px;
  color: var(--text-dim);
  font-weight: 500;
}

.frame-info {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 24px;
  background: rgba(0, 229, 255, 0.08);
  border: 2px solid rgba(0, 229, 255, 0.25);
  border-radius: 8px;
  font-size: 22px;
  color: var(--text-dim);
}

.frame-info-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.frame-info-item strong {
  color: #ffffff;
  font-size: 24px;
  font-family: monospace;
}

.frame-info-item .count-highlight {
  color: var(--accent-amber);
  font-size: 24px;
  font-weight: 700;
}

.frame-image-wrapper {
  width: 100%;
  background: #000000;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 20px;
  border: 2px solid rgba(0, 229, 255, 0.2);
}

.frame-image-wrapper img {
  width: 100%;
  display: block;
  object-fit: contain;
  max-height: 70vh;
}

.detection-list {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 16px;
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

.no-detection {
  color: var(--text-muted);
  font-size: 22px;
  padding: 16px;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
