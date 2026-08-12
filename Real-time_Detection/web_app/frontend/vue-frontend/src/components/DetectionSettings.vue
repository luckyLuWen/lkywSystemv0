<template>
  <div class="card settings-card">
    <div class="settings-header">
      <span class="panel-kicker">Model Config</span>
      <h2>模型配置</h2>
    </div>

    <div class="mode-block">
      <div class="field-title">检测模式</div>
      <div class="segmented-control">
        <button
          type="button"
          :class="{ active: settings.detectionMode === 'single' }"
          @click="settings.detectionMode = 'single'"
        >
          单任务检测
        </button>
        <button
          type="button"
          :class="{ active: settings.detectionMode === 'composite' }"
          @click="settings.detectionMode = 'composite'"
        >
          综合事故检测
        </button>
      </div>
      <div class="tag mode-tag">{{ modeHint }}</div>
    </div>

    <div v-if="settings.detectionMode === 'single'" class="mode-block task-block">
      <div class="field-title">检测任务线</div>
      <div class="segmented-control task-selector">
        <button
          type="button"
          :class="{ active: settings.taskType === 'collision' }"
          @click="settings.taskType = 'collision'"
        >
          客车追尾现场
        </button>
        <button
          type="button"
          :class="{ active: settings.taskType === 'hazmat' }"
          @click="settings.taskType = 'hazmat'"
        >
          油罐车泄露现场
        </button>
      </div>
    </div>

    <div class="model-info">
      <div class="field-title">模型选择</div>
      <template v-if="settings.detectionMode === 'single'">
        <select v-model="settings.model" class="cyber-select">
          <option v-for="model in filteredModels" :key="model.name" :value="model.name">
            {{ getModelLabel(model) }}
          </option>
        </select>
        <div class="tag">改进模型与对照模型</div>
      </template>
      <template v-else>
        <div class="composite-models">
          <div v-for="model in compositeModels" :key="model.name" class="composite-model">
            <span>{{ model.task_label }}</span>
            <strong>{{ getModelLabel(model) }}</strong>
          </div>
        </div>
        <div class="tag">客车追尾现场与油罐车泄露现场综合检测</div>
      </template>
    </div>

    <div class="control-group">
      <div class="control-label">
        <span>置信度设置</span>
        <strong>{{ Number(settings.conf).toFixed(2) }}</strong>
      </div>
      <input type="range" v-model.number="settings.conf" min="0.1" max="0.9" step="0.05" class="cyber-range">
    </div>

    <div class="control-group">
      <div class="control-label">
        <span>IOU阈值设置</span>
        <strong>{{ Number(settings.iou).toFixed(2) }}</strong>
      </div>
      <input type="range" v-model.number="settings.iou" min="0.1" max="0.9" step="0.05" class="cyber-range">
    </div>

    <div class="settings-footline"></div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'

const props = defineProps({
  settings: Object,
  availableModels: {
    type: Array,
    default: () => []
  }
})

const taskLabels = {
  collision: '客车追尾现场',
  hazmat: '油罐车泄露现场'
}

const filteredModels = computed(() => {
  const currentTask = props.settings?.taskType || 'collision'
  const list = props.availableModels.filter(model => (model.task_type || 'collision') === currentTask)
  const uniqueList = []
  const seen = new Set()
  for (const item of list) {
    const label = getModelLabel(item)
    if (label && !seen.has(label)) {
      seen.add(label)
      uniqueList.push(item)
    }
  }
  return uniqueList
})

const compositeModels = computed(() => {
  const modelNames = ['SFGA-YOLO26M', 'LCA-YOLO26N']
  return modelNames
    .map(name => props.availableModels.find(model => model.name === name || model.display_name === name))
    .filter(Boolean)
})

const currentTaskLabel = computed(() => taskLabels[props.settings?.taskType] || '客车追尾现场')

const modeHint = computed(() => {
  if (props.settings?.detectionMode === 'composite') return 'SFGA + LCA 双模型联合推理'
  return `${currentTaskLabel.value}单模型推理`
})

