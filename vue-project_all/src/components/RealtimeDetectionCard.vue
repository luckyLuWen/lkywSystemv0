<template>
  <section class="realtime-detection-card">
    <!-- 头部区域 -->
    <div class="card-head">
      <div>
        <h3 class="card-title">实时检测服务</h3>
        <p class="card-subtitle">{{ detectionBaseUrl }}</p>
      </div>
      <span class="status-badge" :class="backendOnline ? 'online' : 'offline'">
        {{ backendOnline ? '在线' : '离线' }}
      </span>
    </div>

    <!-- 垂直面板区 -->
    <div class="scroll-container">
      
      <!-- 1. 模型配置 -->
      <div v-if="!onlyControl" class="card-section">
        <div class="section-title-wrapper">
          <span class="bracket">[</span>
          <h4 class="section-subtitle-text">模型配置</h4>
          <span class="bracket">]</span>
        </div>
        
        <div class="model-select-group">
          <span class="control-label-text">模型选择</span>
          <select v-model="settings.model" class="cyber-select-compact" :disabled="!backendOnline">
            <option v-for="model in availableModels" :key="model.name" :value="model.name">
              {{ cleanModelName(model.name) }}
            </option>
            <option v-if="availableModels.length === 0" value="">暂无可用模型</option>
          </select>
          <div class="tag-row">
            <span class="tag-compact">主模型与对照模型</span>
          </div>
        </div>

        <div class="control-slider-group">
          <div class="slider-label-row">
            <span>置信度设置</span>
            <span class="slider-val-text">{{ settings.conf }}</span>
          </div>
          <input 
            type="range" 
            v-model.number="settings.conf" 
            min="0.1" 
            max="0.9" 
            step="0.05" 
            class="cyber-range-compact"
            :disabled="!backendOnline"
          />
        </div>

        <div class="control-slider-group">
          <div class="slider-label-row">
            <span>IOU阈值设置</span>
            <span class="slider-val-text">{{ settings.iou }}</span>
          </div>
          <input 
            type="range" 
            v-model.number="settings.iou" 
            min="0.1" 
            max="0.9" 
            step="0.05" 
            class="cyber-range-compact"
            :disabled="!backendOnline"
          />
        </div>
      </div>

      <!-- 2. 模型性能指标 -->
      <div v-if="!onlyControl" class="card-section">
        <div class="section-title-wrapper">
          <span class="bracket">[</span>
          <h4 class="section-subtitle-text">模型性能指标</h4>
          <span class="bracket">]</span>
        </div>

        <div v-if="selectedModelPerformance" class="performance-grid">
          <div class="performance-item wide">
            <span class="perf-label">模型名称</span>
            <strong>{{ selectedModelPerformance.model_name || selectedModelLabel }}</strong>
          </div>
          <div class="performance-item">
            <span class="perf-label">mAP50</span>
            <strong>≥85%</strong>
            <small>{{ formatMetric(selectedModelPerformance.map50) }}</small>
          </div>
          <div class="performance-item">
            <span class="perf-label">Precision</span>
            <strong>{{ formatMetric(selectedModelPerformance.precision) }}</strong>
          </div>
          <div class="performance-item">
            <span class="perf-label">Recall</span>
            <strong>{{ formatMetric(selectedModelPerformance.recall) }}</strong>
          </div>
          <div class="performance-item wide">
            <span class="perf-label">测试集</span>
            <strong>{{ selectedModelPerformance.test_set || 'LKYWDetection Test set' }}</strong>
          </div>
        </div>
        <div v-else class="metric-placeholder">等待检测后端返回模型指标</div>
      </div>

      <!-- 3. 核心监测指标 -->
      <div v-if="!onlyControl && backendOnline && systemInfoData" class="card-section">
        <div class="section-title-wrapper">
          <span class="bracket">[</span>
          <h4 class="section-subtitle-text">核心监测指标</h4>
          <span class="bracket">]</span>
        </div>

        <div class="telemetry-list">
          <div class="telemetry-row">
            <span class="telemetry-col-label">GPU</span>
            <span class="telemetry-col-val text-cyan-glow">{{ systemInfoData.gpu_name || '--' }}</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">CUDA</span>
            <span class="telemetry-col-val text-cyan-glow">{{ systemInfoData.cuda_version || '--' }}</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">VRAM</span>
            <span class="telemetry-col-val">{{ systemInfoData.vram_used_gb || 0 }} / {{ systemInfoData.vram_total_gb || 0 }} GB</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">GPU_温度</span>
            <span class="telemetry-col-val">{{ systemInfoData.gpu_temp || '--' }}°C</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">GPU_利用率</span>
            <span class="telemetry-col-val">{{ systemInfoData.gpu_util || '--' }}%</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">已加载模型</span>
            <span class="telemetry-col-val" :class="{ 'text-cyan-glow': systemInfoData.model_loaded }">
              {{ systemInfoData.model_loaded ? cleanModelName(systemInfoData.model_name) : '待加载' }}
            </span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">今日检测次数</span>
            <span class="telemetry-col-val text-amber-glow">{{ systemInfoData.total_detections_today }}</span>
          </div>
        </div>

        <!-- 动态声波装饰跳动条 -->
        <div class="wave-decoration-compact">
          <div 
            class="wave-bar-compact" 
            v-for="i in 22" 
            :key="i" 
            :style="{ height: getWaveHeight(i) }"
          ></div>
        </div>
      </div>

      <!-- 4. 检测数据统计 -->
      <div v-if="!onlyControl && backendOnline && statsData" class="card-section">
        <div class="section-title-wrapper">
          <span class="bracket">[</span>
          <h4 class="section-subtitle-text">检测数据统计</h4>
          <span class="bracket">]</span>
        </div>

        <!-- 三宫格累计指标磁贴 -->
        <div class="mini-metrics-row">
          <div class="metric-block">
            <span class="metric-val text-cyan-glow">{{ statsData.total_detections }}</span>
            <span class="metric-lbl">累计检测数</span>
          </div>
          <div class="metric-block">
            <span class="metric-val text-amber-glow">{{ statsData.today_detections }}</span>
            <span class="metric-lbl">今日检测</span>
          </div>
          <div class="metric-block">
            <span class="metric-val">{{ statsData.avg_inference_time_s }}s</span>
            <span class="metric-lbl">平均推理</span>
          </div>
        </div>

        <!-- 饼图类别分布 (Conic Gradient) -->
        <div v-if="Object.keys(statsData.class_distribution || {}).length > 0" class="chart-section">
          <span class="chart-title-label">类别分布</span>
          <div class="doughnut-chart" :style="{ background: doughnutGradient }">
            <div class="doughnut-hole">
              <span class="total-text">{{ statsData.total_detections }}次</span>
            </div>
          </div>
          
          <!-- 类别图例 -->
          <div class="legends-grid">
            <div 
              v-for="(count, clsName) in statsData.class_distribution" 
              :key="clsName" 
              class="legend-item"
            >
              <span class="legend-name">
                <span class="legend-dot" :style="{ backgroundColor: getclassColor(clsName) }"></span>
                {{ getclassLabel(clsName) }}
              </span>
              <span class="legend-val">{{ count }} 次</span>
            </div>
          </div>
        </div>

        <!-- 模型使用分布 -->
        <div v-if="Object.keys(statsData.model_usage || {}).length > 0" class="chart-section">
          <span class="chart-title-label">模型使用分布</span>
          <div class="model-usage-list">
            <div 
              v-for="(count, modelName) in statsData.model_usage" 
              :key="modelName" 
              class="model-usage-item"
            >
              <div class="usage-label-row">
                <span class="usage-name">{{ cleanModelName(modelName) }}</span>
                <span class="usage-val">{{ count }} 次</span>
              </div>
              <div class="usage-track">
                <div class="usage-fill" :style="{ width: getModelPct(count) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 离线提示占位符 -->
      <div v-if="!onlyControl && !backendOnline" class="offline-placeholder">
        <span class="placeholder-icon">⚠️</span>
        <p>检测后端处于离线状态，暂无实时监测指标与统计图表。</p>
      </div>

    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, reactive } from 'vue'

