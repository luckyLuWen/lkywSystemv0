<template>
  <div class="dataset-uploader-container">
    <!-- 模块页头说明 -->
    <div class="module-header">
      <div class="header-title-box">
        <h2>两客一危交通事故车辆数据集导入系统</h2>
      </div>
      <p class="header-desc">
        提供多视角高清图像集/压缩包上传服务，支持格式校验、传输进度监控及“两客一危”全局唯一数据集凭证 ID 自动签发。
      </p>
    </div>

    <!-- 主上传区域容器 -->
    <div class="upload-main-card">
      <!-- 状态 1：待上传/拖拽区域 -->
      <div 
        v-if="uploadState === 'idle'"
        class="drop-zone"
        :class="{ 'is-dragover': isDragOver }"
        @dragover.prevent="handleDragOver"
        @dragleave.prevent="handleDragLeave"
        @drop.prevent="handleDrop"
      >
        <input 
          ref="fileInputRef" 
          type="file" 
          class="hidden-input" 
          accept=".zip,.tar.gz,.tar,.7z,.jpg,.jpeg,.png,.webp,.bmp" 
          multiple 
          @change="handleFileSelect"
        />
        <input 
          ref="folderInputRef" 
          type="file" 
          class="hidden-input" 
          webkitdirectory 
          directory 
          multiple 
          @change="handleFolderSelect"
        />

        <div class="drop-content">
          <div class="upload-icon-wrapper">
            <div class="pulse-ring"></div>
            <span class="upload-icon">📁</span>
          </div>
          <h3>拖拽数据集压缩包或图片文件夹至此处</h3>
          <p class="drop-subtext">或者点击下方按钮选择本地文件</p>

          <div class="format-tags">
            <span class="tag">支持格式: .zip / .tar.gz / .7z</span>
            <span class="tag">多视角照片: .jpg / .png / .webp</span>
          </div>

          <div class="action-buttons">
            <button class="btn btn-primary" @click="triggerFileInput">
              <span class="btn-icon">📦</span> 选择数据集压缩包
            </button>
            <button class="btn btn-secondary" @click="triggerFolderInput">
              <span class="btn-icon">📂</span> 选择图片文件夹
            </button>
          </div>
        </div>
      </div>

      <!-- 状态 2：上传进行中状态 -->
      <div v-else-if="uploadState === 'uploading'" class="uploading-zone">
        <div class="uploading-header">
          <div class="upload-spinner"></div>
          <div>
            <h4 class="uploading-title">正在传输“两客一危”事故车辆数据集...</h4>
            <p class="uploading-filename">当前目标: {{ currentFileName }}</p>
          </div>
        </div>

        <!-- 进度条 -->
        <div class="progress-wrapper">
          <div class="progress-info">
            <span class="progress-status">{{ progressStatusText }}</span>
            <span class="progress-percentage">{{ progressPercentage }}%</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" :style="{ width: progressPercentage + '%' }">
              <div class="progress-glow"></div>
            </div>
          </div>
          <div class="progress-metrics">
            <span>传输速度: {{ uploadSpeed }} MB/s</span>
            <span>传输进度: {{ transferredMB }} MB / {{ totalMB }} MB</span>
            <span>预计剩余时间: {{ remainingTime }} 秒</span>
          </div>
        </div>

        <div class="uploading-actions">
          <button class="btn btn-danger-outline" @click="cancelUpload">
            <span class="btn-icon">✕</span> 取消上传
          </button>
        </div>
      </div>

      <!-- 状态 3：上传完成与凭证卡片 -->
      <div v-else-if="uploadState === 'completed'" class="completed-zone">
        <div class="success-header">
          <div class="success-icon-badge">✓</div>
          <div>
            <h3>两客一危交通事故数据集导入成功！</h3>
            <p class="success-subtext">数据包已通过格式校验并成功绑定唯一的两客一危电子凭证 ID。</p>
          </div>
        </div>

        <!-- 全局唯一 Dataset ID 凭证卡片 -->
        <div class="dataset-ticket-card">
          <div class="ticket-header">
            <div class="ticket-type">
              <span class="category-pill" :class="datasetResult.categoryClass">
                {{ datasetResult.categoryLabel }}
              </span>
              <span class="vehicle-model">{{ datasetResult.vehicleModel }}</span>
            </div>
            <span class="ticket-status-badge">凭证已签发</span>
          </div>

          <div class="ticket-id-box">
            <span class="id-label">全局唯一凭证 ID (Dataset ID)</span>
            <div class="id-value-group">
              <code class="dataset-id">{{ datasetResult.id }}</code>
              <button class="btn-copy" @click="copyDatasetId">
                <span class="btn-icon">{{ isCopied ? '✓' : '📋' }}</span>
                {{ isCopied ? '已复制凭证' : '复制凭证 ID' }}
              </button>
            </div>
          </div>

          <!-- 详细元数据网格 -->
          <div class="metadata-grid">
            <div class="meta-item">
              <span class="meta-lbl">事故归属类型</span>
              <span class="meta-val text-yellow">{{ datasetResult.accidentCategory }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-lbl">包含图像帧数</span>
              <span class="meta-val text-cyan">{{ datasetResult.imageCount }} 张多视角帧</span>
            </div>
            <div class="meta-item">
              <span class="meta-lbl">数据集总大小</span>
              <span class="meta-val text-blue">{{ datasetResult.fileSize }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-lbl">数据校验哈希 (MD5)</span>
              <span class="meta-val font-mono">{{ datasetResult.md5Hash }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-lbl">上传时间戳</span>
              <span class="meta-val">{{ datasetResult.timestamp }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-lbl">后续环节说明</span>
              <span class="meta-val text-green">凭证已就绪，可作为分析推演凭证</span>
            </div>
          </div>
        </div>

        <!-- 底部控制按钮 -->
        <div class="completed-actions">
          <button class="btn btn-secondary" @click="resetUploader">
            <span class="btn-icon">↺</span> 重新导入数据集
          </button>
          <button class="btn btn-primary" @click="proceedToNextStep">
            <span class="btn-icon">✓</span> 完成导入
          </button>
        </div>
      </div>
    </div>

    <!-- 错误拦截提示 Toast -->
    <transition name="toast-fade">
      <div v-if="errorMessage" class="error-toast">
        <span class="toast-icon">⚠️</span>
        <span class="toast-text">{{ errorMessage }}</span>
        <button class="toast-close" @click="errorMessage = ''">✕</button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const emit = defineEmits(['dataset-ready', 'next-step'])

// 状态声明
const uploadState = ref('idle') // 'idle' | 'uploading' | 'completed'
const isDragOver = ref(false)
const errorMessage = ref('')
const isCopied = ref(false)

const fileInputRef = ref(null)
const folderInputRef = ref(null)

// 进度监控数据
const progressPercentage = ref(0)
const transferredMB = ref('0.0')
const totalMB = ref('128.5')
const uploadSpeed = ref('14.2')
const remainingTime = ref(9)
const currentFileName = ref('')
let timerId = null

// 结果凭证数据
const datasetResult = ref({
  id: '',
  categoryLabel: '',
  categoryClass: '',
  vehicleModel: '',
  accidentCategory: '',
  imageCount: 0,
  fileSize: '',
  md5Hash: '',
  timestamp: ''
})

// 支持的扩展名列表
const validExtensions = ['.zip', '.tar.gz', '.tar', '.7z', '.jpg', '.jpeg', '.png', '.webp', '.bmp']

// 点击输入框
const triggerFileInput = () => {
  if (fileInputRef.value) fileInputRef.value.click()
}
const triggerFolderInput = () => {
  if (folderInputRef.value) folderInputRef.value.click()
}

// 拖拽处理
const handleDragOver = () => { isDragOver.value = true }
const handleDragLeave = () => { isDragOver.value = false }

const handleDrop = (e) => {
  isDragOver.value = false
  const files = Array.from(e.dataTransfer.files)
  if (!files || files.length === 0) return
  processSelectedFiles(files)
}

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files)
  if (!files || files.length === 0) return
  processSelectedFiles(files)
}

const handleFolderSelect = (e) => {
  const files = Array.from(e.target.files)
  if (!files || files.length === 0) return
  processSelectedFiles(files, true)
}

// 文件校验与处理流程
const processSelectedFiles = (files, isFolder = false) => {
  errorMessage.value = ''

  // 格式合法性校验
  let isValid = true
  let hasValidImageOrArchive = false

  for (const file of files) {
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    const doubleExt = file.name.endsWith('.tar.gz') ? '.tar.gz' : ext

    if (validExtensions.includes(doubleExt) || validExtensions.includes(ext)) {
      hasValidImageOrArchive = true
    } else if (!isFolder && files.length === 1) {
      isValid = false
    }
  }

  if (!isValid || !hasValidImageOrArchive) {
    showErrorToast('格式校验失败！仅支持 .zip / .tar.gz / .7z 压缩包或包含多视角图像 (.jpg/.png) 的数据集包！')
    return
  }

  // 校验通过，启动传输动画
  const firstFile = files[0]
  currentFileName.value = isFolder ? `[文件夹] ${firstFile.webkitRelativePath.split('/')[0] || '两客一危图像数据集'}` : firstFile.name
  
  startSimulatedUpload({
    filename: currentFileName.value,
    imageCount: files.length > 1 ? files.length : Math.floor(Math.random() * 150 + 200),
    fileSizeMB: (files.reduce((acc, f) => acc + f.size, 0) / (1024 * 1024)).toFixed(1),
    prefix: determineCategoryPrefix(currentFileName.value)
  })
}

// 智能判断两客一危车辆类别
const determineCategoryPrefix = (name) => {
  if (name.includes('危化') || name.includes('油罐') || name.includes('hazmat')) return 'LK-HAZMAT'
  if (name.includes('客车') || name.includes('bus')) return 'LK-BUS'
  return 'LK-COACH'
}

// 模拟平滑上传进度条
const startSimulatedUpload = ({ filename, imageCount, fileSizeMB, prefix, presetInfo }) => {
  uploadState.value = 'uploading'
  progressPercentage.value = 0
  
  const targetMB = parseFloat(fileSizeMB) > 0 ? parseFloat(fileSizeMB) : 128.5
  totalMB.value = targetMB.toFixed(1)
  transferredMB.value = '0.0'
  
  if (timerId) clearInterval(timerId)

  timerId = setInterval(() => {
    progressPercentage.value += Math.floor(Math.random() * 8) + 4

    if (progressPercentage.value > 100) {
      progressPercentage.value = 100
    }

    const currentProg = progressPercentage.value / 100
    transferredMB.value = (targetMB * currentProg).toFixed(1)
    uploadSpeed.value = (12 + Math.random() * 5).toFixed(1)
    remainingTime.value = Math.max(0, Math.ceil((1 - currentProg) * 3))

    if (progressPercentage.value >= 100) {
      clearInterval(timerId)
      setTimeout(() => {
        finishUpload({ filename, imageCount, fileSizeMB: totalMB.value, prefix, presetInfo })
      }, 500)
    }
  }, 180)
}

// 上传完成生成电子凭证 ID
const finishUpload = ({ filename, imageCount, fileSizeMB, prefix, presetInfo }) => {
  uploadState.value = 'completed'
  
  const now = new Date()
  const dateStr = now.getFullYear().toString() +
    String(now.getMonth() + 1).padStart(2, '0') +
    String(now.getDate()).padStart(2, '0')
  const randomCode = Math.floor(10000 + Math.random() * 90000)

  const datasetId = `${prefix || 'LK-HAZMAT'}-${dateStr}-${randomCode}`
  
  let categoryLabel = '危化品运输车 (Hazmat Tanker)'
  let categoryClass = 'category-hazmat'
  let vehicleModel = '重型危化品槽罐运输车'
  let accidentCategory = '两客一危 - 危化品泄漏事故'

  if (prefix === 'LK-BUS' || (presetInfo && presetInfo.prefix === 'LK-BUS')) {
    categoryLabel = '长途营运客车 (Passenger Bus)'
    categoryClass = 'category-bus'
    vehicleModel = '55座长途大型双层客车'
    accidentCategory = '两客一危 - 高速连环追尾事故'
  } else if (prefix === 'LK-COACH' || (presetInfo && presetInfo.prefix === 'LK-COACH')) {
    categoryLabel = '旅游包车 (Tour Coach)'
    categoryClass = 'category-coach'
    vehicleModel = '大型高级旅游包车'
    accidentCategory = '两客一危 - 道路侧翻事故'
  }

  datasetResult.value = {
    id: datasetId,
    categoryLabel,
    categoryClass,
    vehicleModel,
    accidentCategory,
    imageCount: imageCount || 342,
    fileSize: `${fileSizeMB} MB`,
    md5Hash: generateMockMD5(),
    timestamp: now.toLocaleString('zh-CN')
  }

  // 触发全局事件告知父组件
  emit('dataset-ready', datasetResult.value)
}

// 生成模拟 MD5 哈希
const generateMockMD5 = () => {
  const chars = '0123456789abcdef'
  let res = ''
  for (let i = 0; i < 32; i++) {
    res += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return res
}

// 错误提示
const showErrorToast = (msg) => {
  errorMessage.value = msg
  setTimeout(() => {
    if (errorMessage.value === msg) errorMessage.value = ''
  }, 4000)
}

// 复制凭证 ID
const copyDatasetId = () => {
  if (!datasetResult.value.id) return
  navigator.clipboard.writeText(datasetResult.value.id)
  isCopied.value = true
  setTimeout(() => { isCopied.value = false }, 2000)
}

// 取消与重置
const cancelUpload = () => {
  if (timerId) clearInterval(timerId)
  uploadState.value = 'idle'
  progressPercentage.value = 0
}

const resetUploader = () => {
  uploadState.value = 'idle'
  progressPercentage.value = 0
  datasetResult.value.id = ''
}

const proceedToNextStep = () => {
  emit('next-step', datasetResult.value)
}

const progressStatusText = computed(() => {
  if (progressPercentage.value < 30) return '校验图像文件格式与元信息...'
  if (progressPercentage.value < 70) return '传输多视角高清晰照片阵列...'
  if (progressPercentage.value < 95) return '正在生成两客一危数据校验包...'
  return '正在签发全局唯一数据集凭证 ID...'
})
</script>

<style scoped>
.dataset-uploader-container {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
  background: rgba(4, 14, 30, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 16px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), inset 0 0 20px rgba(0, 229, 255, 0.04);
  font-family: 'Inter', -apple-system, sans-serif;
  color: #e2e8f0;
}

/* 模块页头 */
.module-header {
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 16px;
}
.header-title-box {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-title-box h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
}
.header-desc {
  margin: 6px 0 0;
  font-size: 13.5px;
  color: #94a3b8;
  line-height: 1.5;
}

/* 主上传卡片 */
.upload-main-card {
  width: 100%;
}
.drop-zone {
  border: 2px dashed rgba(0, 242, 254, 0.3);
  background: rgba(2, 12, 27, 0.5);
  border-radius: 14px;
  padding: 40px 20px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
}
.drop-zone.is-dragover {
  border-color: #00f2fe;
  background: rgba(0, 242, 254, 0.08);
  box-shadow: 0 0 30px rgba(0, 242, 254, 0.2);
}
.hidden-input { display: none; }

.upload-icon-wrapper {
  position: relative;
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.upload-icon {
  font-size: 32px;
  z-index: 2;
}
.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: rgba(0, 242, 254, 0.15);
  animation: pulse-ring 2s infinite;
}
@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 0.8; }
  100% { transform: scale(1.4); opacity: 0; }
}

.drop-content h3 {
  margin: 0 0 6px;
  font-size: 17px;
  color: #f8fafc;
}
.drop-subtext {
  margin: 0 0 16px;
  font-size: 13px;
  color: #64748b;
}
.format-tags {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.tag {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-size: 11.5px;
  padding: 3px 10px;
  border-radius: 20px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

/* 按钮样式 */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  font-weight: 600;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}
.btn-primary {
  background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
  color: #020c1b;
  box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3);
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 242, 254, 0.5);
}
.btn-secondary {
  background: rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.35);
}
.btn-danger-outline {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.btn-danger-outline:hover {
  background: rgba(239, 68, 68, 0.2);
}

/* 上传进行中 */
.uploading-zone {
  background: rgba(10, 25, 47, 0.6);
  border: 1px solid rgba(0, 242, 254, 0.25);
  border-radius: 14px;
  padding: 28px;
}
.uploading-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.upload-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(0, 242, 254, 0.2);
  border-top-color: #00f2fe;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.uploading-title {
  margin: 0 0 4px;
  font-size: 16px;
  color: #f8fafc;
}
.uploading-filename {
  margin: 0;
  font-size: 13px;
  color: #38bdf8;
  font-family: 'Courier New', monospace;
}

