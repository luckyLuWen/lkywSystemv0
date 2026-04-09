<template>
  <div class="modeling-container">
    <h1>精细建模</h1>
    
    <div class="modeling-content">
      <!-- 左侧模型选择面板 -->
      <div class="model-selection">
        <h3>模型库</h3>
        <div class="model-list">
          <div class="model-item active">
            <div class="model-icon">🏗️</div>
            <div class="model-info">
              <div class="model-name">油罐车模型</div>
              <div class="model-desc">高精度油罐车3D模型</div>
            </div>
          </div>
          <div class="model-item">
            <div class="model-icon">🚚</div>
            <div class="model-info">
              <div class="model-name">货车模型</div>
              <div class="model-desc">高精度货车3D模型</div>
            </div>
          </div>
          <div class="model-item">
            <div class="model-icon">🚗</div>
            <div class="model-info">
              <div class="model-name">客车模型</div>
              <div class="model-desc">高精度客车3D模型</div>
            </div>
          </div>
          <div class="model-item">
            <div class="model-icon">🏢</div>
            <div class="model-info">
              <div class="model-name">建筑模型</div>
              <div class="model-desc">高精度建筑3D模型</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 中间建模区域 -->
      <div class="modeling-area">
        <div class="modeling-canvas">
          <div class="canvas-placeholder">
            <div class="placeholder-content">
              <div class="placeholder-icon">🔧</div>
              <div class="placeholder-text">3D建模画布</div>
              <div class="placeholder-desc">在此区域进行精细建模操作</div>
            </div>
          </div>
        </div>
        
        <!-- 建模工具栏 -->
        <div class="modeling-toolbar">
          <div class="tool-group">
            <button class="tool-btn active">
              <span class="tool-icon">📐</span>
              <span>测量</span>
            </button>
            <button class="tool-btn">
              <span class="tool-icon">✏️</span>
              <span>编辑</span>
            </button>
            <button class="tool-btn">
              <span class="tool-icon">🎨</span>
              <span>材质</span>
            </button>
            <button class="tool-btn">
              <span class="tool-icon">📷</span>
              <span>渲染</span>
            </button>
          </div>
        </div>
      </div>
      
      <!-- 右侧属性面板 -->
      <div class="model-properties">
        <h3>模型属性</h3>
        <div class="property-group">
          <div class="property-item">
            <label>模型名称</label>
            <input type="text" value="油罐车模型" class="property-input">
          </div>
          <div class="property-item">
            <label>模型尺寸</label>
            <div class="property-value">12.5m × 2.5m × 3.5m</div>
          </div>
          <div class="property-item">
            <label>模型材质</label>
            <select class="property-select">
              <option>金属</option>
              <option>塑料</option>
              <option>玻璃</option>
              <option>木材</option>
            </select>
          </div>
          <div class="property-item">
            <label>模型颜色</label>
            <div class="color-picker">
              <div class="color-preview" style="background-color: #3498db;"></div>
              <input type="color" value="#3498db" class="color-input">
            </div>
          </div>
        </div>
        
        <div class="action-buttons">
          <button class="action-btn primary">保存模型</button>
          <button class="action-btn">导出模型</button>
          <button class="action-btn">重置</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 精细建模页面逻辑
</script>

<style scoped>
.modeling-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
}

h1 {
  color: var(--primary-color);
  margin: 0 0 20px 0;
  text-shadow: var(--glow-shadow);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
}

.modeling-content {
  flex: 1;
  display: flex;
  gap: 20px;
  height: 100%;
}

/* 左侧模型选择面板 */
.model-selection {
  flex: 0 0 250px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
}

.model-selection h3 {
  color: var(--primary-color);
  margin: 0 0 15px 0;
  text-shadow: var(--glow-shadow);
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.model-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.model-item:hover {
  border-color: var(--primary-color);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.model-item.active {
  border-color: var(--primary-color);
  background: rgba(0, 229, 255, 0.1);
}

.model-icon {
  font-size: 24px;
}

.model-info {
  flex: 1;
}

.model-name {
  font-weight: bold;
  color: #fff;
}

.model-desc {
  font-size: 12px;
  color: #aaa;
}

/* 中间建模区域 */
.modeling-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.modeling-canvas {
  flex: 1;
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.canvas-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(4, 20, 40, 0.8) 0%, rgba(10, 27, 53, 0.8) 100%);
}

.placeholder-content {
  text-align: center;
  color: #aaa;
}

.placeholder-icon {
  font-size: 48px;
  margin-bottom: 10px;
  color: var(--primary-color);
}

.placeholder-text {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 5px;
  color: #fff;
}

.placeholder-desc {
  font-size: 14px;
  color: #aaa;
}

.modeling-toolbar {
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
}

.tool-group {
  display: flex;
  gap: 10px;
}

.tool-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: #aaa;
  cursor: pointer;
  transition: all 0.3s;
  flex: 1;
}

.tool-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.tool-btn.active {
  border-color: var(--primary-color);
  background: rgba(0, 229, 255, 0.1);
  color: var(--primary-color);
}

.tool-icon {
  font-size: 20px;
}

/* 右侧属性面板 */
.model-properties {
  flex: 0 0 300px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.model-properties h3 {
  color: var(--primary-color);
  margin: 0;
  text-shadow: var(--glow-shadow);
}

.property-group {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.property-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.property-item label {
  font-size: 14px;
  color: #aaa;
}

.property-input,
.property-select {
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
}

.property-input:focus,
.property-select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.property-value {
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
}

.color-picker {
  display: flex;
  align-items: center;
  gap: 10px;
}

.color-preview {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  cursor: pointer;
}

.color-input {
  flex: 1;
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  cursor: pointer;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: auto;
}

.action-btn {
  padding: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: #aaa;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.action-btn.primary {
  background: var(--primary-color);
  color: #020813;
  border-color: var(--primary-color);
  font-weight: bold;
}

.action-btn.primary:hover {
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.5);
}
</style>