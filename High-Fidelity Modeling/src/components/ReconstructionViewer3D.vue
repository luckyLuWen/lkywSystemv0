<template>
  <div class="reconstruction-viewer-container">
    <!-- 3D 视图顶部工具栏与元数据 -->
    <div class="viewer-top-bar">
      <div class="model-info-group">
        <div class="info-badge" :class="{ loading: isLoading, error: Boolean(loadError) }">
          <span class="status-dot" :class="{ loading: isLoading, error: Boolean(loadError) }"></span>
          <span class="badge-title" :class="{ 'is-loading': isLoading, 'has-error': Boolean(loadError) }">
            {{ loadError ? '场景读取失败' : isLoading ? '正在载入三维场景' : '三维场景展示中' }}
          </span>
        </div>
        <div class="model-meta">
          <span class="meta-item">
            <span class="lbl">当前场景:</span>
            <span class="val">{{ modelName }}</span>
          </span>
          <span class="meta-item">
            <span class="lbl">场景状态:</span>
            <span class="val" :class="isLoading ? 'text-cyan' : 'text-green'">{{ loadError ? '暂不可用' : isLoading ? '正在载入' : '展示中' }}</span>
          </span>
          <span class="meta-item">
            <span class="lbl">测量基准:</span>
            <span class="val scale-indicator" :class="scaleCalibrated ? 'text-green' : 'text-yellow'" :title="scaleDescription">
              {{ scaleDescription }}
            </span>
          </span>
        </div>
      </div>

      <!-- 右侧全局控制按钮 -->
      <div class="viewer-actions">
        <button 
          class="tool-btn" 
          :class="{ active: showDrawer }" 
          @click="showDrawer = !showDrawer" 
          title="打开/收起测量数据列表"
        >
          <span class="btn-icon">📋</span> 测量记录 ({{ measurements.length }})
        </button>
        <button 
          class="tool-btn report-btn" 
          @click="openReportModal" 
          title="查看当前模型数据与空间量测"
        >
          <span class="btn-icon">📄</span> 模型报告
        </button>
        <button class="tool-btn" :class="{ active: autoRotate }" @click="toggleAutoRotate" title="自动旋转">
          <span class="btn-icon">🔄</span> {{ autoRotate ? '暂停旋转' : '自动环绕' }}
        </button>
        <button class="tool-btn" :class="{ active: isWireframe }" @click="toggleWireframe" title="切换拓扑线框">
          <span class="btn-icon">📐</span> {{ isWireframe ? '实体纹理' : '网格线框' }}
        </button>
        <button class="tool-btn primary-fit" @click="focusCameraToScreen" title="Camera Focus / Fit to Screen">
          <span class="btn-icon">🎯</span> 视角复位
        </button>
        <button class="tool-btn danger-btn" @click="$emit('reset-step')" title="重新开始">
          <span class="btn-icon">↺</span> 重新导入
        </button>
      </div>
    </div>

    <!-- 3D 渲染画布容器 -->
    <div class="canvas-wrapper" ref="canvasContainerRef">
      <div 
        class="canvas-3d" 
        ref="threeCanvasRef" 
        :class="{ 'cursor-crosshair': measureMode !== 'none' }"
        @click="handleCanvasClick"
      ></div>

      <!-- 【步骤五】3D 画布悬浮空间测量工具栏 (Floating Measurement Toolbar) -->
      <div class="floating-measure-toolbar">
        <div class="toolbar-title">
          <span class="pulse-icon">📏</span>
          <span><b>空间量测</b></span>
        </div>
        
        <div class="tool-mode-group">
          <button 
            class="mode-btn" 
            :class="{ active: measureMode === 'point' }" 
            @click="setMeasureMode('point')"
            title="提取场景局部坐标（单位见测量基准）"
          >
            <span class="mode-icon">📍</span> 点坐标提取
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: measureMode === 'line' }" 
            @click="setMeasureMode('line')"
            title="选择 2 点计算直线距离（按当前坐标单位）"
          >
            <span class="mode-icon">📏</span> 直线距离测量
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: measureMode === 'area' }" 
            @click="setMeasureMode('area')"
            title="连续选点计算水平地面正交投影面积 (XZ-Plane)"
          >
            <span class="mode-icon">📐</span> 地面正交投影面积
          </button>
        </div>

        <div class="tool-divider"></div>

        <div class="tool-action-group">
          <button 
            v-if="measureMode === 'area' && pendingPoints.length >= 3"
            class="action-sub-btn success-btn"
            @click="finishPolygonArea"
            title="闭合选点并计算水平地面正交投影影子面积 (Shoelace Formula)"
          >
            ✔️ 完成闭合 ({{ pendingPoints.length }}点)
          </button>
          <button 
            class="action-sub-btn" 
            @click="undoLastAction"
            :disabled="pendingPoints.length === 0 && measurements.length === 0"
            title="撤销上一步选点或上条测量"
          >
            ↩️ 撤销
          </button>
          <button 
            class="action-sub-btn danger-btn" 
            @click="clearMeasurements"
            :disabled="measurements.length === 0 && pendingPoints.length === 0"
            title="清除所有测量数据"
          >
            🗑️ 清空
          </button>
        </div>
      </div>

      <!-- 测量交互实时提示 -->
      <div v-if="measureMode !== 'none'" class="measure-status-hint">
          <span v-if="measureMode === 'point'">📍 <b>点坐标：</b>点击模型表面提取坐标（{{ coordinateUnit }}）</span>
        <span v-else-if="measureMode === 'line'">
          📏 <b>直线距离：</b>
          <template v-if="pendingPoints.length === 0">请点击选择<b>起点 P1</b></template>
          <template v-else>已选择起点，请点击选择<b>终点 P2</b></template>
        </span>
        <span v-else-if="measureMode === 'area'">
          📐 <b>水平投影面积：</b>已选 <b>{{ pendingPoints.length }}</b> 点，至少 3 点后闭合计算。
        </span>
      </div>

      <!-- 加载遮罩与进度条 -->
      <div class="loading-overlay" v-if="isLoading">
        <div class="spinner-box">
          <div class="cyber-spinner"></div>
          <p class="loading-text">正在载入三维场景并整理显示数据…</p>
          <div class="loading-bar-bg">
            <div class="loading-bar-fill" :style="{ width: loadProgress + '%' }"></div>
          </div>
          <span class="progress-num">{{ loadProgress }}%</span>
        </div>
      </div>

      <div v-if="loadError" class="load-error-overlay">
        <div class="load-error-card">
          <strong>三维场景暂时无法读取</strong>
          <p>{{ loadError }}</p>
          <button type="button" @click="loadModel(modelUrl)">重新读取模型</button>
        </div>
      </div>

      <!-- 三维空间检测热点与动态测量 HUD 卡片层 -->
      <div v-if="!isLoading && showAnnotations" class="inspection-tags-layer">
        <!-- 常规检测点 -->
        <div 
          v-for="(tag, idx) in inspectionTags" 
          :key="'tag-' + idx" 
          class="inspection-tag-card"
          :style="{ left: tag.screenX + 'px', top: tag.screenY + 'px' }"
          :class="{ visible: tag.visible }"
        >
          <div class="tag-header">
            <span class="tag-dot"></span>
            <span class="tag-name">{{ tag.name }}</span>
          </div>
          <div class="tag-body">
            <span class="tag-val">{{ tag.value }}</span>
          </div>
        </div>

        <!-- 动态三维测量 HUD 卡片 (`Array<Measurement>`) -->
        <div 
          v-for="m in measurements" 
          :key="'m-' + m.id" 
          class="measurement-hud-card"
          :style="{ left: m.screenX + 'px', top: m.screenY + 'px' }"
          :class="['hud-type-' + m.type, { visible: m.visible }]"
        >
          <div class="hud-header">
            <span class="hud-icon">{{ m.type === 'point' ? '📍' : m.type === 'line' ? '📏' : '📐' }}</span>
            <span class="hud-title">{{ m.name }}: <strong>{{ m.valueStr }}</strong></span>
            <button class="hud-delete-btn" @click.stop="deleteMeasurement(m.id)" title="删除此条">✕</button>
          </div>
          <div class="hud-body">
            <template v-if="m.type === 'point'">
              <span class="hud-vector">X: {{ m.points[0].x.toFixed(2) }} | Y: {{ m.points[0].y.toFixed(2) }} | Z: {{ m.points[0].z.toFixed(2) }} {{ coordinateUnit }}</span>
            </template>
            <template v-else-if="m.type === 'line'">
              <span class="hud-vector">ΔX: {{ m.dx.toFixed(2) }} | ΔY: {{ m.dy.toFixed(2) }} | ΔZ: {{ m.dz.toFixed(2) }} {{ coordinateUnit }}</span>
            </template>
            <template v-else-if="m.type === 'area'">
              <span class="hud-vector">水平投影面积 · 周长 {{ estimateGroundPolygonPerimeter(m.points).toFixed(2) }} {{ coordinateUnit }}</span>
            </template>
          </div>
        </div>
      </div>

      <!-- 右侧测量记录抽屉面板 (Measurement Drawer) -->
      <transition name="slide-left">
        <div v-if="showDrawer" class="measurement-drawer-panel">
          <div class="drawer-header">
            <div class="drawer-title">
              <span>📋 测量数据集</span>
              <span class="count-badge">{{ measurements.length }} 项</span>
            </div>
            <button class="close-drawer-btn" @click="showDrawer = false">✕</button>
          </div>

          <div class="drawer-body">
            <div v-if="measurements.length === 0" class="empty-state">
              <span class="empty-icon">📏</span>
              <p>暂无测量记录</p>
                <span class="empty-sub">选择点、线或面工具后，在模型上取点</span>
            </div>

            <div 
              v-for="(item, index) in measurements" 
              :key="item.id" 
              class="measurement-card-item"
            >
              <div class="item-header">
                <span class="type-tag" :class="'tag-' + item.type">
                  {{ item.type === 'point' ? '点坐标' : item.type === 'line' ? '直线距离' : '地面投影面积' }}
                </span>
                <input
                  v-model.trim="item.name"
                  class="item-name-input"
                  type="text"
                  maxlength="40"
                  aria-label="测量项目名称"
                  @blur="normalizeMeasurementName(item, index)"
                />
                <button class="delete-item-btn" @click="deleteMeasurement(item.id)" title="删除此项">🗑️</button>
              </div>

              <div class="item-value-row">
                <span class="val-main">{{ item.valueStr }}</span>
                <button class="focus-btn" @click="focusOnMeasurement(item)" title="视角聚焦至该测量项">
                  🎯 聚焦
                </button>
              </div>

              <div class="item-coords">
                <div v-for="(p, pIdx) in item.points" :key="pIdx" class="coord-line">
                  P{{ pIdx + 1 }}: ({{ p.x.toFixed(2) }}, {{ p.y.toFixed(2) }}, {{ p.z.toFixed(2) }})
                </div>
              </div>
            </div>
          </div>

          <div class="drawer-footer">
            <button class="footer-btn danger-btn" @click="clearMeasurements" :disabled="measurements.length === 0">
              🗑️ 清空所有数据
            </button>
            <button class="footer-btn primary-btn" @click="openReportModal">
              📄 生成评估报告
            </button>
          </div>
        </div>
      </transition>

      <!-- 画布底部操作指引提示 -->
      <div class="canvas-hint" v-if="!isLoading && measureMode === 'none'">
        <span>左键旋转 · 右键平移 · 滚轮缩放</span>
      </div>
    </div>

    <div v-if="pendingMeasurement" class="measurement-entry-overlay" role="dialog" aria-modal="true" aria-labelledby="measurement-entry-title">
      <form class="measurement-entry-card" @submit.prevent="commitPendingMeasurement">
        <header class="measurement-entry-header">
          <div>
            <span class="entry-eyebrow">保存空间量测</span>
            <h2 id="measurement-entry-title">{{ pendingMeasurement.type === 'point' ? '点坐标' : pendingMeasurement.type === 'line' ? '直线距离' : '水平投影面积' }}</h2>
          </div>
          <span class="entry-measurement-value">{{ pendingMeasurement.valueStr }}</span>
        </header>

        <label class="entry-field">
          <span>测量名称 <b>*</b></span>
          <input v-model.trim="measurementDraft.name" type="text" maxlength="40" placeholder="请输入便于识别的名称" required autofocus />
        </label>

        <template v-if="pendingMeasurement.type === 'point'">
          <div class="entry-reference-heading">
            <span>参考坐标 <small>可选</small></span>
            <span>{{ coordinateUnit }}</span>
          </div>
          <div class="entry-coordinate-grid">
            <label class="entry-field"><span>X</span><input v-model="measurementDraft.referenceX" type="number" step="any" :disabled="!scaleCalibrated" /></label>
            <label class="entry-field"><span>Y</span><input v-model="measurementDraft.referenceY" type="number" step="any" :disabled="!scaleCalibrated" /></label>
            <label class="entry-field"><span>Z</span><input v-model="measurementDraft.referenceZ" type="number" step="any" :disabled="!scaleCalibrated" /></label>
          </div>
          <p v-if="scaleCalibrated" class="entry-help">用于点位对比；参考坐标须与场景局部坐标系一致。</p>
          <p v-else class="entry-help">当前模型尺度未标定，点位实际坐标无法比较。</p>
        </template>

        <template v-else>
          <label class="entry-field">
            <span>{{ pendingMeasurement.type === 'line' ? '参考实际长度' : '参考实际面积' }} <small>可选</small></span>
            <div class="entry-number-field">
              <input v-model="measurementDraft.referenceValue" type="number" min="0" step="any" :placeholder="pendingMeasurement.type === 'line' ? '输入已知长度' : '输入同一边界的水平投影面积'" />
              <span>{{ pendingMeasurement.type === 'line' ? 'm' : 'm²' }}</span>
            </div>
          </label>
          <label v-if="!scaleCalibrated" class="entry-calibration-option">
            <input v-model="measurementDraft.useForScaleCalibration" type="checkbox" :disabled="!measurementDraft.referenceValue" />
            <span>用此参考值标定场景比例</span>
          </label>
          <p v-if="!scaleCalibrated" class="entry-help">未标定时，参考值不能直接比较；若用它标定，本条仅作尺度基准，不计入精度校核。</p>
        </template>

        <label class="entry-field">
          <span>参考来源 <small>可选</small></span>
          <input v-model.trim="measurementDraft.referenceSource" type="text" maxlength="60" placeholder="例如：现场尺量、测绘控制点" />
        </label>

        <p v-if="measurementEntryError" class="entry-error" role="alert">{{ measurementEntryError }}</p>

        <footer class="measurement-entry-actions">
          <button type="button" class="entry-cancel-button" @click="cancelPendingMeasurement">取消本次测量</button>
          <button type="submit" class="entry-save-button" :disabled="!canSavePendingMeasurement">保存测量记录</button>
        </footer>
      </form>
    </div>

    <!-- 【步骤六】：模型测量报告生成与导出 Modal (Assessment Report Modal) -->
    <div v-if="showReportModal" class="report-modal-overlay" @click.self="showReportModal = false">
      <div class="report-modal-card">
        <div class="report-header">
          <div class="report-title-group">
            <h2>三维重建模型与量测报告</h2>
          </div>
          <button class="close-modal-btn" @click="showReportModal = false">✕</button>
        </div>

        <div class="report-body" ref="reportPrintRef">
          <!-- 报告基本元数据区 -->
          <div class="report-meta-grid">
            <div class="meta-card">
              <span class="meta-lbl">报告编号</span>
              <span class="meta-val highlight">{{ reportId }}</span>
            </div>
            <div class="meta-card">
              <span class="meta-lbl">事故车辆模型</span>
              <span class="meta-val">{{ modelName }}</span>
            </div>
            <div class="meta-card">
              <span class="meta-lbl">{{ captureImageTypeLabel }}</span>
              <span class="meta-val">{{ captureImageSummary }}</span>
            </div>
            <div class="meta-card">
              <span class="meta-lbl">生成时间</span>
              <span class="meta-val">{{ reportGenerateTime }}</span>
            </div>
          </div>

          <p v-if="isSyntheticCapture && showSyntheticCaptureNote" class="precision-note synthetic-data-note">仿真 UAV/UGV 视角由三维模型渲染生成，不是真实采集影像，也不构成独立精度验证数据。</p>

          <!-- 当前模型可直接读取的数据与精度依据 -->
          <div class="report-kpi-row">
            <div class="kpi-box">
              <span class="kpi-label">输入影像</span>
              <span class="kpi-num text-cyan">{{ formatInteger(modelMetadata.datasetCounts?.total || 0) }}</span>
              <span class="kpi-unit">{{ captureViewShortSummary }}</span>
            </div>
            <div class="kpi-box">
              <span class="kpi-label">三角网格</span>
              <span class="kpi-num text-yellow">{{ formatMeshCount(modelMetadata.faces) }} 面</span>
              <span class="kpi-unit">{{ formatMeshCount(modelMetadata.vertices) }} 顶点 · {{ surfaceAppearance }}</span>
            </div>
            <div class="kpi-box">
              <span class="kpi-label">坐标与尺度</span>
              <span class="kpi-num text-green">{{ coordinateUnit }}</span>
              <span class="kpi-unit">{{ scaleDescription }}</span>
            </div>
            <div class="kpi-box precision-box">
              <span class="kpi-label">实测准确度</span>
              <span class="kpi-num text-red">待验证</span>
              <span class="kpi-unit">数值显示：{{ measurementReadout }}</span>
            </div>
          </div>

          <p v-if="showReportPrecisionNote" class="precision-note">{{ measurementAccuracyNote }} 网格规模不等于精度；下列内容包括软件处理指标与既有网格内测量，不替代独立检查点的三维误差。</p>

          <section v-if="qualityReportMetrics.length" class="report-table-section quality-report-section">
            <h3>建模处理指标与网格内测量</h3>
            <p class="quality-report-source">
              <span v-if="qualityReportShowSource">{{ modelMetadata.qualityReport.source }}</span>
              <a v-if="modelMetadata.qualityReport.reportFileUrl" :href="modelMetadata.qualityReport.reportFileUrl" target="_blank" rel="noopener">查看原始处理报告</a>
            </p>
            <table class="report-data-table">
              <thead>
                <tr>
                  <th>指标</th>
                  <th>报告值</th>
                  <th v-if="qualityReportShowScopes">来源与口径</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="metric in qualityReportMetrics" :key="metric.id">
                  <td><strong>{{ metric.label }}</strong></td>
                  <td>{{ formatQualityMetric(metric) }}</td>
                  <td v-if="qualityReportShowScopes">{{ metric.scope }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="qualityReportShowCaveat" class="quality-report-caveat">{{ qualityReportCaveat }}</p>
          </section>

          <!-- 测量数据明细列表 -->
          <div class="report-table-section">
            <h3>空间量测记录 · {{ measurements.length }} 项</h3>
            <table class="report-data-table">
              <thead>
                <tr>
                  <th>序号</th>
                  <th>类型</th>
                  <th>测量项名称</th>
                  <th>测量数值 / 维度</th>
                  <th>场景局部坐标（{{ coordinateUnit }}）</th>
                  <th>参考校核状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="measurements.length === 0">
                  <td colspan="7" class="no-data-td">暂无量测记录</td>
                </tr>
                <tr v-for="(m, index) in measurements" :key="m.id">
                  <td>{{ index + 1 }}</td>
                  <td>
                    <span class="type-badge" :class="'badge-' + m.type">
                      {{ m.type === 'point' ? '点坐标' : m.type === 'line' ? '直线距离' : '地面投影面积' }}
                    </span>
                  </td>
                  <td><strong>{{ m.name }}</strong></td>
                  <td class="value-cell">
                    {{ m.valueStr }}
                    <small class="reference-comparison">{{ getMeasurementComparisonSummary(m) }}</small>
                  </td>
                  <td class="coord-cell">
                    <div v-for="(p, pIdx) in m.points" :key="pIdx">
                      P{{ pIdx + 1 }}: ({{ p.x.toFixed(2) }}, {{ p.y.toFixed(2) }}, {{ p.z.toFixed(2) }})
                    </div>
                  </td>
                  <td>
                    <span class="remark-tag" :class="m.referenceComparisonStatus === '单项参考对比' || m.referenceComparisonStatus === '单点坐标对比' ? 'remark-warning' : 'remark-normal'">
                      {{ m.referenceComparisonStatus }}
                    </span>
                  </td>
                  <td>
                    <button class="delete-report-btn" @click="deleteMeasurement(m.id)" title="同步从场景与报表中移除">🗑️ 移除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 精度数据来源说明 -->
          <div class="report-conclusion-box">
            <h4>量测口径</h4>
            <p>{{ measurementAccuracyNote }} 单项偏差只表示与该参考值的比较，不代表模型整体准确度；总体准确度仍需独立检查点或参考扫描验证。</p>
          </div>
        </div>

        <div class="report-footer">
          <button class="report-action-btn secondary" @click="exportTXTReport" title="纯文本 (TXT格式) 导出">
            📝 导出 TXT 纯文本
          </button>
          <button class="report-action-btn secondary" @click="exportMDReport" title="Markdown (MD格式) 表格导出">
            📑 导出 Markdown 报告
          </button>
          <button class="report-action-btn secondary" @click="exportCSVData" title="CSV 数据导出">
            💾 导出 CSV 数据
          </button>
          <button class="report-action-btn primary" @click="printReport" title="打印/导出 PDF 报告">
            🖨️ 打印 / 导出 PDF
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'

// Props & Emits
const props = defineProps({
  modelUrl: {
    type: String,
    default: ''
  },
  modelName: {
    type: String,
    default: '重建场景'
  },
  modelMetadata: {
    type: Object,
    default: () => ({})
  },
  activeStep: {
    type: Number,
    default: 4
  }
})

const emit = defineEmits(['reset-step', 'update-step', 'model-loaded'])

// DOM 引用与 Three.js 句柄
const canvasContainerRef = ref(null)
const threeCanvasRef = ref(null)
const reportPrintRef = ref(null)

let scene = null
let camera = null
let renderer = null
let controls = null
let currentModelGroup = null
let animationFrameId = null
let mixer = null
let measurementGroup = null
let previewGroup = null

const raycaster = new THREE.Raycaster()
const mouse = new THREE.Vector2()
const clock = new THREE.Clock()

let boundingBoxCenter = new THREE.Vector3()
let boundingBoxSize = new THREE.Vector3()
let boundingSphereRadius = 10

// 只采用资源清单声明的尺度；缺少外部基准时保留模型原始单位。
const modelScaleFactor = ref(1.0)
const runtimeScaleFactor = ref(null)
const runtimeScaleSource = ref('')
const scaleCalibrated = computed(() => Number(runtimeScaleFactor.value) > 0 || Boolean(props.modelMetadata.scaleCalibrated))
const coordinateUnit = computed(() => Number(runtimeScaleFactor.value) > 0 ? 'm' : props.modelMetadata.unitLabel || (props.modelMetadata.coordinateSystem === 'ENU' ? 'm' : '模型单位'))
const areaUnit = computed(() => coordinateUnit.value === 'm' ? 'm²' : `${coordinateUnit.value}²`)
const scaleDescription = computed(() => Number(runtimeScaleFactor.value) > 0 ? '参考尺寸标定 · 场景局部坐标' : props.modelMetadata.coordinateLabel || (scaleCalibrated.value ? `米制 · ${props.modelMetadata.coordinateSystem || '场景局部坐标'}` : '未标定 · 模型单位'))
const scaleSourceDescription = computed(() => runtimeScaleSource.value || props.modelMetadata.scaleSource || '未提供')
const surfaceAppearance = computed(() => props.modelMetadata.surfaceAppearance || (props.modelMetadata.textureUrl ? '照片纹理' : '顶点颜色'))
const measurementReadout = computed(() => scaleCalibrated.value && coordinateUnit.value === 'm'
  ? '距离/坐标 0.01 m；面积 0.01 m²'
  : `距离/坐标 0.01 ${coordinateUnit.value}；面积 0.01 ${areaUnit.value}`)
const measurementAccuracyNote = computed(() => scaleCalibrated.value && coordinateUnit.value === 'm'
  ? '距离与坐标显示到 0.01 m（厘米位），面积显示到 0.01 m²；这是数值显示分辨率，不代表实际误差。'
  : `当前按 ${coordinateUnit.value} 显示，尚无米制标定，不能声明厘米级准确度。`)
const isSyntheticCapture = computed(() => String(props.modelMetadata.captureType || '').toLowerCase() === 'synthetic')
const captureImageTypeLabel = computed(() => isSyntheticCapture.value ? '影像来源' : '采集影像')
const captureUavLabel = computed(() => isSyntheticCapture.value ? '仿真 UAV 视角' : '航拍')
const captureUgvLabel = computed(() => isSyntheticCapture.value ? '仿真 UGV 视角' : '地面')
const captureImageSummary = computed(() => {
  const counts = props.modelMetadata.datasetCounts || {}
  const parts = [
    `${captureUavLabel.value} ${counts.uav || 0} 张`,
    `${captureUgvLabel.value} ${counts.ugv || 0} 张`
  ]
  if (counts.other) parts.push(`其他 ${counts.other} 张`)
  return `${isSyntheticCapture.value ? '合成仿真 · ' : ''}${parts.join(' / ')}`
})
const captureViewShortSummary = computed(() => isSyntheticCapture.value
  ? `仿真 UAV ${props.modelMetadata.datasetCounts?.uav || 0} · 仿真 UGV ${props.modelMetadata.datasetCounts?.ugv || 0}`
  : `UAV ${props.modelMetadata.datasetCounts?.uav || 0} · UGV ${props.modelMetadata.datasetCounts?.ugv || 0}`)
const qualityReportMetrics = computed(() => Array.isArray(props.modelMetadata.qualityReport?.metrics)
  ? props.modelMetadata.qualityReport.metrics
  : [])
const qualityReportCaveat = computed(() => props.modelMetadata.qualityReport?.caveat || '')
const qualityReportShowScopes = computed(() => props.modelMetadata.qualityReport?.showScopes !== false)
const qualityReportShowSource = computed(() => props.modelMetadata.qualityReport?.showSource !== false)
const qualityReportShowCaveat = computed(() => props.modelMetadata.qualityReport?.showCaveat !== false && Boolean(qualityReportCaveat.value))
const showSyntheticCaptureNote = computed(() => props.modelMetadata.qualityReport?.showSyntheticCaptureNote !== false)
const showReportPrecisionNote = computed(() => props.modelMetadata.qualityReport?.showPrecisionNote !== false)
const formatQualityMetric = (metric) => `${metric.value}${metric.unit ? ` ${metric.unit}` : ''}`

const formatInteger = (value) => Number(value || 0).toLocaleString('zh-CN')
const formatMeshCount = (value) => {
  const count = Number(value || 0)
  return count >= 1_000_000 ? `约${Math.round(count / 10_000)}万` : formatInteger(count)
}
const formatDistance = (value, digits = 2) => value == null ? '暂无记录' : Number.isFinite(Number(value)) ? `${Number(value).toFixed(digits)} ${coordinateUnit.value}` : '暂无记录'
const formatArea = (value, digits = 2) => value == null ? '暂无记录' : Number.isFinite(Number(value)) ? `${Number(value).toFixed(digits)} ${areaUnit.value}` : '暂无记录'

// 状态管理
const isLoading = ref(true)
const loadProgress = ref(0)
const loadError = ref('')
const autoRotate = ref(false)
const isWireframe = ref(false)
const showAnnotations = ref(false)
const isPlayAnimation = ref(false)
const showDrawer = ref(false)
const showReportModal = ref(false)
const reportGenerateTime = ref('')

// 【步骤五核心】：空间测量模式 ('none' | 'point' | 'line' | 'area')
const measureMode = ref('none')
const pendingPoints = ref([])
const measurements = ref([])
const pendingMeasurement = ref(null)
const measurementEntryError = ref('')
const measurementDraft = ref({
  name: '',
  referenceValue: '',
  referenceX: '',
  referenceY: '',
  referenceZ: '',
  referenceSource: '',
  useForScaleCalibration: false
})
const referenceInputValid = computed(() => {
  if (!pendingMeasurement.value) return true
  if (pendingMeasurement.value.type === 'point') {
    const coords = [measurementDraft.value.referenceX, measurementDraft.value.referenceY, measurementDraft.value.referenceZ].map(value => String(value).trim())
    return coords.every(value => value === '') || (scaleCalibrated.value && coords.every(value => value !== '' && Number.isFinite(Number(value))))
  }
  const rawValue = String(measurementDraft.value.referenceValue).trim()
  return rawValue === '' || (Number.isFinite(Number(rawValue)) && Number(rawValue) > 0)
})
const canSavePendingMeasurement = computed(() => Boolean(measurementDraft.value.name.trim()) && referenceInputValid.value)

// 常规 3D 检测点
const inspectionTags = ref([])
const reportId = ref('')
let modelLoadId = 0

const referenceValueLabel = (measurement) => {
  if (measurement.referenceValue == null) return ''
  const unit = measurement.referenceUnit || (measurement.type === 'area' ? areaUnit.value : coordinateUnit.value)
  const digits = measurement.type === 'area' ? 2 : 2
  return `${Number(measurement.referenceValue).toFixed(digits)} ${unit}`
}

const updateMeasurementComparison = (measurement) => {
  measurement.referenceAbsoluteDeviation = null
  measurement.referenceRelativeDeviation = null

  if (measurement.referenceRole === 'scale-calibration') {
    measurement.referenceComparisonStatus = '比例标定基准'
    measurement.referenceComparisonText = `参考值 ${referenceValueLabel(measurement)}；本条用于尺度标定，不作为精度校核。`
    return
  }

  if (measurement.type === 'point') {
    if (!measurement.referenceCoordinates) {
      measurement.referenceComparisonStatus = '未提供参考坐标'
      measurement.referenceComparisonText = '未提供参考坐标。'
      return
    }
    if (!scaleCalibrated.value || !measurement.points?.[0]) {
      measurement.referenceComparisonStatus = '尺度未标定'
      measurement.referenceComparisonText = '已录入参考坐标；尺度未标定，未比较。'
      return
    }

    const delta = measurement.points[0].clone().sub(measurement.referenceCoordinates)
    measurement.referenceAbsoluteDeviation = delta.length()
    measurement.referenceComparisonStatus = '单点坐标对比'
    measurement.referenceComparisonText = `参考坐标 (${measurement.referenceCoordinates.x.toFixed(2)}, ${measurement.referenceCoordinates.y.toFixed(2)}, ${measurement.referenceCoordinates.z.toFixed(2)}) ${coordinateUnit.value}；三维差 ${formatDistance(delta.length())}${measurement.referenceSource ? `；来源 ${measurement.referenceSource}` : ''}。`
    return
  }

  if (measurement.referenceValue == null) {
    measurement.referenceComparisonStatus = '未提供参考值'
    measurement.referenceComparisonText = '未提供参考值。'
    return
  }
  if (!scaleCalibrated.value) {
    measurement.referenceComparisonStatus = '尺度未标定'
    measurement.referenceComparisonText = `已录入参考值 ${referenceValueLabel(measurement)}；尺度未标定，未比较。`
    return
  }

  const measuredValue = measurement.type === 'area' ? measurement.area : measurement.distance
  const deviation = Math.abs(measuredValue - Number(measurement.referenceValue))
  measurement.referenceAbsoluteDeviation = deviation
  measurement.referenceRelativeDeviation = Number(measurement.referenceValue) > 0 ? (deviation / Number(measurement.referenceValue)) * 100 : null
  const formattedDeviation = measurement.type === 'area' ? formatArea(deviation) : formatDistance(deviation)
  const relative = measurement.referenceRelativeDeviation == null ? '' : `（${measurement.referenceRelativeDeviation.toFixed(2)}%）`
  measurement.referenceComparisonStatus = '单项参考对比'
  measurement.referenceComparisonText = `参考值 ${referenceValueLabel(measurement)}；偏差 ${formattedDeviation}${relative}${measurement.referenceSource ? `；来源 ${measurement.referenceSource}` : ''}。`
}

const updateMeasurementGeometry = (measurement) => {
  const rawPoints = measurement.rawPoints || measurement.points
  if (!rawPoints?.length) return

  if (measurement.type === 'point') {
    const raw = rawPoints[0]
    const point = new THREE.Vector3(raw.x * modelScaleFactor.value, raw.y * modelScaleFactor.value, raw.z * modelScaleFactor.value)
    measurement.points = [point]
    measurement.valueStr = `(${point.x.toFixed(2)}, ${point.y.toFixed(2)}, ${point.z.toFixed(2)}) ${coordinateUnit.value}`
    measurement.unit = coordinateUnit.value
  } else if (measurement.type === 'line') {
    const [p1, p2] = rawPoints
    const distance = p1.distanceTo(p2) * modelScaleFactor.value
    measurement.distance = distance
    measurement.valueStr = formatDistance(distance)
    measurement.unit = coordinateUnit.value
    measurement.dx = Math.abs(p1.x - p2.x) * modelScaleFactor.value
    measurement.dy = Math.abs(p1.y - p2.y) * modelScaleFactor.value
    measurement.dz = Math.abs(p1.z - p2.z) * modelScaleFactor.value
    measurement.points = [
      new THREE.Vector3(p1.x * modelScaleFactor.value, p1.y * modelScaleFactor.value, p1.z * modelScaleFactor.value),
      new THREE.Vector3(p2.x * modelScaleFactor.value, p2.y * modelScaleFactor.value, p2.z * modelScaleFactor.value)
    ]
  } else if (measurement.type === 'area') {
    const area = calculateGroundProjectionArea(rawPoints)
    measurement.area = area
    measurement.valueStr = formatArea(area)
    measurement.unit = areaUnit.value
    measurement.points = rawPoints.map(point => new THREE.Vector3(point.x * modelScaleFactor.value, point.y * modelScaleFactor.value, point.z * modelScaleFactor.value))
  }

  updateMeasurementComparison(measurement)
}

// 应用有来源的尺度基准，并同步更新已有测量值。
const recalibrateScale = () => {
  const runtimeScale = Number(runtimeScaleFactor.value)
  const declaredScale = Number(props.modelMetadata.scaleFactor)
  modelScaleFactor.value = runtimeScale > 0
    ? runtimeScale
    : scaleCalibrated.value && Number.isFinite(declaredScale) && declaredScale > 0 ? declaredScale : 1.0

  measurements.value.forEach(updateMeasurementGeometry)
}

// 模式切换
const setMeasureMode = (mode) => {
  if (measureMode.value === mode) {
    measureMode.value = 'none'
  } else {
    measureMode.value = mode
  }
  clearPendingPoints()

  if (controls) {
    controls.autoRotate = measureMode.value === 'none' ? autoRotate.value : false
  }

  if (measureMode.value !== 'none' && props.activeStep !== 5) {
    emit('update-step', 5)
  }
}

const clearPendingPoints = () => {
  pendingPoints.value = []
  if (previewGroup) {
    while (previewGroup.children.length > 0) {
      const child = previewGroup.children[0]
      if (child.geometry) child.geometry.dispose()
      if (child.material) {
        if (Array.isArray(child.material)) child.material.forEach(m => m.dispose())
        else child.material.dispose()
      }
      previewGroup.remove(child)
    }
  }
}

// 撤销上一步操作
const undoLastAction = () => {
  if (pendingPoints.value.length > 0) {
    pendingPoints.value.pop()
    rebuildPreviewGeometries()
  } else if (measurements.value.length > 0) {
    measurements.value.pop()
    rebuildAllMeasurementGeometries()
  }
}

// 清除所有测量
const clearMeasurements = () => {
  measurements.value = []
  clearPendingPoints()
  rebuildAllMeasurementGeometries()
}

// 删除特定测量项
const deleteMeasurement = (id) => {
  measurements.value = measurements.value.filter(m => m.id !== id)
  rebuildAllMeasurementGeometries()
}

// 打开测量报告 (步骤六)
const openReportModal = () => {
  reportGenerateTime.value = new Date().toLocaleString()
  reportId.value = `REP-${Date.now()}`
  showReportModal.value = true
  emit('update-step', 6)
}

const getModelName = () => props.modelName || '重建场景'

const normalizeMeasurementName = (item, index) => {
  const cleanedName = String(item.name || '').replace(/[\r\n]+/g, ' ').trim()
  if (cleanedName) {
    item.name = cleanedName
    return
  }

  const typeName = item.type === 'point' ? '点坐标' : item.type === 'line' ? '直线距离' : '水平投影面积'
  item.name = `${typeName} #${index + 1}`
}

const queueMeasurement = (measurement) => {
  pendingMeasurement.value = measurement
  measurementDraft.value = {
    name: '',
    referenceValue: '',
    referenceX: '',
    referenceY: '',
    referenceZ: '',
    referenceSource: '',
    useForScaleCalibration: false
  }
  measurementEntryError.value = ''
  measureMode.value = 'none'
  clearPendingPoints()
  if (controls) controls.autoRotate = autoRotate.value
}

const cancelPendingMeasurement = () => {
  pendingMeasurement.value = null
  measurementEntryError.value = ''
  clearPendingPoints()
  if (controls) controls.autoRotate = autoRotate.value
}

const commitPendingMeasurement = () => {
  const measurement = pendingMeasurement.value
  if (!measurement || !canSavePendingMeasurement.value) return

  measurement.name = measurementDraft.value.name.trim()
  measurement.referenceSource = measurementDraft.value.referenceSource.trim()

  if (measurement.type === 'point') {
    const referenceCoords = [measurementDraft.value.referenceX, measurementDraft.value.referenceY, measurementDraft.value.referenceZ].map(value => String(value).trim())
    if (referenceCoords.every(value => value !== '')) {
      measurement.referenceCoordinates = new THREE.Vector3(...referenceCoords.map(Number))
      measurement.referenceUnit = coordinateUnit.value
    }
    updateMeasurementGeometry(measurement)
  } else {
    const referenceValueText = String(measurementDraft.value.referenceValue).trim()
    if (referenceValueText) {
      measurement.referenceValue = Number(referenceValueText)
      measurement.referenceUnit = measurement.type === 'area' ? 'm²' : 'm'
      measurement.referenceRole = 'comparison'
    }

    if (referenceValueText && !scaleCalibrated.value && measurementDraft.value.useForScaleCalibration) {
      const referenceValue = Number(referenceValueText)
      const rawValue = getUnscaledMeasurementValue(measurement)
      if (!(rawValue > 0) || !(referenceValue > 0)) {
        measurementEntryError.value = '当前量测值无法用于比例标定，请检查参考尺寸。'
        return
      }

      runtimeScaleFactor.value = measurement.type === 'line' ? referenceValue / rawValue : Math.sqrt(referenceValue / rawValue)
      runtimeScaleSource.value = `${measurement.name} 的参考${measurement.type === 'line' ? '长度' : '面积'}`
      measurement.referenceRole = 'scale-calibration'
      measurement.referenceUnit = measurement.type === 'area' ? 'm²' : 'm'
      recalibrateScale()
    }

    updateMeasurementGeometry(measurement)
  }

  updateMeasurementComparison(measurement)
  measurements.value.push(measurement)
  pendingMeasurement.value = null
  measurementEntryError.value = ''
  rebuildAllMeasurementGeometries()
}

const getUnscaledMeasurementValue = (measurement) => {
  if (!measurement?.rawPoints?.length) return null
  if (measurement.type === 'line') return measurement.rawPoints[0].distanceTo(measurement.rawPoints[1])
  if (measurement.type === 'area') return calculateGroundProjectionArea(measurement.rawPoints) / Math.pow(modelScaleFactor.value, 2)
  return null
}

const getMeasurementComparisonSummary = (measurement) => measurement.referenceComparisonText || '未提供参考值。'

// 评估报告计算辅助
const getMaxMeasuredDistance = () => {
  let maxD = 0
  measurements.value.forEach(m => {
    if (m.type === 'line' && m.distance > maxD) {
      maxD = m.distance
    }
  })
  return maxD > 0 ? maxD : null
}

const getTotalProjectionArea = () => {
  let totalA = 0
  measurements.value.forEach(m => {
    if (m.type === 'area' && m.area > 0) {
      totalA += m.area
    }
  })
  return totalA > 0 ? totalA : null
}

const estimateGroundPolygonPerimeter = (pts) => {
  if (!pts || pts.length < 2) return 0
  let len = 0
  for (let i = 0; i < pts.length; i++) {
    const p1 = pts[i]
    const p2 = pts[(i + 1) % pts.length]
    // 只在 X-Z 水平地面投影平面上计算两点距离
    const dx = p1.x - p2.x
    const dz = p1.z - p2.z
    len += Math.sqrt(dx * dx + dz * dz)
  }
  return len
}

// 纯文本 (TXT 格式) 导出
const exportTXTReport = () => {
  let txt = `====================================================\n`
  txt += `三维重建模型与空间量测报告\n`
  txt += `报告编号: ${reportId.value || `REP-${Date.now()}`}\n`
  txt += `生成时间: ${reportGenerateTime.value || new Date().toLocaleString()}\n`
  txt += `事故车辆模型: ${getModelName(props.modelUrl)}\n`
  txt += `${captureImageTypeLabel.value}: ${captureImageSummary.value}\n`
  if (isSyntheticCapture.value && showSyntheticCaptureNote.value) txt += `影像性质: 三维模型渲染的仿真机位，不是真实采集影像，不作为独立精度验证数据。\n`
  if (qualityReportMetrics.value.length) {
    txt += `\n【建模处理指标与网格内测量】\n`
    if (qualityReportShowSource.value) txt += `来源: ${props.modelMetadata.qualityReport.source}\n`
    if (props.modelMetadata.qualityReport.reportFileUrl) txt += `原始处理报告: 已从所选数据集中关联，可在页面报告中打开。\n`
    qualityReportMetrics.value.forEach(metric => {
      const scope = qualityReportShowScopes.value && metric.scope ? `（${metric.scope}）` : ''
      txt += `${metric.label}: ${formatQualityMetric(metric)}${scope}\n`
    })
    if (qualityReportShowCaveat.value) txt += `口径说明: ${qualityReportCaveat.value}\n`
  }
  txt += `网格规模: ${formatInteger(props.modelMetadata.vertices || 0)} 顶点 / ${formatInteger(props.modelMetadata.faces || 0)} 面\n`
  txt += `坐标与尺度: ${scaleDescription.value}；量测单位 ${coordinateUnit.value}；尺度来源 ${scaleSourceDescription.value}\n`
  txt += `====================================================\n\n`
  txt += `【测量数据明细列表】\n`

  if (measurements.value.length === 0) {
    txt += `暂无三维测量项数据。\n`
  } else {
    measurements.value.forEach((m, idx) => {
      const typeLabel = m.type === 'point' ? '点坐标' : m.type === 'line' ? '直线距离' : '地面投影面积'
      txt += `测量项${idx + 1}: ${m.name} (${typeLabel}) - ${m.valueStr}\n`
      txt += `   参考对比: ${getMeasurementComparisonSummary(m)}\n`
      m.points.forEach((p, pIdx) => {
        txt += `   P${pIdx + 1}: X=${p.x.toFixed(2)}, Y=${p.y.toFixed(2)}, Z=${p.z.toFixed(2)} ${coordinateUnit.value}\n`
      })
    })
  }

  txt += `\n【空间量测汇总】\n`
  txt += `最大记录距离: ${formatDistance(getMaxMeasuredDistance())}\n`
  txt += `累计水平投影面积: ${formatArea(getTotalProjectionArea(), 2)}\n`
  txt += `数值显示分辨率: ${measurementReadout.value}\n`
  txt += `实测准确度: 待验证（需要独立检查点或参考扫描）。\n`

  const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `LKYW_3D_Measurement_Report_${Date.now()}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

// Markdown (MD 格式) 导出
const exportMDReport = () => {
  let md = `# 三维重建模型与空间量测报告\n\n`
  md += `- **报告编号**: ${reportId.value || `REP-${Date.now()}`}\n`
  md += `- **生成时间**: ${reportGenerateTime.value || new Date().toLocaleString()}\n`
  md += `- **事故车辆模型**: ${getModelName(props.modelUrl)}\n`
  md += `- **${captureImageTypeLabel.value}**: ${captureImageSummary.value}\n`
  if (isSyntheticCapture.value && showSyntheticCaptureNote.value) md += `- **影像性质**: 三维模型渲染的仿真机位，不是真实采集影像，不作为独立精度验证数据。\n`
  md += '\n'

  md += `## 一、模型数据与精度依据\n\n`
  md += `| 项目 | 当前数据 | 说明 |\n| :--- | :--- | :--- |\n`
  md += `| ${captureImageTypeLabel.value} | ${formatInteger(props.modelMetadata.datasetCounts?.total || 0)} 张 | ${captureImageSummary.value} |\n`
  md += `| 网格规模 | ${formatInteger(props.modelMetadata.vertices || 0)} 顶点 / ${formatInteger(props.modelMetadata.faces || 0)} 面 | 表面显示：${surfaceAppearance.value}；不等同于精度 |\n`
  md += `| 坐标与尺度 | ${scaleDescription.value} | 量测单位：${coordinateUnit.value}；来源：${scaleSourceDescription.value} |\n`
  md += `| 数值显示分辨率 | ${measurementReadout.value} | 仅指读数显示位数，不代表实际误差 |\n`
  md += `| 实测准确度 | 待验证 | 缺少独立检查点或参考扫描，绝对位置 RMSE/完整率未计算；重投影 RMS 为软件内部指标 |\n\n`

  if (qualityReportMetrics.value.length) {
    md += `### 建模处理指标与网格内测量\n\n`
    if (qualityReportShowSource.value) md += `来源：${props.modelMetadata.qualityReport.source}\n\n`
    if (props.modelMetadata.qualityReport.reportFileUrl) md += `原始处理报告：已从所选数据集中关联，可在页面报告中打开。\n\n`
    md += qualityReportShowScopes.value
      ? `| 指标 | 报告值 | 来源与口径 |\n| :--- | :--- | :--- |\n`
      : `| 指标 | 报告值 |\n| :--- | :--- |\n`
    qualityReportMetrics.value.forEach(metric => {
      md += qualityReportShowScopes.value
        ? `| ${metric.label} | ${formatQualityMetric(metric)} | ${metric.scope} |\n`
        : `| ${metric.label} | ${formatQualityMetric(metric)} |\n`
    })
    if (qualityReportShowCaveat.value) md += `\n${qualityReportCaveat.value}\n\n`
  }

  md += `## 二、空间量测汇总\n\n`
  md += `| 项目 | 当前数值 | 来源 |\n| :--- | :--- | :--- |\n`
  md += `| 最大记录距离 | ${formatDistance(getMaxMeasuredDistance())} | 本次空间量测 |\n`
  md += `| 累计水平投影面积 | ${formatArea(getTotalProjectionArea(), 2)} | 本次空间量测 |\n\n`

  md += `## 三、空间量测明细\n\n`
  md += `| 序号 | 测量类型 | 测量项名称 | 测量数值 / 维度 | 场景局部坐标 (${coordinateUnit.value}) | 参考校核状态 |\n`
  md += `| :--- | :--- | :--- | :--- | :--- | :--- |\n`

  if (measurements.value.length === 0) {
    md += `| - | - | 暂无三维测量项 | - | - | - |\n`
  } else {
    measurements.value.forEach((m, idx) => {
      const typeLabel = m.type === 'point' ? '点坐标' : m.type === 'line' ? '直线距离' : '地面投影面积'
      const coords = m.points.map((p, pIdx) => `P${pIdx + 1}: (${p.x.toFixed(2)}, ${p.y.toFixed(2)}, ${p.z.toFixed(2)})`).join('<br>')
      const remark = getMeasurementComparisonSummary(m)

      md += `| ${idx + 1} | ${typeLabel} | **${m.name}** | ${m.valueStr} | ${coords} | ${remark} |\n`
    })
  }

  if (showReportPrecisionNote.value) {
    md += `\n## 四、精度口径\n\n`
    md += `${measurementAccuracyNote.value} 网格规模是模型数据量，不是重建精度。Metashape 重投影和坐标精度结果作为软件内部处理指标列出；独立检查点/参考扫描不足，因此不作为全局实际误差或结构安全等级。\n`
  }

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `LKYW_3D_Measurement_Report_${Date.now()}.md`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

// 导出 CSV
const exportCSVData = () => {
  let csvContent = `data:text/csv;charset=utf-8,序号,类型,测量项名称,测量数值,参考值与偏差,X(${coordinateUnit.value}),Y(${coordinateUnit.value}),Z(${coordinateUnit.value}),数值显示分辨率,实测准确度,来源与口径\n`
  const csvCell = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`
  measurements.value.forEach((m, idx) => {
    const firstP = m.points[0] || { x: 0, y: 0, z: 0 }
    const row = [idx + 1, m.type, m.name, m.valueStr, getMeasurementComparisonSummary(m), firstP.x.toFixed(2), firstP.y.toFixed(2), firstP.z.toFixed(2), measurementReadout.value, '待验证', '本次空间量测']
    csvContent += `${row.map(csvCell).join(',')}\n`
  })
  qualityReportMetrics.value.forEach(metric => {
    const recordType = metric.id === 'meshlab-scale-m0' ? '换算系数' : '处理指标'
    const reportAttachmentNote = props.modelMetadata.qualityReport.reportFileUrl ? '；已关联原始处理报告 PDF' : ''
    const source = qualityReportShowSource.value ? props.modelMetadata.qualityReport.source : ''
    const sourceAndScope = [source, qualityReportShowScopes.value ? metric.scope : ''].filter(Boolean).join('；')
    const row = ['', recordType, metric.label, formatQualityMetric(metric), '', '', '', '', '', '待验证', `${sourceAndScope}${reportAttachmentNote}`]
    csvContent += `${row.map(csvCell).join(',')}\n`
  })
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `LKYW_3D_Measurement_Report_${Date.now()}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 打印报告
const printReport = () => {
  window.print()
}

// 聚焦到指定测量项
const focusOnMeasurement = (item) => {
  if (!item || !item.rawMidPoint || !camera || !controls) return
  animateCameraTo(
    new THREE.Vector3(item.rawMidPoint.x + 3, item.rawMidPoint.y + 2, item.rawMidPoint.z + 3),
    item.rawMidPoint
  )
}

// 初始化 Three.js 场景
const initThreeScene = () => {
  if (!threeCanvasRef.value) return

  const width = canvasContainerRef.value.clientWidth || 800
  const height = canvasContainerRef.value.clientHeight || 600

  // 1. Scene
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0e172a)
  scene.fog = new THREE.FogExp2(0x0e172a, 0.003)

  measurementGroup = new THREE.Group()
  scene.add(measurementGroup)

  previewGroup = new THREE.Group()
  scene.add(previewGroup)

  // 2. Camera
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
  camera.position.set(12, 10, 15)

  // 3. Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 0.75

  threeCanvasRef.value.innerHTML = ''
  threeCanvasRef.value.appendChild(renderer.domElement)

  // 4. OrbitControls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.autoRotate = autoRotate.value
  controls.autoRotateSpeed = 1.5
  controls.maxPolarAngle = Math.PI / 2 + 0.05

  setupLighting()
  setupEnvironment()

  window.addEventListener('resize', handleWindowResize)
  animate()
}

const setupLighting = () => {
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.35)
  scene.add(ambientLight)

  const keyLight = new THREE.DirectionalLight(0xffffff, 1.1)
  keyLight.position.set(25, 45, 25)
  keyLight.castShadow = true
  scene.add(keyLight)

  const fillLight = new THREE.DirectionalLight(0xe0f2fe, 0.24)
  fillLight.position.set(-25, 25, -25)
  scene.add(fillLight)

  const backLight = new THREE.DirectionalLight(0x38bdf8, 0.1)
  backLight.position.set(0, 35, -35)
  scene.add(backLight)

  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 0.25)
  scene.add(hemiLight)
}

