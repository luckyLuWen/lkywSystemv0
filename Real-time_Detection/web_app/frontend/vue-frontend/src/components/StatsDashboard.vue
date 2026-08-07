<template>
  <div class="stats-container">
    <div v-if="loading" class="upload-center">
      <div class="loading-box">
        <div class="spinner"></div>
        <p class="scanning-text">加载统计数据中...</p>
      </div>
    </div>

    <div v-else-if="error" class="upload-center">
      <div class="card upload-card">
        <h3>加载失败</h3>
        <p>{{ error }}</p>
        <button class="btn-reupload" @click="fetchStats">重试</button>
      </div>
    </div>

    <div v-else-if="stats" class="stats-content">
      <!-- Summary Cards -->
      <div class="stat-cards-row">
        <!-- 1. 首位：平均推理时间（高亮） -->
        <div class="card stat-card highlight-card">
          <div class="stat-desc highlight-desc">平均推理时间 (s)</div>
          <div class="stat-num cyan-highlight">{{ stats.avg_inference_time_s }}</div>
        </div>
        <!-- 2. 今日检测 -->
        <div class="card stat-card">
          <div class="stat-desc">今日检测</div>
          <div class="stat-num normal-num">{{ stats.today_detections }}</div>
        </div>
        <!-- 3. 累计检测次数 -->
        <div class="card stat-card">
          <div class="stat-desc">累计检测次数</div>
          <div class="stat-num normal-num">{{ stats.total_detections }}</div>
        </div>
        <!-- 4. 使用模型数 -->
        <div class="card stat-card">
          <div class="stat-desc">使用模型数</div>
          <div class="stat-num normal-num">{{ Object.keys(stats.model_usage || {}).length }}</div>
        </div>
      </div>

      <!-- Dual Algorithm Class Distribution Row -->
      <div class="distribution-grid-row">
        <!-- 饼图1：客车追尾检测类别分布 -->
        <div class="card chart-card distribution-card">
          <div class="card-title">客车追尾检测类别分布</div>
          <div v-if="crashDoughnutData" class="distribution-body">
            <div class="chart-wrapper doughnut-wrapper">
              <Doughnut :data="crashDoughnutData" :options="doughnutOptions" />
            </div>
            <div class="distribution-legend">
              <div
                v-for="item in crashLegendItems"
                :key="item.key"
                class="legend-row"
              >
                <span class="legend-color" :style="{ backgroundColor: item.color }"></span>
                <div class="legend-text">
                  <span class="legend-label">{{ item.label }}</span>
                  <span class="legend-code">({{ item.code }})</span>
                </div>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </div>
          <div v-else class="chart-wrapper">
            <div class="empty-chart">暂无追尾检测数据</div>
          </div>
        </div>

        <!-- 饼图2：油罐车泄露检测类别分布 -->
        <div class="card chart-card distribution-card">
          <div class="card-title">油罐车泄露检测类别分布</div>
          <div v-if="leakDoughnutData" class="distribution-body">
            <div class="chart-wrapper doughnut-wrapper">
              <Doughnut :data="leakDoughnutData" :options="doughnutOptions" />
            </div>
            <div class="distribution-legend">
              <div
                v-for="item in leakLegendItems"
                :key="item.key"
                class="legend-row"
              >
                <span class="legend-color" :style="{ backgroundColor: item.color }"></span>
                <div class="legend-text">
                  <span class="legend-label">{{ item.label }}</span>
                  <span class="legend-code">({{ item.code }})</span>
                </div>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </div>
          <div v-else class="chart-wrapper">
            <div class="empty-chart">暂无泄露检测数据</div>
          </div>
        </div>
      </div>

      <!-- Trend Charts Row -->
      <div class="charts-row">
        <div class="card chart-card trend-card-full">
          <div class="card-title">近30天检测趋势</div>
          <div class="chart-wrapper">
            <Bar v-if="barData" :data="barData" :options="barOptions" />
            <div v-else class="empty-chart">暂无数据</div>
          </div>
        </div>
      </div>

      <!-- Model Usage -->
      <div v-if="Object.keys(stats.model_usage || {}).length > 0" class="card model-usage-card">
        <div class="card-title">模型使用分布</div>
        <div class="model-bars">
          <div v-for="item in sortedModelUsageItems" :key="item.name" class="model-bar-item">
            <span class="model-name">{{ item.name }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: barPct(item.value) }"></div>
            </div>
            <span class="model-cnt">{{ item.value }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS, ArcElement, BarElement, CategoryScale,
  LinearScale, Tooltip, Legend, Filler
} from 'chart.js'

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend, Filler)

const props = defineProps({
  safeFetch: Function,
  apiUrl: String
})

const loading = ref(true)
const error = ref(null)
const stats = ref(null)

const CLASS_COLORS_MAP = {
  car_fire: '#E53935',
  lkyw_fire: '#C2185B',
  car_nofire: '#FDD835',
  lkyw_nofire: '#FB8C00',
  leak: '#EA80FC',
  noleak: '#B2FF59',
  car_normal: '#FDD835',
  lkyw_normal: '#FB8C00'
}

