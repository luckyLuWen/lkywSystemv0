<template>
  <div class="system-container">
    <aside class="sidebar">
      <h2 class="title">🚨 两客一危路径规划指挥决策总控台</h2>
      
      <div class="menu-list">
        <button class="menu-btn blue" @click="showStreamlitView">🚑 协同调度平台</button>
        <button class="menu-btn blue" style="background: linear-gradient(to right, #0284c7, #38bdf8);" @click="show2DView">🌍 二维动态推演（次生灾害规避）</button>
        <button class="menu-btn purple" @click="run3DAlgorithm" :disabled="isLoading3D">
          {{ isLoading3D ? '⏳ 算力全开计算中...' : '🟣 三维协同与动态避障' }}
        </button>
        <button class="menu-btn green" @click="toggleMetrics">📊 协同策略能效评估</button>
      </div>

      <div class="metrics-panel" v-show="isMetricsVisible && metrics && currentView === '3d'">
        <h3>📋 实时评估指标 (3D)</h3>
        <div class="metric-item"><span>车辆用时:</span> <span>{{ metrics?.carTime }} 分钟</span></div>
        <div class="metric-item"><span>无人机飞行:</span> <span>{{ metrics?.uavTime }} 分钟</span></div>
        <div class="metric-item"><span>无人机能耗:</span> <span class="warning">{{ metrics?.uavEnergy }} kJ</span></div>
      </div>
    </aside>

    <main class="map-view">
      <iframe v-show="currentView === 'streamlit'" src="http://localhost:8501/?embed=true" class="iframe-map"></iframe>
      
      <iframe v-show="currentView === '2d'" :key="iframeKey" :src="iframe2DSrc" class="iframe-map"></iframe>
      
      <div class="floating-2d-panel" v-show="currentView === '2d'">
        <h4>🌪️ 次生灾害图层重载</h4>
        <div class="loading-mask" v-if="isUpdating2D">正在安全重构路径，请稍候...</div>
        
        <label class="toggle-container" title="关闭后将重新规划直达路径">
          <input type="checkbox" v-model="hasGroundBlock" :disabled="isUpdating2D">
          <span class="toggle-slider"></span>
          <span class="toggle-label">爆炸禁行区 (地面阻断)</span>
        </label>
        
        <label class="toggle-container" title="关闭后将恢复直线飞行">
          <input type="checkbox" v-model="hasAirSmoke" :disabled="isUpdating2D">
          <span class="toggle-slider"></span>
          <span class="toggle-label">烟雾禁飞区 (低空限制)</span>
        </label>

        <h4 style="margin-top: 20px; font-size: 0.95rem; border-top: 1px dashed #cbd5e1; padding-top: 15px;">🎯 协同策略配置</h4>
        <select v-model="selectedStrategy" :disabled="isUpdating2D" 
                style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1; outline: none; cursor: pointer; color: #1e293b; font-weight: bold; background: white;">
          <option value="slow_down_uav">RCD 逆向推演 (空地同步抵达)</option>
          <option value="wait">基地待命模式 (无人机延迟起飞)</option>
          <option value="independent">极速独立模式 (互不等待，各自为战)</option>
        </select>
      </div>
      
      <div v-show="currentView === '3d'" id="cesiumContainer" class="map-box"></div>
      
      <div class="timeline-panel" v-show="currentView === '3d' && maxTimeIndex > 0">
        <button class="play-btn" @click="togglePlay">{{ isPlaying ? '⏸' : '▶' }}</button>
        <input type="range" class="time-slider" v-model.number="currentTimeIndex" min="0" :max="maxTimeIndex">
        <span class="time-label">{{ currentTimeIndex }}s / {{ maxTimeIndex }}s</span>
      </div>

      <div class="evaluation-overlay" v-if="showEvaluationPanel">
        <div class="eval-card">
          <button class="close-btn" @click="showEvaluationPanel = false">✖ 关闭</button>
          <h2 class="eval-title">📊 多维空地协同评估</h2>
          <div class="eval-grid">
            <div class="eval-box">
              <p>系统在复杂空间中完美实现了动态自适应重规划，证明了协同机制的优越性。</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'

const isLoading3D = ref(false)
const isUpdating2D = ref(false) 
const metrics = ref(null)
const currentView = ref('2d') 
const isMetricsVisible = ref(true) 
const showEvaluationPanel = ref(false)

const iframe2DSrc = ref('http://127.0.0.1:3005/wuhan_rescue_optimized.html')
// 🌟 核心修改 3：定义刷新 key
const iframeKey = ref(0)
// 🌟 核心修改 6：定义后端服务状态
const backendStatus = ref('checking') 

