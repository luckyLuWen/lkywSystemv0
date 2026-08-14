<template>
  <div class="home-dashboard">
    <header class="top-nav-desktop">
      <div class="header-left-actions">
        <div class="toolbar">
          <button
            v-for="item in topMenus"
            :key="item.key"
            type="button"
            class="toolbar-btn"
            :class="{ active: activeMenuKey === item.key }"
            @click="goTo(item)"
          >
            <span class="btn-glow-dot"></span>
            {{ item.label }}
          </button>
        </div>
      </div>
      
      <div class="header-center-title" @click="goTo({ key: 'home', label: '地图大屏', path: '/' })" style="cursor: pointer;">
        <div class="title-bg-wing"></div>
        <div class="title-glow">基于数字孪生的交通事故智能决策与救援推演平台</div>
        <div class="title-bottom-line"></div>
      </div>
      
      <div class="header-right-actions">
        <div class="digital-clock">
          <span class="clock-icon">🕒</span>
          <span class="clock-text">{{ systemTime }}</span>
        </div>
      </div>
    </header>

    <div class="main-layout">

      <main class="center-viewport-container">
        
        <div class="viewport-body">
          <div class="globe-layer">
            <HomeCesiumGlobe
              ref="globeRef"
              :phases="timelinePhases"
               v-model:active-phase-index="activePhaseIndex"
              :focused-point-id="currentFocusedPoint"
              :sensor-data="displaySensorData"
              :is-ws-connected="isWsConnected"
              @accident-picked="onAccidentPickedOnGlobe"
              @models-ready="onModelsReady"
            />
          </div>
          
          <div class="timeline-container" :style="{ bottom: timelineBottom + 'px' }">
            <HomeTimeProgress
              v-model="activePhaseIndex"
              v-model:accident-index="activeAccidentIndex"
              :phases="timelinePhases"
              :accidents="accidentPoints"
              :phases-ready="phasesReady"
              @locate="handleLocate"
              @phase-click="handlePhaseClick"
            />
          </div>
        </div>
      </main>

      <aside class="right-sidebar" :class="{ collapsed: isRightCollapsed }">
        <button class="toggle-btn toggle-btn-right" type="button" @click="isRightCollapsed = !isRightCollapsed">
          {{ isRightCollapsed ? '▶' : '◀' }}
        </button>
        <div v-if="activeRightTab !== 'detection'" class="sidebar-header">
          <div class="header-main-title">
            <div class="header-title-block">
              <h2 class="sidebar-title">
                {{ activeRightTab === 'sensor' ? '传感器数据' : '协同响应 规划数据' }}
              </h2>
              <span class="sidebar-subtitle">
                {{ activeRightTab === 'sensor' ? 'SENSOR DATA GATEWAY' : 'RESCUE COLLABORATIVE PLANNING DATA' }}
              </span>
            </div>
            <span class="lkyw-hud-status-badge">● LIVE</span>
          </div>
        </div>
        <div class="sidebar-content right-sidebar-flex-content">
          <div class="right-tab-panel">
            <div v-if="activeRightTab === 'sensor'" class="sensor-data-panel">
              <div class="sensor-header-row">
                <span class="sensor-section-title">地面移动监测节点情况</span>
                <span class="sensor-source-badge" :class="{ online: isSensorDeployed && isWsConnected }">
                  {{ !isSensorDeployed ? '⚠️ 尚未部署 (断联)' : (isWsConnected ? '📡 网关在线' : '⚠️ 离线模拟') }}
                </span>
              </div>
              
              <div class="ugv-cards-container">
                <div class="ugv-card">
                  <div class="ugv-header">
                    <span class="ugv-title">地面感知单元-001</span>
                    <span class="ugv-status" :class="{ offline: !isSensorDeployed }">{{ isSensorDeployed ? '在线' : '断联' }}</span>
                  </div>
                  <div class="ugv-data">
                    <div class="ugv-row">
                      <div class="ugv-item"><span class="ugv-label">温度</span><span class="ugv-value">{{ isSensorDeployed ? ugvA.temp : '0' }}</span></div>
                      <div class="ugv-item"><span class="ugv-label">湿度</span><span class="ugv-value">{{ isSensorDeployed ? ugvA.hum + '%' : '0%' }}</span></div>
                    </div>
                    <div class="ugv-row">
                      <div class="ugv-item full-width"><span class="ugv-label">烟雾</span><span class="ugv-value">{{ isSensorDeployed ? ugvA.smoke + ' ug' : '0 ug' }}</span></div>
                    </div>
                    <div class="ugv-row">
                      <div class="ugv-item"><span class="ugv-label">TVOC</span><span class="ugv-value">{{ isSensorDeployed ? ugvA.tvoc : '0' }}</span></div>
                      <div class="ugv-item"><span class="ugv-label">CO</span><span class="ugv-value">{{ isSensorDeployed ? ugvA.co : '0' }}</span></div>
                    </div>
                  </div>
                  <div class="ugv-footer" @click="router.push({ path: '/sensor-manage', query: { target: 'node1' } })">点击查看详情 →</div>
                </div>

                <div class="ugv-card">
                  <div class="ugv-header">
                    <span class="ugv-title">地面感知单元-002</span>
                    <span class="ugv-status" :class="{ offline: !isSensorDeployed }">{{ isSensorDeployed ? '在线' : '断联' }}</span>
                  </div>
                  <div class="ugv-data">
                    <div class="ugv-row">
                      <div class="ugv-item"><span class="ugv-label">温度</span><span class="ugv-value">{{ isSensorDeployed ? ugvB.temp : '0' }}</span></div>
                      <div class="ugv-item"><span class="ugv-label">湿度</span><span class="ugv-value">{{ isSensorDeployed ? ugvB.hum + '%' : '0%' }}</span></div>
                    </div>
                    <div class="ugv-row">
                      <div class="ugv-item full-width"><span class="ugv-label">烟雾</span><span class="ugv-value">{{ isSensorDeployed ? ugvB.smoke + ' ug' : '0 ug' }}</span></div>
                    </div>
                    <div class="ugv-row">
                      <div class="ugv-item"><span class="ugv-label">TVOC</span><span class="ugv-value">{{ isSensorDeployed ? ugvB.tvoc : '0' }}</span></div>
                      <div class="ugv-item"><span class="ugv-label">CO</span><span class="ugv-value">{{ isSensorDeployed ? ugvB.co : '0' }}</span></div>
                    </div>
                  </div>
                  <div class="ugv-footer" @click="router.push({ path: '/sensor-manage', query: { target: 'node2' } })">点击查看详情 →</div>
                </div>
              </div>

              <div class="sensor-section-title" style="margin-top: 18px;">固定环境感知情况</div>
              
              <div class="meteorology-card">
                <div class="met-icon">🌬️</div>
                <div class="met-details">
                  <div class="met-row">
                    <span class="met-label">实时风速</span>
                    <span class="met-val">{{ isSensorDeployed ? displaySensorData.windSpeed + ' m/s' : '0 m/s' }}</span>
                  </div>
                  <div class="met-divider"></div>
                  <div class="met-row">
                    <span class="met-label">当前风向</span>
                    <span class="met-val">{{ isSensorDeployed ? displaySensorData.windDirection : '--' }}</span>
                  </div>
                </div>
              </div>

           
              <div class="sensor-section-title" style="margin-top: 18px;">空域监测移动节点情况</div>
                 <div class="capability-panel" style="margin-top: 18px;">
               
              </div>
              <div class="sidebar-uav-gallery" v-if="globeRef && globeRef.capturedPhotos">
                <div class="sidebar-uav-main-photo">
                  <img
                    v-if="globeRef.activePhotoIndex !== null"
                    :src="currentPhotoSrc"
                    :class="['sidebar-uav-img', 'photo-angle-' + globeRef.activePhotoIndex]"
                  />
                  <div class="sidebar-uav-placeholder" v-else>
                    <div class="sidebar-radar"></div>
                    <span>等待无人机到达侦察位置...</span>
                  </div>
                   <div class="cap-group">
                    <div class="cap-title">通信与链路效能</div>
                    <div class="cap-items">
                        <div class="cap-item row-flex">
                          <span class="c-lbl">网络拓扑结构</span>
                          <span class="c-val tag-blue">{{ networkStats.networkType }}</span>
                        </div>
                        <div class="cap-item row-flex">
                          <span class="c-lbl">传感吞吐频率</span>
                          <span class="c-val highlight">{{ networkStats.throughput }}</span>
                        </div>
                    </div>
                  </div>

                  <div class="cap-group">
                    <div class="cap-title">多源感知数据态势</div>
                    <div class="cap-items data-stats">
                      <div class="stat-box">
                        <span class="s-lbl">全量感知维度</span>
                        <span class="s-val">{{ networkStats.sensingDimensions }} <small>项</small></span>
                        <span class="s-desc">温/湿/烟/TVOC/CO/风</span>
                      </div>
                      <div class="stat-box">
                        <span class="s-lbl">累计数据吞吐量</span>
                        <span class="s-val">{{ totalPackets }} <small>包</small></span>
                        <span class="s-desc">边缘端实时解析</span>
                      </div>
                    </div>
                  </div>
                  <div class="sidebar-uav-overlay" v-if="globeRef.activePhotoIndex !== null">
                    <span class="timestamp">{{ globeRef.currentTimeStr }}</span>
                    <span class="coords">
                      {{ currentAccidentId === 'rear-end' ? '113.1048°E, 30.3855°N' : '114.8933°E, 30.6317°N' }}
                    </span>
                  </div>
                </div>
                <div class="sidebar-uav-thumbs">
                  <div
                    v-for="i in [0, 1, 2, 3]"
                    :key="i"
                    class="sidebar-thumb-box"
                    :class="{
                      'is-captured': globeRef.capturedPhotos[i],
                      'is-active': globeRef.activePhotoIndex === i
                    }"
                    @click="globeRef.capturedPhotos[i] ? globeRef.activePhotoIndex = i : null"
                  >
                    <div class="thumb-inner" v-if="globeRef.capturedPhotos[i]">
                      <img
                        :src="currentPhotoSrc"
                        :class="['sidebar-thumb-img', 'photo-angle-' + i]"
                      />
                      <div class="thumb-badge">角 {{ i+1 }}</div>
                    </div>
                    <div class="thumb-lock" v-else>🔒</div>
                  </div>
                </div>
              </div>

              <div v-else class="sidebar-uav-no-ref">
                <p>正在初始化三维引擎...</p>
              </div>
              <div class="capability-panel" style="margin-top:18px;">

  <div class="panel-header">
    <h3>感知网络与组网资源效能</h3>
  </div>


  <div class="capability-grid">


    <!-- 组网实体资源状态 -->
    <div class="cap-group">
      <div class="cap-title">
        组网实体资源状态
      </div>

      <div class="cap-items">

        <div class="cap-item icon-item">
          <span class="cap-icon">🚙</span>

          <div class="cap-info">

            <div>
              地面机动节点 (UGV)
            </div>

            <div class="sub-status-row">

              <span :class="['mini-status',
              resourceStatus.ugv1?'on':'off']">

                地面感知单元-001:
                {{resourceStatus.ugv1?'在线':'离线'}}

              </span>


              <span :class="['mini-status',
              resourceStatus.ugv2?'on':'off']">

                地面感知单元-002:
                {{resourceStatus.ugv2?'在线':'离线'}}

              </span>

            </div>

          </div>
        </div>



        <div class="cap-item icon-item">

          <span class="cap-icon">
            🚁
          </span>

          <div>

            空中感知侦查(UAV)

            <div class="sub-status-row">

              <span :class="['mini-status',
              resourceStatus.uav?'on':'off']">

                广角图传:
                {{resourceStatus.uav?'信号正常':'信号断开'}}

              </span>

            </div>

          </div>

        </div>



        <div class="cap-item icon-item">

          <span class="cap-icon">
            🗼
          </span>

          <div>

            气象基准站

            <div class="sub-status-row">

              <span :class="['mini-status',
              resourceStatus.weather?'on':'off']">

                风速风向监测:
                {{resourceStatus.weather?'在线':'离线'}}

              </span>

            </div>

          </div>

        </div>


      </div>

    </div>



    <!-- 通信链路 -->
    <div class="cap-group">

      <div class="cap-title">
        通信与链路效能
      </div>


      <div class="cap-item row-flex">

        <span>
          网络拓扑结构
        </span>

        <span class="c-val tag-blue">
          {{networkStats.networkType}}
        </span>

      </div>

      <div class="cap-item row-flex">

        <span>
          传感吞吐频率
        </span>


        <span class="highlight">

          {{networkStats.throughput}}

        </span>

      </div>


    </div>




    <!-- 数据态势 -->
    <div class="cap-group">

      <div class="cap-title">
        多源感知数据态势
      </div>


      <div class="data-stats">

        <div class="stat-box">

          <span>
            全量感知维度
          </span>


          <span class="s-val">

            {{networkStats.sensingDimensions}}
            项

          </span>

          <span>
            温/湿/烟/TVOC/CO/风
          </span>


        </div>



        <div class="stat-box">

          <span>
            累计数据吞吐量
          </span>


          <span class="s-val">

            {{totalPackets}}
            包

          </span>


          <span>
            边缘端实时解析
          </span>


        </div>


      </div>

    </div>


  </div>

