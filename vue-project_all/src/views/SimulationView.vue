<template>
  <div class="simulation-container">
    <!-- 返回事故时间线按钮 -->
    <button class="back-to-timeline-btn" @click="goBackToTimeline">
      <span class="back-arrow">←</span>
      <span>返回事故时间线</span>
    </button>

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

    <div id="simulationCesiumContainer" class="cesium-container" :style="{ visibility: (viewMode === '3d' || viewMode === 'physics') ? 'visible' : 'hidden', position: 'absolute', top: '20px', left: '20px', right: '20px', bottom: '20px', width: 'auto', height: 'auto', zIndex: 1 }"></div>
    
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
      <iframe v-else :src="iframeSrc" class="deduction-iframe"></iframe>
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
            🚛 货车追尾现场
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
        <div class="phase-selector">
          <button 
            v-for="phase in [3, 4, 5, 6]" 
            :key="phase"
            :class="{ active: selectedPhase === phase }"
            @click="selectPhase(phase)"
            class="phase-btn"
          >
            {{ phase === 3 ? '事故发生' : phase === 4 ? '初期爆发' : phase === 5 ? '剧烈扩散' : '控制减弱' }}
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
          <div class="control-row">
            <label>上升气流 (Gravity)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.gravity" min="0.0" max="6.0" step="0.1" />
              <span class="val-text">{{ smokeAdjust.gravity }}</span>
            </div>
          </div>
          <div class="control-row">
            <label>环境风速 (Wind Speed)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.windSpeed" min="0.0" max="25.0" step="0.5" />
              <span class="val-text">{{ smokeAdjust.windSpeed }}m/s</span>
            </div>
          </div>
          <div class="control-row">
            <label>环境风向 (Wind Direction)</label>
            <div class="slider-group">
              <input type="range" v-model.number="smokeAdjust.windDirection" min="0" max="360" step="5" />
              <span class="val-text">{{ smokeAdjust.windDirection }}°</span>
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
          <div class="control-row">
            <label>上升气流 (Gravity)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.gravity" min="0.0" max="10.0" step="0.1" />
              <span class="val-text">{{ fireAdjust.gravity }}</span>
            </div>
          </div>
          <div class="control-row">
            <label>环境风速 (Wind Speed)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.windSpeed" min="0.0" max="25.0" step="0.5" />
              <span class="val-text">{{ fireAdjust.windSpeed }}m/s</span>
            </div>
          </div>
          <div class="control-row">
            <label>环境风向 (Wind Direction)</label>
            <div class="slider-group">
              <input type="range" v-model.number="fireAdjust.windDirection" min="0" max="360" step="5" />
              <span class="val-text">{{ fireAdjust.windDirection }}°</span>
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
          <div class="control-row">
            <label>空气阻力 (Drag)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.drag" min="0.80" max="1.00" step="0.01" />
              <span class="val-text">{{ diffusionAdjust.drag }}</span>
            </div>
          </div>
          <div class="control-row">
            <label>环境风速 (Wind Speed)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.windSpeed" min="0.0" max="25.0" step="0.5" />
              <span class="val-text">{{ diffusionAdjust.windSpeed }}m/s</span>
            </div>
          </div>
          <div class="control-row">
            <label>环境风向 (Wind Direction)</label>
            <div class="slider-group">
              <input type="range" v-model.number="diffusionAdjust.windDirection" min="0" max="360" step="5" />
              <span class="val-text">{{ diffusionAdjust.windDirection }}°</span>
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
import { onBeforeUnmount, onMounted, ref, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
import * as Cesium from 'cesium'
import { getCollaborativeCommandCenterBaseUrl } from '../config/subsystems'

Cesium.Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIyYTUwYmE4Zi01ZjZlLTQ0MjAtYWMwNS0yYjBkZGFiM2RmOTUiLCJpZCI6MzU4MzQ0LCJpYXQiOjE3NjI1Nzc2NjR9.q9QoG-_99QZ2R2TlUYjiWGhn0-S5I22FFGuou_NAE3Q"

const viewMode = ref('2d')
const iframeSrc = ref('')
const isGenerating2D = ref(false)
const errorMessage = ref('')
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
const route = useRoute()

function goBackToTimeline() {
  // 返回首页大屏总览，并指定跳转到无人感知执行阶段 (第9阶段，索引为 8)
  const scene = currentCity.value === 'xiantao' ? 'rear-end' : 'leakage'
  router.push({
    path: '/',
    query: {
      scene: scene,
      phaseIndex: 8
    }
  })
}
const currentCity = ref(route.query.city === 'huanggang' ? 'huanggang' : 'xiantao')

// 事故现场与坐标配置
const activeScene = ref('truck_crash') // 默认：货车追尾现场

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
const activePhysicsTab = ref('smoke')
const selectedPhase = ref(5) // 默认推演第 5 阶段（剧烈扩散/燃烧）
const copiedMessage = ref('')

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

// 各个阶段的烟雾/火焰/扩散粒子预设配置，按照推演事故线(货车追尾、油罐车泄露)和风向风速来细化
function selectPhase(phaseIndex) {
  selectedPhase.value = phaseIndex;
  
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
      } else if (phaseIndex === 4) { // 初期爆发
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
      } else if (phaseIndex === 5) { // 剧烈燃烧
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
      } else if (phaseIndex === 6) { // 控制减弱
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
      if (phaseIndex === 3) {
        diffusionAdjust.imageWidth = 6;
        diffusionAdjust.imageHeight = 6;
        diffusionAdjust.emissionRate = 30;
        diffusionAdjust.maxSpeed = 2.0;
        diffusionAdjust.minLife = 2.5;
        diffusionAdjust.maxLife = 4.5;
        diffusionAdjust.drag = 0.98;
        diffusionAdjust.windSpeed = 3.0;
        diffusionAdjust.windDirection = 45.0;
      } else if (phaseIndex === 4) {
        diffusionAdjust.imageWidth = 9;
        diffusionAdjust.imageHeight = 9;
        diffusionAdjust.emissionRate = 75;
        diffusionAdjust.maxSpeed = 4.0;
        diffusionAdjust.minLife = 3.5;
        diffusionAdjust.maxLife = 6.0;
        diffusionAdjust.drag = 0.96;
        diffusionAdjust.windSpeed = 5.0;
        diffusionAdjust.windDirection = 60.0;
      } else if (phaseIndex === 5) {
        diffusionAdjust.imageWidth = 15;
        diffusionAdjust.imageHeight = 15;
        diffusionAdjust.emissionRate = 135;
        diffusionAdjust.maxSpeed = 6.5;
        diffusionAdjust.minLife = 4.5;
        diffusionAdjust.maxLife = 7.5;
        diffusionAdjust.drag = 0.94;
        diffusionAdjust.windSpeed = 10.0;
        diffusionAdjust.windDirection = 90.0;
      } else if (phaseIndex === 6) {
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
      if (phaseIndex === 3) {
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
      } else if (phaseIndex === 4) {
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
      } else if (phaseIndex === 5) {
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
      } else if (phaseIndex === 6) {
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
      if (phaseIndex === 3) {
        diffusionAdjust.imageWidth = 8;
        diffusionAdjust.imageHeight = 8;
        diffusionAdjust.emissionRate = 35;
        diffusionAdjust.maxSpeed = 2.5;
        diffusionAdjust.minLife = 3.0;
        diffusionAdjust.maxLife = 5.0;
        diffusionAdjust.drag = 0.98;
        diffusionAdjust.windSpeed = 1.5;
        diffusionAdjust.windDirection = 270.0;
      } else if (phaseIndex === 4) {
        diffusionAdjust.imageWidth = 12;
        diffusionAdjust.imageHeight = 12;
        diffusionAdjust.emissionRate = 80;
        diffusionAdjust.maxSpeed = 4.5;
        diffusionAdjust.minLife = 4.0;
        diffusionAdjust.maxLife = 6.5;
        diffusionAdjust.drag = 0.96;
        diffusionAdjust.windSpeed = 4.5;
        diffusionAdjust.windDirection = 240.0;
      } else if (phaseIndex === 5) {
        diffusionAdjust.imageWidth = 22;
        diffusionAdjust.imageHeight = 22;
        diffusionAdjust.emissionRate = 180;
        diffusionAdjust.maxSpeed = 8.5;
        diffusionAdjust.minLife = 5.0;
        diffusionAdjust.maxLife = 8.5;
        diffusionAdjust.drag = 0.93;
        diffusionAdjust.windSpeed = 12.0; // 强气流风速，有毒气云迅速推开
        diffusionAdjust.windDirection = 210.0;
      } else if (phaseIndex === 6) {
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
  const city = currentCity.value
  const coords = scenePositions[city][sceneName]
  
  if (viewer) {
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
  selectPhase(selectedPhase.value)
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

// 监听视图模式变化，在物理仿真模式下自动对焦至事故中心
watch(viewMode, (newMode) => {
  if (!viewer) return
  if (newMode === 'physics') {
    const city = currentCity.value
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
    activePhysicsTab.value = (city === 'xiantao') ? 'smoke' : 'diffusion'
    selectPhase(selectedPhase.value)
  } else if (newMode === '3d') {
    if (currentCity.value === 'xiantao') {
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(113.43, 30.29, 120000),
        duration: 2.0
      })
    } else {
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(114.90, 30.70, 380000),
        duration: 2.0
      })
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

const generate2DDeduction = async (city) => {
  const endpoint = city === 'xiantao' ? 'crash' : 'leak'
  isGenerating2D.value = true
  errorMessage.value = ''
  const baseUrl = getCollaborativeCommandCenterBaseUrl()
  try {
    const response = await fetch(`${baseUrl}/api/run_3d_strategy?end_point=${endpoint}`)
    if (!response.ok) {
      console.warn('后端生成策略返回非200状态码，将启用本地/历史二维推演缓存显示。')
    }
  } catch (error) {
    console.warn('请求生成二维推演接口出现异常，自动降级为加载默认二维推演界面:', error)
  } finally {
    // 无论后端动态生成接口成功或异常，始终正常加载并展示二维仿真推演界面（优雅降级）
    iframeSrc.value = `${baseUrl}/2d_deduction.html?t=${Date.now()}`
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
  
  // 清除旧的蒙版
  if (currentMaskEntity) {
    viewer.entities.remove(currentMaskEntity);
    currentMaskEntity = null;
  }

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
    { name: '武汉市', file: 'wuhan.json', color: '#00ffd8', center: [114.30, 30.59] },
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
  
  // 触发生成对应的二维推演
  generate2DDeduction(city);

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
    activePhysicsTab.value = (city === 'xiantao') ? 'smoke' : 'diffusion'
    selectPhase(selectedPhase.value)
  } else {
    if (city === 'xiantao') {
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(113.43, 30.29, 120000), // 仙桃：高度适中，稍微偏东侧以避开右侧面板
        duration: 2.0
      });
    } else if (city === 'huanggang') {
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(114.90, 30.70, 380000), // 黄冈+武汉：中心微调以同时容纳并看清两市及救援路径
        duration: 2.0
      });
    }
  }
}

const initSimulationViewer = async () => {
  const container = document.getElementById('simulationCesiumContainer')
  if (!container) return

  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.log('[Cesium Simulation] 容器尺寸为 0，延迟 100ms 重新尝试初始化...')
    initSimulationViewerTimeout = setTimeout(initSimulationViewer, 100)
    return
  }

  // 屏蔽 Cesium 默认的红色崩溃弹窗
  if (Cesium) {
    if (typeof Cesium['showHtmlErrorPanel'] === 'function') {
      Cesium['showHtmlErrorPanel'] = function(title, message, error) {
        console.error('[Cesium Widget Error]', title, message, error);
      };
    }
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
      errorMessage.value = '三维地球 WebGL 初始化失败（可能由于浏览器 WebGL 上下文耗尽或未开启显卡硬件加速），请尝试在浏览器设置中开启“使用硬件加速”并刷新页面重试。';
      console.error('三维地球初始化失败:', e2);
      return;
    }
  }
  
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
  if (currentCity.value === 'xiantao') {
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(113.43, 30.29, 120000)
    })
  } else {
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(114.90, 30.70, 380000)
    })
  }
  
  viewer.scene.globe.enableLighting = false
  viewer.scene.light = new Cesium.DirectionalLight({
    direction: viewer.camera.direction
  })
  removeLightListener = viewer.scene.preRender.addEventListener(function(scene, time) {
    scene.light.direction = Cesium.Cartesian3.clone(scene.camera.directionWC, scene.light.direction)
  })
  viewer.cesiumWidget.creditContainer.style.display = 'none'

  if (!viewer) return
  viewer.imageryLayers.removeAll()
  try {
    const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
    )
    if (!viewer) return
    viewer.imageryLayers.addImageryProvider(imagery)
  } catch (e) {
    if (!viewer) return
    console.error('加载 ArcGIS 影像图层失败:', e)
  }

  if (!viewer) return
  // 加载地形
  try {
    const terrainProvider = await Cesium.CesiumTerrainProvider.fromUrl(
      'https://sandcastle.cesium.com/cesium-ion/rest/v1/assets/1/endpoint'
    )
    if (!viewer) return
    viewer.terrainProvider = terrainProvider
    viewer.scene.globe.depthTestAgainstTerrain = true
  } catch (e) {
    if (!viewer) return
    console.error('加载 Cesium 原生基础地形失败:', e)
  }

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
  initSimulationViewer()
})

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
  left: 50%;
  transform: translateX(-50%);
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

/* 返回事故时间线按钮 */
.back-to-timeline-btn {
  position: absolute;
  top: 40px;
  left: 30px;
  z-index: 1010;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  background: rgba(8, 16, 36, 0.88);
  border: 1px solid rgba(0, 255, 180, 0.5);
  border-radius: 8px;
  color: #6ee7b7;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  backdrop-filter: blur(10px);
  box-shadow: 0 0 12px rgba(0, 255, 180, 0.15);
  transition: all 0.25s ease;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.back-to-timeline-btn:hover {
  background: rgba(16, 185, 129, 0.15);
  border-color: #34d399;
  color: #34d399;
  box-shadow: 0 0 18px rgba(0, 255, 180, 0.3);
  transform: translateX(-2px);
}

.back-arrow {
  font-weight: bold;
  font-size: 15px;
  transition: transform 0.2s;
}

.back-to-timeline-btn:hover .back-arrow {
  transform: translateX(-3px);
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

</style>
