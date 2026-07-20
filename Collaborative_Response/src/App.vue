<template>
  <div class="layout">
    <aside class="sidebar">
      <h2>协同响应指挥面板</h2>

      <div class="menu">
        <button :class="['menu-btn', { active: currentView === 'home' && !showEvaluationPanel }]" @click="showHome">系统首页</button>
        <button :class="['menu-btn', { active: currentView === 'streamlit' }]" @click="showStreamlitView">协同调度平台</button>
        <button :class="['menu-btn', { active: currentView === '2d' }]" @click="show2DView">二维动态推演</button>
        <button :class="['menu-btn', { active: currentView === '3d' }]" @click="show3DView">三维态势地图</button>
        <button :class="['menu-btn', { active: showEvaluationPanel }]" @click="openEvaluationPanel">协同策略评估</button>
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

      <!-- 协同调度控制面板 -->
      <div v-if="currentView === 'streamlit'" class="deduction-controls">
        <h4 class="ctrl-title">联合指挥应急控制台</h4>
        <label class="ctrl-field">
          <span>调度主体优先级类型</span>
          <select v-model="streamlitMode" class="ctrl-select">
            <option value="medical">人员伤亡（医疗急救）</option>
            <option value="fire">火灾事故（消防灭火）</option>
            <option value="police">现场封控（公安交警）</option>
            <option value="hazmat">危化品泄漏（防化部队）</option>
            <option value="road">道路清障（交通路政）</option>
          </select>
        </label>
        <label class="ctrl-field">
          <span>交通事故响应等级</span>
          <select v-model="streamlitSeverity" class="ctrl-select">
            <option value="轻微">轻微</option>
            <option value="中度">中度</option>
            <option value="危重">危重</option>
            <option value="一般">一般</option>
            <option value="较大">较大</option>
            <option value="特大">特大</option>
          </select>
        </label>
        <div class="ctrl-subtitle">环境参数</div>
        <div class="ctrl-row">
          <label class="ctrl-field" style="flex: 1;">
            <span>时间</span>
            <input type="time" v-model="streamlitTime" class="ctrl-select" />
          </label>
          <label class="ctrl-field" style="flex: 1;">
            <span>天气</span>
            <select v-model="streamlitWeather" class="ctrl-select">
              <option value="☀️ 晴朗">晴朗</option>
              <option value="🌧️ 小雨">小雨</option>
              <option value="⛈️ 暴雨">暴雨</option>
              <option value="🌫️ 大雾">大雾</option>
              <option value="❄️ 积雪">积雪</option>
            </select>
          </label>
        </div>
        <div class="ctrl-btns">
          <button class="ctrl-btn ghost" :disabled="streamlitPending" @click="applyStreamlitSettings">应用设置</button>
        </div>
        <p class="ctrl-hint">事故模拟交互和规划按钮在右侧地图中操作</p>
        <p v-if="streamlitStatus" class="ctrl-status">{{ streamlitStatus }}</p>
      </div>

      <!-- 二维推演控制面板 -->
      <div v-if="currentView === '2d'" class="deduction-controls">
        <h4 class="ctrl-title">推演控制</h4>
        <label class="ctrl-field">
          <span>事故场景</span>
          <select v-model="deductionScene" class="ctrl-select">
            <option value="leak">油罐车泄露现场</option>
            <option value="crash">货车追尾现场</option>
          </select>
        </label>
        <label class="ctrl-field">
          <span>障碍物设置</span>
          <select v-model="deductionObstacle" class="ctrl-select">
            <option value="1">开启（禁飞区/拥堵区）</option>
            <option value="0">关闭（直连路径）</option>
          </select>
        </label>
        <label class="ctrl-field">
          <span>协同策略</span>
          <select v-model="deductionStrategy" class="ctrl-select">
            <option value="rcd">逆向推演（RCD）</option>
            <option value="independent">极速独立（ISD）</option>
            <option value="wait">基地待命（CAS）</option>
          </select>
        </label>
        <div class="ctrl-btns">
          <button class="ctrl-btn blue" :disabled="deductionPending" @click="triggerReplan">无人装备出动</button>
          <button class="ctrl-btn green" :disabled="deductionPending" @click="triggerMultiAgent">救援装备出动</button>
        </div>
        <p v-if="deductionStatus" class="ctrl-status">{{ deductionStatus }}</p>
      </div>

      <!-- 三维态势控制面板 -->
      <div v-if="currentView === '3d'" class="deduction-controls">
        <h4 class="ctrl-title">三维态势控制</h4>
        <label class="ctrl-field">
          <span>事故场景</span>
          <select v-model="cesiumScene" class="ctrl-select">
            <option value="leak">油罐车泄露现场</option>
            <option value="crash">货车追尾现场</option>
          </select>
        </label>
        <div class="ctrl-btns">
          <button class="ctrl-btn blue" :disabled="cesiumPending" @click="triggerCesiumUGVUAV">无人装备出动</button>
        </div>
        <div class="ctrl-btns">
          <button class="ctrl-btn green" :disabled="cesiumPending" @click="triggerCesiumMultiAgent">救援装备出动</button>
        </div>
        <p v-if="cesiumStatus" class="ctrl-status">{{ cesiumStatus }}</p>
      </div>

      <!-- 多智能体决策分析面板 -->
      <AgentSelectionPanel
        v-if="(currentView === '2d' || currentView === '3d') && showMultiAgentPanel && multiAgentData"
        :multiAgentData="multiAgentData"
        :isComputing="deductionPending || cesiumPending"
      />
    </aside>

    <main class="content">
      <section v-if="currentView === 'home'" class="panel">
        <div class="card">
          <h3>协同响应子系统接入面板</h3>
          <p>
            当前子系统已接入协同调度平台、二维动态推演、三维态势地图和策略评估。
            现在的重点是统一状态检测、服务启停和远程接入地址管理。
          </p>

          <div class="config-list">
            <label class="field">
              <span>指挥后端地址</span>
              <div class="field-row">
                <input v-model.trim="commandCenterDraft" type="text" placeholder="http://127.0.0.1:5001" />
                <button class="ghost-btn" @click="saveCommandCenterBaseUrl">保存</button>
              </div>
            </label>

            <label class="field">
              <span>协同调度平台地址</span>
              <div class="field-row">
                <input v-model.trim="streamlitDraft" type="text" placeholder="http://127.0.0.1:8501/?embed=true" />
                <button class="ghost-btn" @click="saveStreamlitUrl">保存</button>
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
                <select
                  v-model="cesiumEndpoint"
                  class="scene-select">
                  <option value="crash">&#x1F692; 货车追尾现场</option>
                  <option value="leak">&#x1F6E2; 油罐车泄露现场</option>
                </select>
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
                  :disabled="services.streamlit.pending || !commandCenterOnline"
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
        <div class="overlay-card strategy-evaluation-modal">
          <button class="close-btn" @click="showEvaluationPanel = false">关闭</button>
          <h3 class="modal-title">🏆 协同策略综合评估报告</h3>
          
          <div class="evaluation-meta-grid">
            <div class="meta-item">
              <span class="label">当前起调站点：</span>
              <span class="val">{{ evaluation.metricsRaw?.start_point_name || '未获取' }}</span>
            </div>
            <div class="meta-item">
              <span class="label">联合集结终点：</span>
              <span class="val">{{ evaluation.metricsRaw?.end_point_name || '未获取' }}</span>
            </div>
          </div>

          <!-- 第一部分：核心协同指标 -->
          <h4 class="section-title">⏱️ 协同执行核心时效指标</h4>
          <div class="metrics-grid">
            <div class="metric-card">
              <span class="card-label">车辆集结时效</span>
              <strong class="card-val">{{ metricsDisplay.carTime }}</strong>
            </div>
            <div class="metric-card">
              <span class="card-label">无人机集结时效</span>
              <strong class="card-val">{{ metricsDisplay.uavTime }}</strong>
            </div>
            <div class="metric-card">
              <span class="card-label">协同集结时延</span>
              <strong class="card-val">{{ metricsDisplay.delay }}</strong>
            </div>
            <div class="metric-card">
              <span class="card-label">无人机动力能耗</span>
              <strong class="card-val">{{ metricsDisplay.uavEnergy }}</strong>
            </div>
          </div>

          <!-- 第二部分：常规模式 vs 协同优化比对 -->
          <div v-if="evaluation.metricsRaw?.comparison" class="comparison-section">
            <h4 class="section-title">📊 协同优化效能比对</h4>
            <div class="comparison-grid">
              <div class="comparison-card">
                <h5>🚗 车辆行驶路径节省</h5>
                <div class="comp-details">
                  <span>独立基线: {{ evaluation.metricsRaw.comparison.baselineCarDistKm }} km</span>
                  <span class="arrow">➡️</span>
                  <span class="opt">协同优化: {{ evaluation.metricsRaw.comparison.carDistKm }} km</span>
                </div>
                <div class="saving-badge text-cyan">
                  已节省 {{ evaluation.metricsRaw.comparison.carSavingKm }} km (缩减 {{ evaluation.metricsRaw.comparison.carSavingPct }}%)
                </div>
              </div>
              
              <div class="comparison-card">
                <h5>🛸 无人机航线路径节省</h5>
                <div class="comp-details">
                  <span>独立基线: {{ evaluation.metricsRaw.comparison.baselineUavDistKm }} km</span>
                  <span class="arrow">➡️</span>
                  <span class="opt">协同优化: {{ evaluation.metricsRaw.comparison.uavDistKm }} km</span>
                </div>
                <div class="saving-badge text-cyan">
                  已节省 {{ evaluation.metricsRaw.comparison.uavSavingKm }} km (缩减 {{ evaluation.metricsRaw.comparison.uavSavingPct }}%)
                </div>
              </div>
            </div>
            <div class="total-opt-bar">
              <span>系统路径寻优综合效率提升：</span>
              <strong class="text-cyan">{{ evaluation.metricsRaw.comparison.avgOptimizationPct }}%</strong>
            </div>
          </div>

          <!-- 第三部分：路网灾害感知情况 -->
          <div v-if="evaluation.metricsRaw?.scenario" class="scenario-section">
            <h4 class="section-title">🚧 路网实时障碍与态势感知</h4>
            <div class="scenario-badges">
              <span class="badge" :class="evaluation.metricsRaw.scenario.ugv_blocked ? 'danger' : 'success'">
                地面路网受阻: {{ evaluation.metricsRaw.scenario.ugv_blocked ? '是 (已避绕)' : '否' }}
              </span>
              <span class="badge" :class="evaluation.metricsRaw.scenario.uav_smoke ? 'warning' : 'success'">
                空域气流/浓雾影响: {{ evaluation.metricsRaw.scenario.uav_smoke ? '是 (已校准速度)' : '否' }}
              </span>
              <span class="badge info">
                监测到禁飞区: {{ evaluation.metricsRaw.scenario.nfz_count }} 处
              </span>
            </div>
            <div v-if="evaluation.metricsRaw.scenario.congestion_name" class="congestion-info-box">
              🚨 <strong>{{ evaluation.metricsRaw.scenario.congestion_name }}</strong>: 
              {{ evaluation.metricsRaw.scenario.congestion_info }}
            </div>
          </div>

          <!-- 第四部分：备选力量综合评级与优选比对 -->
          <div v-if="evaluation.metricsRaw?.candidate_points?.length" class="candidates-section">
            <h4 class="section-title">📋 候选协同力量响应比对</h4>
            <div class="candidate-list">
              <div 
                v-for="pt in evaluation.metricsRaw.candidate_points" 
                :key="pt.name" 
                class="candidate-row"
                :class="{ 'is-selected': pt.selected }"
              >
                <span class="name">
                  {{ pt.name }}
                  <span v-if="pt.selected" class="selected-tag">最佳起调点</span>
                </span>
                <span class="dist">距集结地：{{ pt.dist_km.toFixed(2) }} km</span>
              </div>
            </div>
          </div>

          <p class="overlay-meta">状态：{{ evaluation.message || '已载入最新策略数据' }} | 更新于：{{ formatDateTime(evaluation.updatedAt) }}</p>
          <div class="action-row modal-footer">
            <button
              class="cyan-btn"
              :disabled="businessActionPending || !services.commandCenter.online"
              @click="generateStrategy"
            >
              重新寻优解算
            </button>
            <button class="dark-btn" @click="show2DView">二维动态推演</button>
            <button class="purple-btn" @click="show3DView">三维数字地球</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import AgentSelectionPanel from './components/AgentSelectionPanel.vue'
