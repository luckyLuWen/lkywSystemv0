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
          
          <!-- 游标指示器 -->
          <div class="timeline-cursor" :style="{ left: cursorOffset }">
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
  phasesReady: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'update:accidentIndex', 'locate'])

const isPlaying = ref(false)
const forceReady = ref(false)
const isCollapsed = ref(false)
let playbackTimer = null
let loadTimeout = null

// 只要有任何阶段（除了第一个）还没准备好，就认为场景未就绪
const isScenarioReady = computed(() => {
  if (forceReady.value) return true
  if (!props.phasesReady.length) return false
  return props.phasesReady.every(r => r === true)
})

// 5秒超时自动解锁，防止加载状态卡死
watch(() => props.phasesReady, (newVal) => {
  if (loadTimeout) clearTimeout(loadTimeout)
  if (newVal.length > 0 && !newVal.every(r => r === true)) {
    loadTimeout = setTimeout(() => {
      console.warn('模型加载超时，强制开启仿真控制')
      forceReady.value = true
    }, 5000)
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
  if (!props.phases.length) return '0%'
  if (props.phases.length === 1) return '0%'
  const percent = (props.modelValue / (props.phases.length - 1)) * 100
  return `${percent}%`
})

function getPhaseOffset(index) {
  if (!props.phases.length) return '40px'
  if (props.phases.length === 1) return '50%'
  const percent = (index / (props.phases.length - 1)) * 100
  return `calc(40px + (100% - 80px) * ${percent / 100})`
}

function selectPhase(index) {
  isPlaying.value = false // 手动切换时停止自动播放
  emit('update:modelValue', index)
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

// 自动播放逻辑
watch([isPlaying, () => props.modelValue], ([playing, currentIdx]) => {
  if (playbackTimer) clearTimeout(playbackTimer)
  
  if (playing && currentIdx < props.phases.length - 1) {
    // 根据当前事故类型确定时长
    const isTruck = props.phases[0]?.id.startsWith('t-')
    let duration = 3000 // 默认 3 秒

    if (currentIdx === 0) {
      duration = 2000 // 仿真开始
    } else if (isTruck) {
      // 货车专属逻辑 (保持用户原有设置)
      if (currentIdx === 1 || currentIdx === 2) duration = 3000
      else if (currentIdx >= 3 && currentIdx <= 5) duration = 3000 // 烟火灾害改为 3 秒
      else if (currentIdx === 7) duration = 7000 // 无人感知部署阶段设为 7 秒，保证 6 秒飞行及停靠动画完整播放
      else if (currentIdx >= 6) duration = 3000 // 其他无人机阶段 3 秒
    } else {
      // 油罐车专属逻辑 (完全分离)
      if (currentIdx === 7) duration = 7000 // 无人感知部署阶段设为 7 秒
      else duration = 3000
    }

    playbackTimer = setTimeout(() => {
      if (isPlaying.value) {
        emit('update:modelValue', currentIdx + 1)
      }
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

.accident-header {
  display: flex;
  align-items: center;
  gap: 16px;
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