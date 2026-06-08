<template>
  <div class="home-dashboard">
    <!-- Top Nav / Toolbar -->
    <header class="top-nav-desktop">
      <div class="toolbar">
        <button
          v-for="item in topMenus"
          :key="item.key"
          type="button"
          class="toolbar-btn"
          :class="{ active: activeMenuKey === item.key }"
          @click="goTo(item)"
        >
          {{ item.label }}
        </button>
      </div>
    </header>

    <div class="main-layout">
      <!-- Left Sidebar (White) -->
      <aside class="left-sidebar" :class="{ collapsed: isLeftCollapsed }">
        <button class="toggle-btn toggle-btn-left" type="button" @click="isLeftCollapsed = !isLeftCollapsed">
          {{ isLeftCollapsed ? '▶' : '◀' }}
        </button>
        <div class="sidebar-header">
          <h2 class="sidebar-title">工作目录 / 服务中心</h2>
          <span class="sidebar-subtitle">Service Center</span>
        </div>
        <div class="sidebar-content">
          <div
            v-for="item in servicePanels"
            :key="item.id"
            class="accordion-item-light"
            :class="{ open: activeServiceId === item.id }"
          >
            <button class="accordion-trigger-light" type="button" @click="toggleServicePanel(item.id)">
              <div class="trigger-copy">
                <span class="trigger-kicker">{{ item.owner.toUpperCase() }} SERVICE</span>
                <h3 class="trigger-title">{{ item.title }}</h3>
              </div>
              <span class="trigger-indicator">{{ activeServiceId === item.id ? '收起' : '展开' }}</span>
            </button>

            <transition name="accordion">
              <div v-if="activeServiceId === item.id" class="accordion-body-light">
                <CollaborativeResponseCard v-if="item.id === 'collaborative'" />
                <SensorGatewayCard v-else-if="item.id === 'sensor'" />
                <RealtimeDetectionCard v-else />
              </div>
            </transition>
          </div>
        </div>
      </aside>

      <!-- Center Viewport (Cesium Map) -->
      <main class="center-viewport-container">
        <div class="viewport-header">
          <div class="viewport-title-left">
            <span class="viewport-icon">🗺️</span>
            <span class="viewport-title-text">View 1 (Cesium 三维态势图)</span>
          </div>
          <div class="viewport-controls">
            <button class="win-btn">➖</button>
            <button class="win-btn">🔳</button>
            <button class="win-btn">❌</button>
          </div>
        </div>
        
        <div class="viewport-body">
          <div class="globe-layer">
            <HomeCesiumGlobe
              ref="globeRef"
              :phases="timelinePhases"
              :active-phase-index="activePhaseIndex"
              :focused-point-id="currentFocusedPoint"
              @accident-picked="onAccidentPickedOnGlobe"
              @models-ready="onModelsReady"
            />
          </div>
          
          <!-- Bottom Timeline embedded inside center body for containment -->
          <div class="timeline-container" :style="{ bottom: timelineBottom + 'px' }">
            <HomeTimeProgress
              v-model="activePhaseIndex"
              v-model:accident-index="activeAccidentIndex"
              :phases="timelinePhases"
              :accidents="accidentPoints"
              :phases-ready="phasesReady"
              @locate="handleLocate"
            />
          </div>
        </div>
      </main>

      <!-- Right Sidebar (White) -->
      <aside class="right-sidebar" :class="{ collapsed: isRightCollapsed }">
        <button class="toggle-btn toggle-btn-right" type="button" @click="isRightCollapsed = !isRightCollapsed">
          {{ isRightCollapsed ? '◀' : '▶' }}
        </button>
        <div class="sidebar-header">
          <h2 class="sidebar-title">处理参数与当前状态</h2>
          <span class="sidebar-subtitle">Processing Parameters</span>
        </div>
        <div class="sidebar-content">
          <div class="parameter-table">
            <div class="table-header">
              <span class="col-param">参数</span>
              <span class="col-val">当前状态/值</span>
            </div>
            <div class="table-body">
              <div class="table-row">
                <span class="col-param font-medium">当前事故场景</span>
                <span class="col-val text-blue font-semibold">{{ currentAccidentId === 'rear-end' ? '货车追尾现场' : '油罐车泄露现场' }}</span>
              </div>
              <div class="table-row">
                <span class="col-param font-medium">推演阶段</span>
                <span class="col-val font-semibold">{{ timelinePhases[activePhaseIndex]?.shortLabel || '未开始' }}</span>
              </div>
              <div class="table-row">
                <span class="col-param font-medium">仿真当前时间</span>
                <span class="col-val text-amber font-semibold">{{ timelinePhases[activePhaseIndex]?.time || '00:00' }}</span>
              </div>
              <div class="table-row">
                <span class="col-param font-medium">网关与检测</span>
                <span class="col-val text-green font-semibold">系统协同联动中</span>
              </div>
              <div class="table-row">
                <span class="col-param font-medium">三维地图引擎</span>
                <span class="col-val">Cesium 3D Globe</span>
              </div>
            </div>
          </div>

          <IntegrationEventMonitor />
          
          <div class="action-card-right">
            <h3 class="action-card-title">场景重置与交互操作</h3>
            <p class="action-card-desc">您可以点击下方按钮对当前选中的事故点进行视角定位或将仿真阶段重置。</p>
            <div class="action-card-btns">
              <button class="action-btn-desktop primary" @click="handleLocate">定位到事故点</button>
              <button class="action-btn-desktop secondary" @click="activePhaseIndex = 0">重置当前阶段</button>
            </div>
          </div>

          <div class="action-card-right" style="margin-top: 12px;">
            <h3 class="action-card-title">时间轴垂直位置微调</h3>
            <p class="action-card-desc">拉动滑块实时手动调整底部时间轴的垂直高度：</p>
            <div class="slider-control-row">
              <input
                type="range"
                v-model.number="timelineBottom"
                min="-10"
                max="100"
                step="1"
                class="desktop-slider"
              />
              <span class="slider-val">{{ timelineBottom }}px</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import CollaborativeResponseCard from '../components/CollaborativeResponseCard.vue'