import {
  appendUrlParams,
  buildCollaborativeApiUrl,
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
const commandCenterOnline = ref(false)
const commandCenterChecked = ref(false)
const lastError = ref('')
const businessActionPending = ref('')
const viewLaunchPending = ref('')
const streamlitFrameSrc = ref('')
const strategyFrameSrc = ref('')
const cesiumFrameSrc = ref('')
const cesiumEndpoint = ref('crash')
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
  metricsRaw: null,
  updatedAt: '',
})

const deductionScene = ref('leak')
const deductionObstacle = ref('1')
const deductionStrategy = ref('rcd')
const deductionPending = ref(false)
const deductionStatus = ref('')
const multiAgentData = ref(null)
const showMultiAgentPanel = ref(false)

const cesiumScene = ref('leak')
const cesiumPending = ref(false)
const cesiumStatus = ref('')

watch([deductionScene, cesiumScene, deductionObstacle, deductionStrategy], () => {
  showMultiAgentPanel.value = false
})

const streamlitMode = ref('medical')
const streamlitSeverity = ref('中度')
const streamlitWeather = ref('☀️ 晴朗')
const streamlitTime = ref('08:30')
const streamlitPending = ref(false)
const streamlitStatus = ref('')

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
  if (!commandCenterOnline.value) {
    return '当前后端离线，无法远程启动服务。请先运行 start_Collaborative_Response.bat。'
  }
  if (!activeViewService.value?.startConfigured) {
    return activeViewServiceLabel.value + ' 尚未配置启动命令，请检查 services.local.json。'
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
    evaluation.metricsRaw = payload || null
    evaluation.updatedAt = payload.updated_at || ''
    multiAgentData.value = payload.multi_agent || null
  } catch {
    evaluation.message = '暂未获取到策略评估结果'
    evaluation.metrics = {}
    evaluation.metricsRaw = null
    evaluation.updatedAt = ''
    multiAgentData.value = null
  }
}

