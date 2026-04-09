<template>
  <div class="accident-detection-container">
    <div class="iframe-container">
      <iframe
        src="/realtime-detection/index.html"
        frameborder="0"
        class="accident-iframe"
        @load="onIframeLoad"
      ></iframe>
    </div>
  </div>
</template>

<script setup>
const onIframeLoad = () => {
  console.log('Realtime detection page loaded')
}
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
