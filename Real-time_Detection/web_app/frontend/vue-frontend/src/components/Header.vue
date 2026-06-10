<template>
  <header class="header">
    <div class="nav-container">
      <div class="nav-pill return-btn" @click="returnToParent">
        <span class="pill-icon">🗺️</span>
        <span class="pill-label">返回地图大屏</span>
      </div>
      <div class="nav-divider"></div>
      <div 
        v-for="tab in tabs" 
        :key="tab.id"
        class="nav-pill" 
        :class="{ active: activeTab === tab.id }"
        @click="$emit('update:activeTab', tab.id)"
      >
        <span class="pill-icon">{{ tab.icon }}</span>
        <span class="pill-label">{{ tab.label }}</span>
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
  activeTab: String,
  isOnline: Boolean,
  statusDetail: String
})

const tabs = [
  { id: 'image', label: '图片检测', icon: '📷' },
  { id: 'video', label: '视频检测', icon: '🎬' },
  { id: 'webcam', label: '实时检测', icon: '📹' },
  { id: 'history', label: '历史记录', icon: '📋' },
  { id: 'stats', label: '统计仪表板', icon: '📊' }
]

const returnToParent = () => {
  window.top.location.href = '/'
}
</script>

<style scoped>
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 120px;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  pointer-events: none;
}

.nav-container {
  pointer-events: auto;
  display: flex;
  gap: 12px;
  background: rgba(6, 26, 46, 0.8);
  padding: 10px;
  border-radius: 44px;
  border: 1px solid var(--border-cyan);
  backdrop-filter: blur(15px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.nav-pill {
  padding: 16px 36px;
  border-radius: 34px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.3s;
  color: var(--text-dim);
  border: 1px solid transparent;
}

.nav-pill:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
}

.nav-pill.active {
  background: rgba(0, 229, 255, 0.15);
  color: var(--primary-cyan);
  border: 1px solid var(--primary-cyan);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.2);
}

.nav-pill.return-btn {
  background: rgba(0, 229, 255, 0.08);
  color: var(--primary-cyan);
  border: 1px dashed var(--primary-cyan);
}

.nav-pill.return-btn:hover {
  background: rgba(0, 229, 255, 0.2);
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
}

.nav-divider {
  width: 1px;
  height: 36px;
  background: rgba(0, 229, 255, 0.25);
  align-self: center;
}

.pill-icon {
  font-size: 26px;
}

.pill-label {
  font-size: 22px;
  font-weight: 500;
  letter-spacing: 1px;
}
</style>
