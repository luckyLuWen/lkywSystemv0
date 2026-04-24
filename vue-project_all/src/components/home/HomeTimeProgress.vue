<template>
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
    </div>

    <div class="timeline-bar-wrapper">
      <div class="timeline-bar">
        <div class="progress-track"></div>
        
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
          :class="{ active: index === modelValue }"
          :style="{ left: getPhaseOffset(index) }"
          @click="selectPhase(index)"
        >
          <div class="phase-label-pill">{{ phase.shortLabel }}</div>
          <span class="phase-dot"></span>
        </button>
      </div>
    </div>
    
    <div class="simulation-status">
      <span class="status-icon">||</span>
      仿真已暂停
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  phases: { type: Array, default: () => [] },
  modelValue: { type: Number, default: 0 },
  accidents: { type: Array, default: () => [] },
  accidentIndex: { type: Number, default: 0 }
})

const emit = defineEmits(['update:modelValue', 'update:accidentIndex', 'locate'])

// 左右预留 40px 的边距，游标和阶段点在这个范围内移动
const cursorOffset = computed(() => {
  return getPhaseOffset(props.modelValue)
})

function getPhaseOffset(index) {
  if (!props.phases.length) return '40px'
  if (props.phases.length === 1) return '50%'
  // 使用 (index / (length - 1)) 确保第一个点在最左侧(40px)，最后一个点在最右侧(100%-40px)
  const percent = (index / (props.phases.length - 1)) * 100
  return `calc(40px + (100% - 80px) * ${percent / 100})`
}

function selectPhase(index) {
  emit('update:modelValue', index)
}

function onAccidentChange(event) {
  emit('update:accidentIndex', Number(event.target.value))
}

function handleLocate() {
  emit('locate')
}
</script>

<style scoped>
.timeline-shell {
  padding: 24px;
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
  margin-bottom: 30px;
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

.locate-btn {
  display: flex; align-items: center; gap: 6px; height: 36px; padding: 0 16px; border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(255, 255, 255, 0.05); color: #fff; cursor: pointer;
}

.timeline-bar-wrapper {
  padding: 0 10px;
  margin-bottom: 25px;
}

.timeline-bar {
  position: relative;
  height: 90px;
}

.progress-track {
  position: absolute;
  left: 40px;
  right: 40px;
  bottom: 12px;
  height: 10px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.15);
}

.timeline-cursor {
  position: absolute;
  top: 0;
  width: 2px;
  height: 78px;
  transform: translateX(-50%);
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 5;
  pointer-events: none;
}

.cursor-arrow {
  position: absolute;
  top: 45px;
  left: 50%;
  transform: translateX(-50%);
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
  bottom: 0;
  transform: translateX(-50%);
  background: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100px;
  padding: 0;
  z-index: 2;
}

.phase-label-pill {
  padding: 4px 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 14px;
  margin-bottom: 34px;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.phase-step.active .phase-label-pill {
  background: rgba(255, 255, 255, 0.2);
  border-color: #8cf7c5;
  box-shadow: 0 0 15px rgba(140, 247, 197, 0.2);
}

.phase-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #777;
  position: absolute;
  bottom: 11px;
  transition: all 0.3s ease;
}

.phase-step.active .phase-dot {
  background: #fff;
  box-shadow: 0 0 10px #fff;
  transform: scale(1.2);
}

.simulation-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 16px;
  font-weight: 500;
  margin-top: 10px;
}

.status-icon {
  font-family: monospace;
  font-weight: bold;
  letter-spacing: -2px;
  margin-right: 5px;
}

@media (max-width: 1080px) {
  .phase-step { width: 80px; }
  .phase-label-pill { padding: 4px 10px; font-size: 12px; }
}
</style>