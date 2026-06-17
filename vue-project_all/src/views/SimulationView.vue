<template>
  <div class="simulation-container">
    <div id="simulationCesiumContainer" class="cesium-container"></div>
    
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

let viewer = null
const route = useRoute()
const currentCity = ref(route.query.city === 'huanggang' ? 'huanggang' : 'xiantao')

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

  const fileName = city === 'xiantao' ? 'xiantao.json' : 'huanggang.json';
  const colorStr = city === 'xiantao' ? '#ff007f' : '#ffd700';

  try {
    const response = await fetch(`/Dashboard/${fileName}`);
    if (!response.ok) throw new Error(`读取 ${fileName} 失败`);
    const geojson = await response.json();

    const holes = [];
    geojson.features.forEach(feature => {
      const geometry = feature.geometry;
      if (geometry.type === 'Polygon') {
        const outerRing = convertCoordsToCartesians(geometry.coordinates[0]);
        holes.push(new Cesium.PolygonHierarchy(outerRing));
        
        const line = viewer.entities.add({
          polyline: {
            positions: outerRing,
            width: 5.5,
            material: new Cesium.PolylineGlowMaterialProperty({
              glowPower: 0.26,
              color: Cesium.Color.fromCssColorString(colorStr)
            }),
            clampToGround: true
          }
        });
        currentBoundaryLines.push(line);
      } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach(polygon => {
          const outerRing = convertCoordsToCartesians(polygon[0]);
          holes.push(new Cesium.PolygonHierarchy(outerRing));
          
          const line = viewer.entities.add({
            polyline: {
              positions: outerRing,
              width: 5.5,
              material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.26,
                color: Cesium.Color.fromCssColorString(colorStr)
              }),
              clampToGround: true
            }
          });
          currentBoundaryLines.push(line);
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
    console.error(`加载 ${city} 行政边界蒙版时出错:`, error);
  }
}

const flyToCity = async (city) => {
  currentCity.value = city;
  if (!viewer) return;
  
  await loadCityMask(city);
  
  if (city === 'xiantao') {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(113.43, 30.29, 120000), // 仙桃：高度适中，稍微偏东侧以避开右侧面板
      duration: 2.0
    });
  } else if (city === 'huanggang') {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(115.55, 30.65, 380000), // 黄冈：面积大，高度大幅抬升，同样稍微偏东
      duration: 2.0
    });
  }
}

onMounted(async () => {
  const container = document.getElementById('simulationCesiumContainer')
  if (!container) return

  viewer = new Cesium.Viewer(container, {
    animation: false, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
    infoBox: false, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
    timeline: false, shouldAnimate: true, skyAtmosphere: false,
  })
  window.simulationViewer = viewer
  
  // 初始化时直接将视角定位到对应的城市，跳过从地球飞跃的过程
  if (currentCity.value === 'xiantao') {
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(113.43, 30.29, 120000)
    })
  } else {
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(115.55, 30.65, 380000)
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
})

onBeforeUnmount(() => {
  if (viewer) {
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