async function refreshStatus() {
  try {
    const payload = await requestJson(
      buildCollaborativeApiUrl('api/health', commandCenterBaseUrl.value),
      { cache: 'no-store' }
    )
    commandCenterOnline.value = Boolean(payload.ok)
    commandCenterChecked.value = true
    updateService('commandCenter', payload.services?.commandCenter, commandCenterBaseUrl.value)
    updateService('streamlit', payload.services?.streamlit, streamlitUrl.value)
    lastError.value = ''
  } catch (error) {
    commandCenterOnline.value = false
    commandCenterChecked.value = true
    lastError.value = error instanceof Error ? error.message : '无法连接后端'

    const [commandCenterAlive, streamlitAlive] = await Promise.all([
      probeDirect(buildCommandCenterUrl('api/health', commandCenterBaseUrl.value)),
      probeDirect(streamlitUrl.value),
    ])

    updateService(
      'commandCenter',
      { reachable: commandCenterAlive, running: commandCenterAlive, public_url: commandCenterBaseUrl.value },
      commandCenterBaseUrl.value
    )
    updateService(
      'streamlit',
      { reachable: streamlitAlive, running: streamlitAlive, public_url: streamlitUrl.value },
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

async function reloadControllerConfig() {
  if (!commandCenterOnline.value) return false
  try {
    await requestJson(buildCollaborativeApiUrl('api/reload-config', commandCenterBaseUrl.value), {
      method: 'POST',
    })
    return true
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : '后端配置重载失败'
    return false
  }
}

async function toggleManagedService(serviceId, nextRunning) {
  if (!commandCenterOnline.value) {
    lastError.value = '后端离线，当前无法远程启停服务'
    return false
  }

  services[serviceId].pending = true
  try {
    if (nextRunning) {
      await reloadControllerConfig()
    }

    const action = nextRunning ? 'start' : 'stop'
    await requestJson(
      buildCollaborativeApiUrl('api/services/' + serviceId + '/' + action, commandCenterBaseUrl.value),
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

  if (!commandCenterOnline.value) {
    lastError.value = '后端离线，无法远程启动服务'
    return false
  }

  if (!services[serviceId].startConfigured) {
    lastError.value = serviceId + ' 未配置启动命令，请检查 config.local.json'
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

  const serviceLabel = serviceId === 'streamlit' ? '协同调度平台' : '协同响应指挥后端'
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
    buildCommandCenterUrl('2d_deduction.html', resolvedCommandCenterBaseUrl.value),
    { t: Date.now() }
  )
  cesiumFrameSrc.value = appendUrlParams(
    buildCommandCenterUrl('cesium_viewer?end_point=' + cesiumScene.value, resolvedCommandCenterBaseUrl.value),
    { t: Date.now() }
  )
  streamlitFrameKey.value += 1
  strategyFrameKey.value += 1
  cesiumFrameKey.value += 1
}

function showHome() {
  currentView.value = 'home'
  showMultiAgentPanel.value = false
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

function buildStreamlitUrl() {
  const base = (resolvedStreamlitUrl.value || streamlitUrl.value).split('?')[0]
  const p = new URLSearchParams({ embed: 'true', sidebar: 'minimal', mode: streamlitMode.value, severity: streamlitSeverity.value, weather: streamlitWeather.value })
  if (streamlitTime.value) p.set('time', streamlitTime.value)
  return base + '?' + p.toString()
}

function applyStreamlitSettings() {
  streamlitPending.value = true
  streamlitStatus.value = '应用设置中...'
  streamlitFrameSrc.value = buildStreamlitUrl()
  streamlitFrameKey.value += 1
  setTimeout(() => { streamlitPending.value = false; streamlitStatus.value = '' }, 1500)
}

async function showStreamlitView() {
  await openManagedView('streamlit', 'streamlit', () => {
    streamlitFrameSrc.value = buildStreamlitUrl()
    streamlitFrameKey.value += 1
  })
  showMultiAgentPanel.value = false
}

async function show2DView() {
  await openManagedView('2d', 'commandCenter', () => {
    strategyFrameSrc.value = appendUrlParams(
      buildCommandCenterUrl('2d_deduction.html', resolvedCommandCenterBaseUrl.value),
      { t: Date.now() }
    )
    strategyFrameKey.value += 1
  })
  showMultiAgentPanel.value = false
}

async function show3DView() {
  await openManagedView('3d', 'commandCenter', async () => {
    // 先确保 CZML 处于默认状态（全部 POI 亮色）
    await fetch(buildCommandCenterUrl(`api/run_3d_cesium?end_point=${cesiumScene.value}`, commandCenterBaseUrl.value)).catch(()=>{})
    cesiumFrameSrc.value = buildCommandCenterUrl('cesium_viewer?end_point=' + cesiumScene.value, resolvedCommandCenterBaseUrl.value)
    cesiumFrameKey.value += 1
  })
  showMultiAgentPanel.value = false
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
  const ep = cesiumEndpoint.value || 'crash'
  runCommandCenterAction(`api/run_3d_cesium?end_point=${encodeURIComponent(ep)}`, '3d')
}

async function triggerReplan() {
  showMultiAgentPanel.value = false
  deductionPending.value = true
  deductionStatus.value = '规划中...'
  try {
    const params = new URLSearchParams({
      end_point: deductionScene.value,
      ugv_block: deductionObstacle.value,
      uav_smoke: deductionObstacle.value,
      strategy: deductionStrategy.value,
      compare: '1',
    })
    const resp = await fetch(buildCommandCenterUrl(`api/run_3d_strategy?${params}`, commandCenterBaseUrl.value))
    if (!resp.ok) throw new Error('HTTP ' + resp.status)
    deductionStatus.value = '规划完成'
    refreshFrames()
  } catch (e) {
    deductionStatus.value = '规划失败: ' + e.message
  } finally {
    deductionPending.value = false
  }
}

async function triggerMultiAgent() {
  showMultiAgentPanel.value = false
  deductionPending.value = true
  deductionStatus.value = '装备启动中...'
  try {
    const params = new URLSearchParams({
      end_point: deductionScene.value,
      ugv_block: deductionObstacle.value,
      uav_smoke: deductionObstacle.value,
      strategy: deductionStrategy.value,
    })
    const resp = await fetch(buildCommandCenterUrl(`api/run_multi_agent?${params}`, commandCenterBaseUrl.value))
    if (!resp.ok) throw new Error('HTTP ' + resp.status)
    deductionStatus.value = '装备已启动'
    refreshFrames()
    await refreshEvaluation()
    // 计算完成后延迟展示决策日志，体现智能性
    setTimeout(() => { showMultiAgentPanel.value = true }, 800)
  } catch (e) {
    deductionStatus.value = '启动失败: ' + e.message
  } finally {
    deductionPending.value = false
  }
}

async function triggerCesiumUGVUAV() {
  showMultiAgentPanel.value = false
  cesiumPending.value = true; cesiumStatus.value = '无人装备出动中...'
  try {
    const r = await fetch(buildCommandCenterUrl(`api/run_3d_cesium?end_point=${cesiumScene.value}`, commandCenterBaseUrl.value))
    if (!r.ok) throw new Error('HTTP ' + r.status)
    cesiumStatus.value = '已出动'
    cesiumFrameSrc.value = ''; setTimeout(() => refreshFrames(), 800)
  } catch (e) { cesiumStatus.value = '失败: ' + e.message } finally { cesiumPending.value = false }
}

async function triggerCesiumMultiAgent() {
  showMultiAgentPanel.value = false
  cesiumPending.value = true; cesiumStatus.value = '救援装备出动中...'
  try {
    const r = await fetch(buildCommandCenterUrl(`api/run_multi_agent?end_point=${cesiumScene.value}&strategy=rcd`, commandCenterBaseUrl.value))
    if (!r.ok) throw new Error('HTTP ' + r.status)
    cesiumStatus.value = '已出动'
    cesiumFrameSrc.value = ''; setTimeout(() => refreshFrames(), 1000)
    await refreshEvaluation()
    // 计算完成后延迟展示决策日志，体现智能性
    setTimeout(() => { showMultiAgentPanel.value = true }, 800)
  } catch (e) { cesiumStatus.value = '失败: ' + e.message } finally { cesiumPending.value = false }
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
.layout {
  display: flex;
  height: 100vh;
  background: #020813;
  color: #cbd5e1;
  font-family: 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, sans-serif;
  overflow: hidden;
}

.sidebar {
  width: 320px;
  padding: 24px;
  background: rgba(10, 19, 35, 0.82);
  backdrop-filter: blur(20px) saturate(140%);
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  border-right: 1px solid rgba(0, 242, 254, 0.22);
  box-shadow: 0 0 30px rgba(0, 0, 0, 0.7), inset 0 0 20px rgba(0, 242, 254, 0.05);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar h2 {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 800;
  background: linear-gradient(135deg, #ffffff 0%, #93c5fd 50%, #00f2fe 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 20px rgba(0, 242, 254, 0.2);
  text-align: center;
  letter-spacing: 1px;
}

.menu {
  display: grid;
  gap: 10px;
}

.menu-btn,
.blue-btn,
.cyan-btn,
.purple-btn,
.dark-btn,
.ghost-btn {
  border: 1px solid transparent;
  border-radius: 12px;
  color: #cbd5e1;
  cursor: pointer;
  font-weight: 700;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  outline: none;
}

.menu-btn {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #94a3b8;
  font-size: 13px;
}

.menu-btn:hover {
  background: rgba(0, 242, 254, 0.08);
  border-color: rgba(0, 242, 254, 0.35);
  color: #00f2fe;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.15);
}

.menu-btn.active {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.18) 0%, rgba(37, 99, 235, 0.18) 100%);
  border-color: #00f2fe;
  color: #00f2fe;
  box-shadow: 0 0 15px rgba(0, 242, 254, 0.3);
  text-shadow: 0 0 5px rgba(0, 242, 254, 0.5);
}

.blue-btn,
.cyan-btn,
.purple-btn {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(37, 99, 235, 0.15) 100%);
  border: 1px solid rgba(0, 242, 254, 0.4);
  color: #00f2fe;
  text-shadow: 0 0 2px rgba(0, 242, 254, 0.3);
}

.blue-btn:hover,
.cyan-btn:hover,
.purple-btn:hover {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.28) 0%, rgba(37, 99, 235, 0.28) 100%);
  border-color: #00f2fe;
  color: #ffffff;
  box-shadow: 0 0 15px rgba(0, 242, 254, 0.4);
}

.blue-btn:active,
.cyan-btn:active,
.purple-btn:active {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.4) 0%, rgba(37, 99, 235, 0.4) 100%);
  box-shadow: 0 0 20px rgba(0, 242, 254, 0.6);
}

.dark-btn,
.ghost-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #cbd5e1;
}

.dark-btn:hover,
.ghost-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.3);
  color: #ffffff;
}

