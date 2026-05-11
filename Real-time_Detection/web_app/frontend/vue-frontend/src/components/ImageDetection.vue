<template>
  <div class="image-detection-container">
    <!-- Centered Upload Area when no result -->
    <div v-if="!result && !loading" class="upload-center">
      <div 
        class="card upload-card"
        @click="fileInput.click()"
        @dragover.prevent="dragover = true"
        @dragleave.prevent="dragover = false"
        @drop.prevent="handleDrop"
        :class="{ dragover }"
      >
        <div class="upload-icon">☁️</div>
        <h3>上传检测目标</h3>
        <p>支持 JPG, PNG, WEBP 高清图像</p>
        <input 
          type="file" 
          ref="fileInput" 
          accept="image/*" 
          style="display: none;" 
          @change="handleFileChange"
        >
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="upload-center">
      <div class="loading-box">
        <div class="spinner"></div>
        <p class="scanning-text">算法检测中...</p>
      </div>
    </div>

    <!-- Results Display: Horizontal Split -->
    <div v-if="result && !loading" class="result-layout">
      <div class="card result-main">
        <div class="card-header">
          <span class="card-id-tag">OUT</span>
          <h3>检测预览</h3>
          <button class="btn-reset" @click="reset">重新上传</button>
        </div>
        <div class="image-wrapper">
          <img :src="result.image" class="result-image">
        </div>
      </div>

      <div class="result-sidebar">
        <div class="card metrics-card">
          <div class="card-title">检测指标</div>
          <div class="metric-item">
            <span class="label">目标检测数量</span>
            <span class="value cyan">{{ result.count }}</span>
          </div>
          <div class="metric-item">
            <span class="label">模型推理速度</span>
            <span class="value">{{ result.inference_time }} ms</span>
          </div>
        </div>

        <div class="card objects-card">
          <div class="card-title">识别列表</div>
          <div class="detection-list">
            <div 
              v-for="(det, index) in result.detections" 
              :key="index" 
              class="object-item"
            >
              <span class="obj-cls">{{ det.class }}</span>
              <span class="obj-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
            </div>
            <div v-if="result.detections.length === 0" class="empty-text">
              未发现可疑目标
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  settings: Object,
  safeFetch: Function
})

const fileInput = ref(null)
const dragover = ref(false)
const loading = ref(false)
const result = ref(null)

const handleFileChange = (e) => {
  const file = e.target.files[0]
  if (file) processImage(file)
}

const handleDrop = (e) => {
  dragover.value = false
  const file = e.dataTransfer.files[0]
  if (file) processImage(file)
}

const reset = () => {
  result.value = null
  if (fileInput.value) fileInput.value.value = ''
}

const processImage = async (file) => {
  loading.value = true
  const formData = new FormData()
  formData.append('file', file)
  formData.append('model', props.settings.model)
  formData.append('conf', props.settings.conf)
  formData.append('iou', props.settings.iou)

  try {
    const data = await props.safeFetch('/api/detect/image', {
      method: 'POST',
      body: formData
    })
    if (data.success) result.value = data
  } catch (error) {
    alert('检测失败: ' + error.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.image-detection-container {
  height: 100%;
}

.upload-center {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
}

.upload-card {
  width: 500px;
  height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 1px dashed var(--border-cyan);
  background: rgba(0, 229, 255, 0.02);
  cursor: pointer;
  transition: all 0.3s;
}

.upload-card:hover, .upload-card.dragover {
  background: rgba(0, 229, 255, 0.08);
  border-style: solid;
  box-shadow: 0 0 30px rgba(0, 229, 255, 0.1);
}

.upload-icon {
  font-size: 60px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.scanning-text {
  font-family: monospace;
  color: var(--primary-cyan);
  letter-spacing: 2px;
  margin-top: 10px;
}

/* Result Layout */
.result-layout {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  animation: fadeIn 0.5s ease-out;
}

.result-main {
  min-height: 500px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 15px;
}

.btn-reset {
  background: transparent;
  border: 1px solid var(--border-cyan);
  color: var(--primary-cyan);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.image-wrapper {
  width: 100%;
  background: #000;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  justify-content: center;
}

.result-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

/* Sidebar Metrics */
.result-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-title {
  color: var(--primary-cyan);
  font-size: 12px;
  letter-spacing: 2px;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(0,229,255,0.1);
  padding-bottom: 8px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.metric-item .label {
  font-size: 11px;
  color: var(--text-dim);
}

.metric-item .value {
  font-weight: bold;
  font-family: monospace;
}

.metric-item .value.cyan {
  color: var(--primary-cyan);
  text-shadow: 0 0 5px var(--primary-cyan);
}

.object-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dotted rgba(255,255,255,0.1);
  font-size: 13px;
}

.obj-cls {
  color: var(--accent-amber);
}

.obj-conf {
  color: var(--text-dim);
  font-size: 11px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
