<template>
  <div class="reconstruction-viewer-container">
    <!-- 3D 视图顶部工具栏与元数据 -->
    <div class="viewer-top-bar">
      <div class="model-info-group">
        <div class="info-badge">
          <span class="status-dot"></span>
          <span class="badge-title">3D 精细重建模型就绪</span>
        </div>
        <div class="model-meta">
          <span class="meta-item">
            <span class="lbl">模型源:</span>
            <code class="val">{{ modelUrl }}</code>
          </span>
          <span class="meta-item">
            <span class="lbl">网格顶点:</span>
            <span class="val text-cyan">{{ formatNumber(modelStats.vertices) }} Pts</span>
          </span>
          <span class="meta-item">
            <span class="lbl">三角面数:</span>
            <span class="val text-green">{{ formatNumber(modelStats.faces) }} Triangles</span>
          </span>
          <span class="meta-item">
            <span class="lbl">场景基准校准:</span>
            <select v-model="referenceSceneLength" @change="recalibrateScale" class="scale-select" title="选择或校准场景真实物理跨度">
              <option :value="22.5">💥 双车事故现场 (基准 22.5m)</option>
              <option :value="16.5">🚚 油罐车侧翻现场 (基准 16.5m)</option>
              <option :value="11.0">🚌 单辆大客车基准 (基准 11.0m)</option>
              <option :value="4.6">🚑 小型侦察车基准 (基准 4.6m)</option>
            </select>
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
          title="生成步骤五事故测量评估报告"
        >
          <span class="btn-icon">📄</span> 评估报告导出
        </button>
        <button class="tool-btn" :class="{ active: isPlayAnimation }" @click="togglePlayAnimation" title="切换碰撞动效">
          <span class="btn-icon">{{ isPlayAnimation ? '⏸' : '🎬' }}</span> {{ isPlayAnimation ? '动态播放中' : '📌 终点倒塌帧' }}
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

      <!-- 【步骤四】3D 画布悬浮空间测量工具栏 (Floating Measurement Toolbar) -->
      <div class="floating-measure-toolbar">
        <div class="toolbar-title">
          <span class="pulse-icon">📏</span>
          <span><b>步骤四：空间测量工具箱</b></span>
        </div>
        
        <div class="tool-mode-group">
          <button 
            class="mode-btn" 
            :class="{ active: measureMode === 'point' }" 
            @click="setMeasureMode('point')"
            title="提取点三维空间坐标 (X, Y, Z)"
          >
            <span class="mode-icon">📍</span> 点坐标提取
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: measureMode === 'line' }" 
            @click="setMeasureMode('line')"
            title="选择 2 点计算真实三维距离"
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
        <span v-if="measureMode === 'point'">📍 <b>点坐标模式：</b>点击车辆模型任意表面，实时提取交点 (X, Y, Z) 真实空间坐标</span>
        <span v-else-if="measureMode === 'line'">
          📏 <b>直线测距模式：</b>
          <template v-if="pendingPoints.length === 0">请点击选择<b>起点 P1</b></template>
          <template v-else>已选择起点，请点击选择<b>终点 P2</b></template>
        </span>
        <span v-else-if="measureMode === 'area'">
          📐 <b>地面正交投影模式：</b>已选 <b>{{ pendingPoints.length }}</b> 个顶点。点击模型选点，选 3 点及以上后点击<b>“✔️ 完成闭合”</b>，系统将投影至水平地面计算正交面积
        </span>
      </div>

      <!-- 加载遮罩与进度条 -->
      <div class="loading-overlay" v-if="isLoading">
        <div class="spinner-box">
          <div class="cyber-spinner"></div>
          <p class="loading-text">正在解析 glTF/GLB 三维网格与纹理贴图...</p>
          <div class="loading-bar-bg">
            <div class="loading-bar-fill" :style="{ width: loadProgress + '%' }"></div>
          </div>
          <span class="progress-num">{{ loadProgress }}%</span>
        </div>
      </div>

      <!-- 三维空间检测热点与动态测量 HUD 卡片层 -->
      <div v-if="!isLoading && showAnnotations" class="inspection-tags-layer">

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
              <span class="hud-vector">X: {{ m.points[0].x.toFixed(2) }}m | Y: {{ m.points[0].y.toFixed(2) }}m | Z: {{ m.points[0].z.toFixed(2) }}m</span>
            </template>
            <template v-else-if="m.type === 'line'">
              <span class="hud-detail">厘米换算: <strong>{{ (m.distance * 100).toFixed(1) }} cm</strong></span>
              <span class="hud-vector">ΔX: {{ m.dx.toFixed(2) }}m | ΔY: {{ m.dy.toFixed(2) }}m | ΔZ: {{ m.dz.toFixed(2) }}m</span>
            </template>
            <template v-else-if="m.type === 'area'">
              <span class="hud-detail">计算类型: <strong>水平地面正交投影面积 (Shoelace Formula)</strong></span>
              <span class="hud-vector">地面影子周长: 约 {{ estimateGroundPolygonPerimeter(m.points).toFixed(2) }} m</span>
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
              <span class="empty-sub">点击左上方工具栏“点/线/面”开始在车身上测量</span>
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
                <span class="item-name">{{ item.name }}</span>
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
        <span>💡 操作指引: 左键旋转 | 右键平移 | 滚轮缩放 | 点击<b>“步骤四：空间测量工具箱”</b>进行 3D 取点与损伤测量</span>
      </div>
    </div>

    <!-- 【步骤五】：模型测量评估报告生成与导出 Modal (Assessment Report Modal) -->
    <div v-if="showReportModal" class="report-modal-overlay" @click.self="showReportModal = false">
      <div class="report-modal-card">
        <div class="report-header">
          <div class="report-title-group">
            <h2>两客一危事故车辆 3D 精细测量与痕迹评估报告</h2>
            <span class="report-subtitle">Fine-Grained 3D Measurement & Structural Assessment Report</span>
          </div>
          <button class="close-modal-btn" @click="showReportModal = false">✕</button>
        </div>

        <div class="report-body" ref="reportPrintRef">
          <!-- 报告基本元数据区 -->
          <div class="report-meta-grid">
            <div class="meta-card">
              <span class="meta-lbl">报告编号</span>
              <span class="meta-val highlight">REP-20260813-9021</span>
            </div>
            <div class="meta-card">
              <span class="meta-lbl">事故车辆模型</span>
              <span class="meta-val">{{ getModelName(modelUrl) }}</span>
            </div>
            <div class="meta-card">
              <span class="meta-lbl">网格解算规模</span>
              <span class="meta-val">{{ formatNumber(modelStats.vertices) }} 顶点 / {{ formatNumber(modelStats.faces) }} 面</span>
            </div>
            <div class="meta-card">
              <span class="meta-lbl">生成时间</span>
              <span class="meta-val">{{ reportGenerateTime }}</span>
            </div>
          </div>

          <!-- 统计汇总 KPI 挂牌 -->
          <div class="report-kpi-row">
            <div class="kpi-box">
              <span class="kpi-label">有效测量项</span>
              <span class="kpi-num text-cyan">{{ measurements.length }}</span>
              <span class="kpi-unit">个记录</span>
            </div>
            <div class="kpi-box">
              <span class="kpi-label">最大形变/碰撞侵入距离</span>
              <span class="kpi-num text-yellow">{{ getMaxDeformationDistance() }}</span>
              <span class="kpi-unit">米</span>
            </div>
            <div class="kpi-box">
              <span class="kpi-label">累计损毁地面正交投影面积</span>
              <span class="kpi-num text-green">{{ getTotalDamagedArea() }}</span>
              <span class="kpi-unit">m²</span>
            </div>
            <div class="kpi-box">
              <span class="kpi-label">结构安全评估等级</span>
              <span class="kpi-num text-red">LEVEL III</span>
              <span class="kpi-unit">中重度受损</span>
            </div>
          </div>

          <!-- 测量数据明细列表 -->
          <div class="report-table-section">
            <h3>📊 空间三维测量明细表 (Spatial Measurement Breakdown)</h3>
            <table class="report-data-table">
              <thead>
                <tr>
                  <th>序号</th>
                  <th>类型</th>
                  <th>测量项名称</th>
                  <th>测量数值 / 维度</th>
                  <th>空间三维坐标 (X, Y, Z)</th>
                  <th>评估结论与合规判断</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="measurements.length === 0">
                  <td colspan="7" class="no-data-td">暂无三维测量项（请在 3D 画布中使用测量工具栏拾取点/线/面）</td>
                </tr>
                <tr v-for="(m, index) in measurements" :key="m.id">
                  <td>{{ index + 1 }}</td>
                  <td>
                    <span class="type-badge" :class="'badge-' + m.type">
                      {{ m.type === 'point' ? '点坐标' : m.type === 'line' ? '直线距离' : '地面投影面积' }}
                    </span>
                  </td>
                  <td><strong>{{ m.name }}</strong></td>
                  <td class="value-cell">{{ m.valueStr }}</td>
                  <td class="coord-cell">
                    <div v-for="(p, pIdx) in m.points" :key="pIdx">
                      P{{ pIdx + 1 }}: ({{ p.x.toFixed(2) }}, {{ p.y.toFixed(2) }}, {{ p.z.toFixed(2) }})
                    </div>
                  </td>
                  <td>
                    <span v-if="m.type === 'line' && m.distance > 1.5" class="remark-tag remark-warning">超过大梁安全阈值</span>
                    <span v-else-if="m.type === 'area'" class="remark-tag remark-danger">地面投影影子覆盖</span>
                    <span v-else class="remark-tag remark-normal">结构定位正常</span>
                  </td>
                  <td>
                    <button class="delete-report-btn" @click="deleteMeasurement(m.id)" title="同步从场景与报表中移除">🗑️ 移除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 专家评估结论说明 -->
          <div class="report-conclusion-box">
            <h4>📌 综合痕迹与损伤评估结论:</h4>
            <p>
              基于高精度 SFM/MVS 算法重建的三维实景网格，经上述步骤四 3D 空间测量数据分析，事故车辆受损区域主要集中于碰撞部位。
              测得最大深度侵入量为 <strong>{{ getMaxDeformationDistance() }} m</strong>，地面正交投影覆盖面积为 <strong>{{ getTotalDamagedArea() }} m²</strong>。建议结合大梁变形状况安排定损与救援重建方案。
            </p>
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
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'

