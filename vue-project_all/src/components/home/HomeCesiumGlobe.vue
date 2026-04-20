<template>
  <div class="globe-shell">
    <div ref="containerRef" class="globe-viewer"></div>
    
    <!-- 临时微调控件：货车追尾现场 -->
    <div class="debug-panel" v-if="focusedPointId === 'accident_blue'">
      <h3>货车模型微调</h3>
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
        <span>旋转: {{ tankerAdjust.heading }}°</span>
        <input type="range" v-model.number="tankerAdjust.heading" min="0" max="360" step="1" />
      </div>
      <div class="debug-row">
        <span>经度:</span>
        <input type="number" v-model.number="tankerAdjust.lng" step="0.000001" />
      </div>
      <div class="debug-row">
        <span>纬度:</span>
        <input type="number" v-model.number="tankerAdjust.lat" step="0.000001" />
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

// 货车微调状态
const truckAdjust = reactive({
  scale: 0.82,
  heading: 17,
  lng: 113.104833,
  lat: 30.385469
})

// 油罐车微调状态
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
let truckEntity = null
let animationCheckTimer = null
let smokePrimitives = [] // 保存烟雾粒子系统

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

function getOrbitTarget() {
  return Cesium.Cartesian3.fromDegrees(108, 31, 0)
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
  const range = isFocused ? 2500 : 18000000
  const pitch = isFocused ? Cesium.Math.toRadians(-45) : Cesium.Math.toRadians(-34)
  viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(orbitHeading, pitch, range))
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
  if (viewer && spinCallback) {
    viewer.clock.onTick.removeEventListener(spinCallback)
  }
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

// 核心函数：创建烟雾粒子系统
function createSmoke(lng, lat, id) {
  if (!viewer) return null
  
  const modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(
    Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)
  );

  const particleSystem = viewer.scene.primitives.add(new Cesium.ParticleSystem({
    image: '/Dashboard/images/smoke.png',
    startColor: Cesium.Color.LIGHTGRAY.withAlpha(0.7),
    endColor: Cesium.Color.WHITE.withAlpha(0.0),
    startScale: 0.5,
    endScale: 2.0,
    minimumParticleLife: 1.2,
    maximumParticleLife: 2.5,
    minimumSpeed: 1.0,
    maximumSpeed: 4.0,
    imageSize: new Cesium.Cartesian2(15, 15),
    emissionRate: 20.0,
    lifetime: 16.0,
    emitter: new Cesium.CircleEmitter(1.0),
    modelMatrix: modelMatrix,
    sizeInMeters: true,
    show: false // 初始隐藏
  }));

  particleSystem.id = `smoke-${id}`
  return particleSystem
}

// 核心函数：创建火焰粒子系统
function createFire(lng, lat, id) {
  if (!viewer) return null
  
  const modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(
    Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)
  );

  const particleSystem = viewer.scene.primitives.add(new Cesium.ParticleSystem({
    image: '/Dashboard/images/fire.png',
    startColor: Cesium.Color.ORANGE.withAlpha(0.9),
    endColor: Cesium.Color.RED.withAlpha(0.3),
    startScale: 0.2,
    endScale: 0.8,
    minimumParticleLife: 0.5,
    maximumParticleLife: 1.5,
    minimumSpeed: 2.0,
    maximumSpeed: 5.0,
    imageSize: new Cesium.Cartesian2(10, 10),
    emissionRate: 30.0,
    lifetime: 16.0,
    emitter: new Cesium.CircleEmitter(0.5),
    modelMatrix: modelMatrix,
    sizeInMeters: true,
    show: false // 初始隐藏
  }));

  particleSystem.id = `fire-${id}`
  return particleSystem
}

// 核心函数：创建油罐车泄露效果
function createLeak(lng, lat, id) {
  if (!viewer) return null
  
  const modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(
    Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)
  );

  const particleSystem = viewer.scene.primitives.add(new Cesium.ParticleSystem({
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
    modelMatrix: modelMatrix,
    sizeInMeters: true,
    show: false // 初始隐藏
  }));

  particleSystem.id = `leak-${id}`
  return particleSystem
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
    viewer.scene.globe.showGroundAtmosphere = true
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#010811')
    viewer.cesiumWidget.creditContainer.style.display = 'none'

    viewer.imageryLayers.removeAll()
    const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
    )
    viewer.imageryLayers.addImageryProvider(imagery)

    addEventEntities()
    
    // 初始化烟雾
    smokePrimitives.push(createSmoke(truckAdjust.lng, truckAdjust.lat, 'blue'))
    smokePrimitives.push(createSmoke(tankerAdjust.lng, tankerAdjust.lat, 'red'))
    
    // 初始化火焰
    smokePrimitives.push(createFire(truckAdjust.lng, truckAdjust.lat, 'blue'))
    smokePrimitives.push(createFire(tankerAdjust.lng, tankerAdjust.lat, 'red'))
    
    // 初始化油罐车泄露效果
    smokePrimitives.push(createLeak(tankerAdjust.lng, tankerAdjust.lat, 'red'))

    applyOrbitView()
    updatePhaseScene(props.activePhaseIndex)
    startAutoRotate()
    loading.value = false
  } catch (error) {
    errorMessage.value = '三维地球初始化失败'
    loading.value = false
  }
}