const setupEnvironment = () => {
  if (renderer && scene) {
    const pmremGenerator = new THREE.PMREMGenerator(renderer)
    const roomEnv = new RoomEnvironment(renderer)
    scene.environment = pmremGenerator.fromScene(roomEnv).texture
  }

  const gridHelper = new THREE.GridHelper(60, 60, 0x38bdf8, 0x334155)
  gridHelper.position.y = -0.01
  scene.add(gridHelper)
}

const enhanceMaterialLuminance = (mat) => {
  if (!mat) return
  const materials = Array.isArray(mat) ? mat : [mat]
  materials.forEach(m => {
    if (m.color) {
      const hsl = {}
      m.color.getHSL(hsl)
      if (hsl.l < 0.4) {
        m.color.setHex(0x5a6d82)
      }
    }
    if (m.emissive) {
      m.emissive.setHex(0x283648)
      m.emissiveIntensity = 0.5
    }
    if (m.metalness !== undefined) m.metalness = 0.05
    if (m.roughness !== undefined) m.roughness = 0.6
    m.needsUpdate = true
  })
}

// 【步骤五核心】：3D 画布点击射线拾取与精确测距 (Raycasting + Scale Factor)
const handleCanvasClick = (event) => {
  if (measureMode.value === 'none' || !threeCanvasRef.value || !currentModelGroup || !camera) return

  const rect = threeCanvasRef.value.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, camera)
  const intersects = raycaster.intersectObject(currentModelGroup, true)

  if (intersects.length > 0) {
    const hitPoint = intersects[0].point.clone()

    if (measureMode.value === 'point') {
      const realP = new THREE.Vector3(
        hitPoint.x * modelScaleFactor.value,
        hitPoint.y * modelScaleFactor.value,
        hitPoint.z * modelScaleFactor.value
      )

      queueMeasurement({
        id: Date.now(),
        type: 'point',
        name: '',
        valueStr: `(${realP.x.toFixed(2)}, ${realP.y.toFixed(2)}, ${realP.z.toFixed(2)}) ${coordinateUnit.value}`,
        unit: coordinateUnit.value,
        points: [realP],
        rawPoints: [hitPoint],
        rawMidPoint: hitPoint.clone(),
        midPoint: hitPoint.clone(),
        screenX: 0,
        screenY: 0,
        visible: true
      })

    } else if (measureMode.value === 'line') {
      if (pendingPoints.value.length === 0) {
        pendingPoints.value.push(hitPoint)
        rebuildPreviewGeometries()
      } else {
        const p1 = pendingPoints.value[0]
        const p2 = hitPoint
        const rawDist = p1.distanceTo(p2)
        const realDist = rawDist * modelScaleFactor.value
        const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5)

        const realP1 = new THREE.Vector3(p1.x * modelScaleFactor.value, p1.y * modelScaleFactor.value, p1.z * modelScaleFactor.value)
        const realP2 = new THREE.Vector3(p2.x * modelScaleFactor.value, p2.y * modelScaleFactor.value, p2.z * modelScaleFactor.value)

        queueMeasurement({
          id: Date.now(),
          type: 'line',
          name: '',
          valueStr: formatDistance(realDist),
          unit: coordinateUnit.value,
          distance: realDist,
          dx: Math.abs(p1.x - p2.x) * modelScaleFactor.value,
          dy: Math.abs(p1.y - p2.y) * modelScaleFactor.value,
          dz: Math.abs(p1.z - p2.z) * modelScaleFactor.value,
          points: [realP1, realP2],
          rawPoints: [p1, p2],
          rawMidPoint: mid.clone(),
          midPoint: mid.clone(),
          screenX: 0,
          screenY: 0,
          visible: true
        })

      }

    } else if (measureMode.value === 'area') {
      pendingPoints.value.push(hitPoint)
      rebuildPreviewGeometries()
    }
  }
}

