<template>
  <header class="header">
    <div class="header-title">
      <span class="logo-icon">&#8859;</span>
      “两客一危”智能救援系统
    </div>
    
    <nav class="header-nav">
      <a 
        v-for="item in navList" 
        :key="item.key"
        :class="{ active: activeKey === item.key }"
        @click="selectNav(item.key)"
      >
        {{ item.label }}
      </a>
    </nav>

    <div class="header-info">
      <span>多云 32°C</span>
      <span>09:01:00</span>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['change-menu'])

const navList = [
  { label: '首页', key: 'home' },
  { label: '传感器管理', key: 'sensor' },
  { label: '实时检测', key: 'realtime' },
  { label: '协同响应', key: 'coordination' },
  { label: '精细建模', key: 'modeling' },
  { label: '仿真推演', key: 'simulation' },
]

const activeKey = ref('home')

const selectNav = (key) => {
  activeKey.value = key
  emit('change-menu', key)
}
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
  margin-bottom: 20px;
  pointer-events: auto; /* 恢复鼠标交互 */
}

.header-title {
  font-size: 24px;
  font-weight: bold;
  color: var(--primary-color);
  text-shadow: var(--glow-shadow);
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 28px;
}

.header-nav {
  display: flex;
  gap: 30px;
}

.header-nav a {
  color: #ddd;
  text-decoration: none;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.header-nav a:hover, .header-nav a.active {
  color: var(--primary-color);
  text-shadow: var(--glow-shadow);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 14px;
}
</style>