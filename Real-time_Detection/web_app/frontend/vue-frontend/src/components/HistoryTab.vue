<template>
  <div class="history-container">
    <div class="history-toolbar card">
      <div class="filter-field">
        <label>模型名称</label>
        <select v-model="filters.model">
          <option value="">全部模型</option>
          <option v-for="model in modelOptions" :key="model" :value="model">{{ model }}</option>
        </select>
      </div>
      <div class="filter-field label-field">
        <label>检测标签</label>
        <select v-model="filters.label">
          <option value="">全部标签</option>
          <option v-for="label in labelOptions" :key="label" :value="label">{{ label }}</option>
        </select>
      </div>
      <div class="filter-field source-field">
        <label>检测类型</label>
        <select v-model="filters.sourceType">
          <option value="">全部类型</option>
          <option value="image">image</option>
          <option value="video">video</option>
        </select>
      </div>
      <div class="filter-actions">
        <button class="btn-filter primary" @click="loadRecords">查询</button>
        <button class="btn-filter" @click="resetFilters">重置</button>
      </div>
    </div>

    <div v-if="loading" class="upload-center">
      <div class="loading-box">
        <div class="spinner"></div>
        <p class="scanning-text">加载记录中...</p>
      </div>
    </div>

    <div v-else-if="records.length === 0" class="upload-center">
      <div class="card upload-card">
        <div class="upload-icon">📋</div>
        <h3>{{ hasActiveFilters ? '未查询到匹配记录' : '暂无检测记录' }}</h3>
        <p>{{ hasActiveFilters ? '请调整模型名称或检测标签后重试' : '完成检测后，记录将显示在此处' }}</p>
      </div>
    </div>

    <div v-else class="records-list">
      <div
        v-for="rec in records"
        :key="rec.id"
        class="record-card card"
        @click="openDetail(rec.id)"
      >
        <img
          :src="`${apiUrl}/api/results/${rec.result_filename}`"
          class="record-thumb"
          @error="$event.target.style.display='none'"
        >
        <div class="record-info">
          <div class="record-time">{{ formatTime(rec.timestamp) }}</div>
          <div class="record-meta">
            <span class="meta-tag task-tag">{{ displayTaskLabel(rec) }}</span>
            <span
              v-for="model in displayModelNames(rec)"
              :key="`${rec.id}-${model}`"
              class="meta-tag model-tag"
            >{{ model }}</span>
            <span class="meta-tag source-tag">{{ rec.source_type }}</span>
          </div>
          <div class="record-labels" v-if="rec.labels && rec.labels.length">
            <span v-for="label in rec.labels" :key="label" class="label-chip">{{ label }}</span>
          </div>
        </div>
        <div class="record-stats">
          <span class="stat-count">{{ rec.detection_count }}</span>
          <span class="stat-label">个目标</span>
        </div>
        <div class="record-time-s">{{ rec.inference_time_s }} s</div>
        <button class="btn-delete-record" @click.stop="deleteRecord(rec.id)">删除</button>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="detail" class="modal-overlay" @click.self="closeDetail">
      <div class="modal-container">
        <div class="modal-header">
          <h2>检测详情</h2>
          <button class="btn-close" @click="closeDetail">&times;</button>
        </div>
        <div class="modal-body">
          <template v-if="isVideoDetail">
            <div class="video-detail-layout">
              <div class="video-source-panel">
                <div class="panel-label">原视频</div>
                <video :src="`${apiUrl}/api/uploads/${detail.saved_filename}`" controls class="detail-video"></video>
              </div>
              <div class="video-frames-panel">
                <div class="panel-label">检测到目标的帧</div>
                <div v-if="videoFrameGroups.length" class="video-frame-grid">
                  <button
                    v-for="frame in videoFrameGroups"
                    :key="frame.key"
                    type="button"
                    class="video-frame-card"
                    @click="selectedVideoFrame = frame"
                  >
                    <img :src="`${apiUrl}/api/results/${frame.filename}`" class="video-frame-image">
                    <div class="frame-card-meta">
                      <strong>{{ frame.title }}</strong>
                      <span>{{ formatFrameTime(frame.time_s) }}</span>
                    </div>
                    <div class="frame-labels">
                      <span v-for="(det, i) in frame.detections" :key="`${frame.key}-${i}`" class="frame-label-chip">
                        {{ det.class }} {{ formatConfidence(det.confidence) }}
                      </span>
                    </div>
                  </button>
                </div>
                <div v-else class="no-detection video-empty">未发现可疑目标帧</div>
              </div>
            </div>

            <div class="metrics-bar video-metrics">
              <div class="metric-badge">
                <span class="metric-label">推理时间</span>
                <span class="metric-value">{{ detail.inference_time_s }} s</span>
              </div>
              <div class="metric-badge">
                <span class="metric-label">检测任务</span>
                <span class="metric-value small">{{ displayTaskLabel(detail) }}</span>
              </div>
              <div class="metric-badge">
                <span class="metric-label">模型</span>
                <span class="metric-value small model-list-text">{{ displayModelNames(detail).join(' / ') }}</span>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="image-comparison">
              <div class="image-panel">
                <div class="panel-label">原图</div>
                <div class="image-wrapper">
                  <img :src="`${apiUrl}/api/uploads/${detail.saved_filename}`" class="compare-image">
                </div>
              </div>
              <div class="image-panel">
                <div class="panel-label">检测结果</div>
                <div class="image-wrapper">
                  <img :src="`${apiUrl}/api/results/${detail.result_filename}`" class="compare-image">
                </div>
              </div>
            </div>

            <div class="metrics-bar">
              <div class="metric-badge">
                <span class="metric-label">检测数量</span>
                <span class="metric-value cyan">{{ detail.detection_count }}</span>
              </div>
              <div class="metric-badge">
                <span class="metric-label">推理时间</span>
                <span class="metric-value">{{ detail.inference_time_s }} s</span>
              </div>
              <div class="metric-badge">
                <span class="metric-label">检测任务</span>
                <span class="metric-value small">{{ displayTaskLabel(detail) }}</span>
              </div>
              <div class="metric-badge">
                <span class="metric-label">模型</span>
                <span class="metric-value small model-list-text">{{ displayModelNames(detail).join(' / ') }}</span>
              </div>
            </div>

            <div v-if="detail.detections.length > 0" class="detection-results">
              <div class="section-title">识别详情</div>
              <div class="detection-grid">
                <div v-for="(det, i) in detail.detections" :key="i" class="detection-chip">
                  <span class="chip-class">{{ det.class }}</span>
                  <span class="chip-conf">{{ formatConfidence(det.confidence) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="no-detection">未发现可疑目标</div>
          </template>
        </div>
        <div v-if="selectedVideoFrame" class="frame-zoom-overlay" @click.self="selectedVideoFrame = null">
          <div class="frame-zoom-panel">
            <div class="frame-zoom-head">
              <strong>{{ selectedVideoFrame.title }} · {{ formatFrameTime(selectedVideoFrame.time_s) }}</strong>
              <button class="btn-close small" @click="selectedVideoFrame = null">&times;</button>
            </div>
            <img :src="`${apiUrl}/api/results/${selectedVideoFrame.filename}`" class="frame-zoom-image">
            <div class="frame-labels zoom-labels">
              <span v-for="(det, i) in selectedVideoFrame.detections" :key="`zoom-${i}`" class="frame-label-chip">
                {{ det.class }} {{ formatConfidence(det.confidence) }}
              </span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <ExportButtons
            :resultImageUrl="`${apiUrl}/api/results/${detail.result_filename}`"
            :detections="detail.detections"
          />
          <button class="btn-confirm" @click="closeDetail">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import ExportButtons from './ExportButtons.vue'

const props = defineProps({
  safeFetch: Function,
  apiUrl: String
})

const loading = ref(false)
const records = ref([])
const detail = ref(null)
const selectedVideoFrame = ref(null)

const modelOptions = [
  'SFGA-YOLO26M', 'YOLO26M', 'YOLO11M',
  'LCA-YOLO26N', 'YOLO26N', 'YOLO11N'
]
const labelOptions = ['car_fire', 'lkyw_fire', 'car_nofire', 'lkyw_nofire', 'leak', 'noleak']
const filters = reactive({
  model: '',
  label: '',
  sourceType: ''
})

const hasActiveFilters = computed(() => Boolean(filters.model || filters.label || filters.sourceType))

const formatTime = (ts) => {
  if (!ts) return ''
  return ts.replace('T', ' ').substring(0, 19)
}

const COMPOSITE_MODEL_PARTS = {
  'SFGA-YOLO26M+LCA-YOLO26N': ['SFGA-YOLO26M', 'LCA-YOLO26N'],
  '综合事故检测': ['SFGA-YOLO26M', 'LCA-YOLO26N']
}

const displayModelNames = (record) => {
  if (Array.isArray(record?.model_names) && record.model_names.length) return record.model_names
  const modelName = record?.model_name || ''
  if (COMPOSITE_MODEL_PARTS[modelName]) return COMPOSITE_MODEL_PARTS[modelName]
  return modelName ? [modelName] : ['未知模型']
}

const displayModelName = (record) => displayModelNames(record).join(' / ')

const displayTaskLabel = (record) => {
  if (record?.task_label && record.task_label !== '检测任务') return record.task_label
  const modelNames = displayModelNames(record)
  if (modelNames.includes('SFGA-YOLO26M') && modelNames.includes('LCA-YOLO26N')) return '综合事故检测'
  if (modelNames.some(name => ['LCA-YOLO26N', 'YOLO26N', 'YOLO11N'].includes(name))) return '油罐车泄露现场'
  if (modelNames.some(name => ['SFGA-YOLO26M', 'YOLO26M', 'YOLO11M'].includes(name))) return '货车追尾现场'
  return '检测任务'
}

const isVideoDetail = computed(() => detail.value?.source_type === 'video')

const formatConfidence = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`

const formatFrameTime = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)} s` : '--'
}

const inferFrameFilename = (detection) => {
  if (detection?.frame_filename) return detection.frame_filename
  if (detection?.result_filename) return detection.result_filename
  const frameNumber = detection?.frame_number
  const prefix = String(detail.value?.saved_filename || '').match(/^(\d{8}_\d{6})/)?.[1]
  if (prefix && frameNumber !== undefined && frameNumber !== null) return `frame_${prefix}_${frameNumber}.jpg`
  return detail.value?.result_filename || ''
}

const videoFrameGroups = computed(() => {
  if (!isVideoDetail.value) return []
  const groups = new Map()
  for (const detection of detail.value?.detections || []) {
    const frameNumber = detection.frame_number ?? 'unknown'
    const filename = inferFrameFilename(detection)
    const key = `${frameNumber}-${filename}`
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        frame_number: frameNumber,
        time_s: detection.time_s,
        filename,
        title: frameNumber === 'unknown' ? '检测帧' : `第 ${frameNumber} 帧`,
        detections: []
      })
    }
    groups.get(key).detections.push(detection)
  }
  return Array.from(groups.values()).filter(frame => frame.filename)
})