const FALLBACK_COLORS = [
  '#FF6D00', '#00B8D4', '#536DFE', '#EA80FC',
  '#FF4081', '#64FFDA', '#B2FF59', '#FFD740',
  '#40C4FF', '#FF80AB', '#CCFF90', '#84FFFF'
]

const CLASS_LABEL_ALIASES = {
  accident: 'leak',
  normal: 'noleak',
  hazmat_leak: 'leak',
  tank_leak: 'leak',
  no_leak: 'noleak',
  tank_normal: 'noleak',
  carFire: 'car_fire',
  lkywFire: 'lkyw_fire',
  carNofire: 'car_nofire',
  lkywNofire: 'lkyw_nofire',
  car_normal: 'car_nofire',
  lkyw_normal: 'lkyw_nofire'
}

const normalizeClassLabel = (label) => {
  const raw = String(label || '').trim()
  if (!raw) return ''
  const normalized = raw.replace(/[-\s]/g, '_')
  return CLASS_LABEL_ALIASES[raw] || CLASS_LABEL_ALIASES[normalized] || normalized
}

const normalizedClassDistribution = computed(() => {
  const dist = stats.value?.class_distribution || {}
  return Object.entries(dist).reduce((acc, [label, value]) => {
    const normalized = normalizeClassLabel(label)
    if (!normalized) return acc
    acc[normalized] = (acc[normalized] || 0) + Number(value || 0)
    return acc
  }, {})
})


const LABEL_ZH_MAP = {
  car_fire: '轿车碰撞起火',
  lkyw_fire: '两客一危车辆碰撞起火',
  car_nofire: '轿车碰撞无火',
  lkyw_nofire: '两客一危车辆碰撞无火',
  leak: '危化品泄露',
  noleak: '未发现危化品泄露'
}

const CRASH_KEYS = ['car_fire', 'lkyw_fire', 'car_nofire', 'lkyw_nofire']
const LEAK_KEYS = ['leak', 'noleak']

let _colorIdx = 0
const getFallbackColor = () => {
  const c = FALLBACK_COLORS[_colorIdx % FALLBACK_COLORS.length]
  _colorIdx++
  return c
}

// 1. 客车追尾场景分布 (SFGA-YOLO26M)
const crashDistribution = computed(() => {
  const dist = normalizedClassDistribution.value
  const result = {}
  CRASH_KEYS.forEach(k => {
    if (dist[k] !== undefined && dist[k] > 0) result[k] = dist[k]
  })
  return result
})

const crashDoughnutData = computed(() => {
  const dist = crashDistribution.value
  const keys = Object.keys(dist)
  if (keys.length === 0) return null
  return {
    labels: keys.map(k => LABEL_ZH_MAP[k] || k),
    datasets: [{
      data: keys.map(k => dist[k]),
      backgroundColor: keys.map(k => CLASS_COLORS_MAP[k] || getFallbackColor()),
      borderColor: 'rgba(0,0,0,0.3)',
      borderWidth: 1.5
    }]
  }
})

const crashLegendItems = computed(() => {
  const dist = crashDistribution.value
  return Object.entries(dist).map(([k, v]) => ({
    key: k,
    label: LABEL_ZH_MAP[k] || k,
    code: k,
    value: v,
    color: CLASS_COLORS_MAP[k] || getFallbackColor()
  }))
})

// 2. 油罐车泄露场景分布 (LCA-YOLO26N)
const leakDistribution = computed(() => {
  const dist = normalizedClassDistribution.value
  const result = {}
  LEAK_KEYS.forEach(k => {
    if (dist[k] !== undefined && dist[k] > 0) result[k] = dist[k]
  })
  return result
})

const leakDoughnutData = computed(() => {
  const dist = leakDistribution.value
  const keys = Object.keys(dist)
  if (keys.length === 0) return null
  return {
    labels: keys.map(k => LABEL_ZH_MAP[k] || k),
    datasets: [{
      data: keys.map(k => dist[k]),
      backgroundColor: keys.map(k => CLASS_COLORS_MAP[k] || getFallbackColor()),
      borderColor: 'rgba(0,0,0,0.3)',
      borderWidth: 1.5
    }]
  }
})

const leakLegendItems = computed(() => {
  const dist = leakDistribution.value
  return Object.entries(dist).map(([k, v]) => ({
    key: k,
    label: LABEL_ZH_MAP[k] || k,
    code: k,
    value: v,
    color: CLASS_COLORS_MAP[k] || getFallbackColor()
  }))
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '58%',
  plugins: {
    legend: { display: false }
  }
}

const barData = computed(() => {
  const daily = stats.value?.daily_counts
  if (!daily || daily.length === 0) return null
  return {
    labels: daily.map(d => d.date.slice(5)),  // MM-DD
    datasets: [{
      label: '检测次数',
      data: daily.map(d => d.count),
      backgroundColor: 'rgba(0, 229, 255, 0.4)',
      borderColor: 'rgba(0, 229, 255, 0.8)',
      borderWidth: 1,
      borderRadius: 4
    }]
  }
})

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }
  },
  scales: {
    x: {
      ticks: { color: '#b0bec5', font: { size: 18 }, maxRotation: 45 },
      grid: { color: 'rgba(0, 229, 255, 0.06)' }
    },
    y: {
      ticks: { color: '#b0bec5', font: { size: 18 } },
      grid: { color: 'rgba(0, 229, 255, 0.06)' },
      beginAtZero: true
    }
  }
}

