<template>
  <div class="timeline-wrapper" :class="{ 'is-collapsed': isCollapsed }">
    <!-- 🔽 顶端中央折叠/展开收起按钮 -->
    <button 
      class="timeline-toggle-btn" 
      type="button" 
      @click="isCollapsed = !isCollapsed"
      :title="isCollapsed ? '展开事故推演时间轴' : '向下折叠收起时间轴'"
    >
      <span class="arrow-icon" :class="{ 'is-up': isCollapsed }">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M7 10l5 5 5-5z" />
        </svg>
      </span>
    </button>

    <section class="timeline-shell">
      <!-- 固定描述文本 -->
      <div v-if="currentPhaseDesc" class="timeline-phase-desc">
        {{ currentPhaseDesc }}
      </div>
      <div class="accident-header">
        <span class="accident-kicker">事故点</span>

        <div class="accident-select-box">
          <span class="status-dot"></span>
          <select :value="accidentIndex" @change="onAccidentChange" class="accident-native-select">
            <option v-for="(acc, index) in accidents" :key="acc.id" :value="index">
              {{ acc.title }}
            </option>
          </select>
          <span class="select-arrow">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
              <path d="M7 10l5 5 5-5z" />
            </svg>
          </span>
        </div>

        <button class="locate-btn" type="button" @click="handleLocate">
          <svg class="pin-icon" viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
          </svg>
          定位
        </button>

        <div class="simulation-status" @click="togglePlay" :class="{ disabled: !isScenarioReady }">
          <div class="play-trigger">
            <template v-if="isScenarioReady">
              <span v-if="!isPlaying" class="status-icon">▶</span>
              <span v-else class="status-icon">||</span>
              {{ isPlaying ? '仿真运行中' : '仿真已暂停' }}
            </template>
            <template v-else>
              <span class="loading-spinner"></span>
              模型加载中...
            </template>
          </div>
        </div>
      </div>

      <div class="timeline-bar-wrapper">
        <div class="timeline-bar">
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: fillWidth }"></div>
          </div>
          
          <!-- 游标指示器（仅在点击激活有效阶段 modelValue >= 0 时出现，未点击/未开始时不出现） -->
          <div v-if="modelValue >= 0" class="timeline-cursor" :style="{ left: cursorOffset }">
            <div class="cursor-arrow">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="#8cf7c5">
                <path d="M7 10l5 5 5-5z" />
              </svg>
            </div>
            <div class="cursor-line"></div>
          </div>

          <button
            v-for="(phase, index) in phases"
            :key="phase.id"
            type="button"
            class="phase-step"
            :class="{ active: index === modelValue, 'is-staggered': index % 2 !== 0 }"
            :style="{ left: getPhaseOffset(index) }"
            @click="selectPhase(index)"
          >
            <div class="phase-label-pill">
              {{ phase.shortLabel }}
              <span v-if="phasesReady[index]" class="ready-dot" title="模型已就绪"></span>
            </div>
            <span class="phase-dot"></span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  phases: { type: Array, default: () => [] },
  modelValue: { type: Number, default: 0 },
  accidents: { type: Array, default: () => [] },
  accidentIndex: { type: Number, default: 0 },
  phasesReady: { type: Array, default: () => [] },
  // 第 9 阶段的完成信号：四视角采集完成且三维重建模型可展示。
  reconstructionReady: { type: Boolean, default: false },
  // 来自三维场景的实时节奏表；会随车流和无人装备速度控制参数同步更新。
  playbackDurations: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'update:accidentIndex', 'locate', 'phaseClick'])

const isPlaying = ref(false)
const forceReady = ref(false)
const isCollapsed = ref(false)
let playbackTimer = null
let loadTimeout = null
let reconstructionReadyAt = 0
const RECONSTRUCTION_RESULT_HOLD_MS = 2000

