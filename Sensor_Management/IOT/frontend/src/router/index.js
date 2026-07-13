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
import Node3Overview from '../views/Node3Overview.vue'
import Node4Overview from '../views/Node4Overview.vue'
import Node5Overview from '../views/Node5Overview.vue'
import Node4View from '../views/Node4View.vue'
import Node3View from '../views/Node3View.vue'
import Node5View from '../views/Node5View.vue'
import Node6View from '../views/Node6View.vue'
import Node7View from '../views/Node7View.vue'
import DroneView from '../views/DroneView.vue'
import DroneView1 from '../views/DroneView1.vue'
import DroneView2 from '../views/DroneView2.vue'

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
  { path: '/node4', component: Node3Overview },
  { path: '/node5', component: Node4Overview },
  { path: '/node6', component: Node5Overview },
  // --- 固定环境感知节点总控与无人机 --
  { path: '/node3', component: Node3View },
  { path: '/node7', component: Node4View },
  { path: '/node8', component: Node5View },
  { path: '/node9', component: Node6View },
  { path: '/node10', component: Node7View },
  { path: '/drone', component: DroneView },
  { path: '/drone1', component: DroneView1 },
  { path: '/drone2', component: DroneView2 }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router