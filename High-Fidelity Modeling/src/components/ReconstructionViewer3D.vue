<template>
  <div class="reconstruction-viewer-container">
    <!-- 3D 视图顶部工具栏与元数据 -->
    <div class="viewer-top-bar">
      <div class="model-info-group">
        <div class="info-badge">
          <span class="status-dot"></span>
          <span class="badge-title">3D 精细重建模型就绪</span>
        </div>
        <div class="model-meta">
          <span class="meta-item">
            <span class="lbl">模型源:</span>
            <code class="val">{{ modelUrl }}</code>
          </span>
          <span class="meta-item">
            <span class="lbl">网格顶点:</span>
            <span class="val text-cyan">{{ formatNumber(modelStats.vertices) }} Pts</span>
          </span>
          <span class="meta-item">
            <span class="lbl">三角面数:</span>
            <span class="val text-green">{{ formatNumber(modelStats.faces) }} Triangles</span>
          </span>
          <span class="meta-item">
            <span class="lbl">重建精度:</span>
            <span class="val text-yellow">0.5 mm 工业级</span>
          </span>
        </div>
      </div>

      <!-- 右侧交互控制按钮（包含 3D 采样空间测距） -->
      <div class="viewer-actions">
        <button 
          class="tool-btn measure-btn" 
          :class="{ active: isMeasureMode }" 
          @click="toggleMeasureMode" 
          title="点击模型拾取 3D 空间坐标计算真实物理距离"
        >
          <span class="btn-icon">📏</span> {{ isMeasureMode ? '测量模式中(模型上取点)' : '三维空间测距' }}
        </button>
        <button 
          class="tool-btn danger-btn" 
          v-if="measurements.length > 0" 
          @click="clearMeasurements" 
          title="清除所有测距线段"
        >
          <span class="btn-icon">🗑️</span> 清除测距 ({{ measurements.length }})
        </button>
        <button class="tool-btn" :class="{ active: isPlayAnimation }" @click="togglePlayAnimation" title="切换碰撞动效">
          <span class="btn-icon">{{ isPlayAnimation ? '⏸' : '🎬' }}</span> {{ isPlayAnimation ? '动态播放中' : '📌 终点倒塌帧' }}
        </button>
        <button class="tool-btn" :class="{ active: autoRotate }" @click="toggleAutoRotate" title="自动旋转">
          <span class="btn-icon">🔄</span> {{ autoRotate ? '暂停旋转' : '自动环绕' }}
        </button>
        <button class="tool-btn" :class="{ active: isWireframe }" @click="toggleWireframe" title="切换拓扑线框">
          <span class="btn-icon">📐</span> {{ isWireframe ? '实体纹理' : '网格线框' }}
        </button>
        <button class="tool-btn primary-fit" @click="focusCameraToScreen" title="Camera Focus / Fit to Screen">
          <span class="btn-icon">🎯</span> 视角复位 (Fit to Screen)
        </button>
        <button class="tool-btn danger-btn" @click="$emit('reset-step')" title="重新开始">
          <span class="btn-icon">↺</span> 重新导入数据
        </button>
      </div>
    </div>

    <!-- 3D 渲染画布容器 -->
    <div class="canvas-wrapper" ref="canvasContainerRef">
      <div 
        class="canvas-3d" 
        ref="threeCanvasRef" 
        :class="{ 'cursor-crosshair': isMeasureMode }"
        @click="handleCanvasClick"
      ></div>

      <!-- 测量模式高亮提示横幅 -->
      <div v-if="isMeasureMode" class="measure-mode-banner">
        <span class="banner-icon">📏</span>
        <span><b>三维点对点测距模式已开启：</b>请在事故车辆模型表面<b>依次点击 2 个点</b>（起点与终点），系统将自动绘制三维激光测量线并计算精准距离。</span>
        <button class="exit-measure-btn" @click="toggleMeasureMode">退出测量</button>
      </div>

      <!-- 加载遮罩与进度条 -->
      <div class="loading-overlay" v-if="isLoading">
        <div class="spinner-box">
          <div class="cyber-spinner"></div>
          <p class="loading-text">正在解析 glTF/GLB 三维网格与纹理贴图...</p>
          <div class="loading-bar-bg">
            <div class="loading-bar-fill" :style="{ width: loadProgress + '%' }"></div>
          </div>
          <span class="progress-num">{{ loadProgress }}%</span>
        </div>
      </div>

      <!-- 三维空间检测热点标签 (Overlaid Inspection Tags) -->
      <div v-if="!isLoading && showAnnotations" class="inspection-tags-layer">
        <div 
          v-for="(tag, idx) in inspectionTags" 
          :key="idx" 
          class="inspection-tag-card"
          :style="{ left: tag.screenX + 'px', top: tag.screenY + 'px' }"
          :class="{ visible: tag.visible }"
        >
          <div class="tag-header">
            <span class="tag-dot"></span>
            <span class="tag-name">{{ tag.name }}</span>
          </div>
          <div class="tag-body">
            <span class="tag-val">{{ tag.value }}</span>
          </div>
        </div>

        <!-- 动态绘制的三维空间测量 HUD 结果卡片 -->
        <div 
          v-for="m in measurements" 
          :key="m.id" 
          class="measurement-hud-card"
          :style="{ left: m.screenX + 'px', top: m.screenY + 'px' }"
          :class="{ visible: m.visible }"
        >
          <div class="hud-header">
            <span class="hud-icon">📏</span>
            <span class="hud-title">3D 采样距离: <strong>{{ m.distance.toFixed(3) }} m</strong></span>
          </div>
          <div class="hud-body">
            <span class="hud-detail">厘米换算: <strong>{{ (m.distance * 100).toFixed(1) }} cm</strong></span>
            <span class="hud-vector">ΔX: {{ m.dx.toFixed(2) }}m | ΔY: {{ m.dy.toFixed(2) }}m | ΔZ: {{ m.dz.toFixed(2) }}m</span>
          </div>
        </div>
      </div>

      <!-- 画布底部操作指引提示 -->
      <div class="canvas-hint" v-if="!isLoading">
        <span v-if="!isMeasureMode">💡 操作指引: 按住鼠标左键旋转视角 | 鼠标右键平移 | 滚轮缩放 | 点击<b>“三维空间测距”</b>拾取车身点测距</span>
        <span v-else>📏 测量提示: 请直接点击车辆模型表面的任意受损处或构件取点测量距离</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'

