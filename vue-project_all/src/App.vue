<template>
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
</template>

<script setup>
import { useRouter } from 'vue-router'
import Header from './components/Header.vue'

// 1. 实例化路由工具
const router = useRouter()

// 2. 处理导航栏点击事件，改为路由跳转
const handleMenuChange = (key) => {
  // 根据你 Header 组件传回来的 key，决定跳转到哪个网址
  switch (key) {
    case 'home':
      router.push('/') // 首页
      break
    case 'realtime':
      router.push('/realtime') // 实时检测页面，显示系统大屏界面
      break
    case 'sensor':
      router.push('/sensor-manage') // 跳转到我们刚才配置的传感器管理子系统
      break
    case 'modeling':
      router.push('/modeling') // 精细建模
      break
    case 'coordination':
      router.push('/coordination') // 协同响应
      break
    case 'simulation':
      router.push('/simulation') // 仿真推演
      break
    default:
      router.push('/') // 默认兜底回到首页
  }
}
</script>

<style>
/* 全局变量与基础样式 (无需修改，保持原样) */
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
/* 局部样式 (无需修改，保持原样) */
.dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  position: relative;
}



.module-container {
  flex: 1;
  display: flex;
  width: 100%;
  position: relative;
  z-index: 10;
  /* 移除 pointer-events: none; 允许鼠标事件传递到子元素 */
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