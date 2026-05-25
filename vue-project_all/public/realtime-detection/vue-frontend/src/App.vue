<template>
  <div id="app">
    <Header v-model:activeTab="activeTab" :isOnline="isOnline" :statusDetail="statusDetail" />

    <main class="dashboard-main">
      <!-- Left Panel: Engine Telemetry -->
      <aside class="side-panel">
        <DetectionSettings :settings="settings" :availableModels="availableModels" />
        
        <div class="card telemetry-card">
          
          <div class="card-header">
            <span class="bracket">[</span>
            <h3>核心监测指标</h3>
            <span class="bracket">]</span>
          </div>
          <div class="status-content">
            <div class="status-item">
              <span class="label">API_LATENCY</span>
              <span class="value" :class="{ online: isOnline }">{{ isOnline ? '2ms' : 'TIMEOUT' }}</span>
            </div>
            <div class="status-item">
              <span class="label">GPU_ACCEL</span>
              <span class="value online">CUDA_12.1</span>
            </div>
            <div class="status-item">
              <span class="label">ENGINE_STATE</span>
              <span class="value" :class="{ online: isOnline }">{{ isOnline ? 'HOT_SWAP_READY' : 'STANDBY' }}</span>
            </div>
            <div class="status-item">
              <span class="label">VRAM_CACHE</span>
              <span class="value">4.2GB / 8GB</span>
            </div>
          </div>
          <div class="wave-decoration">
            <div class="wave-bar" v-for="i in 20" :key="i" :style="{ height: Math.random() * 20 + 5 + 'px' }"></div>
          </div>
        </div>
      </aside>

      <!-- Center Content -->
      <section class="viewport-panel">
        <ImageDetection 
          v-if="activeTab === 'image'" 
          :settings="settings" 
          :safeFetch="safeFetch"
        />

        <VideoDetection 
          v-if="activeTab === 'video'" 
          :settings="settings" 
          :safeFetch="safeFetch" 
        />

        <RealtimeDetection 
          v-if="activeTab === 'webcam'" 
          :settings="settings" 
          :safeFetch="safeFetch"
          :apiUrl="apiUrl"
        />
      </section>
    </main>

    <footer class="cyber-footer">
      <div class="footer-line"></div>
      <p>REAL-TIME DETECTION SYSTEM // LKYWDetection // AUTHORIZED_ACCESS_ONLY</p>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Header from './components/Header.vue'
import DetectionSettings from './components/DetectionSettings.vue'
import ImageDetection from './components/ImageDetection.vue'
import VideoDetection from './components/VideoDetection.vue'
import RealtimeDetection from './components/RealtimeDetection.vue'
import { useApi } from './composables/useApi'

const { apiUrl, isOnline, statusDetail, settings, availableModels, safeFetch } = useApi()
const activeTab = ref('image') 
</script>

<style>
.dashboard-main {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 30px;
  padding: 100px 40px 40px;
  min-height: calc(100vh - 80px);
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.telemetry-card {
  padding: 25px 20px;
  background: rgba(13, 25, 41, 0.4) !important;
}

.status-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 229, 255, 0.05);
}

.status-item .label {
  font-size: 10px;
  color: var(--text-dim);
  font-family: monospace;
  letter-spacing: 1px;
}

.status-item .value {
  font-size: 11px;
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
  gap: 2px;
  height: 30px;
  margin-top: 20px;
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
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 3px;
  opacity: 0.6;
}
</style>
