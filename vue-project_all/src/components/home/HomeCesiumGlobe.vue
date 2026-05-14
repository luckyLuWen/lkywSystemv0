<template>
  <div class="globe-shell">
    <div ref="containerRef" class="globe-viewer"></div>
    
    <!-- 临时微调控件：货车追尾现场 -->
    <div class="debug-panel" v-if="focusedPointId === 'accident_blue'">
      <h3>货车事故分段控制</h3>
      <div class="debug-row">
        <span>当前阶段: {{ phases[activePhaseIndex]?.shortLabel }}</span>
        <div class="phase-indicator">
          <span v-for="i in 6" :key="i" :class="{ active: (i-1) === activePhaseIndex }"></span>
        </div>
      </div>
      <div class="debug-row" style="margin-top: 10px;">
        <button class="play-btn" @click="replayCurrentPhase">重播当前动画</button>
      </div>
      <hr style="border: 0; border-top: 1px solid rgba(0,229,255,0.2); margin: 15px 0;" />
      <div class="debug-row">
        <span>比例: {{ truckAdjust.scale }}</span>
        <input type="range" v-model.number="truckAdjust.scale" min="0.01" max="5" step="0.01" />
      </div>
      <div class="debug-row">
        <span>旋转: {{ truckAdjust.heading }}°</span>
        <input type="range" v-model.number="truckAdjust.heading" min="0" max="360" step="1" />
      </div>
      <div class="debug-row">
        <span>经度:</span>
        <input type="number" v-model.number="truckAdjust.lng" step="0.000001" />
      </div>
      <div class="debug-row">
        <span>纬度:</span>
        <input type="number" v-model.number="truckAdjust.lat" step="0.000001" />
      </div>
    </div>

    <!-- 临时微调控件：油罐车泄露现场 -->
    <div class="debug-panel" v-if="focusedPointId === 'accident_red'">
      <h3>油罐车模型微调</h3>
      <div class="debug-row">
        <span>比例: {{ tankerAdjust.scale }}</span>
        <input type="range" v-model.number="tankerAdjust.scale" min="0.01" max="5" step="0.01" />
      </div>
      <div class="debug-row">
        <span>经度:</span>
        <input type="number" v-model.number="tankerAdjust.lng" step="0.000001" />
      </div>
    </div>

    <div v-if="loading" class="globe-mask">三维地球加载中...</div>
    <div v-else-if="errorMessage" class="globe-mask is-error">{{ errorMessage }}</div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch, reactive } from 'vue'
import * as Cesium from 'cesium'

const props = defineProps({
  phases: { type: Array, default: () => [] },
  activePhaseIndex: { type: Number, default: 0 },
  focusedPointId: { type: String, default: '' },
})

const emit = defineEmits(['accident-picked'])

// 货车事故分段模型配置 (去重，仅保留唯一物理模型)
const truckModelConfigs = [
  { id: 'model_normal', uri: '/Dashboard/models/Normal_Drive.glb', label: '正常行驶' },
  { id: 'model_accident', uri: '/Dashboard/models/Accident_Occur1.glb', label: '事故阶段' }
]

// 阶段索引到模型ID的映射
const phaseToModelMap = {
  1: 'model_normal',
  2: 'model_accident',
  3: 'model_accident',
  4: 'model_accident',
  5: 'model_accident'
}

let currentActiveModelId = null // 用于防止重复触发相同模型的动画逻辑

const truckAdjust = reactive({
  scale: 0.82,
  heading: 17,
  lng: 113.104833,
  lat: 30.385469
})

const tankerAdjust = reactive({
  scale: 0.04,
  heading: 36,
  lng: 113.070272,
  lat: 30.238683
})

const containerRef = ref(null)
const loading = ref(true)
const errorMessage = ref('')

let viewer = null
let spinCallback = null
let lastSpinAt = 0
let orbitHeading = Cesium.Math.toRadians(8)
let focusAreaEntity = null
let popupEntity = null
let isFlying = false
let tankerEntity = null
let truckEntities = [] 
let animationCheckTimer = null

// 粒子系统实例
let smokeParticle = null
let fireParticle = null
let leakParticle = null

