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
            <h3>算法推理监控面板</h3>
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
              <span class="label">推理模型</span>
              <span class="value model-status-value" :class="{ online: isOnline }">{{ currentActiveModelDisplay }}</span>
            </div>
          </div>
          <div class="detection-summary">
            <div class="summary-head">
              <span>检测结果摘要</span>
              <strong style="font-size: 20px;">RESULT</strong>
            </div>
            <div class="summary-grid">
              <div class="summary-item highlight-item">
                <span>平均推理时间</span>
                <strong class="cyan-highlight">
                  <span class="num">{{ formatInferenceTimeVal(detectionStats.avg_inference_time_s) }}</span>
                  <span class="unit">s</span>
                </strong>
              </div>
              <div class="summary-item">
                <span>今日检测次数</span>
                <strong class="normal-num">{{ formatCount(todayDetectionCount) }}</strong>
              </div>
              <div class="summary-item">
                <span>累计检测次数</span>
                <strong class="normal-num">{{ formatCount(detectionStats.total_detections) }}</strong>
              </div>
              <div class="summary-item">
                <span>已加载模型数</span>
                <strong class="normal-num">{{ loadedModelCount }}</strong>
              </div>
            </div>
          </div>
          <div class="telemetry-trends">
            <div class="trend-card">
              <div class="trend-head">
                <span>显存占用实时折线图</span>
                <strong>{{ formatVram(sysInfo.vram_used_gb, sysInfo.vram_total_gb) }}</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 140 96" preserveAspectRatio="none">
                <line class="trend-axis" x1="12" y1="8" x2="12" y2="88" />
                <line class="trend-axis" x1="12" y1="88" x2="134" y2="88" />
                <line class="trend-grid-line" x1="12" y1="48" x2="134" y2="48" />
                <polyline class="trend-line vram" :points="buildTrendPoints(telemetryHistory.vram, 0.4)" />
              </svg>
            </div>

            <div class="trend-card">
              <div class="trend-head">
                <span>GPU负载实时波动曲线</span>
                <strong>{{ formatPercentMetric(sysInfo.gpu_util) }}</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 140 96" preserveAspectRatio="none">
                <line class="trend-axis" x1="12" y1="8" x2="12" y2="88" />
                <line class="trend-axis" x1="12" y1="88" x2="134" y2="88" />
                <line class="trend-grid-line" x1="12" y1="48" x2="134" y2="48" />
                <polyline class="trend-line util" :points="buildTrendPoints(telemetryHistory.util, 18)" />
              </svg>
            </div>

            <div class="trend-card">
              <div class="trend-head">
                <span>温度实时波动曲线</span>
                <strong>{{ formatTemperature(sysInfo.gpu_temp) }}</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 140 96" preserveAspectRatio="none">
                <line class="trend-axis" x1="12" y1="8" x2="12" y2="88" />
                <line class="trend-axis" x1="12" y1="88" x2="134" y2="88" />
                <line class="trend-grid-line" x1="12" y1="48" x2="134" y2="48" />
                <polyline class="trend-line temp" :points="buildTrendPoints(telemetryHistory.temp, 6)" />
              </svg>
            </div>
          </div>
        </div>
      </aside>
    </main>

    <footer class="cyber-footer">
      <div class="footer-line"></div>
      <div class="footer-content">
        <span class="footer-badge highlight">湖北省重点研发项目</span>
        <span class="footer-divider">◆</span>
        <span class="footer-text">“两客一危”重大交通安全事故智能决策与救援关键技术研究</span>
        <span class="footer-divider">◆</span>
        <span class="footer-badge cyan">“两客一危”交通事故智能检测</span>
      </div>
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
  gpu_name: '', cuda_version: '', vram_total_gb: null, vram_used_gb: null,
  gpu_temp: null, gpu_util: null, gpu_error: '', model_loaded: false, model_name: '',
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
  const top = 8
  const bottom = 88
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

const MODEL_DISPLAY_FALLBACKS = {
  yolo26M: 'YOLO26M',
  yolo26N: 'YOLO26N',
  yolo11M: 'YOLO11M',
  yolo11N: 'YOLO11N',
  'sfga-yolo26m': 'SFGA-YOLO26M',
  'lca-yolo26n': 'LCA-YOLO26N'
}

