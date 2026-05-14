<template>
  <div class="layout">
    <aside class="sidebar">
      <h2>协同响应指挥面板</h2>

      <div class="menu">
        <button class="menu-btn blue" @click="showHome">系统首页</button>
        <button class="menu-btn blue" @click="showStreamlitView">协同调度平台</button>
        <button class="menu-btn cyan" @click="show2DView">二维动态推演</button>
        <button class="menu-btn purple" @click="show3DView">三维态势地图</button>
        <button class="menu-btn green" @click="openEvaluationPanel">协同策略评估</button>
      </div>

      <div class="status-box">
        <div class="status-row">
          <span>当前视图</span>
          <strong>{{ viewLabel }}</strong>
        </div>
        <div class="status-row">
          <span>指挥后端</span>
          <strong :class="commandCenterStatusClass">{{ commandCenterStatusText }}</strong>
        </div>
        <div class="status-row">
          <span>协同调度</span>
          <strong :class="streamlitStatusClass">{{ streamlitStatusText }}</strong>
        </div>
      </div>
    </aside>

    <main class="content">
      <section v-if="currentView === 'home'" class="panel">
        <div class="card">
          <h3>协同响应子系统接入面板</h3>
          <p>
            当前子系统已接入协同调度平台、二维动态推演、三维态势地图和策略评估。
            所有服务由指挥后端统一管理，支持一键启停和远程接入地址管理。
          </p>

          <div class="config-list">
            <label class="field">
              <span>协同调度平台地址</span>
              <div class="field-row">
                <input v-model.trim="streamlitDraft" type="text" placeholder="http://127.0.0.1:8501/?embed=true" />
                <button class="ghost-btn" @click="saveStreamlitUrl">保存</button>
              </div>
            </label>

            <label class="field">
              <span>指挥后端地址</span>
              <div class="field-row">
                <input v-model.trim="commandCenterDraft" type="text" placeholder="http://127.0.0.1:5001" />
                <button class="ghost-btn" @click="saveCommandCenterBaseUrl">保存</button>
              </div>
            </label>
          </div>

          <div class="service-grid">
            <article class="service-card">
              <div class="service-top">
                <div>
                  <strong>协同响应指挥后端</strong>
                  <p>{{ resolvedCommandCenterBaseUrl }}</p>
                </div>
                <span class="chip" :class="statusChipClass(services.commandCenter)">
                  {{ commandCenterStatusText }}
                </span>
              </div>
              <div class="action-row">
                <button
                  class="dark-btn"
                  :disabled="businessActionPending || !services.commandCenter.online"
                  @click="generateStrategy"
                >
                  生成二维推演
                </button>
                <button
                  class="dark-btn"
                  :disabled="businessActionPending || !services.commandCenter.online"
                  @click="generateCesium"
                >
                  生成三维态势
                </button>
              </div>
            </article>

            <article class="service-card">
              <div class="service-top">
                <div>
                  <strong>协同调度平台</strong>
                  <p>{{ resolvedStreamlitUrl }}</p>
                </div>
                <span class="chip" :class="statusChipClass(services.streamlit)">
                  {{ streamlitStatusText }}
                </span>
              </div>
              <div class="action-row">
                <button
                  class="purple-btn"
                  :disabled="services.streamlit.pending || !services.commandCenter.online"
                  @click="toggleManagedService('streamlit', !services.streamlit.running)"
                >
                  {{ services.streamlit.running ? '停止服务' : '启动服务' }}
                </button>
                <button class="blue-btn" @click="showStreamlitView">进入协同调度</button>
                <button class="dark-btn" @click="openEvaluationPanel">查看策略评估</button>
              </div>
            </article>
          </div>

          <p v-if="lastError" class="error-text">最近错误：{{ lastError }}</p>
        </div>
      </section>

      <section v-else class="frame-shell">
        <div v-if="!frameServiceReady" class="frame-state">
          <h3>{{ frameHintTitle }}</h3>
          <p>{{ frameHintDescription }}</p>
          <p v-if="activeViewService?.healthDetail" class="frame-state__meta">
            最近检测：{{ activeViewService.healthDetail }}
          </p>
          <p v-if="lastError" class="frame-state__meta is-error">
            最近错误：{{ lastError }}
          </p>
          <div class="action-row">
            <button class="blue-btn" :disabled="Boolean(viewLaunchPending)" @click="retryCurrentView">
              {{ viewLaunchPending ? '启动中...' : '重试进入' }}
            </button>
            <button class="ghost-btn" @click="refreshStatus">刷新状态</button>
            <button class="dark-btn" @click="showHome">返回首页</button>
          </div>
        </div>

        <iframe
          v-else-if="currentView === 'streamlit'"
          :key="streamlitFrameKey"
          :src="streamlitFrameSrc"
          class="frame"
        ></iframe>
        <iframe
          v-else-if="currentView === '2d'"
          :key="strategyFrameKey"
          :src="strategyFrameSrc"
          class="frame"
        ></iframe>
        <iframe
          v-else-if="currentView === '3d'"
          :key="cesiumFrameKey"
          :src="cesiumFrameSrc"
          class="frame"
        ></iframe>
      </section>

      <div v-if="showEvaluationPanel" class="overlay">
        <div class="overlay-card">
          <button class="close-btn" @click="showEvaluationPanel = false">关闭</button>
          <h3>协同策略评估</h3>
          <div class="metrics">
            <div class="metric">
              <span>车辆到场时间</span>
              <strong>{{ metricsDisplay.carTime }}</strong>
            </div>
            <div class="metric">
              <span>无人机到场时间</span>
              <strong>{{ metricsDisplay.uavTime }}</strong>
            </div>
            <div class="metric">
              <span>无人机能耗</span>
              <strong>{{ metricsDisplay.uavEnergy }}</strong>
            </div>
            <div class="metric">
              <span>协同等待时延</span>
              <strong>{{ metricsDisplay.delay }}</strong>
            </div>
          </div>
          <p class="overlay-meta">结果状态：{{ evaluation.message || '暂无结果' }}</p>
          <p class="overlay-meta">最近更新：{{ formatDateTime(evaluation.updatedAt) }}</p>
          <div class="action-row">
            <button
              class="cyan-btn"
              :disabled="businessActionPending || !services.commandCenter.online"
              @click="generateStrategy"
            >
              重新生成评估
            </button>
            <button class="dark-btn" @click="show2DView">查看二维结果</button>
            <button class="purple-btn" @click="show3DView">查看三维结果</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import {
  appendUrlParams,
  buildCommandCenterUrl,
  getCollaborativeCommandCenterBaseUrl,
  getCollaborativeStreamlitUrl,
  persistCollaborativeCommandCenterBaseUrl,
  persistCollaborativeStreamlitUrl,
} from './service-config'