const getModelLabel = (model) => {
  if (!model) return ''
  const raw = model.display_name || model.name || ''
  const clean = String(raw).replace(/（.*?）|\(.*?\)/g, '')
  if (/^yolo/i.test(clean)) {
    return clean.toUpperCase()
  }
  return clean
}

watch(
  () => [props.settings?.taskType, props.settings?.detectionMode, props.availableModels.length],
  () => {
    if (!props.settings || props.settings.detectionMode !== 'single') return
    const models = filteredModels.value
    if (models.length && !models.some(model => model.name === props.settings.model)) {
      props.settings.model = models[0].name
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.settings-card {
  padding: 30px 27px;
}

.settings-header {
  margin-bottom: 27px;
}

.panel-kicker {
  display: block;
  margin-bottom: 5px;
  color: var(--text-muted);
  font-size: 28px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.settings-header h2 {
  font-size: 38px;
  line-height: 1.1;
}

.mode-block,
.model-info {
  padding: 22px;
  border-left: 3px solid var(--accent-amber);
  border-top: 1px solid rgba(255, 179, 0, 0.16);
  background: rgba(255, 179, 0, 0.055);
  margin-bottom: 26px;
}

.task-block {
  border-left-color: var(--primary-cyan);
  border-top-color: rgba(0, 229, 255, 0.18);
  background: rgba(0, 229, 255, 0.045);
}

.field-title {
  color: var(--text-dim);
  font-size: 23px;
  margin-bottom: 15px;
}

.segmented-control {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.segmented-control button {
  min-height: 54px;
  border: 1px solid rgba(0, 229, 255, 0.28);
  background: rgba(4, 22, 39, 0.72);
  color: var(--text-dim);
  font-size: 20px;
  font-weight: 900;
  cursor: pointer;
}

.segmented-control button.active {
  color: #06111d;
  border-color: var(--accent-amber);
  background: var(--accent-amber);
  box-shadow: 0 0 16px rgba(255, 179, 0, 0.24);
}

.task-selector button.active {
  border-color: var(--primary-cyan);
  background: var(--primary-cyan);
  box-shadow: 0 0 16px rgba(0, 229, 255, 0.24);
}

.cyber-select {
  width: 100%;
  min-width: 0;
  min-height: 69px;
  border: 1px solid rgba(255, 179, 0, 0.62);
  background: rgba(0, 0, 0, 0.32);
  color: #ffffff;
  padding: 0 18px;
  font-size: 30px;
  font-weight: 900;
  cursor: pointer;
  outline: none;
  border-radius: 3px;
}

.cyber-select option {
  background: #071827;
  color: #ffffff;
}

.composite-models {
  display: grid;
  gap: 12px;
}

.composite-model {
  display: grid;
  grid-template-columns: 128px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
  min-height: 58px;
  padding: 12px 14px;
  border: 1px solid rgba(0, 229, 255, 0.2);
  background: rgba(4, 22, 39, 0.58);
}

.composite-model span {
  color: var(--text-dim);
  font-size: 18px;
  white-space: nowrap;
}

.composite-model strong {
  color: #ffffff;
  font-size: 22px;
  line-height: 1.15;
  overflow-wrap: anywhere;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  margin-top: 18px;
  padding: 0 12px;
  background: var(--accent-amber);
  color: #06111d;
  font-size: 20px;
  font-weight: 800;
}

.mode-tag {
  max-width: 100%;
  line-height: 1.25;
}

.control-group {
  margin-bottom: 33px;
}

.control-label {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 15px;
  color: var(--text-main);
  font-family: monospace;
}

.control-label span {
  font-size: 24px;
  color: var(--text-dim);
}

.control-label strong {
  font-size: 38px;
  color: #ffffff;
}

.cyber-range {
  -webkit-appearance: none;
  width: 100%;
  height: 12px;
  border-radius: 2px;
  background: rgba(0, 229, 255, 0.12);
  outline: none;
}

.cyber-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--primary-cyan);
  cursor: pointer;
  box-shadow: 0 0 12px var(--primary-cyan);
}

.settings-footline {
  height: 1px;
  margin-top: 8px;
  background: repeating-linear-gradient(90deg, var(--primary-cyan), var(--primary-cyan) 3px, transparent 3px, transparent 10px);
  opacity: 0.34;
}
</style>
