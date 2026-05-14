<template>
  <section class="collaborative-response-card">
    <div class="card-head">
      <div>
        <h3 class="card-title">协同响应服务</h3>
        <p class="card-subtitle">{{ commandCenterBaseUrl }}</p>
      </div>
      <span class="status-badge" :class="services.commandCenter.online ? 'online' : 'offline'">
        {{ services.commandCenter.online ? '指挥后端在线' : '指挥后端离线' }}
      </span>
    </div>

    <div class="config-row">
      <input
        v-model.trim="commandCenterDraft"
        type="text"
        class="config-input"
        placeholder="例如：http://127.0.0.1:5001"
      />
      <button class="action-btn secondary" @click="saveCommandCenterBaseUrl">保存指挥后端</button>
    </div>

    <div class="config-row">
      <input
        v-model.trim="streamlitDraft"
        type="text"
        class="config-input"
        placeholder="例如：http://127.0.0.1:8501/?embed=true"
      />
      <button class="action-btn secondary" @click="saveStreamlitUrl">保存调度平台</button>
    </div>

    <div class="status-grid">
      <div class="status-item">
        <span class="status-label">指挥后端</span>
        <span class="status-value" :class="services.commandCenter.online ? 'ok' : 'warn'">
          {{ services.commandCenter.online ? '在线' : '离线' }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">协同调度平台</span>
        <span class="status-value" :class="services.streamlit.online ? 'ok' : 'warn'">
          {{ services.streamlit.online ? '在线' : '离线' }}
        </span>
      </div>
    </div>

    <div class="meta-row">
      <span class="meta-chip">指挥后端 {{ resolvedCommandCenterBaseUrl }}</span>
      <span class="meta-chip">调度平台 {{ resolvedStreamlitUrl }}</span>
    </div>

    <div class="service-row">
      <span class="service-label">协同调度启停</span>
      <button
        class="action-btn primary"
        :disabled="services.streamlit.pending || !services.commandCenter.online"
        @click="toggleStreamlit(!services.streamlit.running)"
      >
        {{ services.streamlit.running ? '停止服务' : '启动服务' }}
      </button>
    </div>

    <div class="action-row">
      <button class="action-btn secondary" @click="refreshStatus">刷新状态</button>
      <button class="action-btn ghost" @click="goToCoordination">进入协同响应</button>
    </div>

    <p v-if="lastError" class="error-text">最近错误：{{ lastError }}</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getCollaborativeCommandCenterBaseUrl,
  getCollaborativeStreamlitUrl,
  persistCollaborativeCommandCenterBaseUrl,
  persistCollaborativeStreamlitUrl,
} from '../config/subsystems'

const router = useRouter()
const commandCenterBaseUrl = ref(getCollaborativeCommandCenterBaseUrl())
const streamlitUrl = ref(getCollaborativeStreamlitUrl())
const commandCenterDraft = ref(commandCenterBaseUrl.value)
const streamlitDraft = ref(streamlitUrl.value)
const lastError = ref('')

const services = reactive({
  commandCenter: createServiceState(),
  streamlit: createServiceState(),
})

let pollingTimer = null

function createServiceState() {
  return {
    online: false,
    running: false,
    pending: false,
    publicUrl: '',
  }
}

const resolvedCommandCenterBaseUrl = computed(
  () => services.commandCenter.publicUrl || commandCenterBaseUrl.value
)
const resolvedStreamlitUrl = computed(() => services.streamlit.publicUrl || streamlitUrl.value)

function updateService(serviceId, payload = {}, fallbackUrl = '') {
  services[serviceId].online = Boolean(payload.reachable ?? payload.running)
  services[serviceId].running = Boolean(payload.running ?? payload.reachable)
  services[serviceId].publicUrl = payload.public_url || fallbackUrl
}

async function probeDirectService(url) {
  try {
    const response = await fetch(url, { cache: 'no-store' })
    return response.ok
  } catch {
    return false
  }
}

function buildApiUrl(path = '', baseUrl = commandCenterBaseUrl.value) {
  const normalizedPath = String(path).replace(/^\/+/, '')
  const resolvedBase = baseUrl.trim().replace(/\/+$/, '')
  return normalizedPath ? `${resolvedBase}/${normalizedPath}` : resolvedBase
}

