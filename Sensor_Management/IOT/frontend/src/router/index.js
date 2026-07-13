import { createRouter, createWebHashHistory } from 'vue-router'

// 1. 首页总览
import Overview from '../views/Overview.vue' 

// 2. 逻辑图谱相关组件
import LogicView from '../views/LogicView.vue'       // 全局桑基图容器
import LogicEarly from '../views/LogicEarly.vue'     // 前期
import LogicConfirm from '../views/LogicConfirm.vue' // 中期
import LogicSpread from '../views/LogicSpread.vue'   // 后期
import LogicNoise from '../views/LogicNoise.vue'     // 环境干扰

// 3. 节点及其他组件
import Node1Overview from '../views/Node1Overview.vue'
import Node2Overview from '../views/Node2Overview.vue'
import Node3View from '../views/Node3View.vue'
import DroneView from '../views/DroneView.vue'

const routes = [
  // --- 核心入口 ---
  { path: '/', component: Overview },

  // --- 逻辑图谱组 ---
  { path: '/logic', component: LogicView },
  { path: '/logic/early', component: LogicEarly },
  { path: '/logic/confirm', component: LogicConfirm },
  { path: '/logic/spread', component: LogicSpread },
  { path: '/logic/noise', component: LogicNoise },

  // --- 节点概览 (已移除环境与气象子路由) ---
  { path: '/node1', component: Node1Overview },
  { path: '/node2', component: Node2Overview },

  // --- 固定环境感知节点总控与无人机 ---
  { path: '/node3', component: Node3View },
  { path: '/drone', component: DroneView }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router