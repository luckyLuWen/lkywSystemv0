<template>
  <div class="modeling-container">
    <header class="page-header">
      <div>
        <h1>精细建模</h1>
        <p>面向外部研究员生成的事故现场三维模型，完成导入、识别、要素提取与后续增量融合接口预留。</p>
      </div>
      <div class="header-actions">
        <button class="primary-btn" @click="openFilePicker">导入 Web3D 模型</button>
        <button class="ghost-btn" :disabled="!currentModel" @click="exportKeySceneElements">导出关键场景要素</button>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        class="hidden-input"
        accept=".glb,.gltf,.obj,.fbx,.stl,.ply,.json"
        @change="handleFileImport"
      />
    </header>

    <div class="modeling-content">
      <aside class="workflow-panel">
        <section class="panel-card">
          <h2>业务流程</h2>
          <div class="step-list">
            <article
              v-for="step in workflowSteps"
              :key="step.id"
              class="step-card"
              :class="{ done: step.done }"
            >
              <span class="step-index">{{ step.index }}</span>
              <div>
                <strong>{{ step.title }}</strong>
                <p>{{ step.description }}</p>
              </div>
            </article>
          </div>
        </section>

        <section class="panel-card">
          <h2>已导入模型</h2>
          <div class="asset-list">
            <button
              v-for="model in importedModels"
              :key="model.id"
              class="asset-item"
              :class="{ active: model.id === selectedModelId }"
              @click="selectedModelId = model.id"
            >
              <div class="asset-item__top">
                <strong>{{ model.name }}</strong>
                <span class="asset-chip">{{ model.format }}</span>
              </div>
              <p>{{ model.source }}</p>
              <small>{{ model.updatedAt }}</small>
            </button>
          </div>
        </section>
      </aside>

      <main class="workspace-panel">
        <section class="canvas-card">
          <div class="canvas-stage">
            <div class="stage-grid"></div>
            <div class="stage-overlay">
              <template v-if="currentModel">
                <span class="stage-tag">当前模型</span>
                <h3>{{ currentModel.name }}</h3>
                <p>{{ currentModel.sceneSummary }}</p>
                <div class="stage-tags">
                  <span class="info-chip">{{ currentModel.format }}</span>
                  <span class="info-chip">{{ currentModel.vehicleType }}</span>
                  <span class="info-chip">{{ currentModel.fusionStatus }}</span>
                </div>
              </template>
              <template v-else>
                <span class="stage-tag">等待模型</span>
                <h3>导入外部事故现场三维模型</h3>
                <p>支持 GLB / GLTF / OBJ / FBX / STL / PLY / JSON 等 Web3D 交换格式。</p>
              </template>
            </div>
          </div>

          <div class="canvas-meta">
            <div class="meta-item">
              <span>模型来源</span>
              <strong>{{ currentModel ? currentModel.source : '待导入' }}</strong>
            </div>
            <div class="meta-item">
              <span>识别车辆类型</span>
              <strong>{{ currentModel ? currentModel.vehicleType : '--' }}</strong>
            </div>
            <div class="meta-item">
              <span>关键要素数</span>
              <strong>{{ currentModel ? currentModel.keyElements.length : 0 }}</strong>
            </div>
            <div class="meta-item">
              <span>更新状态</span>
              <strong>{{ currentModel ? currentModel.fusionStatus : '未接入' }}</strong>
            </div>
          </div>
        </section>

        <section class="panel-card">
          <div class="section-head">
            <h2>关键场景要素</h2>
            <button class="ghost-btn small" :disabled="!currentModel" @click="exportKeySceneElements">
              一键导出
            </button>
          </div>
          <div class="element-list">
            <span
              v-for="item in currentModelElements"
              :key="item"
              class="element-chip"
            >
              {{ item }}
            </span>
          </div>
        </section>
      </main>

      <aside class="operation-panel">
        <section class="panel-card">
          <h2>模型属性</h2>
          <div class="property-list">
            <div class="property-item">
              <span>模型名称</span>
              <strong>{{ currentModel ? currentModel.name : '--' }}</strong>
            </div>
            <div class="property-item">
              <span>格式</span>
              <strong>{{ currentModel ? currentModel.format : '--' }}</strong>
            </div>
            <div class="property-item">
              <span>识别结果</span>
              <strong>{{ currentModel ? currentModel.vehicleType : '--' }}</strong>
            </div>
            <div class="property-item">
              <span>精度说明</span>
              <strong>{{ currentModel ? currentModel.accuracy : '--' }}</strong>
            </div>
            <div class="property-item">
              <span>融合状态</span>
              <strong>{{ currentModel ? currentModel.fusionStatus : '--' }}</strong>
            </div>
          </div>
        </section>

        <section class="panel-card">
          <h2>建模操作</h2>
          <div class="action-stack">
            <button class="primary-btn" @click="openFilePicker">导入外部模型</button>
            <button class="secondary-btn" :disabled="!currentModel" @click="identifyCurrentModel">自动识别车辆类型</button>
            <button class="secondary-btn" :disabled="!currentModel" @click="exportKeySceneElements">导出关键场景要素</button>
            <button class="ghost-btn" :disabled="!currentModel" @click="markFusionReady">标记为待增量融合</button>
          </div>
          <p class="panel-tip">{{ statusMessage }}</p>
        </section>

        <section class="panel-card">
          <h2>接口预留</h2>
          <div class="endpoint-list">
            <article v-for="endpoint in fusionEndpoints" :key="endpoint.path" class="endpoint-item">
              <strong>{{ endpoint.label }}</strong>
              <code>{{ endpoint.path }}</code>
              <p>{{ endpoint.description }}</p>
            </article>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const fileInputRef = ref(null)