.status-box {
  padding: 16px;
  border-radius: 16px;
  background: rgba(2, 12, 26, 0.6);
  border: 1px solid rgba(0, 242, 254, 0.15);
  box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.05);
}

.status-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 242, 254, 0.1);
  font-size: 13px;
}

.status-row:last-child {
  border-bottom: none;
}

.ok {
  color: #00f2fe;
  text-shadow: 0 0 8px rgba(0, 242, 254, 0.4);
}

.warn {
  color: #ef4444;
  text-shadow: 0 0 8px rgba(239, 68, 68, 0.4);
}

.pending {
  color: #f59e0b;
  text-shadow: 0 0 8px rgba(245, 158, 11, 0.4);
}

.deduction-controls {
  padding: 16px;
  border-radius: 14px;
  background: rgba(2, 12, 26, 0.6);
  border: 1px solid rgba(0, 242, 254, 0.15);
  box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.05);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ctrl-title {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 700;
  color: #00f2fe;
  text-shadow: 0 0 8px rgba(0, 242, 254, 0.3);
}

.ctrl-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ctrl-field span {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
}

.ctrl-select {
  padding: 7px 28px 7px 10px;
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.4);
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  outline: none;
  transition: all 0.3s;
}

.ctrl-select:focus {
  border-color: #00f2fe;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.4), inset 0 0 8px rgba(0, 242, 254, 0.15);
}