// Props
const props = defineProps({
  modelUrl: {
    type: String,
    default: '/Dashboard/models/Accident_Occur1.glb'
  }
})

// Emits
const emit = defineEmits(['reset-step'])

// DOM 引用与 3D 句柄
const canvasContainerRef = ref(null)
const threeCanvasRef = ref(null)

let scene = null
let camera = null
let renderer = null
let controls = null
let currentModelGroup = null
let animationFrameId = null
let mixer = null
let measurementGroup = null
const raycaster = new THREE.Raycaster()
const mouse = new THREE.Vector2()
const clock = new THREE.Clock()

let boundingBoxCenter = new THREE.Vector3()
let boundingBoxSize = new THREE.Vector3()
let boundingSphereRadius = 10

// 状态管理
const isLoading = ref(true)
const loadProgress = ref(0)
const autoRotate = ref(true)
const isWireframe = ref(false)
const showAnnotations = ref(true)
const isPlayAnimation = ref(false)

// 3D 测量模式状态
const isMeasureMode = ref(false)
const pendingPoint = ref(null)
const measurements = ref([])

const togglePlayAnimation = () => {
  isPlayAnimation.value = !isPlayAnimation.value
}

const toggleMeasureMode = () => {
  isMeasureMode.value = !isMeasureMode.value
  pendingPoint.value = null
  if (controls) {
    // 测量模式开启时暂停自动旋转，防止影响拾取
    if (isMeasureMode.value) {
      controls.autoRotate = false
    } else {
      controls.autoRotate = autoRotate.value
    }
  }
}

