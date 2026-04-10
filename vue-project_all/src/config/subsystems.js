const DEFAULT_SENSOR_GATEWAY_BASE_URL = 'http://127.0.0.1:18080'
const LEGACY_SENSOR_GATEWAY_BASE_URL = 'http://192.168.2.111:8000'
const DEFAULT_REALTIME_DETECTION_BASE_URL = 'http://127.0.0.1:5000'
const DEFAULT_REALTIME_RTSP_URL = 'rtsp://localhost:8554/live'
const DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL = 'http://127.0.0.1:18601'
const DEFAULT_COLLABORATIVE_STREAMLIT_URL = 'http://127.0.0.1:8501/?embed=true'
const DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL = 'http://127.0.0.1:5001'

const STORAGE_KEYS = {
  sensorGatewayBaseUrl: 'lkyw.sensorGatewayBaseUrl',
  realtimeDetectionBaseUrl: 'lkyw.realtimeDetectionBaseUrl',
  realtimeDetectionRtspUrl: 'lkyw.realtimeDetectionRtspUrl',
  collaborativeControllerBaseUrl: 'lkyw.collaborativeControllerBaseUrl',
  collaborativeStreamlitUrl: 'lkyw.collaborativeStreamlitUrl',
  collaborativeCommandCenterBaseUrl: 'lkyw.collaborativeCommandCenterBaseUrl',
  legacyCollaborativeSimulationUrl: 'lkyw.collaborativeSimulationUrl',
}

export function normalizeBaseUrl(value) {
  if (!value || typeof value !== 'string') return ''
  const trimmed = value.trim()
  if (!trimmed) return ''
  const withProtocol = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed)
    ? trimmed
    : `http://${trimmed}`
  return withProtocol.replace(/\/+$/, '')
}

export function normalizeUrl(value) {
  if (!value || typeof value !== 'string') return ''
  return value.trim()
}

function getQueryValue(name) {
  if (typeof window === 'undefined') return ''
  try {
    return new URL(window.location.href).searchParams.get(name) || ''
  } catch {
    return ''
  }
}

function getStorageValue(key) {
  if (typeof window === 'undefined') return ''
  try {
    return window.localStorage.getItem(key) || ''
  } catch {
    return ''
  }
}

function persistValue(key, value) {
  if (typeof window !== 'undefined') {
    try {
      if (value) {
        window.localStorage.setItem(key, value)
      } else {
        window.localStorage.removeItem(key)
      }
    } catch {
      // Ignore storage failures and still use runtime values.
    }
  }
}

function resetValue(key) {
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.removeItem(key)
    } catch {
      // Ignore storage failures and fall back to defaults.
    }
  }
}

function getEnvValue(name) {
  return normalizeBaseUrl(import.meta.env[name])
}

function getEnvUrl(name) {
  return normalizeUrl(import.meta.env[name] || '')
}

export function getSensorGatewayBaseUrl() {
  const storedValue = normalizeBaseUrl(getStorageValue(STORAGE_KEYS.sensorGatewayBaseUrl))
  const normalizedStoredValue =
    storedValue === LEGACY_SENSOR_GATEWAY_BASE_URL ? '' : storedValue

  return (
    normalizeBaseUrl(getQueryValue('sensorGatewayBase')) ||
    normalizedStoredValue ||
    getEnvValue('VITE_SENSOR_GATEWAY_BASE_URL') ||
    DEFAULT_SENSOR_GATEWAY_BASE_URL
  )
}

export function persistSensorGatewayBaseUrl(value) {
  const normalized = normalizeBaseUrl(value) || DEFAULT_SENSOR_GATEWAY_BASE_URL
  persistValue(STORAGE_KEYS.sensorGatewayBaseUrl, normalized)
  return normalized
}

export function resetSensorGatewayBaseUrl() {
  resetValue(STORAGE_KEYS.sensorGatewayBaseUrl)
  return DEFAULT_SENSOR_GATEWAY_BASE_URL
}

