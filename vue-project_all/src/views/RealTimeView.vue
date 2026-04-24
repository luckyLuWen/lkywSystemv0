<template>
  <div class="home-dashboard">
    <div class="globe-layer">
      <HomeCesiumGlobe
        ref="globeRef"
        :phases="timelinePhases"
        :active-phase-index="activePhaseIndex"
        :focused-point-id="currentFocusedPoint"
        @accident-picked="onAccidentPickedOnGlobe"
      />
    </div>

    <div class="globe-overlay"></div>
    <div class="globe-decor" aria-hidden="true">
      <span class="orbit orbit-a"></span>
      <span class="orbit orbit-b"></span>
    </div>

    <header class="top-nav">
      <span class="nav-wing nav-wing-left"></span>
      <nav class="top-nav-links">
        <button
          v-for="item in topMenus"
          :key="item.key"
          type="button"
          class="nav-link"
          :class="{ active: activeMenuKey === item.key }"
          @click="goTo(item)"
        >
          {{ item.label }}
        </button>
      </nav>
      <span class="nav-wing nav-wing-right"></span>
    </header>

    <aside class="left-panel">
      <div
        v-for="item in servicePanels"
        :key="item.id"
        class="accordion-item"
        :class="[`is-${item.theme}`, { open: activeServiceId === item.id }]"
      >
        <button class="accordion-trigger" type="button" @click="toggleServicePanel(item.id)">
          <div class="trigger-copy">
            <span class="trigger-kicker">{{ item.owner }}</span>
            <h2 class="trigger-title">{{ item.title }}</h2>
            <p class="trigger-description">{{ item.description }}</p>
          </div>
          <span class="trigger-indicator">{{ activeServiceId === item.id ? '收起' : '展开' }}</span>
        </button>

        <transition name="accordion">
          <div v-if="activeServiceId === item.id" class="accordion-body">
            <CollaborativeResponseCard v-if="item.id === 'collaborative'" />
            <SensorGatewayCard v-else-if="item.id === 'sensor'" />
            <RealtimeDetectionCard v-else />
          </div>
        </transition>
      </div>
    </aside>

    <footer class="bottom-timeline">
      <HomeTimeProgress
        v-model="activePhaseIndex"
        v-model:accident-index="activeAccidentIndex"
        :phases="timelinePhases"
        :accidents="accidentPoints"
        @locate="handleLocate"
      />
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import CollaborativeResponseCard from '../components/CollaborativeResponseCard.vue'
import RealtimeDetectionCard from '../components/RealtimeDetectionCard.vue'
import SensorGatewayCard from '../components/SensorGatewayCard.vue'
import HomeCesiumGlobe from '../components/home/HomeCesiumGlobe.vue'
import HomeTimeProgress from '../components/home/HomeTimeProgress.vue'

const router = useRouter()
const route = useRoute()
const activeServiceId = ref('')
const activePhaseIndex = ref(0)
const activeMenuKey = ref('')
const globeRef = ref(null)

const activeAccidentIndex = ref(0)
const currentFocusedPoint = ref('')

const topMenus = [
  { key: 'sensor', label: '传感器管理', path: '/sensor-manage' },
  { key: 'realtime', label: '实时检测', path: '/realtime' },
  { key: 'coordination', label: '协同响应', path: '/coordination' },
  { key: 'modeling', label: '精细建模', path: '/modeling' },
  { key: 'simulation', label: '仿真推演', path: '/simulation' },
]

const accidentPoints = [
  {
    id: 'rear-end',
    title: '货车追尾现场',
    focusPoint: 'accident_blue',
  },
  {
    id: 'leakage',
    title: '油罐车泄露现场',
    focusPoint: 'accident_red',
  },
]