import RealtimeDetectionCard from '../components/RealtimeDetectionCard.vue'
import SensorGatewayCard from '../components/SensorGatewayCard.vue'
import IntegrationEventMonitor from '../components/IntegrationEventMonitor.vue'
import HomeCesiumGlobe from '../components/home/HomeCesiumGlobe.vue'
import HomeTimeProgress from '../components/home/HomeTimeProgress.vue'

const router = useRouter()
const route = useRoute()
const activeServiceId = ref('')
const activeMenuKey = ref('')
const globeRef = ref(null)

const isLeftCollapsed = ref(false)
const isRightCollapsed = ref(false)

const activeAccidentIndex = ref(0)
const currentFocusedPoint = ref('')
const modelsReadyStatus = ref({})
const timelineBottom = ref(18)

// 为每个事故点维护独立的进度状态
const accidentPhaseIndices = ref({
  'rear-end': 0,
  'leakage': 0
})

// 计算当前事故点的 ID
const currentAccidentId = computed(() => {
  return accidentPoints[activeAccidentIndex.value]?.id || ''
})

// 计算并控制当前显示的阶段索引
const activePhaseIndex = computed({
  get: () => accidentPhaseIndices.value[currentAccidentId.value] || 0,
  set: (val) => {
    accidentPhaseIndices.value[currentAccidentId.value] = val
  }
})

const topMenus = [
  { key: 'sensor', label: '传感器管理', path: '/sensor-manage' },
  { key: 'realtime', label: '实时检测', path: '/realtime' },
  { key: 'coordination', label: '协同响应', path: '/coordination' },
  { key: '2d-deduction', label: '二维动态推演', path: '/2d-deduction' },
  { key: 'modeling', label: '精细建模', path: '/modeling' },
  { key: 'simulation', label: '仿真推演', path: '/simulation' },
]

