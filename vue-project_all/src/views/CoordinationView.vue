<template>
  <div class="coordination-container">
    <iframe
      src="/collaborative-response/index.html"
      frameborder="0"
      class="coordination-iframe"
      @load="onIframeLoad"
    ></iframe>
  </div>
</template>

<script setup>
const onIframeLoad = () => {
  console.log('Collaborative response page loaded')
}
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
