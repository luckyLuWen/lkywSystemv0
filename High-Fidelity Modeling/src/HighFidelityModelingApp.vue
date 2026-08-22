<template>
  <div class="high-fidelity-app-root">
    <!-- 头部导航与步骤指示器 -->
    <header class="app-header">
      <div class="header-branding">
        <div class="brand-title-group">
          <div class="title-row">
            <h1>精细三维建模系统</h1>
            <span class="system-tag">两客一危专版</span>
          </div>
          <span class="brand-sub">Fine-Grained 3D Reconstruction & Spatial Measurement System</span>
        </div>
      </div>

      <!-- 步骤流程指示器 (Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5) -->
      <div class="workflow-steps-bar">
        <div class="step-pill" :class="{ active: currentStep === 1, completed: currentStep > 1 }">
          <span class="step-num">1</span>
          <span class="step-label">数据集导入</span>
        </div>
        <div class="step-divider"></div>
        <div class="step-pill" :class="{ active: currentStep === 2, completed: currentStep > 2 }">
          <span class="step-num">2</span>
          <span class="step-label">Pipeline 重建</span>
        </div>
        <div class="step-divider"></div>
        <div class="step-pill" :class="{ active: currentStep === 3, completed: currentStep > 3 }">
          <span class="step-num">3</span>
          <span class="step-label">3D 成果展示</span>
        </div>
        <div class="step-divider"></div>
        <div class="step-pill" :class="{ active: currentStep === 4, completed: currentStep > 4 }">
          <span class="step-num">4</span>
          <span class="step-label">事故车辆空间测量</span>
        </div>
        <div class="step-divider"></div>
        <div class="step-pill" :class="{ active: currentStep === 5 }">
          <span class="step-num">5</span>
          <span class="step-label">评估报告导出</span>
        </div>
      </div>
      
      <!-- 触发操作与模型选项 -->
      <div class="header-actions">
        <select 
          v-if="currentStep === 1" 
          v-model="selectedModelPreset" 
          class="preset-select" 
          :disabled="isReconstructing"
        >
          <option value="/Dashboard/models/Accident_Occur1.glb">🚗 事故车辆重建: 客车追尾撞击现场</option>
          <option value="/Dashboard/models/Side_roll_Tanker.glb">🚚 事故车辆重建: 油罐车侧翻泄露现场</option>
        </select>

        <button 
          v-if="currentStep < 3"
          class="action-btn" 
          @click="startReconstruction" 
          :disabled="isReconstructing"
        >
          <span class="btn-icon">{{ isReconstructing ? '⚙️' : '🚀' }}</span>
          {{ isReconstructing ? '重建 Pipeline 执行中...' : '开始三维重建' }}
        </button>

        <button 
          v-else
          class="action-btn secondary-btn"
          @click="resetToStep1"
        >
          <span class="btn-icon">↺</span> 重新导入数据集
        </button>
      </div>
    </header>

    <!-- 工作流主展示视图 (步骤 1 / 2 展示 DatasetUploader；步骤 3/4/5 展示 ReconstructionViewer3D) -->
    <main class="app-viewport">
      <!-- 步骤 1 & 步骤 2：数据集导入与重建锁定状态 -->
      <div v-if="currentStep === 1 || currentStep === 2" class="step-view-container" :class="{ 'is-locked': isReconstructing }">
        <div class="lock-overlay" v-if="isReconstructing">
          <div class="lock-card">
            <div class="lock-spinner"></div>
            <span class="lock-text">🔒 控件已锁定，后台算法引擎正在执行 MVS/SFM 三维重建任务...</span>
            <span class="lock-sub">请观察下方控制台推流日志，完成后将自动呈现 3D 模型</span>
          </div>
        </div>
        <DatasetUploader />
      </div>

      <!-- 步骤 3、4、5：3D 画布与空间测量 / 报告视图 -->
      <div v-else class="step3-canvas-viewport">
        <ReconstructionViewer3D 
          :model-url="reconstructedModelUrl" 
          :active-step="currentStep"
          @update-step="(s) => currentStep = s"
          @reset-step="resetToStep1"
        />
      </div>
    </main>

    <!-- 【交互说明】：当接收到 [SUCCESS] / status: completed 信号时，自动销毁/隐藏日志面板 -->
    <transition name="slide-up">
      <div class="log-console-panel" v-if="showLogConsole && logs.length > 0">
        <!-- 顶部固定显示算法引擎版本 -->
        <div class="console-header">
          <div class="header-left">
            <span class="console-title">🚀 任务执行日志 (Console)</span>
            <span class="engine-version">lkywReconEngine v1.1.0 (Edge Node A)</span>
          </div>
          <div class="header-right">
            <span class="console-status" :class="{ running: isReconstructing }">
              {{ isReconstructing ? 'RECEIVING STREAM...' : 'TASK COMPLETED' }}
            </span>
            <button class="close-console-btn" @click="showLogConsole = false" title="隐藏控制台">✕</button>
          </div>
        </div>
        
        <!-- 日志滚动区 -->
        <div class="console-body" ref="logContainerRef">
          <div 
            v-for="(log, index) in logs" 
            :key="index" 
            class="log-line"
          >
            <span class="log-time">[{{ log.time }}]</span>
            <span 
              class="log-tag" 
              :class="log.type === 'SUCCESS' ? 'tag-success' : 'tag-info'"
            >
              [{{ log.type }}]
            </span>
            <span class="log-text">{{ log.text }}</span>
          </div>
          <!-- 正在接收时的光标效果 -->
          <div class="log-cursor" v-if="isReconstructing">_</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import DatasetUploader from './components/DatasetUploader.vue'
