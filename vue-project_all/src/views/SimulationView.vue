<template>
  <div class="simulation-container">
    <!-- 视图切换开关 -->
    <div class="view-toggle">
      <button :class="{ active: viewMode === '2d' }" @click="viewMode = '2d'">🗺️ 二维推演</button>
      <button :class="{ active: viewMode === '3d' }" @click="viewMode = '3d'">🌍 三维仿真</button>
    </div>

    <div v-show="viewMode === '3d'" id="simulationCesiumContainer" class="cesium-container"></div>
    
    <div v-if="viewMode === '2d'" class="cesium-container iframe-container">
      <div v-if="isGenerating2D" class="loading-overlay">
        <div class="spinner"></div>
        <span>正在生成二维推演...</span>
      </div>
      <iframe v-else :src="iframeSrc" class="deduction-iframe"></iframe>
    </div>
    
    <!-- 市级行政区划切换按钮 -->
    <div class="city-switcher">
      <h4>市级行政区划选择</h4>
      <div class="switch-buttons">
        <button 
          :class="{ active: currentCity === 'xiantao' }" 
          @click="flyToCity('xiantao')"
        >
          📍 仙桃市
        </button>
        <button 
          :class="{ active: currentCity === 'huanggang' }" 
          @click="flyToCity('huanggang')"
        >
          📍 黄冈市
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import * as Cesium from 'cesium'
import { getCollaborativeCommandCenterBaseUrl } from '../config/subsystems'

Cesium.Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIyYTUwYmE4Zi01ZjZlLTQ0MjAtYWMwNS0yYjBkZGFiM2RmOTUiLCJpZCI6MzU4MzQ0LCJpYXQiOjE3NjI1Nzc2NjR9.q9QoG-_99QZ2R2TlUYjiWGhn0-S5I22FFGuou_NAE3Q"

const viewMode = ref('2d')
const iframeSrc = ref('')
const isGenerating2D = ref(false)

let viewer = null
let currentCzmlDataSource = null
let smokeParticle = null
let fireParticle = null
let diffusionParticle = null
let diffusionStartTime = null
let preRenderListener = null
const route = useRoute()
const currentCity = ref(route.query.city === 'huanggang' ? 'huanggang' : 'xiantao')

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
    currentCzmlDataSource = dataSource
    viewer.dataSources.add(dataSource)
    // 保持当前的城市级俯视视角，不改变相机机位
  } catch (error) {
    console.error('加载三维轨迹 CZML 失败:', error)
  }
}

const generate2DDeduction = async (city) => {
  const endpoint = city === 'xiantao' ? 'crash' : 'leak'
  isGenerating2D.value = true
  try {
    const baseUrl = getCollaborativeCommandCenterBaseUrl()
    const response = await fetch(`${baseUrl}/api/run_3d_strategy?end_point=${endpoint}`)
    if (response.ok) {
      iframeSrc.value = `${baseUrl}/2d_deduction.html?t=${Date.now()}`
      // 生成成功后，异步加载并播放 3D 仿真轨迹
      await loadMission()
    } else {
      console.error('二维推演生成失败')
    }
  } catch (error) {
    console.error('请求生成二维推演时出错:', error)
  } finally {
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
  
  // 清除旧的蒙版和边界线
  if (currentMaskEntity) {
    viewer.entities.remove(currentMaskEntity);
    currentMaskEntity = null;
  }
  currentBoundaryLines.forEach(line => {
    viewer.entities.remove(line);
  });
  currentBoundaryLines = [];

  // 定义高亮边界线要加载的文件和颜色
  const outlineFiles = [];
  // 定义遮罩镂空（holes）要加载的文件
  let maskFileName = '';

  if (city === 'xiantao') {
    outlineFiles.push({ name: 'xiantao.json', color: '#ff007f' });
    maskFileName = 'xiantao.json';
  } else {
    outlineFiles.push({ name: 'huanggang.json', color: '#ffd700' });
    outlineFiles.push({ name: 'wuhan.json', color: '#00ffd8' }); // 青色高亮武汉边界
    maskFileName = 'huanggang_wuhan.json'; // 使用合并去边界的geojson作为镂空，避免Cesium多孔相切和自相交渲染黑屏Bug
  }

  try {
    // 1. 生成高亮边界线
    for (const fileInfo of outlineFiles) {
      const response = await fetch(`/Dashboard/${fileInfo.name}`);
      if (!response.ok) throw new Error(`读取 ${fileInfo.name} 失败`);
      const geojson = await response.json();

      geojson.features.forEach(feature => {
        const geometry = feature.geometry;
        if (geometry.type === 'Polygon') {
          const outerRing = convertCoordsToCartesians(geometry.coordinates[0]);
          const line = viewer.entities.add({
            polyline: {
              positions: outerRing,
              width: 5.5,
              material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.26,
                color: Cesium.Color.fromCssColorString(fileInfo.color)
              }),
              clampToGround: true
            }
          });
          currentBoundaryLines.push(line);
        } else if (geometry.type === 'MultiPolygon') {
          geometry.coordinates.forEach(polygon => {
            const outerRing = convertCoordsToCartesians(polygon[0]);
            const line = viewer.entities.add({
              polyline: {
                positions: outerRing,
                width: 5.5,
                material: new Cesium.PolylineGlowMaterialProperty({
                  glowPower: 0.26,
                  color: Cesium.Color.fromCssColorString(fileInfo.color)
                }),
                clampToGround: true
              }
            });
            currentBoundaryLines.push(line);
          });
        }
      });
    }

    // 2. 加载镂空文件，并生成暗色背景蒙版
    const holes = [];
    const maskResponse = await fetch(`/Dashboard/${maskFileName}`);
    if (!maskResponse.ok) throw new Error(`读取 ${maskFileName} 失败`);
    const maskGeojson = await maskResponse.json();

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
        material: Cesium.Color.fromCssColorString('#070b19').withAlpha(0.96),
        classificationType: Cesium.ClassificationType.BOTH,
        outline: false
      }
    });
  } catch (error) {
    console.error(`加载 ${city} 行政边界蒙版与高亮时出错:`, error);
  }
}

