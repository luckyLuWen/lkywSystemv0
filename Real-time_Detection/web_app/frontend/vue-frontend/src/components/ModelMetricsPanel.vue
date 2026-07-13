<template>
  <section class="model-metrics-panel">
    <div class="metrics-title">模型性能指标</div>
    <div class="metrics-grid">
      <div class="metric-item wide">
        <span class="metric-label">模型名称</span>
        <strong>{{ performance.model_name || modelLabel }}</strong>
      </div>
      <div class="metric-item wide map50-item">
        <span class="metric-label">平均精度均值（mAP50）</span>
        <strong>{{ formatPercent(performance.map50) }}</strong>
        <small>验收要求 ≥85%</small>
      </div>
      <div class="metric-item">
        <span class="metric-label">高阈值平均精度均值（mAP50:95）</span>
        <strong>{{ formatPercent(performance.map50_95) }}</strong>
      </div>
      <div class="metric-item">
        <span class="metric-label">精确率（Precision）</span>
        <strong>{{ formatPercent(performance.precision) }}</strong>
      </div>
      <div class="metric-item">
        <span class="metric-label">召回率（Recall）</span>
        <strong>{{ formatPercent(performance.recall) }}</strong>
      </div>
      <div class="metric-item wide">
        <span class="metric-label">测试集</span>
        <strong>{{ performance.test_set || 'LKYWDetection Test set' }}</strong>
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

const modelLabel = computed(() => {
  const model = selectedModel.value
  if (!model) return props.settings?.model || '未选择'
  return model.display_name || model.name
})

const performance = computed(() => selectedModel.value?.performance || {})

const formatPercent = (value) => {
  if (value === undefined || value === null || value === '') return '--'
  return `${(Number(value) * 100).toFixed(2)}%`
}
</script>

<style scoped>
.model-metrics-panel {
  margin-bottom: 24px;
  padding: 18px;
  border: 1px solid rgba(0, 229, 255, 0.18);
  border-left: 4px solid var(--accent-amber);
  background: rgba(0, 0, 0, 0.28);
}

.metrics-title {
  color: var(--primary-cyan);
  font-size: 30px;
  letter-spacing: 1px;
  margin-bottom: 14px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric-item {
  min-height: 78px;
  padding: 12px;
  border: 1px solid rgba(255, 179, 0, 0.18);
  background: rgba(255, 179, 0, 0.05);
}

.metric-item.wide {
  grid-column: 1 / -1;
}

.metric-item.map50-item {
  min-height: 86px;
  border-color: rgba(255, 179, 0, 0.34);
  background: rgba(255, 179, 0, 0.08);
}

.metric-label {
  display: block;
  color: var(--text-dim);
  font-size: 20px;
  margin-bottom: 6px;
}

.metric-item strong {
  display: block;
  color: #fff3bf;
  font-size: 27px;
  line-height: 1.25;
}

.metric-item small {
  display: block;
  color: #fbbf24;
  font-size: 19px;
  margin-top: 4px;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .metric-item.wide {
    grid-column: auto;
  }
}
</style>