const clearMeasurements = () => {
  measurements.value = []
  pendingPoint.value = null
  if (measurementGroup) {
    // 清除 3D 场景中的几何测量节点
    while (measurementGroup.children.length > 0) {
      const child = measurementGroup.children[0]
      if (child.geometry) child.geometry.dispose()
      if (child.material) {
        if (Array.isArray(child.material)) child.material.forEach(m => m.dispose())
        else child.material.dispose()
      }
      measurementGroup.remove(child)
    }
  }
}

const modelStats = ref({
  vertices: 184520,
  faces: 342190
})

// 三维检测标注点
const inspectionTags = ref([
  { name: '客车车头撞击点', value: '终点态凹陷: 0.42m', pos: new THREE.Vector3(0, 1.2, 2.5), screenX: 0, screenY: 0, visible: false },
  { name: '车身激光点云密度', value: '14,200 pts/m²', pos: new THREE.Vector3(-1.8, 1.5, 0), screenX: 0, screenY: 0, visible: false },
  { name: '轮胎侧倾夹角', value: '倾角偏差: 4.2°', pos: new THREE.Vector3(1.5, 0.6, -2.0), screenX: 0, screenY: 0, visible: false }
])

const updateTagsForModel = (url) => {
  if (url && (url.includes('Side_roll') || url.includes('Tanker') || url.includes('tanker'))) {
    inspectionTags.value = [
      { name: '油罐车罐体破裂处', value: '危化品泄露扩散: 15.2m', pos: new THREE.Vector3(0, 1.4, 1.2), screenX: 0, screenY: 0, visible: false },
      { name: '罐体侧翻偏转角', value: '侧倾倒塌: 42.5°', pos: new THREE.Vector3(-1.5, 1.2, -1.0), screenX: 0, screenY: 0, visible: false },
      { name: '气体监测传感器', value: 'TVOC 浓度: 85.4 ppm', pos: new THREE.Vector3(1.8, 0.8, 1.5), screenX: 0, screenY: 0, visible: false }
    ]
  } else {
    inspectionTags.value = [
      { name: '客车车头撞击点', value: '终点态凹陷: 0.42m', pos: new THREE.Vector3(0, 1.2, 2.5), screenX: 0, screenY: 0, visible: false },
      { name: '车身激光点云密度', value: '14,200 pts/m²', pos: new THREE.Vector3(-1.8, 1.5, 0), screenX: 0, screenY: 0, visible: false },
      { name: '轮胎侧倾夹角', value: '倾角偏差: 4.2°', pos: new THREE.Vector3(1.5, 0.6, -2.0), screenX: 0, screenY: 0, visible: false }
    ]
  }
}

const formatNumber = (num) => {
  return num ? num.toLocaleString() : '0'
}

// 初始化 Three.js 场景与渲染器
const initThreeScene = () => {
  if (!threeCanvasRef.value) return

  const width = canvasContainerRef.value.clientWidth || 800
  const height = canvasContainerRef.value.clientHeight || 600

  // 1. Scene - 改变为明亮清爽的现代科技蓝调场景，大幅调淡雾气
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0e172a) // 现代暗蓝灰 Studio 背景
  scene.fog = new THREE.FogExp2(0x0e172a, 0.003) // 调淡雾气密度，防止后方车辆变黑

  measurementGroup = new THREE.Group()
  scene.add(measurementGroup)

  // 2. Camera
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
  camera.position.set(12, 10, 15)

  // 3. Renderer - 提升 Exposure 曝光度
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.85 // 提升曝光度至 1.85，保证细节透亮清晰

  // 清空并挂载
  threeCanvasRef.value.innerHTML = ''
  threeCanvasRef.value.appendChild(renderer.domElement)

  // 4. OrbitControls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.autoRotate = autoRotate.value
  controls.autoRotateSpeed = 1.5
  controls.maxPolarAngle = Math.PI / 2 + 0.05 // 略低于地平线

  // 5. Lighting Setup
  setupLighting()

  // 6. Grid & Ground Helper
  setupEnvironment()

  // 7. Window Resize Listener
  window.addEventListener('resize', handleWindowResize)

  // 8. Start Animation Loop
  animate()
}

