<template>
  <div class="globe-shell">
    <div ref="containerRef" class="globe-viewer"></div>
    <div v-if="loading" class="globe-mask">三维地球加载中...</div>
    <div v-else-if="errorMessage" class="globe-mask is-error">{{ errorMessage }}</div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as Cesium from 'cesium'

const props = defineProps({
  phases: {
    type: Array,
    default: () => [],
  },
  activePhaseIndex: {
    type: Number,
    default: 0,
  },
})

const containerRef = ref(null)
const loading = ref(true)
const errorMessage = ref('')

let viewer = null
let spinCallback = null
let lastSpinAt = 0
let orbitHeading = Cesium.Math.toRadians(8)
let focusMarkerEntity = null
let focusAreaEntity = null
let popupEntity = null

const scenarioPoints = {
  command: {
    id: 'command',
    label: '远程指挥中心',
    longitude: 114.3055,
    latitude: 30.5928,
    color: '#67b8ff',
  },
  gateway: {
    id: 'gateway',
    label: '边缘传感网关',
    longitude: 114.3524,
    latitude: 30.5442,
    color: '#00e5ff',
  },
  detection: {
    id: 'detection',
    label: '检测现场',
    longitude: 114.389,
    latitude: 30.5282,
    color: '#ffb84d',
  },
  response: {
    id: 'response',
    label: '协同处置区域',
    longitude: 114.3348,
    latitude: 30.5638,
    color: '#8cf7c5',
  },
}

function toCesiumColor(color, alpha = 1) {
  return Cesium.Color.fromCssColorString(color).withAlpha(alpha)
}

function getOrbitTarget() {
  return Cesium.Cartesian3.fromDegrees(108, 31, 0)
}

function applyOrbitView() {
  if (!viewer) return

  viewer.camera.lookAt(
    getOrbitTarget(),
    new Cesium.HeadingPitchRange(
      orbitHeading,
      Cesium.Math.toRadians(-34),
      18000000
    )
  )
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
}

async function initViewer() {
  if (!containerRef.value || viewer) return

  try {
    viewer = new Cesium.Viewer(containerRef.value, {
      animation: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      shouldAnimate: true,
      skyAtmosphere: false,
    })

    viewer.scene.globe.enableLighting = true
    viewer.scene.globe.showGroundAtmosphere = true
    viewer.scene.screenSpaceCameraController.minimumZoomDistance = 12000000
    viewer.scene.screenSpaceCameraController.maximumZoomDistance = 26000000
    viewer.scene.screenSpaceCameraController.enableTranslate = false
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#010811')
    viewer.cesiumWidget.creditContainer.style.display = 'none'

    viewer.imageryLayers.removeAll()
    const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
    )
    viewer.imageryLayers.addImageryProvider(imagery)

    addEventEntities()
    applyOrbitView()
    updatePhaseScene(props.activePhaseIndex)
    startAutoRotate()
    loading.value = false
  } catch (error) {
    console.error(error)
    errorMessage.value = '三维地球初始化失败'
    loading.value = false
  }
}

function addEventEntities() {
  focusAreaEntity = viewer.entities.add({
    id: 'event-area',
    position: Cesium.Cartesian3.fromDegrees(114.35, 30.55, 0),
    ellipse: {
      semiMinorAxis: 150000,
      semiMajorAxis: 190000,
      material: toCesiumColor('#00e5ff', 0.06),
      outline: true,
      outlineColor: toCesiumColor('#00e5ff', 0.32),
      height: 0,
    },
  })

  focusMarkerEntity = viewer.entities.add({
    id: 'event-focus',
    position: Cesium.Cartesian3.fromDegrees(114.35, 30.55, 1200),
    point: {
      pixelSize: 16,
      color: toCesiumColor('#00e5ff', 0.98),
      outlineColor: Cesium.Color.WHITE.withAlpha(0.95),
      outlineWidth: 2,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  })

  popupEntity = viewer.entities.add({
    id: 'event-popup',
    position: Cesium.Cartesian3.fromDegrees(114.35, 30.55, 1200),
    label: {
      text: '',
      font: 'bold 15px Microsoft YaHei',
      fillColor: Cesium.Color.WHITE,
      showBackground: true,
      backgroundColor: toCesiumColor('#061628', 0.88),
      backgroundPadding: new Cesium.Cartesian2(16, 12),
      pixelOffset: new Cesium.Cartesian2(120, -56),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      horizontalOrigin: Cesium.HorizontalOrigin.LEFT,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      style: Cesium.LabelStyle.FILL,
      scale: 0.96,
    },
  })
}

function formatPopupText(phase, point) {
  const systemsText = (phase.systems || []).join(' / ')
  return `${phase.title}\n位置：${phase.focusLabel || point.label}\n时间：${phase.time}\n联动：${systemsText}`
}

function updatePhaseScene(index) {
  if (!viewer || !props.phases.length || !popupEntity || !focusMarkerEntity || !focusAreaEntity) {
    return
  }

  const phase = props.phases[index] || props.phases[0]
  if (!phase) return

  const point = scenarioPoints[phase.focusPoint] || scenarioPoints.gateway
  const pointColor = point.color || '#00e5ff'
  const pointPosition = Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, 1200)

  focusMarkerEntity.position = pointPosition
  focusMarkerEntity.point.color = toCesiumColor(pointColor, 0.98)

  focusAreaEntity.position = Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, 0)
  focusAreaEntity.ellipse.material = toCesiumColor(pointColor, 0.08)
  focusAreaEntity.ellipse.outlineColor = toCesiumColor(pointColor, 0.36)
  focusAreaEntity.ellipse.semiMinorAxis = phase.areaRadiusMinor || 150000
  focusAreaEntity.ellipse.semiMajorAxis = phase.areaRadiusMajor || 190000

  popupEntity.position = pointPosition
  popupEntity.label.text = formatPopupText(phase, point)
  popupEntity.label.backgroundColor = toCesiumColor('#061628', 0.9)
  popupEntity.label.pixelOffset = new Cesium.Cartesian2(
    phase.popupOffsetX ?? 110,
    phase.popupOffsetY ?? -56
  )

  orbitHeading = Cesium.Math.toRadians(phase.focusHeading ?? 8)
  applyOrbitView()
}

watch(
  () => props.activePhaseIndex,
  (nextValue) => {
    updatePhaseScene(nextValue)
  }
)

onMounted(() => {
  initViewer()
})

onBeforeUnmount(() => {
  stopAutoRotate()

  if (viewer) {
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
    viewer.destroy()
    viewer = null
  }
})
</script>

<style scoped>
.globe-shell,
.globe-viewer {
  width: 100%;
  height: 100%;
}

.globe-shell {
  position: relative;
}

.globe-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at center, rgba(0, 229, 255, 0.08) 0%, rgba(0, 229, 255, 0) 44%),
    rgba(2, 10, 22, 0.88);
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  letter-spacing: 0.08em;
}

.globe-mask.is-error {
  color: #ff9b9b;
}
</style>
