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

          <div class="action-buttons-grid">
            <div class="action-btn-card">
              <button class="btn btn-primary btn-block" @click="triggerFileInput">
                <span class="btn-icon">📦</span> 选择数据集压缩包
              </button>
              <div class="preset-default-row" @click="loadPresetZip" title="点击一键直接载入默认压缩包">
                <span class="preset-label">默认路径:</span>
                <code class="preset-path">Dashboard/zip</code>
                <span class="quick-badge">⚡ 一键载入</span>
              </div>
            </div>

            <div class="action-btn-card">
              <button class="btn btn-secondary btn-block" @click="triggerFolderInput">
                <span class="btn-icon">📂</span> 选择图片文件夹
              </button>
              <div class="preset-default-row" @click="loadPresetImages" title="点击一键直接载入默认图片集">
                <span class="preset-label">默认路径:</span>
                <code class="preset-path">Dashboard/images2</code>
                <span class="quick-badge">⚡ 一键载入</span>
              </div>
            </div>
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

          <!-- 详细元数据网格 (区分无人机/无人车视角图像数量) -->
          <div class="metadata-grid">
            <div class="meta-item">
              <span class="meta-lbl">事故归属类型</span>
              <span class="meta-val text-yellow">{{ datasetResult.accidentCategory }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-lbl">包含图像总帧数</span>
              <span class="meta-val text-cyan">{{ datasetResult.imageCount }} 张多视角帧</span>
            </div>
            <div class="meta-item highlight-uav-item">
              <span class="meta-lbl">🚁 无人机(UAV)视角图像数</span>
              <span class="meta-val text-uav"><b>{{ datasetResult.uavCount }}</b> 张 (高空/俯瞰/倾斜)</span>
            </div>
            <div class="meta-item highlight-ugv-item">
              <span class="meta-lbl">🚜 无人车(UGV)视角图像数</span>
              <span class="meta-val text-amber"><b>{{ datasetResult.ugvCount }}</b> 张 (地面/近景/特写)</span>
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

        <!-- 【步骤一交互增强】：已导入多视角图像预览集 (按无人机/无人车视角分类) -->
        <div class="image-gallery-section">
          <div class="gallery-header">
            <div class="gallery-title-box">
              <span class="gallery-icon">📸</span>
              <div>
                <h4 class="gallery-title">已导入“两客一危”事故车辆多视角图像集</h4>
                <p class="gallery-subtitle">
                  拆解视角: <b>🚁 无人机视角 ({{ uavImageList.length }} 帧)</b> | <b>🚜 无人车视角 ({{ ugvImageList.length }} 帧)</b> | 点击筛选分类与放大
                </p>
              </div>
            </div>

            <!-- 无人机/无人车视角分类切换卡 -->
            <div class="gallery-filter-tabs">
              <button 
                class="filter-tab" 
                :class="{ active: perspectiveFilter === 'all' }"
                @click="perspectiveFilter = 'all'"
              >
                全部视角 ({{ imagePreviewList.length }})
              </button>
              <button 
                class="filter-tab tab-uav-filter" 
                :class="{ active: perspectiveFilter === 'uav' }"
                @click="perspectiveFilter = 'uav'"
              >
                🚁 无人机(UAV)视角 ({{ uavImageList.length }})
              </button>
              <button 
                class="filter-tab tab-ugv-filter" 
                :class="{ active: perspectiveFilter === 'ugv' }"
                @click="perspectiveFilter = 'ugv'"
              >
                🚜 无人车(UGV)视角 ({{ ugvImageList.length }})
              </button>
            </div>
          </div>

          <div class="thumbnail-grid">
            <div 
              v-for="(img, idx) in filteredImageList" 
              :key="idx" 
              class="thumb-card"
              @click="openImageViewer(imagePreviewList.indexOf(img))"
              title="点击查看全图与视角参数"
            >
              <div class="thumb-img-wrapper">
                <img :src="img.url" :alt="img.name" class="thumb-img" />
                <div class="thumb-overlay">
                  <span class="zoom-btn">🔍 点击查看大图</span>
                </div>
                <span class="thumb-angle-tag" :class="img.tagClass">{{ img.angleTag }}</span>
              </div>
              <div class="thumb-info">
                <span class="thumb-name" :title="img.name">{{ img.name }}</span>
                <span class="thumb-meta">{{ img.res }} | {{ img.size }}</span>
              </div>
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

    <!-- 🖼️ 图片大图放大查看器 Modal (Lightbox Viewer) -->
    <transition name="modal-fade">
      <div v-if="activePreviewIndex !== null" class="image-viewer-modal" @click.self="closeImageViewer">
        <div class="viewer-dialog">
          <div class="viewer-header">
            <div class="viewer-title-group">
              <span class="viewer-icon">📷</span>
              <span class="viewer-filename">{{ currentPreviewImage?.name }}</span>
              <span class="viewer-tag" :class="currentPreviewImage?.tagClass">{{ currentPreviewImage?.angleTag }}</span>
            </div>
            <button class="viewer-close-btn" @click="closeImageViewer" title="关闭预览 (Esc)">✕</button>
          </div>

          <div class="viewer-body">
            <button 
              class="nav-btn prev-btn" 
              @click="prevImage" 
              :disabled="activePreviewIndex === 0"
              title="上一张图片"
            >
              ❮
            </button>
            
            <div class="main-image-wrapper">
              <img :src="currentPreviewImage?.url" :alt="currentPreviewImage?.name" class="main-preview-img" />
            </div>

            <button 
              class="nav-btn next-btn" 
              @click="nextImage" 
              :disabled="activePreviewIndex === imagePreviewList.length - 1"
              title="下一张图片"
            >
              ❯
            </button>
          </div>

          <div class="viewer-footer">
            <div class="meta-row">
              <span class="meta-chip">分辨率: <b>{{ currentPreviewImage?.res }}</b></span>
              <span class="meta-chip">大小: <b>{{ currentPreviewImage?.size }}</b></span>
              <span class="meta-chip">采集设备: <b>{{ currentPreviewImage?.device }}</b></span>
              <span class="meta-chip">视角方位: <b>{{ currentPreviewImage?.perspective }}</b></span>
            </div>
            <div class="viewer-counter">
              <b>{{ activePreviewIndex + 1 }}</b> / {{ imagePreviewList.length }}
            </div>
          </div>
        </div>
      </div>
    </transition>

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

// 📸 图像预览与放大查看器状态
const imagePreviewList = ref([])
const activePreviewIndex = ref(null)
const perspectiveFilter = ref('all') // 'all' | 'uav' | 'ugv'
let rawUploadedFiles = []

const uavImageList = computed(() => {
  return imagePreviewList.value.filter(img => img.perspectiveType === 'uav')
})

const ugvImageList = computed(() => {
  return imagePreviewList.value.filter(img => img.perspectiveType === 'ugv')
})

const filteredImageList = computed(() => {
  if (perspectiveFilter.value === 'uav') return uavImageList.value
  if (perspectiveFilter.value === 'ugv') return ugvImageList.value
  return imagePreviewList.value
})

const currentPreviewImage = computed(() => {
  if (activePreviewIndex.value === null || !imagePreviewList.value.length) return null
  return imagePreviewList.value[activePreviewIndex.value]
})

const openImageViewer = (index) => {
  activePreviewIndex.value = index
}

const closeImageViewer = () => {
  activePreviewIndex.value = null
}

const prevImage = () => {
  if (activePreviewIndex.value > 0) {
    activePreviewIndex.value--
  }
}

const nextImage = () => {
  if (activePreviewIndex.value < imagePreviewList.value.length - 1) {
    activePreviewIndex.value++
  }
}

// 默认预设演示图片集 (包含无人机/无人车多视角高精图像)
const defaultPresetImages = [
  {
    name: 'UAV_Cam_01_Overview.png',
    url: '/Dashboard/images2/uav_aerial_photo.png',
    size: '0.91 MB',
    res: '4096 x 2160',
    angleTag: 'UAV 4K 俯瞰帧',
    tagClass: 'tag-uav',
    perspectiveType: 'uav',
    device: 'DJI M300 RTK 搭载 Zenmuse H20T',
    perspective: '俯瞰正交全景 (Pitch: -90°)'
  },
  {
    name: 'UAV_Ground_02_SideAngle.png',
    url: '/Dashboard/images2/tanker_aerial_photo.png',
    size: '0.94 MB',
    res: '3840 x 2160',
    angleTag: 'UAV 45° 倾斜帧',
    tagClass: 'tag-uav',
    perspectiveType: 'uav',
    device: 'DJI M300 RTK 搭载 Zenmuse H20T',
    perspective: '侧前方45度视角 (Pitch: -45°)'
  },
  {
    name: 'UGV_Impact_Detail_03.png',
    url: '/Dashboard/images2/tanker-accident-detection.png',
    size: '0.86 MB',
    res: '1920 x 1080',
    angleTag: 'UGV 地面撞击近景帧',
    tagClass: 'tag-ugv',
    perspectiveType: 'ugv',
    device: '1号无人侦察车 激光与光学防爆摄像头',
    perspective: '罐体前侧碰撞深度凹陷区'
  },
  {
    name: 'UAV_Feature_Matching_04.png',
    url: '/Dashboard/images2/story-accident-detection.png',
    size: '3.12 MB',
    res: '3840 x 2160',
    angleTag: 'UAV 多视角匹配帧',
    tagClass: 'tag-uav',
    perspectiveType: 'uav',
    device: '边缘计算节点 SIFT 特征云端融合',
    perspective: '多维坐标匹配与密集点云对齐'
  },
  {
    name: 'UGV_Leak_Area_Detail_05.png',
    url: '/Dashboard/images2/tanker-leak-detection.png',
    size: '2.68 MB',
    res: '2560 x 1440',
    angleTag: 'UGV 泄漏处特写帧',
    tagClass: 'tag-ugv',
    perspectiveType: 'ugv',
    device: '1号无人侦察车 防爆气体/红外监控',
    perspective: '罐体阀门与右侧板撕裂口近景'
  },
  {
    name: 'UAV_Diffusion_Panorama_06.png',
    url: '/Dashboard/images2/tanker-diffusion-detection.png',
    size: '4.18 MB',
    res: '3840 x 2160',
    angleTag: 'UAV 扩散全景视角帧',
    tagClass: 'tag-uav',
    perspectiveType: 'uav',
    device: '无人机高空长焦红外相机',
    perspective: '现场次生灾害气体扩散边界'
  },
  {
    name: 'UGV_Thermal_Infrared_07.png',
    url: '/Dashboard/images2/story-fire-detection.png',
    size: '2.80 MB',
    res: '1920 x 1080',
    angleTag: 'UGV 热成像光谱融合帧',
    tagClass: 'tag-ugv',
    perspectiveType: 'ugv',
    device: '1号无人侦察车 FLIR 热成像仪',
    perspective: '事故车辆受损区域热红外温差'
  }
]

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

// ⚡ 一键载入默认示例数据集包 (public/Dashboard/zip)
const loadPresetZip = () => {
  currentFileName.value = 'accident_truck_dataset.zip (默认示范包: public/Dashboard/zip)'
  startSimulatedUpload({
    filename: 'accident_truck_dataset.zip',
    imageCount: 248,
    fileSizeMB: '156.8',
    prefix: 'LK-COACH',
    presetInfo: {
      source: 'public/Dashboard/zip/accident_truck_dataset.zip',
      modelType: '仙桃市追尾事故客车'
    }
  })
}

// ⚡ 一键载入默认示例图片集 (public/Dashboard/images2)
const loadPresetImages = () => {
  currentFileName.value = '[多视角图片集] public/Dashboard/images2/'
  startSimulatedUpload({
    filename: 'public/Dashboard/images2/',
    imageCount: 180,
    fileSizeMB: '94.2',
    prefix: 'LK-HAZMAT',
    presetInfo: {
      source: 'public/Dashboard/images2/',
      modelType: '重型危化品槽罐车'
    }
  })
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

  // 校验通过，记录文件并启动传输动画
  rawUploadedFiles = files
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

  // 📷 填充多视角图像预览列表
  const localImageFiles = rawUploadedFiles.filter(f => {
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    return ['.jpg', '.jpeg', '.png', '.webp', '.bmp'].includes(ext)
  })

  if (localImageFiles.length > 0) {
    imagePreviewList.value = localImageFiles.map((file, idx) => {
      const isUav = idx % 2 === 0
      return {
        name: file.name,
        url: URL.createObjectURL(file),
        size: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
        res: '3840 x 2160',
        angleTag: isUav ? 'UAV 4K 视角' : 'UGV 地面视角',
        tagClass: isUav ? 'tag-uav' : 'tag-ugv',
        perspectiveType: isUav ? 'uav' : 'ugv',
        device: isUav ? 'DJI M300 RTK 搭载 Zenmuse H20T' : '1号无人侦察车 (UGV)',
        perspective: `环绕视角 #${idx + 1} (${(idx * 35) % 360}° 方位角)`
      }
    })
  } else {
    imagePreviewList.value = defaultPresetImages
  }
  
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

  const totalCount = imageCount || 342
  const ratioUav = uavImageList.value.length / (imagePreviewList.value.length || 1)
  const uavCountVal = Math.round(totalCount * ratioUav)
  const ugvCountVal = totalCount - uavCountVal

  datasetResult.value = {
    id: datasetId,
    categoryLabel,
    categoryClass,
    vehicleModel,
    accidentCategory,
    imageCount: totalCount,
    uavCount: uavCountVal,
    ugvCount: ugvCountVal,
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

.action-buttons-grid {
  display: flex;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
  max-width: 680px;
  margin: 0 auto;
}

.action-btn-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 280px;
}

.btn-block {
  width: 100%;
  justify-content: center;
}

.preset-default-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.65);
  border: 1px dashed rgba(0, 242, 254, 0.35);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 11.5px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
}

