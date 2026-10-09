import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'lkyw.currentRole'

export const ROLE_OPTIONS = [
  { key: 'commander', label: '指挥员', description: '方案研判与协同指挥', icon: '◆' },
  { key: 'dispatcher', label: '调度员', description: '告警跟踪与资源调度', icon: '●' },
  { key: 'expert', label: '技术专家', description: '算法分析与推演验证', icon: '◇' },
  { key: 'admin', label: '系统管理员', description: '设备服务与系统运维', icon: '▣' }
]

const readStoredRole = () => {
  try {
    const role = window.localStorage.getItem(STORAGE_KEY)
    return ROLE_OPTIONS.some(item => item.key === role) ? role : 'commander'
  } catch {
    return 'commander'
  }
}

// 当前项目尚未接入统一身份认证；此状态用于演示四类岗位的页面与功能边界，
// 并预留给后续登录接口写入真实角色。
export const currentRole = ref(typeof window === 'undefined' ? 'commander' : readStoredRole())

watch(currentRole, role => {
  try {
    window.localStorage.setItem(STORAGE_KEY, role)
  } catch {
    // 本地存储不可用时仅在当前会话中保持角色。
  }
})

export const currentRoleProfile = computed(() =>
  ROLE_OPTIONS.find(item => item.key === currentRole.value) || ROLE_OPTIONS[0]
)

export const canAccessRoute = (roles = []) =>
  !roles.length || roles.includes(currentRole.value)

