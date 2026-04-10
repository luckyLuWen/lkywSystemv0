import { buildGatewayApiUrl } from "./gateway-config"

async function requestJson(path, init) {
  const response = await fetch(buildGatewayApiUrl(path), init)
  if (!response.ok) {
    throw new Error(`gateway_request_failed:${response.status}`)
  }
  return response.json()
}

export function fetchGatewayHealth() {
  return requestJson("health")
}

export function fetchGatewayStatus() {
  return requestJson("status")
}

export function setGatewaySampling(active) {
  return requestJson("control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  })
}