const closeDetail = () => {
  detail.value = null
  selectedVideoFrame.value = null
}

const buildHistoryQuery = () => {
  const params = new URLSearchParams({ limit: '50' })
  if (filters.model) params.set('model', filters.model)
  if (filters.label) params.set('label', filters.label)
  if (filters.sourceType) params.set('source_type', filters.sourceType)
  return params.toString()
}

const loadRecords = async () => {
  loading.value = true
  try {
    const data = await props.safeFetch(`/api/history?${buildHistoryQuery()}`)
    if (data.success) records.value = data.records
  } catch (e) {
    alert('加载历史记录失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.model = ''
  filters.label = ''
  filters.sourceType = ''
  loadRecords()
}

const openDetail = async (id) => {
  selectedVideoFrame.value = null
  try {
    const data = await props.safeFetch(`/api/history/${id}`)
    if (data.success) detail.value = data.record
  } catch (e) {
    alert('加载详情失败: ' + e.message)
  }
}

const deleteRecord = async (id) => {
  if (!confirm('确认删除这条检测历史记录？')) return
  try {
    const data = await props.safeFetch(`/api/history/${id}`, { method: 'DELETE' })
    if (data.success) {
      if (detail.value?.id === id) detail.value = null
      records.value = records.value.filter((record) => record.id !== id)
    }
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

onMounted(loadRecords)
</script>

<style scoped>
.history-container {
  height: 100%;
  overflow-y: auto;
}

.history-toolbar {
  display: grid;
  grid-template-columns: 260px minmax(240px, 1fr) 180px auto;
  gap: 18px;
  align-items: end;
  padding: 18px 22px;
  margin-bottom: 14px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-field label {
  color: var(--text-dim);
  font-size: 17px;
  letter-spacing: 1px;
}

.filter-field select,
.filter-field input {
  height: 46px;
  border-radius: 6px;
  border: 1px solid rgba(0, 229, 255, 0.22);
  background: rgba(2, 8, 23, 0.72);
  color: var(--text-main);
  padding: 0 14px;
  font-size: 19px;
  outline: none;
}

.filter-field select:focus,
.filter-field input:focus {
  border-color: var(--primary-cyan);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.18);
}

.filter-actions {
  display: flex;
  gap: 10px;
}

.btn-filter {
  height: 46px;
  min-width: 86px;
  border-radius: 6px;
  border: 1px solid rgba(0, 229, 255, 0.28);
  background: rgba(0, 229, 255, 0.08);
  color: var(--primary-cyan);
  font-size: 18px;
  cursor: pointer;
}

.btn-filter.primary {
  background: var(--primary-cyan);
  color: #001018;
  border-color: var(--primary-cyan);
  font-weight: 700;
}

.records-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: calc(100vh - 180px);
  overflow-y: auto;
}

.record-card {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 18px 24px;
  cursor: pointer;
  transition: all 0.3s;
}

.record-card:hover {
  background: rgba(0, 229, 255, 0.05);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.1);
}

.record-thumb {
  width: 150px;
  height: 112px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid rgba(0, 229, 255, 0.2);
  background: #000;
}

.record-info {
  flex: 1;
}

.record-time {
  font-size: 22px;
  color: var(--text-main);
  margin-bottom: 8px;
}

.record-meta {
  display: flex;
  gap: 9px;
  flex-wrap: wrap;
}

.record-labels {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.label-chip {
  font-size: 22px;
  color: var(--accent-amber);
  border: 1px solid rgba(255, 193, 7, 0.28);
  background: rgba(255, 193, 7, 0.08);
  padding: 6px 13px;
  border-radius: 999px;
  font-weight: 700;
}

.meta-tag {
  font-size: 27px;
  color: var(--text-dim);
  background: rgba(0, 229, 255, 0.08);
  padding: 5px 12px;
  border-radius: 3px;
}

.meta-tag.model-tag {
  color: var(--text-main);
  max-width: 520px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-tag.task-tag {
  color: var(--accent-amber);
  border: 1px solid rgba(255, 193, 7, 0.24);
  background: rgba(255, 193, 7, 0.08);
}

.meta-tag.source-tag {
  font-size: 24px;
}

.record-stats {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-count {
  font-size: 42px;
  font-weight: bold;
  color: var(--primary-cyan);
  font-family: monospace;
  text-shadow: 0 0 5px var(--primary-cyan);
}

.stat-label {
  font-size: 19px;
  color: var(--text-dim);
}

.record-time-s {
  font-size: 21px;
  color: var(--text-dim);
  font-family: monospace;
  min-width: 135px;
  text-align: right;
}

.btn-delete-record {
  flex: 0 0 auto;
  border: 1px solid rgba(239, 68, 68, 0.46);
  background: rgba(239, 68, 68, 0.1);
  color: #fecaca;
  border-radius: 6px;
  padding: 9px 14px;
  font-size: 18px;
  cursor: pointer;
}

.btn-delete-record:hover {
  background: rgba(239, 68, 68, 0.22);
}

/* Modal — reused from ImageDetection */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease-out;
}

.modal-container {
  background: var(--card-bg);
  border: 1px solid var(--border-cyan);
  border-radius: 12px;
  width: 90vw;
  max-width: 1500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 0 60px rgba(0, 229, 255, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30px 36px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
}

.modal-header h2 {
  color: var(--primary-cyan);
  font-size: 30px;
  letter-spacing: 2px;
  margin: 0;
}

.btn-close {
  background: transparent;
  border: 1px solid var(--border-cyan);
  color: var(--primary-cyan);
  width: 48px; height: 48px;
  border-radius: 50%;
  font-size: 27px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  background: rgba(0, 229, 255, 0.15);
}

.modal-body { padding: 36px; }

.image-comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.image-panel { display: flex; flex-direction: column; }

.panel-label {
  color: var(--primary-cyan);
  font-size: 21px;
  letter-spacing: 2px;
  margin-bottom: 18px;
  padding: 12px 21px;
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 4px;
  align-self: flex-start;
}

.image-wrapper {
  width: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.compare-image {
  max-width: 100%;
  max-height: 40vh;
  object-fit: contain;
}

.video-detail-layout {
  display: grid;
  grid-template-columns: minmax(360px, 0.95fr) minmax(520px, 1.35fr);
  gap: 22px;
  margin-bottom: 22px;
}

.video-source-panel,
.video-frames-panel {
  min-width: 0;
}

.detail-video {
  width: 100%;
  max-height: 340px;
  background: #000;
  border: 1px solid rgba(0, 229, 255, 0.18);
  border-radius: 6px;
}

.video-frame-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(172px, 1fr));
  gap: 12px;
  max-height: 430px;
  overflow-y: auto;
  padding-right: 4px;
}

.video-frame-card {
  border: 1px solid rgba(0, 229, 255, 0.22);
  background: rgba(0, 229, 255, 0.045);
  border-radius: 6px;
  padding: 8px;
  color: var(--text-main);
  text-align: left;
  cursor: pointer;
}

.video-frame-card:hover {
  border-color: var(--primary-cyan);
  box-shadow: 0 0 14px rgba(0, 229, 255, 0.16);
}

.video-frame-image {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: 4px;
  background: #000;
  display: block;
}

.frame-card-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
  font-family: monospace;
}

.frame-card-meta strong {
  color: var(--primary-cyan);
  font-size: 15px;
}

.frame-card-meta span {
  color: var(--text-dim);
  font-size: 14px;
}

.frame-labels {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.frame-label-chip {
  color: var(--accent-amber);
  border: 1px solid rgba(255, 193, 7, 0.28);
  background: rgba(255, 193, 7, 0.08);
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.15;
}

.video-empty {
  min-height: 260px;
}

.video-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.frame-zoom-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 34px;
  background: rgba(0, 0, 0, 0.78);
  backdrop-filter: blur(3px);
}

.frame-zoom-panel {
  width: min(1180px, 92vw);
  max-height: 90vh;
  border: 1px solid var(--border-cyan);
  border-radius: 8px;
  background: rgba(2, 12, 24, 0.96);
  padding: 18px;
  overflow: auto;
}

.frame-zoom-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  margin-bottom: 14px;
  color: var(--primary-cyan);
  font-size: 22px;
}

.btn-close.small {
  width: 36px;
  height: 36px;
  font-size: 22px;
}

.frame-zoom-image {
  width: 100%;
  max-height: 70vh;
  object-fit: contain;
  background: #000;
  border-radius: 6px;
  display: block;
}

.zoom-labels {
  margin-top: 14px;
}

.zoom-labels .frame-label-chip {
  font-size: 20px;
  padding: 6px 12px;
}

.metrics-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.metric-badge {
  flex: 1;
  background: rgba(0, 229, 255, 0.05);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.metric-label {
  display: block;
  font-size: 19px;
  color: var(--text-dim);
  letter-spacing: 1px;
  margin-bottom: 6px;
}

.metric-value {
  display: block;
  font-size: 42px;
  font-weight: bold;
  font-family: monospace;
}

.metric-value.cyan {
  color: var(--primary-cyan);
  text-shadow: 0 0 8px var(--primary-cyan);
}

.metric-value.small {
  font-size: 21px;
  word-break: break-all;
}

.detection-results { margin-bottom: 16px; }

.section-title {
  color: var(--primary-cyan);
  font-size: 21px;
  letter-spacing: 2px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
}

.detection-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.detection-chip {
  background: rgba(255, 193, 7, 0.08);
  border: 1px solid rgba(255, 193, 7, 0.25);
  border-radius: 6px;
  padding: 8px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.chip-class {
  color: var(--accent-amber);
  font-size: 22px;
  font-weight: 500;
}

.chip-conf {
  color: var(--text-dim);
  font-size: 19px;
  font-family: monospace;
}

.no-detection {
  text-align: center;
  color: var(--text-dim);
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 24px 36px;
  border-top: 1px solid rgba(0, 229, 255, 0.1);
}

.btn-confirm {
  background: var(--primary-cyan);
  border: none;
  color: #000;
  padding: 10px 28px;
  border-radius: 6px;
  font-size: 21px;
  font-weight: 600;
  cursor: pointer;
}

.btn-confirm:hover {
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