// 完成多边形闭合与【水平地面正交投影面积】计算 (Shoelace Formula)
const finishPolygonArea = () => {
  if (pendingPoints.value.length < 3) return
  const rawPts = [...pendingPoints.value]
  const realArea = calculateGroundProjectionArea(rawPts)

  const centroid = new THREE.Vector3(0, 0, 0)
  rawPts.forEach(p => centroid.add(p))
  centroid.divideScalar(rawPts.length)

  const realPts = rawPts.map(p => new THREE.Vector3(p.x * modelScaleFactor.value, p.y * modelScaleFactor.value, p.z * modelScaleFactor.value))

  queueMeasurement({
    id: Date.now(),
    type: 'area',
    name: '',
    valueStr: formatArea(realArea),
    unit: areaUnit.value,
    area: realArea,
    points: realPts,
    rawPoints: rawPts,
    rawMidPoint: centroid.clone(),
    midPoint: centroid.clone(),
    screenX: 0,
    screenY: 0,
    visible: true
  })
}

// 核心公式：【水平地面正交投影面积】算法 (鞋带公式 / Shoelace Formula on XZ-Plane)
const calculateGroundProjectionArea = (pts) => {
  if (!pts || pts.length < 3) return 0
  const n = pts.length
  let sum = 0
  for (let i = 0; i < n; i++) {
    const p1 = pts[i]
    const p2 = pts[(i + 1) % n]
    // 忽略 Y 轴高度，在 X-Z 水平地面平面上计算鞋带公式 (x1*z2 - x2*z1)
    sum += (p1.x * p2.z) - (p2.x * p1.z)
  }
  const rawGroundArea = 0.5 * Math.abs(sum)
  return rawGroundArea * Math.pow(modelScaleFactor.value, 2)
}

