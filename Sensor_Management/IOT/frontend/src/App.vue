<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { fetchGatewayHealth, fetchGatewayStatus } from './gateway-api'
import { EDGE_GATEWAY_WS_URL } from './gateway-config'
import { store } from './store.js'

let socket = null
let retryTimer = null
let gatewayTimer = null

const refreshStatusText = () => {
  if (!store.gatewayOnline) {
    store.status = '网关离线'
    return
  }
  if (!store.connected) {
    store.status = '实时通道断开'
    return
  }
  store.status = store.samplingRunning ? '采集中' : '已暂停'
}

const applyNodeStatus = (nodes = {}) => {
  Object.entries(nodes).forEach(([key, value]) => {
    if (store.nodes[key]) {
      Object.assign(store.nodes[key], value)
    }
  })
}

const applyGatewayPayload = (payload = {}) => {
  store.gatewayOnline = true
  store.gatewayMode = payload.mode || store.gatewayMode
  store.samplingRunning = Boolean(payload.running)
  store.lastSampleAt = payload.last_sample_at || store.lastSampleAt
  store.databaseOnline = Boolean(payload.database?.ok)
  store.videoOnline = Boolean(payload.video?.online)
  applyNodeStatus(payload.nodes)
  refreshStatusText()
}

const refreshGatewayState = async () => {
  try {
    const [health, status] = await Promise.all([fetchGatewayHealth(), fetchGatewayStatus()])
    applyGatewayPayload(health)
    applyGatewayPayload(status)
  } catch (error) {
    store.gatewayOnline = false
    store.samplingRunning = false
    store.databaseOnline = false
    store.videoOnline = false
    refreshStatusText()
  }
}

const connectWS = () => {
  socket = new WebSocket(EDGE_GATEWAY_WS_URL)

  socket.onopen = () => {
    store.connected = true
    if (retryTimer) clearTimeout(retryTimer)
    refreshStatusText()
  }

  socket.onclose = () => {
    store.connected = false
    refreshStatusText()
    retryTimer = setTimeout(connectWS, 3000)
  }

  socket.onerror = () => {
    if (socket) socket.close()
  }

  socket.onmessage = (event) => {
    try {
      store.data = JSON.parse(event.data)
      store.lastRealtimeAt = new Date().toISOString()
    } catch (error) {
      console.error(error)
    }
  }
}

// === 菜单控制状态变量整合 ===
const isOverviewOpen = ref(true)
const isLogicMenuOpen = ref(false)
const isNodeGroupOpen = ref(false) // 统一接管感知单元A和B的菜单展开状态
const isFixedNodeGroupOpen = ref(false)
const isDroneGroupOpen = ref(false)

const toggleOverview = () => { isOverviewOpen.value = !isOverviewOpen.value }
const toggleLogicMenu = () => { isLogicMenuOpen.value = !isLogicMenuOpen.value }
const toggleNodeGroup = () => { isNodeGroupOpen.value = !isNodeGroupOpen.value }
const toggleFixedNodeGroup = () => { isFixedNodeGroupOpen.value = !isFixedNodeGroupOpen.value }
const toggleDroneGroup = () => { isDroneGroupOpen.value = !isDroneGroupOpen.value }
onMounted(() => {
  connectWS()
  refreshGatewayState()
  gatewayTimer = setInterval(refreshGatewayState, 5000)
})