const currentView = ref('home')
const showEvaluationPanel = ref(false)
const streamlitUrl = ref(getCollaborativeStreamlitUrl())
const commandCenterBaseUrl = ref(getCollaborativeCommandCenterBaseUrl())
const streamlitDraft = ref(streamlitUrl.value)
const commandCenterDraft = ref(commandCenterBaseUrl.value)
const lastError = ref('')
const businessActionPending = ref('')
const viewLaunchPending = ref('')
const streamlitFrameSrc = ref('')
const strategyFrameSrc = ref('')
const cesiumFrameSrc = ref('')
const streamlitFrameKey = ref(0)
const strategyFrameKey = ref(0)
const cesiumFrameKey = ref(0)

const services = reactive({
  commandCenter: createServiceState(),
  streamlit: createServiceState(),
})

const evaluation = reactive({
  message: '尚未读取策略评估结果',
  metrics: {},
  updatedAt: '',
})

let pollingTimer = null

function createServiceState() {
  return {
    checked: false,
    online: false,
    running: false,
    managed: false,
    pending: false,
    publicUrl: '',
    healthDetail: '',
    startConfigured: false,
  }
}

const viewLabel = computed(() => {
  const labels = {
    home: '系统首页',
    streamlit: '协同调度平台',
    '2d': '二维动态推演',
    '3d': '三维态势地图',
  }
  return labels[currentView.value] || '未知'
})