// 预览当前正在选点的半成品几何图元
const rebuildPreviewGeometries = () => {
  if (!previewGroup) return
  while (previewGroup.children.length > 0) {
    const child = previewGroup.children[0]
    if (child.geometry) child.geometry.dispose()
    if (child.material) {
      if (Array.isArray(child.material)) child.material.forEach(m => m.dispose())
      else child.material.dispose()
    }
    previewGroup.remove(child)
  }

  pendingPoints.value.forEach(p => {
    createPointMarker(previewGroup, p, 0xfbbf24, 0.14)
  })

  if (pendingPoints.value.length >= 2) {
    const lineGeo = new THREE.BufferGeometry().setFromPoints(pendingPoints.value)
    const lineMat = new THREE.LineBasicMaterial({
      color: 0xfbbf24,
      linewidth: 2,
      depthTest: false,
      transparent: true,
      opacity: 0.9
    })
    const lineMesh = new THREE.Line(lineGeo, lineMat)
    lineMesh.renderOrder = 9999
    previewGroup.add(lineMesh)
  }
}

// 重构场景中所有确定的 3D 测量几何体 (包含水平地面正交投影高亮膜与垂线)
const rebuildAllMeasurementGeometries = () => {
  if (!measurementGroup) return
  while (measurementGroup.children.length > 0) {
    const child = measurementGroup.children[0]
    if (child.geometry) child.geometry.dispose()
    if (child.material) {
      if (Array.isArray(child.material)) child.material.forEach(m => m.dispose())
      else child.material.dispose()
    }
    measurementGroup.remove(child)
  }

  measurements.value.forEach(m => {
    const rawPts = m.rawPoints || m.points
    if (m.type === 'point') {
      createPointMarker(measurementGroup, rawPts[0], 0x00f2fe, 0.16)

    } else if (m.type === 'line') {
      const p1 = rawPts[0]
      const p2 = rawPts[1]
      createPointMarker(measurementGroup, p1, 0x00f2fe, 0.14)
      createPointMarker(measurementGroup, p2, 0xfbbf24, 0.14)
      createLaserCylinderMesh(measurementGroup, p1, p2)

    } else if (m.type === 'area') {
      rawPts.forEach(p => {
        createPointMarker(measurementGroup, p, 0x34d399, 0.12)
      })
      // 渲染地面正交投影高亮膜 + 3D 选点垂直向下投影至地面的黄色激光虚线
      renderGroundOrthographicProjectionOverlay(measurementGroup, rawPts)
    }
  })
}

