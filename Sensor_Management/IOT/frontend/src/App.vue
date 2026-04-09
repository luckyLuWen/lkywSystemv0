<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { store } from './store.js'

let socket = null
let retryTimer = null

const connectWS = () => {
  const wsUrl = "ws://localhost:8000/ws"
  socket = new WebSocket(wsUrl)
  
  socket.onopen = () => { 
    console.log("WS Connected"); store.connected = true; store.status = "🟢 在线"; 
    if (retryTimer) clearInterval(retryTimer)
  }
  socket.onclose = () => { 
    console.log("WS Disconnected"); store.connected = false; store.status = "🔴 离线"; 
    retryTimer = setTimeout(connectWS, 3000)
  }
  socket.onmessage = (e) => { 
    try { store.data = JSON.parse(e.data) } catch (err) {} 
  }
}

// === 折叠状态控制 ===
const isOverviewOpen = ref(true)   // 一级：总览
const isLogicMenuOpen = ref(false) // 🟢 [新增] 二级：逻辑图谱折叠状态
const isNode1Open = ref(false)
const isNode2Open = ref(false)

const toggleOverview = () => { isOverviewOpen.value = !isOverviewOpen.value }
const toggleLogicMenu = () => { isLogicMenuOpen.value = !isLogicMenuOpen.value } // 🟢
const toggleNode1 = () => { isNode1Open.value = !isNode1Open.value }
const toggleNode2 = () => { isNode2Open.value = !isNode2Open.value }

onMounted(() => { connectWS() })
onUnmounted(() => { if (socket) socket.close(); if (retryTimer) clearTimeout(retryTimer) })
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">🔥 监控指挥中心</div>
      <nav>
        
        <div class="nav-group">
          <div class="nav-item group-title" @click="toggleOverview">
            <span>📊 全站总览大屏</span>
            <span class="arrow">{{ isOverviewOpen ? '▼' : '▶' }}</span>
          </div>
          
          <div v-if="isOverviewOpen" class="sub-menu">
            <router-link to="/" class="nav-item sub-item">🖥️ 实时监控面板</router-link>
            
            <div class="nav-item sub-item nested-group-title" @click="toggleLogicMenu">
              <span>🧬 融合逻辑图谱</span>
              <span class="arrow-small">{{ isLogicMenuOpen ? '▼' : '▶' }}</span>
            </div>

            <div v-if="isLogicMenuOpen" class="level-3-menu">
              <router-link to="/logic" class="nav-item level-3-item logic-main">🌐 全局桑基图</router-link>
              <router-link to="/logic/early" class="nav-item level-3-item">⚠️ 前期: 早期预警</router-link>
              <router-link to="/logic/confirm" class="nav-item level-3-item">🔥 中期: 火灾确证</router-link>
              <router-link to="/logic/spread" class="nav-item level-3-item">💨 后期: 态势蔓延</router-link>
              <router-link to="/logic/noise" class="nav-item level-3-item">🛡️ 辅助: 干扰清洗</router-link>
            </div>
          </div>
        </div>
        
        <div class="nav-group">
          <div class="nav-item group-title" @click="toggleNode1">
            <span>🚗 无人车 A (219)</span>
            <span class="arrow">{{ isNode1Open ? '▼' : '▶' }}</span>
          </div>
          <div v-if="isNode1Open" class="sub-menu">
            <router-link to="/node1" class="nav-item sub-item">⚙️ 总体状态</router-link>
            <router-link to="/node1/weather" class="nav-item sub-item">🌤️ 气象监控</router-link>
            <router-link to="/node1/env" class="nav-item sub-item">☢️ 环境监控</router-link>
          </div>
        </div>

        <div class="nav-group">
          <div class="nav-item group-title" @click="toggleNode2">
            <span>🚙 无人车 B (241)</span>
            <span class="arrow">{{ isNode2Open ? '▼' : '▶' }}</span>
          </div>
          <div v-if="isNode2Open" class="sub-menu">
            <router-link to="/node2" class="nav-item sub-item">⚙️ 总体状态</router-link>
            <router-link to="/node2/weather" class="nav-item sub-item">🌤️ 气象监控</router-link>
            <router-link to="/node2/env" class="nav-item sub-item">☢️ 环境监控</router-link>
          </div>
        </div>

        <router-link to="/node3" class="nav-item group-title link-style">
          <span>🌬️ 固定杆 (71)</span>
          <span class="arrow">➜</span>
        </router-link>

        <router-link to="/drone" class="nav-item group-title link-style-drone">
          <span>🚁 无人机侦查</span>
          <span class="arrow">➜</span>
        </router-link>

      </nav>
      <div class="footer">
        <div>系统状态: {{ store.status }}</div>
        <div style="font-size: 0.7rem; color: #444; margin-top: 5px;">v2.0.0 IoT System</div>
      </div>
    </aside>

    <main class="content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style>
