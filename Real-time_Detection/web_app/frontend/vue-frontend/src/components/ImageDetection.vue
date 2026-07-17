<template>
  <div class="image-detection-container">
    <ModelMetricsPanel :settings="props.settings" :availableModels="props.availableModels" />

    <!-- Upload Area -->
    <div v-if="!result && !loading" class="upload-center">
      <div
        class="card upload-card"
        @click="fileInput.click()"
        @dragover.prevent="dragover = true"
        @dragleave.prevent="dragover = false"
        @drop.prevent="handleDrop"
        :class="{ dragover }"
      >
        <div class="upload-icon">☁️</div>
        <h3>上传检测目标</h3>
        <p>支持 JPG, PNG, WEBP（支持多文件批量检测）</p>
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
              <span class="metric-value cyan">{{ result.count }}</span>
            </div>
            <div class="metric-badge">
              <span class="metric-label">推理时间</span>
              <span class="metric-value">{{ result.inference_time }} s</span>
            </div>
          </div>
          <div v-if="result.detections.length > 0" class="detection-results">
            <div class="section-title">识别详情</div>
            <div class="detection-grid">
              <div v-for="(det, i) in result.detections" :key="i" class="detection-chip" :style="getClassStyle(det.class)">
                <span class="chip-class">{{ det.class }}</span>
                <span class="chip-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
              </div>
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
              <span class="metric-value cyan">{{ batchDetail.count }}</span>
            </div>
            <div class="metric-badge">
              <span class="metric-label">推理时间</span>
              <span class="metric-value">{{ batchDetail.inference_time }} s</span>
            </div>
          </div>
          <div v-if="batchDetail.detections.length > 0" class="detection-results">
            <div class="section-title">识别详情</div>
            <div class="detection-grid">
              <div v-for="(det, j) in batchDetail.detections" :key="j" class="detection-chip" :style="getClassStyle(det.class)">
                <span class="chip-class">{{ det.class }}</span>
                <span class="chip-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
              </div>
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
</template>

<script setup>
import { ref, computed } from 'vue'
import ExportButtons from './ExportButtons.vue'
import ModelMetricsPanel from './ModelMetricsPanel.vue'
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
const dragover = ref(false)
const loading = ref(false)
const result = ref(null)
const originalImage = ref(null)
const batchMode = ref(false)
const processedCount = ref(0)
const totalCount = ref(0)
const batchDetail = ref(null)

const isBatchResult = computed(() => result.value && result.value.total_files !== undefined && result.value.total_files > 1)
const progressText = computed(() => totalCount.value ? `${processedCount.value}/${totalCount.value}` : '')

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
  if (files.length === 0) return

  if (files.length === 1) {
    // Single file — use existing endpoint
    const file = files[0]
    if (originalImage.value) URL.revokeObjectURL(originalImage.value)
    originalImage.value = URL.createObjectURL(file)
    batchMode.value = false

    loading.value = true
    const formData = new FormData()
    formData.append('file', file)
    formData.append('model', props.settings.model)
    formData.append('conf', props.settings.conf)
    formData.append('iou', props.settings.iou)

    try {
      const data = await props.safeFetch('/api/detect/image', {
        method: 'POST',
        body: formData
      })
      if (data.success) result.value = data
    } catch (error) {
      alert('检测失败: ' + error.message)
    } finally {
      loading.value = false
    }
  } else {
    // Multiple files — use batch endpoint
    batchMode.value = true
    totalCount.value = files.length
    processedCount.value = 0

    loading.value = true
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    formData.append('model', props.settings.model)
    formData.append('conf', props.settings.conf)
    formData.append('iou', props.settings.iou)

    try {
      const data = await props.safeFetch('/api/detect/batch', {
        method: 'POST',
        body: formData
      })
      if (data.success) {
        processedCount.value = data.total_files
        result.value = data
      }
    } catch (error) {
      alert('批量检测失败: ' + error.message)
    } finally {
      loading.value = false
    }
  }
}
</script>

<style scoped>
.image-detection-container { height: 100%; }
.upload-center {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}
.upload-card {
  width: 840px; height: 510px;
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  border: 1px dashed var(--border-cyan);
  background: rgba(0, 229, 255, 0.02);
  cursor: pointer;
  transition: all 0.3s;
}
.upload-card:hover, .upload-card.dragover {
  background: rgba(0, 229, 255, 0.08);
  border-style: solid;
  box-shadow: 0 0 30px rgba(0, 229, 255, 0.1);
}
.upload-icon { font-size: 108px; margin-bottom: 36px; opacity: 0.5; }
.scanning-text { font-family: monospace; font-size: 24px; color: var(--primary-cyan); letter-spacing: 2px; margin-top: 16px; }

