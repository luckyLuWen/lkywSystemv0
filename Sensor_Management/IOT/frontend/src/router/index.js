import { createRouter, createWebHistory } from 'vue-router'

// 1. 首页总览
import Overview from '../views/Overview.vue' 

// 2. 逻辑图谱相关组件
import LogicView from '../views/LogicView.vue'       // 全局桑基图容器
import LogicEarly from '../views/LogicEarly.vue'     // 前期
import LogicConfirm from '../views/LogicConfirm.vue' // 中期
import LogicSpread from '../views/LogicSpread.vue'   // 后期
import LogicNoise from '../views/LogicNoise.vue'     // 环境干扰

// 3. 节点详情组件
import Node1Overview from '../views/Node1Overview.vue'
import Node1SensorTH from '../views/Node1SensorTH.vue'
import Node1SensorEnv from '../views/Node1SensorEnv.vue'

import Node2Overview from '../views/Node2Overview.vue'
import Node2SensorTH from '../views/Node2SensorTH.vue'
import Node2SensorEnv from '../views/Node2SensorEnv.vue'

import Node3View from '../views/Node3View.vue'
import DroneView from '../views/DroneView.vue'

const routes = [
  // --- 核心入口 ---
  { path: '/', component: Overview },

  // --- 逻辑图谱组 (全部独立路由) ---
  { path: '/logic', component: LogicView }, // 总图
  { path: '/logic/early', component: LogicEarly },
  { path: '/logic/confirm', component: LogicConfirm },
  { path: '/logic/spread', component: LogicSpread },
  { path: '/logic/noise', component: LogicNoise },

  // --- Node 1 ---
  { path: '/node1', component: Node1Overview },
  { path: '/node1/weather', component: Node1SensorTH },
  { path: '/node1/env', component: Node1SensorEnv },

  // --- Node 2 ---
  { path: '/node2', component: Node2Overview },
  { path: '/node2/weather', component: Node2SensorTH },
  { path: '/node2/env', component: Node2SensorEnv },

  // --- Node 3 ---
  { path: '/node3', component: Node3View },

  // --- 无人机 ---
  { path: '/drone', component: DroneView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router