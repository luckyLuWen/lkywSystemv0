<template>
  <div class="cesium-wrapper">
    <div id="cesiumContainer" ref="containerRef" class="cesium-container"></div>
    
    <!-- 模型调整控制面板 -->
    <div class="debug-panel" v-if="false">
      <!-- 场景切换按钮 -->
      <div class="scene-switcher">
        <h4>场景选择</h4>
        <div class="switch-buttons">
          <button 
            :class="{ active: currentScene === 'truck' }" 
            @click="currentScene = 'truck'"
          >
            🚛 货车追尾现场
          </button>
          <button 
            :class="{ active: currentScene === 'tanker' }" 
            @click="currentScene = 'tanker'"
          >
            ⛽ 油罐车泄露现场
          </button>
        </div>
      </div>
      
      <hr style="margin: 8px 0; border-color: #333;" />
      
      <!-- 无人机微调控件 -->
      <h4>无人机微调控件</h4>
      <div>
        <label>经度 (X): <input type="number" v-model.number="currentUavAdjust.lng" step="0.00001" /></label>
      </div>
      <div>
        <label>纬度 (Y): <input type="number" v-model.number="currentUavAdjust.lat" step="0.00001" /></label>
      </div>
      <div>
        <label>高度 (Z): <input type="number" v-model.number="currentUavAdjust.height" step="0.5" /></label>
      </div>
      <div>
        <label>模型大小: <input type="number" v-model.number="currentUavAdjust.scale" step="1.0" /></label>
      </div>
      <div>
        <label>旋转角度: <input type="number" v-model.number="currentUavAdjust.heading" step="0.5" /></label>
      </div>
      
      <hr style="margin: 8px 0; border-color: #333;" />
      
      <!-- 事故车辆微调 -->
      <h4>事故车辆微调</h4>
      <div>
        <label>经度 (X): <input type="number" v-model.number="currentTruckAdjust.lng" step="0.00001" /></label>
      </div>
      <div>
        <label>纬度 (Y): <input type="number" v-model.number="currentTruckAdjust.lat" step="0.00001" /></label>
      </div>
      <div>
        <label>高度 (Z): <input type="number" v-model.number="currentTruckAdjust.height" step="0.1" /></label>
      </div>
      <div>
        <label>模型大小: <input type="number" v-model.number="currentTruckAdjust.scale" step="0.01" /></label>
      </div>
      <div>
        <label>旋转角度: <input type="number" v-model.number="currentTruckAdjust.heading" step="1" /></label>
      </div>
      
      <hr style="margin: 8px 0; border-color: #333;" />
      
      <!-- 救援车微调 -->
      <h4>救援车微调</h4>
      <div>
        <label>经度 (X): <input type="number" v-model.number="currentRescueCarAdjust.lng" step="0.00001" /></label>
      </div>
      <div>
        <label>纬度 (Y): <input type="number" v-model.number="currentRescueCarAdjust.lat" step="0.00001" /></label>
      </div>
      <div>
        <label>高度 (Z): <input type="number" v-model.number="currentRescueCarAdjust.height" step="0.5" /></label>
      </div>
      <div>
        <label>模型大小: <input type="number" v-model.number="currentRescueCarAdjust.scale" step="0.1" /></label>
      </div>
      <div>
        <label>旋转角度: <input type="number" v-model.number="currentRescueCarAdjust.heading" step="5" /></label>
      </div>
    </div>

    <div v-if="loading" class="globe-mask">三维地球加载中...</div>
    <div v-else-if="errorMessage" class="globe-mask is-error">{{ errorMessage }}</div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch, reactive, computed } from 'vue'
import * as Cesium from 'cesium'

// 当前选中的场景
const currentScene = ref('truck')

// 计算属性：根据当前场景返回对应的参数对象
const currentUavAdjust = computed(() => {
  return currentScene.value === 'truck' ? uavAdjust : tankerUavAdjust
})

const currentTruckAdjust = computed(() => {
  return currentScene.value === 'truck' ? truckAdjust : tankerAdjust
})

const currentRescueCarAdjust = computed(() => {
  return currentScene.value === 'truck' ? rescueCarAdjust : tankerRescueCarAdjust
})

const props = defineProps({
  phases: { type: Array, default: () => [] },
  activePhaseIndex: { type: Number, default: 0 },
  focusedPointId: { type: String, default: '' },
})

const emit = defineEmits(['accident-picked', 'models-ready'])

// 货车事故分段模型配置 (去重，仅保留唯一物理模型)
const truckModelConfigs = [
  { id: 'model_normal', uri: '/Dashboard/models/Normal_Drive.glb', label: '正常行驶' },
  { id: 'model_accident', uri: '/Dashboard/models/Accident_Occur1.glb', label: '事故阶段' }
]

// 油罐车事故分段模型配置
const tankerModelConfigs = [
  { id: 'tanker_normal', uri: '/Dashboard/models/Normal_Drive_Tanker.glb', label: '正常行驶' },
  { id: 'tanker_accident', uri: '/Dashboard/models/Side_roll_Tanker.glb', label: '事故阶段' }
]

// 阶段索引到模型ID的映射
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

// 油罐车阶段索引到模型ID的映射
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

let currentActiveModelId = null 
let currentActiveTankerModelId = null
let lastPhaseIndex = -1
let lastTankerPhaseIndex = -1

const truckAdjust = reactive({
  scale: 0.82,
  heading: 17,
  lng: 113.104833,
  lat: 30.385469,
  height: -1.2 // 手动微调高度以贴合地面
})

const tankerAdjust = reactive({
  scale: 0.26,
  heading: 36,
  lng: 113.070226,
  lat: 30.238683,
  height: -1.2 // 手动微调高度以贴合地面
})

const tankerPointAdjust = reactive({
  lng: 113.067999,
  lat: 30.2401
})

// 无人机配置
const uavModelConfigs = [
  { id: 'uav_model', uri: '/Dashboard/models/drone_all7.glb', label: '出动无人机' },
  { id: 'uav_model_move', uri: '/Dashboard/models/drone_all7.glb', label: '感知部署无人机' }
]

// 救援车配置
const rescueCarModelConfigs = [
  { id: 'rescue_car_model', uri: '/Dashboard/models/recure%20car.glb', label: '救援车' }
]

// 油罐车场景救援车配置
const tankerRescueCarModelConfigs = [
  { id: 'tanker_rescue_car_model', uri: '/Dashboard/models/recure%20car_2.glb', label: '油罐车救援车' }
]

// 无人机位置调整（在货车追尾现场附近，稍微偏移中心点防止重叠）
const uavAdjust = reactive({
  scale: 6,
  heading: 18,
  lng: 113.1072,
  lat: 30.38493,
  height: 18.5
});

const rescueCarAdjust = reactive({
  scale: 250.7,
  heading: 195,
  lng: 113.1073,
  lat: 30.3849,
  height: -1.5
});

