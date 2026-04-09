<template>
  <div class="system-dashboard">
    <!-- 左侧面板 -->
    <aside class="left-panel">
      <div class="card">
        <div class="card-title">应急任务年度统计</div>
        <div class="stat-list">
          <div class="stat-item">
            <div class="stat-label">
              <span class="stat-icon cyan"></span>
              <span>任务数量</span>
            </div>
            <span class="stat-value">1802</span>
          </div>
          <div class="stat-sub">A级 32% &nbsp; B级 28% &nbsp; C级 40%</div>
          
          <div class="stat-item">
            <div class="stat-label">
              <span class="stat-icon red"></span>
              <span>待完成数量</span>
            </div>
            <span class="stat-value">106</span>
          </div>
          
          <div class="stat-item">
            <div class="stat-label">
              <span class="stat-icon green"></span>
              <span>已完成数量</span>
            </div>
            <span class="stat-value">1693</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title flex-between">
          应急任务栏
          <span class="more-btn">更多 ></span>
        </div>
        <div class="task-tabs">
          <span class="active">新任务</span>
          <span>进行中</span>
          <span>已完结</span>
        </div>
        <ul class="task-list">
          <li v-for="i in 4" :key="i">
            <span>某时某地发生车祸</span> 
            <span class="date">2020*-1-21</span>
          </li>
        </ul>
      </div>
    </aside>

    <!-- 中间空白区域 -->
    <div class="center-map">
      <!-- 空白区域 -->
    </div>

    <!-- 右侧面板 -->
    <aside class="right-panel">
      <div class="card">
        <div class="card-title">气象预警</div>
        <div class="weather-box">
          <div class="weather-item">
            <span class="date">2025/12/24</span>
            <span class="temp">25°C</span>
            <span>☁️ 多云</span>
            <span class="range">11-25 °C</span>
          </div>
          <div class="weather-item">
            <span class="date">2025/12/25</span>
            <span class="temp">25°C</span>
            <span>☀️ 晴</span>
            <span class="range">20-26 °C</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">通知栏</div>
        <div class="notification-carousel">
          <div class="notification-item active">
            <span class="notification-content">系统将于今晚23:00进行例行维护</span>
          </div>
          <div class="notification-item">
            <span class="notification-content">传感器固件已更新至最新版本</span>
          </div>
          <div class="notification-item">
            <span class="notification-content">第一季度报告已生成</span>
          </div>
        </div>
        <div class="carousel-indicators">
          <span class="indicator active"></span>
          <span class="indicator"></span>
          <span class="indicator"></span>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
// 系统大屏页面逻辑
</script>

<style scoped>
.system-dashboard {
  display: flex;
  width: 100%;
  height: 100%;
}

/* 左右面板样式 */
.left-panel,
.right-panel {
  flex: 0 0 300px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 0 10px;
}

/* 中间空白区域 */
.center-map {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
}

/* 基础卡片样式 */
.card {
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  box-shadow: inset 0 0 15px rgba(0, 229, 255, 0.1);
  backdrop-filter: blur(5px);
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 18px;
  color: var(--primary-color);
  margin-bottom: 20px;
  text-shadow: var(--glow-shadow);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.more-btn {
  font-size: 14px;
  cursor: pointer;
  color: #aaa;
}

/* 统计数据样式 */
.stat-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  box-shadow: 0 0 8px currentColor;
}

.stat-icon.cyan {
  background-color: #00e5ff;
  color: #00e5ff;
}

.stat-icon.red {
  background-color: #ff3333;
  color: #ff3333;
}

.stat-icon.green {
  background-color: #33ff33;
  color: #33ff33;
}

.stat-value {
  font-size: 22px;
  color: var(--primary-color);
  font-family: monospace;
  font-weight: bold;
}

.stat-sub {
  font-size: 12px;
  color: #aaa;
  margin-left: 26px;
  margin-top: 4px;
}

/* 任务列表样式 */
.task-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 15px;
}

.task-tabs span {
  padding: 5px 15px;
  cursor: pointer;
  font-size: 14px;
  color: #aaa;
  transition: all 0.3s;
}

.task-tabs span.active {
  color: var(--primary-color);
  border-bottom: 2px solid var(--primary-color);
  text-shadow: var(--glow-shadow);
}

.task-list {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 14px;
  overflow-y: auto;
  flex: 1;
}

.task-list li {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: #ddd;
}

.task-list li .date {
  color: var(--primary-color);
  font-size: 12px;
}

/* 气象样式 */
.weather-box {
  display: flex;
  justify-content: space-around;
  text-align: center;
  font-size: 14px;
  flex: 1;
}

.weather-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #ddd;
}

.weather-item .temp {
  font-size: 20px;
  color: #ff9900;
  font-weight: bold;
}

.weather-item .range {
  color: #aaa;
  font-size: 12px;
}

/* 通知栏样式 */
.notification-carousel {
  flex: 1;
  display: flex;
  align-items: center;
  overflow: hidden;
  position: relative;
}

.notification-item {
  position: absolute;
  width: 100%;
  opacity: 0;
  transition: opacity 0.5s ease;
}

.notification-item.active {
  opacity: 1;
  position: relative;
}

.notification-content {
  color: #ddd;
  font-size: 14px;
  line-height: 1.5;
}

.carousel-indicators {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 15px;
}

.indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  cursor: pointer;
  transition: all 0.3s;
}

.indicator.active {
  background: var(--primary-color);
  box-shadow: 0 0 8px var(--primary-color);
  transform: scale(1.2);
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 229, 255, 0.3);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 229, 255, 0.5);
}
</style>