// 绘制点坐标 Marker
const createPointMarker = (targetGroup, pos, colorHex, radius = 0.15) => {
  const geo = new THREE.SphereGeometry(radius, 24, 24)
  const mat = new THREE.MeshBasicMaterial({
    color: colorHex,
    depthTest: false,
    depthWrite: false,
    transparent: true,
    opacity: 0.95
  })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.position.copy(pos)
  mesh.renderOrder = 9999
  targetGroup.add(mesh)
}

// 绘制 3D 激光测距圆柱
const createLaserCylinderMesh = (targetGroup, p1, p2) => {
  const distance = p1.distanceTo(p2)
  if (distance < 0.001) return

  const radius = 0.035
  const geometry = new THREE.CylinderGeometry(radius, radius, distance, 12)
  const material = new THREE.MeshBasicMaterial({
    color: 0x00f2fe,
    depthTest: false,
    depthWrite: false,
    transparent: true,
    opacity: 0.92
  })

  const cylinderMesh = new THREE.Mesh(geometry, material)
  cylinderMesh.renderOrder = 9999

  const midPoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5)
  cylinderMesh.position.copy(midPoint)

  const up = new THREE.Vector3(0, 1, 0)
  const direction = new THREE.Vector3().subVectors(p2, p1).normalize()
  const quaternion = new THREE.Quaternion()
  quaternion.setFromUnitVectors(up, direction)
  cylinderMesh.quaternion.copy(quaternion)

  targetGroup.add(cylinderMesh)

  const lineGeo = new THREE.BufferGeometry().setFromPoints([p1, p2])
  const lineMat = new THREE.LineBasicMaterial({
    color: 0xffffff,
    depthTest: false,
    depthWrite: false,
    transparent: true,
    opacity: 0.9
  })
  const lineMesh = new THREE.Line(lineGeo, lineMat)
  lineMesh.renderOrder = 9999
  targetGroup.add(lineMesh)
}

