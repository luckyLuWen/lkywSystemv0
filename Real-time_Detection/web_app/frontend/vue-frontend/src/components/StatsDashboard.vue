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
        <div class="card stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-num cyan">{{ stats.total_detections }}</div>
          <div class="stat-desc">累计检测次数</div>
        </div>
        <div class="card stat-card">
          <div class="stat-icon">📅</div>
          <div class="stat-num amber">{{ stats.today_detections }}</div>
          <div class="stat-desc">今日检测</div>
        </div>
        <div class="card stat-card">
          <div class="stat-icon">⚡</div>
          <div class="stat-num">{{ stats.avg_inference_time_s }}</div>
          <div class="stat-desc">平均推理时间 (s)</div>
        </div>
        <div class="card stat-card">
          <div class="stat-icon">🧠</div>
          <div class="stat-num small">{{ Object.keys(stats.model_usage || {}).length }}</div>
          <div class="stat-desc">使用模型数</div>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="charts-row">
        <div class="card chart-card">
          <div class="card-title">类别分布</div>
          <div class="chart-wrapper">
            <Doughnut v-if="doughnutData" :data="doughnutData" :options="doughnutOptions" />
            <div v-else class="empty-chart">暂无数据</div>
          </div>
        </div>
        <div class="card chart-card">
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
          <div v-for="(cnt, name) in stats.model_usage" :key="name" class="model-bar-item">
            <span class="model-name">{{ name }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: barPct(name, cnt) }"></div>
            </div>
            <span class="model-cnt">{{ cnt }}</span>
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
  lkyw_fire: '#B71C1C',
  car_nofire: '#FDD835',
  lkyw_nofire: '#FB8C00',
  car_normal: '#FDD835',
  lkyw_normal: '#FB8C00'
}

const FALLBACK_COLORS = [
  '#FF6D00', '#00B8D4', '#536DFE', '#EA80FC',
  '#FF4081', '#64FFDA', '#B2FF59', '#FFD740',
  '#40C4FF', '#FF80AB', '#CCFF90', '#84FFFF'
]

let _colorIdx = 0
const getFallbackColor = () => {
  const c = FALLBACK_COLORS[_colorIdx % FALLBACK_COLORS.length]
  _colorIdx++
  return c
}

const doughnutData = computed(() => {
  const dist = stats.value?.class_distribution
  if (!dist || Object.keys(dist).length === 0) return null
  _colorIdx = 0
  const labels = Object.keys(dist)
  return {
    labels,
    datasets: [{
      data: labels.map(k => dist[k]),
      backgroundColor: labels.map(k => CLASS_COLORS_MAP[k] || getFallbackColor()),
      borderColor: 'rgba(0,0,0,0.3)',
      borderWidth: 1
    }]
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#b0bec5', padding: 16, font: { size: 19 } }
    }
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

const maxModelCount = computed(() => {
  const usage = stats.value?.model_usage || {}
  return Math.max(1, ...Object.values(usage))
})

const barPct = (name, cnt) => {
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
  padding: 30px 24px;
}

.stat-icon {
  font-size: 42px;
  margin-bottom: 10px;
}

.stat-num {
  font-size: 48px;
  font-weight: bold;
  font-family: monospace;
  margin-bottom: 4px;
}

.stat-num.cyan {
  color: var(--primary-cyan);
  text-shadow: 0 0 8px var(--primary-cyan);
}

.stat-num.amber {
  color: var(--accent-amber);
  text-shadow: 0 0 8px var(--accent-amber);
}

.stat-num.small {
  font-size: 36px;
}

.stat-desc {
  font-size: 19px;
  color: var(--text-dim);
  letter-spacing: 1px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  min-height: 450px;
}

.card-title {
  color: var(--primary-cyan);
  font-size: 21px;
  letter-spacing: 2px;
  margin-bottom: 18px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(0, 229, 255, 0.1);
}

.chart-wrapper {
  height: 450px;
  display: flex;
  align-items: center;
  justify-content: center;
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

@media (max-width: 900px) {
  .stat-cards-row { grid-template-columns: repeat(2, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
}
</style>
