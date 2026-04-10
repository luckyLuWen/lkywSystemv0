<template>
  <div class="accident-detection-container">
    <div class="iframe-container">
      <iframe
        :key="iframeKey"
        :src="iframeSrc"
        frameborder="0"
        class="accident-iframe"
        @load="onIframeLoad"
      ></iframe>
    </div>
  </div>
</template>

<script setup>
import { onActivated, ref } from 'vue'
import { buildRealtimeDetectionIframeSrc } from '../config/subsystems'

const iframeSrc = ref(buildRealtimeDetectionIframeSrc())
const iframeKey = ref(0)

function refreshIframe() {
  iframeSrc.value = buildRealtimeDetectionIframeSrc()
  iframeKey.value += 1
}

function onIframeLoad() {
  console.log('Realtime detection page loaded')
}

onActivated(() => {
  refreshIframe()
})
</script>

<style scoped>
.accident-detection-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.iframe-container {
  flex: 1;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.accident-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