// 绘制【水平地面正交投影】高亮平罩与垂直引导线
const renderGroundOrthographicProjectionOverlay = (targetGroup, pts) => {
  if (!pts || pts.length < 3) return
  const n = pts.length

  // 1. 将 3D 顶点垂直下投影到 Y = 0.02 地面平面上
  const groundPts = pts.map(p => new THREE.Vector3(p.x, 0.02, p.z))

  // 2. 在地面平面生成 2D 投影多边形
  const shape2DPoints = groundPts.map(p => new THREE.Vector2(p.x, p.z))
  let faces = []
  try {
    faces = THREE.ShapeUtils.triangulateShape(shape2DPoints, [])
  } catch (err) {
    for (let i = 1; i < n - 1; i++) faces.push([0, i, i + 1])
  }

  const positions = []
  groundPts.forEach(p => positions.push(p.x, 0.02, p.z))
  const indices = []
  faces.forEach(f => indices.push(f[0], f[1], f[2]))

  const groundGeom = new THREE.BufferGeometry()
  groundGeom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  groundGeom.setIndex(indices)
  groundGeom.computeVertexNormals()

  // 渲染地面青色投影阴影高亮膜
  const groundMat = new THREE.MeshBasicMaterial({
    color: 0x00f2fe,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.45,
    depthTest: false,
    depthWrite: false
  })
  const groundMesh = new THREE.Mesh(groundGeom, groundMat)
  groundMesh.renderOrder = 9999
  targetGroup.add(groundMesh)

  // 3. 在地面绘制影子边缘闭合黄色连线
  const groundLinePts = [...groundPts, groundPts[0]]
  const groundLineGeom = new THREE.BufferGeometry().setFromPoints(groundLinePts)
  const groundLineMat = new THREE.LineBasicMaterial({
    color: 0x34d399,
    linewidth: 2,
    depthTest: false,
    transparent: true,
    opacity: 0.95
  })
  const groundLineLoop = new THREE.Line(groundLineGeom, groundLineMat)
  groundLineLoop.renderOrder = 9999
  targetGroup.add(groundLineLoop)

  // 4. 绘制从车身 3D 选点 $P_i(x, y, z)$ 垂直向下照射到地面 $(x, 0.02, z)$ 的发光投影垂直虚线
  for (let i = 0; i < n; i++) {
    const topP = pts[i]
    const botP = groundPts[i]

    const dropLineGeom = new THREE.BufferGeometry().setFromPoints([topP, botP])
    const dropLineMat = new THREE.LineDashedMaterial({
      color: 0xfbbf24,
      dashSize: 0.2,
      gapSize: 0.1,
      transparent: true,
      opacity: 0.85
    })
    const dropLine = new THREE.Line(dropLineGeom, dropLineMat)
    dropLine.computeLineDistances()
    dropLine.renderOrder = 9999
    targetGroup.add(dropLine)

    // 地面投影落点 Marker
    createPointMarker(targetGroup, botP, 0x34d399, 0.1)
  }

  // 5. 同时保留车身 3D 选点之间的闭合多边形框架
  const topLinePts = [...pts, pts[0]]
  const topLineGeom = new THREE.BufferGeometry().setFromPoints(topLinePts)
  const topLineMat = new THREE.LineBasicMaterial({
    color: 0xfbbf24,
    linewidth: 2,
    depthTest: false,
    transparent: true,
    opacity: 0.9
  })
  const topLineLoop = new THREE.Line(topLineGeom, topLineMat)
  topLineLoop.renderOrder = 9999
  targetGroup.add(topLineLoop)
}

const disposeModelGroup = (group) => {
  if (!group) return
  const geometries = new Set()
  const materials = new Set()
  const textures = new Set()

  group.traverse((child) => {
    if (child.geometry) geometries.add(child.geometry)
    const childMaterials = Array.isArray(child.material) ? child.material : [child.material]
    childMaterials.filter(Boolean).forEach((material) => {
      materials.add(material)
      Object.values(material).forEach((value) => {
        if (value && value.isTexture) textures.add(value)
      })
    })
  })

  geometries.forEach((geometry) => geometry.dispose())
  textures.forEach((texture) => texture.dispose())
  materials.forEach((material) => material.dispose())
}

// 直接读取项目中的 PLY 重建成果，并用 XHR 进度反馈实际文件读取进度。
const loadModel = (url) => {
  const requestId = ++modelLoadId
  if (!url || !scene) return

  isLoading.value = true
  loadError.value = ''
  loadProgress.value = 0
  clearMeasurements()

  if (currentModelGroup) {
    scene.remove(currentModelGroup)
    disposeModelGroup(currentModelGroup)
    currentModelGroup = null
  }

  const loader = new PLYLoader()
  loader.load(
    url,
    (geometry) => {
      if (requestId !== modelLoadId) {
        geometry.dispose()
        return
      }

      const position = geometry.getAttribute('position')
      if (!position || position.count === 0) {
        geometry.dispose()
        isLoading.value = false
        loadError.value = '场景数据暂时无法读取，请检查资源配置。'
        return
      }

      if (props.modelMetadata.upAxis === 'z') {
        geometry.computeBoundingBox()
        const sourceBounds = geometry.boundingBox
        const sourceCenter = sourceBounds.getCenter(new THREE.Vector3())
        geometry.translate(-sourceCenter.x, -sourceCenter.y, -sourceBounds.min.z)
      } else {
        geometry.computeBoundingBox()
        const sourceBounds = geometry.boundingBox
        const sourceCenter = sourceBounds.getCenter(new THREE.Vector3())
        geometry.translate(-sourceCenter.x, -sourceBounds.min.y, -sourceCenter.z)
      }

      if (!geometry.getAttribute('normal')) geometry.computeVertexNormals()

      const hasUv = Boolean(geometry.getAttribute('uv'))
      const useTexture = Boolean(props.modelMetadata.textureUrl && hasUv)
      const hasVertexColors = Boolean(geometry.getAttribute('color'))
      const vertexColors = hasVertexColors && !useTexture
      const material = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        vertexColors,
        roughness: 0.86,
        metalness: 0.02,
        envMapIntensity: 0.2,
        side: THREE.DoubleSide,
        wireframe: isWireframe.value
      })
      if (useTexture) {
        new THREE.TextureLoader().load(
          props.modelMetadata.textureUrl,
          (texture) => {
            if (requestId !== modelLoadId) {
              texture.dispose()
              return
            }
            texture.colorSpace = THREE.SRGBColorSpace
            texture.anisotropy = renderer.capabilities.getMaxAnisotropy()
            texture.minFilter = THREE.LinearMipmapLinearFilter
            texture.magFilter = THREE.LinearFilter
            material.color.setScalar(0.92)
            material.map = texture
            material.needsUpdate = true
          },
          undefined,
          (error) => {
            console.warn('[Three.js] PLY 材质纹理读取失败。', error)
            if (hasVertexColors) {
              material.color.set(0xffffff)
              material.vertexColors = true
              material.needsUpdate = true
            }
          }
        )
      }
      const mesh = new THREE.Mesh(geometry, material)
      mesh.castShadow = true
      mesh.receiveShadow = true

      currentModelGroup = new THREE.Group()
      currentModelGroup.name = props.modelName
      if (props.modelMetadata.upAxis === 'z') currentModelGroup.rotation.x = -Math.PI / 2
      currentModelGroup.add(mesh)
      scene.add(currentModelGroup)

      fitCameraToModel(currentModelGroup)
      loadProgress.value = 100
      isLoading.value = false
      emit('model-loaded')
      emit('update-step', 4)
    },
    (xhr) => {
      if (requestId !== modelLoadId) return
      if (xhr.total > 0) {
        loadProgress.value = Math.min(96, Math.round((xhr.loaded / xhr.total) * 96))
      } else {
        loadProgress.value = Math.min(90, loadProgress.value + 5)
      }
    },
    (error) => {
      if (requestId !== modelLoadId) return
      console.error('[Three.js] PLY 模型读取失败:', error)
      isLoading.value = false
      loadError.value = '场景数据读取失败，请重试或联系管理员检查资源配置。'
    }
  )
}

// 自动检测模型包围盒并自动归一化物理单位校准比例 (Model Physical Scale Calibration)
const fitCameraToModel = (modelObj) => {
  if (!modelObj || !camera || !controls) return

  const box = new THREE.Box3().setFromObject(modelObj)
  box.getCenter(boundingBoxCenter)
  box.getSize(boundingBoxSize)

  const sphere = new THREE.Sphere()
  box.getBoundingSphere(sphere)
  boundingSphereRadius = sphere.radius || 5

  recalibrateScale()

  const fov = camera.fov * (Math.PI / 180)
  const maxDim = Math.max(boundingBoxSize.x, boundingBoxSize.y, boundingBoxSize.z)
  const aspect = camera.aspect || 1
  let distance = Math.max(
    maxDim / (2 * Math.tan(fov / 2)),
    maxDim / (2 * Math.tan(fov / 2) * aspect)
  )

  distance *= 0.92
  const viewTarget = boundingBoxCenter.clone()
  viewTarget.y -= Math.max(maxDim * 0.08, 0.1)
  controls.target.copy(viewTarget)

  const targetCamPos = new THREE.Vector3(
    viewTarget.x + distance * 0.7,
    viewTarget.y + distance * 0.5,
    viewTarget.z + distance * 0.9
  )

  animateCameraTo(targetCamPos, viewTarget)
}

const animateCameraTo = (targetPos, targetLookAt) => {
  const startPos = camera.position.clone()
  const startTarget = controls.target.clone()
  const duration = 1000
  const startTime = Date.now()

  const step = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    const ease = 1 - Math.pow(1 - progress, 3)

    camera.position.lerpVectors(startPos, targetPos, ease)
    controls.target.lerpVectors(startTarget, targetLookAt, ease)
    controls.update()

    if (progress < 1) {
      requestAnimationFrame(step)
    }
  }
  step()
}

