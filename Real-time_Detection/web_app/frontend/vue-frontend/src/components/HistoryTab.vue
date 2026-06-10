<template>
  <div class="history-container">
    <div v-if="loading" class="upload-center">
      <div class="loading-box">
        <div class="spinner"></div>
        <p class="scanning-text">加载记录中...</p>
      </div>
    </div>

    <div v-else-if="records.length === 0" class="upload-center">
      <div class="card upload-card">
        <div class="upload-icon">📋</div>
        <h3>暂无检测记录</h3>
        <p>完成检测后，记录将显示在此处</p>
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
            <span class="meta-tag">{{ rec.model_name }}</span>
            <span class="meta-tag">{{ rec.source_type }}</span>
          </div>
        </div>
        <div class="record-stats">
          <span class="stat-count">{{ rec.detection_count }}</span>
          <span class="stat-label">个目标</span>
        </div>
        <div class="record-time-s">{{ rec.inference_time_s }} s</div>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="detail" class="modal-overlay" @click.self="detail = null">
      <div class="modal-container">
        <div class="modal-header">
          <h2>检测详情</h2>
          <button class="btn-close" @click="detail = null">&times;</button>
        </div>
        <div class="modal-body">
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
              <span class="metric-label">模型</span>
              <span class="metric-value small">{{ detail.model_name }}</span>
            </div>
          </div>

          <div v-if="detail.detections.length > 0" class="detection-results">
            <div class="section-title">识别详情</div>
            <div class="detection-grid">
              <div v-for="(det, i) in detail.detections" :key="i" class="detection-chip">
                <span class="chip-class">{{ det.class }}</span>
                <span class="chip-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          <div v-else class="no-detection">未发现可疑目标</div>
        </div>
        <div class="modal-footer">
          <ExportButtons
            :resultImageUrl="`${apiUrl}/api/results/${detail.result_filename}`"
            :detections="detail.detections"
          />
          <button class="btn-confirm" @click="detail = null">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ExportButtons from './ExportButtons.vue'

const props = defineProps({
  safeFetch: Function,
  apiUrl: String
})

const loading = ref(false)
const records = ref([])
const detail = ref(null)

const formatTime = (ts) => {
  if (!ts) return ''
  return ts.replace('T', ' ').substring(0, 19)
}

const openDetail = async (id) => {
  try {
    const data = await props.safeFetch(`/api/history/${id}`)
    if (data.success) detail.value = data.record
  } catch (e) {
    alert('加载详情失败: ' + e.message)
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const data = await props.safeFetch('/api/history?limit=50')
    if (data.success) records.value = data.records
  } catch (e) {
    // silently fail, empty state shown
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.history-container {
  height: 100%;
  overflow-y: auto;
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
}

.meta-tag {
  font-size: 27px;
  color: var(--text-dim);
  background: rgba(0, 229, 255, 0.08);
  padding: 5px 12px;
  border-radius: 3px;
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