onUnmounted(() => {
  if (socket) socket.close()
  if (retryTimer) clearTimeout(retryTimer)
  if (gatewayTimer) clearInterval(gatewayTimer)
})
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">交通事故立体感知传感网</div>
      <nav>
        <div class="nav-group">
          <div class="nav-item group-title" @click="toggleOverview">
            <span>立体感知网络总览</span>
            <span class="arrow">{{ isOverviewOpen ? '▼' : '▶' }}</span>
          </div>

          <div v-if="isOverviewOpen" class="sub-menu">
            <router-link to="/" class="nav-item sub-item">立体感知实时态势监测</router-link>

            <div class="nav-item sub-item nested-group-title" @click="toggleLogicMenu">
              <span>融合逻辑图谱</span>
              <span class="arrow-small">{{ isLogicMenuOpen ? '▼' : '▶' }}</span>
            </div>

            <div v-if="isLogicMenuOpen" class="level-3-menu">
              <router-link to="/logic" class="nav-item level-3-item logic-main">全局桑基图</router-link>
              <router-link to="/logic/early" class="nav-item level-3-item">前期: 早期预警</router-link>
              <router-link to="/logic/confirm" class="nav-item level-3-item">中期: 火灾确认</router-link>
              <router-link to="/logic/spread" class="nav-item level-3-item">后期: 态势蔓延</router-link>
              <router-link to="/logic/noise" class="nav-item level-3-item">辅助: 干扰清洗</router-link>
            </div>
          </div>
        </div>

        <div class="nav-group">
          <div class="nav-item group-title" @click="toggleNodeGroup">
            <span>地面监测移动节点总控</span>
            <span class="arrow">{{ isNodeGroupOpen ? '▼' : '▶' }}</span>
          </div>
          <div v-if="isNodeGroupOpen" class="sub-menu">
            <router-link to="/node1" class="nav-item sub-item">感知单元(UGV)-001 </router-link>
            <router-link to="/node2" class="nav-item sub-item">感知单元(UGV)-002 </router-link>
            <router-link to="/node4" class="nav-item sub-item">感知单元(UGV)-003 </router-link>
            <router-link to="/node5" class="nav-item sub-item">感知单元(UGV)-004 </router-link>
            <router-link to="/node6" class="nav-item sub-item">感知单元(UGV)-005 </router-link>
          </div>
        </div>

        <div class="nav-group">
          <div class="nav-item group-title" @click="toggleFixedNodeGroup">
            <span>固定环境感知节点总控</span>
            <span class="arrow">{{ isFixedNodeGroupOpen ? '▼' : '▶' }}</span>
          </div>
          <div v-if="isFixedNodeGroupOpen" class="sub-menu">
            <router-link to="/node3" class="nav-item sub-item">固定监测站-001</router-link>
            <router-link to="/node7" class="nav-item sub-item">固定监测站-002</router-link>
            <router-link to="/node8" class="nav-item sub-item">固定监测站-003</router-link>
            <router-link to="/node9" class="nav-item sub-item">固定监测站-004</router-link>
            <router-link to="/node10" class="nav-item sub-item">固定监测站-005</router-link>
            </div>
        </div>

        <div class="nav-group">
          <div class="nav-item group-title" @click="toggleDroneGroup">
            <span>空域监测移动节点总控</span>
            <span class="arrow">{{ isDroneGroupOpen ? '▼' : '▶' }}</span>
          </div>
          <div v-if="isDroneGroupOpen" class="sub-menu">
            <!-- 对应 DroneView.vue -->
            <router-link to="/drone" class="nav-item sub-item">空域监测节点-001</router-link>
            <!-- 对应 DroneView1.vue (修正了原描述中的 DroneView.1vue) -->
            <router-link to="/drone1" class="nav-item sub-item">空域监测节点-002</router-link>
            <!-- 对应 DroneView2.vue -->
            <router-link to="/drone2" class="nav-item sub-item">空域监测节点-003</router-link>
          </div>
        </div>
      </nav>

      <div class="footer">
        <div>系统状态: {{ store.status }}</div>
        <div style="font-size: 0.7rem; color: #888; margin-top: 5px;">网关: {{ store.gatewayBaseUrl }}</div>
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
body { margin: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f0f2f5; }
.layout { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
.sidebar { width: 250px; background: #20232a; color: white; display: flex; flex-direction: column; flex-shrink: 0; box-shadow: 2px 0 10px rgba(0,0,0,0.3); z-index: 10; }
.logo { padding: 25px 20px; font-size: 1.3rem; font-weight: bold; text-align: center; border-bottom: 1px solid #333; background: linear-gradient(135deg, #181a1f 0%, #20232a 100%); letter-spacing: 1px; }
nav { flex: 1; padding-top: 15px; overflow-y: auto; }
nav::-webkit-scrollbar { width: 4px; }
nav::-webkit-scrollbar-thumb { background: #444; border-radius: 2px; }

.nav-item { display: block; padding: 14px 25px; color: #a6adb4; text-decoration: none; transition: all 0.2s; border-left: 4px solid transparent; font-size: 0.95rem; }
.nav-item:hover { color: white; background: #2c3038; }
.router-link-active { color: #61dafb; background: #2c3038; border-left-color: #61dafb; font-weight: 600; }

.nav-group { margin-bottom: 5px; }
.group-title { cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none; color: #fff; font-weight: bold; background: #282c34; margin-top: 5px; border-left: 4px solid #444; }
.group-title:hover { background: #333842; border-left-color: #666; }

.sub-menu { background: #16181d; transition: all 0.3s; padding-bottom: 5px; }
.sub-item { padding-left: 50px !important; font-size: 0.9rem; border-left: 4px solid transparent; color: #888; }
.sub-item:hover { color: #ddd; }
.sub-menu .router-link-active { background: #1a1d23; border-left-color: transparent; color: #61dafb; }

.nested-group-title { cursor: pointer; display: flex; justify-content: space-between; align-items: center; color: #ccc; font-weight: bold; }
.nested-group-title:hover { color: white; background: #252830; }

.level-3-menu { background: #0f1114; transition: all 0.3s; }
.level-3-item {
  padding-left: 75px !important;
  font-size: 0.85rem;
  color: #777;
  padding-top: 10px;
  padding-bottom: 10px;
}
.level-3-item:hover { color: #fff; }
.level-3-item.router-link-active {
  color: #f6ad55 !important;
  background: #1a1d23;
  border-left: 4px solid #d69e2e !important;
}

.arrow { font-size: 0.7rem; opacity: 0.6; transition: transform 0.2s; }
.arrow-small { font-size: 0.6rem; opacity: 0.5; margin-left: 5px; }

.link-style.router-link-active { border-left-color: #3182ce; background: #2b3a4a; color: #63b3ed; }
.link-style-drone.router-link-active { border-left-color: #8b5cf6; background: #2d2b38; color: #c4b5fd; }

.footer { padding: 15px; font-size: 0.8rem; text-align: center; color: #666; border-top: 1px solid #333; background: #181a1f; }
.content { flex: 1; padding: 30px; overflow-y: auto; background-color: #f7fafc; position: relative; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>