let uavEntities = []
let rescueCarEntities = []
let phase7StartTime = 0
let lastUavPhaseIndex = -1

// 油罐车场景的无人机和救援车配置（独立控制）
const tankerUavAdjust = reactive({
  scale: 6,
  heading: 34,
  lng: 113.06925,
  lat: 30.23928,
  height: 11.5
});

const tankerRescueCarAdjust = reactive({
  scale: 250,
  heading: 215,
  lng: 113.06929,
  lat: 30.2393,
  height: -1.5
});

// 油罐车场景的无人机和救援车实体数组
let tankerUavEntities = []
let tankerRescueCarEntities = []
let tankerPhase7StartTime = 0
let lastTankerUavPhaseIndex = -1

const containerRef = ref(null)
const loading = ref(true)
const errorMessage = ref('')

let viewer = null
let spinCallback = null
let lastSpinAt = 0
// 分离相机航向角
let truckOrbitHeading = Cesium.Math.toRadians(8)
let tankerOrbitHeading = Cesium.Math.toRadians(8)
let focusAreaEntity = null
let popupEntity = null 
let connectionLineEntity = null

// 粒子系统实例
let isFlying = false
let truckEntities = [] 
let tankerEntities = [] 
let animationCheckTimer = null
const modelsReadyStatus = reactive({});
let lastEmitTime = 0;
const primitiveCache = new Map(); // 缓存找到的 primitive，避免重复递归搜索
let readyCheckFrameCounter = 0; // 帧计数器，用于节流

// 递归查找原始模型对象
function findModelPrimitive(collection, entity) {
  if (!collection || typeof collection.get !== 'function') return null
  const len = collection.length
  for (let i = 0; i < len; i++) {
    const p = collection.get(i)
    if (!p) continue
    
    // 匹配逻辑：匹配 entity 对象、ID 字符串或 .id 属性
    const pId = p.id
    // 检查 pId 是否是 Entity 对象，或者 pId 字符串匹配
    const isMatch = (pId === entity) || 
                    (pId && pId.id === entity.id) ||
                    (pId === entity.id) ||
                    (pId && pId._id === entity.id)
                    
    if (isMatch) {
      // 如果是模型或者包含 model 属性的对象
      if (p.ready !== undefined || p.readyPromise !== undefined || p.model) {
        return p
      }
    }
    
    // 如果是集合，递归查找
    if (typeof p.get === 'function' && typeof p.length === 'number') {
      const found = findModelPrimitive(p, entity)
      if (found) return found
    }
  }
  return null
}

function updateModelsReadyStatus() {
  if (!viewer) return;
  
  // 节流：每 20 帧检查一次，不需要每帧都进行昂贵的递归搜索
  readyCheckFrameCounter++;
  if (readyCheckFrameCounter % 20 !== 0) return;

  let changed = false;
  const allEntities = [...truckEntities, ...tankerEntities, ...uavEntities, ...tankerUavEntities];
  
  allEntities.forEach(entity => {
    if (modelsReadyStatus[entity.id]) return;
    
    // 先从缓存找
    let p = primitiveCache.get(entity.id);
    
    if (!p) {
      // 缓存没中，再进行搜索
      p = findModelPrimitive(viewer.scene.primitives, entity);
      if (!p) {
        p = findModelPrimitive(viewer.scene.groundPrimitives, entity);
      }
      if (p) {
        primitiveCache.set(entity.id, p);
        console.log(`[Cesium] 已找到并缓存实体 primitive: ${entity.id}`);
      }
    }

    if (p) {
      // 兼容多种就绪状态判断
      const isReady = p.ready || 
                      (p.readyPromise && p.readyPromise.state === 'fulfilled') || 
                      p._ready ||
                      (p.model && p.model.ready);
      
      if (isReady) {
        modelsReadyStatus[entity.id] = true;
        changed = true;
        console.log(`[Cesium] 检测到模型就绪: ${entity.id}`);
      }
    }
  });

  const now = Date.now();
  // 如果有变化，或者距离上次发送超过 1 秒，就发送一次全量状态
  if (changed || (now - lastEmitTime > 1000)) {
    const statusCopy = {};
    for (const key in modelsReadyStatus) {
      statusCopy[key] = modelsReadyStatus[key];
    }
    emit('models-ready', statusCopy);
    lastEmitTime = now;
  }
}

// 粒子系统实例
let smokeParticle = null
let fireParticle = null
let leakParticle = null
let diffusionParticle = null

const scenarioPoints = {
  command: { id: 'command', label: '远程指挥中心', longitude: 114.3055, latitude: 30.5928, color: '#67b8ff' },
  gateway: { id: 'gateway', label: '边缘传感网关', longitude: 114.3524, latitude: 30.5442, color: '#00e5ff' },
  detection: { id: 'detection', label: '检测现场', longitude: 114.389, latitude: 30.5282, color: '#ffb84d' },
  response: { id: 'response', label: '协同处置区域', longitude: 114.3348, latitude: 30.5638, color: '#8cf7c5' },
  accident_blue: { id: 'accident_blue', label: '货车追尾现场', longitude: 113.104833, latitude: 30.385469, color: '#ffea00' }, // 改为黄色
  accident_red: { id: 'accident_red', label: '油罐车泄露现场', longitude: 113.067999, latitude: 30.2401, color: '#00e5ff' },  // 改为蓝色
}

function toCesiumColor(color, alpha = 1) {
  return Cesium.Color.fromCssColorString(color).withAlpha(alpha)
}