const props = defineProps({
  onlyControl: {
    type: Boolean,
    default: false
  }
})
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

// 统计、模型配置和显卡遥测数据
const statsData = ref(null)
const systemInfoData = ref(null)
const availableModels = ref([])

const settings = reactive({
  model: '',
  conf: 0.25,
  iou: 0.45
})

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

const MODEL_NAME_MAP = {
  'SFGA-YOLO26M': 'SFGA-YOLO26M',
  yolo26M: 'YOLO26M',
  yolo11M: 'YOLO11M',
  yolo26m_BestPt_1: 'YOLO26M',
  yolo11m_BestPt_0: 'YOLO11M',
  YOLO26M: 'YOLO26M',
  YOLO11M: 'YOLO11M'
}

const cleanModelName = (name) => {
  if (!name) return ''
  return MODEL_NAME_MAP[name] || String(name).replace(/（.*）$/, '')
}

const selectedModel = computed(() => {
  return availableModels.value.find(model => model.name === settings.model) || null
})

const selectedModelLabel = computed(() => {
  const model = selectedModel.value
  if (!model) return cleanModelName(settings.model) || '未选择'
  return model.performance?.model_name || model.display_name || cleanModelName(model.name)
})

const selectedModelPerformance = computed(() => {
  return selectedModel.value?.performance || null
})