/* Modal */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex; justify-content: center; align-items: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease-out;
}
.modal-container {
  background: var(--card-bg);
  border: 1px solid var(--border-cyan);
  border-radius: 12px;
  width: 95vw; max-width: 1400px; max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 0 60px rgba(0, 229, 255, 0.15);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 30px 36px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
}
.modal-header h2 { color: var(--primary-cyan); font-size: 30px; letter-spacing: 2px; margin: 0; }
.btn-close {
  background: transparent; border: 1px solid var(--border-cyan); color: var(--primary-cyan);
  width: 54px; height: 54px; border-radius: 50%; font-size: 30px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.btn-close:hover { background: rgba(0, 229, 255, 0.15); }
.modal-body { padding: 42px; }
.image-comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 36px; margin-bottom: 42px; }
.image-panel { display: flex; flex-direction: column; }
.panel-label {
  color: var(--primary-cyan); font-size: 21px; letter-spacing: 2px;
  margin-bottom: 16px; padding: 12px 24px;
  border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 4px;
  align-self: flex-start;
}
.image-wrapper {
  width: 100%; background: #000; border-radius: 8px; overflow: hidden;
  display: flex; justify-content: center; align-items: center; min-height: 300px;
}
.compare-image { max-width: 100%; max-height: 60vh; object-fit: contain; }
.metrics-bar { display: flex; gap: 24px; margin-bottom: 42px; }
.metric-badge {
  flex: 1; background: rgba(0, 229, 255, 0.05);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 8px; padding: 30px; text-align: center;
}
.metric-label { display: block; font-size: 19px; color: var(--text-dim); letter-spacing: 1px; margin-bottom: 12px; }
.metric-value { display: block; font-size: 42px; font-weight: bold; font-family: monospace; }
.metric-value.cyan { color: var(--primary-cyan); text-shadow: 0 0 8px var(--primary-cyan); }
.detection-results { margin-bottom: 20px; }
.section-title {
  color: var(--primary-cyan); font-size: 21px; letter-spacing: 2px;
  margin-bottom: 16px; padding-bottom: 14px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
}
.detection-grid { display: flex; flex-wrap: wrap; gap: 14px; }
.detection-chip {
  background: rgba(255, 193, 7, 0.08);
  border: 1px solid rgba(255, 193, 7, 0.25);
  border-radius: 8px; padding: 14px 24px;
  display: flex; align-items: center; gap: 14px;
}
.chip-class { color: inherit; font-size: 22px; font-weight: 700; }
.chip-conf { color: inherit; opacity: 0.9; font-size: 19px; font-family: monospace; }
.no-detection { text-align: center; color: var(--text-dim); padding: 36px; font-size: 22px; }
.modal-footer {
  display: flex; justify-content: flex-end; align-items: center; gap: 18px;
  padding: 27px 42px; border-top: 1px solid rgba(0, 229, 255, 0.1);
}
.btn-reupload {
  background: transparent; border: 1px solid var(--border-cyan);
  color: var(--primary-cyan); padding: 15px 36px; border-radius: 8px;
  font-size: 21px; cursor: pointer;
}
.btn-reupload:hover { background: rgba(0, 229, 255, 0.1); }
.btn-confirm {
  background: var(--primary-cyan); border: none; color: #000;
  padding: 15px 42px; border-radius: 8px; font-size: 21px;
  font-weight: 600; cursor: pointer;
}
.btn-confirm:hover { box-shadow: 0 0 20px rgba(0, 229, 255, 0.3); }

/* Batch Results */
.batch-results {
  padding: 15px 0;
  animation: fadeIn 0.5s ease-out;
}
.batch-header {
  display: flex; align-items: center; gap: 24px;
  margin-bottom: 36px;
}
.batch-header h2 { color: var(--primary-cyan); font-size: 30px; letter-spacing: 2px; margin: 0; }
.batch-summary { color: var(--text-dim); font-size: 21px; flex: 1; }
.batch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 30px;
}
.batch-card {
  padding: 0;
  cursor: pointer;
  transition: all 0.3s;
  overflow: hidden;
}
.batch-card:hover {
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.15);
  transform: translateY(-2px);
}
.batch-thumb-wrap {
  width: 100%; height: 270px;
  background: #000;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
}
.batch-thumb {
  max-width: 100%; max-height: 100%;
  object-fit: contain;
}
.batch-error-thumb {
  color: #ff4444;
  font-size: 21px;
  text-align: center;
  padding: 30px;
}
.batch-info {
  padding: 21px 24px;
}
.batch-filename {
  font-size: 21px;
  color: var(--text-main);
  margin-bottom: 12px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.batch-stats {
  display: flex; justify-content: space-between; align-items: center;
}
.batch-count {
  font-size: 22px; color: var(--primary-cyan);
  font-family: monospace; font-weight: bold;
}
.batch-time {
  font-size: 19px; color: var(--text-dim);
  font-family: monospace;
}
.batch-err {
  font-size: 19px; color: #ff4444;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
