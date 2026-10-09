<template>
  <div class="simulation-container">
    <!-- 视图切换开关 -->
    <div class="view-toggle">
      <button :class="{ active: viewMode === '2d' }" @click="viewMode = '2d'">🗺️ 二维推演</button>
      <button :class="{ active: viewMode === '3d' }" @click="viewMode = '3d'">🌍 三维仿真</button>
      <button :class="{ active: viewMode === 'physics' }" @click="viewMode = 'physics'">⚙️ 物理仿真</button>
    </div>

    <!-- 城市切换开关 -->
    <div class="city-toggle">
      <button :class="{ active: currentCity === 'xiantao' }" @click="flyToCity('xiantao')">📍 仙桃市推演</button>
      <button :class="{ active: currentCity === 'huanggang' }" @click="flyToCity('huanggang')">📍 黄冈市推演</button>
    </div>

    <div id="simulationCesiumContainer" class="cesium-container" :style="{ visibility: (viewMode === '3d') ? 'visible' : 'hidden', position: 'absolute', top: '20px', left: '20px', right: '20px', bottom: '20px', width: 'auto', height: 'auto', zIndex: 1 }"></div>
    <div v-if="viewMode === '3d' && isInitializing3D" class="three-d-loading-overlay">
      正在初始化三维仿真地图…
    </div>
    <div v-else-if="viewMode === '3d' && threeDError" class="three-d-loading-overlay error">
      {{ threeDError }}
    </div>
    <!-- HUD 不依赖 Cesium 的异步 ready 标记；进入三维模式即展示并同步寻优日志。 -->
    <template v-if="viewMode === '3d'">
      <div class="three-d-vignette"></div>
      <aside class="three-d-situation-panel">
        <div class="three-d-panel-kicker"><i></i> LIVE INCIDENT</div>
        <strong>{{ activeScene === 'truck_crash' ? '货车追尾事故' : '油罐车泄露事故' }}</strong>
        <p>{{ currentCity === 'xiantao' ? '仙桃市 · 高速路段' : '黄冈市 · 化工园区' }}</p>
        <div class="three-d-risk"><span>应急响应等级</span><b>{{ activeScene === 'truck_crash' ? 'Ⅱ级' : 'Ⅰ级' }}</b></div>
        <div class="three-d-kpis"><div><b>05</b><span>联动单位</span></div><div><b>RCD</b><span>寻优策略</span></div><div><b>24</b><span>实时监测</span></div></div>
        <div class="three-d-panel-actions"><button @click="flyToCity(currentCity)">⌖ 定位现场</button><button @click="toggleThreeDFullscreen">⛶ 全屏</button></div>
      </aside>
      <aside class="three-d-force-panel">
        <div class="three-d-panel-head"><span>协同救援力量</span><em><i></i> ONLINE</em></div>
        <div class="three-d-force"><i class="medical"></i><span>医疗急救</span><b>已出动</b></div><div class="three-d-force"><i class="fire"></i><span>消防灭火</span><b>已出动</b></div><div class="three-d-force"><i class="police"></i><span>公安交警</span><b>已出动</b></div><div class="three-d-force"><i class="hazmat"></i><span>防化处置</span><b>已出动</b></div><div class="three-d-force"><i class="road"></i><span>交通路政</span><b>已出动</b></div>
      </aside>
      <aside class="three-d-optimization-log">
        <div class="three-d-log-head"><div class="three-d-log-title"><i>◈</i><div><strong>多智能体全局寻优决策日志</strong><span>GLOBAL OPTIMIZATION LOG</span></div></div><b :class="{ loading: optimizationLog.loading }">{{ optimizationLog.loading ? '同步中' : '决策已锁定' }}</b></div>
        <div class="three-d-log-terminal">
          <p><i>[SYS]</i> 启动多智能体并发寻优，读取区域 OSM 路网拓扑…</p>
          <p><i>[SYS]</i> Dijkstra 加权算法完成，动态路阻因子已纳入。</p>
          <p class="success"><i>[SYS]</i> 真实拓扑寻优比对完成，决策结果已落地。</p>
        </div>
        <div v-if="optimizationAgents.length" class="three-d-log-results">
          <div class="three-d-agent-tabs"><button v-for="agent in optimizationAgents" :key="agent.key" :class="{ active: selectedOptimizationAgentKey === agent.key }" :style="{ '--agent-color': agent.color }" @click="selectedOptimizationAgentKey = agent.key">{{ optimizationAgentShortNames[agent.key] || agent.label }}</button></div>
          <div v-if="selectedOptimizationAgent" class="three-d-agent-decision" :style="{ '--agent-color': selectedOptimizationAgent.color }">
            <template v-for="agent in [selectedOptimizationAgent]" :key="agent.key">
            <div class="three-d-agent-head"><span></span><b>{{ agent.label }}</b><strong>{{ agent.poi?.name || '最优站点已选定' }}</strong></div>
            <div class="three-d-agent-metrics"><div><span>真实路网寻优距离</span><b>{{ agent.poi?.net_dist_km ?? '--' }} km</b></div><div><span>空间直线初筛距离</span><em>{{ agent.poi?.dist_km ?? '--' }} km</em></div></div>
            <div v-if="agent.losers?.length" class="three-d-agent-losers"><span>[-] 动态路阻因子剔除名录</span><p v-for="(loser, index) in agent.losers" :key="index">✕ {{ loser.name }}<em>{{ loser.reason }}</em></p></div>
            <div v-else class="three-d-agent-losers empty">[-] 当前无被剔除候选节点</div>
            </template>
          </div>
        </div>
        <div v-else-if="!optimizationLog.loading" class="three-d-log-empty">等待协同响应寻优结果…</div>
      </aside>
    </template>

    <!-- 物理仿真不需要加载 Cesium 地图，仅在独立高性能 2D Canvas 中进行极高兼容度的物理粒子级仿真 -->
    <div v-if="viewMode === 'physics'" class="physics-simulation-container" style="position: absolute; top: 20px; left: 20px; right: 20px; bottom: 20px; z-index: 5; background: #070b19; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid rgba(0, 255, 180, 0.15);">
      <canvas id="physicsSmokeCanvas" style="width: 100%; height: 100%; display: block;"></canvas>
      
      <!-- 物理仿真状态抬头指示器 (HUD) -->
      <div class="physics-hud" style="position: absolute; top: 80px; right: 20px; color: #00ffd8; font-family: monospace; background: rgba(8,12,28,0.85); padding: 15px; border-radius: 6px; border: 1px solid rgba(0,255,180,0.3); font-size: 14px; pointer-events: none; line-height: 1.6; z-index: 10; box-shadow: 0 0 15px rgba(0,0,0,0.5);">
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px; border-bottom: 1px solid rgba(0,255,180,0.3); padding-bottom: 4px; color: #fff;">📡 物理粒子引擎监控</div>
        <div>当前区域: <span style="color: #fff;">{{ currentCity === 'xiantao' ? '仙桃市' : '黄冈市' }}</span></div>
        <div>当前场景: <span style="color: #fff;">{{ activeScene === 'truck_crash' ? '客车追尾现场' : '油罐车泄露现场' }}</span></div>
        <div>当前阶段: <span style="color: #fff;">{{ activeAccidentPhases[activePhaseIndex]?.shortLabel || '未知' }}</span></div>
        <div>环境风速: <span style="color: #ffb700; font-weight: bold;">{{ currentWindSpeed }} m/s</span></div>
        <div>环境风向: <span style="color: #ffb700; font-weight: bold;">{{ currentWindDirection }}° ({{ getWindDirectionText(currentWindDirection) }})</span></div>
        <div>活跃粒子: <span style="color: #00ffd8; font-weight: bold;">{{ activeParticleCount }} / 600</span></div>
      </div>
    </div>
    
    <div v-if="viewMode === '2d'" class="cesium-container iframe-container" style="position: absolute; top: 20px; left: 20px; right: 20px; bottom: 20px; z-index: 10; width: auto; height: auto;">
      <div v-if="isGenerating2D" class="loading-overlay">
        <div class="spinner"></div>
        <span>正在生成二维推演...</span>
      </div>
      <div v-else-if="errorMessage" class="error-overlay">
        <div class="error-icon">⚠️</div>
        <span>{{ errorMessage }}</span>
        <button class="retry-btn" @click="generate2DDeduction(currentCity)">重试</button>
      </div>
      <iframe v-else :key="twoDimensionalRunKey" :src="iframeSrc" class="deduction-iframe"></iframe>
    </div>

    <!-- 物理仿真控制面板 -->
    <div v-if="viewMode === 'physics'" class="physics-tweak-panel">
      <div class="physics-tweak-header">
        <span class="icon">⚙️</span>
        <span class="title">物理仿真 - 粒子微调面板</span>
      </div>

      <div class="physics-tweak-body">
        <!-- 事故现场选择 -->
        <div class="section-title">📍 事故现场切换</div>
        <div class="phase-selector" style="margin-bottom: 8px;">
          <button 
            :class="{ active: activeScene === 'truck_crash' }"
            @click="changeScene('truck_crash')"
            class="phase-btn"
          >
            🚌 客车追尾现场
          </button>
          <button 
            :class="{ active: activeScene === 'tanker_leak' }"
            @click="changeScene('tanker_leak')"
            class="phase-btn"
          >
            ⛽ 油罐车泄露现场
          </button>
        </div>

        <!-- 阶段选择 -->
        <div class="section-title">📅 推演阶段选择</div>
        <div class="phase-selector" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
          <button 
            v-for="(phase, index) in activeAccidentPhases" 
            :key="phase.id"
            v-show="index >= 2"
            :class="{ active: activePhaseIndex === index }"
            @click="selectPhase(index)"
            class="phase-btn"
            style="padding: 8px 4px; font-size: 13px; min-height: 40px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            :title="phase.shortLabel"
          >
            {{ phase.shortLabel }}
          </button>
        </div>

        <!-- 粒子系统 Tab 选择 (根据城市不同，仙桃市有烟雾/火焰，黄冈市有泄露扩散) -->
        <div class="section-title">📡 粒子系统选择</div>
        <div class="physics-tab-header">
          <template v-if="currentCity === 'xiantao'">
            <button 
              :class="{ active: activePhysicsTab === 'smoke' }" 
              @click="activePhysicsTab = 'smoke'"
              class="tab-btn"
            >
              🌫️ 烟雾粒子
            </button>
            <button 
              :class="{ active: activePhysicsTab === 'fire' }" 
              @click="activePhysicsTab = 'fire'"
              class="tab-btn"
            >
              🔥 火焰粒子
            </button>
          </template>
          <template v-else>
            <button 
              :class="{ active: activePhysicsTab === 'diffusion' }" 
              @click="activePhysicsTab = 'diffusion'"
              class="tab-btn"
            >
              🤢 泄漏扩散粒子
            </button>
          </template>
        </div>

        <!-- 烟雾粒子调节项 -->
        <div v-if="activePhysicsTab === 'smoke' && currentCity === 'xiantao'" class="tweak-controls">
          <div class="control-row">
            <label>粒子宽度 (Width)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.imageWidth" min="2" max="50" step="1" />
              <span class="val-text">{{ smokeAdjust.imageWidth }}px</span>
            </div>
          </div>
          <div class="control-row">
            <label>粒子高度 (Height)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.imageHeight" min="2" max="50" step="1" />
              <span class="val-text">{{ smokeAdjust.imageHeight }}px</span>
            </div>
          </div>
          <div class="control-row">
            <label>发射速率 (Rate)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.emissionRate" min="5" max="150" step="1" />
              <span class="val-text">{{ smokeAdjust.emissionRate }}</span>
            </div>
          </div>
          <div class="control-row">
            <label>最大速度 (Speed)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.maxSpeed" min="0.5" max="10.0" step="0.1" />
              <span class="val-text">{{ smokeAdjust.maxSpeed }}m/s</span>
            </div>
          </div>
          <div class="control-row">
            <label>最小寿命 (MinLife)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.minLife" min="0.5" max="10.0" step="0.1" />
              <span class="val-text">{{ smokeAdjust.minLife }}s</span>
            </div>
          </div>
          <div class="control-row">
            <label>最大寿命 (MaxLife)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.maxLife" min="0.5" max="10.0" step="0.1" />
              <span class="val-text">{{ smokeAdjust.maxLife }}s</span>
            </div>
          </div>
        </div>

        <!-- 火焰粒子调节项 -->
        <div v-if="activePhysicsTab === 'fire' && currentCity === 'xiantao'" class="tweak-controls">
          <div class="control-row">
            <label>粒子宽度 (Width)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.imageWidth" min="2" max="50" step="1" />
              <span class="val-text">{{ fireAdjust.imageWidth }}px</span>
            </div>
          </div>
          <div class="control-row">
            <label>粒子高度 (Height)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.imageHeight" min="2" max="50" step="1" />
              <span class="val-text">{{ fireAdjust.imageHeight }}px</span>
            </div>
          </div>
          <div class="control-row">
            <label>发射速率 (Rate)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.emissionRate" min="0" max="150" step="1" />
              <span class="val-text">{{ fireAdjust.emissionRate }}</span>
            </div>
          </div>
          <div class="control-row">
            <label>最大速度 (Speed)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.maxSpeed" min="0.5" max="12.0" step="0.1" />
              <span class="val-text">{{ fireAdjust.maxSpeed }}m/s</span>
            </div>
          </div>
          <div class="control-row">
            <label>最小寿命 (MinLife)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.minLife" min="0.5" max="8.0" step="0.1" />
              <span class="val-text">{{ fireAdjust.minLife }}s</span>
            </div>
          </div>
          <div class="control-row">
            <label>最大寿命 (MaxLife)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.maxLife" min="0.5" max="8.0" step="0.1" />
              <span class="val-text">{{ fireAdjust.maxLife }}s</span>
            </div>
          </div>
        </div>

        <!-- 泄漏扩散粒子调节项 -->
        <div v-if="activePhysicsTab === 'diffusion' && currentCity === 'huanggang'" class="tweak-controls">
          <div class="control-row">
            <label>粒子宽度 (Width)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.imageWidth" min="2" max="40" step="1" />
              <span class="val-text">{{ diffusionAdjust.imageWidth }}px</span>
            </div>
          </div>
          <div class="control-row">
            <label>粒子高度 (Height)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.imageHeight" min="2" max="40" step="1" />
              <span class="val-text">{{ diffusionAdjust.imageHeight }}px</span>
            </div>
          </div>
          <div class="control-row">
            <label>发射速率 (Rate)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.emissionRate" min="5" max="250" step="1" />
              <span class="val-text">{{ diffusionAdjust.emissionRate }}</span>
            </div>
          </div>
          <div class="control-row">
            <label>最大速度 (Speed)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.maxSpeed" min="0.5" max="12.0" step="0.1" />
              <span class="val-text">{{ diffusionAdjust.maxSpeed }}m/s</span>
            </div>
          </div>
          <div class="control-row">
            <label>最小寿命 (MinLife)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.minLife" min="0.5" max="10.0" step="0.1" />
              <span class="val-text">{{ diffusionAdjust.minLife }}s</span>
            </div>
          </div>
          <div class="control-row">
            <label>最大寿命 (MaxLife)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.maxLife" min="0.5" max="10.0" step="0.1" />
              <span class="val-text">{{ diffusionAdjust.maxLife }}s</span>
            </div>
          </div>
        </div>

        <!-- 🍃 物理环境与自然因素模拟 -->
        <div class="section-title" style="margin-top: 15px; border-top: 1px solid rgba(0, 255, 180, 0.15); padding-top: 12px; display: flex; align-items: center; gap: 6px;">
          <span>🍃 物理环境与自然因素</span>
        </div>
        <div class="tweak-controls environment-controls" style="background: rgba(0, 255, 180, 0.04); border: 1px solid rgba(0, 255, 180, 0.12);">
          <div class="control-row">
            <label>环境风速 (Wind Speed)</label>
            <div class="slider-group">
              <input type="range" v-model.number="globalWindSpeed" min="0.0" max="25.0" step="0.5" />
              <span class="val-text">{{ globalWindSpeed }}m/s</span>
            </div>
          </div>
          <div class="control-row">
            <label>环境风向 (Wind Direction)</label>
            <div class="slider-group">
              <input type="range" v-model.number="globalWindDirection" min="0" max="360" step="5" />
              <span class="val-text">{{ globalWindDirection }}° ({{ getWindDirectionText(globalWindDirection) }})</span>
            </div>
          </div>
          <div class="control-row" v-if="currentCity === 'xiantao'">
            <label>上升气流/浮力 (Gravity/Updraft)</label>
            <div class="slider-group">
              <input type="range" v-model.number="globalGravity" min="0.0" max="10.0" step="0.1" />
              <span class="val-text">{{ globalGravity }}</span>
            </div>
          </div>
          <div class="control-row" v-if="currentCity === 'huanggang'">
            <label>环境阻力/阻尼 (Drag/Resistance)</label>
            <div class="slider-group">
              <input type="range" v-model.number="globalDrag" min="0.80" max="1.00" step="0.01" />
              <span class="val-text">{{ globalDrag }}</span>
            </div>
          </div>
        </div>

        <!-- 辅助按钮 -->
        <div class="panel-actions">
          <button @click="resetTweakParams" class="action-btn secondary">🔄 重置参数</button>
          <button @click="copyTweakParams" class="action-btn primary">📋 复制参数</button>
        </div>
        <div v-if="copiedMessage" class="copied-feedback">{{ copiedMessage }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, reactive, watch, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'

import * as Cesium from 'cesium'
import { getCollaborativeCommandCenterBaseUrl } from '../config/subsystems'

Cesium.Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIyYTUwYmE4Zi01ZjZlLTQ0MjAtYWMwNS0yYjBkZGFiM2RmOTUiLCJpZCI6MzU4MzQ0LCJpYXQiOjE3NjI1Nzc2NjR9.q9QoG-_99QZ2R2TlUYjiWGhn0-S5I22FFGuou_NAE3Q"

const viewMode = ref('2d')
const iframeSrc = ref('')
const isGenerating2D = ref(false)
const errorMessage = ref('')
const twoDimensionalRunKey = ref(0)
const isInitializing3D = ref(false)
const threeDError = ref('')
const is3DReady = ref(false)
const hoveredCityName = ref('')
const tooltipStyle = ref({
  left: '0px',
  top: '0px'
})

let viewer = null
let currentCzmlDataSource = null
let smokeParticle = null
let fireParticle = null
let diffusionParticle = null
let diffusionStartTime = null
let preRenderListener = null
let mouseHandler = null
let persistentCityEntities = []
let initSimulationViewerTimeout = null
let removeLightListener = null
let isSimulationViewerInitializing = false
const route = useRoute()

const currentCity = ref(route.query.city === 'huanggang' ? 'huanggang' : 'xiantao')

// 三维推演默认采用区域总览视角：完整保留行政边界、事故现场和五类救援路线。
const THREE_D_OVERVIEW = {
  xiantao: { lng: 113.28, lat: 30.40, height: 145000 },
  huanggang: { lng: 114.87, lat: 30.61, height: 150000 }
}

const flyToThreeDOverview = (city = currentCity.value, duration = 2.0) => {
  if (!viewer) return
  const view = THREE_D_OVERVIEW[city] || THREE_D_OVERVIEW.xiantao
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(view.lng, view.lat, view.height),
    orientation: { heading: 0, pitch: -Cesium.Math.PI_OVER_TWO, roll: 0 },
    duration
  })
}

