<template>
  <div class="home-dashboard" :class="{ 'story-active': !!currentFocusedPoint || !!route.query.scene }" :style="{
    '--layout-left-reserve': !isLandingView && !isSensorPanelCollapsed ? 'calc(var(--layout-sidebar-width) + 32px)' : '20px',
    '--layout-right-reserve': !isLandingView && !isSituationPanelCollapsed ? 'calc(var(--layout-sidebar-width) + 32px)' : '20px'
  }">
    <div class="main-layout">

      <main class="center-viewport-container">
        
        <div class="viewport-body">
          <div class="globe-layer">
            <HomeCesiumGlobe
              ref="globeRef"
              :phases="timelinePhases"
              :landing-view="isLandingView"
               v-model:active-phase-index="activePhaseIndex"
              :focused-point-id="currentFocusedPoint"
              :sensor-data="displaySensorData"
              :is-ws-connected="isWsConnected"
              :right-sidebar-collapsed="isSituationPanelCollapsed"
              @accident-picked="onAccidentPickedOnGlobe"
              @models-ready="onModelsReady"
              @reconstruction-ready="onReconstructionReady"
              @playback-durations="onPlaybackDurations"
              @loading-change="isGlobeLoading = $event"
              @vehicle-layer-change="mapLayerState = $event"
            />
          </div>
          
          <div v-if="!isLandingView" class="timeline-container" :style="{ bottom: timelineBottom + 'px' }">
            <HomeTimeProgress
              v-model="activePhaseIndex"
              v-model:accident-index="activeAccidentIndex"
              :phases="timelinePhases"
              :accidents="accidentPoints"
              :phases-ready="phasesReady"
              :reconstruction-ready="reconstructionReady"
              :playback-durations="playbackDurations"
              @locate="handleLocate"
              @phase-click="handlePhaseClick"
            />
          </div>
        </div>
      </main>

      <HomeDigitalHuman
        v-if="route.path === '/'"
        :accident-title="accidentPoints[activeAccidentIndex]?.title"
        :phase="timelinePhases[activePhaseIndex]"
      />

      <!-- 已由下方的水务风格双侧信息栏替代；保留原结构以避免影响既有推演状态。 -->
      <aside v-if="false" class="right-sidebar" :class="{ collapsed: isRightCollapsed }">
        <div v-if="isGlobeLoading" class="sidebar-loading-scrim" aria-hidden="true"></div>
        <button
          class="toggle-btn toggle-btn-right"
          type="button"
          :title="isRightCollapsed ? '展开左侧信息栏' : '收起左侧信息栏'"
          @click="isRightCollapsed = !isRightCollapsed"
        >
          <img
            class="sidebar-toggle-icon"
            :src="isRightCollapsed ? '/hud-assets/closeIcon/left_right_arrow.png' : '/hud-assets/closeIcon/left_left_arrow.png'"
            alt=""
          />
        </button>
        <div v-if="activeRightTab !== 'detection'" class="sidebar-header">
          <div class="header-main-title">
            <div class="header-title-block">
              <h2 class="sidebar-title">
                {{ activeRightTab === 'sensor' ? '传感器数据' : '协同响应 规划数据' }}
              </h2>
            </div>
            <span class="lkyw-hud-status-badge">● LIVE</span>
          </div>
        </div>
        <div class="sidebar-content right-sidebar-flex-content">
          <div class="right-tab-panel">
            <div v-if="activeRightTab === 'sensor'" class="sensor-data-panel">
              <!-- 切图左侧第一个框：仅承载地面感知单元 001 / 002。 -->
              <section class="airport-sidebar-slot airport-sidebar-slot--ground">
                <div class="sensor-header-row">
                  <span class="sensor-section-title">地面移动监测节点情况</span>
                  <span class="sensor-source-badge" :class="{ online: isSensorDeployed && isWsConnected }">
                    {{ !isSensorDeployed ? '⚠️ 尚未部署 (断联)' : (isWsConnected ? '📡 网关在线' : '⚠️ 离线模拟') }}
                  </span>
                </div>
                <div class="ugv-cards-container">
                  <button class="sensor-unit-gauge" type="button" @click="router.push({ path: '/sensor-manage', query: { target: 'node1' } })">
                    <img src="/hud-assets/gauge-ticks.png" alt="" />
                    <span class="sensor-unit-gauge__name">感知单元 1</span>
                    <span class="sensor-unit-gauge__status" :class="{ offline: !isSensorDeployed }">{{ isSensorDeployed ? '在线运行' : '等待部署' }}</span>
                  </button>
                  <button class="sensor-unit-gauge" type="button" @click="router.push({ path: '/sensor-manage', query: { target: 'node2' } })">
                    <img src="/hud-assets/gauge-ticks.png" alt="" />
                    <span class="sensor-unit-gauge__name">感知单元 2</span>
                    <span class="sensor-unit-gauge__status" :class="{ offline: !isSensorDeployed }">{{ isSensorDeployed ? '在线运行' : '等待部署' }}</span>
                  </button>
              </div>
              </section>

              <div class="sensor-section-title" style="margin-top: 0;">固定环境感知情况</div>
              
              <div class="meteorology-card">
                <div class="met-icon">🌬️</div>
                <div class="met-details">
                  <div class="met-row">
                    <span class="met-label">实时风速</span>
                    <span class="met-val">{{ isSensorDeployed ? displaySensorData.windSpeed : '0' }}<small class="metric-unit">m/s</small></span>
                  </div>
                  <div class="met-divider"></div>
                  <div class="met-row">
                    <span class="met-label">当前风向</span>
                    <span class="met-val">{{ isSensorDeployed ? displaySensorData.windDirection : '--' }}</span>
                  </div>
                </div>
              </div>

           
              <div class="sensor-section-title" style="margin-top: 0;">空域监测移动节点情况</div>
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


          <span class="s-val">{{networkStats.sensingDimensions}} <small class="metric-unit">项</small></span>

          <span>
            温/湿/烟/TVOC/CO/风
          </span>


        </div>



        <div class="stat-box">

          <span>
            累计数据吞吐量
          </span>


          <span class="s-val">{{totalPackets}} <small class="metric-unit">包</small></span>


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

      <aside v-if="!isLandingView" class="water-sidebar water-sidebar--left" :class="{ collapsed: isSensorPanelCollapsed }" aria-label="地图与模块信息">
        <button class="water-sidebar__toggle water-sidebar__toggle--left" type="button" :title="isSensorPanelCollapsed ? '展开传感器数据' : '收起传感器数据'" @click="isSensorPanelCollapsed = !isSensorPanelCollapsed">
          <img class="sidebar-toggle-icon" :src="isSensorPanelCollapsed ? '/hud-assets/closeIcon/left_right_arrow.png' : '/hud-assets/closeIcon/left_left_arrow.png'" alt="" />
        </button>
        <div class="water-sidebar__head command-head">
          <div><span>FIVE-MODULE COORDINATION</span><h2>五大模块联动总览</h2></div>
          <b><i></i>运行中</b>
        </div>
        <div class="water-sidebar__scroll command-scroll">
          <section class="water-section">
            <div class="water-section__title"><span>五大能力概览</span><small>5 MODULES</small></div>
            <div class="module-status-list">
              <button v-for="module in moduleStatusCards" :key="module.key" class="module-status-card" type="button" @click="goToModule(module.key)">
                <span class="module-status-card__icon" :class="{ 'has-generated-icon': module.image }">
                  <img v-if="module.image" :src="module.image" alt="" />
                  <AppIcon v-else :name="module.icon" />
                </span>
                <span class="module-status-card__copy"><strong>{{ module.name }}</strong></span>
                <span class="module-status-card__value" :class="module.tone">{{ module.value }}<em>{{ module.unit }}</em></span>
              </button>
            </div>
            <div class="module-link-chart" aria-label="五大模块联动关系">
              <button v-for="(module, index) in moduleStatusCards" :key="module.key" :style="moduleOrbitStyle(index)" class="module-link-node" :class="{ 'is-selected': selectedOverviewModule === module.key }" type="button" :aria-label="module.name + '：' + module.detail + '，点击切换下一个模块'" :aria-pressed="selectedOverviewModule === module.key" @click="advanceOverviewModule">
                <svg class="module-link-node__outline" viewBox="0 0 120 100" aria-hidden="true"><path d="M20 65 L60 43 L100 65 L60 87 Z" /></svg>
                <img class="module-link-node__base" src="/hud-assets/smart-park/capability-base.png" alt="" />
                <strong class="module-link-node__name">{{ module.name }}</strong>
                <small class="module-link-node__detail">{{ module.detail }}</small>
              </button>

            </div>
          </section>

          <section class="water-section operation-summary-panel">
            <div class="water-section__title"><span>地图感知要素</span><small>{{ isWsConnected ? '网关状态' : '演示数据' }}</small></div>
            <div class="sensor-bar-chart" role="img" :aria-label="sensorResourceLabel">
              <div class="sensor-bar-legend"><i></i>节点数</div>
              <div v-for="resource in sensorResourceBars" :key="resource.key" class="sensor-bar-row">
                <span>{{ resource.label }}</span><div class="sensor-bar-track"><i :style="{ width: `${resource.value / sensorResourceMax * 100}%` }"></i><b>{{ resource.value }}<em>个</em></b></div>
              </div>
              <div class="sensor-chart-axis"><span>0</span><span>节点数 / 个</span><span>{{ sensorResourceMax }}</span></div>
            </div>
            <div class="chart-status-footer">
              <span>数据频率 <b>{{ networkStats.throughput }}</b></span>
              <span>风速 <b>{{ displaySensorData.windSpeed }} m/s</b></span>
            </div>
          </section>


        </div>
      </aside>

      <aside v-if="!isLandingView" class="water-sidebar water-sidebar--right" :class="{ collapsed: isSituationPanelCollapsed }" aria-label="应急态势">
        <button class="water-sidebar__toggle water-sidebar__toggle--right" type="button" :title="isSituationPanelCollapsed ? '展开应急态势' : '收起应急态势'" @click="isSituationPanelCollapsed = !isSituationPanelCollapsed">
          <img class="sidebar-toggle-icon" :src="isSituationPanelCollapsed ? '/hud-assets/closeIcon/right_left_arrow.png' : '/hud-assets/closeIcon/right_right_arrow.png'" alt="" />
        </button>
        <div class="water-sidebar__head command-head">
          <div><span>MAP SITUATION OVERVIEW</span><h2>地图态势总览</h2></div>
          <b><i></i>仿真演示</b>
        </div>
        <div class="water-sidebar__scroll command-scroll">
          <section class="water-section map-base-summary">
            <div class="water-section__title"><span>地图基础信息</span><small>HUBEI MAP</small></div>
            <div class="map-base-summary__region"><strong>湖北省</strong><span>两客一危 · 省域态势</span></div>
            <div class="map-base-summary__layers"><span>卫星底图</span><i>＋</i><span>行政区划</span><i>＋</i><span>道路网络</span></div>
            <p>电子围栏标示省域范围，车辆点沿道路动态分布。</p>
            <dl class="map-base-summary__facts">
              <div><dt>覆盖范围</dt><dd>湖北省域 · 重点事故路段</dd></div>
              <div><dt>监管对象</dt><dd>公路客运 / 旅游客运 / 危化品运输</dd></div>
            </dl>
          </section>


          <section class="water-section">
            <div class="water-section__title"><span>车辆分类图层</span><button class="map-text-button" type="button" @click="selectMapCategory('all')">显示全部</button></div>
            <div class="vehicle-donut-chart">
              <svg viewBox="0 0 160 160" role="img" :aria-label="vehicleChartLabel">
                <title>{{ vehicleChartLabel }}</title>
                <circle cx="80" cy="80" r="69" fill="none" stroke="#BADCFF5C" stroke-width="1" stroke-dasharray="2 2" />
                <circle cx="80" cy="80" r="54" fill="none" stroke="#ffffff12" stroke-width="11" />
                <circle v-for="segment in vehicleDonutSegments" :key="segment.key" cx="80" cy="80" r="54" fill="none" :stroke="segment.ringColor" stroke-width="11" pathLength="100" :stroke-dasharray="segment.percent + ' ' + (100 - segment.percent)" :stroke-dashoffset="-segment.offset" transform="rotate(-90 80 80)"><title>{{ segment.name }}：{{ segment.count }}点</title></circle>
              </svg>
              <div class="vehicle-donut-chart__legend" aria-label="车辆分类筛选">
                <button v-for="vehicle in vehicleDonutSegments" :key="vehicle.key" type="button" :style="{ '--vehicle-color': vehicle.ringColor }" :class="{ selected: mapLayerState.category === vehicle.key }" :aria-pressed="mapLayerState.category === vehicle.key" @click="selectMapCategory(mapLayerState.category === vehicle.key ? 'all' : vehicle.key)"><i></i><span>{{ vehicle.name }}</span><b>{{ vehicle.count }}<small>点</small></b></button>
              </div>
            </div>
          </section>



          <section class="water-section map-key-locations">
            <div class="water-section__title"><span>地图重点位置</span><small>MAP LOCATIONS</small></div>
            <button v-for="location in mapKeyLocations" :key="location.id" type="button" class="map-location-row" @click="globeRef?.zoomToPoint(location.id)"><span class="map-location-row__pin" aria-hidden="true"></span><span><strong>{{ location.city }}</strong><small>{{ location.road }}</small><em>{{ location.label }}</em></span><b>定位 ›</b></button>
          </section>



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
import HomeDigitalHuman from '../components/home/HomeDigitalHuman.vue'
import { MAP_VEHICLE_STYLES } from '../config/mapVehicleStyles'
import AppIcon from '../components/AppIcon.vue'
import { getSensorGatewayBaseUrl } from '../config/subsystems'
import { currentRole, canAccessRoute } from '../composables/useRoleAccess'

