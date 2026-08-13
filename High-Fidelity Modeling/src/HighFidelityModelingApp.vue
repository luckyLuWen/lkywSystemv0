<template>
  <div class="high-fidelity-app-root">
    <!-- 头部导航 -->
    <header class="app-header">
      <div class="header-branding">
        <div class="brand-title-group">
          <div class="title-row">
            <h1>精细三维建模系统 2</h1>
            <span class="system-tag">两客一危专版</span>
          </div>
          <span class="brand-sub">Fine-Grained 3D Reconstruction & Spatial Measurement System</span>
        </div>
      </div>
      
      <!-- 触发操作 -->
      <div class="header-actions">
        <button 
          class="action-btn" 
          @click="startReconstruction" 
          :disabled="isReconstructing"
        >
          {{ isReconstructing ? '重建进行中...' : '开始三维重建' }}
        </button>
      </div>
    </header>

    <!-- 工作流主展示视图 -->
    <main class="app-viewport">
      <!-- 界面锁定逻辑：通过 is-locked class 和内部遮罩层实现物理与视觉双重锁定 -->
      <div class="step-view-container" :class="{ 'is-locked': isReconstructing }">
        <div class="lock-overlay" v-if="isReconstructing">
          <span class="lock-text">🔒 控件已锁定，后台正在执行重建任务...</span>
        </div>
        <DatasetUploader />
      </div>
    </main>

    <!-- 仿真日志终端面板 -->
    <transition name="slide-up">
      <div class="log-console-panel" v-if="logs.length > 0">
        <!-- 顶部固定显示虚拟算法引擎版本 -->
        <div class="console-header">
          <div class="header-left">
            <span class="console-title">🚀 任务执行日志 (Console)</span>
            <span class="engine-version">lkywReconEngine v1.1.0 (Edge Node A)</span>
          </div>
          <span class="console-status" :class="{ running: isReconstructing }">
            {{ isReconstructing ? 'RECEIVING STREAM...' : 'CONNECTION CLOSED' }}
          </span>
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
import { ref, nextTick, onBeforeUnmount } from 'vue'

// ================= 状态管理 =================
const isReconstructing = ref(false)
const logs = ref([])
const logContainerRef = ref(null)
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
  
  // 监听容器高度，新日志到达时自动滚动到底部
  await nextTick()
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
}

// ================= 虚拟 WebSocket 后端服务 =================
// 模拟创建一个真实的 WS 连接对象，处理长连接的推流逻辑
class MockReconstructionWebSocket {
  constructor(url) {
    this.url = url
    this.onmessage = null
    this.onclose = null
    this.isAborted = false
    
    // 配置标准序列与可信耗时等待 (单位: ms)
    this.pipelineSteps = [
      { type: 'INFO', text: '初始化重建任务，Task ID: RECON-90210...', wait: 800 },
      { type: 'INFO', text: '开始读取无人机(UAV)图像数据，共计 342 张...', wait: 2000 },
      { type: 'INFO', text: '开始读取无人车(UGV)图像数据，共计 156 张...', wait: 1500 },
      { type: 'INFO', text: '图像预处理与去畸变 (Image Undistortion) 完成.', wait: 3500 },
      { type: 'INFO', text: '开始 SIFT特征提取 (Feature Extraction)...', wait: 3000 },
      { type: 'INFO', text: '特征匹配 (Feature Matching) 与几何校验中...', wait: 4000 },
      { type: 'INFO', text: '运行 SFM (Structure from Motion) 生成稀疏点云 (Sparse Point Cloud)...', wait: 4500 },
      { type: 'INFO', text: '运行 MVS (Multi-View Stereo) 构建密集点云 (Dense Point Cloud)...', wait: 4500 },
      { type: 'INFO', text: '泊松表面重建 (Poisson Surface Reconstruction) 与网格化...', wait: 3000 },
      { type: 'INFO', text: '纹理映射 (Texture Mapping) 完成.', wait: 2500 },
      { type: 'INFO', text: '模型轻量化与标准格式转换 (glTF/3D Tiles export)...', wait: 2000 },
      { type: 'SUCCESS', text: '3D重建Pipeline执行完毕，耗时 14m 23s.', wait: 1000 }
    ]
  }