const formatLoadedModelName = (name) => {
  if (!name) return ''
  const found = availableModels.value?.find(m => m.name === name || m.display_name === name)
  if (found && (found.display_name || found.name)) {
    return String(found.display_name || found.name).replace(/（.*?）|\(.*?\)/g, '')
  }
  const clean = String(name).replace(/（.*?）|\(.*?\)/g, '')
  return MODEL_DISPLAY_FALLBACKS[clean] || MODEL_DISPLAY_FALLBACKS[clean.toLowerCase()] || clean
}

const currentActiveModelDisplay = computed(() => {
  if (settings.detectionMode === 'composite') {
    return 'SFGA-YOLO26M + LCA-YOLO26N'
  }
  if (settings.model) {
    return formatLoadedModelName(settings.model)
  }
  return sysInfo.model_loaded ? formatLoadedModelName(sysInfo.model_name) : '待加载'
})

const formatCount = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toLocaleString('zh-CN') : '--'
}

const formatVram = (used, total) => {
  const usedValue = Number(used)
  const totalValue = Number(total)
  if (!Number.isFinite(usedValue) || !Number.isFinite(totalValue) || totalValue <= 0) return 'N/A'
  return `${usedValue} / ${totalValue} GB`
}

const formatPercentMetric = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${numeric}%` : 'N/A'
}

const formatTemperature = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${numeric}°C` : 'N/A'
}

const formatInferenceTime = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '--'
  return `${numeric.toFixed(numeric >= 1 ? 2 : 3)} s`
}

const formatInferenceTimeVal = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '--'
  return numeric.toFixed(numeric >= 1 ? 2 : 3)
}

const todayDetectionCount = computed(() => (
  detectionStats.today_detections ?? sysInfo.total_detections_today
))

const fetchSystemInfo = async () => {
  try {
    const data = await safeFetch('/api/system/info')
    if (data.success) {
      Object.assign(sysInfo, data.info)
      if (Number.isFinite(Number(data.info.vram_used_gb))) pushTelemetryPoint('vram', data.info.vram_used_gb)
      if (Number.isFinite(Number(data.info.gpu_util))) pushTelemetryPoint('util', data.info.gpu_util)
      if (Number.isFinite(Number(data.info.gpu_temp))) pushTelemetryPoint('temp', data.info.gpu_temp)
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
  padding: 196px 20px 18px;
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
  top: 196px;
  align-self: start;
  min-height: 0;
  max-height: calc(100vh - 212px);
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
  max-height: calc(100vh - 170px);
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px 22px;
  background: var(--card-bg-strong) !important;
}

.card-header h3 {
  font-size: 32px;
  line-height: 1.15;
  margin-bottom: 0;
  color: var(--primary-cyan);
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.4);
}

.status-content {
  display: grid;
  gap: 6px;
}

.status-item {
  display: grid;
  grid-template-columns: 130px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(0, 229, 255, 0.12);
}

.status-item.gpu-row {
  grid-template-columns: 60px minmax(0, 1fr);
}

.status-item .label {
  font-size: 22px;
  color: var(--text-dim);
  font-family: 'Microsoft YaHei', '微软雅黑', 'PingFang SC', sans-serif;
  white-space: nowrap;
}

.status-item .value {
  font-size: 22px;
  color: #fff;
  font-weight: 800;
  font-family: 'Times New Roman', Times, serif;
  min-width: 0;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-item.gpu-row .value {
  font-size: 20px;
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
  font-size: 22px;
  font-weight: 800;
  font-family: 'Times New Roman', Times, serif;
  white-space: normal;
  word-break: break-word;
  overflow: visible;
  text-overflow: clip;
}

.detection-summary {
  margin-top: 20px;
  padding: 18px 16px;
  border: 1px solid rgba(0, 229, 255, 0.25);
  background:
    linear-gradient(135deg, rgba(0, 229, 255, 0.12), rgba(255, 193, 7, 0.05)),
    rgba(0, 229, 255, 0.05);
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
  font-family: 'Microsoft YaHei', '微软雅黑', 'PingFang SC', sans-serif;
}

.summary-head span {
  color: var(--primary-cyan);
  font-size: 22px;
  font-weight: 800;
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.45);
}

.summary-head strong {
  color: rgba(255, 193, 7, 0.9);
  font-size: 16px;
  font-family: 'Times New Roman', Times, serif;
  letter-spacing: 0.08em;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.summary-item {
  min-height: 84px;
  padding: 14px 12px;
  border: 1px solid rgba(0, 229, 255, 0.14);
  background: rgba(2, 16, 30, 0.55);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  min-width: 0;
}

.summary-item.highlight-item {
  border: 1.5px solid rgba(0, 229, 255, 0.45);
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.15), rgba(3, 20, 36, 0.85));
  box-shadow: 0 0 14px rgba(0, 229, 255, 0.18);
}

