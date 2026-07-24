import sys

file_path = 'src/components/home/HomeCesiumGlobe.vue'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    <!-- 📋 推演阶段说明悬浮卡片 -->
    <transition name="phase-card-fade">
      <div v-if="phaseDescVisible && currentPhaseDesc" class="phase-desc-card"
        :style="{ left: phaseCardConfig.left + 'px', bottom: phaseCardConfig.bottom + 'px', width: phaseCardConfig.width + 'px', fontSize: phaseCardConfig.fontSize + 'px' }"
      >
        <!-- 切换事件场景 Tabs -->
        <div class="phase-card-scene-tabs">
          <button 
            :class="{ active: isTruckScene }" 
            @click="switchCameraScene('truck')"
          >
            🚚 货车追尾
          </button>
          <button 
            :class="{ active: !isTruckScene }" 
            @click="switchCameraScene('tanker')"
          >
            ⛽ 油罐车泄露
          </button>
        </div>

        <div class="phase-desc-card-header">
          <span class="phase-desc-card-icon">{{ isTruckScene ? '🚚' : '⛽' }}</span>
          <span class="phase-desc-card-step">阶段 {{ String(props.activePhaseIndex + 1).padStart(2, '0') }}</span>
          <span class="phase-desc-card-label">{{ currentPhaseDesc.shortLabel }}</span>
          <span class="phase-desc-card-time">{{ currentPhaseDesc.time }}</span>
          <button class="phase-desc-card-tune-btn" @click.stop="phaseCardConfig.showTweak = !phaseCardConfig.showTweak" title="微调卡片位置">⚙️</button>
          <button class="phase-desc-card-close" @click="phaseDescVisible = false">✕</button>
        </div>
        <div class="phase-desc-card-body" :style="{ fontSize: phaseCardConfig.fontSize + 'px' }">{{ currentPhaseDesc.description }}</div>
      </div>
    </transition>

    <!-- 📋 阶段卡片位置大小微调面板 -->
    <div v-if="phaseCardConfig.showTweak" class="phase-card-tweak-panel">
      <div class="phase-card-tweak-header">
        <span>📋 阶段卡片微调</span>
        <button class="phase-card-tweak-close" @click="phaseCardConfig.showTweak = false">✕</button>
      </div>
      <div class="phase-card-tweak-body">
        <div class="phase-card-tweak-row">
          <label>左边距离 (px)</label>
          <input type="range" v-model.number="phaseCardConfig.left" min="0" max="800" step="1" class="pct-slider" />
          <input type="number" v-model.number="phaseCardConfig.left" min="0" max="800" class="pct-num" />
        </div>
        <div class="phase-card-tweak-row">
          <label>底边距离 (px)</label>
          <input type="range" v-model.number="phaseCardConfig.bottom" min="0" max="800" step="1" class="pct-slider" />
          <input type="number" v-model.number="phaseCardConfig.bottom" min="0" max="800" class="pct-num" />
        </div>
        <div class="phase-card-tweak-row">
          <label>卡片宽度 (px)</label>
          <input type="range" v-model.number="phaseCardConfig.width" min="160" max="800" step="4" class="pct-slider" />
          <input type="number" v-model.number="phaseCardConfig.width" min="160" max="800" class="pct-num" />
        </div>
        <div class="phase-card-tweak-row">
          <label>正文字号 (px)</label>
          <input type="range" v-model.number="phaseCardConfig.fontSize" min="9" max="28" step="0.5" class="pct-slider" />
          <input type="number" v-model.number="phaseCardConfig.fontSize" min="9" max="28" step="0.5" class="pct-num" />
        </div>
        <div class="phase-card-tweak-btn-row">
          <button class="phase-card-tweak-reset" @click="resetPhaseCardConfig">↩ 重置默认</button>
          <button class="phase-card-tweak-save" @click="savePhaseCardDefaults">📌 设为默认</button>
        </div>
      </div>
    </div>
"""

target2 = """const TRUCK_PHASE_DESC = [
  { shortLabel: '仿真推演开始', time: '14:00', description: '系统完成初始化，开始对货车追尾事故场景进行数字孪生仿真推演，全域感知网络进入就绪状态。' },
  { shortLabel: '车辆正常行驶', time: '14:05', description: '事故发生前，两辆货车在高速公路上正常行驶，车载边缘网关实时采集并上传行驶状态数据。' },
  { shortLabel: '事故发生', time: '14:12', description: '后车未保持安全距离，发生追尾碰撞。传感网络检测到异常冲击振动，自动触发事故告警并上报指挥中心。' },
  { shortLabel: '次生灾害·烟雾', time: '14:18', description: '碰撞导致货物起火，现场产生大量浓烟。烟雾传感器浓度超过预警阈值，系统自动推送疏散建议。' },
  { shortLabel: '次生灾害·起火', time: '14:26', description: '发动机舱引燃，车辆开始明显燃烧。温度传感器数据急剧上升，协同响应系统推送消防出警指令。' },
  { shortLabel: '次生灾害·大火', time: '14:40', description: '火势向周边蔓延，已波及多辆车辆。系统评估扩散模型，向救援指挥中心同步实时火情态势图。' },
  { shortLabel: '无人装备出动', time: '14:45', description: '无人车与无人机从消防站协同出发。无人车沿蓝线地面路径先行，无人机走到一半时起飞，两者同时抵达救援点。' },
  { shortLabel: '无人感知部署', time: '14:50', description: '无人装备到达事故现场，按预规划坐标完成传感节点的自动布设，形成现场多维感知覆盖网络。' },
  { shortLabel: '无人感知执行', time: '14:55', description: '无人机开始绕现场执行低空侦察任务，实时回传高清图像；无人车同步采集地面化学环境数据。' },
  { shortLabel: '救援装备出动', time: '15:00', description: '指挥中心根据感知数据研判灾情，专业救援队伍携带重型装备出动，进入最终处置阶段。' },
]