  // 模拟发送指令
  send(command) {
    if (command === 'START') {
      this._startStreaming()
    }
  }

  // 终止连接
  close() {
    this.isAborted = true
    if (this.onclose) this.onclose()
  }

  // 内部：模拟服务器按时间轴不断推流数据
  async _startStreaming() {
    for (const step of this.pipelineSteps) {
      if (this.isAborted) break
      // 模拟服务器执行耗时
      await new Promise(resolve => setTimeout(resolve, step.wait))
      
      // 模拟收到 WS 推送事件
      if (this.onmessage && !this.isAborted) {
        this.onmessage({ data: JSON.stringify(step) })
      }
    }
    // 推流结束，自动断开连接
    this.close()
  }
}

// ================= 交互逻辑 =================
const startReconstruction = () => {
  if (isReconstructing.value) return
  
  // 1. 锁定界面并重置状态
  isReconstructing.value = true
  logs.value = []

  // 2. 创建虚拟 WS 实例建立长连接
  currentWsMock = new MockReconstructionWebSocket('wss://api.example.com/recon/stream')
  
  // 3. 监听后端推送的数据
  currentWsMock.onmessage = (event) => {
    const logData = JSON.parse(event.data)
    appendLog(logData)
  }
  
  // 4. 监听连接关闭
  currentWsMock.onclose = () => {
    // 收到 SUCCESS 后不断开控件锁定，或者你可以将这里设为 false
    isReconstructing.value = false 
  }
  
  // 5. 触发后端开始干活
  currentWsMock.send('START')
}

// 组件卸载时断开连接，防止内存泄漏
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
  padding: 16px 24px;
  background: rgba(4, 12, 26, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
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
  font-size: 11.5px;
  color: #64748b;
  font-family: 'Courier New', monospace;
}

.action-btn {
  background: transparent;
  border: 1px solid #00f2fe;
  color: #00f2fe;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}
.action-btn:hover:not(:disabled) {
  background: rgba(0, 242, 254, 0.15);
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.2);
}
.action-btn:disabled {
  border-color: #475569;
  color: #94a3b8;
  cursor: not-allowed;
  background: rgba(255,255,255,0.05);
}

/* =========== 中间工作区及锁定遮罩 =========== */
.app-viewport {
  flex: 1;
  padding: 24px;
  display: flex;
  justify-content: center;
  overflow-y: auto; 
}
.step-view-container {
  width: 100%;
  position: relative;
  transition: opacity 0.3s;
}

/* 当处于锁定状态时，阻止内部所有事件穿透，并降低透明度 */
.step-view-container.is-locked {
  pointer-events: none;
  opacity: 0.7;
}

/* 上传控件遮罩层UI */
.lock-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(2, 7, 18, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 20;
  border-radius: 8px;
}
.lock-text {
  background: rgba(0, 0, 0, 0.8);
  border: 1px solid #475569;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  color: #fbbf24; /* 警告黄 */
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}

/* =========== 终端日志面板 =========== */
.log-console-panel {
  height: 280px;
  background: #090e17;
  border-top: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.5);
  z-index: 5;
}

.console-header {
  padding: 8px 16px;
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

.console-body {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.console-body::-webkit-scrollbar {
  width: 8px;
}
.console-body::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
}
.console-body::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 4px;
}

.log-line {
  margin-bottom: 6px;
  display: flex;
  gap: 8px;
  word-break: break-all;
}

.log-time {
  color: #64748b;
  flex-shrink: 0;
}

.log-tag {
  font-weight: bold;
  flex-shrink: 0;
}
.tag-info {
  color: #38bdf8;
}
.tag-success {
  color: #34d399;
}

.log-text {
  color: #cbd5e1;
}

.log-cursor {
  display: inline-block;
  width: 8px;
  color: #38bdf8;
  font-weight: bold;
  animation: blink 1s step-end infinite;
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
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>