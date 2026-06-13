<template>
  <div class="dashboard-container">
    <!-- 统一的子页面导航栏，避免返回首页按钮遮挡子系统自身标题 -->
    <header v-if="route.path !== '/'" class="subpage-navbar">
      <button
        type="button"
        class="return-home-btn-inline"
        @click="router.push('/')"
      >
        <span class="back-icon">←</span> 返回首页
      </button>
      <div class="nav-divider"></div>
      <span class="subpage-title">{{ routeTitle }}</span>
    </header>

    <main class="module-container">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()

const routeTitle = computed(() => {
  switch (route.path) {
    case '/realtime': return '事故监控中心'
    case '/sensor-manage': return '设备管理服务'
    case '/coordination': return '协同响应指挥'
    case '/modeling': return '精细建模'
    case '/simulation': return '仿真推演'
    default: return ''
  }
})
</script>

<style>
:root {
  --primary-color: #00e5ff;
  --text-color: #ffffff;
  --bg-color: #020813;
  --panel-bg: rgba(4, 20, 40, 0.6);
  --border-color: rgba(0, 229, 255, 0.3);
  --glow-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
}

body {
  margin: 0;
  padding: 0;
  font-family: 'Microsoft YaHei', sans-serif;
  background-color: var(--bg-color);
  color: var(--text-color);
  height: 100vh;
  overflow: hidden;
  background-image: radial-gradient(circle at center, #0a1b35 0%, #020813 100%);
}
</style>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.module-container {
  flex: 1;
  min-height: 0;
  position: relative;
  z-index: 1;
}

.subpage-navbar {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  background: rgba(2, 10, 22, 0.85);
  border-bottom: 1px solid rgba(0, 229, 255, 0.25);
  backdrop-filter: blur(12px);
  z-index: 10;
  flex-shrink: 0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}

.return-home-btn-inline {
  min-height: 36px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(0, 229, 255, 0.25);
  background: rgba(0, 229, 255, 0.08);
  color: #e6faff;
  font-size: 14px;
  cursor: pointer;
  transition: 0.18s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  backdrop-filter: blur(8px);
}

.return-home-btn-inline:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
  background: rgba(0, 229, 255, 0.15);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.2);
}

.back-icon {
  font-size: 16px;
  line-height: 1;
}

.nav-divider {
  width: 1px;
  height: 18px;
  background: rgba(0, 229, 255, 0.25);
  margin: 0 16px;
}

.subpage-title {
  font-size: 18px;
  font-weight: 700;
  color: #effaff;
  letter-spacing: 1px;
  text-shadow: var(--glow-shadow);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
