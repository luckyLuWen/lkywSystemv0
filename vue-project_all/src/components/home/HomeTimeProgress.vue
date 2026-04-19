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

    <div class="timeline-bar">
      <div class="progress-track"></div>
      <div class="progress-fill" :style="{ width: progressWidth }"></div>

      <button
        v-for="(phase, index) in phases"
        :key="phase.id"
        type="button"
        class="phase-step"
        :class="{ active: index === modelValue, passed: index < modelValue }"
        @click="selectPhase(index)"
      >
        <span class="phase-dot"></span>
        <span class="phase-time">{{ phase.time }}</span>
        <span class="phase-name">{{ phase.shortLabel }}</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 下方时间线数据
  phases: {
    type: Array,
    default: () => [],
  },
  // 当前时间线索引
  modelValue: {
    type: Number,
    default: 0,
  },
  // 上方事故点数据
  accidents: {
    type: Array,
    default: () => [],
  },
  // 当前事故点索引
  accidentIndex: {
    type: Number,
    default: 0,
  }
})

const emit = defineEmits(['update:modelValue', 'update:accidentIndex', 'locate'])

const progressWidth = computed(() => {
  if (!props.phases.length) return '0%'
  if (props.phases.length === 1) return '100%'
  return `${(props.modelValue / (props.phases.length - 1)) * 100}%`
})

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
  padding: 20px 24px;
  border-radius: 20px;
  border: 1px solid rgba(255, 184, 77, 0.18);
  background: linear-gradient(180deg, rgba(12, 18, 8, 0.72) 0%, rgba(15, 20, 8, 0.88) 100%);
  box-shadow:
    inset 0 0 24px rgba(255, 184, 77, 0.08),
    0 10px 26px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(12px);
}

.accident-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
}

.accident-kicker {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 184, 77, 0.22);
  background: rgba(64, 48, 24, 0.6);
  color: #ffd68e;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.05em;
}

.accident-select-box {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 180px;
  height: 38px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 229, 255, 0.6);
  background: rgba(0, 229, 255, 0.04);
  transition: all 0.2s ease;
}

.accident-select-box:hover {
  border-color: #00e5ff;
  background: rgba(0, 229, 255, 0.08);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00e5ff;
  box-shadow: 0 0 8px #00e5ff;
  margin-right: 12px;
  flex-shrink: 0;
}

.accident-native-select {
  flex: 1;
  background: transparent;
  border: none;
  color: #00e5ff;
  font-size: 15px;
  font-weight: 500;
  appearance: none;
  outline: none;
  cursor: pointer;
  padding-right: 20px;
}

.accident-native-select option {
  background: #0c1208;
  color: #00e5ff;
}

.select-arrow {
  position: absolute;
  right: 10px;
  pointer-events: none;
  color: #00e5ff;
  display: flex;
}

.locate-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 18px;
  border-radius: 8px;
  border: 1px solid rgba(255, 107, 107, 0.32);
  background: rgba(255, 107, 107, 0.06);
  color: #ff9b9b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.locate-btn:hover {
  background: rgba(255, 107, 107, 0.12);
  border-color: rgba(255, 107, 107, 0.5);
  box-shadow: 0 0 14px rgba(255, 107, 107, 0.15);
}

.pin-icon {
  color: #ff4d4d;
  filter: drop-shadow(0 0 4px rgba(255, 77, 77, 0.4));
}

.timeline-bar {
  position: relative;
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
  padding-top: 18px;
}

.progress-track,
.progress-fill {
  position: absolute;
  left: 0;
  right: 0;
  top: 8px;
  height: 4px;
  border-radius: 999px;
}

.progress-track {
  background: rgba(255, 255, 255, 0.1);
}

.progress-fill {
  right: auto;
  background: linear-gradient(90deg, #ffb84d 0%, #ffe18c 100%);
  box-shadow: 0 0 16px rgba(255, 184, 77, 0.32);
}

.phase-step {
  position: relative;
  display: grid;
  gap: 4px;
  padding: 12px 10px 10px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.72);
  text-align: center;
  cursor: pointer;
}

.phase-dot {
  position: absolute;
  top: -4px;
  left: 50%;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  transform: translateX(-50%);
  border: 2px solid rgba(255, 255, 255, 0.18);
  background: #161308;
}

.phase-step.passed .phase-dot,
.phase-step.active .phase-dot {
  border-color: rgba(255, 184, 77, 0.46);
  background: #ffb84d;
  box-shadow: 0 0 12px rgba(255, 184, 77, 0.35);
}

.phase-step.active {
  color: #fff4d7;
}

.phase-time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.58);
}

.phase-name {
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
}

@media (max-width: 1080px) {
  .timeline-bar {
    grid-template-columns: 1fr;
    padding-top: 0;
  }

  .progress-track,
  .progress-fill {
    display: none;
  }

  .phase-step {
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.04);
    text-align: left;
  }

  .phase-dot {
    display: none;
  }
}
</style>