const sortedModelUsageItems = computed(() => {
  const usage = stats.value?.model_usage || {}
  return Object.entries(usage)
    .map(([name, value]) => ({ name, value: Number(value || 0) }))
    .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name))
})

const maxModelCount = computed(() => {
  return Math.max(1, ...sortedModelUsageItems.value.map(item => item.value))
})

const barPct = (cnt) => {
  return (cnt / maxModelCount.value * 100).toFixed(0) + '%'
}

const fetchStats = async () => {
  loading.value = true
  error.value = null
  try {
    const data = await props.safeFetch('/api/stats')
    if (data.success) stats.value = data.stats
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.stats-container {
  height: 100%;
  overflow-y: auto;
}

.stats-content {
  animation: fadeIn 0.5s ease-out;
}

.stat-cards-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  text-align: center;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1px solid rgba(0, 229, 255, 0.14);
  background: rgba(4, 22, 39, 0.78);
}

.stat-card.highlight-card {
  border: 1.5px solid rgba(0, 229, 255, 0.5);
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.16), rgba(4, 22, 39, 0.95));
  box-shadow: 0 0 16px rgba(0, 229, 255, 0.22);
}

.stat-num {
  font-size: 48px;
  font-weight: 800;
  font-family: 'Times New Roman', Times, serif;
  margin-bottom: 0;
  line-height: 1;
}

.stat-num.normal-num {
  color: #e2f8ff;
  text-shadow: none;
}

.stat-num.cyan-highlight {
  color: var(--primary-cyan);
  text-shadow: 0 0 14px rgba(0, 229, 255, 0.65);
}

.stat-desc {
  font-size: 23px;
  color: var(--text-dim);
  letter-spacing: 1px;
  font-weight: 600;
  white-space: nowrap;
}

.stat-desc.highlight-desc {
  color: var(--primary-cyan);
  font-weight: 800;
}

.distribution-grid-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  min-height: 440px;
}

/* 所有卡片标题放大 1.3 倍 (21px * 1.3 = 27px ~ 28px) */
.card-title {
  color: var(--primary-cyan);
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 2px;
  margin-bottom: 18px;
  padding-bottom: 15px;
  border-bottom: 2px solid rgba(0, 229, 255, 0.2);
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.35);
}

.chart-wrapper {
  height: 380px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.distribution-card {
  min-width: 0;
}

.distribution-body {
  min-height: 380px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  align-items: stretch;
}

.doughnut-wrapper {
  width: 100%;
  height: 240px;
}

.distribution-legend {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.legend-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  min-height: 48px;
  padding: 10px 16px;
  border: 1px solid rgba(0, 229, 255, 0.18);
  background: rgba(0, 229, 255, 0.05);
  border-radius: 6px;
}

.legend-color {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  box-shadow: 0 0 10px currentColor;
}

.legend-text {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.legend-label {
  color: var(--text-main);
  font-size: 22px;
  font-weight: 700;
  white-space: nowrap;
}

.legend-code {
  font-size: 20px;
  color: #b0bec5;
  font-weight: 700;
  font-family: 'Times New Roman', Times, serif;
  letter-spacing: 0.5px;
  opacity: 0.95;
}

.legend-row strong {
  color: var(--primary-cyan);
  font-size: 26px;
  font-family: 'Times New Roman', Times, serif;
  font-weight: 800;
}

.empty-chart {
  color: var(--text-dim);
  font-size: 19px;
}

.model-usage-card {
  margin-bottom: 24px;
}

.model-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.model-bar-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-name {
  font-size: 21px;
  color: var(--text-dim);
  min-width: 195px;
  text-align: right;
  word-break: break-all;
}

.bar-track {
  flex: 1;
  height: 30px;
  background: rgba(0, 229, 255, 0.06);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(0, 229, 255, 0.4), var(--primary-cyan));
  border-radius: 4px;
  transition: width 0.6s ease;
}

.model-cnt {
  font-size: 22px;
  font-family: monospace;
  color: var(--primary-cyan);
  min-width: 75px;
}

.btn-reupload {
  background: transparent;
  border: 1px solid var(--border-cyan);
  color: var(--primary-cyan);
  padding: 12px 30px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 12px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1100px) {
  .charts-row { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
  .stat-cards-row { grid-template-columns: repeat(2, 1fr); }
  .distribution-body { grid-template-columns: 1fr; }
}
</style>
