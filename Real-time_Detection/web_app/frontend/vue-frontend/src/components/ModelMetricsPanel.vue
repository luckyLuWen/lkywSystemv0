<template>
  <section class="model-metrics-panel">
    <div class="metrics-title">{{ panelTitle }}</div>
    <div class="metrics-stack">
      <div v-for="model in displayModels" :key="model.name" class="metrics-grid">
        <div class="metric-item wide">
          <span class="metric-label">模型名称</span>
          <strong>{{ getPerformance(model).model_name || getModelLabel(model) }}</strong>
        </div>
        <div class="metric-item wide map50-item">
          <span class="metric-label">平均精度均值（mAP50）</span>
          <strong>{{ formatPercent(getPerformance(model).map50) }}</strong>
          <small>{{ getPerformance(model).map50 == null ? '指标待接入' : '验收要求 ≥85%' }}</small>
        </div>
        <div class="metric-pair">
          <div class="metric-item">
            <span class="metric-label">精确率</span>
            <strong>{{ formatPercent(getPerformance(model).precision) }}</strong>
          </div>
          <div class="metric-item">
            <span class="metric-label">召回率</span>
            <strong>{{ formatPercent(getPerformance(model).recall) }}</strong>
          </div>
        </div>
        <div class="metric-item wide">
          <span class="metric-label">测试集</span>
          <strong>{{ getPerformance(model).test_set || '待接入' }}</strong>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  settings: Object,
  availableModels: {
    type: Array,
    default: () => []
  }
})

const selectedModel = computed(() => {
  return props.availableModels.find(item => item.name === props.settings?.model) || null
})

const compositeModels = computed(() => {
  const modelNames = ['SFGA-YOLO26M', 'LCA-YOLO26N']
  return modelNames
    .map(name => props.availableModels.find(model => model.name === name))
    .filter(Boolean)
})

const displayModels = computed(() => {
  if (props.settings?.detectionMode === 'composite') return compositeModels.value
  return selectedModel.value ? [selectedModel.value] : []
})

const panelTitle = computed(() => {
  return props.settings?.detectionMode === 'composite' ? '综合模型性能指标' : '模型性能指标'
})

const getModelLabel = (model) => {
  if (!model) return props.settings?.model || '未选择'
  const raw = model.display_name || model.name || ''
  return String(raw).replace(/（.*?）|\(.*?\)/g, '')
}

const getPerformance = (model) => model?.performance || {}

const formatPercent = (value) => {
  if (value === undefined || value === null || value === '') return '待接入'
  return `${(Number(value) * 100).toFixed(2)}%`
}
</script>

<style scoped>
.model-metrics-panel {
  margin-bottom: 0;
  padding: 26px 22px;
  border: 1px solid rgba(0, 229, 255, 0.22);
  border-left: 4px solid var(--accent-amber);
  background: rgba(4, 22, 39, 0.78);
  position: relative;
}

.model-metrics-panel::before {
  content: "";
  position: absolute;
  top: -1px;
  left: -1px;
  width: 18px;
  height: 18px;
  border-top: 2px solid var(--primary-cyan);
  border-left: 2px solid var(--primary-cyan);
}

.model-metrics-panel::after {
  content: "";
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 18px;
  height: 18px;
  border-right: 2px solid var(--primary-cyan);
  border-bottom: 2px solid var(--primary-cyan);
}

.metrics-title {
  color: var(--primary-cyan);
  font-size: 31px;
  font-weight: 900;
  margin-bottom: 20px;
  text-shadow: 0 0 12px rgba(0, 229, 255, 0.4);
}

.metrics-stack {
  display: grid;
  gap: 18px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.14);
}

.metrics-grid:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.metric-pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.metric-item {
  min-height: 74px;
  padding: 13px 16px;
  border: 1px solid rgba(255, 179, 0, 0.2);
  background: rgba(255, 179, 0, 0.045);
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  column-gap: 14px;
}

.metric-item.map50-item {
  min-height: 92px;
  grid-template-columns: 1fr;
  align-items: start;
  border-color: rgba(255, 179, 0, 0.4);
  background: rgba(255, 179, 0, 0.08);
}

.metric-label {
  display: block;
  color: var(--text-dim);
  font-size: 20px;
  line-height: 1.22;
  min-width: 0;
}

.metric-item strong {
  display: block;
  color: #fff3bf;
  font-size: 25px;
  line-height: 1.16;
  text-align: right;
  white-space: nowrap;
}

.metric-item.map50-item strong {
  margin-top: 8px;
  text-align: left;
  font-size: 31px;
}

.metric-item small {
  display: block;
  color: #fbbf24;
  font-size: 19px;
  margin-top: 6px;
}


.metric-item.wide strong {
  white-space: normal;
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .metric-pair,
  .metric-item {
    grid-template-columns: 1fr;
    row-gap: 8px;
  }

  .metric-item strong {
    text-align: left;
  }
}
</style>