const formatMetric = (value) => {
  if (value === undefined || value === null || value === '') return '--'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(4) : String(value)
}

// 动态生成圆环图的 conic-gradient 渐变值
const doughnutGradient = computed(() => {
  if (!statsData.value || !statsData.value.class_distribution) return 'transparent'
  const dist = statsData.value.class_distribution
  const total = Object.values(dist).reduce((a, b) => a + b, 0)
  if (total === 0) return 'transparent'
  
  let currentPct = 0
  const parts = []
  Object.entries(dist).forEach(([cls, cnt]) => {
    const pct = (cnt / total) * 100
    const color = getclassColor(cls)
    parts.push(`${color} ${currentPct}% ${currentPct + pct}%`)
    currentPct += pct
  })
  return `conic-gradient(${parts.join(', ')})`
})

// 计算声波装饰的高度
const getWaveHeight = (i) => {
  const base = Math.sin(i * 0.4 + (Date.now() / 1500)) * 14 + 18
  return `${Math.max(4, Math.min(32, base))}px`
}

const normalizeClassKey = (cls) => String(cls || '').trim().toLowerCase().replace(/[-\s]+/g, '_')

// 分类中文翻译
const getclassLabel = (cls) => {
  const key = normalizeClassKey(cls)
  const CLASS_LABELS_MAP = {
    car_fire: '普通车辆起火',
    lkyw_fire: '两客一危车辆起火',
    car_nofire: '普通车辆未起火',
    lkyw_nofire: '两客一危车辆未起火',
    car_normal: '普通车辆未起火',
    lkyw_normal: '两客一危车辆未起火'
  }
  return CLASS_LABELS_MAP[key] || cls
}

// 分类色彩配置
const getclassColor = (cls) => {
  const key = normalizeClassKey(cls)
  const CLASS_COLORS_MAP = {
    car_fire: '#E53935',
    lkyw_fire: '#C2185B',
    car_nofire: '#FDD835',
    lkyw_nofire: '#FB8C00',
    car_normal: '#FDD835',
    lkyw_normal: '#FB8C00'
  }
  if (CLASS_COLORS_MAP[key]) return CLASS_COLORS_MAP[key]
  if (key.includes('nofire') || key.includes('normal')) return key.includes('lkyw') ? '#FB8C00' : '#FDD835'
  if (key.includes('fire')) return key.includes('lkyw') ? '#C2185B' : '#E53935'
  return '#cbd5e1'
}

// 模型最大占比计算
const maxModelCount = computed(() => {
  if (!statsData.value || !statsData.value.model_usage) return 1
  const vals = Object.values(statsData.value.model_usage)
  return Math.max(1, ...vals)
})

const getModelPct = (count) => {
  return Math.round((count / maxModelCount.value) * 100)
}

// 获取模型列表
async function fetchModels() {
  try {
    const response = await fetch(buildRealtimeDetectionApiUrl('api/models', detectionBaseUrl.value))
    if (response.ok) {
      const data = await response.json()
      if (data.models && data.models.length > 0) {
        availableModels.value = data.models
        if (!settings.model) {
          settings.model = data.models[0].name
        }
      }
    }
  } catch (e) {
    console.warn('Failed to fetch models:', e)
  }
}

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

  // 只有后端在线时，才拉取模型、系统遥测和统计指标
  if (backendOnline.value) {
    if (availableModels.value.length === 0) {
      await fetchModels()
    }
    
    try {
      const [statsRes, sysRes] = await Promise.all([
        fetch(buildRealtimeDetectionApiUrl('api/stats', detectionBaseUrl.value), { cache: 'no-store' }),
        fetch(buildRealtimeDetectionApiUrl('api/system/info', detectionBaseUrl.value), { cache: 'no-store' })
      ])
      if (statsRes.ok) {
        const statsJson = await statsRes.json()
        if (statsJson.success) statsData.value = statsJson.stats
      }
      if (sysRes.ok) {
        const sysJson = await sysRes.json()
        if (sysJson.success) systemInfoData.value = sysJson.info
      }
    } catch (e) {
      console.warn('Silent telemetry fetch failed:', e)
    }
  } else {
    statsData.value = null
    systemInfoData.value = null
    availableModels.value = []
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
          // 提交当前界面选中的模型配置
          model: settings.model,
          conf: settings.conf,
          iou: settings.iou
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
    lastError.value = error instanceof Error ? error.message : '实时检测操作失败'
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
  height: 100%;
  gap: 16px;
  padding: 20px;
  border: 1px solid rgba(255, 184, 77, 0.28);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(13, 25, 41, 0.94) 0%, rgba(8, 16, 28, 0.94) 100%);
  box-shadow: 0 0 24px rgba(255, 184, 77, 0.14);
  backdrop-filter: blur(10px);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  border-bottom: 1px solid rgba(0, 242, 254, 0.15);
  padding-bottom: 12px;
}