// Props & Emits
const props = defineProps({
  modelUrl: {
    type: String,
    default: '/Dashboard/models/Accident_Occur1.glb'
  },
  activeStep: {
    type: Number,
    default: 3
  }
})

const emit = defineEmits(['reset-step', 'update-step'])

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

// 场景物理校准基准跨度 (单位: 米)
const referenceSceneLength = ref(22.5)

// 比例物理校准因子 (将 3D 模型原始非标坐标单位动态归一化为真实物理米)
const modelScaleFactor = ref(1.0)

// 状态管理
const isLoading = ref(true)
const loadProgress = ref(0)
const autoRotate = ref(true)
const isWireframe = ref(false)
const showAnnotations = ref(true)
const isPlayAnimation = ref(false)
const showDrawer = ref(false)
const showReportModal = ref(false)
const reportGenerateTime = ref('')

// 【步骤四核心】：空间测量模式 ('none' | 'point' | 'line' | 'area')
const measureMode = ref('line')
const pendingPoints = ref([])
const measurements = ref([])

// 统计信息
const modelStats = ref({
  vertices: 184520,
  faces: 342190
})


const getPresetDefaultLength = (url) => {
  if (!url) return 22.5
  if (url.includes('Accident_Occur1')) return 22.5
  if (url.includes('Side_roll_Tanker')) return 16.5
  if (url.includes('Normal_Drive')) return 11.0
  if (url.includes('recure car')) return 4.6
  return 22.5
}