const commandCenterStatusText = computed(() => {
  if (!services.commandCenter.checked) return '检测中'
  return services.commandCenter.online ? '在线' : '离线'
})

const commandCenterStatusClass = computed(() => {
  if (!services.commandCenter.checked) return 'pending'
  return services.commandCenter.online ? 'ok' : 'warn'
})

const streamlitStatusText = computed(() => {
  if (!services.streamlit.checked) return '检测中'
  return services.streamlit.online ? '在线' : '离线'
})

const streamlitStatusClass = computed(() => {
  if (!services.streamlit.checked) return 'pending'
  return services.streamlit.online ? 'ok' : 'warn'
})

const resolvedStreamlitUrl = computed(() => services.streamlit.publicUrl || streamlitUrl.value)
const resolvedCommandCenterBaseUrl = computed(() => services.commandCenter.publicUrl || commandCenterBaseUrl.value)

const activeViewService = computed(() => {
  if (currentView.value === 'streamlit') return services.streamlit
  if (currentView.value === '2d' || currentView.value === '3d') return services.commandCenter
  return null
})

const activeViewServiceLabel = computed(() => {
  if (currentView.value === 'streamlit') return '协同调度平台'
  if (currentView.value === '2d' || currentView.value === '3d') return '协同响应指挥后端'
  return ''
})

const frameServiceReady = computed(() => {
  if (currentView.value === 'home') return true
  return Boolean(activeViewService.value?.online)
})

const frameHintTitle = computed(() => {
  if (viewLaunchPending.value) return '正在拉起远程服务'
  if (currentView.value === 'streamlit') return '协同调度平台暂未就绪'
  if (currentView.value === '2d') return '二维动态推演暂未就绪'
  if (currentView.value === '3d') return '三维态势地图暂未就绪'
  return '服务暂未就绪'
})

const frameHintDescription = computed(() => {
  if (viewLaunchPending.value) {
    return '正在尝试启动 ' + activeViewServiceLabel.value + '，请稍候刷新状态。'
  }
  if (!services.commandCenter.online) {
    return '指挥后端离线，无法启动任何服务。请先运行 start_Collaborative_Response.bat 启动指挥后端。'
  }
  if (!activeViewService.value?.startConfigured) {
    return activeViewServiceLabel.value + ' 由指挥后端统一管理，当前不可用。'
  }
  return '当前未检测到 ' + activeViewServiceLabel.value + ' 在线，可尝试自动启动后再进入该界面。'
})

const metricsDisplay = computed(() => ({
  carTime: evaluation.metrics.carTime ? evaluation.metrics.carTime + ' s' : '--',
  uavTime: evaluation.metrics.uavTime ? evaluation.metrics.uavTime + ' s' : '--',
  uavEnergy: evaluation.metrics.uavEnergy ? evaluation.metrics.uavEnergy + ' Wh' : '--',
  delay: evaluation.metrics.delay ? evaluation.metrics.delay + ' s' : '--',
}))

function statusChipClass(service) {
  if (!service.checked) return 'pending'
  return service.online ? 'ok' : 'warn'
}

function formatDateTime(value) {
  if (!value) return '--'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function updateService(serviceId, payload = {}, fallbackUrl = '') {
  services[serviceId].checked = true
  services[serviceId].online = Boolean(payload.reachable ?? payload.running)
  services[serviceId].running = Boolean(payload.running ?? payload.reachable)
  services[serviceId].managed = Boolean(payload.managed)
  services[serviceId].publicUrl = payload.public_url || fallbackUrl
  services[serviceId].healthDetail = payload.health_detail || ''
  services[serviceId].startConfigured = Boolean(payload.start_configured)
}

async function probeDirect(url) {
  try {
    const response = await fetch(url, { cache: 'no-store' })
    return response.ok
  } catch {
    return false
  }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.error || payload.message || 'HTTP ' + response.status)
  }
  return payload
}

