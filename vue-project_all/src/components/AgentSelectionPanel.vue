<template>
  <section class="agent-selection-panel" v-if="multiAgentData && Object.keys(multiAgentData.agents).length > 0">
    <div class="card-head">
      <div>
        <h3 class="card-title">多智能体全局寻优决策日志</h3>
        <p class="card-subtitle">MULTI-AGENT GLOBAL OPTIMIZATION LOG</p>
      </div>
      <span class="status-badge settled">● 决策已锚定 SETTLED</span>
    </div>

    <div class="scroll-container log-container">
      <!-- 终端打字效果区 -->
      <div class="terminal-logs">
        <div class="log-line" style="animation-delay: 0.1s;"><span>[SYS]</span> 启动多智能体并发寻优... 正在获取区域 OSM 路网拓扑...</div>
        <div class="log-line" style="animation-delay: 0.6s;"><span>[SYS]</span> Dijkstra 加权算法启动，执行动态路阻因子剔除...</div>
        <div class="log-line" style="animation-delay: 1.2s;"><span>[SYS]</span> 真实拓扑加权寻优比对完成，决策结果已落地。</div>
      </div>

      <!-- 五路决策矩阵 -->
      <div class="decision-matrix">
        <div 
          v-for="(agent, key) in multiAgentData.agents" 
          :key="key"
          class="agent-card"
          :style="{ '--agent-color': agent.color }"
        >
          <div class="agent-header">
            <span class="agent-label">
              <span class="agent-icon">✦</span> {{ agent.label }} 
            </span>
            <span class="agent-winner-name">{{ agent.poi.name }}</span>
          </div>

          <div class="agent-body">
            <div class="winner-stats">
              <div class="stat-row highlight">
                <span class="stat-lbl">拓扑路网寻优距离</span>
                <span class="stat-val">{{ agent.poi.net_dist_km }} km</span>
              </div>
              <div class="stat-row">
                <span class="stat-lbl">空间欧氏初筛距离</span>
                <span class="stat-val">{{ agent.poi.dist_km }} km</span>
              </div>
            </div>

            <!-- 淘汰比对区 -->
            <div class="losers-section" v-if="agent.losers && agent.losers.length > 0">
              <div class="losers-title">[-] 动态路阻因子剔除名录</div>
              <div class="loser-item" v-for="(loser, idx) in agent.losers" :key="idx">
                <div class="loser-name">❌ {{ loser.name }}</div>
                <div class="loser-reason">{{ loser.reason }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  multiAgentData: {
    type: Object,
    default: null
  }
})
</script>

<style scoped>
.agent-selection-panel {
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
  margin-top: 16px;
  animation: slideInRight 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  flex-shrink: 0;
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(30px); }
  to { opacity: 1; transform: translateX(0); }
}

.card-head {
  padding: 14px 18px;
  background: rgba(30, 41, 59, 0.6);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
  font-family: "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.card-subtitle {
  margin: 4px 0 0;
  font-size: 13.5px;
  color: #00f2fe;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.status-badge {
  font-size: 13.5px;
  font-family: monospace;
  font-weight: bold;
  padding: 4px 10px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.status-badge.computing {
  background: rgba(14, 165, 233, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
}
.status-badge.settled {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.35);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.2);
}
.pulse {
  animation: pulse-border 1.5s infinite;
}
@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.4); }
  70% { box-shadow: 0 0 0 4px rgba(56, 189, 248, 0); }
  100% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); }
}

.scroll-container {
  padding: 16px;
  overflow-y: auto;
  max-height: 500px;
}
.scroll-container::-webkit-scrollbar { width: 4px; }
.scroll-container::-webkit-scrollbar-thumb { background: rgba(148, 163, 184, 0.2); border-radius: 2px; }

.terminal-logs {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 14px;
  color: #cbd5e1;
  background: rgba(0, 0, 0, 0.35);
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 16px;
  border-left: 3px solid #38bdf8;
}
.log-line {
  margin-bottom: 4px;
  opacity: 0;
  animation: fadeInLog 0.3s forwards;
  line-height: 1.6;
}
.log-line span {
  color: #38bdf8;
  font-weight: bold;
}
@keyframes fadeInLog {
  to { opacity: 1; }
}

.decision-matrix {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.agent-card {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-left: 3px solid var(--agent-color);
  border-radius: 6px;
  padding: 12px;
}
.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.agent-label {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--agent-color);
}
.agent-winner-name {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}
.winner-stats {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  padding: 8px 10px;
  margin-bottom: 10px;
}
.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 14.5px;
  color: #cbd5e1;
  margin-bottom: 5px;
}
.stat-row:last-child { margin-bottom: 0; }
.stat-row.highlight {
  color: #38bdf8;
  font-weight: 600;
}
.stat-val {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-weight: bold;
}
.losers-section {
  border-top: 1px dashed rgba(148, 163, 184, 0.2);
  padding-top: 8px;
}
.losers-title {
  font-size: 13px;
  font-weight: bold;
  color: #f87171;
  margin-bottom: 6px;
}
.loser-item {
  margin-bottom: 6px;
}
.loser-name {
  font-size: 14px;
  color: #cbd5e1;
  font-weight: 500;
}
.loser-reason {
  font-size: 13px;
  color: #ff8f8f;
  margin-left: 14px;
  margin-top: 2px;
}
</style>