const focusCameraToScreen = () => {
  if (currentModelGroup) {
    fitCameraToModel(currentModelGroup)
  }
}

const toggleAutoRotate = () => {
  autoRotate.value = !autoRotate.value
  if (controls) controls.autoRotate = autoRotate.value
}

const togglePlayAnimation = () => {
  isPlayAnimation.value = !isPlayAnimation.value
}

const toggleWireframe = () => {
  isWireframe.value = !isWireframe.value
  if (currentModelGroup) {
    currentModelGroup.traverse((child) => {
      if (child.isMesh && child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.wireframe = isWireframe.value)
        } else {
          child.material.wireframe = isWireframe.value
        }
      }
    })
  }
}

// 屏幕坐标投影更新
const updateTagAndHUDPositions = () => {
  if (!camera || !renderer || !canvasContainerRef.value || isLoading.value) return
  const width = canvasContainerRef.value.clientWidth
  const height = canvasContainerRef.value.clientHeight

  // 更新 3D 检测点
  inspectionTags.value.forEach((tag) => {
    const worldPos = tag.pos.clone().add(boundingBoxCenter)
    const projected = worldPos.project(camera)
    if (projected.z < 1.0) {
      const x = (projected.x * 0.5 + 0.5) * width
      const y = (-(projected.y * 0.5) + 0.5) * height
      tag.screenX = Math.round(x)
      tag.screenY = Math.round(y)
      tag.visible = x >= 20 && x <= width - 20 && y >= 20 && y <= height - 20
    } else {
      tag.visible = false
    }
  })

  // 更新测量 HUD 卡片
  measurements.value.forEach((m) => {
    const rawPos = m.rawMidPoint || m.midPoint
    if (!rawPos) return
    const projected = rawPos.clone().project(camera)
    if (projected.z < 1.0) {
      const x = (projected.x * 0.5 + 0.5) * width
      const y = (-(projected.y * 0.5) + 0.5) * height
      m.screenX = Math.round(x)
      m.screenY = Math.round(y)
      m.visible = x >= 20 && x <= width - 20 && y >= 20 && y <= height - 20
    } else {
      m.visible = false
    }
  })
}

// 动画主循环
const animate = () => {
  animationFrameId = requestAnimationFrame(animate)

  const delta = clock.getDelta()
  if (mixer && isPlayAnimation.value) {
    mixer.update(delta)
  }
  if (controls) {
    controls.update()
  }
  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
  updateTagAndHUDPositions()
}

const handleWindowResize = () => {
  if (!canvasContainerRef.value || !camera || !renderer) return
  const width = canvasContainerRef.value.clientWidth
  const height = canvasContainerRef.value.clientHeight
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

onMounted(async () => {
  await nextTick()
  initThreeScene()
  loadModel(props.modelUrl)
})

watch(() => props.modelUrl, (newUrl) => {
  if (newUrl) {
    loadModel(newUrl)
  }
})

onBeforeUnmount(() => {
  modelLoadId += 1
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  window.removeEventListener('resize', handleWindowResize)
  if (currentModelGroup) {
    disposeModelGroup(currentModelGroup)
    currentModelGroup = null
  }
  if (renderer) {
    renderer.dispose()
  }
})
</script>

<style scoped>
.reconstruction-viewer-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #020712;
  position: relative;
  overflow: hidden;
  font-family: 'Inter', -apple-system, sans-serif;
}

/* 顶部工具栏 */
.viewer-top-bar {
  padding: 12px 20px;
  background: rgba(8, 16, 32, 0.88);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  z-index: 10;
}

.model-info-group {
  display: flex;
  align-items: center;
  gap: 16px;
}
.info-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(52, 211, 153, 0.12);
  border: 1px solid rgba(52, 211, 153, 0.3);
  padding: 4px 10px;
  border-radius: 20px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 8px #34d399;
  animation: pulse-dot 1.5s infinite;
}
.info-badge.loading { background: rgba(56, 189, 248, 0.11); border-color: rgba(56, 189, 248, 0.35); }
.info-badge.error { background: rgba(248, 113, 113, 0.12); border-color: rgba(248, 113, 113, 0.32); }
.status-dot.loading { background: #38bdf8; box-shadow: 0 0 8px #38bdf8; }
.status-dot.error { background: #f87171; box-shadow: 0 0 8px #f87171; animation: none; }
.badge-title {
  color: #34d399;
  font-size: 12px;
  font-weight: 600;
}
.badge-title.is-loading { color: #7dd3fc; }
.badge-title.has-error { color: #fca5a5; }

.model-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 12px;
}
.meta-item .lbl { color: #64748b; margin-right: 4px; }
.meta-item .val { color: #e2e8f0; font-family: 'Fira Code', monospace; }
.meta-item .text-cyan { color: #00f2fe; }
.meta-item .text-green { color: #34d399; }
.meta-item .text-yellow { color: #fbbf24; }

.scale-indicator { display: inline-flex; align-items: center; padding: 3px 7px; border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 5px; font-size: 10.5px; white-space: nowrap; }

.viewer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tool-btn {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}
.tool-btn:hover {
  background: rgba(30, 41, 59, 1);
  border-color: #00f2fe;
  color: #00f2fe;
}
.tool-btn.active {
  background: rgba(0, 242, 254, 0.18);
  border-color: #00f2fe;
  color: #00f2fe;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.35);
}
.tool-btn.report-btn {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.2), rgba(52, 211, 153, 0.2));
  border-color: #00f2fe;
  color: #00f2fe;
  font-weight: 600;
}
.tool-btn.report-btn:hover {
  background: #00f2fe;
  color: #020712;
  box-shadow: 0 0 14px rgba(0, 242, 254, 0.5);
}
.tool-btn.primary-fit {
  background: rgba(0, 242, 254, 0.18);
  border-color: #00f2fe;
  color: #00f2fe;
  font-weight: 600;
}
.tool-btn.primary-fit:hover {
  background: #00f2fe;
  color: #020712;
  box-shadow: 0 0 14px rgba(0, 242, 254, 0.6);
}
.tool-btn.danger-btn:hover {
  border-color: #f87171;
  color: #f87171;
  background: rgba(248, 113, 113, 0.15);
}

/* 3D 渲染区域与悬浮工具栏 */
.canvas-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.canvas-3d {
  width: 100%;
  height: 100%;
  cursor: grab;
}
.canvas-3d:active {
  cursor: grabbing;
}
.canvas-3d.cursor-crosshair {
  cursor: crosshair !important;
}

/* 【步骤五】：3D 画布悬浮测量工具栏 UI */
.floating-measure-toolbar {
  position: absolute;
  top: 16px;
  left: 20px;
  background: rgba(8, 16, 32, 0.92);
  border: 1px solid rgba(0, 242, 254, 0.35);
  border-radius: 10px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 18px rgba(0, 242, 254, 0.15);
  backdrop-filter: blur(12px);
  z-index: 15;
}
.toolbar-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #00f2fe;
  font-size: 13px;
  white-space: nowrap;
}
.pulse-icon {
  animation: pulse-dot 1.5s infinite;
}

.tool-mode-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mode-btn {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid #334155;
  color: #cbd5e1;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12.5px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.25s ease;
}
.mode-btn:hover {
  border-color: #00f2fe;
  color: #00f2fe;
}
.mode-btn.active {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.25), rgba(59, 130, 246, 0.25));
  border-color: #00f2fe;
  color: #00f2fe;
  font-weight: 600;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.4);
}

.tool-divider {
  width: 1px;
  height: 24px;
  background: rgba(255, 255, 255, 0.15);
}

.tool-action-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.action-sub-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid #475569;
  color: #cbd5e1;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.action-sub-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}
.action-sub-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.action-sub-btn.success-btn {
  background: rgba(52, 211, 153, 0.2);
  border-color: #34d399;
  color: #34d399;
  font-weight: 600;
}
.action-sub-btn.success-btn:hover {
  background: #34d399;
  color: #020712;
}
.action-sub-btn.danger-btn:hover:not(:disabled) {
  border-color: #f87171;
  color: #f87171;
}

/* 测量状态提示 */
.measure-status-hint {
  position: absolute;
  top: 72px;
  left: 20px;
  background: rgba(10, 20, 40, 0.9);
  border: 1px solid #fbbf24;
  padding: 6px 14px;
  border-radius: 20px;
  color: #fbbf24;
  font-size: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  z-index: 14;
}

/* 加载遮罩 */
.loading-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(2, 7, 18, 0.85);
  backdrop-filter: blur(6px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 20;
}
.spinner-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 320px;
}
.cyber-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(0, 242, 254, 0.15);
  border-top-color: #00f2fe;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}
.loading-text {
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 12px;
}
.loading-bar-bg {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}
.loading-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00f2fe, #3b82f6);
  transition: width 0.2s ease;
}
.progress-num {
  color: #00f2fe;
  font-family: 'Fira Code', monospace;
  font-weight: 700;
  font-size: 14px;
}

.load-error-overlay {
  position: absolute;
  inset: 0;
  z-index: 21;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(2, 7, 18, 0.88);
  backdrop-filter: blur(6px);
}

.load-error-card {
  width: min(460px, 100%);
  padding: 22px;
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.97);
  text-align: center;
}

