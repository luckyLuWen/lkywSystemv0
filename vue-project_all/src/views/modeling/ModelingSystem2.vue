<!--
================================================================================
  精细三维建模系统 2 (ModelingSystem2.vue)
  【独立空白界面】
  根据需求，系统 2 保持为一个干净的空白界面（预留给后续新系统接入）。
  完全独立自包含，不含冗余功能。
================================================================================
-->
<template>
  <div class="modeling-system-2-blank">
    <!-- 顶部标题栏 -->
    <header class="modeling-header">
      <div class="header-left">
        <button class="back-btn" @click="goHome">
          <span class="btn-icon">←</span> 返回首页大屏
        </button>
        <div class="header-title-group">
          <div class="title-with-badge">
            <h1>精细三维建模系统 2</h1>
            <span class="system-badge">系统 2 (新版预留)</span>
          </div>
          <span class="sub-title">Fine-grained 3D Modeling System 2 (Standby)</span>
        </div>
      </div>
      <div class="header-right">
        <div class="status-indicator">
          <span class="status-dot"></span>
          <span class="status-text">系统状态: 待接入 (Standby)</span>
        </div>
      </div>
    </header>

    <!-- 主体空白预留展示区 -->
    <main class="blank-main-area">
      <div class="blank-container">
        <div class="placeholder-box">
          <span class="placeholder-icon">📐</span>
          <h2>精细三维建模系统 2</h2>
          <p class="placeholder-text">（本界面为系统 2 空白预留界面，无任何多余功能，待后续直接接入新系统）</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.modeling-system-2-blank {
  width: 100%;
  height: 100%;
  background-color: #020710;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  font-family: 'Outfit', 'Inter', -apple-system, sans-serif;
}

/* Header */
.modeling-header {
  height: 64px;
  min-height: 64px;
  background: rgba(4, 12, 26, 0.75);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
  z-index: 5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.35);
  border-radius: 8px;
  padding: 6px 14px;
  color: #00f2fe;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.back-btn:hover {
  background: rgba(0, 229, 255, 0.18);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.25);
  transform: translateX(-2px);
}

.header-title-group {
  display: flex;
  flex-direction: column;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-title-group h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #ffffff;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.system-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(0, 229, 255, 0.15);
  border: 1px solid rgba(0, 229, 255, 0.35);
  color: #00e5ff;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.sub-title {
  font-size: 11px;
  color: rgba(0, 229, 255, 0.7);
  text-transform: uppercase;
  letter-spacing: 1.2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(7, 20, 38, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 20px;
  padding: 5px 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #8c8c8c;
}

.status-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

/* Blank Main Area */
.blank-main-area {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.blank-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px 70px;
  background: rgba(4, 14, 28, 0.5);
  border: 1px dashed rgba(0, 229, 255, 0.25);
  border-radius: 16px;
  backdrop-filter: blur(8px);
}

.placeholder-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  text-align: center;
}

.placeholder-icon {
  font-size: 52px;
  opacity: 0.7;
}

.placeholder-box h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 1px;
}

.placeholder-text {
  margin: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.45);
}
</style>