const selectedModelId = ref('sample-1')
const statusMessage = ref('等待导入外部研究员生成的事故现场三维模型。')

const importedModels = ref([
  {
    id: 'sample-1',
    name: '事故现场融合模型_A',
    format: 'GLB',
    source: '无人机影像 + 无人车点云',
    vehicleType: '危化品运输车',
    accuracy: '厘米级配准',
    fusionStatus: '可直接接入总系统',
    sceneSummary: '已融合道路、事故车辆、隔离带和重点残骸区域，可用于指挥研判。',
    keyElements: ['事故车辆', '道路边界', '碰撞点', '残骸散落区', '警戒范围'],
    updatedAt: '2026-04-10 13:10',
  },
  {
    id: 'sample-2',
    name: '事故现场融合模型_B',
    format: 'GLTF',
    source: '多机位图像重建',
    vehicleType: '客车',
    accuracy: '分米级配准',
    fusionStatus: '待补充增量更新',
    sceneSummary: '当前模型覆盖车体、路面和部分周边设施，适合快速复盘。',
    keyElements: ['事故车辆', '路面标线', '护栏', '停靠区域'],
    updatedAt: '2026-04-10 09:30',
  },
])

const fusionEndpoints = [
  {
    label: '模型导入接口',
    path: '/api/modeling/import',
    description: '接入外部 Web3D 模型文件与配套元数据。',
  },
  {
    label: '关键要素导出接口',
    path: '/api/modeling/export/key-elements',
    description: '向总系统输出车辆、道路、碰撞区域等关键场景要素。',
  },
  {
    label: '增量融合接口',
    path: '/api/modeling/fusion/incremental',
    description: '为后续动态更新和新传感器数据增量融合保留接入口。',
  },
]

const currentModel = computed(() => {
  return importedModels.value.find((item) => item.id === selectedModelId.value) || null
})

const workflowSteps = computed(() => {
  const hasModel = Boolean(currentModel.value)
  const hasIdentifiedVehicle = hasModel && currentModel.value.vehicleType !== '待识别'
  const hasElements = hasModel && currentModel.value.keyElements.length > 0
  const fusionReady = hasModel && currentModel.value.fusionStatus.includes('融合')

  return [
    {
      id: 'import',
      index: '01',
      title: '导入外部模型',
      description: '接入研究员生成的事故现场 Web3D 模型。',
      done: hasModel,
    },
    {
      id: 'identify',
      index: '02',
      title: '自动识别类型',
      description: '根据文件名和业务标签识别车辆或场景类型。',
      done: hasIdentifiedVehicle,
    },
    {
      id: 'export',
      index: '03',
      title: '导出关键要素',
      description: '提取事故车辆、道路边界、碰撞区域等核心要素。',
      done: hasElements,
    },
    {
      id: 'fusion',
      index: '04',
      title: '预留增量融合',
      description: '保留后续动态更新和二次融合的业务接口。',
      done: fusionReady,
    },
  ]
})

