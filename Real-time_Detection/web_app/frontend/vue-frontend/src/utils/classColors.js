const CLASS_STYLES = {
  car_fire: {
    background: '#dc2626',
    borderColor: '#fecaca',
    color: '#ffffff'
  },
  lkyw_fire: {
    background: '#991b1b',
    borderColor: '#fca5a5',
    color: '#ffffff'
  },
  car_nofire: {
    background: '#facc15',
    borderColor: '#fef08a',
    color: '#1f2937'
  },
  lkyw_nofire: {
    background: '#f59e0b',
    borderColor: '#fde68a',
    color: '#111827'
  },
  car_normal: {
    background: '#facc15',
    borderColor: '#fef08a',
    color: '#1f2937'
  },
  lkyw_normal: {
    background: '#f59e0b',
    borderColor: '#fde68a',
    color: '#111827'
  }
}

export const getClassStyle = (className = '') => {
  const key = String(className).toLowerCase()
  if (CLASS_STYLES[key]) return CLASS_STYLES[key]
  if (key.includes('fire') || key.includes('火')) return CLASS_STYLES.car_fire
  if (key.includes('nofire') || key.includes('normal') || key.includes('无火') || key.includes('正常')) {
    return CLASS_STYLES.car_nofire
  }
  return {
    background: '#64748b',
    borderColor: '#cbd5e1',
    color: '#ffffff'
  }
}