</div>
            </div>

            <div v-else-if="activeRightTab === 'detection'" class="detection-data-panel">
              <RealtimeDetectionCard :key="currentDetectionScenario" :scenario="currentDetectionScenario" />
            </div>

            <div v-else-if="activeRightTab === 'planning'" class="planning-data-panel">
              <CollaborativeResponseCard :scenario="currentAccidentId === 'rear-end' ? 'crash' : 'leak'" />
            </div>
          </div>
        </div>
        <div class="right-sidebar-footer-tabs">
          <button 
            type="button" 
            class="right-tab-btn" 
            :class="{ active: activeRightTab === 'sensor' }"
            @click="activeRightTab = 'sensor'"
          >
            <span class="tab-icon">📡</span>
            <span class="tab-text">传感器数据</span>
          </button>
          <button 
            type="button" 
            class="right-tab-btn" 
            :class="{ active: activeRightTab === 'detection' }"
            @click="activeRightTab = 'detection'"
          >
            <span class="tab-icon">🔍</span>
            <span class="tab-text">检测数据</span>
          </button>
          <button 
            type="button" 
            class="right-tab-btn" 
            :class="{ active: activeRightTab === 'planning' }"
            @click="activeRightTab = 'planning'"
          >
            <span class="tab-icon">📋</span>
            <span class="tab-text">规划数据</span>
          </button>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed, nextTick, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import CollaborativeResponseCard from '../components/CollaborativeResponseCard.vue'