const scenarioPoints = {
  command: { id: 'command', label: '远程指挥中心', longitude: 114.3055, latitude: 30.5928, color: '#67b8ff' },
  gateway: { id: 'gateway', label: '边缘传感网关', longitude: 114.3524, latitude: 30.5442, color: '#00e5ff' },
  detection: { id: 'detection', label: '检测现场', longitude: 114.389, latitude: 30.5282, color: '#ffb84d' },
  response: { id: 'response', label: '协同处置区域', longitude: 114.3348, latitude: 30.5638, color: '#8cf7c5' },
  accident_blue: { id: 'accident_blue', label: '货车追尾现场', longitude: 113.104833, latitude: 30.385469, color: '#00e5ff' },
  accident_red: { id: 'accident_red', label: '油罐车泄露现场', longitude: 113.070272, latitude: 30.238683, color: '#ffb84d' },
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
      lng = tankerAdjust.lng; lat = tankerAdjust.lat;
    } else {
      lng = scenarioPoints[pointId].longitude;
      lat = scenarioPoints[pointId].latitude;
    }
  } else {
    lng = 108; lat = 31;
  }

  const target = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
  const range = isFocused ? 400 : 18000000
  const pitch = isFocused ? Cesium.Math.toRadians(-45) : Cesium.Math.toRadians(-34)
  viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(orbitHeading, pitch, range))
  
  // 如果没有在自动旋转，则立即解除锁定，允许鼠标自由操作
  if (!spinCallback) {
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  }
}

function startAutoRotate() {
  if (!viewer || spinCallback) return
  lastSpinAt = performance.now()
  spinCallback = () => {
    if (!viewer) return
    const now = performance.now()
    const deltaSeconds = (now - lastSpinAt) / 1000
    lastSpinAt = now
    orbitHeading -= 0.06 * deltaSeconds
    applyOrbitView()
  }
  viewer.clock.onTick.addEventListener(spinCallback)
}

function stopAutoRotate() {
  if (viewer && spinCallback) viewer.clock.onTick.removeEventListener(spinCallback)
  spinCallback = null
  if (viewer) {
    const position = viewer.camera.position.clone()
    const direction = viewer.camera.direction.clone()
    const up = viewer.camera.up.clone()
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
    viewer.camera.position = position
    viewer.camera.direction = direction
    viewer.camera.up = up
  }
}

// 创建烟雾
function createSmokeSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/smoke.png',
    startColor: Cesium.Color.LIGHTGRAY.withAlpha(0.7),
    endColor: Cesium.Color.WHITE.withAlpha(0.0),
    startScale: 0.5,
    endScale: 2.0,
    minimumParticleLife: 1.5,
    maximumParticleLife: 3.0,
    minimumSpeed: 1.0,
    maximumSpeed: 4.0,
    imageSize: new Cesium.Cartesian2(15, 15),
    emissionRate: 20.0,
    lifetime: 16.0,
    emitter: new Cesium.CircleEmitter(2.0),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false
  });
}

// 创建火焰
function createFireSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/fire.png',
    startColor: Cesium.Color.ORANGE.withAlpha(0.8),
    endColor: Cesium.Color.RED.withAlpha(0.2),
    startScale: 0.3,
    endScale: 1.2,
    minimumParticleLife: 0.6,
    maximumParticleLife: 1.5,
    minimumSpeed: 2.0,
    maximumSpeed: 6.0,
    imageSize: new Cesium.Cartesian2(12, 12),
    emissionRate: 35.0,
    lifetime: 16.0,
    emitter: new Cesium.CircleEmitter(1.0),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false
  });
}

// 创建油罐车泄露效果
function createLeakSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/fog01.png',
    startColor: Cesium.Color.LIGHTBLUE.withAlpha(0.6),
    endColor: Cesium.Color.LIGHTBLUE.withAlpha(0.1),
    startScale: 0.4,
    endScale: 1.5,
    minimumParticleLife: 2.0,
    maximumParticleLife: 4.0,
    minimumSpeed: 0.5,
    maximumSpeed: 2.0,
    imageSize: new Cesium.Cartesian2(12, 12),
    emissionRate: 15.0,
    lifetime: 16.0,
    emitter: new Cesium.CircleEmitter(0.6),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false
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
    Cesium.Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIyYTUwYmE4Zi01ZjZlLTQ0MjAtYWMwNS0yYjBkZGFiM2RmOTUiLCJpZCI6MzU4MzQ0LCJpYXQiOjE3NjI1Nzc2NjR9.q9QoG-_99QZ2R2TlUYjiWGhn0-S5I22FFGuou_NAE3Q"

    viewer.imageryLayers.removeAll()
    viewer.imageryLayers.addImageryProvider(
      new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 19,
      })
    )

    addEventEntities()
    
    // 初始化粒子系统
    smokeParticle = viewer.scene.primitives.add(createSmokeSystem(truckAdjust.lng, truckAdjust.lat))
    fireParticle = viewer.scene.primitives.add(createFireSystem(truckAdjust.lng, truckAdjust.lat))
    leakParticle = viewer.scene.primitives.add(createLeakSystem(tankerAdjust.lng, tankerAdjust.lat))

    applyOrbitView()
    updatePhaseScene(props.activePhaseIndex)
    loading.value = false
  } catch (error) {
    errorMessage.value = '三维地球初始化失败'
    loading.value = false
  }
}

