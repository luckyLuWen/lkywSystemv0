<template>
  <div class="simulation-container">
    <h1>仿真推演</h1>
    <div class="iframe-container">
      <iframe
        src="/constructive-simulation/index.html"
        frameborder="0"
        class="simulation-iframe"
        @load="onIframeLoad"
      ></iframe>
    </div>
  </div>
</template>

<script setup>
const onIframeLoad = () => {
  console.log('Constructive simulation page loaded')
}
</script>

<style scoped>
.simulation-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
}

h1 {
  color: var(--primary-color);
  margin: 0 0 20px 0;
  text-shadow: var(--glow-shadow);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
}

.iframe-container {
  flex: 1;
  width: 100%;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
}

.simulation-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #000;
}
</style>