.ctrl-btns {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.ctrl-btn {
  flex: 1;
  min-height: 36px;
  border-radius: 8px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
}

.ctrl-btn.blue {
  background: rgba(37, 99, 235, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.4);
  color: #38bdf8;
}

.ctrl-btn.blue:hover {
  background: rgba(56, 189, 248, 0.35);
  border-color: #38bdf8;
  color: #fff;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
}

.ctrl-btn.green {
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(52, 211, 153, 0.4);
  color: #34d399;
}

.ctrl-btn.green:hover {
  background: rgba(52, 211, 153, 0.35);
  border-color: #34d399;
  color: #fff;
  box-shadow: 0 0 10px rgba(52, 211, 153, 0.3);
}

.ctrl-btn.ghost {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #cbd5e1;
}

.ctrl-btn.ghost:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.3);
  color: #fff;
}

.ctrl-status {
  margin: 0;
  font-size: 11px;
  color: #fbbf24;
  text-align: center;
}

.content {
  flex: 1;
  position: relative;
  background:
    radial-gradient(circle at top left, rgba(0, 242, 254, 0.08), transparent 35%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.08), transparent 35%),
    #020813;
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
  overflow-y: auto;
}

.card {
  width: min(1080px, 100%);
  padding: 28px;
  border-radius: 24px;
  background: rgba(2, 12, 26, 0.7);
  border: 1px solid rgba(0, 242, 254, 0.18);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 0 30px rgba(0, 242, 254, 0.05);
}