// 自动播放节奏表（毫秒）。这里的停留时间与 HomeCesiumGlobe 中真正的
// 位移动画一一对应；末尾的缓冲时间用于让镜头、标注和动画终帧稳定下来。
//
// 关键动画来源：
// - 正常行驶/事故发生：模型单次动画 + 终帧展示；
// - 无人机出动：默认 6 秒航线飞行；
// - 无人机侦察：200 米末段飞行 8 秒；
// - 无人装备出动：货车场景 6 秒，油罐车场景的地面装备需 10 秒；
// - 无人感知部署：空、地装备最后 200 米均为 6 秒；
// - 无人感知执行：12 秒完成一圈航拍并触发四个拍摄节点。
const PLAYBACK_DURATION_MS = Object.freeze({
  initialize: 2500,
  normalDriving: 5500,
  accident: 5000,
  uavDispatch: 7000,
  uavReconnaissance: 9000,
  secondaryHazard: 6000,
  truckEquipmentDispatch: 7000,
  tankerEquipmentDispatch: 11000,
  sensorDeployment: 7000,
  sensorExecution: 13000,
  signalInterference: 4000
})

const TRUCK_PHASE_DESC = [
  { shortLabel: '仿真开始', time: '14:00', description: '数字孪生场景完成初始化，事故路段的四辆社会车辆按真实道路轨迹行驶；感知、通信与指挥链路进入持续监测状态。' },
  { shortLabel: '正常行驶', time: '14:05', description: '客车与前方车辆保持正常行驶，后方货车持续接近；边缘网关同步采集车速、车距与道路环境数据，为异常识别建立基线。' },
  { shortLabel: '事故发生', time: '14:12', description: '货车因疲劳驾驶未能保持安全车距，避让不及追尾客车；碰撞冲击数据触发一级告警，事故画面与位置随即上报指挥中心。' },
  { shortLabel: '无人机出动', time: '14:14', description: '指挥中心确认告警后派出先遣无人机，系统以三维 B 样条航线避开风险区域，引导无人机从基地快速飞往事故现场外围。' },
  { shortLabel: '无人机侦察', time: '14:15', description: '无人机抵达现场外约 200 米的安全侦察位，开始低空巡查与影像回传，为灾情等级研判和后续装备调度提供实时依据。' },
  { shortLabel: '次生灾害·烟雾', time: '14:18', description: '侦察发现发动机舱受热冒烟，烟雾开始向上扩散；环境传感器同步捕捉异常浓度，指挥中心将处置状态由事故响应升级为灾情预警。' },
  { shortLabel: '次生灾害·起火', time: '14:26', description: '燃油泄漏后被高温部件引燃，火势向车身蔓延；系统据此扩大危险区并进入空地协同处置准备状态。' },
  { shortLabel: '无人装备出动', time: '14:30', description: '无人机与无人车接收协同任务后同步集结，RCD/A* 规划避开路阻和禁飞约束，保障空地装备以可控时延抵近火场。' },
  { shortLabel: '无人感知部署', time: '14:35', description: '空地装备到达安全边界后完成最后 200 米接近，在预设坐标投放地面、空域与固定监测节点，形成覆盖事故核心区的感知网。' },
  { shortLabel: '无人感知执行', time: '14:40', description: '部署完成后，无人机环绕航拍并采集四视角影像，无人车持续采集地面数据；系统完成三维实景重建，形成“空—地—固定—基站”协同感知闭环。' },
  { shortLabel: '信号干扰', time: '14:45', description: '现场复杂电磁环境使基站通信受干扰；系统启动抗干扰自愈机制，将数据链路切换至搭载 Jetson 算力板的无人车，维持现场数据回传。' },
  { shortLabel: '救援装备出动', time: '14:50', description: '在稳定的数据链路支撑下，多智能体引擎基于真实 OSM 路网完成 Dijkstra 加权寻优，联动消防、医疗、公安、防化、路政五类力量沿最优路线协同出动。' },
]

