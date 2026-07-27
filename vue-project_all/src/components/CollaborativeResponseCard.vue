<template>
  <section class="collaborative-response-card">
    <template v-if="strategyMetrics">
      <!-- ===== 头部 ===== -->
      <div class="card-head">
        <div>
          <h3 class="card-title">协同响应规划</h3>
          <p class="card-subtitle">{{ strategyMetrics.end_point_name }}</p>
        </div>
        <span class="status-badge online">数据就绪</span>
      </div>

      <!-- ===== 滚动内容区 ===== -->
      <div class="scroll-container">

        <!-- 1. 场景概况 -->
        <div class="card-section">
          <div class="section-title-wrapper">
            <span class="bracket">[</span>
            <h4 class="section-subtitle-text">场景概况</h4>
            <span class="bracket">]</span>
          </div>
          <div class="info-table">
            <div class="info-row">
              <span class="info-label">灾害场景</span>
              <span class="info-val scene-color">{{ strategyMetrics.end_point_name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">协同机制</span>
              <span class="info-val mech-color">{{ strategyLabel }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">更新时间</span>
              <span class="info-val">{{ updateTimeStr }}</span>
            </div>
          </div>
        </div>

        <!-- 1.5 候选救援点 -->
        <div v-if="candidatePoints.length > 0" class="card-section">
          <div class="section-title-wrapper">
            <span class="bracket">[</span>
            <h4 class="section-subtitle-text">救援点选取</h4>
            <span class="bracket">]</span>
          </div>
          <div class="candidate-list">
            <div
              v-for="(p, idx) in candidatePoints"
              :key="idx"
              class="candidate-row"
              :class="{ selected: p.selected }"
            >
              <span class="candidate-dot" :class="{ on: p.selected }"></span>
              <span class="candidate-name">{{ p.name }}</span>
              <span class="candidate-dist">{{ p.dist_km }} km</span>
            </div>
          </div>
        </div>

        <!-- 2. 协同效能指标 -->
        <div class="card-section">
          <div class="section-title-wrapper">
            <span class="bracket">[</span>
            <h4 class="section-subtitle-text">协同效能指标</h4>
            <span class="bracket">]</span>
          </div>

          <!-- 时间指标 2列 -->
          <div class="mini-metrics-row two-col">
            <div class="metric-block">
              <span class="metric-val text-cyan">{{ strategyMetrics.metrics.carTime }} <small>min</small></span>
              <span class="metric-lbl">车辆 (UGV) 耗时</span>
            </div>
            <div class="metric-block">
              <span class="metric-val text-cyan">{{ strategyMetrics.metrics.uavTime }} <small>min</small></span>
              <span class="metric-lbl">无人机 (UAV) 飞行</span>
            </div>
            <div class="metric-block delay-block">
              <span class="metric-val text-amber">{{ strategyMetrics.metrics.delay }} <small>s</small></span>
              <span class="metric-lbl">无人机地面待机</span>
            </div>
            <div class="metric-block sync-block" :class="{ perfect: timeDiffVal === 0 }">
              <span class="metric-val" :class="timeDiffVal === 0 ? 'text-green' : ''">{{ strategyMetrics.metrics.timeDiff || '0.0' }} <small>s</small></span>
              <span class="metric-lbl">协同终端时间差</span>
            </div>
          </div>

          <!-- 距离/能耗 2列，含算法对比 -->
          <div class="mini-metrics-row two-col" style="margin-top: 8px;">
            <div class="metric-block dist-block">
              <span class="metric-val text-purple">{{ comparison?.carDistKm || '--' }} <small>km</small></span>
              <span class="metric-lbl">车辆行驶距离 (Dijkstra)</span>
              <span v-if="comparison" class="metric-vs">vs BFS {{ comparison.baselineCarDistKm }}km ▼{{ comparison.carSavingKm }}km</span>
            </div>
            <div class="metric-block dist-block">
              <span class="metric-val text-purple">{{ comparison?.uavDistKm || '--' }} <small>km</small></span>
              <span class="metric-lbl">无人机飞行距离 (A*)</span>
              <span v-if="comparison" class="metric-vs">vs Greedy {{ comparison.baselineUavDistKm }}km ▼{{ comparison.uavSavingKm }}km</span>
            </div>
            <div class="metric-block">
              <span class="metric-val text-pink">{{ strategyMetrics.metrics.uavEnergy }} <small>Wh</small></span>
              <span class="metric-lbl">无人机能源消耗</span>
            </div>
            <div class="metric-block">
              <span class="metric-val text-cyan dim">{{ speeds.carKmh || 80 }} / {{ speeds.uavMs || 20 }}</span>
              <span class="metric-lbl">车辆(km/h) / 无人机(m/s)</span>
            </div>
          </div>

        </div>

        <!-- 3. 环境约束与参数 -->
        <div v-if="scenario" class="card-section">
          <div class="section-title-wrapper">
            <span class="bracket">[</span>
            <h4 class="section-subtitle-text">环境约束与参数</h4>
            <span class="bracket">]</span>
          </div>
          <div class="env-grid">
            <div class="env-item" :class="{ active: scenario.ugv_blocked }">
              <span class="env-dot" :class="{ on: scenario.ugv_blocked }"></span>
              <div class="env-body">
                <span class="env-label">拥堵区</span>
                <span class="env-state">{{ scenario.ugv_blocked ? '已启用' : '未启用' }}</span>
              </div>
            </div>
            <div class="env-item" :class="{ active: scenario.uav_smoke }">
              <span class="env-dot" :class="{ on: scenario.uav_smoke }"></span>
              <div class="env-body">
                <span class="env-label">禁飞区×{{ scenario.nfz_count }}</span>
                <span class="env-state">{{ scenario.uav_smoke ? '已启用' : '未启用' }}</span>
              </div>
            </div>
          </div>
          <div v-if="scenario.congestion_name" class="congestion-info">
            <span class="congestion-name">{{ scenario.congestion_name }}</span>
            <span class="congestion-detail">{{ scenario.congestion_info }}</span>
          </div>
        </div>

        <!-- 4. 路径规划与技术参数 -->
        <div class="card-section">
          <div class="section-title-wrapper">
            <span class="bracket">[</span>
            <h4 class="section-subtitle-text">路径规划摘要</h4>
            <span class="bracket">]</span>
          </div>
          <div class="info-table">
            <div class="info-row">
              <span class="info-label">车辆算法</span>
              <span class="info-val">Dijkstra 加权最短路径</span>
            </div>
            <div class="info-row">
              <span class="info-label">无人机算法</span>
              <span class="info-val">A* 全局搜索 + B-Spline 平滑</span>
            </div>
            <div class="info-row">
              <span class="info-label">路网数据源</span>
              <span class="info-val">OpenStreetMap 真实路网</span>
            </div>
            <div class="info-row">
              <span class="info-label">无人机避障</span>
              <span class="info-val">8方向网格 + 禁飞区约束</span>
            </div>
          </div>
        </div>

      </div>
    </template>

    <!-- 动态载入多智能体寻优面板 -->
    <AgentSelectionPanel 
      v-if="multiAgentData" 
      :multiAgentData="multiAgentData" 
    />

    <!-- 空状态 -->
    <div v-if="!strategyMetrics && !lastError" class="empty-state">
      <div class="empty-icon">📋</div>
      <p class="empty-text">暂无协同响应数据</p>
      <p class="empty-hint">请先在协同响应面板中生成二维推演或三维态势</p>
    </div>

    <p v-if="lastError" class="error-text">{{ lastError }}</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AgentSelectionPanel from './AgentSelectionPanel.vue'
import {
  buildCollaborativeApiUrl,
  getCollaborativeControllerBaseUrl,
} from '../config/subsystems'

const controllerBaseUrl = ref(getCollaborativeControllerBaseUrl())
const lastError = ref('')
const strategyMetrics = ref(null)

let pollingTimer = null

const strategyLabel = computed(() => {
  const s = strategyMetrics.value?.strategy
  if (s === 'rcd') return 'RCD 逆向推演'
  if (s === 'independent') return 'ISD 极速独立'
  if (s === 'wait') return 'CAS 基地待命'
  return s || '--'
})

const comparison = computed(() => strategyMetrics.value?.comparison || null)
const candidatePoints = computed(() => strategyMetrics.value?.candidate_points || [])
const scenario = computed(() => strategyMetrics.value?.scenario || null)
const speeds = computed(() => strategyMetrics.value?.speeds || { carKmh: 80, uavMs: 20 })
const multiAgentData = computed(() => strategyMetrics.value?.multi_agent || null)

const timeDiffVal = computed(() => {
  const v = parseFloat(strategyMetrics.value?.metrics?.timeDiff)
  return isNaN(v) ? null : v
})

const updateTimeStr = computed(() => {
  const t = strategyMetrics.value?.updated_at
  if (!t) return '--'
  try {
    return new Date(t).toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    return '--'
  }
})

async function refreshStatus() {
  try {
    const response = await fetch(
      buildCollaborativeApiUrl('api/health', controllerBaseUrl.value),
      { cache: 'no-store' }
    )
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const payload = await response.json()
    if (payload.strategy_metrics && payload.strategy_metrics.available) {
      strategyMetrics.value = payload.strategy_metrics
    } else {
      strategyMetrics.value = null
    }
    lastError.value = ''
  } catch (error) {
    strategyMetrics.value = null
    lastError.value = error instanceof Error ? error.message : '无法连接控制层'
  }
}

onMounted(() => {
  refreshStatus()
  pollingTimer = window.setInterval(refreshStatus, 5000)
})

onBeforeUnmount(() => {
  if (pollingTimer) window.clearInterval(pollingTimer)
})
</script>

<style scoped>
.collaborative-response-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 16px;
  padding: 20px;
  border: 1px solid rgba(96, 165, 250, 0.28);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(13, 25, 41, 0.94) 0%, rgba(8, 16, 28, 0.94) 100%);
  box-shadow: 0 0 24px rgba(96, 165, 250, 0.14);
  backdrop-filter: blur(10px);
}

/* ===== 头部 ===== */
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.18);
  padding-bottom: 12px;
}