const router = useRouter()
const route = useRoute()
const activeServiceId = ref('')
const selectedOverviewModule = ref('')
// Advance automatically after five seconds without a carousel click.
const moduleOrbitAngle = ref(0)
let moduleOrbitFrame = 0
let moduleOrbitStep = 0
let moduleOrbitTimer = 0
function scheduleOverviewAdvance() {
  window.clearTimeout(moduleOrbitTimer)
  moduleOrbitTimer = window.setTimeout(advanceOverviewModule, 5000)
}
function moduleOrbitStyle(index) {
  const angle = moduleOrbitAngle.value + index * Math.PI * 2 / moduleStatusCards.value.length
  const depth = (Math.cos(angle) + 1) / 2
  return {
    left: (50 + Math.sin(angle) * 33) + '%',
    top: (75 + Math.cos(angle) * 65) + 'px',
    transform: 'translateX(-50%) scale(' + (.68 + depth * .32) + ')',
    opacity: .7 + depth * .3,
    '--detail-opacity': Math.max(0, (depth - .92) / .08),
    zIndex: Math.round(depth * 100) + 1
  }
}
function advanceOverviewModule() {
  scheduleOverviewAdvance()
  cancelAnimationFrame(moduleOrbitFrame)
  const count = moduleStatusCards.value.length
  moduleOrbitStep += 1
  const from = moduleOrbitAngle.value
  const target = -moduleOrbitStep * Math.PI * 2 / count
  selectedOverviewModule.value = moduleStatusCards.value[moduleOrbitStep % count].key
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    moduleOrbitAngle.value = target
    return
  }
  const started = performance.now()
  function animate(time) {
    const progress = Math.min((time - started) / 650, 1)
    const eased = .5 - Math.cos(progress * Math.PI) / 2
    moduleOrbitAngle.value = from + (target - from) * eased
    if (progress < 1) moduleOrbitFrame = requestAnimationFrame(animate)
    else moduleOrbitFrame = 0
  }
  moduleOrbitFrame = requestAnimationFrame(animate)
}
onMounted(scheduleOverviewAdvance)
onBeforeUnmount(() => {
  window.clearTimeout(moduleOrbitTimer)
  cancelAnimationFrame(moduleOrbitFrame)
})

const activeMenuKey = ref('')
const globeRef = ref(null)
const isGlobeLoading = ref(true)
const isLandingView = computed(() => route.path === '/' && route.query.view !== 'overview' && !route.query.scene)
watch(isLandingView, () => {
  isSensorPanelCollapsed.value = true
  isSituationPanelCollapsed.value = true
}, { flush: 'post' })
const isSensorPanelCollapsed = ref(true)
const isSituationPanelCollapsed = ref(true)

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

