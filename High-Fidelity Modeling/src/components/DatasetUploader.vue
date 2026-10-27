<template>
  <section class="dataset-catalog" :class="{ 'gallery-open': Boolean(activeGallery) }">
    <div class="catalog-layout">
      <div class="catalog-main">
        <header class="catalog-header">
          <div>
            <h2>选择场景</h2>
          </div>
          <div class="catalog-status" :class="{ ready: !loading && !error }">
            <span class="status-indicator"></span>
            {{ loading ? '正在读取数据' : error ? '数据暂不可用' : `${datasets.length} 个演示，可导入空地数据集进行重建` }}
          </div>
        </header>

        <div v-if="loading" class="catalog-message">
          <div class="loading-ring"></div>
          <span>正在读取 UAV / UGV 文件清单…</span>
        </div>

        <div v-else-if="error" class="catalog-message error-message">
          <span class="message-icon">!</span>
          <div>
            <strong>场景数据暂不可用</strong>
            <p>{{ error }}</p>
            <p class="error-hint">请联系管理员检查场景数据配置。</p>
          </div>
        </div>

        <div v-else-if="datasets.length === 0" class="catalog-message">
          <span>目录中还没有可导入的数据集。</span>
        </div>

        <div v-else class="dataset-grid">
          <article v-for="dataset in datasets" :key="dataset.id" class="dataset-card">
            <div class="dataset-card-top">
              <div class="dataset-title-block">
                <span class="dataset-kind" :class="`kind-${dataset.id}`">{{ dataset.vehicleType === 'coach' ? '客运车辆' : '危化品运输' }}</span>
                <h3>{{ dataset.title }}</h3>
              </div>
              <div class="total-count">
                <strong>{{ formatNumber(dataset.counts.total) }}</strong>
                <span>{{ dataset.captureType === 'synthetic' ? '张合成视角' : '张照片' }}</span>
              </div>
            </div>

            <div class="source-counts">
              <div class="count-cell uav-cell">
                <span class="count-label">{{ captureCountLabel(dataset, 'uav') }}</span>
                <strong>{{ formatNumber(dataset.counts.uav) }}</strong>
                <span>张</span>
              </div>
              <div class="count-cell ugv-cell">
                <span class="count-label">{{ captureCountLabel(dataset, 'ugv') }}</span>
                <strong>{{ formatNumber(dataset.counts.ugv) }}</strong>
                <span>张</span>
              </div>
            </div>

            <div class="sample-section">
              <div class="section-heading">
                <span>{{ dataset.captureType === 'synthetic' ? '合成视角样例' : '现场影像' }}</span>
                <button class="gallery-link-button" type="button" @click="openDatasetGallery(dataset)">查看影像集 <span aria-hidden="true">↗</span></button>
              </div>
              <div class="sample-grid">
                <figure v-for="sample in dataset.samples" :key="sample.url" class="sample-tile">
                  <img :src="sample.url" :alt="captureSampleAlt(dataset, sample.kind)" loading="lazy" />
                  <figcaption :class="`sample-${sample.kind}`">{{ captureSampleLabel(dataset, sample.kind) }}</figcaption>
                </figure>
                <div v-if="dataset.samples.length === 0" class="no-samples">{{ dataset.captureType === 'synthetic' ? '暂无合成视角' : '暂无现场影像' }}</div>
              </div>
            </div>

            <button class="import-button" type="button" @click="selectDataset(dataset)">
              导入数据并重建
              <span aria-hidden="true">→</span>
            </button>
          </article>
        </div>

        <section class="custom-scene-panel" :class="{ expanded: showCustomForm }">
          <div class="custom-scene-summary">
            <div>
              <span class="custom-scene-kicker">新增场景</span>
              <h3>空地数据集</h3>
              <p>选择场景文件夹，系统自动运行重建并展示模型及其纹理。</p>
            </div>
            <button class="custom-toggle-button" type="button" @click="toggleCustomForm">
              {{ showCustomForm ? '收起' : '导入空地数据集' }}
              <span aria-hidden="true">{{ showCustomForm ? '−' : '+' }}</span>
            </button>
          </div>

          <form v-if="showCustomForm" class="custom-scene-form" @submit.prevent="importCustomScene">
            <label class="custom-field custom-name-field">
              <span>场景名称 <b>*</b></span>
              <input v-model.trim="customTitle" maxlength="48" placeholder="选择文件夹后自动使用文件夹名称，也可自行修改" @input="markCustomTitleEdited" required />
            </label>

            <label class="custom-field">
              <span>模型竖直轴</span>
              <select v-model="customUpAxis">
                <option value="z">Z 轴向上</option>
                <option value="y">Y 轴向上</option>
              </select>
            </label>

            <div class="custom-folder-picker">
              <input ref="folderInput" class="custom-file-input" type="file" webkitdirectory directory multiple aria-hidden="true" tabindex="-1" @change="readCustomFolder" />
              <button class="custom-file-button folder-pick-button" type="button" @click="folderInput?.click()">
                {{ customFolderData ? '重新选择场景文件夹' : '选择场景文件夹' }}
              </button>
              <span class="custom-file-state">{{ customFolderData ? '已读取文件夹内容' : '必选 · 文件名不会显示在场景页' }}</span>
            </div>

            <div v-if="customFolderData" class="custom-association-summary">
              <span><b>UAV</b> {{ formatNumber(customFolderData.counts.uav) }} 张</span>
              <span><b>UGV</b> {{ formatNumber(customFolderData.counts.ugv) }} 张</span>
              <button class="gallery-link-button" type="button" :disabled="!hasCustomCaptureImages" @click="openCustomGallery">查看影像集 <span aria-hidden="true">↗</span></button>
            </div>

            <div class="custom-form-footer">
              <div>
                <p v-if="customImportError" class="custom-import-error" role="alert">{{ customImportError }}</p>
                <p v-else class="custom-local-note">自动选择网格面数最多的 PLY，并按纹理引用/目录分类关联资源；文件仅本地读取，不上传。</p>
              </div>
              <button class="import-button custom-import-button" type="submit" :disabled="customBusy || !customTitle.trim() || !customFolderData">
                {{ customBusy ? '正在整理场景' : '导入文件夹并重建' }}
                <span aria-hidden="true">→</span>
              </button>
            </div>
          </form>
        </section>
      </div>

      <Transition name="gallery-slide">
        <aside v-if="activeGallery" class="capture-gallery-panel" aria-label="场景视角影像集">
          <header class="gallery-panel-header">
            <div class="gallery-panel-title">
              <h3>{{ activeGallery.title }}</h3>
            </div>
            <button class="gallery-close-button" type="button" aria-label="关闭影像集" @click="closeGallery">×</button>
          </header>

          <nav class="gallery-tabs" aria-label="视角类型">
            <button type="button" :class="{ active: activeGalleryTab === 'uav' }" @click="setGalleryTab('uav')">UAV 视角</button>
            <button type="button" :class="{ active: activeGalleryTab === 'ugv' }" @click="setGalleryTab('ugv')">UGV 视角</button>
            <button type="button" :class="{ active: activeGalleryTab === 'joint' }" @click="setGalleryTab('joint')">联合视角</button>
          </nav>

          <div v-if="activeGalleryTab === 'joint'" class="joint-gallery-content">
            <CaptureViewJoint3D :uav-count="activeGallery.counts.uav" :ugv-count="activeGallery.counts.ugv" :vehicle-type="activeGallery.vehicleType" />
          </div>

          <template v-else>
            <div class="gallery-list-heading">
              <strong>{{ activeGalleryTab === 'uav' ? 'UAV 航拍影像' : 'UGV 地面影像' }}</strong>
              <span>{{ formatNumber(galleryItems.length) }} 张</span>
            </div>
            <div v-if="galleryItems.length" class="gallery-thumbnail-grid">
              <button v-for="item in galleryPageItems" :key="item.key" class="gallery-thumbnail" type="button" :aria-label="`查看${activeGalleryTab === 'uav' ? 'UAV' : 'UGV'}第 ${item.sequence} 张原图`" @click="openOriginal(item)">
                <span class="thumbnail-image-frame">
                  <img v-if="thumbnailStates[item.key] === 'ready'" :src="thumbnailUrls[item.key]" alt="" loading="lazy" />
                  <span v-else-if="thumbnailStates[item.key] === 'error'" class="thumbnail-placeholder">预览不可用</span>
                  <span v-else class="thumbnail-placeholder"><i class="loading-ring"></i></span>
                </span>
                <span class="thumbnail-caption">{{ activeGalleryTab === 'uav' ? 'UAV' : 'UGV' }} · {{ String(item.sequence).padStart(3, '0') }}</span>
              </button>
            </div>
            <div v-else class="gallery-empty-state">该视角组暂无图像。</div>

            <footer v-if="galleryItems.length > galleryPageSize" class="gallery-pagination">
              <button type="button" :disabled="galleryPage <= 1" @click="galleryPage -= 1">上一页</button>
              <span>{{ galleryPage }} / {{ galleryPageCount }}</span>
              <button type="button" :disabled="galleryPage >= galleryPageCount" @click="galleryPage += 1">下一页</button>
            </footer>
          </template>
        </aside>
      </Transition>
    </div>

    <div v-if="previewItem" class="original-preview-overlay" role="presentation" @click.self="closeOriginal">
      <section class="original-preview-dialog" role="dialog" aria-modal="true" aria-label="原始分辨率影像">
        <header class="original-preview-header">
          <div>
            <span>{{ previewItem.kind === 'uav' ? 'UAV 原图' : 'UGV 原图' }}</span>
            <strong>{{ String(previewItem.sequence).padStart(3, '0') }} / {{ formatNumber(galleryItems.length) }}</strong>
          </div>
          <button type="button" aria-label="关闭原图" @click="closeOriginal">×</button>
        </header>
        <div class="original-preview-image-wrap">
          <img :src="previewUrl" :alt="previewItem.kind === 'uav' ? 'UAV 原始分辨率影像' : 'UGV 原始分辨率影像'" />
        </div>
        <footer class="original-preview-footer">
          <button type="button" :disabled="galleryItems.length < 2" @click="stepOriginal(-1)">上一张</button>
          <span>原始分辨率</span>
          <button type="button" :disabled="galleryItems.length < 2" @click="stepOriginal(1)">下一张</button>
        </footer>
      </section>
    </div>

    <div v-if="showImportModeDialog" class="import-choice-overlay">
      <section class="import-choice-dialog" role="dialog" aria-modal="true" aria-labelledby="import-choice-title">
        <h3 id="import-choice-title">检测到已有 PLY 模型，是否直接展示？</h3>
        <div class="import-choice-actions">
          <button type="button" class="import-choice-secondary" @click="confirmCustomImport(false)">继续重建流程</button>
          <button type="button" class="import-choice-primary" @click="confirmCustomImport(true)">直接展示</button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import CaptureViewJoint3D from './CaptureViewJoint3D.vue'

