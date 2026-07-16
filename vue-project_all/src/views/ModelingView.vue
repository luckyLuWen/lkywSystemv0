<template>
  <div class="modeling-page-wrapper">
    <!-- Top Header Bar -->
    <header class="modeling-header">
      <div class="header-left">
        <button class="back-btn" @click="goHome">
          <span class="btn-icon">←</span> 返回首页大屏
        </button>
        <div class="header-title-group">
          <h1>精细三维建模系统</h1>
          <span class="sub-title">Fine-grained 3D Modeling Inspector</span>
        </div>
      </div>
      <div class="header-right">
        <div class="status-indicator">
          <span class="status-dot pulse"></span>
          <span class="status-text">三维引擎: Web3D ModelViewer (已加载)</span>
        </div>
      </div>
    </header>

    <div class="modeling-main-layout">
      <!-- Left Sidebar: Scene Switcher & Metadata -->
      <aside class="sidebar left-sidebar">
        <!-- Section: Scene Switcher -->
        <div class="panel-section">
          <div class="section-header">
            <span class="section-icon">🌐</span>
            <h3>选择精细建模场景</h3>
          </div>
          <div class="scene-cards-container">
            <div 
              v-for="scene in sceneConfigs" 
              :key="scene.key"
              class="scene-card"
              :class="{ active: activeTab === scene.key }"
              @click="switchScene(scene.key)"
            >
              <div class="scene-card-info">
                <h4>{{ scene.label }}</h4>
                <p>{{ scene.location }}</p>
              </div>
              <div class="active-indicator" v-if="activeTab === scene.key"></div>
            </div>
          </div>
        </div>

        <!-- Section: Model Metadata -->
        <div class="panel-section flex-1">
          <div class="section-header">
            <span class="section-icon">📊</span>
            <h3>模型元数据 (文件真实数据)</h3>
          </div>
          <div class="metadata-grid" v-if="parsedMetadata">
            <div class="meta-item">
              <span class="meta-label">模型文件名</span>
              <span class="meta-value highlight">{{ parsedMetadata.fileName }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">文件大小</span>
              <span class="meta-value">{{ parsedMetadata.fileSize }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">规格版本</span>
              <span class="meta-value text-teal">{{ parsedMetadata.version }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">导出工具</span>
              <span class="meta-value">{{ parsedMetadata.generator }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">三角面数</span>
              <span class="meta-value highlight">{{ parsedMetadata.triangles }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">顶点数量</span>
              <span class="meta-value">{{ parsedMetadata.vertices }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">贴图数量</span>
              <span class="meta-value">{{ parsedMetadata.textures }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">材质数量</span>
              <span class="meta-value">{{ parsedMetadata.materials }}</span>
            </div>
          </div>
          <div class="loading-metadata" v-else>
            <span class="pulse-icon loading-spin">⏳</span> 正在读取并分析三维文件信息...
          </div>
        </div>
      </aside>

      <!-- Center: 3D Viewport -->
      <main class="center-viewport">
        <!-- Grid overlay & Model Viewer container -->
        <div class="cesium-container-wrapper">
          <div class="radar-bg-grid"></div>
          
          <model-viewer
            v-if="scriptLoaded"
            ref="modelViewerRef"
            autoplay
            :src="currentModel.uri"
            camera-controls
            interaction-prompt="none"
            :auto-rotate="autoRotate"
            :auto-rotate-delay="0"
            :rotation-speed="rotateSpeed + 'deg'"
            :camera-orbit="cameraOrbit"
            :camera-target="cameraTarget"
            shadow-intensity="1.5"
            shadow-softness="0.8"
            environment-image="neutral"
            :exposure="exposure"
            @load="onModelLoad"
            style="width: 100%; height: 100%; background: transparent;"
          >
            <!-- Interactive 3D Hotspots on Model Surface -->
            <button 
              v-for="item in activeHotspots" 
              :key="item.id"
              class="hotspot-pin"
              :slot="'hotspot-' + item.id"
              :data-position="item.position"
              :data-normal="item.normal"
              :class="{ active: selectedHotspotId === item.id }"
              @click="selectHotspot(item)"
            >
              <div class="hotspot-dot"></div>
              <div class="hotspot-tooltip">{{ item.label }}</div>
            </button>
          </model-viewer>
        </div>

        <!-- Float Overlay: Controls Overlay -->
        <div class="viewport-hud-bottom">
          <div class="control-group">
            <button 
              class="control-btn" 
              :class="{ active: autoRotate }"
              @click="toggleAutoRotate"
              title="开启/关闭视角自动环绕"
            >
              {{ autoRotate ? '环绕中' : '自动环绕' }}
            </button>
          </div>
          
          <!-- Animation playback controls if the model has animations -->
          <div class="control-divider" v-if="hasAnimation"></div>
          <div class="control-group" v-if="hasAnimation">
            <button 
              class="control-btn anim-action-btn" 
              :class="{ active: !isFrozen }"
              @click="playCollisionAnimation"
              :title="activeTab === 'truck' ? '重播撞击动画' : '重播侧翻动画'"
            >
              {{ activeTab === 'truck' ? '播放相撞过程' : '播放侧翻过程' }}
            </button>
            <button 
              class="control-btn anim-action-btn" 
              :class="{ active: isFrozen }"
              @click="freezeLastFrame"
              title="定格最终状态"
            >
              {{ activeTab === 'truck' ? '定格倒塌状态' : '定格侧翻状态' }}
            </button>
          </div>
          
          <div class="control-divider"></div>
          <div class="control-group">
            <span class="control-label">环绕速度</span>
            <input 
              type="range" 
              min="0.5" 
              max="4" 
              step="0.5" 
              v-model.number="rotateSpeed" 
              class="slider"
            />
          </div>
        </div>
      </main>

      <!-- Right Sidebar: Interactive Controls & Hotspots -->
      <aside class="sidebar right-sidebar">
        <!-- Section: View Settings -->
        <div class="panel-section">
          <div class="section-header">
            <span class="section-icon">🛠</span>
            <h3>显示设置 (Viewer Settings)</h3>
          </div>
          <div class="setting-item">
            <span class="setting-label">环境光强度 (Exposure)</span>
            <input 
              type="range" 
              min="0.4" 
              max="2.0" 
              step="0.1" 
              v-model.number="exposure" 
              class="slider-full"
            />
          </div>
          <p class="mode-description">
            实验室精细分析模式：已过滤外部地理底图，提供统一棚拍式无偏光源，辅助三维构件形变深度与破损裂隙的视觉定量分析。
          </p>
        </div>

        <!-- Section: Detail Hotspots -->
        <div class="panel-section flex-1">
          <div class="section-header">
            <span class="section-icon">🔍</span>
            <h3>高精细细节检查 (Hotspots)</h3>
          </div>
          <div class="hotspots-list">
            <div 
              v-for="item in activeHotspots" 
              :key="item.id"
              class="hotspot-item"
              :class="{ active: selectedHotspotId === item.id }"
              @click="selectHotspot(item)"
            >
              <div class="hotspot-header">
                <span class="hotspot-tag">{{ item.tag }}</span>
                <h4>{{ item.label }}</h4>
              </div>
              <p class="hotspot-desc">{{ item.desc }}</p>
              <div class="click-to-fly">查看定位 🔎</div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const goHome = () => {
  router.push('/')
}

// Scene Configurations
const sceneConfigs = {
  truck: {
    key: 'truck',
    label: '货车追尾事件',
    location: '三维扫描现场重建',
    icon: '🚛',
    uri: '/Dashboard/models/Accident_Occur1.glb'
  },
  tanker: {
    key: 'tanker',
    label: '油罐车泄露事件',
    location: '三维扫描现场重建',
    icon: '⛽',
    uri: '/Dashboard/models/Side_roll_Tanker.glb'
  }
}

// Hotspots list with precise surface placements and orbit targets
const truckHotspots = [
  {
    id: 'cabin_impact',
    label: '车头撞击受损点',
    tag: 'Zone A',
    desc: '货车驾驶室前半部在高速冲撞下产生向内溃缩，A柱严重弯折，形变深度达1.2米。',
    position: '0.2m 1.3m 3.3m',
    normal: '0m 0.2m 1m',
    cameraOrbit: '40deg 75deg 4.5m',
    cameraTarget: '0.2m 1.3m 3.3m'
  },
  {
    id: 'chassis_beam',
    label: '防撞钢梁形变',
    tag: 'Zone B',
    desc: '前防撞梁中段凹陷开裂，吸能盒吸能完全，两侧车架大梁轻微扭曲。',
    position: '0m 0.5m 3.7m',
    normal: '0m -0.1m 1m',
    cameraOrbit: '15deg 85deg 3m',
    cameraTarget: '0m 0.5m 3.7m'
  },
  {
    id: 'rear_impact',
    label: '后侧挂车追尾面',
    tag: 'Zone C',
    desc: '被追尾挂车防撞网完全断裂，车尾大梁右侧开裂弯曲，钣金表面凹坑深度达24cm。',
    position: '0m 1.0m -3.2m',
    normal: '0m 0.1m -1m',
    cameraOrbit: '195deg 75deg 4.5m',
    cameraTarget: '0m 1.0m -3.2m'
  }
]

const tankerHotspots = [
  {
    id: 'leak_valve',
    label: '破损泄露法兰阀',
    tag: 'Zone A',
    desc: '罐体后侧下排料阀法兰处破裂，阀门把手变形断裂，液体沿罐体表面流淌。',
    position: '0m 0.7m -4.0m',
    normal: '0m 0m -1m',
    cameraOrbit: '170deg 78deg 3.5m',
    cameraTarget: '0m 0.7m -4.0m'
  },
  {
    id: 'support_point',
    label: '侧翻受力支撑点',
    tag: 'Zone B',
    desc: '罐体与护栏撞击受压支撑面，防波板焊缝受力挤压局部产生2mm微裂纹。',
    position: '-1.1m 0.4m 0.5m',
    normal: '-1m 0m 0.2m',
    cameraOrbit: '-110deg 82deg 3.8m',
    cameraTarget: '-1.1m 0.4m 0.5m'
  },
  {
    id: 'tank_seam',
    label: '罐体防波板焊缝',
    tag: 'Zone C',
    desc: '中后段焊缝表面漆层剥落，超声波检测显示内部受撞击拉力延伸变形1.8%。',
    position: '0m 1.8m 1.0m',
    normal: '0m 1m 0m',
    cameraOrbit: '45deg 55deg 4.5m',
    cameraTarget: '0m 1.8m 1.0m'
  }
]

// State vars
const activeTab = ref('truck')
const autoRotate = ref(true)
const rotateSpeed = ref(1.5)
const exposure = ref(1.1)
const selectedHotspotId = ref(null)
const scriptLoaded = ref(false)

const cameraOrbit = ref('45deg 75deg auto')
const cameraTarget = ref('auto auto auto')

const currentModel = computed(() => sceneConfigs[activeTab.value])
const activeHotspots = computed(() => activeTab.value === 'truck' ? truckHotspots : tankerHotspots)

// Real Dynamic Metadata States
const parsedMetadata = ref(null)

// Animation Control States
const modelViewerRef = ref(null)
const hasAnimation = ref(false)
const isFrozen = ref(true)

// Dynamic GLB Parser function
const parseGlbMetadata = async (url) => {
  const response = await fetch(url)
  if (!response.ok) throw new Error('Fetch model failed')

  const arrayBuffer = await response.arrayBuffer()
  const byteLength = arrayBuffer.byteLength
  const sizeMB = (byteLength / (1024 * 1024)).toFixed(2) + ' MB'

  const dataView = new DataView(arrayBuffer)
  const magicBytes = new Uint8Array(arrayBuffer, 0, 4)
  const magicStr = new TextDecoder('utf-8').decode(magicBytes)
  if (magicStr !== 'glTF') {
    throw new Error('Invalid GLB magic: ' + magicStr)
  }

  const chunkLength = dataView.getUint32(12, true)
  const chunkTypeBytes = new Uint8Array(arrayBuffer, 16, 4)
  const chunkTypeStr = new TextDecoder('utf-8').decode(chunkTypeBytes)
  if (chunkTypeStr !== 'JSON') {
    throw new Error('GLB chunk 0 is not JSON: ' + chunkTypeStr)
  }

  const jsonBytes = new Uint8Array(arrayBuffer, 20, chunkLength)
  const decoder = new TextDecoder('utf-8')
  const jsonStr = decoder.decode(jsonBytes)
  const gltf = JSON.parse(jsonStr)

  let vertices = 0
  let triangles = 0

  if (gltf.accessors && gltf.meshes) {
    gltf.meshes.forEach(mesh => {
      if (mesh.primitives) {
        mesh.primitives.forEach(prim => {
          if (prim.attributes && prim.attributes.POSITION !== undefined) {
            const accessor = gltf.accessors[prim.attributes.POSITION]
            if (accessor) {
              vertices += accessor.count
            }
          }
          if (prim.indices !== undefined) {
            const accessor = gltf.accessors[prim.indices]
            if (accessor) {
              triangles += Math.floor(accessor.count / 3)
            }
          } else if (prim.attributes && prim.attributes.POSITION !== undefined) {
            const accessor = gltf.accessors[prim.attributes.POSITION]
            if (accessor) {
              triangles += Math.floor(accessor.count / 3)
            }
          }
        })
      }
    })
  }

  const texturesCount = gltf.textures ? gltf.textures.length : 0
  const materialsCount = gltf.materials ? gltf.materials.length : 0
  const generator = gltf.asset && gltf.asset.generator ? gltf.asset.generator : 'Generic Exporter'
  const version = gltf.asset && gltf.asset.version ? `glTF v${gltf.asset.version}` : 'glTF v2.0'

  return {
    fileName: url.substring(url.lastIndexOf('/') + 1),
    fileSize: sizeMB,
    version,
    generator,
    vertices: vertices.toLocaleString(),
    triangles: triangles.toLocaleString(),
    textures: texturesCount + ' 个',
    materials: materialsCount + ' 个'
  }
}

const loadMetadata = async () => {
  parsedMetadata.value = null
  try {
    const meta = await parseGlbMetadata(currentModel.value.uri)
    parsedMetadata.value = meta
  } catch (error) {
    console.error('Failed parsing GLB metadata:', error)
    parsedMetadata.value = {
      fileName: currentModel.value.uri.substring(currentModel.value.uri.lastIndexOf('/') + 1),
      fileSize: '读取错误',
      version: 'glTF v2.0',
      generator: '未知',
      vertices: '读取错误',
      triangles: '读取错误',
      textures: '未知',
      materials: '未知'
    }
  }
}

// Load Google Model Viewer dynamically
const loadModelViewerScript = () => {
  if (window.customElements && window.customElements.get('model-viewer')) {
    scriptLoaded.value = true
    return
  }

  const scriptId = 'model-viewer-web-component-script'
  if (document.getElementById(scriptId)) {
    scriptLoaded.value = true
    return
  }

  const script = document.createElement('script')
  script.id = scriptId
  script.type = 'module'
  script.src = 'https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js'
  script.onload = () => {
    scriptLoaded.value = true
  }
  script.onerror = () => {
    console.error('Failed to load <model-viewer> component library.')
  }
  document.head.appendChild(script)
  
  // Backup timeout activation
  setTimeout(() => {
    scriptLoaded.value = true
  }, 1000)
}

// Reset Camera Focus
const resetCamera = () => {
  selectedHotspotId.value = null
  cameraOrbit.value = '45deg 75deg auto'
  cameraTarget.value = 'auto auto auto'
  autoRotate.value = true
}

// Switch Scenes (Truck <-> Tanker)
const switchScene = (key) => {
  activeTab.value = key
  hasAnimation.value = false
  isFrozen.value = true
  resetCamera()
  loadMetadata()
}

// Select/Focus Hotspot
const selectHotspot = (item) => {
  selectedHotspotId.value = item.id
  autoRotate.value = false
  cameraOrbit.value = item.cameraOrbit
  cameraTarget.value = item.cameraTarget
}

// Toggle Auto Rotate
const toggleAutoRotate = () => {
  autoRotate.value = !autoRotate.value
}

// Model Load Handler
const onModelLoad = () => {
  const modelViewer = modelViewerRef.value
  if (!modelViewer) return

  const animations = modelViewer.availableAnimations
  if (animations && animations.length > 0) {
    hasAnimation.value = true
    modelViewer.animationName = animations[0]
    
    // Auto freeze at the last frame
    freezeLastFrame()
  } else {
    hasAnimation.value = false
  }
}

// Freeze at the last frame of the animation
const freezeLastFrame = () => {
  const modelViewer = modelViewerRef.value
  if (!modelViewer) return

  isFrozen.value = true
  if (trackingFrameId) {
    cancelAnimationFrame(trackingFrameId)
    trackingFrameId = null
  }
  
  // Poll until duration is populated, then set currentTime to duration and pause
  let attempts = 0
  const maxAttempts = 30
  const tryFreeze = () => {
    if (modelViewer.duration > 0) {
      modelViewer.currentTime = modelViewer.duration
      modelViewer.pause()
      
      // Update camera target dynamically to the end state
      const sceneSymbol = Object.getOwnPropertySymbols(modelViewer)
        .find(symbol => symbol.description === 'scene')
      const scene = sceneSymbol ? modelViewer[sceneSymbol] : null
      
      let trackNodes = []
      if (scene) {
        scene.traverse(node => {
          if (node.name === 'Object_3' || node.name === '货车' || node.name === '大巴车') {
            trackNodes.push(node)
          }
        })
        if (trackNodes.length === 0) {
          scene.traverse(node => {
            if (node.isMesh && trackNodes.length === 0) {
              trackNodes.push(node)
            }
          })
        }
      }
      
      if (trackNodes.length > 0) {
        let sumX = 0, sumY = 0, sumZ = 0
        trackNodes.forEach(node => {
          node.updateMatrixWorld(true)
          const elements = node.matrixWorld.elements
          sumX += elements[12]
          sumY += elements[13]
          sumZ += elements[14]
        })
        const x = sumX / trackNodes.length
        const yOffset = activeTab.value === 'tanker' ? 1.0 : 1.2
        const y = (sumY / trackNodes.length) + yOffset
        const z = sumZ / trackNodes.length
        
        const targetStr = `${x.toFixed(2)}m ${y.toFixed(2)}m ${z.toFixed(2)}m`
        
        // Restore smooth decay for user interaction when frozen
        modelViewer.interpolationDecay = 100
        cameraTarget.value = targetStr
        modelViewer.cameraTarget = targetStr
        modelViewer.jumpCameraToGoal()
      }
      
      console.log('[ModelViewer] Successfully frozen at last frame:', modelViewer.duration, 's')
    } else if (attempts < maxAttempts) {
      attempts++
      setTimeout(tryFreeze, 100)
    }
  }
  tryFreeze()
}

// Play animation once
let trackingFrameId = null
const playCollisionAnimation = () => {
  const modelViewer = modelViewerRef.value
  if (!modelViewer) return

  isFrozen.value = false
  modelViewer.currentTime = 0
  
  // Set decay to 0 during playback to snap instantly to computed node coordinates without lag/decay fighting
  modelViewer.interpolationDecay = 0
  modelViewer.play({ repetitions: 1 })

  // Find the scene and nodes to track
  const sceneSymbol = Object.getOwnPropertySymbols(modelViewer)
    .find(symbol => symbol.description === 'scene')
  const scene = sceneSymbol ? modelViewer[sceneSymbol] : null

  let trackNodes = []
  if (scene) {
    scene.traverse(node => {
      if (node.name === 'Object_3' || node.name === '货车' || node.name === '大巴车') {
        trackNodes.push(node)
      }
    })
    if (trackNodes.length === 0) {
      scene.traverse(node => {
        if (node.isMesh && trackNodes.length === 0) {
          trackNodes.push(node)
        }
      })
    }
  }

  // Camera smooth follow variables to filter out frame-rate jitter
  let smoothX = 0
  let smoothY = 0
  let smoothZ = 0
  let hasInitialized = false

  const updateCameraTracking = () => {
    if (!modelViewer || isFrozen.value) return

    if (trackNodes.length > 0) {
      try {
        let sumX = 0, sumY = 0, sumZ = 0
        trackNodes.forEach(node => {
          node.updateMatrixWorld(true)
          const elements = node.matrixWorld.elements
          if (elements && elements.length >= 16) {
            sumX += elements[12]
            sumY += elements[13]
            sumZ += elements[14]
          }
        })
        const targetX = sumX / trackNodes.length
        const yOffset = activeTab.value === 'tanker' ? 1.0 : 1.2
        const targetY = (sumY / trackNodes.length) + yOffset
        const targetZ = sumZ / trackNodes.length
        
        if (!hasInitialized) {
          smoothX = targetX
          smoothY = targetY
          smoothZ = targetZ
          hasInitialized = true
        } else {
          // Lerp factor of 0.2 filters out high-frequency 60fps frame jitter
          const lerpFactor = 0.2
          smoothX += (targetX - smoothX) * lerpFactor
          smoothY += (targetY - smoothY) * lerpFactor
          smoothZ += (targetZ - smoothZ) * lerpFactor
        }
        
        const targetStr = `${smoothX.toFixed(2)}m ${smoothY.toFixed(2)}m ${smoothZ.toFixed(2)}m`
        
        // Write directly to the DOM element property to bypass Vue's asynchronous updates.
        // We DO NOT update cameraTarget.value here to keep Vue completely quiet during playback.
        modelViewer.cameraTarget = targetStr
        modelViewer.jumpCameraToGoal()
      } catch (err) {
        // ignore frame errors
      }
    }

    const duration = modelViewer.duration || 4.0
    const progress = Math.min(modelViewer.currentTime / duration, 1.0)
    if (progress < 1.0 && !isFrozen.value) {
      trackingFrameId = requestAnimationFrame(updateCameraTracking)
    }
  }

  if (trackingFrameId) cancelAnimationFrame(trackingFrameId)
  trackingFrameId = requestAnimationFrame(updateCameraTracking)

  // Auto set isFrozen to true when the animation finishes
  const onFinished = () => {
    isFrozen.value = true
    if (trackingFrameId) {
      cancelAnimationFrame(trackingFrameId)
      trackingFrameId = null
    }
    // Restore smooth decay for normal manual orbiting
    modelViewer.interpolationDecay = 100
    
    // Snap to the final position on finished and sync Vue reactive ref once
    if (trackNodes.length > 0) {
      let sumX = 0, sumY = 0, sumZ = 0
      trackNodes.forEach(node => {
        node.updateMatrixWorld(true)
        const elements = node.matrixWorld.elements
        sumX += elements[12]
        sumY += elements[13]
        sumZ += elements[14]
      })
      const x = sumX / trackNodes.length
      const yOffset = activeTab.value === 'tanker' ? 1.0 : 1.2
      const y = (sumY / trackNodes.length) + yOffset
      const z = sumZ / trackNodes.length
      
      const targetStr = `${x.toFixed(2)}m ${y.toFixed(2)}m ${z.toFixed(2)}m`
      cameraTarget.value = targetStr
      modelViewer.cameraTarget = targetStr
      modelViewer.jumpCameraToGoal()
    }
    modelViewer.removeEventListener('finished', onFinished)
  }
  modelViewer.addEventListener('finished', onFinished)
}

onMounted(() => {
  loadModelViewerScript()
  loadMetadata()
})
</script>

<style scoped>
.modeling-page-wrapper {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #020710;
  color: #e2e8f0;
  font-family: 'Outfit', 'Inter', -apple-system, sans-serif;
  overflow: hidden;
}

/* Header */
.modeling-header {
  height: 70px;
  min-height: 70px;
  background: rgba(4, 12, 26, 0.7);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.back-btn {
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.35);
  border-radius: 8px;
  padding: 8px 16px;
  color: #00f2fe;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.back-btn:hover {
  background: rgba(0, 229, 255, 0.18);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.25);
  transform: translateX(-2px);
}

.header-title-group h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #ffffff;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.sub-title {
  font-size: 11px;
  color: rgba(0, 229, 255, 0.7);
  text-transform: uppercase;
  letter-spacing: 1.5px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(7, 20, 38, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 20px;
  padding: 6px 14px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #00ffd8;
  box-shadow: 0 0 8px #00ffd8;
}

.status-dot.pulse {
  animation: pulse-glow 2s infinite;
}

.status-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
}

/* Main Layout */
.modeling-main-layout {
  flex: 1;
  display: flex;
  padding: 16px;
  gap: 16px;
  height: calc(100vh - 70px);
  box-sizing: border-box;
}

.sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-section {
  background: rgba(4, 14, 28, 0.75);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  box-shadow: inset 0 0 15px rgba(0, 229, 255, 0.03);
}

.flex-1 {
  flex: 1;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
  padding-bottom: 8px;
}

.section-icon {
  font-size: 18px;
}

.section-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #00ffd8;
  letter-spacing: 0.5px;
}

/* Scene Cards */
.scene-cards-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.scene-card {
  position: relative;
  background: rgba(2, 10, 20, 0.5);
  border: 1px solid rgba(0, 229, 255, 0.12);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.scene-card:hover {
  background: rgba(0, 229, 255, 0.05);
  border-color: rgba(0, 229, 255, 0.3);
  transform: translateY(-2px);
}

.scene-card.active {
  background: rgba(0, 229, 255, 0.1);
  border-color: #00f2fe;
  box-shadow: 0 4px 15px rgba(0, 242, 254, 0.15);
}

.scene-card-icon {
  font-size: 24px;
}

.scene-card-info h4 {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.scene-card-info p {
  margin: 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.active-indicator {
  position: absolute;
  left: 0;
  top: 15%;
  height: 70%;
  width: 3px;
  background-color: #00ffd8;
  border-radius: 0 4px 4px 0;
  box-shadow: 0 0 8px #00ffd8;
}

/* Metadata */
.metadata-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  overflow-y: auto;
}

.meta-item {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.meta-value {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  text-align: right;
}

.meta-value.highlight {
  color: #00f2fe;
}

.meta-value.text-teal {
  color: #00ffd8;
}

.loading-metadata {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  padding: 40px 0;
}

.loading-spin {
  display: inline-block;
  animation: float 2s infinite ease-in-out;
}

/* Viewport Center */
.center-viewport {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  border-radius: 12px;
  border: 1px solid rgba(0, 229, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  background: #020914;
}

.cesium-container-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

/* Circular Radar/Grid Styling for Web3D inspect base */
.radar-bg-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at center, transparent 30%, rgba(2, 9, 20, 0.95) 75%),
    radial-gradient(circle at center, rgba(0, 229, 255, 0.07) 1px, transparent 1px),
    linear-gradient(to right, rgba(0, 229, 255, 0.03) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(0, 229, 255, 0.03) 1px, transparent 1px);
  background-size: 100% 100%, 30px 30px, 30px 30px, 30px 30px;
  background-position: center;
  pointer-events: none;
}

.viewport-hud-bottom {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(3, 11, 23, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 30px;
  padding: 8px 24px;
  display: flex;
  align-items: center;
  gap: 18px;
  z-index: 10;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.control-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 12px;
  color: #e2e8f0;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.control-btn:hover {
  background: rgba(0, 229, 255, 0.12);
  border-color: rgba(0, 229, 255, 0.4);
  color: #00ffd8;
}

.control-btn.active {
  background: rgba(0, 229, 255, 0.18);
  border-color: #00f2fe;
  color: #ffffff;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.anim-action-btn.active {
  background: rgba(0, 255, 216, 0.15) !important;
  border-color: #00ffd8 !important;
  color: #ffffff !important;
  box-shadow: 0 0 10px rgba(0, 255, 216, 0.2);
}

.control-divider {
  width: 1px;
  height: 18px;
  background: rgba(255, 255, 255, 0.15);
}

.control-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.slider {
  -webkit-appearance: none;
  width: 80px;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.15);
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #00ffd8;
  cursor: pointer;
  box-shadow: 0 0 6px #00ffd8;
  transition: transform 0.1s ease;
}

.slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

/* Right side Settings */
.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.setting-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.slider-full {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.15);
  outline: none;
}

.slider-full::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #00ffd8;
  cursor: pointer;
  box-shadow: 0 0 6px #00ffd8;
}

.mode-description {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.6;
  margin: 10px 0 0;
  text-align: justify;
}

/* Hotspots on model-viewer */
.hotspot-pin {
  background: rgba(0, 255, 216, 0.22);
  border: 2px solid #00ffd8;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  cursor: pointer;
  padding: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 0 10px rgba(0, 255, 216, 0.6);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  outline: none;
}

.hotspot-pin:hover, .hotspot-pin.active {
  background: #00ffd8;
  box-shadow: 0 0 15px #00ffd8;
  transform: scale(1.2);
}

.hotspot-dot {
  width: 5px;
  height: 5px;
  background: #ffffff;
  border-radius: 50%;
}

.hotspot-tooltip {
  position: absolute;
  bottom: 26px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(4, 14, 28, 0.95);
  border: 1px solid rgba(0, 255, 216, 0.5);
  color: #ffffff;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.25s ease;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
}

.hotspot-pin:hover .hotspot-tooltip, .hotspot-pin.active .hotspot-tooltip {
  opacity: 1;
}

/* Hotspots list */
.hotspots-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}

.hotspot-item {
  background: rgba(2, 10, 20, 0.4);
  border: 1px solid rgba(0, 229, 255, 0.08);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.hotspot-item:hover {
  background: rgba(0, 229, 255, 0.04);
  border-color: rgba(0, 229, 255, 0.25);
  transform: translateY(-2px);
}

.hotspot-item.active {
  background: rgba(0, 229, 255, 0.08);
  border-color: #00ffd8;
  box-shadow: 0 4px 15px rgba(0, 255, 216, 0.08);
}

.hotspot-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.hotspot-tag {
  background: rgba(0, 255, 216, 0.15);
  border: 1px solid rgba(0, 255, 216, 0.35);
  color: #00ffd8;
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.hotspot-header h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
}

.hotspot-desc {
  margin: 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.5;
  text-align: justify;
}

.click-to-fly {
  position: absolute;
  right: 12px;
  top: 12px;
  font-size: 10px;
  color: rgba(0, 229, 255, 0.7);
  opacity: 0;
  transform: translateX(5px);
  transition: all 0.2s ease;
}

.hotspot-item:hover .click-to-fly {
  opacity: 1;
  transform: translateX(0);
}

.hotspot-item.active .click-to-fly {
  color: #00ffd8;
}

/* Animations */
@keyframes pulse-glow {
  0% {
    box-shadow: 0 0 0 0 rgba(0, 255, 216, 0.5);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(0, 255, 216, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(0, 255, 216, 0);
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-6px) rotate(180deg);
  }
}
</style>