.preset-default-row:hover {
  background: rgba(0, 242, 254, 0.1);
  border-color: #00f2fe;
  color: #f1f5f9;
}

.preset-path {
  color: #38bdf8;
  font-family: "Consolas", monospace;
  font-size: 11px;
}

.quick-badge {
  color: #00ffaa;
  font-weight: bold;
  font-size: 11px;
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
.text-uav { color: #00f2fe; }
.text-amber { color: #fbbf24; }
.font-mono { font-family: monospace; font-size: 12px; }

.highlight-uav-item {
  background: rgba(0, 242, 254, 0.06) !important;
  border: 1px solid rgba(0, 242, 254, 0.3) !important;
}

.highlight-ugv-item {
  background: rgba(251, 191, 36, 0.06) !important;
  border: 1px solid rgba(251, 191, 36, 0.3) !important;
}

.gallery-filter-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 4px;
  border-radius: 8px;
}

.filter-tab {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 11.5px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-tab:hover {
  color: #f8fafc;
  background: rgba(255, 255, 255, 0.06);
}

.filter-tab.active {
  background: #00f2fe;
  color: #020712;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
}

.filter-tab.tab-uav-filter.active {
  background: #00f2fe;
  color: #020712;
}

.filter-tab.tab-ugv-filter.active {
  background: #fbbf24;
  color: #020712;
}

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

/* 📸 图像预览集与查看器样式 */
.image-gallery-section {
  margin-top: 20px;
  margin-bottom: 24px;
  background: rgba(2, 11, 24, 0.7);
  border: 1px solid rgba(0, 242, 254, 0.2);
  border-radius: 12px;
  padding: 16px 20px;
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.gallery-title-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

.gallery-icon {
  font-size: 22px;
}

.gallery-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #00f2fe;
}

.gallery-subtitle {
  margin: 2px 0 0 0;
  font-size: 11.5px;
  color: #94a3b8;
}

.gallery-badge {
  font-size: 11px;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  padding: 3px 10px;
  border-radius: 20px;
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.thumbnail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(145px, 1fr));
  gap: 12px;
  max-height: 280px;
  overflow-y: auto;
  padding-right: 4px;
}

.thumb-card {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
}

.thumb-card:hover {
  transform: translateY(-3px);
  border-color: #00f2fe;
  box-shadow: 0 8px 20px rgba(0, 242, 254, 0.25);
}

.thumb-img-wrapper {
  position: relative;
  width: 100%;
  height: 95px;
  background: #090f1d;
  overflow: hidden;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.thumb-card:hover .thumb-img {
  transform: scale(1.08);
}

.thumb-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(2, 12, 27, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.thumb-card:hover .thumb-overlay {
  opacity: 1;
}

.zoom-btn {
  font-size: 11px;
  font-weight: 600;
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.2);
  border: 1px solid #00f2fe;
  padding: 3px 8px;
  border-radius: 4px;
  backdrop-filter: blur(4px);
}

.thumb-angle-tag {
  position: absolute;
  bottom: 4px;
  left: 4px;
  font-size: 9.5px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  backdrop-filter: blur(4px);
}
.tag-uav { background: rgba(0, 242, 254, 0.85); color: #020712; }
.tag-ugv { background: rgba(251, 191, 36, 0.85); color: #020712; }
.tag-feature { background: rgba(52, 211, 153, 0.85); color: #020712; }
.tag-thermal { background: rgba(248, 113, 113, 0.85); color: #020712; }

.thumb-info {
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: rgba(8, 15, 30, 0.9);
}

.thumb-name {
  font-size: 11px;
  color: #e2e8f0;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.thumb-meta {
  font-size: 10px;
  color: #64748b;
  font-family: monospace;
}

/* 🖼️ 大图查看器 Lightbox Modal */
.image-viewer-modal {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(2, 7, 18, 0.92);
  backdrop-filter: blur(12px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.viewer-dialog {
  width: 960px;
  max-width: 95vw;
  max-height: 92vh;
  background: #091122;
  border: 1px solid rgba(0, 242, 254, 0.4);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.9), 0 0 30px rgba(0, 242, 254, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.viewer-header {
  padding: 14px 20px;
  background: #0f172a;
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.viewer-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.viewer-icon { font-size: 18px; }
.viewer-filename { font-size: 14px; font-weight: 700; color: #ffffff; font-family: monospace; }
.viewer-tag { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; }

.viewer-close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 20px;
  cursor: pointer;
  transition: color 0.2s;
}
.viewer-close-btn:hover { color: #f87171; }

.viewer-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #040914;
  position: relative;
  overflow: hidden;
}

.main-image-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  max-height: 65vh;
  overflow: hidden;
}

.main-preview-img {
  max-width: 100%;
  max-height: 65vh;
  object-fit: contain;
  border-radius: 6px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8), 0 0 15px rgba(0, 242, 254, 0.15);
}

.nav-btn {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(0, 242, 254, 0.3);
  color: #00f2fe;
  font-size: 20px;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  z-index: 10;
  margin: 0 10px;
}
.nav-btn:hover:not(:disabled) {
  background: #00f2fe;
  color: #020712;
  box-shadow: 0 0 15px rgba(0, 242, 254, 0.5);
}
.nav-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
  border-color: #334155;
  color: #64748b;
}

.viewer-footer {
  padding: 12px 20px;
  background: #0f172a;
  border-top: 1px solid #1e293b;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-row {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #94a3b8;
}
.meta-chip b { color: #00f2fe; }

.viewer-counter {
  font-size: 13px;
  color: #cbd5e1;
  font-family: monospace;
}
.viewer-counter b { color: #00f2fe; font-size: 15px; }

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.25s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
</style>