const TANKER_PHASE_DESC = [
  { shortLabel: '仿真推演开始', time: '15:00', description: '危化品油罐车数字孪生场景完成初始化，车辆、道路与全域感知网络进入稳定运行状态，开始持续监测罐体与行驶姿态。' },
  { shortLabel: '车辆正常行驶', time: '15:05', description: '满载危化品的油罐车在省道正常行驶，车载传感器持续回传压力、温度和姿态数据，为后续风险变化建立正常基线。' },
  { shortLabel: '事故发生·侧翻', time: '15:12', description: '油罐车在弯道紧急避让时发生侧翻；碰撞与姿态异常触发一级告警，路侧影像和车辆状态同步送达指挥中心。' },
  { shortLabel: '无人机出动', time: '15:14', description: '指挥中心确认侧翻事故后派出无人机，从应急基地沿预定三维航线起飞，优先获取罐体周边的高空态势。' },
  { shortLabel: '无人机侦察', time: '15:15', description: '无人机到达安全侦察位，执行低空巡查与红外观测，回传罐体姿态、现场影像和泄漏风险线索，为危险区划定提供依据。' },
  { shortLabel: '次生灾害·泄露', time: '15:20', description: '侧翻冲击造成罐体缝隙泄露，TVOC 等指标快速升高；系统立即标记危险源并启动泄漏隔离与人员防护预警。' },
  { shortLabel: '次生灾害·弥漫', time: '15:35', description: '泄露介质在地面铺展并持续挥发，有毒有害气体向周边空域弥漫；系统据扩散态势扩大警戒区并推送疏散建议。' },
  { shortLabel: '无人装备出动', time: '15:40', description: '无人机与无人车按空地协同方案从基地集结出发，通过车机追赶和速比匹配抵近事故核心区，同时避开高风险污染范围。' },
  { shortLabel: '无人感知部署', time: '15:45', description: '装备在安全边界完成最后接近后，自动布设 TVOC、CO 等空地传感节点，形成围绕泄漏源的多维监测网格。' },
  { shortLabel: '无人感知执行', time: '15:50', description: '无人机环绕采集四视角影像并完成三维实景重建，无人车持续采集地面气体数据；空、地、固定节点与基站共同输出动态风险态势。' },
  { shortLabel: '信号干扰', time: '15:55', description: '复杂现场环境造成基站通信受强干扰；系统启动路由自愈，将现场数据链路切换至搭载 Jetson 模块的无人车，保障监测不中断。' },
  { shortLabel: '救援装备出动', time: '16:00', description: '稳定回传的灾情数据进入多智能体决策引擎，系统基于真实 OSM 路网筛选最优路线，联动消防、防化、医疗、公安、路政五类力量实施封堵与协同处置。' },
]

const currentPhaseDesc = computed(() => {
  const isTruck = props.accidentIndex === 0
  const phaseData = isTruck ? TRUCK_PHASE_DESC : TANKER_PHASE_DESC
  return phaseData[props.modelValue]?.description || ''
})

const isScenarioReady = computed(() => {
  if (forceReady.value) return true
  if (!props.phasesReady.length) return false
  const currentReady = props.phasesReady[props.modelValue]
  if (currentReady) return true
  return props.phasesReady.every(r => r === true)
})

// 1秒超时自动解锁，防止因为未显示阶段的后台模型加载而阻塞用户操作
watch(() => props.phasesReady, (newVal) => {
  if (loadTimeout) clearTimeout(loadTimeout)
  if (newVal.length > 0 && !newVal.every(r => r === true)) {
    loadTimeout = setTimeout(() => {
      forceReady.value = true
    }, 1000)
  } else {
    forceReady.value = false
  }
}, { immediate: true })

// 左右预留 40px 的边距，游标和阶段点在这个范围内移动
const cursorOffset = computed(() => {
  return getPhaseOffset(props.modelValue)
})

// 计算已播放部分的进度条宽度
const fillWidth = computed(() => {
  if (!props.phases.length || props.modelValue < 0) return '0%'
  if (props.phases.length === 1) return '0%'
  const percent = (props.modelValue / (props.phases.length - 1)) * 100
  return `${percent}%`
})

function getPhaseOffset(index) {
  if (!props.phases.length || index < 0) return '40px'
  if (props.phases.length === 1) return '50%'
  const percent = (index / (props.phases.length - 1)) * 100
  return `calc(40px + (100% - 80px) * ${percent / 100})`
}

function selectPhase(index) {
  isPlaying.value = false // 点击任意阶段节点（含【仿真开始】）均为手动切换该节点，不自动推进时间轴
  emit('update:modelValue', index)
  emit('phaseClick', index)
}

function onAccidentChange(event) {
  isPlaying.value = false
  emit('update:accidentIndex', Number(event.target.value))
}

function handleLocate() {
  emit('locate')
}