const hasGroundBlock = ref(true)
const hasAirSmoke = ref(true)
const selectedStrategy = ref('slow_down_uav') 

let viewer = null
const currentTimeIndex = ref(0)
const maxTimeIndex = ref(0)
const isPlaying = ref(false)
let playInterval = null
let savedCarPath = []
let savedUavPath = []

const createIcon = (emoji, glowColor) => {
  const canvas = document.createElement('canvas');
  canvas.width = 80; canvas.height = 80;
  const ctx = canvas.getContext('2d');
  ctx.font = '50px "Segoe UI Emoji", "Apple Color Emoji", sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.shadowColor = glowColor; ctx.shadowBlur = 15;
  ctx.fillText(emoji, 40, 40);
  return canvas.toDataURL('image/png');
};
const CAR_ICON = createIcon('🚑', 'rgba(37, 99, 235, 0.8)');
const UAV_ICON = createIcon('🚁', 'rgba(168, 85, 247, 0.8)');

// 🌟 核心修改 4：统一使用 watch 监听状态变化并发送请求，解决死锁
watch([hasGroundBlock, hasAirSmoke, selectedStrategy], async () => {
  if (isUpdating2D.value) return; 
  console.log(`📡 状态变更拦截！当前策略: ${selectedStrategy.value}`);
  isUpdating2D.value = true;
  
  const url = `http://127.0.0.1:3005/update-2d-map?ugvBlock=${hasGroundBlock.value ? '1' : '0'}&uavSmoke=${hasAirSmoke.value ? '1' : '0'}&strategy=${selectedStrategy.value}`;
  
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error("后端服务报错");
    
    // 更新时间戳并强制改变 key 撕裂缓存
    iframe2DSrc.value = `http://127.0.0.1:3005/wuhan_rescue_optimized.html?t=${new Date().getTime()}`;
    iframeKey.value += 1; 
  } catch (error) {
    console.error("❌ 更新请求失败:", error);
    alert("地图更新失败，请检查 Node 后端终端的报错信息！");
  } finally { 
    isUpdating2D.value = false; 
  }
});

onMounted(() => {
  const initCesium = () => {
    if (!window.Cesium) return;
    try {
      viewer = new window.Cesium.Viewer('cesiumContainer', {
        imageryProvider: false, animation: false, timeline: false, baseLayerPicker: false, infoBox: true, geocoder: false, homeButton: false, sceneModePicker: false, navigationHelpButton: false
      });
      viewer.cesiumWidget.creditContainer.style.display = "none";
      const gaodeProvider = new window.Cesium.UrlTemplateImageryProvider({ url: 'https://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}' });
      viewer.imageryLayers.addImageryProvider(gaodeProvider);
      viewer.camera.flyTo({ destination: window.Cesium.Cartesian3.fromDegrees(114.4140, 30.5185, 5000), orientation: { heading: 0, pitch: window.Cesium.Math.toRadians(-55), roll: 0.0 }, duration: 2 });
    } catch (error) {
        console.error("Cesium初始化报错:", error);
    }
  };
  initCesium();
  
  // 🌟 核心修改 7：检查后端服务状态
  checkBackendStatus();
});

// 🌟 核心修改 8：检查后端服务状态
async function checkBackendStatus() {
  try {
    const response = await fetch('http://127.0.0.1:3005/wuhan_rescue_optimized.html', { method: 'HEAD' });
    backendStatus.value = response.ok ? 'online' : 'offline';
  } catch (error) {
    console.error("后端服务检查失败:", error);
    backendStatus.value = 'offline';
  }
}

function showStreamlitView() {
  // 检查 Streamlit 服务状态
  fetch('http://localhost:8501/?embed=true', { method: 'HEAD' })
    .then(response => {
      if (response.ok) {
        currentView.value = 'streamlit';
        showEvaluationPanel.value = false;
      } else {
        alert("⚠️ Streamlit 服务未启动，请先运行 Streamlit 服务！");
      }
    })
    .catch(error => {
      console.error("Streamlit 服务检查失败:", error);
      alert("⚠️ Streamlit 服务未启动，请先运行 Streamlit 服务！");
    });
}

function show2DView() {
  // 检查后端服务状态
  if (backendStatus.value === 'offline') {
    alert("⚠️ 后端服务未启动，请先运行 Rescue_System_V2/backend 中的 npm start 命令！");
    return;
  }
  currentView.value = '2d';
  showEvaluationPanel.value = false;
}
function toggleMetrics() { showEvaluationPanel.value = true; }

