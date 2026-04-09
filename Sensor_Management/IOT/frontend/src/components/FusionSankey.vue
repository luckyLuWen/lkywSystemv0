<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

// --- 状态与引用 ---
const chartRef = ref(null)
let myChart = null

// --- 初始化桑基图 ---
const initChart = () => {
  if (!chartRef.value) return
  myChart = echarts.init(chartRef.value)

  // 1. 定义节点 (颜色配色方案)
  const nodes = [
    // 蓝色系：传感器输入
    { name: '烟雾传感器', itemStyle: { color: '#5470c6' } },
    { name: '红外摄像头', itemStyle: { color: '#5470c6' } },
    { name: 'CO传感器', itemStyle: { color: '#5470c6' } },
    { name: 'TVOC传感器', itemStyle: { color: '#5470c6' } },
    { name: '温度传感器', itemStyle: { color: '#5470c6' } },
    { name: '风速风向', itemStyle: { color: '#5470c6' } },
    { name: '湿度', itemStyle: { color: '#5470c6' } },

    // 橙色系：中间逻辑层
    { name: '逻辑:燃烧产物综合判定', itemStyle: { color: '#fac858' } },
    { name: '逻辑:热-气多维融合', itemStyle: { color: '#fac858' } },
    { name: '逻辑:态势预测', itemStyle: { color: '#fac858' } },
    { name: '逻辑:环境干扰清洗', itemStyle: { color: '#fac858' } },

    // 结果层
    { name: '决策:确证火灾警情', itemStyle: { color: '#c92a2a' } }, // 深红
    { name: '决策:早期隐患预警', itemStyle: { color: '#ee6666' } }, // 红
    { name: '决策:态势扩散分析', itemStyle: { color: '#73c0de' } }, // 蓝
    { name: '决策:环境干扰/非火灾', itemStyle: { color: '#91cc75' } } // 绿
  ]

  // 2. 定义连线 (逻辑流向)
  const links = [
    { source: "烟雾传感器", target: "逻辑:燃烧产物综合判定", value: 3 },
    { source: "红外摄像头", target: "逻辑:燃烧产物综合判定", value: 2 },
    { source: "CO传感器", target: "逻辑:燃烧产物综合判定", value: 2 },
    { source: "TVOC传感器", target: "逻辑:燃烧产物综合判定", value: 1 }, 
    { source: "逻辑:燃烧产物综合判定", target: "决策:确证火灾警情", value: 8 },

    { source: "温度传感器", target: "逻辑:热-气多维融合", value: 2 },
    { source: "TVOC传感器", target: "逻辑:热-气多维融合", value: 4 },
    { source: "红外摄像头", target: "逻辑:热-气多维融合", value: 4 },
    { source: "逻辑:热-气多维融合", target: "决策:早期隐患预警", value: 10 },

    { source: "风速风向", target: "逻辑:态势预测", value: 2 },
    { source: "TVOC传感器", target: "逻辑:态势预测", value: 1 },
    { source: "逻辑:态势预测", target: "决策:态势扩散分析", value: 3 },

    { source: "湿度", target: "逻辑:环境干扰清洗", value: 3 },
    { source: "烟雾传感器", target: "逻辑:环境干扰清洗", value: 1 },
    { source: "TVOC传感器", target: "逻辑:环境干扰清洗", value: 1 },
    { source: "逻辑:环境干扰清洗", target: "决策:环境干扰/非火灾", value: 5 },
  ]

  const option = {
    title: { 
        text: '决策逻辑溯源 (Sankey Flow)', 
        left: 'center', 
        top: '20',
        textStyle: { color: '#909399', fontSize: 14 } 
    },
    tooltip: { trigger: 'item', triggerOn: 'mousemove' },
    series: {
      type: 'sankey',
      layout: 'none',
      emphasis: { focus: 'adjacency' },
      data: nodes,
      links: links,
      top: '60px', bottom: '30px', left: '40px', right: '40px',
      nodeGap: 20,
      nodeWidth: 30,
      itemStyle: { borderWidth: 1, borderColor: '#aaa' },
      lineStyle: { color: 'source', opacity: 0.3, curveness: 0.5 },
      label: { color: '#333', fontSize: 13, fontWeight: 600 }
    }
  }

  myChart.setOption(option)
}

const handleResize = () => { myChart && myChart.resize() }

onMounted(async () => {
  await nextTick()
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (myChart) myChart.dispose()
})
</script>

<template>
  <div class="sankey-section">
    <div class="header-bar">
      <div class="left">
        <div class="titles">
          <h2>🧬 多传感器融合逻辑图谱</h2>
          <span class="subtitle">决策算法可视化 | 逻辑溯源</span>
        </div>
      </div>
      <div class="right-controls">
        <div class="status-badge bg-blue">
          🤖 算法运行中
        </div>
      </div>
    </div>

    <div class="chart-box">
      <div ref="chartRef" style="width: 100%; height: 600px;"></div>
    </div>

    <div class="info-section">
      <h3>📋 逻辑图例说明</h3>
      <div class="legend-row">
        <span class="legend-item"><span class="dot blue"></span> 传感器层</span>
        <span class="legend-item"><span class="dot yellow"></span> 逻辑判定层</span>
        <span class="legend-item"><span class="dot red"></span> 报警输出</span>
        <span class="legend-item"><span class="dot green"></span> 安全/排除</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 容器样式 */
.sankey-section {
  padding-top: 20px;
}

/* 头部栏 (复用风格) */
.header-bar { 
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; 
  background: white; padding: 15px 25px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.03); 
}
.titles h2 { margin: 0; color: #303133; font-size: 1.3rem; }
.subtitle { color: #909399; font-size: 0.85rem; }
.status-badge { padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 0.9rem; color: white; }
.bg-blue { background: #409eff; }

/* 图表卡片 */
.chart-box { 
  background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 20px; border: 1px solid #ebeef5;
}

/* 底部说明 */
.info-section { 
  background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); 
}
.info-section h3 { margin: 0 0 15px 0; font-size: 1rem; color: #606266; }
.legend-row { display: flex; gap: 20px; }
.legend-item { display: flex; align-items: center; font-size: 0.9rem; color: #606266; }
.dot { width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
.blue { background: #5470c6; }
.yellow { background: #fac858; }
.red { background: #ee6666; }
.green { background: #91cc75; }
</style>