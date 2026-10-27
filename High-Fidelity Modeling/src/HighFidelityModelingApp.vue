<template>
  <div class="high-fidelity-app-root">
    <header class="app-header">
      <div class="branding">
        <div class="brand-mark">3D</div>
        <div>
          <h1>精细三维建模系统</h1>
        </div>
      </div>

      <nav class="workflow-steps" aria-label="建模工作流">
        <div
          v-for="step in workflowSteps"
          :key="step.id"
          class="step-pill"
          :class="{ active: currentStep === step.id, completed: currentStep > step.id }"
        >
          <span class="step-number">{{ step.id }}</span>
          <span>{{ step.label }}</span>
        </div>
      </nav>

      <div class="header-actions">
        <span v-if="selectedDataset && currentStep > 1" class="selected-dataset-label">{{ selectedDataset.title }}</span>
        <button v-if="currentStep > 1" class="back-to-catalog" type="button" @click="returnToCatalog">
          重新选择场景
        </button>
      </div>
    </header>

    <main class="app-viewport">
      <DatasetUploader
        v-if="currentStep === 1"
        :datasets="datasets"
        :loading="catalogLoading"
        :error="catalogError"
        @dataset-ready="importDataset"
      />

      <section v-else-if="currentStep === 2 && selectedDataset" class="process-stage">
        <header class="process-heading">
          <div>
            <h2>{{ selectedDataset.title }} · 重建</h2>
            <p>
              {{ captureViewLabel(selectedDataset, 'uav') }} {{ selectedDataset.counts.uav }} 张 <span aria-hidden="true">·</span>
              {{ captureViewLabel(selectedDataset, 'ugv') }} {{ selectedDataset.counts.ugv }} 张
              <template v-if="selectedDataset.counts.other"> · 其他 {{ selectedDataset.counts.other }} 张</template>
            </p>
          </div>
          <span class="process-state" :class="{ complete: !isProcessRunning }">
            <i></i>{{ isProcessRunning ? '运行中，请等待' : '演示完成' }}
          </span>
        </header>

        <div class="terminal-window">
          <div class="terminal-titlebar">
            <div class="terminal-lights" aria-hidden="true"><i></i><i></i><i></i></div>
            <span class="terminal-path">root/program/modelconstruct/3DPModeling.exe</span>
          </div>
          <div ref="processLogPanel" class="terminal-body" aria-live="polite">
            <div class="terminal-command">
              <span class="terminal-prompt">lkyw@scene</span>
              <span> $ recon --demo --scene "{{ selectedDataset.title }}" --uav {{ selectedDataset.counts.uav }} --ugv {{ selectedDataset.counts.ugv }}<template v-if="selectedDataset.captureType === 'synthetic'"> --capture synthetic</template><template v-if="selectedDataset.counts.other"> --other {{ selectedDataset.counts.other }}</template></span>
            </div>
            <div v-for="(entry, index) in processLogs" :key="`${index}-${entry.time}`" class="terminal-line" :class="`log-${entry.level.toLowerCase()}`">
              <time>[{{ entry.time }}]</time>
              <span class="log-level">{{ entry.level }}</span>
              <span>{{ entry.text }}</span>
            </div>
            <div v-if="isProcessRunning" class="terminal-cursor">▋</div>
          </div>
          <div class="terminal-progress-row">
            <span>流程进度</span>
            <div class="terminal-progress"><i :style="{ width: processProgress + '%' }"></i></div>
            <strong>{{ processProgress }}%</strong>
          </div>
        </div>

      </section>

      <section v-else-if="currentStep === 3 && selectedDataset" class="load-gateway-stage">
        <div class="load-gateway-card">
          <span class="gateway-eyebrow">重建结果已就绪</span>
          <div class="gateway-icon">3D</div>
          <h2>{{ selectedDataset.title }}</h2>
          <button class="load-scene-button" type="button" @click="showScene">
            <span>前往查看</span>
            <span aria-hidden="true">→</span>
          </button>
        </div>
      </section>

      <section v-else-if="currentStep >= 4 && selectedDataset" class="viewer-stage">
        <div class="viewer-frame">
          <ReconstructionViewer3D
            :key="selectedDataset.id"
            :model-url="selectedDataset.model.url"
            :model-name="selectedDataset.title"
            :model-metadata="selectedDataset.model"
            :active-step="currentStep"
            @model-loaded="currentStep = 4"
            @update-step="updateViewerStep"
            @reset-step="returnToCatalog"
          />
        </div>
      </section>

      <div v-else class="catalog-error">
        <strong>尚未选择数据集</strong>
        <button type="button" @click="returnToCatalog">返回数据集目录</button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import DatasetUploader from './components/DatasetUploader.vue'