.card h3 {
  margin: 0 0 14px;
  font-size: 26px;
  font-weight: 800;
  color: #ffffff;
  background: linear-gradient(135deg, #ffffff 0%, #00f2fe 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.card p {
  line-height: 1.8;
  color: #cbd5e1;
  font-size: 14px;
}

.config-list {
  display: grid;
  gap: 16px;
  margin-top: 24px;
}

.field span {
  display: block;
  margin-bottom: 8px;
  font-weight: 700;
  color: #94a3b8;
  font-size: 13px;
}

.field-row,
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.field input {
  flex: 1 1 320px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid rgba(0, 242, 254, 0.3);
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  transition: all 0.3s;
}

.field input:focus {
  border-color: #00f2fe;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.4), inset 0 0 8px rgba(0, 242, 254, 0.15);
  outline: none;
}

.ghost-btn,
.blue-btn,
.cyan-btn,
.purple-btn,
.dark-btn {
  min-height: 42px;
  padding: 0 20px;
}

.service-grid {
  display: grid;
  gap: 16px;
  margin-top: 24px;
}

.service-card {
  padding: 20px;
  border-radius: 14px;
  background: rgba(10, 25, 47, 0.4);
  border: 1px solid rgba(0, 242, 254, 0.12);
  box-shadow: inset 0 0 15px rgba(0, 242, 254, 0.03);
  transition: all 0.3s ease;
}

.service-card:hover {
  border-color: rgba(0, 242, 254, 0.35);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4), inset 0 0 20px rgba(0, 242, 254, 0.08);
}