defineProps({
  datasets: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

const emit = defineEmits(['dataset-ready'])

const showCustomForm = ref(false)
const customTitle = ref('')
const customTitleManuallyEdited = ref(false)
const customUpAxis = ref('z')
const customBusy = ref(false)
const showImportModeDialog = ref(false)
const customImportError = ref('')
const folderInput = ref(null)
const customFolderData = ref(null)
const activeGallery = ref(null)
const activeGalleryTab = ref('uav')
const galleryPage = ref(1)
const galleryPageSize = 9
const thumbnailUrls = ref({})
const thumbnailStates = ref({})
const previewItem = ref(null)
const previewUrl = ref('')
let previewObjectUrl = ''
let galleryGeneration = 0
const thumbnailCache = new Map()

const hasCustomCaptureImages = computed(() => Boolean(customFolderData.value?.counts.uav || customFolderData.value?.counts.ugv))
const galleryItems = computed(() => activeGallery.value?.groups?.[activeGalleryTab.value] || [])
const galleryPageItems = computed(() => {
  const start = (galleryPage.value - 1) * galleryPageSize
  return galleryItems.value.slice(start, start + galleryPageSize)
})
const galleryPageCount = computed(() => Math.max(1, Math.ceil(galleryItems.value.length / galleryPageSize)))

const formatNumber = (value) => Number(value || 0).toLocaleString('zh-CN')
const captureCountLabel = (dataset, kind) => dataset.captureType === 'synthetic'
  ? kind === 'uav' ? '仿真 UAV 视角' : '仿真 UGV 视角'
  : kind === 'uav' ? 'UAV 航拍' : 'UGV 地面'
const captureSampleLabel = (dataset, kind) => dataset.captureType === 'synthetic'
  ? kind === 'uav' ? '仿真 UAV' : '仿真 UGV'
  : kind === 'uav' ? '航拍' : '地面'
const captureSampleAlt = (dataset, kind) => dataset.captureType === 'synthetic'
  ? kind === 'uav' ? '仿真无人机视角图像样例' : '仿真地面视角图像样例'
  : kind === 'uav' ? '无人机航拍影像样例' : '地面采集影像样例'

const buildDatasetGalleryItems = (dataset, kind) => {
  const images = Array.isArray(dataset.images) ? dataset.images.filter(image => image.kind === kind) : []
  const source = images.length ? images : (dataset.samples || []).filter(image => image.kind === kind)
  return source.map((image, index) => ({
    key: `${dataset.id}:${kind}:${index}`,
    kind,
    sequence: index + 1,
    url: image.url
  }))
}

const inferVehicleType = (title, fallback = 'generic') => {
  if (/(油罐|危化|tanker)/i.test(title || '')) return 'oil-tanker'
  if (/(客车|大巴|公交|coach|bus)/i.test(title || '')) return 'coach'
  return fallback
}

const openGallery = (gallery) => {
  activeGallery.value = gallery
  activeGalleryTab.value = gallery.counts.uav ? 'uav' : 'ugv'
  galleryPage.value = 1
}

const openDatasetGallery = (dataset) => {
  openGallery({
    id: dataset.id,
    title: dataset.title,
    vehicleType: inferVehicleType(dataset.title, dataset.vehicleType),
    counts: { uav: Number(dataset.counts?.uav || 0), ugv: Number(dataset.counts?.ugv || 0) },
    groups: {
      uav: buildDatasetGalleryItems(dataset, 'uav'),
      ugv: buildDatasetGalleryItems(dataset, 'ugv')
    }
  })
}

const sortedFiles = (files) => [...files].sort((left, right) => normalizeRelativePath(left).localeCompare(normalizeRelativePath(right), 'zh-CN', { numeric: true, sensitivity: 'base' }))

const openCustomGallery = () => {
  if (!customFolderData.value) return
  const customId = 'custom-folder-preview'
  const toGalleryItems = (files, kind) => sortedFiles(files).map((file, index) => ({
    key: `${customId}:${kind}:${index}:${normalizeRelativePath(file)}`,
    kind,
    sequence: index + 1,
    file
  }))
  openGallery({
    id: customId,
    title: customTitle.value.trim() || '自定义场景',
    vehicleType: inferVehicleType(customTitle.value),
    counts: { uav: customFolderData.value.counts.uav, ugv: customFolderData.value.counts.ugv },
    groups: {
      uav: toGalleryItems(customFolderData.value.uavFiles, 'uav'),
      ugv: toGalleryItems(customFolderData.value.ugvFiles, 'ugv')
    }
  })
}

const setGalleryTab = (tab) => {
  closeOriginal()
  activeGalleryTab.value = tab
  galleryPage.value = 1
}

const clearGalleryThumbnails = () => {
  galleryGeneration += 1
  thumbnailCache.forEach(url => URL.revokeObjectURL(url))
  thumbnailCache.clear()
  thumbnailUrls.value = {}
  thumbnailStates.value = {}
}

const closeOriginal = () => {
  if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl)
  previewObjectUrl = ''
  previewItem.value = null
  previewUrl.value = ''
}

const closeGallery = () => {
  closeOriginal()
  activeGallery.value = null
  clearGalleryThumbnails()
}

const openOriginal = (item) => {
  closeOriginal()
  previewItem.value = item
  if (item.file) {
    previewObjectUrl = URL.createObjectURL(item.file)
    previewUrl.value = previewObjectUrl
  } else {
    previewUrl.value = item.url
  }
}

const stepOriginal = (offset) => {
  if (!galleryItems.value.length || !previewItem.value) return
  const currentIndex = galleryItems.value.findIndex(item => item.key === previewItem.value.key)
  const nextIndex = (currentIndex + offset + galleryItems.value.length) % galleryItems.value.length
  openOriginal(galleryItems.value[nextIndex])
}

const makeThumbnail = async (item, generation) => {
  if (thumbnailCache.has(item.key)) {
    thumbnailStates.value = { ...thumbnailStates.value, [item.key]: 'ready' }
    return
  }

  thumbnailStates.value = { ...thumbnailStates.value, [item.key]: 'loading' }
  try {
    const responseBlob = item.file
      ? item.file
      : await fetch(item.url, { cache: 'force-cache' }).then(response => {
          if (!response.ok) throw new Error('Image request failed')
          return response.blob()
        })
    let bitmap
    try {
      bitmap = await createImageBitmap(responseBlob, { resizeWidth: 480, resizeQuality: 'high' })
    } catch {
      bitmap = await createImageBitmap(responseBlob)
    }
    if (generation !== galleryGeneration) {
      bitmap.close()
      return
    }

    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    const context = canvas.getContext('2d', { alpha: false })
    if (!context) throw new Error('Canvas is unavailable')
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    const thumbnailBlob = await new Promise((resolve, reject) => {
      canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Thumbnail encoding failed')), 'image/webp', 0.78)
    })
    if (generation !== galleryGeneration) return

    const thumbnailUrl = URL.createObjectURL(thumbnailBlob)
    thumbnailCache.set(item.key, thumbnailUrl)
    thumbnailUrls.value = { ...thumbnailUrls.value, [item.key]: thumbnailUrl }
    thumbnailStates.value = { ...thumbnailStates.value, [item.key]: 'ready' }
    while (thumbnailCache.size > 48) {
      const oldestKey = thumbnailCache.keys().next().value
      const oldestUrl = thumbnailCache.get(oldestKey)
      URL.revokeObjectURL(oldestUrl)
      thumbnailCache.delete(oldestKey)
      const nextUrls = { ...thumbnailUrls.value }
      delete nextUrls[oldestKey]
      thumbnailUrls.value = nextUrls
      if (!galleryPageItems.value.some(pageItem => pageItem.key === oldestKey)) {
        const nextStates = { ...thumbnailStates.value }
        delete nextStates[oldestKey]
        thumbnailStates.value = nextStates
      }
    }
  } catch {
    if (generation === galleryGeneration) thumbnailStates.value = { ...thumbnailStates.value, [item.key]: 'error' }
  }
}

const primeGalleryThumbnails = async () => {
  if (!activeGallery.value || activeGalleryTab.value === 'joint') return
  const generation = galleryGeneration
  const items = galleryPageItems.value
  let nextIndex = 0
  const worker = async () => {
    while (nextIndex < items.length && generation === galleryGeneration) {
      const item = items[nextIndex]
      nextIndex += 1
      await makeThumbnail(item, generation)
    }
  }
  await Promise.all(Array.from({ length: Math.min(3, items.length) }, worker))
}

watch(() => [activeGallery.value, activeGalleryTab.value, galleryPage.value], () => {
  void primeGalleryThumbnails()
}, { flush: 'post' })

onBeforeUnmount(() => {
  closeOriginal()
  clearGalleryThumbnails()
})

const selectDataset = (dataset) => {
  emit('dataset-ready', dataset)
}

const markCustomTitleEdited = () => {
  customTitleManuallyEdited.value = true
}

const toggleCustomForm = () => {
  showCustomForm.value = !showCustomForm.value
  customImportError.value = ''
}

const readPlyHeader = async (file) => {
  const headerText = await file.slice(0, 128 * 1024).text()
  const headerEnd = headerText.indexOf('end_header')
  if (!headerText.startsWith('ply') || headerEnd < 0) {
    throw new Error('所选文件不是可读取的 PLY 模型。')
  }

  const header = headerText.slice(0, headerEnd)
  const vertexCount = Number(header.match(/^element\s+vertex\s+(\d+)/m)?.[1] || 0)
  const faceCount = Number(header.match(/^element\s+face\s+(\d+)/m)?.[1] || 0)
  if (vertexCount < 1 || faceCount < 1) {
    throw new Error('PLY 中未找到顶点和三角面信息，请选择网格模型。')
  }

  const hasTextureCoordinates = /\btexcoord\b|^property\s+float\s+(u|v|s|t)\s*$/m.test(header)
  const hasVertexColors = ['red', 'green', 'blue'].every(channel => new RegExp(`^property\\s+\\w+\\s+${channel}\\s*$`, 'm').test(header))
  const textureFileReference = header.match(/^comment\s+TextureFile\s+(.+)$/im)?.[1]?.trim() || ''
  const upAxisHint = header.match(/^comment\s+(?:upAxis|up_axis)\s*[:=]?\s*([yz])\s*$/im)?.[1]?.toLowerCase() || ''
  return { vertexCount, faceCount, hasTextureCoordinates, hasVertexColors, textureFileReference, upAxisHint }
}

const normalizeRelativePath = (file) => String(file.webkitRelativePath || file.name || '').replace(/\\/g, '/').replace(/^\/+/, '')

const isThumbnailPath = (file) => /(^|\/)(?:thumbnails?|thumbs?)(?:\/|$)/i.test(normalizeRelativePath(file))

const imageKindFromPath = (file) => {
  const path = normalizeRelativePath(file).toLowerCase()
  const parts = path.split('/')
  const tags = [...parts.slice(1, -1), parts.at(-1) || ''].join('/')
  if (/(^|[^a-z0-9])(?:uav|aerial|drone|航拍)([^a-z0-9]|$)/i.test(tags)) return 'uav'
  if (/(^|[^a-z0-9])(?:ugv|ground|terrestrial|地面)([^a-z0-9]|$)/i.test(tags)) return 'ugv'
  return 'other'
}

const readSpatialMetadata = async (files, modelFile) => {
  const modelDirectory = normalizeRelativePath(modelFile).split('/').slice(0, -1)
  const metadataFiles = files.filter(file => /(^|\/)metadata\.xml$/i.test(normalizeRelativePath(file)))
  metadataFiles.sort((left, right) => {
    const leftDirectory = normalizeRelativePath(left).split('/').slice(0, -1)
    const rightDirectory = normalizeRelativePath(right).split('/').slice(0, -1)
    const commonPrefix = (parts) => parts.reduce((length, part, index) => modelDirectory[index] === part ? length + 1 : length, 0)
    const leftScore = commonPrefix(leftDirectory) * 100 - Math.abs(modelDirectory.length - leftDirectory.length)
    const rightScore = commonPrefix(rightDirectory) * 100 - Math.abs(modelDirectory.length - rightDirectory.length)
    return rightScore - leftScore
  })
  const metadataFile = metadataFiles[0]
  if (!metadataFile) return { isEnuMetric: false, hasMetricScale: false, scaleFactor: 1, unitLabel: '', scaleSource: '', upAxisHint: '', captureType: '', qualityReport: null }

  const xml = await metadataFile.text()
  const srs = xml.match(/<SRS>\s*([^<]+)\s*<\/SRS>/i)?.[1] || ''
  const axis = xml.match(/<UpAxis>\s*([yz])\s*<\/UpAxis>/i)?.[1]?.toLowerCase() || ''
  const captureType = xml.match(/<CaptureType>\s*([^<]+)\s*<\/CaptureType>/i)?.[1]?.trim().toLowerCase() || ''
  const isEnuMetric = /^\s*ENU\s*:/i.test(srs)
  const declaredScale = /<ScaleCalibrated>\s*true\s*<\/ScaleCalibrated>/i.test(xml)
  const unitLabel = xml.match(/<UnitLabel>\s*([^<]+)\s*<\/UnitLabel>/i)?.[1]?.trim() || ''
  const scaleSource = xml.match(/<ScaleSource>\s*([^<]+)\s*<\/ScaleSource>/i)?.[1]?.trim() || ''
  const declaredScaleFactor = Number(xml.match(/<ScaleFactor>\s*([^<]+)\s*<\/ScaleFactor>/i)?.[1])
  const scaleFactor = Number.isFinite(declaredScaleFactor) && declaredScaleFactor > 0 ? declaredScaleFactor : 1
  const hasMetricScale = isEnuMetric || (declaredScale && unitLabel.toLowerCase() === 'm')
  const qualityBlock = xml.match(/<QualityReport\b([^>]*)>([\s\S]*?)<\/QualityReport>/i)
  const qualityReport = qualityBlock ? (() => {
    const parseAttributes = (attributeText) => Object.fromEntries(
      Array.from(attributeText.matchAll(/([\w-]+)\s*=\s*["']([^"']*)["']/g), match => [match[1], match[2]])
    )
    const reportAttributes = parseAttributes(qualityBlock[1])
    const metrics = Array.from(qualityBlock[2].matchAll(/<Metric\b([^>]*)\/?\s*>/gi), match => parseAttributes(match[1]))
    const caveat = qualityBlock[2].match(/<Caveat>\s*([^<]+)\s*<\/Caveat>/i)?.[1]?.trim() || ''
    const reportFileReference = qualityBlock[2].match(/<ReportFile>\s*([^<]+)\s*<\/ReportFile>/i)?.[1]?.trim() || ''
    return {
      source: reportAttributes.source || '来源处理报告',
      independentCheckpoints: Number(reportAttributes.independentCheckpoints || 0),
      scaleBars: Number(reportAttributes.scaleBars || 0),
      showScopes: reportAttributes.showScopes?.toLowerCase() !== 'false',
      showSource: reportAttributes.showSource?.toLowerCase() !== 'false',
      showCaveat: reportAttributes.showCaveat?.toLowerCase() !== 'false',
      showSyntheticCaptureNote: reportAttributes.showSyntheticCaptureNote?.toLowerCase() !== 'false',
      showPrecisionNote: reportAttributes.showPrecisionNote?.toLowerCase() !== 'false',
      caveat,
      reportFileReference,
      metrics: metrics.filter(metric => metric.id && metric.label && metric.value !== undefined && metric.visible?.toLowerCase() !== 'false')
    }
  })() : null
  return { isEnuMetric, hasMetricScale, scaleFactor, unitLabel, scaleSource, upAxisHint: axis, captureType, qualityReport }
}

const findAssociatedTexture = (files, modelFile, modelInfo) => {
  if (!modelInfo.hasTextureCoordinates) return null
  const images = files.filter(file => file.type.startsWith('image/') && !isThumbnailPath(file))
  const datasetImage = (file) => imageKindFromPath(file) !== 'other'
  const usableImages = images.filter(file => !datasetImage(file) && !/(^|[/_-])(?:scene[-_]?preview|preview|overview)([/_.-]|$)/i.test(normalizeRelativePath(file)))
  const modelPath = normalizeRelativePath(modelFile)
  const modelDirectory = modelPath.slice(0, Math.max(0, modelPath.lastIndexOf('/'))).toLowerCase()
  const reference = modelInfo.textureFileReference.replace(/\\/g, '/').replace(/^\.\//, '').replace(/^['"]|['"]$/g, '').toLowerCase()

  if (reference) {
    const exactPath = `${modelDirectory}/${reference}`.replace(/^\/+/, '')
    const referenceBaseName = reference.split('/').pop()
    const exactMatch = usableImages.find(file => normalizeRelativePath(file).toLowerCase() === exactPath)
      || usableImages.find(file => normalizeRelativePath(file).toLowerCase().endsWith(`/${referenceBaseName}`))
    if (exactMatch) return exactMatch
  }

  const sameFolder = usableImages.filter(file => normalizeRelativePath(file).slice(0, Math.max(0, normalizeRelativePath(file).lastIndexOf('/'))).toLowerCase() === modelDirectory)
  return sameFolder.find(file => /(texture|atlas|albedo|material)/i.test(file.name))
    || usableImages.find(file => /(texture|atlas|albedo|material)/i.test(file.name))
    || null
}

const readCustomFolder = async (event) => {
  const files = Array.from(event.target.files || [])
  const selectedFolderName = files.length ? normalizeRelativePath(files[0]).split('/')[0]?.trim() : ''
  if (selectedFolderName && (!customTitleManuallyEdited.value || !customTitle.value.trim())) {
    customTitle.value = selectedFolderName
    customTitleManuallyEdited.value = false
  }
  event.target.value = ''
  customImportError.value = ''
  customFolderData.value = null
  closeGallery()
  if (!files.length) return

  customBusy.value = true
  try {
    const plyFiles = files.filter(file => file.name.toLowerCase().endsWith('.ply'))
    if (!plyFiles.length) throw new Error('所选文件夹中没有可用的 PLY 网格。')

    const candidates = (await Promise.all(plyFiles.map(async file => {
      try {
        return { file, info: await readPlyHeader(file) }
      } catch {
        return null
      }
    }))).filter(Boolean)
    if (!candidates.length) throw new Error('文件夹中没有包含顶点和三角面的 PLY 网格。')

    const modelPreference = (file) => {
      const path = normalizeRelativePath(file).toLowerCase()
      if (/meshed[-_ ]?poisson/.test(path)) return 3
      if (/(^|[/_-])meshed?([/_.-]|$)/.test(path)) return 2
      return 1
    }
    candidates.sort((a, b) => modelPreference(b.file) - modelPreference(a.file) || b.info.faceCount - a.info.faceCount)
    const selectedModel = candidates[0]
    const textureFile = findAssociatedTexture(files, selectedModel.file, selectedModel.info)
    const spatialMetadata = await readSpatialMetadata(files, selectedModel.file)
    const reportReference = spatialMetadata.qualityReport?.reportFileReference?.replace(/\\/g, '/').replace(/^\.\//, '').toLowerCase() || ''
    const qualityReportFile = reportReference
      ? files.find(file => {
          const relativePath = normalizeRelativePath(file).toLowerCase()
          return relativePath === reportReference || relativePath.endsWith(`/${reportReference}`)
        }) || null
      : null
    const suggestedUpAxis = selectedModel.info.upAxisHint || spatialMetadata.upAxisHint
    if (suggestedUpAxis) customUpAxis.value = suggestedUpAxis

    const images = files.filter(file => file.type.startsWith('image/') && file !== textureFile && !isThumbnailPath(file))
    const uavFiles = images.filter(file => imageKindFromPath(file) === 'uav')
    const ugvFiles = images.filter(file => imageKindFromPath(file) === 'ugv')
    const otherFiles = images.filter(file => imageKindFromPath(file) === 'other')
    customFolderData.value = {
      modelFile: selectedModel.file,
      modelInfo: selectedModel.info,
      textureFile,
      qualityReportFile,
      uavFiles,
      ugvFiles,
      otherFiles,
      spatialMetadata,
      captureType: spatialMetadata.captureType,
      counts: { uav: uavFiles.length, ugv: ugvFiles.length, other: otherFiles.length, total: images.length }
    }
  } catch (error) {
    customImportError.value = error instanceof Error ? error.message : '场景文件夹读取失败。'
  } finally {
    customBusy.value = false
  }
}

const importCustomScene = () => {
  const folder = customFolderData.value
  if (!customTitle.value.trim() || !folder || customBusy.value) return
  showImportModeDialog.value = true
}

const confirmCustomImport = async (directDisplay) => {
  const folder = customFolderData.value
  if (!customTitle.value.trim() || !folder || customBusy.value) return

  showImportModeDialog.value = false
  customBusy.value = true
  customImportError.value = ''
  const objectUrls = []
  const makeObjectUrl = (file) => {
    const url = URL.createObjectURL(file)
    objectUrls.push(url)
    return url
  }

  try {
    const modelUrl = makeObjectUrl(folder.modelFile)
    const useTexture = Boolean(folder.textureFile && folder.modelInfo.hasTextureCoordinates)
    const textureUrl = useTexture ? makeObjectUrl(folder.textureFile) : ''
    const samples = []
    if (folder.uavFiles[0]) samples.push({ url: makeObjectUrl(folder.uavFiles[0]), kind: 'uav' })
    if (folder.ugvFiles[0]) samples.push({ url: makeObjectUrl(folder.ugvFiles[0]), kind: 'ugv' })

    const { uav, ugv, other, total } = folder.counts
    const isEnuMetric = folder.spatialMetadata.isEnuMetric
    const hasMetricScale = folder.spatialMetadata.hasMetricScale
    const dataset = {
      id: `custom-${Date.now()}`,
      title: customTitle.value.trim(),
      captureType: folder.captureType,
      skipReconstructionWait: directDisplay,
      counts: { uav, ugv, other, total },
      samples,
      objectUrls,
      model: {
        format: 'PLY',
        url: modelUrl,
        textureUrl,
        vertices: folder.modelInfo.vertexCount,
        faces: folder.modelInfo.faceCount,
        upAxis: customUpAxis.value,
        coordinateSystem: isEnuMetric ? 'ENU' : hasMetricScale ? 'MeshLab Scale 标定局部坐标' : '自定义局部坐标',
        unitLabel: hasMetricScale ? 'm' : '模型单位',
        scaleCalibrated: hasMetricScale,
        scaleFactor: folder.spatialMetadata.scaleFactor,
        coordinateLabel: isEnuMetric ? 'ENU米制 · 场景局部坐标' : hasMetricScale ? '米制 · MeshLab Scale 尺度基准' : '未标定 · 模型单位',
        scaleSource: folder.spatialMetadata.scaleSource || (isEnuMetric ? '所选文件夹中的 ENU 空间参考元数据' : hasMetricScale ? '所选文件夹中的 MeshLab Scale 米制尺度基准' : '未提供已知尺寸或独立控制点'),
        surfaceAppearance: useTexture ? '照片纹理' : folder.modelInfo.hasVertexColors ? '顶点颜色' : '默认单色',
        captureType: folder.captureType,
        qualityReport: folder.spatialMetadata.qualityReport ? {
          ...folder.spatialMetadata.qualityReport,
          reportFileUrl: folder.qualityReportFile ? makeObjectUrl(folder.qualityReportFile) : ''
        } : null,
        datasetCounts: { uav, ugv, other, total }
      }
    }

    emit('dataset-ready', dataset)
  } catch (error) {
    objectUrls.forEach(url => URL.revokeObjectURL(url))
    customImportError.value = error instanceof Error ? error.message : '自定义场景读取失败。'
  } finally {
    customBusy.value = false
  }
}
</script>

<style scoped>
.dataset-catalog { box-sizing: border-box; width: min(1380px, 100%); margin: 0 auto; padding: 16px clamp(12px, 2vw, 30px) 10px; container-type: inline-size; color: #e6f4ff; }
.catalog-header, .dataset-card-top, .section-heading { display: flex; align-items: center; justify-content: space-between; }
.catalog-header { box-sizing: border-box; width: 100%; gap: 24px; margin: 0 auto 16px; max-width: 960px; }
.catalog-header h2 { margin: 0; color: #f2fbff; font-size: clamp(22px, 2.2vw, 30px); }
.catalog-status { display: inline-flex; max-width: 100%; align-items: center; gap: 9px; flex: 0 1 auto; padding: 9px 13px; border: 1px solid rgba(148, 163, 184, 0.24); border-radius: 14px; background: rgba(15, 31, 49, 0.78); color: #9eb1c1; font-size: 12px; line-height: 1.45; }
.catalog-status.ready { border-color: rgba(45, 212, 191, 0.32); color: #80f0dc; }
.status-indicator { width: 7px; height: 7px; border-radius: 50%; background: currentColor; box-shadow: 0 0 10px currentColor; }
.dataset-grid { box-sizing: border-box; display: grid; width: 100%; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; max-width: 960px; margin: 0 auto; }
.dataset-card { min-width: 0; padding: 16px; border: 1px solid rgba(69, 136, 168, 0.3); border-radius: 14px; background: linear-gradient(145deg, rgba(10, 28, 48, 0.97), rgba(5, 15, 29, 0.98)); box-shadow: 0 16px 40px rgba(0, 0, 0, 0.23), inset 0 1px rgba(255, 255, 255, 0.035); }
.dataset-card-top { align-items: flex-start; gap: 16px; }
.dataset-kind { display: inline-block; margin-bottom: 7px; color: #65dff1; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; }
.kind-oil-tanker { color: #ffc66d; }
.dataset-title-block h3 { margin: 0 0 5px; color: #effaff; font-size: 19px; }
.total-count { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; flex-shrink: 0; }
.total-count strong { color: #e7fbff; font: 700 27px/1 'Consolas', monospace; }
.total-count span { color: #849cb0; font-size: 11px; }
.source-counts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin: 12px 0; }
.count-cell { display: grid; grid-template-columns: 1fr auto auto; align-items: baseline; gap: 6px; padding: 11px 12px; border: 1px solid rgba(117, 158, 182, 0.14); border-radius: 9px; background: rgba(6, 18, 32, 0.76); }
.count-label { color: #91aabd; font-size: 11px; }
.count-cell strong { font: 700 20px/1 'Consolas', monospace; }
.count-cell > span:last-child { color: #8097aa; font-size: 11px; }
.uav-cell strong { color: #55d8ed; }
.ugv-cell strong { color: #f2bd67; }
.sample-section { padding-top: 12px; border-top: 1px solid rgba(117, 158, 182, 0.14); }
.section-heading { margin-bottom: 9px; color: #bdd2df; font-size: 11px; }
.section-heading span:last-child { color: #71899d; }
.sample-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.sample-tile { position: relative; min-width: 0; margin: 0; overflow: hidden; border: 1px solid rgba(117, 158, 182, 0.15); border-radius: 7px; background: #06101d; }
.sample-tile img { display: block; width: 100%; height: 92px; object-fit: cover; }
.sample-tile figcaption { position: absolute; right: 7px; bottom: 7px; padding: 3px 7px; border: 1px solid rgba(115, 221, 236, 0.35); border-radius: 99px; background: rgba(3, 12, 22, 0.82); color: #a8f1f5; font-size: 9px; line-height: 1.3; }
.sample-tile figcaption.sample-ugv { border-color: rgba(241, 194, 118, 0.35); color: #f1c276; }
.no-samples { grid-column: 1 / -1; padding: 18px; color: #8298aa; text-align: center; font-size: 12px; }
.import-button { display: flex; width: 100%; align-items: center; justify-content: space-between; margin-top: 12px; padding: 13px 14px; border: 1px solid rgba(65, 216, 207, 0.5); border-radius: 8px; background: linear-gradient(100deg, rgba(12, 110, 116, 0.45), rgba(20, 74, 119, 0.5)); color: #c7fffb; cursor: pointer; font-size: 12px; font-weight: 700; transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease; }
.import-button:hover { transform: translateY(-1px); border-color: #71f2e4; background: linear-gradient(100deg, rgba(14, 143, 145, 0.55), rgba(35, 104, 159, 0.56)); }
.import-button span { font-size: 17px; }
.catalog-message { display: flex; min-height: 240px; align-items: center; justify-content: center; gap: 14px; color: #a8bfce; font-size: 13px; }
.error-message { color: #ffb4a9; }
.error-message p { margin: 7px 0 0; color: #c98d88; }
.error-message .error-hint { color: #8fa3b5; font-size: 11px; }
.message-icon { display: grid; width: 28px; height: 28px; place-items: center; border: 1px solid rgba(255, 120, 102, 0.45); border-radius: 50%; font-weight: 700; }
.loading-ring { width: 19px; height: 19px; border: 2px solid rgba(94, 234, 212, 0.2); border-top-color: #5eead4; border-radius: 50%; animation: spin 0.8s linear infinite; }
.custom-scene-panel { box-sizing: border-box; width: 100%; max-width: 960px; margin: 16px auto 0; padding: 14px 16px; border: 1px dashed rgba(94, 164, 186, 0.32); border-radius: 12px; background: rgba(5, 17, 30, 0.72); color: #dcebf2; }
.custom-scene-panel.expanded { border-style: solid; border-color: rgba(70, 190, 194, 0.42); }
.custom-scene-summary { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-start; gap: 12px 18px; }
.custom-scene-kicker { color: #70d8dc; font-size: 9px; font-weight: 700; letter-spacing: 0.14em; }
.custom-scene-summary h3 { margin: 3px 0; color: #eaf6fa; font-size: 14px; }
.custom-scene-summary p { margin: 0; color: #829aaa; font-size: 11px; }
.custom-toggle-button { display: inline-flex; min-width: 145px; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 12px; border: 1px solid rgba(74, 205, 199, 0.4); border-radius: 7px; background: rgba(13, 59, 73, 0.58); color: #bdfaf0; cursor: pointer; font-size: 11px; font-weight: 700; }
.custom-toggle-button span { font-size: 16px; }
.custom-scene-form { display: grid; gap: 14px; margin-top: 16px; padding-top: 14px; border-top: 1px solid rgba(117, 158, 182, 0.14); }
.custom-field { display: grid; min-width: 0; gap: 6px; color: #9eb5c3; font-size: 10px; }
.custom-field b, .custom-field-label b { color: #f4ba71; }
.custom-name-field { max-width: 440px; }
.custom-field input, .custom-field select { box-sizing: border-box; width: 100%; min-height: 34px; padding: 7px 9px; border: 1px solid rgba(117, 158, 182, 0.24); border-radius: 6px; outline: none; background: rgba(2, 10, 19, 0.72); color: #e4f2f7; font: 11px 'Microsoft YaHei', sans-serif; }
.custom-field input:focus, .custom-field select:focus { border-color: rgba(81, 219, 207, 0.68); box-shadow: 0 0 0 2px rgba(81, 219, 207, 0.08); }
.custom-folder-picker { display: flex; min-height: 50px; align-items: center; flex-wrap: wrap; gap: 10px; padding: 10px; border: 1px solid rgba(117, 158, 182, 0.18); border-radius: 7px; background: rgba(3, 13, 24, 0.55); }
.custom-association-summary { display: flex; align-items: center; flex-wrap: wrap; gap: 7px; }
.custom-association-summary span { padding: 6px 9px; border: 1px solid rgba(117, 158, 182, 0.16); border-radius: 99px; background: rgba(6, 18, 32, 0.7); color: #9ab0bd; font-size: 10px; }
.custom-association-summary b { margin-right: 4px; color: #71dcd6; font-weight: 700; }
.custom-file-input { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); clip-path: inset(50%); white-space: nowrap; }
.custom-file-button { min-width: 0; padding: 6px 8px; border: 1px solid rgba(79, 151, 174, 0.3); border-radius: 5px; background: rgba(17, 42, 60, 0.72); color: #d1e8ef; cursor: pointer; font-size: 9px; white-space: nowrap; }
.custom-file-button:hover { border-color: #50d3ce; color: #bafff5; }
.custom-file-state { overflow: hidden; color: #7d98a8; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.custom-form-footer { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px 16px; }
.custom-form-footer > div { min-width: 0; flex: 1 1 320px; }
.custom-local-note, .custom-import-error { margin: 0; color: #728b9a; font-size: 10px; line-height: 1.5; }
.custom-import-error { color: #ff9b8c; }
.custom-import-button { width: auto; min-width: 195px; flex-shrink: 0; margin-top: 0; padding: 10px 13px; }
.custom-import-button:disabled { border-color: rgba(117, 158, 182, 0.14); background: rgba(22, 37, 49, 0.65); color: #708595; cursor: not-allowed; transform: none; }
.import-choice-overlay { position: fixed; inset: 0; z-index: 120; display: grid; place-items: center; padding: 20px; background: rgba(2, 7, 18, 0.82); backdrop-filter: blur(7px); }
.import-choice-dialog { box-sizing: border-box; width: min(450px, 100%); padding: 22px; border: 1px solid rgba(89, 202, 211, 0.42); border-radius: 12px; background: linear-gradient(145deg, #0c1b2b, #07111d); color: #e6f4fa; box-shadow: 0 24px 75px rgba(0, 0, 0, 0.55); }
.import-choice-dialog h3 { margin: 0; color: #f1f9fc; font-size: 19px; }
.import-choice-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 9px; margin-top: 19px; }
.import-choice-actions button { min-height: 36px; padding: 8px 12px; border-radius: 7px; cursor: pointer; font-size: 11px; font-weight: 700; }
.import-choice-secondary { border: 1px solid rgba(117, 158, 182, 0.3); background: rgba(17, 37, 55, 0.72); color: #c0d0d9; }
.import-choice-primary { border: 1px solid rgba(84, 217, 202, 0.58); background: linear-gradient(100deg, rgba(11, 117, 121, 0.68), rgba(22, 82, 131, 0.72)); color: #d6fffa; }
.dataset-catalog.gallery-open { width: min(1580px, 100%); }
.catalog-layout { display: grid; grid-template-columns: minmax(0, 1fr); align-items: start; gap: 16px; }
.catalog-main { min-width: 0; }
.gallery-open .catalog-layout { grid-template-columns: minmax(0, 1fr) minmax(410px, 0.88fr); }
.gallery-open .catalog-header, .gallery-open .dataset-grid, .gallery-open .custom-scene-panel { max-width: none; }
.gallery-open .dataset-grid { grid-template-columns: minmax(0, 1fr); }
.section-heading { gap: 8px; }
.gallery-link-button { flex: 0 0 auto; padding: 5px 8px; border: 1px solid rgba(82, 198, 207, 0.28); border-radius: 6px; background: rgba(12, 49, 66, 0.44); color: #76dbe3; cursor: pointer; font: 600 10px 'Microsoft YaHei', sans-serif; transition: border-color 0.16s ease, background 0.16s ease; }
.gallery-link-button:hover:not(:disabled) { border-color: rgba(90, 226, 221, 0.68); background: rgba(15, 77, 90, 0.62); color: #c0fff8; }
.gallery-link-button:disabled { opacity: 0.45; cursor: not-allowed; }
.custom-association-summary .gallery-link-button { margin-left: 2px; }
.capture-gallery-panel { box-sizing: border-box; position: sticky; top: 14px; display: flex; min-width: 0; height: min(740px, calc(100vh - 42px)); flex-direction: column; overflow: hidden; padding: 15px; border: 1px solid rgba(67, 171, 190, 0.35); border-radius: 13px; background: radial-gradient(circle at 95% 0, rgba(24, 91, 116, 0.15), transparent 37%), linear-gradient(155deg, rgba(8, 24, 41, 0.98), rgba(4, 13, 25, 0.99)); box-shadow: 0 20px 58px rgba(0, 0, 0, 0.3), inset 0 1px rgba(255, 255, 255, 0.035); }
.gallery-panel-header { display: flex; min-width: 0; align-items: flex-start; justify-content: space-between; gap: 14px; }
.gallery-panel-title { min-width: 0; }
.gallery-panel-title h3 { overflow: hidden; margin: 0; color: #effaff; font-size: 16px; text-overflow: ellipsis; white-space: nowrap; }
.gallery-close-button, .original-preview-header button { display: grid; width: 30px; height: 30px; flex: 0 0 auto; place-items: center; border: 1px solid rgba(134, 165, 184, 0.2); border-radius: 7px; background: rgba(17, 39, 57, 0.58); color: #a9bfcd; cursor: pointer; font: 22px/1 'Segoe UI', sans-serif; }
.gallery-close-button:hover, .original-preview-header button:hover { border-color: rgba(105, 215, 216, 0.5); color: #d9fffb; }
.gallery-tabs { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; padding: 4px; border: 1px solid rgba(102, 151, 174, 0.14); border-radius: 8px; background: rgba(2, 11, 22, 0.58); }
.gallery-tabs button { min-width: 0; min-height: 32px; border: 1px solid transparent; border-radius: 5px; background: transparent; color: #819aaa; cursor: pointer; font: 600 10px 'Microsoft YaHei', sans-serif; transition: color 0.16s ease, background 0.16s ease, border-color 0.16s ease; }
.gallery-tabs button:hover { color: #c9eaf0; }
.gallery-tabs button.active { border-color: rgba(66, 205, 207, 0.35); background: linear-gradient(100deg, rgba(19, 96, 109, 0.48), rgba(20, 61, 94, 0.46)); color: #bafff6; }
.gallery-list-heading { display: flex; min-width: 0; align-items: baseline; justify-content: space-between; gap: 10px; margin: 14px 1px 9px; color: #d4e9f1; font-size: 11px; }
.gallery-list-heading strong { min-width: 0; flex: 1 1 auto; color: #d4e9f1; font-size: 12px; white-space: nowrap; }
.gallery-list-heading span { flex: 0 0 auto; color: #819aaa; font: 10px 'Consolas', monospace; }
.gallery-thumbnail-grid { display: grid; min-height: 0; flex: 1 1 auto; grid-template-columns: repeat(3, minmax(0, 1fr)); align-content: start; gap: 9px; overflow: auto; padding: 1px 2px 5px 1px; scrollbar-color: rgba(75, 135, 155, 0.45) rgba(4, 14, 26, 0.3); scrollbar-width: thin; }
.gallery-thumbnail { min-width: 0; padding: 0; overflow: hidden; border: 1px solid rgba(95, 145, 167, 0.22); border-radius: 7px; background: rgba(5, 16, 28, 0.78); color: #a5bbc8; cursor: zoom-in; text-align: left; transition: border-color 0.16s ease, transform 0.16s ease; }
.gallery-thumbnail:hover { transform: translateY(-1px); border-color: rgba(77, 210, 218, 0.62); }
.thumbnail-image-frame { display: grid; width: 100%; aspect-ratio: 4 / 3; place-items: center; overflow: hidden; background: linear-gradient(140deg, #0c1c2a, #06101c); }
.thumbnail-image-frame img { display: block; width: 100%; height: 100%; object-fit: contain; }
.thumbnail-placeholder { display: grid; width: 100%; height: 100%; place-items: center; color: #6f8998; font-size: 9px; }
.thumbnail-placeholder .loading-ring { width: 15px; height: 15px; }
.thumbnail-caption { display: block; overflow: hidden; padding: 6px 7px; color: #9ab0bd; font: 9px 'Consolas', monospace; text-overflow: ellipsis; white-space: nowrap; }
.gallery-empty-state { display: grid; min-height: 180px; flex: 1; place-items: center; color: #879eac; font-size: 11px; }
.gallery-pagination { display: flex; flex: 0 0 auto; align-items: center; justify-content: center; gap: 13px; padding: 10px 0 2px; color: #8da6b5; font: 10px 'Consolas', monospace; }
.gallery-pagination button, .original-preview-footer button { min-height: 29px; padding: 5px 10px; border: 1px solid rgba(99, 153, 174, 0.24); border-radius: 6px; background: rgba(14, 35, 52, 0.7); color: #bbd2dc; cursor: pointer; font: 10px 'Microsoft YaHei', sans-serif; }
.gallery-pagination button:hover:not(:disabled), .original-preview-footer button:hover:not(:disabled) { border-color: rgba(93, 209, 211, 0.55); color: #d8fffa; }
.gallery-pagination button:disabled, .original-preview-footer button:disabled { opacity: 0.42; cursor: not-allowed; }
.joint-gallery-content { display: flex; min-height: 0; flex: 1 1 auto; margin-top: 12px; }
.gallery-slide-enter-active, .gallery-slide-leave-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.gallery-slide-enter-from, .gallery-slide-leave-to { transform: translateX(18px); opacity: 0; }
.original-preview-overlay { position: fixed; inset: 0; z-index: 150; display: grid; place-items: center; padding: 24px; background: rgba(1, 6, 14, 0.91); backdrop-filter: blur(8px); }
.original-preview-dialog { box-sizing: border-box; display: flex; width: min(1320px, 100%); height: min(920px, 94vh); flex-direction: column; overflow: hidden; border: 1px solid rgba(83, 167, 189, 0.38); border-radius: 12px; background: #06101c; box-shadow: 0 24px 80px rgba(0, 0, 0, 0.55); }
.original-preview-header, .original-preview-footer { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 14px; border-bottom: 1px solid rgba(100, 142, 162, 0.17); background: rgba(10, 25, 41, 0.88); }
.original-preview-header > div { display: flex; align-items: baseline; gap: 10px; }
.original-preview-header span { color: #6ed7df; font-size: 11px; font-weight: 700; }
.original-preview-header strong { color: #a5bbc8; font: 10px 'Consolas', monospace; }
.original-preview-image-wrap { display: grid; min-height: 0; flex: 1 1 auto; place-items: center; padding: 10px; background: #030912; }
.original-preview-image-wrap img { display: block; max-width: 100%; max-height: 100%; object-fit: contain; }
.original-preview-footer { justify-content: center; border-top: 1px solid rgba(100, 142, 162, 0.17); border-bottom: 0; color: #8199a8; font-size: 10px; }
@keyframes spin { to { transform: rotate(360deg); } }
@container (max-width: 1350px) { .dataset-grid { grid-template-columns: 1fr; } .catalog-header { align-items: flex-start; flex-direction: column; } }
@media (max-width: 980px) { .gallery-open .catalog-layout { grid-template-columns: minmax(0, 1fr); } .capture-gallery-panel { position: relative; top: auto; height: min(690px, 82vh); } }
@media (max-width: 520px) { .dataset-card { padding: 14px; } .sample-tile img { height: 82px; } .custom-scene-summary, .custom-form-footer, .custom-folder-picker { align-items: flex-start; flex-direction: column; } .custom-toggle-button, .custom-import-button { width: 100%; } .capture-gallery-panel { height: min(620px, 78vh); padding: 12px; } .gallery-thumbnail-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .original-preview-overlay { padding: 10px; } .original-preview-dialog { height: 96vh; } }
</style>
