<template>
  <div class="sensor-manage-container">
    <iframe
      :key="iframeKey"
      :src="iframeSrc"
      frameborder="0"
      class="sensor-iframe"
      @load="onIframeLoad"
    ></iframe>
  </div>
</template>

<script setup>
import { onActivated, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { buildSensorManagementIframeSrc } from '../config/subsystems'

const route = useRoute()
const iframeSrc = ref('')
const iframeKey = ref(0)

const refreshIframe = () => {
  let baseSrc = buildSensorManagementIframeSrc()
  // 如果存在 target 参数，拼接作为 iframe 内部系统的 Hash 路由跳转
  if (route.query.target) {
    baseSrc += `#/${route.query.target}`
  }
  iframeSrc.value = baseSrc
  iframeKey.value += 1
}

const onIframeLoad = () => {
  console.log('Sensor management page loaded:', iframeSrc.value)
}

watch(() => route.query.target, () => {
  refreshIframe()
})

onActivated(() => {
  refreshIframe()
})
</script>

<style scoped>
.sensor-manage-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--bg-color);
}

.sensor-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #000;
}
</style>