import RealtimeDetectionCard from '../components/RealtimeDetectionCard.vue'
import SensorGatewayCard from '../components/SensorGatewayCard.vue'
import IntegrationEventMonitor from '../components/IntegrationEventMonitor.vue'
import HomeCesiumGlobe from '../components/home/HomeCesiumGlobe.vue'
import HomeTimeProgress from '../components/home/HomeTimeProgress.vue'
import { getSensorGatewayBaseUrl } from '../config/subsystems'

const router = useRouter()
const route = useRoute()
const activeServiceId = ref('')
const activeMenuKey = ref('')
const globeRef = ref(null)

// --- 新增：感知网络效能面板响应式数据 ---
// --- 动态感知资源状态 ---
const resourceStatus = computed(() => {
  // 如果 WebSocket 断开，全部判定为离线 (或根据你的需求调整)
  if (!isWsConnected.value || !wsData.value) {
    return { ugv1: false, ugv2: false, uav: false, weather: false }
  }

  // 假设 wsData 中包含这些节点的在线状态字段
  // 如果后台推送的数据里没有直接的在线字段，可以根据是否存在数据来判断
  const data = wsData.value
  return {
    ugv1: !!data.node1,        // 存在 node1 数据则为在线
    ugv2: !!data.node2,        // 存在 node2 数据则为在线
    uav: !!data.uav_link,      // 假设有 uav_link 字段
    weather: !!data.node3      // 假设 node3 是气象站
  }
})

const networkStats = reactive({
  networkType: '异构多链路直连',
  alivePercent: 100,
  aliveRatio: '4/4',
  throughput: '1Hz ',
  sensingDimensions: 7
})

const totalPackets = ref(125430)
let packetTimer = null
// ------------------------------------

const currentPhotoSrc = computed(() => {
  return currentAccidentId.value === 'rear-end' 
    ? '/Dashboard/images/uav_aerial_photo.png' 
    : '/Dashboard/images/tanker_aerial_photo.png'
})

const sensorData = ref({
  temp: 24.5,
  humidity: 52.0,
  smoke: 0.02,
  co: 1.2,
  tvoc: 0.15,
  windSpeed: 3.2,
  windDirection: '东北风'
})

let sensorInterval = null

const wsData = ref(null)
const isWsConnected = ref(false)
let socket = null
let reconnectTimer = null

let wsReconnectAttempts = 0
const MAX_WS_RECONNECT_ATTEMPTS = 2

function connectWS() {
  if (wsReconnectAttempts >= MAX_WS_RECONNECT_ATTEMPTS) {
    return
  }
  if (socket) {
    try {
      socket.onopen = null
      socket.onmessage = null
      socket.onclose = null
      socket.onerror = null
      socket.close()
    } catch(e){}
  }
  try {
    const base = getSensorGatewayBaseUrl()
    const wsUrl = base.replace(/^http/i, 'ws') + '/ws'
    socket = new WebSocket(wsUrl)
    
    socket.onopen = () => {
      isWsConnected.value = true
      wsReconnectAttempts = 0
    }
    
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        if (parsed && (parsed.node1 || parsed.node3)) {
          wsData.value = parsed
        }
      } catch (e) {}
    }
    
    socket.onclose = () => {
      isWsConnected.value = false
      wsReconnectAttempts++
      if (wsReconnectAttempts < MAX_WS_RECONNECT_ATTEMPTS) {
        reconnectTimer = setTimeout(connectWS, 10000)
      }
    }
    
    socket.onerror = () => {
      isWsConnected.value = false
    }
  } catch (e) {
    isWsConnected.value = false
  }
}

const displaySensorData = computed(() => {
  if (isWsConnected.value && wsData.value) {
    const n1 = wsData.value.node1 || {}
    const n3 = wsData.value.node3 || {}
    return {
      temp: n1.temp !== undefined ? n1.temp : 24.5,
      humidity: n1.hum !== undefined ? n1.hum : 52.0,
      smoke: n1.smoke !== undefined ? (n1.smoke / 1000).toFixed(2) : 0.02,
      co: n1.co !== undefined ? n1.co : 1.2,
      tvoc: n1.tvoc !== undefined ? n1.tvoc : 0.15,
      windSpeed: n3.wind !== undefined ? n3.wind : 3.2,
      windDirection: n3.wind_dir || '东北风'
    }
  } else {
    return sensorData.value
  }
})

const ugvA = computed(() => {
  const data = displaySensorData.value;
  return {
    temp: data.temp || 0,
    hum: data.humidity || 0,
    smoke: Math.floor((data.smoke || 0) * 1000),
    tvoc: data.tvoc || 0,
    co: data.co || 0,
  }
})

const ugvB = computed(() => {
  return {
    temp: +(ugvA.value.temp - 0.45).toFixed(2),
    hum: +(ugvA.value.hum - 2.12).toFixed(2),
    smoke: Math.max(0, Math.floor(ugvA.value.smoke * 0.95)),
    tvoc: Math.max(0, +(ugvA.value.tvoc * 0.88).toFixed(3)),
    co: Math.max(0, +(ugvA.value.co * 0.92).toFixed(1)),
  }
})

const systemTime = ref('')
let timeInterval = null

const isLeftCollapsed = ref(false)
const isRightCollapsed = ref(false)

const activeAccidentIndex = ref(0)
const currentFocusedPoint = ref('')
const modelsReadyStatus = ref({})
const timelineBottom = ref(18)
const activeRightTab = ref('sensor')

const accidentPhaseIndices = ref({
  'rear-end': -1,
  'leakage': -1
})

const currentAccidentId = computed(() => {
  return accidentPoints[activeAccidentIndex.value]?.id || ''
})

const currentDetectionScenario = computed(() => {
  return currentAccidentId.value === 'rear-end' ? 'crash' : 'leak'
})