const currentModelElements = computed(() => {
  if (!currentModel.value) return ['等待导入模型后生成']
  return currentModel.value.keyElements
})

function openFilePicker() {
  fileInputRef.value?.click()
}

function handleFileImport(event) {
  const file = event.target.files?.[0]
  if (!file) return

  const normalizedName = file.name.trim()
  const format = inferFormat(normalizedName)
  const vehicleType = inferVehicleType(normalizedName)
  const modelId = 'import-' + Date.now()

  importedModels.value.unshift({
    id: modelId,
    name: normalizedName,
    format,
    source: '外部导入模型',
    vehicleType,
    accuracy: '待确认',
    fusionStatus: '待补充增量更新',
    sceneSummary: '已完成文件接入，等待结合业务规则进一步识别和场景解析。',
    keyElements: inferKeyElements(vehicleType),
    updatedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
  })

  selectedModelId.value = modelId
  statusMessage.value = '已导入模型 ' + normalizedName + '，可继续执行车辆识别和要素导出。'
  event.target.value = ''
}

function identifyCurrentModel() {
  if (!currentModel.value) return

  currentModel.value.vehicleType = inferVehicleType(currentModel.value.name)
  currentModel.value.keyElements = inferKeyElements(currentModel.value.vehicleType)
  currentModel.value.sceneSummary = '已完成车型识别和关键场景要素分析，可直接输出至总系统。'
  currentModel.value.accuracy = currentModel.value.accuracy === '待确认' ? '待人工复核' : currentModel.value.accuracy
  statusMessage.value = '已完成模型类型识别：' + currentModel.value.vehicleType
}

function markFusionReady() {
  if (!currentModel.value) return
  currentModel.value.fusionStatus = '已预留增量融合接口'
  statusMessage.value = '当前模型已标记为后续动态更新与增量融合接入对象。'
}

function exportKeySceneElements() {
  if (!currentModel.value) return

  const payload = {
    model_name: currentModel.value.name,
    model_format: currentModel.value.format,
    vehicle_type: currentModel.value.vehicleType,
    source: currentModel.value.source,
    key_elements: currentModel.value.keyElements,
    fusion_status: currentModel.value.fusionStatus,
    exported_at: new Date().toISOString(),
  }

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = currentModel.value.name.replace(/\.[^.]+$/, '') + '_scene_elements.json'
  anchor.click()
  URL.revokeObjectURL(url)

  statusMessage.value = '已导出关键场景要素文件，可用于总系统接入或后续联动。'
}

function inferFormat(name) {
  const match = name.toLowerCase().match(/\.([a-z0-9]+)$/)
  return match ? match[1].toUpperCase() : '未知格式'
}

function inferVehicleType(name) {
  const lowerName = name.toLowerCase()
  if (lowerName.includes('tank') || lowerName.includes('oil') || lowerName.includes('hazmat') || lowerName.includes('危')) {
    return '危化品运输车'
  }
  if (lowerName.includes('bus') || lowerName.includes('客')) {
    return '客车'
  }
  if (lowerName.includes('truck') || lowerName.includes('货')) {
    return '货车'
  }
  if (lowerName.includes('car') || lowerName.includes('sedan') || lowerName.includes('轿')) {
    return '轿车'
  }
  return '待识别'
}

function inferKeyElements(vehicleType) {
  if (vehicleType === '危化品运输车') {
    return ['事故车辆', '罐体区域', '泄漏风险区', '道路边界', '警戒范围']
  }
  if (vehicleType === '客车') {
    return ['事故车辆', '乘员区域', '道路边界', '碰撞点']
  }
  if (vehicleType === '货车') {
    return ['事故车辆', '货箱区域', '散落物区域', '道路边界']
  }
  if (vehicleType === '轿车') {
    return ['事故车辆', '碰撞点', '道路边界']
  }
  return ['事故车辆', '道路边界', '碰撞区域', '相机位姿']
}
</script>

<style scoped>
.modeling-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 22px;
  box-sizing: border-box;
  gap: 20px;
  background:
    radial-gradient(circle at top left, rgba(0, 229, 255, 0.08), transparent 28%),
    linear-gradient(180deg, rgba(4, 16, 34, 0.98), rgba(2, 10, 22, 0.98));
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.page-header h1 {
  margin: 0 0 8px;
  color: var(--primary-color);
  text-shadow: var(--glow-shadow);
}

