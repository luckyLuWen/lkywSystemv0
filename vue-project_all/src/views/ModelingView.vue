<!--
================================================================================
  精细三维建模系统主界面 (ModelingView.vue)
  【功能说明】精细三维建模主系统，集成数据集导入签发、Pipeline解算及3D模型精细重建展示
================================================================================
-->
<template>
  <div class="modeling-view-root">
    <ModelingSystem2 />
  </div>
</template>

<script setup>
import ModelingSystem2 from './modeling/ModelingSystem2.vue'
</script>

<style scoped>
.modeling-view-root {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: #020710;
}
</style>
