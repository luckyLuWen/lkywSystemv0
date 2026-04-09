import { reactive } from 'vue'

export const store = reactive({
  connected: false,
  status: "🔴 离线",
  data: {
    node1: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node2: { temp: 0, hum: 0, smoke: 0, tvoc: 0, co: 0 },
    node3: { wind: 0, wind_dir: "北" }
  }
})