// 默认 Cesium 影像依赖 Ion 在线资产；当该资产在当前网络环境中不可用时，
// 场景仍会正常渲染，但地表会退化为黑色。三维仿真固定使用与首页相同的
// ArcGIS 卫星影像，并只在成功取得 provider 后替换默认图层，避免出现空底图。
const configureSimulationBasemap = async () => {
  if (!viewer) return
  const targetViewer = viewer

  try {
    const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
    )
    if (viewer !== targetViewer || targetViewer.isDestroyed()) return

    targetViewer.imageryLayers.removeAll(true)
    const layer = targetViewer.imageryLayers.addImageryProvider(imagery)
    // 轻微提亮，确保卫星图在深色 HUD 与夜间视觉配置下仍清晰可辨。
    layer.brightness = 1.08
    layer.contrast = 1.04
    layer.gamma = 1.0
    console.info('[Cesium Simulation] 卫星影像底图加载成功')
  } catch (error) {
    // 不清除 Cesium 已创建的默认图层。这样即使备用服务暂时不可用，
    // 仍可继续使用已成功加载的任何默认瓦片，而不会退化为空白地球。
    console.warn('[Cesium Simulation] 卫星影像底图加载失败，保留默认底图:', error)
  }
}

const optimizationLog = reactive({ loading: false, data: null })
const optimizationAgentOrder = ['fire', 'medical', 'police', 'hazmat', 'road']
const optimizationAgentShortNames = { fire: '消防', medical: '医疗', police: '公安', hazmat: '防化', road: '路政' }
const selectedOptimizationAgentKey = ref('fire')
const optimizationAgents = computed(() => {
  const agents = optimizationLog.data?.agents
  if (!agents) return []
  return optimizationAgentOrder
    .filter(key => agents[key])
    .map(key => ({ key, ...agents[key] }))
})
const selectedOptimizationAgent = computed(() =>
  optimizationAgents.value.find(agent => agent.key === selectedOptimizationAgentKey.value) || optimizationAgents.value[0] || null
)

const fetchOptimizationLog = async (city = currentCity.value) => {
  optimizationLog.loading = true
  const scenario = city === 'huanggang' ? 'leak' : 'crash'
  try {
    const baseUrl = getCollaborativeCommandCenterBaseUrl()
    const response = await fetch(`${baseUrl}/api/strategy_metrics?scenario=${scenario}`, { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload = await response.json()
    optimizationLog.data = payload?.multi_agent?.agents ? payload.multi_agent : null
    if (optimizationLog.data?.agents && !optimizationLog.data.agents[selectedOptimizationAgentKey.value]) {
      selectedOptimizationAgentKey.value = optimizationAgentOrder.find(key => optimizationLog.data.agents[key]) || ''
    }
  } catch (error) {
    console.warn('读取协同响应多智能体寻优日志失败:', error)
  } finally {
    optimizationLog.loading = false
  }
}

const toggleThreeDFullscreen = async () => {
  const target = document.querySelector('.simulation-container')
  if (!target) return

  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    } else {
      await target.requestFullscreen()
    }
  } catch (error) {
    console.warn('切换三维推演全屏失败:', error)
  }
}

// 事故现场与坐标配置
const activeScene = ref('truck_crash') // 默认：客车追尾现场

const scenePositions = {
  xiantao: {
    truck_crash: { lng: 113.104833, lat: 30.385469 },
    tanker_leak: { lng: 113.100800, lat: 30.382000 }
  },
  huanggang: {
    truck_crash: { lng: 114.873321, lat: 30.607381 },
    tanker_leak: { lng: 114.870000, lat: 30.603000 }
  }
}

// 物理仿真模式下粒子微调相关的响应式状态
// 物理仿真模式下粒子微调相关的响应式状态
const activePhysicsTab = ref('smoke')
const activePhaseIndex = ref(5) // 默认推演第 5 阶段
const selectedPhase = activePhaseIndex // 别名，确保向后兼容

const accidentsList = [
  { id: 'rear-end', title: '客车追尾现场' },
  { id: 'leakage', title: '油罐车泄露现场' }
]

const accidentPoints = [
  {
    id: 'rear-end',
    title: '客车追尾现场',
    phases: [
      { id: 't-start', time: '14:00', shortLabel: '仿真开始', title: '仿真推演开始' },
      { id: 't-normal', time: '14:05', shortLabel: '正常行驶', title: '车辆正常行驶阶段' },
      { id: 't-accident', time: '14:12', shortLabel: '事故发生', title: '客车追尾事故瞬间' },
      { id: 't-uav-dispatch', time: '14:14', shortLabel: '无人机出动', title: '无人机出动' },
      { id: 't-uav-recon', time: '14:15', shortLabel: '无人机侦察', title: '无人机快速出动侦察' },
      { id: 't-smoke', time: '14:18', shortLabel: '次生灾害（烟雾）', title: '事故现场产生大量烟雾' },
      { id: 't-fire', time: '14:26', shortLabel: '次生灾害（起火）', title: '事故车辆开始起火' },
      { id: 't-uav-start', time: '14:30', shortLabel: '无人装备出动', title: '无人装备协同出动' },
      { id: 't-uav-deploy', time: '14:35', shortLabel: '无人感知部署', title: '无人感知节点部署' },
      { id: 't-uav-exec', time: '14:40', shortLabel: '无人感知执行', title: '无人感知任务执行' },
      { id: 't-signal', time: '14:45', shortLabel: '信号干扰', title: '通信信号受到干扰' },
      { id: 't-rescue-start', time: '14:50', shortLabel: '救援装备出动', title: '专业救援装备协同出动' },
    ]
  },
  {
    id: 'leakage',
    title: '油罐车泄露现场',
    phases: [
      { id: 'l-start', time: '15:00', shortLabel: '仿真开始', title: '油罐车仿真推演开始' },
      { id: 'l-normal', time: '15:05', shortLabel: '正常行驶', title: '油罐车正常行驶阶段' },
      { id: 'l-accident', time: '15:12', shortLabel: '事故发生（侧翻）', title: '油罐车发生侧翻事故' },
      { id: 'l-uav-dispatch', time: '15:14', shortLabel: '无人机出动', title: '无人机出动' },
      { id: 'l-uav-recon', time: '15:15', shortLabel: '无人机侦察', title: '无人机快速出动侦察' },
      { id: 'l-leak', time: '15:20', shortLabel: '次生灾害（泄露）', title: '罐体受损开始发生化学品泄露' },
      { id: 'l-fill', time: '15:35', shortLabel: '次生灾害（弥漫）', title: '泄露液体开始向四周大面积弥漫' },
      { id: 'l-uav-start', time: '15:40', shortLabel: '无人装备出动', title: '无人装备协同出动' },
      { id: 'l-uav-deploy', time: '15:45', shortLabel: '无人感知部署', title: '无人感知节点部署' },
      { id: 'l-uav-exec', time: '15:50', shortLabel: '无人感知执行', title: '无人感知任务执行' },
      { id: 'l-signal', time: '15:55', shortLabel: '信号干扰', title: '通信信号受到干扰' },
      { id: 'l-rescue-start', time: '16:00', shortLabel: '救援装备出动', title: '专业救援装备协同出动' },
    ]
  }
]

const activeAccidentIndex = computed({
  get: () => activeScene.value === 'truck_crash' ? 0 : 1,
  set: (val) => {
    const sceneName = val === 0 ? 'truck_crash' : 'tanker_leak'
    const city = val === 0 ? 'xiantao' : 'huanggang'
    currentCity.value = city
    activeScene.value = sceneName
    activePhysicsTab.value = val === 0 ? 'smoke' : 'diffusion'
    
    // 即使 viewer 为 null，也要正常更新预设
    selectPhase(activePhaseIndex.value)
    
    // 如果 viewer 不为空，触发相应动作
    if (viewer) {
      loadCityMask(city)
      updateParticlesVisibility(city)
      const coords = scenePositions[city][sceneName]
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(coords.lng, coords.lat, city === 'xiantao' ? 1500 : 2000),
        orientation: {
          heading: Cesium.Math.toRadians(0.0),
          pitch: Cesium.Math.toRadians(-35.0),
          roll: 0.0
        },
        duration: 2.0
      })
    }
  }
})

const activeAccidentPhases = computed(() => {
  return accidentPoints[activeAccidentIndex.value]?.phases || []
})

const isRescueDispatchPhase = (phaseIndex = activePhaseIndex.value) => {
  return activeAccidentPhases.value[Number(phaseIndex)]?.id?.endsWith('rescue-start') || false
}

const phasesReadyList = computed(() => {
  return Array(activeAccidentPhases.value.length).fill(true)
})

let simulationEntities = []

const copiedMessage = ref('')

const globalWindSpeed = ref(3.0)
const globalWindDirection = ref(45.0)
const globalGravity = ref(2.5)
const globalDrag = ref(0.98)

watch(globalWindSpeed, (newVal) => {
  smokeAdjust.windSpeed = newVal
  fireAdjust.windSpeed = newVal
  diffusionAdjust.windSpeed = newVal
})

watch(globalWindDirection, (newVal) => {
  smokeAdjust.windDirection = newVal
  fireAdjust.windDirection = newVal
  diffusionAdjust.windDirection = newVal
})

watch(globalGravity, (newVal) => {
  smokeAdjust.gravity = newVal
  fireAdjust.gravity = newVal
  diffusionAdjust.gravity = newVal
})

watch(globalDrag, (newVal) => {
  smokeAdjust.drag = newVal
  fireAdjust.drag = newVal
  diffusionAdjust.drag = newVal
})

const smokeAdjust = reactive({
  imageWidth: 25,
  imageHeight: 25,
  emissionRate: 60.0,
  maxSpeed: 5.0,
  minLife: 2.0,
  maxLife: 4.5,
  gravity: 2.5,
  windSpeed: 3.0,
  windDirection: 45.0
})

const fireAdjust = reactive({
  imageWidth: 25,
  imageHeight: 25,
  emissionRate: 65.0,
  maxSpeed: 7.0,
  minLife: 1.0,
  maxLife: 2.5,
  gravity: 5.0,
  windSpeed: 3.0,
  windDirection: 45.0
})

const diffusionAdjust = reactive({
  imageWidth: 9,
  imageHeight: 9,
  emissionRate: 120.0,
  maxSpeed: 5.5,
  minLife: 4.0,
  maxLife: 6.5,
  drag: 0.96,
  windSpeed: 3.0,
  windDirection: 45.0
})