function applyOrbitView() {
  if (!viewer || isFlying) return
  const pointId = props.focusedPointId
  const isFocused = !!pointId && scenarioPoints[pointId]

  let lng, lat;
  if (isFocused) {
    if (pointId === 'accident_blue') {
      lng = truckAdjust.lng; lat = truckAdjust.lat;
    } else if (pointId === 'accident_red') {
      lng = tankerPointAdjust.lng; lat = tankerPointAdjust.lat;
    } else {
      lng = scenarioPoints[pointId].longitude;
      lat = scenarioPoints[pointId].latitude;
    }
  } else {
    lng = 108; lat = 31;
  }

  try {
    const target = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
    
    // 默认视角参数 - 使用无人装备出动阶段的视角作为默认视角
    let range = isFocused ? (props.focusedPointId === 'accident_red' ? 480 : 480) : 18000000
    let pitch = isFocused ? (props.focusedPointId === 'accident_red' ? Cesium.Math.toRadians(-32) : Cesium.Math.toRadians(-38)) : Cesium.Math.toRadians(-34)

    if (isFocused) {
      if (props.activePhaseIndex <= 1) {
        // 仿真开始及正常行驶阶段：全景拉远
        range = 1200
        pitch = Cesium.Math.toRadians(-45);
      } else if (props.activePhaseIndex === 2) {
        // 事故发生瞬间：货车保持特写，油罐车保持全景
        if (props.focusedPointId === 'accident_red') {
          range = 1200
          pitch = Cesium.Math.toRadians(-45);
        } else {
          range = 80
          pitch = Cesium.Math.toRadians(-22)
        }
      } else if (props.activePhaseIndex === 3 || props.activePhaseIndex === 4) {
        range = props.focusedPointId === 'accident_red' ? 100 : 220;
        pitch = props.focusedPointId === 'accident_red' 
          ? Cesium.Math.toRadians(-25) 
          : Cesium.Math.toRadians(-65);
      } else if (props.activePhaseIndex === 5) {
        // 大火与弥漫扩散阶段：油罐车中近距离视角，确保能看清大面积扩散细节
        if (props.focusedPointId === 'accident_red') {
          range = 300
          pitch = Cesium.Math.toRadians(-30)
        } else {
          range = 220
          pitch = Cesium.Math.toRadians(-65)
        }
      } else if (props.activePhaseIndex >= 6) {
        if (props.focusedPointId === 'accident_red') {
          range = 450
          pitch = Cesium.Math.toRadians(-25)
        }
      }
    }

    // 航向角处理：针对事故阶段切换到另一侧视角
    let finalHeading = (props.focusedPointId === 'accident_red') ? tankerOrbitHeading : truckOrbitHeading
    
    // 航向角处理：只有货车在事故后旋转视角
    // 油罐车始终保持初始航向角，不进行自动旋转
    const shouldRotate = (props.focusedPointId === 'accident_red') ? false : (props.activePhaseIndex >= 2)
    
    if (isFocused && shouldRotate) {
      finalHeading += Cesium.Math.toRadians(165)
    }

    viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(finalHeading, pitch, range))
  } catch (error) {
    console.warn('应用轨道视角时出现警告:', error.message)
  }
}

onBeforeUnmount(() => {
  if (animationCheckTimer) clearInterval(animationCheckTimer)
})

function startAutoRotate() {
  if (!viewer || spinCallback) return
  lastSpinAt = performance.now()
  spinCallback = () => {
    if (!viewer) return
    const now = performance.now()
    const deltaSeconds = (now - lastSpinAt) / 1000
    lastSpinAt = now
    
    // 分离旋转逻辑
    if (props.focusedPointId === 'accident_red') {
      // 油罐车现场：不再进行持续自动旋转，保持视角完全静止
      // tankerOrbitHeading 保持不变
    } else {
      // 货车现场：保持原有的持续旋转效果
      truckOrbitHeading -= 0.06 * deltaSeconds
    }
    
    applyOrbitView()
  }
  viewer.clock.onTick.addEventListener(spinCallback)
}

function stopAutoRotate() {
  if (viewer && spinCallback) viewer.clock.onTick.removeEventListener(spinCallback)
  spinCallback = null
  if (viewer) {
    try {
      viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
    } catch (error) {
      console.warn('停止自动旋转时出现警告:', error.message)
    }
  }
}

// 创建更加逼真的烟雾系统
function createSmokeSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/smoke.png',
    startColor: new Cesium.Color(0.2, 0.2, 0.2, 0.6), // 初始深灰
    endColor: new Cesium.Color(0.9, 0.9, 0.9, 0.0),   // 最终淡白透明
    startScale: 1.0,
    endScale: 6.0, 
    minimumParticleLife: 2.0,
    maximumParticleLife: 4.5,
    minimumSpeed: 2.0,
    maximumSpeed: 5.0,
    imageSize: new Cesium.Cartesian2(25, 25), // 增大尺寸
    emissionRate: 60.0, // 增加密度
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(3.0), // 使用球形发射器增加体积感
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 模拟浮力：烟雾受热向上飘
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 2.5 * dt, gravityScratch); // 向上力
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
    }
  });
}

// 创建更加逼真的火焰/爆炸系统
function createFireSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/explosion00.png',
    startColor: new Cesium.Color(1.0, 0.9, 0.5, 0.8), // 爆炸瞬间的亮黄白
    endColor: new Cesium.Color(1.0, 0.3, 0.0, 0.0),   // 消失时的深橘红
    startScale: 1.5,
    endScale: 4.5, // 爆炸云团膨胀
    minimumParticleLife: 1.0,
    maximumParticleLife: 2.5,
    minimumSpeed: 3.0,
    maximumSpeed: 7.0,
    imageSize: new Cesium.Cartesian2(25, 25), // 增大尺寸以匹配爆炸图
    emissionRate: 65.0, 
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(2.0),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 快速向四周和上方窜升
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 5.0 * dt, gravityScratch); 
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
    }
  });
}

// 创建更加逼真的油罐车泄露效果 (使用 whitePuff00.png) - 优化尺寸版
function createLeakSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/whitePuff00.png',
    startColor: new Cesium.Color(0.7, 0.85, 1.0, 0.1), // 极低不透明度
    endColor: new Cesium.Color(0.9, 0.95, 1.0, 0.0),
    startScale: 1.0,
    endScale: 3.0, // 显著减小膨胀比例
    minimumParticleLife: 2.0,
    maximumParticleLife: 4.0,
    minimumSpeed: 0.3,
    maximumSpeed: 0.8,
    imageSize: new Cesium.Cartesian2(4, 4), // 显著减小原始尺寸（从15降到4）
    emissionRate: 35.0, // 略微降低频率
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(1.0), // 缩小发射半径
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 模拟气云缓慢散开
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 0.1 * dt, gravityScratch); 
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
    }
  });
}

// 创建弥漫效果系统 (使用 fart00.png) - 优化版，防止效果过大
function createDiffusionSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/fart00.png',
    // 使用更淡的颜色和更低的透明度
    startColor: new Cesium.Color(0.8, 0.9, 1.0, 0.15), 
    endColor: new Cesium.Color(0.9, 0.95, 1.0, 0.0),
    startScale: 1.0,
    endScale: 5.0, // 显著缩小膨胀比例
    minimumParticleLife: 5.0,
    maximumParticleLife: 10.0,
    minimumSpeed: 0.1,
    maximumSpeed: 0.5,
    imageSize: new Cesium.Cartesian2(12, 12), // 略微回调尺寸（从8调到12）
    emissionRate: 20.0, 
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(4.0), // 稍微增大发射半径
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 模拟缓慢的空气漂浮
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 0.05 * dt, gravityScratch); 
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
    }
  });
}