.page-header p {
  margin: 0;
  max-width: 820px;
  color: rgba(230, 246, 255, 0.72);
  line-height: 1.7;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.hidden-input {
  display: none;
}

.modeling-content {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 340px;
  gap: 18px;
}

.workflow-panel,
.workspace-panel,
.operation-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.panel-card,
.canvas-card {
  background: rgba(7, 19, 37, 0.88);
  border: 1px solid rgba(0, 229, 255, 0.22);
  border-radius: 18px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.18);
}

.panel-card {
  padding: 18px;
}

.panel-card h2 {
  margin: 0 0 16px;
  font-size: 18px;
  color: #effaff;
}

.step-list,
.asset-list,
.property-list,
.action-stack,
.endpoint-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-card {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
}

.step-card.done {
  border-color: rgba(0, 229, 255, 0.4);
  background: rgba(0, 229, 255, 0.08);
}

.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(0, 229, 255, 0.12);
  color: #9ef6ff;
  font-weight: 700;
}

.step-card strong,
.asset-item strong,
.endpoint-item strong {
  display: block;
  color: #f4fdff;
}

.step-card p,
.asset-item p,
.endpoint-item p,
.panel-tip {
  margin: 6px 0 0;
  color: rgba(220, 240, 250, 0.72);
  line-height: 1.6;
}

.asset-item {
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  text-align: left;
  cursor: pointer;
  color: inherit;
}

.asset-item.active {
  border-color: rgba(0, 229, 255, 0.45);
  box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.18) inset;
}

.asset-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.asset-chip,
.info-chip,
.element-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
}

.asset-chip,
.info-chip {
  background: rgba(0, 229, 255, 0.12);
  color: #9ef6ff;
}

.canvas-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.canvas-stage {
  position: relative;
  flex: 1;
  min-height: 380px;
  background:
    radial-gradient(circle at 50% 50%, rgba(0, 229, 255, 0.12), transparent 36%),
    linear-gradient(180deg, rgba(8, 20, 38, 0.96), rgba(5, 14, 28, 0.98));
}

.stage-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 229, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 229, 255, 0.08) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: radial-gradient(circle at center, black 36%, transparent 92%);
}

.stage-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
}

.stage-overlay h3 {
  margin: 0;
  color: #ffffff;
  font-size: 30px;
}

.stage-overlay p {
  margin: 0;
  max-width: 560px;
  color: rgba(225, 242, 250, 0.76);
  line-height: 1.7;
}

.stage-tag {
  display: inline-flex;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(0, 229, 255, 0.12);
  color: #9ef6ff;
  font-size: 12px;
  letter-spacing: 0.08em;
}

.stage-tags,
.element-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.canvas-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 18px 18px;
  border-top: 1px solid rgba(0, 229, 255, 0.12);
}

.meta-item,
.property-item,
.endpoint-item {
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
}

.meta-item span,
.property-item span {
  display: block;
  margin-bottom: 6px;
  color: rgba(216, 236, 246, 0.68);
  font-size: 13px;
}

.meta-item strong,
.property-item strong {
  color: #ffffff;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.element-chip {
  background: rgba(255, 255, 255, 0.08);
  color: #f7fdff;
}

.primary-btn,
.secondary-btn,
.ghost-btn {
  min-height: 44px;
  padding: 0 16px;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  font-weight: 700;
}

.primary-btn {
  background: linear-gradient(135deg, #00c7e6, #1ef2ff);
  color: #03111b;
}

.secondary-btn {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.14), rgba(0, 229, 255, 0.06));
  color: #eefdff;
  border: 1px solid rgba(0, 229, 255, 0.24);
}

.ghost-btn {
  background: rgba(255, 255, 255, 0.06);
  color: #eefdff;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.ghost-btn.small {
  min-height: 34px;
  padding: 0 12px;
  font-size: 12px;
}

.primary-btn:disabled,
.secondary-btn:disabled,
.ghost-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.endpoint-item code {
  display: inline-block;
  margin-top: 8px;
  color: #8eeeff;
  background: rgba(0, 229, 255, 0.08);
  padding: 6px 10px;
  border-radius: 10px;
}

@media (max-width: 1440px) {
  .modeling-content {
    grid-template-columns: 280px minmax(0, 1fr) 300px;
  }

  .canvas-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1120px) {
  .page-header,
  .modeling-content {
    grid-template-columns: none;
    display: flex;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions button {
    flex: 1;
  }
}
</style>