// 各个阶段的烟雾/火焰/扩散粒子预设配置
function selectPhase(phaseIndex) {
  activePhaseIndex.value = phaseIndex;
  return;
  
  if (activeScene.value === 'truck_crash') {
    // 事故线A：货车追尾现场
    if (currentCity.value === 'xiantao') {
      if (phaseIndex === 3) { // 事故发生
        smokeAdjust.imageWidth = 18;
        smokeAdjust.imageHeight = 18;
        smokeAdjust.emissionRate = 40;
        smokeAdjust.maxSpeed = 3.0;
        smokeAdjust.minLife = 1.5;
        smokeAdjust.maxLife = 3.5;
        smokeAdjust.gravity = 1.8;
        smokeAdjust.windSpeed = 3.0;
        smokeAdjust.windDirection = 45.0; // 东北偏向风
        
        fireAdjust.emissionRate = 0;
        if (smokeParticle) smokeParticle.show = true;
        if (fireParticle) fireParticle.show = false;
      } else if (phaseIndex === 3 || phaseIndex === 4) { // 无人机出动 / 无人机侦察 (use accident effects, maybe keep same as phase 3/4)
      } else if (phaseIndex === 5) { // 初期爆发
        smokeAdjust.imageWidth = 25;
        smokeAdjust.imageHeight = 25;
        smokeAdjust.emissionRate = 70;
        smokeAdjust.maxSpeed = 4.5;
        smokeAdjust.minLife = 2.0;
        smokeAdjust.maxLife = 4.5;
        smokeAdjust.gravity = 2.2;
        smokeAdjust.windSpeed = 5.0;
        smokeAdjust.windDirection = 60.0;

        fireAdjust.imageWidth = 18;
        fireAdjust.imageHeight = 18;
        fireAdjust.emissionRate = 35;
        fireAdjust.maxSpeed = 4.0;
        fireAdjust.minLife = 1.0;
        fireAdjust.maxLife = 2.0;
        fireAdjust.gravity = 3.5;
        fireAdjust.windSpeed = 5.0;
        fireAdjust.windDirection = 60.0;
        if (smokeParticle) smokeParticle.show = true;
        if (fireParticle) fireParticle.show = true;
      } else if (phaseIndex === 6) { // 剧烈燃烧
        smokeAdjust.imageWidth = 38;
        smokeAdjust.imageHeight = 38;
        smokeAdjust.emissionRate = 110;
        smokeAdjust.maxSpeed = 6.5;
        smokeAdjust.minLife = 2.5;
        smokeAdjust.maxLife = 5.0;
        smokeAdjust.gravity = 3.0;
        smokeAdjust.windSpeed = 10.0; // 大风造成迅速蔓延
        smokeAdjust.windDirection = 90.0; // 正东风，烟雾及火焰大范围向东飘逸

        fireAdjust.imageWidth = 32;
        fireAdjust.imageHeight = 32;
        fireAdjust.emissionRate = 95;
        fireAdjust.maxSpeed = 8.5;
        fireAdjust.minLife = 1.5;
        fireAdjust.maxLife = 2.5;
        fireAdjust.gravity = 5.5;
        fireAdjust.windSpeed = 10.0;
        fireAdjust.windDirection = 90.0;
        if (smokeParticle) smokeParticle.show = true;
        if (fireParticle) fireParticle.show = true;
      } else if (phaseIndex === 7) { // 控制减弱
        smokeAdjust.imageWidth = 15;
        smokeAdjust.imageHeight = 15;
        smokeAdjust.emissionRate = 20;
        smokeAdjust.maxSpeed = 2.0;
        smokeAdjust.minLife = 1.0;
        smokeAdjust.maxLife = 2.5;
        smokeAdjust.gravity = 1.2;
        smokeAdjust.windSpeed = 2.5;
        smokeAdjust.windDirection = 120.0;

        fireAdjust.imageWidth = 10;
        fireAdjust.imageHeight = 10;
        fireAdjust.emissionRate = 5;
        fireAdjust.maxSpeed = 1.5;
        fireAdjust.minLife = 0.5;
        fireAdjust.maxLife = 1.0;
        fireAdjust.gravity = 1.8;
        fireAdjust.windSpeed = 2.5;
        fireAdjust.windDirection = 120.0;
        if (smokeParticle) smokeParticle.show = true;
        if (fireParticle) fireParticle.show = true;
      }
    } else {
      // 黄冈市泄露扩散 (货车追尾引发的泄露/起火等扩散)
      if (phaseIndex === 3 || phaseIndex === 4) {
        diffusionAdjust.imageWidth = 6;
        diffusionAdjust.imageHeight = 6;
        diffusionAdjust.emissionRate = 30;
        diffusionAdjust.maxSpeed = 2.0;
        diffusionAdjust.minLife = 2.5;
        diffusionAdjust.maxLife = 4.5;
        diffusionAdjust.drag = 0.98;
        diffusionAdjust.windSpeed = 3.0;
        diffusionAdjust.windDirection = 45.0;
      } else if (phaseIndex === 5) {
        diffusionAdjust.imageWidth = 9;
        diffusionAdjust.imageHeight = 9;
        diffusionAdjust.emissionRate = 75;
        diffusionAdjust.maxSpeed = 4.0;
        diffusionAdjust.minLife = 3.5;
        diffusionAdjust.maxLife = 6.0;
        diffusionAdjust.drag = 0.96;
        diffusionAdjust.windSpeed = 5.0;
        diffusionAdjust.windDirection = 60.0;
      } else if (phaseIndex === 6) {
        diffusionAdjust.imageWidth = 15;
        diffusionAdjust.imageHeight = 15;
        diffusionAdjust.emissionRate = 135;
        diffusionAdjust.maxSpeed = 6.5;
        diffusionAdjust.minLife = 4.5;
        diffusionAdjust.maxLife = 7.5;
        diffusionAdjust.drag = 0.94;
        diffusionAdjust.windSpeed = 10.0;
        diffusionAdjust.windDirection = 90.0;
      } else if (phaseIndex === 7) {
        diffusionAdjust.imageWidth = 5;
        diffusionAdjust.imageHeight = 5;
        diffusionAdjust.emissionRate = 15;
        diffusionAdjust.maxSpeed = 1.5;
        diffusionAdjust.minLife = 1.8;
        diffusionAdjust.maxLife = 3.5;
        diffusionAdjust.drag = 0.97;
        diffusionAdjust.windSpeed = 2.5;
        diffusionAdjust.windDirection = 120.0;
      }
    }
  } else {
    // 事故线B：油罐车泄露现场
    if (currentCity.value === 'xiantao') {
      // 仙桃市发生油罐车泄露，引发流淌火灾和剧烈烟雾
      if (phaseIndex === 3 || phaseIndex === 4) {
        smokeAdjust.imageWidth = 15;
        smokeAdjust.imageHeight = 15;
        smokeAdjust.emissionRate = 35;
        smokeAdjust.maxSpeed = 2.5;
        smokeAdjust.minLife = 1.8;
        smokeAdjust.maxLife = 3.5;
        smokeAdjust.gravity = 1.5;
        smokeAdjust.windSpeed = 1.5;
        smokeAdjust.windDirection = 270.0; // 偏西风
        
        fireAdjust.emissionRate = 0;
        if (smokeParticle) smokeParticle.show = true;
        if (fireParticle) fireParticle.show = false;
      } else if (phaseIndex === 5) {
        smokeAdjust.imageWidth = 22;
        smokeAdjust.imageHeight = 22;
        smokeAdjust.emissionRate = 60;
        smokeAdjust.maxSpeed = 4.0;
        smokeAdjust.minLife = 2.2;
        smokeAdjust.maxLife = 4.8;
        smokeAdjust.gravity = 2.0;
        smokeAdjust.windSpeed = 4.5;
        smokeAdjust.windDirection = 240.0;

        fireAdjust.imageWidth = 15;
        fireAdjust.imageHeight = 15;
        fireAdjust.emissionRate = 25;
        fireAdjust.maxSpeed = 3.5;
        fireAdjust.minLife = 0.8;
        fireAdjust.maxLife = 1.8;
        fireAdjust.gravity = 3.0;
        fireAdjust.windSpeed = 4.5;
        fireAdjust.windDirection = 240.0;
        if (smokeParticle) smokeParticle.show = true;
        if (fireParticle) fireParticle.show = true;
      } else if (phaseIndex === 6) {
        smokeAdjust.imageWidth = 32;
        smokeAdjust.imageHeight = 32;
        smokeAdjust.emissionRate = 85;
        smokeAdjust.maxSpeed = 5.5;
        smokeAdjust.minLife = 2.5;
        smokeAdjust.maxLife = 5.2;
        smokeAdjust.gravity = 2.8;
        smokeAdjust.windSpeed = 12.0; // 猛烈风速
        smokeAdjust.windDirection = 210.0; // 吹向东北，覆盖面积广

        fireAdjust.imageWidth = 26;
        fireAdjust.imageHeight = 26;
        fireAdjust.emissionRate = 75;
        fireAdjust.maxSpeed = 6.5;
        fireAdjust.minLife = 1.2;
        fireAdjust.maxLife = 2.6;
        fireAdjust.gravity = 5.0;
        fireAdjust.windSpeed = 12.0;
        fireAdjust.windDirection = 210.0;
        if (smokeParticle) smokeParticle.show = true;
        if (fireParticle) fireParticle.show = true;
      } else if (phaseIndex === 7) {
        smokeAdjust.imageWidth = 10;
        smokeAdjust.imageHeight = 10;
        smokeAdjust.emissionRate = 12;
        smokeAdjust.maxSpeed = 1.5;
        smokeAdjust.minLife = 1.0;
        smokeAdjust.maxLife = 2.0;
        smokeAdjust.gravity = 1.0;
        smokeAdjust.windSpeed = 3.0;
        smokeAdjust.windDirection = 180.0;

        fireAdjust.emissionRate = 0;
        if (smokeParticle) smokeParticle.show = true;
        if (fireParticle) fireParticle.show = false;
      }
    } else {
      // 黄冈市泄露扩散 (油罐车气体大量扩散)
      if (phaseIndex === 3 || phaseIndex === 4) {
        diffusionAdjust.imageWidth = 8;
        diffusionAdjust.imageHeight = 8;
        diffusionAdjust.emissionRate = 35;
        diffusionAdjust.maxSpeed = 2.5;
        diffusionAdjust.minLife = 3.0;
        diffusionAdjust.maxLife = 5.0;
        diffusionAdjust.drag = 0.98;
        diffusionAdjust.windSpeed = 1.5;
        diffusionAdjust.windDirection = 270.0;
      } else if (phaseIndex === 5) {
        diffusionAdjust.imageWidth = 12;
        diffusionAdjust.imageHeight = 12;
        diffusionAdjust.emissionRate = 80;
        diffusionAdjust.maxSpeed = 4.5;
        diffusionAdjust.minLife = 4.0;
        diffusionAdjust.maxLife = 6.5;
        diffusionAdjust.drag = 0.96;
        diffusionAdjust.windSpeed = 4.5;
        diffusionAdjust.windDirection = 240.0;
      } else if (phaseIndex === 6) {
        diffusionAdjust.imageWidth = 22;
        diffusionAdjust.imageHeight = 22;
        diffusionAdjust.emissionRate = 180;
        diffusionAdjust.maxSpeed = 8.5;
        diffusionAdjust.minLife = 5.0;
        diffusionAdjust.maxLife = 8.5;
        diffusionAdjust.drag = 0.93;
        diffusionAdjust.windSpeed = 12.0; // 强气流风速，有毒气云迅速推开
        diffusionAdjust.windDirection = 210.0;
      } else if (phaseIndex === 7) {
        diffusionAdjust.imageWidth = 6;
        diffusionAdjust.imageHeight = 6;
        diffusionAdjust.emissionRate = 15;
        diffusionAdjust.maxSpeed = 2.0;
        diffusionAdjust.minLife = 2.0;
        diffusionAdjust.maxLife = 4.0;
        diffusionAdjust.drag = 0.97;
        diffusionAdjust.windSpeed = 3.0;
        diffusionAdjust.windDirection = 180.0;
      }
    }
  }
}

const changeScene = (sceneName) => {
  activeScene.value = sceneName
  const city = sceneName === 'truck_crash' ? 'xiantao' : 'huanggang'
  currentCity.value = city
  
  if (viewer) {
    loadCityMask(city)
    updateParticlesVisibility(city)
    const coords = scenePositions[city][sceneName]
    
    if (city === 'xiantao') {
      if (smokeParticle) {
        adjustParticleHeight(smokeParticle, coords.lng, coords.lat, 2.0)
      }
      if (fireParticle) {
        adjustParticleHeight(fireParticle, coords.lng, coords.lat, 2.0)
      }
    } else {
      if (diffusionParticle) {
        adjustParticleHeight(diffusionParticle, coords.lng, coords.lat, 2.8)
      }
    }

    // 相机对焦至新的事故现场
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(coords.lng, coords.lat, city === 'xiantao' ? 1500 : 2000),
      orientation: {
        heading: Cesium.Math.toRadians(0.0),
        pitch: Cesium.Math.toRadians(-35.0),
        roll: 0.0
      },
      duration: 2.0
    })
  }

  // 刷新预设参数
  selectPhase(activePhaseIndex.value)
}

const resetTweakParams = () => {
  selectPhase(selectedPhase.value)
}

const copyTweakParams = () => {
  let content = ''
  if (currentCity.value === 'xiantao') {
    if (activePhysicsTab.value === 'smoke') {
      content = JSON.stringify(smokeAdjust, null, 2)
    } else {
      content = JSON.stringify(fireAdjust, null, 2)
    }
  } else {
    content = JSON.stringify(diffusionAdjust, null, 2)
  }
  
  navigator.clipboard.writeText(content).then(() => {
    copiedMessage.value = '参数配置已复制到剪切板！'
    setTimeout(() => {
      copiedMessage.value = ''
    }, 2000)
  }).catch(err => {
    console.error('复制失败:', err)
  })
}

// 重新计算并提供各阶段的动态粒子预设参数（针对全部 10 个阶段）
function get2DParticleConfig(phaseIndex) {
  const isTruck = activeScene.value === 'truck_crash'
  const config = {
    smoke: { imageWidth: 25, imageHeight: 25, emissionRate: 60, maxSpeed: 5.0, minLife: 2.0, maxLife: 4.5, gravity: 2.5, windSpeed: 3.0, windDirection: 45.0 },
    fire: { imageWidth: 25, imageHeight: 25, emissionRate: 65, maxSpeed: 7.0, minLife: 1.0, maxLife: 2.5, gravity: 5.0, windSpeed: 3.0, windDirection: 45.0 },
    diffusion: { imageWidth: 9, imageHeight: 9, emissionRate: 120, maxSpeed: 5.5, minLife: 4.0, maxLife: 6.5, drag: 0.96, windSpeed: 3.0, windDirection: 45.0 }
  }
  
  if (isTruck) {
    if (phaseIndex <= 1) { // 仿真开始/正常行驶
      config.smoke.emissionRate = 0
      config.fire.emissionRate = 0
    } else if (phaseIndex >= 2 && phaseIndex <= 4) { // 事故发生 / 无人机出动 / 无人机侦察 (暂无大范围烟雾与火焰)
      config.smoke.emissionRate = 0
      config.fire.emissionRate = 0
    } else if (phaseIndex === 5) { // 次生灾害（烟雾）
      config.smoke.emissionRate = 70
      config.fire.emissionRate = 0
    } else if (phaseIndex === 6) { // 次生灾害（大火）
      config.smoke.emissionRate = 110
      config.smoke.imageWidth = 32
      config.smoke.imageHeight = 32
      config.fire.emissionRate = 95
      config.fire.imageWidth = 30
      config.fire.imageHeight = 30
    } else if (phaseIndex === 7) { // 无人装备出动
      config.smoke.emissionRate = 90
      config.fire.emissionRate = 80
    } else if (phaseIndex === 8) { // 无人感知部署
      config.smoke.emissionRate = 70
      config.fire.emissionRate = 60
    } else if (phaseIndex === 9) { // 无人感知执行
      config.smoke.emissionRate = 50
      config.fire.emissionRate = 45
    } else if (phaseIndex === 10) { // 救援装备出动
      config.smoke.emissionRate = 15
      config.fire.emissionRate = 8
      config.smoke.imageWidth = 10
      config.smoke.imageHeight = 10
      config.fire.imageWidth = 8
      config.fire.imageHeight = 8
    }
  } else {
    // 油罐车泄漏扩散
    if (phaseIndex <= 1) {
      config.diffusion.emissionRate = 0
    } else if (phaseIndex >= 2 && phaseIndex <= 4) { // 事故发生 / 无人机出动 / 无人机侦察 (暂无泄露扩散)
      config.diffusion.emissionRate = 0
    } else if (phaseIndex === 5) { // 次生灾害（泄露）
      config.diffusion.emissionRate = 90
      config.diffusion.imageWidth = 14
      config.diffusion.imageHeight = 14
    } else if (phaseIndex === 6) { // 次生灾害（扩散）
      config.diffusion.emissionRate = 180
      config.diffusion.imageWidth = 24
      config.diffusion.imageHeight = 24
    } else if (phaseIndex === 7) { // 无人装备出动
      config.diffusion.emissionRate = 130
      config.diffusion.imageWidth = 20
      config.diffusion.imageHeight = 20
    } else if (phaseIndex === 8) { // 无人感知部署
      config.diffusion.emissionRate = 95
      config.diffusion.imageWidth = 15
      config.diffusion.imageHeight = 15
    } else if (phaseIndex === 9) { // 无人感知执行
      config.diffusion.emissionRate = 65
      config.diffusion.imageWidth = 10
      config.diffusion.imageHeight = 10
    } else if (phaseIndex === 10) { // 救援装备出动
      config.diffusion.emissionRate = 20
      config.diffusion.imageWidth = 5
      config.diffusion.imageHeight = 5
    }
  }
  
  return config
}

// 动态管理 3D 模型实体的可见性
function update3DModelsVisibility() {
  if (!viewer) return
  
  const phase = activePhaseIndex.value
  const scene = activeScene.value
  
  // 先把所有模型都隐藏
  simulationEntities.forEach(e => {
    e.show = false
  })
  
  if (scene === 'truck_crash') {
    // 货车现场基站展示
    const jizhan = viewer.entities.getById('sim_jizhan')
    if (jizhan) jizhan.show = true
    
    if (phase <= 1) {
      const normal = viewer.entities.getById('sim_truck_normal')
      if (normal) normal.show = true
    } else {
      const accident = viewer.entities.getById('sim_truck_accident')
      if (accident) accident.show = true
    }
  } else {
    // 油罐车现场
    if (phase <= 1) {
      const normal = viewer.entities.getById('sim_tanker_normal')
      if (normal) normal.show = true
    } else {
      const accident = viewer.entities.getById('sim_tanker_accident')
      if (accident) accident.show = true
    }
  }
}

// 载入 3D 事故模型实体
function add3DModels() {
  if (!viewer) return
  
  // 清理老 Entities
  simulationEntities.forEach(e => viewer.entities.remove(e))
  simulationEntities = []
  
  const xtCoords = scenePositions.xiantao.truck_crash
  const hgCoords = scenePositions.huanggang.tanker_leak
  
  // 1. 货车正常行驶模型
  const truckNormal = viewer.entities.add({
    id: 'sim_truck_normal',
    name: '货车行驶',
    position: Cesium.Cartesian3.fromDegrees(xtCoords.lng, xtCoords.lat, 0),
    model: {
      uri: '/Dashboard/models/Normal_Drive.glb',
      scale: 1.0,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    },
    show: false
  })
  simulationEntities.push(truckNormal)
  
  // 2. 货车事故模型
  const truckAccident = viewer.entities.add({
    id: 'sim_truck_accident',
    name: '货车追尾',
    position: Cesium.Cartesian3.fromDegrees(xtCoords.lng, xtCoords.lat, 0),
    model: {
      uri: '/Dashboard/models/Accident_Occur1.glb',
      scale: 1.0,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    },
    show: false
  })
  simulationEntities.push(truckAccident)
  
  // 3. 油罐车正常行驶模型
  const tankerNormal = viewer.entities.add({
    id: 'sim_tanker_normal',
    name: '油罐车行驶',
    position: Cesium.Cartesian3.fromDegrees(hgCoords.lng, hgCoords.lat, 0),
    model: {
      uri: '/Dashboard/models/Normal_Drive_Tanker.glb',
      scale: 1.0,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    },
    show: false
  })
  simulationEntities.push(tankerNormal)
  
  // 4. 油罐车事故模型
  const tankerAccident = viewer.entities.add({
    id: 'sim_tanker_accident',
    name: '油罐车侧翻',
    position: Cesium.Cartesian3.fromDegrees(hgCoords.lng, hgCoords.lat, 0),
    model: {
      uri: '/Dashboard/models/Side_roll_Tanker.glb',
      scale: 1.0,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    },
    show: false
  })
  simulationEntities.push(tankerAccident)
  
  // 5. 5G基站模型 (货车现场)
  const jizhan = viewer.entities.add({
    id: 'sim_jizhan',
    name: '5G基站',
    position: Cesium.Cartesian3.fromDegrees(xtCoords.lng + 0.0001, xtCoords.lat + 0.0001, 0),
    model: {
      uri: '/Dashboard/models/jizhan.glb',
      scale: 2.0,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    },
    show: false
  })
  simulationEntities.push(jizhan)
  
  update3DModelsVisibility()
}