import ReconstructionViewer3D from './components/ReconstructionViewer3D.vue'
import { ref, nextTick, onBeforeUnmount } from 'vue'

// ================= 状态管理 =================
const currentStep = ref(1) // 1: 导入 | 2: 重建中 | 3: 3D展示
const isReconstructing = ref(false)
const showLogConsole = ref(false)
const logs = ref([])
const logContainerRef = ref(null)

const selectedModelPreset = ref('/Dashboard/models/Accident_Occur1.glb')
const reconstructedModelUrl = ref('/Dashboard/models/Accident_Occur1.glb')
const uavImageCount = ref(248) // 替换为你想要的一致数字
const ugvImageCount = ref(180) // 替换为你想要的一致数字
let currentWsMock = null

// 格式化时间 [HH:mm:ss]
const getCurrentTime = () => {
  return new Date().toTimeString().split(' ')[0]
}

// 模拟向视图追加日志并自动滚动
const appendLog = async (logData) => {
  logs.value.push({
    time: getCurrentTime(),
    type: logData.type,
    text: logData.text
  })
  
  // 自动滚动到底部
  await nextTick()
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
}

// 重置回步骤 1
const resetToStep1 = () => {
  currentStep.value = 1
  isReconstructing.value = false
  showLogConsole.value = false
  logs.value = []
  if (currentWsMock) {
    currentWsMock.close()
  }
}