export function buildSensorGatewayApiUrl(path = '', baseUrl = getSensorGatewayBaseUrl()) {
  const normalizedPath = String(path).replace(/^\/+/, '')
  const apiBaseUrl = `${normalizeBaseUrl(baseUrl)}/api`
  return normalizedPath ? `${apiBaseUrl}/${normalizedPath}` : apiBaseUrl
}

export function buildSensorManagementIframeSrc(baseUrl = getSensorGatewayBaseUrl()) {
  const normalizedBase = normalizeBaseUrl(baseUrl) || DEFAULT_SENSOR_GATEWAY_BASE_URL
  return `/sensor-management/index.html?edgeBase=${encodeURIComponent(normalizedBase)}`
}

export function getCollaborativeControllerBaseUrl() {
  return (
    normalizeBaseUrl(getQueryValue('controllerBase')) ||
    normalizeBaseUrl(getStorageValue(STORAGE_KEYS.collaborativeControllerBaseUrl)) ||
    getEnvValue('VITE_COLLABORATIVE_CONTROLLER_BASE_URL') ||
    DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL
  )
}

export function persistCollaborativeControllerBaseUrl(value) {
  const normalized = normalizeBaseUrl(value) || DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL
  persistValue(STORAGE_KEYS.collaborativeControllerBaseUrl, normalized)
  return normalized
}

export function resetCollaborativeControllerBaseUrl() {
  resetValue(STORAGE_KEYS.collaborativeControllerBaseUrl)
  return DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL
}

export function getCollaborativeStreamlitUrl() {
  return (
    normalizeUrl(getQueryValue('streamlitUrl')) ||
    normalizeUrl(getStorageValue(STORAGE_KEYS.collaborativeStreamlitUrl)) ||
    getEnvUrl('VITE_COLLABORATIVE_STREAMLIT_URL') ||
    DEFAULT_COLLABORATIVE_STREAMLIT_URL
  )
}

export function persistCollaborativeStreamlitUrl(value) {
  const normalized = normalizeUrl(value) || DEFAULT_COLLABORATIVE_STREAMLIT_URL
  persistValue(STORAGE_KEYS.collaborativeStreamlitUrl, normalized)
  return normalized
}

export function resetCollaborativeStreamlitUrl() {
  resetValue(STORAGE_KEYS.collaborativeStreamlitUrl)
  return DEFAULT_COLLABORATIVE_STREAMLIT_URL
}

function deriveBaseUrl(value) {
  const normalized = normalizeUrl(value)
  if (!normalized) return ''
  try {
    const resolved = new URL(
      normalized,
      typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1'
    )
    return `${resolved.protocol}//${resolved.host}`
  } catch {
    return normalizeBaseUrl(normalized)
  }
}

export function getCollaborativeCommandCenterBaseUrl() {
  return (
    normalizeBaseUrl(getQueryValue('commandCenterBase')) ||
    normalizeBaseUrl(getStorageValue(STORAGE_KEYS.collaborativeCommandCenterBaseUrl)) ||
    getEnvValue('VITE_COLLABORATIVE_COMMAND_CENTER_BASE_URL') ||
    deriveBaseUrl(getQueryValue('simulationUrl')) ||
    deriveBaseUrl(getStorageValue(STORAGE_KEYS.legacyCollaborativeSimulationUrl)) ||
    DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL
  )
}

export function persistCollaborativeCommandCenterBaseUrl(value) {
  const normalized =
    normalizeBaseUrl(value) || DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL
  persistValue(STORAGE_KEYS.collaborativeCommandCenterBaseUrl, normalized)
  return normalized
}

export function resetCollaborativeCommandCenterBaseUrl() {
  resetValue(STORAGE_KEYS.collaborativeCommandCenterBaseUrl)
  return DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL
}

export function buildCollaborativeApiUrl(
  path = '',
  baseUrl = getCollaborativeControllerBaseUrl()
) {
  const normalizedPath = String(path).replace(/^\/+/, '')
  const apiBaseUrl = normalizeBaseUrl(baseUrl)
  return normalizedPath ? `${apiBaseUrl}/${normalizedPath}` : apiBaseUrl
}

