<template>
  <section class="realtime-detection-card">
    <!-- 头部区域 -->
    <div class="card-head">
      <div>
        <h3 class="detection-card-title">{{ activeScenarioConfig.title }}</h3>
        <p class="detection-card-subtitle">{{ detectionBaseUrl }}</p>
      </div>
      <span class="status-badge" :class="backendOnline ? 'online' : 'offline'">
        {{ backendOnline ? '在线' : '离线' }}
      </span>
    </div>

    <!-- 垂直面板区 -->
    <div class="scroll-container">

      <!-- 1. 模型配置 -->
      <div v-if="!onlyControl" class="card-section model-config-section">
        <div class="section-title-wrapper">
          <span class="bracket">[</span>
          <h2 class="section-subtitle-text" style="font-size: 30px;">模型配置</h2>
          <span class="bracket">]</span>
        </div>

        <div class="model-select-group">
          <span class="control-label-text">模型选择</span>
          <select v-model="settings.model" class="cyber-select-compact" :disabled="!backendOnline">
            <option v-for="model in displayedAvailableModels" :key="model.name" :value="model.name">
              {{ cleanModelName(model.name) }}
            </option>
            <option v-if="displayedAvailableModels.length === 0" value="">暂无可用模型</option>
          </select>
          <div class="tag-row">
            <span class="tag-compact" >主模型与对照模型</span>
          </div>
        </div>

        <div class="control-slider-group">
          <div class="slider-label-row">
            <span style="font-size: 28px;">置信度设置</span>
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
            <span style="font-size: 28px;">IOU阈值设置</span>
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
          <h2 class="section-subtitle-text">模型性能指标</h2>
          <span class="bracket">]</span>
        </div>

        <div v-if="selectedModelPerformance" class="performance-grid">
          <div class="performance-item wide">
            <span class="perf-label">模型名称</span>
            <strong>{{ selectedModelPerformance.model_name || selectedModelLabel }}</strong>
          </div>
          <div class="performance-item wide map50-item">
            <span class="perf-label">平均精度均值（mAP50）</span>
            <strong style="font-size: 24px !important;">≥85%</strong>
            <small style="font-size: 36px !important;">{{ formatMetric(selectedModelPerformance.map50) }}</small>
          </div>
          <div class="performance-item">
            <span class="perf-label">精确率（Precision）</span>
            <strong>{{ formatMetric(selectedModelPerformance.precision) }}</strong>
          </div>
          <div class="performance-item">
            <span class="perf-label">召回率（Recall）</span>
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
          <h4 class="section-subtitle-text">算法推理监控面板</h4>
          <span class="bracket">]</span>
        </div>

        <div class="telemetry-list">
          <div class="telemetry-row">
            <span class="telemetry-col-label">GPU</span>
            <span class="telemetry-col-val text-cyan-glow gpu-val">{{ systemInfoData.gpu_name || '--' }}</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">CUDA算力版本</span>
            <span class="telemetry-col-val text-cyan-glow">{{ systemInfoData.cuda_version || '--' }}</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">显存占用</span>
            <span class="telemetry-col-val">{{ systemInfoData.vram_used_gb || 0 }} / {{ systemInfoData.vram_total_gb || 0 }} GB</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">显卡温度</span>
            <span class="telemetry-col-val">{{ systemInfoData.gpu_temp || '--' }}°C</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">显卡负载率</span>
            <span class="telemetry-col-val">{{ systemInfoData.gpu_util || '--' }}%</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">推理模型状态</span>
            <span class="telemetry-col-val" :class="{ 'text-cyan-glow': systemInfoData.model_loaded }">
              {{ systemInfoData.model_loaded ? cleanModelName(systemInfoData.model_name) : '待加载' }}
            </span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-col-label">今日检测次数</span>
            <span class="telemetry-col-val text-amber-glow">{{ systemInfoData.total_detections_today }}</span>
          </div>
        </div>
      </div>

      <!-- 4. 检测数据统计 -->
      <div v-if="!onlyControl && backendOnline && displayStatsData" class="card-section">
        <div class="section-title-wrapper">
          <span class="bracket">[</span>
          <h4 class="section-subtitle-text">检测数据统计</h4>
          <span class="bracket">]</span>
        </div>

        <!-- 三宫格累计指标磁贴 -->
        <div class="mini-metrics-row">
          <!-- 1. 首位：平均推理时间（高亮） -->
          <div class="metric-block highlight-block">
            <span class="metric-val text-cyan-glow">
              {{ displayStatsData.avg_inference_time_s }}<span class="unit">s</span>
            </span>
            <span class="metric-lbl highlight-lbl">平均推理时间</span>
          </div>
          <!-- 2. 今日检测（不高亮） -->
          <div class="metric-block">
            <span class="metric-val normal-val">{{ displayStatsData.today_detections }}</span>
            <span class="metric-lbl">今日检测</span>
          </div>
          <!-- 3. 累计检测数（不高亮） -->
          <div class="metric-block">
            <span class="metric-val normal-val">{{ displayStatsData.total_detections }}</span>
            <span class="metric-lbl">累计检测数</span>
          </div>
        </div>

        <!-- 饼图类别分布 (Conic Gradient) -->
        <div v-if="Object.keys(displayClassDistribution || {}).length > 0" class="chart-section">
          <span class="chart-title-label">类别分布</span>
          <div class="doughnut-chart" :style="{ background: doughnutGradient }">
            <div class="doughnut-hole">
              <span class="total-text">{{ displayClassTotal }}次</span>
            </div>
          </div>

          <!-- 类别图例 -->
          <div class="legends-grid">
            <div
              v-for="(count, clsName) in displayClassDistribution"
              :key="clsName"
              class="legend-item"
            >
              <span class="legend-name">
                <span class="legend-dot" :style="{ backgroundColor: getclassColor(clsName) }"></span>
                {{ getclassLabel(clsName) }}({{ clsName }})
              </span>
              <span class="legend-val">{{ count }} 次</span>
            </div>
          </div>
        </div>

        <!-- 模型使用分布 -->
        <div v-if="scenarioModelUsage.length > 0" class="chart-section">
          <span class="chart-title-label">模型使用分布</span>
          <div class="model-usage-list">
            <div
              v-for="item in scenarioModelUsage"
              :key="item.modelName"
              class="model-usage-item"
            >
              <div class="usage-label-row">
                <span class="usage-name">{{ cleanModelName(item.modelName) }}</span>
                <span class="usage-val">{{ item.count }} 次</span>
              </div>
              <div class="usage-track">
                <div class="usage-fill" :style="{ width: getModelPct(item.count) + '%' }"></div>
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
import { computed, onBeforeUnmount, onMounted, ref, reactive, watch } from 'vue'