function playTankerAnimation() {
  if (!viewer || !viewer.scene || !tankerEntity) return
  const primitives = viewer.scene.primitives
  for (let i = 0; i < primitives.length; i++) {
    const p = primitives.get(i)
    if (p.id === tankerEntity && p.activeAnimations) {
      p.activeAnimations.removeAll()
      p.activeAnimations.add({
        index: 0,
        loop: Cesium.ModelAnimationLoop.NONE,
        multiplier: 0.2,
        startTime: viewer.clock.currentTime
      })
      break
    }
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

  truckEntity = viewer.entities.add({
    id: 'accident_blue',
    position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(truckAdjust.lng, truckAdjust.lat, 0), false),
    orientation: new Cesium.CallbackProperty(() => {
      const position = Cesium.Cartesian3.fromDegrees(truckAdjust.lng, truckAdjust.lat, 0);
      const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(truckAdjust.heading), 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
    }, false),
    point: {
      pixelSize: 12, color: Cesium.Color.fromCssColorString('#00e5ff'), outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2, heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
    model: {
      uri: '/Dashboard/models/truck rear-ended_1.glb',
      scale: new Cesium.CallbackProperty(() => truckAdjust.scale, false),
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
    }
  })

  tankerEntity = viewer.entities.add({
    id: 'accident_red',
    position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(tankerAdjust.lng, tankerAdjust.lat, 0), false),
    orientation: new Cesium.CallbackProperty(() => {
      const position = Cesium.Cartesian3.fromDegrees(tankerAdjust.lng, tankerAdjust.lat, 0);
      const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(tankerAdjust.heading), 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
    }, false),
    point: {
      pixelSize: 12, color: Cesium.Color.fromCssColorString('#ffb84d'), outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2, heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
    model: {
      uri: '/Dashboard/models/tanker_leak_scene.2.glb',
      scale: new Cesium.CallbackProperty(() => tankerAdjust.scale, false),
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      runAnimations: true
    },
  })

  animationCheckTimer = setInterval(() => {
    if (!viewer || !viewer.scene) return
    const primitives = viewer.scene.primitives
    for (let i = 0; i < primitives.length; i++) {
      const p = primitives.get(i)
      if (p.id === tankerEntity && p.activeAnimations) {
        playTankerAnimation()
        clearInterval(animationCheckTimer)
        break
      }
    }
  }, 1000)

  viewer.screenSpaceEventHandler.setInputAction(function onLeftClick(movement) {
    const pickedObject = viewer.scene.pick(movement.position);
    if (Cesium.defined(pickedObject) && pickedObject.id) {
      const entityId = pickedObject.id.id;
      if (entityId === 'accident_blue' || entityId === 'accident_red') {
        emit('accident-picked', entityId);
        zoomToPoint(entityId);
      }
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}

function formatPopupText(phase, point) {
  const systemsText = (phase.systems || []).join(' / ')
  return `${phase.title}\n位置：${point.label}\n时间：${phase.time}\n联动：${systemsText}`
}

function updatePhaseScene(index) {
  if (!viewer || !props.phases.length || !focusAreaEntity) return
  const phase = props.phases[index] || props.phases[0]
  if (!phase) return
  const pointId = props.focusedPointId || phase.focusPoint || 'gateway'
  const point = scenarioPoints[pointId] || scenarioPoints.gateway
  const pointColor = point.color || '#00e5ff'
  
  let lng = point.longitude, lat = point.latitude;
  if (pointId === 'accident_blue') {
    lng = truckAdjust.lng; lat = truckAdjust.lat;
  } else if (pointId === 'accident_red') {
    lng = tankerAdjust.lng; lat = tankerAdjust.lat;
  }

  const pointPosition = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
  focusAreaEntity.position = pointPosition
  focusAreaEntity.ellipse.material = toCesiumColor(pointColor, 0.08)
  focusAreaEntity.ellipse.outlineColor = toCesiumColor(pointColor, 0.36)
  focusAreaEntity.ellipse.semiMinorAxis = phase.areaRadiusMinor || 150000
  focusAreaEntity.ellipse.semiMajorAxis = phase.areaRadiusMajor || 190000

  if (popupEntity) {
    popupEntity.position = Cesium.Cartesian3.fromDegrees(lng, lat, 500)
    popupEntity.label.text = formatPopupText(phase, point)
    popupEntity.label.backgroundColor = toCesiumColor('#061628', 0.9)
  }

  // 烟雾、火焰和泄露效果显隐控制：进入现场才显示对应的效果
  smokePrimitives.forEach(particle => {
    if (particle) {
      const isFire = particle.id.includes('fire');
      const isLeak = particle.id.includes('leak');
      const isBlue = particle.id.includes('blue');
      const isRed = particle.id.includes('red');
      
      if (isFire) {
        // 火焰只在货车追尾现场显示
        particle.show = !!props.focusedPointId && pointId === 'accident_blue' && isBlue;
      } else if (isLeak) {
        // 泄露效果只在油罐车泄露现场显示
        particle.show = !!props.focusedPointId && pointId === 'accident_red' && isRed;
      } else {
        // 烟雾在两个事故点都显示
        particle.show = !!props.focusedPointId && particle.id.includes(pointId === 'accident_blue' ? 'blue' : 'red');
      }
    }
  })

  if (!spinCallback && props.focusedPointId && !isFlying) applyOrbitView()
}

function zoomToPoint(pointId) {
  if (!viewer || isFlying) return
  const point = scenarioPoints[pointId] || scenarioPoints.gateway
  let lng = point.longitude, lat = point.latitude;
  if (pointId === 'accident_blue') {
    lng = truckAdjust.lng; lat = truckAdjust.lat;
  } else if (pointId === 'accident_red') {
    lng = tankerAdjust.lng; lat = tankerAdjust.lat;
  }

  stopAutoRotate()
  viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  isFlying = true
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(lng, lat, 2500),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-45), roll: 0.0 },
    duration: 1.5,
    complete: () => {
      isFlying = false
      if (props.focusedPointId) applyOrbitView()
      if (pointId === 'accident_red') playTankerAnimation()
    },
    cancel: () => { isFlying = false }
  })
}

