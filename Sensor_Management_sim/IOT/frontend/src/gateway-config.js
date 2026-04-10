const DEFAULT_EDGE_GATEWAY_BASE_URL = "http://127.0.0.1:18080"
const STORAGE_KEY = "sensorManagement.edgeBaseUrl"

function normalizeBaseUrl(value) {
  if (!value || typeof value !== "string") return ""
  const trimmed = value.trim()
  if (!trimmed) return ""
  const withProtocol = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed)
    ? trimmed
    : `http://${trimmed}`
  return withProtocol.replace(/\/+$/, "")
}

function getQueryBaseUrl() {
  if (typeof window === "undefined") return ""
  try {
    return new URL(window.location.href).searchParams.get("edgeBase") || ""
  } catch {
    return ""
  }
}

function getStorageBaseUrl() {
  if (typeof window === "undefined") return ""
  try {
    return window.localStorage.getItem(STORAGE_KEY) || ""
  } catch {
    return ""
  }
}

function pickBaseUrl() {
  const queryBase = normalizeBaseUrl(getQueryBaseUrl())
  const envBase = normalizeBaseUrl(import.meta.env.VITE_SENSOR_EDGE_BASE_URL)
  const storageBase = normalizeBaseUrl(getStorageBaseUrl())

  return queryBase || storageBase || envBase || DEFAULT_EDGE_GATEWAY_BASE_URL
}

export const EDGE_GATEWAY_BASE_URL = pickBaseUrl()
export const EDGE_GATEWAY_API_BASE_URL = `${EDGE_GATEWAY_BASE_URL}/api`
export const EDGE_GATEWAY_WS_URL = `${EDGE_GATEWAY_BASE_URL.replace(/^http/i, (value) =>
  value.toLowerCase() === "https" ? "wss" : "ws"
)}/ws`

export function buildGatewayApiUrl(path = "") {
  const normalizedPath = String(path).replace(/^\/+/, "")
  return normalizedPath ? `${EDGE_GATEWAY_API_BASE_URL}/${normalizedPath}` : EDGE_GATEWAY_API_BASE_URL
}

export function buildGatewayVideoUrl() {
  return `${buildGatewayApiUrl("video_feed")}?t=${Date.now()}`
}

export function buildGatewayExportUrl(params = {}) {
  const url = new URL(buildGatewayApiUrl("export"))
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value)
    }
  })
  return url.toString()
}

export function buildGatewayHistoryUrl(params = {}) {
  const url = new URL(buildGatewayApiUrl("history"))
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value)
    }
  })
  return url.toString()
}
