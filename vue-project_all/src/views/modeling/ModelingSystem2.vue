<!--
================================================================================
  精细三维建模系统 2 (ModelingSystem2.vue)
  【两客一危事故车辆精细重建与测量评估系统】
  挂载运行来自 High-Fidelity Modeling 文件夹中的高精度三维建模子系统。
================================================================================
-->
<template>
  <div class="modeling-system-2-container">
    <HighFidelityModelingApp />
  </div>
</template>

<script setup>
import HighFidelityModelingApp from '@high-fidelity/src/HighFidelityModelingApp.vue'
</script>

<style scoped>
.modeling-system-2-container {
  width: 100%;
  height: 100%;
  background-color: #020710;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}
</style>