/* 全局样式 */
body { margin: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f0f2f5; }
.layout { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
.sidebar { width: 250px; background: #20232a; color: white; display: flex; flex-direction: column; flex-shrink: 0; box-shadow: 2px 0 10px rgba(0,0,0,0.3); z-index: 10; }
.logo { padding: 25px 20px; font-size: 1.3rem; font-weight: bold; text-align: center; border-bottom: 1px solid #333; background: linear-gradient(135deg, #181a1f 0%, #20232a 100%); letter-spacing: 1px; }
nav { flex: 1; padding-top: 15px; overflow-y: auto; }
nav::-webkit-scrollbar { width: 4px; }
nav::-webkit-scrollbar-thumb { background: #444; border-radius: 2px; }

/* 基础菜单项 */
.nav-item { display: block; padding: 14px 25px; color: #a6adb4; text-decoration: none; transition: all 0.2s; border-left: 4px solid transparent; font-size: 0.95rem; }
.nav-item:hover { color: white; background: #2c3038; }
.router-link-active { color: #61dafb; background: #2c3038; border-left-color: #61dafb; font-weight: 600; }

/* 一级菜单组 */
.nav-group { margin-bottom: 5px; }
.group-title { cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none; color: #fff; font-weight: bold; background: #282c34; margin-top: 5px; border-left: 4px solid #444; }
.group-title:hover { background: #333842; border-left-color: #666; }

/* 二级子菜单 */
.sub-menu { background: #16181d; transition: all 0.3s; padding-bottom: 5px; }
.sub-item { padding-left: 50px !important; font-size: 0.9rem; border-left: 4px solid transparent; color: #888; }
.sub-item:hover { color: #ddd; }
.sub-menu .router-link-active { background: #1a1d23; border-left-color: transparent; color: #61dafb; }

/* 🟢 [新增] 二级菜单中的折叠项 (逻辑图谱父级) */
.nested-group-title { cursor: pointer; display: flex; justify-content: space-between; align-items: center; color: #ccc; font-weight: bold; }
.nested-group-title:hover { color: white; background: #252830; }

/* 🟢 [新增] 三级子菜单 */
.level-3-menu { background: #0f1114; /* 比二级更深一点的背景 */ transition: all 0.3s; }
.level-3-item { 
  padding-left: 75px !important; /* 更深的缩进 */
  font-size: 0.85rem; 
  color: #777;
  padding-top: 10px;
  padding-bottom: 10px;
}
.level-3-item:hover { color: #fff; }
/* 三级菜单激活高亮 (金色系) */
.level-3-item.router-link-active { 
  color: #f6ad55 !important; 
  background: #1a1d23; 
  border-left: 4px solid #d69e2e !important;
}

/* 图标与箭头 */
.arrow { font-size: 0.7rem; opacity: 0.6; transition: transform 0.2s; }
.arrow-small { font-size: 0.6rem; opacity: 0.5; margin-left: 5px; }

/* 独立页面的特殊颜色 */
.link-style.router-link-active { border-left-color: #3182ce; background: #2b3a4a; color: #63b3ed; }
.link-style-drone.router-link-active { border-left-color: #8b5cf6; background: #2d2b38; color: #c4b5fd; }

.footer { padding: 15px; font-size: 0.8rem; text-align: center; color: #666; border-top: 1px solid #333; background: #181a1f; }
.content { flex: 1; padding: 30px; overflow-y: auto; background-color: #f7fafc; position: relative; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>