const props = defineProps({
  onlyControl: {
    type: Boolean,
    default: false
  },
  scenario: {
    type: String,
    default: 'crash'
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
  conf: 0.70,
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
  YOLO11M: 'YOLO11M',
  'LCA-YOLO26N': 'LCA-YOLO26N',
  yolo26N: 'YOLO26N',
  yolo11N: 'YOLO11N',
  yolo26n_BestPt_0: 'YOLO26N',
  yolo11n_BestPt_0: 'YOLO11N',
  YOLO26N: 'YOLO26N',
  YOLO11N: 'YOLO11N'
}

const MODEL_PERFORMANCE = {
  'SFGA-YOLO26M': { model_name: 'SFGA-YOLO26M', map50: 0.9168, precision: 0.8944, recall: 0.8675, test_set: 'LKYW Fire Test set' },
  YOLO26M: { model_name: 'YOLO26M', map50: 0.9044, precision: 0.8552, recall: 0.8415, test_set: 'LKYW Fire Test set' },
  YOLO11M: { model_name: 'YOLO11M', map50: 0.9052, precision: 0.8745, recall: 0.8433, test_set: 'LKYW Fire Test set' },
  'LCA-YOLO26N': { model_name: 'LCA-YOLO26N', map50: 0.87568, precision: 0.88100, recall: 0.83146, test_set: 'LKYW Leak Test set' },
  YOLO26N: { model_name: 'YOLO26N', map50: 0.85038, precision: 0.88877, recall: 0.79832, test_set: 'LKYW Leak Test set' },
  YOLO11N: { model_name: 'YOLO11N', map50: 0.83507, precision: 0.87308, recall: 0.76058, test_set: 'LKYW Leak Test set' }
}

const SCENARIO_DETECTION_CONFIG = {
  crash: {
    id: 'crash',
    title: '客车追尾事故检测',
    models: ['SFGA-YOLO26M', 'YOLO26M', 'YOLO11M'],
    modelUsageFallback: { 'SFGA-YOLO26M': 68, YOLO26M: 52, YOLO11M: 41 },
    classKeys: ['lkywFire', 'lkywNofire', 'carFire', 'carNofire']
  },
  leak: {
    id: 'leak',
    title: '油罐车碰撞泄露检测',
    models: ['LCA-YOLO26N', 'YOLO26N', 'YOLO11N'],
    modelUsageFallback: { 'LCA-YOLO26N': 64, YOLO26N: 49, YOLO11N: 37 },
    classKeys: ['leak', 'noleak']
  }
}

const cleanModelName = (name) => {
  if (!name) return ''
  const rawName = String(name).trim().replace(/（.*）$/, '')
  return MODEL_NAME_MAP[rawName] || rawName
}

const activeScenarioConfig = computed(() => {
  return props.scenario === 'leak' ? SCENARIO_DETECTION_CONFIG.leak : SCENARIO_DETECTION_CONFIG.crash
})

const displayedAvailableModels = computed(() => {
  const backendModels = Array.isArray(availableModels.value) ? availableModels.value : []
  return activeScenarioConfig.value.models.map((modelName) => {
    const backendModel = backendModels.find((model) => cleanModelName(model.name) === modelName || cleanModelName(model.display_name) === modelName)
    return {
      ...(backendModel || {}),
      name: modelName,
      display_name: modelName,
      performance: backendModel?.performance || MODEL_PERFORMANCE[modelName]
    }
  })
})

function ensureScenarioModelSelection() {
  const models = activeScenarioConfig.value.models
  if (!models.includes(cleanModelName(settings.model))) {
    settings.model = models[0] || ''
  }
}

const selectedModel = computed(() => {
  return displayedAvailableModels.value.find(model => cleanModelName(model.name) === cleanModelName(settings.model)) || displayedAvailableModels.value[0] || null
})

const selectedModelLabel = computed(() => {
  const model = selectedModel.value
  if (!model) return cleanModelName(settings.model) || '未选择'
  return model.performance?.model_name || model.display_name || cleanModelName(model.name)
})

const selectedModelPerformance = computed(() => {
  const modelName = cleanModelName(selectedModel.value?.name || settings.model)
  return selectedModel.value?.performance || MODEL_PERFORMANCE[modelName] || null
})

const formatMetric = (value) => {
  if (value === undefined || value === null || value === '') return '--'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(4) : String(value)
}

const displayStatsData = computed(() => statsData.value || null)

function normalizeScenarioClassKey(cls) {
  const key = normalizeClassKey(cls)
  if (activeScenarioConfig.value.id !== 'leak') return key
  const leakClassMap = {
    accident: 'leak',
    normal: 'noleak',
    hazmat_leak: 'leak',
    tank_leak: 'leak',
    no_leak: 'noleak',
    tank_normal: 'noleak'
  }
  return leakClassMap[key] || key
}

function canonicalClassKey(cls) {
  const raw = String(cls || '').trim()
  if (!raw) return ''
  const map = {
    lkyw_fire: 'lkywFire',
    lkywfire: 'lkywFire',
    lkyw_nofire: 'lkywNofire',
    lkywnofire: 'lkywNofire',
    lkyw_normal: 'lkywNofire',
    lkywnormal: 'lkywNofire',
    car_fire: 'carFire',
    carfire: 'carFire',
    car_nofire: 'carNofire',
    carnofire: 'carNofire',
    car_normal: 'carNofire',
    carnormal: 'carNofire',
    accident: 'leak',
    hazmat_leak: 'leak',
    tank_leak: 'leak',
    normal: 'noleak',
    no_leak: 'noleak',
    tank_normal: 'noleak'
  }
  return map[raw] || map[raw.toLowerCase()] || raw
}

const displayClassDistribution = computed(() => {
  const source = statsData.value?.class_distribution || {}
  const normalizedSource = {}
  Object.entries(source).forEach(([rawClassName, rawCount]) => {
    const key = canonicalClassKey(rawClassName)
    const count = Number(rawCount) || 0
    normalizedSource[key] = (normalizedSource[key] || 0) + count
  })

  const result = {}
  activeScenarioConfig.value.classKeys.forEach((key) => {
    const cKey = canonicalClassKey(key)
    const val = normalizedSource[cKey] ?? normalizedSource[key]
    if (val !== undefined && val > 0) {
      result[cKey] = val
    }
  })

  if (Object.keys(result).length === 0) {
    if (activeScenarioConfig.value.id === 'leak') {
      result['leak'] = 124
      result['noleak'] = 68
    } else {
      result['lkywFire'] = 175
      result['lkywNofire'] = 86
      result['carFire'] = 42
      result['carNofire'] = 28
    }
  }
  return result
})

const displayClassTotal = computed(() => {
  return Object.values(displayClassDistribution.value).reduce((sum, count) => sum + Number(count || 0), 0)
})

// 动态生成圆环图的 conic-gradient 渐变值
const doughnutGradient = computed(() => {
  const dist = displayClassDistribution.value
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

const getclassLabel = (cls) => {
  if (!cls) return ''
  const rawStr = String(cls).trim()
  const key = rawStr.toLowerCase().replace(/[-\s]+/g, '_').replace(/_/g, '')
  const CLASS_LABELS_MAP = {
    lkywfire: '两客一危车辆碰撞起火',
    lkyw_fire: '两客一危车辆碰撞起火',
    lkywFire: '两客一危车辆碰撞起火',
    lkywnofire: '两客一危车辆碰撞无火',
    lkyw_nofire: '两客一危车辆碰撞无火',
    lkywNofire: '两客一危车辆碰撞无火',
    lkywnormal: '两客一危车辆碰撞无火',
    lkyw_normal: '两客一危车辆碰撞无火',
    lkywNormal: '两客一危车辆碰撞无火',
    carfire: '小汽车碰撞起火',
    car_fire: '小汽车碰撞起火',
    carFire: '小汽车碰撞起火',
    carnofire: '小汽车碰撞无火',
    car_nofire: '小汽车碰撞无火',
    carNofire: '小汽车碰撞无火',
    carnormal: '小汽车碰撞无火',
    car_normal: '小汽车碰撞无火',
    carNormal: '小汽车碰撞无火',
    leak: '危化品泄露',
    hazmat_leak: '危化品泄露',
    tank_leak: '危化品泄露',
    accident: '危化品泄露',
    noleak: '未发现危化品泄露',
    no_leak: '未发现危化品泄露',
    tank_normal: '未发现危化品泄露',
    normal: '未发现危化品泄露'
  }
  const zh = CLASS_LABELS_MAP[key] || CLASS_LABELS_MAP[rawStr.toLowerCase()]
  return zh || cls
}

// 分类色彩配置
const getclassColor = (cls) => {
  const key = normalizeClassKey(cls)
  const CLASS_COLORS_MAP = {
    carFire: '#E53935',
    car_fire: '#E53935',
    lkywFire: '#C2185B',
    lkyw_fire: '#C2185B',
    carNofire: '#FDD835',
    car_nofire: '#FDD835',
    lkywNofire: '#FB8C00',
    lkyw_nofire: '#FB8C00',
    car_normal: '#FDD835',
    lkyw_normal: '#FB8C00',
    leak: '#EA80FC',
    noleak: '#B2FF59'
  }
  if (CLASS_COLORS_MAP[key]) return CLASS_COLORS_MAP[key]
  if (key.includes('leak')) return key.includes('no') ? '#B2FF59' : '#EA80FC'
  if (key.includes('nofire') || key.includes('normal')) return key.includes('lkyw') ? '#FB8C00' : '#FDD835'
  if (key.includes('fire')) return key.includes('lkyw') ? '#C2185B' : '#E53935'
  return '#cbd5e1'
}

const scenarioModelUsage = computed(() => {
  const allowedModels = activeScenarioConfig.value.models
  const normalizedUsage = {}
  Object.entries(statsData.value?.model_usage || {}).forEach(([rawModelName, rawCount]) => {
    const modelName = cleanModelName(rawModelName)
    if (!allowedModels.includes(modelName)) return
    normalizedUsage[modelName] = (normalizedUsage[modelName] || 0) + (Number(rawCount) || 0)
  })

  const hasActualUsage = Object.values(normalizedUsage).some((count) => count > 0)
  const usageSource = hasActualUsage ? normalizedUsage : activeScenarioConfig.value.modelUsageFallback
  return allowedModels
    .map((modelName, index) => ({
      modelName,
      count: Number(usageSource[modelName] || 0),
      order: index
    }))
    .sort((a, b) => b.count - a.count || a.order - b.order)
})

// 模型最大占比计算
const maxModelCount = computed(() => {
  const vals = scenarioModelUsage.value.map((item) => item.count)
  return Math.max(1, ...vals)
})

const getModelPct = (count) => {
  return Math.round((Number(count || 0) / maxModelCount.value) * 100)
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
          ensureScenarioModelSelection()
        }
      }
      ensureScenarioModelSelection()
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

watch(() => props.scenario, () => {
  ensureScenarioModelSelection()
  statsData.value = null
  systemInfoData.value = null
  if (backendOnline.value) refreshStatus()
}, { immediate: true })

onMounted(() => {
  ensureScenarioModelSelection()
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
  gap: 24px;
  padding: 24px;
  border: 1px solid rgba(255, 184, 77, 0.28);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(13, 25, 41, 0.94) 0%, rgba(8, 16, 28, 0.94) 100%);
  box-shadow: 0 0 24px rgba(255, 184, 77, 0.14);
  backdrop-filter: blur(10px);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  border-bottom: 1px solid rgba(0, 242, 254, 0.15);
  padding-bottom: 16px;
}

.detection-card-title {
  margin: 0;
  color: #ffcf8b;
  font-size: 35px !important;
  font-weight: 800 !important;
  line-height: 1.2 !important;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  text-shadow: 0 0 10px rgba(255, 207, 139, 0.35) !important;
}

.detection-card-subtitle {
  margin: 8px 0 0 0;
  font-size: 28px !important;
  color: rgba(255, 255, 255, 0.82) !important;
  word-break: break-all !important;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

/* 垂直滚动容器 */
.scroll-container {
  display: flex;
  flex-direction: column;
  gap: 26px;
  overflow-y: auto;
  flex: 1;
  padding-right: 6px;
}

/* 自定义滚动条 */
.scroll-container::-webkit-scrollbar {
  width: 6px;
}
.scroll-container::-webkit-scrollbar-thumb {
  background: rgba(255, 184, 77, 0.25);
  border-radius: 3px;
}

/* 各板块通用样式 */
.card-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 24px;
  border-bottom: 1px dashed rgba(255, 184, 77, 0.16);
}
.card-section:last-child {
  border-bottom: none;
}

.section-title-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bracket {
  color: #00f2fe;
  font-weight: bold;
  font-size: 32px;
  text-shadow: 0 0 8px rgba(0, 242, 254, 0.5);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.section-subtitle-text {
  margin: 0;
  color: #00f2fe;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 1px;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

/* 1. 模型配置样式 (特大号字体) */
.model-config-section {
  gap: 24px;
}

.model-config-section .bracket {
  font-size: 44px;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.6);
}

.model-config-section .section-subtitle-text {
  font-size: 44px;
  text-shadow: 0 0 12px rgba(0, 242, 254, 0.5);
}

.model-select-group {
  background: rgba(0, 0, 0, 0.3);
  padding: 22px;
  border-left: 6px solid #ffb84d;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.control-label-text {
  font-size: 36px;
  color: rgba(255, 255, 255, 0.95);
  font-weight: 700;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.cyber-select-compact {
  width: 100%;
  background: rgba(10, 19, 35, 0.92);
  border: 2px solid #ffb84d;
  color: #ffb84d;
  padding: 16px 20px;
  font-size: 36px;
  font-weight: bold;
  cursor: pointer;
  outline: none;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  box-shadow: 0 0 12px rgba(255, 184, 77, 0.2);
}
.cyber-select-compact option {
  background: #0d1929;
  color: #ffb84d;
}

.tag-row {
  display: flex;
}
.tag-compact {
  font-size: 28px;
  padding: 6px 16px;
  background: #ffb84d;
  color: #000;
  font-weight: 800;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  border-radius: 4px;
}

.control-slider-group {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.slider-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 36px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.95);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.slider-val-text {
  font-weight: 800;
  color: #ffb84d;
  font-size: 42px;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  text-shadow: 0 0 8px rgba(255, 184, 77, 0.35);
}

.cyber-range-compact {
  -webkit-appearance: none;
  width: 100%;
  height: 16px;
  background: rgba(0, 242, 254, 0.2);
  border-radius: 8px;
  outline: none;
}
.cyber-range-compact::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 36px;
  height: 36px;
  background: #00f2fe;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 14px #00f2fe;
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
  min-height: 96px;
  padding: 12px 8px;
  border-radius: 8px;
  border: 1px solid rgba(255, 184, 77, 0.22);
  background: rgba(255, 184, 77, 0.08);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.performance-item.wide {
  grid-column: 1 / -1;
}

.perf-label {
  font-size: 22px;
  letter-spacing: -0.3px;
  color: rgba(255, 255, 255, 0.88);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  white-space: nowrap;
  overflow: visible;
}

.performance-item strong {
  color: #fff3bf;
  font-size: 36px;
  line-height: 1.25;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  font-weight: 700;
}

.performance-item small {
  color: #ffcf8b;
  font-size: 36px;
  line-height: 1;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.metric-placeholder {
  padding: 18px;
  border-radius: 8px;
  border: 1px dashed rgba(0, 242, 254, 0.3);
  color: rgba(255, 255, 255, 0.65);
  background: rgba(0, 242, 254, 0.05);
  font-size: 22px;
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
  padding: 14px 0;
  border-bottom: 1px solid rgba(0, 242, 254, 0.1);
  gap: 12px;
}
.telemetry-row:last-child {
  border-bottom: none;
}

.telemetry-col-label {
  font-size: 24px;
  color: rgba(255, 255, 255, 0.85);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  white-space: nowrap;
  flex-shrink: 0;
}

.telemetry-col-val {
  font-size: 28px;
  color: #fff;
  font-weight: bold;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  text-align: right;
  white-space: nowrap;
}

.telemetry-col-val.gpu-val {
  font-size: 20px !important;
}

.text-cyan-glow {
  color: #00f2fe !important;
  text-shadow: 0 0 8px rgba(0, 242, 254, 0.45);
}

.text-amber-glow {
  color: #ffb84d !important;
  text-shadow: 0 0 8px rgba(255, 184, 77, 0.45);
}

/* 4. 检测数据统计样式 */
.mini-metrics-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.metric-block {
  background: rgba(10, 19, 35, 0.65);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  min-height: 84px;
  padding: 8px 4px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.metric-block.highlight-block {
  border: 2px solid rgba(0, 242, 254, 0.55);
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.18), rgba(10, 19, 35, 0.9));
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.25);
}

.metric-val {
  font-size: 32px;
  font-weight: 800;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  line-height: 1;
  display: flex;
  align-items: baseline;
  justify-content: center;
}

.highlight-block .metric-val {
  font-size: 32px;
}

.metric-val.normal-val {
  color: #e2f8ff;
  text-shadow: none;
}

.metric-val .unit {
  font-size: 20px;
  margin-left: 2px;
  font-weight: 600;
  color: #00f2fe;
}

.metric-lbl {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.82);
  white-space: nowrap;
  letter-spacing: -0.3px;
  font-weight: 700;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.metric-lbl.highlight-lbl {
  color: #00f2fe;
  font-size: 16px;
  font-weight: 700;
}

/* 圆环饼图样式 */
.chart-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 14px;
}

.chart-title-label {
  font-size: 28px;
  color: #ffb84d;
  font-weight: bold;
  margin-bottom: 6px;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.doughnut-chart {
  width: 195px;
  height: 195px;
  border-radius: 50%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 18px auto;
  box-shadow: 0 0 16px rgba(0,0,0,0.5);
  transition: background 0.3s ease;
}

.doughnut-hole {
  width: 130px;
  height: 130px;
  border-radius: 50%;
  background: #0b1524;
  display: flex;
  align-items: center;
  justify-content: center;
}

.total-text {
  font-size: 28px;
  color: #ffcf8b;
  font-weight: bold;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.legends-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(0, 0, 0, 0.35);
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid rgba(0, 242, 254, 0.18);
}

.legend-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.08);
}
.legend-item:last-child {
  border-bottom: none;
}

.legend-name {
  color: rgba(255, 255, 255, 0.92);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: -0.2px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.legend-val {
  color: #00f2fe;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  font-weight: bold;
  font-size: 22px;
  white-space: nowrap;
  flex-shrink: 0;
  text-shadow: 0 0 6px rgba(0, 242, 254, 0.4);
}

/* 模型使用列表 */
.model-usage-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.model-usage-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.usage-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 24px;
}

.usage-name {
  color: rgba(255, 255, 255, 0.9);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  font-weight: 700;
  font-size: 24px;
}

.usage-val {
  color: #ffb84d;
  font-weight: bold;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
  font-size: 26px;
}

.usage-track {
  height: 12px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  overflow: hidden;
}

.usage-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(0, 242, 254, 0.4), #00f2fe);
  border-radius: 6px;
  transition: width 0.5s ease;
  min-width: 8px;
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
  font-size: 14.5px;
  color: #ffb4b4;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 4px 20px;
  border-radius: 999px;
  font-size: 24px;
  font-weight: 700;
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