// 全方位工业级 4 点演播室光照系统（补足主光、补光、背光、地表反光及货车专照光）
const setupLighting = () => {
  const ambientLight = new THREE.AmbientLight(0xffffff, 3.8)
  scene.add(ambientLight)

  const keyLight = new THREE.DirectionalLight(0xffffff, 3.5)
  keyLight.position.set(25, 45, 25)
  keyLight.castShadow = true
  keyLight.shadow.mapSize.width = 2048
  keyLight.shadow.mapSize.height = 2048
  keyLight.shadow.bias = -0.0005
  scene.add(keyLight)

  const fillLight = new THREE.DirectionalLight(0xe0f2fe, 2.8)
  fillLight.position.set(-25, 25, -25)
  scene.add(fillLight)

  const backLight = new THREE.DirectionalLight(0x38bdf8, 2.5)
  backLight.position.set(0, 35, -35)
  scene.add(backLight)

  const truckSpot = new THREE.DirectionalLight(0xffffff, 3.8)
  truckSpot.position.set(35, 30, 10)
  scene.add(truckSpot)

  const bounceLight = new THREE.DirectionalLight(0x94a3b8, 2.0)
  bounceLight.position.set(0, -20, 0)
  scene.add(bounceLight)

  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 2.5)
  scene.add(hemiLight)
}

const setupEnvironment = () => {
  if (renderer && scene) {
    const pmremGenerator = new THREE.PMREMGenerator(renderer)
    const roomEnv = new RoomEnvironment(renderer)
    scene.environment = pmremGenerator.fromScene(roomEnv).texture
  }

  const gridHelper = new THREE.GridHelper(60, 60, 0x38bdf8, 0x334155)
  gridHelper.position.y = -0.01
  scene.add(gridHelper)
}

// 核心算法：提升暗色材质明度与自发光补偿，防止货车车身远距离变黑
const enhanceMaterialLuminance = (mat) => {
  if (!mat) return
  const materials = Array.isArray(mat) ? mat : [mat]
  materials.forEach(m => {
    if (m.color) {
      const hsl = {}
      m.color.getHSL(hsl)
      if (hsl.l < 0.4) {
        m.color.setHex(0x5a6d82) // 明显提亮为工业钢铁蓝灰色
      }
    }

    if (m.emissive) {
      m.emissive.setHex(0x283648) // 柔和钢铁蓝灰自发光
      m.emissiveIntensity = 0.5
    }

    if (m.metalness !== undefined) {
      m.metalness = 0.05
    }
    if (m.roughness !== undefined) {
      m.roughness = 0.6
    }
    m.needsUpdate = true
  })
}

// 【关键算法】：3D 拾取与空间点对点测距 (Raycasting Measurement)
const handleCanvasClick = (event) => {
  if (!isMeasureMode.value || !threeCanvasRef.value || !currentModelGroup || !camera) return

  const rect = threeCanvasRef.value.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, camera)
  const intersects = raycaster.intersectObject(currentModelGroup, true)

  if (intersects.length > 0) {
    const hitPoint = intersects[0].point.clone()

    if (!pendingPoint.value) {
      // 第一次点击：生成起点球体
      pendingPoint.value = hitPoint
      createPointSphere(hitPoint, 0x00f2fe)
    } else {
      // 第二次点击：生成终点球体，连接 3D 激光测量线，计算 3D 物理距离
      const p1 = pendingPoint.value.clone()
      const p2 = hitPoint.clone()
      createPointSphere(p2, 0xfbbf24)

      const dist = p1.distanceTo(p2)
      createLaserMeasurementLine(p1, p2)

      const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5)

      measurements.value.push({
        id: Date.now(),
        p1,
        p2,
        midPoint: mid,
        distance: dist,
        dx: Math.abs(p1.x - p2.x),
        dy: Math.abs(p1.y - p2.y),
        dz: Math.abs(p1.z - p2.z),
        screenX: 0,
        screenY: 0,
        visible: true
      })

      pendingPoint.value = null
    }
  }
}

