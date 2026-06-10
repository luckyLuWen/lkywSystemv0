<template>
  <div class="card settings-card">
    <div class="card-header">
      <span class="bracket">[</span>
      <h2>模型配置</h2>
      <span class="bracket">]</span>
    </div>
    
    <div class="model-info">
      <div class="label">模型选择</div>
      <select v-model="settings.model" class="cyber-select">
        <option v-for="model in availableModels" :key="model.name" :value="model.name">
          {{ cleanModelName(model.name) }}
        </option>
      </select>
      <div class="tag">支持不同尺寸模型</div>
    </div>
    
    <div class="control-group">
      <div class="control-label">
        <span>置信度设置</span>
        <span class="value">{{ settings.conf }}</span>
      </div>
      <input type="range" v-model.number="settings.conf" min="0.1" max="0.9" step="0.05" class="cyber-range">
    </div>
    
    <div class="control-group">
      <div class="control-label">
        <span>IOU阈值设置</span>
        <span class="value">{{ settings.iou }}</span>
      </div>
      <input type="range" v-model.number="settings.iou" min="0.1" max="0.9" step="0.05" class="cyber-range">
    </div>

    <div class="decoration-line"></div>
  </div>
</template>

<script setup>
defineProps({
  settings: Object,
  availableModels: Array
})

// 净化名称逻辑：保留下划线前的核心型号
const cleanModelName = (name) => {
  return name.split('_')[0]
}
</script>

<style scoped>
.settings-card {
  height: fit-content;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 25px;
}

.bracket {
  color: var(--primary-cyan);
  font-weight: bold;
  font-size: 44px;
}

.model-info {
  background: rgba(0, 0, 0, 0.3);
  padding: 34px;
  border-left: 3px solid var(--accent-amber);
  margin-bottom: 42px;
}

.label {
  font-size: 23px;
  color: var(--text-dim);
}

.cyber-select {
  width: 100%;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--accent-amber);
  color: var(--accent-amber);
  padding: 18px;
  font-size: 35px;
  font-weight: bold;
  margin: 18px 0;
  cursor: pointer;
  outline: none;
  border-radius: 0;
}

.cyber-select option {
  background: #0a1929;
  color: var(--accent-amber);
}

.value {
  font-size: 44px;
  color: var(--accent-amber);
  font-weight: bold;
  margin: 8px 0;
}

.tag {
  font-size: 20px;
  display: inline-block;
  padding: 5px 12px;
  background: var(--accent-amber);
  color: black;
  font-weight: bold;
}

.control-group {
  margin-bottom: 44px;
}

.control-label {
  display: flex;
  justify-content: space-between;
  font-size: 24px;
  margin-bottom: 14px;
  font-family: monospace;
  color: var(--text-main);
}

.cyber-range {
  -webkit-appearance: none;
  width: 100%;
  height: 10px;
  background: rgba(0, 229, 255, 0.1);
  border-radius: 2px;
  outline: none;
}

.cyber-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 34px;
  height: 34px;
  background: var(--primary-cyan);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 10px var(--primary-cyan);
}

.decoration-line {
  height: 2px;
  background: repeating-linear-gradient(
    90deg,
    var(--primary-cyan),
    var(--primary-cyan) 2px,
    transparent 2px,
    transparent 10px
  );
  margin-top: 20px;
  opacity: 0.3;
}
</style>