// 🌟 核心修改 5：删除原本多余的 forceUpdateMap 函数，已经用 watch 替代。

function togglePlay() {
  isPlaying.value = !isPlaying.value;
  if (isPlaying.value) {
    if (currentTimeIndex.value >= maxTimeIndex.value) currentTimeIndex.value = 0;
    playInterval = setInterval(() => {
      if (currentTimeIndex.value < maxTimeIndex.value) currentTimeIndex.value++;
      else { clearInterval(playInterval); isPlaying.value = false; }
    }, 50); 
  } else { clearInterval(playInterval); }
}

async function run3DAlgorithm() {
  currentView.value = '3d';
  
  // 🌟 核心修改 9：检查后端服务状态
  if (backendStatus.value === 'offline') {
    alert("⚠️ 后端服务未启动，请先运行 Rescue_System_V2/backend 中的 npm start 命令！");
    return;
  }
  
  if (!viewer) {
      alert("❌ 3D地图引擎(Cesium)没有加载成功！请检查网络或刷新页面。");
      return;
  }
  
  try {
    isLoading3D.value = true;
    viewer.entities.removeAll(); 
    showEvaluationPanel.value = false; 

    const url = `http://127.0.0.1:3005/run-algorithm?ugvBlock=${hasGroundBlock.value ? '1' : '0'}&uavSmoke=${hasAirSmoke.value ? '1' : '0'}&strategy=${selectedStrategy.value}`;
    console.log("准备调用 3D 接口:", url);
    
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`连接 Python 失败！状态码: ${response.status}`);
    }
    
    const data = await response.json();
    console.log("成功接收到 3D 路径数据:", data);
    
    if (!data.car_path || data.car_path.length === 0) {
        throw new Error("Python 运行结束了，但返回的车辆路径数据是空的！");
    }

    savedCarPath = data.car_path;
    savedUavPath = data.uav_path;
    maxTimeIndex.value = Math.max(savedCarPath.length, savedUavPath.length) - 1;
    currentTimeIndex.value = 0;

    viewer.entities.add({
      name: "车辆救援路径",
      polyline: {
        positions: window.Cesium.Cartesian3.fromDegreesArrayHeights(savedCarPath.flat()),
        width: 5,
        material: window.Cesium.Color.CYAN
      }
    });

    viewer.entities.add({
      name: "无人机飞行路径",
      polyline: {
        positions: window.Cesium.Cartesian3.fromDegreesArrayHeights(savedUavPath.flat()),
        width: 3,
        material: window.Cesium.Color.MAGENTA
      }
    });

    if (data.obstacles && Array.isArray(data.obstacles)) {
      data.obstacles.forEach(obs => {
        const safeColor = window.Cesium.Color.fromCssColorString(obs.color || '#ff0000').withAlpha(0.35);
        if (obs.type === 'cylinder' && obs.center) {
          viewer.entities.add({
            position: window.Cesium.Cartesian3.fromDegrees(obs.center[0], obs.center[1], obs.height / 2),
            cylinder: { length: obs.height, topRadius: obs.radius, bottomRadius: obs.radius, material: safeColor }
          });
        } else if (obs.type === 'polygon' && obs.positions) {
          viewer.entities.add({
            polygon: { hierarchy: window.Cesium.Cartesian3.fromDegreesArray(obs.positions), material: safeColor, extrudedHeight: 10 }
          });
        }
      });
    }

    viewer.entities.add({
      position: new window.Cesium.CallbackProperty(() => {
        const pt = savedCarPath[Math.min(currentTimeIndex.value, savedCarPath.length - 1)];
        return pt ? window.Cesium.Cartesian3.fromDegrees(pt[0], pt[1], pt[2] + 5) : undefined;
      }, false),
      billboard: { image: CAR_ICON, scale: 0.8, verticalOrigin: window.Cesium.VerticalOrigin.BOTTOM, disableDepthTestDistance: Number.POSITIVE_INFINITY }
    });

    viewer.entities.add({
      position: new window.Cesium.CallbackProperty(() => {
        const pt = savedUavPath[Math.min(currentTimeIndex.value, savedUavPath.length - 1)];
        return pt ? window.Cesium.Cartesian3.fromDegrees(pt[0], pt[1], pt[2]) : undefined;
      }, false),
      billboard: { image: UAV_ICON, scale: 0.8, disableDepthTestDistance: Number.POSITIVE_INFINITY }
    });

    metrics.value = data.metrics;
    isMetricsVisible.value = true;
    
    viewer.flyTo(viewer.entities); 

  } catch (error) {
    console.error("🚨 3D 计算/渲染发生致命错误:", error);
    alert(`⚠️ 渲染失败，原因: \n${error.message}\n\n请去 Node 后端黑窗口看 Python 报了什么错！`);
  } finally {
    isLoading3D.value = false;
  }
}
</script>

