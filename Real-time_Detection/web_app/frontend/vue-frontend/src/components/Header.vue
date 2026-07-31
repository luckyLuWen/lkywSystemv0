<template>
  <header class="header">
    <div class="platform-title">
      <strong>[ 两客一危交通事故智能检测 ]</strong>
    </div>

    <nav class="nav-container" aria-label="实时检测子系统导航">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="nav-pill"
        :class="{ active: activeTab === tab.id }"
        @click="$emit('update:activeTab', tab.id)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <div class="header-status" :class="{ online: isOnline }">
      <div class="status-content-row">
        <div class="status-state-group">
          <span class="status-dot"></span>
          <strong class="status-online-text">{{ isOnline ? '服务在线' : '服务离线' }}</strong>
        </div>
        <span class="status-model-text">{{ statusDetail || '模型已就绪' }}</span>
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
  { id: 'image', label: '图片检测' },
  { id: 'video', label: '视频检测' },
  { id: 'webcam', label: '实时检测' },
  { id: 'history', label: '历史记录' },
  { id: 'stats', label: '统计仪表板' }
]
</script>

<style scoped>
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 180px;
  z-index: 1000;
  display: grid;
  grid-template-rows: 72px 82px;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px 22px;
  padding: 12px 20px 16px;
  background: linear-gradient(180deg, rgba(2, 10, 19, 0.97), rgba(2, 10, 19, 0.8));
  border-bottom: 2px solid rgba(0, 229, 255, 0.3);
  backdrop-filter: blur(16px);
}

.platform-title {
  grid-row: 1;
  grid-column: 1 / -1;
  justify-self: center;
  align-self: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  pointer-events: none;
}

.platform-title strong {
  color: var(--primary-cyan);
  font-size: 36px;
  line-height: 1;
  letter-spacing: 0.05em;
  text-shadow: 0 0 18px rgba(0, 229, 255, 0.85);
  white-space: nowrap;
}

.nav-container {
  grid-row: 2;
  grid-column: 2;
  justify-self: center;
  display: flex;
  gap: 14px;
  padding: 10px 16px;
  border: 2px solid rgba(0, 229, 255, 0.4);
  border-radius: 8px;
  background: rgba(3, 20, 36, 0.92);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
}

.nav-pill {
  height: 56px;
  min-width: 160px;
  padding: 0 24px;
  border: 2px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--text-dim);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 24px;
  font-weight: 800;
  white-space: nowrap;
}

.nav-pill:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
}

.nav-pill.active {
  color: var(--primary-cyan);
  border-color: rgba(0, 229, 255, 0.85);
  background: rgba(0, 229, 255, 0.2);
  box-shadow: inset 0 0 16px rgba(0, 229, 255, 0.2), 0 0 16px rgba(0, 229, 255, 0.3);
}

/* Header Status Box - Long bar matching right panel width (440px) */
.header-status {
  grid-row: 1 / 3;
  grid-column: 3;
  justify-self: end;
  align-self: center;
  width: 440px;
  max-width: 100%;
  margin-right: 0;
  padding: 14px 24px;
  border: 2px solid rgba(0, 229, 255, 0.35);
  background: rgba(4, 22, 39, 0.92);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(8px);
}

.status-content-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.status-state-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 10px #ef4444;
  flex-shrink: 0;
}

.header-status.online .status-dot {
  background: #22c55e;
  box-shadow: 0 0 12px #22c55e;
}

.status-online-text {
  color: #ffffff;
  font-size: 24px;
  font-weight: 800;
  white-space: nowrap;
}

.header-status.online .status-online-text {
  color: var(--primary-cyan);
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
}

.status-model-text {
  color: #e6fbff;
  font-size: 22px;
  font-weight: 700;
  white-space: nowrap;
}

@media (max-width: 1280px) {
  .header {
    position: sticky;
    height: auto;
    grid-template-rows: auto auto auto;
    grid-template-columns: 1fr;
  }

  .platform-title,
  .nav-container,
  .header-status {
    grid-row: auto;
    grid-column: 1;
    justify-self: stretch;
  }

  .platform-title {
    justify-self: center;
  }

  .nav-container {
    overflow-x: auto;
  }

  .header-status {
    width: 100%;
    margin-top: 0;
  }
}
</style>