import ReconstructionViewer3D from './components/ReconstructionViewer3D.vue'

const workflowSteps = [
  { id: 1, label: '场景数据导入' },
  { id: 2, label: '模型重建流程' },
  { id: 3, label: '场景模型加载' },
  { id: 4, label: '三维成果展示' },
  { id: 5, label: '空间测量' },
  { id: 6, label: '报告导出' }
]

const currentStep = ref(1)
const datasets = ref([])
const selectedDataset = ref(null)
const catalogLoading = ref(true)
const catalogError = ref('')
const processLogs = ref([])
const processProgress = ref(0)
const isProcessRunning = ref(false)
const processLogPanel = ref(null)
let processRunId = 0

const loadDatasetCatalog = async () => {
  catalogLoading.value = true
  catalogError.value = ''

  try {
    const response = await fetch('/ModelingData/catalog.json', { cache: 'no-store' })
    if (!response.ok) {
      throw new Error(`读取目录失败（HTTP ${response.status}）。`)
    }

    const catalog = await response.json()
    if (!Array.isArray(catalog.datasets)) {
      throw new Error('catalog.json 中缺少 datasets 列表。')
    }
    datasets.value = catalog.datasets
  } catch (error) {
    catalogError.value = error instanceof Error ? error.message : '读取项目数据目录时发生未知错误。'
  } finally {
    catalogLoading.value = false
  }
}

const importDataset = (dataset) => {
  processRunId += 1
  selectedDataset.value = dataset
  if (dataset.skipReconstructionWait) {
    processLogs.value = []
    processProgress.value = 100
    isProcessRunning.value = false
    currentStep.value = 4
    return
  }
  currentStep.value = 2
  void runProcessSimulation(dataset, processRunId)
}

const captureViewLabel = (dataset, kind) => dataset.captureType === 'synthetic'
  ? `仿真 ${kind.toUpperCase()} 视角`
  : kind === 'uav' ? 'UAV 航拍' : 'UGV 地面'

const showScene = () => {
  if (selectedDataset.value) currentStep.value = 4
}

const returnToCatalog = () => {
  const previousDataset = selectedDataset.value
  processRunId += 1
  isProcessRunning.value = false
  currentStep.value = 1
  selectedDataset.value = null
  const objectUrls = previousDataset?.objectUrls || []
  if (objectUrls.length) void nextTick(() => objectUrls.forEach(url => URL.revokeObjectURL(url)))
}

const delay = (milliseconds) => new Promise(resolve => setTimeout(resolve, milliseconds))

const appendProcessLog = async (level, text) => {
  processLogs.value.push({
    level,
    text,
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false })
  })
  await nextTick()
  if (processLogPanel.value) processLogPanel.value.scrollTop = processLogPanel.value.scrollHeight
}

