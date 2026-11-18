<template>
  <div class="compact-scenario-timeline" :class="{ 'is-disabled': disabled }">
    <!-- 接入主页时由父容器将本区域定位到数字人右侧。 -->
    <aside
      v-if="subtitle || $slots.subtitle"
      class="compact-scenario-timeline__subtitle"
      role="status"
      aria-live="polite"
    >
      <span class="compact-scenario-timeline__speaker">数字人播报</span>
      <slot name="subtitle" :subtitle="subtitle">
        <p>{{ subtitle }}</p>
      </slot>
    </aside>

    <nav
      v-if="normalizedModes.length"
      class="compact-scenario-timeline__modes"
      aria-label="推演展示模式"
    >
      <button
        v-for="(mode, index) in normalizedModes"
        :key="mode.id"
        class="compact-scenario-timeline__mode"
        :class="{ active: mode.id === modeValue }"
        type="button"
        :disabled="disabled || mode.disabled"
        @click="selectMode(mode.id, index)"
      >
        {{ mode.label }}
      </button>
    </nav>

    <section
      class="compact-scenario-timeline__panel"
      :style="{ '--phase-count': Math.max(normalizedPhases.length, 1) }"
      aria-label="事故推演时间轴"
    >
      <div class="compact-scenario-timeline__track" aria-hidden="true">
        <span
          class="compact-scenario-timeline__progress"
          :style="{ width: progressWidth }"
        ></span>
      </div>

      <button
        v-for="(phase, index) in normalizedPhases"
        :key="phase.id"
        class="compact-scenario-timeline__phase"
        :class="{
          active: index === modelValue,
          completed: index < modelValue,
        }"
        type="button"
        :disabled="disabled || phase.disabled"
        :aria-current="index === modelValue ? 'step' : undefined"
        @click="selectPhase(index)"
      >
        <span class="compact-scenario-timeline__phase-label">{{ phase.label }}</span>
        <span class="compact-scenario-timeline__dot"></span>
      </button>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modes: {
    type: Array,
    default: () => [
      { id: 'overview', label: '综合' },
      { id: 'sensing', label: '感知' },
      { id: 'response', label: '响应' },
      { id: 'simulation', label: '推演' },
    ],
  },
  modeValue: { type: [String, Number], default: 'overview' },
  phases: { type: Array, default: () => [] },
  modelValue: { type: Number, default: 0 },
  subtitle: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:modelValue',
  'update:modeValue',
  'phaseClick',
  'modeChange',
])

const normalizedModes = computed(() => props.modes.map((mode, index) => {
  if (typeof mode === 'string') {
    return { id: index, label: mode, disabled: false }
  }

  return {
    id: mode.id ?? index,
    label: mode.label ?? mode.name ?? `模式 ${index + 1}`,
    disabled: Boolean(mode.disabled),
  }
}))

const normalizedPhases = computed(() => props.phases.map((phase, index) => {
  if (typeof phase === 'string') {
    return { id: index, label: phase, disabled: false }
  }

  return {
    id: phase.id ?? index,
    label: phase.shortLabel ?? phase.label ?? phase.name ?? `阶段 ${index + 1}`,
    disabled: Boolean(phase.disabled),
  }
}))

const progressWidth = computed(() => {
  const total = normalizedPhases.value.length
  if (total <= 1 || props.modelValue < 0) return '0%'

  const current = Math.min(Math.max(props.modelValue, 0), total - 1)
  return `${(current / (total - 1)) * 100}%`
})

function selectMode(modeId, index) {
  if (props.disabled) return
  emit('update:modeValue', modeId)
  emit('modeChange', { id: modeId, index })
}

function selectPhase(index) {
  if (props.disabled) return
  emit('update:modelValue', index)
  emit('phaseClick', index)
}
</script>

<style scoped>
.compact-scenario-timeline {
  --timeline-accent: #6af5eb;
  --timeline-accent-soft: rgba(106, 245, 235, 0.34);
  --timeline-panel: rgba(18, 72, 76, 0.82);
  position: relative;
  width: min(920px, 100%);
  color: #efffff;
  font-family: 'LkywOppoSans', 'Microsoft YaHei UI', 'Microsoft YaHei', sans-serif;
  filter: drop-shadow(0 10px 22px rgba(0, 15, 26, 0.34));
}

.compact-scenario-timeline.is-disabled {
  opacity: 0.62;
}

.compact-scenario-timeline__subtitle {
  position: absolute;
  right: 0;
  bottom: calc(100% + 18px);
  width: clamp(280px, 34vw, 520px);
  padding: 12px 16px 13px;
  border: 1px solid rgba(91, 236, 255, 0.46);
  border-left: 3px solid var(--timeline-accent);
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(2, 26, 42, 0.94), rgba(4, 49, 61, 0.86));
  box-shadow: inset 0 0 18px rgba(32, 213, 225, 0.08), 0 0 18px rgba(0, 0, 0, 0.22);
  backdrop-filter: blur(10px);
}