async function refreshEvaluation() {
  try {
    const payload = await requestJson(
      buildCommandCenterUrl('api/strategy_metrics', commandCenterBaseUrl.value),
      { cache: 'no-store' }
    )
    evaluation.message = payload.message || '已读取策略评估结果'
    evaluation.metrics = payload.metrics || {}
    evaluation.updatedAt = payload.updated_at || ''
  } catch {
    evaluation.message = '暂未获取到策略评估结果'
    evaluation.metrics = {}
    evaluation.updatedAt = ''
  }
}

async function refreshStatus() {
  try {
    const payload = await requestJson(
      buildCommandCenterUrl('api/health', commandCenterBaseUrl.value),
      { cache: 'no-store' }
    )
    updateService('commandCenter', payload.services?.commandCenter, commandCenterBaseUrl.value)
    updateService('streamlit', payload.services?.streamlit, streamlitUrl.value)
    lastError.value = ''
  } catch (error) {
    updateService('commandCenter', {}, commandCenterBaseUrl.value)
    lastError.value = error instanceof Error ? error.message : '无法连接指挥后端'

    const streamlitOnline = await probeDirect(streamlitUrl.value)
    updateService(
      'streamlit',
      { reachable: streamlitOnline, running: streamlitOnline, public_url: streamlitUrl.value },
      streamlitUrl.value
    )
  }

  await refreshEvaluation()
}

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

async function toggleManagedService(serviceId, nextRunning) {
  services[serviceId].pending = true
  try {
    const action = nextRunning ? 'start' : 'stop'
    await requestJson(
      buildCommandCenterUrl('api/services/' + serviceId + '/' + action, commandCenterBaseUrl.value),
      { method: 'POST' }
    )
    await refreshStatus()
    return true
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : '服务控制失败'
    return false
  } finally {
    services[serviceId].pending = false
  }
}

async function ensureServiceReady(serviceId, timeoutMs = 15000) {
  await refreshStatus()
  if (services[serviceId].online) return true

  if (serviceId === 'commandCenter') {
    lastError.value = '指挥后端离线，无法远程启动。请先运行 start_Collaborative_Response.bat。'
    return false
  }

  if (!services.commandCenter.online) {
    lastError.value = '指挥后端离线，无法远程启动' + (serviceId === 'streamlit' ? '协同调度平台' : serviceId)
    return false
  }

  if (!services[serviceId].startConfigured) {
    lastError.value = serviceId + ' 未配置启动命令'
    return false
  }

  const started = await toggleManagedService(serviceId, true)
  if (!started) return false

  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    await sleep(1000)
    await refreshStatus()
    if (services[serviceId].online) return true
  }

  const serviceLabel = serviceId === 'streamlit' ? '协同调度平台' : serviceId
  if (services[serviceId].healthDetail) {
    lastError.value = serviceLabel + ' 启动超时：' + services[serviceId].healthDetail
  } else {
    lastError.value = serviceLabel + ' 启动超时，请检查后端日志'
  }
  return false
}

async function runCommandCenterAction(path, nextView) {
  if (!services.commandCenter.online) {
    const ready = await ensureServiceReady('commandCenter')
    if (!ready) return
  }

  businessActionPending.value = path
  try {
    const payload = await requestJson(buildCommandCenterUrl(path, commandCenterBaseUrl.value), {
      cache: 'no-store',
    })
    if (payload.ok === false) {
      throw new Error(payload.message || '业务执行失败')
    }

    await refreshEvaluation()
    if (nextView === '2d') await show2DView()
    if (nextView === '3d') await show3DView()
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : '业务计算失败'
  } finally {
    businessActionPending.value = ''
  }
}