const accidentPoints = [
  {
    id: 'rear-end',
    title: '货车追尾现场',
    focusPoint: 'accident_blue',
    phases: [
      { id: 't-start', time: '14:00', shortLabel: '仿真开始', title: '仿真推演开始', systems: ['总系统首页'], focusPoint: 'accident_blue' },
      { id: 't-normal', time: '14:05', shortLabel: '正常行驶', title: '车辆正常行驶阶段', systems: ['边缘网关'], focusPoint: 'accident_blue' },
      { id: 't-accident', time: '14:12', shortLabel: '事故发生', title: '货车追尾事故瞬间', systems: ['实时检测'], focusPoint: 'detection' },
      { id: 't-smoke', time: '14:18', shortLabel: '次生灾害（烟雾）', title: '事故现场产生大量烟雾', systems: ['协同响应'], focusPoint: 'command' },
      { id: 't-fire', time: '14:26', shortLabel: '次生灾害（起火）', title: '事故车辆开始起火', systems: ['协同响应'], focusPoint: 'response' },
      { id: 't-spread', time: '14:40', shortLabel: '次生灾害（大火）', title: '火势进一步扩大蔓延', systems: ['总系统首页'], focusPoint: 'gateway' },
      { id: 't-uav-start', time: '14:45', shortLabel: '无人装备出动', title: '无人装备协同出动', systems: ['协同响应'], focusPoint: 'accident_blue' },
      { id: 't-uav-deploy', time: '14:50', shortLabel: '无人感知部署', title: '无人感知节点部署', systems: ['实时检测'], focusPoint: 'accident_blue' },
      { id: 't-uav-exec', time: '14:55', shortLabel: '无人感知执行', title: '无人感知任务执行', systems: ['协同响应'], focusPoint: 'accident_blue' },
    ]
  },
  {
    id: 'leakage',
    title: '油罐车泄露现场',
    focusPoint: 'accident_red',
    phases: [
      { id: 'l-start', time: '15:00', shortLabel: '仿真开始', title: '油罐车仿真推演开始', systems: ['总系统首页'], focusPoint: 'accident_red' },
      { id: 'l-normal', time: '15:05', shortLabel: '正常行驶', title: '油罐车正常行驶阶段', systems: ['边缘网关'], focusPoint: 'accident_red' },
      { id: 'l-accident', time: '15:12', shortLabel: '事故发生（侧翻）', title: '油罐车发生侧翻事故', systems: ['实时检测'], focusPoint: 'accident_red' },
      { id: 'l-leak', time: '15:20', shortLabel: '次生灾害（泄露）', title: '罐体受损开始发生化学品泄露', systems: ['实时检测', '协同响应'], focusPoint: 'accident_red' },
      { id: 'l-fill', time: '15:35', shortLabel: '次生灾害（弥漫）', title: '泄露液体开始向四周大面积弥漫', systems: ['协同响应'], focusPoint: 'accident_red' },
      { id: 'l-spread', time: '15:50', shortLabel: '次生灾害（扩散）', title: '挥发气体随风向周边区域扩散', systems: ['总系统首页', '协同响应'], focusPoint: 'accident_red' },
      { id: 'l-uav-start', time: '15:55', shortLabel: '无人装备出动', title: '无人装备协同出动', systems: ['协同响应'], focusPoint: 'accident_red' },
      { id: 'l-uav-deploy', time: '16:00', shortLabel: '无人感知部署', title: '无人感知节点部署', systems: ['实时检测'], focusPoint: 'accident_red' },
      { id: 'l-uav-exec', time: '16:05', shortLabel: '无人感知执行', title: '无人感知任务执行', systems: ['协同响应'], focusPoint: 'accident_red' },
    ]
  },
]

// 计算当前显示的阶段
const timelinePhases = computed(() => {
  return accidentPoints[activeAccidentIndex.value]?.phases || []
})

const phaseToModelMap = {
  1: 'model_normal',
  2: 'model_accident',
  3: 'model_accident',
  4: 'model_accident',
  5: 'model_accident',
  6: 'model_accident',
  7: 'model_accident',
  8: 'model_accident'
}

const tankerPhaseToModelMap = {
  1: 'tanker_normal',
  2: 'tanker_accident',
  3: 'tanker_accident',
  4: 'tanker_accident',
  5: 'tanker_accident',
  6: 'tanker_accident',
  7: 'tanker_accident',
  8: 'tanker_accident'
}

const phasesReady = computed(() => {
  if (timelinePhases.value.length === 0) return []
  const isTruck = timelinePhases.value[0]?.id.startsWith('t-')
  const map = isTruck ? phaseToModelMap : tankerPhaseToModelMap
  return timelinePhases.value.map((p, idx) => {
    const mid = map[idx]
    if (!mid) return true // 不需要模型的阶段视为就绪
    return !!modelsReadyStatus.value[mid]
  })
})

const servicePanels = [
  {
    id: 'collaborative',
    theme: 'collaborative',
    owner: 'dh',
    title: '协同响应服务',
    description: '控制层、二维推演、三维态势地图与策略评估接入。',
  },
  {
    id: 'sensor',
    theme: 'sensor',
    owner: 'lb',
    title: '边缘传感器网关',
    description: '办公室端查看边缘状态，控制采集并承接现场数据。',
  },
  {
    id: 'realtime',
    theme: 'realtime',
    owner: 'zby',
    title: '实时检测服务',
    description: '模型状态、RTSP 推理任务与检测联动控制。',
  },
]

