import { reactive } from "vue"
import { EDGE_GATEWAY_BASE_URL } from "./gateway-config"

function createNodeState(label) {
  return {
    label,
    display_name: label,
    online: false,
    address: "",
    type: "",
    last_success_at: "",
    last_error: "",
  }
}

export const store = reactive({
  gatewayBaseUrl: EDGE_GATEWAY_BASE_URL,
  gatewayMode: "edge",
  gatewayOnline: false,
  connected: false,
  status: "离线",
  samplingRunning: false,
  lastSampleAt: "",
  lastRealtimeAt: "",
  databaseOnline: false,
  videoOnline: false,
  nodes: {
    node1: createNodeState("监测点 A"),
    node2: createNodeState("监测点 B"),
    node3: createNodeState("气象站"),
  },
  data: {
    node1: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node2: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node3: { wind: 0, wind_dir: "北" },
  },
})