.card-title {
  margin: 0;
  color: #93c5fd;
  font-size: 18px;
  line-height: 1.2;
}

.card-subtitle {
  margin: 4px 0 0 0;
  font-size: 14.5px;
  color: rgba(255, 255, 255, 0.72);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 14px;
}

.status-badge.online {
  color: #93c5fd;
  background: rgba(96, 165, 250, 0.16);
  border: 1px solid rgba(96, 165, 250, 0.24);
}

/* ===== 滚动容器 ===== */
.scroll-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  flex: 1;
  padding-right: 4px;
}

.scroll-container::-webkit-scrollbar {
  width: 5px;
}

.scroll-container::-webkit-scrollbar-thumb {
  background: rgba(96, 165, 250, 0.25);
  border-radius: 2.5px;
}

/* ===== 各板块通用 ===== */
.card-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px dashed rgba(96, 165, 250, 0.12);
}

.card-section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.section-title-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.bracket {
  color: #60a5fa;
  font-weight: bold;
  font-size: 18px;
  text-shadow: 0 0 6px rgba(96, 165, 250, 0.5);
}

.section-subtitle-text {
  margin: 0;
  color: #60a5fa;
  font-size: 17.5px;
  font-weight: bold;
  letter-spacing: 0.5px;
}

/* ===== 信息表格 ===== */
.info-table {
  display: flex;
  flex-direction: column;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 0;
  border-bottom: 1px solid rgba(96, 165, 250, 0.06);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 14.5px;
  color: rgba(255, 255, 255, 0.6);
}