async function initViewer() {
  if (!containerRef.value || viewer) return
  try {
    viewer = new Cesium.Viewer(containerRef.value, {
      animation: false, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
      infoBox: false, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
      timeline: false, shouldAnimate: true, skyAtmosphere: false,
    })
    viewer.scene.globe.enableLighting = true
    viewer.cesiumWidget.creditContainer.style.display = 'none'

    viewer.imageryLayers.removeAll()
    const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
    )
    viewer.imageryLayers.addImageryProvider(imagery)

    try {
      addEventEntities()
    } catch (e) {
      console.warn('添加事件实体时出现警告:', e.message)
    }

    try {
      smokeParticle = viewer.scene.primitives.add(createSmokeSystem(truckAdjust.lng, truckAdjust.lat))
      fireParticle = viewer.scene.primitives.add(createFireSystem(truckAdjust.lng, truckAdjust.lat))
      leakParticle = viewer.scene.primitives.add(createLeakSystem(tankerPointAdjust.lng, tankerPointAdjust.lat))
      diffusionParticle = viewer.scene.primitives.add(createDiffusionSystem(tankerPointAdjust.lng, tankerPointAdjust.lat))
    } catch (e) {
      console.warn('初始化粒子系统时出现警告:', e.message)
    }

    try {
      applyOrbitView()
    } catch (e) {
      console.warn('应用初始视角时出现警告:', e.message)
    }

    try {
      updatePhaseScene(props.activePhaseIndex)
    } catch (e) {
      console.warn('更新初始场景时出现警告:', e.message)
    }

    viewer.scene.postRender.addEventListener(updateModelsReadyStatus)

    loading.value = false
  } catch (error) {
    errorMessage.value = '三维地球初始化失败'
    loading.value = false
    console.error('三维地球初始化失败:', error)
  }
}

function updateTruckSequence(phaseIndex) {
  if (!viewer) return
  
  const targetModelId = phaseToModelMap[phaseIndex] || null
  
  // 1. 物理显隐状态：通过控制 alpha 或 scale 来实现，而不是 entity.show，因为我们要预加载
  // 这里我们已经通过 CallbackProperty 控制了 scale

  // 2. 动画触发逻辑：
  // - 如果物理模型发生变化（如从正常行驶切到事故模型），必须触发播放
  // - 如果物理模型没变（如从事故发生切到次生灾害），则保持当前帧（不重播），满足用户“在最后一帧静止”的需求
  const isModelChanged = targetModelId !== currentActiveModelId
  const isInitialSwitch = (phaseIndex <= 1 && lastPhaseIndex <= 1 && phaseIndex !== lastPhaseIndex)
  
  if (targetModelId) {
    truckEntities.forEach(entity => {
      const isTarget = entity.id === targetModelId
      if (isTarget) {
        entity.show = true
      } else {
        entity.show = !modelsReadyStatus[entity.id]
      }
    })
    
    // 无人机阶段（阶段6、7、8）不播放动画，保持事故发生后的最后一帧
    if (phaseIndex < 6 && (isModelChanged || isInitialSwitch)) {
      const entity = truckEntities.find(e => e.id === targetModelId)
      if (entity) {
        playEntityAnimation(entity, false)
      }
    }
  }
  
  currentActiveModelId = targetModelId
  lastPhaseIndex = phaseIndex

  const isTruckFocus = props.focusedPointId === 'accident_blue';

  const isBigFire = (phaseIndex === 5);
  const smokeScaleBase = isBigFire ? 2.8 : 1.0;
  const fireScaleBase = isBigFire ? 2.0 : 1.0;

  if (smokeParticle) {
    // 只有在聚焦该点且阶段 >= 3 时才显示，防止回退时粒子残留
    smokeParticle.show = isTruckFocus && (phaseIndex >= 3);
    smokeParticle.startScale = 0.5 * smokeScaleBase;
    smokeParticle.endScale = 2.0 * smokeScaleBase;
    smokeParticle.emissionRate = (phaseIndex >= 3) ? 60.0 : 0.0;
  }
  if (fireParticle) {
    // 只有在聚焦该点且阶段 >= 4 时才显示
    fireParticle.show = isTruckFocus && (phaseIndex >= 4);
    fireParticle.startScale = 0.3 * fireScaleBase;
    fireParticle.endScale = 1.2 * fireScaleBase;
    fireParticle.emissionRate = (phaseIndex >= 4) ? 80.0 : 0.0;
  }
}

// 油罐车模型序列更新函数
function updateTankerSequence(phaseIndex) {
  if (!viewer) return
  
  const targetModelId = tankerPhaseToModelMap[phaseIndex] || null

  const isModelChanged = targetModelId !== currentActiveTankerModelId
  const isInitialSwitch = (phaseIndex <= 1 && lastPhaseIndex <= 1 && phaseIndex !== lastPhaseIndex)

  if (targetModelId && (isModelChanged || isInitialSwitch)) {
    tankerEntities.forEach(entity => {
      const isTarget = entity.id === targetModelId
      if (isTarget) {
        entity.show = true
      } else {
        entity.show = !modelsReadyStatus[entity.id]
      }
    })
    const entity = tankerEntities.find(e => e.id === targetModelId)
    if (entity) {
      playEntityAnimation(entity, false)
    }
  }
  
  currentActiveTankerModelId = targetModelId
  lastTankerPhaseIndex = phaseIndex

  // 全时段就绪：泄露与弥漫效果根据focusedPointId决定是否显示
  const isTankerFocus = props.focusedPointId === 'accident_red';

  if (leakParticle) {
    // 只有在聚焦该点且阶段 >= 3 时才显示
    leakParticle.show = isTankerFocus && (phaseIndex >= 3);
    // 阶段3（泄露）开始产生
    leakParticle.emissionRate = (phaseIndex >= 3) ? 45.0 : 0.0; 
  }
  
  if (diffusionParticle) {
    // 只有在聚焦该点且阶段 >= 4 时才显示
    diffusionParticle.show = isTankerFocus && (phaseIndex >= 4);
    // 阶段4（弥漫）开始产生，阶段5（扩散）显著增强
    if (phaseIndex === 4) {
      diffusionParticle.emissionRate = 30.0;
    } else if (phaseIndex >= 5) {
      diffusionParticle.emissionRate = 80.0; // 显著增强
    } else {
      diffusionParticle.emissionRate = 0.0;
    }
  }
}

function playEntityAnimation(entity, loop = false, duration = 0, speedMultiplier = 1.0) {
  if (!viewer || !entity) return;

  const tryPlay = (attemptsLeft) => {
    if (attemptsLeft <= 0) {
      console.warn(`[Cesium] 播放动画超时，模型未能及时就绪: ${entity.id}`);
      return;
    }

    try {
      let p = primitiveCache.get(entity.id);
      if (!p) p = findModelPrimitive(viewer.scene.primitives, entity);
      if (!p) p = findModelPrimitive(viewer.scene.groundPrimitives, entity);

      // 检查模型是否完全加载就绪
      const isReady = p && (
        p.ready || 
        (p.readyPromise && p.readyPromise.state === 'fulfilled') || 
        p._ready || 
        (p.model && p.model.ready)
      );

      if (p && isReady && p.activeAnimations && typeof p.activeAnimations.addAll === 'function') {
        console.log(`[Cesium] 成功找到模型且已就绪，开始强制播放全轨道动画: ${entity.id}`);
        try {
          p.activeAnimations.removeAll();
          const options = {
            loop: loop ? Cesium.ModelAnimationLoop.REPEAT : Cesium.ModelAnimationLoop.NONE,
            multiplier: speedMultiplier, // 使用动态控制的播放倍速
            startTime: viewer.clock.currentTime,
            removeOnStop: false // 停止时保留在最后一帧状态
          };
          
          if (duration > 0) {
            options.stopTime = Cesium.JulianDate.addSeconds(viewer.clock.currentTime, duration, new Cesium.JulianDate());
          }
          
          // 核心：调用 addAll 强制激活模型内所有的 animation tracks
          p.activeAnimations.addAll(options);
          console.log(`[Cesium] 动画播放指令已成功下发: duration = ${duration}s, 播放倍速 = ${speedMultiplier}`);
        } catch (animError) {
          console.warn('播放动画时出现警告:', animError.message);
        }
      } else {
        // 如果未找到或未就绪，等待 200ms 后重试
        setTimeout(() => tryPlay(attemptsLeft - 1), 200);
      }
    } catch (error) {
      console.warn('查找实体时出现警告:', error.message);
    }
  };

  // 启动轮询检查，最多重试 50 次 (约 10 秒)
  tryPlay(50);
}

