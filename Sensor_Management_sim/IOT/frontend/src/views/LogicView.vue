<script setup>
import { ref, shallowRef } from 'vue'

// 1. 引入所有子组件 (确保你之前已经创建了这些文件)
import FusionSankey from '../components/FusionSankey.vue' // 全局桑基图组件
import LogicEarly from './LogicEarly.vue'     // 前期页面
import LogicConfirm from './LogicConfirm.vue' // 中期页面
import LogicSpread from './LogicSpread.vue'   // 后期页面
import LogicNoise from './LogicNoise.vue'     // 环境页面

// 2. 配置标签页
const tabs = [
  { id: 'global', name: '🌐 全局图谱', comp: FusionSankey },
  { id: 'early', name: '⚠️ 早期预警', comp: LogicEarly },
  { id: 'confirm', name: '🔥 火灾确证', comp: LogicConfirm },
  { id: 'spread', name: '💨 态势蔓延', comp: LogicSpread },
  { id: 'noise', name: '🛡️ 干扰清洗', comp: LogicNoise }
]

// 3. 当前选中的标签 (默认第一个)
const currentTab = shallowRef(FusionSankey)
const currentTabId = ref('global')

// 4. 切换逻辑
const switchTab = (tab) => {
  currentTabId.value = tab.id
  currentTab.value = tab.comp
}
</script>

<template>
  <div class="logic-container">
    
    <div class="nav-bar">
      <div class="page-title">🧬 融合逻辑决策中心</div>
      <div class="tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="tab-btn"
          :class="{ active: currentTabId === tab.id }"
          @click="switchTab(tab)"
        >
          {{ tab.name }}
        </button>
      </div>
    </div>

    <div class="content-area">
      <transition name="slide-fade" mode="out-in">
        <component :is="currentTab" />
      </transition>
    </div>

  </div>
</template>

<style scoped>
.logic-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 导航栏样式 */
.nav-bar {
  background: white;
  padding: 15px 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: #2c3e50;
}

.tabs {
  display: flex;
  gap: 10px;
  background: #f1f3f5;
  padding: 5px;
  border-radius: 8px;
}

.tab-btn {
  border: none;
  background: transparent;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  color: #606266;
  font-weight: 600;
  transition: all 0.3s;
}

.tab-btn:hover {
  color: #409eff;
  background: rgba(255,255,255,0.5);
}

/* 激活状态样式 */
.tab-btn.active {
  background: white;
  color: #409eff; /* 默认蓝色 */
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

/* 内容区 */
.content-area {
  flex: 1;
  /* 这里的样式可以确保子组件填满空间 */
  overflow-y: auto; 
}

/* 切换动画 */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(10px);
  opacity: 0;
}
</style>