.compact-scenario-timeline__speaker {
  display: block;
  margin-bottom: 5px;
  color: var(--timeline-accent);
  font-family: 'LkywTencentSans', 'Microsoft YaHei', sans-serif;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1px;
}

.compact-scenario-timeline__subtitle p {
  margin: 0;
  color: rgba(235, 253, 255, 0.94);
  font-size: 15px;
  line-height: 1.65;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.52);
}

.compact-scenario-timeline__modes {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  min-height: 32px;
  padding-left: 28px;
}

.compact-scenario-timeline__mode {
  min-width: 64px;
  height: 30px;
  padding: 0 17px;
  border: 1px solid rgba(216, 255, 243, 0.22);
  border-bottom: 0;
  border-radius: 3px 3px 0 0;
  background: linear-gradient(180deg, rgba(40, 96, 78, 0.86), rgba(19, 62, 60, 0.94));
  color: rgba(238, 255, 250, 0.88);
  font: 600 13px/1 'LkywTencentSans', 'Microsoft YaHei', sans-serif;
  letter-spacing: 1px;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.compact-scenario-timeline__mode:hover:not(:disabled),
.compact-scenario-timeline__mode.active {
  color: #ffffff;
  background: linear-gradient(180deg, rgba(97, 126, 49, 0.96), rgba(49, 85, 55, 0.98));
  box-shadow: inset 0 1px 0 rgba(226, 255, 177, 0.3), 0 0 12px rgba(104, 242, 203, 0.14);
  transform: translateY(-1px);
}

.compact-scenario-timeline__mode:disabled,
.compact-scenario-timeline__phase:disabled {
  cursor: not-allowed;
}

.compact-scenario-timeline__panel {
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--phase-count, 1), minmax(72px, 1fr));
  min-height: 66px;
  padding: 0 22px;
  overflow: hidden;
  border: 1px solid rgba(139, 255, 237, 0.34);
  border-radius: 4px;
  background:
    linear-gradient(90deg, rgba(77, 135, 83, 0.36), transparent 14%, transparent 86%, rgba(77, 135, 83, 0.24)),
    var(--timeline-panel);
  box-shadow: inset 0 1px 0 rgba(202, 255, 239, 0.12), inset 0 -12px 26px rgba(3, 27, 42, 0.18);
  backdrop-filter: blur(9px);
}

.compact-scenario-timeline__track {
  position: absolute;
  right: calc(22px + (100% - 44px) / (2 * var(--phase-count, 1)));
  bottom: 12px;
  left: calc(22px + (100% - 44px) / (2 * var(--phase-count, 1)));
  height: 2px;
  background: rgba(179, 253, 236, 0.36);
  box-shadow: 0 0 5px rgba(107, 250, 232, 0.15);
}

.compact-scenario-timeline__progress {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #b8ff6b, var(--timeline-accent));
  box-shadow: 0 0 8px rgba(106, 245, 235, 0.72);
  transition: width 0.28s ease;
}

.compact-scenario-timeline__phase {
  position: relative;
  z-index: 1;
  min-width: 0;
  padding: 15px 5px 22px;
  border: 0;
  background: transparent;
  color: rgba(235, 255, 249, 0.78);
  font: 500 13px/1.2 'LkywOppoSans', 'Microsoft YaHei', sans-serif;
  text-align: center;
  cursor: pointer;
}

.compact-scenario-timeline__phase-label {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s ease, text-shadow 0.2s ease;
}

.compact-scenario-timeline__dot {
  position: absolute;
  bottom: 8px;
  left: 50%;
  width: 7px;
  height: 7px;
  border: 1px solid rgba(204, 255, 243, 0.84);
  border-radius: 50%;
  background: #30cad0;
  box-shadow: 0 0 7px rgba(77, 236, 227, 0.72);
  transform: translateX(-50%);
  transition: transform 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.compact-scenario-timeline__phase:hover:not(:disabled) .compact-scenario-timeline__phase-label,
.compact-scenario-timeline__phase.active .compact-scenario-timeline__phase-label {
  color: #ffffff;
  text-shadow: 0 0 8px rgba(186, 255, 240, 0.48);
}

.compact-scenario-timeline__phase.completed .compact-scenario-timeline__dot {
  background: #a9ef72;
}

.compact-scenario-timeline__phase.active .compact-scenario-timeline__dot {
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(106, 245, 235, 0.22), 0 0 12px var(--timeline-accent);
  transform: translateX(-50%) scale(1.28);
}

@media (max-width: 760px) {
  .compact-scenario-timeline__subtitle {
    width: min(420px, 92vw);
  }

  .compact-scenario-timeline__modes {
    gap: 4px;
    padding-left: 8px;
  }

  .compact-scenario-timeline__mode {
    min-width: 54px;
    padding: 0 10px;
    font-size: 12px;
  }

  .compact-scenario-timeline__panel {
    overflow-x: auto;
    grid-auto-columns: minmax(84px, 1fr);
  }
}
</style>