.service-card strong {
  color: #ffffff;
  font-size: 16px;
}

.service-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.service-top p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #00f2fe;
  word-break: break-all;
  font-family: monospace;
}

.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
}

.chip.ok {
  background: rgba(0, 242, 254, 0.1);
  color: #00f2fe;
  border-color: rgba(0, 242, 254, 0.3);
}

.chip.warn {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
}

.chip.pending {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.3);
}

.error-text {
  margin-top: 16px;
  color: #f87171;
  font-size: 13px;
}

.frame-shell {
  position: relative;
}

.frame-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  gap: 16px;
  padding: 32px;
  background: rgba(2, 8, 19, 0.95);
}

.frame-state h3 {
  margin: 0;
  font-size: 24px;
  color: #ffffff;
}

.frame-state p {
  margin: 0;
  max-width: 600px;
  line-height: 1.8;
  color: #cbd5e1;
}

.frame-state__meta {
  color: #00f2fe;
  font-family: monospace;
}

.frame-state__meta.is-error {
  color: #ef4444;
}

.frame {
  width: 100%;
  height: 100%;
  border: none;
  background: #020813;
}

.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(2, 8, 19, 0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.overlay-card {
  width: min(760px, calc(100% - 48px));
  padding: 32px;
  border-radius: 20px;
  background: rgba(2, 12, 26, 0.95);
  border: 1px solid rgba(0, 242, 254, 0.35);
  position: relative;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), inset 0 0 30px rgba(0, 242, 254, 0.08);
}

