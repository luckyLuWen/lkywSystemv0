<template>
  <div class="deduction-container">
    <iframe
      :key="iframeKey"
      :src="iframeSrc"
      frameborder="0"
      class="deduction-iframe"
      @load="onIframeLoad"
    ></iframe>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { build2DDeductionIframeSrc, trigger2DDeduction } from '../config/subsystems'

const iframeSrc = ref('')
const iframeKey = ref(0)

async function refresh() {
  try {
    await trigger2DDeduction()
  } catch (e) {
    console.warn('触发二维推演生成失败，尝试加载已有结果', e)
  }
  iframeSrc.value = build2DDeductionIframeSrc()
  iframeKey.value += 1
}

function onIframeLoad() {
  console.log('二维动态推演页面已加载')
}

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.deduction-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--bg-color);
}

.deduction-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #000;
}
</style>