function replayCurrentPhase() {
  if (currentActiveModelId) {
    const entity = truckEntities.find(e => e.id === currentActiveModelId)
    if (entity) playEntityAnimation(entity)
  }
}

function addEventEntities() {
  let sharedTankerRescueCarPosition = null;
  focusAreaEntity = viewer.entities.add({
    id: 'event-area',
    position: Cesium.Cartesian3.fromDegrees(114.35, 30.55, 0),
    ellipse: {
      semiMinorAxis: 150000, semiMajorAxis: 190000, material: toCesiumColor('#00e5ff', 0.06),
      outline: true, outlineColor: toCesiumColor('#00e5ff', 0.32), height: 0,
    },
  })

  popupEntity = viewer.entities.add({
    id: 'event-popup',
    position: Cesium.Cartesian3.fromDegrees(114.35, 30.55, 500),
    label: {
      text: '', font: 'bold 15px Microsoft YaHei', fillColor: Cesium.Color.WHITE, showBackground: true,
      backgroundColor: toCesiumColor('#061628', 0.88), backgroundPadding: new Cesium.Cartesian2(16, 12),
      pixelOffset: new Cesium.Cartesian2(0, -60), disableDepthTestDistance: Number.POSITIVE_INFINITY,
      horizontalOrigin: Cesium.HorizontalOrigin.CENTER, verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      style: Cesium.LabelStyle.FILL, scale: 0.96,
    },
  })

  connectionLineEntity = viewer.entities.add({
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        if (!connectionLineEntity || !connectionLineEntity.show) return []
        const pos = popupEntity.position.getValue(viewer.clock.currentTime)
        if (!pos) return []
        const carto = Cesium.Cartographic.fromCartesian(pos)
        const groundPos = Cesium.Cartesian3.fromDegrees(
          Cesium.Math.toDegrees(carto.longitude),
          Cesium.Math.toDegrees(carto.latitude),
          0
        )
        return [groundPos, pos]
      }, false),
      width: 3,
      material: Cesium.Color.CYAN.withAlpha(0.7),
      show: false
    }
  })

  Object.values(scenarioPoints).filter(p => p.id.startsWith('accident_')).forEach(point => {
    viewer.entities.add({
      id: `marker-${point.id}`,
      position: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, 0),
      point: {
        pixelSize: 10,
        color: Cesium.Color.fromCssColorString(point.color),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
  })

  truckModelConfigs.forEach((config) => {
    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false,
      position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(Number(truckAdjust.lng)||0, Number(truckAdjust.lat)||0, Number(truckAdjust.height)||0), false),
      orientation: new Cesium.CallbackProperty(() => {
        const position = Cesium.Cartesian3.fromDegrees(Number(truckAdjust.lng)||0, Number(truckAdjust.lat)||0, Number(truckAdjust.height)||0);
        const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(truckAdjust.heading)||0), 0, 0);
        return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
      }, false),
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => {
          const targetModelId = phaseToModelMap[props.activePhaseIndex]
          // 始终保持一个微小但存在的比例，配合 minimumPixelSize 强制加载
          if (config.id === targetModelId) return truckAdjust.scale
          return 0.001
        }, false),
        minimumPixelSize: 1, // 关键：强制 Cesium 始终渲染该模型，从而触发加载
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, // 使用 Cesium 原生贴地
        // 关闭原生动画循环，交由 updateTruckSequence 和 playEntityAnimation 手动控制只播一次并定格
        runAnimations: false
      }
    })
    entity.show = true // 强制开启显示以触发加载
    truckEntities.push(entity)
  })

  tankerModelConfigs.forEach((config) => {
    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false,
      position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(Number(tankerAdjust.lng)||0, Number(tankerAdjust.lat)||0, Number(tankerAdjust.height)||0), false),
      orientation: new Cesium.CallbackProperty(() => {
        const position = Cesium.Cartesian3.fromDegrees(Number(tankerAdjust.lng)||0, Number(tankerAdjust.lat)||0, Number(tankerAdjust.height)||0);
        const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(tankerAdjust.heading)||0), 0, 0);
        return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
      }, false),
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => {
          const targetModelId = tankerPhaseToModelMap[props.activePhaseIndex]
          if (config.id === targetModelId) return tankerAdjust.scale
          return 0.001
        }, false),
        minimumPixelSize: 1, // 关键：强制加载
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, // 使用 Cesium 原生贴地
        // 关闭原生动画循环，手动控制
        runAnimations: false
      }
    })
    entity.show = true
    tankerEntities.push(entity)
  })

  // 初始化无人机模型（用于货车追尾现场的无人装备出动阶段）
  uavModelConfigs.forEach((config) => {
    console.log(`[Cesium] 正在初始化无人机实体: ${config.id}, 路径: ${config.uri}`);

    const uavPosition = new Cesium.CallbackProperty(() => {
      const startLng = Number(uavAdjust.lng) || 113.1072;
      const startLat = Number(uavAdjust.lat) || 30.38493;
      const startHeight = Number(uavAdjust.height) || 18.5;

      // 终点位置设在货车事故点 (113.104833, 30.385469) 正上方悬停，高度保持一致
      const targetLng = Number(truckAdjust.lng) || 113.104833;
      const targetLat = Number(truckAdjust.lat) || 30.385469;
      const targetHeight = startHeight; // 保持在原先的高度高空悬停

      if (props.activePhaseIndex < 7) {
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else if (props.activePhaseIndex === 7) {
        if (!phase7StartTime) {
          phase7StartTime = Date.now();
        }
        const elapsed = Date.now() - phase7StartTime;
        const duration = 6000; // 6秒内平滑飞过
        const t = Math.min(elapsed / duration, 1.0);
        // 使用 EaseInOutQuad 缓动函数
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        const lng = startLng + (targetLng - startLng) * easeT;
        const lat = startLat + (targetLat - startLat) * easeT;
        const height = startHeight + (targetHeight - startHeight) * easeT;
        return Cesium.Cartesian3.fromDegrees(lng, lat, height);
      } else {
        // 阶段 >= 8 停留在事故点上方
        return Cesium.Cartesian3.fromDegrees(targetLng, targetLat, targetHeight);
      }
    }, false);

    const uavOrientation = new Cesium.CallbackProperty(() => {
      const pos = uavPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;
      const headingDeg = Number(uavAdjust.heading) || 18;
      const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(headingDeg), 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(pos, hpr);
    }, false);

    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false, // 初始隐藏
      position: uavPosition,
      orientation: uavOrientation,
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => uavAdjust.scale > 0 ? uavAdjust.scale : 0.1, false),
        minimumPixelSize: 64, 
        heightReference: Cesium.HeightReference.NONE,
        // 关闭 Entity 自带的动画调度，避免与手动 addAll 产生冲突
        runAnimations: false
      }
    });
    uavEntities.push(entity);
  });

  // 初始化救援车
  rescueCarModelConfigs.forEach((config) => {
    console.log(`[Cesium] 正在初始化救援车实体: ${config.id}, 路径: ${config.uri}`);

    const rescueCarPosition = new Cesium.CallbackProperty(() => {
      const startLng = Number(rescueCarAdjust.lng) || 113.1073;
      const startLat = Number(rescueCarAdjust.lat) || 30.3849;
      const startHeight = Number(rescueCarAdjust.height) || -1.5;

      const accidentLng = Number(truckAdjust.lng) || 113.104833;
      const accidentLat = Number(truckAdjust.lat) || 30.385469;

      // 投影计算：沿着起火点和初始坐标所在的这条马路车道直线前进，保证绝对不换道或发生偏航，在距离车祸点约60米的前方停车 (f = 0.78)
      const targetLng = startLng + 0.78 * (accidentLng - startLng);
      const targetLat = startLat + 0.78 * (accidentLat - startLat);
      const targetHeight = -1.5; // 保持与起点的 Z 轴高度一致，防止陷车

      if (props.activePhaseIndex < 7) {
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else if (props.activePhaseIndex === 7) {
        if (!phase7StartTime) {
          phase7StartTime = Date.now();
        }
        const elapsed = Date.now() - phase7StartTime;
        const duration = 6000; // 6秒内平滑开到事故现场
        const t = Math.min(elapsed / duration, 1.0);
        // 使用 EaseInOutQuad 缓动函数，让启动和停止更自然
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        
        const lng = startLng + (targetLng - startLng) * easeT;
        const lat = startLat + (targetLat - startLat) * easeT;
        const height = startHeight + (targetHeight - startHeight) * easeT;
        return Cesium.Cartesian3.fromDegrees(lng, lat, height);
      } else {
        // 阶段 >= 8：停留在现场终点
        return Cesium.Cartesian3.fromDegrees(targetLng, targetLat, targetHeight);
      }
    }, false);

    const rescueCarOrientation = new Cesium.CallbackProperty(() => {
      const pos = rescueCarPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;
      const headingDeg = Number(rescueCarAdjust.heading) || 195;
      const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(headingDeg), 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(pos, hpr);
    }, false);

    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false,
      position: rescueCarPosition,
      orientation: rescueCarOrientation,
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => Number(rescueCarAdjust.scale) || 1.0, false),
        minimumPixelSize: 16, // 保底 16 像素，防止模型物理尺寸过小导致完全不可见，但不至于像 64 那样完全覆盖微调效果
        heightReference: Cesium.HeightReference.NONE, // 移除自动贴地，完全由用户通过 Z 轴微调高度，防止模型原点错误导致深埋地下
        runAnimations: true
      }
    });
    rescueCarEntities.push(entity);
  });

  // 初始化油罐车场景的无人机模型
  uavModelConfigs.forEach((config) => {
    console.log(`[Cesium] 正在初始化油罐车场景无人机实体: ${config.id}, 路径: ${config.uri}`);

    const tankerUavPosition = new Cesium.CallbackProperty(() => {
      const startHeight = Number(tankerUavAdjust.height) || 11.5;
      if (sharedTankerRescueCarPosition) {
        const carPos = sharedTankerRescueCarPosition.getValue(viewer.clock.currentTime);
        if (carPos) {
          const cartographic = Cesium.Cartographic.fromCartesian(carPos);
          const lng = Cesium.Math.toDegrees(cartographic.longitude);
          const lat = Cesium.Math.toDegrees(cartographic.latitude);
          return Cesium.Cartesian3.fromDegrees(lng, lat, startHeight);
        }
      }
      
      const startLng = Number(tankerRescueCarAdjust.lng) || 113.06929;
      const startLat = Number(tankerRescueCarAdjust.lat) || 30.2393;
      return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
    }, false);

    const tankerUavOrientation = new Cesium.CallbackProperty(() => {
      const pos = tankerUavPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;
      const headingDeg = Number(tankerUavAdjust.heading) || 18;
      const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(headingDeg), 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(pos, hpr);
    }, false);

    const entity = viewer.entities.add({
      id: config.id + '_tanker',
      name: config.label + ' (油罐车)',
      show: false,
      position: tankerUavPosition,
      orientation: tankerUavOrientation,
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => tankerUavAdjust.scale > 0 ? tankerUavAdjust.scale : 0.1, false),
        minimumPixelSize: 64,
        heightReference: Cesium.HeightReference.NONE,
        runAnimations: false
      }
    });
    tankerUavEntities.push(entity);
  });

  // 初始化油罐车场景的救援车
  tankerRescueCarModelConfigs.forEach((config) => {
    console.log(`[Cesium] 正在初始化油罐车场景救援车实体: ${config.id}, 路径: ${config.uri}`);

    const tankerRescueCarPosition = new Cesium.CallbackProperty(() => {
      const startLng = Number(tankerRescueCarAdjust.lng) || 113.06929;
      const startLat = Number(tankerRescueCarAdjust.lat) || 30.2393;
      const startHeight = Number(tankerRescueCarAdjust.height) || -1.5;

      const targetLng = Number(tankerPointAdjust.lng) || 113.067999;
      const targetLat = Number(tankerPointAdjust.lat) || 30.2401;
      const targetHeight = startHeight;

      if (props.activePhaseIndex < 7) {
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else if (props.activePhaseIndex === 7) {
        if (!tankerPhase7StartTime) {
          tankerPhase7StartTime = Date.now();
        }
        const elapsed = Date.now() - tankerPhase7StartTime;
        const duration = 6000;
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        const stopFactor = 0.55;
        const actualTargetLng = startLng + stopFactor * (targetLng - startLng);
        const actualTargetLat = startLat + stopFactor * (targetLat - startLat);

        const lng = startLng + (actualTargetLng - startLng) * easeT;
        const lat = startLat + (actualTargetLat - startLat) * easeT;
        const height = startHeight + (targetHeight - startHeight) * easeT;
        return Cesium.Cartesian3.fromDegrees(lng, lat, height);
      } else {
        const stopFactor = 0.55;
        const actualTargetLng = startLng + stopFactor * (targetLng - startLng);
        const actualTargetLat = startLat + stopFactor * (targetLat - startLat);
        return Cesium.Cartesian3.fromDegrees(actualTargetLng, actualTargetLat, startHeight);
      }
    }, false);

    const tankerRescueCarOrientation = new Cesium.CallbackProperty(() => {
      const pos = tankerRescueCarPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;
      const headingDeg = Number(tankerRescueCarAdjust.heading) || 215;
      const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(headingDeg), 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(pos, hpr);
    }, false);

    sharedTankerRescueCarPosition = tankerRescueCarPosition;

    const entity = viewer.entities.add({
      id: config.id,
      name: config.label + ' (油罐车)',
      show: false,
      position: tankerRescueCarPosition,
      orientation: tankerRescueCarOrientation,
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => Number(tankerRescueCarAdjust.scale) || 1.0, false),
        minimumPixelSize: 16,
        heightReference: Cesium.HeightReference.NONE,
        runAnimations: true
      }
    });
    tankerRescueCarEntities.push(entity);
  });

  viewer.screenSpaceEventHandler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.position);
    if (Cesium.defined(pickedObject) && pickedObject.id) {
      const entityId = pickedObject.id.id;
      // 检查点击的是否是货车模型或油罐车
      if (entityId.includes('model_') || entityId.includes('tanker_') || entityId === 'accident_red' || entityId === 'accident_blue') {
        const emitId = (entityId.includes('model_') || entityId === 'accident_blue') ? 'accident_blue' : 'accident_red'
        emit('accident-picked', emitId);
        zoomToPoint(emitId);
      }
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}