.card-title {
  margin: 0;
  color: #ffcf8b;
  font-size: 20px;
  line-height: 1.2;
}

.card-subtitle {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.72);
  word-break: break-all;
}

/* 垂直滚动容器 */
.scroll-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  flex: 1;
  padding-right: 4px;
}

/* 自定义滚动条 */
.scroll-container::-webkit-scrollbar {
  width: 5px;
}
.scroll-container::-webkit-scrollbar-thumb {
  background: rgba(255, 184, 77, 0.25);
  border-radius: 2.5px;
}

/* 各板块通用样式 */
.card-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 18px;
  border-bottom: 1px dashed rgba(255, 184, 77, 0.12);
}
.card-section:last-child {
  border-bottom: none;
}

.section-title-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.bracket {
  color: #00f2fe;
  font-weight: bold;
  font-size: 20px;
  text-shadow: 0 0 6px rgba(0, 242, 254, 0.5);
}

.section-subtitle-text {
  margin: 0;
  color: #00f2fe;
  font-size: 16px;
  font-weight: bold;
  letter-spacing: 1px;
  text-shadow: 0 0 8px rgba(0, 242, 254, 0.3);
}

/* 1. 模型配置样式 */
.model-select-group {
  background: rgba(0, 0, 0, 0.25);
  padding: 14px;
  border-left: 3px solid #ffb84d;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-label-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.cyber-select-compact {
  width: 100%;
  background: rgba(10, 19, 35, 0.85);
  border: 1px solid #ffb84d;
  color: #ffb84d;
  padding: 10px;
  font-size: 15px;
  font-weight: bold;
  cursor: pointer;
  outline: none;
}
.cyber-select-compact option {
  background: #0d1929;
  color: #ffb84d;
}

.tag-row {
  display: flex;
}
.tag-compact {
  font-size: 11px;
  padding: 2px 6px;
  background: #ffb84d;
  color: #000;
  font-weight: bold;
}

.control-slider-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.slider-label-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.82);
}

.slider-val-text {
  font-weight: bold;
  color: #ffb84d;
}

.cyber-range-compact {
  -webkit-appearance: none;
  width: 100%;
  height: 8px;
  background: rgba(0, 242, 254, 0.12);
  border-radius: 4px;
  outline: none;
}
.cyber-range-compact::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  background: #00f2fe;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 6px #00f2fe;
  transition: transform 0.1s ease;
}
.cyber-range-compact::-webkit-slider-thumb:hover {
  transform: scale(1.25);
}

/* 2. 模型性能指标样式 */
.performance-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.performance-item {
  min-height: 58px;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 184, 77, 0.18);
  background: rgba(255, 184, 77, 0.07);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.performance-item.wide {
  grid-column: 1 / -1;
}

.perf-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.56);
}

.performance-item strong {
  color: #fff3bf;
  font-size: 15px;
  line-height: 1.25;
}

.performance-item small {
  color: #ffcf8b;
  font-size: 11px;
  line-height: 1;
}

.metric-placeholder {
  padding: 12px;
  border-radius: 6px;
  border: 1px dashed rgba(0, 242, 254, 0.22);
  color: rgba(255, 255, 255, 0.62);
  background: rgba(0, 242, 254, 0.05);
  font-size: 13px;
}

/* 兼容旧控制样式 */
.config-row-compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.input-action-row {
  display: flex;
  gap: 8px;
}

.config-input-compact {
  flex: 1;
  min-height: 36px;
  padding: 0 10px;
  border: 1px solid rgba(0, 242, 254, 0.2);
  border-radius: 6px;
  background: rgba(10, 19, 35, 0.85);
  color: #fff;
  font-size: 13px;
  outline: none;
}
.config-input-compact:focus {
  border-color: rgba(0, 242, 254, 0.6);
}

.action-btn-compact {
  min-height: 36px;
  padding: 0 12px;
  border-radius: 6px;
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid rgba(0, 242, 254, 0.3);
  color: #00f2fe;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.action-btn-compact:hover {
  background: rgba(0, 242, 254, 0.2);
}

