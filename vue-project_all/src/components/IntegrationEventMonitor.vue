<template>
  <section class="integration-card">
    <div class="integration-head">
      <div>
        <h3 class="integration-title">集成总线</h3>
        <p class="integration-subtitle">{{ hubBaseUrl }}</p>
      </div>
      <span class="connection-chip" :class="connectionClass">{{ connectionText }}</span>
    </div>

    <div class="config-row">
      <input
        v-model.trim="hubDraft"
        type="text"
        class="hub-input"
        placeholder="例如：http://127.0.0.1:18701"
      />
      <button class="small-btn secondary" @click="saveHubBaseUrl">保存</button>
      <button class="small-btn ghost" @click="resetHubBaseUrlHandler">默认</button>
    </div>

    <div class="metric-grid">
      <div class="metric-item">
        <span>传感器</span>
        <strong>{{ sensorStatusText }}</strong>
      </div>
      <div class="metric-item">
        <span>检测流</span>
        <strong>{{ activeStreamCount }}</strong>
      </div>
      <div class="metric-item warn" v-if="store.sensor.latestThreshold">
        <span>最新预警</span>
        <strong>{{ store.sensor.latestThreshold.subject }}</strong>
      </div>
      <div class="metric-item warn" v-else-if="store.detection.latestFire">
        <span>最新检测</span>
        <strong>fire</strong>
      </div>
    </div>

    <div class="command-panel">
      <div class="panel-title">命令通道</div>
      <div class="command-grid">
        <button class="command-btn" :disabled="commandBusy" @click="sendSensorCommand(true)">
          启动采样
        </button>
        <button class="command-btn" :disabled="commandBusy" @click="sendSensorCommand(false)">
          停止采样
        </button>
        <button class="command-btn" :disabled="commandBusy" @click="sendRtspCommand(true)">
          启动 RTSP
        </button>
        <button class="command-btn" :disabled="commandBusy" @click="sendRtspCommand(false)">
          停止 RTSP
        </button>
      </div>
      <p v-if="commandError" class="error-text">{{ commandError }}</p>
      <div class="command-list">
        <article
          v-for="command in visibleCommands"
          :key="command.commandId"
          class="command-row"
          :class="command.status"
        >
          <span class="command-type">{{ command.type || command.commandId }}</span>
          <span class="command-status">{{ command.status }}</span>
        </article>
        <p v-if="!visibleCommands.length" class="empty-text">等待命令回执</p>
      </div>
    </div>

    <div class="event-list">
      <article v-for="event in visibleEvents" :key="event.streamId || event.eventId" class="event-row">
        <span class="event-type">{{ event.type }}</span>
        <span class="event-source">{{ event.source }}</span>
      </article>
      <p v-if="!visibleEvents.length" class="empty-text">等待 sensor / realtime 事件</p>
    </div>

    <p v-if="store.connection.lastError" class="error-text">
      {{ store.connection.lastError }}
    </p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  getIntegrationHubBaseUrl,
  getRealtimeDetectionRtspUrl,
  persistIntegrationHubBaseUrl,
  resetIntegrationHubBaseUrl,
} from '../config/subsystems'
import {
  connectIntegrationHubEvents,
  disconnectIntegrationHubEvents,
  fetchRecentIntegrationEvents,
  publishIntegrationCommand,
} from '../integration/integrationHubClient'
import { resetIntegrationEvents, situationStore as store } from '../integration/situationStore'

const hubBaseUrl = ref(getIntegrationHubBaseUrl())
const hubDraft = ref(hubBaseUrl.value)
const commandBusy = ref(false)
const commandError = ref('')

const connectionText = computed(() => {
  if (store.connection.state === 'connected') return '在线'
  if (store.connection.state === 'connecting') return '连接中'
  if (store.connection.state === 'error') return '离线'
  return '未连接'
})

const connectionClass = computed(() => {
  if (store.connection.state === 'connected') return 'online'
  if (store.connection.state === 'connecting') return 'pending'
  return 'offline'
})