function updatePhaseScene(index) {
  if (!viewer || !props.phases.length || !focusAreaEntity) return

  try {
    const phase = props.phases[index] || props.phases[0]
    const pointId = props.focusedPointId || phase.focusPoint || 'gateway'
    const point = scenarioPoints[pointId] || scenarioPoints.gateway

    let lng = point.longitude, lat = point.latitude;
    if (pointId === 'accident_blue') {
      lng = truckAdjust.lng; lat = truckAdjust.lat;
    } else if (pointId === 'accident_red') {
      lng = tankerPointAdjust.lng; lat = tankerPointAdjust.lat;
    }

    // 无论在哪个场景，都让所有模型保持 show: true 状态以触发预加载
    // 但通过 scale 来控制真正可见的模型
    if (pointId === 'accident_blue') {
      updateTruckSequence(index)
      if (leakParticle) leakParticle.show = false
    } else if (pointId === 'accident_red') {
      updateTankerSequence(index)
      if (smokeParticle) smokeParticle.show = false
      if (fireParticle) fireParticle.show = false
    } else {
      if (smokeParticle) smokeParticle.show = false
      if (fireParticle) fireParticle.show = false
      if (leakParticle) leakParticle.show = false
    }

    focusAreaEntity.position = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
    if (popupEntity) {
      // 隐藏悬浮窗和连接线（根据用户要求取消显示）
      popupEntity.show = false
      if (connectionLineEntity) connectionLineEntity.show = false

      if (index >= 6) {
        // 在货车追尾现场的无人机阶段显示无人机模型和救援车并隐藏所有粒子效果
        if (pointId === 'accident_blue') {
          uavEntities.forEach(entity => {
            const isTarget = (index === 6 && entity.id === 'uav_model') || (index >= 7 && entity.id === 'uav_model_move');
            if (isTarget) {
              const needsAnimation = !entity.show || (entity.id === 'uav_model_move' && index === 7 && lastUavPhaseIndex !== 7);
              entity.show = true;
              if (needsAnimation) {
                // 两个阶段的无人机螺旋桨都需要持续高速旋转
                playEntityAnimation(entity, true, 0, 6.0);
              }
            } else {
              entity.show = false;
            }
          });
          rescueCarEntities.forEach(entity => { entity.show = true });
          
          // 隐藏油罐车场景的无人机和救援车
          tankerUavEntities.forEach(entity => { entity.show = false })
          tankerRescueCarEntities.forEach(entity => { entity.show = false })
          
          // 隐藏所有粒子效果，只保留模型
          if (smokeParticle) smokeParticle.show = false
          if (fireParticle) fireParticle.show = false
          if (leakParticle) leakParticle.show = false
          if (diffusionParticle) diffusionParticle.show = false
        } else if (pointId === 'accident_red') {
          // 在油罐车泄露现场的无人机阶段显示无人机模型和救援车并隐藏所有粒子效果
          tankerUavEntities.forEach(entity => {
            const isTarget = (index === 6 && entity.id === 'uav_model_tanker') || (index >= 7 && entity.id === 'uav_model_move_tanker');
            if (isTarget) {
              const needsAnimation = !entity.show || (entity.id === 'uav_model_move_tanker' && index === 7 && lastTankerUavPhaseIndex !== 7);
              entity.show = true;
              if (needsAnimation) {
                // 两个阶段的无人机螺旋桨都需要持续高速旋转
                playEntityAnimation(entity, true, 0, 6.0);
              }
            } else {
              entity.show = false;
            }
          });
          tankerRescueCarEntities.forEach(entity => { entity.show = true });
          
          // 隐藏货车场景的无人机和救援车
          uavEntities.forEach(entity => { entity.show = false })
          rescueCarEntities.forEach(entity => { entity.show = false })
          
          // 隐藏所有粒子效果，只保留模型
          if (smokeParticle) smokeParticle.show = false
          if (fireParticle) fireParticle.show = false
          if (leakParticle) leakParticle.show = false
          if (diffusionParticle) diffusionParticle.show = false
        } else {
          // 如果视角切换到其他地方，隐藏所有无人机和救援车
          uavEntities.forEach(entity => { entity.show = false })
          rescueCarEntities.forEach(entity => { entity.show = false })
          tankerUavEntities.forEach(entity => { entity.show = false })
          tankerRescueCarEntities.forEach(entity => { entity.show = false })
        }
      } else {
        // 前置阶段隐藏悬浮窗和连接线
        popupEntity.show = false
        if (connectionLineEntity) connectionLineEntity.show = false
        // 隐藏所有无人机模型和救援车
        uavEntities.forEach(entity => { entity.show = false })
        rescueCarEntities.forEach(entity => { entity.show = false })
        tankerUavEntities.forEach(entity => { entity.show = false })
        tankerRescueCarEntities.forEach(entity => { entity.show = false })
      }
    }

    lastUavPhaseIndex = index;
    lastTankerUavPhaseIndex = index;

    if (!spinCallback && props.focusedPointId && !isFlying) applyOrbitView()
  } catch (error) {
    console.warn('更新阶段场景时出现警告:', error.message)
  }
}