function togglePlay() {
  if (!isScenarioReady.value) return
  if (isPlaying.value) {
    isPlaying.value = false
  } else {
    // 如果已经到最后了，从头开始
    if (props.modelValue >= props.phases.length - 1) {
      emit('update:modelValue', 0)
    }
    isPlaying.value = true
  }
}

function getPlaybackDuration(currentIdx) {
  const measuredDuration = Number(props.playbackDurations?.[currentIdx])
  if (Number.isFinite(measuredDuration) && measuredDuration > 0) {
    return measuredDuration
  }

  const isTruck = props.phases[0]?.id.startsWith('t-')

  switch (currentIdx) {
    case 0: return PLAYBACK_DURATION_MS.initialize
    case 1: return PLAYBACK_DURATION_MS.normalDriving
    case 2: return PLAYBACK_DURATION_MS.accident
    case 3: return PLAYBACK_DURATION_MS.uavDispatch
    case 4: return PLAYBACK_DURATION_MS.uavReconnaissance
    case 5:
    case 6: return PLAYBACK_DURATION_MS.secondaryHazard
    case 7:
      // 油罐车场景的地面装备从基地集结到事故点需要 10 秒，
      // 因而取两类装备中较长的一段，防止其尚未到位就切换阶段。
      return isTruck
        ? PLAYBACK_DURATION_MS.truckEquipmentDispatch
        : PLAYBACK_DURATION_MS.tankerEquipmentDispatch
    case 8: return PLAYBACK_DURATION_MS.sensorDeployment
    case 9: return PLAYBACK_DURATION_MS.sensorExecution
    case 10: return PLAYBACK_DURATION_MS.signalInterference
    default: return PLAYBACK_DURATION_MS.signalInterference
  }
}

function advancePlayback(currentIdx) {
  if (!isPlaying.value) return

  // 第 9 阶段不能只依赖预估时长：浏览器性能或资源加载可能使重建稍晚完成。
  // 未收到完成信号时，游标保持在当前节点，待模型就绪后才继续。
  if (currentIdx === 9 && !props.reconstructionReady) {
    playbackTimer = setTimeout(() => advancePlayback(currentIdx), 250)
    return
  }

  // 三维模型切换为“已生成”后，固定保留两秒完整展示时间，
  // 避免用户刚看到重建结果就被时间轴切换到下一阶段。
  if (currentIdx === 9) {
    const readyAt = reconstructionReadyAt || Date.now()
    const remaining = RECONSTRUCTION_RESULT_HOLD_MS - (Date.now() - readyAt)
    if (remaining > 0) {
      playbackTimer = setTimeout(() => advancePlayback(currentIdx), remaining)
      return
    }
  }

  emit('update:modelValue', currentIdx + 1)
}

watch(
  () => [props.reconstructionReady, props.modelValue],
  ([isReady, phaseIndex]) => {
    if (Number(phaseIndex) !== 9 || !isReady) {
      reconstructionReadyAt = 0
    } else if (!reconstructionReadyAt) {
      reconstructionReadyAt = Date.now()
    }
  },
  { immediate: true }
)

// 自动播放逻辑
watch([isPlaying, () => props.modelValue], ([playing, currentIdx]) => {
  if (playbackTimer) clearTimeout(playbackTimer)
  
  if (playing && currentIdx < props.phases.length - 1) {
    const duration = getPlaybackDuration(currentIdx)

    playbackTimer = setTimeout(() => {
      advancePlayback(currentIdx)
    }, duration)
  } else if (currentIdx >= props.phases.length - 1) {
    isPlaying.value = false
  }
})

onBeforeUnmount(() => {
  if (playbackTimer) clearTimeout(playbackTimer)
  if (loadTimeout) clearTimeout(loadTimeout)
})
</script>

<style scoped>
.timeline-wrapper {
  position: relative;
  width: 100%;
  transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.timeline-wrapper.is-collapsed {
  transform: translateY(calc(100% - 10px));
}

.timeline-toggle-btn {
  position: absolute;
  top: -24px;
  left: 50%;
  transform: translateX(-50%);
  width: 56px;
  height: 24px;
  background: rgba(10, 15, 24, 0.95);
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-bottom: none;
  border-radius: 12px 12px 0 0;
  color: #00e5ff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  box-shadow: 0 -4px 15px rgba(0, 229, 255, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.timeline-toggle-btn:hover {
  background: rgba(0, 229, 255, 0.25);
  border-color: #00e5ff;
  box-shadow: 0 -6px 20px rgba(0, 229, 255, 0.5);
  height: 26px;
  top: -26px;
}

.arrow-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s ease;
}