<style scoped>
/* 原样式完全保留，未做任何修改 */
.system-container { display: flex; height: 100vh; width: 100vw; background-color: #0f172a; font-family: sans-serif; overflow: hidden; }
.sidebar { width: 320px; background-color: #1e293b; color: white; padding: 25px; z-index: 1000; border-right: 2px solid #334155; }
.title { font-size: 1.25rem; margin-bottom: 30px; color: #f8fafc; text-align: center; }
.menu-list { display: flex; flex-direction: column; gap: 15px; }
.menu-btn { padding: 15px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; color: white; transition: 0.2s;}
.menu-btn:hover { filter: brightness(1.1); }
.blue { background: linear-gradient(to right, #0284c7, #38bdf8); }
.purple { background: linear-gradient(to right, #7e22ce, #a855f7); }
.green { background: linear-gradient(to right, #059669, #10b981); }
.metrics-panel { margin-top: 30px; background: #0f172a; padding: 15px; border-radius: 8px; border: 1px solid #334155; }
.metric-item { display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 8px; }
.warning { color: #f59e0b; }
.map-view { flex: 1; position: relative; background: #000; }
.map-box { width: 100%; height: 100%; }
.iframe-map { width: 100%; height: 100%; border: none; background-color: #fff; }

.floating-2d-panel {
  position: absolute; top: 20px; right: 20px;
  background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(8px);
  border: 1px solid #cbd5e1; border-radius: 12px; padding: 20px;
  z-index: 2000; box-shadow: 0 10px 25px rgba(0,0,0,0.15);
  color: #1e293b; width: 300px;
}
.floating-2d-panel h4 { margin: 0 0 15px 0; font-size: 1.05rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; color: #3b82f6;}
.loading-mask { font-size: 0.8rem; color: #ef4444; margin-bottom: 10px; font-weight: bold; animation: pulse 1.5s infinite;}
.toggle-container { display: flex; align-items: center; margin-bottom: 15px; cursor: pointer; }
.toggle-container input { display: none; }
.toggle-slider { width: 44px; height: 24px; background-color: #cbd5e1; border-radius: 20px; position: relative; transition: 0.3s; margin-right: 12px; flex-shrink: 0;}
.toggle-slider::before { content: ""; position: absolute; width: 18px; height: 18px; border-radius: 50%; background-color: white; top: 3px; left: 3px; transition: 0.3s; box-shadow: 0 2px 4px rgba(0,0,0,0.2);}
.toggle-container input:checked + .toggle-slider { background-color: #ef4444; }
.toggle-container input:checked + .toggle-slider::before { transform: translateX(20px); }
.toggle-label { color: #475569; font-size: 0.95rem; font-weight: 500;}

.timeline-panel { position: absolute; bottom: 30px; left: 50%; transform: translateX(-50%); background: rgba(30, 41, 59, 0.9); padding: 10px 20px; border-radius: 50px; display: flex; align-items: center; gap: 15px; width: 60%; z-index: 1000; }
.play-btn { background: #3b82f6; color: white; border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;}
.time-slider { flex: 1; accent-color: #a855f7; cursor: pointer;}
.time-label { color: white; font-size: 0.8rem; min-width: 70px; }
.evaluation-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px); z-index: 3000; display: flex; justify-content: center; align-items: center;}
.eval-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #3b82f6; border-radius: 15px; width: 80%; max-width: 850px; padding: 30px; position: relative; color: white;}
.close-btn { position: absolute; top: 15px; right: 20px; background: transparent; border: none; color: #94a3b8; font-size: 1.1rem; cursor: pointer; }
.eval-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.eval-box { background: rgba(255, 255, 255, 0.03); border: 1px solid #334155; border-radius: 10px; padding: 20px; }
.bar-container { margin-bottom: 15px; }
.bar-bg { background: #334155; border-radius: 20px; height: 24px; width: 100%; overflow: hidden; }
.bar-fill { height: 100%; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; font-size: 0.8rem; font-weight: bold; color: white;}
.bar-fill.red { background: linear-gradient(90deg, #b91c1c, #ef4444); }
.bar-fill.green { background: linear-gradient(90deg, #047857, #10b981); }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
</style>