.info-val {
  font-size: 14.5px;
  color: #fff;
  font-weight: 600;
  text-align: right;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-val.scene-color { color: #fbbf24; }
.info-val.mech-color { color: #34d399; }

/* ===== 指标卡片网格 ===== */
.mini-metrics-row {
  display: grid;
  gap: 8px;
}

.mini-metrics-row.two-col {
  grid-template-columns: repeat(2, 1fr);
}

.metric-block {
  background: rgba(10, 19, 35, 0.55);
  border: 1px solid rgba(96, 165, 250, 0.12);
  border-radius: 6px;
  padding: 10px 8px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-block.delay-block {
  border-color: rgba(245, 158, 11, 0.25);
  background: rgba(245, 158, 11, 0.06);
}

.metric-block.sync-block.perfect {
  border-color: rgba(52, 211, 153, 0.25);
  background: rgba(52, 211, 153, 0.06);
}

.metric-val {
  font-size: 26px;
  font-weight: bold;
  font-family: 'JetBrains Mono', Consolas, monospace;
  color: #e2e8f0;
}

.metric-val small {
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
}

.metric-val.text-cyan { color: #60a5fa; }
.metric-val.text-amber { color: #fbbf24; }
.metric-val.text-green { color: #34d399; }
.metric-val.text-purple { color: #a78bfa; }
.metric-val.text-pink { color: #f472b6; }
.metric-val.dim { font-size: 17px; color: #cbd5e1; }

.metric-lbl {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.65);
  white-space: nowrap;
}

/* ===== 环境约束 ===== */
.env-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.env-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.env-item.active {
  border-color: rgba(249, 115, 22, 0.25);
  background: rgba(249, 115, 22, 0.06);
}

.env-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #475569;
  flex-shrink: 0;
}

.env-dot.on {
  background: #f97316;
  box-shadow: 0 0 6px rgba(249, 115, 22, 0.5);
}

.env-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.env-label {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.65);
}

.env-state {
  font-size: 15px;
  font-weight: 600;
  color: #64748b;
}

.env-item.active .env-state {
  color: #fdba74;
}

.congestion-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  background: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 6px;
}

.congestion-name {
  font-size: 15px;
  font-weight: 600;
  color: #93c5fd;
}

.congestion-detail {
  font-size: 13.5px;
  color: rgba(147, 197, 253, 0.8);
}

/* ===== 候选救援点列表 ===== */
.candidate-list {
  display: flex;
  flex-direction: column;
}

.candidate-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 4px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
}

.candidate-row.selected {
  color: #fff;
  background: rgba(52, 211, 153, 0.08);
  border: 1px solid rgba(52, 211, 153, 0.2);
}

.candidate-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #475569;
  flex-shrink: 0;
}

.candidate-dot.on {
  background: #34d399;
  box-shadow: 0 0 6px rgba(52, 211, 153, 0.6);
}

.candidate-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.candidate-row.selected .candidate-name {
  font-weight: 600;
  color: #fff;
}

.candidate-dist {
  font-family: monospace;
  font-size: 12px;
  color: inherit;
  flex-shrink: 0;
}

/* ===== 距离卡片算法对比 ===== */
.metric-block.dist-block {
  position: relative;
}

.metric-vs {
  font-size: 13.5px;
  color: #4ade80;
  margin-top: 2px;
  white-space: nowrap;
}

/* ===== 空状态 ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 16px;
  text-align: center;
}

.empty-icon { font-size: 32px; opacity: 0.4; }

.empty-text { margin: 0; color: #94a3b8; font-size: 14.5px; font-weight: 600; }

.empty-hint { margin: 0; color: rgba(148, 163, 184, 0.6); font-size: 12.5px; }

.error-text {
  margin: 0;
  font-size: 13.5px;
  color: #ffb4b4;
  text-align: center;
}
</style>