function zoomToPhase(index) {
  const phase = props.phases[index]
  if (phase) zoomToPoint(phase.focusPoint)
}

defineExpose({ zoomToPhase, zoomToPoint })
watch(() => props.activePhaseIndex, (nextValue) => updatePhaseScene(nextValue))
watch(() => props.focusedPointId, () => updatePhaseScene(props.activePhaseIndex))

// 监听微调值的变化
watch([() => truckAdjust.lng, () => truckAdjust.lat, () => tankerAdjust.lng, () => tankerAdjust.lat], () => {
  if (!isFlying && props.focusedPointId) applyOrbitView();
  
  // 同步更新烟雾、火焰和泄露效果位置
  smokePrimitives.forEach(particle => {
    if (!particle) return;
    const isBlue = particle.id.includes('blue');
    const lng = isBlue ? truckAdjust.lng : tankerAdjust.lng;
    const lat = isBlue ? truckAdjust.lat : tankerAdjust.lat;
    particle.modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(
      Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)
    );
  });
});

onMounted(() => initViewer())
onBeforeUnmount(() => {
  if (animationCheckTimer) clearInterval(animationCheckTimer)
  stopAutoRotate()
  if (viewer) {
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
    viewer.destroy()
    viewer = null
  }
})
</script>

<style scoped>
.globe-shell, .globe-viewer { width: 100%; height: 100%; }
.globe-shell { position: relative; }
.globe-mask {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: radial-gradient(circle at center, rgba(0, 229, 255, 0.08) 0%, rgba(0, 229, 255, 0) 44%), rgba(2, 10, 22, 0.88);
  color: rgba(255, 255, 255, 0.78); font-size: 14px; letter-spacing: 0.08em;
}
.globe-mask.is-error { color: #ff9b9b; }

.debug-panel {
  position: absolute; top: 100px; right: 20px; z-index: 9999;
  background: rgba(0, 0, 0, 0.8); padding: 15px; border-radius: 8px; border: 1px solid #00e5ff; color: white; width: 220px;
}
.debug-row { margin-bottom: 10px; display: flex; flex-direction: column; }
.debug-panel h3 { margin: 0 0 15px 0; color: #00e5ff; font-size: 16px; }
.debug-row span { font-size: 12px; margin-bottom: 5px; }
.debug-row input { background: #333; color: white; border: 1px solid #555; padding: 4px; }
</style>
