import { reactive } from 'vue'

const MAX_RECENT_EVENTS = 60
const MAX_RECENT_COMMANDS = 30

export const situationStore = reactive({
  connection: {
    state: 'idle',
    hubUrl: '',
    lastError: '',
    connectedAt: '',
  },
  recentEvents: [],
  sensor: {
    latestObservation: null,
    latestThreshold: null,
    samplingRunning: null,
  },
  detection: {
    activeStreams: {},
    latestFire: null,
    latestAccident: null,
  },
  commands: {
    byId: {},
    recent: [],
  },
})

function pushRecentEvent(event) {
  situationStore.recentEvents.unshift(event)
  if (situationStore.recentEvents.length > MAX_RECENT_EVENTS) {
    situationStore.recentEvents.splice(MAX_RECENT_EVENTS)
  }
}

function upsertCommandFromEvent(event) {
  const payload = event.payload || {}
  const commandId = payload.commandId || event.correlationId || event.subject
  if (!commandId) return

  const current = situationStore.commands.byId[commandId] || {}
  const next = {
    ...current,
    commandId,
    type: payload.commandType || current.type || '',
    target: payload.target || current.target || '',
    source: payload.source || current.source || event.source || '',
    status: payload.status || String(event.type || '').replace('command.', '') || current.status || '',
    message: payload.message || current.message || '',
    error: payload.error || current.error || '',
    result: payload.result || current.result || null,
    updatedAt: event.timestamp || payload.updatedAt || current.updatedAt || '',
    event,
  }

  situationStore.commands.byId[commandId] = next
  const existingIndex = situationStore.commands.recent.findIndex((item) => item.commandId === commandId)
  if (existingIndex >= 0) {
    situationStore.commands.recent.splice(existingIndex, 1)
  }
  situationStore.commands.recent.unshift(next)
  if (situationStore.commands.recent.length > MAX_RECENT_COMMANDS) {
    situationStore.commands.recent.splice(MAX_RECENT_COMMANDS)
  }
}

export function setIntegrationConnection(partial) {
  Object.assign(situationStore.connection, partial)
}

export function applyIntegrationEvent(event) {
  if (!event || typeof event !== 'object') return

  pushRecentEvent(event)

  switch (event.type) {
    case 'command.submitted':
    case 'command.accepted':
    case 'command.running':
    case 'command.completed':
    case 'command.failed':
      upsertCommandFromEvent(event)
      break
    case 'sensor.gateway.started':
      situationStore.sensor.samplingRunning = Boolean(event.payload?.running)
      break
    case 'sensor.observation.updated':
      situationStore.sensor.latestObservation = event
      situationStore.sensor.samplingRunning = Boolean(event.payload?.running)
      break
    case 'sensor.threshold.exceeded':
      situationStore.sensor.latestThreshold = event
      break
    case 'sensor.sampling.started':
      situationStore.sensor.samplingRunning = true
      break
    case 'sensor.sampling.stopped':
      situationStore.sensor.samplingRunning = false
      break
    case 'detection.stream.started':
      situationStore.detection.activeStreams[event.subject || event.payload?.streamId] = {
        running: true,
        event,
      }
      break
    case 'detection.stream.stopped':
      situationStore.detection.activeStreams[event.subject || event.payload?.streamId] = {
        running: false,
        event,
      }
      break
    case 'detection.fire.detected':
      situationStore.detection.latestFire = event
      break
    case 'detection.accident.confirmed':
      situationStore.detection.latestAccident = event
      break
    default:
      break
  }
}

export function resetIntegrationEvents() {
  situationStore.recentEvents.splice(0)
  situationStore.sensor.latestObservation = null
  situationStore.sensor.latestThreshold = null
  situationStore.sensor.samplingRunning = null
  situationStore.detection.latestFire = null
  situationStore.detection.latestAccident = null
  Object.keys(situationStore.detection.activeStreams).forEach((key) => {
    delete situationStore.detection.activeStreams[key]
  })
  Object.keys(situationStore.commands.byId).forEach((key) => {
    delete situationStore.commands.byId[key]
  })
  situationStore.commands.recent.splice(0)
}
