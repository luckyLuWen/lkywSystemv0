import { ref, reactive, onMounted } from 'vue'

export function useApi() {
  const API_STORAGE_KEY = 'realtimeDetection.apiBaseUrl'
  
  const getInitialApiUrl = () => {
    // 优先从 URL Query 参数中提取大系统传入的 apiBase 地址
    const urlParams = new URLSearchParams(window.location.search)
    const queryApiBase = urlParams.get('apiBase')
    if (queryApiBase) {
      return queryApiBase.replace(/\/+$/, '')
    }

    const dynamicDefault = `${window.location.protocol}//${window.location.hostname}:5000`
    const stored = localStorage.getItem(API_STORAGE_KEY)
    
    // 如果存储的地址是本地环回地址，但当前是用外部 IP 访问的，自动升级为外部 IP 以免连接失败
    if (stored && (stored.includes('://127.0.0.1') || stored.includes('://localhost'))) {
      if (window.location.hostname !== '127.0.0.1' && window.location.hostname !== 'localhost') {
        localStorage.setItem(API_STORAGE_KEY, dynamicDefault)
        return dynamicDefault
      }
    }
    return stored || dynamicDefault
  }

  const apiUrl = ref(getInitialApiUrl())
  const isOnline = ref(false)
  const statusDetail = ref('')
  const availableModels = ref([])

  const settings = reactive({
    model: '',
    conf: 0.25,
    iou: 0.45
  })

  const checkHealth = async () => {
    try {
      const response = await fetch(`${apiUrl.value}/api/health`, { cache: 'no-store' })
      const data = await response.json()
      isOnline.value = true
      statusDetail.value = data?.model_ready === false ? '模型未就绪' : '模型已就绪'
      
      // Health check passed, now fetch models
      await fetchModels()
    } catch (error) {
      isOnline.value = false
      statusDetail.value = `无法连接检测后端 ${apiUrl.value}`
    }
  }

  const fetchModels = async () => {
    try {
      const data = await safeFetch('/api/models')
      if (data.models && data.models.length > 0) {
        availableModels.value = data.models
        // Only set default if not already set
        if (!settings.model) {
          settings.model = data.models[0].name
        }
      }
    } catch (error) {
      console.error('Failed to fetch models:', error)
    }
  }

  const safeFetch = async (endpoint, options = {}) => {
    const url = endpoint.startsWith('http') ? endpoint : `${apiUrl.value}${endpoint}`
    try {
      const response = await fetch(url, options)
      const contentType = response.headers.get('content-type') || ''
      
      let payload
      if (contentType.includes('application/json')) {
        payload = await response.json()
      } else {
        payload = { error: await response.text() }
      }

      if (!response.ok) {
        throw new Error(payload.error || payload.message || `请求失败（HTTP ${response.status}）`)
      }
      return payload
    } catch (error) {
      console.error('API request failed:', error)
      const message = error.message.includes('Failed to fetch') 
        ? `无法连接检测后端 ${apiUrl.value}`
        : error.message
      throw new Error(message)
    }
  }

  const setApiUrl = (url) => {
    apiUrl.value = url.replace(/\/+$/, '')
    localStorage.setItem(API_STORAGE_KEY, apiUrl.value)
    checkHealth()
  }

  onMounted(checkHealth)

  return {
    apiUrl,
    isOnline,
    statusDetail,
    settings,
    availableModels,
    setApiUrl,
    checkHealth,
    safeFetch
  }
}
