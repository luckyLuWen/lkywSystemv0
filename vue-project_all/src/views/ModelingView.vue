<template>
  <div class="modeling-container">
    <div class="modeling-placeholder-card">
      <div class="icon-wrapper">
        <span class="pulse-icon">📐</span>
      </div>
      <h2>精细建模系统</h2>
      <p class="subtitle">Fine Modeling System</p>
      <div class="divider"></div>
      <p class="description">
        系统已预留精细建模路由与相应接口。外部研究员生成的事故现场三维模型（GLB/GLTF格式）后续将直接通过此路由及后台增量融合接口接入总系统。
      </p>
      <div class="tech-tags">
        <span class="tag">Web3D</span>
        <span class="tag">增量融合</span>
        <span class="tag">接口已预留</span>
      </div>
    </div>
  </div>
</template>

<script setup>
// 仅保留路由占位与界面提示，简化具体建模功能
</script>

<style scoped>
.modeling-container {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  box-sizing: border-box;
  background:
    radial-gradient(circle at top left, rgba(0, 229, 255, 0.08), transparent 35%),
    linear-gradient(180deg, rgba(4, 16, 34, 0.98), rgba(2, 10, 22, 0.98));
}

.modeling-placeholder-card {
  max-width: 520px;
  width: 90%;
  padding: 40px;
  text-align: center;
  background: rgba(7, 19, 37, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.3);
  border-radius: 20px;
  box-shadow: 
    0 20px 50px rgba(0, 0, 0, 0.3),
    0 0 30px rgba(0, 229, 255, 0.1);
  backdrop-filter: blur(10px);
  animation: fadeIn 0.8s ease-out;
}

.icon-wrapper {
  font-size: 48px;
  margin-bottom: 16px;
  display: inline-block;
  position: relative;
}

.pulse-icon {
  display: inline-block;
  animation: float 3s ease-in-out infinite;
}

h2 {
  margin: 10px 0 4px;
  font-size: 24px;
  color: #effaff;
  letter-spacing: 1px;
}

.subtitle {
  margin: 0;
  font-size: 13px;
  color: rgba(0, 229, 255, 0.85);
  text-transform: uppercase;
  letter-spacing: 2px;
}

.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.3), transparent);
  margin: 24px auto;
  width: 80%;
}

.description {
  margin: 0 0 30px;
  font-size: 14px;
  color: rgba(230, 246, 255, 0.75);
  line-height: 1.8;
  text-align: justify;
}

.tech-tags {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.tag {
  font-size: 12px;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(0, 229, 255, 0.12);
  color: #9ef6ff;
  border: 1px solid rgba(0, 229, 255, 0.2);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}
</style>
