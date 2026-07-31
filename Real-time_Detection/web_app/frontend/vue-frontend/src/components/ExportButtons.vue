<template>
  <div class="export-buttons">
    <button class="btn-export" @click="downloadImage">下载标注图</button>
    <button class="btn-export" @click="exportCSV">导出 CSV</button>
  </div>
</template>

<script setup>
const props = defineProps({
  resultImageUrl: String,
  detections: Array
})

const downloadImage = async () => {
  const url = props.resultImageUrl
  const ext = url.startsWith('data:') ? 'jpg' : url.split('.').pop() || 'jpg'
  const filename = `detection_result_${Date.now()}.${ext}`

  if (url.startsWith('data:')) {
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    return
  }

  try {
    const response = await fetch(url)
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename
    a.click()
    URL.revokeObjectURL(objectUrl)
  } catch {
    const a = document.createElement('a')
    a.href = url
    a.target = '_blank'
    a.download = filename
    a.click()
  }
}

const detectionLabels = (detection) => {
  if (Array.isArray(detection?.merged_labels) && detection.merged_labels.length) return detection.merged_labels
  return [{ class: detection?.class || '', confidence: detection?.confidence || 0 }]
}

const exportCSV = () => {
  const header = 'class,confidence,bbox_x1,bbox_y1,bbox_x2,bbox_y2'
  const rows = props.detections.flatMap(d => {
    const [x1, y1, x2, y2] = d.bbox
    return detectionLabels(d).map(label => {
      const confidence = Number(label.confidence || 0)
      return `${label.class},${confidence.toFixed(4)},${x1},${y1},${x2},${y2}`
    })
  })
  const csv = '\ufeff' + [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `detection_results_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

</script>

<style scoped>
.export-buttons {
  display: flex;
  gap: 18px;
}

.btn-export {
  background: transparent;
  border: 2px solid var(--border-cyan);
  color: var(--primary-cyan);
  padding: 14px 38px;
  border-radius: 8px;
  font-size: 24px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  min-height: 58px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.btn-export:hover {
  background: rgba(0, 229, 255, 0.15);
  border-color: var(--primary-cyan);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
}
</style>