/* 进度条 */
.progress-wrapper {
  margin-bottom: 20px;
}
.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
}
.progress-status { color: #cbd5e1; }
.progress-percentage { color: #00f2fe; font-weight: 700; font-family: monospace; }

.progress-bar-bg {
  height: 10px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 5px;
  overflow: hidden;
  position: relative;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00f2fe 0%, #38bdf8 100%);
  border-radius: 5px;
  transition: width 0.2s linear;
  position: relative;
}
.progress-glow {
  position: absolute;
  top: 0; right: 0; bottom: 0; width: 30px;
  background: rgba(255, 255, 255, 0.5);
  filter: blur(4px);
}

.progress-metrics {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
}

.uploading-actions {
  display: flex;
  justify-content: flex-end;
}

/* 上传完成卡片 */
.completed-zone {
  background: rgba(10, 25, 47, 0.7);
  border: 1px solid rgba(52, 211, 153, 0.3);
  border-radius: 14px;
  padding: 24px;
}
.success-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}
.success-icon-badge {
  width: 44px;
  height: 44px;
  background: rgba(52, 211, 153, 0.15);
  border: 2px solid #34d399;
  border-radius: 50%;
  color: #34d399;
  font-size: 22px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}
.success-header h3 {
  margin: 0 0 4px;
  font-size: 18px;
  color: #ffffff;
}
.success-subtext {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}

/* 电子凭证卡片 */
.dataset-ticket-card {
  background: rgba(2, 11, 24, 0.9);
  border: 1px dashed rgba(0, 242, 254, 0.4);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: inset 0 0 15px rgba(0, 242, 254, 0.05);
}
.ticket-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.category-pill {
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 4px;
  margin-right: 8px;
}
.category-hazmat { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
.category-bus { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
.category-coach { background: rgba(14, 165, 233, 0.2); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.4); }

.vehicle-model {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
}
.ticket-status-badge {
  font-size: 11px;
  color: #34d399;
  background: rgba(52, 211, 153, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid rgba(52, 211, 153, 0.3);
}

.ticket-id-box {
  background: rgba(0, 242, 254, 0.06);
  border: 1px solid rgba(0, 242, 254, 0.25);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}
.id-label {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.id-value-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.dataset-id {
  font-size: 18px;
  font-weight: 800;
  color: #00f2fe;
  font-family: 'Courier New', Courier, monospace;
  letter-spacing: 1px;
}
.btn-copy {
  background: rgba(0, 242, 254, 0.15);
  border: 1px solid rgba(0, 242, 254, 0.4);
  color: #00f2fe;
  font-size: 12px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-copy:hover {
  background: #00f2fe;
  color: #020c1b;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}
.meta-item {
  background: rgba(255, 255, 255, 0.03);
  padding: 8px 12px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
}
.meta-lbl {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 2px;
}
.meta-val {
  font-size: 13px;
  color: #e2e8f0;
  font-weight: 500;
}
.text-yellow { color: #fbbf24; }
.text-cyan { color: #00f2fe; }
.text-blue { color: #38bdf8; }
.text-green { color: #34d399; }
.font-mono { font-family: monospace; font-size: 12px; }

.completed-actions {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
}

/* Toast 提示 */
.error-toast {
  position: fixed;
  bottom: 30px;
  right: 30px;
  background: rgba(239, 68, 68, 0.95);
  color: #ffffff;
  padding: 12px 18px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 10px 25px rgba(239, 68, 68, 0.4);
  z-index: 9999;
  font-size: 13.5px;
}
.toast-close {
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 16px;
  cursor: pointer;
}

.toast-fade-enter-active, .toast-fade-leave-active { transition: all 0.3s ease; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateY(10px); }
</style>