// ================= 虚拟 WebSocket 后端服务 =================
class MockReconstructionWebSocket {
  constructor(url, targetModelUrl, uavCount, ugvCount) {
    this.url = url
    this.targetModelUrl = targetModelUrl
    this.onmessage = null
    this.onclose = null
    this.isAborted = false
    
    // 配置标准序列与可信耗时等待 (单位: ms)
    this.pipelineSteps = [
      { type: 'INFO', text: '初始化重建任务，Task ID: RECON-90210...', wait: 600 },
      
      // 👇 修改：使用反引号(``) 和 ${} 动态插入影像数量
      { type: 'INFO', text: `开始读取无人机(UAV)多视角图像数据，共计 ${uavCount} 张...`, wait: 1200 },
      { type: 'INFO', text: `开始读取无人车(UGV)地面近景图像数据，共计 ${ugvCount} 张...`, wait: 1000 },
      
      { type: 'INFO', text: '图像预处理与去畸变 (Image Undistortion) 完成.', wait: 1500 },
      { type: 'INFO', text: '开始 SIFT 特征提取 (Feature Extraction)...', wait: 1800 },
      { type: 'INFO', text: '特征匹配 (Feature Matching) 与几何约束校验中...', wait: 2000 },
      { type: 'INFO', text: '运行 SFM (Structure from Motion) 生成稀疏点云 (Sparse Point Cloud)...', wait: 2200 },
      { type: 'INFO', text: '运行 MVS (Multi-View Stereo) 构建密集点云 (Dense Point Cloud)...', wait: 2500 },
      { type: 'INFO', text: '泊松表面重建 (Poisson Surface Reconstruction) 与多边形网格化...', wait: 1800 },
      { type: 'INFO', text: '纹理映射 (Texture Mapping) 与 PBR 材质烘焙完成.', wait: 1500 },
      { type: 'INFO', text: '模型轻量化导出为标准 glTF 2.0 / GLB 格式...', wait: 1200 },
      { 
        type: 'SUCCESS', 
        status: 'completed', 
        text: `3D重建Pipeline执行完毕，生成高精模型 ${targetModelUrl}，耗时 14m 23s.`, 
        modelUrl: targetModelUrl, 
        wait: 800 
      }
    ]
  }

  send(command) {
    if (command === 'START') {
      this._startStreaming()
    }
  }

  close() {
    this.isAborted = true
    if (this.onclose) this.onclose()
  }

  async _startStreaming() {
    for (const step of this.pipelineSteps) {
      if (this.isAborted) break
      await new Promise(resolve => setTimeout(resolve, step.wait))
      
      if (this.onmessage && !this.isAborted) {
        this.onmessage({ data: JSON.stringify(step) })
      }
    }
    this.close()
  }
}
const startReconstruction = () => {
  if (isReconstructing.value) return
  
  // 1. 进入步骤 2，锁定界面并展示控制台
  currentStep.value = 2
  isReconstructing.value = true
  showLogConsole.value = true
  logs.value = []

  // 👇 关键修改在这里：必须把 uavImageCount.value 和 ugvImageCount.value 传进去！
  // 注意一定不能漏掉 .value
  currentWsMock = new MockReconstructionWebSocket(
    'wss://api.example.com/recon/stream',
    selectedModelPreset.value,
    uavImageCount.value,  // 第3个参数：无人机照片数量
    ugvImageCount.value   // 第4个参数：无人车照片数量
  )
  
  // 3. 监听后端推送的数据
  currentWsMock.onmessage = (event) => {
    const logData = JSON.parse(event.data)
    appendLog(logData)

    // 当接收到 SUCCESS 或 status: completed 信号时
    if (logData.type === 'SUCCESS' || logData.status === 'completed') {
      reconstructedModelUrl.value = logData.modelUrl || selectedModelPreset.value
      
      // 延时自动隐藏日志面板，展示 3D 画布容器
      setTimeout(() => {
        isReconstructing.value = false
        showLogConsole.value = false 
        currentStep.value = 3        
      }, 1200)
    }
  }
  
  currentWsMock.onclose = () => {
    if (currentStep.value !== 3) {
      isReconstructing.value = false
    }
  }
  
  // 4. 触发后端执行
  currentWsMock.send('START')
}

onBeforeUnmount(() => {
  if (currentWsMock) {
    currentWsMock.close()
  }
})
</script>

<style scoped>
/* =========== 基础布局 =========== */
.high-fidelity-app-root {
  width: 100%;
  height: 100%;
  background: #020712;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden; 
  font-family: 'Inter', -apple-system, sans-serif;
}

.app-header {
  padding: 14px 24px;
  background: rgba(4, 12, 26, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 242, 254, 0.18);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  z-index: 10;
}

.brand-title-group .title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-title-group h1 {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: #ffffff;
}
.system-tag {
  background: rgba(0, 242, 254, 0.12);
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.3);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.brand-sub {
  font-size: 11px;
  color: #64748b;
  font-family: 'Courier New', monospace;
}