const activePhaseIndex = computed({
  get: () => accidentPhaseIndices.value[currentAccidentId.value] || 0,
  set: (val) => {
    accidentPhaseIndices.value[currentAccidentId.value] = val
  }
})

const isSensorDeployed = computed(() => {
  return activePhaseIndex.value >= 2
})

const topMenus = [
  { key: 'home', label: '地图大屏', path: '/' },
  { key: 'sensor', label: '感知组网', path: '/sensor-manage' },
  { key: 'realtime', label: '实时检测', path: '/realtime' },
  { key: 'coordination', label: '协同响应', path: '/coordination' },
  { key: 'modeling', label: '精细建模', path: '/modeling' },
  { key: 'simulation', label: '仿真推演', path: '/simulation' },
]

const accidentPoints = [
  {
    id: 'rear-end',
    title: '客车追尾现场',
    focusPoint: 'accident_blue',
    phases: [
      { id: 't-start', time: '14:00', shortLabel: '仿真开始', title: '仿真推演开始', systems: ['总系统首页'], focusPoint: 'accident_blue' },
      { id: 't-normal', time: '14:05', shortLabel: '正常行驶', title: '车辆正常行驶阶段', systems: ['边缘网关'], focusPoint: 'accident_blue' },
      { id: 't-accident', time: '14:12', shortLabel: '事故发生', title: '客车追尾事故瞬间', systems: ['实时检测'], focusPoint: 'detection' },
      { id: 't-uav-dispatch', time: '14:14', shortLabel: '无人机出动', title: '无人机出动', systems: ['协同响应'], focusPoint: 'accident_blue' },
      { id: 't-uav-recon', time: '14:15', shortLabel: '无人机侦察', title: '无人机快速出动侦察', systems: ['协同响应'], focusPoint: 'accident_blue' },
      { id: 't-smoke', time: '14:18', shortLabel: '次生灾害（烟雾）', title: '事故现场产生大量烟雾', systems: ['协同响应'], focusPoint: 'accident_blue' },
      { id: 't-fire', time: '14:26', shortLabel: '次生灾害（起火）', title: '事故车辆开始起火', systems: ['实时检测', '协同响应'], focusPoint: 'accident_blue' },
      { id: 't-uav-start', time: '14:30', shortLabel: '无人装备出动', title: '无人装备协同出动', systems: ['协同响应'], focusPoint: 'accident_blue' },
      { id: 't-uav-deploy', time: '14:35', shortLabel: '无人感知部署', title: '无人感知节点部署', systems: ['实时检测'], focusPoint: 'accident_blue' },
      { id: 't-uav-exec', time: '14:40', shortLabel: '无人感知执行', title: '无人感知任务执行', systems: ['协同响应'], focusPoint: 'accident_blue' },
      { id: 't-signal', time: '14:45', shortLabel: '信号干扰', title: '通信信号受到干扰', systems: ['协同响应'], focusPoint: 'accident_blue' },
      { id: 't-rescue-start', time: '14:50', shortLabel: '救援装备出动', title: '专业救援装备协同出动', systems: ['协同响应'], focusPoint: 'accident_blue' },
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
      { id: 'l-uav-dispatch', time: '15:14', shortLabel: '无人机出动', title: '无人机出动', systems: ['协同响应'], focusPoint: 'accident_red' },
      { id: 'l-uav-recon', time: '15:15', shortLabel: '无人机侦察', title: '无人机快速出动侦察', systems: ['协同响应'], focusPoint: 'accident_red' },
      { id: 'l-leak', time: '15:20', shortLabel: '次生灾害（泄露）', title: '罐体受损开始发生化学品泄露', systems: ['实时检测', '协同响应'], focusPoint: 'accident_red' },
      { id: 'l-fill', time: '15:35', shortLabel: '次生灾害（弥漫）', title: '泄露液体开始向四周大面积弥漫', systems: ['协同响应'], focusPoint: 'accident_red' },
      { id: 'l-uav-start', time: '15:40', shortLabel: '无人装备出动', title: '无人装备协同出动', systems: ['协同响应'], focusPoint: 'accident_red' },
      { id: 'l-uav-deploy', time: '15:45', shortLabel: '无人感知部署', title: '无人感知节点部署', systems: ['实时检测'], focusPoint: 'accident_red' },
      { id: 'l-uav-exec', time: '15:50', shortLabel: '无人感知执行', title: '无人感知任务执行', systems: ['协同响应'], focusPoint: 'accident_red' },
      { id: 'l-signal', time: '15:55', shortLabel: '信号干扰', title: '通信信号受到干扰', systems: ['协同响应'], focusPoint: 'accident_red' },
      { id: 'l-rescue-start', time: '16:00', shortLabel: '救援装备出动', title: '专业救援装备协同出动', systems: ['协同响应'], focusPoint: 'accident_red' },
    ]
  },
]

const timelinePhases = computed(() => {
  return accidentPoints[activeAccidentIndex.value]?.phases || []
})

const phaseToModelMap = {
  1: 'model_normal', 2: 'model_accident', 3: 'model_accident', 4: 'model_accident', 5: 'model_accident', 
  6: 'model_accident', 7: 'model_accident', 8: 'model_accident', 9: 'model_accident', 10: 'model_accident', 11: 'model_accident'
}

const tankerPhaseToModelMap = {
  1: 'tanker_normal', 2: 'tanker_accident', 3: 'tanker_accident', 4: 'tanker_accident', 5: 'tanker_accident', 
  6: 'tanker_accident', 7: 'tanker_accident', 8: 'tanker_accident', 9: 'tanker_accident', 10: 'tanker_accident', 11: 'tanker_accident'
}

const phasesReady = computed(() => {
  if (timelinePhases.value.length === 0) return []
  const isTruck = timelinePhases.value[0]?.id.startsWith('t-')
  const map = isTruck ? phaseToModelMap : tankerPhaseToModelMap
  return timelinePhases.value.map((p, idx) => {
    const mid = map[idx]
    if (!mid) return true
    return !!modelsReadyStatus.value[mid]
  })
})

function goTo(item) {
  if (item.path === '/') {
    if (globeRef.value) globeRef.value.resetView()
    currentFocusedPoint.value = ''
    activeServiceId.value = ''
    accidentPhaseIndices.value = { 'rear-end': -1, 'leakage': -1 }
  }
  activeMenuKey.value = item.key
  router.push(item.path)
}

