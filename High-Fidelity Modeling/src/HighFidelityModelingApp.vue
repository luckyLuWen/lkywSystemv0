<template>
  <div class="high-fidelity-app-root">
    <!-- 头部导航 -->
    <header class="app-header">
      <div class="header-branding">
        <div class="brand-title-group">
          <div class="title-row">
            <h1>精细三维建模系统 2</h1>
            <span class="system-tag">两客一危专版</span>
          </div>
          <span class="brand-sub">Fine-Grained 3D Reconstruction & Spatial Measurement System</span>
        </div>
      </div>
    </header>

    <!-- 工作流主展示视图 -->
    <main class="app-viewport">
      <div class="step-view-container">
        <DatasetUploader />
      </div>
    </main>
  </div>
</template>

<script setup>
import DatasetUploader from './components/DatasetUploader.vue'
</script>

<style scoped>
.high-fidelity-app-root {
  width: 100%;
  height: 100%;
  background: #020712;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow-y: auto;
  font-family: 'Inter', -apple-system, sans-serif;
}

/* 头部导航 */
.app-header {
  padding: 16px 24px;
  background: rgba(4, 12, 26, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.brand-title-group .title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-title-group h1 {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: #ffffff;
}
.system-tag {
  background: rgba(0, 242, 254, 0.12);
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.3);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.brand-sub {
  font-size: 11.5px;
  color: #64748b;
  font-family: 'Courier New', monospace;
}

/* 主展示区 */
.app-viewport {
  flex: 1;
  padding: 24px;
  display: flex;
  justify-content: center;
}
.step-view-container {
  width: 100%;
}
</style>