// 监听事故阶段和事故场景的变化，动态更新各面板状态
watch([activePhaseIndex, activeScene], ([phaseIdx, scene]) => {
  const config = get2DParticleConfig(phaseIdx)
  
  // 1. 同步调节面板状态
  if (scene === 'truck_crash') {
    Object.keys(config.smoke).forEach(key => {
      smokeAdjust[key] = config.smoke[key]
    })
    Object.keys(config.fire).forEach(key => {
      fireAdjust[key] = config.fire[key]
    })
    globalWindSpeed.value = config.smoke.windSpeed || 3.0
    globalWindDirection.value = config.smoke.windDirection || 45.0
    globalGravity.value = config.smoke.gravity || 2.5
    globalDrag.value = 0.98
  } else {
    Object.keys(config.diffusion).forEach(key => {
      diffusionAdjust[key] = config.diffusion[key]
    })
    globalWindSpeed.value = config.diffusion.windSpeed || 3.0
    globalWindDirection.value = config.diffusion.windDirection || 45.0
    globalGravity.value = 2.5
    globalDrag.value = config.diffusion.drag || 0.96
  }
  
  // 2. 同步更新 3D 粒子和 3D 模型
  if (viewer) {
    update3DModelsVisibility()
    // 同步更新 3D 粒子的可见性：烟雾与泄露在阶段 >= 5 (次生灾害烟雾/泄露) 才显示；火焰在阶段 >= 6 (次生灾害起火) 显示
    if (smokeParticle) smokeParticle.show = (currentCity.value === 'xiantao' && phaseIdx >= 5)
    if (fireParticle) fireParticle.show = (currentCity.value === 'xiantao' && phaseIdx >= 6)
    if (diffusionParticle) diffusionParticle.show = (currentCity.value === 'huanggang' && phaseIdx >= 5)
    
    // 同步更新 CZML 实体可见性
    if (currentCzmlDataSource) {
      const multiAgentPrefixes = ['Agent_', 'AgentPath_', 'AgentPOI_', 'AgentCP_'];
      currentCzmlDataSource.entities.values.forEach(entity => {
        const id = entity.id;
        if (id && multiAgentPrefixes.some(prefix => id.startsWith(prefix))) {
            const shouldShow = isRescueDispatchPhase(phaseIdx);
            entity.show = shouldShow;
        } else if (id === 'Car_Path' || id === 'Car_Path_glow' || id === 'Car') {
            entity.show = (Number(phaseIdx) >= 7);
        } else if (id === 'UAV_Path' || id === 'UAV_Path_glow' || id === 'UAV') {
            entity.show = (Number(phaseIdx) >= 3);
        } else {
            entity.show = (Number(phaseIdx) !== 6);
        }
      });
    }
  }
}, { immediate: true })

// 监听视图模式变化，在物理仿真模式下自动对焦至事故中心，并切换 2D 渲染引擎
watch(viewMode, async (newMode) => {
  if (newMode === '3d') {
    fetchOptimizationLog(currentCity.value)
    await nextTick()
    if (!viewer) await initSimulationViewer()
    if (viewer) {
      viewer.resize()
      generate3DRescueDispatch(currentCity.value)
      flyToThreeDOverview(currentCity.value)
    }
    return
  }

  if (newMode === 'physics') {
    const city = currentCity.value
    if (viewer) {
      const coords = scenePositions[city][activeScene.value]
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(coords.lng, coords.lat, city === 'xiantao' ? 1500 : 2000),
        orientation: {
          heading: Cesium.Math.toRadians(0.0),
          pitch: Cesium.Math.toRadians(-35.0),
          roll: 0.0
        },
        duration: 2.0
      });
      add3DModels()
    }
    activePhysicsTab.value = (city === 'xiantao') ? 'smoke' : 'diffusion'
    selectPhase(activePhaseIndex.value)
    
    // 异步启动 2D 物理粒子循环
    nextTick(() => {
      start2DPhysicsSimulation()
    })
  } else {
    // 停止 2D 物理粒子循环
    stop2DPhysicsSimulation()
    
    if (viewer) {
      // 清理 3D 事故模型
      simulationEntities.forEach(e => viewer.entities.remove(e))
      simulationEntities = []
      
      if (newMode === '3d') {
        generate3DRescueDispatch(currentCity.value)
        flyToThreeDOverview(currentCity.value)
      }
    }
  }
})

const loadMission = async () => {
  if (!viewer) return
  try {
    const baseUrl = getCollaborativeCommandCenterBaseUrl()
    
    // 清理旧的 CZML 数据源
    if (currentCzmlDataSource) {
      viewer.dataSources.remove(currentCzmlDataSource)
      currentCzmlDataSource = null
    }
    
    const czmlUrl = `${baseUrl}/mission.czml?t=${Date.now()}`
    const dataSource = await Cesium.CzmlDataSource.load(czmlUrl)
    if (!viewer) return
    currentCzmlDataSource = dataSource
    
    // Clear availability and handle visibility
    const multiAgentPrefixes = ['Agent_', 'AgentPath_', 'AgentPOI_', 'AgentCP_'];
    dataSource.entities.values.forEach(entity => {
      entity.availability = undefined;
      const id = entity.id;
      if (id && multiAgentPrefixes.some(prefix => id.startsWith(prefix))) {
          entity.show = isRescueDispatchPhase();
      } else if (id === 'Car_Path' || id === 'Car_Path_glow' || id === 'Car') {
          entity.show = (Number(activePhaseIndex.value) >= 7);
      } else if (id === 'UAV_Path' || id === 'UAV_Path_glow' || id === 'UAV') {
          entity.show = (Number(activePhaseIndex.value) >= 3);
      } else {
          entity.show = (Number(activePhaseIndex.value) !== 6);
      }
    });

    viewer.dataSources.add(dataSource)

    // 同步时间轴
    if (dataSource.clock) {
      viewer.clock.startTime = dataSource.clock.startTime;
      viewer.clock.stopTime = dataSource.clock.stopTime;
      viewer.clock.currentTime = dataSource.clock.currentTime;
      viewer.clock.clockRange = dataSource.clock.clockRange;
      viewer.clock.multiplier = 20.0;
      viewer.clock.shouldAnimate = true;
    }
    // 保持当前的城市级俯视视角，不改变相机机位
  } catch (error) {
    console.error('加载三维轨迹 CZML 失败:', error)
  }
}

let latestTwoDimensionalRequest = 0
let latestThreeDimensionalRequest = 0

// 仿真推演的城市场景与协同响应指挥的二维动态推演场景保持一一对应。
// 每次切换场景均重新加载该场景的五类救援装备出动结果，防止两个场景共用旧路线。
const TWO_DIMENSIONAL_SCENARIOS = {
  xiantao: 'crash',
  huanggang: 'leak'
}