const timelinePhases = [
  {
    id: 'start',
    time: '14:00',
    shortLabel: '仿真开始',
    title: '仿真推演开始',
    systems: ['总系统首页'],
    focusPoint: 'gateway',
    focusHeading: 0,
    areaRadiusMinor: 150000,
    areaRadiusMajor: 200000,
  },
  {
    id: 'normal',
    time: '14:05',
    shortLabel: '正常行驶',
    title: '车辆正常行驶阶段',
    systems: ['边缘网关', '总系统首页'],
    focusPoint: 'gateway',
    focusHeading: 6,
    areaRadiusMinor: 120000,
    areaRadiusMajor: 170000,
  },
  {
    id: 'accident',
    time: '14:12',
    shortLabel: '事故发生',
    title: '货车追尾事故瞬间',
    systems: ['实时检测', '边缘网关'],
    focusPoint: 'detection',
    focusHeading: 18,
    areaRadiusMinor: 110000,
    areaRadiusMajor: 150000,
  },
  {
    id: 'smoke',
    time: '14:18',
    shortLabel: '烟雾阶段',
    title: '事故现场产生大量烟雾',
    systems: ['协同响应', '实时检测'],
    focusPoint: 'command',
    focusHeading: -10,
    areaRadiusMinor: 150000,
    areaRadiusMajor: 210000,
  },
  {
    id: 'fire',
    time: '14:26',
    shortLabel: '起火阶段',
    title: '事故车辆开始起火',
    systems: ['协同响应', '边缘网关'],
    focusPoint: 'response',
    focusHeading: 26,
    areaRadiusMinor: 130000,
    areaRadiusMajor: 180000,
  },
  {
    id: 'spread',
    time: '14:40',
    shortLabel: '大火蔓延',
    title: '火势进一步扩大蔓延',
    systems: ['总系统首页', '协同响应'],
    focusPoint: 'gateway',
    focusHeading: 10,
    areaRadiusMinor: 180000,
    areaRadiusMajor: 240000,
  },
]

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

watch(activeAccidentIndex, () => {
  activePhaseIndex.value = 0
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
.home-dashboard {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #020813;
}

.globe-layer,
.globe-overlay,
.globe-decor {
  position: absolute;
  inset: 0;
}

.globe-layer {
  z-index: 1;
}

.globe-overlay {
  z-index: 2;
  pointer-events: none;
  background:
    radial-gradient(circle at 50% 50%, rgba(0, 0, 0, 0) 0%, rgba(2, 8, 19, 0.18) 54%, rgba(2, 8, 19, 0.56) 100%),
    linear-gradient(180deg, rgba(1, 7, 16, 0.62) 0%, rgba(1, 7, 16, 0.18) 20%, rgba(1, 7, 16, 0.26) 100%);
}

.globe-decor {
  z-index: 3;
  pointer-events: none;
}

.orbit {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 50%;
  border: 1px solid rgba(0, 229, 255, 0.18);
  box-shadow:
    0 0 18px rgba(0, 229, 255, 0.1),
    inset 0 0 18px rgba(0, 229, 255, 0.04);
  transform: translate(-50%, -50%);
}

.orbit-a {
  width: min(64vw, 820px);
  height: min(64vw, 820px);
  opacity: 0.28;
}

.orbit-b {
  width: min(76vw, 980px);
  height: min(46vw, 590px);
  opacity: 0.22;
  border-color: rgba(255, 184, 77, 0.18);
  box-shadow:
    0 0 18px rgba(255, 184, 77, 0.1),
    inset 0 0 18px rgba(255, 184, 77, 0.04);
}

.top-nav {
  position: absolute;
  top: 18px;
  left: 50%;
  z-index: 4;
  transform: translateX(-50%);
  padding: 10px 18px;
  border-radius: 999px;
  border: 1px solid rgba(0, 229, 255, 0.16);
  background: rgba(2, 10, 22, 0.54);
  backdrop-filter: blur(12px);
  box-shadow: 0 0 24px rgba(0, 229, 255, 0.1);
  overflow: hidden;
}

.top-nav::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(
    90deg,
    rgba(0, 229, 255, 0.36) 0%,
    rgba(255, 184, 77, 0.18) 45%,
    rgba(0, 229, 255, 0.36) 100%
  );
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.top-nav-links {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-wing {
  position: absolute;
  top: 50%;
  width: 76px;
  height: 20px;
  transform: translateY(-50%);
  background: linear-gradient(90deg, rgba(255, 184, 77, 0.16) 0%, rgba(0, 229, 255, 0.08) 100%);
  opacity: 0.85;
  pointer-events: none;
}

.nav-wing-left {
  left: -58px;
  clip-path: polygon(100% 0, 18% 0, 0 50%, 18% 100%, 100% 100%, 86% 50%);
}

.nav-wing-right {
  right: -58px;
  transform: translateY(-50%) scaleX(-1);
  clip-path: polygon(100% 0, 18% 0, 0 50%, 18% 100%, 100% 100%, 86% 50%);
}

.nav-link {
  min-height: 38px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  color: rgba(255, 255, 255, 0.84);
  font-size: 14px;
  cursor: pointer;
  transition: 0.2s ease;
}

.nav-link:hover,
.nav-link.active {
  color: var(--primary-color);
  border-color: rgba(0, 229, 255, 0.16);
  background: rgba(0, 229, 255, 0.08);
  box-shadow: 0 0 14px rgba(0, 229, 255, 0.12);
}

.nav-link.active {
  color: #03111d;
  background: linear-gradient(90deg, rgba(0, 229, 255, 0.92) 0%, rgba(142, 247, 255, 0.94) 100%);
  border-color: rgba(0, 229, 255, 0.26);
}

.left-panel,
.bottom-timeline {
  position: absolute;
  z-index: 4;
}

.left-panel {
  top: 88px;
  left: 20px;
  width: min(360px, calc(100vw - 40px));
  max-height: calc(100% - 210px);
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: auto;
  padding-right: 4px;
}

.bottom-timeline {
  left: 50%;
  bottom: 18px;
  width: min(1120px, calc(100vw - 120px));
  transform: translateX(-50%);
}

.accordion-item {
  position: relative;
  border-radius: 18px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  background: linear-gradient(180deg, rgba(5, 16, 31, 0.82) 0%, rgba(3, 10, 21, 0.92) 100%);
  box-shadow:
    inset 0 0 22px rgba(0, 229, 255, 0.06),
    0 12px 32px rgba(0, 0, 0, 0.16);
  backdrop-filter: blur(14px);
  overflow: hidden;
}

.accordion-item::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08) 0%,
    rgba(0, 229, 255, 0.22) 38%,
    rgba(255, 184, 77, 0.18) 68%,
    rgba(255, 255, 255, 0.08) 100%
  );
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.accordion-item.is-collaborative {
  border-color: rgba(96, 165, 250, 0.22);
}

.accordion-item.is-sensor {
  border-color: rgba(0, 229, 255, 0.2);
}

.accordion-item.is-realtime {
  border-color: rgba(255, 184, 77, 0.24);
}

.accordion-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.trigger-copy {
  min-width: 0;
}

.trigger-kicker {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.68);
  font-size: 11px;
  letter-spacing: 0.12em;
}

