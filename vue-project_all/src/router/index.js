import { createRouter, createWebHistory } from 'vue-router'

import HomeDashboardView from '../views/HomeDashboardView.vue'
import AccidentDetectionView from '../views/AccidentDetectionView.vue'
import SensorManage from '../views/SensorManage.vue'
import SimulationView from '../views/SimulationView.vue'
import ModelingView from '../views/ModelingView.vue'
import CoordinationView from '../views/CoordinationView.vue'

const routes = [
  { path: '/', component: HomeDashboardView },
  { path: '/realtime', component: AccidentDetectionView },
  { path: '/sensor-manage', component: SensorManage },
  { path: '/coordination', component: CoordinationView },
  { path: '/modeling', component: ModelingView },
  { path: '/modeling-1', redirect: '/modeling?sys=1' },
  { path: '/modeling-2', redirect: '/modeling?sys=2' },
  { path: '/simulation', component: SimulationView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