function updateTruckSequence(phaseIndex) {
  if (!viewer) return
  
  const targetModelId = phaseToModelMap[phaseIndex] || null
  
  // 1. 物理显隐状态：始终同步。确保无论从哪个区域切回来，模型都能按当前阶段显示
  truckEntities.forEach((entity) => {
    entity.show = (entity.id === targetModelId)
  })

  // 2. 动画触发逻辑：只有当物理模型文件真正发生变化时（如从正常行驶模型切到事故模型），才触发播放
  if (targetModelId && targetModelId !== currentActiveModelId) {
    const entity = truckEntities.find(e => e.id === targetModelId)
    if (entity) playEntityAnimation(entity)
  }
  
  currentActiveModelId = targetModelId

  // 粒子效果控制：针对货车追尾现场
  const isAccidentArea = props.focusedPointId === 'accident_blue' || 
                        (props.phases[phaseIndex]?.focusPoint === 'accident_blue');

  // 5: 大火蔓延阶段，将效果放大
  const isBigFire = (phaseIndex === 5);
  const smokeScaleBase = isBigFire ? 2.8 : 1.0; 
  const fireScaleBase = isBigFire ? 2.0 : 1.0;

  if (smokeParticle) {
    smokeParticle.show = (phaseIndex >= 3 && isAccidentArea);
    smokeParticle.startScale = 0.5 * smokeScaleBase;
    smokeParticle.endScale = 2.0 * smokeScaleBase;
  }
  if (fireParticle) {
    fireParticle.show = (phaseIndex >= 4 && isAccidentArea);
    fireParticle.startScale = 0.3 * fireScaleBase;
    fireParticle.endScale = 1.2 * fireScaleBase;
  }
}

function playEntityAnimation(entity) {
  let attempts = 0;
  const maxAttempts = 50; 

  const tryPlay = () => {
    if (!viewer || !entity) return;
    const primitives = viewer.scene.primitives;
    let found = false;
    
    for (let i = 0; i < primitives.length; i++) {
      const p = primitives.get(i);
      if (p.id === entity && p.activeAnimations) {
        found = true;
        p.activeAnimations.removeAll();
        p.activeAnimations.addAll({
          loop: Cesium.ModelAnimationLoop.NONE,
          multiplier: 1.0,
          startTime: viewer.clock.currentTime, 
          removeOnStop: false
        });
        break;
      }
    }

    if (!found && attempts < maxAttempts) {
      attempts++;
      setTimeout(tryPlay, 100);
    }
  };

  tryPlay();
}

function replayCurrentPhase() {
  if (currentActiveModelId) {
    const entity = truckEntities.find(e => e.id === currentActiveModelId)
    if (entity) playEntityAnimation(entity)
  }
}

