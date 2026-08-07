<template>
  <div class="image-detection-container">
    <div class="card image-detection-card">
      <h3 class="panel-title">📷 图片检测 <span class="scene-badge">{{ pageModeLabel }}</span></h3>

      <!-- Upload Area -->
      <div v-if="!result && !loading" class="upload-center">
        <div
          class="upload-card"
          @click="fileInput.click()"
          @dragover.prevent="dragover = true"
          @dragleave.prevent="dragover = false"
          @drop.prevent="handleDrop"
          :class="{ dragover }"
        >
          <div class="upload-icon">☁️</div>
          <h3 class="upload-title">上传检测目标</h3>
          <p class="upload-subtitle">支持 JPG, PNG, WEBP（支持多文件批量检测）</p>
          <input
            type="file"
            ref="fileInput"
            accept="image/*"
            multiple
            style="display: none;"
            @change="handleFileChange"
          >
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="upload-center">
        <div class="loading-box">
          <div class="spinner"></div>
          <p class="scanning-text">{{ batchMode ? `批量检测中 (${progressText})...` : '算法检测中...' }}</p>
        </div>
      </div>

      <!-- Single Image Result Modal -->
      <div v-if="result && !loading && !isBatchResult" class="modal-overlay" @click.self="closeModal">
        <div class="modal-container">
          <div class="modal-header">
            <h2>检测结果</h2>
            <button class="btn-close" @click="closeModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="image-comparison">
              <div class="image-panel">
                <div class="panel-label">原图</div>
                <div class="image-wrapper">
                  <img :src="originalImage" class="compare-image">
                </div>
              </div>
              <div class="image-panel">
                <div class="panel-label">检测结果</div>
                <div class="image-wrapper">
                  <img :src="result.image" class="compare-image">
                </div>
              </div>
            </div>
            <div class="metrics-bar">
              <div class="metric-badge">
                <span class="metric-label">检测数量</span>
                <span class="metric-value">{{ result.count }}</span>
              </div>
              <div class="metric-badge">
                <span class="metric-label">推理时间</span>
                <span class="metric-value cyan">{{ result.inference_time }} s</span>
              </div>
            </div>
            <div v-if="hasModelBreakdown" class="model-breakdown">
              <div v-for="modelResult in result.models" :key="modelResult.model" class="model-breakdown-card">
                <div class="model-breakdown-head">
                  <span>{{ modelResult.task_label }}</span>
                  <strong>{{ modelResult.model_display_name }}</strong>
                </div>
                <div class="model-breakdown-meta">
                  <span>{{ modelResult.count }} 个目标</span>
                  <span>{{ modelResult.inference_time }} s</span>
                </div>
              </div>
            </div>
            <div v-if="result.detections.length > 0" class="detection-results">
              <div class="section-title">识别详情</div>
              <div class="detection-grid">
                <template v-for="(det, i) in result.detections" :key="i">
                  <template v-for="(label, labelIdx) in displayLabels(det)" :key="labelIdx">
                    <div class="detection-chip en-chip" :style="getClassStyle(primaryClass(det))">
                      <div class="chip-row">
                        <span class="chip-class">{{ label.class }}</span>
                        <span class="chip-conf">({{ formatConfidence(label.confidence) }})</span>
                      </div>
                    </div>
                    <div v-if="getClassChinese(label.class)" class="detection-chip zh-chip" :style="getClassStyle(primaryClass(det))">
                      <div class="chip-row">
                        <span class="chip-class">{{ getClassChinese(label.class) }}</span>
                      </div>
                    </div>
                  </template>
                </template>
              </div>
            </div>
            <div v-else class="no-detection">未发现可疑目标</div>
          </div>
          <div class="modal-footer">
            <ExportButtons
              :resultImageUrl="result.image"
              :detections="result.detections"
            />
            <button class="btn-reupload" @click="reset">重新上传</button>
            <button class="btn-confirm" @click="closeModal">确认</button>
          </div>
        </div>
      </div>

      <!-- Batch Result Grid -->
      <div v-if="result && !loading && isBatchResult" class="batch-results">
        <div class="batch-header">
          <h2>批量检测结果</h2>
          <span class="batch-summary">共 {{ result.total_files }} 个文件，总耗时 {{ result.total_inference_time }} s</span>
          <button class="btn-reupload" @click="reset">重新上传</button>
        </div>
        <div class="batch-grid">
          <div v-for="(item, i) in result.results" :key="i" class="card batch-card" @click="openBatchDetail(item)">
            <div class="batch-thumb-wrap">
              <img v-if="item.success" :src="item.image" class="batch-thumb">
              <div v-else class="batch-error-thumb">
                <span>检测失败</span>
              </div>
            </div>
            <div class="batch-info">
              <div class="batch-filename">{{ item.filename }}</div>
              <div class="batch-stats">
                <template v-if="item.success">
                  <span class="batch-count">{{ item.count }} 个目标</span>
                  <span class="batch-time">{{ item.inference_time }} s</span>
                </template>
                <span v-else class="batch-err">{{ item.error }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Batch Item Detail Modal -->
      <div v-if="batchDetail" class="modal-overlay" @click.self="batchDetail = null">
        <div class="modal-container">
          <div class="modal-header">
            <h2>{{ batchDetail.filename }}</h2>
            <button class="btn-close" @click="batchDetail = null">&times;</button>
          </div>
          <div class="modal-body">
            <div class="image-wrapper">
              <img :src="batchDetail.image" class="compare-image">
            </div>
            <div class="metrics-bar" style="margin-top: 16px">
              <div class="metric-badge">
                <span class="metric-label">检测数量</span>
                <span class="metric-value">{{ batchDetail.count }}</span>
              </div>
              <div class="metric-badge">
                <span class="metric-label">推理时间</span>
                <span class="metric-value cyan">{{ batchDetail.inference_time }} s</span>
              </div>
            </div>
            <div v-if="batchDetail.detections && batchDetail.detections.length > 0" class="detection-results">
              <div class="section-title">识别详情</div>
              <div class="detection-grid">
                <template v-for="(det, j) in batchDetail.detections" :key="j">
                  <template v-for="(label, labelIdx) in displayLabels(det)" :key="labelIdx">
                    <div class="detection-chip en-chip" :style="getClassStyle(primaryClass(det))">
                      <div class="chip-row">
                        <span class="chip-class">{{ label.class }}</span>
                        <span class="chip-conf">({{ formatConfidence(label.confidence) }})</span>
                      </div>
                    </div>
                    <div v-if="getClassChinese(label.class)" class="detection-chip zh-chip" :style="getClassStyle(primaryClass(det))">
                      <div class="chip-row">
                        <span class="chip-class">{{ getClassChinese(label.class) }}</span>
                      </div>
                    </div>
                  </template>
                </template>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <ExportButtons
              :resultImageUrl="batchDetail.image"
              :detections="batchDetail.detections"
            />
            <button class="btn-confirm" @click="batchDetail = null">确认</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ExportButtons from './ExportButtons.vue'
import { getClassStyle, getClassChinese, formatClassWithChinese } from '../utils/classColors'

const props = defineProps({
  settings: Object,
  availableModels: {
    type: Array,
    default: () => []
  },
  safeFetch: Function
})

const fileInput = ref(null)
const dragover = ref(false)
const loading = ref(false)
const result = ref(null)
const originalImage = ref(null)
const batchMode = ref(false)
const processedCount = ref(0)
const totalCount = ref(0)
const batchDetail = ref(null)

const isBatchResult = computed(() => result.value && result.value.total_files !== undefined && result.value.total_files > 1)
const hasModelBreakdown = computed(() => Array.isArray(result.value?.models) && result.value.models.length > 1)
const pageModeLabel = computed(() => {
  if (props.settings?.detectionMode === 'composite') return '综合事故检测'
  return props.settings?.taskType === 'hazmat' ? '油罐车泄露现场' : '客车追尾现场'
})
const progressText = computed(() => totalCount.value ? `${processedCount.value}/${totalCount.value}` : '')

const displayLabels = (det) => {
  if (Array.isArray(det?.merged_labels) && det.merged_labels.length) return det.merged_labels
  return [{ class: det?.class || '', confidence: det?.confidence || 0 }]
}

const primaryClass = (det) => det?.class || displayLabels(det)[0]?.class || ''

const formatConfidence = (confidence) => `${(Number(confidence || 0) * 100).toFixed(1)}%`

const handleFileChange = (e) => {
  const files = Array.from(e.target.files || [])
  if (files.length) processFiles(files)
}

const handleDrop = (e) => {
  dragover.value = false
  const files = Array.from(e.dataTransfer.files || [])
  if (files.length) processFiles(files)
}

const closeModal = () => {
  result.value = null
}

const reset = () => {
  result.value = null
  batchDetail.value = null
  if (originalImage.value) {
    URL.revokeObjectURL(originalImage.value)
    originalImage.value = null
  }
  if (fileInput.value) fileInput.value.value = ''
}

const openBatchDetail = (item) => {
  if (item.success) batchDetail.value = item
}

const processFiles = async (files) => {
  if (!files || files.length === 0) return

  const isSingleFile = files.length === 1
  batchMode.value = !isSingleFile
  loading.value = true

  const formData = new FormData()
  formData.append('model', props.settings.model)
  formData.append('detection_mode', props.settings.detectionMode || 'single')
  formData.append('task_type', props.settings.taskType || 'collision')
  formData.append('conf', props.settings.conf)
  formData.append('iou', props.settings.iou)

  if (isSingleFile) {
    const file = files[0]
    if (originalImage.value) URL.revokeObjectURL(originalImage.value)
    originalImage.value = URL.createObjectURL(file)
    formData.append('file', file)
  } else {
    totalCount.value = files.length
    processedCount.value = 0
    files.forEach(f => formData.append('files', f))
  }

  const endpoint = isSingleFile ? '/api/detect/image' : '/api/detect/batch'
  const errorMessage = isSingleFile ? '检测失败: ' : '批量检测失败: '

  try {
    const data = await props.safeFetch(endpoint, {
      method: 'POST',
      body: formData
    })
    if (data.success) {
      result.value = data
      if (!isSingleFile) {
        processedCount.value = data.total_files
      }
    }
  } catch (error) {
    alert(errorMessage + error.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.image-detection-container { height: 100%; }

.image-detection-card {
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

.scene-badge {
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

.upload-center {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  padding: 30px 0;
}

.upload-card {
  width: 100%;
  padding: 60px 30px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 3px dashed rgba(0, 229, 255, 0.4);
  background: rgba(0, 229, 255, 0.03);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-card:hover, .upload-card.dragover {
  background: rgba(0, 229, 255, 0.08);
  border-color: var(--primary-cyan);
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

.scanning-text {
  font-family: monospace;
  font-size: 28px;
  color: var(--primary-cyan);
  letter-spacing: 2px;
  margin-top: 20px;
}

/* Modal */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(6px);
  display: flex; justify-content: center; align-items: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease-out;
}
.modal-container {
  background: var(--card-bg-strong);
  border: 2px solid var(--border-cyan);
  border-radius: 14px;
  width: 95vw; max-width: 1450px; max-height: 92vh;
  overflow-y: auto;
  box-shadow: 0 0 60px rgba(0, 229, 255, 0.2);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 30px 40px;
  border-bottom: 2px solid rgba(0, 229, 255, 0.2);
}
.modal-header h2 { color: var(--primary-cyan); font-size: 36px; letter-spacing: 2px; margin: 0; }
.btn-close {
  background: transparent; border: 2px solid var(--border-cyan); color: var(--primary-cyan);
  width: 58px; height: 58px; border-radius: 50%; font-size: 32px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.btn-close:hover { background: rgba(0, 229, 255, 0.2); }
.modal-body { padding: 42px; }
.image-comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 36px; margin-bottom: 42px; }
.image-panel { display: flex; flex-direction: column; }
.panel-label {
  color: var(--primary-cyan); font-size: 24px; font-weight: 700; letter-spacing: 2px;
  margin-bottom: 18px; padding: 12px 28px;
  border: 2px solid rgba(0, 229, 255, 0.3); border-radius: 6px;
  background: rgba(0, 229, 255, 0.08);
  align-self: flex-start;
}
.image-wrapper {
  width: 100%; background: #000; border-radius: 10px; overflow: hidden;
  display: flex; justify-content: center; align-items: center; min-height: 350px;
  border: 2px solid rgba(0, 229, 255, 0.2);
}
.compare-image { max-width: 100%; max-height: 60vh; object-fit: contain; }
.metrics-bar { display: flex; gap: 28px; margin-bottom: 42px; }
.metric-badge {
  flex: 1;
  min-width: 0;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.1), rgba(3, 20, 36, 0.85));
  border: 2px solid rgba(0, 229, 255, 0.3);
  border-radius: 10px; padding: 24px 16px; text-align: center;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
}
.metric-label { display: block; font-size: 22px; color: var(--text-dim); letter-spacing: 1px; margin-bottom: 10px; font-weight: 600; white-space: nowrap; }
.metric-value {
  display: flex; align-items: center; justify-content: center;
  height: 48px; width: 100%;
  font-size: 32px; font-weight: 800;
  font-family: var(--font-main);
  color: #ffffff; line-height: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.metric-value.cyan { color: var(--primary-cyan) !important; text-shadow: 0 0 12px var(--primary-cyan); }
.detection-results { margin-bottom: 24px; }
.section-title {
  color: var(--primary-cyan); font-size: 28px; font-weight: 700; letter-spacing: 2px;
  margin-bottom: 20px; padding-bottom: 14px;
  border-bottom: 2px solid rgba(0, 229, 255, 0.2);
}
.detection-grid { display: flex; flex-wrap: wrap; gap: 16px; }
.detection-chip {
  border-radius: 8px; padding: 12px 24px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
.chip-row { display: flex; align-items: center; gap: 12px; }
.chip-class { color: inherit; font-size: 24px; font-weight: 700; }
.chip-conf { color: inherit; opacity: 0.95; font-size: 22px; font-family: var(--font-main); font-weight: 700; }
.no-detection { text-align: center; color: var(--text-dim); padding: 36px; font-size: 26px; }
.modal-footer {
  display: flex; justify-content: flex-end; align-items: center; gap: 20px;
  padding: 28px 42px; border-top: 2px solid rgba(0, 229, 255, 0.2);
}
.btn-reupload {
  background: transparent; border: 2px solid var(--border-cyan);
  color: var(--primary-cyan); padding: 14px 38px; border-radius: 8px;
  font-size: 24px; font-weight: 700; cursor: pointer;
}
.btn-reupload:hover { background: rgba(0, 229, 255, 0.15); }
.btn-confirm {
  background: var(--primary-cyan); border: none; color: #000;
  padding: 14px 44px; border-radius: 8px; font-size: 24px;
  font-weight: 700; cursor: pointer;
}
.btn-confirm:hover { box-shadow: 0 0 24px rgba(0, 229, 255, 0.4); }

/* Batch Results */
.batch-results {
  padding: 20px 0;
  animation: fadeIn 0.5s ease-out;
}
.batch-header {
  display: flex; align-items: center; gap: 28px;
  margin-bottom: 36px;
}
.batch-header h2 { color: var(--primary-cyan); font-size: 36px; letter-spacing: 2px; margin: 0; }
.batch-summary { color: var(--text-dim); font-size: 24px; flex: 1; }
.batch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 30px;
}
.batch-card {
  padding: 0;
  cursor: pointer;
  transition: all 0.3s;
  overflow: hidden;
  border: 2px solid var(--border-cyan);
}
.batch-card:hover {
  box-shadow: 0 0 30px rgba(0, 229, 255, 0.2);
  transform: translateY(-3px);
}
.batch-thumb-wrap {
  width: 100%; height: 280px;
  background: #000;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  border-bottom: 2px solid rgba(0, 229, 255, 0.2);
}
.batch-thumb {
  max-width: 100%; max-height: 100%;
  object-fit: contain;
}
.batch-error-thumb {
  color: #ff4444;
  font-size: 24px;
  text-align: center;
  padding: 30px;
}
.batch-info {
  padding: 24px;
}
.batch-filename {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 14px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.batch-stats {
  display: flex; justify-content: space-between; align-items: center;
}
.batch-count {
  font-size: 26px; color: var(--primary-cyan);
  font-family: monospace; font-weight: bold;
}
.batch-time {
  font-size: 22px; color: var(--text-dim);
  font-family: monospace;
}
.batch-err {
  font-size: 22px; color: #ff4444;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
