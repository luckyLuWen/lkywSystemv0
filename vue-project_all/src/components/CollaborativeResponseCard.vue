<template>
  <section class="collaborative-response-card">
    <div class="card-head">
      <div>
        <h3 class="card-title">协同响应服务</h3>
        <p class="card-subtitle">{{ controllerBaseUrl }}</p>
      </div>
      <span class="status-badge" :class="controllerOnline ? 'online' : 'offline'">
        {{ controllerOnline ? '控制层在线' : '控制层离线' }}
      </span>
    </div>

    <div class="config-row">
      <input
        v-model.trim="controllerDraft"
        type="text"
        class="config-input"
        placeholder="例如：http://127.0.0.1:18601"
      />
      <button class="action-btn secondary" @click="saveControllerBaseUrl">保存控制层</button>
    </div>

    <div class="config-row">
      <input
        v-model.trim="commandCenterDraft"
        type="text"
        class="config-input"
        placeholder="例如：http://127.0.0.1:5000"
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
      <span class="service-label">指挥后端启停</span>
      <button
        class="action-btn primary"
        :disabled="services.commandCenter.pending || !controllerOnline"
        @click="toggleService('commandCenter', !services.commandCenter.running)"
      >
        {{ services.commandCenter.running ? '停止服务' : '启动服务' }}
      </button>
    </div>

    <div class="service-row">
      <span class="service-label">协同调度启停</span>
      <button
        class="action-btn primary"
        :disabled="services.streamlit.pending || !controllerOnline"
        @click="toggleService('streamlit', !services.streamlit.running)"
      >
        {{ services.streamlit.running ? '停止服务' : '启动服务' }}
      </button>
    </div>

    <div class="action-row">
      <button class="action-btn secondary" @click="refreshStatus">刷新状态</button>
      <button class="action-btn ghost" @click="goToCoordination">进入协同响应</button>
    </div>

    <div v-if="strategyMetrics" class="strategy-metrics-panel">
      <h4 class="metrics-title">📊 协同策略评估结果</h4>
      <div class="metrics-grid">
        <div class="metric-item" style="grid-column: span 2;">
          <span class="metric-label">灾害场景</span>
          <span class="metric-value highlight">{{ strategyMetrics.end_point_name }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">协同机制</span>
          <span class="metric-value highlight">
            {{ strategyMetrics.strategy === 'rcd' ? 'RCD 逆向推演' : (strategyMetrics.strategy === 'independent' ? 'ISD 极速独立' : 'CAS 基地待命') }}
          </span>
        </div>
        <div class="metric-item">
          <span class="metric-label">无人机地面待机</span>
          <span class="metric-value warning">{{ strategyMetrics.metrics.delay }} s</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">无人车(UGV)耗时</span>
          <span class="metric-value">{{ strategyMetrics.metrics.carTime }} min</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">无人机(UAV)飞行</span>
          <span class="metric-value">{{ strategyMetrics.metrics.uavTime }} min</span>
        </div>
      </div>
    </div>

    <p v-if="lastError" class="error-text">最近错误：{{ lastError }}</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  buildCollaborativeApiUrl,
  getCollaborativeCommandCenterBaseUrl,
  getCollaborativeControllerBaseUrl,
  getCollaborativeStreamlitUrl,
  persistCollaborativeCommandCenterBaseUrl,
  persistCollaborativeControllerBaseUrl,
  persistCollaborativeStreamlitUrl,
} from '../config/subsystems'

const router = useRouter()
const controllerBaseUrl = ref(getCollaborativeControllerBaseUrl())
const commandCenterBaseUrl = ref(getCollaborativeCommandCenterBaseUrl())
const streamlitUrl = ref(getCollaborativeStreamlitUrl())
const controllerDraft = ref(controllerBaseUrl.value)
const commandCenterDraft = ref(commandCenterBaseUrl.value)
const streamlitDraft = ref(streamlitUrl.value)
const controllerOnline = ref(false)
const lastError = ref('')
const strategyMetrics = ref(null)

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

async function refreshStatus() {
  try {
    const response = await fetch(buildCollaborativeApiUrl('api/health', controllerBaseUrl.value), {
      cache: 'no-store',
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const payload = await response.json()
    controllerOnline.value = Boolean(payload.ok)
    updateService('commandCenter', payload.services?.commandCenter, commandCenterBaseUrl.value)
    updateService('streamlit', payload.services?.streamlit, streamlitUrl.value)
    if (payload.strategy_metrics && payload.strategy_metrics.available) {
      strategyMetrics.value = payload.strategy_metrics
    } else {
      strategyMetrics.value = null
    }
    lastError.value = ''
    return
  } catch (error) {
    controllerOnline.value = false
    strategyMetrics.value = null
    lastError.value = error instanceof Error ? error.message : '无法连接控制层'
  }

  const [commandCenterOnline, streamlitOnline] = await Promise.all([
    probeDirectService(`${commandCenterBaseUrl.value}/api/health`),
    probeDirectService(streamlitUrl.value),
  ])

  updateService(
    'commandCenter',
    { reachable: commandCenterOnline, running: commandCenterOnline, public_url: commandCenterBaseUrl.value },
    commandCenterBaseUrl.value
  )
  updateService(
    'streamlit',
    { reachable: streamlitOnline, running: streamlitOnline, public_url: streamlitUrl.value },
    streamlitUrl.value
  )
}

async function toggleService(serviceId, nextRunning) {
  if (!controllerOnline.value) {
    lastError.value = '控制层离线，无法远程启停服务'
    return
  }

  services[serviceId].pending = true
  try {
    const action = nextRunning ? 'start' : 'stop'
    const response = await fetch(
      buildCollaborativeApiUrl(`api/services/${serviceId}/${action}`, controllerBaseUrl.value),
      { method: 'POST' }
    )
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || !payload.ok) throw new Error(payload.error || `HTTP ${response.status}`)
    await refreshStatus()
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : '服务控制失败'
  } finally {
    services[serviceId].pending = false
  }
}

function saveControllerBaseUrl() {
  controllerBaseUrl.value = persistCollaborativeControllerBaseUrl(controllerDraft.value)
  controllerDraft.value = controllerBaseUrl.value
  refreshStatus()
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

.strategy-metrics-panel {
  margin-top: 4px;
  padding: 14px;
  border-radius: 10px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
}
.metrics-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #34d399;
}
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
}
.metric-label {
  font-size: 11px;
  color: #94a3b8;
}
.metric-value {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}
.metric-value.highlight {
  color: #60a5fa;
}
.metric-value.warning {
  color: #fbbf24;
}
</style>
