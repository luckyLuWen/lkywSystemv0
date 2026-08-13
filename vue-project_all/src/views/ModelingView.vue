<!--
================================================================================
  精细三维建模系统主入口与调度容器 (ModelingView.vue)
  
  【功能说明】
  1. 页面顶部常驻显示“精细建模系统 1”与“精细建模系统 2”的切换按钮；
  2. 精细建模系统 1：当前完整的三维建模检测系统；
  3. 精细建模系统 2：干净独立的空白界面（预留给后续新系统接入）；
  4. 后续删除系统 1 时，直接删除 ModelingSystem1.vue 并移除本文件中的系统1引用即可。
================================================================================
-->
<template>
  <div class="modeling-view-root">
    <!-- 顶部高亮醒目的系统切换栏 -->
    <div class="system-switcher-container">
      <div class="switcher-pill">
        <button
          type="button"
          class="switch-btn"
          :class="{ active: currentSystem === '1' }"
          @click="setSystem('1')"
        >
          <span class="btn-indicator" v-if="currentSystem === '1'"></span>
          <span>精细建模系统 1</span>
        </button>
        
        <button
          type="button"
          class="switch-btn"
          :class="{ active: currentSystem === '2' }"
          @click="setSystem('2')"
        >
          <span class="btn-indicator" v-if="currentSystem === '2'"></span>
<<<<<<< HEAD
          <span>精细建模系统 2 (空白预留)</span>
=======
          <span>精细三维建模系统 2 (两客一危专版)</span>
>>>>>>> origin/develop
        </button>
      </div>
    </div>

    <!-- 子系统主视图渲染区 -->
    <div class="subsystem-viewport">
      <keep-alive>
        <component :is="activeComponent" />
      </keep-alive>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// 引入独立的两个子系统组件
import ModelingSystem1 from './modeling/ModelingSystem1.vue'
import ModelingSystem2 from './modeling/ModelingSystem2.vue'

const route = useRoute()
const router = useRouter()

// 默认进入“精细建模系统 1”，支持通过 ?sys=1 或 ?sys=2 传参直达
const currentSystem = ref('1')

// 同步路由 query 参数
const syncFromRoute = () => {
  const querySys = route.query.sys || route.query.system
  if (querySys === '1' || querySys === '2') {
    currentSystem.value = String(querySys)
  }
}

// 切换子系统
const setSystem = (sysKey) => {
  currentSystem.value = sysKey
  router.replace({
    path: route.path,
    query: { ...route.query, sys: sysKey }
  })
}

// 动态映射组件
const activeComponent = computed(() => {
  if (currentSystem.value === '2') {
    return ModelingSystem2
  }
  return ModelingSystem1
})

watch(() => route.query.sys, () => {
  syncFromRoute()
})

onMounted(() => {
  syncFromRoute()
})
</script>

<style scoped>
.modeling-view-root {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: #020710;
}

/* 顶部高亮醒目的系统切换栏 */
.system-switcher-container {
  position: absolute;
  top: 14px;
  right: 320px;
  z-index: 1000;
  pointer-events: auto;
}

.switcher-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(3, 12, 28, 0.92);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 229, 255, 0.35);
  border-radius: 30px;
  padding: 4px 6px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5), 0 0 15px rgba(0, 229, 255, 0.15);
}

.switch-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 20px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.75);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  letter-spacing: 0.5px;
}

.switch-btn:hover {
  background: rgba(0, 229, 255, 0.12);
  color: #00ffd8;
}

.switch-btn.active {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.3), rgba(0, 255, 216, 0.25));
  border: 1px solid #00ffd8;
  color: #ffffff;
  box-shadow: 0 0 14px rgba(0, 255, 216, 0.35);
  text-shadow: 0 0 8px rgba(0, 255, 216, 0.5);
}

.btn-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00ffd8;
  box-shadow: 0 0 6px #00ffd8;
}

/* 子系统视口容器 */
.subsystem-viewport {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>