function addEventEntities() {
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
      pixelOffset: new Cesium.Cartesian2(120, -56), disableDepthTestDistance: Number.POSITIVE_INFINITY,
      horizontalOrigin: Cesium.HorizontalOrigin.LEFT, verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      style: Cesium.LabelStyle.FILL, scale: 0.96,
    },
  })

  // 改用 truckModelConfigs
  viewer.entities.add({
    id: 'yellow-target-point',
    position: Cesium.Cartesian3.fromDegrees(113.104833, 30.385469, 0),
    point: {
      pixelSize: 10,
      color: Cesium.Color.YELLOW,
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 2,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  })

  truckModelConfigs.forEach((config) => {
    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false,
      position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(truckAdjust.lng, truckAdjust.lat, 0), false),
      orientation: new Cesium.CallbackProperty(() => {
        const position = Cesium.Cartesian3.fromDegrees(truckAdjust.lng, truckAdjust.lat, 0);
        const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(truckAdjust.heading), 0, 0);
        return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
      }, false),
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => truckAdjust.scale, false),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        runAnimations: false // 关键修改：禁用自动播放，防止内部循环
      }
    })
    truckEntities.push(entity)
  })

  tankerEntity = viewer.entities.add({
    id: 'accident_red',
    position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(tankerAdjust.lng, tankerAdjust.lat, 0), false),
    orientation: new Cesium.CallbackProperty(() => {
      const position = Cesium.Cartesian3.fromDegrees(tankerAdjust.lng, tankerAdjust.lat, 0);
      const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(tankerAdjust.heading), 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
    }, false),
    model: {
      uri: '/Dashboard/models/tanker_leak_scene.2.glb',
      scale: new Cesium.CallbackProperty(() => tankerAdjust.scale, false),
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      runAnimations: true // 油罐车可以保持自动播放（如果有持续效果的话）
    },
  })

  viewer.screenSpaceEventHandler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.position);
    if (Cesium.defined(pickedObject) && pickedObject.id) {
      const entityId = pickedObject.id.id;
      if (entityId.includes('truck_sequence') || entityId === 'accident_red') {
        const emitId = entityId.includes('truck_sequence') ? 'accident_blue' : 'accident_red'
        emit('accident-picked', emitId);
        zoomToPoint(emitId);
      }
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}

function updatePhaseScene(index) {
  if (!viewer || !props.phases.length || !focusAreaEntity) return
  const phase = props.phases[index] || props.phases[0]
  const pointId = props.focusedPointId || phase.focusPoint || 'gateway'
  const point = scenarioPoints[pointId] || scenarioPoints.gateway
  
  let lng = point.longitude, lat = point.latitude;
  if (pointId === 'accident_blue') {
    lng = truckAdjust.lng; lat = truckAdjust.lat;
    updateTruckSequence(index)
  } else if (pointId === 'accident_red') {
    lng = tankerAdjust.lng; lat = tankerAdjust.lat;
    truckEntities.forEach(e => e.show = false)
    if (smokeParticle) smokeParticle.show = false;
    if (fireParticle) fireParticle.show = false;
    if (leakParticle) leakParticle.show = true;
  } else {
    truckEntities.forEach(e => e.show = false)
    if (smokeParticle) smokeParticle.show = false;
    if (fireParticle) fireParticle.show = false;
    if (leakParticle) leakParticle.show = false;
  }

  focusAreaEntity.position = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
  if (popupEntity) {
    popupEntity.position = Cesium.Cartesian3.fromDegrees(lng, lat, 500)
    popupEntity.label.text = `${phase.title}\n位置：${point.label}\n联动：${(phase.systems || []).join('/')}`
  }

  if (!spinCallback && props.focusedPointId && !isFlying) applyOrbitView()
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

// 监听微调值的变化同步更新粒子位置
watch([() => truckAdjust.lng, () => truckAdjust.lat], () => {
  const matrix = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(truckAdjust.lng, truckAdjust.lat, 0.0));
  if (smokeParticle) smokeParticle.modelMatrix = matrix;
  if (fireParticle) fireParticle.modelMatrix = matrix;
});

// 监听油罐车位置变化同步更新泄露效果位置
watch([() => tankerAdjust.lng, () => tankerAdjust.lat], () => {
  const matrix = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(tankerAdjust.lng, tankerAdjust.lat, 0.0));
  if (leakParticle) leakParticle.modelMatrix = matrix;
});

defineExpose({ zoomToPoint })
watch(() => props.activePhaseIndex, (next) => updatePhaseScene(next))
watch(() => props.focusedPointId, () => updatePhaseScene(props.activePhaseIndex))

onMounted(() => initViewer())
onBeforeUnmount(() => {
  stopAutoRotate()
  if (viewer) {
    if (smokeParticle) viewer.scene.primitives.remove(smokeParticle)
    if (fireParticle) viewer.scene.primitives.remove(fireParticle)
    if (leakParticle) viewer.scene.primitives.remove(leakParticle)
    viewer.destroy()
  }
})
</script>

<style scoped>
.globe-shell, .globe-viewer { width: 100%; height: 100%; }
.globe-shell { position: relative; }
.globe-mask {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(2, 10, 22, 0.88); color: rgba(255, 255, 255, 0.78);
}
.debug-panel {
  position: absolute; top: 100px; right: 20px; z-index: 999;
  background: rgba(0, 0, 0, 0.8); padding: 15px; border-radius: 8px; border: 1px solid #00e5ff; color: white; width: 220px;
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