.arrow-icon.is-up {
  transform: rotate(180deg);
}

.timeline-shell {
  padding: 12px 24px; /* 减小上下内边距 */
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(10, 15, 24, 0.85);
  backdrop-filter: blur(20px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
}

.timeline-phase-desc {
  width: 100%;
  padding: 4px 0 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 12px;
  color: rgba(186, 230, 253, 0.95);
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.5px;
  line-height: 1.6;
  text-align: left;
}

.accident-header {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 12px; /* 显著减小间距 */
}

.accident-kicker {
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 13px;
}

.accident-select-box {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 180px;
  height: 36px;
  padding: 0 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.05);
}

.status-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #00e5ff; margin-right: 10px;
}

.accident-native-select {
  flex: 1; background: transparent; border: none; color: #fff; font-size: 14px; outline: none; cursor: pointer;
}

.accident-native-select option {
  background: #0a0f18; /* 显式设置背景色 */
  color: #fff;
}

.locate-btn {
  display: flex; align-items: center; gap: 6px; height: 36px; padding: 0 16px; border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(255, 255, 255, 0.05); color: #fff; cursor: pointer;
}

.timeline-bar-wrapper {
  padding: 0 10px;
  margin-bottom: 12px; /* 减小间距 */
}

.timeline-bar {
  position: relative;
  height: 90px; /* 显著减小高度 (从140降到90) */
  display: flex;
  align-items: center;
}

.progress-track {
  position: absolute;
  left: 40px;
  right: 40px;
  top: 50%; /* 轨道居中 */
  transform: translateY(-50%);
  height: 10px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.15);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, #00e5ff, #8cf7c5);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.6);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.timeline-cursor {
  position: absolute;
  top: 0;
  bottom: 0; /* 贯穿整个轨道区域 */
  width: 2px;
  transform: translateX(-50%);
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 5;
  pointer-events: none;
}

.cursor-arrow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.cursor-line {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 0;
  border-left: 2px dashed #8cf7c5;
  opacity: 0.8;
}

.phase-step {
  position: absolute;
  top: 50%; /* 锚点居中 */
  transform: translate(-50%, -50%);
  background: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100px;
  padding: 0;
  z-index: 10;
}

.phase-label-pill {
  position: absolute;
  top: -38px; /* 标签上移距离减小 */
  left: 50%;
  transform: translateX(-50%);
  padding: 3px 12px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 13px; /* 略微缩小字号 */
  white-space: nowrap;
  transition: all 0.3s ease;
}

/* 错行排列：奇数索引的标签移到轨道下方 */
.phase-step.is-staggered .phase-label-pill {
  top: 18px; /* 标签下移距离减小 */
}

.phase-step.active .phase-label-pill {
  background: rgba(255, 255, 255, 0.2);
  border-color: #8cf7c5;
  box-shadow: 0 0 15px rgba(140, 247, 197, 0.2);
}

.phase-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #777;
  transition: all 0.3s ease;
  border: 2px solid #000;
}

.phase-step.active .phase-dot {
  background: #fff;
  box-shadow: 0 0 10px #fff;
  transform: scale(1.2);
}

.simulation-status {
  display: flex;
  align-items: center;
}

.play-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 16px;
  border-radius: 18px;
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid rgba(0, 229, 255, 0.35);
  color: #00e5ff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.play-trigger:hover:not(.disabled) {
  background: rgba(0, 229, 255, 0.2);
  border-color: rgba(0, 229, 255, 0.6);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.3);
}

.simulation-status.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ready-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00ff88;
  margin-left: 6px;
  box-shadow: 0 0 5px #00ff88;
  vertical-align: middle;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0, 229, 255, 0.3);
  border-top-color: #00e5ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.status-icon {
  font-family: monospace;
  font-weight: bold;
  letter-spacing: -2px;
}

@media (max-width: 1080px) {
  .phase-step { width: 80px; }
  .phase-label-pill { padding: 4px 10px; font-size: 12px; }
}
</style>