const sensorStatusText = computed(() => {
  if (store.sensor.samplingRunning === true) return '采集中'
  if (store.sensor.samplingRunning === false) return '已暂停'
  return '--'
})

const activeStreamCount = computed(() => {
  return Object.values(store.detection.activeStreams).filter((item) => item.running).length
})

const visibleEvents = computed(() => store.recentEvents.slice(0, 5))
const visibleCommands = computed(() => store.commands.recent.slice(0, 4))

async function reconnect() {
  resetIntegrationEvents()
  try {
    await fetchRecentIntegrationEvents(hubBaseUrl.value)
  } catch {
    // SSE connection state will show the useful runtime error.
  }
  connectIntegrationHubEvents(hubBaseUrl.value)
}

function saveHubBaseUrl() {
  hubBaseUrl.value = persistIntegrationHubBaseUrl(hubDraft.value)
  hubDraft.value = hubBaseUrl.value
  reconnect()
}

function resetHubBaseUrlHandler() {
  hubBaseUrl.value = resetIntegrationHubBaseUrl()
  hubDraft.value = hubBaseUrl.value
  reconnect()
}

async function sendCommand(command) {
  commandBusy.value = true
  commandError.value = ''
  try {
    await publishIntegrationCommand(hubBaseUrl.value, command)
  } catch (error) {
    commandError.value = error instanceof Error ? error.message : '命令发送失败'
  } finally {
    commandBusy.value = false
  }
}

function sendSensorCommand(active) {
  return sendCommand({
    type: active ? 'sensor.sampling.start' : 'sensor.sampling.stop',
    target: 'sensor-management-edge',
    subject: 'sensor-gateway',
    payload: { active },
  })
}

function sendRtspCommand(active) {
  const streamId = 'rtsp_cam_01'
  return sendCommand({
    type: active ? 'detection.rtsp.start' : 'detection.rtsp.stop',
    target: 'real-time-detection',
    subject: streamId,
    payload: active
      ? {
          streamId,
          rtspUrl: getRealtimeDetectionRtspUrl(),
          cameraName: 'RTSP Camera',
        }
      : { streamId },
  })
}

onMounted(reconnect)
onBeforeUnmount(disconnectIntegrationHubEvents)
</script>

<style scoped>
.integration-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.integration-head,
.config-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.integration-title {
  margin: 0;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.integration-subtitle,
.empty-text,
.error-text {
  margin: 5px 0 0;
  font-size: 11px;
  word-break: break-all;
}

.integration-subtitle,
.empty-text {
  color: #64748b;
}

.error-text {
  color: #b91c1c;
}

.connection-chip {
  min-width: 52px;
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.connection-chip.online {
  color: #15803d;
  background: #dcfce7;
}

.connection-chip.pending {
  color: #b45309;
  background: #fef3c7;
}

.connection-chip.offline {
  color: #b91c1c;
  background: #fee2e2;
}

.hub-input {
  flex: 1;
  min-width: 0;
  height: 34px;
  padding: 0 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  color: #334155;
  background: #f8fafc;
}

.small-btn,
.command-btn {
  height: 34px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
}

.small-btn.secondary {
  color: #2563eb;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.small-btn.ghost {
  color: #475569;
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.metric-grid,
.command-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.metric-item {
  padding: 10px;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.metric-item.warn {
  grid-column: 1 / -1;
  background: #fff7ed;
  border-color: #fed7aa;
}

.metric-item span {
  display: block;
  margin-bottom: 5px;
  color: #64748b;
  font-size: 11px;
}

.metric-item strong {
  color: #0f172a;
  font-size: 12px;
}

.command-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
}

.panel-title {
  color: #0f172a;
  font-size: 12px;
  font-weight: 700;
}

.command-btn {
  color: #0f172a;
  background: #f8fafc;
  border-color: #cbd5e1;
}

.command-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.event-list,
.command-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.event-row,
.command-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 9px;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  font-size: 11px;
}

.command-row.completed {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.command-row.failed {
  background: #fef2f2;
  border-color: #fecaca;
}

.event-type,
.command-type {
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-source,
.command-status {
  color: #64748b;
  flex: 0 0 auto;
}
</style>