// 与协同响应指挥“三维态势地图”的救援装备出动共用同一套多智能体接口，
// 将五类救援力量的 CZML 动态轨迹加载到当前 Cesium 三维推演中。
const generate3DRescueDispatch = async (city) => {
  const endpoint = TWO_DIMENSIONAL_SCENARIOS[city] || 'crash'
  const requestId = ++latestThreeDimensionalRequest
  const baseUrl = getCollaborativeCommandCenterBaseUrl()

  try {
    const params = new URLSearchParams({
      end_point: endpoint,
      strategy: 'rcd',
      ugv_block: '1',
      uav_smoke: '1',
      compare: '1'
    })
    const response = await fetch(`${baseUrl}/api/run_multi_agent?${params.toString()}`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const result = await response.json().catch(() => ({}))
    if (result.ok === false) throw new Error(result.message || '三维救援装备路线生成失败')
    if (requestId !== latestThreeDimensionalRequest) return

    // 三维视图没有独立的阶段选择面板；进入救援出动推演时自动定位到该阶段，
    // 使五类救援装备及其动态轨迹立即可见。
    const rescuePhaseIndex = activeAccidentPhases.value.findIndex(phase =>
      phase.id.endsWith('rescue-start')
    )
    if (rescuePhaseIndex >= 0) activePhaseIndex.value = rescuePhaseIndex

    await loadMission()
    await fetchOptimizationLog(city)
  } catch (error) {
    if (requestId !== latestThreeDimensionalRequest) return
    console.warn('请求协同响应三维救援装备出动失败，保留当前三维推演结果:', error)
  }
}

const generate2DDeduction = async (city) => {
  const endpoint = TWO_DIMENSIONAL_SCENARIOS[city] || 'crash'
  const requestId = ++latestTwoDimensionalRequest
  isGenerating2D.value = true
  errorMessage.value = ''
  const baseUrl = getCollaborativeCommandCenterBaseUrl()
  try {
    // 与协同响应指挥模块的“救援装备出动”使用同一接口和策略：
    // 五类救援力量（医疗、消防、公安、防化、路政）会生成并写入对应场景的二维动态路线。
    const params = new URLSearchParams({
      end_point: endpoint,
      ugv_block: '1',
      uav_smoke: '1',
      strategy: 'rcd',
      compare: '1'
    })
    const response = await fetch(`${baseUrl}/api/run_multi_agent?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const result = await response.json().catch(() => ({}))
    if (result.ok === false) throw new Error(result.message || '救援装备路线生成失败')

    // 用户在请求期间已切换场景时，不再用旧场景结果覆盖当前二维推演。
    if (requestId !== latestTwoDimensionalRequest) return
  } catch (error) {
    if (requestId !== latestTwoDimensionalRequest) return
    console.warn('请求救援装备二维动态推演失败，将尝试加载后端最近一次可用结果:', error)
  } finally {
    if (requestId !== latestTwoDimensionalRequest) return

    // 携带场景与出动类型标识，强制 iframe 刷新到本次生成的协同响应二维结果。
    iframeSrc.value = `${baseUrl}/2d_deduction.html?end_point=${endpoint}&dispatch=rescue&t=${Date.now()}`
    twoDimensionalRunKey.value += 1
    try {
      await loadMission()
    } catch (e) {
      console.error('加载轨迹异常:', e)
    }
    isGenerating2D.value = false
  }
}

// 辅助方法：将经纬度数组转换为 Cesium.Cartesian3 数组
const convertCoordsToCartesians = (coords) => {
  const degrees = [];
  coords.forEach(pt => {
    degrees.push(pt[0], pt[1]);
  });
  return Cesium.Cartesian3.fromDegreesArray(degrees);
};

let currentMaskEntity = null;
let currentBoundaryLines = [];

async function loadCityMask(city) {
  if (!viewer) return;
  
  // 清除旧的蒙版。三维推演直接使用协同响应的完整 Cesium 底图，
  // 不再把仙桃或黄冈以外的地图区域覆盖成深色遮罩。
  if (currentMaskEntity) {
    viewer.entities.remove(currentMaskEntity);
    currentMaskEntity = null;
  }

  if (viewMode.value === '3d') return;

  // 定义遮罩镂空（holes）要加载的文件
  let maskFileName = '';
  if (city === 'xiantao') {
    maskFileName = 'xiantao.json';
  } else {
    maskFileName = 'huanggang_wuhan.json';
  }

  try {
    // 加载镂空文件，并生成暗色背景蒙版
    const holes = [];
    const maskResponse = await fetch(`/Dashboard/${maskFileName}`);
    if (!viewer) return;
    if (!maskResponse.ok) throw new Error(`读取 ${maskFileName} 失败`);
    const maskGeojson = await maskResponse.json();
    if (!viewer) return;

    maskGeojson.features.forEach(feature => {
      const geometry = feature.geometry;
      if (geometry.type === 'Polygon') {
        const outerRing = convertCoordsToCartesians(geometry.coordinates[0]);
        holes.push(new Cesium.PolygonHierarchy(outerRing));
      } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach(polygon => {
          const outerRing = convertCoordsToCartesians(polygon[0]);
          holes.push(new Cesium.PolygonHierarchy(outerRing));
        });
      }
    });

    const worldPolygonHierarchy = new Cesium.PolygonHierarchy(
      Cesium.Cartesian3.fromDegreesArray([
        50, 65,
        160, 65,
        160, 5,
        50, 5
      ]),
      holes
    );

    currentMaskEntity = viewer.entities.add({
      polygon: {
        hierarchy: worldPolygonHierarchy,
        material: Cesium.Color.fromCssColorString('#070b19').withAlpha(0.94),
        classificationType: Cesium.ClassificationType.BOTH,
        outline: false
      }
    });
  } catch (error) {
    console.error(`加载 ${city} 行政边界蒙版时出错:`, error);
  }
}

async function initCityRegionsAndLabels() {
  if (!viewer) return;
  
  // 清理可能已经存在的持久化实体
  persistentCityEntities.forEach(entity => {
    viewer.entities.remove(entity);
  });
  persistentCityEntities = [];

  const citiesConfig = [
    { name: '黄冈市', file: 'huanggang.json', color: '#ffd700', center: [114.87, 30.61] },
    { name: '仙桃市', file: 'xiantao.json', color: '#ff007f', center: [113.43, 30.29] }
  ];

  for (const city of citiesConfig) {
    try {
      const response = await fetch(`/Dashboard/${city.file}`);
      if (!viewer) return;
      if (!response.ok) throw new Error(`读取 ${city.file} 失败`);
      const geojson = await response.json();
      if (!viewer) return;

      geojson.features.forEach(feature => {
        const geometry = feature.geometry;
        
        // 1. 绘制行政边界线
        if (geometry.type === 'Polygon') {
          const outerRing = convertCoordsToCartesians(geometry.coordinates[0]);
          const line = viewer.entities.add({
            polyline: {
              positions: outerRing,
              width: 5.5,
              material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.26,
                color: Cesium.Color.fromCssColorString(city.color)
              }),
              clampToGround: true
            }
          });
          persistentCityEntities.push(line);

          // 2. 绘制半透明多边形，用于鼠标移动 hover 拾取
          const polygonEntity = viewer.entities.add({
            polygon: {
              hierarchy: new Cesium.PolygonHierarchy(outerRing),
              material: Cesium.Color.fromCssColorString(city.color).withAlpha(0.015),
              classificationType: Cesium.ClassificationType.TERRAIN
            },
            properties: {
              cityName: city.name
            }
          });
          persistentCityEntities.push(polygonEntity);
        } else if (geometry.type === 'MultiPolygon') {
          geometry.coordinates.forEach(polygon => {
            const outerRing = convertCoordsToCartesians(polygon[0]);
            const line = viewer.entities.add({
              polyline: {
                positions: outerRing,
                width: 5.5,
                material: new Cesium.PolylineGlowMaterialProperty({
                  glowPower: 0.26,
                  color: Cesium.Color.fromCssColorString(city.color)
                }),
                clampToGround: true
              }
            });
            persistentCityEntities.push(line);

            const polygonEntity = viewer.entities.add({
              polygon: {
                hierarchy: new Cesium.PolygonHierarchy(outerRing),
                material: Cesium.Color.fromCssColorString(city.color).withAlpha(0.015),
                classificationType: Cesium.ClassificationType.TERRAIN
              },
              properties: {
                cityName: city.name
              }
            });
            persistentCityEntities.push(polygonEntity);
          });
        }
      });

      // 3. 在各市中心添加文字标注
      const labelEntity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(city.center[0], city.center[1], 100),
        label: {
          text: city.name,
          font: 'bold 16px "Microsoft YaHei", sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.fromCssColorString('#070b19'),
          outlineWidth: 5,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          eyeOffset: new Cesium.Cartesian3(0, 0, -1000) // 让标注稍显突出，不被覆盖
        }
      });
      persistentCityEntities.push(labelEntity);

    } catch (e) {
      console.error(`初始化 ${city.name} 的持久化边界和标注失败:`, e);
    }
  }
}

const flyToCity = async (city) => {
  currentCity.value = city;
  activeScene.value = city === 'xiantao' ? 'truck_crash' : 'tanker_leak'
  
  // 根据当前视图加载协同响应指挥中对应场景的救援装备动态推演。
  if (viewMode.value === '3d') {
    await generate3DRescueDispatch(city)
  } else {
    generate2DDeduction(city)
  }

  // 即使 viewer 为 null，也要正常更新物理仿真的 Tab 和推演阶段以刷新 2D Canvas
  if (viewMode.value === 'physics') {
    activePhysicsTab.value = (city === 'xiantao') ? 'smoke' : 'diffusion'
    selectPhase(selectedPhase.value)
  }

  if (!viewer) return;
  
  await loadCityMask(city);
  updateParticlesVisibility(city);
  
  if (viewMode.value === 'physics') {
    const coords = scenePositions[city][activeScene.value]
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(coords.lng, coords.lat, city === 'xiantao' ? 1500 : 2000),
      orientation: {
        heading: Cesium.Math.toRadians(0.0),
        pitch: Cesium.Math.toRadians(-35.0),
        roll: 0.0
      },
      duration: 2.0
    });
  } else {
    flyToThreeDOverview(city)
  }
}

const initSimulationViewer = async () => {
  if (viewer || isSimulationViewerInitializing) return
  const container = document.getElementById('simulationCesiumContainer')
  if (!container) return

  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.log('[Cesium Simulation] 容器尺寸为 0，延迟 100ms 重新尝试初始化...')
    initSimulationViewerTimeout = setTimeout(initSimulationViewer, 100)
    return
  }

  isSimulationViewerInitializing = true
  isInitializing3D.value = true
  threeDError.value = ''
  is3DReady.value = false

  // 屏蔽 Cesium 默认的红色崩溃弹窗
  if (Cesium) {
    if (Cesium.CesiumWidget && Cesium.CesiumWidget.prototype) {
      Cesium.CesiumWidget.prototype.showErrorPanel = function(title, message, error) {
        console.error('[Cesium Widget Proto Error Blocked]', title, message, error);
      };
    }
  }

  try {
    console.log('[Cesium Simulation] 尝试创建 WebGL 2 Viewer...')
    viewer = new Cesium.Viewer(container, {
      animation: true, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
      infoBox: true, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
      timeline: true, shouldAnimate: true, skyAtmosphere: false,
      contextOptions: {
        webgl: {
          failIfMajorPerformanceCaveat: false
        }
      }
    })
  } catch (e1) {
    console.warn('[Cesium Simulation] WebGL 2 创建失败，尝试降级创建 WebGL 1...', e1.message)
    try {
      viewer = new Cesium.Viewer(container, {
        animation: true, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
        infoBox: true, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
        timeline: true, shouldAnimate: true, skyAtmosphere: false,
        contextOptions: {
          requestWebgl1: true,
          webgl: {
            failIfMajorPerformanceCaveat: false
          }
        }
      })
    } catch (e2) {
      threeDError.value = '三维地球初始化失败，请确认浏览器已启用 WebGL/硬件加速后刷新重试。'
      isInitializing3D.value = false
      isSimulationViewerInitializing = false
      console.error('三维地球初始化失败:', e2);
      return;
    }
  }

  isInitializing3D.value = false
  isSimulationViewerInitializing = false
  is3DReady.value = true
  
  window.simulationViewer = viewer

  // 加载 3D 建筑
  try {
    Cesium.createOsmBuildingsAsync().then(buildings => {
      if (!viewer) return
      viewer.scene.primitives.add(buildings)
      buildings.style = new Cesium.Cesium3DTileStyle({
        color: "color('#ffffff', 0.72)",
      })
    }).catch(err => {
      console.warn("OSM 建筑加载失败", err)
    })
  } catch (error) {
    console.warn("加载 OSM 建筑出错:", error)
  }
  
  if (!viewer) return
  // 初始化时直接将视角定位到对应的城市，跳过从地球飞跃的过程
  const initialOverview = THREE_D_OVERVIEW[currentCity.value] || THREE_D_OVERVIEW.xiantao
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(initialOverview.lng, initialOverview.lat, initialOverview.height),
    orientation: { heading: 0, pitch: -Cesium.Math.PI_OVER_TWO, roll: 0 }
  })
  
  viewer.scene.globe.enableLighting = false
  viewer.scene.globe.depthTestAgainstTerrain = true
  viewer.scene.highDynamicRange = true
  viewer.scene.postProcessStages.fxaa.enabled = true
  viewer.scene.fog.enabled = true
  viewer.scene.fog.density = 0.00012
  viewer.scene.light = new Cesium.DirectionalLight({
    direction: viewer.camera.direction
  })
  removeLightListener = viewer.scene.preRender.addEventListener(function(scene, time) {
    scene.light.direction = Cesium.Cartesian3.clone(scene.camera.directionWC, scene.light.direction)
  })
  viewer.cesiumWidget.creditContainer.style.display = 'none'

  if (!viewer) return
  // 使用可控的卫星影像底图。默认 Ion 图层在部分网络环境会静默失败，
  // 导致只显示路线和标注、地表近黑；这里提供稳定的卫星影像来源。
  await configureSimulationBasemap()

  if (!viewer) return
  if (!viewer) return
  await loadCityMask(currentCity.value)
  if (!viewer) return
  
  // 初始生成对应的二维推演
  generate2DDeduction(currentCity.value)
  if (!viewer) return

  // 初始化粒子系统
  initParticleSystems()
  if (!viewer) return

  // 动态粒子大小 and 速度监听器
  preRenderListener = viewer.scene.preRender.addEventListener(() => {
    if (!viewer) return
    const cameraHeight = viewer.camera.positionCartographic.height
    // 动态缩放比例，基于高度：在 400 米以下为 1.0 倍，随高度增加而呈幂级数缩放
    const scaleFactor = Math.max(1.0, Math.pow(cameraHeight / 400.0, 0.85))
    
    if (viewMode.value === 'physics') {
      // 物理仿真微调模式：应用调整面板的实时参数 (受相机高度缩放)
      if (smokeParticle) {
        smokeParticle.imageSize = new Cesium.Cartesian2(smokeAdjust.imageWidth * scaleFactor, smokeAdjust.imageHeight * scaleFactor)
        smokeParticle.emissionRate = smokeAdjust.emissionRate
        smokeParticle.minimumSpeed = (smokeAdjust.maxSpeed * 0.4) * scaleFactor
        smokeParticle.maximumSpeed = smokeAdjust.maxSpeed * scaleFactor
        smokeParticle.minimumParticleLife = smokeAdjust.minLife
        smokeParticle.maximumParticleLife = smokeAdjust.maxLife
      }
      if (fireParticle) {
        fireParticle.imageSize = new Cesium.Cartesian2(fireAdjust.imageWidth * scaleFactor, fireAdjust.imageHeight * scaleFactor)
        fireParticle.emissionRate = fireAdjust.emissionRate
        fireParticle.minimumSpeed = (fireAdjust.maxSpeed * 0.4) * scaleFactor
        fireParticle.maximumSpeed = fireAdjust.maxSpeed * scaleFactor
        fireParticle.minimumParticleLife = fireAdjust.minLife
        fireParticle.maximumParticleLife = fireAdjust.maxLife
      }
      if (diffusionParticle) {
        diffusionParticle.imageSize = new Cesium.Cartesian2(diffusionAdjust.imageWidth * scaleFactor, diffusionAdjust.imageHeight * scaleFactor)
        diffusionParticle.emissionRate = diffusionAdjust.emissionRate
        diffusionParticle.minimumSpeed = (diffusionAdjust.maxSpeed * 0.45) * scaleFactor
        diffusionParticle.maximumSpeed = diffusionAdjust.maxSpeed * scaleFactor
        diffusionParticle.minimumParticleLife = diffusionAdjust.minLife
        diffusionParticle.maximumParticleLife = diffusionAdjust.maxLife
      }
    } else {
      // 默认三维推演模式：使用标准比例
      if (smokeParticle) {
        smokeParticle.imageSize = new Cesium.Cartesian2(25 * scaleFactor, 25 * scaleFactor)
        smokeParticle.minimumSpeed = 2.0 * scaleFactor
        smokeParticle.maximumSpeed = 5.0 * scaleFactor
      }
      if (fireParticle) {
        fireParticle.imageSize = new Cesium.Cartesian2(25 * scaleFactor, 25 * scaleFactor)
        fireParticle.minimumSpeed = 3.0 * scaleFactor
        fireParticle.maximumSpeed = 7.0 * scaleFactor
      }
      if (diffusionParticle) {
        diffusionParticle.imageSize = new Cesium.Cartesian2(9 * scaleFactor, 9 * scaleFactor)
        diffusionParticle.minimumSpeed = 2.0 * scaleFactor
        diffusionParticle.maximumSpeed = 5.5 * scaleFactor
      }
    }
  })

  // 初始化各个市级区域和标注
  await initCityRegionsAndLabels()

  // 已取消市级名字悬浮窗事件监听
}

onMounted(() => {
  if (viewMode.value === '2d') {
    generate2DDeduction(currentCity.value)
  } else if (viewMode.value === 'physics') {
    start2DPhysicsSimulation()
  }
})

// ==================== 2D 物理粒子仿真引擎 ====================
let physicsCanvas = null
let physicsCtx = null
let physicsAnimationId = null
let physicsParticles = []

// 获取风向的中文文字描述
function getWindDirectionText(dir) {
  if (dir >= 337.5 || dir < 22.5) return '北风'
  if (dir >= 22.5 && dir < 67.5) return '东北风'
  if (dir >= 67.5 && dir < 112.5) return '东风'
  if (dir >= 112.5 && dir < 157.5) return '东南风'
  if (dir >= 157.5 && dir < 202.5) return '南风'
  if (dir >= 202.5 && dir < 247.5) return '西南风'
  if (dir >= 247.5 && dir < 292.5) return '西风'
  return '西北风'
}

// 绑定风速，用于界面 HUD
const currentWindSpeed = computed(() => globalWindSpeed.value)

// 绑定风向，用于界面 HUD
const currentWindDirection = computed(() => globalWindDirection.value)

const activeParticleCount = ref(0)

class Physics2DParticle {
  constructor(x, y, type) {
    this.x = x
    this.y = y
    this.type = type // 'smoke' | 'fire' | 'diffusion'
    
    // 获取当前粒子调节参数
    const adjust = type === 'smoke' ? smokeAdjust : type === 'fire' ? fireAdjust : diffusionAdjust
    
    // 初始速度：向上喷射，加入一定的随机扇形展角
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * 0.4 // 垂直向上方向的随机偏角
    const speed = adjust.maxSpeed * (0.35 + Math.random() * 0.65) // 随机速度大小
    
    this.vx = Math.cos(angle) * speed * 25 // 2D 像素尺度缩放
    this.vy = Math.sin(angle) * speed * 25
    
    this.maxLife = adjust.minLife + Math.random() * (adjust.maxLife - adjust.minLife)
    this.life = this.maxLife
    
    // 初始大小
    this.initWidth = adjust.imageWidth * 1.5
    this.initHeight = adjust.imageHeight * 1.5
    this.width = this.initWidth
    this.height = this.initHeight
    
    // 阻力
    this.drag = type === 'diffusion' ? (diffusionAdjust.drag || 0.96) : 0.98
    
    // 重力/上升力系数
    this.gravity = adjust.gravity || (type === 'fire' ? 5.0 : 2.5)
  }
  
  update(dt, windX, windY) {
    this.life -= dt
    if (this.life <= 0) return false
    
    // 1. 上升力（上升力向上，故在 2D 坐标系中 y 减小）
    const buoyancy = this.gravity * 35 * dt
    this.vy -= buoyancy
    
    // 2. 环境风力影响
    this.vx += windX * 15 * dt
    this.vy += windY * 15 * dt
    
    // 3. 阻力/摩擦力
    this.vx *= Math.pow(this.drag, dt * 60)
    this.vy *= Math.pow(this.drag, dt * 60)
    
    // 4. 位移更新
    this.x += this.vx * dt
    this.y += this.vy * dt
    
    // 5. 随着寿命增加，粒子膨胀扩展
    const ageRatio = 1.0 - (this.life / this.maxLife)
    // 烟雾和扩散粒子在生命周期末期会急剧膨胀，火焰则保持或缩小
    const scaleMultiplier = this.type === 'fire' ? (1.0 - ageRatio * 0.3) : (1.0 + ageRatio * 3.5)
    this.width = this.initWidth * scaleMultiplier
    this.height = this.initHeight * scaleMultiplier
    
    return true
  }
  
  draw(ctx) {
    const ageRatio = this.life / this.maxLife
    ctx.save()
    
    // 使用径向渐变模拟真实的雾状/火焰发光粒子
    const grad = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, Math.max(this.width, this.height) / 2)
    
    if (this.type === 'fire') {
      // 火焰粒子：亮黄/橙色中心，渐变为红色，末梢透明
      grad.addColorStop(0, `rgba(255, 255, 200, ${ageRatio * 0.9})`)
      grad.addColorStop(0.2, `rgba(255, 180, 0, ${ageRatio * 0.8})`)
      grad.addColorStop(0.5, `rgba(240, 50, 0, ${ageRatio * 0.5})`)
      grad.addColorStop(1, 'rgba(120, 0, 0, 0)')
      ctx.globalCompositeOperation = 'lighter' // 叠加发光模式
    } else if (this.type === 'smoke') {
      // 烟雾粒子：中心灰黑色，边缘透明灰色
      const darkness = 35 + (1.0 - ageRatio) * 45 // 随着衰老变灰淡
      grad.addColorStop(0, `rgba(${darkness}, ${darkness}, ${darkness + 5}, ${ageRatio * 0.65})`)
      grad.addColorStop(0.4, `rgba(${darkness - 10}, ${darkness - 10}, ${darkness - 5}, ${ageRatio * 0.4})`)
      grad.addColorStop(1, 'rgba(20, 20, 20, 0)')
    } else {
      // 泄漏扩散粒子：亮霓虹绿/黄色中心，渐变为黄绿透明，模拟毒气
      grad.addColorStop(0, `rgba(57, 255, 20, ${ageRatio * 0.7})`)
      grad.addColorStop(0.3, `rgba(180, 255, 0, ${ageRatio * 0.4})`)
      grad.addColorStop(0.6, `rgba(100, 220, 40, ${ageRatio * 0.15})`)
      grad.addColorStop(1, 'rgba(0, 150, 0, 0)')
    }
    
    ctx.fillStyle = grad
    ctx.beginPath()
    // 绘制椭圆来匹配 Width / Height
    ctx.ellipse(this.x, this.y, this.width / 2, this.height / 2, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }
}

class WaterSuppressionParticle {
  constructor(startX, startY, targetX, targetY) {
    this.x = startX
    this.y = startY
    this.type = 'water'
    
    // 抛物线水流：朝向起火点/泄漏点发射
    const dx = targetX - startX
    const dy = targetY - startY
    const dist = Math.sqrt(dx*dx + dy*dy)
    
    // 随机散射弧度
    const angle = Math.atan2(dy, dx) + (Math.random() - 0.5) * 0.25
    const speed = (dist / 1.1) * (0.85 + Math.random() * 0.3)
    
    this.vx = Math.cos(angle) * speed
    this.vy = Math.sin(angle) * speed - 60 // 往上喷射抛物线
    
    this.life = 1.2 + Math.random() * 0.4
    this.maxLife = this.life
    this.size = 3 + Math.random() * 4
  }
  
  update(dt) {
    this.life -= dt
    if (this.life <= 0) return false
    
    // 水滴受重力影响下坠
    this.vy += 220 * dt
    this.x += this.vx * dt
    this.y += this.vy * dt
    
    return true
  }
  
  draw(ctx) {
    const ageRatio = this.life / this.maxLife
    ctx.save()
    ctx.fillStyle = `rgba(0, 229, 255, ${ageRatio * 0.85})`
    ctx.shadowBlur = 6
    ctx.shadowColor = '#00e5ff'
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }
}

// 绘制地面的事故车或设施的高科技线框图
function drawAccidentBase(ctx, width, height) {
  const baseX = width / 2
  const baseY = height * 2 / 3
  const phase = activePhaseIndex.value
  
  ctx.save()
  // 1. 绘制带有科技感的发光底座
  ctx.shadowColor = '#00ffd8'
  ctx.shadowBlur = 10
  ctx.strokeStyle = 'rgba(0, 255, 216, 0.4)'
  ctx.lineWidth = 2
  
  // 地面横线
  ctx.beginPath()
  ctx.moveTo(baseX - 350, baseY + 60)
  ctx.lineTo(baseX + 350, baseY + 60)
  ctx.stroke()
  
  // 刻度网格线
  for (let offset = -300; offset <= 300; offset += 50) {
    ctx.beginPath()
    ctx.moveTo(baseX + offset, baseY + 60)
    ctx.lineTo(baseX + offset + (offset * 0.15), baseY + 85)
    ctx.strokeStyle = 'rgba(0, 255, 216, 0.12)'
    ctx.stroke()
  }
  ctx.shadowBlur = 0

  if (activeScene.value === 'truck_crash') {
    // ==================== 货车追尾现场 ====================
    // 车辆模型已按需不绘制
    
    // 起火核心点警示标志
    if (phase >= 2) {
      ctx.fillStyle = 'rgba(255, 50, 0, 0.15)'
      ctx.beginPath()
      ctx.arc(baseX, baseY + 15, 35, 0, Math.PI * 2)
      ctx.fill()
    }
    
  } else {
    // ==================== 油罐车泄露现场 ====================
    // 车辆模型已按需不绘制
    
    // 泄漏水渍 and 流淌效果
    if (phase >= 3) {
      ctx.fillStyle = 'rgba(0, 255, 180, 0.15)'
      ctx.beginPath()
      ctx.ellipse(baseX, baseY + 48, 65, 12, 0, 0, Math.PI * 2)
      ctx.fill()
    }
  }
  ctx.restore()
}

// 启动 2D 物理粒子循环
function start2DPhysicsSimulation() {
  stop2DPhysicsSimulation()
  
  physicsCanvas = document.getElementById('physicsSmokeCanvas')
  if (!physicsCanvas) return
  
  physicsCtx = physicsCanvas.getContext('2d')
  if (!physicsCtx) return
  
  // 自适应 Canvas 大小
  const resizeCanvas = () => {
    if (!physicsCanvas) return
    const rect = physicsCanvas.parentElement.getBoundingClientRect()
    physicsCanvas.width = rect.width
    physicsCanvas.height = rect.height
  }
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
  
  physicsParticles = []
  let lastTime = performance.now()
  let spawnAccumulator = 0
  
  const loop = (now) => {
    if (!physicsCanvas || !physicsCtx) return
    
    const dt = Math.min((now - lastTime) / 1000, 0.1) // 限制最大时间差
    lastTime = now
    
    // 1. 清屏并填充暗夜网格背景
    physicsCtx.fillStyle = '#070b19'
    physicsCtx.fillRect(0, 0, physicsCanvas.width, physicsCanvas.height)
    
    // 绘制高科技感的星空背景网格
    physicsCtx.save()
    physicsCtx.strokeStyle = 'rgba(0, 255, 180, 0.03)'
    physicsCtx.lineWidth = 1
    const gridSize = 40
    for (let x = 0; x < physicsCanvas.width; x += gridSize) {
      physicsCtx.beginPath()
      physicsCtx.moveTo(x, 0)
      physicsCtx.lineTo(x, physicsCanvas.height)
      physicsCtx.stroke()
    }
    for (let y = 0; y < physicsCanvas.height; y += gridSize) {
      physicsCtx.beginPath()
      physicsCtx.moveTo(0, y)
      physicsCtx.lineTo(physicsCanvas.width, y)
      physicsCtx.stroke()
    }
    physicsCtx.restore()
    
    // 2. 绘制事故模型底座
    drawAccidentBase(physicsCtx, physicsCanvas.width, physicsCanvas.height)
    
    // 3. 计算当前的物理环境力 (风向风速)
    const angleRad = (currentWindDirection.value + 180) * Math.PI / 180
    const windSpeedVal = currentWindSpeed.value
    // 风力的 X 和 Y 分量
    const windX = Math.sin(angleRad) * windSpeedVal
    const windY = -Math.cos(angleRad) * windSpeedVal // 向上为负
    
    // 4. 生成新粒子 (发射速率控制)
    let rate = 0
    let types = []
    
    if (activePhaseIndex.value >= 2 && activePhaseIndex.value <= 9) {
      if (currentCity.value === 'xiantao') {
        // 仙桃：烟雾和火焰
        if (activePhaseIndex.value === 2 || activePhaseIndex.value === 3) {
          rate = smokeAdjust.emissionRate
          types = ['smoke']
        } else {
          rate = (smokeAdjust.emissionRate + fireAdjust.emissionRate)
          const total = smokeAdjust.emissionRate + fireAdjust.emissionRate
          const smokeRatio = total > 0 ? smokeAdjust.emissionRate / total : 0.5
          types = Math.random() < smokeRatio ? ['smoke'] : ['fire']
        }
      } else {
        // 黄冈：泄露扩散
        rate = diffusionAdjust.emissionRate
        types = ['diffusion']
      }
    }
    
    // 累积生成数
    spawnAccumulator += rate * dt
    const sourceX = physicsCanvas.width / 2
    const sourceY = physicsCanvas.height * 2 / 3 + 15
    
    while (spawnAccumulator >= 1) {
      types.forEach(t => {
        physicsParticles.push(new Physics2DParticle(sourceX, sourceY, t))
      })
      spawnAccumulator -= 1
    }
    
    // 5. 更新并渲染粒子
    physicsParticles = physicsParticles.filter(p => {
      let isAlive
      if (p.type === 'water') {
        isAlive = p.update(dt)
      } else {
        isAlive = p.update(dt, windX, windY)
      }
      if (isAlive) {
        p.draw(physicsCtx)
      }
      return isAlive
    })
    
    // 6. 更新仪表盘数据
    activeParticleCount.value = physicsParticles.length
    
    physicsAnimationId = requestAnimationFrame(loop)
  }
  
  physicsAnimationId = requestAnimationFrame(loop)
}

function stop2DPhysicsSimulation() {
  if (physicsAnimationId) {
    cancelAnimationFrame(physicsAnimationId)
    physicsAnimationId = null
  }
  if (physicsCanvas) {
    window.removeEventListener('resize', () => {})
    physicsCanvas = null
  }
  physicsCtx = null
  physicsParticles = []
}

// 创建烟雾系统
function createSmokeSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/smoke.png',
    startColor: new Cesium.Color(0.2, 0.2, 0.2, 0.6),
    endColor: new Cesium.Color(0.9, 0.9, 0.9, 0.0),
    startScale: 1.0,
    endScale: 6.0,
    minimumParticleLife: 2.0,
    maximumParticleLife: 4.5,
    minimumSpeed: 2.0,
    maximumSpeed: 5.0,
    imageSize: new Cesium.Cartesian2(25, 25),
    emissionRate: 60.0,
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(3.0),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      const currentGravity = (viewMode.value === 'physics') ? smokeAdjust.gravity : 2.5;
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, currentGravity * dt, gravityScratch);
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);

      // 叠加环境风力效果
      if (viewMode.value === 'physics') {
        const center = smokeParticle 
          ? Cesium.Matrix4.getTranslation(smokeParticle.modelMatrix, new Cesium.Cartesian3())
          : Cesium.Cartesian3.fromDegrees(lng, lat, 0.0);
        const enuMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(center);
        const eastVec = Cesium.Matrix4.getColumn(enuMatrix, 0, new Cesium.Cartesian3());
        const northVec = Cesium.Matrix4.getColumn(enuMatrix, 1, new Cesium.Cartesian3());

        const rad = smokeAdjust.windDirection * Math.PI / 180;
        const windEastForce = smokeAdjust.windSpeed * Math.sin(rad) * dt * 0.4;
        const windNorthForce = smokeAdjust.windSpeed * Math.cos(rad) * dt * 0.4;

        const windVec = new Cesium.Cartesian3();
        const eastOffset = new Cesium.Cartesian3();
        const northOffset = new Cesium.Cartesian3();
        Cesium.Cartesian3.multiplyByScalar(eastVec, windEastForce, eastOffset);
        Cesium.Cartesian3.multiplyByScalar(northVec, windNorthForce, northOffset);
        Cesium.Cartesian3.add(eastOffset, northOffset, windVec);

        Cesium.Cartesian3.add(particle.velocity, windVec, particle.velocity);
      }
    }
  });
}

// 创建火焰系统
function createFireSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/explosion00.png',
    startColor: new Cesium.Color(1.0, 0.9, 0.5, 0.8),
    endColor: new Cesium.Color(1.0, 0.3, 0.0, 0.0),
    startScale: 1.5,
    endScale: 4.5,
    minimumParticleLife: 1.0,
    maximumParticleLife: 2.5,
    minimumSpeed: 3.0,
    maximumSpeed: 7.0,
    imageSize: new Cesium.Cartesian2(25, 25),
    emissionRate: 65.0,
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(2.0),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      const currentGravity = (viewMode.value === 'physics') ? fireAdjust.gravity : 5.0;
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, currentGravity * dt, gravityScratch);
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);

      // 叠加环境风力效果
      if (viewMode.value === 'physics') {
        const center = fireParticle 
          ? Cesium.Matrix4.getTranslation(fireParticle.modelMatrix, new Cesium.Cartesian3())
          : Cesium.Cartesian3.fromDegrees(lng, lat, 0.0);
        const enuMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(center);
        const eastVec = Cesium.Matrix4.getColumn(enuMatrix, 0, new Cesium.Cartesian3());
        const northVec = Cesium.Matrix4.getColumn(enuMatrix, 1, new Cesium.Cartesian3());

        const rad = fireAdjust.windDirection * Math.PI / 180;
        const windEastForce = fireAdjust.windSpeed * Math.sin(rad) * dt * 0.4;
        const windNorthForce = fireAdjust.windSpeed * Math.cos(rad) * dt * 0.4;

        const windVec = new Cesium.Cartesian3();
        const eastOffset = new Cesium.Cartesian3();
        const northOffset = new Cesium.Cartesian3();
        Cesium.Cartesian3.multiplyByScalar(eastVec, windEastForce, eastOffset);
        Cesium.Cartesian3.multiplyByScalar(northVec, windNorthForce, northOffset);
        Cesium.Cartesian3.add(eastOffset, northOffset, windVec);

        Cesium.Cartesian3.add(particle.velocity, windVec, particle.velocity);
      }
    }
  });
}

// 创建绿色有毒气体扩散系统
function createDiffusionSystem(lng, lat) {
  const center = Cesium.Cartesian3.fromDegrees(lng, lat, 0.8);
  const enuMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(center);
  const eastVec = Cesium.Matrix4.getColumn(enuMatrix, 0, new Cesium.Cartesian3());
  const northVec = Cesium.Matrix4.getColumn(enuMatrix, 1, new Cesium.Cartesian3());
  const upVec = Cesium.Matrix4.getColumn(enuMatrix, 2, new Cesium.Cartesian3());

  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/whitePuff00.png',
    startColor: new Cesium.Color(0.35, 0.8, 0.35, 0.45),
    endColor: new Cesium.Color(0.45, 0.85, 0.45, 0.0),
    startScale: 0.8,
    endScale: 8.0,
    minimumParticleLife: 4.0,
    maximumParticleLife: 6.5,
    minimumSpeed: 2.0,
    maximumSpeed: 5.5,
    imageSize: new Cesium.Cartesian2(9, 9),
    emissionRate: 120.0,
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(2.5),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(center),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      const buoyancy = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(upVec, 0.5 * dt, buoyancy);
      Cesium.Cartesian3.add(particle.velocity, buoyancy, particle.velocity);
      
      const enuMatrixDynamic = diffusionParticle 
        ? Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Matrix4.getTranslation(diffusionParticle.modelMatrix, new Cesium.Cartesian3()))
        : enuMatrix;
      const currentEastVec = Cesium.Matrix4.getColumn(enuMatrixDynamic, 0, new Cesium.Cartesian3());
      const currentNorthVec = Cesium.Matrix4.getColumn(enuMatrixDynamic, 1, new Cesium.Cartesian3());

      if (viewMode.value === 'physics') {
        // 动态风速风向影响
        const rad = diffusionAdjust.windDirection * Math.PI / 180;
        const windEastForce = diffusionAdjust.windSpeed * Math.sin(rad) * dt * 0.45;
        const windNorthForce = diffusionAdjust.windSpeed * Math.cos(rad) * dt * 0.45;

        const windVec = new Cesium.Cartesian3();
        const eastOffset = new Cesium.Cartesian3();
        const northOffset = new Cesium.Cartesian3();
        Cesium.Cartesian3.multiplyByScalar(currentEastVec, windEastForce, eastOffset);
        Cesium.Cartesian3.multiplyByScalar(currentNorthVec, windNorthForce, northOffset);
        Cesium.Cartesian3.add(eastOffset, northOffset, windVec);

        Cesium.Cartesian3.add(particle.velocity, windVec, particle.velocity);
      } else {
        // 默认三维模式的风力效果
        const windEast = new Cesium.Cartesian3();
        Cesium.Cartesian3.multiplyByScalar(currentEastVec, 0.5 * dt, windEast);
        Cesium.Cartesian3.add(particle.velocity, windEast, particle.velocity);
        
        const windNorth = new Cesium.Cartesian3();
        Cesium.Cartesian3.multiplyByScalar(currentNorthVec, 0.25 * dt, windNorth);
        Cesium.Cartesian3.add(particle.velocity, windNorth, particle.velocity);
      }

      const currentCenter = diffusionParticle 
        ? Cesium.Matrix4.getTranslation(diffusionParticle.modelMatrix, new Cesium.Cartesian3())
        : center;
      const offset = Cesium.Cartesian3.subtract(particle.position, currentCenter, new Cesium.Cartesian3());
      const dist = Cesium.Cartesian3.magnitude(offset);
      if (dist > 0.01) {
        const dir = new Cesium.Cartesian3();
        Cesium.Cartesian3.normalize(offset, dir);
        
        const elapsed = diffusionStartTime ? (Date.now() - diffusionStartTime) / 1000 : 0;
        const systemTimeRatio = Math.min(elapsed / 15.0, 1.0);
        
        const extraForce = (4.0 + 12.0 * systemTimeRatio) * dt;
        const expansion = new Cesium.Cartesian3();
        Cesium.Cartesian3.multiplyByScalar(dir, extraForce, expansion);
        Cesium.Cartesian3.add(particle.velocity, expansion, particle.velocity);
        
        const ageRatio = particle.age / particle.life;
        const currentEndScale = (viewMode.value === 'physics' ? (diffusionAdjust.imageWidth * 0.9) : 8.0) + 8.0 * systemTimeRatio;
        particle.scale = 0.8 + (currentEndScale - 0.8) * ageRatio;
      }

      const currentDrag = (viewMode.value === 'physics') ? diffusionAdjust.drag : 0.96;
      const dragFactor = Math.pow(currentDrag, dt * 60);
      particle.velocity.x *= dragFactor;
      particle.velocity.y *= dragFactor;
      particle.velocity.z *= dragFactor;
    }
  });
}

async function adjustParticleHeight(particleSystem, lng, lat, heightOffset = 0.0) {
  if (!viewer) return;
  const carto = Cesium.Cartographic.fromDegrees(lng, lat);
  try {
    // 异步查询当前地形高度，使粒子贴合地表面渲染，避免被深度缓冲区遮挡
    let height = heightOffset;
    if (viewer.terrainProvider && !(viewer.terrainProvider instanceof Cesium.EllipsoidTerrainProvider)) {
      const [sampled] = await Cesium.sampleTerrainMostDetailed(viewer.terrainProvider, [carto]);
      if (!viewer) return;
      if (sampled && typeof sampled.height === 'number') {
        height = sampled.height + heightOffset;
      }
    }
    if (!viewer) return;
    particleSystem.modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(
      Cesium.Cartesian3.fromDegrees(lng, lat, height)
    );
  } catch (e) {
    console.warn('调整粒子系统高度失败:', e);
  }
}

function initParticleSystems() {
  if (!viewer) return;
  try {
    const xtCoords = scenePositions.xiantao[activeScene.value];
    const hgCoords = scenePositions.huanggang[activeScene.value];

    smokeParticle = viewer.scene.primitives.add(createSmokeSystem(xtCoords.lng, xtCoords.lat));
    fireParticle = viewer.scene.primitives.add(createFireSystem(xtCoords.lng, xtCoords.lat));
    diffusionParticle = viewer.scene.primitives.add(createDiffusionSystem(hgCoords.lng, hgCoords.lat));
    
    // 异步调整粒子高度使其紧贴地形表面
    adjustParticleHeight(smokeParticle, xtCoords.lng, xtCoords.lat, 2.0);
    adjustParticleHeight(fireParticle, xtCoords.lng, xtCoords.lat, 2.0);
    adjustParticleHeight(diffusionParticle, hgCoords.lng, hgCoords.lat, 2.8);

    // 更新可见性
    updateParticlesVisibility(currentCity.value);
  } catch (error) {
    console.error('初始化粒子系统失败:', error);
  }
}

function updateParticlesVisibility(city) {
  if (city === 'xiantao') {
    if (smokeParticle) smokeParticle.show = true;
    if (fireParticle) fireParticle.show = true;
    if (diffusionParticle) diffusionParticle.show = false;
    diffusionStartTime = null;
  } else {
    if (smokeParticle) smokeParticle.show = false;
    if (fireParticle) fireParticle.show = false;
    if (diffusionParticle) {
      diffusionParticle.show = true;
      if (!diffusionStartTime) {
        diffusionStartTime = Date.now();
      }
    }
  }
}

onBeforeUnmount(() => {
  stop2DPhysicsSimulation()
  if (initSimulationViewerTimeout) {
    clearTimeout(initSimulationViewerTimeout)
    initSimulationViewerTimeout = null
  }
  if (viewer) {
    if (mouseHandler) {
      mouseHandler.destroy();
      mouseHandler = null;
    }
    persistentCityEntities.forEach(entity => {
      viewer.entities.remove(entity);
    });
    persistentCityEntities = [];
    if (preRenderListener) {
      viewer.scene.preRender.removeEventListener(preRenderListener);
      preRenderListener = null;
    }
    if (removeLightListener) {
      removeLightListener()
      removeLightListener = null
    }
    if (smokeParticle) {
      viewer.scene.primitives.remove(smokeParticle);
      smokeParticle = null;
    }
    if (fireParticle) {
      viewer.scene.primitives.remove(fireParticle);
      fireParticle = null;
    }
    if (diffusionParticle) {
      viewer.scene.primitives.remove(diffusionParticle);
      diffusionParticle = null;
    }
    try {
      if (viewer && !viewer.isDestroyed()) {
        viewer.destroy();
      }
    } catch (destroyError) {
      console.warn('销毁 viewer 时出错:', destroyError);
    }
    viewer = null;
    window.simulationViewer = null;
  }
})
</script>

<style scoped>
.simulation-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: var(--bg-color);
  padding: 20px;
  box-sizing: border-box;
}

.cesium-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
}

.three-d-loading-overlay {
  position: absolute;
  inset: 20px;
  z-index: 12;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #67e8f9;
  font-size: 15px;
  background: rgba(2, 8, 20, 0.76);
  border: 1px solid rgba(0, 229, 255, 0.35);
  border-radius: 8px;
  pointer-events: none;
}

.three-d-loading-overlay.error {
  color: #fca5a5;
  border-color: rgba(248, 113, 113, 0.55);
}

.three-d-titlebar,
.three-d-scene-card,
.three-d-legend,
.three-d-statusbar {
  position: absolute;
  z-index: 20;
  color: #dbeafe;
  border: 1px solid rgba(96, 165, 250, 0.3);
  background: linear-gradient(135deg, rgba(5, 15, 31, 0.9), rgba(11, 29, 52, 0.78));
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28), inset 0 1px rgba(186, 230, 253, 0.08);
  backdrop-filter: blur(12px);
}

.three-d-titlebar {
  top: 42px;
  left: 42px;
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 318px;
  padding: 11px 14px;
  border-radius: 9px;
}

.three-d-title-mark {
  color: #38bdf8;
  font-size: 26px;
  text-shadow: 0 0 13px rgba(56, 189, 248, 0.85);
}

.three-d-eyebrow,
.three-d-card-label {
  color: #7dd3fc;
  font: 700 9px/1.2 "Segoe UI", sans-serif;
  letter-spacing: 1.15px;
}

.three-d-title {
  margin-top: 3px;
  color: #f8fafc;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 1px;
}

.three-d-live {
  margin-left: auto;
  font-size: 11px;
  color: #a7f3d0;
  white-space: nowrap;
}

.three-d-live i,
.three-d-status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 6px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 9px #34d399;
  animation: three-d-pulse 1.6s ease-in-out infinite;
}

@keyframes three-d-pulse { 50% { opacity: 0.35; transform: scale(1.45); } }

.three-d-scene-card {
  top: 122px;
  left: 42px;
  width: 220px;
  padding: 13px 15px;
  border-radius: 8px;
}

.three-d-scene-card strong { display: block; margin: 7px 0 4px; color: #f8fafc; font-size: 15px; }
.three-d-scene-card span { color: #94a3b8; font-size: 11px; }
.three-d-card-divider { height: 1px; margin: 11px 0 8px; background: rgba(96, 165, 250, 0.2); }
.three-d-card-meta { color: #cbd5e1; font-size: 11px; }
.three-d-card-meta b { margin-right: 4px; color: #38bdf8; font-size: 16px; }

.three-d-legend {
  top: 122px;
  right: 42px;
  width: 142px;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 11px;
  line-height: 1.95;
}

.three-d-legend-title { margin-bottom: 4px; color: #7dd3fc; font-size: 12px; font-weight: 700; border-bottom: 1px solid rgba(96, 165, 250, 0.2); }
.three-d-legend i { display: inline-block; width: 7px; height: 7px; margin-right: 8px; border-radius: 50%; box-shadow: 0 0 7px currentColor; }
.three-d-legend .medical { color: #22c55e; background: currentColor; }.three-d-legend .fire { color: #f97316; background: currentColor; }.three-d-legend .police { color: #3b82f6; background: currentColor; }.three-d-legend .hazmat { color: #a855f7; background: currentColor; }.three-d-legend .road { color: #94a3b8; background: currentColor; }

.three-d-statusbar {
  right: 42px;
  bottom: 42px;
  display: flex;
  align-items: center;
  padding: 9px 14px;
  border-radius: 7px;
  color: #cbd5e1;
  font-size: 11px;
}
.three-d-status-separator { width: 1px; height: 14px; margin: 0 12px; background: rgba(148, 163, 184, 0.35); }

@media (max-width: 900px) {
  .three-d-titlebar { left: 28px; min-width: 270px; }
  .three-d-scene-card { left: 28px; }
  .three-d-legend { right: 28px; }
  .three-d-statusbar { right: 28px; }
}

/* 三维态势大屏：以协同响应指挥的低饱和蓝黑玻璃态为基调。 */
.is-three-d .cesium-container { border: 0; border-radius: 0; box-shadow: none; }
.three-d-vignette { position: absolute; inset: 20px; z-index: 2; pointer-events: none; background: radial-gradient(ellipse at center, transparent 42%, rgba(1, 8, 20, .18) 100%); box-shadow: inset 0 0 90px rgba(1, 8, 20, .48); }
.three-d-commandbar { position:absolute; z-index:20; top:34px; left:42px; right:42px; height:62px; display:flex; align-items:center; padding:0 18px; border:1px solid rgba(125,211,252,.22); border-radius:10px; background:linear-gradient(90deg,rgba(5,17,35,.94),rgba(10,30,54,.76)); box-shadow:0 14px 34px rgba(0,0,0,.34), inset 0 1px rgba(255,255,255,.05); backdrop-filter:blur(15px); }
.three-d-brand { display:flex; align-items:center; gap:10px; min-width:260px; }.three-d-brand>span { color:#38bdf8; font-size:26px; text-shadow:0 0 14px #38bdf8; }.three-d-brand small { display:block; color:#7dd3fc; font:700 8px/1.1 Consolas,sans-serif; letter-spacing:1.5px; }.three-d-brand strong { display:block; margin-top:4px; color:#f1f5f9; font-size:16px; letter-spacing:1px; }
.three-d-mode-switch { display:flex; align-self:stretch; margin:auto; }.three-d-mode-switch button,.three-d-city-switch button { border:0; background:transparent; color:#94a3b8; cursor:pointer; transition:.2s; }.three-d-mode-switch button { padding:0 17px; border-bottom:2px solid transparent; font-size:12px; }.three-d-mode-switch button:hover,.three-d-mode-switch button.active { color:#e0f2fe; border-color:#38bdf8; background:rgba(14,165,233,.09); }
.three-d-city-switch { display:flex; gap:5px; padding:4px; border:1px solid rgba(148,163,184,.18); border-radius:6px; }.three-d-city-switch button { padding:7px 9px; border-radius:4px; font-size:11px; }.three-d-city-switch button.active { color:#dff8ff; background:rgba(14,165,233,.2); box-shadow:inset 0 0 0 1px rgba(56,189,248,.28); }
.three-d-situation-panel,.three-d-force-panel { position:absolute; z-index:20; border:1px solid rgba(125,211,252,.23); border-radius:9px; background:linear-gradient(145deg,rgba(5,17,35,.9),rgba(9,29,52,.7)); box-shadow:0 12px 28px rgba(0,0,0,.28); backdrop-filter:blur(13px); }.three-d-situation-panel { top:116px; left:42px; width:220px; padding:16px; }.three-d-panel-kicker { color:#7dd3fc; font:700 9px/1 Consolas,sans-serif; letter-spacing:1.4px; }.three-d-situation-panel strong { display:block; margin:10px 0 5px; color:#f8fafc; font-size:17px; }.three-d-situation-panel p { margin:0; color:#94a3b8; font-size:11px; }.three-d-risk { display:flex; justify-content:space-between; align-items:center; margin:16px -16px 0; padding:10px 16px; border-top:1px solid rgba(125,211,252,.16); border-bottom:1px solid rgba(125,211,252,.12); color:#94a3b8; font-size:11px; }.three-d-risk b { color:#fbbf24; font-size:14px; }.three-d-kpis { display:flex; gap:22px; margin-top:13px; }.three-d-kpis b,.three-d-kpis span { display:block; }.three-d-kpis b { color:#e0f2fe; font-size:17px; }.three-d-kpis span { margin-top:3px; color:#64748b; font-size:10px; }
.three-d-force-panel { top:116px; right:42px; width:210px; padding:13px 15px; }.three-d-panel-head { display:flex; justify-content:space-between; padding-bottom:9px; border-bottom:1px solid rgba(125,211,252,.16); color:#dbeafe; font-size:12px; font-weight:700; }.three-d-panel-head em { color:#6ee7b7; font:700 8px/1.5 Consolas,sans-serif; letter-spacing:.5px; }.three-d-panel-head i { display:inline-block; width:5px; height:5px; margin-right:4px; border-radius:50%; background:#34d399; box-shadow:0 0 7px #34d399; }.three-d-force { display:flex; align-items:center; gap:8px; padding:8px 0 5px; border-bottom:1px solid rgba(125,211,252,.08); color:#cbd5e1; font-size:11px; }.three-d-force:last-child { border:0; }.three-d-force i { width:7px; height:7px; border-radius:50%; background:currentColor; box-shadow:0 0 7px currentColor; }.three-d-force .medical { color:#22c55e; }.three-d-force .fire { color:#fb923c; }.three-d-force .police { color:#60a5fa; }.three-d-force .hazmat { color:#c084fc; }.three-d-force .road { color:#cbd5e1; }.three-d-force b { margin-left:auto; color:#86efac; font-size:10px; font-weight:500; }
.three-d-timeline-bar { position:absolute; z-index:20; bottom:36px; left:50%; transform:translateX(-50%); display:flex; align-items:center; width:min(680px,58vw); padding:12px 16px; border:1px solid rgba(125,211,252,.23); border-radius:9px; background:rgba(5,17,35,.88); box-shadow:0 12px 28px rgba(0,0,0,.32); backdrop-filter:blur(13px); }.three-d-timeline-title { min-width:128px; font-size:10px; color:#94a3b8; }.three-d-timeline-title i { display:inline-block; width:7px; height:7px; margin-right:5px; border-radius:50%; background:#34d399; box-shadow:0 0 8px #34d399; }.three-d-timeline-title strong { display:block; margin:4px 0 0 12px; color:#e0f2fe; font-size:12px; }.three-d-track { position:relative; flex:1; display:flex; justify-content:space-between; align-items:center; height:20px; }.three-d-track span { position:absolute; left:2px; right:2px; height:1px; background:linear-gradient(90deg,#0284c7,#38bdf8,#475569); }.three-d-track i { position:relative; width:7px; height:7px; border:2px solid #0f253e; border-radius:50%; background:#38bdf8; box-shadow:0 0 0 1px #38bdf8,0 0 8px rgba(56,189,248,.55); }.three-d-track i.active { width:10px; height:10px; background:#fbbf24; box-shadow:0 0 0 1px #fbbf24,0 0 12px #fbbf24; }.three-d-timeline-meta { min-width:140px; margin-left:14px; color:#64748b; font-size:10px; line-height:1.45; }
@media (max-width: 1050px) { .three-d-brand { min-width:210px; }.three-d-mode-switch button { padding:0 9px; }.three-d-timeline-meta { display:none; }.three-d-timeline-bar { width:55vw; } }

/* 城市悬浮提示框样式 - 赛博朋克高阶战术 HUD 标签 */
.city-tooltip {
  position: absolute;
  z-index: 9999;
  pointer-events: none;
  background: linear-gradient(135deg, rgba(6, 18, 38, 0.92) 0%, rgba(10, 28, 54, 0.88) 100%);
  border: 1px solid rgba(0, 255, 216, 0.45);
  border-radius: 6px;
  padding: 8px 14px 10px 14px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.75), 0 0 16px rgba(0, 255, 216, 0.25), inset 0 0 12px rgba(0, 255, 216, 0.12);
  backdrop-filter: blur(10px);
  min-width: 125px;
  transform: translate(-10%, -120%);
  transition: opacity 0.15s ease-out, transform 0.15s cubic-bezier(0.18, 0.89, 0.32, 1.28);
}

.hud-glow-line {
  position: absolute;
  bottom: 0;
  left: 15%;
  right: 15%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00ffd8, transparent);
  box-shadow: 0 0 8px #00ffd8;
}

.hud-corner {
  position: absolute;
  width: 6px;
  height: 6px;
  border-color: #00ffd8;
  border-style: solid;
  border-width: 0;
}
.hud-corner.top-left { top: -1px; left: -1px; border-top-width: 2px; border-left-width: 2px; }
.hud-corner.top-right { top: -1px; right: -1px; border-top-width: 2px; border-right-width: 2px; }
.hud-corner.bottom-left { bottom: -1px; left: -1px; border-bottom-width: 2px; border-left-width: 2px; }
.hud-corner.bottom-right { bottom: -1px; right: -1px; border-bottom-width: 2px; border-right-width: 2px; }

.hud-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hud-icon-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  background: rgba(0, 255, 216, 0.12);
  border: 1px solid rgba(0, 255, 216, 0.5);
  border-radius: 4px;
  color: #00ffd8;
}

.hud-radar-svg {
  width: 18px;
  height: 18px;
  animation: hud-radar-spin 5s linear infinite;
}

@keyframes hud-radar-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.hud-radar-dot {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 5px;
  height: 5px;
  background: #00ff66;
  border-radius: 50%;
  box-shadow: 0 0 6px #00ff66;
  animation: hud-dot-pulse 1.2s infinite ease-in-out;
}

@keyframes hud-dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(1.5); }
}

.hud-text-wrap {
  display: flex;
  flex-direction: column;
}

.hud-sub-label {
  font-size: 9px;
  color: #00ffd8;
  letter-spacing: 1px;
  opacity: 0.85;
  font-family: 'Courier New', Courier, monospace;
  margin-bottom: 2px;
}

.hud-main-title {
  color: #ffffff;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 1.5px;
  text-shadow: 0 0 8px rgba(0, 255, 216, 0.6), 0 0 16px rgba(0, 255, 216, 0.3);
  background: linear-gradient(180deg, #ffffff 0%, #c1f3ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.view-toggle {
  position: absolute;
  top: 40px;
  left: 30px;
  transform: none;
  background: rgba(6, 22, 40, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-radius: 8px;
  padding: 6px;
  display: flex;
  gap: 8px;
  z-index: 1000;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.35);
}

.view-toggle button {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid transparent;
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 600;
}

.view-toggle button:hover {
  color: #00e5ff;
}

.view-toggle button.active {
  background: rgba(0, 229, 255, 0.15);
  border-color: rgba(0, 229, 255, 0.4);
  color: #00e5ff;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.city-toggle {
  position: absolute;
  top: 40px;
  right: 30px;
  background: rgba(6, 22, 40, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-radius: 8px;
  padding: 6px;
  display: flex;
  gap: 8px;
  z-index: 1000;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.35);
}

.city-toggle button {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid transparent;
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 600;
}

.city-toggle button:hover {
  color: #00e5ff;
}

.city-toggle button.active {
  background: rgba(0, 229, 255, 0.15);
  border-color: rgba(0, 229, 255, 0.4);
  color: #00e5ff;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.iframe-container {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
}

.deduction-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 8px;
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #00e5ff;
  font-size: 16px;
  font-weight: bold;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(0, 229, 255, 0.2);
  border-top-color: #00e5ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #ef4444;
  font-size: 16px;
  font-weight: bold;
}

.error-icon {
  font-size: 32px;
}

.retry-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #ef4444;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.retry-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
}

/* 物理仿真微调面板样式 */
.physics-tweak-panel {
  position: absolute;
  top: 100px;
  left: 40px;
  bottom: 40px;
  width: 350px;
  z-index: 1000;
  background: linear-gradient(135deg, rgba(6, 18, 38, 0.92) 0%, rgba(10, 28, 54, 0.88) 100%);
  border: 1px solid rgba(0, 229, 255, 0.45);
  border-radius: 8px;
  padding: 18px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 229, 255, 0.2);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  color: #c1f3ff;
  overflow-y: auto;
}

.physics-tweak-header {
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.25);
  padding-bottom: 12px;
  margin-bottom: 15px;
}

.physics-tweak-header .icon {
  font-size: 20px;
}

.physics-tweak-header .title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #00ffd8;
  text-shadow: 0 0 8px rgba(0, 255, 216, 0.5);
}

.physics-tweak-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.physics-tweak-body .section-title {
  font-size: 13px;
  font-weight: 600;
  color: #38bdf8;
  border-left: 2px solid #38bdf8;
  padding-left: 6px;
  margin-bottom: 8px;
}

.phase-selector {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.phase-btn {
  padding: 8px 6px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  color: #94a3b8;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.25s ease;
}

.phase-btn:hover {
  border-color: rgba(56, 189, 248, 0.5);
  color: #38bdf8;
}

.phase-btn.active {
  background: rgba(56, 189, 248, 0.2);
  border-color: #38bdf8;
  color: #38bdf8;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.25);
}

.physics-tab-header {
  display: flex;
  gap: 6px;
  background: rgba(15, 23, 42, 0.5);
  padding: 4px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.physics-tab-header .tab-btn {
  flex: 1;
  padding: 8px 4px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #64748b;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.physics-tab-header .tab-btn:hover {
  color: #38bdf8;
}

.physics-tab-header .tab-btn.active {
  background: rgba(56, 189, 248, 0.15);
  color: #00ffd8;
}

.tweak-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(15, 23, 42, 0.3);
  padding: 10px;
  border-radius: 6px;
}

.control-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.control-row label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.slider-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.slider-group input[type="range"] {
  flex: 1;
  -webkit-appearance: none;
  background: rgba(30, 41, 59, 0.8);
  height: 4px;
  border-radius: 2px;
  outline: none;
}

.slider-group input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #00ffd8;
  cursor: pointer;
  box-shadow: 0 0 6px #00ffd8;
  transition: transform 0.1s;
}

.slider-group input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.val-text {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  color: #34d399;
  min-width: 48px;
  text-align: right;
  font-weight: bold;
}

.panel-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.action-btn {
  flex: 1;
  padding: 9px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn.primary {
  background: #0284c7;
  color: #fff;
  border: 1px solid #0284c7;
}

.action-btn.primary:hover {
  background: #0369a1;
  box-shadow: 0 0 10px rgba(2, 132, 199, 0.4);
}

.action-btn.secondary {
  background: rgba(30, 41, 59, 0.6);
  color: #cbd5e1;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.action-btn.secondary:hover {
  background: rgba(51, 65, 85, 0.8);
  border-color: rgba(255, 255, 255, 0.15);
}

.copied-feedback {
  font-size: 11px;
  color: #34d399;
  text-align: center;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 6px;
  border-radius: 4px;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 三维推演采用与协同响应一致的深海蓝玻璃 HUD：信息靠边，不遮挡事故现场。 */
.is-three-d {
  background: #020817;
}

.is-three-d .cesium-container {
  inset: 20px !important;
  overflow: hidden;
  border: 1px solid rgba(96, 165, 250, 0.28);
  border-radius: 12px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.42), inset 0 0 0 1px rgba(255, 255, 255, 0.025);
}

.is-three-d .view-toggle,
.is-three-d .city-toggle {
  z-index: 30;
  border-color: rgba(96, 165, 250, 0.38);
  background: rgba(10, 18, 32, 0.86);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.is-three-d .view-toggle button.active,
.is-three-d .city-toggle button.active {
  color: #dbeafe;
  border-color: rgba(96, 165, 250, 0.72);
  background: rgba(59, 130, 246, 0.18);
  box-shadow: inset 0 0 16px rgba(59, 130, 246, 0.12);
}

.three-d-vignette {
  inset: 20px;
  border-radius: 12px;
  background:
    linear-gradient(90deg, rgba(2, 8, 23, 0.24), transparent 24%, transparent 76%, rgba(2, 8, 23, 0.24)),
    radial-gradient(ellipse at center, transparent 38%, rgba(1, 8, 20, 0.24) 100%);
  box-shadow: inset 0 0 80px rgba(1, 8, 20, 0.42);
}

.three-d-situation-panel,
.three-d-force-panel,
.three-d-timeline-bar {
  border-color: rgba(96, 165, 250, 0.3);
  background: linear-gradient(140deg, rgba(10, 18, 32, 0.93), rgba(15, 35, 61, 0.76));
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.34), inset 0 1px 0 rgba(191, 219, 254, 0.08);
  backdrop-filter: blur(16px);
}

.three-d-situation-panel {
  top: 116px;
  left: 42px;
  width: 238px;
  padding: 15px 16px 13px;
}

.three-d-panel-kicker {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #93c5fd;
}

.three-d-panel-kicker i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 9px #34d399;
}

.three-d-situation-panel strong {
  margin: 9px 0 4px;
  font-size: 18px;
  letter-spacing: 0.5px;
}

.three-d-risk {
  margin-top: 14px;
  border-color: rgba(96, 165, 250, 0.16);
  background: rgba(2, 6, 23, 0.24);
}

.three-d-kpis {
  justify-content: space-between;
  gap: 0;
  margin-top: 13px;
}

.three-d-kpis b { color: #dbeafe; }

.three-d-panel-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
  margin-top: 14px;
}

.three-d-panel-actions button {
  padding: 7px 5px;
  border: 1px solid rgba(96, 165, 250, 0.32);
  border-radius: 5px;
  color: #bfdbfe;
  background: rgba(30, 58, 138, 0.18);
  font-size: 11px;
  cursor: pointer;
  transition: 0.2s ease;
}

.three-d-panel-actions button:hover {
  color: #fff;
  border-color: #60a5fa;
  background: rgba(59, 130, 246, 0.35);
}

.three-d-force-panel {
  top: 116px;
  right: 42px;
  width: 222px;
  padding: 13px 15px;
}

.three-d-force {
  padding: 9px 0 6px;
  border-color: rgba(148, 163, 184, 0.1);
}

.three-d-optimization-log {
  position: absolute;
  z-index: 20;
  top: 395px;
  left: 42px;
  width: 292px;
  max-height: calc(100% - 430px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(56, 189, 248, 0.36);
  border-radius: 9px;
  background: linear-gradient(145deg, rgba(6, 18, 38, 0.94), rgba(4, 13, 28, 0.88));
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.34), inset 0 1px 0 rgba(191, 219, 254, 0.08);
  backdrop-filter: blur(16px);
}

.three-d-log-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 11px 13px;
  border-bottom: 1px solid rgba(56, 189, 248, 0.22);
}

.three-d-log-head strong,
.three-d-log-head span { display: block; }
.three-d-log-head strong { color: #f1f5f9; font-size: 17px; letter-spacing: 0.3px; }
.three-d-log-head span { margin-top: 4px; color: #7dd3fc; font: 700 11px/1 Consolas, monospace; letter-spacing: 0.8px; }
.three-d-log-head > b { flex: 0 0 auto; padding: 6px 8px; border: 1px solid rgba(52, 211, 153, 0.4); border-radius: 4px; color: #6ee7b7; background: rgba(16, 185, 129, 0.1); font-size: 11px; }
.three-d-log-head > b.loading { color: #fcd34d; border-color: rgba(251, 191, 36, 0.45); background: rgba(245, 158, 11, 0.1); }

.three-d-log-terminal { padding: 11px 13px 9px; border-left: 3px solid #22d3ee; background: rgba(2, 6, 23, 0.42); }
.three-d-log-terminal p { margin: 0 0 7px; color: #67e8f9; font: 600 12px/1.58 Consolas, 'Microsoft YaHei', sans-serif; }
.three-d-log-terminal p:last-child { margin-bottom: 0; }
.three-d-log-terminal p i { margin-right: 4px; color: #22d3ee; font-style: normal; }
.three-d-log-terminal p.success { color: #bbf7d0; }

.three-d-log-results { overflow-y: auto; overscroll-behavior: contain; }
.three-d-log-results::-webkit-scrollbar { width: 4px; }
.three-d-log-results::-webkit-scrollbar-thumb { border-radius: 4px; background: rgba(56, 189, 248, 0.34); }
.three-d-agent-tabs { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 4px; padding: 8px 9px; border-top: 1px solid rgba(148, 163, 184, 0.12); border-bottom: 1px solid rgba(148, 163, 184, 0.12); background: rgba(15, 23, 42, 0.52); }
.three-d-agent-tabs button { overflow: hidden; padding: 7px 1px; border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 4px; color: #94a3b8; background: rgba(30, 41, 59, 0.42); cursor: pointer; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; transition: 0.2s ease; }
.three-d-agent-tabs button:hover { color: #e0f2fe; border-color: var(--agent-color); }
.three-d-agent-tabs button.active { color: var(--agent-color); border-color: var(--agent-color); background: color-mix(in srgb, var(--agent-color) 15%, rgba(15, 23, 42, 0.7)); box-shadow: inset 0 0 8px color-mix(in srgb, var(--agent-color) 22%, transparent); font-weight: 700; }
.three-d-agent-decision { padding: 10px 11px; border-top: 1px solid rgba(148, 163, 184, 0.13); border-left: 3px solid var(--agent-color); background: linear-gradient(90deg, color-mix(in srgb, var(--agent-color) 8%, transparent), transparent 65%); }
.three-d-agent-head { display: grid; grid-template-columns: 7px auto 1fr; align-items: center; gap: 6px; }
.three-d-agent-head > span { width: 7px; height: 7px; border-radius: 50%; background: var(--agent-color); box-shadow: 0 0 8px var(--agent-color); }
.three-d-agent-head b { color: var(--agent-color); font-size: 13px; white-space: nowrap; }
.three-d-agent-head strong { overflow: hidden; color: #f1f5f9; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.three-d-agent-metrics { margin-top: 9px; padding: 8px 10px; border: 1px solid rgba(56, 189, 248, 0.16); border-radius: 4px; background: rgba(2, 6, 23, 0.48); }
.three-d-agent-metrics div { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: #cbd5e1; font-size: 12px; line-height: 1.8; }
.three-d-agent-metrics b { color: #22d3ee; font: 700 13px Consolas, monospace; white-space: nowrap; }
.three-d-agent-metrics em { color: #cbd5e1; font: 12px Consolas, monospace; font-style: normal; white-space: nowrap; }
.three-d-agent-losers { margin-top: 9px; color: #e2e8f0; font-size: 12px; line-height: 1.48; }
.three-d-agent-losers > span { display: block; margin-bottom: 3px; }
.three-d-agent-losers p { margin: 3px 0 0; color: #fb7185; }
.three-d-agent-losers p em { display: block; padding-left: 13px; color: #f87171; font-style: normal; font-size: 11px; }
.three-d-agent-losers.empty { color: #64748b; }
.three-d-log-empty { padding: 10px 12px; color: #64748b; font-size: 10px; }

.three-d-timeline-bar {
  bottom: 36px;
  width: min(710px, 61vw);
  padding: 13px 18px;
}

.three-d-timeline-meta {
  display: flex;
  min-width: 150px;
  flex-direction: column;
  gap: 3px;
}

.three-d-timeline-meta b { color: #bfdbfe; font-size: 10px; }

@media (max-width: 900px) {
  .three-d-situation-panel { left: 28px; width: 205px; }
  .three-d-force-panel { right: 28px; width: 190px; }
  .three-d-optimization-log { left: 28px; width: 248px; }
  .three-d-kpis div:last-child,
  .three-d-panel-actions { display: none; }
}

/* 统一采用首页大屏的可读字号层级，避免仿真操作区在大屏上显得过小。 */
.simulation-container { font-size: 16px; }
.view-toggle button,
.city-toggle button { padding: 10px 19px; font-size: 16px; }
.view-toggle,
.city-toggle { gap: 9px; padding: 7px; }

.three-d-panel-kicker { font-size: 11px; }
.three-d-situation-panel p,
.three-d-risk,
.three-d-force { font-size: 13px; }
.three-d-situation-panel strong { font-size: 21px; }
.three-d-risk b { font-size: 17px; }
.three-d-kpis b { font-size: 20px; }
.three-d-kpis span { font-size: 12px; }
.three-d-panel-actions button { padding: 9px 6px; font-size: 13px; }
.three-d-panel-head { font-size: 15px; }
.three-d-panel-head em { font-size: 10px; }
.three-d-force b { font-size: 12px; }
.three-d-timeline-title { font-size: 13px; }
.three-d-timeline-title strong { font-size: 15px; }
.three-d-timeline-meta { font-size: 12px; }
.three-d-timeline-meta b { font-size: 12px; }

.physics-hud { font-size: 16px !important; }
.physics-hud > div:first-child { font-size: 19px !important; }
.physics-tweak-header .title { font-size: 20px; }
.physics-tweak-body .section-title { font-size: 16px; }
.phase-btn,
.physics-tab-header .tab-btn { font-size: 14px; }
.control-row label { font-size: 13px; }
.tweak-controls input,
.tweak-controls select,
.tweak-controls button,
.action-btn { font-size: 14px !important; }

@media (max-width: 900px) {
  .view-toggle button,
  .city-toggle button { padding: 9px 13px; font-size: 14px; }
  .three-d-situation-panel strong { font-size: 19px; }
}

/* 寻优日志使用首页大屏的强调字号，便于在地图背景上快速阅读。 */
.three-d-optimization-log { width: 332px; }
.three-d-log-head { padding: 13px 15px; }
.three-d-log-head strong { font-size: 20px; }
.three-d-log-head span { font-size: 12px; }
.three-d-log-head > b { padding: 7px 9px; font-size: 12px; }
.three-d-log-terminal { padding: 13px 15px 11px; }
.three-d-log-terminal p { font-size: 14px; line-height: 1.65; }
.three-d-agent-tabs { gap: 5px; padding: 10px; }
.three-d-agent-tabs button { padding: 8px 2px; font-size: 12px; }
.three-d-agent-decision { padding: 13px 14px; }
.three-d-agent-head b,
.three-d-agent-head strong { font-size: 15px; }
.three-d-agent-metrics { padding: 10px 12px; }
.three-d-agent-metrics div { font-size: 14px; }
.three-d-agent-metrics b { font-size: 15px; }
.three-d-agent-metrics em { font-size: 14px; }
.three-d-agent-losers { font-size: 14px; line-height: 1.55; }
.three-d-agent-losers p em { font-size: 12px; }

@media (max-width: 900px) {
  .three-d-optimization-log { width: min(332px, calc(100vw - 56px)); }
}

/* 寻优日志大屏卡片：提高信息密度的同时强化标题、状态和决策层级。 */
.three-d-optimization-log {
  width: min(390px, calc(100vw - 56px));
  border: 1px solid rgba(34, 211, 238, 0.56);
  border-radius: 14px;
  background: linear-gradient(155deg, rgba(5, 21, 43, 0.97), rgba(3, 12, 29, 0.94));
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.48), 0 0 28px rgba(14, 165, 233, 0.14), inset 0 1px 0 rgba(186, 230, 253, 0.12);
}
.three-d-optimization-log,
.three-d-optimization-log * {
  font-family: 'Microsoft YaHei', '微软雅黑', 'PingFang SC', 'Segoe UI', Arial, sans-serif !important;
}
.three-d-log-head { align-items: center; padding: 16px 18px; background: linear-gradient(90deg, rgba(14, 165, 233, 0.2), rgba(14, 165, 233, 0.02)); }
.three-d-log-title { display: flex; align-items: center; min-width: 0; gap: 10px; }
.three-d-log-title > i { color: #22d3ee; font-size: 23px; font-style: normal; text-shadow: 0 0 12px rgba(34, 211, 238, 0.8); }
.three-d-log-head strong { font-size: 22px; line-height: 1.18; text-shadow: 0 0 12px rgba(186, 230, 253, 0.22); }
.three-d-log-head span { margin-top: 5px; font-size: 12px; letter-spacing: 1.1px; }
.three-d-log-head > b { padding: 8px 10px; border-radius: 6px; font-size: 13px; box-shadow: inset 0 0 10px rgba(16, 185, 129, 0.09); }
.three-d-log-terminal { margin: 10px 12px 0; padding: 14px 16px 12px; border: 1px solid rgba(34, 211, 238, 0.2); border-left: 4px solid #22d3ee; border-radius: 7px; background: rgba(1, 9, 23, 0.66); }
.three-d-log-terminal p { font-size: 16px; line-height: 1.62; letter-spacing: 0.1px; }
.three-d-log-terminal p i { color: #67e8f9; font-weight: 800; }
.three-d-agent-tabs { gap: 6px; padding: 12px; background: transparent; }
.three-d-agent-tabs button { padding: 9px 3px; border-radius: 7px; font-size: 14px; font-weight: 700; }
.three-d-agent-tabs button.active { box-shadow: 0 0 0 1px var(--agent-color), inset 0 0 16px color-mix(in srgb, var(--agent-color) 25%, transparent), 0 0 12px color-mix(in srgb, var(--agent-color) 25%, transparent); }
.three-d-agent-decision { margin: 0 12px 13px; padding: 15px 16px 16px; border: 1px solid color-mix(in srgb, var(--agent-color) 48%, rgba(148, 163, 184, 0.24)); border-left: 5px solid var(--agent-color); border-radius: 9px; background: linear-gradient(135deg, color-mix(in srgb, var(--agent-color) 13%, rgba(4, 15, 32, 0.9)), rgba(3, 12, 27, 0.74)); }
.three-d-agent-head { grid-template-columns: 9px auto 1fr; gap: 8px; }
.three-d-agent-head > span { width: 9px; height: 9px; }
.three-d-agent-head b { font-size: 17px; }
.three-d-agent-head strong { font-size: 16px; }
.three-d-agent-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 0; border: 0; background: transparent; }
.three-d-agent-metrics div { display: flex; min-height: 60px; flex-direction: column; align-items: flex-start; justify-content: center; padding: 8px 10px; border: 1px solid rgba(56, 189, 248, 0.22); border-radius: 6px; background: rgba(2, 10, 24, 0.66); font-size: 14px; line-height: 1.3; }
.three-d-agent-metrics b { margin-top: 5px; font-size: 17px; }
.three-d-agent-metrics em { margin-top: 5px; font-size: 17px; }
.three-d-agent-losers { padding-top: 10px; border-top: 1px dashed rgba(148, 163, 184, 0.25); font-size: 15px; }
.three-d-agent-losers > span { color: #e2e8f0; font-weight: 700; }
.three-d-agent-losers p { margin-top: 6px; font-size: 14px; }
.three-d-agent-losers p em { padding-left: 16px; font-size: 13px; line-height: 1.42; }

@media (max-width: 520px) {
  .three-d-log-head strong { font-size: 19px; }
  .three-d-log-terminal p { font-size: 14px; }
  .three-d-agent-tabs button { font-size: 12px; }
  .three-d-agent-head b { font-size: 15px; }
  .three-d-agent-head strong { font-size: 14px; }
}

/* 事故态势卡与下方寻优日志共用同一版心，形成左侧对齐的信息栏。 */
.three-d-situation-panel {
  left: 42px;
  width: min(390px, calc(100vw - 56px));
  box-sizing: border-box;
}
.three-d-kpis { gap: 0; }
.three-d-kpis > div { flex: 1; }
.three-d-panel-actions { grid-template-columns: repeat(2, minmax(0, 1fr)); }

@media (max-width: 900px) {
  .three-d-situation-panel { left: 28px; width: min(390px, calc(100vw - 56px)); }
}

</style>
