<template>
  <section class="realtime-detection-card">
    <div class="card-head">
      <div>
        <h3 class="card-title">实时检测服务</h3>
        <p class="card-subtitle">{{ detectionBaseUrl }}</p>
      </div>
      <span class="status-badge" :class="backendOnline ? 'online' : 'offline'">
        {{ backendOnline ? '在线' : '离线' }}
      </span>
    </div>

    <div class="config-row">
      <input
        v-model.trim="detectionBaseDraft"
        type="text"
        class="config-input"
        placeholder="例如：http://127.0.0.1:5000"
      />
      <button class="action-btn secondary" @click="saveDetectionBaseUrl">保存地址</button>
      <button class="action-btn ghost" @click="resetDetectionBaseUrlHandler">恢复默认</button>
    </div>

    <div class="config-row">
      <input
        v-model.trim="rtspUrlDraft"
        type="text"
        class="config-input"
        placeholder="例如：rtsp://localhost:8554/live"
      />
      <button class="action-btn secondary" @click="saveRtspUrl">保存流地址</button>
      <button class="action-btn ghost" @click="resetRtspUrlHandler">恢复默认</button>
    </div>

    <div class="status-grid">
      <div class="status-item">
        <span class="status-label">模型状态</span>
        <span class="status-value" :class="modelReady ? 'ok' : 'warn'">
          {{ modelReady ? '已就绪' : '缺少模型' }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">检测任务</span>
        <span class="status-value" :class="rtspRunning ? 'ok' : 'warn'">
          {{ rtspRunning ? '运行中' : '未启动' }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">活跃流数</span>
        <span class="status-value">{{ activeStreams }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">最后更新</span>
        <span class="status-value">{{ formattedLastUpdate }}</span>
      </div>
    </div>

    <div class="meta-row">
      <span class="meta-chip">当前流: {{ currentStreamId }}</span>
      <span class="meta-chip">视频源: {{ resolvedRtspUrl }}</span>
    </div>

    <div class="action-row">
      <button
        class="action-btn primary"
        :disabled="actionPending"
        @click="toggleRtspDetection(!rtspRunning)"
      >
        {{ actionPending ? '执行中...' : rtspRunning ? '停止检测' : '开始检测' }}
      </button>
      <button class="action-btn secondary" @click="refreshStatus">刷新状态</button>
      <button class="action-btn ghost" @click="goToRealtimeDetection">进入实时检测</button>
    </div>

    <p class="tip-text">支持本地调试 RTSP，也支持接入边缘端提供的视频流地址。</p>
    <p v-if="lastError" class="error-text">最近错误：{{ lastError }}</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  DEFAULT_REALTIME_DETECTION_BASE_URL,
  DEFAULT_REALTIME_RTSP_URL,
  buildRealtimeDetectionApiUrl,
  getRealtimeDetectionBaseUrl,
  getRealtimeDetectionRtspUrl,
  persistRealtimeDetectionBaseUrl,
  persistRealtimeDetectionRtspUrl,
  resetRealtimeDetectionBaseUrl,
  resetRealtimeDetectionRtspUrl,
} from '../config/subsystems'

const router = useRouter()
const DEFAULT_STREAM_ID = 'rtsp_cam_01'

const detectionBaseUrl = ref(getRealtimeDetectionBaseUrl())
const detectionBaseDraft = ref(detectionBaseUrl.value)
const rtspUrl = ref(getRealtimeDetectionRtspUrl())
const rtspUrlDraft = ref(rtspUrl.value)

const backendOnline = ref(false)
const modelReady = ref(false)
const activeStreams = ref(0)
const streamList = ref([])
const lastUpdate = ref('')
const lastError = ref('')
const actionPending = ref(false)

let pollingTimer = null

const rtspRunning = computed(() => activeStreams.value > 0)
const currentStreamId = computed(() => streamList.value[0]?.camera_id || DEFAULT_STREAM_ID)
const resolvedRtspUrl = computed(() => streamList.value[0]?.rtsp_url || rtspUrl.value || DEFAULT_REALTIME_RTSP_URL)
const formattedLastUpdate = computed(() => {
  const raw = streamList.value[0]?.last_detection_time || lastUpdate.value
  if (!raw) return '暂无'

  const numeric = Number(raw)
  if (!Number.isNaN(numeric) && numeric > 0) {
    return new Date(numeric * 1000).toLocaleString('zh-CN', { hour12: false })
  }

  const parsed = new Date(raw)
  return Number.isNaN(parsed.getTime()) ? String(raw) : parsed.toLocaleString('zh-CN', { hour12: false })
})

async function refreshStatus() {
  try {
    const [healthResponse, statusResponse] = await Promise.all([
      fetch(buildRealtimeDetectionApiUrl('api/health', detectionBaseUrl.value), { cache: 'no-store' }),
      fetch(buildRealtimeDetectionApiUrl('api/rtsp/status', detectionBaseUrl.value), { cache: 'no-store' }),
    ])

    if (!healthResponse.ok || !statusResponse.ok) {
      throw new Error(`HTTP ${healthResponse.status}/${statusResponse.status}`)
    }

    const health = await healthResponse.json()
    const status = await statusResponse.json()

    backendOnline.value = health.status === 'ok'
    modelReady.value = Boolean(health.model_ready ?? status.model_ready)
    activeStreams.value = Number(status.active_streams || 0)
    streamList.value = Array.isArray(status.streams) ? status.streams : []
    lastUpdate.value = new Date().toISOString()
    lastError.value = ''
  } catch (error) {
    backendOnline.value = false
    modelReady.value = false
    activeStreams.value = 0
    streamList.value = []
    lastError.value = error instanceof Error ? error.message : '无法连接检测服务'
  }
}

async function toggleRtspDetection(nextRunning) {
  actionPending.value = true
  lastError.value = ''

  try {
    if (nextRunning) {
      const response = await fetch(buildRealtimeDetectionApiUrl('api/rtsp/start', detectionBaseUrl.value), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stream_id: DEFAULT_STREAM_ID,
          rtsp_url: rtspUrl.value,
          camera_name: '总系统远程检测',
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
    } else {
      const response = await fetch(
        buildRealtimeDetectionApiUrl(`api/rtsp/stop/${currentStreamId.value}`, detectionBaseUrl.value),
        { method: 'POST' }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
    }

    await refreshStatus()
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : '检测任务控制失败'
  } finally {
    actionPending.value = false
  }
}

function saveDetectionBaseUrl() {
  detectionBaseUrl.value = persistRealtimeDetectionBaseUrl(detectionBaseDraft.value)
  detectionBaseDraft.value = detectionBaseUrl.value
  refreshStatus()
}

function resetDetectionBaseUrlHandler() {
  detectionBaseUrl.value = resetRealtimeDetectionBaseUrl()
  detectionBaseDraft.value = detectionBaseUrl.value
  refreshStatus()
}

function saveRtspUrl() {
  rtspUrl.value = persistRealtimeDetectionRtspUrl(rtspUrlDraft.value)
  rtspUrlDraft.value = rtspUrl.value
}

function resetRtspUrlHandler() {
  rtspUrl.value = resetRealtimeDetectionRtspUrl()
  rtspUrlDraft.value = rtspUrl.value
}

function goToRealtimeDetection() {
  router.push('/realtime')
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
.realtime-detection-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(255, 184, 77, 0.28);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(48, 24, 12, 0.92) 0%, rgba(28, 16, 10, 0.92) 100%);
  box-shadow: 0 0 24px rgba(255, 184, 77, 0.14);
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
  color: #ffcf8b;
  font-size: 18px;
  line-height: 1.2;
}

.card-subtitle,
.tip-text,
.error-text {
  margin: 0;
  font-size: 12px;
}

.card-subtitle,
.tip-text {
  color: rgba(255, 255, 255, 0.72);
  word-break: break-all;
}

.error-text {
  color: #ffb4b4;
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
  border: 1px solid rgba(255, 184, 77, 0.24);
  border-radius: 8px;
  background: rgba(18, 12, 8, 0.94);
  color: #fff;
  outline: none;
}

.config-input:focus {
  border-color: rgba(255, 184, 77, 0.56);
  box-shadow: 0 0 0 2px rgba(255, 184, 77, 0.14);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.status-item {
  padding: 12px;
  border-radius: 10px;
  background: rgba(24, 14, 8, 0.72);
  border: 1px solid rgba(255, 184, 77, 0.14);
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
  color: #ffd68e;
  background: rgba(255, 184, 77, 0.16);
  border: 1px solid rgba(255, 184, 77, 0.24);
}

.status-badge.offline,
.status-value.warn {
  color: #ffb4b4;
  background: rgba(168, 54, 54, 0.18);
  border: 1px solid rgba(255, 180, 180, 0.28);
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
  color: #201106;
  background: linear-gradient(90deg, #ffb84d 0%, #ffd89a 100%);
}

.action-btn.secondary {
  color: #ffd68e;
  background: rgba(255, 184, 77, 0.08);
  border-color: rgba(255, 184, 77, 0.24);
}

.action-btn.ghost {
  color: rgba(255, 255, 255, 0.82);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
}

@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }

  .realtime-detection-card {
    padding: 16px;
  }
}
</style>