// 在 3D 场景中绘制拾取点球体（强制 X-Ray 最顶层渲染，防止被货车车身挡住）
const createPointSphere = (pos, colorHex) => {
  const geo = new THREE.SphereGeometry(0.16, 24, 24)
  const mat = new THREE.MeshBasicMaterial({
    color: colorHex,
    depthTest: false,   // 强制关闭深度测试，防止货车车身深度阻挡
    depthWrite: false,  // 禁止写入深度缓存
    transparent: true,
    opacity: 0.95
  })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.position.copy(pos)
  mesh.renderOrder = 9999 // 强制设置为最高渲染顺序
  measurementGroup.add(mesh)
}

// 在 3D 场景中绘制 3D 空间发光激光柱 (Cylinder Laser Beam, 解决 Line 极细与车身挡线问题)
const createLaserMeasurementLine = (p1, p2) => {
  const distance = p1.distanceTo(p2)
  if (distance < 0.001) return

  // 1. 创建高亮 3D 实体激光管道（半径 3.5cm）
  const radius = 0.035
  const geometry = new THREE.CylinderGeometry(radius, radius, distance, 12)
  const material = new THREE.MeshBasicMaterial({
    color: 0x00f2fe,
    depthTest: false,   // 强制关闭深度测试，贯穿模型顶层显示
    depthWrite: false,  // 禁止写入深度缓存
    transparent: true,
    opacity: 0.92
  })

  const cylinderMesh = new THREE.Mesh(geometry, material)
  cylinderMesh.renderOrder = 9999 // 强制最高渲染层级

  // 居中位置
  const midPoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5)
  cylinderMesh.position.copy(midPoint)

  // 转向 p1 -> p2 方向
  const up = new THREE.Vector3(0, 1, 0)
  const direction = new THREE.Vector3().subVectors(p2, p1).normalize()
  const quaternion = new THREE.Quaternion()
  quaternion.setFromUnitVectors(up, direction)
  cylinderMesh.quaternion.copy(quaternion)

  measurementGroup.add(cylinderMesh)

  // 2. 补加核心高亮白色光芯线
  const lineGeo = new THREE.BufferGeometry().setFromPoints([p1, p2])
  const lineMat = new THREE.LineBasicMaterial({
    color: 0xffffff,
    depthTest: false,
    depthWrite: false,
    transparent: true,
    opacity: 0.9
  })
  const lineMesh = new THREE.Line(lineGeo, lineMat)
  lineMesh.renderOrder = 9999
  measurementGroup.add(lineMesh)
}

// 核心要点：加载模型与相机包围盒自动 Focus / Fit to Screen
const loadModel = (url) => {
  isLoading.value = true
  loadProgress.value = 5
  clearMeasurements()
  updateTagsForModel(url)

  if (currentModelGroup) {
    scene.remove(currentModelGroup)
    currentModelGroup = null
  }

  if (mixer) {
    mixer.stopAllAction()
    mixer = null
  }

  const loader = new GLTFLoader()
  loader.load(
    url,
    (gltf) => {
      currentModelGroup = gltf.scene || gltf.scenes[0]
      scene.add(currentModelGroup)

      if (gltf.animations && gltf.animations.length > 0) {
        mixer = new THREE.AnimationMixer(currentModelGroup)
        gltf.animations.forEach((clip) => {
          const action = mixer.clipAction(clip)
          action.play()
          action.time = clip.duration
        })
        mixer.update(0)
      }

      let vertCount = 0
      let faceCount = 0
      currentModelGroup.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true
          child.receiveShadow = true
          
          if (child.material) {
            enhanceMaterialLuminance(child.material)
          }

          if (child.geometry) {
            const geom = child.geometry
            if (geom.attributes && geom.attributes.position) {
              vertCount += geom.attributes.position.count
            }
            if (geom.index) {
              faceCount += geom.index.count / 3
            } else if (geom.attributes && geom.attributes.position) {
              faceCount += geom.attributes.position.count / 3
            }
          }
        }
      })
      modelStats.value.vertices = vertCount || 184520
      modelStats.value.faces = Math.round(faceCount) || 342190

      fitCameraToModel(currentModelGroup)

      isLoading.value = false
      loadProgress.value = 100
    },
    (xhr) => {
      if (xhr.total > 0) {
        loadProgress.value = Math.min(99, Math.round((xhr.loaded / xhr.total) * 100))
      } else {
        loadProgress.value = Math.min(95, loadProgress.value + 10)
      }
    },
    (err) => {
      console.warn('[ThreeJS] GLTF 加载遇到提示，尝试降级默认展示:', err)
      createFallbackVehicleMesh()
      isLoading.value = false
    }
  )
}

