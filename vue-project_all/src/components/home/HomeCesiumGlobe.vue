<template>
  <div class="cesium-wrapper">
    <div id="cesiumContainer" ref="containerRef" class="cesium-container"></div>
    
    <!-- 飞行动画照片 -->
    <div
      v-for="photo in flyingPhotos"
      :key="photo.id"
      class="flying-photo"
      :style="{
        left: photo.x + 'px',
        top: photo.y + 'px',
        width: photo.width + 'px',
        height: photo.height + 'px',
        opacity: photo.opacity,
        backgroundImage: `url(${photo.src})`
      }"
    ></div>
    
    <!-- 模型调整控制面板 -->
    <div class="debug-panel" v-if="true">
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
      
      <!-- 事故点位置微调 (蓝色标记点) -->
      <h4>事故点位置微调</h4>
      <div>
        <label>经度 (X): <input type="number" v-model.number="currentPointAdjust.lng" step="0.00001" /></label>
      </div>
      <div>
        <label>纬度 (Y): <input type="number" v-model.number="currentPointAdjust.lat" step="0.00001" /></label>
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

    <!-- 救援装备出动悬浮窗 -->
    <div 
      v-if="rescuePopup.show" 
      class="shelter-popup-panel"
      :style="{ left: rescuePopup.x + 'px', top: rescuePopup.y + 'px' }"
    >
      <div class="shelter-popup-header">
        <span>{{ rescuePopup.title }}</span>
        <button class="close-btn" @click="rescuePopup.show = false">×</button>
      </div>
      <table class="shelter-popup-table">
        <tbody>
          <tr>
            <td class="label">无人机</td>
            <td class="value">{{ rescuePopup.uavCount }}</td>
          </tr>
          <tr>
            <td class="label">无人车</td>
            <td class="value">{{ rescuePopup.carCount }}</td>
          </tr>
          <tr>
            <td class="label">出动状态</td>
            <td class="value">{{ rescuePopup.status }}</td>
          </tr>
        </tbody>
      </table>
      <div class="shelter-popup-arrow"></div>
    </div>

    <!-- 无人机现场侦察照片悬浮窗 -->
    <div 
      v-if="props.activePhaseIndex === 8" 
      class="uav-photo-panel"
    >
      <div class="uav-photo-header">
        <span class="uav-photo-icon">📸</span>
        <span class="uav-photo-title">多角度现场侦察拍图 ({{ capturedCount }}/4)</span>
        <span class="uav-status-tag" :class="{ 'status-done': capturedCount === 4 }">
          {{ capturedCount === 4 ? '拍摄完成' : '侦察拍摄中...' }}
        </span>
      </div>
      
      <div class="uav-photo-content">
        <!-- 主图区域 -->
        <div class="uav-main-photo-wrapper">
          <img 
            v-if="activePhotoIndex !== null"
            :src="currentPhotoSrc" 
            :class="['uav-photo-img', 'photo-angle-' + activePhotoIndex]" 
            alt="无人机侦察照片" 
          />
          <div v-else class="uav-photo-placeholder">
            <div class="radar-scan"></div>
            <span>等待无人机到达拍照位置...</span>
          </div>
          
          <div class="uav-photo-overlay" v-if="activePhotoIndex !== null">
            <div class="uav-photo-timestamp">REC ● {{ currentTimeStr }}</div>
            <div class="uav-photo-coords">{{ getAngleName(activePhotoIndex) }} ({{ props.phases[0]?.id.startsWith('t-') ? '113.1048°E, 30.3855°N' : '114.8945°E, 30.6322°N' }})</div>
          </div>
        </div>
        
        <!-- 4张缩略图列表 -->
        <div class="uav-thumbnails-row">
          <div 
            v-for="i in [0, 1, 2, 3]" 
            :key="i"
            class="uav-thumb-box"
            :class="{ 
              'is-captured': capturedPhotos[i], 
              'is-active': activePhotoIndex === i 
            }"
            @click="selectThumb(i)"
          >
            <div class="uav-thumb-inner" v-if="capturedPhotos[i]">
              <img 
                :src="currentPhotoSrc" 
                :class="['uav-thumb-img', 'photo-angle-' + i]" 
              />
              <div class="thumb-badge">角 {{ i+1 }}</div>
            </div>
            <div class="uav-thumb-lock" v-else>
              <span class="lock-icon">🔒</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 无人车 A 实时数据悬浮窗 -->
    <div 
      v-if="props.activePhaseIndex >= 7 && ugvA.x !== -1000" 
      class="ugv-panel"
      :style="{ left: ugvA.x + 'px', top: ugvA.y + 'px' }"
    >
      <div class="ugv-header">
        <span class="ugv-title">无人车 A</span>
        <span class="ugv-status">在线</span>
      </div>
      <div class="ugv-data">
        <div class="ugv-row">
          <div class="ugv-item"><span class="ugv-label">温度</span><span class="ugv-value">{{ ugvA.temp }}</span></div>
          <div class="ugv-item"><span class="ugv-label">湿度</span><span class="ugv-value">{{ ugvA.hum }}%</span></div>
        </div>
        <div class="ugv-row">
          <div class="ugv-item full-width"><span class="ugv-label">烟雾</span><span class="ugv-value">{{ ugvA.smoke }} ug</span></div>
        </div>
        <div class="ugv-row">
          <div class="ugv-item"><span class="ugv-label">TVOC</span><span class="ugv-value">{{ ugvA.tvoc }}</span></div>
          <div class="ugv-item"><span class="ugv-label">CO</span><span class="ugv-value">{{ ugvA.co }}</span></div>
        </div>
      </div>
      <div class="ugv-footer" @click="goToSensorManage('node1')">点击查看详情 →</div>
    </div>

    <!-- 无人车 B 实时数据悬浮窗 -->
    <div 
      v-if="props.activePhaseIndex >= 7 && ugvB.x !== -1000" 
      class="ugv-panel"
      :style="{ left: ugvB.x + 'px', top: ugvB.y + 'px' }"
    >
      <div class="ugv-header">
        <span class="ugv-title">无人车 B</span>
        <span class="ugv-status">在线</span>
      </div>
      <div class="ugv-data">
        <div class="ugv-row">
          <div class="ugv-item"><span class="ugv-label">温度</span><span class="ugv-value">{{ ugvB.temp }}</span></div>
          <div class="ugv-item"><span class="ugv-label">湿度</span><span class="ugv-value">{{ ugvB.hum }}%</span></div>
        </div>
        <div class="ugv-row">
          <div class="ugv-item full-width"><span class="ugv-label">烟雾</span><span class="ugv-value">{{ ugvB.smoke }} ug</span></div>
        </div>
        <div class="ugv-row">
          <div class="ugv-item"><span class="ugv-label">TVOC</span><span class="ugv-value">{{ ugvB.tvoc }}</span></div>
          <div class="ugv-item"><span class="ugv-label">CO</span><span class="ugv-value">{{ ugvB.co }}</span></div>
        </div>
      </div>
      <div class="ugv-footer" @click="goToSensorManage('node2')">点击查看详情 →</div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as Cesium from 'cesium'

const router = useRouter()

function goToSensorManage(target = '') {
  const query = target ? { target } : {}
  router.push({ path: '/sensor-manage', query })
}

// 当前选中的场景
const currentScene = ref('truck')

// 无人机视频/图像时间戳更新
const currentTimeStr = ref('')
const updateTime = () => {
  const now = new Date()
  const pad = (num) => String(num).padStart(2, '0')
  currentTimeStr.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}
let timeInterval = null

// 无人机多角度照片拍摄状态
const capturedPhotos = ref([false, false, false, false])
const activePhotoIndex = ref(null)

