const DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL = 'http://127.0.0.1:18601'
const DEFAULT_COLLABORATIVE_STREAMLIT_URL = 'http://127.0.0.1:8501/?embed=true'
const DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL = 'http://127.0.0.1:5001'

const STORAGE_KEYS = {
  controllerBaseUrl: 'lkyw.collaborative.controllerBaseUrl',
  streamlitUrl: 'lkyw.collaborative.streamlitUrl',
  commandCenterBaseUrl: 'lkyw.collaborative.commandCenterBaseUrl',
  legacySimulationUrl: 'lkyw.collaborative.simulationUrl',
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
  if (typeof window === 'undefined') return
  try {
    if (value) {
      window.localStorage.setItem(key, value)
    } else {
      window.localStorage.removeItem(key)
    }
  } catch {
    // Ignore storage failures and keep runtime values.
  }
}

function resetValue(key) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(key)
  } catch {
    // Ignore storage failures and fall back to defaults.
  }
}

function normalizeBaseUrl(value) {
  if (!value || typeof value !== 'string') return ''
  return value.trim().replace(/\/+$/, '')
}

function normalizeUrl(value) {
  if (!value || typeof value !== 'string') return ''
  return value.trim()
}

function getEnvValue(name) {
  return normalizeUrl(import.meta.env[name] || '')
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

export function getCollaborativeControllerBaseUrl() {
  return (
    normalizeBaseUrl(getQueryValue('controllerBase')) ||
    normalizeBaseUrl(getStorageValue(STORAGE_KEYS.controllerBaseUrl)) ||
    normalizeBaseUrl(getEnvValue('VITE_COLLABORATIVE_CONTROLLER_BASE_URL')) ||
    DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL
  )
}

export function persistCollaborativeControllerBaseUrl(value) {
  const normalized = normalizeBaseUrl(value) || DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL
  persistValue(STORAGE_KEYS.controllerBaseUrl, normalized)
  return normalized
}

export function resetCollaborativeControllerBaseUrl() {
  resetValue(STORAGE_KEYS.controllerBaseUrl)
  return DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL
}

export function getCollaborativeStreamlitUrl() {
  return (
    normalizeUrl(getQueryValue('streamlitUrl')) ||
    normalizeUrl(getStorageValue(STORAGE_KEYS.streamlitUrl)) ||
    normalizeUrl(getEnvValue('VITE_COLLABORATIVE_STREAMLIT_URL')) ||
    DEFAULT_COLLABORATIVE_STREAMLIT_URL
  )
}

export function persistCollaborativeStreamlitUrl(value) {
  const normalized = normalizeUrl(value) || DEFAULT_COLLABORATIVE_STREAMLIT_URL
  persistValue(STORAGE_KEYS.streamlitUrl, normalized)
  return normalized
}

export function resetCollaborativeStreamlitUrl() {
  resetValue(STORAGE_KEYS.streamlitUrl)
  return DEFAULT_COLLABORATIVE_STREAMLIT_URL
}

export function getCollaborativeCommandCenterBaseUrl() {
  return (
    normalizeBaseUrl(getQueryValue('commandCenterBase')) ||
    normalizeBaseUrl(getStorageValue(STORAGE_KEYS.commandCenterBaseUrl)) ||
    normalizeBaseUrl(getEnvValue('VITE_COLLABORATIVE_COMMAND_CENTER_BASE_URL')) ||
    deriveBaseUrl(getQueryValue('simulationUrl')) ||
    deriveBaseUrl(getStorageValue(STORAGE_KEYS.legacySimulationUrl)) ||
    DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL
  )
}

export function persistCollaborativeCommandCenterBaseUrl(value) {
  const normalized =
    normalizeBaseUrl(value) || DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL
  persistValue(STORAGE_KEYS.commandCenterBaseUrl, normalized)
  return normalized
}

export function resetCollaborativeCommandCenterBaseUrl() {
  resetValue(STORAGE_KEYS.commandCenterBaseUrl)
  return DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL
}

export function buildCollaborativeApiUrl(path = '', baseUrl = getCollaborativeControllerBaseUrl()) {
  const normalizedPath = String(path).replace(/^\/+/, '')
  const apiBaseUrl = normalizeBaseUrl(baseUrl)
  return normalizedPath ? `${apiBaseUrl}/${normalizedPath}` : apiBaseUrl
}

export function buildCommandCenterUrl(
  path = '',
  baseUrl = getCollaborativeCommandCenterBaseUrl()
) {
  const normalizedPath = String(path).replace(/^\/+/, '')
  const resolvedBase = normalizeBaseUrl(baseUrl)
  return normalizedPath ? `${resolvedBase}/${normalizedPath}` : resolvedBase
}

export function appendUrlParams(url, params = {}) {
  const normalized = normalizeUrl(url)
  if (!normalized) return ''

  const resolvedUrl = new URL(
    normalized,
    typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1'
  )
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    resolvedUrl.searchParams.set(key, String(value))
  })
  return resolvedUrl.toString()
}

export {
  DEFAULT_COLLABORATIVE_CONTROLLER_BASE_URL,
  DEFAULT_COLLABORATIVE_STREAMLIT_URL,
  DEFAULT_COLLABORATIVE_COMMAND_CENTER_BASE_URL,
}
