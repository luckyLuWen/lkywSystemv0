<template>
  <div class="dashboard-container">
    <SystemChrome v-if="route.path === '/'" />

    <main class="module-container">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <keep-alive :key="authUser?.username || 'anonymous'">
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { watch } from 'vue'
import { authUser } from './composables/useAuth'
import { useRoute, useRouter } from 'vue-router'
import { canAccessRoute, currentRole } from './composables/useRoleAccess'
import SystemChrome from './components/SystemChrome.vue'

const router = useRouter()
const route = useRoute()

watch(currentRole, () => {
  if (route.path !== '/' && !canAccessRoute(route.meta.roles || [])) {
    router.replace('/')
  }
})
</script>

<style>
:root {
  --font-family-ui: 'Microsoft YaHei UI', 'Microsoft YaHei', '微软雅黑', 'PingFang SC', 'Segoe UI', Arial, sans-serif;
  --font-family-number: 'DIN Alternate', Arial, sans-serif;
  --font-size-system-title: 30px;
  --font-size-navigation: 19px;
  --font-size-panel-title: 17px;
  --font-size-body: 15px;
  --font-size-assist: 13px;
  --font-weight-heading: 600;
  --font-weight-body: 400;
  --primary-color: #00e5ff;
  --text-color: #ffffff;
  --bg-color: #020813;
  --panel-bg: rgba(4, 20, 40, 0.6);
  --border-color: rgba(0, 229, 255, 0.3);
  --glow-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
  /* 推荐的“晴朗明亮”天气：优先保证地图和业务标注的可读性。 */
  --scene-brightness: 1.28;
  --scene-saturation: 1.12;
  --scene-contrast: 1.04;
}

html[data-weather-mode='cloudy'] { --scene-saturation: .94; --scene-contrast: 1; }
html[data-weather-mode='rain'] { --scene-saturation: .78; --scene-contrast: .94; }
html[data-weather-mode='night'] { --scene-saturation: .76; --scene-contrast: 1.02; }

body {
  caret-color: transparent;
  margin: 0;
  padding: 0;
  font-family: var(--font-family-ui);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-body);
  background-color: var(--bg-color);
  color: var(--text-color);
  height: 100vh;
  overflow: hidden;
  background-image: radial-gradient(circle at center, #12385a 0%, #03101f 72%, #020813 100%);
}

/* 仅提亮三维底图，HUD、告警色和文字不会被滤镜冲淡。 */
.cesium-container {
  filter: brightness(var(--scene-brightness)) saturate(var(--scene-saturation)) contrast(var(--scene-contrast));
  transition: filter .35s ease;
}

button,
input,
select,
textarea {
  font: inherit;
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

<style>
input, textarea, [contenteditable="true"] { caret-color: auto; }
</style>
