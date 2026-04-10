<template>
  <section class="timeline-shell">
    <div class="timeline-current">
      <span class="current-kicker">时间进度</span>
      <strong class="current-label">
        {{ phases[modelValue]?.time || '--:--' }} · {{ phases[modelValue]?.title || '联动流程' }}
      </strong>
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
  phases: {
    type: Array,
    default: () => [],
  },
  modelValue: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits(['update:modelValue'])

const progressWidth = computed(() => {
  if (!props.phases.length) return '0%'
  if (props.phases.length === 1) return '100%'
  return `${(props.modelValue / (props.phases.length - 1)) * 100}%`
})

function selectPhase(index) {
  emit('update:modelValue', index)
}
</script>

<style scoped>
.timeline-shell {
  padding: 16px 20px 14px;
  border-radius: 20px;
  border: 1px solid rgba(255, 184, 77, 0.18);
  background: linear-gradient(180deg, rgba(12, 18, 8, 0.72) 0%, rgba(15, 20, 8, 0.88) 100%);
  box-shadow:
    inset 0 0 24px rgba(255, 184, 77, 0.08),
    0 10px 26px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(12px);
}

.timeline-current {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.current-kicker {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 184, 77, 0.18);
  background: rgba(255, 184, 77, 0.08);
  color: rgba(255, 214, 142, 0.92);
  font-size: 11px;
  letter-spacing: 0.1em;
}

.current-label {
  color: #fff4d7;
  font-size: 15px;
  line-height: 1.4;
}

.timeline-bar {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
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