.overlay-card h3 {
  margin: 0 0 20px;
  font-size: 24px;
  color: #ffffff;
  border-bottom: 1px solid rgba(0, 242, 254, 0.15);
  padding-bottom: 10px;
}

.close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.05);
  color: #94a3b8;
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  transition: all 0.3s;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.4);
  color: #ffffff;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.metric {
  padding: 18px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(0, 242, 254, 0.08);
}

.metric span {
  display: block;
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 13px;
}

.metric strong {
  font-size: 24px;
  color: #00f2fe;
  text-shadow: 0 0 8px rgba(0, 242, 254, 0.3);
}

.overlay-meta {
  margin-top: 20px;
  color: #cbd5e1;
  font-size: 13px;
}

@media (max-width: 1200px) {
  .layout {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid rgba(0, 242, 254, 0.22);
  }
}

.scene-select {
  min-height: 42px;
  padding: 0 32px 0 12px;
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.4);
  color: #fbbf24;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  outline: none;
  transition: all 0.3s;
}

.scene-select:hover,
.scene-select:focus {
  border-color: #00f2fe;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.2);
}

.scene-select option {
  background: #020813;
  color: #e2e8f0;
}

.dark-btn:disabled,
.ghost-btn:disabled,
.blue-btn:disabled,
.cyan-btn:disabled,
.purple-btn:disabled,
.ctrl-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  box-shadow: none !important;
  border-color: rgba(255, 255, 255, 0.05) !important;
  background: rgba(255, 255, 255, 0.02) !important;
  color: #64748b !important;
  text-shadow: none !important;
}

@media (max-width: 768px) {
  .metrics {
    grid-template-columns: 1fr;
  }
}

/* 协同策略评估报告弹窗增强样式 */
.strategy-evaluation-modal {
  width: min(840px, calc(100% - 48px)) !important;
  max-height: 85vh;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 242, 254, 0.3) transparent;
}
.strategy-evaluation-modal::-webkit-scrollbar {
  width: 6px;
}
.strategy-evaluation-modal::-webkit-scrollbar-thumb {
  background-color: rgba(0, 242, 254, 0.3);
  border-radius: 3px;
}
.modal-title {
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.3);
}
.evaluation-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 20px;
}
.evaluation-meta-grid .meta-item {
  display: flex;
  flex-direction: column;
}
.evaluation-meta-grid .label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 4px;
}
.evaluation-meta-grid .val {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}
.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #00f2fe;
  margin: 18px 0 10px;
  border-left: 3px solid #00f2fe;
  padding-left: 8px;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.metric-card {
  background: rgba(10, 25, 47, 0.3);
  border: 1px solid rgba(0, 242, 254, 0.12);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.02);
}
.metric-card .card-label {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 6px;
}
.metric-card .card-val {
  font-size: 18px;
  color: #ffffff;
  font-weight: 700;
}
.comparison-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 12px;
}
.comparison-card {
  background: rgba(2, 12, 26, 0.5);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 14px;
}
.comparison-card h5 {
  margin: 0 0 10px;
  font-size: 13px;
  color: #cbd5e1;
}
.comp-details {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}
.comp-details .arrow {
  color: #00f2fe;
}
.comp-details .opt {
  color: #ffffff;
  font-weight: 600;
}
.saving-badge {
  font-size: 12px;
  font-weight: 600;
  background: rgba(0, 242, 254, 0.08);
  border: 1px solid rgba(0, 242, 254, 0.2);
  border-radius: 4px;
  padding: 4px;
  text-align: center;
}
.text-cyan {
  color: #00f2fe !important;
}
.total-opt-bar {
  background: rgba(0, 242, 254, 0.05);
  border: 1px dashed rgba(0, 242, 254, 0.3);
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  margin-bottom: 20px;
}
.total-opt-bar strong {
  font-size: 16px;
}
.scenario-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid transparent;
}
.badge.danger {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.25);
}
.badge.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.25);
}
.badge.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.25);
}
.badge.info {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.25);
}
.congestion-info-box {
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #cbd5e1;
  margin-bottom: 20px;
}
.candidate-list {
  display: grid;
  gap: 6px;
  margin-bottom: 20px;
}
.candidate-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.01);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #cbd5e1;
}
.candidate-row.is-selected {
  background: rgba(0, 242, 254, 0.04);
  border-color: rgba(0, 242, 254, 0.3);
  color: #ffffff;
}
.candidate-row .selected-tag {
  background: #00f2fe;
  color: #020813;
  font-size: 9px;
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 3px;
  margin-left: 8px;
}
.modal-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