const TANKER_PHASE_DESC = [
  { shortLabel: '仿真推演开始', time: '15:00', description: '系统完成初始化，开始对油罐车侧翻泄露事故场景进行数字孪生仿真推演，全域感知网络进入就绪状态。' },
  { shortLabel: '车辆正常行驶', time: '15:05', description: '油罐车在省道上满载运输危化品，车载传感器实时监测罐体压力、温度及行驶姿态，一切正常。' },
  { shortLabel: '事故发生·侧翻', time: '15:12', description: '车辆在弯道处发生侧翻，冲击传感器触发一级告警，指挥中心立即启动危化品事故应急响应流程。' },
  { shortLabel: '次生灾害·泄露', time: '15:20', description: '罐体受碰撞损坏，化学品开始向外泄露。TVOC传感器浓度迅速攀升，系统推送危险区域隔离指令。' },
  { shortLabel: '次生灾害·弥漫', time: '15:35', description: '泄露液体扩散至路面并开始挥发，大面积有毒气体向四周弥漫，系统推送周边1公里疏散建议。' },
  { shortLabel: '次生灾害·扩散', time: '15:50', description: '挥发气体随风向继续扩散，系统结合实时风速风向数据生成动态扩散预测模型，划定动态禁区。' },
  { shortLabel: '无人装备出动', time: '15:55', description: '无人车与无人机从黄州区路口镇消防站协同出发。无人车先行，无人机在其走到一半时起飞追赶，同时到达现场。' },
  { shortLabel: '无人感知部署', time: '16:00', description: '无人装备抵达现场，自动规避高浓度危险区域，在安全边界内完成TVOC、CO等传感节点的精准布设。' },
  { shortLabel: '无人感知执行', time: '16:05', description: '无人机在安全高度执行现场侦察，实时回传画面；无人车持续采集地面气体数据，辅助研判扩散态势。' },
  { shortLabel: '救援装备出动', time: '16:10', description: '指挥中心根据感知数据确认现场态势，专业危化品处置队伍携带防护装备出动，进行最终封堵处置。' },
]

const isTruckScene = computed(() => props.phases?.[0]?.id?.startsWith('t-') ?? true)
const phaseDescAllData = computed(() => isTruckScene.value ? TRUCK_PHASE_DESC : TANKER_PHASE_DESC)

const phaseCardConfig = reactive({
  left: 255,
  bottom: 725,
  width: 328,
  fontSize: 28,
  showTweak: false
})

const phaseCardDefaults = reactive({ left: 255, bottom: 725, width: 328, fontSize: 28 })

function savePhaseCardDefaults() {
  phaseCardDefaults.left = phaseCardConfig.left
  phaseCardDefaults.bottom = phaseCardConfig.bottom
  phaseCardDefaults.width = phaseCardConfig.width
  phaseCardDefaults.fontSize = phaseCardConfig.fontSize
}

function resetPhaseCardConfig() {
  phaseCardConfig.left = phaseCardDefaults.left
  phaseCardConfig.bottom = phaseCardDefaults.bottom
  phaseCardConfig.width = phaseCardDefaults.width
  phaseCardConfig.fontSize = phaseCardDefaults.fontSize
}

const phaseDescVisible = ref(false)
const currentPhaseDesc = computed(() => phaseDescAllData.value[props.activePhaseIndex] || null)

watch(() => props.activePhaseIndex, () => {
  phaseDescVisible.value = true
})
"""

import re
css_pattern = re.compile(r'/\* ========================================\n   📋 推演阶段说明悬浮卡片\n   ======================================== \*/.*?/\* ================================================================\n   🚨 救援装备出动操控面板样式\n   ================================================================ \*/', re.DOTALL)


if target1 in content:
    content = content.replace(target1, '')
else:
    print('target1 not found')

if target2 in content:
    content = content.replace(target2, '')
else:
    print('target2 not found')

content = css_pattern.sub('/* ================================================================\n   🚨 救援装备出动操控面板样式\n   ================================================================ */', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Success')