async function refreshStatus() {
  try {
    const response = await fetch(buildApiUrl('api/health'), { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const payload = await response.json()
    updateService('commandCenter', payload.services?.commandCenter, commandCenterBaseUrl.value)
    updateService('streamlit', payload.services?.streamlit, streamlitUrl.value)
    lastError.value = ''
  } catch (error) {
    updateService('commandCenter', {}, commandCenterBaseUrl.value)
    lastError.value = error instanceof Error ? error.message : '无法连接指挥后端'

    const streamlitOnline = await probeDirectService(streamlitUrl.value)
    updateService(
      'streamlit',
      { reachable: streamlitOnline, running: streamlitOnline, public_url: streamlitUrl.value },
      streamlitUrl.value
    )
  }
}

async function toggleStreamlit(nextRunning) {
  if (!services.commandCenter.online) {
    lastError.value = '指挥后端离线，无法远程启停服务'
    return
  }

  services.streamlit.pending = true
  try {
    const action = nextRunning ? 'start' : 'stop'
    const response = await fetch(
      buildApiUrl(`api/services/streamlit/${action}`),
      { method: 'POST' }
    )
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || !payload.ok) throw new Error(payload.error || `HTTP ${response.status}`)
    await refreshStatus()
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : '服务控制失败'
  } finally {
    services.streamlit.pending = false
  }
}

function saveCommandCenterBaseUrl() {
  commandCenterBaseUrl.value = persistCollaborativeCommandCenterBaseUrl(commandCenterDraft.value)
  commandCenterDraft.value = commandCenterBaseUrl.value
  refreshStatus()
}

function saveStreamlitUrl() {
  streamlitUrl.value = persistCollaborativeStreamlitUrl(streamlitDraft.value)
  streamlitDraft.value = streamlitUrl.value
  refreshStatus()
}

function goToCoordination() {
  router.push('/coordination')
}

onMounted(() => {
  refreshStatus()
  pollingTimer = window.setInterval(refreshStatus, 5000)
})

onBeforeUnmount(() => {
  if (pollingTimer) window.clearInterval(pollingTimer)
})
</script>

<style scoped>
.collaborative-response-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(96, 165, 250, 0.28);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(10, 22, 48, 0.92) 0%, rgba(8, 16, 34, 0.92) 100%);
  box-shadow: 0 0 24px rgba(96, 165, 250, 0.14);
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.card-title {
  margin: 0;
  color: #bfdcff;
  font-size: 18px;
}
.card-subtitle,
.error-text {
  margin: 0;
  font-size: 12px;
}
.card-subtitle {
  color: rgba(255, 255, 255, 0.72);
  word-break: break-all;
}
.config-row,
.action-row,
.meta-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.config-input {
  flex: 1 1 220px;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid rgba(96, 165, 250, 0.24);
  border-radius: 8px;
  background: rgba(8, 13, 26, 0.94);
  color: #fff;
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.status-item,
.service-row {
  padding: 12px;
  border-radius: 10px;
  background: rgba(8, 16, 34, 0.72);
  border: 1px solid rgba(96, 165, 250, 0.14);
}
.status-label {
  display: block;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
}
.status-badge,
.status-value,
.meta-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
}
.status-badge.online,
.status-value.ok,
.meta-chip {
  color: #bfdcff;
  background: rgba(96, 165, 250, 0.16);
  border: 1px solid rgba(96, 165, 250, 0.24);
}
.status-badge.offline,
.status-value.warn {
  color: #ffb4b4;
  background: rgba(168, 54, 54, 0.18);
  border: 1px solid rgba(255, 180, 180, 0.28);
}
.service-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.service-label {
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 700;
}
.action-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 13px;
}
.action-btn.primary {
  color: #081220;
  background: linear-gradient(90deg, #7db6ff 0%, #bfdcff 100%);
}
.action-btn.secondary {
  color: #bfdcff;
  background: rgba(96, 165, 250, 0.08);
  border-color: rgba(96, 165, 250, 0.24);
}
.action-btn.ghost {
  color: rgba(255, 255, 255, 0.82);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
}
.error-text {
  color: #ffb4b4;
}
@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
  .service-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