const runProcessSimulation = async (dataset, runId) => {
  const { uav, ugv, other = 0 } = dataset.counts
  const imageCount = Math.max(1, Number(uav || 0) + Number(ugv || 0) + Number(other || 0))
  const capturePrefix = dataset.captureType === 'synthetic' ? '仿真' : ''
  const entries = [
    { level: 'INFO', text: '建立影像重建工作区。', wait: 0 },
    { level: 'DATA', text: `载入${capturePrefix}UAV视角影像：${uav} 张。`, wait: 0 },
    { level: 'DATA', text: `载入${capturePrefix}UGV视角影像：${ugv} 张。`, wait: 0 },
    { level: 'SFM', text: '相机位姿解算与稀疏结构生成。', processingShare: 0.26 },
    { level: 'MVS', text: '多视角稠密重建与场景融合。', processingShare: 0.46 },
    { level: 'MESH', text: '表面网格生成与颜色整理。', processingShare: 0.28 },
    { level: 'CHECK', text: '汇总场景范围、影像关联与模型信息。', wait: 0 },
    { level: 'DONE', text: '演示流程完成，三维成果可加载。', wait: 0 }
  ]
  if (other > 0) entries.splice(3, 0, { level: 'DATA', text: `载入其他影像：${other} 张。`, wait: 0 })
  // 初始化、影像清单和结束检查只输出日志；目标等待时间仅分配给 SFM/MVS/Mesh。
  const targetWaitMs = Math.min(10 * 60 * 1000, Math.max(8_000, 25_000 * Math.pow(imageCount / 32, 1.25)))
  const timedEntries = entries.map(({ processingShare, wait = 0, ...entry }) => ({
    ...entry,
    wait: processingShare ? Math.round(targetWaitMs * processingShare) : wait
  }))

  processLogs.value = []
  processProgress.value = 0
  isProcessRunning.value = true
  await appendProcessLog('CMD', `启动 ${dataset.title} 模型重建流程演示。`)

  for (let index = 0; index < timedEntries.length; index += 1) {
    if (timedEntries[index].wait > 0) await delay(timedEntries[index].wait)
    if (runId !== processRunId) return
    await appendProcessLog(timedEntries[index].level, timedEntries[index].text)
    processProgress.value = Math.round(((index + 1) / timedEntries.length) * 100)
  }

  if (runId !== processRunId) return
  isProcessRunning.value = false
  if (runId === processRunId) currentStep.value = 3
}

const updateViewerStep = (step) => {
  if (step >= 4) currentStep.value = step
}

onBeforeUnmount(() => {
  processRunId += 1
  selectedDataset.value?.objectUrls?.forEach(url => URL.revokeObjectURL(url))
})

onMounted(loadDatasetCatalog)
</script>

<style scoped>
.high-fidelity-app-root {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  position: relative;
  overflow: hidden; 
  font-family: 'Microsoft YaHei', '微软雅黑', 'PingFang SC', 'Segoe UI', Arial, sans-serif;
}

.app-header {
  position: relative;
  z-index: 10;
  display: grid;
  min-height: 76px;
  grid-template-columns: minmax(210px, 1fr) auto minmax(210px, 1fr);
  align-items: center;
  gap: 18px;
  padding: 10px 22px;
  border-bottom: 1px solid rgba(80, 169, 203, 0.22);
  background: rgba(4, 14, 25, 0.94);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22);
}

.branding { display: flex; min-width: 0; align-items: center; gap: 11px; }
.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid rgba(86, 220, 231, 0.6);
  border-radius: 9px;
  background: linear-gradient(145deg, rgba(31, 142, 164, 0.35), rgba(14, 45, 77, 0.64));
  color: #8af4f1;
  font: 700 13px 'Consolas', monospace;
  box-shadow: 0 0 17px rgba(48, 193, 211, 0.15);
}
.branding h1 { margin: 0; color: #f1f8fc; font-size: 16px; font-weight: 700; }
.workflow-steps { display: flex; align-items: center; gap: 5px; }
.step-pill { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 99px; color: #647d90; font-size: 12.5px; white-space: nowrap; }
.step-number { display: grid; width: 22px; height: 22px; place-items: center; border-radius: 50%; background: rgba(132, 155, 174, 0.13); font: 700 11px 'Consolas', monospace; }
.step-pill.active { background: rgba(45, 197, 206, 0.1); color: #83eef0; }
.step-pill.active .step-number { background: #5ad7df; color: #06232c; box-shadow: 0 0 12px rgba(90, 215, 223, 0.32); }
.step-pill.completed { color: #70c9ae; }
.step-pill.completed .step-number { background: rgba(54, 173, 136, 0.2); color: #71d9b8; }
.header-actions { display: flex; min-width: 0; align-items: center; justify-content: flex-end; gap: 12px; }
.selected-dataset-label { overflow: hidden; color: #9eb7c8; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.back-to-catalog, .catalog-error button {
  padding: 8px 11px;
  border: 1px solid rgba(118, 158, 184, 0.32);
  border-radius: 7px;
  background: rgba(17, 37, 55, 0.7);
  color: #c2d8e7;
  cursor: pointer;
  font-size: 11px;
}
</style>