function zoomToPoint(pointId) {
  if (!viewer || isFlying) return
  const point = scenarioPoints[pointId]
  stopAutoRotate()
  isFlying = true
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, 2500),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-45), roll: 0.0 },
    duration: 1.5,
    complete: () => {
      isFlying = false
      if (props.focusedPointId) applyOrbitView()
      if (pointId === 'accident_blue') updateTruckSequence(props.activePhaseIndex)
    }
  })
}

// 监听微调值的变化同步更新模型与粒子位置
watch([() => truckAdjust.lng, () => truckAdjust.lat, () => truckAdjust.heading, () => truckAdjust.height], () => {
  if (typeof truckAdjust.lng !== 'number' || typeof truckAdjust.lat !== 'number' || typeof truckAdjust.height !== 'number' || typeof truckAdjust.heading !== 'number') return;
  const position = Cesium.Cartesian3.fromDegrees(truckAdjust.lng, truckAdjust.lat, truckAdjust.height);
  const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(truckAdjust.heading), 0, 0);
  const orientation = Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
  
  truckEntities.forEach(entity => {
    entity.position = position;
    entity.orientation = orientation;
  });

  const matrix = Cesium.Transforms.eastNorthUpToFixedFrame(position);
  if (smokeParticle) smokeParticle.modelMatrix = matrix;
  if (fireParticle) fireParticle.modelMatrix = matrix;
});