export function buildCollaborativeResponseIframeSrc(
  controllerBaseUrl = getCollaborativeControllerBaseUrl(),
  streamlitUrl = getCollaborativeStreamlitUrl(),
  commandCenterBaseUrl = getCollaborativeCommandCenterBaseUrl()
) {
  return `/collaborative-response/index.html?controllerBase=${encodeURIComponent(
    normalizeBaseUrl(controllerBaseUrl) || DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL
  )}&streamlitUrl=${encodeURIComponent(
    normalizeUrl(streamlitUrl) || DEFAULT_COLLABORATIVE_STREAMLIT_URL
  )}&commandCenterBase=${encodeURIComponent(
    normalizeBaseUrl(commandCenterBaseUrl) || DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL
  )}`
}

export function getRealtimeDetectionBaseUrl() {
  return (
    normalizeBaseUrl(getQueryValue('realtimeDetectionBase')) ||
    normalizeBaseUrl(getStorageValue(STORAGE_KEYS.realtimeDetectionBaseUrl)) ||
    getEnvValue('VITE_REALTIME_DETECTION_BASE_URL') ||
    DEFAULT_REALTIME_DETECTION_BASE_URL
  )
}

export function persistRealtimeDetectionBaseUrl(value) {
  const normalized = normalizeBaseUrl(value) || DEFAULT_REALTIME_DETECTION_BASE_URL
  persistValue(STORAGE_KEYS.realtimeDetectionBaseUrl, normalized)
  return normalized
}

export function resetRealtimeDetectionBaseUrl() {
  resetValue(STORAGE_KEYS.realtimeDetectionBaseUrl)
  return DEFAULT_REALTIME_DETECTION_BASE_URL
}

export function getRealtimeDetectionRtspUrl() {
  return (
    getQueryValue('realtimeRtspUrl').trim() ||
    getStorageValue(STORAGE_KEYS.realtimeDetectionRtspUrl).trim() ||
    (import.meta.env.VITE_REALTIME_DETECTION_RTSP_URL || '').trim() ||
    DEFAULT_REALTIME_RTSP_URL
  )
}

export function persistRealtimeDetectionRtspUrl(value) {
  const normalized = String(value || '').trim() || DEFAULT_REALTIME_RTSP_URL
  persistValue(STORAGE_KEYS.realtimeDetectionRtspUrl, normalized)
  return normalized
}

export function resetRealtimeDetectionRtspUrl() {
  resetValue(STORAGE_KEYS.realtimeDetectionRtspUrl)
  return DEFAULT_REALTIME_RTSP_URL
}

export function buildRealtimeDetectionApiUrl(path = '', baseUrl = getRealtimeDetectionBaseUrl()) {
  const normalizedPath = String(path).replace(/^\/+/, '')
  const apiBaseUrl = normalizeBaseUrl(baseUrl)
  return normalizedPath ? `${apiBaseUrl}/${normalizedPath}` : apiBaseUrl
}

export function buildRealtimeDetectionIframeSrc(
  baseUrl = getRealtimeDetectionBaseUrl(),
  rtspUrl = getRealtimeDetectionRtspUrl()
) {
  const normalizedBase = normalizeBaseUrl(baseUrl) || DEFAULT_REALTIME_DETECTION_BASE_URL
  const resolvedRtspUrl = String(rtspUrl || '').trim() || DEFAULT_REALTIME_RTSP_URL

  return `/realtime-detection/index.html?apiBase=${encodeURIComponent(
    normalizedBase
  )}&rtspUrl=${encodeURIComponent(resolvedRtspUrl)}`
}

export {
  DEFAULT_SENSOR_GATEWAY_BASE_URL,
  DEFAULT_REALTIME_DETECTION_BASE_URL,
  DEFAULT_REALTIME_RTSP_URL,
  DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL,
  DEFAULT_COLLABORATIVE_STREAMLIT_URL,
  DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL,
}