function refreshFrames() {
  streamlitFrameSrc.value = appendUrlParams(resolvedStreamlitUrl.value, { embed: 'true', t: Date.now() })
  strategyFrameSrc.value = appendUrlParams(
    buildCommandCenterUrl('wuhan_rescue_optimized.html', resolvedCommandCenterBaseUrl.value),
    { t: Date.now() }
  )
  cesiumFrameSrc.value = appendUrlParams(
    buildCommandCenterUrl('cesium_viewer', resolvedCommandCenterBaseUrl.value),
    { t: Date.now() }
  )
  streamlitFrameKey.value += 1
  strategyFrameKey.value += 1
  cesiumFrameKey.value += 1
}

function showHome() {
  currentView.value = 'home'
}

async function openManagedView(viewId, serviceId, frameBuilder) {
  currentView.value = viewId
  lastError.value = ''

  if (!services[serviceId].online) {
    viewLaunchPending.value = serviceId
    const ready = await ensureServiceReady(serviceId)
    viewLaunchPending.value = ''
    if (!ready) return
  }

  frameBuilder()
}

async function showStreamlitView() {
  await openManagedView('streamlit', 'streamlit', () => {
    streamlitFrameSrc.value = appendUrlParams(resolvedStreamlitUrl.value, { embed: 'true', t: Date.now() })
    streamlitFrameKey.value += 1
  })
}

async function show2DView() {
  await openManagedView('2d', 'commandCenter', () => {
    strategyFrameSrc.value = appendUrlParams(
      buildCommandCenterUrl('wuhan_rescue_optimized.html', resolvedCommandCenterBaseUrl.value),
      { t: Date.now() }
    )
    strategyFrameKey.value += 1
  })
}

async function show3DView() {
  await openManagedView('3d', 'commandCenter', () => {
    cesiumFrameSrc.value = appendUrlParams(
      buildCommandCenterUrl('cesium_viewer', resolvedCommandCenterBaseUrl.value),
      { t: Date.now() }
    )
    cesiumFrameKey.value += 1
  })
}

function retryCurrentView() {
  if (currentView.value === 'streamlit') {
    showStreamlitView()
    return
  }
  if (currentView.value === '2d') {
    show2DView()
    return
  }
  if (currentView.value === '3d') {
    show3DView()
  }
}

function openEvaluationPanel() {
  refreshEvaluation()
  showEvaluationPanel.value = true
}

function generateStrategy() {
  runCommandCenterAction('api/run_3d_strategy', '2d')
}

function generateCesium() {
  runCommandCenterAction('api/run_3d_cesium', '3d')
}

function saveStreamlitUrl() {
  streamlitUrl.value = persistCollaborativeStreamlitUrl(streamlitDraft.value)
  streamlitDraft.value = streamlitUrl.value
  refreshStatus()
  refreshFrames()
}

function saveCommandCenterBaseUrl() {
  commandCenterBaseUrl.value = persistCollaborativeCommandCenterBaseUrl(commandCenterDraft.value)
  commandCenterDraft.value = commandCenterBaseUrl.value
  refreshStatus()
  refreshFrames()
}

onMounted(async () => {
  await refreshStatus()
  refreshFrames()
  pollingTimer = window.setInterval(refreshStatus, 5000)
})

onUnmounted(() => {
  if (pollingTimer) window.clearInterval(pollingTimer)
})
</script>

<style scoped>
/* ============================================
   Blue-dark broadcast / CCTV command style
   ============================================ */
