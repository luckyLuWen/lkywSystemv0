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
    node1: createNodeState("感知单元(UGV)-001"),
    node2: createNodeState("感知单元(UGV)-002"),
    node4: createNodeState("感知单元(UGV)-003"),
    node5: createNodeState("感知单元(UGV)-004"),
    node6: createNodeState("感知单元(UGV)-005"),
    node3: createNodeState("固定环境感知节点总控-001"),
    node7: createNodeState("固定环境感知节点总控-002"),
    node8: createNodeState("固定环境感知节点总控-003"),
    node9: createNodeState("固定环境感知节点总控-004"),
  },
  data: {
    node1: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node2: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node4: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node5: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node6: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node3: { wind: 0, wind_dir: "北" },
    node7: { wind: 0, wind_dir: "北" },
    node8: { wind: 0, wind_dir: "北" },
    node9: { wind: 0, wind_dir: "北" },
  },
})
