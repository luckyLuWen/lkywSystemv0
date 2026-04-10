<template>
  <section class="sensor-gateway-card">
    <div class="card-head">
      <div>
        <h3 class="card-title">边缘传感器网关</h3>
        <p class="card-subtitle">{{ gatewayBaseUrl }}</p>
      </div>
      <span class="status-badge" :class="gatewayOnline ? 'online' : 'offline'">
        {{ gatewayOnline ? '在线' : '离线' }}
      </span>
    </div>

    <div class="config-row">
      <input
        v-model.trim="gatewayDraft"
        type="text"
        class="gateway-input"
        placeholder="例如：http://127.0.0.1:18080（模拟）或 http://192.168.2.111:8000（边缘）"
      />
      <button class="action-btn secondary" @click="saveGatewayBaseUrl">保存地址</button>
      <button class="action-btn ghost" @click="resetGatewayBaseUrlHandler">恢复默认</button>
    </div>

    <div class="status-grid">
      <div class="status-item">
        <span class="status-label">采集状态</span>
        <span class="status-value" :class="samplingRunning ? 'ok' : 'warn'">
          {{ samplingRunning ? '采集中' : '已暂停' }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">数据库</span>
        <span class="status-value" :class="databaseOnline ? 'ok' : 'warn'">
          {{ databaseOnline ? '正常' : '异常' }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">视频流</span>
        <span class="status-value" :class="videoOnline ? 'ok' : 'warn'">
          {{ videoOnline ? '在线' : '断开' }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">最近采样</span>
        <span class="status-value">{{ formattedLastSampleAt }}</span>
      </div>
    </div>

    <div class="node-row">
      <span
        v-for="node in nodeStatusList"
        :key="node.key"
        class="node-chip"
        :class="node.online ? 'online' : 'offline'"
      >
        {{ node.label }} {{ node.online ? '在线' : '离线' }}
      </span>
    </div>

    <div class="action-row">
      <button
        class="action-btn primary"
        :disabled="actionPending"
        @click="toggleSampling(!samplingRunning)"
      >
        {{ actionPending ? '执行中...' : samplingRunning ? '停止采集' : '开始采集' }}
      </button>
      <button class="action-btn secondary" @click="refreshStatus">刷新状态</button>
      <button class="action-btn ghost" @click="goToSensorManage">进入传感器管理</button>
    </div>

    <p v-if="lastError" class="error-text">最近错误：{{ lastError }}</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  DEFAULT_SENSOR_GATEWAY_BASE_URL,
  buildSensorGatewayApiUrl,
  getSensorGatewayBaseUrl,
  persistSensorGatewayBaseUrl,
  resetSensorGatewayBaseUrl,
} from '../config/subsystems'

const router = useRouter()

const gatewayBaseUrl = ref(getSensorGatewayBaseUrl())
const gatewayDraft = ref(gatewayBaseUrl.value)
const gatewayOnline = ref(false)
const samplingRunning = ref(false)
const databaseOnline = ref(false)
const videoOnline = ref(false)
const lastSampleAt = ref('')
const lastError = ref('')
const actionPending = ref(false)
const nodeStatuses = ref(createEmptyNodes())

let pollingTimer = null

function createEmptyNodes() {
  return {
    node1: { label: 'A', online: false },
    node2: { label: 'B', online: false },
    node3: { label: '固定杆', online: false },
  }
}

function normalizeNodes(nodes = {}) {
  const fallback = createEmptyNodes()
  return {
    node1: {
      ...fallback.node1,
      ...(nodes.node1 || {}),
      label: nodes.node1?.label || fallback.node1.label,
      online: Boolean(nodes.node1?.online),
    },
    node2: {
      ...fallback.node2,
      ...(nodes.node2 || {}),
      label: nodes.node2?.label || fallback.node2.label,
      online: Boolean(nodes.node2?.online),
    },
    node3: {
      ...fallback.node3,
      ...(nodes.node3 || {}),
      label: nodes.node3?.label || fallback.node3.label,
      online: Boolean(nodes.node3?.online),
    },
  }
}

const nodeStatusList = computed(() => [
  { key: 'node1', label: nodeStatuses.value.node1.label, online: nodeStatuses.value.node1.online },
  { key: 'node2', label: nodeStatuses.value.node2.label, online: nodeStatuses.value.node2.online },
  { key: 'node3', label: nodeStatuses.value.node3.label, online: nodeStatuses.value.node3.online },
])

const formattedLastSampleAt = computed(() => {
  if (!lastSampleAt.value) return '暂无'
  const parsed = new Date(lastSampleAt.value)
  return Number.isNaN(parsed.getTime())
    ? lastSampleAt.value
    : parsed.toLocaleString('zh-CN', { hour12: false })
})

async function refreshStatus() {
  const baseUrl = gatewayBaseUrl.value || DEFAULT_SENSOR_GATEWAY_BASE_URL

  try {
    const [healthResponse, statusResponse] = await Promise.all([
      fetch(buildSensorGatewayApiUrl('health', baseUrl), { cache: 'no-store' }),
      fetch(buildSensorGatewayApiUrl('status', baseUrl), { cache: 'no-store' }),
    ])

    if (!healthResponse.ok || !statusResponse.ok) {
      throw new Error(`HTTP ${healthResponse.status}/${statusResponse.status}`)
    }

    const health = await healthResponse.json()
    const status = await statusResponse.json()

    gatewayOnline.value = Boolean(health.ok && status.gateway_online)
    samplingRunning.value = Boolean(status.running)
    databaseOnline.value = Boolean(status.database?.ok)
    videoOnline.value = Boolean(status.video?.online)
    lastSampleAt.value = status.last_sample_at || ''
    nodeStatuses.value = normalizeNodes(status.nodes)
    lastError.value = ''
  } catch (error) {
    gatewayOnline.value = false
    samplingRunning.value = false
    databaseOnline.value = false
    videoOnline.value = false
    nodeStatuses.value = createEmptyNodes()
    lastError.value = error instanceof Error ? error.message : '无法连接边缘网关'
  }
}

async function toggleSampling(active) {
  actionPending.value = true
  lastError.value = ''

  try {
    const response = await fetch(buildSensorGatewayApiUrl('control', gatewayBaseUrl.value), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ active }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    await refreshStatus()
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : '采集控制失败'
  } finally {
    actionPending.value = false
  }
}

function saveGatewayBaseUrl() {
  gatewayBaseUrl.value = persistSensorGatewayBaseUrl(gatewayDraft.value)
  gatewayDraft.value = gatewayBaseUrl.value
  refreshStatus()
}

function resetGatewayBaseUrlHandler() {
  gatewayBaseUrl.value = resetSensorGatewayBaseUrl()
  gatewayDraft.value = gatewayBaseUrl.value
  refreshStatus()
}

function goToSensorManage() {
  router.push('/sensor-manage')
}

onMounted(() => {
  refreshStatus()
  pollingTimer = window.setInterval(refreshStatus, 5000)
})

onBeforeUnmount(() => {
  if (pollingTimer) {
    window.clearInterval(pollingTimer)
  }
})
</script>

<style scoped>
.sensor-gateway-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(5, 28, 56, 0.92) 0%, rgba(4, 18, 38, 0.92) 100%);
  box-shadow: 0 0 24px rgba(0, 229, 255, 0.15);
  backdrop-filter: blur(10px);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.card-title {
  margin: 0;
  color: var(--primary-color);
  font-size: 18px;
  line-height: 1.2;
}

.card-subtitle {
  margin: 6px 0 0;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  word-break: break-all;
}

.status-badge,
.node-chip,
.status-value {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
}

.status-badge.online,
.node-chip.online,
.status-value.ok {
  color: #67f7b2;
  background: rgba(28, 140, 96, 0.2);
  border: 1px solid rgba(103, 247, 178, 0.32);
}

.status-badge.offline,
.node-chip.offline,
.status-value.warn {
  color: #ff8f8f;
  background: rgba(160, 40, 40, 0.18);
  border: 1px solid rgba(255, 143, 143, 0.32);
}

.config-row,
.action-row,
.node-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.gateway-input {
  flex: 1 1 220px;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid rgba(0, 229, 255, 0.28);
  border-radius: 8px;
  background: rgba(2, 11, 22, 0.95);
  color: #fff;
  outline: none;
}

.gateway-input:focus {
  border-color: rgba(0, 229, 255, 0.56);
  box-shadow: 0 0 0 2px rgba(0, 229, 255, 0.16);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.status-item {
  padding: 12px;
  border-radius: 10px;
  background: rgba(1, 12, 28, 0.72);
  border: 1px solid rgba(0, 229, 255, 0.16);
}

.status-label {
  display: block;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
}

.action-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.action-btn.primary {
  color: #041424;
  background: linear-gradient(90deg, #4ff0ff 0%, #8cf7ff 100%);
}

.action-btn.secondary {
  color: var(--primary-color);
  background: rgba(0, 229, 255, 0.08);
  border-color: rgba(0, 229, 255, 0.24);
}

.action-btn.ghost {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
}

.error-text {
  margin: 0;
  color: #ff9b9b;
  font-size: 12px;
}

@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }

  .sensor-gateway-card {
    padding: 16px;
  }
}
</style>
