import { buildIntegrationHubApiUrl, buildIntegrationHubSseUrl } from '../config/subsystems'
import { applyIntegrationEvent, setIntegrationConnection } from './situationStore'

let eventSource = null

export async function fetchRecentIntegrationEvents(baseUrl) {
  const response = await fetch(buildIntegrationHubApiUrl('api/events/recent?count=30', baseUrl), {
    cache: 'no-store',
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  const payload = await response.json()
  ;(payload.events || []).forEach(applyIntegrationEvent)
  return payload
}

export async function publishIntegrationCommand(baseUrl, command) {
  const response = await fetch(buildIntegrationHubApiUrl('api/commands', baseUrl), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      source: 'home-dashboard',
      ...command,
    }),
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export function connectIntegrationHubEvents(baseUrl) {
  disconnectIntegrationHubEvents()

  const sseUrl = buildIntegrationHubSseUrl(baseUrl)
  setIntegrationConnection({
    state: 'connecting',
    hubUrl: baseUrl,
    lastError: '',
    connectedAt: '',
  })

  eventSource = new EventSource(sseUrl)

  eventSource.addEventListener('integration-ready', () => {
    setIntegrationConnection({
      state: 'connected',
      hubUrl: baseUrl,
      lastError: '',
      connectedAt: new Date().toISOString(),
    })
  })

  eventSource.addEventListener('integration-event', (message) => {
    try {
      applyIntegrationEvent(JSON.parse(message.data))
    } catch (error) {
      setIntegrationConnection({
        state: 'error',
        lastError: error instanceof Error ? error.message : '事件解析失败',
      })
    }
  })

  eventSource.addEventListener('integration-error', (message) => {
    setIntegrationConnection({
      state: 'error',
      lastError: message.data || 'Integration Hub 事件流异常',
    })
  })

  eventSource.onerror = () => {
    setIntegrationConnection({
      state: 'error',
      lastError: '无法连接 Integration Hub SSE',
    })
  }

  return eventSource
}

export function disconnectIntegrationHubEvents() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}