.load-error-card strong { color: #fecaca; font-size: 15px; }
.load-error-card p { margin: 10px 0 16px; color: #a9bac8; font-size: 12px; line-height: 1.6; }
.load-error-card button { padding: 8px 13px; border: 1px solid rgba(248, 113, 113, 0.45); border-radius: 6px; background: rgba(127, 29, 29, 0.24); color: #fecaca; cursor: pointer; }
.load-error-card button:hover { background: rgba(127, 29, 29, 0.46); }

/* 标注与测量结果 HUD 卡片 */
.inspection-tags-layer {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: none;
  z-index: 5;
}
.inspection-tag-card {
  position: absolute;
  transform: translate(-50%, -100%) translateY(-12px);
  background: rgba(8, 16, 32, 0.88);
  border: 1px solid rgba(0, 242, 254, 0.4);
  border-radius: 6px;
  padding: 6px 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: auto;
}
.inspection-tag-card.visible { opacity: 1; }
.tag-header { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.tag-dot { width: 6px; height: 6px; border-radius: 50%; background: #fbbf24; }
.tag-name { color: #94a3b8; font-size: 11px; }
.tag-val { color: #00f2fe; font-size: 12px; font-weight: 700; font-family: 'Fira Code', monospace; }

/* 3D 动态测量 HUD 卡片 */
.measurement-hud-card {
  position: absolute;
  transform: translate(-50%, -100%) translateY(-15px);
  background: rgba(4, 16, 36, 0.94);
  border: 1px solid #00f2fe;
  border-radius: 8px;
  padding: 8px 12px;
  box-shadow: 0 6px 20px rgba(0, 242, 254, 0.3);
  backdrop-filter: blur(10px);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: auto;
  min-width: 180px;
}
.measurement-hud-card.visible { opacity: 1; }
.measurement-hud-card.hud-type-area { border-color: #34d399; box-shadow: 0 6px 20px rgba(52, 211, 153, 0.3); }
.measurement-hud-card.hud-type-point { border-color: #fbbf24; box-shadow: 0 6px 20px rgba(251, 191, 36, 0.3); }

.hud-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 4px;
  margin-bottom: 4px;
}
.hud-icon { font-size: 13px; }
.hud-title { color: #e2e8f0; font-size: 12px; }
.hud-title strong { color: #00f2fe; font-family: 'Fira Code', monospace; font-size: 13px; }
.hud-delete-btn { background: transparent; border: none; color: #64748b; cursor: pointer; font-size: 12px; }
.hud-delete-btn:hover { color: #f87171; }

.hud-body { display: flex; flex-direction: column; gap: 2px; font-size: 11px; }
.hud-detail { color: #fbbf24; }
.hud-detail strong { font-family: 'Fira Code', monospace; }
.hud-vector { color: #94a3b8; font-family: 'Fira Code', monospace; font-size: 10.5px; }

/* 测量记录抽屉面板 (Measurement Drawer) */
.measurement-drawer-panel {
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 320px;
  background: rgba(8, 16, 32, 0.95);
  border-left: 1px solid rgba(0, 242, 254, 0.3);
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  z-index: 18;
}
.drawer-header {
  padding: 14px 18px;
  background: rgba(16, 24, 40, 0.9);
  border-bottom: 1px solid #1e293b;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #f8fafc;
}
.count-badge {
  background: rgba(0, 242, 254, 0.15);
  color: #00f2fe;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-family: 'Fira Code', monospace;
}
.close-drawer-btn { background: transparent; border: none; color: #64748b; font-size: 16px; cursor: pointer; }
.close-drawer-btn:hover { color: #f87171; }

.drawer-body {
  flex: 1;
  padding: 14px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #64748b;
  text-align: center;
}
.empty-icon { font-size: 32px; margin-bottom: 8px; opacity: 0.5; }
.empty-sub { font-size: 11.5px; color: #475569; margin-top: 4px; }

.measurement-card-item {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 10px 12px;
  transition: all 0.2s ease;
}
.measurement-card-item:hover {
  border-color: rgba(0, 242, 254, 0.4);
  background: rgba(15, 23, 42, 0.95);
}
.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.type-tag {
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.tag-point { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.tag-line { background: rgba(0, 242, 254, 0.15); color: #00f2fe; }
.tag-area { background: rgba(52, 211, 153, 0.15); color: #34d399; }
.item-name-input { box-sizing: border-box; min-width: 80px; flex: 1; margin: 0 8px; padding: 4px 6px; border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 5px; outline: none; background: rgba(2, 7, 18, 0.5); color: #cbd5e1; font: 12px 'Microsoft YaHei', sans-serif; }
.item-name-input:focus { border-color: rgba(0, 242, 254, 0.62); box-shadow: 0 0 0 2px rgba(0, 242, 254, 0.08); }
.item-name-input::placeholder { color: #64748b; }
.delete-item-btn { background: transparent; border: none; cursor: pointer; font-size: 12px; opacity: 0.6; }
.delete-item-btn:hover { opacity: 1; }

.item-value-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.val-main { color: #f8fafc; font-weight: 700; font-family: 'Fira Code', monospace; font-size: 13.5px; }
.focus-btn {
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid rgba(0, 242, 254, 0.3);
  color: #00f2fe;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}
.focus-btn:hover { background: #00f2fe; color: #020712; }

.item-coords { font-size: 10px; color: #64748b; font-family: 'Fira Code', monospace; line-height: 1.4; }

.drawer-footer {
  padding: 12px 14px;
  background: rgba(16, 24, 40, 0.9);
  border-top: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.footer-btn {
  width: 100%;
  padding: 8px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.footer-btn.primary-btn {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.25), rgba(52, 211, 153, 0.25));
  border-color: #00f2fe;
  color: #00f2fe;
}
.footer-btn.primary-btn:hover { background: #00f2fe; color: #020712; }
.footer-btn.danger-btn { background: rgba(248, 113, 113, 0.1); border-color: #f87171; color: #f87171; }
.footer-btn.danger-btn:hover:not(:disabled) { background: #f87171; color: #020712; }
.footer-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* 【步骤六】：测量报告导出 Modal */
.report-modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(2, 7, 18, 0.85);
  backdrop-filter: blur(8px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
  padding: 20px;
}
.report-modal-card {
  width: 900px;
  max-width: 95vw;
  max-height: 90vh;
  background: #090f1d;
  border: 1px solid rgba(0, 242, 254, 0.35);
  border-radius: 12px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.8), 0 0 24px rgba(0, 242, 254, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.report-header {
  padding: 16px 24px;
  background: #0f172a;
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.report-title-group h2 {
  margin: 0;
  font-size: 18px;
  color: #ffffff;
}
.report-subtitle {
  font-size: 11px;
  color: #64748b;
  font-family: 'Courier New', monospace;
}
.close-modal-btn { background: transparent; border: none; color: #64748b; font-size: 20px; cursor: pointer; }
.close-modal-btn:hover { color: #f87171; }

.report-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: #0b1329;
}

.report-meta-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.meta-card {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 10px 14px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.meta-lbl { font-size: 11px; color: #64748b; }
.meta-val { font-size: 13px; color: #f8fafc; font-weight: 600; }
.meta-val.highlight { color: #00f2fe; font-family: 'Fira Code', monospace; }

.report-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.kpi-box {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(0, 242, 254, 0.2);
  padding: 14px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.kpi-label { font-size: 11.5px; color: #94a3b8; }
.kpi-num { font-size: clamp(16px, 1.8vw, 22px); font-weight: 800; font-family: 'Fira Code', monospace; }
.kpi-unit { font-size: 10px; color: #8496a8; text-align: center; }
.precision-box { border-color: rgba(251, 191, 36, 0.25); }
.precision-note { margin: -3px 0 0; padding: 9px 12px; border-left: 2px solid rgba(251, 191, 36, 0.65); background: rgba(251, 191, 36, 0.06); color: #a9b7c4; font-size: 11px; line-height: 1.55; }
.synthetic-data-note { margin: 0 0 12px; border-left-color: rgba(96, 165, 250, 0.68); background: rgba(59, 130, 246, 0.06); }

.report-table-section h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #38bdf8;
}
.quality-report-section { margin-bottom: 18px; }
.quality-report-source { margin: -5px 0 10px; color: #8aa0b3; font-size: 10px; line-height: 1.45; }
.quality-report-source a { margin-left: 8px; color: #70dce3; text-decoration: underline; text-underline-offset: 2px; }
.quality-report-caveat { margin: 9px 0 0; color: #91a5b5; font-size: 10px; line-height: 1.5; }
.report-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: left;
}
.report-data-table th {
  background: #0f172a;
  color: #94a3b8;
  padding: 10px 12px;
  border-bottom: 1px solid #1e293b;
  font-weight: 600;
}
.report-data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
}
.no-data-td { text-align: center; color: #64748b; padding: 20px !important; }

.type-badge { padding: 2px 6px; border-radius: 4px; font-size: 10.5px; font-weight: 600; }
.badge-point { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.badge-line { background: rgba(0, 242, 254, 0.15); color: #00f2fe; }
.badge-area { background: rgba(52, 211, 153, 0.15); color: #34d399; }

.value-cell { font-family: 'Fira Code', monospace; color: #00f2fe; font-weight: 600; }
.coord-cell { font-family: 'Fira Code', monospace; font-size: 10.5px; color: #94a3b8; }

.remark-tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; }
.remark-normal { background: rgba(52, 211, 153, 0.1); color: #34d399; }
.remark-warning { background: rgba(251, 191, 36, 0.1); color: #fbbf24; }
.remark-danger { background: rgba(248, 113, 113, 0.1); color: #f87171; }
.reference-comparison { display: block; max-width: 260px; margin-top: 4px; color: #91a5b5; font-size: 10px; font-weight: 400; line-height: 1.45; white-space: normal; }

.delete-report-btn {
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.3);
  color: #f87171;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.delete-report-btn:hover {
  background: #f87171;
  color: #020712;
}
.measurement-entry-overlay { position: fixed; inset: 0; z-index: 110; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(2, 7, 18, 0.86); backdrop-filter: blur(8px); }
.measurement-entry-card { display: grid; width: min(520px, 96vw); gap: 15px; padding: 23px; border: 1px solid rgba(75, 166, 189, 0.48); border-radius: 14px; background: linear-gradient(145deg, #0b1a2a, #07111d); color: #e5f1f6; box-shadow: 0 22px 68px rgba(0, 0, 0, 0.58), 0 0 28px rgba(45, 193, 202, 0.12); }
.measurement-entry-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding-bottom: 12px; border-bottom: 1px solid rgba(117, 158, 182, 0.16); }
.entry-eyebrow { color: #61d5dc; font-size: 9px; font-weight: 700; letter-spacing: 0.14em; }
.measurement-entry-header h2 { margin: 5px 0 0; color: #f1f8fb; font-size: 20px; }
.entry-measurement-value { padding: 7px 9px; border: 1px solid rgba(90, 215, 223, 0.26); border-radius: 7px; background: rgba(8, 38, 50, 0.62); color: #8eece2; font: 700 12px 'Consolas', monospace; }
.entry-field { display: grid; min-width: 0; gap: 6px; color: #a9bdc9; font-size: 11px; }
.entry-field b { color: #f3b66a; }
.entry-field small, .entry-reference-heading small { color: #71899a; font-size: 10px; font-weight: 400; }
.entry-field input { box-sizing: border-box; width: 100%; min-height: 36px; padding: 8px 10px; border: 1px solid rgba(117, 158, 182, 0.26); border-radius: 7px; outline: none; background: rgba(2, 10, 19, 0.78); color: #eff8fb; font: 12px 'Microsoft YaHei', sans-serif; }
.entry-field input:focus { border-color: rgba(81, 219, 207, 0.68); box-shadow: 0 0 0 2px rgba(81, 219, 207, 0.08); }
.entry-field input:disabled { opacity: 0.48; cursor: not-allowed; }
.entry-field input::placeholder { color: #566d7b; }
.entry-reference-heading { display: flex; align-items: center; justify-content: space-between; color: #a9bdc9; font-size: 11px; }
.entry-coordinate-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
.entry-number-field { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 9px; }
.entry-number-field span { color: #7edfd5; font: 11px 'Consolas', monospace; }
.entry-calibration-option { display: flex; align-items: flex-start; gap: 8px; color: #d4e3e9; font-size: 11px; }
.entry-calibration-option input { margin: 2px 0 0; accent-color: #38cfc7; }
.entry-calibration-option input:disabled { opacity: 0.4; }
.entry-help { margin: -7px 0 0; color: #7892a2; font-size: 10px; line-height: 1.5; }
.entry-error { margin: 0; color: #ff9b8c; font-size: 11px; }
.measurement-entry-actions { display: flex; justify-content: flex-end; gap: 9px; padding-top: 10px; border-top: 1px solid rgba(117, 158, 182, 0.14); }
.entry-cancel-button, .entry-save-button { min-height: 35px; padding: 8px 12px; border-radius: 7px; cursor: pointer; font-size: 11px; font-weight: 700; }
.entry-cancel-button { border: 1px solid rgba(117, 158, 182, 0.3); background: rgba(17, 37, 55, 0.72); color: #b8cbd5; }
.entry-save-button { border: 1px solid rgba(84, 217, 202, 0.58); background: linear-gradient(100deg, rgba(11, 117, 121, 0.64), rgba(22, 82, 131, 0.66)); color: #d6fffa; }
.entry-save-button:disabled { border-color: rgba(117, 158, 182, 0.14); background: rgba(22, 37, 49, 0.65); color: #708595; cursor: not-allowed; }
.report-conclusion-box {
  background: rgba(15, 23, 42, 0.8);
  border: 1px dashed rgba(0, 242, 254, 0.3);
  padding: 14px 18px;
  border-radius: 8px;
}
.report-conclusion-box h4 { margin: 0 0 6px 0; color: #00f2fe; font-size: 13px; }
.report-conclusion-box p { margin: 0; font-size: 12px; color: #cbd5e1; line-height: 1.6; }

.report-footer {
  padding: 14px 24px;
  background: #0f172a;
  border-top: 1px solid #1e293b;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.report-action-btn {
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.report-action-btn.secondary { background: rgba(255, 255, 255, 0.08); color: #cbd5e1; border-color: #475569; }
.report-action-btn.secondary:hover { background: rgba(255, 255, 255, 0.15); color: #ffffff; }
.report-action-btn.primary { background: #00f2fe; color: #020712; }
.report-action-btn.primary:hover { background: #38bdf8; box-shadow: 0 0 14px rgba(0, 242, 254, 0.5); }

/* 动画与响应式 */
.slide-left-enter-active, .slide-left-leave-active { transition: transform 0.3s ease; }
.slide-left-enter-from, .slide-left-leave-to { transform: translateX(100%); }

.canvas-hint {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(4, 12, 26, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 12px;
  color: #94a3b8;
  backdrop-filter: blur(4px);
  pointer-events: none;
  white-space: nowrap;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}
</style>