const capturedCount = computed(() => {
  return capturedPhotos.value.filter(Boolean).length
})

const getAngleName = (index) => {
  const names = ['东北角视角', '东南角视角', '西南角视角', '西北角视角']
  return names[index] || ''
}

const selectThumb = (index) => {
  if (capturedPhotos.value[index]) {
    activePhotoIndex.value = index
  }
}

const currentPhotoSrc = computed(() => {
  const isTruck = props.phases[0]?.id.startsWith('t-')
  return isTruck ? '/Dashboard/images/uav_aerial_photo.png' : '/Dashboard/images/tanker_aerial_photo.png'
})

const flyingPhotos = ref([]);

function triggerPhotoAnimation(index, cartesianPos) {
  if (!viewer) return;
  const windowPos = Cesium.SceneTransforms.worldToWindowCoordinates(viewer.scene, cartesianPos);
  if (!windowPos) return;

  const photoId = Date.now() + '-' + index;
  const photo = reactive({
    id: photoId,
    index: index,
    src: currentPhotoSrc.value,
    x: windowPos.x - 20,
    y: windowPos.y - 15,
    width: 40,
    height: 30,
    opacity: 1
  });
  flyingPhotos.value.push(photo);

  setTimeout(() => {
    const thumbs = document.querySelectorAll('.sidebar-thumb-box, .uav-thumb-box');
    const targetEl = thumbs[index];
    if (targetEl) {
      const rect = targetEl.getBoundingClientRect();
      photo.x = rect.left;
      photo.y = rect.top;
      photo.width = rect.width;
      photo.height = rect.height;
    } else {
      photo.x = window.innerWidth - 100;
      photo.y = window.innerHeight / 2;
      photo.width = 60;
      photo.height = 40;
    }
  }, 50);

  setTimeout(() => {
    const idx = flyingPhotos.value.findIndex(p => p.id === photoId);
    if (idx !== -1) {
      flyingPhotos.value.splice(idx, 1);
    }
  }, 900);
}



// 救援装备出动状态与坐标 (放在无人机/车出动起点附近)
const rescueCoords = reactive({ lng: 113.10725, lat: 30.38491, height: 24.0 });

const rescuePopup = reactive({
  show: false,
  title: '救援装备出动',
  uavCount: '1 架',
  carCount: '2 辆',
  status: '已出发',
  x: 0,
  y: 0
});

// 城市高亮上浮高度 (仙桃与黄冈)
const xiantaoHeight = ref(0);
const huanggangHeight = ref(0);

let rescueMarkerEntity = null;

let sharedTruckRescueCarPosition = null;
let sharedTankerRescueCarPosition = null;

// 无人车实时数据及浮窗位置
const ugvA = reactive({
  temp: 29.88, hum: 58.02, smoke: 25284, tvoc: 0.357, co: 2.8,
  x: -1000, y: -1000
});
const ugvB = reactive({
  temp: 27.07, hum: 43.47, smoke: 25292, tvoc: 0.588, co: 3.3,
  x: -1000, y: -1000
});

// 计算属性：根据当前场景返回对应的参数对象
const currentUavAdjust = computed(() => {
  return currentScene.value === 'truck' ? uavAdjust : tankerUavAdjust
})

const currentTruckAdjust = computed(() => {
  return currentScene.value === 'truck' ? truckAdjust : tankerAdjust
})

const currentPointAdjust = computed(() => {
  return currentScene.value === 'truck' ? truckPointAdjust : tankerPointAdjust
})

const currentRescueCarAdjust = computed(() => {
  return currentScene.value === 'truck' ? rescueCarAdjust : tankerRescueCarAdjust
})