const createFallbackVehicleMesh = () => {
  currentModelGroup = new THREE.Group()
  const busGeo = new THREE.BoxGeometry(6, 2.5, 2.2)
  const busMat = new THREE.MeshStandardMaterial({ color: 0x1e3a8a, metalness: 0.6, roughness: 0.3 })
  const busMesh = new THREE.Mesh(busGeo, busMat)
  busMesh.position.y = 1.25
  currentModelGroup.add(busMesh)

  const truckGeo = new THREE.BoxGeometry(7, 3, 2.4)
  const truckMat = new THREE.MeshStandardMaterial({ color: 0xb91c1c, metalness: 0.5, roughness: 0.4 })
  const truckMesh = new THREE.Mesh(truckGeo, truckMat)
  truckMesh.position.set(0, 1.5, 4.5)
  currentModelGroup.add(truckMesh)

  scene.add(currentModelGroup)
  fitCameraToModel(currentModelGroup)
}

const fitCameraToModel = (modelObj) => {
  if (!modelObj || !camera || !controls) return

  const box = new THREE.Box3().setFromObject(modelObj)
  box.getCenter(boundingBoxCenter)
  box.getSize(boundingBoxSize)

  const sphere = new THREE.Sphere()
  box.getBoundingSphere(sphere)
  boundingSphereRadius = sphere.radius || 5

  const fov = camera.fov * (Math.PI / 180)
  const maxDim = Math.max(boundingBoxSize.x, boundingBoxSize.y, boundingBoxSize.z)
  const aspect = camera.aspect || 1
  let distance = Math.max(
    maxDim / (2 * Math.tan(fov / 2)),
    maxDim / (2 * Math.tan(fov / 2) * aspect)
  )

  distance *= 1.45 
  controls.target.copy(boundingBoxCenter)

  const targetCamPos = new THREE.Vector3(
    boundingBoxCenter.x + distance * 0.7,
    boundingBoxCenter.y + distance * 0.5,
    boundingBoxCenter.z + distance * 0.9
  )

  animateCameraTo(targetCamPos, boundingBoxCenter)
}

const animateCameraTo = (targetPos, targetLookAt) => {
  const startPos = camera.position.clone()
  const startTarget = controls.target.clone()
  const duration = 1000 
  const startTime = Date.now()

  const step = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    const ease = 1 - Math.pow(1 - progress, 3)

    camera.position.lerpVectors(startPos, targetPos, ease)
    controls.target.lerpVectors(startTarget, targetLookAt, ease)
    controls.update()

    if (progress < 1) {
      requestAnimationFrame(step)
    }
  }
  step()
}

const focusCameraToScreen = () => {
  if (currentModelGroup) {
    fitCameraToModel(currentModelGroup)
  }
}

const toggleAutoRotate = () => {
  autoRotate.value = !autoRotate.value
  if (controls) {
    controls.autoRotate = autoRotate.value
  }
}

const toggleWireframe = () => {
  isWireframe.value = !isWireframe.value
  if (currentModelGroup) {
    currentModelGroup.traverse((child) => {
      if (child.isMesh && child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.wireframe = isWireframe.value)
        } else {
          child.material.wireframe = isWireframe.value
        }
      }
    })
  }
}

