<template>
  <div id="app">
    <Header v-model:activeTab="activeTab" :isOnline="isOnline" :statusDetail="statusDetail" />

    <main class="dashboard-main">
      <!-- Left Panel: Settings -->
      <aside class="side-panel">
        <DetectionSettings :settings="settings" :availableModels="availableModels" />
      </aside>

      <!-- Center Content -->
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

      <!-- Right Panel: Telemetry -->
      <aside class="right-panel">
        <div class="card telemetry-card">
          <div class="card-header">
            <!-- <span class="bracket">[</span> -->
            <h3>[算法推理监控面板]</h3>
            <!-- <span class="bracket">]</span> -->
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
            <div class="status-item">
              <span class="label">今日检测次数</span>
              <span class="value cyan">{{ sysInfo.total_detections_today }}</span>
            </div>
          </div>
          <div class="telemetry-trends">
            <div class="trend-card">
              <div class="trend-head">
                <span>显存占用实时折线图</span>
                <strong>{{ sysInfo.vram_used_gb || 0 }} / {{ sysInfo.vram_total_gb || 0 }} GB</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 120 44" preserveAspectRatio="none">
                <polyline class="trend-grid-line" points="0,22 120,22" />
                <polyline class="trend-line vram" :points="buildTrendPoints(telemetryHistory.vram, 0.4)" />
              </svg>
            </div>

            <div class="trend-card">
              <div class="trend-head">
                <span>GPU负载实时波动曲线</span>
                <strong>{{ sysInfo.gpu_util || 0 }}%</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 120 44" preserveAspectRatio="none">
                <polyline class="trend-grid-line" points="0,22 120,22" />
                <polyline class="trend-line util" :points="buildTrendPoints(telemetryHistory.util, 18)" />
              </svg>
            </div>

            <div class="trend-card">
              <div class="trend-head">
                <span>温度实时波动曲线</span>
                <strong>{{ sysInfo.gpu_temp || '--' }}°C</strong>
              </div>
              <svg class="trend-chart" viewBox="0 0 120 44" preserveAspectRatio="none">
                <polyline class="trend-grid-line" points="0,22 120,22" />
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
import { ref, reactive, onMounted } from 'vue'
import Header from './components/Header.vue'
import DetectionSettings from './components/DetectionSettings.vue'
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

  return values.map((value, index) => {
    const x = (index / lastIndex) * 120
    const normalized = axisMax === axisMin ? 0.5 : (value - axisMin) / (axisMax - axisMin)
    const y = 39 - Math.max(0, Math.min(1, normalized)) * 32
    return `${x.toFixed(2)},${y.toFixed(2)}`
  }).join(' ')
}

const formatLoadedModelName = (name) => {
  if (!name) return ''
  return String(name).replace(/（.*?）|\(.*?\)/g, '')
}

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

onMounted(() => { fetchSystemInfo(); setInterval(fetchSystemInfo, 2500) })
</script>

<style>
.dashboard-main {
  display: grid;
  grid-template-columns: 480px 1fr 440px;
  gap: 36px;
  padding: 150px 40px 50px;
  min-height: calc(100vh - 80px);
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.telemetry-card {
  padding: 28px 24px;
  background: rgba(13, 25, 41, 0.4) !important;
}

.status-item {
  display: grid;
  grid-template-columns: 154px minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  padding: 18px 0;
  border-bottom: 1px solid rgba(0, 229, 255, 0.05);
}

.status-item.gpu-row {
  grid-template-columns: 56px minmax(0, 1fr);
}

.status-item .label {
  font-size: 22px;
  color: var(--text-dim);
  font-family: monospace;
  letter-spacing: 0;
  white-space: nowrap;
}

.status-item .value {
  font-size: 24px;
  color: #fff;
  font-weight: bold;
  font-family: monospace;
  min-width: 0;
  text-align: right;
  white-space: nowrap;
}

.status-item .value.online {
  color: var(--primary-cyan);
  text-shadow: 0 0 8px var(--primary-cyan);
}

.status-item.gpu-row .value {
  font-size: 20px;
}

.status-item .model-status-value {
  font-size: 20px;
}

.telemetry-trends {
  display: grid;
  gap: 14px;
  margin-top: 22px;
}

.trend-card {
  padding: 12px 12px 10px;
  border: 1px solid rgba(0, 229, 255, 0.16);
  background: rgba(0, 229, 255, 0.045);
}

.trend-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-family: monospace;
}

.trend-head span {
  color: var(--text-dim);
  font-size: 15px;
  white-space: nowrap;
}

.trend-head strong {
  color: #fff3bf;
  font-size: 16px;
  white-space: nowrap;
}

.trend-chart {
  width: 100%;
  height: 58px;
  overflow: visible;
}

.trend-grid-line {
  fill: none;
  stroke: rgba(255, 255, 255, 0.12);
  stroke-width: 0.7;
  stroke-dasharray: 3 4;
}

.trend-line {
  fill: none;
  stroke-width: 2.2;
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

.viewport-panel {
  min-height: 70vh;
}

.cyber-footer {
  padding: 40px;
  text-align: center;
}

.footer-line {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-cyan), transparent);
  margin-bottom: 15px;
}

.cyber-footer p {
  font-family: monospace;
  font-size: 19px;
  color: var(--text-dim);
  letter-spacing: 3px;
  opacity: 0.6;
}
</style>