const props = defineProps({
  phases: { type: Array, default: () => [] },
  activePhaseIndex: { type: Number, default: 0 },
  focusedPointId: { type: String, default: '' },
  sensorData: { type: Object, default: () => ({}) }
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

const truckPointAdjust = reactive({
  lng: 113.104833,
  lat: 30.385469
})

const tankerAdjust = reactive({
  scale: 0.26,
  heading: -29,
  lng: 114.8945,
  lat: 30.632161,
  height: -1.2 // 手动微调高度以贴合地面
})

const tankerPointAdjust = reactive({
  lng: 114.89209,
  lat: 30.63101
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
let uavOrbitStartTime = 0
let diffusionStartTime = 0
let lastUavPhaseIndex = -1

// 油罐车场景的无人机和救援车配置（独立控制）
const tankerUavAdjust = reactive({
  scale: 6,
  heading: 34,
  lng: 114.89539,
  lat: 30.63129,
  height: 11.5
});

const tankerRescueCarAdjust = reactive({
  scale: 250,
  heading: 155,
  lng: 114.89417,
  lat: 30.63182,
  height: 6.5
});

const TANKER_STOP_FACTOR = 0.4;

// 油罐车场景的无人机和救援车实体数组
let tankerUavEntities = []
let tankerRescueCarEntities = []
let tankerPhase7StartTime = 0
let tankerUavOrbitStartTime = 0
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
  accident_red: { id: 'accident_red', label: '油罐车泄露现场', longitude: 114.8945, latitude: 30.632161, color: '#00e5ff' },  // 改为蓝色
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
    // 湖北省中心点 (微调经纬度，使地图在视觉上避开左侧边栏和底部时间线)
    lng = 112.5; lat = 30.6;
  }

  try {
    const target = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
    
    // 默认视角参数 - 使用正上方向下看 (-90度) 展示完整的湖北省，并拉大高度以避免被UI遮挡
    let range = isFocused ? (props.focusedPointId === 'accident_red' ? 480 : 480) : 1200000
    let pitch = isFocused ? (props.focusedPointId === 'accident_red' ? Cesium.Math.toRadians(-32) : Cesium.Math.toRadians(-38)) : Cesium.Math.toRadians(-90)

    if (isFocused) {
      if (props.activePhaseIndex <= 1) {
        // 仿真开始及正常行驶阶段：高俯视全景视角
        range = 1800
        pitch = Cesium.Math.toRadians(-75);
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
        if (props.focusedPointId === 'accident_red') {
          range = 100; // 统一为以次生灾害弥漫为主的 100 米范围视角
          pitch = Cesium.Math.toRadians(-25); // 统一为以次生灾害弥漫为主的 -25 度俯仰角
        } else {
          range = 220;
          pitch = Cesium.Math.toRadians(-65);
        }
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

// 创建更加逼真、动感的油罐车泄露效果 (高压侧向喷射抛物线 Plume 效果)
function createLeakSystem(lng, lat) {
  const position = Cesium.Cartesian3.fromDegrees(lng, lat, 0.8);
  const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(tankerAdjust.heading) || 36), 0, 0);
  const modelMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(position, hpr);

  // 旋转发射器方向：把默认朝上(+z)的锥形喷射旋转-90度，使其朝向车身侧面(+y方向)喷出
  const rotation = Cesium.Matrix3.fromRotationX(Cesium.Math.toRadians(-90.0));
  // 稍微向车外侧偏移，使粒子从侧面罐体破裂处喷出，而不是车底中心
  const translation = new Cesium.Cartesian3(0.0, 1.2, 0.2);
  const emitterModelMatrix = Cesium.Matrix4.fromRotationTranslation(rotation, translation);

  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/whitePuff00.png',
    startColor: new Cesium.Color(0.85, 0.9, 0.95, 0.65), // 增强不透明度，表现喷射处的浓密感
    endColor: new Cesium.Color(0.95, 0.97, 1.0, 0.0),
    startScale: 0.6,  // 喷口处适当保留体积
    endScale: 5.5,    // 随抛物线下落扩散开来
    minimumParticleLife: 1.0,
    maximumParticleLife: 2.2, // 较短寿命防止在天空中堆积
    minimumSpeed: 3.5, // 喷出的初始速度
    maximumSpeed: 6.0,
    imageSize: new Cesium.Cartesian2(6, 6), // 较小的粒子尺寸以获得精细自然的渐变感
    emissionRate: 140.0, // 显著提高粒子发射率以模拟连续高压水柱/气柱
    lifetime: 16.0,
    emitter: new Cesium.ConeEmitter(Cesium.Math.toRadians(25.0)), // 25度适度喷嘴角度
    modelMatrix: modelMatrix,
    emitterModelMatrix: emitterModelMatrix,
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 1. 模拟水平方向空气阻力：速度迅速衰减，表现喷射后的悬浮感
      const dragFactor = Math.pow(0.85, dt * 60);
      particle.velocity.x *= dragFactor;
      particle.velocity.y *= dragFactor;

      // 2. 模拟重力下坠：喷出后的气体/液体在重力作用下呈优美的抛物线弧度坠落到地面
      particle.velocity.z -= 4.0 * dt;
    }
  });
}

// 创建弥漫效果系统 (使用 whitePuff00.png) - 统一为与泄露一致的圆形粒子喷射散开效果，并支持随时间渐进向外扩散 (已微调减小)
function createDiffusionSystem(lng, lat) {
  const center = Cesium.Cartesian3.fromDegrees(lng, lat, 0.8);
  
  // 计算卡车所在位置的局部 ENU (东-北-上) 坐标轴向量，用于在地球世界坐标系中进行方向纠正
  const enuMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(center);
  const eastVec = Cesium.Matrix4.getColumn(enuMatrix, 0, new Cesium.Cartesian3());
  const northVec = Cesium.Matrix4.getColumn(enuMatrix, 1, new Cesium.Cartesian3());
  const upVec = Cesium.Matrix4.getColumn(enuMatrix, 2, new Cesium.Cartesian3());

  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/whitePuff00.png',
    startColor: new Cesium.Color(0.35, 0.8, 0.35, 0.45), // 绿色半透明圆形粒子
    endColor: new Cesium.Color(0.45, 0.85, 0.45, 0.0),       // 渐变至完全透明
    startScale: 0.8,
    endScale: 8.0, // 在生命周期中逐渐膨胀变大
    minimumParticleLife: 4.0,
    maximumParticleLife: 6.5, // 微调粒子寿命，适度减小扩散半径
    minimumSpeed: 2.0,
    maximumSpeed: 5.5, // 适度调低喷出初速度
    imageSize: new Cesium.Cartesian2(9, 9), // 基础尺寸调整为 9x9 (原为12x12)，更显精细与克制
    emissionRate: 120.0, // 保持发射率以维持连贯的团雾质感
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(2.5), // 发射器半径调整为 2.5 (原为3.5)
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(center),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 1. 真实局部向上浮力 (Z轴向上，使整个弥漫气云升空)
      const buoyancy = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(upVec, 0.5 * dt, buoyancy); 
      Cesium.Cartesian3.add(particle.velocity, buoyancy, particle.velocity);
      
      // 2. 真实地理风向漂移：沿局部东向和北向缓缓漂移
      const windEast = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(eastVec, 0.5 * dt, windEast);
      Cesium.Cartesian3.add(particle.velocity, windEast, particle.velocity);
      
      const windNorth = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(northVec, 0.25 * dt, windNorth);
      Cesium.Cartesian3.add(particle.velocity, windNorth, particle.velocity);

      // 3. 随仿真阶段时间推移的“渐进式向外二次大范围膨胀扩散”
      const offset = Cesium.Cartesian3.subtract(particle.position, center, new Cesium.Cartesian3());
      const dist = Cesium.Cartesian3.magnitude(offset);
      if (dist > 0.01) {
        const dir = new Cesium.Cartesian3();
        Cesium.Cartesian3.normalize(offset, dir);
        
        // 根据阶段持续运行时间 (15 秒内渐进增强)
        const elapsed = diffusionStartTime ? (Date.now() - diffusionStartTime) / 1000 : 0;
        const systemTimeRatio = Math.min(elapsed / 15.0, 1.0);
        
        // 随着阶段进行，粒子向四周放射膨胀的速度适度增加
        const extraForce = (4.0 + 12.0 * systemTimeRatio) * dt;
        const expansion = new Cesium.Cartesian3();
        Cesium.Cartesian3.multiplyByScalar(dir, extraForce, expansion);
        Cesium.Cartesian3.add(particle.velocity, expansion, particle.velocity);
        
        // 动态调控粒子大小：远端的粒子适度膨胀
        const ageRatio = particle.age / particle.life;
        const currentEndScale = 8.0 + 8.0 * systemTimeRatio; // 最大可膨胀到 16.0 倍 (原为22.0)
        particle.scale = 0.8 + (currentEndScale - 0.8) * ageRatio;
      }

      // 4. 空气阻力：阻力从 0.978 调整到 0.96，使扩散边界略微收拢，防止过度散开
      const dragFactor = Math.pow(0.96, dt * 60);
      particle.velocity.x *= dragFactor;
      particle.velocity.y *= dragFactor;
      particle.velocity.z *= dragFactor;
    }
  });
}

function updatePopupPosition() {
  if (!viewer) return;

  // 救援装备出动阶段 (index === 6) 让浮窗和图标跟随无人机的位置运动
  if (rescuePopup.show && Number(props.activePhaseIndex) === 6) {
    const isTanker = props.focusedPointId === 'accident_red';
    const uavId = isTanker ? 'uav_model_tanker' : 'uav_model';
    const uavEntity = viewer.entities.getById(uavId);
    if (uavEntity) {
      const pos = uavEntity.position.getValue(viewer.clock.currentTime);
      if (pos) {
        const cartographic = Cesium.Cartographic.fromCartesian(pos);
        rescueCoords.lng = Cesium.Math.toDegrees(cartographic.longitude);
        rescueCoords.lat = Cesium.Math.toDegrees(cartographic.latitude);
        // 让浮窗/标记在无人机上方以避免重叠
        rescueCoords.height = cartographic.height + 8.0;
      }
    }
  }

  if (rescuePopup.show) {
    const cartesian = Cesium.Cartesian3.fromDegrees(rescueCoords.lng, rescueCoords.lat, rescueCoords.height);
    const canvasPosition = viewer.scene.cartesianToCanvasCoordinates(cartesian);
    if (canvasPosition) {
      rescuePopup.x = canvasPosition.x;
      rescuePopup.y = canvasPosition.y - 45;
    }
  }

  // 更新无人车浮窗坐标与数据 (仅在到达现场后显示，也就是 activePhaseIndex >= 7)
  if (props.activePhaseIndex >= 7) {
    const isTanker = props.focusedPointId === 'accident_red';
    const carPosCallback = isTanker ? sharedTankerRescueCarPosition : sharedTruckRescueCarPosition;
    
    if (carPosCallback) {
      const pos = carPosCallback.getValue(viewer.clock.currentTime);
      if (pos) {
        const canvasPos = viewer.scene.cartesianToCanvasCoordinates(pos);
        if (canvasPos) {
          // A车在左侧，B车在右侧，稍微错开
          ugvA.x = canvasPos.x - 220;
          ugvA.y = canvasPos.y - 120;
          ugvB.x = canvasPos.x + 20;
          ugvB.y = canvasPos.y - 120;

          // 关联真实的全局传感数据
          ugvA.temp = props.sensorData?.temp || 0;
          ugvA.hum = props.sensorData?.humidity || 0;
          ugvA.smoke = props.sensorData?.smoke || 0;
          ugvA.tvoc = props.sensorData?.tvoc || 0;
          ugvA.co = props.sensorData?.co || 0;

          // 无人车 B 作为辅助节点，制造合理的微小偏差以体现多设备空间差异
          ugvB.temp = +(ugvA.temp - 0.45).toFixed(2);
          ugvB.hum = +(ugvA.hum - 2.12).toFixed(2);
          ugvB.smoke = Math.max(0, Math.floor(ugvA.smoke * 0.95));
          ugvB.tvoc = Math.max(0, +(ugvA.tvoc * 0.88).toFixed(3));
          ugvB.co = Math.max(0, +(ugvA.co * 0.92).toFixed(1));
        } else {
          ugvA.x = -1000; ugvA.y = -1000;
          ugvB.x = -1000; ugvB.y = -1000;
        }
      }
    }
  } else {
    ugvA.x = -1000; ugvA.y = -1000;
    ugvB.x = -1000; ugvB.y = -1000;
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

// 绘制湖北省行政边界外框线 (霓虹发光材质)
function drawBoundaryLine(coords) {
  if (!viewer) return;
  const positions = convertCoordsToCartesians(coords);
  viewer.entities.add({
    name: '湖北省行政边界',
    polyline: {
      positions: positions,
      width: 4.5,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.22,
        color: Cesium.Color.fromCssColorString('#00ffff') // 蓝绿色发光边界
      }),
      clampToGround: true
    }
  });
}

