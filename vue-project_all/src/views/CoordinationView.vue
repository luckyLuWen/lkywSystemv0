<template>
  <div class="coordination-container">
    <iframe
      :key="iframeKey"
      :src="iframeSrc"
      frameborder="0"
      class="coordination-iframe"
      @load="onIframeLoad"
    ></iframe>
  </div>
</template>

<script setup>
import { onActivated, ref } from 'vue'
import { buildCollaborativeResponseIframeSrc } from '../config/subsystems'

const iframeSrc = ref(buildCollaborativeResponseIframeSrc())
const iframeKey = ref(0)

function refreshIframe() {
  iframeSrc.value = buildCollaborativeResponseIframeSrc()
  iframeKey.value += 1
}

const onIframeLoad = () => {
  console.log('Collaborative response page loaded')
}

onActivated(() => {
  refreshIframe()
})
</script>

<style scoped>
.coordination-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--bg-color);
}

.coordination-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #000;
}
</style>