const flyToCity = async (city) => {
  currentCity.value = city;
  
  // 触发生成对应的二维推演
  generate2DDeduction(city);

  if (!viewer) return;
  
  await loadCityMask(city);
  updateParticlesVisibility(city);
  
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

onMounted(async () => {
  const container = document.getElementById('simulationCesiumContainer')
  if (!container) return

  viewer = new Cesium.Viewer(container, {
    animation: true, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
    infoBox: true, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
    timeline: true, shouldAnimate: true, skyAtmosphere: false,
  })
  window.simulationViewer = viewer

  // 加载 3D 建筑
  try {
    Cesium.createOsmBuildingsAsync().then(buildings => {
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
  viewer.scene.preRender.addEventListener(function(scene, time) {
    scene.light.direction = Cesium.Cartesian3.clone(scene.camera.directionWC, scene.light.direction)
  })
  viewer.cesiumWidget.creditContainer.style.display = 'none'

  viewer.imageryLayers.removeAll()
  try {
    const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
    )
    viewer.imageryLayers.addImageryProvider(imagery)
  } catch (e) {
    console.error('加载 ArcGIS 影像图层失败:', e)
  }

  // 加载地形
  try {
    const terrainProvider = await Cesium.CesiumTerrainProvider.fromUrl(
      'https://sandcastle.cesium.com/cesium-ion/rest/v1/assets/1/endpoint'
    )
    viewer.terrainProvider = terrainProvider
    viewer.scene.globe.depthTestAgainstTerrain = true
  } catch (e) {
    console.error('加载 Cesium 原生基础地形失败:', e)
  }

  await loadCityMask(currentCity.value)
  
  // 初始生成对应的二维推演
  generate2DDeduction(currentCity.value)

  // 初始化粒子系统
  initParticleSystems()

  // 动态粒子大小和速度监听器：根据相机高度动态缩放，保证高空视角下粒子依然可见且有真实上升漂移感
  preRenderListener = viewer.scene.preRender.addEventListener(() => {
    if (!viewer) return
    const cameraHeight = viewer.camera.positionCartographic.height
    // 动态缩放比例，基于高度：在 400 米以下为 1.0 倍，随高度增加而呈幂级数缩放
    const scaleFactor = Math.max(1.0, Math.pow(cameraHeight / 400.0, 0.85))
    
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
  })
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
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 2.5 * dt, gravityScratch);
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
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
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 5.0 * dt, gravityScratch);
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
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
      
      const windEast = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(eastVec, 0.5 * dt, windEast);
      Cesium.Cartesian3.add(particle.velocity, windEast, particle.velocity);
      
      const windNorth = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(northVec, 0.25 * dt, windNorth);
      Cesium.Cartesian3.add(particle.velocity, windNorth, particle.velocity);

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
        const currentEndScale = 8.0 + 8.0 * systemTimeRatio;
        particle.scale = 0.8 + (currentEndScale - 0.8) * ageRatio;
      }

      const dragFactor = Math.pow(0.96, dt * 60);
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
      if (sampled && typeof sampled.height === 'number') {
        height = sampled.height + heightOffset;
      }
    }
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
    // 仙桃市货车追尾现场坐标：lng = 113.104833, lat = 30.385469
    smokeParticle = viewer.scene.primitives.add(createSmokeSystem(113.104833, 30.385469));
    fireParticle = viewer.scene.primitives.add(createFireSystem(113.104833, 30.385469));

    // 黄冈市油罐车泄露现场坐标：lng = 114.873321, lat = 30.607381
    diffusionParticle = viewer.scene.primitives.add(createDiffusionSystem(114.873321, 30.607381));
    
    // 异步调整粒子高度使其紧贴地形表面
    adjustParticleHeight(smokeParticle, 113.104833, 30.385469, 2.0);
    adjustParticleHeight(fireParticle, 113.104833, 30.385469, 2.0);
    adjustParticleHeight(diffusionParticle, 114.873321, 30.607381, 2.8);

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
  if (viewer) {
    if (preRenderListener) {
      viewer.scene.preRender.removeEventListener(preRenderListener);
      preRenderListener = null;
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
    viewer.destroy()
    viewer = null
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

.view-toggle {
  position: absolute;
  top: 40px;
  left: 100px;
  background: rgba(6, 22, 40, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-radius: 8px;
  padding: 6px;
  display: flex;
  gap: 8px;
  z-index: 1000;
  backdrop-filter: blur(8px);
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

.city-switcher {
  position: absolute;
  top: 40px;
  right: 40px;
  width: 320px;
  background: rgba(6, 22, 40, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-radius: 8px;
  padding: 16px;
  color: #fff;
  z-index: 1000;
  backdrop-filter: blur(8px);
}

.city-switcher h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #00e5ff;
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  padding-bottom: 8px;
}

.switch-buttons {
  display: flex;
  gap: 12px;
}

.switch-buttons button {
  flex: 1;
  padding: 10px 0;
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid rgba(0, 229, 255, 0.3);
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
}

.switch-buttons button:hover {
  background: rgba(0, 229, 255, 0.2);
  border-color: rgba(0, 229, 255, 0.6);
}

.switch-buttons button.active {
  background: rgba(0, 229, 255, 0.3);
  border-color: #00e5ff;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.4);
  font-weight: bold;
}
</style>
