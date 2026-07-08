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
            <span class="bracket">[</span>
            <h3>核心监测指标</h3>
            <span class="bracket">]</span>
          </div>
          <div class="status-content">
            <div class="status-item">
              <span class="label">GPU</span>
              <span class="value online">{{ sysInfo.gpu_name || '--' }}</span>
            </div>
            <div class="status-item">
              <span class="label">CUDA</span>
              <span class="value online">{{ sysInfo.cuda_version || '--' }}</span>
            </div>
            <div class="status-item">
              <span class="label">VRAM</span>
              <span class="value">{{ sysInfo.vram_used_gb || 0 }} / {{ sysInfo.vram_total_gb || 0 }} GB</span>
            </div>
            <div class="status-item">
              <span class="label">GPU_温度</span>
              <span class="value">{{ sysInfo.gpu_temp || '--' }}°C</span>
            </div>
            <div class="status-item">
              <span class="label">GPU_利用率</span>
              <span class="value">{{ sysInfo.gpu_util || '--' }}%</span>
            </div>
            <div class="status-item">
              <span class="label">已加载模型</span>
              <span class="value" :class="{ online: sysInfo.model_loaded }">{{ sysInfo.model_loaded ? sysInfo.model_name : '待加载' }}</span>
            </div>
            <div class="status-item">
              <span class="label">今日检测次数</span>
              <span class="value cyan">{{ sysInfo.total_detections_today }}</span>
            </div>
          </div>
          <div class="wave-decoration">
            <div class="wave-bar" v-for="i in 20" :key="i" :style="{ height: Math.random() * 20 + 5 + 'px' }"></div>
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

const fetchSystemInfo = async () => {
  try {
    const data = await safeFetch('/api/system/info')
    if (data.success) Object.assign(sysInfo, data.info)
  } catch (e) { /* silently fail */ }
}

onMounted(() => { fetchSystemInfo(); setInterval(fetchSystemInfo, 10000) })
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
  display: flex;
  justify-content: space-between;
  padding: 18px 0;
  border-bottom: 1px solid rgba(0, 229, 255, 0.05);
}

.status-item .label {
  font-size: 22px;
  color: var(--text-dim);
  font-family: monospace;
  letter-spacing: 1px;
}

.status-item .value {
  font-size: 24px;
  color: #fff;
  font-weight: bold;
  font-family: monospace;
}

.status-item .value.online {
  color: var(--primary-cyan);
  text-shadow: 0 0 8px var(--primary-cyan);
}

.wave-decoration {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 45px;
  margin-top: 24px;
  opacity: 0.3;
}

.wave-bar {
  flex: 1;
  background: var(--primary-cyan);
  border-radius: 1px;
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
