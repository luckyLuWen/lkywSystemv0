<template>
  <div class="card settings-card">
    <div class="settings-header">
      <span class="panel-kicker">Model Config</span>
      <h2>模型配置</h2>
    </div>

    <div class="model-info">
      <div class="field-title">模型选择</div>
      <select v-model="settings.model" class="cyber-select">
        <option v-for="model in availableModels" :key="model.name" :value="model.name">
          {{ getModelLabel(model) }}
        </option>
      </select>
      <div class="tag">主模型与对照模型</div>
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
defineProps({
  settings: Object,
  availableModels: Array
})

const getModelLabel = (model) => {
  if (model.display_name) return model.display_name
  return model.name.split('_')[0]
}
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

.model-info {
  padding: 24px;
  border-left: 3px solid var(--accent-amber);
  border-top: 1px solid rgba(255, 179, 0, 0.16);
  background: rgba(255, 179, 0, 0.055);
  margin-bottom: 33px;
}

.field-title {
  color: var(--text-dim);
  font-size: 23px;
  margin-bottom: 15px;
}

.cyber-select {
  width: 100%;
  min-width: 0;
  min-height: 69px;
  border: 1px solid rgba(255, 179, 0, 0.62);
  background: rgba(0, 0, 0, 0.32);
  color: var(--accent-amber);
  padding: 0 18px;
  font-size: 30px;
  font-weight: 900;
  cursor: pointer;
  outline: none;
  border-radius: 3px;
}

.cyber-select option {
  background: #071827;
  color: var(--accent-amber);
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
  color: var(--accent-amber);
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