.trigger-title {
  margin: 10px 0 8px;
  color: #f4fbff;
  font-size: 28px;
  line-height: 1.04;
}

.trigger-description {
  margin: 0;
  color: rgba(255, 255, 255, 0.68);
  font-size: 13px;
  line-height: 1.6;
}

.trigger-indicator {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.82);
  font-size: 13px;
}

.accordion-item.is-collaborative .trigger-title,
.accordion-item.is-collaborative .trigger-indicator {
  color: #bfdcff;
}

.accordion-item.is-sensor .trigger-title,
.accordion-item.is-sensor .trigger-indicator {
  color: var(--primary-color);
}

.accordion-item.is-realtime .trigger-title,
.accordion-item.is-realtime .trigger-indicator {
  color: #ffd68e;
}

.accordion-body {
  padding: 0 14px 14px;
}

.accordion-body :deep(.collaborative-response-card),
.accordion-body :deep(.sensor-gateway-card),
.accordion-body :deep(.realtime-detection-card) {
  border-radius: 14px;
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

.left-panel::-webkit-scrollbar {
  width: 6px;
}

.left-panel::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 999px;
}

.left-panel::-webkit-scrollbar-thumb {
  background: rgba(0, 229, 255, 0.28);
  border-radius: 999px;
}

@media (max-width: 1320px) {
  .top-nav {
    width: calc(100vw - 40px);
  }

  .top-nav-links {
    justify-content: center;
    flex-wrap: wrap;
  }

  .left-panel {
    width: 320px;
  }

  .bottom-timeline {
    width: calc(100vw - 80px);
  }

  .orbit-a {
    width: min(72vw, 760px);
    height: min(72vw, 760px);
  }
}

@media (max-width: 1080px) {
  .left-panel,
  .bottom-timeline {
    position: static;
    width: auto;
    transform: none;
  }

  .home-dashboard {
    display: flex;
    flex-direction: column;
    overflow: auto;
    padding: 84px 16px 16px;
    box-sizing: border-box;
    gap: 16px;
  }

  .globe-layer,
  .globe-overlay,
  .globe-decor {
    position: fixed;
  }

  .top-nav {
    top: 12px;
    width: calc(100vw - 32px);
  }

  .nav-wing {
    display: none;
  }
}
</style>