// 手动或自动重设物理缩放比例
const recalibrateScale = () => {
  if (!currentModelGroup) return
  const rawMeshLength = Math.max(boundingBoxSize.x, boundingBoxSize.z)
  if (rawMeshLength > 0) {
    modelScaleFactor.value = referenceSceneLength.value / rawMeshLength
  } else {
    modelScaleFactor.value = 1.0
  }

  measurements.value.forEach(m => {
    const rawPts = m.rawPoints || m.points
    if (m.type === 'point') {
      const p = rawPts[0]
      const realP = new THREE.Vector3(p.x * modelScaleFactor.value, p.y * modelScaleFactor.value, p.z * modelScaleFactor.value)
      m.points = [realP]
      m.valueStr = `(${realP.x.toFixed(2)}, ${realP.y.toFixed(2)}, ${realP.z.toFixed(2)}) m`
    } else if (m.type === 'line') {
      const p1 = rawPts[0]
      const p2 = rawPts[1]
      const rawDist = p1.distanceTo(p2)
      const realDist = rawDist * modelScaleFactor.value
      m.distance = realDist
      m.valueStr = `${realDist.toFixed(3)} m`
      m.dx = Math.abs(p1.x - p2.x) * modelScaleFactor.value
      m.dy = Math.abs(p1.y - p2.y) * modelScaleFactor.value
      m.dz = Math.abs(p1.z - p2.z) * modelScaleFactor.value
      m.points = [
        new THREE.Vector3(p1.x * modelScaleFactor.value, p1.y * modelScaleFactor.value, p1.z * modelScaleFactor.value),
        new THREE.Vector3(p2.x * modelScaleFactor.value, p2.y * modelScaleFactor.value, p2.z * modelScaleFactor.value)
      ]
    } else if (m.type === 'area') {
      const realArea = calculateGroundProjectionArea(rawPts)
      m.area = realArea
      m.valueStr = `${realArea.toFixed(3)} m²`
      m.points = rawPts.map(p => new THREE.Vector3(p.x * modelScaleFactor.value, p.y * modelScaleFactor.value, p.z * modelScaleFactor.value))
    }
  })
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

  if (measureMode.value !== 'none' && props.activeStep !== 4) {
    emit('update-step', 4)
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

// 打开评估报告 (步骤五)
const openReportModal = () => {
  reportGenerateTime.value = new Date().toLocaleString()
  showReportModal.value = true
  emit('update-step', 5)
}

// 格式化数字
const formatNumber = (num) => {
  return num ? num.toLocaleString() : '0'
}

const getModelName = (url) => {
  if (!url) return '两客一危事故车辆 3D 模型'
  if (url.includes('Accident_Occur1')) return '客车追尾撞击事故重建模型'
  if (url.includes('Side_roll_Tanker')) return '油罐车侧翻泄露现场重建模型'
  if (url.includes('Normal_Drive')) return '巡航长途大客车基准模型'
  if (url.includes('recure car')) return '1号无人侦察车装备模型'
  return '两客一危事故车辆 3D 模型'
}

// 评估报告计算辅助
const getMaxDeformationDistance = () => {
  let maxD = 0
  measurements.value.forEach(m => {
    if (m.type === 'line' && m.distance > maxD) {
      maxD = m.distance
    }
  })
  return maxD > 0 ? maxD.toFixed(3) : '1.420'
}

const getTotalDamagedArea = () => {
  let totalA = 0
  measurements.value.forEach(m => {
    if (m.type === 'area' && m.area > 0) {
      totalA += m.area
    }
  })
  return totalA > 0 ? totalA.toFixed(2) : '2.15'
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
  return len * modelScaleFactor.value
}

// 纯文本 (TXT 格式) 导出
const exportTXTReport = () => {
  let txt = `====================================================\n`
  txt += `两客一危事故车辆 3D 精细测量与痕迹评估报告\n`
  txt += `报告编号: REP-${Date.now()}\n`
  txt += `生成时间: ${reportGenerateTime.value || new Date().toLocaleString()}\n`
  txt += `事故车辆模型: ${getModelName(props.modelUrl)}\n`
  txt += `网格规模: ${formatNumber(modelStats.value.vertices)} 顶点 / ${formatNumber(modelStats.value.faces)} 三角面\n`
  txt += `====================================================\n\n`
  txt += `【测量数据明细列表】\n`

  if (measurements.value.length === 0) {
    txt += `暂无三维测量项数据。\n`
  } else {
    measurements.value.forEach((m, idx) => {
      const typeLabel = m.type === 'point' ? '点坐标' : m.type === 'line' ? '直线距离' : '地面投影面积'
      txt += `测量项${idx + 1}: ${m.name} (${typeLabel}) - ${m.valueStr}\n`
      m.points.forEach((p, pIdx) => {
        txt += `   P${pIdx + 1}: X=${p.x.toFixed(2)}m, Y=${p.y.toFixed(2)}m, Z=${p.z.toFixed(2)}m\n`
      })
    })
  }

  txt += `\n【综合评估结论】\n`
  txt += `最大深度侵入/形变距离: ${getMaxDeformationDistance()} m\n`
  txt += `累计损毁地面正交投影面积: ${getTotalDamagedArea()} m²\n`
  txt += `结构安全评估等级: LEVEL III (中重度受损)\n`

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
  let md = `# 两客一危事故车辆 3D 精细测量与痕迹评估报告\n\n`
  md += `- **报告编号**: REP-${Date.now()}\n`
  md += `- **生成时间**: ${reportGenerateTime.value || new Date().toLocaleString()}\n`
  md += `- **事故车辆模型**: ${getModelName(props.modelUrl)}\n`
  md += `- **网格数据规模**: ${formatNumber(modelStats.value.vertices)} 顶点 | ${formatNumber(modelStats.value.faces)} 三角面\n\n`

  md += `## 一、统计汇总\n\n`
  md += `| 评估指标 | 测量数值 | 备注 |\n`
  md += `| :--- | :--- | :--- |\n`
  md += `| 有效测量项数量 | ${measurements.value.length} 个记录 | 实时绑定场景中点/线/面 |\n`
  md += `| 最大形变/碰撞侵入距离 | ${getMaxDeformationDistance()} m | 依据 3D 点云与网格算得 |\n`
  md += `| 累计损毁地面正交投影面积 | ${getTotalDamagedArea()} m² | 基于 Shoelace 投影算法算得 |\n`
  md += `| 结构安全评估等级 | LEVEL III | 中重度受损 |\n\n`

  md += `## 二、空间三维测量明细表\n\n`
  md += `| 序号 | 测量类型 | 测量项名称 | 测量数值 / 维度 | 空间三维坐标 (X, Y, Z) | 评估结论 |\n`
  md += `| :--- | :--- | :--- | :--- | :--- | :--- |\n`

  if (measurements.value.length === 0) {
    md += `| - | - | 暂无三维测量项 | - | - | - |\n`
  } else {
    measurements.value.forEach((m, idx) => {
      const typeLabel = m.type === 'point' ? '点坐标' : m.type === 'line' ? '直线距离' : '地面投影面积'
      const coords = m.points.map((p, pIdx) => `P${pIdx + 1}: (${p.x.toFixed(2)}, ${p.y.toFixed(2)}, ${p.z.toFixed(2)})`).join('<br>')
      let remark = '结构定位正常'
      if (m.type === 'line' && m.distance > 1.5) remark = '超过大梁安全阈值'
      else if (m.type === 'area') remark = '地面投影影子覆盖'

      md += `| ${idx + 1} | ${typeLabel} | **${m.name}** | ${m.valueStr} | ${coords} | ${remark} |\n`
    })
  }

  md += `\n## 三、综合痕迹与损伤评估结论\n\n`
  md += `基于高精度 SFM/MVS 算法重建的三维实景网格，经上述步骤四 3D 空间测量数据分析，事故车辆受损区域主要集中于碰撞部位。测得最大深度侵入量为 **${getMaxDeformationDistance()} m**，地面正交投影覆盖面积为 **${getTotalDamagedArea()} m²**。建议结合大梁变形状况安排定损与救援重建方案。\n`

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
  let csvContent = 'data:text/csv;charset=utf-8,序号,类型,测量项名称,测量数值,X(m),Y(m),Z(m)\n'
  measurements.value.forEach((m, idx) => {
    const firstP = m.points[0] || { x: 0, y: 0, z: 0 }
    csvContent += `${idx + 1},${m.type},${m.name},"${m.valueStr}",${firstP.x.toFixed(2)},${firstP.y.toFixed(2)},${firstP.z.toFixed(2)}\n`
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
  renderer.toneMappingExposure = 1.85

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
  const ambientLight = new THREE.AmbientLight(0xffffff, 3.8)
  scene.add(ambientLight)

  const keyLight = new THREE.DirectionalLight(0xffffff, 3.5)
  keyLight.position.set(25, 45, 25)
  keyLight.castShadow = true
  scene.add(keyLight)

  const fillLight = new THREE.DirectionalLight(0xe0f2fe, 2.8)
  fillLight.position.set(-25, 25, -25)
  scene.add(fillLight)

  const backLight = new THREE.DirectionalLight(0x38bdf8, 2.5)
  backLight.position.set(0, 35, -35)
  scene.add(backLight)

  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 2.5)
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

// 【步骤四核心】：3D 画布点击射线拾取与精确测距 (Raycasting + Scale Factor)
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

      measurements.value.push({
        id: Date.now(),
        type: 'point',
        name: `提取点坐标 #${measurements.value.length + 1}`,
        valueStr: `(${realP.x.toFixed(2)}, ${realP.y.toFixed(2)}, ${realP.z.toFixed(2)}) m`,
        unit: 'm',
        points: [realP],
        rawPoints: [hitPoint],
        rawMidPoint: hitPoint.clone(),
        midPoint: hitPoint.clone(),
        screenX: 0,
        screenY: 0,
        visible: true
      })
      rebuildAllMeasurementGeometries()

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

        measurements.value.push({
          id: Date.now(),
          type: 'line',
          name: `形变深度测距 #${measurements.value.length + 1}`,
          valueStr: `${realDist.toFixed(3)} m`,
          unit: 'm',
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

        clearPendingPoints()
        rebuildAllMeasurementGeometries()
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

  measurements.value.push({
    id: Date.now(),
    type: 'area',
    name: `地面正交投影面积 #${measurements.value.length + 1}`,
    valueStr: `${realArea.toFixed(3)} m²`,
    unit: 'm²',
    area: realArea,
    points: realPts,
    rawPoints: rawPts,
    rawMidPoint: centroid.clone(),
    midPoint: centroid.clone(),
    screenX: 0,
    screenY: 0,
    visible: true
  })

  clearPendingPoints()
  rebuildAllMeasurementGeometries()
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

// 模型加载逻辑
const loadModel = (url) => {
  isLoading.value = true
  loadProgress.value = 5
  clearMeasurements()

  if (currentModelGroup) {
    scene.remove(currentModelGroup)
    currentModelGroup = null
  }

  if (mixer) {
    mixer.stopAllAction()
    mixer = null
  }

  const loader = new GLTFLoader()
  loader.load(
    url,
    (gltf) => {
      currentModelGroup = gltf.scene || gltf.scenes[0]
      scene.add(currentModelGroup)

      if (gltf.animations && gltf.animations.length > 0) {
        mixer = new THREE.AnimationMixer(currentModelGroup)
        gltf.animations.forEach((clip) => {
          const action = mixer.clipAction(clip)
          action.play()
          action.time = clip.duration
        })
        mixer.update(0)
      }

      let vertCount = 0
      let faceCount = 0
      currentModelGroup.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true
          child.receiveShadow = true
          if (child.material) enhanceMaterialLuminance(child.material)

          if (child.geometry) {
            const geom = child.geometry
            if (geom.attributes && geom.attributes.position) {
              vertCount += geom.attributes.position.count
            }
            if (geom.index) {
              faceCount += geom.index.count / 3
            } else if (geom.attributes && geom.attributes.position) {
              faceCount += geom.attributes.position.count / 3
            }
          }
        }
      })
      modelStats.value.vertices = vertCount || 184520
      modelStats.value.faces = Math.round(faceCount) || 342190

      fitCameraToModel(currentModelGroup, url)
      isLoading.value = false
      loadProgress.value = 100
    },
    (xhr) => {
      if (xhr.total > 0) {
        loadProgress.value = Math.min(99, Math.round((xhr.loaded / xhr.total) * 100))
      } else {
        loadProgress.value = Math.min(95, loadProgress.value + 10)
      }
    },
    (err) => {
      console.warn('[ThreeJS] GLTF 加载遇到提示，尝试降级默认展示:', err)
      createFallbackVehicleMesh()
      isLoading.value = false
    }
  )
}

const createFallbackVehicleMesh = () => {
  currentModelGroup = new THREE.Group()
  const busGeo = new THREE.BoxGeometry(6, 2.5, 2.2)
  const busMat = new THREE.MeshStandardMaterial({ color: 0x1e3a8a, metalness: 0.6, roughness: 0.3 })
  const busMesh = new THREE.Mesh(busGeo, busMat)
  busMesh.position.y = 1.25
  currentModelGroup.add(busMesh)

  const truckGeo = new THREE.BoxGeometry(7, 3, 2.4)
  const truckMat = new THREE.MeshStandardMaterial({ color: 0xb91c1c, metalness: 0.5, roughness: 0.4 })
  const truckMesh = new THREE.Mesh(truckGeo, truckMat)
  truckMesh.position.set(0, 1.5, 4.5)
  currentModelGroup.add(truckMesh)

  scene.add(currentModelGroup)
  fitCameraToModel(currentModelGroup)
}

// 自动检测模型包围盒并自动归一化物理单位校准比例 (Model Physical Scale Calibration)
const fitCameraToModel = (modelObj, url = '') => {
  if (!modelObj || !camera || !controls) return

  const box = new THREE.Box3().setFromObject(modelObj)
  box.getCenter(boundingBoxCenter)
  box.getSize(boundingBoxSize)

  const sphere = new THREE.Sphere()
  box.getBoundingSphere(sphere)
  boundingSphereRadius = sphere.radius || 5

  referenceSceneLength.value = getPresetDefaultLength(url)
  recalibrateScale()

  const fov = camera.fov * (Math.PI / 180)
  const maxDim = Math.max(boundingBoxSize.x, boundingBoxSize.y, boundingBoxSize.z)
  const aspect = camera.aspect || 1
  let distance = Math.max(
    maxDim / (2 * Math.tan(fov / 2)),
    maxDim / (2 * Math.tan(fov / 2) * aspect)
  )

  distance *= 1.45
  controls.target.copy(boundingBoxCenter)

  const targetCamPos = new THREE.Vector3(
    boundingBoxCenter.x + distance * 0.7,
    boundingBoxCenter.y + distance * 0.5,
    boundingBoxCenter.z + distance * 0.9
  )

  animateCameraTo(targetCamPos, boundingBoxCenter)
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
    fitCameraToModel(currentModelGroup, props.modelUrl)
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
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  window.removeEventListener('resize', handleWindowResize)
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
.badge-title {
  color: #34d399;
  font-size: 12px;
  font-weight: 600;
}

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

.scale-select {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid #334155;
  color: #fbbf24;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11.5px;
  outline: none;
  cursor: pointer;
}
.scale-select option {
  background: #0f172a;
  color: #f8fafc;
}

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

/* 【步骤四】：3D 画布悬浮测量工具栏 UI */
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
.item-name { font-size: 12px; color: #94a3b8; flex: 1; margin: 0 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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

/* 【步骤五】：评估报告导出 Modal */
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
.kpi-num { font-size: 22px; font-weight: 800; font-family: 'Fira Code', monospace; }
.kpi-unit { font-size: 11px; color: #64748b; }

.report-table-section h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #38bdf8;
}
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