// 监听油罐车微调变化
watch([() => tankerAdjust.lng, () => tankerAdjust.lat, () => tankerAdjust.heading, () => tankerAdjust.height], () => {
  if (typeof tankerAdjust.lng !== 'number' || typeof tankerAdjust.lat !== 'number' || typeof tankerAdjust.height !== 'number' || typeof tankerAdjust.heading !== 'number') return;
  const position = Cesium.Cartesian3.fromDegrees(tankerAdjust.lng, tankerAdjust.lat, tankerAdjust.height);
  const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(tankerAdjust.heading), 0, 0);
  const orientation = Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
  
  tankerEntities.forEach(entity => {
    entity.position = position;
    entity.orientation = orientation;
  });
});

// 监听救援车微调变化 (位置、角度和缩放已完全由 CallbackProperty 接管，此处无需手动更新 Entity 属性)

// 监听油罐车事故点位置变化同步更新泄露与弥漫效果位置
watch([() => tankerPointAdjust.lng, () => tankerPointAdjust.lat], () => {
  if (typeof tankerPointAdjust.lng !== 'number' || typeof tankerPointAdjust.lat !== 'number') return;
  const matrix = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(tankerPointAdjust.lng, tankerPointAdjust.lat, 0.0));
  if (leakParticle) leakParticle.modelMatrix = matrix;
  if (diffusionParticle) diffusionParticle.modelMatrix = matrix;
});

// 监听无人机微调变化 (位置和角度已完全由 CallbackProperty 接管，此处无需手动更新 Entity 属性)

// 无人机控制函数
function showUav() {
  uavEntities.forEach(entity => { entity.show = true })
  console.log('无人机已显示')
}

function hideUav() {
  uavEntities.forEach(entity => { entity.show = false })
  console.log('无人机已隐藏')
}

function flyToUav() {
  if (!viewer) return
  const position = Cesium.Cartesian3.fromDegrees(uavAdjust.lng, uavAdjust.lat, uavAdjust.height)
  viewer.camera.flyTo({
    destination: position,
    orientation: {
      heading: Cesium.Math.toRadians(uavAdjust.heading),
      pitch: Cesium.Math.toRadians(-30),
      roll: 0.0
    },
    duration: 2.0
  })
  console.log('正在飞往无人机位置')
}

defineExpose({ zoomToPoint });

watch(() => props.activePhaseIndex, (next, prev) => {
  if (next === 7 && prev !== 7) {
    phase7StartTime = Date.now();
    tankerPhase7StartTime = Date.now();
  } else if (next < 7) {
    phase7StartTime = 0;
    tankerPhase7StartTime = 0;
  }
  updatePhaseScene(next);
});

watch(() => props.focusedPointId, () => {
  updatePhaseScene(props.activePhaseIndex);
});

onMounted(() => initViewer())
onBeforeUnmount(() => {
  stopAutoRotate()
  if (viewer) {
    viewer.scene.postRender.removeEventListener(updateModelsReadyStatus)
    if (smokeParticle) viewer.scene.primitives.remove(smokeParticle)
    if (fireParticle) viewer.scene.primitives.remove(fireParticle)
    if (leakParticle) viewer.scene.primitives.remove(leakParticle)
    if (diffusionParticle) viewer.scene.primitives.remove(diffusionParticle)
    viewer.destroy()
  }
})
</script>

<style scoped>
.cesium-wrapper, .cesium-container { width: 100%; height: 100%; position: relative; }
.globe-mask {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(2, 10, 22, 0.88); color: rgba(255, 255, 255, 0.78);
}
.debug-panel {
  position: absolute; top: 100px; right: 20px; z-index: 999;
  background: rgba(0, 0, 0, 0.85); padding: 15px; border-radius: 8px; border: 1px solid #00e5ff; color: white; width: 220px;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
}
.debug-panel h4 {
  margin: 0 0 12px 0; color: #00e5ff; font-size: 14px; text-align: center;
}
.debug-panel div {
  margin-bottom: 8px;
}
.debug-panel label {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px;
}
.debug-panel input {
  width: 80px; padding: 4px; border: 1px solid #333; border-radius: 4px;
  background: rgba(255,255,255,0.1); color: white; font-size: 12px;
}
.scene-switcher .switch-buttons {
  display: flex; gap: 6px;
}
.scene-switcher .switch-buttons button {
  flex: 1; padding: 6px 8px; border: 1px solid #333; border-radius: 4px;
  background: rgba(255,255,255,0.1); color: white; font-size: 11px;
  cursor: pointer; transition: all 0.2s;
}
.scene-switcher .switch-buttons button:hover {
  background: rgba(0, 229, 255, 0.2);
}
.scene-switcher .switch-buttons button.active {
  background: linear-gradient(135deg, #00e5ff, #0080ff);
  color: #061628;
  font-weight: bold;
  border-color: #00e5ff;
}
.debug-panel button {
  width: 100%; margin-top: 5px; padding: 6px; border: none; border-radius: 4px;
  background: linear-gradient(135deg, #00e5ff, #0080ff); color: #061628;
  font-size: 12px; font-weight: bold; cursor: pointer;
}
.debug-panel button:hover {
  opacity: 0.9;
}
.debug-row { margin-bottom: 10px; display: flex; flex-direction: column; }
.debug-panel h3 { margin: 0 0 15px 0; color: #00e5ff; font-size: 16px; }
.phase-indicator { display: flex; gap: 4px; margin-top: 8px; }
.phase-indicator span { flex: 1; height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; }
.phase-indicator span.active { background: #00e5ff; box-shadow: 0 0 8px #00e5ff; }
.play-btn {
  background: #00e5ff; color: #061628; border: none; padding: 8px; border-radius: 4px; cursor: pointer; font-weight: bold;
}

</style>