function onAccidentPickedOnGlobe(entityId) {
  const index = accidentPoints.findIndex((acc) => acc.focusPoint === entityId)
  if (index !== -1) {
    currentFocusedPoint.value = entityId
    activeAccidentIndex.value = index
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
function onModelsReady(status) { modelsReadyStatus.value = status }

onMounted(() => {
  connectWS()
  systemTime.value = new Date().toLocaleString()
  timeInterval = setInterval(() => { systemTime.value = new Date().toLocaleString() }, 1000)
  
  // 模拟数据包增加逻辑
  packetTimer = setInterval(() => {
    if (isSensorDeployed.value && isWsConnected.value) {
      totalPackets.value += Math.floor(Math.random() * 3) + 2
    }
  }, 500)

  sensorInterval = setInterval(() => {
    const isCrisis = activePhaseIndex.value >= 3
    sensorData.value.temp = +(24.5 + (Math.random() - 0.5) * 0.4).toFixed(1)
    sensorData.value.smoke = +( (isCrisis ? 0.35 : 0.02) + (Math.random() - 0.5) * 0.04).toFixed(2)
    // ...其余模拟数据保持不变
  }, 3000)

  activeMenuKey.value = 'home'

  // 初始化时检查 URL 路由参数
  const queryScene = route.query.scene
  const queryPhaseIndex = route.query.phaseIndex !== undefined ? parseInt(route.query.phaseIndex, 10) : null

  if (queryScene && queryPhaseIndex !== null) {
    const idx = accidentPoints.findIndex(acc => acc.id === queryScene)
    if (idx !== -1) {
      activeAccidentIndex.value = idx
    }
    accidentPhaseIndices.value = {
      'rear-end': queryScene === 'rear-end' ? queryPhaseIndex : 0,
      'leakage': queryScene === 'leakage' ? queryPhaseIndex : 0
    }
    const currentAcc = accidentPoints[activeAccidentIndex.value]
    if (currentAcc && currentAcc.phases[queryPhaseIndex]) {
      currentFocusedPoint.value = currentAcc.phases[queryPhaseIndex].focusPoint || currentAcc.focusPoint
    }

    // 清除 URL 中的查询参数，避免刷新页面时再次加载指定阶段
    try {
      window.history.replaceState(null, '', window.location.pathname)
    } catch (e) {
      console.warn('Failed to clear URL query parameters:', e)
    }
  }
})

onBeforeUnmount(() => {
  clearInterval(sensorInterval)
  clearInterval(timeInterval)
  clearInterval(packetTimer)
  if (socket) socket.close()
})

watch(activeAccidentIndex, () => { currentFocusedPoint.value = '' })

watch(
  () => route.fullPath,
  () => {
    if (route.path === '/') {
      activeMenuKey.value = 'home'
      activeServiceId.value = ''

      const queryScene = route.query.scene
      const queryPhaseIndex = route.query.phaseIndex !== undefined ? parseInt(route.query.phaseIndex, 10) : null

      if (queryScene && queryPhaseIndex !== null) {
        // 设置指定场景索引与阶段索引
        const idx = accidentPoints.findIndex(acc => acc.id === queryScene)
        if (idx !== -1) {
          activeAccidentIndex.value = idx
        }
        
        accidentPhaseIndices.value = {
          'rear-end': queryScene === 'rear-end' ? queryPhaseIndex : 0,
          'leakage': queryScene === 'leakage' ? queryPhaseIndex : 0
        }

        const currentAcc = accidentPoints[activeAccidentIndex.value]
        if (currentAcc && currentAcc.phases[queryPhaseIndex]) {
          currentFocusedPoint.value = currentAcc.phases[queryPhaseIndex].focusPoint || currentAcc.focusPoint
        }

        // 清除 URL 中的查询参数，避免刷新页面时再次加载指定阶段
        try {
          window.history.replaceState(null, '', window.location.pathname)
        } catch (e) {
          console.warn('Failed to clear URL query parameters:', e)
        }
      } else {
        // 重置所有事故时间线
        accidentPhaseIndices.value = {
          'rear-end': 0,
          'leakage': 0
        }
        // 清除当前聚焦点
        currentFocusedPoint.value = ''

        // Cesium恢复默认视角
        if (globeRef.value) {
          globeRef.value.resetView()
        }
      }
    }
  }
)

function handlePhaseClick(idx) {
  if (globeRef.value && typeof globeRef.value.triggerPhaseReplay === 'function') {
    globeRef.value.triggerPhaseReplay(idx)
  }
}
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
  min-height: 0;
  width: 100%;
  overflow: hidden;
  position: relative;
}

/* Top Nav Desktop (Menu bar + Toolbar) Overhaul */
.top-nav-desktop {
  background: linear-gradient(180deg, rgba(6, 16, 32, 0.98) 0%, rgba(4, 12, 24, 0.90) 100%);
  border-bottom: 1px solid rgba(0, 240, 255, 0.35);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 240, 255, 0.15);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 84px;
  user-select: none;
  z-index: 100;
  position: relative;
  overflow: hidden;
}

/* 顶部流光扫描光轨效果 */
.top-nav-desktop::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 60%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00F0FF, transparent);
  animation: topScanLine 6s linear infinite;
  opacity: 0.8;
}

@keyframes topScanLine {
  0% { left: -60%; }
  100% { left: 140%; }
}

.header-logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-logo-icon {
  font-size: 20px;
  filter: drop-shadow(0 0 8px #00f2fe);
}

.header-logo-text {
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
  background: linear-gradient(180deg, #ffffff 0%, #a5b4fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-logo-sub {
  font-size: 10px;
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid rgba(0, 242, 254, 0.2);
  padding: 1px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.header-center-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  pointer-events: auto;
}

.title-glow {
  font-size: 27px;
  font-weight: 800;
  color: #00f2fe;
  text-shadow: 0 0 12px rgba(0, 242, 254, 0.65), 0 0 4px rgba(0, 242, 254, 0.8);
  letter-spacing: 3px;
  font-family: "Microsoft YaHei", sans-serif;
  position: relative;
}

/* Brackets decoration for center title */
.title-glow::before {
  content: '[';
  margin-right: 8px;
  color: rgba(0, 242, 254, 0.5);
}
.title-glow::after {
  content: ']';
  margin-left: 8px;
  color: rgba(0, 242, 254, 0.5);
}

.header-left-actions,
.header-right-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-btn {
  padding: 9px 20px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.05);
  color: #cbd5e1;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.toolbar-btn:hover {
  background: rgba(0, 242, 254, 0.1);
  border-color: rgba(0, 242, 254, 0.4);
  color: #00f2fe;
  box-shadow: 0 0 8px rgba(0, 242, 254, 0.2);
}

.toolbar-btn.active {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.2) 0%, rgba(37, 99, 235, 0.2) 100%);
  border-color: #00f2fe;
  color: #00f2fe;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.35);
  text-shadow: 0 0 4px rgba(0, 242, 254, 0.5);
}

.digital-clock {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  color: #94a3b8;
  background: rgba(0, 0, 0, 0.3);
  padding: 8px 18px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-family: monospace;
}

.clock-icon {
  color: #00f2fe;
}

/* Left & Right Sidebars Overhaul */
.left-sidebar,
.right-sidebar {
  width: 500px;
  height: calc(100% - 32px);
  background: rgba(10, 19, 35, 0.82);
  backdrop-filter: blur(20px) saturate(140%);
  display: flex;
  flex-direction: column;
  overflow: visible;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6), inset 0 0 15px rgba(0, 242, 254, 0.08);
  border: 1px solid rgba(0, 242, 254, 0.22);
  border-radius: 14px;
  position: absolute;
  top: 16px;
  bottom: 16px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.left-sidebar {
  right: 16px;
  z-index: 10;
}