.status-grid-compact {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.status-item-compact {
  padding: 10px;
  border-radius: 6px;
  background: rgba(10, 19, 35, 0.6);
  border: 1px solid rgba(0, 242, 254, 0.1);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-lbl {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.status-val-txt {
  font-size: 13px;
  font-weight: 500;
}
.status-val-txt.ok {
  color: #ffcf8b;
}
.status-val-txt.warn {
  color: #ffb4b4;
}

.action-row-compact {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn-primary-compact {
  height: 40px;
  border-radius: 6px;
  background: linear-gradient(90deg, #ffb84d 0%, #ffd89a 100%);
  color: #000;
  font-size: 14px;
  font-weight: bold;
  border: none;
  cursor: pointer;
  transition: opacity 0.2s ease;
}
.action-btn-primary-compact:hover {
  opacity: 0.9;
}
.action-btn-primary-compact:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn-ghost-compact {
  height: 34px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.action-btn-ghost-compact:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* 3. 核心监测指标样式 */
.telemetry-list {
  display: flex;
  flex-direction: column;
  gap: 0px;
}

.telemetry-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0, 242, 254, 0.05);
}
.telemetry-row:last-child {
  border-bottom: none;
}

.telemetry-col-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  font-family: monospace;
}

.telemetry-col-val {
  font-size: 14px;
  color: #fff;
  font-weight: bold;
  font-family: monospace;
}

.text-cyan-glow {
  color: #00f2fe !important;
  text-shadow: 0 0 6px rgba(0, 242, 254, 0.4);
}

.text-amber-glow {
  color: #ffb84d !important;
  text-shadow: 0 0 6px rgba(255, 184, 77, 0.4);
}

.wave-decoration-compact {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 38px;
  margin-top: 12px;
  opacity: 0.4;
  justify-content: center;
}

.wave-bar-compact {
  flex: 1;
  max-width: 6px;
  background: #00f2fe;
  border-radius: 1px;
  transition: height 0.3s ease;
}

/* 4. 检测数据统计样式 */
.mini-metrics-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.metric-block {
  background: rgba(10, 19, 35, 0.6);
  border: 1px solid rgba(0, 242, 254, 0.1);
  border-radius: 6px;
  padding: 10px 4px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-val {
  font-size: 18px;
  font-weight: bold;
  font-family: monospace;
}

.metric-lbl {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
}

/* 圆环饼图样式 */
.chart-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.chart-title-label {
  font-size: 13px;
  color: #ffb84d;
  font-weight: bold;
  margin-bottom: 4px;
}

.doughnut-chart {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 12px auto;
  box-shadow: 0 0 12px rgba(0,0,0,0.5);
  transition: background 0.3s ease;
}

.doughnut-hole {
  width: 84px;
  height: 84px;
  border-radius: 50%;
  background: #0b1524;
  display: flex;
  align-items: center;
  justify-content: center;
}

.total-text {
  font-size: 14px;
  color: #ffcf8b;
  font-weight: bold;
}

.legends-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  background: rgba(0,0,0,0.15);
  padding: 10px;
  border-radius: 6px;
}

.legend-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.legend-name {
  color: rgba(255, 255, 255, 0.85);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.legend-val {
  color: #00f2fe;
  font-family: monospace;
}

/* 模型使用列表 */
.model-usage-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.model-usage-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.usage-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.usage-name {
  color: rgba(255, 255, 255, 0.6);
  font-family: monospace;
}

.usage-val {
  color: #ffb84d;
  font-weight: bold;
}

.usage-track {
  height: 5px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2.5px;
  overflow: hidden;
}

.usage-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(0, 242, 254, 0.4), #00f2fe);
  border-radius: 2.5px;
  transition: width 0.5s ease;
}

/* 离线状态提示 */
.offline-placeholder {
  text-align: center;
  padding: 28px 14px;
  background: rgba(168, 54, 54, 0.05);
  border: 1px dashed rgba(255, 180, 180, 0.2);
  border-radius: 8px;
  margin-top: 10px;
}

.placeholder-icon {
  font-size: 26px;
  margin-bottom: 8px;
  display: block;
}

.offline-placeholder p {
  margin: 0;
  font-size: 13px;
  color: #ffb4b4;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
}
.status-badge.online {
  color: #ffd68e;
  background: rgba(255, 184, 77, 0.16);
  border: 1px solid rgba(255, 184, 77, 0.24);
}
.status-badge.offline {
  color: #ffb4b4;
  background: rgba(168, 54, 54, 0.18);
  border: 1px solid rgba(255, 180, 180, 0.28);
}
</style>