function readStoredMenuKey() {
  try {
    return window.localStorage.getItem('lkyw.homeActiveMenuKey') || ''
  } catch {
    return ''
  }
}

function persistMenuKey(value) {
  try {
    window.localStorage.setItem('lkyw.homeActiveMenuKey', value)
  } catch {
    // ignore
  }
}

function toggleServicePanel(serviceId) {
  activeServiceId.value = activeServiceId.value === serviceId ? '' : serviceId
}

function goTo(item) {
  activeMenuKey.value = item.key
  persistMenuKey(item.key)
  router.push(item.path)
}

function onAccidentPickedOnGlobe(entityId) {
  const index = accidentPoints.findIndex((acc) => acc.focusPoint === entityId)
  if (index !== -1) {
    activeAccidentIndex.value = index
    currentFocusedPoint.value = entityId
  }
}

function handleLocate() {
  if (globeRef.value) {
    const accident = accidentPoints[activeAccidentIndex.value]
    if (accident) {
      currentFocusedPoint.value = accident.focusPoint
      globeRef.value.zoomToPoint(accident.focusPoint)
    }
  }
}

function onModelsReady(status) {
  modelsReadyStatus.value = status
}

watch(activeAccidentIndex, () => {
  // 切换事故点时不再重置 activePhaseIndex.value = 0，使其保持各自的进度
  currentFocusedPoint.value = ''
})

watch(
  () => route.path,
  (newPath) => {
    if (newPath === '/') {
      activeMenuKey.value = ''
    }
  }
)

onMounted(() => {
  activeMenuKey.value = ''
})
</script>

<style scoped>
/* Main Layout structure */
.home-dashboard {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #eaedf1;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #334155;
}

.main-layout {
  display: flex;
  flex: 1;
  height: 0;
  width: 100%;
  overflow: hidden;
  position: relative;
}

/* Top Nav Desktop (Menu bar + Toolbar) */
.top-nav-desktop {
  background: #f8fafc;
  border-bottom: 1px solid #cbd5e1;
  display: flex;
  flex-direction: column;
  user-select: none;
}

.menu-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 6px 16px;
  background: #ffffff;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
  color: #475569;
}

.app-logo {
  font-weight: 700;
  color: #1e3a8a;
  margin-right: 12px;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.menu-item {
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.menu-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.menu-item.active {
  color: #2563eb;
  font-weight: 600;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f8fafc;
}

.toolbar-btn {
  padding: 6px 12px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.toolbar-btn:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}

.toolbar-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.3);
}

/* Left & Right Sidebars */
.left-sidebar,
.right-sidebar {
  width: 380px;
  height: calc(100% - 32px);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  overflow: visible;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  position: absolute;
  top: 16px;
  bottom: 16px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.left-sidebar {
  left: 16px;
  z-index: 10;
}

.left-sidebar.collapsed {
  transform: translateX(calc(-100% - 20px));
}

.right-sidebar {
  right: 16px;
  z-index: 10;
}

.right-sidebar.collapsed {
  transform: translateX(calc(100% + 20px));
}

/* Sidebar Toggle Buttons */
.toggle-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 50px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 11px;
  transition: all 0.2s;
  z-index: 11;
  padding: 0;
}
.toggle-btn:hover {
  color: #2563eb;
  background: #f8fafc;
}
.toggle-btn-left {
  right: -20px;
  border-radius: 0 8px 8px 0;
  border-left: none;
}
.toggle-btn-right {
  left: -20px;
  border-radius: 8px 0 0 8px;
  border-right: none;
}

