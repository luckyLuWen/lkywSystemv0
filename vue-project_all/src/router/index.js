import { createRouter, createWebHistory } from 'vue-router'

import HomeDashboardView from '../views/HomeDashboardView.vue'
import AccidentDetectionView from '../views/AccidentDetectionView.vue'
import SensorManage from '../views/SensorManage.vue'
import SimulationView from '../views/SimulationView.vue'
import ModelingView from '../views/ModelingView.vue'
import CoordinationView from '../views/CoordinationView.vue'
import { canAccessRoute } from '../composables/useRoleAccess'

const routes = [
  { path: '/', component: HomeDashboardView },
  { path: '/realtime', component: AccidentDetectionView, meta: { roles: ['dispatcher', 'expert', 'admin'] } },
  { path: '/sensor-manage', component: SensorManage, meta: { roles: ['dispatcher', 'admin'] } },
  { path: '/coordination', component: CoordinationView, meta: { roles: ['commander', 'dispatcher', 'admin'] } },
  { path: '/modeling', component: ModelingView, meta: { roles: ['commander', 'expert', 'admin'] } },
  { path: '/modeling-1', redirect: '/modeling?sys=1' },
  { path: '/modeling-2', redirect: '/modeling?sys=2' },
  { path: '/simulation', component: SimulationView, meta: { roles: ['commander', 'expert', 'admin'] } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (!canAccessRoute(to.meta.roles || [])) {
    return { path: '/', query: { notice: 'access-denied' } }
  }
  return true
})

export default router
