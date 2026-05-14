<template>
  <div class="two-passenger-one-danger-control">
    <div class="dashboard-container">
      <Header @change-menu="handleMenuChange" />

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
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import Header from './Header.vue'

// 实例化路由工具
const router = useRouter()

// 处理导航栏点击事件，改为路由跳转
const handleMenuChange = (key) => {
  // 根据 Header 组件传回来的 key，决定跳转到哪个网址
  switch (key) {
    case 'realtime':
      router.push('/realtime') // 实时检测页面，显示系统大屏界面
      break
    case 'sensor':
      router.push('/sensor-manage') // 跳转到传感器管理子系统
      break
    case 'coordination':
      window.location.href = 'http://localhost:5174' // 协同响应
      break
    case 'modeling':
      router.push('/modeling') // 预留：精细建模
      break
    case 'simulation':
      router.push('/simulation') // 预留：仿真推演
      break
    default:
      router.push('/') // 默认兜底回到首页
  }
}
</script>

<style scoped>
.two-passenger-one-danger-control {
  width: 100%;
  height: 100%;
}

/* 全局变量与基础样式 */
:root {
  --primary-color: #00e5ff;
  --text-color: #ffffff;
  --bg-color: #020813;
  --panel-bg: rgba(4, 20, 40, 0.6);
  --border-color: rgba(0, 229, 255, 0.3);
  --glow-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
}

.dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
  position: relative;
  background-color: var(--bg-color);
  background-image: radial-gradient(circle at center, #0a1b35 0%, #020813 100%);
}

.module-container {
  flex: 1;
  display: flex;
  width: 100%;
  position: relative;
  z-index: 10;
}

/* 模块切换动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>