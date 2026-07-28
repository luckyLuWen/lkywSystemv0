const CLASS_STYLES = {
  car_fire: {
    background: '#E53935',
    borderColor: '#FFCDD2',
    color: '#ffffff'
  },
  lkyw_fire: {
    background: '#C2185B',
    borderColor: '#F8BBD0',
    color: '#ffffff'
  },
  car_nofire: {
    background: '#FDD835',
    borderColor: '#FFF59D',
    color: '#1f2937'
  },
  lkyw_nofire: {
    background: '#FB8C00',
    borderColor: '#FFE0B2',
    color: '#111827'
  },
  car_normal: {
    background: '#FDD835',
    borderColor: '#FFF59D',
    color: '#1f2937'
  },
  lkyw_normal: {
    background: '#FB8C00',
    borderColor: '#FFE0B2',
    color: '#111827'
  },
  normal: {
    background: '#0EA5E9',
    borderColor: '#7DD3FC',
    color: '#ffffff'
  },
  accident: {
    background: '#A8432E',
    borderColor: '#F2A08D',
    color: '#ffffff'
  },
  hazmat_leak: {
    background: '#0EA5E9',
    borderColor: '#7DD3FC',
    color: '#ffffff'
  },
  tank_leak: {
    background: '#A8432E',
    borderColor: '#F2A08D',
    color: '#ffffff'
  }
}

export const getClassStyle = (className = '') => {
  const key = String(className).toLowerCase()
  if (CLASS_STYLES[key]) return CLASS_STYLES[key]
  if (key.includes('nofire') || key.includes('normal') || key.includes('无火') || key.includes('正常')) {
    return key.includes('lkyw') ? CLASS_STYLES.lkyw_nofire : CLASS_STYLES.car_nofire
  }
  if (key.includes('leak') || key.includes('hazmat') || key.includes('tank') || key.includes('泄露') || key.includes('泄漏') || key.includes('危化')) {
    return key.includes('tank') ? CLASS_STYLES.tank_leak : CLASS_STYLES.hazmat_leak
  }
  if (key.includes('fire') || key.includes('火')) {
    return key.includes('lkyw') ? CLASS_STYLES.lkyw_fire : CLASS_STYLES.car_fire
  }
  return {
    background: '#64748b',
    borderColor: '#cbd5e1',
    color: '#ffffff'
  }
}