/* 步骤指示器 */
.workflow-steps-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4px 12px;
  border-radius: 20px;
}
.step-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  transition: all 0.3s ease;
}
.step-pill .step-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
}
.step-pill.active {
  color: #00f2fe;
  font-weight: 600;
}
.step-pill.active .step-num {
  background: #00f2fe;
  color: #020712;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
}
.step-pill.completed {
  color: #34d399;
}
.step-pill.completed .step-num {
  background: rgba(52, 211, 153, 0.2);
  color: #34d399;
  border: 1px solid #34d399;
}
.step-divider {
  width: 20px;
  height: 1px;
  background: rgba(255, 255, 255, 0.15);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.preset-select {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid #334155;
  color: #38bdf8;
  padding: 7px 12px;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  cursor: pointer;
}
.preset-select option {
  background: #0f172a;
  color: #f8fafc;
}

.action-btn {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.2), rgba(59, 130, 246, 0.2));
  border: 1px solid #00f2fe;
  color: #00f2fe;
  padding: 8px 18px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.25s ease;
}
.action-btn:hover:not(:disabled) {
  background: #00f2fe;
  color: #020712;
  box-shadow: 0 0 14px rgba(0, 242, 254, 0.5);
}
.action-btn:disabled {
  border-color: #475569;
  color: #94a3b8;
  cursor: not-allowed;
  background: rgba(255,255,255,0.05);
}
.action-btn.secondary-btn {
  border-color: #64748b;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.05);
}
.action-btn.secondary-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

/* =========== 中间工作区及锁定遮罩 =========== */
.app-viewport {
  flex: 1;
  padding: 20px;
  display: flex;
  justify-content: center;
  position: relative;
  overflow: hidden; 
}
.step-view-container {
  width: 100%;
  position: relative;
  transition: opacity 0.3s;
  overflow-y: auto;
}
.step-view-container.is-locked {
  pointer-events: none;
  opacity: 0.7;
}

.step3-canvas-viewport {
  width: 100%;
  height: 100%;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(0, 242, 254, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

/* 锁定遮罩层UI */
.lock-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(2, 7, 18, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 20;
  border-radius: 8px;
}
.lock-card {
  background: rgba(10, 18, 36, 0.95);
  border: 1px solid #00f2fe;
  padding: 24px 32px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  box-shadow: 0 10px 30px rgba(0, 242, 254, 0.25);
}
.lock-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(0, 242, 254, 0.2);
  border-top-color: #00f2fe;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
.lock-text {
  font-size: 14.5px;
  color: #00f2fe;
  font-weight: 600;
}
.lock-sub {
  font-size: 12px;
  color: #94a3b8;
}

/* =========== 终端日志面板 =========== */
.log-console-panel {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 280px;
  background: #090e17;
  border-top: 1px solid rgba(0, 242, 254, 0.3);
  display: flex;
  flex-direction: column;
  box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.7);
  z-index: 30;
}

.console-header {
  padding: 8px 20px;
  background: #101726;
  border-bottom: 1px solid #1e293b;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.console-title {
  color: #94a3b8;
  font-weight: 600;
}
.engine-version {
  background: rgba(56, 189, 248, 0.1);
  color: #38bdf8;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 11px;
  border: 1px solid rgba(56, 189, 248, 0.2);
}

.console-status {
  color: #94a3b8;
  font-family: 'Fira Code', monospace;
}
.console-status.running {
  color: #fbbf24;
  animation: pulse 1.5s infinite;
}

.close-console-btn {
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 14px;
}
.close-console-btn:hover {
  color: #f87171;
}

.console-body {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-line {
  margin-bottom: 6px;
  display: flex;
  gap: 8px;
  word-break: break-all;
}
.log-time { color: #64748b; flex-shrink: 0; }
.log-tag { font-weight: bold; flex-shrink: 0; }
.tag-info { color: #38bdf8; }
.tag-success { color: #34d399; }
.log-text { color: #cbd5e1; }

.log-cursor {
  display: inline-block;
  width: 8px;
  color: #38bdf8;
  font-weight: bold;
  animation: blink 1s step-end infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.35s ease, opacity 0.35s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>