.layout {
  --blue-deep: #0a0f23;
  --blue-panel: #0f1a33;
  --blue-accent: #4a9eff;
  --gold: #c9a84c;
  --text-primary: #e8edf5;
  --text-secondary: rgba(200, 210, 225, 0.62);
  --border: rgba(74, 158, 255, 0.16);

  display: flex;
  height: 100vh;
  background:
    radial-gradient(ellipse at 40% 25%, rgba(30, 60, 120, 0.12) 0%, transparent 55%),
    radial-gradient(ellipse at 70% 70%, rgba(15, 35, 70, 0.08) 0%, transparent 50%),
    var(--blue-deep);
  color: #ffffff;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}

/* ---- sidebar ---- */
.sidebar {
  position: relative;
  width: 312px;
  padding: 30px 20px 24px;
  background: linear-gradient(180deg, #111d3a 0%, #0d1630 40%, #0a1025 100%);
  border-right: 1px solid rgba(74, 158, 255, 0.15);
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
}

.sidebar::after {
  content: '';
  position: absolute;
  right: -1px; top: 0; bottom: 0;
  width: 1px;
  background: linear-gradient(180deg,
    transparent 0%,
    rgba(74,158,255,0.3) 20%,
    rgba(74,158,255,0.3) 80%,
    transparent 100%);
  pointer-events: none;
}

.sidebar h2 {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.06em;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(74,158,255,0.16);
  position: relative;
}

.sidebar h2::after {
  content: '';
  position: absolute;
  bottom: -1px; left: 0;
  width: 40px;
  height: 2px;
  background: var(--blue-accent);
  border-radius: 1px;
}

/* ---- menu ---- */
.menu {
  display: grid;
  gap: 8px;
  margin-top: 18px;
}

.menu-btn {
  min-height: 42px;
  padding: 0 14px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-primary);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.03em;
}

.menu-btn::before {
  content: '';
  width: 4px; height: 4px;
  border-radius: 50%;
  background: rgba(255,255,255,0.25);
  flex-shrink: 0;
  transition: background 0.2s;
}

.menu-btn:hover {
  background: rgba(74,158,255,0.1);
  border-color: rgba(74,158,255,0.3);
  color: #ffffff;
}
.menu-btn:hover::before { background: var(--blue-accent); }

/* ---- shared button resets ---- */
.blue-btn,
.cyan-btn,
.purple-btn,
.dark-btn,
.ghost-btn {
  border: none;
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  transition: all 0.2s ease;
  letter-spacing: 0.03em;
}

.blue-btn,
.cyan-btn,
.purple-btn {
  min-height: 40px;
  padding: 0 18px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: #fff;
  box-shadow: 0 2px 12px rgba(37,99,235,0.3);
}

.blue-btn:hover,
.cyan-btn:hover,
.purple-btn:hover {
  background: linear-gradient(135deg, #1d4ed8, #2563eb);
  box-shadow: 0 4px 18px rgba(37,99,235,0.45);
  transform: translateY(-1px);
}

.dark-btn {
  min-height: 40px;
  padding: 0 18px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(74,158,255,0.14);
  color: var(--text-primary);
}

.dark-btn:hover {
  border-color: rgba(74,158,255,0.32);
  background: rgba(74,158,255,0.08);
  color: #fff;
}

.ghost-btn {
  min-height: 40px;
  padding: 0 18px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.ghost-btn:hover {
  border-color: rgba(74,158,255,0.28);
  color: var(--blue-accent);
}

/* ---- status box ---- */
.status-box {
  margin-top: 22px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(12, 22, 45, 0.6);
  border: 1px solid rgba(74, 158, 255, 0.14);
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 0;
  border-bottom: 1px solid rgba(74,158,255,0.08);
  font-size: 13px;
}

.status-row:last-child { border-bottom: none; }

.status-row span { color: var(--text-secondary); }

.ok { color: #5ec76e; }
.warn { color: #e8915c; }
.pending { color: var(--text-secondary); }

/* ---- content area ---- */
.content {
  flex: 1;
  position: relative;
  background:
    radial-gradient(ellipse at 40% 30%, rgba(30,60,120,0.1) 0%, transparent 55%),
    radial-gradient(ellipse at 65% 65%, rgba(15,35,70,0.06) 0%, transparent 50%),
    var(--blue-deep);
}

.panel,
.frame-shell {
  width: 100%;
  height: 100%;
}

.panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  box-sizing: border-box;
}

/* ---- home card ---- */
.card {
  width: min(1080px, 100%);
  padding: 32px;
  border-radius: 10px;
  background: var(--blue-card);
  border: 1px solid rgba(74,158,255,0.16);
  box-shadow: 0 16px 40px rgba(0,0,0,0.25);
}

.card h3 {
  margin: 0 0 12px;
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.04em;
}

.card p {
  line-height: 1.8;
  color: var(--text-secondary);
}

/* ---- config fields ---- */
.config-list {
  display: grid;
  gap: 14px;
  margin-top: 22px;
}

.field span {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--text-primary);
  font-size: 13px;
}

.field-row,
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.field input {
  flex: 1 1 320px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 6px;
  border: 1px solid rgba(74,158,255,0.16);
  background: rgba(8,16,34,0.8);
  color: #fff;
  font-size: 13px;
  transition: 0.2s ease;
}

.field input:focus {
  outline: none;
  border-color: rgba(74,158,255,0.45);
  box-shadow: 0 0 0 3px rgba(74,158,255,0.08);
}

/* ---- service cards ---- */
.service-grid {
  display: grid;
  gap: 14px;
  margin-top: 24px;
}

.service-card {
  padding: 18px;
  border-radius: 8px;
  background: rgba(16, 28, 55, 0.7);
  border: 1px solid rgba(74,158,255,0.12);
  transition: 0.2s ease;
}

.service-card:hover {
  border-color: rgba(74,158,255,0.3);
}

.service-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.service-top strong { color: #ffffff; }

.service-top p {
  margin: 8px 0 0;
  font-size: 12.5px;
  color: var(--blue-accent-dim, rgba(74,158,255,0.65));
  word-break: break-all;
}

/* ---- chip ---- */
.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.chip.ok { background: rgba(94,199,110,0.15); color: #5ec76e; }
.chip.warn { background: rgba(232,145,92,0.14); color: #e8915c; }
.chip.pending { background: rgba(255,255,255,0.06); color: var(--text-secondary); }

/* ---- error ---- */
.error-text {
  margin-top: 16px;
  color: #e8915c;
  font-size: 13px;
}

/* ---- iframe area ---- */
.frame-shell { position: relative; }

.frame-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 14px;
  padding: 32px;
  background: rgba(8,14,30,0.96);
}

.frame-state h3 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
}

.frame-state p {
  margin: 0;
  max-width: 720px;
  line-height: 1.8;
  color: var(--text-secondary);
}

.frame-state__meta { color: var(--blue-accent); font-size: 13px; }
.frame-state__meta.is-error { color: #e8915c; }

.frame {
  width: 100%;
  height: 100%;
  border: none;
  background: #060b1a;
}

/* ---- overlay ---- */
.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(6,11,26,0.88);
  backdrop-filter: blur(8px);
  z-index: 10;
}

.overlay-card {
  width: min(760px, calc(100% - 48px));
  padding: 32px;
  border-radius: 10px;
  background: var(--blue-card);
  border: 1px solid rgba(74,158,255,0.2);
  box-shadow: 0 20px 48px rgba(0,0,0,0.28);
  position: relative;
}

.overlay-card h3 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
}

.close-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  transition: 0.2s;
}

.close-btn:hover {
  border-color: rgba(74,158,255,0.3);
  color: var(--blue-accent);
}

/* ---- metrics ---- */
.metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.metric {
  padding: 18px;
  border-radius: 8px;
  background: rgba(20,35,65,0.5);
  border: 1px solid rgba(74,158,255,0.1);
}

.metric span {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric strong {
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
}

.overlay-meta {
  margin-top: 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

/* ---- scrollbar ---- */
.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-track { background: transparent; }
.sidebar::-webkit-scrollbar-thumb { background: rgba(74,158,255,0.15); border-radius: 4px; }

/* ---- responsive ---- */
@media (max-width: 1200px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; max-height: 300px; flex-shrink: 0; }
}

@media (max-width: 768px) {
  .metrics { grid-template-columns: 1fr; }
  .card { padding: 20px; }
  .overlay-card { padding: 20px; }
}
</style>