.sidebar-header {
  padding: 14px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.sidebar-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.sidebar-subtitle {
  font-size: 10px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-content::-webkit-scrollbar {
  width: 6px;
}
.sidebar-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 99px;
}

/* Accordion Items - Light/White theme */
.accordion-item-light {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  transition: all 0.2s ease;
}

.accordion-item-light.open {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: #cbd5e1;
}

.accordion-trigger-light {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: none;
  background: #f8fafc;
  cursor: pointer;
  text-align: left;
  border-bottom: 1px solid transparent;
}

.accordion-item-light.open .accordion-trigger-light {
  border-bottom-color: #e2e8f0;
}

.trigger-kicker {
  font-size: 9px;
  color: #94a3b8;
  font-weight: 600;
  letter-spacing: 1px;
}

.trigger-title {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.trigger-indicator {
  font-size: 11px;
  color: #64748b;
  background: #ffffff;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-weight: 500;
}

.accordion-body-light {
  padding: 12px;
  background: #ffffff;
}

/* Deep overrides to skin inner dark cards as premium white */
.left-sidebar :deep(.collaborative-response-card),
.left-sidebar :deep(.sensor-gateway-card),
.left-sidebar :deep(.realtime-detection-card) {
  background: #ffffff !important;
  color: #334155 !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: none !important;
  padding: 12px !important;
}

.left-sidebar :deep(.card-title) {
  color: #0f172a !important;
  font-size: 14px !important;
}

.left-sidebar :deep(.card-subtitle),
.left-sidebar :deep(.tip-text) {
  color: #64748b !important;
}

.left-sidebar :deep(.config-input),
.left-sidebar :deep(.gateway-input) {
  background: #f8fafc !important;
  color: #334155 !important;
  border: 1px solid #cbd5e1 !important;
}

.left-sidebar :deep(.status-item),
.left-sidebar :deep(.service-row) {
  background: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
}

.left-sidebar :deep(.status-label),
.left-sidebar :deep(.service-label) {
  color: #64748b !important;
}

.left-sidebar :deep(.status-badge.online),
.left-sidebar :deep(.node-chip.online),
.left-sidebar :deep(.status-value.ok) {
  color: #15803d !important;
  background: #dcfce7 !important;
  border-color: #bbf7d0 !important;
}

.left-sidebar :deep(.status-badge.offline),
.left-sidebar :deep(.node-chip.offline),
.left-sidebar :deep(.status-value.warn) {
  color: #b91c1c !important;
  background: #fee2e2 !important;
  border-color: #fca5a5 !important;
}

.left-sidebar :deep(.action-btn.secondary) {
  color: #2563eb !important;
  background: #eff6ff !important;
  border-color: #bfdbfe !important;
}

.left-sidebar :deep(.action-btn.primary) {
  color: #ffffff !important;
  background: linear-gradient(90deg, #3b82f6 0%, #1d4ed8 100%) !important;
}

.left-sidebar :deep(.action-btn.ghost) {
  color: #475569 !important;
  background: #f1f5f9 !important;
  border-color: #cbd5e1 !important;
}

/* Center Viewport (The GIS View Window) */
.center-viewport-container {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #e2e8f0;
  position: relative;
}

.viewport-header {
  height: 38px;
  background: #1e293b;
  color: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  font-size: 12px;
  font-weight: 500;
  user-select: none;
}

.viewport-title-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.viewport-title-text {
  letter-spacing: 0.5px;
}

.viewport-controls {
  display: flex;
  gap: 6px;
}

.win-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.win-btn:hover {
  background: #334155;
  color: #ffffff;
}

.viewport-body {
  flex: 1;
  position: relative;
  height: 0;
}

.globe-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
}

/* Floating Timeline floating beautifully above the globe */
.timeline-container {
  position: absolute;
  bottom: 20px; /* 往上移动一点，贴近视口 */
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 40px);
  max-width: 1400px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  padding: 12px 20px;
  z-index: 5;
  backdrop-filter: blur(8px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.35);
}

/* Right Sidebar elements */
.parameter-table {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  font-size: 11px;
}

.table-header {
  background: #f8fafc;
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 8px 12px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
}

.table-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  align-items: center;
}

.table-row:last-child {
  border-bottom: none;
}

.font-medium {
  font-weight: 500;
}
.font-semibold {
  font-weight: 600;
}
.text-blue {
  color: #2563eb;
}
.text-amber {
  color: #d97706;
}
.text-green {
  color: #16a34a;
}

.action-card-right {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #f8fafc;
}

.action-card-title {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.action-card-desc {
  margin: 0 0 14px;
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
}

.action-card-btns {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn-desktop {
  width: 100%;
  padding: 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
  text-align: center;
}

.action-btn-desktop.primary {
  background: #2563eb;
  color: #ffffff;
}
.action-btn-desktop.primary:hover {
  background: #1d4ed8;
}

.action-btn-desktop.secondary {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #334155;
}
.action-btn-desktop.secondary:hover {
  background: #f1f5f9;
}

.accordion-enter-active,
.accordion-leave-active {
  transition: all 0.22s ease;
}

.accordion-enter-from,
.accordion-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Slider Controls */
.slider-control-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.desktop-slider {
  flex: 1;
  height: 5px;
  border-radius: 99px;
  background: #e2e8f0;
  outline: none;
  cursor: pointer;
  accent-color: #2563eb;
  border: none;
  padding: 0;
}

.slider-val {
  font-size: 11px;
  font-weight: 600;
  color: #334155;
  min-width: 32px;
  text-align: right;
}
</style>
