<template>
  <div id="app">
    <Header v-model:activeTab="activeTab" :isOnline="isOnline" :statusDetail="statusDetail" />

    <main class="dashboard-main">
      <aside class="side-panel">
        <DetectionSettings :settings="settings" :availableModels="availableModels" />
        <ModelMetricsPanel :settings="settings" :availableModels="availableModels" />
      </aside>

      <section class="viewport-panel">
        <ImageDetection
          v-if="activeTab === 'image'"
          :settings="settings"
          :availableModels="availableModels"
          :safeFetch="safeFetch"
        />

        <VideoDetection
          v-if="activeTab === 'video'"
          :settings="settings"
          :availableModels="availableModels"
          :safeFetch="safeFetch"
        />

        <RealtimeDetection
          v-if="activeTab === 'webcam'"
          :settings="settings"
          :availableModels="availableModels"
          :safeFetch="safeFetch"
          :apiUrl="apiUrl"
        />

        <HistoryTab
          v-if="activeTab === 'history'"
          :safeFetch="safeFetch"
          :apiUrl="apiUrl"
        />

        <StatsDashboard
          v-if="activeTab === 'stats'"
          :safeFetch="safeFetch"
          :apiUrl="apiUrl"
        />
      </section>

      <aside class="right-panel">
        <div class="card telemetry-card">
          <div class="card-header">
            <h3>[算法推理监控面板]</h3>
          </div>
          <div class="status-content">
            <div class="status-item gpu-row">
              <span class="label">GPU</span>
              <span class="value online">{{ sysInfo.gpu_name || '--' }}</span>
            </div>
            <div class="status-item">
              <span class="label">CUDA算力版本</span>
              <span class="value online">{{ sysInfo.cuda_version || '--' }}</span>
            </div>
            <div class="status-item">
              <span class="label">推理模型状态</span>
              <span class="value model-status-value" :class="{ online: sysInfo.model_loaded }">{{ sysInfo.model_loaded ? formatLoadedModelName(sysInfo.model_name) : '待加载' }}</span>
            </div>
          </div>
          <div class="detection-summary">
            <div class="summary-head">
              <span>检测结果摘要</span>
              <strong>RESULT</strong>
            </div>
            <div class="summary-grid">
              <div class="summary-item">
                <span>累计检测次数</span>
                <strong class="cyan">{{ formatCount(detectionStats.total_detections) }}</strong>
              </div>
              <div class="summary-item">
                <span>今日检测次数</span>
                <strong class="amber">{{ formatCount(todayDetectionCount) }}</strong>
              </div>
              <div class="summary-item">
                <span>平均推理时间</span>
                <strong>{{ formatInferenceTime(detectionStats.avg_inference_time_s) }}</strong>
              </div>
              <div class="summary-item">
                <span>已加载模型数</span>
                <strong class="cyan">{{ loadedModelCount }}</strong>
              </div>
            </div>
          </div>
          <div class="telemetry-trends">
            <div class="trend-card">
              <div class="trend-head">
                <span>显存占用实时折线图</span>
                <strong>{{ sysInfo.vram_used_gb || 0 }} / {{ sysInfo.vram_total_gb || 0 }} GB</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 140 88" preserveAspectRatio="none">
                <line class="trend-axis" x1="12" y1="10" x2="12" y2="74" />
                <line class="trend-axis" x1="12" y1="74" x2="134" y2="74" />
                <line class="trend-grid-line" x1="12" y1="42" x2="134" y2="42" />
                <polyline class="trend-line vram" :points="buildTrendPoints(telemetryHistory.vram, 0.4)" />
              </svg>
            </div>

            <div class="trend-card">
              <div class="trend-head">
                <span>GPU负载实时波动曲线</span>
                <strong>{{ sysInfo.gpu_util || 0 }}%</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 140 88" preserveAspectRatio="none">
                <line class="trend-axis" x1="12" y1="10" x2="12" y2="74" />
                <line class="trend-axis" x1="12" y1="74" x2="134" y2="74" />
                <line class="trend-grid-line" x1="12" y1="42" x2="134" y2="42" />
                <polyline class="trend-line util" :points="buildTrendPoints(telemetryHistory.util, 18)" />
              </svg>
            </div>

            <div class="trend-card">
              <div class="trend-head">
                <span>温度实时波动曲线</span>
                <strong>{{ sysInfo.gpu_temp || '--' }}°C</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 140 88" preserveAspectRatio="none">
                <line class="trend-axis" x1="12" y1="10" x2="12" y2="74" />
                <line class="trend-axis" x1="12" y1="74" x2="134" y2="74" />
                <line class="trend-grid-line" x1="12" y1="42" x2="134" y2="42" />
                <polyline class="trend-line temp" :points="buildTrendPoints(telemetryHistory.temp, 6)" />
              </svg>
            </div>
          </div>
        </div>
      </aside>
    </main>

    <footer class="cyber-footer">
      <div class="footer-line"></div>
      <p>湖北省重点研发项目 // “两客一危”重大交通安全事故智能决策与救援关键技术研究 // “两客一危”事故智能检测</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import Header from './components/Header.vue'