// 网关未连接时沿用感知组网子系统的演示编队数据；连通后严格以网关状态展示。
const fleetOnline = computed(() => {
  if (!isWsConnected.value || !wsData.value) {
    return { uav: 3, ugv: 5, environment: 8, video: 4 }
  }
  return {
    uav: resourceStatus.value.uav ? 3 : 0,
    ugv: resourceStatus.value.ugv1 || resourceStatus.value.ugv2 ? 5 : 0,
    environment: resourceStatus.value.weather ? 8 : 0,
    video: 4,
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
const reconstructionReady = ref(false)
const playbackDurations = ref({})
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
  get: () => accidentPhaseIndices.value[currentAccidentId.value] ?? -1,
  set: (val) => {
    accidentPhaseIndices.value[currentAccidentId.value] = val
  }
})

const isSensorDeployed = computed(() => {
  return activePhaseIndex.value >= 2
})

const moduleMenus = [
  { key: 'home', label: '地图大屏', path: '/', roles: [] },
  { key: 'sensor', label: '感知组网', path: '/sensor-manage', roles: ['dispatcher', 'admin'] },
  { key: 'realtime', label: '实时检测', path: '/realtime', roles: ['dispatcher', 'expert', 'admin'] },
  { key: 'coordination', label: '协同响应', path: '/coordination', roles: ['commander', 'dispatcher', 'admin'] },
  { key: 'modeling', label: '精细建模', path: '/modeling', roles: ['commander', 'expert', 'admin'] },
  { key: 'simulation', label: '仿真推演', path: '/simulation', roles: ['commander', 'expert', 'admin'] },
]

const topMenus = computed(() =>
  moduleMenus.filter(item => !item.roles.length || item.roles.includes(currentRole.value))
)

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

const onlineSensorTotal = computed(() =>
  Number(fleetOnline.value.uav || 0) + Number(fleetOnline.value.ugv || 0) + Number(fleetOnline.value.environment || 0) + Number(fleetOnline.value.video || 0)
)

const moduleStatusCards = computed(() => [
  { key: 'sensor', name: '感知组网', shortName: '感知', icon: 'broadcast', detail: '空地节点实时感知', value: onlineSensorTotal.value, unit: '在线', tone: 'cyan' },
  { key: 'realtime', name: '实时检测', shortName: '检测', icon: 'radar', detail: '车辆事故智能识别', value: activePhaseIndex.value >= 2 ? '01' : '00', unit: '事件', tone: 'orange' },
  { key: 'coordination', name: '协同响应', shortName: '协同', icon: 'route', image: '/hud-assets/module-icons/uav-ugv-coordination.png', detail: '无人机与无人车协同', value: `${fleetOnline.value.uav}/${coordinatedUgvCount}`, unit: 'UAV / UGV', tone: 'green' },
  { key: 'modeling', name: '精细建模', shortName: '建模', icon: 'cube', detail: '三维场景重建', value: reconstructionReady.value ? '100' : '--', unit: reconstructionReady.value ? '%' : '', tone: 'purple' },
  { key: 'simulation', name: '仿真推演', shortName: '推演', icon: 'activity', image: '/hud-assets/module-icons/five-rescue-routes.png', detail: '五类救援路线推演', value: '05', unit: '类路线', tone: 'gold' }
])

const mapVehicleSummary = Object.entries(MAP_VEHICLE_STYLES).map(([key, style]) => ({ key, ...style }))
function isModuleLinked(module) {
  const systems = timelinePhases.value[activePhaseIndex.value]?.systems || []
  if (module.key === 'sensor') return activePhaseIndex.value < 2 || systems.includes('边缘网关')
  if (module.key === 'modeling') return activePhaseIndex.value === 9 && reconstructionReady.value
  if (module.key === 'simulation') return true
  return systems.includes(module.name)
}
const sensorResourceBars = computed(() => [
  { key: 'uav', label: '空基无人机', value: Number(fleetOnline.value.uav) || 0, color: '#76d3dc' },
  { key: 'ugv', label: '地基无人车', value: Number(fleetOnline.value.ugv) || 0, color: '#8caddc' },
  { key: 'environment', label: '环境感知', value: Number(fleetOnline.value.environment) || 0, color: '#91c5ae' },
  { key: 'video', label: '视频节点', value: Number(fleetOnline.value.video) || 0, color: '#c3b58b' },
])
const sensorResourceMax = computed(() => Math.max(10, Math.ceil(Math.max(...sensorResourceBars.value.map(item => item.value)) / 5) * 5))
const sensorResourceLabel = computed(() => sensorResourceBars.value.map(item => `${item.label}${item.value}个`).join('，'))
const mapKeyLocations = [
  { id: 'accident_blue', city: '仙桃市', road: '随岳高速 · 毛嘴段', label: '货车追尾客车场景' },
  { id: 'accident_red', city: '黄冈市 · 团风县', road: '迎宾大道环岛', label: '槽罐车侧翻泄漏场景' },
]
const mapLayerState = ref({ category: 'all', counts: { hazard: 0, passenger: 0, tourist: 0 } })
const visibleMapVehicleCount = computed(() => Object.values(mapLayerState.value.counts).reduce((sum, count) => sum + count, 0))
const vehicleChartMax = computed(() => Math.max(50, Math.ceil(Math.max(...Object.values(mapLayerState.value.counts)) / 50) * 50))
const vehicleChartTicks = computed(() => Array.from({ length: 5 }, (_, index) => ({ value: vehicleChartMax.value * index / 4, y: 142 - index * 28 })))
const vehicleChartPoints = computed(() => mapVehicleSummary.map((vehicle, index) => {
  const count = mapLayerState.value.counts[vehicle.key] || 0
  return { ...vehicle, count, x: 64 + index * 125, y: 142 - count / vehicleChartMax.value * 112 }
}))
// Smart park option3: thin ring, dashed outer rim and vertical rectangular legend.
const vehicleDonutSegments = computed(() => {
  const colors = ['#ec7585', '#13ceba', '#2d98ff']
  const total = vehicleChartPoints.value.reduce((sum, point) => sum + point.count, 0)
  let offset = 0
  return vehicleChartPoints.value.map((point, index) => {
    const percent = total ? point.count / total * 100 : 0
    const segment = { ...point, ringColor: colors[index], percent, offset }
    offset += percent
    return segment
  })
})
const vehicleChartLine = computed(() => vehicleChartPoints.value.map(point => `${point.x},${point.y}`).join(' '))
const vehicleChartArea = computed(() => `M64,142 L${vehicleChartPoints.value.map(point => `${point.x},${point.y}`).join(' L')} L314,142 Z`)
const vehicleChartLabel = computed(() => `当前地图车辆分类点数：${vehicleChartPoints.value.map(point => `${point.name}${point.count}点`).join('，')}`)
function selectMapCategory(category) { globeRef.value?.setMapVehicleCategory(category) }

const coordinatedUgvCount = 4

const currentFocusedVehicle = computed(() => {
  const phase = timelinePhases.value[activePhaseIndex.value]
  const index = activePhaseIndex.value
  const truck = currentAccidentId.value === 'rear-end'
  return {
    phase: phase?.shortLabel || '初始化',
    level: index < 2 ? '监测阶段' : '事故推演',
    type: truck ? '高速公路碰撞 · 烟雾与火情演化' : '危化品运输 · 泄漏与扩散演化',
    location: truck ? '随岳高速 · 仙桃毛嘴段' : '黄冈团风 · 迎宾大道环岛',
    status: index < 2 ? '车辆与道路进入持续监测，等待事故阶段触发。' : index < 5 ? '事故告警触发空地侦察，获取现场影像与环境信息。' : index < 7 ? (truck ? '持续观察烟雾与火情，辅助研判次生灾害风险。' : '持续观察泄漏与扩散，辅助研判警戒和防护范围。') : index < 10 ? '空地装备协同抵近，部署感知节点并采集三维重建数据。' : index === 10 ? '演示通信受扰后的链路切换和数据回传。' : '展示消防、医疗、公安、防化和路政五类力量的协同救援路线。',
  }
})

function goToModule(key) {
  const target = moduleMenus.find(module => module.key === key)
  if (target && canAccessRoute(target.roles)) router.push(target.path)
}

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

watch(currentRole, () => {
  // 身份切换后回到总览，确保不会停留在已无权限的旧模块页面。
  activeMenuKey.value = 'home'
  router.replace({ path: '/' })
})

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
function onReconstructionReady(isReady) { reconstructionReady.value = Boolean(isReady) }
function onPlaybackDurations(durations) { playbackDurations.value = durations || {} }

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
      'rear-end': queryScene === 'rear-end' ? queryPhaseIndex : -1,
      'leakage': queryScene === 'leakage' ? queryPhaseIndex : -1
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
          'rear-end': queryScene === 'rear-end' ? queryPhaseIndex : -1,
          'leakage': queryScene === 'leakage' ? queryPhaseIndex : -1
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
          'rear-end': -1,
          'leakage': -1
        }
        const wasFocused = !!currentFocusedPoint.value
        // 清除当前聚焦点
        currentFocusedPoint.value = ''

        // Cesium恢复默认视角
        // landingView 的监听统一负责迎宾与综合态势之间的相机过渡。
        if (globeRef.value && wasFocused) {
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
@font-face {
  font-family: 'LkywSanjiyunhei';
  src: url('/hud-assets/fonts/sanjiyunhei.ttf') format('truetype');
  font-display: swap;
}
@font-face {
  font-family: 'LkywOppoSans';
  src: url('/hud-assets/fonts/oppo-sans-regular.ttf') format('truetype');
  font-display: swap;
}
@font-face {
  font-family: 'LkywTencentSans';
  src: url('/hud-assets/fonts/tencent-sans-w7.otf') format('opentype');
  font-display: swap;
}
@font-face {
  font-family: 'LkywHanyi';
  src: url('/hud-assets/fonts/hanyi-changmeihei.ttf') format('truetype');
  font-display: swap;
}
@font-face {
  font-family: 'LkywDigital';
  src: url('/hud-assets/fonts/ds-digi.ttf') format('truetype');
  font-display: swap;
}
/* Main Layout structure */
.home-dashboard {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100%;
  overflow: hidden;
  background: #eaedf1;
  font-family: var(--font-family-ui);
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
  font-size: var(--font-size-system-title);
  font-weight: var(--font-weight-heading);
  color: #00f2fe;
  text-shadow: 0 0 12px rgba(0, 242, 254, 0.65), 0 0 4px rgba(0, 242, 254, 0.8);
  letter-spacing: 3px;
  font-family: var(--font-family-ui);
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

.role-switcher {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  padding: 5px 9px;
  border: 1px solid rgba(0, 242, 254, 0.28);
  border-radius: 7px;
  background: rgba(0, 242, 254, 0.06);
  color: #dffcff;
}

.role-switcher-label,
.role-description {
  color: #8ca5bd;
  font-size: 12px;
  white-space: nowrap;
}

.role-icon {
  color: #00f2fe;
  font-size: 15px;
  text-shadow: 0 0 8px rgba(0, 242, 254, 0.8);
}

.role-switcher select {
  min-width: 86px;
  height: 28px;
  padding: 0 6px;
  border: 0;
  border-radius: 4px;
  color: #f2fcff;
  background: #0a2035;
  font: inherit;
  font-size: 14px;
  font-weight: 700;
  outline: none;
  cursor: pointer;
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
  font-size: var(--font-size-navigation);
  font-weight: var(--font-weight-heading);
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
  font-size: var(--font-size-assist);
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
  /* 对齐机场切图的左侧栏宽度：保留原业务内容与滚动行为。 */
  width: clamp(280px, 19vw, 365px);
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

/* 三维地图初始化期间，左侧业务栏与右侧指挥栏同步进入不可交互的虚化态。 */
.sidebar-loading-scrim {
  position: absolute;
  z-index: 20;
  inset: -1px;
  border-radius: inherit;
  background: rgba(2, 10, 22, 0.68);
  backdrop-filter: blur(5px) saturate(75%);
  -webkit-backdrop-filter: blur(5px) saturate(75%);
  pointer-events: auto;
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
  height: 88px;
  background: transparent;
  border: none;
  box-shadow: none;
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
  filter: brightness(1.2) drop-shadow(0 0 7px rgba(0, 242, 254, 0.65));
}
.sidebar-toggle-icon { display: block; width: 18px; height: 88px; object-fit: contain; }
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
  font-size: var(--font-size-assist);
  color: #00f2fe;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: inline-block;
  margin-top: 3px;
  opacity: 0.85;
  font-family: var(--font-family-ui);
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

/* 数字人向地图左上侧偏移：避开右侧信息栏和底部切换栏。 */
.digital-human-assistant {
  --sidebar-clearance: clamp(280px, 19vw, 365px);
  position: absolute;
  right: calc(var(--sidebar-clearance) + 82px);
  bottom: clamp(168px, 19vh, 220px);
  z-index: 16;
  width: clamp(130px, 11vw, 210px);
  pointer-events: none;
}

.digital-human-assistant img {
  display: block;
  width: 100%;
  height: auto;
  max-height: min(42vh, 360px);
  object-fit: contain;
  filter: drop-shadow(0 8px 12px rgba(0, 0, 0, 0.42));
}

@media (max-width: 720px) {
  .digital-human-assistant {
    display: none;
  }
}

/* Floating Timeline floating beautifully above the globe */
.timeline-container {
  position: absolute;
  bottom: 20px; /* 往上移动一点，贴近视口 */
  /*
   * 地图内还叠放了左右两个 500px 的控制面板（含 16px 外边距）。
   * 不能再以整个视口居中，否则浏览器缩放到 67% 时，时间线会延伸到
   * 面板下面。为两侧各预留 540px，使时间线始终只占用中间的安全区域。
   */
  left: 540px;
  right: 540px;
  width: auto;
  transform: none;
  min-width: 0;
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
  font-weight: var(--font-weight-heading);
  margin: 2px 0;
  font-family: var(--font-family-number);
}
.sidebar-title {
  font-size: var(--font-size-system-title) !important;
  font-weight: var(--font-weight-heading) !important;
  text-shadow: 0 0 6px rgba(0, 242, 254, 0.4) !important; /* 顺便加个发光效果更醒目 */
}
/* ==========================================
   智慧园区大屏字体层级覆盖
   ========================================== */

/* 1. 面板标题 */
.sensor-section-title {
  font-size: var(--font-size-panel-title) !important;
  font-weight: var(--font-weight-heading) !important;
}
.panel-header h3 {
  font-size: var(--font-size-panel-title) !important;
  font-weight: var(--font-weight-heading) !important;
}

/* 2. 卡片标题 */
.ugv-card .ugv-title {
  font-size: var(--font-size-panel-title) !important;
  font-weight: var(--font-weight-heading);
}

/* 3. 正文与标签 */
.ugv-card .ugv-label,
.meteorology-card .met-label,
.c-lbl,
.cap-item > div > div:first-child,
.stat-box span:first-child {
  font-size: var(--font-size-body) !important;
  font-weight: var(--font-weight-body);
}

/* 4. 核心指标数字 */
.ugv-card .ugv-value,
.meteorology-card .met-val,
.c-val,
.highlight {
  font-family: var(--font-family-number);
  font-size: 26px !important;
  font-weight: var(--font-weight-heading);
}
.metric-unit,
.s-val small {
  margin-left: 3px;
  color: inherit;
  font-family: var(--font-family-ui);
  font-size: .7em;
  font-weight: var(--font-weight-body);
}

/* 5. 分组标题与辅助信息 */
.cap-title {
  font-size: var(--font-size-panel-title) !important;
  font-weight: var(--font-weight-heading);
}
.mini-status {
  font-size: var(--font-size-assist) !important;
  font-weight: var(--font-weight-body);
}
.ugv-card .ugv-footer {
  font-size: var(--font-size-body) !important;
  font-weight: var(--font-weight-body);
}

/* 机场切图左侧三格：第一格固定仅显示 001 / 002，两节点内容可以在格内独立滚动。 */
.right-sidebar-flex-content {
  overflow: hidden;
  padding: 8px;
}
.right-tab-panel,
.sensor-data-panel {
  min-height: 0;
  height: 100%;
}
.sensor-data-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  scrollbar-width: none;
}
.sensor-data-panel::-webkit-scrollbar { display: none; width: 0; height: 0; }
.airport-sidebar-slot {
  min-height: 0;
  overflow: visible;
  padding: 8px;
  border: 1px solid rgba(47, 169, 222, .54);
  background: linear-gradient(145deg, rgba(4, 32, 56, .92), rgba(3, 20, 38, .88));
  box-shadow: inset 0 0 18px rgba(0, 210, 255, .08);
}
.airport-sidebar-slot--ground {
  display: flex;
  flex-direction: column;
  flex: none;
}
.airport-sidebar-slot--ground .ugv-cards-container {
  overflow: visible;
  padding-right: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.sensor-unit-gauge {
  position: relative;
  min-height: 112px;
  border: 1px solid rgba(0, 229, 255, .2);
  border-radius: 6px;
  overflow: hidden;
  background: radial-gradient(circle at 50% 52%, rgba(0, 141, 193, .16), rgba(3, 21, 39, .78) 64%);
  color: #dffaff;
  cursor: pointer;
}
.sensor-unit-gauge::before {
  content: '';
  position: absolute;
  inset: 7px;
  border: 1px solid rgba(0, 229, 255, .08);
  border-radius: 50%;
}
.sensor-unit-gauge img {
  position: absolute;
  width: 104px;
  height: 104px;
  top: 3px;
  left: 50%;
  transform: translateX(-50%);
  opacity: .95;
}
.sensor-unit-gauge__name,
.sensor-unit-gauge__status {
  position: absolute;
  left: 0;
  right: 0;
  text-align: center;
}
.sensor-unit-gauge__name {
  top: 40px;
  color: #e9fbff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .5px;
  text-shadow: 0 0 8px rgba(0, 229, 255, .55);
}
.sensor-unit-gauge__status {
  top: 61px;
  color: #00e7a8;
  font-size: 10px;
}
.sensor-unit-gauge__status::before {
  content: '●';
  margin-right: 4px;
  font-size: 8px;
}
.sensor-unit-gauge__status.offline { color: #ffb4b4; }
.sensor-unit-gauge:hover {
  border-color: rgba(0, 229, 255, .65);
  box-shadow: inset 0 0 18px rgba(0, 229, 255, .1), 0 0 12px rgba(0, 229, 255, .12);
}
.airport-sidebar-slot--ground .sensor-section-title {
  font-size: var(--font-size-panel-title) !important;
  line-height: 1.2;
}
.airport-sidebar-slot--ground .ugv-data { padding: 5px 7px; gap: 3px; }
.airport-sidebar-slot--ground .ugv-item { padding: 4px 6px; min-height: 32px; }
.airport-sidebar-slot--ground .ugv-label { font-size: 11px !important; }
.airport-sidebar-slot--ground .ugv-value { font-size: 17px !important; }
.airport-sidebar-slot--ground .ugv-header { padding: 5px 7px; }
.airport-sidebar-slot--ground .ugv-title { font-size: 13px !important; }
.airport-sidebar-slot--ground .ugv-status { padding: 1px 4px; font-size: 10px; }
.airport-sidebar-slot--ground .ugv-footer { padding: 5px 7px; font-size: 11px !important; }
.sensor-data-panel > .sensor-section-title {
  margin: 0 !important;
  padding: 9px 10px;
  border: 1px solid rgba(47, 169, 222, .54);
  border-bottom: 0;
  background: linear-gradient(90deg, rgba(6, 81, 137, .6), rgba(4, 28, 50, .9));
}
.sensor-data-panel > .meteorology-card {
  margin-top: -8px;
  border: 1px solid rgba(47, 169, 222, .54);
  border-top: 0;
  border-radius: 0;
  background: rgba(3, 23, 42, .9);
}

/* 智慧水务风格的双侧信息栏：左侧聚焦实体感知，右侧聚焦应急态势。 */
:deep(.lkyw-monitor-hud.high-end-panel) { display: none !important; }
.water-sidebar {
  position: absolute;
  z-index: 34;
  top: 16px;
  bottom: 16px;
  width: clamp(280px, 18vw, 346px);
  display: flex;
  flex-direction: column;
  overflow: visible;
  border: 1px solid rgba(32, 216, 255, .48);
  border-radius: 7px;
  background: linear-gradient(180deg, rgba(2, 26, 43, .62), rgba(2, 13, 28, .52));
  box-shadow: 0 14px 34px rgba(0, 0, 0, .42), inset 0 0 30px rgba(0, 199, 255, .07);
  backdrop-filter: blur(10px);
  color: #e8faff;
  transition: transform .28s ease;
}
.water-sidebar--left { left: 16px; }
.water-sidebar--right { right: 16px; }
.water-sidebar--left.collapsed { transform: translateX(calc(-100% - 22px)); }
.water-sidebar--right.collapsed { transform: translateX(calc(100% + 22px)); }
.water-sidebar__toggle {
  position: absolute;
  z-index: 4;
  top: 50%;
  width: 18px;
  height: 88px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  transform: translateY(-50%);
  transition: filter .2s ease;
}
.water-sidebar__toggle:hover { filter: brightness(1.2) drop-shadow(0 0 5px rgba(0, 220, 255, .7)); }
.water-sidebar__toggle--left { right: -18px; }
.water-sidebar__toggle--right { left: -18px; }
.water-sidebar__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 52px;
  padding: 0 13px;
  border-bottom: 1px solid rgba(72, 208, 239, .43);
  background: linear-gradient(90deg, rgba(0, 120, 153, .34), rgba(0, 28, 49, .25));
}
.water-sidebar__head span { display: block; color: #68ddf4; font: 700 9px/1 Consolas, monospace; letter-spacing: 1.2px; }
.water-sidebar__head h2 { margin: 4px 0 0; color: #f1feff; font-size: 20px; line-height: 1; letter-spacing: 1px; }
.water-sidebar__head > b { display: inline-flex; align-items: center; gap: 5px; padding: 4px 6px; border: 1px solid rgba(24, 230, 170, .32); border-radius: 3px; color: #55f1bf; background: rgba(0, 148, 100, .12); font-size: 10px; font-weight: 600; white-space: nowrap; }
.water-sidebar__head i { width: 6px; height: 6px; border-radius: 50%; background: #17efaa; box-shadow: 0 0 7px #17efaa; }
.water-sidebar__scroll { flex: 1; min-height: 0; padding: 10px; overflow-y: auto; scrollbar-width: thin; scrollbar-color: rgba(69, 212, 241, .55) transparent; }
.water-sidebar__scroll::-webkit-scrollbar { width: 4px; }.water-sidebar__scroll::-webkit-scrollbar-thumb { border-radius: 4px; background: rgba(69, 212, 241, .55); }
.water-section { margin-bottom: 12px; }.water-section:last-child { margin-bottom: 0; }
.water-section__title { display: flex; align-items: center; justify-content: space-between; min-height: 25px; padding: 0 7px; border-bottom: 1px solid rgba(126, 212, 236, .25); background: linear-gradient(90deg, rgba(35, 129, 153, .3), transparent); color: #ddfbff; font-size: 13px; font-weight: 700; }
.water-section__title span::before { content: ''; display: inline-block; width: 3px; height: 13px; margin-right: 6px; vertical-align: -2px; background: #1dddf4; box-shadow: 0 0 6px rgba(29, 221, 244, .85); }.water-section__title small { color: #68b8ca; font: 9px/1 Consolas, monospace; }
.sensor-fleet-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; padding-top: 8px; }
.sensor-fleet-card { min-height: 100px; padding: 9px 8px 7px; border: 1px solid rgba(34, 182, 216, .38); border-radius: 5px; background: linear-gradient(145deg, rgba(1, 35, 57, .82), rgba(3, 17, 31, .62)); color: #e8fbff; cursor: pointer; text-align: center; transition: .18s ease; }.sensor-fleet-card:hover { border-color: #3deaff; background: rgba(0, 117, 148, .26); box-shadow: inset 0 0 14px rgba(25, 220, 255, .08), 0 0 10px rgba(25, 220, 255, .15); transform: translateY(-1px); }
.sensor-fleet-card__icon { display: block; height: 28px; font-size: 24px; filter: drop-shadow(0 0 5px rgba(67, 229, 255, .5)); }.sensor-fleet-card strong { display: block; min-height: 26px; margin-top: 3px; color: #e9fbff; font-size: 11px; line-height: 1.2; }.sensor-fleet-card > div { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 7px; color: #7bb5c6; font-size: 9px; }.sensor-fleet-card > div span + span { border-left: 1px solid rgba(79, 190, 216, .22); }.sensor-fleet-card b { display: block; margin-top: 1px; color: #72efff; font-size: 14px; line-height: 1; }.sensor-fleet-card b.offline { color: #ff8898; }
.environment-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin-top: 7px; border: 1px solid rgba(44, 169, 201, .24); background: rgba(44, 169, 201, .20); }.environment-grid > div { min-height: 58px; padding: 8px; background: rgba(3, 22, 38, .84); }.environment-grid span { display: block; color: #85bbcb; font-size: 10px; }.environment-grid b { display: block; margin-top: 5px; color: #f0fcff; font: 700 19px/1 Arial, sans-serif; }.environment-grid em { margin-left: 3px; color: #71d8ee; font-size: 9px; font-style: normal; }.environment-grid .environment-grid__direction { color: #6be9ff; font-size: 14px; padding-top: 3px; }
.water-link-status { padding-bottom: 2px; }.water-link-status > div:not(.water-section__title) { display: flex; align-items: center; justify-content: space-between; padding: 8px 7px; border-bottom: 1px dashed rgba(92, 190, 214, .18); color: #91bdca; font-size: 11px; }.water-link-status > div:last-child { border-bottom: 0; }.water-link-status b { color: #6ee9fa; font-size: 11px; }
.situation-current { padding: 8px 9px 9px; border: 1px solid rgba(42, 193, 223, .25); background: linear-gradient(150deg, rgba(6, 68, 93, .42), rgba(3, 19, 34, .5)); }.situation-current .water-section__title { margin: -8px -9px 9px; }.situation-current > strong { color: #f5fbff; font-size: 17px; }.situation-current p { margin: 5px 0 9px; color: #91c4d1; font-size: 11px; }.situation-current__phase { display: flex; align-items: center; justify-content: space-between; padding-top: 8px; border-top: 1px solid rgba(104, 202, 226, .19); color: #9bc2cb; font-size: 11px; }.situation-current__phase b { color: #ffe587; font-size: 12px; }
.response-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; padding-top: 8px; }.response-grid > div { padding: 8px; border: 1px solid rgba(52, 177, 207, .26); background: rgba(0, 52, 75, .28); }.response-grid span, .response-grid small { display: block; color: #85b7c6; font-size: 10px; }.response-grid b { display: inline-block; margin: 4px 5px 0 0; color: #72edff; font: 700 22px/1 Arial, sans-serif; }.response-grid small { display: inline; color: #49dca5; }
.event-signal-list > div:not(.water-section__title) { display: flex; align-items: center; gap: 6px; padding: 9px 4px; border-bottom: 1px solid rgba(86, 180, 205, .14); color: #accbd3; font-size: 11px; }.event-signal-list > div:last-child { border-bottom: 0; }.event-signal-list b { margin-left: auto; color: #e8fbff; font-size: 11px; }.event-signal-list__dot { width: 6px; height: 6px; border-radius: 50%; }.event-signal-list__dot.critical { background: #ff4d6d; box-shadow: 0 0 7px #ff4d6d; }.event-signal-list__dot.warn { background: #ffc34d; box-shadow: 0 0 7px #ffc34d; }.event-signal-list__dot.normal { background: #32e9b0; box-shadow: 0 0 7px #32e9b0; }
.situation-progress > div:not(.water-section__title) { display: grid; grid-template-columns: 70px 1fr; gap: 7px; align-items: center; margin-top: 8px; color: #9fc5cf; font-size: 11px; }.situation-progress b { display: block; height: 5px; border-radius: 5px; background: rgba(115, 156, 169, .25); }.situation-progress b.complete { background: linear-gradient(90deg, #14d7ec, #42eda8); box-shadow: 0 0 8px rgba(55, 230, 204, .48); }

/* 首页指挥驾驶舱：模块闭环与地图车辆态势。 */
.command-head { background: linear-gradient(90deg, rgba(0, 73, 102, .28), rgba(2, 25, 44, .14)); }
.command-scroll { padding: 14px 16px; }
/* 轮转节点的装饰图不应撑出滚动区域，左侧总览保持固定视口。 */
.water-sidebar--left .water-sidebar__scroll { overflow: hidden; }
.module-status-list { display: grid; gap: 0; margin-top: 10px; overflow: hidden; border: 1px solid rgba(89, 191, 216, .28); border-radius: 6px; background: rgba(2, 20, 35, .38); }
.module-status-card { display: grid; grid-template-columns: 45px minmax(0, 1fr) auto; align-items: center; min-height: 64px; padding: 7px 12px; border: 0; border-bottom: 1px solid rgba(105, 191, 214, .18); border-radius: 0; background: transparent; color: #ebfcff; cursor: pointer; text-align: left; transition: background .18s ease; }
.module-status-card:last-child { border-bottom: 0; }.module-status-card:hover { background: rgba(22, 122, 151, .16); }
.module-status-card__icon { display: grid; place-items: center; width: 31px; height: 31px; border: 1px solid rgba(100, 228, 255, .46); border-radius: 50%; color: #8cefff; background: transparent; box-shadow: none; font-size: 17px; }
.module-status-card__icon.has-generated-icon { overflow: hidden; border-color: rgba(100, 228, 255, .55); background: transparent; }.module-status-card__icon img { display: block; width: 26px; height: 26px; object-fit: contain; }
.module-status-card__copy { min-width: 0; }.module-status-card__copy strong { display: block; color: #f1fdff; font-size: 19px; line-height: 1.2; letter-spacing: .5px; }.module-status-card__copy small { display: block; margin-top: 5px; color: #8fb9c4; font-size: 13px; line-height: 1.15; }
.module-status-card__value { min-width: 57px; color: #8befff; font: 700 24px/1 Arial, sans-serif; letter-spacing: -.5px; text-align: right; text-shadow: none; }.module-status-card__value em { margin-left: 3px; color: #9fbec7; font: 600 10px/1 Arial, sans-serif; font-style: normal; text-shadow: none; }.module-status-card__value.orange { color: #ffd176; }.module-status-card__value.green { color: #62ebb1; }.module-status-card__value.purple { color: #c3a6ff; }.module-status-card__value.gold { color: #ffe28c; }
.module-relationship { padding: 12px 0 0; border: 0; border-top: 1px solid rgba(104, 202, 226, .22); border-radius: 0; background: transparent; }.module-relationship .water-section__title { margin: 0 0 11px; }.module-flow { display: flex; align-items: center; justify-content: space-between; gap: 2px; }.module-flow__step { display: grid; justify-items: center; gap: 4px; min-width: 0; padding: 0; border: 0; background: transparent; color: #c4e8ee; cursor: pointer; font-size: 12px; font-weight: 600; }.module-flow__step .app-icon { width: 25px; height: 25px; padding: 4px; border: 1px solid rgba(75, 217, 245, .45); border-radius: 50%; background: transparent; }.module-flow__step:hover { color: #fff0a0; }.module-flow__arrow { color: #62cfdf; font-size: 19px; font-style: normal; line-height: 1; }.module-relationship__summary { display: none; }
.vehicle-overview { padding: 15px 14px; border: 1px solid rgba(69, 203, 218, .28); border-radius: 6px; background: rgba(0, 70, 95, .2); box-shadow: none; }.vehicle-overview__main { display: flex; align-items: baseline; gap: 6px; }.vehicle-overview__main span { color: #b9dbe1; font-size: 14px; }.vehicle-overview__main strong { margin-left: auto; color: #8cecf4; font: 700 31px/1 Arial, sans-serif; letter-spacing: 1px; text-shadow: none; }.vehicle-overview__main em { color: #b6d8df; font-size: 12px; font-style: normal; }.vehicle-overview__meta { display: flex; justify-content: space-between; gap: 10px; margin-top: 11px; padding-top: 10px; border-top: 1px solid rgba(93, 220, 237, .18); color: #9fc9d2; font-size: 12px; }.vehicle-overview__meta b { color: #ffd176; font-size: 15px; }
.vehicle-category-list { display: grid; gap: 0; margin-top: 10px; overflow: hidden; border: 1px solid rgba(90, 184, 207, .25); border-radius: 6px; }.vehicle-category { display: grid; grid-template-columns: 35px 1fr auto; align-items: center; gap: 8px; min-height: 52px; padding: 7px 10px; border-left: 3px solid #e35f75; border-bottom: 1px solid rgba(89, 177, 200, .16); background: transparent; }.vehicle-category:last-child { border-bottom: 0; }.vehicle-category.passenger { border-left-color: #54dca4; background: transparent; }.vehicle-category.tourist { border-left-color: #5acaf1; background: transparent; }.vehicle-category__icon { display: grid; place-items: center; width: 27px; height: 27px; border-radius: 50%; background: rgba(82, 170, 190, .12); font-size: 15px; }.vehicle-category__name { color: #e6f7fa; font-size: 15px; font-weight: 600; }.vehicle-category__name small { display: none; }.vehicle-category > b { color: #ff8795; font: 700 21px/1 Arial, sans-serif; }.vehicle-category.passenger > b { color: #64e9b4; }.vehicle-category.tourist > b { color: #6ad6f4; }.vehicle-category > b em { margin-left: 2px; color: #9fbec7; font-size: 10px; font-style: normal; }
.focused-vehicle { padding: 12px; border: 1px solid rgba(178, 191, 157, .26); border-radius: 6px; background: rgba(32, 39, 33, .34); }.focused-vehicle .water-section__title { margin: -12px -12px 11px; }.focused-vehicle__plate { display: flex; align-items: center; gap: 7px; }.focused-vehicle__plate > span { font-size: 20px; }.focused-vehicle__plate strong { color: #f3fbfc; font-size: 20px; letter-spacing: .7px; }.focused-vehicle__plate b { margin-left: auto; padding: 4px 6px; border: 1px solid rgba(255, 185, 113, .45); color: #ffd18a; font-size: 10px; }.focused-vehicle p { margin: 7px 0; color: #a7c4cb; font-size: 12px; }.focused-vehicle > div:not(.water-section__title):not(.focused-vehicle__plate) { display: flex; justify-content: space-between; gap: 12px; padding-top: 8px; border-top: 1px solid rgba(151, 187, 191, .14); color: #91b2bb; font-size: 12px; }.focused-vehicle > div b { color: #e5f6f8; text-align: right; }
.operation-summary-panel { padding: 0; }.operation-summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; }.operation-summary-grid > div { display: grid; grid-template-columns: 20px 1fr; grid-template-rows: auto auto; column-gap: 7px; min-height: 69px; padding: 9px; border: 1px solid rgba(85, 183, 205, .2); border-radius: 5px; background: rgba(2, 35, 52, .34); }.operation-summary-grid .app-icon { grid-row: 1 / 3; width: 18px; height: 18px; margin-top: 2px; color: #62e2f4; }.operation-summary-grid span { color: #9abec7; font-size: 12px; }.operation-summary-grid b { overflow: hidden; margin-top: 4px; color: #e9fafc; font-size: 14px; font-weight: 600; line-height: 1.1; text-overflow: ellipsis; white-space: nowrap; }.operation-summary-grid em { margin-left: 2px; color: #72ddec; font-size: 10px; font-style: normal; }
.mission-brief-panel { padding: 12px; border: 1px solid rgba(93, 197, 214, .25); border-radius: 6px; background: rgba(2, 42, 61, .34); }.mission-brief-panel .water-section__title { margin: -12px -12px 10px; }.mission-brief-panel strong { display: block; color: #f0fbfd; font-size: 18px; font-weight: 600; }.mission-brief-panel > div:not(.water-section__title) { display: flex; justify-content: space-between; gap: 12px; padding-top: 9px; margin-top: 9px; border-top: 1px solid rgba(105, 202, 220, .14); color: #9dc0c9; font-size: 13px; }.mission-brief-panel b { color: #c9edf2; font-weight: 600; text-align: right; }
.road-risk-panel { padding: 0; }.road-risk-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px; }.road-risk-grid > div { display: grid; justify-items: center; gap: 3px; min-height: 72px; padding: 8px 4px; border: 1px solid rgba(94, 180, 203, .2); border-radius: 5px; background: rgba(3, 35, 50, .35); color: #82e7f3; }.road-risk-grid .app-icon { width: 17px; height: 17px; }.road-risk-grid b { color: #f2fbfc; font: 700 23px/1 Arial, sans-serif; }.road-risk-grid span { color: #a1c4cb; font-size: 12px; white-space: nowrap; }.road-risk-grid .risk-high b { color: #ff8d9a; }.road-risk-grid .risk-warn b { color: #ffd17d; }.road-risk-grid .risk-normal b { color: #70dff0; }
.incident-brief { padding: 12px; border: 1px solid rgba(112, 195, 213, .24); border-radius: 6px; background: rgba(1, 39, 58, .36); }.incident-brief .water-section__title { margin: -12px -12px 10px; }.incident-brief strong { display: block; color: #f3fcff; font-size: 18px; font-weight: 600; }.incident-brief > span { display: block; margin-top: 7px; color: #a8ced6; font-size: 13px; }
.map-link-panel { padding: 0 9px; border: 1px solid rgba(58, 182, 210, .22); border-radius: 6px; background: rgba(2, 24, 40, .55); }.map-link-panel .water-section__title { margin: 0 -9px; }.map-link-panel > div:not(.water-section__title) { display: flex; align-items: center; gap: 8px; padding: 9px 0; border-bottom: 1px dashed rgba(86, 194, 219, .18); color: #c3e1e8; font-size: 13px; line-height: 1.25; }.map-link-panel > div:last-child { border-bottom: 0; }.map-link-panel .app-icon { width: 18px; height: 18px; color: #60e8ff; }

/* 大屏阅读优化：侧栏加宽，正文、指标和告警文字统一提升一个层级。 */
.water-sidebar { width: clamp(330px, 22vw, 430px); }
.water-sidebar__head { min-height: 64px; padding: 0 16px; }.water-sidebar__head span { font-size: 10px; }.water-sidebar__head h2 { font-size: 25px; }.water-sidebar__head > b { gap: 6px; padding: 5px 8px; font-size: 12px; }.water-sidebar__head i { width: 7px; height: 7px; }
.water-sidebar__scroll { padding: 13px; }.water-section { margin-bottom: 15px; }.water-section__title { min-height: 31px; padding: 0 9px; font-size: 16px; }.water-section__title span::before { width: 4px; height: 16px; margin-right: 8px; }.water-section__title small { font-size: 10px; }
.sensor-fleet-grid { gap: 9px; padding-top: 10px; }.sensor-fleet-card { min-height: 120px; padding: 11px 9px 9px; }.sensor-fleet-card__icon { height: 32px; font-size: 28px; }.sensor-fleet-card strong { min-height: 31px; margin-top: 4px; font-size: 13px; }.sensor-fleet-card > div { gap: 6px; margin-top: 8px; font-size: 11px; }.sensor-fleet-card b { margin-top: 2px; font-size: 18px; }
.environment-grid { margin-top: 9px; }.environment-grid > div { min-height: 68px; padding: 10px; }.environment-grid span { font-size: 12px; }.environment-grid b { margin-top: 6px; font-size: 24px; }.environment-grid em { margin-left: 4px; font-size: 11px; }.environment-grid .environment-grid__direction { font-size: 17px; }
.water-link-status > div:not(.water-section__title) { padding: 10px 9px; font-size: 13px; }.water-link-status b { font-size: 13px; }
.situation-current { padding: 10px 11px 11px; }.situation-current .water-section__title { margin: -10px -11px 11px; }.situation-current > strong { font-size: 21px; }.situation-current p { margin: 6px 0 11px; font-size: 13px; }.situation-current__phase { padding-top: 10px; font-size: 13px; }.situation-current__phase b { font-size: 14px; }
.response-grid { gap: 9px; padding-top: 10px; }.response-grid > div { padding: 10px; }.response-grid span, .response-grid small { font-size: 12px; }.response-grid b { margin: 5px 6px 0 0; font-size: 27px; }
.event-signal-list > div:not(.water-section__title) { gap: 8px; padding: 11px 5px; font-size: 13px; }.event-signal-list b { font-size: 13px; }.event-signal-list__dot { width: 8px; height: 8px; }
.situation-progress > div:not(.water-section__title) { grid-template-columns: 82px 1fr; gap: 9px; margin-top: 10px; font-size: 13px; }.situation-progress b { height: 6px; }

/* 两侧驾驶舱字体层级：以中文界面字体为主，数字使用等宽字形。 */
.water-sidebar,
.water-sidebar button {
  font-family: 'LkywOppoSans', "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
.water-sidebar__head h2 { font-family: 'LkywHanyi', 'LkywTencentSans', "Microsoft YaHei", sans-serif; font-weight: 600; letter-spacing: .4px; }
.water-sidebar__head > b { font-weight: 600; letter-spacing: .15px; }
.water-section__title { font-family: 'LkywTencentSans', "Microsoft YaHei", sans-serif; font-weight: 600; letter-spacing: .2px; }
.module-status-card__copy strong { font-family: 'LkywTencentSans', "Microsoft YaHei", sans-serif; font-size: 17px; font-weight: 600; letter-spacing: .15px; }
.module-status-card__value,
.vehicle-overview__main strong,
.vehicle-category > b,
.response-grid b { font-family: 'LkywDigital', "DIN Alternate", "Arial Narrow", Arial, sans-serif; font-weight: 700; font-variant-numeric: tabular-nums; }
.module-status-card__value em { font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif; font-weight: 600; letter-spacing: 0; }
.module-flow__step { font-weight: 600; letter-spacing: .1px; }
.module-relationship__summary { font-weight: 400; letter-spacing: .15px; }
.vehicle-category__name,
.focused-vehicle__plate strong { font-weight: 600; letter-spacing: .2px; }
.focused-vehicle p,
.focused-vehicle > div:not(.water-section__title):not(.focused-vehicle__plate),
.map-link-panel > div:not(.water-section__title) { font-weight: 400; }

/* 借鉴智慧水务大屏的字体层级：标题、分栏标题、数据、说明四级清晰区分。 */
.water-sidebar { width: clamp(360px, 22vw, 440px); }
.water-sidebar__head { min-height: 72px; padding: 0 18px; }
.water-sidebar__head span { color: #73d9ee; font: 700 11px/1.1 "Arial Narrow", Consolas, monospace; letter-spacing: 1.35px; }
.water-sidebar__head h2 { margin-top: 5px; color: #f4feff; font-size: 28px; font-weight: 700; letter-spacing: .8px; text-shadow: 0 0 9px rgba(109, 231, 249, .28); }
.water-sidebar__head > b { padding: 6px 10px; font-size: 13px; }
.water-sidebar__scroll { padding: 15px 16px 18px; }
.water-section { margin-bottom: 18px; }
.water-section__title { min-height: 36px; padding: 0 10px; color: #eafcff; font-size: 18px; font-weight: 700; letter-spacing: .35px; }
.water-section__title span::before { width: 4px; height: 19px; margin-right: 9px; }.water-section__title small { color: #72c8d8; font-size: 10px; letter-spacing: .8px; }
.module-status-card { min-height: 72px; padding: 9px 13px; }.module-status-card__icon { width: 34px; height: 34px; font-size: 19px; }.module-status-card__icon img { width: 29px; height: 29px; }
.module-status-card__copy strong { font-size: 19px; font-weight: 700; letter-spacing: .3px; }.module-status-card__copy small { margin-top: 5px; color: #a6cbd3; font-size: 14px; font-weight: 500; }
.module-status-card__value { min-width: 71px; font-family: 'LkywDigital', "DIN Alternate", Arial, sans-serif; font-size: 29px; }.module-status-card__value em { margin-left: 3px; font-family: 'LkywOppoSans', "Microsoft YaHei", sans-serif; font-size: 12px; }
.operation-summary-grid { gap: 10px; }.operation-summary-grid > div { min-height: 76px; padding: 10px; }.operation-summary-grid .app-icon { width: 20px; height: 20px; }.operation-summary-grid span { font-size: 13px; }.operation-summary-grid b { margin-top: 5px; font-size: 16px; }.operation-summary-grid em { font-size: 11px; }
.mission-brief-panel strong { font-size: 20px; }.mission-brief-panel > div:not(.water-section__title) { font-size: 14px; }.mission-brief-panel b { font-size: 14px; }
.vehicle-overview { padding: 17px 16px; }.vehicle-overview__main span { font-size: 16px; }.vehicle-overview__main strong { font-size: 38px; }.vehicle-overview__main em { font-size: 14px; }.vehicle-overview__meta { font-size: 13px; }.vehicle-overview__meta b { font-size: 17px; }
.vehicle-category { grid-template-columns: 1fr auto; min-height: 58px; padding: 9px 11px; }.vehicle-category__name { font-size: 17px; }.vehicle-category > b { font-size: 25px; }.vehicle-category > b em { font-size: 11px; }
.focused-vehicle { padding: 14px; }.focused-vehicle .water-section__title { margin: -14px -14px 12px; }.focused-vehicle__plate strong { font-size: 23px; }.focused-vehicle p { font-size: 14px; }.focused-vehicle > div:not(.water-section__title):not(.focused-vehicle__plate) { font-size: 14px; }
.road-risk-grid > div { min-height: 80px; }.road-risk-grid .app-icon { width: 19px; height: 19px; }.road-risk-grid b { font-size: 27px; }.road-risk-grid span { font-size: 13px; }.incident-brief { padding: 14px; }.incident-brief .water-section__title { margin: -14px -14px 12px; }.incident-brief strong { font-size: 20px; }.incident-brief > span { font-size: 14px; }
.map-overview-note { margin: 10px 0 0; color: #9abdc9; font-size: 12px; line-height: 1.65; }
.water-sidebar .map-base-summary { font-family: 'LkywOppoSans', "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif; }
.map-base-summary__facts { margin: 14px 0 0; padding: 0; border-top: 1px solid rgba(126, 212, 236, .18); }
.map-base-summary__facts > div { display: grid; grid-template-columns: 80px minmax(0, 1fr); align-items: baseline; gap: 12px; padding: 10px 0; border-bottom: 1px solid rgba(126, 212, 236, .1); font-size: 16px; line-height: 1.6; }
.map-base-summary__facts dt { color: #8cabb7; }
.map-base-summary__facts dd { margin: 0; color: #d2eff8; overflow-wrap: anywhere; }
.map-base-summary__region { display: flex; align-items: baseline; gap: 14px; padding: 15px 0 12px; }
.map-base-summary__region strong { font-size: 25px; color: #dbf2f7; }
.map-base-summary__region span { font-size: 12px; color: #8cabb7; }
.map-base-summary__layers { display: flex; gap: 7px; align-items: center; flex-wrap: wrap; }
.map-base-summary__layers span { display: inline-flex; align-items: center; justify-content: center; min-width: 84px; height: 28px; padding: 0 12px; border: 0; color: #d2eff8; font-size: 12px; white-space: nowrap; background: url('/hud-assets/pill-default.svg') center / 100% 100% no-repeat; }
.map-base-summary__layers span:hover { color: #e6ffdb; background-image: url('/hud-assets/pill-active.svg'); }
.map-base-summary__layers i { font-size: 12px; color: #6d939f; font-style: normal; }

.map-base-summary p { margin: 12px 0 0; color: #8cabb7; font-size: 12px; line-height: 1.7; }
.map-composition__bar { display: flex; height: 8px; overflow: hidden; border-radius: 3px; margin: 18px 0 12px; background: #648b9d22; }
.map-composition__bar span { height: 100%; transition: width .25s ease; }
.map-composition__row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; color: #b4cdd7; font-size: 13px; }
.map-composition__row > span { display: flex; align-items: center; gap: 9px; }
.map-composition__row i { width: 5px; height: 5px; border-radius: 50%; }
.map-composition__row b { font-variant-numeric: tabular-nums; font-size: 17px; color: #d5e7ec; font-weight: 500; }
.map-composition__row small { margin-left: 4px; font-size: 11px; color: #89aab8; }
.map-location-row { display: flex; align-items: center; gap: 12px; width: 100%; border: 0; border-bottom: 1px solid #6799ab22; padding: 15px 3px; background: transparent; color: #c0dbe5; font: inherit; text-align: left; cursor: pointer; }
.map-location-row:hover { background: #91c5d20a; }
.map-location-row:focus-visible { outline: 1px solid #80d5e8; outline-offset: -1px; }
.map-location-row__pin { flex: 0 0 7px; height: 7px; border: 1px solid #d9ba70; border-radius: 50%; box-shadow: 0 0 0 4px #d9ba7012; }
.map-location-row > span:nth-child(2) { display: flex; flex-direction: column; gap: 5px; }
.map-location-row strong { font-size: 16px; font-weight: 500; }
.map-location-row small { font-size: 12px; color: #9cb9c5; }
.map-location-row em { font-size: 11px; color: #799ca9; font-style: normal; }
.map-location-row > b { margin-left: auto; font-size: 12px; font-weight: 400; white-space: nowrap; color: #80c9dd; }
.map-symbol-list { display: grid; gap: 14px; padding: 15px 0 4px; }
.map-symbol-list > div { display: grid; grid-template-columns: 23px 1fr auto; align-items: center; gap: 10px; font-size: 13px; color: #b6ced8; }
.map-symbol-list small { color: #819fac; font-size: 11px; }
.map-symbol-list i { justify-self: center; font-style: normal; }
.map-symbol-line { width: 20px; height: 1px; background: #87e2ef; box-shadow: 0 0 3px #8be4ef66; }
.map-symbol-dot { width: 5px; height: 5px; border-radius: 50%; background: #ffd43b; }
.map-symbol-label { font-size: 9px; padding: 1px 3px; border: 1px solid #78b7c666; border-radius: 3px; }
.map-symbol-alert { font-size: 14px; font-weight: 700; color: #e6bb68; }
.module-link-chart { position: relative; height: 264px; margin: 12px 0 8px; overflow: clip; border-bottom: 1px solid #6bafc11a; }
.module-link-node { position: absolute; width: 120px; max-width: 36%; height: 100px; padding: 0; border: 0; background: transparent; color: #d7ffff; font-family: 'LkywOppoSans', "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif; cursor: pointer; isolation: isolate; transform-origin: center center; }
/* Enlarge holograms independently of labels and orbit hit targets. */
.module-link-node__base { position: absolute; z-index: -1; left: -50%; top: -12px; width: 200%; height: auto; clip-path: inset(0 0 44% 0); pointer-events: none; }
.module-link-node__outline { position: absolute; z-index: -2; left: 0; top: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; }
.module-link-node__outline path { fill: rgba(23, 93, 135, .04); stroke: rgba(109, 181, 225, .62); stroke-width: .7; }
.module-link-node__name { position: absolute; top: 12px; left: 0; width: 100%; color: #d7ffff; font-family: inherit; font-size: 18px; font-weight: 400; font-style: normal; line-height: 24px; white-space: nowrap; text-align: center; text-shadow: none; }
.module-link-node__detail { position: absolute; top: 90px; left: -15%; width: 130%; color: #66a3c0; font-family: inherit; font-size: 15px; font-weight: 400; line-height: 20px; white-space: nowrap; text-align: center; opacity: var(--detail-opacity); pointer-events: none; }
.module-link-node:focus-visible { outline: 1px solid #69d9e6; outline-offset: 2px; border-radius: 4px; }
@media (prefers-reduced-motion: reduce) { .module-link-node, .module-link-node__base { transition: none; } }

.water-sidebar--left .module-status-card { min-height: 56px; padding: 8px 10px; }
.water-sidebar--left .module-status-card__icon { width: 27px; height: 27px; }
.water-sidebar--left .module-status-card__icon img { width: 25px; height: 25px; }
.water-sidebar--left .module-status-card__copy strong { font-size: 18px; }
.water-sidebar--left .module-status-card__copy small { font-size: 12px; margin-top: 3px; }
.water-sidebar--left .module-status-card__value { font-size: 23px; }
.sensor-bar-chart { padding: 18px 4px 10px; }
.sensor-bar-legend { display: flex; align-items: center; gap: 6px; margin: 0 0 12px 36px; color: #e5f5f5; font-size: 12px; }
.sensor-bar-legend i { width: 10px; height: 10px; border-radius: 2px; background: linear-gradient(90deg, rgba(45, 152, 255, .3), #00d2ba); }
.water-sidebar .sensor-bar-row { display: grid; grid-template-columns: 96px minmax(0, 1fr); align-items: center; gap: 9px; margin: 0; min-height: 48px; color: #e2eeee; font-family: 'LkywOppoSans', "Microsoft YaHei", sans-serif; font-size: 13px; }
.sensor-bar-row > span { text-align: right; padding-right: 2px; }
.sensor-bar-track { position: relative; display: flex; align-items: center; height: 48px; padding-right: 44px; border-left: 1px solid rgba(255, 255, 255, .3); }
.sensor-bar-track::before { content: ''; position: absolute; top: 0; bottom: 0; left: -5px; width: 5px; background: linear-gradient(#ffffff55, #ffffff55) left top / 5px 1px no-repeat, linear-gradient(#ffffff55, #ffffff55) left bottom / 5px 1px no-repeat; }
.sensor-bar-track i { display: block; flex-shrink: 0; height: 18px; border-radius: 0 2px 2px 0; background: linear-gradient(90deg, rgba(45, 152, 255, .3), rgba(0, 210, 186, 1)); transition: width .3s ease; }
.water-sidebar .sensor-bar-row b { margin-left: 5px; white-space: nowrap; color: #f5ffff; font-family: 'LkywSanjiyunhei', "Microsoft YaHei", sans-serif; font-size: 16px; font-weight: 400; font-variant-numeric: tabular-nums; }
.sensor-bar-row b em { margin-left: 2px; font-size: 12px; font-style: normal; }

.chart-status-footer { display: flex; justify-content: space-between; padding: 12px 4px; border-top: 1px solid #6bafc11a; color: #8cabb8; font-size: 12px; }
.chart-status-footer b { margin-left: 5px; color: #c5dfe7; font-weight: 500; }
.mission-brief-panel > .rescue-flow-chart { display: flex; flex-direction: column; align-items: center; gap: 7px; margin-top: 15px; }
.rescue-flow-chart__source { font-size: 12px; color: #a6cbd3; }
.rescue-flow-chart > i { color: #6da5b7; font-size: 15px; font-style: normal; line-height: 1; }
.rescue-flow-chart > .rescue-flow-chart__hub { padding: 8px 28px; border: 1px solid #69b7cb66; border-radius: 3px; color: #b8e6ef; font-size: 14px; font-weight: 500; background: #24677a1a; }
.rescue-flow-chart__targets { position: relative; display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; align-self: stretch; padding-top: 9px; border-top: 1px solid #6da5b744; }
.rescue-flow-chart__targets span { position: relative; padding: 7px 0; border-radius: 3px; background: #7caebe12; color: #afcdd7; font-size: 12px; text-align: center; }
.rescue-flow-chart__targets span::before { content: ''; position: absolute; width: 1px; height: 9px; background: #6da5b744; top: -9px; left: 50%; }
.water-sidebar--right .focused-vehicle > .phase-progress-chart { display: flex; align-items: center; gap: 20px; justify-content: flex-start; padding: 10px 0; border: 0; }
.phase-progress-chart svg { width: 96px; height: 96px; flex: 0 0 96px; font-family: inherit; }
.phase-progress-chart__number { fill: #ddf5fa; font-size: 26px; font-family: 'LkywDigital', sans-serif; }
.phase-progress-chart__total { fill: #87aab7; font-size: 14px; }
.phase-progress-chart__caption { fill: #8db0bd; font-size: 10px; }
.phase-progress-chart__copy { display: flex; flex-direction: column; gap: 6px; }
.phase-progress-chart__copy > span { color: #89aab8; font-size: 11px; }
.phase-progress-chart__copy > strong { color: #d8f0f6; font-size: 18px; font-weight: 600; }
.phase-progress-chart__copy time { color: #84c4d4; font-size: 14px; font-variant-numeric: tabular-nums; }
.water-sidebar--right .focused-vehicle > .phase-node-strip { display: flex; justify-content: space-between; border: 0; padding: 0 0 17px; gap: 0; }
.phase-node-strip > span { display: flex; align-items: center; flex: 1; }
.phase-node-strip > span:not(:last-child)::after { content: ''; height: 1px; flex: 1; background: #53758566; }
.phase-node-strip i { display: block; width: 6px; height: 6px; border-radius: 50%; border: 1px solid #597c8d; background: #152b37; }
.phase-node-strip .passed i { background: #669cae; border-color: #669cae; }
.phase-node-strip .current i { background: #a5edee; border-color: #a5edee; box-shadow: 0 0 0 4px #8adbe51f; }
.phase-node-strip > span:last-child { flex: 0; }
@media (prefers-reduced-motion: reduce) { .sensor-bar-track i { transition: none; } }
.vehicle-donut-chart { display: grid; grid-template-columns: minmax(110px, 44%) minmax(0, 1fr); align-items: center; gap: 12px; padding: 22px 0 14px; }
.vehicle-donut-chart svg { display: block; width: 100%; height: auto; }
.vehicle-donut-chart__legend { display: grid; gap: 14px; }
.vehicle-donut-chart__legend button { display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; gap: 7px; align-items: center; width: 100%; padding: 5px 2px; border: 1px solid transparent; border-radius: 3px; background: transparent; color: #effafa; font: inherit; font-size: 13px; text-align: left; cursor: pointer; }
.vehicle-donut-chart__legend i { width: 18px; height: 11px; border-radius: 2px; background: var(--vehicle-color); }
.vehicle-donut-chart__legend b { font-family: 'LkywSanjiyunhei', "Microsoft YaHei", sans-serif; font-size: 17px; font-weight: 400; white-space: nowrap; }
.vehicle-donut-chart__legend small { margin-left: 2px; font-size: 12px; }
.vehicle-donut-chart__legend button:hover, .vehicle-donut-chart__legend button.selected { border-color: var(--vehicle-color); background: #78d9ed0d; }
.vehicle-donut-chart__legend button:focus-visible { outline: 2px solid #c4f0fa; outline-offset: 2px; }
.vehicle-line-chart { padding: 12px 0 4px; }
.vehicle-line-chart__unit { color: #89aebc; font-size: 11px; margin-bottom: 4px; }
.vehicle-line-chart svg { display: block; width: 100%; height: auto; overflow: visible; }
.vehicle-line-chart__grid { stroke: #83b6c3; stroke-opacity: .13; stroke-dasharray: 3 5; }
.vehicle-line-chart__tick { fill: #9ab9c6; font-family: inherit; font-size: 11px; }
.vehicle-line-chart__value { font-family: 'LkywDigital', sans-serif; font-size: 19px; }
.vehicle-line-chart__legend { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; margin-top: 8px; }
.vehicle-line-chart__legend button { display: inline-flex; align-items: center; gap: 6px; border: 1px solid transparent; border-radius: 3px; padding: 6px; background: transparent; color: #bad1db; font: inherit; font-size: 12px; cursor: pointer; }
.vehicle-line-chart__legend i { width: 5px; height: 5px; border-radius: 50%; background: var(--vehicle-color); }
.vehicle-line-chart__legend button:hover, .vehicle-line-chart__legend button.selected { border-color: var(--vehicle-color); background: #78d9ed0d; }
.vehicle-line-chart__legend button:focus-visible { outline: 2px solid #c4f0fa; outline-offset: 2px; }
.water-sidebar--right .vehicle-overview { border: 0; border-bottom: 1px solid #6bafc12b; border-radius: 0; background: transparent; padding: 12px 4px 18px; }
.water-sidebar--right .vehicle-overview__main strong { color: #d8edf2; font-size: 34px; }
.water-sidebar--right .vehicle-overview__meta { border-top: 0; margin-top: 10px; padding-top: 0; font-size: 12px; }
.water-sidebar--right .vehicle-category-list { border: 0; margin-top: 6px; border-radius: 0; }
.vehicle-category-list .vehicle-category { position: relative; grid-template-columns: 1fr auto; width: 100%; min-height: 46px; padding: 10px 8px 10px 19px; text-align: left; font-family: inherit; cursor: pointer; border: 0; border-bottom: 1px solid #6bafc11a; background: transparent; border-radius: 3px; }
.vehicle-category-list .vehicle-category::before { content: ''; position: absolute; left: 3px; top: 50%; transform: translateY(-50%); width: 4px; height: 16px; border-radius: 2px; background: var(--vehicle-color); }
.vehicle-category-list .vehicle-category__name { font-size: 16px; font-weight: 500; color: #ccdde4; }
.vehicle-category-list .vehicle-category > b { color: var(--vehicle-color); font-size: 23px; font-weight: 500; }
.vehicle-category-list .vehicle-category__name small { display: block; margin-top: 5px; color: #9abdc9; font-size: 12px; font-weight: 400; }
.vehicle-category-list .vehicle-category:hover, .vehicle-category-list .vehicle-category.is-selected { background: #608f9c1a; box-shadow: none; }
.water-sidebar--right .focused-vehicle, .water-sidebar--right .incident-brief { padding: 12px 0; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
.water-sidebar--right .focused-vehicle .water-section__title, .water-sidebar--right .incident-brief .water-section__title { margin: 0 0 14px; }
.water-sidebar--right .focused-vehicle__plate strong { font-size: 21px; font-weight: 600; }
.water-sidebar--right .focused-vehicle__plate b { border-color: #86a7ad55; color: #aec9d1; background: transparent; }
.water-sidebar--right .focused-vehicle > div:not(.water-section__title):not(.focused-vehicle__plate) { padding: 9px 0; font-size: 13px; border-bottom-color: #6bafc11a; }
.map-text-button { border: 0; background: transparent; color: #8ae6f7; font: inherit; font-size: 12px; cursor: pointer; }
.map-locate-button { width: 100%; margin-top: 12px; padding: 9px; border: 1px solid #51d8ee66; border-radius: 4px; background: #087b932b; color: #bdf7ff; font: inherit; cursor: pointer; }
.map-stage-description { margin: 12px 0; color: #bfdee7; font-size: 14px; line-height: 1.8; }
.map-stage-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.map-stage-tags span { padding: 5px 9px; border: 1px solid #65ccdf4d; border-radius: 3px; background: #0c52652b; color: #90eaf6; font-size: 13px; }
.map-locate-button:focus-visible, .map-text-button:focus-visible, .vehicle-category:focus-visible { outline: 2px solid #fff; outline-offset: -3px; }
/* 两侧共用文字层级，避免右栏及紧凑卡片单独缩小字号。 */
.water-sidebar { font-size: 16px; }
.water-sidebar .water-sidebar__head h2 { font-family: 'LkywTencentSans', "Microsoft YaHei", sans-serif; font-size: 28px; font-weight: 700; font-style: normal; }
.water-sidebar .water-section__title { font-family: 'LkywTencentSans', "Microsoft YaHei", sans-serif; font-size: 20px; font-weight: 700; font-style: normal; line-height: 1.4; letter-spacing: .3px; min-height: 40px; padding: 0 10px; color: #eafcff; border-bottom: 1px solid rgba(126, 212, 236, .25); background: linear-gradient(90deg, rgba(35, 129, 153, .3), transparent); }
.water-sidebar .water-section__title > span { font: inherit; letter-spacing: inherit; }
.water-sidebar .water-section__title > span::before { width: 4px; height: 19px; margin-right: 9px; vertical-align: -2px; background: #1dddf4; box-shadow: 0 0 6px rgba(29, 221, 244, .85); }
.water-sidebar .water-section__title small,
.water-sidebar .water-sidebar__head span { font-size: 12px; }
.water-sidebar .module-status-card__copy strong { font-family: 'LkywOppoSans', "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif; font-size: 18px; font-weight: 400; font-style: normal; }
.water-sidebar .module-status-card { min-height: 66px; }
.water-sidebar .module-status-card__copy small { font-size: 14px; line-height: 1.4; }
.water-sidebar .module-status-card__value em { font-size: 14px; }


.water-sidebar .sensor-chart-axis,
.water-sidebar .vehicle-line-chart__unit,
.water-sidebar .module-link-chart > span { font-size: 13px; }
.water-sidebar .chart-status-footer,
.water-sidebar .map-base-summary__region span,
.water-sidebar .map-base-summary__layers span,
.water-sidebar .map-base-summary p,
.water-sidebar .vehicle-overview__meta,
.water-sidebar .map-overview-note,
.water-sidebar .vehicle-line-chart__legend button,
.water-sidebar .map-text-button,
.water-sidebar .vehicle-category__name small { font-size: 14px; }
.water-sidebar .vehicle-overview__main span,
.water-sidebar .map-composition__row,
.water-sidebar .map-locate-button,
.water-sidebar .map-stage-description,
.water-sidebar .map-location-row strong,
.water-sidebar .map-symbol-list > div { font-size: 16px; }
.water-sidebar .map-composition__row b { font-size: 20px; }
.water-sidebar .map-composition__row small { font-size: 14px; }
.water-sidebar .vehicle-line-chart__tick { font-size: 13px; }
.water-sidebar .module-link-chart svg { font-size: 14px; }
.water-sidebar .water-section__title { padding-left: 30px; background: url('/hud-assets/smart-park/section-title.png') left center / 100% 100% no-repeat; border-bottom: 0; font-family: 'LkywSanjiyunhei', "Microsoft YaHei", sans-serif; font-weight: 400; }
.water-sidebar .water-section__title > span::before { display: none; }
.water-sidebar .water-section__title { position: relative; }
.water-sidebar .water-section__title::before { content: ''; position: absolute; top: -5px; left: 0; width: 12px; height: 12px; background: url('/hud-assets/header-chevron.png') center / contain no-repeat; pointer-events: none; }
.water-sidebar .map-base-summary__region span { font-size: 16px; }
.water-sidebar .map-base-summary__layers span { min-width: 96px; height: 38px; padding: 0 10px; font-family: 'LkywSanjiyunhei', "Microsoft YaHei", sans-serif; font-size: 22px; font-weight: 400; line-height: 1.3; }
.water-sidebar .map-base-summary__layers i { font-size: 16px; }
.water-sidebar .map-base-summary p { font-size: 16px; line-height: 1.7; }
.water-sidebar .map-location-row { padding: 18px 4px; }
.water-sidebar .map-location-row > span:nth-child(2) { gap: 7px; }
.water-sidebar .map-location-row strong { font-size: 20px; }
.water-sidebar .map-location-row small { font-size: 20px; line-height: 1.5; }
.water-sidebar .map-location-row em { font-size: 18px; line-height: 1.5; }
.water-sidebar .map-location-row > b { font-size: 16px; }
.water-sidebar .map-base-summary__region strong,
.water-sidebar .map-location-row strong { font-family: 'LkywSanjiyunhei', "Microsoft YaHei", sans-serif; font-weight: 400; }
@media (max-width: 1250px) { .water-sidebar { width: 330px; }.timeline-container { left: 360px; right: 360px; } }
@media (max-width: 1050px) { .water-sidebar { width: 300px; }.timeline-container { left: 330px; right: 330px; } }
@media (max-width: 720px) {
  .water-sidebar { display: none; }
  .airport-sidebar-slot--ground { min-height: 150px; }
}
</style>

<style scoped>
/* 首页与两条故事线共用边界，展开/收起只改变预留区域。 */
.home-dashboard { --layout-sidebar-width: clamp(360px, 22vw, 440px); --layout-gap: 16px; --layout-timeline-space: 220px; }
.water-sidebar { width: var(--layout-sidebar-width); box-sizing: border-box; }
/* 时间轴使用固定画布，侧栏和相机切换不改变节点间距。 */
.timeline-container { left: 50%; right: auto; width: 1616px; min-width: 1616px; transform: translateX(-50%); }
@media(max-width:1250px) { .home-dashboard { --layout-sidebar-width: 330px; } }
@media(max-width:1050px) { .home-dashboard { --layout-sidebar-width: 300px; } }
@media(max-width:900px) { .home-dashboard { --layout-left-reserve: 16px !important; --layout-right-reserve: 16px !important; } }
</style>

<style scoped>
/* 数字人由组件统一固定到浏览器视口。 */
</style>

<style scoped>
.story-active :deep(.story-detection-alert), .story-active :deep(.collab-metrics-popup), .story-active :deep(.agent-log-popup) { max-height: calc(100% - 560px); }
</style>