// 绘制市级行政区区划边界与点击面 (霓虹发光材质与半透明填充)
function drawCityBoundary(coords, colorStr, name, id) {
  if (!viewer) return;
  const positions = convertCoordsToCartesians(coords);
  
  // 1. 霓虹发光边线
  viewer.entities.add({
    id: id + '-line',
    name: name,
    polyline: {
      positions: positions,
      width: 5.5, // 稍微加粗，使市级边界显眼
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.26,
        color: Cesium.Color.fromCssColorString(colorStr)
      }),
      clampToGround: true
    }
  });

  // 2. 填充的多边形 (设置挤出高度，使其成为具有上浮效果的三维立体模块，并能接收点击事件)
  viewer.entities.add({
    id: id,
    name: name,
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      material: Cesium.Color.fromCssColorString(colorStr).withAlpha(0.15), // 提高透明度让立体感更强
      extrudedHeight: 12000, // 赋予12公里厚度，使其成为明显的三维立体控板
      outline: false
    }
  });
}

// 异步加载湖北省仙桃市与黄冈市的行政区划边界数据，并用亮色边界和填充面描绘出来
async function loadCityBoundaries() {
  if (!viewer) return;

  // 1. 仙桃市边界 ( adcode: 429004 ) - 使用亮粉红/粉紫色霓虹发光与半透明面
  try {
    const response = await fetch('/Dashboard/xiantao.json');
    if (!response.ok) throw new Error('读取 xiantao.json 失败');
    const geojson = await response.json();
    
    geojson.features.forEach(feature => {
      const geometry = feature.geometry;
      if (geometry.type === 'Polygon') {
        drawCityBoundary(geometry.coordinates[0], '#ff007f', '仙桃市', 'city-boundary-xiantao');
      } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach((polygon, idx) => {
          drawCityBoundary(polygon[0], '#ff007f', '仙桃市', 'city-boundary-xiantao-' + idx);
        });
      }
    });
    console.log('[Cesium] 仙桃市行政边界加载成功');
  } catch (error) {
    console.error('加载仙桃市行政边界时出错:', error);
  }

  // 2. 黄冈市边界 ( adcode: 421100 ) - 使用明亮黄/金黄色霓虹发光与半透明面
  try {
    const response = await fetch('/Dashboard/huanggang.json');
    if (!response.ok) throw new Error('读取 huanggang.json 失败');
    const geojson = await response.json();
    
    geojson.features.forEach(feature => {
      const geometry = feature.geometry;
      if (geometry.type === 'Polygon') {
        drawCityBoundary(geometry.coordinates[0], '#ffd700', '黄冈市', 'city-boundary-huanggang');
      } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach((polygon, idx) => {
          drawCityBoundary(polygon[0], '#ffd700', '黄冈市', 'city-boundary-huanggang-' + idx);
        });
      }
    });
    console.log('[Cesium] 黄冈市行政边界加载成功');
  } catch (error) {
    console.error('加载黄冈市行政边界时出错:', error);
  }
}

// 异步加载湖北省行政区划边界数据，并建立反向蒙版 (遮罩层)
async function loadHubeiMask() {
  if (!viewer) return;
  try {
    const response = await fetch('/Dashboard/hubei.json');
    if (!response.ok) throw new Error('读取 hubei.json 失败');
    const geojson = await response.json();

    const holes = [];
    geojson.features.forEach(feature => {
      const geometry = feature.geometry;
      if (geometry.type === 'Polygon') {
        const outerRing = convertCoordsToCartesians(geometry.coordinates[0]);
        holes.push(new Cesium.PolygonHierarchy(outerRing));
        drawBoundaryLine(geometry.coordinates[0]);
      } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach(polygon => {
          const outerRing = convertCoordsToCartesians(polygon[0]);
          holes.push(new Cesium.PolygonHierarchy(outerRing));
          drawBoundaryLine(polygon[0]);
        });
      }
    });

    // 建立一个安全的大范围外圈多边形（避免南北极和经度 180 度折叠/纠缠造成的渲染失败）
    const worldPolygonHierarchy = new Cesium.PolygonHierarchy(
      Cesium.Cartesian3.fromDegreesArray([
        50, 65,
        160, 65,
        160, 5,
        50, 5
      ]),
      holes
    );

    // 将湖北省作为“空洞”添加到这个多边形中，实现反向遮罩：
    // 湖北省外区域被深蓝黑色（匹配大屏底色）遮盖，仅有湖北省内部保持透明以显示遥感地图与地形
    viewer.entities.add({
      id: 'hubei-mask',
      name: '湖北省行政边界反向遮罩',
      polygon: {
        hierarchy: worldPolygonHierarchy,
        material: Cesium.Color.fromCssColorString('#070b19').withAlpha(0.96), // 贴合大屏的极简深邃蓝底色
        classificationType: Cesium.ClassificationType.BOTH,
        outline: false
      }
    });

  } catch (error) {
    console.error('加载湖北省行政边界蒙版时出错:', error);
  }
}