import DetectionSettings from './components/DetectionSettings.vue'
import ModelMetricsPanel from './components/ModelMetricsPanel.vue'
import ImageDetection from './components/ImageDetection.vue'
import VideoDetection from './components/VideoDetection.vue'
import RealtimeDetection from './components/RealtimeDetection.vue'
import HistoryTab from './components/HistoryTab.vue'
import StatsDashboard from './components/StatsDashboard.vue'
import { useApi } from './composables/useApi'

const { apiUrl, isOnline, statusDetail, settings, availableModels, safeFetch } = useApi()
const activeTab = ref('image')

const sysInfo = reactive({
  gpu_name: '', cuda_version: '', vram_total_gb: 0, vram_used_gb: 0,
  gpu_temp: 0, gpu_util: 0, model_loaded: false, model_name: '',
  total_detections_today: 0
})

const detectionStats = reactive({
  total_detections: null,
  today_detections: null,
  avg_inference_time_s: null
})

const loadedModelCount = 6

const MAX_HISTORY_POINTS = 36
const telemetryHistory = reactive({
  vram: [],
  util: [],
  temp: []
})

const pushTelemetryPoint = (key, value) => {
  const numeric = Number(value)
  const series = telemetryHistory[key]
  series.push(Number.isFinite(numeric) ? numeric : 0)
  if (series.length > MAX_HISTORY_POINTS) series.shift()
}

const buildTrendPoints = (series, minSpan = 10) => {
  const values = series.length ? series.map(value => Number(value) || 0) : [0]
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const actualSpan = maxValue - minValue
  const span = Math.max(Number(minSpan) || 1, actualSpan)
  const center = (minValue + maxValue) / 2
  const axisMin = center - span / 2
  const axisMax = center + span / 2
  const lastIndex = Math.max(1, values.length - 1)
  const left = 12
  const right = 134
  const top = 10
  const bottom = 74
  const chartWidth = right - left
  const chartHeight = bottom - top

  return values.map((value, index) => {
    const x = left + (index / lastIndex) * chartWidth
    const normalized = axisMax === axisMin ? 0.5 : (value - axisMin) / (axisMax - axisMin)
    const clamped = Math.max(0, Math.min(1, normalized))
    const y = bottom - clamped * chartHeight
    return `${x.toFixed(2)},${y.toFixed(2)}`
  }).join(' ')
}

const formatLoadedModelName = (name) => {
  if (!name) return ''
  return String(name).replace(/（.*?）|\(.*?\)/g, '')
}

const formatCount = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toLocaleString('zh-CN') : '--'
}

const formatInferenceTime = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '--'
  return `${numeric.toFixed(numeric >= 1 ? 2 : 3)} s`
}

const todayDetectionCount = computed(() => (
  detectionStats.today_detections ?? sysInfo.total_detections_today
))

const fetchSystemInfo = async () => {
  try {
    const data = await safeFetch('/api/system/info')
    if (data.success) {
      Object.assign(sysInfo, data.info)
      pushTelemetryPoint('vram', data.info.vram_used_gb)
      pushTelemetryPoint('util', data.info.gpu_util)
      pushTelemetryPoint('temp', data.info.gpu_temp)
    }
  } catch (e) { /* silently fail */ }
}

const fetchDetectionStats = async () => {
  try {
    const data = await safeFetch('/api/stats')
    if (data.success && data.stats) {
      Object.assign(detectionStats, {
        total_detections: data.stats.total_detections,
        today_detections: data.stats.today_detections,
        avg_inference_time_s: data.stats.avg_inference_time_s
      })
    }
  } catch (e) { /* silently fail */ }
}

let systemTimer = null
let statsTimer = null

onMounted(() => {
  fetchSystemInfo()
  fetchDetectionStats()
  systemTimer = setInterval(fetchSystemInfo, 2500)
  statsTimer = setInterval(fetchDetectionStats, 5000)
})

onUnmounted(() => {
  if (systemTimer) clearInterval(systemTimer)
  if (statsTimer) clearInterval(statsTimer)
})
</script>

<style>
#app {
  min-height: 100vh;
}

.dashboard-main {
  display: grid;
  grid-template-columns: minmax(380px, 420px) minmax(0, 1fr) minmax(390px, 440px);
  gap: 22px;
  padding: 178px 20px 18px;
  min-height: calc(100vh - 74px);
  align-items: start;
}

.side-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
  position: sticky;
  top: 178px;
  align-self: start;
  min-height: 0;
  max-height: calc(100vh - 196px);
  overflow: auto;
  padding-right: 2px;
}