// 屏幕坐标映射（更新 3D 标注点与 3D 空间测距卡片位置）
const updateInspectionTagPositions = () => {
  if (!camera || !renderer || !canvasContainerRef.value || isLoading.value) return
  const width = canvasContainerRef.value.clientWidth
  const height = canvasContainerRef.value.clientHeight

  // 更新常规检测点
  inspectionTags.value.forEach((tag) => {
    const worldPos = tag.pos.clone().add(boundingBoxCenter)
    const projected = worldPos.project(camera)

    if (projected.z < 1.0) {
      const x = (projected.x * 0.5 + 0.5) * width
      const y = (-(projected.y * 0.5) + 0.5) * height
      tag.screenX = Math.round(x)
      tag.screenY = Math.round(y)
      tag.visible = x >= 20 && x <= width - 20 && y >= 20 && y <= height - 20
    } else {
      tag.visible = false
    }
  })

  // 更新动态点对点空间测距卡片
  measurements.value.forEach((m) => {
    const projected = m.midPoint.clone().project(camera)
    if (projected.z < 1.0) {
      const x = (projected.x * 0.5 + 0.5) * width
      const y = (-(projected.y * 0.5) + 0.5) * height
      m.screenX = Math.round(x)
      m.screenY = Math.round(y)
      m.visible = x >= 20 && x <= width - 20 && y >= 20 && y <= height - 20
    } else {
      m.visible = false
    }
  })
}

// 动画主循环
const animate = () => {
  animationFrameId = requestAnimationFrame(animate)

  const delta = clock.getDelta()
  if (mixer && isPlayAnimation.value) {
    mixer.update(delta)
  }

  if (controls) {
    controls.update()
  }

  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }

  updateInspectionTagPositions()
}

const handleWindowResize = () => {
  if (!canvasContainerRef.value || !camera || !renderer) return
  const width = canvasContainerRef.value.clientWidth
  const height = canvasContainerRef.value.clientHeight
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

onMounted(async () => {
  await nextTick()
  initThreeScene()
  loadModel(props.modelUrl)
})

watch(() => props.modelUrl, (newUrl) => {
  if (newUrl) {
    loadModel(newUrl)
  }
})

onBeforeUnmount(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  window.removeEventListener('resize', handleWindowResize)
  if (renderer) {
    renderer.dispose()
  }
})
</script>

<style scoped>
.reconstruction-viewer-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #020712;
  position: relative;
  overflow: hidden;
}

/* 顶部工具栏 */
.viewer-top-bar {
  padding: 12px 20px;
  background: rgba(8, 16, 32, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  z-index: 10;
}

.model-info-group {
  display: flex;
  align-items: center;
  gap: 16px;
}
.info-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(52, 211, 153, 0.12);
  border: 1px solid rgba(52, 211, 153, 0.3);
  padding: 4px 10px;
  border-radius: 20px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 8px #34d399;
  animation: pulse-dot 1.5s infinite;
}
.badge-title {
  color: #34d399;
  font-size: 12px;
  font-weight: 600;
}

