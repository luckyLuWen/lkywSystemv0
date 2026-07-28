<template>
  <section class="agent-selection-panel" v-if="multiAgentData && multiAgentData.agents && Object.keys(multiAgentData.agents).length > 0">
    <div class="panel-head">
      <div>
        <h4 class="panel-title">多智能体全局寻优决策日志</h4>
        <p class="panel-subtitle">Global Optimization Log</p>
      </div>
      <span class="status-badge" :class="isComputing ? 'computing pulse' : 'ready'">
        {{ isComputing ? '决策计算中' : '决策已锁定' }}
      </span>
    </div>

    <!-- 终端打字效果区 -->
    <div class="terminal-logs">
      <div class="log-line text-cyan" style="animation-delay: 0.1s;"><span>[SYS]</span> 启动多智能体并发寻优... 正在提取区域 OSM 路网拓扑...</div>
      <div class="log-line text-cyan" style="animation-delay: 0.6s;"><span>[SYS]</span> Dijkstra 加权算法启动，执行动态路阻因子剔除...</div>
      <div class="log-line text-green" style="animation-delay: 1.2s;"><span>[SYS]</span> 真实拓扑加权寻优比对完成，决策结果已落地。</div>
    </div>

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
              <span class="stat-lbl">真实路网寻优距离</span>
              <span class="stat-val text-cyan">{{ agent.poi.net_dist_km }} km</span>
            </div>
            <div class="stat-row">
              <span class="stat-lbl">空间直线初筛距离</span>
              <span class="stat-val text-gray">{{ agent.poi.dist_km }} km</span>
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
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  multiAgentData: {
    type: Object,
    default: null
  },
  isComputing: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.agent-selection-panel {
  background: rgba(2, 12, 26, 0.8);
  border: 1px solid rgba(0, 242, 254, 0.22);
  border-radius: 12px;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), inset 0 0 15px rgba(0, 242, 254, 0.05);
  margin-top: 16px;
  animation: slideInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  flex-shrink: 0;
}

@keyframes slideInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.panel-head {
  padding: 12px 14px;
  background: rgba(10, 25, 47, 0.4);
  border-bottom: 1px solid rgba(0, 242, 254, 0.15);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.5px;
}
.panel-subtitle {
  margin: 1px 0 0;
  font-size: 10px;
  color: #94a3b8;
  font-family: 'Courier New', Courier, monospace;
}
.status-badge {
  font-size: 9px;
  font-weight: 600;
  padding: 3px 6px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}
.status-badge.computing {
  background: rgba(0, 242, 254, 0.1);
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.3);
  text-shadow: 0 0 5px rgba(0, 242, 254, 0.4);
}
.status-badge.ready {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(74, 222, 128, 0.3);
}
.pulse {
  animation: pulse-border 1.5s infinite;
}
@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(0, 242, 254, 0.4); }
  70% { box-shadow: 0 0 0 4px rgba(0, 242, 254, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 242, 254, 0); }
}

.terminal-logs {
  font-family: 'Courier New', Courier, monospace;
  font-size: 10px;
  color: #94a3b8;
  background: rgba(0, 0, 0, 0.55);
  padding: 10px;
  margin: 10px 12px;
  border-radius: 6px;
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-left: 3px solid #00f2fe;
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5);
}
.log-line {
  margin-bottom: 4px;
  opacity: 0;
  animation: fadeInLog 0.3s forwards;
  line-height: 1.4;
}
.log-line:last-child {
  margin-bottom: 0;
}
.log-line span {
  font-weight: bold;
}
.text-cyan { color: #00f2fe; }
.text-cyan span { color: #008fa7; }
.text-green { color: #4ade80; }
.text-green span { color: #22c55e; }

@keyframes fadeInLog {
  to { opacity: 1; }
}

.decision-matrix {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 12px 12px;
}
.agent-card {
  background: rgba(10, 25, 47, 0.25);
  border: 1px solid rgba(0, 242, 254, 0.1);
  border-left: 3px solid var(--agent-color);
  border-radius: 6px;
  padding: 10px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.agent-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  border-color: rgba(0, 242, 254, 0.25);
}
.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.agent-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--agent-color);
}
.agent-icon {
  margin-right: 2px;
}
.agent-winner-name {
  font-size: 12px;
  font-weight: 600;
  color: #e2e8f0;
}
.winner-stats {
  background: rgba(0, 0, 0, 0.25);
  border-radius: 4px;
  padding: 6px 8px;
  margin-bottom: 8px;
}
.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #94a3b8;
  margin-bottom: 3px;
}
.stat-row:last-child { margin-bottom: 0; }
.stat-row.highlight {
  font-weight: 600;
}
.text-cyan { color: #00f2fe; }
.text-gray { color: #cbd5e1; }

.losers-section {
  border-top: 1px dashed rgba(0, 242, 254, 0.15);
  padding-top: 6px;
}
.losers-title {
  font-size: 9px;
  color: #64748b;
  margin-bottom: 4px;
  font-weight: 600;
}
.loser-item {
  margin-bottom: 4px;
}
.loser-item:last-child {
  margin-bottom: 0;
}
.pattern-match-line {
  display: none;
}
.loser-name {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 500;
}
.loser-reason {
  font-size: 9px;
  color: #ef4444;
  margin-left: 12px;
  margin-top: 1px;
  line-height: 1.3;
}
</style>