async function initViewer() {
  console.log('[Cesium] 开始初始化三维地球...')
  if (!containerRef.value || viewer) {
    console.log('[Cesium] 容器不存在或已初始化')
    return
  }
  console.log('[Cesium] 容器元素:', containerRef.value)
  console.log('[Cesium] 容器尺寸:', containerRef.value.offsetWidth, 'x', containerRef.value.offsetHeight)
  
  try {
    console.log('[Cesium] 创建 Viewer 实例...')
    viewer = new Cesium.Viewer(containerRef.value, {
      animation: false, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
      infoBox: false, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
      timeline: false, shouldAnimate: true, skyAtmosphere: false,
    })
    window.viewer = viewer
    console.log('[Cesium] Viewer 实例创建成功')
    
    // 关闭地球物理光照（防止因为时差导致场景处于黑夜）
    viewer.scene.globe.enableLighting = false
    
    // 关键修复：添加“相机头灯”，将环境光强制绑定到相机视角前方，这样不管什么角度看模型，模型都是被照亮的
    viewer.scene.light = new Cesium.DirectionalLight({
      direction: viewer.camera.direction
    })
    viewer.scene.preRender.addEventListener(function(scene, time) {
      scene.light.direction = Cesium.Cartesian3.clone(scene.camera.directionWC, scene.light.direction)
    })

     viewer.cesiumWidget.creditContainer.style.display = 'none'

    // 临时调试点击事件，获取道路精确坐标
    const debugHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    debugHandler.setInputAction(function (movement) {
      // 优先检测是否点击了三维立体控板
      const pickedObject = viewer.scene.pick(movement.position);
      if (Cesium.defined(pickedObject) && pickedObject.id) {
        const pickedId = String(pickedObject.id.id);
        if (pickedId.startsWith('city-boundary-xiantao') || pickedId === 'marker-accident_blue') {
          router.push('/simulation?city=xiantao');
          return;
        } else if (pickedId.startsWith('city-boundary-huanggang') || pickedId === 'marker-accident_red') {
          router.push('/simulation?city=huanggang');
          return;
        }
      }

      // 临时调试点击事件，获取道路精确坐标
      const ray = viewer.camera.getPickRay(movement.position);
      const cartesian = viewer.scene.globe.pick(ray, viewer.scene);
      if (cartesian) {
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
        const longitudeString = Cesium.Math.toDegrees(cartographic.longitude).toFixed(6);
        const latitudeString = Cesium.Math.toDegrees(cartographic.latitude).toFixed(6);
        console.log(`[CLICK_COORDS] lng: ${longitudeString}, lat: ${latitudeString}`);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    viewer.imageryLayers.removeAll()
    console.log('[Cesium] 加载 ArcGIS 影像图层...')
    try {
      const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
        'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
      )
      viewer.imageryLayers.addImageryProvider(imagery)
      console.log('[Cesium] ArcGIS 影像图层加载成功')
    } catch (e) {
      console.warn('[Cesium] ArcGIS 影像图层加载失败，使用默认底图:', e.message)
      viewer.imageryLayers.addImageryProvider(new Cesium.createWorldImagery())
    }

    // 加载湖北省行政边界反向蒙版
    try {
      await loadHubeiMask()
    } catch (e) {
      console.warn('初始化湖北省遮罩蒙版时出现警告:', e.message)
    }

    // 加载仙桃市和黄冈市行政边界
    try {
      await loadCityBoundaries()
    } catch (e) {
      console.warn('初始化仙桃市和黄冈市边界时出现警告:', e.message)
    }

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
    viewer.scene.postRender.addEventListener(updatePopupPosition)

    loading.value = false
  } catch (error) {
    errorMessage.value = '三维地球初始化失败'
    loading.value = false
    console.error('三维地球初始化失败:', error)
  }
}

function updateTruckSequence(phaseIndex, pointId = '') {
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

  const isTruckFocus = pointId === 'accident_blue' || props.focusedPointId === 'accident_blue';

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
function updateTankerSequence(phaseIndex, pointId = '') {
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
  const isTankerFocus = pointId === 'accident_red' || props.focusedPointId === 'accident_red';

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
      diffusionParticle.emissionRate = 100.0; // 提升初始浓度
    } else if (phaseIndex >= 5) {
      diffusionParticle.emissionRate = 180.0; // 显著增强，提供大范围浓烈雾气效果
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
  focusAreaEntity = viewer.entities.add({
    id: 'event-area',
    show: false,
    position: Cesium.Cartesian3.fromDegrees(114.35, 30.55, 0),
    ellipse: {
      semiMinorAxis: 150000, semiMajorAxis: 190000, material: toCesiumColor('#00e5ff', 0.06),
      outline: true, outlineColor: toCesiumColor('#00e5ff', 0.32), height: 0,
    },
  })

  // 创建高精度绿色救援装备图标
  const rescueSvgIcon = `data:image/svg+xml;utf8,` + encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="48" height="48">
      <polygon points="50,5 95,30 95,75 50,98 5,75 5,30" fill="rgba(0, 229, 90, 0.18)" stroke="#00e575" stroke-width="6"/>
      <path d="M25,50 L40,50 M60,50 L75,50 M50,25 L50,40 M50,60 L50,75 M35,35 L65,65 M35,65 L65,35" stroke="#00e575" stroke-width="5"/>
      <circle cx="50" cy="50" r="10" fill="#00e575"/>
    </svg>
  `);

  rescueMarkerEntity = viewer.entities.add({
    id: 'rescue-marker',
    position: new Cesium.CallbackProperty(() => {
      return Cesium.Cartesian3.fromDegrees(rescueCoords.lng, rescueCoords.lat, rescueCoords.height);
    }, false),
    billboard: {
      image: rescueSvgIcon,
      width: 24,
      height: 24,
      heightReference: Cesium.HeightReference.NONE,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM
    },
    show: false
  });

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
    let positionCallback;
    if (point.id === 'accident_blue') {
      positionCallback = new Cesium.CallbackProperty(() => {
        return Cesium.Cartesian3.fromDegrees(Number(truckPointAdjust.lng) || point.longitude, Number(truckPointAdjust.lat) || point.latitude, 0);
      }, false);
    } else if (point.id === 'accident_red') {
      positionCallback = new Cesium.CallbackProperty(() => {
        return Cesium.Cartesian3.fromDegrees(Number(tankerPointAdjust.lng) || point.longitude, Number(tankerPointAdjust.lat) || point.latitude, 0);
      }, false);
    } else {
      positionCallback = Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, 0);
    }
    
    viewer.entities.add({
      id: `marker-${point.id}`,
      position: positionCallback,
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
        // 阶段 >= 8：无人机围绕事故点做圆周绕飞拍照 (绕远一点，且只绕一圈)
        if (!uavOrbitStartTime) {
          uavOrbitStartTime = Date.now();
        }
        const elapsed = Date.now() - uavOrbitStartTime;
        const period = 12000; // 12秒绕一圈
        const rawAngle = (elapsed / period) * 2.0 * Math.PI;
        const angle = Math.min(rawAngle, 2.0 * Math.PI); // 限制只绕一圈
        
        // 绕飞半径调大 (绕远一点，约 50 米)
        const radiusLng = 0.00055;
        const radiusLat = 0.00045;
        
        const currentLng = targetLng + radiusLng * Math.cos(angle);
        const currentLat = targetLat + radiusLat * Math.sin(angle);

        // 触发多角度照片拍摄状态 (在圆周飞行不同弧度时拍照)
        if (angle >= 0.5 * Math.PI && !capturedPhotos.value[0]) {
          capturedPhotos.value[0] = true;
          activePhotoIndex.value = 0;
          triggerPhotoAnimation(0, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight));
        }
        if (angle >= 1.0 * Math.PI && !capturedPhotos.value[1]) {
          capturedPhotos.value[1] = true;
          activePhotoIndex.value = 1;
          triggerPhotoAnimation(1, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight));
        }
        if (angle >= 1.5 * Math.PI && !capturedPhotos.value[2]) {
          capturedPhotos.value[2] = true;
          activePhotoIndex.value = 2;
          triggerPhotoAnimation(2, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight));
        }
        if (angle >= 2.0 * Math.PI && !capturedPhotos.value[3]) {
          capturedPhotos.value[3] = true;
          activePhotoIndex.value = 3;
          triggerPhotoAnimation(3, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight));
        }

        return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight);
      }
    }, false);

    const uavOrientation = new Cesium.CallbackProperty(() => {
      const pos = uavPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;

      let headingRad;
      if (props.activePhaseIndex >= 8) {
        // 计算无人机当前位置指向事故中心的朝向角度，使其镜头始终对准事故车拍照
        const targetLng = Number(truckAdjust.lng) || 113.104833;
        const targetLat = Number(truckAdjust.lat) || 30.385469;
        
        // 从当前位置转换出经纬度
        const carto = Cesium.Cartographic.fromCartesian(pos);
        const currentLng = Cesium.Math.toDegrees(carto.longitude);
        const currentLat = Cesium.Math.toDegrees(carto.latitude);
        
        // 朝向目标点的弧度：Cesium 航向角 0 度为正北，顺时针方向增加
        headingRad = Math.PI / 2 - Math.atan2(targetLat - currentLat, targetLng - currentLng);
      } else {
        const headingDeg = Number(uavAdjust.heading) || 18;
        headingRad = Cesium.Math.toRadians(headingDeg);
      }

      const hpr = new Cesium.HeadingPitchRoll(headingRad, 0, 0);
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

    sharedTruckRescueCarPosition = rescueCarPosition;

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
      const targetLng = Number(tankerPointAdjust.lng) || 114.8945;
      const targetLat = Number(tankerPointAdjust.lat) || 30.632161;

      if (props.activePhaseIndex <= 7) {
        if (sharedTankerRescueCarPosition) {
          const carPos = sharedTankerRescueCarPosition.getValue(viewer.clock.currentTime);
          if (carPos) {
            const cartographic = Cesium.Cartographic.fromCartesian(carPos);
            const lng = Cesium.Math.toDegrees(cartographic.longitude);
            const lat = Cesium.Math.toDegrees(cartographic.latitude);
            // 无人机一直在两辆车（救援车和事故点上的油罐车）的中间
            const midLng = lng + 0.5 * (targetLng - lng);
            const midLat = lat + 0.5 * (targetLat - lat);
            return Cesium.Cartesian3.fromDegrees(midLng, midLat, startHeight);
          }
        }
        
        const startLng = Number(tankerRescueCarAdjust.lng) || 114.895791;
        const startLat = Number(tankerRescueCarAdjust.lat) || 30.631361;
        const midLng = startLng + 0.5 * (targetLng - startLng);
        const midLat = startLat + 0.5 * (targetLat - startLat);
        return Cesium.Cartesian3.fromDegrees(midLng, midLat, startHeight);
      } else {
        // 阶段 >= 8：先从两车中间飞向绕飞起点，再围绕事故点做圆周绕飞拍照 (只绕一圈)
        if (!tankerUavOrbitStartTime) {
          tankerUavOrbitStartTime = Date.now();
        }
        const elapsed = Date.now() - tankerUavOrbitStartTime;
        
        // 获取救援车当前位置（与阶段7保持一致）
        let carLng, carLat;
        if (sharedTankerRescueCarPosition) {
          const carPos = sharedTankerRescueCarPosition.getValue(viewer.clock.currentTime);
          if (carPos) {
            const cartographic = Cesium.Cartographic.fromCartesian(carPos);
            carLng = Cesium.Math.toDegrees(cartographic.longitude);
            carLat = Cesium.Math.toDegrees(cartographic.latitude);
          } else {
            const startLng = Number(tankerRescueCarAdjust.lng) || 114.895791;
            const startLat = Number(tankerRescueCarAdjust.lat) || 30.631361;
            carLng = startLng + TANKER_STOP_FACTOR * (targetLng - startLng);
            carLat = startLat + TANKER_STOP_FACTOR * (targetLat - startLat);
          }
        } else {
          const startLng = Number(tankerRescueCarAdjust.lng) || 114.895791;
          const startLat = Number(tankerRescueCarAdjust.lat) || 30.631361;
          carLng = startLng + TANKER_STOP_FACTOR * (targetLng - startLng);
          carLat = startLat + TANKER_STOP_FACTOR * (targetLat - startLat);
        }

        // 起点：前一阶段的终点（两车中间点）- 与阶段7保持一致的计算方式
        const uavStartLng = carLng + 0.5 * (targetLng - carLng);
        const uavStartLat = carLat + 0.5 * (targetLat - carLat);

        // 绕飞开始
        const orbitDuration = 12000;
        
        // 计算无人机当前位置相对于事故点的初始角度和半径
        const dLng = uavStartLng - targetLng;
        const dLat = uavStartLat - targetLat;
        const radius = Math.sqrt(dLng * dLng + dLat * dLat);
        const startAngle = Math.atan2(dLat, dLng);

        if (elapsed < orbitDuration) {
          // 1. 围绕事故点进行圆周绕飞拍照 (顺时针，角度递减 2*PI)
          const rawAngle = startAngle - (elapsed / orbitDuration) * 2.0 * Math.PI;
          const angle = Math.max(rawAngle, startAngle - 2.0 * Math.PI); // 限制只绕一圈
          
          const currentLng = targetLng + radius * Math.cos(angle);
          const currentLat = targetLat + radius * Math.sin(angle);
          
          // 触发多角度照片拍摄状态 (根据经过的角度比例)
          const angleDiff = startAngle - angle; // 从 0 增加到 2*PI
          if (angleDiff >= 0.5 * Math.PI && !capturedPhotos.value[0]) {
            capturedPhotos.value[0] = true;
            activePhotoIndex.value = 0;
            triggerPhotoAnimation(0, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
          }
          if (angleDiff >= 1.0 * Math.PI && !capturedPhotos.value[1]) {
            capturedPhotos.value[1] = true;
            activePhotoIndex.value = 1;
            triggerPhotoAnimation(1, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
          }
          if (angleDiff >= 1.5 * Math.PI && !capturedPhotos.value[2]) {
            capturedPhotos.value[2] = true;
            activePhotoIndex.value = 2;
            triggerPhotoAnimation(2, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
          }
          if (angleDiff >= 1.95 * Math.PI && !capturedPhotos.value[3]) {
            capturedPhotos.value[3] = true;
            activePhotoIndex.value = 3;
            triggerPhotoAnimation(3, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
          }

          return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight);
        } else {
          // 2. 绕飞结束，悬停在终点（即起点位置）
          if (!capturedPhotos.value[3]) {
            capturedPhotos.value[3] = true;
            activePhotoIndex.value = 3;
            triggerPhotoAnimation(3, Cesium.Cartesian3.fromDegrees(uavStartLng, uavStartLat, startHeight));
          }
          return Cesium.Cartesian3.fromDegrees(uavStartLng, uavStartLat, startHeight);
        }
      }
    }, false);

    const tankerUavOrientation = new Cesium.CallbackProperty(() => {
      const pos = tankerUavPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;

      let headingRad;
      if (props.activePhaseIndex >= 8) {
        // 计算无人机当前位置指向事故中心的朝向角度，使其镜头始终对准事故车拍照
        const targetLng = Number(tankerPointAdjust.lng) || 114.8945;
        const targetLat = Number(tankerPointAdjust.lat) || 30.632161;
        
        const carto = Cesium.Cartographic.fromCartesian(pos);
        const currentLng = Cesium.Math.toDegrees(carto.longitude);
        const currentLat = Cesium.Math.toDegrees(carto.latitude);
        
        headingRad = Math.PI / 2 - Math.atan2(targetLat - currentLat, targetLng - currentLng);
      } else {
        const headingDeg = Number(tankerUavAdjust.heading) || 18;
        headingRad = Cesium.Math.toRadians(headingDeg);
      }

      const hpr = new Cesium.HeadingPitchRoll(headingRad, 0, 0);
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
      const startLng = Number(tankerRescueCarAdjust.lng) || 114.895791;
      const startLat = Number(tankerRescueCarAdjust.lat) || 30.631361;
      const startHeight = Number(tankerRescueCarAdjust.height) || -1.5;

      const targetLng = Number(tankerPointAdjust.lng) || 114.8945;
      const targetLat = Number(tankerPointAdjust.lat) || 30.632161;
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

        const actualTargetLng = startLng + TANKER_STOP_FACTOR * (targetLng - startLng);
        const actualTargetLat = startLat + TANKER_STOP_FACTOR * (targetLat - startLat);

        const lng = startLng + (actualTargetLng - startLng) * easeT;
        const lat = startLat + (actualTargetLat - startLat) * easeT;
        const height = startHeight + (targetHeight - startHeight) * easeT;
        return Cesium.Cartesian3.fromDegrees(lng, lat, height);
      } else {
        const actualTargetLng = startLng + TANKER_STOP_FACTOR * (targetLng - startLng);
        const actualTargetLat = startLat + TANKER_STOP_FACTOR * (targetLat - startLat);
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
      
      let emitId = null;
      if (entityId === 'accident_blue' || entityId === 'marker-accident_blue' || entityId === 'model_normal' || entityId === 'model_accident') {
        emitId = 'accident_blue';
      } else if (entityId === 'accident_red' || entityId === 'marker-accident_red' || entityId === 'tanker_normal' || entityId === 'tanker_accident') {
        emitId = 'accident_red';
      }
      
      if (emitId) {
        emit('accident-picked', emitId);
        zoomToPoint(emitId);
      }
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}

function updatePhaseScene(index) {
  if (!viewer || !props.phases.length || !focusAreaEntity) return

  try {
    if (index !== 7) {
      phase7StartTime = 0;
    }
    if (index !== 8) {
      uavOrbitStartTime = 0;
      tankerUavOrbitStartTime = 0;
      capturedPhotos.value = [false, false, false, false];
      activePhotoIndex.value = null;
    }
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
      updateTruckSequence(index, pointId)
      if (leakParticle) leakParticle.show = false
      if (diffusionParticle) diffusionParticle.show = false
    } else if (pointId === 'accident_red') {
      updateTankerSequence(index, pointId)
      if (smokeParticle) smokeParticle.show = false
      if (fireParticle) fireParticle.show = false
    } else {
      if (smokeParticle) smokeParticle.show = false
      if (fireParticle) fireParticle.show = false
      if (leakParticle) leakParticle.show = false
      if (diffusionParticle) diffusionParticle.show = false
    }

    focusAreaEntity.position = Cesium.Cartesian3.fromDegrees(lng, lat, 0)

    // 悬浮窗展示逻辑：在货车追尾现场和油罐车泄露现场的“无人装备出动阶段”(索引 6) 和 “无人感知部署阶段”(索引 7) 显示
    const isTruckScene = (pointId === 'accident_blue');
    const isTankerScene = (pointId === 'accident_red');

    if (isTruckScene && index === 6) {
      rescuePopup.title = '救援装备出动';
      rescuePopup.status = '已出发';
      rescueCoords.lng = 113.10725;
      rescueCoords.lat = 30.38491;
      rescueCoords.height = 24.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
    } else if (isTruckScene && index === 7) {
      rescuePopup.title = '无人机感知部署';
      rescuePopup.status = '已到达';
      rescueCoords.lng = 113.104833;
      rescueCoords.lat = 30.385469;
      rescueCoords.height = 24.0;
      
      // 飞行/行驶动画耗时约6秒，在第5秒（即将到达的最后一秒）再显示标记和悬浮窗，避免突兀
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
      
      setTimeout(() => {
        if (props.focusedPointId === 'accident_blue' && Number(props.activePhaseIndex) === 7) {
          if (rescueMarkerEntity) rescueMarkerEntity.show = true;
          rescuePopup.show = true;
        }
      }, 5000);
    } else if (isTankerScene && index === 6) {
      rescuePopup.title = '救援装备出动';
      rescuePopup.status = '已出发';
      // 跟随无人机位置，悬浮窗显示在无人机头顶上方
      rescueCoords.lng = tankerUavAdjust.lng;
      rescueCoords.lat = tankerUavAdjust.lat;
      rescueCoords.height = tankerUavAdjust.height + 8.0; // 显示在无人机头顶上方
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
    } else if (isTankerScene && index === 7) {
      rescuePopup.title = '无人机感知部署';
      rescuePopup.status = '已到达';
      // 油罐车事故点 (使用动态的 tankerPointAdjust)
      rescueCoords.lng = tankerPointAdjust.lng;
      rescueCoords.lat = tankerPointAdjust.lat;
      rescueCoords.height = 17.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
      
      setTimeout(() => {
        if (props.focusedPointId === 'accident_red' && Number(props.activePhaseIndex) === 7) {
          if (rescueMarkerEntity) rescueMarkerEntity.show = true;
          rescuePopup.show = true;
        }
      }, 5000);
    } else {
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
    }
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

// 监听油罐车事故点位置与车身朝向变化同步更新泄露与弥漫效果位置
watch([() => tankerPointAdjust.lng, () => tankerPointAdjust.lat, () => tankerAdjust.heading], () => {
  if (typeof tankerPointAdjust.lng !== 'number' || typeof tankerPointAdjust.lat !== 'number') return;
  
  // 泄露粒子系统使用车身朝向对齐的坐标系，使侧向喷射角度正确
  const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(tankerAdjust.heading) || 36), 0, 0);
  const leakMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(Cesium.Cartesian3.fromDegrees(tankerPointAdjust.lng, tankerPointAdjust.lat, 0.8), hpr);
  if (leakParticle) leakParticle.modelMatrix = leakMatrix;

  // 弥漫粒子系统保持 ENU 坐标系以利于风向漂移
  const diffMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(tankerPointAdjust.lng, tankerPointAdjust.lat, 0.0));
  if (diffusionParticle) diffusionParticle.modelMatrix = diffMatrix;
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

function resetView() {
  if (!viewer || isFlying) return
  stopAutoRotate()
  isFlying = true
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(112.5, 30.6, 1200000),
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-90),
      roll: 0.0
    },
    duration: 1.5,
    complete: () => {
      isFlying = false
    }
  })
  console.log('地图已重置回湖北全图概览')
}

defineExpose({ zoomToPoint, resetView, capturedPhotos, activePhotoIndex, currentTimeStr });

watch(() => props.activePhaseIndex, (next, prev) => {
  if (next === 7 && prev !== 7) {
    phase7StartTime = Date.now();
    tankerPhase7StartTime = Date.now();
  } else if (next < 7) {
    phase7StartTime = 0;
    tankerPhase7StartTime = 0;
  }
  
  if (next >= 4 && (prev < 4 || !diffusionStartTime)) {
    diffusionStartTime = Date.now();
  } else if (next < 4) {
    diffusionStartTime = 0;
  }
  updatePhaseScene(next);
});

watch(() => props.focusedPointId, () => {
  updatePhaseScene(props.activePhaseIndex);
});

onMounted(() => {
  initViewer()
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
})
onBeforeUnmount(() => {
  stopAutoRotate()
  if (timeInterval) clearInterval(timeInterval)
  if (viewer) {
    viewer.scene.postRender.removeEventListener(updateModelsReadyStatus)
    viewer.scene.postRender.removeEventListener(updatePopupPosition)
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

/* 无人机拍照侦察悬浮窗样式 */
.uav-photo-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  width: 350px;
  background: rgba(7, 11, 25, 0.9);
  border: 1px solid rgba(0, 255, 255, 0.45);
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.65), 0 0 12px rgba(0, 255, 255, 0.2);
  z-index: 1000;
  overflow: hidden;
  backdrop-filter: blur(10px);
  animation: photoPanelFadeIn 0.3s ease-out;
  pointer-events: auto;
}

.uav-photo-header {
  background: rgba(0, 255, 255, 0.12);
  border-bottom: 1px solid rgba(0, 255, 255, 0.25);
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.uav-photo-icon {
  font-size: 14px;
}

.uav-photo-title {
  color: #00ffff;
  font-size: 13px;
  font-weight: bold;
  letter-spacing: 0.5px;
}

.uav-status-tag {
  margin-left: auto;
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(255, 169, 64, 0.15);
  color: #ffa940;
  border: 1px solid rgba(255, 169, 64, 0.35);
  border-radius: 4px;
  font-weight: bold;
  white-space: nowrap;
}

.uav-status-tag.status-done {
  background: rgba(82, 196, 26, 0.15);
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.35);
}

.uav-photo-content {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.uav-main-photo-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: #000;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.uav-photo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #888;
  font-size: 12px;
  gap: 10px;
}

.radar-scan {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px dashed #00ffff;
  animation: spin 3s linear infinite;
}

.uav-photo-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 模拟多角度透视和裁剪效果 */
.photo-angle-0 {
  transform: scale(1.0);
}
.photo-angle-1 {
  transform: scale(1.22) rotate(90deg);
}
.photo-angle-2 {
  transform: scale(1.15) scaleX(-1);
}
.photo-angle-3 {
  transform: scale(1.3) rotate(270deg);
}

.uav-photo-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.85), transparent);
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
  font-family: monospace;
  font-size: 11px;
}

.uav-photo-timestamp {
  color: #ff4d4f;
  font-weight: bold;
}

.uav-photo-coords {
  color: #00e5ff;
}

.uav-thumbnails-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
}

.uav-thumb-box {
  flex: 1;
  aspect-ratio: 16 / 10;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
  overflow: hidden;
  position: relative;
  cursor: not-allowed;
  transition: all 0.25s ease;
}

.uav-thumb-box.is-captured {
  border: 1px solid rgba(255, 255, 255, 0.3);
  cursor: pointer;
}

.uav-thumb-box.is-captured:hover {
  border-color: #00ffff;
  transform: translateY(-2px);
}

.uav-thumb-box.is-captured.is-active {
  border: 1.5px solid #00ffff;
  box-shadow: 0 0 8px rgba(0, 255, 255, 0.4);
}

.uav-thumb-inner {
  width: 100%;
  height: 100%;
  position: relative;
}

.uav-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-badge {
  position: absolute;
  top: 2px;
  left: 2px;
  background: rgba(0, 0, 0, 0.75);
  color: #00ffff;
  font-size: 8px;
  padding: 1px 3px;
  border-radius: 2px;
  font-family: monospace;
  font-weight: bold;
  border: 0.5px solid rgba(0, 255, 255, 0.3);
}

.uav-thumb-lock {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.4;
}

.lock-icon {
  font-size: 11px;
}

@keyframes photoPanelFadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 避难点 HTML 悬浮窗样式 */
.shelter-popup-panel {
  position: absolute;
  z-index: 1000;
  transform: translate(-50%, -100%);
  width: 170px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  font-family: "Microsoft YaHei", sans-serif;
  overflow: visible;
  pointer-events: auto;
}

.shelter-popup-header {
  background-color: #b49b1c; /* 芥末黄/金黄色 */
  color: white;
  padding: 4px 8px;
  font-weight: bold;
  font-size: 11px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
}

.shelter-popup-header .close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.shelter-popup-header .close-btn:hover {
  opacity: 0.8;
}

.shelter-popup-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  color: #333;
}

.shelter-popup-table td {
  padding: 4px 6px;
  border: 1px solid #dff0f6;
  text-align: center;
}

.shelter-popup-table td.label {
  background-color: #e0f0f5;
  color: #555;
  font-weight: bold;
  width: 45%;
}

.shelter-popup-table td.value {
  background-color: white;
  color: #333;
}

.shelter-popup-arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid white;
  filter: drop-shadow(0 2px 2px rgba(0, 0, 0, 0.15));
}
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

/* 无人车实时数据悬浮窗 - 赛博朋克深色主题 - 紧凑版 */
.ugv-panel {
  position: absolute;
  width: 175px;
  background: rgba(7, 11, 25, 0.85);
  border-radius: 5px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6), 0 0 8px rgba(0, 255, 255, 0.15);
  font-family: "JetBrains Mono", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #fff;
  z-index: 1000;
  pointer-events: none;
  overflow: hidden;
  border: 1px solid rgba(0, 255, 255, 0.25);
  backdrop-filter: blur(6px);
  transform: translate(-50%, -100%);
}

/* 顶部霓虹边框高光 */
.ugv-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00ffff, transparent);
}

.ugv-panel::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid rgba(0, 255, 255, 0.4);
  filter: drop-shadow(0 1px 3px rgba(0, 255, 255, 0.3));
}

.ugv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.12);
  background: rgba(0, 255, 255, 0.04);
}

.ugv-title {
  font-weight: bold;
  font-size: 11px;
  color: #00ffff;
  letter-spacing: 0.5px;
}

.ugv-status {
  font-size: 9px;
  color: #00ff88;
  font-weight: bold;
  padding: 1px 4px;
  background: rgba(0, 255, 136, 0.08);
  border: 1px solid rgba(0, 255, 136, 0.25);
  border-radius: 2px;
}

.ugv-data {
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ugv-row {
  display: flex;
  gap: 4px;
}

.ugv-item {
  flex: 1;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  padding: 4px 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: background 0.3s;
}

.ugv-item.full-width {
  flex: 100%;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.ugv-label {
  font-size: 10px;
  color: #8fa3b0;
}

.ugv-value {
  font-size: 11px;
  font-weight: 700;
  color: #e0f2fe;
  text-shadow: 0 0 4px rgba(224, 242, 254, 0.3);
}

.ugv-footer {
  text-align: right;
  padding: 5px 10px;
  font-size: 9px;
  color: #00ffff;
  background: rgba(0, 255, 255, 0.04);
  border-top: 1px solid rgba(0, 255, 255, 0.12);
  opacity: 0.8;
  cursor: pointer;
  pointer-events: auto;
  transition: opacity 0.2s, background 0.2s;
}

.ugv-footer:hover {
  opacity: 1;
  background: rgba(0, 255, 255, 0.12);
}

/* 城市行政区划说明悬浮窗样式 */
.city-popup-panel {
  position: absolute;
  z-index: 1000;
  transform: translate(-50%, -100%);
  width: 220px;
  background: rgba(7, 11, 25, 0.9);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6), 0 0 10px rgba(0, 229, 255, 0.2);
  font-family: "Microsoft YaHei", sans-serif;
  overflow: visible;
  pointer-events: auto;
  border: 1px solid rgba(0, 229, 255, 0.3);
  backdrop-filter: blur(8px);
  padding: 0;
  color: #ffffff;
}

.city-popup-header {
  background: linear-gradient(90deg, rgba(255, 0, 127, 0.2), rgba(255, 0, 127, 0.05));
  border-bottom: 1px solid rgba(255, 0, 127, 0.3);
  color: #ff007f;
  padding: 8px 12px;
  font-weight: bold;
  font-size: 13px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
}

.city-popup-header.is-huanggang {
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.2), rgba(255, 215, 0, 0.05));
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  color: #ffd700;
}

.city-popup-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.city-close-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.city-close-btn:hover {
  color: #ffffff;
}

.city-popup-body {
  padding: 10px 12px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.city-info-item {
  display: flex;
  line-height: 1.4;
}

.info-label {
  color: #8fa3b0;
  width: 65px;
  flex-shrink: 0;
}

.info-value {
  color: #e0f2fe;
}

.info-value.desc {
  text-align: justify;
}

.city-popup-arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid rgba(7, 11, 25, 0.9);
}

</style>

<style>
.flying-photo {
  position: fixed;
  z-index: 9999;
  background-size: cover;
  background-position: center;
  border: 2px solid #00e5ff;
  border-radius: 4px;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.8);
  transition: all 0.8s cubic-bezier(0.25, 1, 0.5, 1);
  pointer-events: none;
}
</style>
