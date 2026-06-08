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

const exportCSV = () => {
  const header = 'class,confidence,bbox_x1,bbox_y1,bbox_x2,bbox_y2'
  const rows = props.detections.map(d => {
    const [x1, y1, x2, y2] = d.bbox
    return `${d.class},${d.confidence.toFixed(4)},${x1},${y1},${x2},${y2}`
  })
  const csv = '﻿' + [header, ...rows].join('\n')
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
  gap: 10px;
}

.btn-export {
  background: transparent;
  border: 1px solid var(--border-cyan);
  color: var(--primary-cyan);
  padding: 8px 18px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-export:hover {
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.15);
}
</style>
