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
      <span class="status-dot"></span>
      <div>
        <strong>{{ isOnline ? '服务在线' : '服务离线' }}</strong>
        <span>{{ statusDetail || '模型已就绪' }}</span>
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
  height: 164px;
  z-index: 1000;
  display: grid;
  grid-template-rows: 64px 64px;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 8px 22px;
  padding: 14px 24px 16px;
  background: linear-gradient(180deg, rgba(2, 10, 19, 0.97), rgba(2, 10, 19, 0.76));
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  backdrop-filter: blur(14px);
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
  font-size: 28px;
  line-height: 1;
  letter-spacing: 0.04em;
  text-shadow: 0 0 14px rgba(0, 229, 255, 0.72);
  white-space: nowrap;
}

.platform-title span {
  color: rgba(224, 247, 250, 0.58);
  font-size: 13px;
  letter-spacing: 0.22em;
  white-space: nowrap;
}

.nav-container {
  grid-row: 2;
  grid-column: 2;
  justify-self: center;
  display: flex;
  gap: 8px;
  padding: 7px;
  border: 1px solid rgba(0, 229, 255, 0.28);
  border-radius: 4px;
  background: rgba(4, 22, 39, 0.82);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
}

.nav-pill {
  height: 42px;
  min-width: 126px;
  padding: 0 18px;
  border: 1px solid transparent;
  border-radius: 3px;
  background: transparent;
  color: var(--text-dim);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 18px;
  font-weight: 800;
  white-space: nowrap;
}

.nav-pill:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.045);
}

.nav-pill.active {
  color: var(--primary-cyan);
  border-color: rgba(0, 229, 255, 0.78);
  background: rgba(0, 229, 255, 0.13);
  box-shadow: inset 0 0 14px rgba(0, 229, 255, 0.1), 0 0 12px rgba(0, 229, 255, 0.16);
}

.header-status {
  grid-row: 1 / 3;
  grid-column: 3;
  justify-self: end;
  align-self: start;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 210px;
  margin-top: 14px;
  padding: 10px 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(15, 23, 42, 0.56);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #64748b;
}

.header-status.online .status-dot {
  background: #22c55e;
  box-shadow: 0 0 10px #22c55e;
}

.header-status div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.header-status strong {
  color: #e6fbff;
  font-size: 16px;
}

.header-status span:last-child {
  color: var(--text-muted);
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
    margin-top: 0;
  }
}
</style>