.left-sidebar.collapsed {
  transform: translateX(calc(100% + 20px));
}

.right-sidebar {
  left: 16px;
  z-index: 10;
}

.right-sidebar.collapsed {
  transform: translateX(calc(-100% - 20px));
}

/* 侧边栏顶部/底部 4 角战术边角 */
.left-sidebar::before,
.right-sidebar::before {
  content: '';
  position: absolute;
  top: -1px;
  left: -1px;
  width: 12px;
  height: 12px;
  border-top: 2px solid #00F0FF;
  border-left: 2px solid #00F0FF;
  border-radius: 4px 0 0 0;
  pointer-events: none;
  box-shadow: -2px -2px 8px rgba(0, 240, 255, 0.6);
  z-index: 12;
}

.left-sidebar::after,
.right-sidebar::after {
  content: '';
  position: absolute;
  bottom: -1px;
  right: -1px;
  width: 12px;
  height: 12px;
  border-bottom: 2px solid #00F0FF;
  border-right: 2px solid #00F0FF;
  border-radius: 0 0 4px 0;
  pointer-events: none;
  box-shadow: 2px 2px 8px rgba(0, 240, 255, 0.6);
  z-index: 12;
}

/* Sidebar Toggle Buttons - High Tech Glass */
.toggle-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 60px;
  background: rgba(10, 19, 35, 0.9);
  border: 1px solid rgba(0, 242, 254, 0.3);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #00f2fe;
  font-size: 10px;
  transition: all 0.2s;
  z-index: 11;
  padding: 0;
}
.toggle-btn:hover {
  color: #ffffff;
  background: rgba(0, 242, 254, 0.2);
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
}
.toggle-btn-left {
  left: -18px;
  border-radius: 8px 0 0 8px;
  border-right: none;
}
.toggle-btn-right {
  right: -18px;
  border-radius: 0 8px 8px 0;
  border-left: none;
}

.sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 242, 254, 0.15);
  background: rgba(0, 0, 0, 0.25);
  border-radius: 12px 12px 0 0;
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header::before {
  content: '';
  position: absolute;
  left: 0;
  top: 18px;
  bottom: 18px;
  width: 4px;
  background: #00f2fe;
  border-radius: 0 4px 4px 0;
  box-shadow: 0 0 8px rgba(0, 242, 254, 0.7);
}

.header-main-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 8px;
}

.header-title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.sidebar-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
  font-family: "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.sidebar-subtitle {
  font-size: 16px;
  color: #00f2fe;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: inline-block;
  margin-top: 3px;
  opacity: 0.85;
  font-family: "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.right-sidebar .lkyw-hud-status-badge,
.left-sidebar .lkyw-hud-status-badge {
  font-size: 15px;
  font-family: monospace;
  font-weight: bold;
  color: #00ffaa;
  background: rgba(0, 255, 170, 0.12);
  border: 1px solid rgba(0, 255, 170, 0.35);
  padding: 4px 14px;
  border-radius: 4px;
  white-space: nowrap;
  letter-spacing: 0.5px;
  box-shadow: 0 0 8px rgba(0, 255, 170, 0.2);
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

/* Accordion Items - High Tech Dark Theme */
.accordion-item-light {
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.45);
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.accordion-item-light.open {
  box-shadow: 0 4px 16px rgba(0, 242, 254, 0.15);
  border-color: rgba(0, 242, 254, 0.4);
  background: rgba(15, 23, 42, 0.7);
}

.accordion-trigger-light {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: none;
  background: rgba(10, 19, 35, 0.6);
  cursor: pointer;
  text-align: left;
  border-bottom: 1px solid transparent;
  transition: all 0.2s;
}

.accordion-trigger-light:hover {
  background: rgba(0, 242, 254, 0.08);
}

.accordion-item-light.open .accordion-trigger-light {
  border-bottom-color: rgba(0, 242, 254, 0.15);
  background: rgba(0, 242, 254, 0.05);
}

.trigger-kicker {
  font-size: 11px;
  color: #00f2fe;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-shadow: 0 0 4px rgba(0, 242, 254, 0.3);
}

.trigger-title {
  margin: 4px 0 0;
  font-size: 17px;
  font-weight: 700;
  color: #ffffff;
}

.trigger-indicator {
  font-size: 13px;
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.1);
  padding: 5px 12px;
  border-radius: 6px;
  border: 1px solid rgba(0, 242, 254, 0.25);
  font-weight: 600;
  transition: all 0.2s;
}

.trigger-indicator:hover {
  background: rgba(0, 242, 254, 0.2);
  border-color: rgba(0, 242, 254, 0.5);
  box-shadow: 0 0 8px rgba(0, 242, 254, 0.3);
}

.accordion-body-light {
  padding: 14px;
  background: transparent;
}

/* Deep overrides to skin inner cards into gorgeous high-tech dark mode */
.left-sidebar :deep(.collaborative-response-card),
.left-sidebar :deep(.sensor-gateway-card) {
  background: rgba(2, 12, 26, 0.6) !important;
  color: #e2e8f0 !important;
  border: 1px solid rgba(0, 242, 254, 0.15) !important;
  box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.05) !important;
  padding: 12px !important;
  border-radius: 8px !important;
}

.left-sidebar :deep(.card-title),
.right-sidebar :deep(.card-title) {
  color: #ffffff !important;
  font-size: 22px !important;
  font-weight: 700 !important;
  text-shadow: 0 0 6px rgba(0, 242, 254, 0.3);
}

.left-sidebar :deep(.card-subtitle),
.left-sidebar :deep(.tip-text) {
  color: #94a3b8 !important;
}

.left-sidebar :deep(.config-input),
.left-sidebar :deep(.gateway-input) {
  background: rgba(0, 0, 0, 0.4) !important;
  color: #ffffff !important;
  border: 1px solid rgba(0, 242, 254, 0.3) !important;
}

.left-sidebar :deep(.config-input:focus),
.left-sidebar :deep(.gateway-input:focus) {
  border-color: #00f2fe !important;
  box-shadow: 0 0 8px rgba(0, 242, 254, 0.3) !important;
}

.left-sidebar :deep(.status-item),
.left-sidebar :deep(.service-row) {
  background: rgba(10, 19, 35, 0.7) !important;
  border: 1px solid rgba(0, 242, 254, 0.12) !important;
}

.left-sidebar :deep(.status-label),
.left-sidebar :deep(.service-label) {
  color: #94a3b8 !important;
}

.left-sidebar :deep(.status-badge.online),
.left-sidebar :deep(.node-chip.online),
.left-sidebar :deep(.status-value.ok) {
  color: #67f7b2 !important;
  background: rgba(28, 140, 96, 0.25) !important;
  border-color: rgba(103, 247, 178, 0.3) !important;
}