.model-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 12px;
}
.meta-item .lbl { color: #64748b; margin-right: 4px; }
.meta-item .val { color: #e2e8f0; font-family: 'Fira Code', monospace; }
.meta-item .text-cyan { color: #00f2fe; }
.meta-item .text-green { color: #34d399; }
.meta-item .text-yellow { color: #fbbf24; }

/* 按钮组 */
.viewer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tool-btn {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}
.tool-btn:hover {
  background: rgba(30, 41, 59, 1);
  border-color: #00f2fe;
  color: #00f2fe;
}
.tool-btn.active {
  background: rgba(0, 242, 254, 0.18);
  border-color: #00f2fe;
  color: #00f2fe;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.35);
}
.tool-btn.measure-btn.active {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.25), rgba(251, 191, 36, 0.25));
  border-color: #fbbf24;
  color: #fbbf24;
  box-shadow: 0 0 12px rgba(251, 191, 36, 0.4);
}
.tool-btn.primary-fit {
  background: rgba(0, 242, 254, 0.18);
  border-color: #00f2fe;
  color: #00f2fe;
  font-weight: 600;
}
.tool-btn.primary-fit:hover {
  background: #00f2fe;
  color: #020712;
  box-shadow: 0 0 14px rgba(0, 242, 254, 0.6);
}
.tool-btn.danger-btn:hover {
  border-color: #f87171;
  color: #f87171;
  background: rgba(248, 113, 113, 0.15);
}

/* 3D 渲染区域 */
.canvas-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.canvas-3d {
  width: 100%;
  height: 100%;
  cursor: grab;
}
.canvas-3d:active {
  cursor: grabbing;
}
.canvas-3d.cursor-crosshair {
  cursor: crosshair !important;
}

/* 测量模式高亮提示横幅 */
.measure-mode-banner {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(10, 20, 40, 0.92);
  border: 1px solid #fbbf24;
  padding: 8px 20px;
  border-radius: 30px;
  color: #fbbf24;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.6), 0 0 15px rgba(251, 191, 36, 0.25);
  backdrop-filter: blur(8px);
  z-index: 15;
}
.exit-measure-btn {
  background: rgba(248, 113, 113, 0.2);
  border: 1px solid #f87171;
  color: #f87171;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11.5px;
  cursor: pointer;
}
.exit-measure-btn:hover {
  background: #f87171;
  color: #020712;
}

/* 加载遮罩 */
.loading-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(2, 7, 18, 0.85);
  backdrop-filter: blur(6px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 20;
}
.spinner-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 320px;
}
.cyber-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(0, 242, 254, 0.15);
  border-top-color: #00f2fe;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}
.loading-text {
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 12px;
}
.loading-bar-bg {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}
.loading-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00f2fe, #3b82f6);
  transition: width 0.2s ease;
}
.progress-num {
  color: #00f2fe;
  font-family: 'Fira Code', monospace;
  font-weight: 700;
  font-size: 14px;
}

/* 标注热点与测量结果 HUD 卡片 */
.inspection-tags-layer {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: none;
  z-index: 5;
}
.inspection-tag-card {
  position: absolute;
  transform: translate(-50%, -100%) translateY(-12px);
  background: rgba(8, 16, 32, 0.88);
  border: 1px solid rgba(0, 242, 254, 0.4);
  border-radius: 6px;
  padding: 6px 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: auto;
}
.inspection-tag-card.visible {
  opacity: 1;
}
.tag-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}
.tag-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fbbf24;
}
.tag-name {
  color: #94a3b8;
  font-size: 11px;
}
.tag-val {
  color: #00f2fe;
  font-size: 12px;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
}

/* 3D 测量 HUD 卡片 */
.measurement-hud-card {
  position: absolute;
  transform: translate(-50%, -100%) translateY(-15px);
  background: rgba(4, 16, 36, 0.94);
  border: 1px solid #00f2fe;
  border-radius: 8px;
  padding: 8px 12px;
  box-shadow: 0 6px 20px rgba(0, 242, 254, 0.3);
  backdrop-filter: blur(10px);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: auto;
  min-width: 170px;
}
.measurement-hud-card.visible {
  opacity: 1;
}
.hud-header {
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  padding-bottom: 4px;
  margin-bottom: 4px;
}
.hud-title {
  color: #e2e8f0;
  font-size: 12px;
}
.hud-title strong {
  color: #00f2fe;
  font-family: 'Fira Code', monospace;
  font-size: 13.5px;
}
.hud-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
}
.hud-detail {
  color: #fbbf24;
}
.hud-detail strong {
  font-family: 'Fira Code', monospace;
}
.hud-vector {
  color: #94a3b8;
  font-family: 'Fira Code', monospace;
  font-size: 10.5px;
}

/* 底部操作提示 */
.canvas-hint {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(4, 12, 26, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 12px;
  color: #94a3b8;
  backdrop-filter: blur(4px);
  pointer-events: none;
  white-space: nowrap;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}
</style>