.summary-item.wide {
  grid-column: 1 / -1;
}

.summary-item span {
  color: var(--text-dim);
  font-family: 'Microsoft YaHei', '微软雅黑', 'PingFang SC', sans-serif;
  font-size: 19px;
  white-space: nowrap;
}

.summary-item.highlight-item span {
  color: var(--primary-cyan);
  font-weight: 700;
}

.summary-item strong {
  font-family: 'Times New Roman', Times, serif;
  font-size: 32px;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
  display: flex;
  align-items: baseline;
  margin: 0;
  padding: 0;
}

.summary-item strong.normal-num {
  color: #e2f8ff;
  text-shadow: none;
}

.summary-item strong.cyan-highlight,
.summary-item strong.cyan-highlight .num {
  color: var(--primary-cyan);
  text-shadow: 0 0 12px rgba(0, 229, 255, 0.65);
}

.summary-item strong .unit {
  font-size: 20px;
  margin-left: 6px;
  font-weight: 600;
  color: var(--text-dim);
  font-family: 'Times New Roman', Times, serif;
  text-shadow: none;
}

.summary-item.highlight-item strong .unit {
  color: var(--primary-cyan);
  opacity: 0.9;
}

.telemetry-trends {
  display: grid;
  gap: 16px;
  margin-top: 20px;
}

.trend-card {
  min-height: 168px;
  padding: 16px 16px 12px;
  border: 1px solid rgba(0, 229, 255, 0.25);
  background: rgba(0, 229, 255, 0.06);
}

.trend-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
  font-family: var(--font-main);
}

.trend-head span {
  color: #e0f2fe;
  font-size: 21px;
  font-weight: 700;
  white-space: nowrap;
}

.trend-head strong {
  color: #fff3bf;
  font-size: 23px;
  font-weight: 800;
  white-space: nowrap;
}

.trend-chart {
  width: 100%;
  height: 116px;
  overflow: visible;
}

.trend-grid-line {
  fill: none;
  stroke: rgba(255, 255, 255, 0.15);
  stroke-width: 0.8;
  stroke-dasharray: 4 4;
}

.trend-axis {
  fill: none;
  stroke: rgba(0, 229, 255, 0.35);
  stroke-width: 1.2;
}

.trend-line {
  fill: none;
  stroke-width: 3.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 0 6px currentColor);
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
  margin-top: 20px;
  padding: 20px 30px 28px;
  text-align: center;
  background: linear-gradient(180deg, rgba(2, 10, 19, 0.7), rgba(2, 12, 24, 0.95));
  backdrop-filter: blur(12px);
}

.footer-line {
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.7), transparent);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.5);
  margin-bottom: 18px;
}

.footer-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  flex-wrap: wrap;
}

.footer-badge {
  padding: 7px 18px;
  border-radius: 6px;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.footer-badge.highlight {
  background: rgba(255, 193, 7, 0.12);
  border: 1px solid rgba(255, 193, 7, 0.35);
  color: #ffc107;
  box-shadow: 0 0 12px rgba(255, 193, 7, 0.15);
}

.footer-badge.cyan {
  background: rgba(0, 229, 255, 0.12);
  border: 1px solid rgba(0, 229, 255, 0.35);
  color: var(--primary-cyan);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.15);
}

.footer-text {
  font-size: 19px;
  font-weight: 600;
  color: #e2f8ff;
  letter-spacing: 0.08em;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.footer-divider {
  color: var(--primary-cyan);
  font-size: 14px;
  opacity: 0.8;
  text-shadow: 0 0 10px var(--primary-cyan);
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


