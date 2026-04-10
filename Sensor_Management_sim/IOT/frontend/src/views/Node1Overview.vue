<script setup>
import { computed } from 'vue'
import { store } from '../store.js'

const nodeState = computed(() => store.nodes.node1)
</script>

<template>
  <div class="page-container">
    <h1>无人车 A - 总体状态</h1>

    <div class="status-banner" :class="{ online: nodeState.online, offline: !nodeState.online }">
      <div class="icon">{{ nodeState.online ? '●' : '○' }}</div>
      <div class="info">
        <h2>{{ nodeState.online ? '节点在线' : '节点离线' }}</h2>
        <p>设备地址: {{ nodeState.address || '未配置' }}</p>
      </div>
    </div>

    <h3 style="margin-top: 30px;">挂载监控项</h3>
    <div class="device-list">
      <div class="device-item" @click="$router.push('/node1/weather')">
        <div class="device-icon">🌡</div>
        <div class="device-info">
          <h4>气象监控</h4>
          <p>数据: {{ store.data.node1.temp }}°C | {{ store.data.node1.hum }}%</p>
        </div>
        <div class="arrow">详情 →</div>
      </div>

      <div class="device-item" @click="$router.push('/node1/env')">
        <div class="device-icon">☁</div>
        <div class="device-info">
          <h4>环境监控</h4>
          <p>TVOC: {{ store.data.node1.tvoc }} | 烟雾: {{ store.data.node1.smoke }} | CO: {{ store.data.node1.co }}</p>
        </div>
        <div class="arrow">详情 →</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container { padding: 30px; }
.status-banner { padding: 30px; border-radius: 12px; display: flex; align-items: center; gap: 20px; background: #eee; color: #666; }
.status-banner.online { background: #e6fffa; color: #2c7a7b; border: 1px solid #b2f5ea; }
.status-banner.offline { background: #fff5f5; color: #c53030; border: 1px solid #feb2b2; }
.icon { font-size: 3rem; }
.device-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 15px; }
.device-item { background: white; padding: 20px; border-radius: 10px; border: 1px solid #eee; display: flex; align-items: center; gap: 15px; cursor: pointer; transition: 0.2s; }
.device-item:hover { border-color: #42b983; transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.device-icon { font-size: 2rem; background: #f0f2f5; padding: 10px; border-radius: 50%; }
.device-info h4 { margin: 0 0 5px 0; color: #333; }
.device-info p { margin: 0; color: #888; font-size: 0.9rem; }
.arrow { margin-left: auto; color: #ccc; font-size: 0.8rem; }
</style>
