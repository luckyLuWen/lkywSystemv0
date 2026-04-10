<template>
  <div class="dashboard-container">
    <button
      v-if="route.path !== '/'"
      type="button"
      class="return-home-btn"
      @click="router.push('/')"
    >
      返回首页
    </button>

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
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
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
  position: relative;
  height: 100vh;
  overflow: hidden;
}

.module-container {
  width: 100%;
  height: 100%;
  position: relative;
  z-index: 1;
}

.return-home-btn {
  position: absolute;
  top: 18px;
  left: 18px;
  z-index: 30;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(0, 229, 255, 0.18);
  background: rgba(2, 10, 22, 0.62);
  color: #e6faff;
  font-size: 14px;
  cursor: pointer;
  backdrop-filter: blur(12px);
  box-shadow:
    inset 0 0 12px rgba(0, 229, 255, 0.06),
    0 8px 22px rgba(0, 0, 0, 0.18);
  transition: 0.18s ease;
}

.return-home-btn:hover {
  color: var(--primary-color);
  border-color: rgba(0, 229, 255, 0.3);
  background: rgba(0, 229, 255, 0.08);
  box-shadow:
    inset 0 0 12px rgba(0, 229, 255, 0.08),
    0 0 16px rgba(0, 229, 255, 0.12);
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
