import { ref } from 'vue'
import { currentRole } from './useRoleAccess'
export const authUser = ref(null)
export const authReady = ref(false)
async function request(path, options = {}) {
  const response = await fetch('/api/auth/' + path, { credentials: 'same-origin', ...options })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || '登录服务暂不可用，请稍后重试')
  return data
}
export async function checkSession() {
  try { authUser.value = await request('session'); currentRole.value = authUser.value.role }
  catch { authUser.value = null }
  finally { authReady.value = true }
}
export async function signIn(values) {
  authUser.value = await request('login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) })
  currentRole.value = authUser.value.role
}
export async function signOut() {
  await request('logout', { method: 'POST' })
  authUser.value = null
}