.left-sidebar :deep(.status-badge.offline),
.left-sidebar :deep(.node-chip.offline),
.left-sidebar :deep(.status-value.warn) {
  color: #ff8f8f !important;
  background: rgba(160, 40, 40, 0.2) !important;
  border-color: rgba(255, 143, 143, 0.3) !important;
}

.left-sidebar :deep(.action-btn.secondary) {
  color: #00f2fe !important;
  background: rgba(0, 242, 254, 0.1) !important;
  border-color: rgba(0, 242, 254, 0.25) !important;
}

.left-sidebar :deep(.action-btn.secondary:hover) {
  background: rgba(0, 242, 254, 0.2) !important;
  border-color: #00f2fe !important;
  box-shadow: 0 0 8px rgba(0, 242, 254, 0.3) !important;
}

.left-sidebar :deep(.action-btn.primary) {
  color: #09101f !important;
  background: linear-gradient(90deg, #00f2fe 0%, #38bdf8 100%) !important;
  font-weight: 700 !important;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.3) !important;
}

.left-sidebar :deep(.action-btn.primary:hover) {
  box-shadow: 0 0 15px rgba(0, 242, 254, 0.5) !important;
}

.left-sidebar :deep(.action-btn.ghost) {
  color: #cbd5e1 !important;
  background: rgba(255, 255, 255, 0.05) !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
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
  height: calc(100% - 38px);
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
  background: transparent;
  border: none;
  padding: 0;
  z-index: 20;
  pointer-events: none;
  overflow: visible;
}
.timeline-container > * {
  pointer-events: auto;
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

/* 右边栏最下边的切换栏样式 */
.right-sidebar-footer-tabs {
  display: flex;
  height: 64px;
  background: rgba(8, 16, 28, 0.95);
  border-top: 1px solid rgba(0, 242, 254, 0.25);
  border-radius: 0 0 14px 14px;
  overflow: hidden;
  padding: 5px;
  gap: 5px;
}

.right-tab-btn {
  flex: 1;
  border: 1px solid transparent;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  cursor: pointer;
  color: #94a3b8;
  font-family: inherit;
  border-radius: 6px;
  transition: all 0.25s ease;
  padding: 6px 0;
}

.right-tab-btn:hover {
  background: rgba(0, 242, 254, 0.08);
  color: #00f2fe;
}

.right-tab-btn.active {
  background: linear-gradient(180deg, rgba(0, 242, 254, 0.15) 0%, rgba(37, 99, 235, 0.15) 100%);
  color: #00f2fe;
  box-shadow: inset 0 0 8px rgba(0, 242, 254, 0.15);
  border-color: rgba(0, 242, 254, 0.4);
}

.right-tab-btn .tab-icon {
  font-size: 18px;
}

.right-tab-btn .tab-text {
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.right-tab-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 实时环境数据面板样式 */
.sensor-data-panel,
.detection-data-panel,
.planning-data-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: tabFadeIn 0.3s ease-out;
}

@keyframes tabFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.sensor-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.sensor-source-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  color: #94a3b8;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.sensor-source-badge.online {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border-color: rgba(16, 185, 129, 0.35);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.25);
}

.sensor-section-title {
  font-size: 17.5px;
  font-weight: 700;
  color: #ffffff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-left: 3px solid #00f2fe;
  padding-left: 8px;
  margin: 4px 0 8px;
}

.sensor-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.sensor-card-item {
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(0, 242, 254, 0.12);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
  transition: all 0.25s ease;
}

.sensor-card-item:hover {
  transform: translateY(-2px);
  border-color: rgba(0, 242, 254, 0.35);
  box-shadow: 0 4px 15px rgba(0, 242, 254, 0.15);
}

.sensor-card-item .card-icon {
  font-size: 20px;
  opacity: 0.95;
  filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.2));
}

.sensor-card-item .card-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sensor-card-item .sensor-name {
  font-size: 14.5px;
  color: #94a3b8;
  font-weight: 600;
}

.sensor-card-item .sensor-val {
  font-size: 26px;
  color: #ffffff;
  font-weight: 700;
  font-family: monospace;
  text-shadow: 0 0 4px rgba(255, 255, 255, 0.2);
}

.sensor-card-item .unit {
  font-size: 16px;
  color: #00f2fe;
  font-weight: bold;
}

/* 传感器状态小圆点与脉冲动画 */
.sensor-status-dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.pulse-green {
  background-color: #10b981;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  animation: pulseGreen 2s infinite;
}

.pulse-red {
  background-color: #ef4444;
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  animation: pulseRed 2s infinite;
}

@keyframes pulseGreen {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 4px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

@keyframes pulseRed {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 4px rgba(239, 68, 68, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

/* 局部气象卡片 */
.meteorology-card {
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.05);
}

.meteorology-card .met-icon {
  font-size: 26px;
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid rgba(0, 242, 254, 0.25);
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-shadow: 0 0 5px #00f2fe;
}

.meteorology-card .met-details {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meteorology-card .met-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meteorology-card .met-label {
  font-size: 14.5px;
  color: #94a3b8;
  font-weight: 600;
}

.meteorology-card .met-val {
  font-size: 18px;
  color: #ffffff;
  font-weight: 700;
  text-shadow: 0 0 4px rgba(0, 242, 254, 0.3);
}

.meteorology-card .met-divider {
  width: 1px;
  height: 24px;
  background: rgba(0, 242, 254, 0.2);
}

/* 右边栏无人机图片展示 */
.sidebar-uav-gallery {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(15, 23, 42, 0.6);
  padding: 8px;
  border-radius: 8px;
  border: 1px solid rgba(0, 242, 254, 0.2);
}

.sidebar-uav-main-photo {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: #09101f;
  border-radius: 4px;
  border: 1px solid rgba(0, 242, 254, 0.15);
  overflow: hidden;
}

.sidebar-uav-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-uav-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: rgba(0, 242, 254, 0.5);
  font-size: 11px;
  gap: 8px;
}

.sidebar-radar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px dashed #00f2fe;
  animation: spin 3s linear infinite;
  box-shadow: 0 0 8px rgba(0, 242, 254, 0.3);
}

.sidebar-uav-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(10, 19, 35, 0.95), transparent);
  padding: 4px 8px;
  display: flex;
  justify-content: space-between;
  color: #00f2fe;
  font-family: monospace;
  font-size: 9px;
  border-top: 1px solid rgba(0, 242, 254, 0.1);
}

.sidebar-uav-thumbs {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
}

.sidebar-thumb-box {
  flex: 1;
  aspect-ratio: 16 / 10;
  border: 1px dashed rgba(0, 242, 254, 0.25);
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.3);
  overflow: hidden;
  position: relative;
  cursor: not-allowed;
  transition: all 0.2s ease;
}

