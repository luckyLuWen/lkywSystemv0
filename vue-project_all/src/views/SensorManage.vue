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
import { onActivated, ref } from 'vue'
import { buildSensorManagementIframeSrc } from '../config/subsystems'

const iframeSrc = ref(buildSensorManagementIframeSrc())
const iframeKey = ref(0)

const refreshIframe = () => {
  iframeSrc.value = buildSensorManagementIframeSrc()
  iframeKey.value += 1
}

const onIframeLoad = () => {
  console.log('Sensor management page loaded')
}

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
