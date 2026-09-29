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
  overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(14, 83, 118, 0.17), transparent 54%),
    #030a13;
  color: #e2e8f0;
  font-family: Inter, 'Microsoft YaHei', sans-serif;
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
.back-to-catalog:hover, .catalog-error button:hover { border-color: rgba(94, 234, 212, 0.6); color: #a5fff1; }
.app-viewport { flex: 1; min-height: 0; overflow: auto; }
.process-stage { display: flex; width: min(1120px, calc(100% - 40px)); min-height: 100%; flex-direction: column; justify-content: center; gap: 18px; margin: 0 auto; padding: 30px 0; }
.process-heading { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.process-heading h2 { margin: 0 0 5px; color: #eaf6fc; font-size: clamp(19px, 2vw, 25px); }
.process-heading p { margin: 0; color: #829bad; font-size: 12px; }
.process-state { display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid rgba(80, 200, 220, 0.25); border-radius: 99px; color: #8bdce6; font-size: 11px; white-space: nowrap; }
.process-state i { width: 7px; height: 7px; border-radius: 50%; background: #57d4e3; box-shadow: 0 0 9px #57d4e3; animation: pulse 1s infinite; }
.process-state.complete { color: #82d9b8; border-color: rgba(99, 210, 165, 0.25); }
.process-state.complete i { background: #63d2a5; box-shadow: 0 0 9px #63d2a5; animation: none; }
.terminal-window { display: flex; min-height: 340px; max-height: 58vh; flex-direction: column; overflow: hidden; border: 1px solid rgba(79, 144, 169, 0.4); border-radius: 11px; background: #050b12; box-shadow: 0 22px 70px rgba(0, 0, 0, 0.42), 0 0 35px rgba(36, 163, 184, 0.08); }
.terminal-titlebar { display: grid; min-height: 42px; grid-template-columns: 1fr auto 1fr; align-items: center; padding: 0 15px; border-bottom: 1px solid rgba(108, 139, 154, 0.17); background: #101923; color: #b4c5d0; font-size: 11px; }
.terminal-lights { display: flex; gap: 6px; }
.terminal-lights i { width: 8px; height: 8px; border-radius: 50%; background: #f16b63; }
.terminal-lights i:nth-child(2) { background: #e7bc59; }
.terminal-lights i:nth-child(3) { background: #54c486; }
.terminal-path { justify-self: center; color: #b4c5d0; font: 11px 'Consolas', monospace; white-space: nowrap; }
.terminal-body { flex: 1; min-height: 0; overflow: auto; padding: 19px 21px; color: #a8bdc8; font: 12px/1.8 'Consolas', 'Cascadia Mono', monospace; }
.terminal-command { margin-bottom: 11px; color: #dceaf0; }
.terminal-prompt { color: #69d9bb; }
.terminal-line { display: grid; grid-template-columns: 78px 60px minmax(0, 1fr); gap: 10px; align-items: baseline; }
.terminal-line time { color: #536b79; }
.log-level { color: #73bfd0; font-weight: 700; }
.log-cmd .log-level, .log-done .log-level { color: #6fe1b8; }
.log-sfm .log-level, .log-mvs .log-level, .log-mesh .log-level { color: #e7c478; }
.terminal-cursor { margin-top: 5px; color: #6fe1b8; animation: terminal-blink 0.9s step-end infinite; }
.terminal-progress-row { display: grid; grid-template-columns: auto minmax(80px, 1fr) 42px; align-items: center; gap: 13px; padding: 12px 18px; border-top: 1px solid rgba(108, 139, 154, 0.17); background: #0b131c; color: #7893a2; font-size: 10px; }
.terminal-progress-row strong { color: #70e2c0; font: 700 11px 'Consolas', monospace; text-align: right; }
.terminal-progress { height: 5px; overflow: hidden; border-radius: 8px; background: #1a2a35; }
.terminal-progress i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #30bfb8, #7ce3b6); transition: width 0.35s ease; }
.load-gateway-stage { display: grid; min-height: 100%; place-items: center; padding: 32px 18px; }
.load-gateway-card { width: min(460px, 100%); padding: 34px clamp(20px, 5vw, 44px); border: 1px solid rgba(75, 166, 189, 0.32); border-radius: 18px; background: radial-gradient(circle at 50% 0, rgba(23, 107, 125, 0.2), transparent 48%), linear-gradient(145deg, rgba(9, 26, 44, 0.98), rgba(4, 14, 26, 0.99)); text-align: center; box-shadow: 0 24px 75px rgba(0, 0, 0, 0.38); }
.gateway-eyebrow { color: #62d5e3; font: 700 9px 'Consolas', monospace; letter-spacing: 0.2em; }
.gateway-icon { display: grid; width: 66px; height: 66px; place-items: center; margin: 18px auto 15px; border: 1px solid rgba(111, 225, 222, 0.55); border-radius: 17px; background: linear-gradient(140deg, rgba(31, 142, 164, 0.27), rgba(14, 45, 77, 0.54)); color: #9af4ec; font: 700 19px 'Consolas', monospace; box-shadow: 0 0 27px rgba(45, 193, 202, 0.16); }
.load-gateway-card h2 { margin: 0 0 19px; color: #f0f8fc; font-size: clamp(21px, 3vw, 28px); }
.load-scene-button { display: flex; width: 100%; align-items: center; justify-content: space-between; margin-top: 0; padding: 13px 15px; border: 1px solid rgba(84, 217, 202, 0.58); border-radius: 9px; background: linear-gradient(100deg, rgba(11, 117, 121, 0.55), rgba(22, 82, 131, 0.55)); color: #d6fffa; cursor: pointer; font-size: 12px; font-weight: 700; transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease; }
.load-scene-button:hover { transform: translateY(-1px); border-color: #7bf1df; background: linear-gradient(100deg, rgba(14, 145, 141, 0.65), rgba(32, 110, 161, 0.65)); }
.load-scene-button span:last-child { font-size: 17px; }
.viewer-stage { box-sizing: border-box; display: flex; width: 100%; height: 100%; min-height: 0; flex-direction: column; padding: 10px 14px 14px; }
.viewer-frame { position: relative; flex: 1; min-height: 0; overflow: hidden; border: 1px solid rgba(69, 155, 184, 0.24); border-radius: 10px; background: #020711; }
.catalog-error { display: flex; min-height: 100%; align-items: center; justify-content: center; gap: 14px; color: #fca5a5; }
@keyframes pulse { 50% { opacity: 0.4; } }
@keyframes terminal-blink { 50% { opacity: 0; } }
@media (max-width: 1020px) {
  .app-header { grid-template-columns: 1fr auto; }
  .workflow-steps { grid-column: 1 / -1; grid-row: 2; justify-content: center; }
  .header-actions { grid-column: 2; grid-row: 1; }
}
@media (max-width: 620px) {
  .app-header { gap: 6px; padding: 10px 12px; }
  .branding h1 { font-size: 14px; }
  .workflow-steps { justify-content: flex-start; overflow-x: auto; }
  .step-pill { padding: 5px 7px; font-size: 10.5px; }
  .selected-dataset-label { display: none; }
  .viewer-stage { padding: 7px; }
  .process-stage { width: calc(100% - 24px); }
  .process-heading { align-items: flex-start; flex-direction: column; gap: 12px; }
  .terminal-body { padding: 14px 11px; font-size: 10px; }
  .terminal-line { grid-template-columns: 67px 46px minmax(0, 1fr); gap: 6px; }
}
</style>