.sidebar-thumb-box.is-captured {
  border: 1px solid rgba(0, 242, 254, 0.4);
  cursor: pointer;
}

.sidebar-thumb-box.is-captured:hover {
  border-color: #00f2fe;
  box-shadow: 0 0 6px rgba(0, 242, 254, 0.3);
}

.sidebar-thumb-box.is-captured.is-active {
  border: 1.5px solid #00f2fe;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.6);
}

.sidebar-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sidebar-thumb-box .thumb-badge {
  position: absolute;
  top: 1px;
  left: 1px;
  background: rgba(0, 0, 0, 0.85);
  color: #00f2fe;
  font-size: 7px;
  padding: 0px 3px;
  border-radius: 1px;
  font-family: monospace;
  border: 1px solid rgba(0, 242, 254, 0.2);
}

.sidebar-thumb-box .thumb-lock {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 242, 254, 0.4);
  font-size: 9px;
  opacity: 0.75;
}

.sidebar-uav-no-ref {
  padding: 20px;
  text-align: center;
  color: rgba(0, 242, 254, 0.5);
  font-size: 12px;
}

/* Deep overrides for right sidebar child cards to match dark digital twin look */
.right-sidebar :deep(.collaborative-response-card),
.right-sidebar :deep(.sensor-gateway-card) {
  background: rgba(2, 12, 26, 0.6) !important;
  color: #e2e8f0 !important;
  border: 1px solid rgba(0, 242, 254, 0.15) !important;
  box-shadow: inset 0 0 10px rgba(0, 242, 254, 0.05) !important;
  padding: 12px !important;
  border-radius: 8px !important;
}

.right-sidebar :deep(.card-title) {
  color: #ffffff !important;
  font-size: 18px !important;
  font-weight: 700 !important;
  text-shadow: 0 0 6px rgba(0, 242, 254, 0.3);
}

.right-sidebar :deep(.card-subtitle),
.right-sidebar :deep(.tip-text) {
  color: #94a3b8 !important;
  font-size: 14.5px !important;
}

.right-sidebar :deep(.config-input),
.right-sidebar :deep(.gateway-input) {
  background: rgba(0, 0, 0, 0.4) !important;
  color: #ffffff !important;
  border: 1px solid rgba(0, 242, 254, 0.3) !important;
}

.right-sidebar :deep(.config-input:focus),
.right-sidebar :deep(.gateway-input:focus) {
  border-color: #00f2fe !important;
  box-shadow: 0 0 8px rgba(0, 242, 254, 0.3) !important;
}

.right-sidebar :deep(.status-item),
.right-sidebar :deep(.service-row) {
  background: rgba(10, 19, 35, 0.7) !important;
  border: 1px solid rgba(0, 242, 254, 0.12) !important;
}

.right-sidebar :deep(.status-label),
.right-sidebar :deep(.service-label) {
  color: #94a3b8 !important;
}



.right-sidebar :deep(.realtime-detection-card .usage-fill) {
  min-width: 8px !important;
}

/* Sidebar UGV Cards - 赛博朋克深色主题 */
.ugv-cards-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ugv-card {
  flex: 1;
  background: rgba(7, 11, 25, 0.85);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6), 0 0 10px rgba(0, 255, 255, 0.1);
  font-family: "JetBrains Mono", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #fff;
  border: 1px solid rgba(0, 255, 255, 0.3);
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
}

.ugv-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00ffff, transparent);
}

.ugv-card .ugv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.15);
  background: rgba(0, 255, 255, 0.05);
}

.ugv-card .ugv-title {
  font-weight: bold;
  font-size: 20px;
  color: #00ffff;
  letter-spacing: 1px;
}

.ugv-card .ugv-status {
  font-size: 14px;
  color: #00ff88;
  font-weight: bold;
  padding: 2px 5px;
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
  border-radius: 3px;
}

.ugv-card .ugv-status.offline {
  color: #ffb4b4;
  background: rgba(168, 54, 54, 0.18);
  border-color: rgba(255, 180, 180, 0.28);
}

.ugv-card .ugv-data {
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ugv-card .ugv-row {
  display: flex;
  gap: 6px;
}

.ugv-card .ugv-item {
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  /* 调整内边距让视觉更舒展 */
  padding: 8px 12px; 
  display: flex;
  /* ★ 改为横向同行排列 */
  flex-direction: row; 
  /* ★ 两端对齐：左边标签，右边数值 */
  justify-content: space-between; 
  /* ★ 垂直居中 */
  align-items: center; 
  gap: 8px;
  transition: background 0.3s;
}

.ugv-card .ugv-item.full-width {
  flex: 100%;
  /* 基础 item 已经是 row 和 space-between 了，这里只需保持即可 */
}

.ugv-card .ugv-label {
  /* ★ 增大标签字体，原为 14.5px */
  font-size: 16px; 
  color: #8fa3b0;
  /* 略微加粗提升清晰度 */
  font-weight: 500; 
}

.ugv-card .ugv-value {
  /* ★ 增大数值字体，原为 18px */
  font-size: 22px; 
  font-weight: 700;
  color: #e0f2fe;
  text-shadow: 0 0 5px rgba(224, 242, 254, 0.4);
  /* 使用等宽字体让跳动的数字更稳定且具科技感 */
  font-family: "JetBrains Mono", monospace; 
}

.ugv-card .ugv-footer {
  text-align: right;
  padding: 8px 12px;
  font-size: 14.5px;
  color: #00ffff;
  background: rgba(0, 255, 255, 0.05);
  border-top: 1px solid rgba(0, 255, 255, 0.15);
  opacity: 0.8;
  cursor: pointer;
  transition: opacity 0.2s, background 0.2s;
}

.ugv-card .ugv-footer:hover {
  opacity: 1;
  background: rgba(0, 255, 255, 0.15);
}
.capability-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 8px;
  padding: 12px;
  color: #e2e8f0;
  margin-top: 12px;
}

.panel-header h3 {
  margin: 0 0 12px 0;
  font-size: 17.5px;
  color: #38bdf8;
  font-weight: 600;
  text-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
}

.capability-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cap-group {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.cap-title {
  font-size: 14.5px;
  color: #94a3b8;
  margin-bottom: 8px;
  border-left: 2px solid #38bdf8;
  padding-left: 6px;
  font-weight: 600;
}

.cap-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.c-lbl { font-size: 14.5px; color: #cbd5e1; }
.c-val { font-size: 14.5px; color: #f8fafc; font-weight: 500; }

.mini-status {
  font-size: 13px;
  padding: 2px 6px;
  border-radius: 4px;
}

.mini-status.on {
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.mini-status.off {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.progress-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  max-width: 120px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: #334155;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #0ea5e9, #38bdf8);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.stat-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(15, 23, 42, 0.4);
  padding: 8px;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.s-val {
  font-size: 26px;
  color: #38bdf8;
  font-weight: bold;
  margin: 2px 0;
  font-family: var(--font-family-mono);
}
</style>