.side-panel > .card,
.side-panel > .model-metrics-panel,
.right-panel > .card {
  width: 100%;
}

.viewport-panel {
  min-height: calc(100vh - 206px);
  padding: 0;
  border: 0;
  background: transparent;
}

.viewport-panel > * {
  min-height: calc(100vh - 206px);
}

.telemetry-card {
  max-height: calc(100vh - 196px);
  min-height: 0;
  overflow: hidden;
  padding: 24px 22px;
  background: var(--card-bg-strong) !important;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  margin-bottom: 16px;
}

.card-header h3 {
  font-size: 28px;
  line-height: 1.15;
  margin-bottom: 0;
}

.status-content {
  display: grid;
  gap: 4px;
}

.status-item {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 229, 255, 0.08);
}

.status-item.gpu-row {
  grid-template-columns: 68px minmax(0, 1fr);
}

.status-item .label {
  font-size: 21px;
  color: var(--text-dim);
  font-family: monospace;
  white-space: nowrap;
}

.status-item .value {
  font-size: 20px;
  color: #fff;
  font-weight: 800;
  font-family: monospace;
  min-width: 0;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-item.gpu-row .value {
  font-size: 18px;
}

.status-item .value.online {
  color: var(--primary-cyan);
  text-shadow: 0 0 8px var(--primary-cyan);
}

.status-item .value.cyan {
  color: var(--primary-cyan);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.55);
}

.status-item .model-status-value {
  font-size: 20px;
}

.detection-summary {
  margin-top: 18px;
  padding: 16px 14px;
  border: 1px solid rgba(0, 229, 255, 0.22);
  background:
    linear-gradient(135deg, rgba(0, 229, 255, 0.1), rgba(255, 193, 7, 0.045)),
    rgba(0, 229, 255, 0.045);
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
  font-family: monospace;
}

.summary-head span {
  color: var(--primary-cyan);
  font-size: 19px;
  font-weight: 800;
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.45);
}

.summary-head strong {
  color: rgba(255, 193, 7, 0.9);
  font-size: 14px;
  letter-spacing: 0.08em;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-item {
  min-height: 72px;
  padding: 12px 10px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  background: rgba(2, 16, 30, 0.45);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  min-width: 0;
}

.summary-item.wide {
  grid-column: 1 / -1;
}

.summary-item span {
  color: var(--text-dim);
  font-family: monospace;
  font-size: 16px;
  white-space: nowrap;
}

.summary-item strong {
  color: #fff3bf;
  font-family: monospace;
  font-size: 28px;
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-item strong.cyan {
  color: var(--primary-cyan);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.5);
}

.summary-item strong.amber {
  color: var(--primary-yellow);
  text-shadow: 0 0 8px rgba(255, 193, 7, 0.42);
}

.telemetry-trends {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.trend-card {
  min-height: 124px;
  padding: 14px 14px 10px;
  border: 1px solid rgba(0, 229, 255, 0.18);
  background: rgba(0, 229, 255, 0.045);
}

.trend-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-bottom: 10px;
  font-family: monospace;
}

.trend-head span {
  color: var(--text-dim);
  font-size: 17px;
  white-space: nowrap;
}

.trend-head strong {
  color: #fff3bf;
  font-size: 18px;
  white-space: nowrap;
}

.trend-chart {
  width: 100%;
  height: 76px;
  overflow: visible;
}

.trend-grid-line {
  fill: none;
  stroke: rgba(255, 255, 255, 0.12);
  stroke-width: 0.7;
  stroke-dasharray: 3 4;
}

.trend-axis {
  fill: none;
  stroke: rgba(0, 229, 255, 0.28);
  stroke-width: 1;
}

.trend-line {
  fill: none;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 0 4px currentColor);
}

.trend-line.vram {
  stroke: #00e5ff;
  color: #00e5ff;
}

.trend-line.util {
  stroke: #fbbf24;
  color: #fbbf24;
}

.trend-line.temp {
  stroke: #fb7185;
  color: #fb7185;
}

.cyber-footer {
  padding: 18px 24px 24px;
  text-align: center;
}

.footer-line {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-cyan), transparent);
  margin-bottom: 8px;
}

.cyber-footer p {
  font-family: monospace;
  font-size: 14px;
  color: var(--text-dim);
  letter-spacing: 0.12em;
  opacity: 0.75;
}

@media (max-width: 1500px) {
  .dashboard-main {
    grid-template-columns: 360px minmax(0, 1fr) 380px;
  }
}

@media (max-width: 1280px) {
  .dashboard-main {
    grid-template-columns: 1fr;
    padding-top: 146px;
  }

  .side-panel,
  .right-panel {
    position: static;
    min-height: 0;
    max-height: none;
    overflow: visible;
  }

  .telemetry-card {
    min-height: 0;
  }
}
</style>


