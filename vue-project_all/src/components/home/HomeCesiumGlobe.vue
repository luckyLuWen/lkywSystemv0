<template>
  <div class="cesium-wrapper">
    <div id="cesiumContainer" ref="containerRef" class="cesium-container"></div>
    
    <!-- 飞行动画照片 -->
    <div
      v-for="photo in flyingPhotos"
      :key="photo.id"
      class="flying-photo"
      :style="{
        left: photo.x + 'px',
        top: photo.y + 'px',
        width: photo.width + 'px',
        height: photo.height + 'px',
        opacity: photo.opacity,
        backgroundImage: `url(${photo.src})`
      }"
    ></div>
    
    <!-- 🛠️ 右下角微调控制台：弹窗面板堆叠容器 -->
    <div class="bottom-right-panels-stack">
      <!-- 🚗 全省车流与巡航动态微调工具 弹窗面板 -->
      <div v-if="trafficConfig.show" class="camera-adjust-modal traffic-adjust-modal">
        <div class="camera-modal-header">
          <div class="header-title gold-title">
            <span class="icon">🚗</span>
            <span>全省车流与巡航动态微调工具</span>
          </div>
          <button class="close-btn" @click="trafficConfig.show = false">✕</button>
        </div>

        <div class="camera-modal-body">
          <!-- 行驶速度倍率 (Speed Factor) -->
          <div class="slider-row">
            <div class="slider-header">
              <span class="slider-label">车流行驶速度倍率</span>
              <span class="val-tag gold-tag">{{ trafficConfig.speedFactor.toFixed(1) }}x</span>
            </div>
            <div class="slider-control">
              <input 
                type="range" 
                v-model.number="trafficConfig.speedFactor" 
                min="0.1" 
                max="10.0" 
                step="0.1" 
                class="cyber-range-slider gold-slider"
              />
              <input 
                type="number" 
                v-model.number="trafficConfig.speedFactor" 
                min="0.1"
                max="10.0"
                step="0.1"
                class="cyber-num-input gold-input"
              />
            </div>
          </div>

          <!-- 线路最少行驶路程 (Min Route Distance) -->
          <div class="slider-row">
            <div class="slider-header">
              <span class="slider-label">线路最少行驶路程 (Km)</span>
              <span class="val-tag gold-tag">{{ (trafficConfig.minDistance / 1000).toFixed(1) }} km</span>
            </div>
            <div class="slider-control">
              <input 
                type="range" 
                v-model.number="trafficConfig.minDistance" 
                min="1000" 
                max="50000" 
                step="1000" 
                class="cyber-range-slider gold-slider"
                @change="reApplyTrafficRoutes"
              />
              <input 
                type="number" 
                :value="(trafficConfig.minDistance / 1000).toFixed(1)"
                @change="e => { trafficConfig.minDistance = Math.max(1000, Number(e.target.value) * 1000); reApplyTrafficRoutes(); }"
                class="cyber-num-input gold-input"
              />
            </div>
          </div>

          <!-- 巡航车辆密度 (Vehicle Count) -->
          <div class="slider-row">
            <div class="slider-header">
              <span class="slider-label">巡航车辆密度 (辆)</span>
              <span class="val-tag gold-tag">{{ trafficConfig.vehicleCount }} 辆</span>
            </div>
            <div class="slider-control">
              <input 
                type="range" 
                v-model.number="trafficConfig.vehicleCount" 
                min="5" 
                max="40" 
                step="1" 
                class="cyber-range-slider gold-slider"
                @change="reApplyTrafficRoutes"
              />
              <input 
                type="number" 
                v-model.number="trafficConfig.vehicleCount" 
                min="5"
                max="40"
                class="cyber-num-input gold-input"
                @change="reApplyTrafficRoutes"
              />
            </div>
          </div>

          <!-- 车辆类型快速筛选 -->
          <div class="form-row flex-col">
            <label class="form-label" style="margin-bottom: 6px;">两客一危类型筛选</label>
            <div class="vehicle-filter-tabs">
              <button :class="{ active: trafficConfig.activeCategory === 'all' }" @click="setVehicleCategoryFilter('all')">全部</button>
              <button :class="{ active: trafficConfig.activeCategory === 'hazard' }" @click="setVehicleCategoryFilter('hazard')">🧪 危化品车</button>
              <button :class="{ active: trafficConfig.activeCategory === 'passenger' }" @click="setVehicleCategoryFilter('passenger')">🚌 班线客车</button>
              <button :class="{ active: trafficConfig.activeCategory === 'tourist' }" @click="setVehicleCategoryFilter('tourist')">🚐 旅游包车</button>
            </div>
          </div>

          <!-- 按钮控制组 -->
          <div class="btn-group">
            <button class="action-btn-reset gold-btn" @click="resetTrafficConfig">
              🔄 重置车流默认参数
            </button>
          </div>
        </div>
      </div>

      <!-- 📹 全阶段相机视角微调工具 弹窗面板 -->
      <div v-if="cameraAdjust.show" class="camera-adjust-modal">
        <div class="camera-modal-header">
          <div class="header-title">
            <span class="icon">📹</span>
            <span>全阶段相机视角微调工具</span>
          </div>
          <button class="close-btn" @click="cameraAdjust.show = false">✕</button>
        </div>

        <div class="camera-modal-body">
          <!-- 场景选择按钮组 -->
          <div class="scene-toggle-group">
            <button 
              :class="{ active: cameraAdjust.scene === 'truck' }" 
              @click="switchCameraScene('truck')"
            >
              🚚 货车追尾现场
            </button>
            <button 
              :class="{ active: cameraAdjust.scene === 'tanker' }" 
              @click="switchCameraScene('tanker')"
            >
              ⛽ 油罐车泄露现场
            </button>
          </div>

          <!-- 推演阶段选择 -->
          <div class="form-row">
            <label class="form-label">推演阶段</label>
            <select v-model.number="cameraAdjust.phaseIndex" class="phase-select" @change="onPhaseSelectChange">
              <option v-for="(phase, idx) in currentPhaseOptions" :key="idx" :value="idx + 1">
                {{ idx + 1 }}: {{ phase.shortLabel || phase.title }}
              </option>
            </select>
          </div>

          <!-- 视距 (Range / m) -->
          <div class="slider-row">
            <label class="slider-label">视距 (Range / m)</label>
            <div class="slider-control">
              <input 
                type="range" 
                v-model.number="cameraAdjust.range" 
                min="200" 
                max="6000" 
                step="10" 
                class="cyber-range-slider"
                @input="applyCameraAdjust"
              />
              <input 
                type="number" 
                v-model.number="cameraAdjust.range" 
                class="cyber-num-input"
                @change="applyCameraAdjust"
              />
            </div>
          </div>

          <!-- 俯仰角 (Pitch / °) -->
          <div class="slider-row">
            <label class="slider-label">俯仰角 (Pitch / °)</label>
            <div class="slider-control">
              <input 
                type="range" 
                v-model.number="cameraAdjust.pitch" 
                min="-90" 
                max="0" 
                step="1" 
                class="cyber-range-slider"
                @input="applyCameraAdjust"
              />
              <input 
                type="number" 
                v-model.number="cameraAdjust.pitch" 
                class="cyber-num-input"
                @change="applyCameraAdjust"
              />
            </div>
          </div>

          <!-- 航向角 (Heading / °) -->
          <div class="slider-row">
            <label class="slider-label">航向角 (Heading / °)</label>
            <div class="slider-control">
              <input 
                type="range" 
                v-model.number="cameraAdjust.heading" 
                min="-180" 
                max="180" 
                step="1" 
                class="cyber-range-slider"
                @input="applyCameraAdjust"
              />
              <input 
                type="number" 
                v-model.number="cameraAdjust.heading" 
                class="cyber-num-input"
                @change="applyCameraAdjust"
              />
            </div>
          </div>

          <!-- 按钮控制组 -->
          <div class="btn-group">
            <button class="action-btn-reset" @click="resetCurrentPhaseDefaultView">
              🔄 重置当前阶段默认视角
            </button>
            <button class="action-btn-copy" @click="copyCurrentCameraParams">
              📋 复制当前视角配置参数
            </button>
          </div>

          <div v-if="cameraAdjust.copiedMsg" class="copied-feedback">
            {{ cameraAdjust.copiedMsg }}
          </div>
        </div>
      </div>

      <!-- 💡 现场灯光微调工具面板 -->
      <div v-if="isLightPanelExpanded" class="light-control-panel">
        <div class="light-panel-header" @click="toggleLightPanel">
          <span class="light-panel-title">💡 现场灯光微调工具</span>
          <span class="light-panel-toggle">✕</span>
        </div>
        
        <div class="light-panel-body">
          <div class="light-control-row">
            <label class="light-control-label">选择灯光</label>
            <div class="light-select-tabs">
              <button 
                v-for="(l, idx) in lights" 
                :key="l.id" 
                :class="['light-tab-btn', { active: activeLightIndex === idx }]"
                @click="activeLightIndex = idx"
              >
                {{ l.id }}
              </button>
            </div>
          </div>
          
          <div class="light-control-row">
            <label class="light-control-label">显示灯光模型</label>
            <input type="checkbox" v-model="lightAdjust.show" class="light-checkbox" />
          </div>
          
          <div class="light-control-row">
            <label class="light-control-label">经度 (Lng)</label>
            <input type="number" v-model.number="lightAdjust.lng" step="0.000001" class="light-input-num" />
          </div>
          
          <div class="light-control-row">
            <label class="light-control-label">纬度 (Lat)</label>
            <input type="number" v-model.number="lightAdjust.lat" step="0.000001" class="light-input-num" />
          </div>

          <div class="light-control-row">
            <label class="light-control-label">高度 (Height)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="lightAdjust.height" min="-20" max="100" step="0.1" class="light-slider" />
              <input type="number" v-model.number="lightAdjust.height" step="0.1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-control-row">
            <label class="light-control-label">缩放 (Scale)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="lightAdjust.scale" min="0.001" max="10.0" step="0.001" class="light-slider" />
              <input type="number" v-model.number="lightAdjust.scale" step="0.001" class="light-slider-input" />
            </div>
          </div>

          <div class="light-control-row">
            <label class="light-control-label">航向 (Heading)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="lightAdjust.heading" min="0" max="360" step="1" class="light-slider" />
              <input type="number" v-model.number="lightAdjust.heading" step="1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-control-row">
            <label class="light-control-label">俯仰 (Pitch)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="lightAdjust.pitch" min="-180" max="180" step="1" class="light-slider" />
              <input type="number" v-model.number="lightAdjust.pitch" step="1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-control-row">
            <label class="light-control-label">翻滚 (Roll)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="lightAdjust.roll" min="-180" max="180" step="1" class="light-slider" />
              <input type="number" v-model.number="lightAdjust.roll" step="1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-panel-buttons">
            <button @click="snapLightTo('truck')" class="light-btn">🚚 定位至货车点</button>
            <button @click="snapLightTo('tanker')" class="light-btn">⛽ 定位至油罐车点</button>
          </div>

          <div class="light-panel-buttons" style="flex-direction: column; gap: 6px;">
            <button @click="copyLightCoords" class="light-btn btn-primary">📋 复制当前灯光配置参数</button>
            <button @click="copyAllLightsCoords" class="light-btn">📋 复制所有灯光配置参数</button>
          </div>
          
          <div v-if="coordCopiedMessage" class="light-copied-msg">{{ coordCopiedMessage }}</div>
        </div>
      </div>

      <!-- 📡 5G通信基站微调工具面板 -->
      <div v-if="isJizhanPanelExpanded" class="light-control-panel jizhan-control-panel">
        <div class="light-panel-header" @click="toggleJizhanPanel">
          <span class="light-panel-title">5G通信基站微调工具 (jizhan.glb)</span>
          <span class="light-panel-toggle">✕</span>
        </div>
        
        <div class="light-panel-body">
          <div class="light-control-row">
            <label class="light-control-label">显示基站模型</label>
            <input type="checkbox" v-model="jizhanAdjust.show" class="light-checkbox" />
          </div>
          
          <div class="light-control-row">
            <label class="light-control-label">经度 (Lng)</label>
            <input type="number" v-model.number="jizhanAdjust.lng" step="0.000001" class="light-input-num" />
          </div>
          
          <div class="light-control-row">
            <label class="light-control-label">纬度 (Lat)</label>
            <input type="number" v-model.number="jizhanAdjust.lat" step="0.000001" class="light-input-num" />
          </div>

          <div class="light-control-row">
            <label class="light-control-label">高度 (Height)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="jizhanAdjust.height" min="-20" max="100" step="0.1" class="light-slider" />
              <input type="number" v-model.number="jizhanAdjust.height" step="0.1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-control-row">
            <label class="light-control-label">缩放 (Scale)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="jizhanAdjust.scale" min="0.01" max="50.0" step="0.1" class="light-slider" />
              <input type="number" v-model.number="jizhanAdjust.scale" step="0.1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-control-row">
            <label class="light-control-label">航向 (Heading)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="jizhanAdjust.heading" min="0" max="360" step="1" class="light-slider" />
              <input type="number" v-model.number="jizhanAdjust.heading" step="1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-control-row">
            <label class="light-control-label">俯仰 (Pitch)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="jizhanAdjust.pitch" min="-180" max="180" step="1" class="light-slider" />
              <input type="number" v-model.number="jizhanAdjust.pitch" step="1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-control-row">
            <label class="light-control-label">翻滚 (Roll)</label>
            <div class="light-slider-container">
              <input type="range" v-model.number="jizhanAdjust.roll" min="-180" max="180" step="1" class="light-slider" />
              <input type="number" v-model.number="jizhanAdjust.roll" step="1" class="light-slider-input" />
            </div>
          </div>

          <div class="light-panel-buttons">
            <button @click="snapJizhanToTruck" class="light-btn">重置定位至货车追尾点</button>
          </div>

          <div class="light-panel-buttons">
            <button @click="copyJizhanCoords" class="light-btn btn-primary">复制基站配置参数</button>
          </div>
          
          <div v-if="jizhanCopiedMessage" class="light-copied-msg">{{ jizhanCopiedMessage }}</div>
        </div>
      </div>

      <!-- 🏷️ 市级行政区文字标注微调面板 -->
      <div v-if="labelConfig.show" class="camera-adjust-modal label-adjust-modal">
        <div class="camera-modal-header">
          <div class="header-title">
            <span class="icon">🏷️</span>
            <span>市级行政区划标注字号微调</span>
          </div>
          <button class="close-btn" @click="labelConfig.show = false">✕</button>
        </div>

        <div class="camera-modal-body">
          <div class="slider-row">
            <div class="slider-header">
              <span class="slider-label">标注字号大小 (px)</span>
              <span class="val-tag gold-tag">{{ labelConfig.fontSize }} px</span>
            </div>
            <div class="slider-control">
              <input 
                type="range" 
                v-model.number="labelConfig.fontSize" 
                min="12" 
                max="36" 
                step="1" 
                class="cyber-range-slider gold-slider"
                @input="updateCityLabelsFont"
              />
              <input 
                type="number" 
                v-model.number="labelConfig.fontSize" 
                min="12"
                max="36"
                class="cyber-num-input gold-input"
                @change="updateCityLabelsFont"
              />
            </div>
          </div>

          <div class="slider-row">
            <div class="slider-header">
              <span class="slider-label">外圈描边厚度 (px)</span>
              <span class="val-tag gold-tag">{{ labelConfig.outlineWidth }} px</span>
            </div>
            <div class="slider-control">
              <input 
                type="range" 
                v-model.number="labelConfig.outlineWidth" 
                min="1" 
                max="8" 
                step="1" 
                class="cyber-range-slider gold-slider"
                @input="updateCityLabelsFont"
              />
              <input 
                type="number" 
                v-model.number="labelConfig.outlineWidth" 
                min="1"
                max="8"
                class="cyber-num-input gold-input"
                @change="updateCityLabelsFont"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 🛠️ 右下角微调控制台：悬浮按钮组 -->
    <div class="bottom-right-tool-dock">
      <button 
        class="dock-tool-btn label-btn" 
        :class="{ active: labelConfig.show }" 
        @click="labelConfig.show = !labelConfig.show"
      >
        标注字号微调
      </button>
      <button 
        class="dock-tool-btn camera-btn" 
        :class="{ active: cameraAdjust.show }" 
        @click="cameraAdjust.show = !cameraAdjust.show"
      >
        相机视角微调
      </button>
      <button 
        class="dock-tool-btn traffic-btn" 
        :class="{ active: trafficConfig.show }" 
        @click="trafficConfig.show = !trafficConfig.show"
      >
        车流动态微调
      </button>
      <button 
        class="dock-tool-btn light-btn" 
        :class="{ active: isLightPanelExpanded }" 
        @click="toggleLightPanel"
      >
        现场灯光微调
      </button>
      <button 
        class="dock-tool-btn jizhan-btn" 
        :class="{ active: isJizhanPanelExpanded }" 
        @click="toggleJizhanPanel"
      >
        5G基站微调
      </button>
    </div>


    <div v-if="loading" class="globe-mask">三维地球加载中...</div>
    <div v-else-if="errorMessage" class="globe-mask is-error">{{ errorMessage }}</div>

    <!-- 事故现场三级视角：事故详情悬浮窗 -->
    <div 
      v-if="accidentDetailPopup.show && props.focusedPointId" 
      class="accident-detail-popup"
      :style="{ left: accidentDetailPopup.x + 'px', top: accidentDetailPopup.y + 'px' }"
    >
      <div class="accident-detail-header">
        <span>{{ accidentDetailPopup.title }}</span>
        <button class="close-btn" @click="accidentDetailPopup.show = false">×</button>
      </div>
      <div class="accident-detail-body" @click="goToMediumView">
        <div class="img-wrapper">
          <img :src="accidentDetailPopup.img" class="accident-img" alt="事故实况" />
          <div class="img-hover-overlay">
            <span class="zoom-icon">🔍</span>
            <span>点击图片拉近视角观测</span>
          </div>
        </div>
      </div>
      <div class="accident-detail-arrow"></div>
    </div>

    <!-- 实时视频识别与检测悬浮窗 (次生灾害起火阶段 index === 4) -->
    <div 
      v-if="detectionPopup.show && props.activePhaseIndex === 4 && props.focusedPointId === 'accident_blue'" 
      class="detection-popup-panel"
      :style="{ left: detectionPopup.x + 'px', top: detectionPopup.y + 'px' }"
    >
      <div class="detection-popup-header">
        <div class="header-title-wrap">
          <span class="pulse-dot"></span>
          <span class="header-title">实时检测</span>
        </div>
        <button class="close-btn" @click="detectionPopup.show = false">×</button>
      </div>
      
      <div class="detection-popup-content">
        <!-- Left side: Image and Bounding Boxes -->
        <div class="detection-img-container">
          <img src="/Dashboard/images/uav_aerial_photo.png" class="detection-raw-img" />
          
          <!-- SVG Bounding Box Overlay -->
          <svg v-if="detectionPopup.state === 'detected'" class="detection-svg-overlay">
            <!-- Fire Box -->
            <g class="box-group fire-box">
              <rect x="52%" y="42%" width="22%" height="24%" class="box-rect rect-fire" />
              <text x="52%" y="39%" class="box-label label-fire">🔥 Fire: 98.6%</text>
            </g>
            <!-- Truck Box -->
            <g class="box-group truck-box">
              <rect x="42%" y="35%" width="40%" height="45%" class="box-rect rect-truck" />
              <text x="42%" y="32%" class="box-label label-truck">🚚 Truck: 99.2%</text>
            </g>
            <!-- Smoke Box -->
            <g class="box-group smoke-box">
              <rect x="48%" y="15%" width="32%" height="25%" class="box-rect rect-smoke" />
              <text x="48%" y="12%" class="box-label label-smoke">💨 Smoke: 94.5%</text>
            </g>
          </svg>
          
          <!-- Scanning/Radar sweep effect when detecting -->
          <div v-if="detectionPopup.state === 'detecting'" class="scanning-line"></div>
          <div v-if="detectionPopup.state === 'detecting'" class="scanning-overlay">AI 图像推理中...</div>
        </div>
        
        <!-- Right side: Detection Control Panel -->
        <div class="detection-control-panel">
          <div class="panel-section-title">检测控制区</div>
          
          <!-- State 1: Idle (Not started) -->
          <div v-if="detectionPopup.state === 'idle'" class="state-idle-wrap">
            <p class="desc-text">已接入当前边缘摄像机视频源，可对现场次生灾害起火及烟雾状况进行实时智能分析。</p>
            <button class="detect-btn pulse-button" @click="startDetection">
              <span class="btn-icon">⚡</span> 点击进行检测
            </button>
          </div>
          
          <!-- State 2: Detecting (Loading) -->
          <div v-if="detectionPopup.state === 'detecting'" class="state-detecting-wrap">
            <div class="spinner"></div>
            <p class="loading-text">正在运行推理：{{ detectionPopup.progress }}%</p>
            <div class="progress-bar-container">
              <div class="progress-bar-fill" :style="{ width: detectionPopup.progress + '%' }"></div>
            </div>
          </div>
          
          <!-- State 3: Detected (Results) -->
          <div v-if="detectionPopup.state === 'detected'" class="state-results-wrap">
            <div class="result-summary">
              <span class="status-indicator warning">存在险情</span>
              <span class="result-count">检出目标: 3</span>
            </div>
            
            <div class="detection-items-list">
              <div class="detect-item fire">
                <span class="item-icon">🔥</span>
                <span class="item-name">明火区域</span>
                <span class="item-conf">98.6%</span>
              </div>
              <div class="detect-item truck">
                <span class="item-icon">🚚</span>
                <span class="item-name">重型卡车</span>
                <span class="item-conf">99.2%</span>
              </div>
              <div class="detect-item smoke">
                <span class="item-icon">💨</span>
                <span class="item-name">扩散烟雾</span>
                <span class="item-conf">94.5%</span>
              </div>
            </div>
            
            <div class="report-box">
              <strong>研判结果:</strong> 监测到明火伴随大量烟雾，火焰呈扩大趋势，建议立刻通知消防队伍出动泡沫车进行扑灭。
            </div>
            
            <button class="reset-btn" @click="resetDetection">重新检测</button>
          </div>
        </div>
      </div>
      
      <div class="detection-popup-arrow"></div>
    </div>

    <!-- 仿真推演模块悬浮窗 (无人感知执行阶段 index === 8) -->
    <div 
      v-if="simulationPopup.show && props.activePhaseIndex === 8 && props.focusedPointId === 'accident_blue'" 
      class="simulation-popup-panel"
      :style="{ left: simulationPopup.x + 'px', top: simulationPopup.y + 'px' }"
    >
      <div class="simulation-popup-header">
        <div class="header-title-wrap">
          <span class="simulation-icon">📊</span>
          <span class="header-title">仿真推演</span>
        </div>
        <button class="close-btn" @click="simulationPopup.show = false">×</button>
      </div>
      
      <div class="simulation-popup-content">
        <p class="desc-text">感知数据采集完毕，已生成完整的事故现场推演模型与协同应急部署方案。</p>
        
        <button class="enter-sim-btn pulse-button" @click="enterSimulation">
          <span>进入仿真推演</span> <span class="arrow-icon">→</span>
        </button>
      </div>
      
      <div class="simulation-popup-arrow"></div>
    </div>

    <!-- 救援装备出动悬浮窗 -->
    <div 
      v-if="rescuePopup.show" 
      class="shelter-popup-panel"
      :style="{ left: rescuePopup.x + 'px', top: rescuePopup.y + 'px' }"
    >
      <div class="shelter-popup-header">
        <span>{{ rescuePopup.title }}</span>
        <button class="close-btn" @click="rescuePopup.show = false">×</button>
      </div>
      <table class="shelter-popup-table">
        <tbody>
          <tr>
            <td class="label">空域监测移动节点</td>
            <td class="value">{{ rescuePopup.uavCount }}</td>
          </tr>
          <tr>
            <td class="label">地面监测移动节点</td>
            <td class="value">{{ rescuePopup.carCount }}</td>
          </tr>
          <tr>
            <td class="label">出动状态</td>
            <td class="value">{{ rescuePopup.status }}</td>
          </tr>
        </tbody>
      </table>
      <div class="shelter-popup-arrow"></div>
    </div>

    <!-- 无人机现场侦察照片悬浮窗 -->
    <div 
      v-if="props.activePhaseIndex === 8" 
      class="uav-photo-panel"
    >
      <div class="uav-photo-header">
        <span class="uav-photo-icon">📸</span>
        <span class="uav-photo-title">多角度现场侦察拍图 ({{ capturedCount }}/4)</span>
        <span class="uav-status-tag" :class="{ 'status-done': capturedCount === 4 }">
          {{ capturedCount === 4 ? '拍摄完成' : '侦察拍摄中...' }}
        </span>
      </div>
      
      <div class="uav-photo-content">
        <!-- 主图区域 -->
        <div class="uav-main-photo-wrapper">
          <img 
            v-if="activePhotoIndex !== null"
            :src="currentPhotoSrc" 
            :class="['uav-photo-img', 'photo-angle-' + activePhotoIndex]" 
            alt="无人机侦察照片" 
          />
          <div v-else class="uav-photo-placeholder">
            <div class="radar-scan"></div>
            <span>等待无人机到达拍照位置...</span>
          </div>
          
          <div class="uav-photo-overlay" v-if="activePhotoIndex !== null">
            <div class="uav-photo-timestamp">REC ● {{ currentTimeStr }}</div>
            <div class="uav-photo-coords">{{ getAngleName(activePhotoIndex) }} ({{ props.phases[0]?.id.startsWith('t-') ? '113.1048°E, 30.3855°N' : '114.8933°E, 30.6317°N' }})</div>
          </div>
        </div>
        
        <!-- 4张缩略图列表 -->
        <div class="uav-thumbnails-row">
          <div 
            v-for="i in [0, 1, 2, 3]" 
            :key="i"
            class="uav-thumb-box"
            :class="{ 
              'is-captured': capturedPhotos[i], 
              'is-active': activePhotoIndex === i 
            }"
            @click="selectThumb(i)"
          >
            <div class="uav-thumb-inner" v-if="capturedPhotos[i]">
              <img 
                :src="currentPhotoSrc" 
                :class="['uav-thumb-img', 'photo-angle-' + i]" 
              />
              <div class="thumb-badge">角 {{ i+1 }}</div>
            </div>
            <div class="uav-thumb-lock" v-else>
              <span class="lock-icon">🔒</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 无人车 A 实时数据悬浮窗 (仅在有传感器数据时显示) -->
    <div class="ugv-data">

  <div class="ugv-line">
    <span class="ugv-label">温度</span>
    <span class="ugv-value">
      {{ props.isWsConnected ? ugvA.temp + ' ℃' : '--' }}
    </span>
  </div>


  <div class="ugv-line">
    <span class="ugv-label">湿度</span>
    <span class="ugv-value">
      {{ props.isWsConnected ? ugvA.hum + '%' : '--' }}
    </span>
  </div>


  <div class="ugv-line">
    <span class="ugv-label">烟雾</span>
    <span class="ugv-value warning">
      {{ props.isWsConnected ? ugvA.smoke + ' ug' : '--' }}
    </span>
  </div>


  <div class="ugv-line">
    <span class="ugv-label">TVOC</span>
    <span class="ugv-value">
      {{ props.isWsConnected ? ugvA.tvoc : '--' }}
    </span>
  </div>


  <div class="ugv-line">
    <span class="ugv-label">CO</span>
    <span class="ugv-value">
      {{ props.isWsConnected ? ugvA.co : '--' }}
    </span>
  </div>

</div>

    <!-- 无人车 B 实时数据悬浮窗 (仅在有传感器数据时显示) -->
    <div 
      v-if="props.activePhaseIndex >= 7 && ugvB.x !== -1000 && props.sensorData" 
      class="ugv-panel"
      :style="{ left: ugvB.x + 'px', top: ugvB.y + 'px' }"
    >
      <div class="ugv-header">
        <span class="ugv-title">无人车 B</span>
        <span class="ugv-status" :class="{ offline: !props.isWsConnected }">{{ props.isWsConnected ? '在线' : '离线' }}</span>
      </div>
      <div class="ugv-data">
        <div class="ugv-row">
          <div class="ugv-item"><span class="ugv-label">温度</span><span class="ugv-value">{{ props.isWsConnected ? ugvB.temp : '--' }}</span></div>
          <div class="ugv-item"><span class="ugv-label">湿度</span><span class="ugv-value">{{ props.isWsConnected ? ugvB.hum + '%' : '--' }}</span></div>
        </div>
        <div class="ugv-row">
          <div class="ugv-item full-width"><span class="ugv-label">烟雾</span><span class="ugv-value">{{ props.isWsConnected ? ugvB.smoke + ' ug' : '--' }}</span></div>
        </div>
        <div class="ugv-row">
          <div class="ugv-item"><span class="ugv-label">TVOC</span><span class="ugv-value">{{ props.isWsConnected ? ugvB.tvoc : '--' }}</span></div>
          <div class="ugv-item"><span class="ugv-label">CO</span><span class="ugv-value">{{ props.isWsConnected ? ugvB.co : '--' }}</span></div>
        </div>
      </div>
      <div class="ugv-footer" @click="goToSensorManage('node2')">点击查看详情 →</div>
    </div>



    <!-- 两客一危 湖北省交通数字孪生智控终端 (右侧高精对称伸缩侧边栏) -->
    <div class="lkyw-monitor-hud high-end-panel" :class="{ collapsed: isHudCollapsed }">
      <!-- 侧边伸缩拉手按键 (与左侧边栏高精对称的 toggle-btn) -->
      <button 
        class="toggle-btn toggle-btn-right-sidebar" 
        type="button" 
        :title="isHudCollapsed ? '点击展开智控终端' : '点击收起智控终端'"
        @click="isHudCollapsed = !isHudCollapsed"
      >
        {{ isHudCollapsed ? '◀' : '▶' }}
      </button>

      <!-- 头部标题与 LIVE 状态标识 (与左侧边栏 .sidebar-header 规格风格完全一致对齐) -->
      <div class="sidebar-header">
        <div class="header-main-title">
          <div class="header-title-block">
            <h2 class="sidebar-title">湖北省两客一危 · 智控终端</h2>
            <span class="sidebar-subtitle">TRAFFIC MONITORING CONTROL TERMINAL</span>
          </div>
          <span class="lkyw-hud-status-badge">● LIVE</span>
        </div>
      </div>

      <!-- 滚动主体内容区 (与左侧边栏 .sidebar-content 统一样式) -->
      <div class="hud-scroll-content">
        <!-- 视图模式切换 Tabs (全景总览 | 风险预警 | 卡口排行 | 智能推演) -->
        <div class="hud-mode-tabs">
          <button 
            class="mode-btn" 
            :class="{ active: activeHudTab === 'overview' }"
            @click="activeHudTab = 'overview'"
          >
            全景总览
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: activeHudTab === 'risk' }"
            @click="activeHudTab = 'risk'"
          >
            风险预警
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: activeHudTab === 'checkpoint' }"
            @click="activeHudTab = 'checkpoint'"
          >
            卡口排行
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: activeHudTab === 'ai' }"
            @click="activeHudTab = 'ai'"
          >
            智能推演
          </button>
        </div>

      <!-- 0. 全省 18 省界卡口 · 双向进出省总统计大盘舱 (全景模式展示) -->
      <div v-show="activeHudTab === 'overview'" class="cyber-border-flow-panel">
        <div class="border-panel-header">
          <span class="border-title">省界卡口 · 进出省双向流向</span>
          <span class="net-inflow-badge" :class="netInflowCount >= 0 ? 'pos' : 'neg'">
            净流入: {{ netInflowCount >= 0 ? '+' : '' }}{{ netInflowCount.toLocaleString() }} 辆
          </span>
        </div>
        <div class="border-flow-grid">
          <!-- 实时累计入省 (INBOUND) -->
          <div class="border-flow-card in">
            <div class="border-flow-top">
              <span class="flow-label">累计入省</span>
              <span class="flow-anim-arrow green">>>></span>
            </div>
            <div class="border-flow-val green">
              {{ totalInboundCount.toLocaleString() }} <span class="flow-unit">辆</span>
            </div>
          </div>
          <!-- 实时累计出省 (OUTBOUND) -->
          <div class="border-flow-card out">
            <div class="border-flow-top">
              <span class="flow-label">累计出省</span>
              <span class="flow-anim-arrow gold"><<<</span>
            </div>
            <div class="border-flow-val gold">
              {{ totalOutboundCount.toLocaleString() }} <span class="flow-unit">辆</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 1. 在途监控卡片列表 (全景总览模式展示) -->
      <div v-show="activeHudTab === 'overview'" class="lkyw-hud-grid">
        <!-- 危化品运输车 -->
        <div 
          class="lkyw-hud-card hazard" 
          :class="{ active: activeVehicleFilter === 'hazard' }" 
          @click="toggleVehicleFilter('hazard')"
        >
          <div class="lkyw-card-header">
            <span class="lkyw-label">危化品运输车</span>
            <span class="lkyw-subbadge red">高危 {{ hazardRatioPercent }}%</span>
          </div>
          <div class="lkyw-card-main">
            <div class="lkyw-val-block">
              <span class="lkyw-value red" :class="{ pulse: trafficStats.hazard.totalPulse }">
                {{ trafficStats.hazard.total.toLocaleString() }}
              </span>
              <span class="lkyw-unit">辆 在途</span>
            </div>
            <!-- 赛博强化：进出省对撞数据舱 -->
            <div class="cyber-flow-box-group">
              <div class="cyber-flow-box in" :class="{ flash: trafficStats.hazard.inPulse }">
                <span class="box-icon">入省</span>
                <span class="box-val green">{{ trafficStats.hazard.inbound.toLocaleString() }}</span>
              </div>
              <div class="cyber-flow-box out" :class="{ flash: trafficStats.hazard.outPulse }">
                <span class="box-icon">出省</span>
                <span class="box-val gold">{{ trafficStats.hazard.outbound.toLocaleString() }}</span>
              </div>
            </div>
          </div>
          <div class="lkyw-card-footer-tip">
            <span class="dot-indicator red"></span> 红色图例对应左图危化品点位 (演示标牌: {{ activeHazardDemoCount }} 辆)
          </div>
        </div>

        <!-- 省际/班线客车 -->
        <div 
          class="lkyw-hud-card passenger" 
          :class="{ active: activeVehicleFilter === 'passenger' }" 
          @click="toggleVehicleFilter('passenger')"
        >
          <div class="lkyw-card-header">
            <span class="lkyw-label">省际/班线客车</span>
            <span class="lkyw-subbadge green">占比 {{ passengerRatioPercent }}%</span>
          </div>
          <div class="lkyw-card-main">
            <div class="lkyw-val-block">
              <span class="lkyw-value green" :class="{ pulse: trafficStats.passenger.totalPulse }">
                {{ trafficStats.passenger.total.toLocaleString() }}
              </span>
              <span class="lkyw-unit">辆 在途</span>
            </div>
            <!-- 赛博强化：进出省对撞数据舱 -->
            <div class="cyber-flow-box-group">
              <div class="cyber-flow-box in" :class="{ flash: trafficStats.passenger.inPulse }">
                <span class="box-icon">入省</span>
                <span class="box-val green">{{ trafficStats.passenger.inbound.toLocaleString() }}</span>
              </div>
              <div class="cyber-flow-box out" :class="{ flash: trafficStats.passenger.outPulse }">
                <span class="box-icon">出省</span>
                <span class="box-val gold">{{ trafficStats.passenger.outbound.toLocaleString() }}</span>
              </div>
            </div>
          </div>
          <div class="lkyw-card-footer-tip">
            <span class="dot-indicator green"></span> 绿色图例对应班线客车点位 (演示标牌: {{ activePassengerDemoCount }} 辆)
          </div>
        </div>

        <!-- 旅游包车专线 -->
        <div 
          class="lkyw-hud-card tourist" 
          :class="{ active: activeVehicleFilter === 'tourist' }" 
          @click="toggleVehicleFilter('tourist')"
        >
          <div class="lkyw-card-header">
            <span class="lkyw-label">旅游包车专线</span>
            <span class="lkyw-subbadge blue">占比 {{ touristRatioPercent }}%</span>
          </div>
          <div class="lkyw-card-main">
            <div class="lkyw-val-block">
              <span class="lkyw-value blue" :class="{ pulse: trafficStats.tourist.totalPulse }">
                {{ trafficStats.tourist.total.toLocaleString() }}
              </span>
              <span class="lkyw-unit">辆 在途</span>
            </div>
            <!-- 赛博强化：进出省对撞数据舱 -->
            <div class="cyber-flow-box-group">
              <div class="cyber-flow-box in" :class="{ flash: trafficStats.tourist.inPulse }">
                <span class="box-icon">入省</span>
                <span class="box-val green">{{ trafficStats.tourist.inbound.toLocaleString() }}</span>
              </div>
              <div class="cyber-flow-box out" :class="{ flash: trafficStats.tourist.outPulse }">
                <span class="box-icon">出省</span>
                <span class="box-val gold">{{ trafficStats.tourist.outbound.toLocaleString() }}</span>
              </div>
            </div>
          </div>
          <div class="lkyw-card-footer-tip">
            <span class="dot-indicator blue"></span> 蓝色图例对应旅游包车点位 (演示标牌: {{ activeTouristDemoCount }} 辆)
          </div>
        </div>
      </div>

      <!-- 2. 极光 SVG 环形占比饼图 (全景总览模式保留) -->
      <div v-show="activeHudTab === 'overview'" class="hud-chart-section pie-section">
        <div class="chart-title-bar">
          <span class="chart-title">全省车辆类型占比饼图</span>
          <span class="chart-sub">LIVE 分布</span>
        </div>
        <div class="pie-chart-container">
          <div class="svg-pie-wrapper">
            <svg class="pie-svg" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="38" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="12" />
              <!-- 班线客车 (绿) -->
              <circle 
                cx="50" cy="50" r="38" fill="none" 
                stroke="#00E676" stroke-width="12"
                :stroke-dasharray="`${passengerStrokeLen} 238.76`"
                stroke-dashoffset="0"
                transform="rotate(-90 50 50)"
                class="pie-arc"
              />
              <!-- 旅游包车 (青) -->
              <circle 
                cx="50" cy="50" r="38" fill="none" 
                stroke="#00B0FF" stroke-width="12"
                :stroke-dasharray="`${touristStrokeLen} 238.76`"
                :stroke-dashoffset="`-${passengerStrokeLen}`"
                transform="rotate(-90 50 50)"
                class="pie-arc"
              />
              <!-- 危化品 (红) -->
              <circle 
                cx="50" cy="50" r="38" fill="none" 
                stroke="#FF2D55" stroke-width="12"
                :stroke-dasharray="`${hazardStrokeLen} 238.76`"
                :stroke-dashoffset="`-${Number(passengerStrokeLen) + Number(touristStrokeLen)}`"
                transform="rotate(-90 50 50)"
                class="pie-arc"
              />
            </svg>
            <div class="pie-center-info">
              <span class="pie-total-num">{{ totalActiveInTransit.toLocaleString() }}</span>
              <span class="pie-total-unit">全省在途</span>
            </div>
          </div>
          <div class="pie-legend">
            <div class="legend-row hazard" @click="toggleVehicleFilter('hazard')">
              <span class="legend-dot red"></span>
              <span class="legend-name">危化品运输</span>
              <span class="legend-val red">{{ hazardRatioPercent }}%</span>
            </div>
            <div class="legend-row passenger" @click="toggleVehicleFilter('passenger')">
              <span class="legend-dot green"></span>
              <span class="legend-name">省际班线客车</span>
              <span class="legend-val green">{{ passengerRatioPercent }}%</span>
            </div>
            <div class="legend-row tourist" @click="toggleVehicleFilter('tourist')">
              <span class="legend-dot blue"></span>
              <span class="legend-name">旅游包车专线</span>
              <span class="legend-val blue">{{ touristRatioPercent }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 4. 省界卡口实时抓拍与抓拍播报 (全景总览模式保留) -->
      <div v-show="activeHudTab === 'overview'" class="hud-chart-section log-section">
        <div class="chart-title-bar">
          <span class="chart-title">省界卡口实时抓拍流</span>
          <span class="chart-sub">LIVE 抓拍</span>
        </div>
        <div class="camera-log-list">
          <div 
            v-for="(log, idx) in latestCameraLogs" 
            :key="idx" 
            class="camera-log-item"
            :class="{ newest: idx === 0 }"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-loc">{{ log.location }}</span>
            <span class="log-plate">{{ log.plate }}</span>
            <span class="log-tag" :class="log.action === '入省' ? 'in' : 'out'">
              {{ log.action }}
            </span>
          </div>
        </div>
      </div>

      <!-- 3. 3D 重点干线流量柱状图 (全景总览模式保留) -->
      <div v-show="activeHudTab === 'overview'" class="hud-chart-section bar-section">
        <div class="chart-title-bar">
          <span class="chart-title">重点干线实时流量 Top5 柱状图</span>
          <span class="chart-sub">实时监视</span>
        </div>
        <div class="bar-chart-list">
          <div 
            v-for="(item, idx) in highwayFlowData" 
            :key="item.code" 
            class="bar-item"
          >
            <div class="bar-info-row">
              <span class="highway-name">
                <i class="rank-badge" :class="`rank-${idx+1}`">{{ idx + 1 }}</i> {{ item.name }}
              </span>
              <div class="bar-val-block">
                <span class="bar-count">{{ item.count }} 辆</span>
                <span class="hazard-tag" :class="{ alert: item.hazardRatio > 20 }">
                  高危 {{ item.hazardRatio }}%
                </span>
              </div>
            </div>
            <div class="bar-track">
              <div 
                class="bar-fill" 
                :style="{ width: `${(item.count / item.max) * 100}%` }"
                :class="{ high: item.hazardRatio > 20 }"
              >
                <div class="bar-glow-cap"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 5. ⚠️ 实时风险预警矩阵 Tab 面板 -->
      <div v-show="activeHudTab === 'risk'" class="hud-tab-pane risk-pane">
        <div class="risk-summary-grid">
          <div class="risk-summary-item red">
            <span class="risk-num">14</span>
            <span class="risk-lbl">高危车辆</span>
          </div>
          <div class="risk-summary-item gold">
            <span class="risk-num">8</span>
            <span class="risk-lbl">超速预警</span>
          </div>
          <div class="risk-summary-item orange">
            <span class="risk-num">6</span>
            <span class="risk-lbl">疲劳驾驶</span>
          </div>
          <div class="risk-summary-item blue">
            <span class="risk-num">2</span>
            <span class="risk-lbl">路线偏离</span>
          </div>
        </div>

        <div class="chart-title-bar" style="margin-top: 10px;">
          <span class="chart-title">实时高危车辆告警流</span>
          <span class="chart-sub">LIVE ALERT</span>
        </div>

        <div class="risk-vehicle-list">
          <div class="risk-card-item high-risk">
            <div class="risk-card-top">
              <span class="risk-plate">鄂A-H8921</span>
              <span class="risk-type-tag hazard">危化品 · 液化气</span>
              <span class="risk-level-badge red">高危告警</span>
            </div>
            <div class="risk-card-body">
              <div class="risk-reason">严重超速 (98km/h) · 罐体压力异常偏高</div>
              <div class="risk-meta-row">位置: 沪渝高速 G50 KM412 (仙桃段)</div>
              <div class="risk-meta-row">驾驶员: 李*强 (138****5921)</div>
            </div>
            <button class="risk-action-btn" @click="focusRiskVehicleOnMap(113.45, 30.36)">
              地图追踪定位
            </button>
          </div>

          <div class="risk-card-item high-risk">
            <div class="risk-card-top">
              <span class="risk-plate">鄂C-K5531</span>
              <span class="risk-type-tag hazard">危化品 · 汽油</span>
              <span class="risk-level-badge red">高危告警</span>
            </div>
            <div class="risk-card-body">
              <div class="risk-reason">连续驾驶超 4 小时 (疲劳驾驶警报)</div>
              <div class="risk-meta-row">位置: 福银高速 G70 KM285 (襄阳段)</div>
              <div class="risk-meta-row">驾驶员: 王*伟 (139****1842)</div>
            </div>
            <button class="risk-action-btn" @click="focusRiskVehicleOnMap(112.14, 32.04)">
              地图追踪定位
            </button>
          </div>

          <div class="risk-card-item mid-risk">
            <div class="risk-card-top">
              <span class="risk-plate">鄂B-H9021</span>
              <span class="risk-type-tag passenger">班线客车 · 49座</span>
              <span class="risk-level-badge orange">偏离线路</span>
            </div>
            <div class="risk-card-body">
              <div class="risk-reason">偏离核定运行线路 (超出 12 公里)</div>
              <div class="risk-meta-row">位置: 沪蓉高速 G42 KM198 (宜昌段)</div>
              <div class="risk-meta-row">驾驶员: 张*国 (137****3310)</div>
            </div>
            <button class="risk-action-btn" @click="focusRiskVehicleOnMap(111.28, 30.69)">
              地图追踪定位
            </button>
          </div>

          <div class="risk-card-item low-risk">
            <div class="risk-card-top">
              <span class="risk-plate">鄂F-T9918</span>
              <span class="risk-type-tag tourist">旅游包车</span>
              <span class="risk-level-badge gold">违规时段</span>
            </div>
            <div class="risk-card-body">
              <div class="risk-reason">违规夜间 2:00-5:00 仍处于行驶状态</div>
              <div class="risk-meta-row">位置: 汉十高速 S82 KM120 (十堰段)</div>
              <div class="risk-meta-row">驾驶员: 陈*龙 (136****9088)</div>
            </div>
            <button class="risk-action-btn" @click="focusRiskVehicleOnMap(110.79, 32.65)">
              地图追踪定位
            </button>
          </div>
        </div>
      </div>

      <!-- 6. 全省省界卡口通行流量排行 Tab 面板 -->
      <div v-show="activeHudTab === 'checkpoint'" class="hud-tab-pane checkpoint-pane">
        <div class="chart-title-bar">
          <span class="chart-title">湖北省界卡口实时流量 Top 5</span>
          <span class="chart-sub">CHECKPOINT RANK</span>
        </div>

        <div class="checkpoint-list">
          <div class="checkpoint-card">
            <div class="cp-rank-header">
              <span class="cp-rank gold">TOP 1</span>
              <span class="cp-name">临湘湖北省界卡口 (G4京港澳)</span>
              <span class="cp-status green">畅通</span>
            </div>
            <div class="cp-stats-row">
              <div class="cp-stat">
                <span class="cp-label">流量</span>
                <span class="cp-val green">1,842 <small>辆/h</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计入省</span>
                <span class="cp-val green">1,020 <small>辆</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计出省</span>
                <span class="cp-val gold">822 <small>辆</small></span>
              </div>
            </div>
          </div>

          <div class="checkpoint-card">
            <div class="cp-rank-header">
              <span class="cp-rank gold">TOP 2</span>
              <span class="cp-name">黄梅九江大桥卡口 (G70福银)</span>
              <span class="cp-status gold">繁忙</span>
            </div>
            <div class="cp-stats-row">
              <div class="cp-stat">
                <span class="cp-label">流量</span>
                <span class="cp-val gold">1,560 <small>辆/h</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计入省</span>
                <span class="cp-val green">840 <small>辆</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计出省</span>
                <span class="cp-val gold">720 <small>辆</small></span>
              </div>
            </div>
          </div>

          <div class="checkpoint-card">
            <div class="cp-rank-header">
              <span class="cp-rank silver">TOP 3</span>
              <span class="cp-name">荆州长江大桥卡口 (G55二广)</span>
              <span class="cp-status green">畅通</span>
            </div>
            <div class="cp-stats-row">
              <div class="cp-stat">
                <span class="cp-label">流量</span>
                <span class="cp-val green">1,320 <small>辆/h</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计入省</span>
                <span class="cp-val green">710 <small>辆</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计出省</span>
                <span class="cp-val gold">610 <small>辆</small></span>
              </div>
            </div>
          </div>

          <div class="checkpoint-card">
            <div class="cp-rank-header">
              <span class="cp-rank border">TOP 4</span>
              <span class="cp-name">京港澳赤壁卡口 (G4)</span>
              <span class="cp-status orange">缓行</span>
            </div>
            <div class="cp-stats-row">
              <div class="cp-stat">
                <span class="cp-label">流量</span>
                <span class="cp-val orange">1,180 <small>辆/h</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计入省</span>
                <span class="cp-val green">650 <small>辆</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计出省</span>
                <span class="cp-val gold">530 <small>辆</small></span>
              </div>
            </div>
          </div>

          <div class="checkpoint-card">
            <div class="cp-rank-header">
              <span class="cp-rank border">TOP 5</span>
              <span class="cp-name">鄂陕界关防卡口 (G7011)</span>
              <span class="cp-status green">畅通</span>
            </div>
            <div class="cp-stats-row">
              <div class="cp-stat">
                <span class="cp-label">流量</span>
                <span class="cp-val green">950 <small>辆/h</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计入省</span>
                <span class="cp-val green">510 <small>辆</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计出省</span>
                <span class="cp-val gold">440 <small>辆</small></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 7. 智能推演预测与应急预案 Tab 面板 -->
      <div v-show="activeHudTab === 'ai'" class="hud-tab-pane ai-pane">
        <div class="chart-title-bar">
          <span class="chart-title">AI 流量预测与风险推演</span>
          <span class="chart-sub">AI PREDICTION</span>
        </div>

        <div class="ai-metrics-panel">
          <div class="ai-metric-row">
            <span class="ai-lbl">未来 2 小时峰值预测:</span>
            <span class="ai-val highlight">4,200 辆/h (21:00 Peak)</span>
          </div>
          <div class="ai-metric-row">
            <span class="ai-lbl">危化品安全健康指数:</span>
            <span class="ai-val green">92.4 分 (安全可控)</span>
          </div>
          <div class="ai-metric-row">
            <span class="ai-lbl">恶劣天气风险预警:</span>
            <span class="ai-val gold">黄石段大雾 视距&lt;200m</span>
          </div>
        </div>

        <div class="chart-title-bar" style="margin-top: 10px;">
          <span class="chart-title">应急资源调度备勤状态</span>
          <span class="chart-sub">RESOURCES</span>
        </div>

        <div class="resource-grid">
          <div class="resource-card">
            <div class="res-info">
              <span class="res-title">巡逻警车</span>
              <span class="res-val green">18 辆在岗巡查</span>
            </div>
          </div>
          <div class="resource-card">
            <div class="res-info">
              <span class="res-title">救援无人机</span>
              <span class="res-val blue">6 架随时备勤</span>
            </div>
          </div>
          <div class="resource-card">
            <div class="res-info">
              <span class="res-title">危化处置组</span>
              <span class="res-val gold">3 组定点待命</span>
            </div>
          </div>
          <div class="resource-card">
            <div class="res-info">
              <span class="res-title">医疗救援车</span>
              <span class="res-val green">5 辆联动响应</span>
            </div>
          </div>
        </div>

        <button class="ai-dispatch-btn" @click="handleAutoDispatchTrigger">
          启动全省自动预警联动 (AUTO-DISPATCH)
        </button>
      </div>

      </div>

      <!-- 底部全局状态 -->
      <div class="lkyw-hud-footer">
        <span class="lkyw-footer-item" @click="toggleVehicleFilter('all')" style="cursor: pointer;">
          <i class="dot gold"></i> 显示全部 <strong>({{ totalActiveInTransit.toLocaleString() }} 辆)</strong>
        </span>
        <span class="lkyw-footer-item">
          <i class="dot green"></i> 全省干线: <strong>畅通在线</strong>
        </span>
      </div>
    </div>


  </div>
</template>

<script setup>
// 1. 顶端高度修正常量 (如果连线太高/太低，调这两个数字)
const JIZHAN_TOP_OFFSET = 18.0;  
const LIGHT_TOP_OFFSET = 7.5;    
// ==========================================
// 🌀 新增：多源数据动态传输流光材质
// ==========================================
// ==========================================
// 🌀 新增：多源数据动态传输流光材质 (完整正确版)
// ==========================================
class DynamicFlowMaterialProperty {
  constructor(options = {}) {
    this._definitionChanged = new Cesium.Event();
    this.color = options.color || Cesium.Color.CYAN;
    this.speed = options.speed || 3.0;    
    this.repeat = options.repeat || 10.0; 
  }
  get isConstant() { return false; }
  get definitionChanged() { return this._definitionChanged; }
  getType() { return 'DynamicFlowLine'; }
  
  // 👇 刚才仅仅只是修改了这里面的 result.color 这一行 👇
  getValue(time, result) {
    if (!Cesium.defined(result)) { result = {}; }
    result.color = Cesium.Color.clone(this.color, result.color); // 这是修复后不报错的写法
    result.speed = this.speed;
    result.repeat = this.repeat;
    return result;
  }
  // 👆 刚才仅仅只是修改了上面这一行 👆

  equals(other) { return this === other; }
}

// 注册底层的 GLSL 材质到 Cesium 引擎 (这部分也不用动)
Cesium.Material._materialCache.addMaterial('DynamicFlowLine', {
  fabric: {
    type: 'DynamicFlowLine',
    uniforms: {
      color: new Cesium.Color(0.0, 1.0, 1.0, 1.0),
      speed: 3.0,
      repeat: 10.0
    },
    source: `
      czm_material czm_getMaterial(czm_materialInput materialInput) {
        czm_material material = czm_getDefaultMaterial(materialInput);
        vec2 st = materialInput.st;
        float t = fract(czm_frameNumber * speed / 100.0 - st.s * repeat);
        material.diffuse = color.rgb;
        material.alpha = color.a * t * step(0.1, t);
        return material;
      }
    `
  }
}); 
// 2. 计算模型顶端世界坐标的工具函数
function getModelTopPosition(lng, lat, height, heading, pitch, roll, localZOffset) {
  const basePosition = Cesium.Cartesian3.fromDegrees(Number(lng), Number(lat), Number(height));
  const hpr = new Cesium.HeadingPitchRoll(
    Cesium.Math.toRadians(Number(heading || 0)),
    Cesium.Math.toRadians(Number(pitch || 0)),
    Cesium.Math.toRadians(Number(roll || 0))
  );
  const quaternion = Cesium.Transforms.headingPitchRollQuaternion(basePosition, hpr);
  const localOffset = new Cesium.Cartesian3(0, 0, Number(localZOffset));
  const matrix3 = Cesium.Matrix3.fromQuaternion(quaternion);
  const worldOffset = Cesium.Matrix3.multiplyByVector(matrix3, localOffset, new Cesium.Cartesian3());
  return Cesium.Cartesian3.add(basePosition, worldOffset, new Cesium.Cartesian3());
}
import { onBeforeUnmount, onMounted, ref, watch, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as Cesium from 'cesium'
import { getCollaborativeCommandCenterBaseUrl } from '../../config/subsystems'

const props = defineProps({
  phases: { type: Array, default: () => [] },
  activePhaseIndex: { type: Number, default: 0 },
  focusedPointId: { type: String, default: '' },
  sensorData: { type: Object, default: () => ({}) },
  isWsConnected: { type: Boolean, default: false }
})

const emit = defineEmits(['accident-picked', 'models-ready', 'update:activePhaseIndex'])

const router = useRouter()

const hoveredCityName = ref('')
const tooltipStyle = ref({
  left: '0px',
  top: '0px'
})

// 📹 全阶段相机视角微调工具 状态与定义
const cameraAdjust = reactive({
  show: false,
  scene: 'truck',
  phaseIndex: 1,
  range: 1440,
  pitch: -39,
  heading: -5,
  copiedMsg: ''
})

// 🚗 全省车流与巡航动态控制面板 状态
const trafficConfig = reactive({
  show: false,
  speedFactor: 1.0,     // 速度倍率 (0.1x ~ 10.0x)
  minDistance: 43000,   // 最短行驶路线段长度 (默认 43.0 km)
  vehicleCount: 23,     // 巡航车辆显示数量 (默认 23 辆)
  activeCategory: 'all' // 车辆类型筛选: 'all' | 'hazard' | 'passenger' | 'tourist'
})

// 🏷️ 市级行政区文字标注微调面板 状态
const labelConfig = reactive({
  show: false,
  fontSize: 31,      // 默认文字大小 31px
  outlineWidth: 3    // 默认描边厚度 3px
})

// 保存市级文字标注 Entity 引用
const cityLabelEntities = []

function updateCityLabelsFont() {
  if (!viewer) return
  const fontStr = `bold ${labelConfig.fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
  cityLabelEntities.forEach(entity => {
    if (entity && entity.label) {
      entity.label.font = new Cesium.ConstantProperty(fontStr)
      entity.label.outlineWidth = new Cesium.ConstantProperty(labelConfig.outlineWidth)
    }
  })
}

let cachedHubeiGeojson = null;

function reApplyTrafficRoutes() {
  if (!cachedHubeiGeojson) return;
  initTrafficVehiclesFromGeoJson(cachedHubeiGeojson);
  initLkywVehiclesFromGeoJson(cachedHubeiGeojson);
}

function resetTrafficConfig() {
  trafficConfig.speedFactor = 1.0;
  trafficConfig.minDistance = 43000;
  trafficConfig.vehicleCount = 23;
  trafficConfig.activeCategory = 'all';
  reApplyTrafficRoutes();
}

function setVehicleCategoryFilter(cat) {
  trafficConfig.activeCategory = cat;
  toggleVehicleFilter(cat);
}


const defaultPhaseCameraConfigs = {
  truck: {
    1: { range: 1440, pitch: -39, heading: -5 },
    2: { range: 630, pitch: -25, heading: 33 },
    3: { range: 630, pitch: -25, heading: 33 },
    4: { range: 630, pitch: -25, heading: 33 },
    5: { range: 630, pitch: -25, heading: 33 },
    6: { range: 1600, pitch: -45, heading: 0 },
    7: { range: 1400, pitch: -35, heading: 15 },
    8: { range: 1200, pitch: -30, heading: -10 },
    9: { range: 1800, pitch: -45, heading: 0 },
    10: { range: 2200, pitch: -50, heading: 0 }
  },
  tanker: {
    1: { range: 2500, pitch: -45, heading: 0 },
    2: { range: 1800, pitch: -35, heading: -15 },
    3: { range: 1440, pitch: -39, heading: -5 },
    4: { range: 1200, pitch: -30, heading: 10 },
    5: { range: 1500, pitch: -40, heading: -20 },
    6: { range: 1600, pitch: -45, heading: 0 },
    7: { range: 1400, pitch: -35, heading: 15 },
    8: { range: 1200, pitch: -30, heading: -10 },
    9: { range: 1800, pitch: -45, heading: 0 },
    10: { range: 2200, pitch: -50, heading: 0 }
  }
}

const truckPhases = [
  { shortLabel: '仿真开始', title: '仿真推演开始' },
  { shortLabel: '正常行驶', title: '车辆正常行驶阶段' },
  { shortLabel: '事故发生', title: '货车追尾事故瞬间' },
  { shortLabel: '次生灾害（烟雾）', title: '事故现场产生大量烟雾' },
  { shortLabel: '次生灾害（起火）', title: '事故车辆开始起火' },
  { shortLabel: '次生灾害（大火）', title: '火势进一步扩大蔓延' },
  { shortLabel: '无人装备出动', title: '无人装备协同出动' },
  { shortLabel: '无人感知部署', title: '无人感知节点部署' },
  { shortLabel: '无人感知执行', title: '无人感知任务执行' },
  { shortLabel: '救援装备出动', title: '专业救援装备协同出动' }
]

const tankerPhases = [
  { shortLabel: '仿真开始', title: '油罐车仿真推演开始' },
  { shortLabel: '正常行驶', title: '油罐车正常行驶阶段' },
  { shortLabel: '事故发生（侧翻）', title: '油罐车发生侧翻事故' },
  { shortLabel: '次生灾害（泄露）', title: '罐体受损开始发生化学品泄露' },
  { shortLabel: '次生灾害（弥漫）', title: '泄露液体开始向四周大面积弥漫' },
  { shortLabel: '次生灾害（扩散）', title: '挥发气体随风向周边区域扩散' },
  { shortLabel: '无人装备出动', title: '无人装备协同出动' },
  { shortLabel: '无人感知部署', title: '无人感知节点部署' },
  { shortLabel: '无人感知执行', title: '无人感知任务执行' },
  { shortLabel: '救援装备出动', title: '专业救援装备协同出动' }
]

const currentPhaseOptions = computed(() => {
  if (cameraAdjust.scene === 'tanker') {
    return tankerPhases
  }
  return truckPhases
})

function applyCameraAdjust() {
  if (!viewer) return
  let lng = 113.104833, lat = 30.385469
  if (cameraAdjust.scene === 'tanker' || props.focusedPointId === 'accident_red') {
    lng = 114.893327
    lat = 30.631683
  }
  const center = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
  const h = Cesium.Math.toRadians(Number(cameraAdjust.heading))
  const p = Cesium.Math.toRadians(Number(cameraAdjust.pitch))
  const r = Number(cameraAdjust.range)
  
  try {
    viewer.camera.lookAt(center, new Cesium.HeadingPitchRange(h, p, r))
  } catch (e) {
    console.warn('Camera lookAt error:', e)
  }
}

function switchCameraScene(sceneType) {
  cameraAdjust.scene = sceneType
  if (typeof currentScene !== 'undefined' && currentScene.value !== undefined) {
    currentScene.value = sceneType
  }
  const targetPointId = sceneType === 'tanker' ? 'accident_red' : 'accident_blue'
  emit('accident-picked', targetPointId)
  onPhaseSelectChange()
}

function onPhaseSelectChange() {
  const pIdx = cameraAdjust.phaseIndex
  const scene = cameraAdjust.scene
  const cfg = (defaultPhaseCameraConfigs[scene] && defaultPhaseCameraConfigs[scene][pIdx]) || { range: 1440, pitch: -39, heading: -5 }
  cameraAdjust.range = cfg.range
  cameraAdjust.pitch = cfg.pitch
  cameraAdjust.heading = cfg.heading
  applyCameraAdjust()
  emit('update:activePhaseIndex', pIdx - 1)
}

function resetCurrentPhaseDefaultView() {
  onPhaseSelectChange()
}

function copyCurrentCameraParams() {
  const text = `// 阶段 ${cameraAdjust.phaseIndex} 视角配置\n{ range: ${cameraAdjust.range}, pitch: ${cameraAdjust.pitch}, heading: ${cameraAdjust.heading} }`
  navigator.clipboard.writeText(text).then(() => {
    cameraAdjust.copiedMsg = '📋 已复制当前视角配置参数至剪贴板！'
    setTimeout(() => {
      cameraAdjust.copiedMsg = ''
    }, 2000)
  }).catch(() => {
    cameraAdjust.copiedMsg = '复制失败，请手动记录'
    setTimeout(() => {
      cameraAdjust.copiedMsg = ''
    }, 2000)
  })
}


// 现场灯光微调相关状态与控制
const isLightPanelExpanded = ref(false)

const coordCopiedMessage = ref('')

const activeLightIndex = ref(0)
const lights = reactive([
  { id: 'light1', name: '灯光 1', show: true, lng: 113.105001, lat: 30.385353, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light2', name: '灯光 2', show: true, lng: 113.105781, lat: 30.385317, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light3', name: '灯光 3', show: true, lng: 113.104482, lat: 30.385632, height: 8.5, scale: 0.003, heading: 198, pitch: 0, roll: 0 },
  { id: 'light4', name: '灯光 4', show: true, lng: 114.891139, lat: 30.630711, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light5', name: '灯光 5', show: true, lng: 114.892429, lat: 30.631096, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light6', name: '灯光 6 (原3D自带)', show: true, lng: 114.893327, lat: 30.631683, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { 
 id: 'light7', 
 name: '灯光 7', 
 show: true,
 lng: 113.106713,
 lat: 30.385096,
 height: 8.5,
 scale: 0.003,
 heading: 201,
 pitch: 0,
 roll: 0
},

{ 
 id: 'light8', 
 name: '灯光 8', 
 show: true,
 lng: 113.106053,
 lat: 30.385035,
 height: 8.5,
 scale: 0.003,
 heading: 201,
 pitch: 0,
 roll: 0
},

{ 
 id: 'light9', 
 name: '灯光 9', 
 show: true,
 lng: 113.106993,
 lat: 30.384839,
 height: 8.5,
 scale: 0.003,
 heading: 201,
 pitch: 0,
 roll: 0
},

{ 
 id: 'light10', 
 name: '灯光 10', 
 show: true,
 lng: 113.104025,
 lat: 30.385567,
 height: 8.5,
 scale: 0.003,
 heading: 201,
 pitch: 0,
 roll: 0
},
{ id: 'light11', name: '灯光 11', show: true, lng: 113.103713, lat: 30.385879, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light12', name: '灯光 12', show: true, lng: 113.102937, lat: 30.385845, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light13', name: '灯光 13', show: true, lng: 113.102025, lat: 30.386324, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light14', name: '灯光 14', show: true, lng: 113.100805, lat: 30.386452, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light15', name: '灯光 15', show: true, lng: 113.100141, lat:30.386877, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light16', name: '灯光 16', show: true, lng:113.09881, lat: 30.387111, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light17', name: '灯光 17', show: true, lng: 113.0977, lat:30.387665, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light18', name: '灯光 18', show: true, lng:113.096165, lat: 30.38803, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
 { id: 'light19', name: '灯光 19', show: true, lng: 113.108476, lat: 30.384758, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light20', name: '灯光 20', show: true, lng:113.10978, lat:30.384221, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light21', name: '灯光 21', show: true, lng: 113.110784, lat: 30.384221, height: 8.5, scale: 0.003, heading: 198, pitch: 0, roll: 0 },
])

const lightAdjust = reactive({
  show: true,
  lng: 113.105001,
  lat: 30.385353,
  height: 8.5,
  scale: 0.003,
  heading: 16,
  pitch: 0,
  roll: 0
})

// 当切换当前编辑的灯光时，将对应的参数回填到 lightAdjust
watch(activeLightIndex, (newIdx) => {
  if (newIdx === 5) {
    // light6 (索引 5) 转变成对原 3D 事故模型 (tankerAdjust) 的位置与姿态控制
    lightAdjust.show = true
    lightAdjust.lng = tankerAdjust.lng
    lightAdjust.lat = tankerAdjust.lat
    lightAdjust.height = tankerAdjust.height
    lightAdjust.scale = tankerAdjust.scale
    lightAdjust.heading = tankerAdjust.heading
    lightAdjust.pitch = 0
    lightAdjust.roll = 0
  } else {
    const currentLight = lights[newIdx]
    lightAdjust.show = currentLight.show
    lightAdjust.lng = currentLight.lng
    lightAdjust.lat = currentLight.lat
    lightAdjust.height = currentLight.height
    lightAdjust.scale = currentLight.scale
    lightAdjust.heading = currentLight.heading
    lightAdjust.pitch = currentLight.pitch
    lightAdjust.roll = currentLight.roll
  }
}, { immediate: true })

// 当微调面板修改了 lightAdjust 时，同步回对应目标
watch(lightAdjust, (newVals) => {
  if (activeLightIndex.value === 5) {
    // 同步修改到原 3D 事故模型 tankerAdjust，从而直接控制该模型在地图上的经纬度、高度、朝向与比例
    tankerAdjust.lng = newVals.lng
    tankerAdjust.lat = newVals.lat
    tankerAdjust.height = newVals.height
    tankerAdjust.scale = newVals.scale
    tankerAdjust.heading = newVals.heading
    // 同时同步记录回 lights[5]
    const currentLight = lights[5]
    currentLight.lng = newVals.lng
    currentLight.lat = newVals.lat
    currentLight.height = newVals.height
    currentLight.scale = newVals.scale
    currentLight.heading = newVals.heading
  } else {
    const currentLight = lights[activeLightIndex.value]
    currentLight.show = newVals.show
    currentLight.lng = newVals.lng
    currentLight.lat = newVals.lat
    currentLight.height = newVals.height
    currentLight.scale = newVals.scale
    currentLight.heading = newVals.heading
    currentLight.pitch = newVals.pitch
    currentLight.roll = newVals.roll
  }
}, { deep: true })

// 📡 5G 通信基站 (jizhan.glb) 模型参数 (接入货车追尾现场)
const isJizhanPanelExpanded = ref(false)
const jizhanCopiedMessage = ref('')

const jizhanAdjust = reactive({
  show: true,
  lng: 113.105385,
  lat: 30.385795,
  height: -1.9,
  scale: 0.01,
  heading: 99,
  pitch: 0,
  roll: 0
})

function toggleJizhanPanel() {
  isJizhanPanelExpanded.value = !isJizhanPanelExpanded.value
}

function snapJizhanToTruck() {
  jizhanAdjust.lng = 113.105385;
  jizhanAdjust.lat = 30.385795;
  jizhanAdjust.height = -1.9;
  jizhanAdjust.scale = 0.01;
  jizhanAdjust.heading = 99;
  jizhanAdjust.pitch = 0;
  jizhanAdjust.roll = 0;
}

function copyJizhanCoords() {
  const text = `lng: ${jizhanAdjust.lng.toFixed(6)}, lat: ${jizhanAdjust.lat.toFixed(6)}, height: ${jizhanAdjust.height}, scale: ${jizhanAdjust.scale}, heading: ${jizhanAdjust.heading}, pitch: ${jizhanAdjust.pitch}, roll: ${jizhanAdjust.roll}`;
  navigator.clipboard.writeText(text).then(() => {
    jizhanCopiedMessage.value = '基站配置参数已成功复制到剪贴板！';
    setTimeout(() => {
      jizhanCopiedMessage.value = '';
    }, 2000);
  }).catch(err => {
    console.error('复制失败:', err);
    jizhanCopiedMessage.value = '复制失败，请手动记录';
    setTimeout(() => {
      jizhanCopiedMessage.value = '';
    }, 2000);
  });
}

function toggleLightPanel() {
  isLightPanelExpanded.value = !isLightPanelExpanded.value
}

function snapLightTo(sceneType) {
  if (sceneType === 'truck') {
    lightAdjust.lng = 113.105001;
    lightAdjust.lat = 30.385353;
    lightAdjust.height = 8.5;
    lightAdjust.heading = 16;
  } else if (sceneType === 'tanker') {
    lightAdjust.lng = 114.893327;
    lightAdjust.lat = 30.631683;
    lightAdjust.height = 8.5;
  }
}

function copyLightCoords() {
  const text = `lng: ${lightAdjust.lng.toFixed(6)}, lat: ${lightAdjust.lat.toFixed(6)}, height: ${lightAdjust.height}, scale: ${lightAdjust.scale}, heading: ${lightAdjust.heading}, pitch: ${lightAdjust.pitch}, roll: ${lightAdjust.roll}`;
  navigator.clipboard.writeText(text).then(() => {
    coordCopiedMessage.value = `${lights[activeLightIndex.value].id} 配置已成功复制到剪贴板！`;
    setTimeout(() => {
      coordCopiedMessage.value = '';
    }, 2000);
  }).catch(err => {
    console.error('复制失败:', err);
    coordCopiedMessage.value = '复制失败，请手动记录';
    setTimeout(() => {
      coordCopiedMessage.value = '';
    }, 2000);
  });
}

function copyAllLightsCoords() {
  const listText = lights.map(l => 
    `{ id: '${l.id}', lng: ${l.lng.toFixed(6)}, lat: ${l.lat.toFixed(6)}, height: ${l.height}, scale: ${l.scale}, heading: ${l.heading}, pitch: ${l.pitch}, roll: ${l.roll} }`
  ).join(',\n');
  navigator.clipboard.writeText(listText).then(() => {
    coordCopiedMessage.value = '所有 6 个灯光配置已成功复制到剪贴板！';
    setTimeout(() => {
      coordCopiedMessage.value = '';
    }, 2500);
  }).catch(err => {
    console.error('复制失败:', err);
    coordCopiedMessage.value = '复制失败';
    setTimeout(() => {
      coordCopiedMessage.value = '';
    }, 2000);
  });
}

// 自动检测场景切换并联动灯光坐标
watch(() => props.focusedPointId, (newId) => {
  if (newId === 'accident_red') {
    snapLightTo('tanker');
  } else if (newId === 'accident_blue') {
    snapLightTo('truck');
  }
}, { immediate: true });

function goToSensorManage(target = '') {
  const query = target ? { target } : {}
  router.push({ path: '/sensor-manage', query })
}

// 当前选中的场景
const currentScene = ref('truck')

// 无人机视频/图像时间戳更新
const currentTimeStr = ref('')
const updateTime = () => {
  const now = new Date()
  const pad = (num) => String(num).padStart(2, '0')
  currentTimeStr.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}
let timeInterval = null

// 无人机多角度照片拍摄状态
const capturedPhotos = ref([false, false, false, false])
const activePhotoIndex = ref(null)

const capturedCount = computed(() => {
  return capturedPhotos.value.filter(Boolean).length
})

const getAngleName = (index) => {
  const names = ['东北角视角', '东南角视角', '西南角视角', '西北角视角']
  return names[index] || ''
}

const selectThumb = (index) => {
  if (capturedPhotos.value[index]) {
    activePhotoIndex.value = index
  }
}

const currentPhotoSrc = computed(() => {
  const isTruck = props.phases[0]?.id.startsWith('t-')
  return isTruck ? '/Dashboard/images/uav_aerial_photo.png' : '/Dashboard/images/tanker_aerial_photo.png'
})

const flyingPhotos = ref([]);

function triggerPhotoAnimation(index, cartesianPos) {
  if (!viewer) return;
  const windowPos = Cesium.SceneTransforms.worldToWindowCoordinates(viewer.scene, cartesianPos);
  if (!windowPos) return;

  const photoId = Date.now() + '-' + index;
  const photo = reactive({
    id: photoId,
    index: index,
    src: currentPhotoSrc.value,
    x: windowPos.x - 20,
    y: windowPos.y - 15,
    width: 40,
    height: 30,
    opacity: 1
  });
  flyingPhotos.value.push(photo);

  setTimeout(() => {
    const thumbs = document.querySelectorAll('.sidebar-thumb-box, .uav-thumb-box');
    const targetEl = thumbs[index];
    if (targetEl) {
      const rect = targetEl.getBoundingClientRect();
      photo.x = rect.left;
      photo.y = rect.top;
      photo.width = rect.width;
      photo.height = rect.height;
    } else {
      photo.x = window.innerWidth - 100;
      photo.y = window.innerHeight / 2;
      photo.width = 60;
      photo.height = 40;
    }
  }, 50);

  setTimeout(() => {
    const idx = flyingPhotos.value.findIndex(p => p.id === photoId);
    if (idx !== -1) {
      flyingPhotos.value.splice(idx, 1);
    }
  }, 900);
}



// 救援装备出动状态与坐标 (放在无人机/车出动起点附近)
const rescueCoords = reactive({ lng: 113.10725, lat: 30.38491, height: 24.0 });

const rescuePopup = reactive({
  show: false,
  title: '救援装备出动',
  uavCount: '3 架',
  carCount: '6 辆',
  status: '已出发',
  x: 0,
  y: 0
});

// 城市高亮上浮高度 (仙桃与黄冈)
const xiantaoHeight = ref(0);
const huanggangHeight = ref(0);

let rescueMarkerEntity = null;

let sharedTruckRescueCarPosition = null;
let sharedTankerRescueCarPosition = null;

// 无人车实时数据及浮窗位置
const ugvA = reactive({
  temp: 29.88, hum: 58.02, smoke: 25284, tvoc: 0.357, co: 2.8,
  x: -1000, y: -1000
});
const ugvB = reactive({
  temp: 27.07, hum: 43.47, smoke: 25292, tvoc: 0.588, co: 3.3,
  x: -1000, y: -1000
});

// 计算属性：根据当前场景返回对应的参数对象
const currentUavAdjust = computed(() => {
  return currentScene.value === 'truck' ? uavAdjust : tankerUavAdjust
})

const currentTruckAdjust = computed(() => {
  return currentScene.value === 'truck' ? truckAdjust : tankerAdjust
})

const currentPointAdjust = computed(() => {
  return currentScene.value === 'truck' ? truckPointAdjust : tankerPointAdjust
})

const currentRescueCarAdjust = computed(() => {
  return currentScene.value === 'truck' ? rescueCarAdjust : tankerRescueCarAdjust
})



// 货车事故分段模型配置 (去重，仅保留唯一物理模型)
const truckModelConfigs = [
  { id: 'model_normal', uri: '/Dashboard/models/Normal_Drive.glb', label: '正常行驶' },
  { id: 'model_accident', uri: '/Dashboard/models/Accident_Occur1.glb', label: '事故阶段' }
]

// 油罐车事故分段模型配置
const tankerModelConfigs = [
  { id: 'tanker_normal', uri: '/Dashboard/models/Normal_Drive_Tanker.glb', label: '正常行驶' },
  { id: 'tanker_accident', uri: '/Dashboard/models/Side_roll_Tanker.glb', label: '事故阶段' }
]

// 阶段索引到模型ID的映射
const phaseToModelMap = {
  1: 'model_normal',
  2: 'model_accident',
  3: 'model_accident',
  4: 'model_accident',
  5: 'model_accident',
  6: 'model_accident',
  7: 'model_accident',
  8: 'model_accident',
  9: 'model_accident',
  10: 'model_accident'
}

// 油罐车阶段索引到模型ID的映射
const tankerPhaseToModelMap = {
  1: 'tanker_normal',
  2: 'tanker_accident',
  3: 'tanker_accident',
  4: 'tanker_accident',
  5: 'tanker_accident',
  6: 'tanker_accident',
  7: 'tanker_accident',
  8: 'tanker_accident',
  9: 'tanker_accident',
  10: 'tanker_accident'
}

let currentActiveModelId = null 
let currentActiveTankerModelId = null
let lastPhaseIndex = -1
let lastTankerPhaseIndex = -1

const truckAdjust = reactive({
  scale: 0.82,
  heading: 17,
  lng: 113.104833,
  lat: 30.385469,
  height: -1.2 // 手动微调高度以贴合地面
})

const truckPointAdjust = reactive({
  lng: 113.104833,
  lat: 30.385469
})

const tankerAdjust = reactive({
  scale: 0.26,
  heading: -29,
  lng: 114.893327,
  lat: 30.631683,
  height: -1.2 // 手动微调高度以贴合地面
})

const tankerPointAdjust = reactive({
  lng: 114.89209,
  lat: 30.63101
})

// 无人机配置
// 无人机配置 (包含主无人机与2架僚机，支持编队飞行与120度等距环绕)
const uavModelConfigs = [
  // 1号机 (主) - 位于编队正前方
  { id: 'uav_model', uri: '/Dashboard/models/drone_all7.glb', label: '1号出动无人机', lonOffset: 0, latOffset: 0, angleOffset: 0 },
  { id: 'uav_model_move', uri: '/Dashboard/models/drone_all7.glb', label: '1号感知部署无人机', lonOffset: 0, latOffset: 0, angleOffset: 0 },
  // 2号机 (左翼僚机) - 位于左后方，环绕时相差 120°
  { id: 'uav_model_2', uri: '/Dashboard/models/drone_all7.glb', label: '2号出动无人机', lonOffset: -0.00005, latOffset: -0.00005, angleOffset: Math.PI * 2 / 3 },
  { id: 'uav_model_move_2', uri: '/Dashboard/models/drone_all7.glb', label: '2号感知部署无人机', lonOffset: -0.00005, latOffset: -0.00005, angleOffset: Math.PI * 2 / 3 },
  // 3号机 (右翼僚机) - 位于右后方，环绕时相差 240°
  { id: 'uav_model_3', uri: '/Dashboard/models/drone_all7.glb', label: '3号出动无人机', lonOffset: 0.00005, latOffset: -0.00005, angleOffset: Math.PI * 4 / 3 },
  { id: 'uav_model_move_3', uri: '/Dashboard/models/drone_all7.glb', label: '3号感知部署无人机', lonOffset: 0.00005, latOffset: -0.00005, angleOffset: Math.PI * 4 / 3 }
]

// 救援车配置
// 救援车配置（共3个模型，每个模型2辆车，合计6辆车视觉效果。采用“品”字形扇形停靠）
const rescueCarModelConfigs = [
  { id: 'rescue_car_model_1', uri: '/Dashboard/models/recure%20car.glb', label: '1号编队(中)', stopFactor: 0.78, lonOffset: 0, latOffset: 0 },
  // 左翼车道：稍微靠后停下，向左偏移
  { id: 'rescue_car_model_2', uri: '/Dashboard/models/recure%20car.glb', label: '2号编队(左)', stopFactor: 0.74, lonOffset: -0.00006, latOffset: -0.00004 },
  // 右翼车道：稍微靠后停下，向右偏移
  { id: 'rescue_car_model_3', uri: '/Dashboard/models/recure%20car.glb', label: '3号编队(右)', stopFactor: 0.74, lonOffset: 0.00006, latOffset: 0.00004 }
]

// 油罐车场景救援车配置（同理，3个编队扇形包围）
const tankerRescueCarModelConfigs = [
  { id: 'tanker_rescue_car_model_1', uri: '/Dashboard/models/recure%20car_2.glb', label: '1号油罐救援编队(中)', stopFactor: 0.40, lonOffset: 0, latOffset: 0 },
  { id: 'tanker_rescue_car_model_2', uri: '/Dashboard/models/recure%20car_2.glb', label: '2号油罐救援编队(左)', stopFactor: 0.36, lonOffset: -0.00006, latOffset: -0.00004 },
  { id: 'tanker_rescue_car_model_3', uri: '/Dashboard/models/recure%20car_2.glb', label: '3号油罐救援编队(右)', stopFactor: 0.36, lonOffset: 0.00006, latOffset: 0.00004 }
]
// 无人机位置调整（起始点：仙桃市毛嘴镇消防站）
const uavAdjust = reactive({
  scale: 6,
  heading: 18,
  lng: 113.418173,
  lat: 30.321919,
  height: 18.5
});

const rescueCarAdjust = reactive({
  scale: 250.7,
  heading: 195,
  lng: 113.1073,
  lat: 30.3849,
  height: -1.5
});

let uavEntities = []
let rescueCarEntities = []
let phase7StartTime = 0
let uavOrbitStartTime = 0
let diffusionStartTime = 0
let lastUavPhaseIndex = -1

// 油罐车场景的无人机和救援车配置（独立控制）
const tankerUavAdjust = reactive({
  scale: 6,
  heading: 34,
  lng: 114.89539,
  lat: 30.63129,
  height: 11.5
});

const tankerRescueCarAdjust = reactive({
  scale: 250,
  heading: 155,
  lng: 114.89417,
  lat: 30.63182,
  height: 6.5
});

const TANKER_STOP_FACTOR = 0.4;

// 油罐车场景的无人机和救援车实体数组
let tankerUavEntities = []
let tankerRescueCarEntities = []
let tankerPhase7StartTime = 0
let tankerUavOrbitStartTime = 0
let lastTankerUavPhaseIndex = -1

const containerRef = ref(null)
const loading = ref(true)
const errorMessage = ref('')

let viewer = null
let spinCallback = null
let lastSpinAt = 0
// 分离相机航向角
let truckOrbitHeading = Cesium.Math.toRadians(8)
let tankerOrbitHeading = Cesium.Math.toRadians(8)
let focusAreaEntity = null
let popupEntity = null 
let connectionLineEntity = null

// 事故现场三级视角状态
const accidentViewLevel = ref('far') // 'far', 'medium', 'close'
const accidentDetailPopup = reactive({
  show: false,
  x: 0,
  y: 0,
  title: '',
  img: '',
  pointId: ''
})

// 实时检测模块弹窗状态
const detectionPopup = reactive({
  show: false,
  state: 'idle', // 'idle' | 'detecting' | 'detected'
  progress: 0,
  x: 0,
  y: 0
})

let detectionTimer = null
function startDetection() {
  if (detectionTimer) clearInterval(detectionTimer)
  detectionPopup.state = 'detecting'
  detectionPopup.progress = 0
  
  detectionTimer = setInterval(() => {
    detectionPopup.progress += 5
    if (detectionPopup.progress >= 100) {
      clearInterval(detectionTimer)
      detectionTimer = null
      detectionPopup.state = 'detected'
    }
  }, 75)
}

function resetDetection() {
  if (detectionTimer) {
    clearInterval(detectionTimer)
    detectionTimer = null
  }
  detectionPopup.state = 'idle'
  detectionPopup.progress = 0
}

// 仿真推演悬浮窗状态
const simulationPopup = reactive({
  show: false,
  x: 0,
  y: 0
})

function enterSimulation() {
  router.push('/simulation?city=xiantao')
}

// 粒子系统实例
let isFlying = false
let truckEntities = [] 
let tankerEntities = [] 
let animationCheckTimer = null
const modelsReadyStatus = reactive({});
let lastEmitTime = 0;
const primitiveCache = new Map(); // 缓存找到的 primitive，避免重复递归搜索
let readyCheckFrameCounter = 0; // 帧计数器，用于节流

let currentMissionDataSource = null;

const loadMission = async () => {
  if (!viewer) return;
  try {
    const baseUrl = getCollaborativeCommandCenterBaseUrl();
    if (currentMissionDataSource) {
      viewer.dataSources.remove(currentMissionDataSource);
      currentMissionDataSource = null;
    }
    
    const endpoint = currentScene.value === 'truck' ? 'crash' : 'leak';
    // 触发并等待生成，确保 CZML 已经写入完毕
    try {
      await fetch(`${baseUrl}/api/run_3d_strategy?end_point=${endpoint}`);
    } catch (e) {
      console.warn('[Cesium] 触发策略生成失败，将尝试加载已有 CZML:', e);
    }
    
    // 如果在请求 API 期间，用户已经切回到前面（例如回到首页），则终止后续加载
    if (props.activePhaseIndex < 6) {
      return;
    }
    
    // 加载最新的 czml
    const czmlUrl = `${baseUrl}/mission.czml?t=${Date.now()}`;
    const dataSource = await Cesium.CzmlDataSource.load(czmlUrl);
    
    // 再次双重校验，防止加载文件期间用户切换了阶段
    if (props.activePhaseIndex < 6) {
      return;
    }

    currentMissionDataSource = dataSource;
    viewer.dataSources.add(dataSource);

    // 根据用户要求，加快无人机无人车行走的时间
    viewer.clock.multiplier = 20.0;
    viewer.clock.shouldAnimate = true;
  } catch (error) {
    console.error('加载三维轨迹 CZML 失败:', error);
  }
}

// 递归查找原始模型对象
function findModelPrimitive(collection, entity) {
  if (!collection || typeof collection.get !== 'function') return null
  const len = collection.length
  for (let i = 0; i < len; i++) {
    const p = collection.get(i)
    if (!p) continue
    
    // 匹配逻辑：匹配 entity 对象、ID 字符串或 .id 属性
    const pId = p.id
    // 检查 pId 是否是 Entity 对象，或者 pId 字符串匹配
    const isMatch = (pId === entity) || 
                    (pId && pId.id === entity.id) ||
                    (pId === entity.id) ||
                    (pId && pId._id === entity.id)
                    
    if (isMatch) {
      // 如果是模型或者包含 model 属性的对象
      if (p.ready !== undefined || p.readyPromise !== undefined || p.model) {
        return p
      }
    }
    
    // 如果是集合，递归查找
    if (typeof p.get === 'function' && typeof p.length === 'number') {
      const found = findModelPrimitive(p, entity)
      if (found) return found
    }
  }
  return null
}

function updateModelsReadyStatus() {
  if (!viewer) return;
  
  // 节流：每 20 帧检查一次，不需要每帧都进行昂贵的递归搜索
  readyCheckFrameCounter++;
  if (readyCheckFrameCounter % 20 !== 0) return;

  let changed = false;
  const allEntities = [...truckEntities, ...tankerEntities, ...uavEntities, ...tankerUavEntities];
  
  allEntities.forEach(entity => {
    if (modelsReadyStatus[entity.id]) return;
    
    // 先从缓存找
    let p = primitiveCache.get(entity.id);
    
    if (!p) {
      // 缓存没中，再进行搜索
      p = findModelPrimitive(viewer.scene.primitives, entity);
      if (!p) {
        p = findModelPrimitive(viewer.scene.groundPrimitives, entity);
      }
      if (p) {
        primitiveCache.set(entity.id, p);
        console.log(`[Cesium] 已找到并缓存实体 primitive: ${entity.id}`);
      }
    }

    if (p) {
      // 兼容多种就绪状态判断
      const isReady = p.ready || 
                      (p.readyPromise && p.readyPromise.state === 'fulfilled') || 
                      p._ready ||
                      (p.model && p.model.ready);
      
      if (isReady) {
        modelsReadyStatus[entity.id] = true;
        changed = true;
        console.log(`[Cesium] 检测到模型就绪: ${entity.id}`);
      }
    }
  });

  const now = Date.now();
  // 如果有变化，或者距离上次发送超过 1 秒，就发送一次全量状态
  if (changed || (now - lastEmitTime > 1000)) {
    const statusCopy = {};
    for (const key in modelsReadyStatus) {
      statusCopy[key] = modelsReadyStatus[key];
    }
    emit('models-ready', statusCopy);
    lastEmitTime = now;
  }
}

// 粒子系统实例
let smokeParticle = null
let fireParticle = null
let leakParticle = null
let diffusionParticle = null
let hoverHandler = null

const scenarioPoints = {
  command: { id: 'command', label: '远程指挥中心', longitude: 114.3055, latitude: 30.5928, color: '#67b8ff' },
  gateway: { id: 'gateway', label: '边缘传感网关', longitude: 114.3524, latitude: 30.5442, color: '#00e5ff' },
  detection: { id: 'detection', label: '检测现场', longitude: 114.389, latitude: 30.5282, color: '#ffb84d' },
  response: { id: 'response', label: '协同处置区域', longitude: 114.3348, latitude: 30.5638, color: '#8cf7c5' },
  accident_blue: { id: 'accident_blue', label: '货车追尾现场', longitude: 113.104833, latitude: 30.385469, color: '#ffea00' }, // 改为黄色
  accident_red: { id: 'accident_red', label: '油罐车泄露现场', longitude: 114.893327, latitude: 30.631683, color: '#00e5ff' },  // 改为蓝色
}

function toCesiumColor(color, alpha = 1) {
  return Cesium.Color.fromCssColorString(color).withAlpha(alpha)
}

function applyOrbitView(animate = false) {
  if (!viewer || isFlying) return
  const pointId = props.focusedPointId
  const isFocused = !!pointId && scenarioPoints[pointId]

  let lng, lat;
  if (isFocused) {
    if (pointId === 'accident_blue') {
      lng = truckAdjust.lng; lat = truckAdjust.lat;
    } else if (pointId === 'accident_red') {
      lng = tankerPointAdjust.lng; lat = tankerPointAdjust.lat;
    } else {
      lng = scenarioPoints[pointId].longitude;
      lat = scenarioPoints[pointId].latitude;
    }
  } else {
    // 湖北省中心点 (微调经纬度，使地图在视觉上避开左侧边栏和底部时间线)
    lng = 112.5; lat = 30.6;
  }

  try {
    const target = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
    
    // 默认视角参数 - 使用正上方向下看 (-90度) 展示完整的湖北省，并拉大高度以避免被UI遮挡
    let range = 1200000
    let pitch = Cesium.Math.toRadians(-90)
    let finalHeading = 0

    if (isFocused) {
      if (accidentViewLevel.value === 'far') {
        range = 120000
        pitch = Cesium.Math.toRadians(-60)
        finalHeading = (props.focusedPointId === 'accident_red' ? tankerOrbitHeading : truckOrbitHeading)
      } else if (accidentViewLevel.value === 'medium') {
        range = 2500
        pitch = Cesium.Math.toRadians(-45)
        finalHeading = (props.focusedPointId === 'accident_red' ? tankerOrbitHeading : truckOrbitHeading)
      } else if (accidentViewLevel.value === 'close') {
        range = props.focusedPointId === 'accident_red' ? 100 : 75
        pitch = Cesium.Math.toRadians(-20)
        finalHeading = Cesium.Math.toRadians(8)
      } else {
        // Read from defaultPhaseCameraConfigs
        const pIdx = props.activePhaseIndex + 1
        const scene = props.focusedPointId === 'accident_red' ? 'tanker' : 'truck'
        const cfg = (defaultPhaseCameraConfigs[scene] && defaultPhaseCameraConfigs[scene][pIdx]) || { range: 1440, pitch: -39, heading: -5 }
        
        range = cfg.range
        pitch = Cesium.Math.toRadians(cfg.pitch)
        finalHeading = Cesium.Math.toRadians(cfg.heading)
      }
    }

    if (animate && isFocused) {
      try {
        viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
      } catch (e) {}

      isFlying = true;
      viewer.camera.flyToBoundingSphere(new Cesium.BoundingSphere(target, 0), {
        offset: new Cesium.HeadingPitchRange(finalHeading, pitch, range),
        duration: 1.8,
        complete: () => {
          isFlying = false;
          try {
            if (viewer && !spinCallback) {
              viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(finalHeading, pitch, range));
            }
          } catch (e) {}
        },
        cancel: () => {
          isFlying = false;
        }
      });
    } else {
      viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(finalHeading, pitch, range))
    }
  } catch (error) {
    console.warn('应用轨道视角时出现警告:', error.message)
  }
}

onBeforeUnmount(() => {
  if (animationCheckTimer) clearInterval(animationCheckTimer)
  if (hoverHandler) {
    hoverHandler.destroy()
    hoverHandler = null
  }
})

function startAutoRotate() {
  if (!viewer || spinCallback) return
  lastSpinAt = performance.now()
  spinCallback = () => {
    if (!viewer) return
    if (accidentViewLevel.value === 'far') {
      stopAutoRotate();
      return;
    }
    const now = performance.now()
    const deltaSeconds = (now - lastSpinAt) / 1000
    lastSpinAt = now
    
    // 分离旋转逻辑
    if (props.focusedPointId === 'accident_red') {
      // 油罐车现场：不再进行持续自动旋转，保持视角完全静止
      // tankerOrbitHeading 保持不变
    } else {
      // 货车现场：保持原有的持续旋转效果
      truckOrbitHeading -= 0.06 * deltaSeconds
    }
    
    applyOrbitView()
  }
  viewer.clock.onTick.addEventListener(spinCallback)
}

function stopAutoRotate() {
  if (viewer && spinCallback) viewer.clock.onTick.removeEventListener(spinCallback)
  spinCallback = null
  if (viewer) {
    try {
      viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
    } catch (error) {
      console.warn('停止自动旋转时出现警告:', error.message)
    }
  }
}

// 创建更加逼真的烟雾系统
function createSmokeSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/smoke.png',
    startColor: new Cesium.Color(0.2, 0.2, 0.2, 0.6), // 初始深灰
    endColor: new Cesium.Color(0.9, 0.9, 0.9, 0.0),   // 最终淡白透明
    startScale: 1.0,
    endScale: 6.0, 
    minimumParticleLife: 2.0,
    maximumParticleLife: 4.5,
    minimumSpeed: 2.0,
    maximumSpeed: 5.0,
    imageSize: new Cesium.Cartesian2(25, 25), // 增大尺寸
    emissionRate: 60.0, // 增加密度
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(3.0), // 使用球形发射器增加体积感
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 模拟浮力：烟雾受热向上飘
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 2.5 * dt, gravityScratch); // 向上力
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
    }
  });
}

// 创建更加逼真的火焰/爆炸系统
function createFireSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/explosion00.png',
    startColor: new Cesium.Color(1.0, 0.9, 0.5, 0.8), // 爆炸瞬间的亮黄白
    endColor: new Cesium.Color(1.0, 0.3, 0.0, 0.0),   // 消失时的深橘红
    startScale: 1.5,
    endScale: 4.5, // 爆炸云团膨胀
    minimumParticleLife: 1.0,
    maximumParticleLife: 2.5,
    minimumSpeed: 3.0,
    maximumSpeed: 7.0,
    imageSize: new Cesium.Cartesian2(25, 25), // 增大尺寸以匹配爆炸图
    emissionRate: 65.0, 
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(2.0),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 快速向四周和上方窜升
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 5.0 * dt, gravityScratch); 
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
    }
  });
}

// 创建更加逼真、动感的油罐车泄露效果 (高压侧向喷射抛物线 Plume 效果)
function createLeakSystem(lng, lat) {
  const position = Cesium.Cartesian3.fromDegrees(lng, lat, 0.8);
  const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(tankerAdjust.heading) || 36), 0, 0);
  const modelMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(position, hpr);

  // 旋转发射器方向：把默认朝上(+z)的锥形喷射旋转-90度，使其朝向车身侧面(+y方向)喷出
  const rotation = Cesium.Matrix3.fromRotationX(Cesium.Math.toRadians(-90.0));
  // 稍微向车外侧偏移，使粒子从侧面罐体破裂处喷出，而不是车底中心
  const translation = new Cesium.Cartesian3(0.0, 1.2, 0.2);
  const emitterModelMatrix = Cesium.Matrix4.fromRotationTranslation(rotation, translation);

  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/whitePuff00.png',
    startColor: new Cesium.Color(0.85, 0.9, 0.95, 0.65), // 增强不透明度，表现喷射处的浓密感
    endColor: new Cesium.Color(0.95, 0.97, 1.0, 0.0),
    startScale: 0.6,  // 喷口处适当保留体积
    endScale: 5.5,    // 随抛物线下落扩散开来
    minimumParticleLife: 1.0,
    maximumParticleLife: 2.2, // 较短寿命防止在天空中堆积
    minimumSpeed: 3.5, // 喷出的初始速度
    maximumSpeed: 6.0,
    imageSize: new Cesium.Cartesian2(6, 6), // 较小的粒子尺寸以获得精细自然的渐变感
    emissionRate: 140.0, // 显著提高粒子发射率以模拟连续高压水柱/气柱
    lifetime: 16.0,
    emitter: new Cesium.ConeEmitter(Cesium.Math.toRadians(25.0)), // 25度适度喷嘴角度
    modelMatrix: modelMatrix,
    emitterModelMatrix: emitterModelMatrix,
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 1. 模拟水平方向空气阻力：速度迅速衰减，表现喷射后的悬浮感
      const dragFactor = Math.pow(0.85, dt * 60);
      particle.velocity.x *= dragFactor;
      particle.velocity.y *= dragFactor;

      // 2. 模拟重力下坠：喷出后的气体/液体在重力作用下呈优美的抛物线弧度坠落到地面
      particle.velocity.z -= 4.0 * dt;
    }
  });
}

// 创建弥漫效果系统 (使用 whitePuff00.png) - 统一为与泄露一致的圆形粒子喷射散开效果，并支持随时间渐进向外扩散 (已微调减小)
function createDiffusionSystem(lng, lat) {
  const center = Cesium.Cartesian3.fromDegrees(lng, lat, 0.8);
  
  // 计算卡车所在位置的局部 ENU (东-北-上) 坐标轴向量，用于在地球世界坐标系中进行方向纠正
  const enuMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(center);
  const eastVec = Cesium.Matrix4.getColumn(enuMatrix, 0, new Cesium.Cartesian3());
  const northVec = Cesium.Matrix4.getColumn(enuMatrix, 1, new Cesium.Cartesian3());
  const upVec = Cesium.Matrix4.getColumn(enuMatrix, 2, new Cesium.Cartesian3());

  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/whitePuff00.png',
    startColor: new Cesium.Color(0.35, 0.8, 0.35, 0.45), // 绿色半透明圆形粒子
    endColor: new Cesium.Color(0.45, 0.85, 0.45, 0.0),       // 渐变至完全透明
    startScale: 0.8,
    endScale: 8.0, // 在生命周期中逐渐膨胀变大
    minimumParticleLife: 4.0,
    maximumParticleLife: 6.5, // 微调粒子寿命，适度减小扩散半径
    minimumSpeed: 2.0,
    maximumSpeed: 5.5, // 适度调低喷出初速度
    imageSize: new Cesium.Cartesian2(9, 9), // 基础尺寸调整为 9x9 (原为12x12)，更显精细与克制
    emissionRate: 120.0, // 保持发射率以维持连贯的团雾质感
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(2.5), // 发射器半径调整为 2.5 (原为3.5)
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(center),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 1. 真实局部向上浮力 (Z轴向上，使整个弥漫气云升空)
      const buoyancy = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(upVec, 0.5 * dt, buoyancy); 
      Cesium.Cartesian3.add(particle.velocity, buoyancy, particle.velocity);
      
      // 2. 真实地理风向漂移：沿局部东向和北向缓缓漂移
      const windEast = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(eastVec, 0.5 * dt, windEast);
      Cesium.Cartesian3.add(particle.velocity, windEast, particle.velocity);
      
      const windNorth = new Cesium.Cartesian3();
      Cesium.Cartesian3.multiplyByScalar(northVec, 0.25 * dt, windNorth);
      Cesium.Cartesian3.add(particle.velocity, windNorth, particle.velocity);

      // 3. 随仿真阶段时间推移的“渐进式向外二次大范围膨胀扩散”
      const offset = Cesium.Cartesian3.subtract(particle.position, center, new Cesium.Cartesian3());
      const dist = Cesium.Cartesian3.magnitude(offset);
      if (dist > 0.01) {
        const dir = new Cesium.Cartesian3();
        Cesium.Cartesian3.normalize(offset, dir);
        
        // 根据阶段持续运行时间 (15 秒内渐进增强)
        const elapsed = diffusionStartTime ? (Date.now() - diffusionStartTime) / 1000 : 0;
        const systemTimeRatio = Math.min(elapsed / 15.0, 1.0);
        
        // 随着阶段进行，粒子向四周放射膨胀的速度适度增加
        const extraForce = (4.0 + 12.0 * systemTimeRatio) * dt;
        const expansion = new Cesium.Cartesian3();
        Cesium.Cartesian3.multiplyByScalar(dir, extraForce, expansion);
        Cesium.Cartesian3.add(particle.velocity, expansion, particle.velocity);
        
        // 动态调控粒子大小：远端的粒子适度膨胀
        const ageRatio = particle.age / particle.life;
        const currentEndScale = 8.0 + 8.0 * systemTimeRatio; // 最大可膨胀到 16.0 倍 (原为22.0)
        particle.scale = 0.8 + (currentEndScale - 0.8) * ageRatio;
      }

      // 4. 空气阻力：阻力从 0.978 调整到 0.96，使扩散边界略微收拢，防止过度散开
      const dragFactor = Math.pow(0.96, dt * 60);
      particle.velocity.x *= dragFactor;
      particle.velocity.y *= dragFactor;
      particle.velocity.z *= dragFactor;
    }
  });
}

function updatePopupPosition() {
  if (!viewer) return;

  // 救援装备出动阶段 (index === 6) 让浮窗和图标跟随无人机的位置运动
  if (rescuePopup.show && Number(props.activePhaseIndex) === 6) {
    const isTanker = props.focusedPointId === 'accident_red';
    const uavId = isTanker ? 'uav_model_tanker' : 'uav_model';
    const uavEntity = viewer.entities.getById(uavId);
    if (uavEntity) {
      const pos = uavEntity.position.getValue(viewer.clock.currentTime);
      if (pos) {
        const cartographic = Cesium.Cartographic.fromCartesian(pos);
        rescueCoords.lng = Cesium.Math.toDegrees(cartographic.longitude);
        rescueCoords.lat = Cesium.Math.toDegrees(cartographic.latitude);
        // 让浮窗/标记在无人机上方以避免重叠
        rescueCoords.height = cartographic.height + 8.0;
      }
    }
  }

  if (rescuePopup.show) {
    const cartesian = Cesium.Cartesian3.fromDegrees(rescueCoords.lng, rescueCoords.lat, rescueCoords.height);
    const canvasPosition = viewer.scene.cartesianToCanvasCoordinates(cartesian);
    if (canvasPosition) {
      rescuePopup.x = canvasPosition.x;
      rescuePopup.y = canvasPosition.y - 45;
    }
  }

  // 更新实时检测浮窗坐标 (当位于货车追尾现场的次生灾害起火阶段 index === 4 时)
  if (detectionPopup.show && props.activePhaseIndex === 4 && props.focusedPointId === 'accident_blue') {
    const lng = Number(truckAdjust.lng) || 113.104833;
    const lat = Number(truckAdjust.lat) || 30.385469;
    const cartesian = Cesium.Cartesian3.fromDegrees(lng, lat, 20.0);
    const canvasPosition = viewer.scene.cartesianToCanvasCoordinates(cartesian);
    if (canvasPosition) {
      detectionPopup.x = canvasPosition.x;
      detectionPopup.y = canvasPosition.y - 130;
    }
  }

  // 更新仿真推演悬浮窗坐标 (当位于货车追尾现场的无人感知执行阶段 index === 8 时)
  if (simulationPopup.show && props.activePhaseIndex === 8 && props.focusedPointId === 'accident_blue') {
    const lng = Number(truckAdjust.lng) || 113.104833;
    const lat = Number(truckAdjust.lat) || 30.385469;
    const cartesian = Cesium.Cartesian3.fromDegrees(lng, lat, 20.0);
    const canvasPosition = viewer.scene.cartesianToCanvasCoordinates(cartesian);
    if (canvasPosition) {
      simulationPopup.x = canvasPosition.x;
      simulationPopup.y = canvasPosition.y - 120;
    }
  }

  // 更新事故现场图片浮窗坐标
  if (accidentDetailPopup.show && accidentDetailPopup.pointId) {
    const point = scenarioPoints[accidentDetailPopup.pointId];
    if (point) {
      let lng = point.longitude, lat = point.latitude;
      if (accidentDetailPopup.pointId === 'accident_blue') {
        lng = truckAdjust.lng; lat = truckAdjust.lat;
      } else if (accidentDetailPopup.pointId === 'accident_red') {
        lng = tankerPointAdjust.lng; lat = tankerPointAdjust.lat;
      }
      const cartesian = Cesium.Cartesian3.fromDegrees(lng, lat, 0);
      const canvasPosition = viewer.scene.cartesianToCanvasCoordinates(cartesian);
      if (canvasPosition) {
        accidentDetailPopup.x = canvasPosition.x;
        accidentDetailPopup.y = canvasPosition.y - 40;
      }
    }
  }

  // 更新无人车浮窗坐标与数据 (仅在到达现场后显示，也就是 activePhaseIndex >= 7)
  if (props.activePhaseIndex >= 7) {
    const isTanker = props.focusedPointId === 'accident_red';
    const carPosCallback = isTanker ? sharedTankerRescueCarPosition : sharedTruckRescueCarPosition;
    
    if (carPosCallback) {
      const pos = carPosCallback.getValue(viewer.clock.currentTime);
      if (pos) {
        const canvasPos = viewer.scene.cartesianToCanvasCoordinates(pos);
        if (canvasPos) {
          // A车在左侧，B车在右侧，稍微错开
          ugvA.x = canvasPos.x - 220;
          ugvA.y = canvasPos.y - 120;
          ugvB.x = canvasPos.x + 20;
          ugvB.y = canvasPos.y - 120;

          // 关联真实的全局传感数据
          ugvA.temp = props.sensorData?.temp || 0;
          ugvA.hum = props.sensorData?.humidity || 0;
          ugvA.smoke = props.sensorData?.smoke || 0;
          ugvA.tvoc = props.sensorData?.tvoc || 0;
          ugvA.co = props.sensorData?.co || 0;

          // 无人车 B 作为辅助节点，制造合理的微小偏差以体现多设备空间差异
          ugvB.temp = +(ugvA.temp - 0.45).toFixed(2);
          ugvB.hum = +(ugvA.hum - 2.12).toFixed(2);
          ugvB.smoke = Math.max(0, Math.floor(ugvA.smoke * 0.95));
          ugvB.tvoc = Math.max(0, +(ugvA.tvoc * 0.88).toFixed(3));
          ugvB.co = Math.max(0, +(ugvA.co * 0.92).toFixed(1));
        } else {
          ugvA.x = -1000; ugvA.y = -1000;
          ugvB.x = -1000; ugvB.y = -1000;
        }
      }
    }
  } else {
    ugvA.x = -1000; ugvA.y = -1000;
    ugvB.x = -1000; ugvB.y = -1000;
  }
}

// 辅助方法：将经纬度数组转换为 Cesium.Cartesian3 数组
const convertCoordsToCartesians = (coords) => {
  const degrees = [];
  coords.forEach(pt => {
    degrees.push(pt[0], pt[1]);
  });
  return Cesium.Cartesian3.fromDegreesArray(degrees);
};

// 绘制湖北省行政边界外框线 (霓虹发光材质)
function drawBoundaryLine(coords) {
  if (!viewer) return;
  const positions = convertCoordsToCartesians(coords);
  viewer.entities.add({
    name: '湖北省行政边界',
    polyline: {
      positions: positions,
      width: 4.5,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.22,
        color: Cesium.Color.fromCssColorString('#00ffff') // 蓝绿色发光边界
      }),
      clampToGround: true
    }
  });
}

// 绘制市级行政区区划边界与点击面 (霓虹发光材质与半透明填充)
function drawCityBoundary(coords, colorStr, name, id) {
  if (!viewer) return;
  const positions = convertCoordsToCartesians(coords);
  
  // 1. 霓虹发光边线
  viewer.entities.add({
    id: id + '-line',
    name: name,
    polyline: {
      positions: positions,
      width: 5.5, // 稍微加粗，使市级边界显眼
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.26,
        color: Cesium.Color.fromCssColorString(colorStr)
      }),
      clampToGround: true
    }
  });

  // 2. 填充的多边形 (设置挤出高度，使其成为具有上浮效果的三维立体模块，并能接收点击事件)
  viewer.entities.add({
    id: id,
    name: name,
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      material: Cesium.Color.fromCssColorString(colorStr).withAlpha(0.15), // 提高透明度让立体感更强
      classificationType: Cesium.ClassificationType.BOTH,
      outline: false
    }
  });
}

// 异步加载湖北省所有市级行政区划边界数据与标注，并用亮色边界和填充面描绘出来
async function loadCityBoundaries() {
  if (!viewer) return;
  cityLabelEntities.length = 0;

  try {
    const response = await fetch('/Dashboard/hubei_cities.json');
    if (!response.ok) throw new Error('读取 hubei_cities.json 失败');
    const geojson = await response.json();
    
    geojson.features.forEach(feature => {
      const properties = feature.properties || {};
      const name = properties.name || '';
      const adcode = properties.adcode;
      const geometry = feature.geometry;
      if (!name || !geometry) return;

      // 为不同的市分配精细的霓虹配色，突出重点城市 (武汉/黄冈/仙桃)
      let colorStr = '#00ffd8'; // 默认淡青色
      if (name.includes('武汉')) {
        colorStr = '#00e5ff'; // 亮青
      } else if (name.includes('黄冈')) {
        colorStr = '#ffd700'; // 金黄
      } else if (name.includes('仙桃')) {
        colorStr = '#ff007f'; // 霓虹粉
      }

      // 生成唯一的 ID 标识，用于鼠标悬停和点击事件
      const cityId = `city-boundary-${adcode}`;

      // 1. 绘制边界多边形及外框线
      if (geometry.type === 'Polygon') {
        drawCityBoundary(geometry.coordinates[0], colorStr, name, cityId);
      } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach((polygon, idx) => {
          drawCityBoundary(polygon[0], colorStr, name, `${cityId}-${idx}`);
        });
      }

      // 2. 添加市级文字标注（以白字黑边展示）
      const center = properties.centroid || properties.center;
      if (center && center.length >= 2) {
        const labelEntity = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(center[0], center[1], 1000),
          label: {
            text: name,
            font: `bold ${labelConfig.fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`,
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.fromCssColorString('#070b19'),
            outlineWidth: labelConfig.outlineWidth,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            eyeOffset: new Cesium.Cartesian3(0, 0, -1000),
            // 随相机距离自动缩放：近看正常大小，拉远时缩小
            scaleByDistance: new Cesium.NearFarScalar(300000, 1.0, 2500000, 0.4),
            // 远距离时逐渐半透明，避免标注拥挤
            translucencyByDistance: new Cesium.NearFarScalar(800000, 1.0, 2800000, 0.5)
          }
        });
        cityLabelEntities.push(labelEntity);
      }
    });
    console.log('[Cesium] 湖北省所有市级行政边界及标注加载成功');
  } catch (error) {
    console.error('加载湖北省市级行政边界时出错:', error);
  }
}

// 异步加载湖北省行政区划边界数据，并建立反向蒙版 (遮罩层)
async function loadHubeiMask() {
  if (!viewer) return;
  try {
    const response = await fetch('/Dashboard/hubei.json');
    if (!response.ok) throw new Error('读取 hubei.json 失败');
    const geojson = await response.json();

    const holes = [];
    geojson.features.forEach(feature => {
      const geometry = feature.geometry;
      if (geometry.type === 'Polygon') {
        const outerRing = convertCoordsToCartesians(geometry.coordinates[0]);
        holes.push(new Cesium.PolygonHierarchy(outerRing));
        drawBoundaryLine(geometry.coordinates[0]);
      } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach(polygon => {
          const outerRing = convertCoordsToCartesians(polygon[0]);
          holes.push(new Cesium.PolygonHierarchy(outerRing));
          drawBoundaryLine(polygon[0]);
        });
      }
    });

    // 建立一个安全的大范围外圈多边形（避免南北极和经度 180 度折叠/纠缠造成的渲染失败）
    const worldPolygonHierarchy = new Cesium.PolygonHierarchy(
      Cesium.Cartesian3.fromDegreesArray([
        50, 65,
        160, 65,
        160, 5,
        50, 5
      ]),
      holes
    );

    // 将湖北省作为“空洞”添加到这个多边形中，实现反向遮罩：
    // 湖北省外区域被深蓝黑色（匹配大屏底色）遮盖，仅有湖北省内部保持透明以显示遥感地图与地形
    viewer.entities.add({
      id: 'hubei-mask',
      name: '湖北省行政边界反向遮罩',
      polygon: {
        hierarchy: worldPolygonHierarchy,
        material: Cesium.Color.fromCssColorString('#070b19').withAlpha(0.96), // 贴合大屏的极简深邃蓝底色
        classificationType: Cesium.ClassificationType.BOTH,
        outline: false
      }
    });

  } catch (error) {
    console.error('加载湖北省行政边界蒙版时出错:', error);
  }
}

async function initViewer() {
  console.log('[Cesium] 开始初始化三维地球...')
  if (!containerRef.value || viewer) {
    console.log('[Cesium] 容器不存在或已初始化')
    return
  }
  console.log('[Cesium] 容器元素:', containerRef.value)
  console.log('[Cesium] 容器尺寸:', containerRef.value.offsetWidth, 'x', containerRef.value.offsetHeight)
  
  try {
    console.log('[Cesium] 创建 Viewer 实例...')
    viewer = new Cesium.Viewer(containerRef.value, {
      animation: false, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
      infoBox: false, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
      timeline: false, shouldAnimate: true, skyAtmosphere: false,
    })
    window.viewer = viewer
    console.log('[Cesium] Viewer 实例创建成功')
    
    // 关闭地球物理光照（防止因为时差导致场景处于黑夜）
    viewer.scene.globe.enableLighting = false
    
    // 关键修复：添加“相机头灯”，将环境光强制绑定到相机视角前方，这样不管什么角度看模型，模型都是被照亮的
    viewer.scene.light = new Cesium.DirectionalLight({
      direction: viewer.camera.direction
    })
    viewer.scene.preRender.addEventListener(function(scene, time) {
      scene.light.direction = Cesium.Cartesian3.clone(scene.camera.directionWC, scene.light.direction)
    })

     viewer.cesiumWidget.creditContainer.style.display = 'none'

    // 临时调试点击事件，获取道路精确坐标
    const debugHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    debugHandler.setInputAction(function (movement) {
      // 优先检测是否点击了三维立体控板
      const pickedObject = viewer.scene.pick(movement.position);
      if (Cesium.defined(pickedObject) && pickedObject.id) {
        const pickedId = String(pickedObject.id.id);
        if (pickedId.startsWith('city-boundary-xiantao') || pickedId.startsWith('city-boundary-429004')) {
          // 点击仙桃市行政区域 → 与点击黄色事故点效果相同，跳转到第二视角
          emit('accident-picked', 'accident_blue');
          zoomToPoint('accident_blue');
          return;
        } else if (pickedId.startsWith('city-boundary-huanggang') || pickedId.startsWith('city-boundary-421100')) {
          // 点击黄冈市行政区域 → 与点击红色事故点效果相同，跳转到第二视角
          emit('accident-picked', 'accident_red');
          zoomToPoint('accident_red');
          return;
        }
      }

      // 临时调试点击事件，获取道路精确坐标
      const ray = viewer.camera.getPickRay(movement.position);
      const cartesian = viewer.scene.globe.pick(ray, viewer.scene);
      if (cartesian) {
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
        const longitudeString = Cesium.Math.toDegrees(cartographic.longitude).toFixed(6);
        const latitudeString = Cesium.Math.toDegrees(cartographic.latitude).toFixed(6);
        console.log(`[CLICK_COORDS] lng: ${longitudeString}, lat: ${latitudeString}`);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);



    viewer.imageryLayers.removeAll()
    console.log('[Cesium] 加载 ArcGIS 影像图层...')
    try {
      const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
        'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
      )
      viewer.imageryLayers.addImageryProvider(imagery)
      console.log('[Cesium] ArcGIS 影像图层加载成功')
    } catch (e) {
      console.warn('[Cesium] ArcGIS 影像图层加载失败，使用默认底图:', e.message)
      viewer.imageryLayers.addImageryProvider(new Cesium.createWorldImagery())
    }

    // 加载湖北省行政边界反向蒙版
    try {
      await loadHubeiMask()
    } catch (e) {
      console.warn('初始化湖北省遮罩蒙版时出现警告:', e.message)
    }

    // 加载仙桃市和黄冈市行政边界
    try {
      await loadCityBoundaries()
    } catch (e) {
      console.warn('初始化仙桃市和黄冈市边界时出现警告:', e.message)
    }

    try {
      await loadHubeiRoads()
    } catch (e) {
      console.warn('初始化湖北省干线路网和两客一危车辆时出现警告:', e.message)
    }

    try {
      addEventEntities()
    } catch (e) {
      console.warn('添加事件实体时出现警告:', e.message)
    }

    try {
      smokeParticle = viewer.scene.primitives.add(createSmokeSystem(truckAdjust.lng, truckAdjust.lat))
      fireParticle = viewer.scene.primitives.add(createFireSystem(truckAdjust.lng, truckAdjust.lat))
      leakParticle = viewer.scene.primitives.add(createLeakSystem(tankerPointAdjust.lng, tankerPointAdjust.lat))
      diffusionParticle = viewer.scene.primitives.add(createDiffusionSystem(tankerPointAdjust.lng, tankerPointAdjust.lat))
    } catch (e) {
      console.warn('初始化粒子系统时出现警告:', e.message)
    }

    try {
      applyOrbitView()
    } catch (e) {
      console.warn('应用初始视角时出现警告:', e.message)
    }

    try {
      updatePhaseScene(props.activePhaseIndex)
    } catch (e) {
      console.warn('更新初始场景时出现警告:', e.message)
    }

    viewer.scene.postRender.addEventListener(updateModelsReadyStatus)
    viewer.scene.postRender.addEventListener(updatePopupPosition)

    loading.value = false
  } catch (error) {
    errorMessage.value = '三维地球初始化失败'
    loading.value = false
    console.error('三维地球初始化失败:', error)
  }
}

// 两客一危在途监控分类筛选与状态
const activeVehicleFilter = ref('all');
let lkywVehicles = [];
let lkywBillboardCollection = null;
let lkywPointCollection = null;
let trafficVehicles = [];
let trafficPointCollection = null;
let trafficAnimationRemoveListener = null;

// 🚚 全省两客一危 实时省界卡口流转监管 动态数据
const trafficStats = reactive({
  hazard: {
    total: 342,
    inbound: 1284,
    outbound: 968,
    inPulse: false,
    outPulse: false,
    totalPulse: false
  },
  passenger: {
    total: 856,
    inbound: 3412,
    outbound: 3105,
    inPulse: false,
    outPulse: false,
    totalPulse: false
  },
  tourist: {
    total: 512,
    inbound: 1890,
    outbound: 1650,
    inPulse: false,
    outPulse: false,
    totalPulse: false
  }
});

// 🛠️ 大屏 HUD 高阶视图 Tabs 模式 ('overview' | 'risk' | 'checkpoint' | 'ai')
const activeHudTab = ref('overview');

const focusRiskVehicleOnMap = (lng, lat) => {
  if (viewer) {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lng, lat, 3500),
      orientation: {
        heading: Cesium.Math.toRadians(0.0),
        pitch: Cesium.Math.toRadians(-40.0),
        roll: 0.0
      },
      duration: 1.5
    });
  }
};

const handleAutoDispatchTrigger = () => {
  alert('🤖 全省应急联动机制已成功开启！系统正在推演最佳调度路线与巡逻无人机航线。');
};
// 🛠️ 右侧智控终端面板 展开/收起 状态
const isHudCollapsed = ref(false);

const activeHazardDemoCount = computed(() => {
  if (!lkywVehicles) return 0;
  return lkywVehicles.filter(v => v.category === 'hazard').length;
});

const activePassengerDemoCount = computed(() => {
  if (!lkywVehicles) return 0;
  return lkywVehicles.filter(v => v.category === 'passenger').length;
});

const activeTouristDemoCount = computed(() => {
  if (!lkywVehicles) return 0;
  return lkywVehicles.filter(v => v.category === 'tourist').length;
});

const totalActiveInTransit = computed(() => {
  return trafficStats.hazard.total + trafficStats.passenger.total + trafficStats.tourist.total;
});

// 🌐 全省省界卡口 入省/出省/净流入 实时统计计算
const totalInboundCount = computed(() => {
  return trafficStats.hazard.inbound + trafficStats.passenger.inbound + trafficStats.tourist.inbound;
});

const totalOutboundCount = computed(() => {
  return trafficStats.hazard.outbound + trafficStats.passenger.outbound + trafficStats.tourist.outbound;
});

const netInflowCount = computed(() => {
  return totalInboundCount.value - totalOutboundCount.value;
});

const hazardRatioPercent = computed(() => {
  const tot = totalActiveInTransit.value || 1;
  return ((trafficStats.hazard.total / tot) * 100).toFixed(1);
});

const passengerRatioPercent = computed(() => {
  const tot = totalActiveInTransit.value || 1;
  return ((trafficStats.passenger.total / tot) * 100).toFixed(1);
});

const touristRatioPercent = computed(() => {
  const tot = totalActiveInTransit.value || 1;
  return ((trafficStats.tourist.total / tot) * 100).toFixed(1);
});

// SVG Donut 饼图弧度比例动态计算 (2 * Math.PI * 38 ≈ 238.76)
const passengerStrokeLen = computed(() => {
  const tot = totalActiveInTransit.value || 1;
  return (238.76 * (trafficStats.passenger.total / tot)).toFixed(2);
});

const touristStrokeLen = computed(() => {
  const tot = totalActiveInTransit.value || 1;
  return (238.76 * (trafficStats.tourist.total / tot)).toFixed(2);
});

const hazardStrokeLen = computed(() => {
  const tot = totalActiveInTransit.value || 1;
  return (238.76 * (trafficStats.hazard.total / tot)).toFixed(2);
});

// 📊 湖北省重点干线车流 Top 5 动态柱状图数据
const highwayFlowData = reactive([
  { name: '沪渝高速 G50', code: 'G50', count: 428, hazardRatio: 18.5, max: 500 },
  { name: '福银高速 G70', code: 'G70', count: 385, hazardRatio: 22.4, max: 500 },
  { name: '京港澳 G4',    code: 'G4',  count: 350, hazardRatio: 14.8, max: 500 },
  { name: '沪蓉高速 G42', code: 'G42', count: 312, hazardRatio: 24.1, max: 500 },
  { name: '汉十高速 S82', code: 'S82', count: 235, hazardRatio: 11.6, max: 500 }
]);

// ⚡ 实时抓拍卡口日志数据流（动态推送）
const latestCameraLogs = reactive([
  { time: '19:09:40', location: '武黄省界卡口', plate: '鄂A-H8921', category: '危化品', action: '入省' },
  { time: '19:09:39', location: '京港澳赤壁卡口', plate: '鄂C-K5531', category: '班线客车', action: '出省' },
  { time: '19:09:37', location: '沪蓉鄂东大桥', plate: '鄂F-T9918', category: '旅游包车', action: '入省' }
]);

const cameraLocations = [
  '武黄高速省界卡口', '京港澳赤壁卡口', '沪蓉鄂东大桥卡口', '福银高速黄梅卡口', 
  '沪渝鄂西关口', '汉十高速襄阳卡口', '随岳高速省界卡口', '宜恩高速卡口'
];

const platePrefixes = ['鄂A', '鄂B', '鄂C', '鄂E', '鄂F', '鄂H'];

function generateRandomPlate() {
  const pref = platePrefixes[Math.floor(Math.random() * platePrefixes.length)];
  const num = Math.floor(1000 + Math.random() * 9000);
  return `${pref}-${num}`;
}

let hudStatsTimer = null;

function startHudStatsSimulation() {
  if (hudStatsTimer) clearInterval(hudStatsTimer);
  
  // ⚡ 850ms 高频实时动态流转引擎 (不断进行统计与跳动计算)
  hudStatsTimer = setInterval(() => {
    const categories = ['hazard', 'passenger', 'tourist'];
    
    // 1. 卡口流量与在途数量高频流转
    const cat = categories[Math.floor(Math.random() * categories.length)];
    const isEntry = Math.random() > 0.45;
    const target = trafficStats[cat];

    if (isEntry) {
      const inc = Math.floor(Math.random() * 2) + 1;
      target.inbound += inc;
      target.total += inc;
      target.inPulse = true;
      target.totalPulse = true;
      setTimeout(() => {
        target.inPulse = false;
        target.totalPulse = false;
      }, 450);
    } else {
      const dec = Math.floor(Math.random() * 2) + 1;
      target.outbound += dec;
      target.total = Math.max(120, target.total - dec + (Math.random() > 0.5 ? 1 : 0));
      target.outPulse = true;
      target.totalPulse = true;
      setTimeout(() => {
        target.outPulse = false;
        target.totalPulse = false;
      }, 450);
    }

    // 2. 重点干线柱状图 (车流量与高危比例 动态跳动重算)
    const hwCountToUpdate = Math.floor(Math.random() * 2) + 1;
    for (let i = 0; i < hwCountToUpdate; i++) {
      const hwIndex = Math.floor(Math.random() * highwayFlowData.length);
      const hwDelta = (Math.random() > 0.48 ? 1 : -1) * (Math.floor(Math.random() * 3) + 1);
      highwayFlowData[hwIndex].count = Math.max(150, Math.min(485, highwayFlowData[hwIndex].count + hwDelta));
      
      // 动态重算高危占比
      const ratioDelta = ((Math.random() - 0.5) * 0.4).toFixed(1);
      const newRatio = parseFloat((highwayFlowData[hwIndex].hazardRatio + parseFloat(ratioDelta)).toFixed(1));
      highwayFlowData[hwIndex].hazardRatio = Math.max(10.0, Math.min(28.0, newRatio));
    }

    // 3. 动态推送最新卡口抓拍与实时通报
    if (Math.random() > 0.35) {
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
      const randomLoc = cameraLocations[Math.floor(Math.random() * cameraLocations.length)];
      const randomCat = cat === 'hazard' ? '危化品' : (cat === 'passenger' ? '班线客车' : '旅游包车');
      
      latestCameraLogs.unshift({
        time: timeStr,
        location: randomLoc,
        plate: generateRandomPlate(),
        category: randomCat,
        action: isEntry ? '入省' : '出省'
      });
      if (latestCameraLogs.length > 4) latestCameraLogs.pop();
    }

  }, 850);
}

// 启动省界卡口实时流转模拟
startHudStatsSimulation();

function toggleVehicleFilter(filterType) {
  activeVehicleFilter.value = filterType;
  trafficConfig.activeCategory = filterType;

  // 1. 过滤精细重点巡航 Demo 悬浮标牌
  if (lkywVehicles && lkywVehicles.length > 0) {
    lkywVehicles.forEach(item => {
      const isMatch = (filterType === 'all' || item.category === filterType);
      if (item.billboard) item.billboard.show = isMatch;
      if (item.point) item.point.show = isMatch;
    });
  }

  // 2. 过滤全省公路背景点位（赤红危化品/翠绿客车/青蓝包车）
  if (trafficVehicles && trafficVehicles.length > 0) {
    trafficVehicles.forEach(v => {
      if (!v.primitive) return;
      if (filterType === 'all') {
        v.primitive.show = true;
        v.primitive.color = Cesium.Color.fromCssColorString(v.dotColor).withAlpha(0.85);
        v.primitive.pixelSize = v.category === 'hazard' ? 4.0 : 3.0;
      } else if (v.category === filterType) {
        v.primitive.show = true;
        v.primitive.color = Cesium.Color.fromCssColorString(v.dotColor).withAlpha(1.0);
        v.primitive.pixelSize = 5.5; // 高亮放大
      } else {
        v.primitive.show = true;
        v.primitive.color = Cesium.Color.fromCssColorString(v.dotColor).withAlpha(0.12); // 淡化暗显
        v.primitive.pixelSize = 2.0;
      }
    });
  }
}

// 动态绘制 "两客一危" 车辆的极简高科技赛博胶囊徽章（Capsule Badge）
function createVehicleBillboardCanvas(category, plate, speed) {
  // Retina 2x 超清绘制，保证高分屏与缩放视角下极度精致
  const scaleFactor = 2;
  const logicalWidth = 138;
  const logicalHeight = 30;
  const canvas = document.createElement('canvas');
  canvas.width = logicalWidth * scaleFactor;
  canvas.height = logicalHeight * scaleFactor;
  const ctx = canvas.getContext('2d');

  ctx.scale(scaleFactor, scaleFactor);

  let themeColor, icon;
  if (category === 'hazard') {
    themeColor = '#FF3344'; // 高危红
    icon = '🧪';
  } else if (category === 'passenger') {
    themeColor = '#00E676'; // 班线绿
    icon = '🚌';
  } else {
    themeColor = '#00B0FF'; // 包车蓝
    icon = '🚐';
  }

  const cardW = 130;
  const cardH = 22;
  const cardX = 4;
  const cardY = 3;

  // 1. 底层胶囊背景：半透明极光深黑 + 1.2px 边框发光
  ctx.save();
  ctx.shadowColor = themeColor;
  ctx.shadowBlur = 5;

  ctx.fillStyle = 'rgba(6, 12, 24, 0.90)';
  ctx.strokeStyle = themeColor;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  if (typeof ctx.roundRect === 'function') {
    ctx.roundRect(cardX, cardY, cardW, cardH, 11);
  } else {
    ctx.rect(cardX, cardY, cardW, cardH);
  }
  ctx.fill();
  ctx.stroke();
  ctx.restore();

  // 2. 左侧图标圆圈
  const iconCx = cardX + 12;
  const iconCy = cardY + cardH / 2;

  ctx.fillStyle = themeColor;
  ctx.beginPath();
  ctx.arc(iconCx, iconCy, 7.5, 0, Math.PI * 2);
  ctx.fill();

  // 图标 Emoji
  ctx.font = '8.5px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(icon, iconCx, iconCy + 0.5);

  // 3. 车牌号 (主标题：纯白 11px 粗体)
  ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  ctx.fillStyle = '#FFFFFF';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText(plate, cardX + 24, cardY + cardH / 2);

  // 4. 实时速度 (右侧鲜黄 10px monospace)
  ctx.font = 'bold 9.5px monospace';
  ctx.fillStyle = '#FFD700';
  ctx.textAlign = 'right';
  ctx.fillText(`${speed}k/h`, cardX + cardW - 6, cardY + cardH / 2);

  // 5. 底部下沉定位针尖（定位下沉，解决悬浮感）
  ctx.fillStyle = themeColor;
  ctx.beginPath();
  ctx.moveTo(logicalWidth / 2 - 3, cardY + cardH);
  ctx.lineTo(logicalWidth / 2 + 3, cardY + cardH);
  ctx.lineTo(logicalWidth / 2, cardY + cardH + 4);
  ctx.closePath();
  ctx.fill();

  return canvas;
}

// 异步加载湖北省主要高速干线路网并初始化车流与在途“两客一危”
async function loadHubeiRoads() {
  if (!viewer) return;
  try {
    if (!cachedHubeiGeojson) {
      const response = await fetch('/Dashboard/hubei_highways.geojson');
      if (!response.ok) return;
      cachedHubeiGeojson = await response.json();
    }
    const geojson = cachedHubeiGeojson;

    const highwaysSource = await Cesium.GeoJsonDataSource.load(geojson, {
      clampToGround: true
    });
    
    // 使用纤细雅致暗金线条渲染基础路网
    const roadMaterial = new Cesium.ColorMaterialProperty(
      Cesium.Color.fromCssColorString('#d4af37').withAlpha(0.38)
    );

    highwaysSource.entities.values.forEach(entity => {
      if (entity.polyline) {
        entity.polyline.material = roadMaterial;
        entity.polyline.width = 1.0;
      }
    });
    viewer.dataSources.add(highwaysSource);

    reApplyTrafficRoutes();
  } catch (error) {
    console.error('加载湖北省路网数据时出错:', error);
  }
}

// 初始化全省干线两客一危（危化品运输车、班线客车、旅游包车）动态巡航监测系统
function initLkywVehiclesFromGeoJson(geojson) {
  if (!viewer || !geojson || !geojson.features) return;

  if (lkywBillboardCollection) {
    viewer.scene.primitives.remove(lkywBillboardCollection);
    lkywBillboardCollection = null;
  }
  if (lkywPointCollection) {
    viewer.scene.primitives.remove(lkywPointCollection);
    lkywPointCollection = null;
  }

  lkywVehicles = [];
  lkywBillboardCollection = new Cesium.BillboardCollection();
  lkywPointCollection = new Cesium.PointPrimitiveCollection();

  const allRoutes = [];

  geojson.features.forEach(feature => {
    const geom = feature.geometry;
    if (!geom) return;

    const parseRoute = (coords) => {
      if (!coords || coords.length < 3) return;
      const segmentLengths = [0];
      let totalDist = 0;

      for (let i = 0; i < coords.length - 1; i++) {
        const ptA = coords[i];
        const ptB = coords[i + 1];
        const midLat = (ptA[1] + ptB[1]) / 2;
        const dx = (ptB[0] - ptA[0]) * 111000 * Math.cos((midLat * Math.PI) / 180);
        const dy = (ptB[1] - ptA[1]) * 111000;
        const dist = Math.sqrt(dx * dx + dy * dy);
        totalDist += dist;
        segmentLengths.push(totalDist);
      }

      if (totalDist > 800) {
        allRoutes.push({
          coords,
          segmentLengths,
          totalDist,
          name: feature.properties?.name || '省际高速干线'
        });
      }
    };

    if (geom.type === 'LineString') {
      parseRoute(geom.coordinates);
    } else if (geom.type === 'MultiLineString') {
      geom.coordinates.forEach(coords => parseRoute(coords));
    }
  });

  if (allRoutes.length === 0) return;

  // 按线路长度降序排列
  allRoutes.sort((a, b) => b.totalDist - a.totalDist);

  // 关键修复：智能选线逻辑！防止 minDistance 设置过高导致候选线路骤减为 1~2 条而使所有车辆挤成一堆
  // 保证候选线路池数量至少覆盖车辆数，确保车辆全省均匀分布
  const totalVehicles = Math.min(trafficConfig.vehicleCount, 40);
  let candidateRoutes = allRoutes.filter(r => r.totalDist >= trafficConfig.minDistance * 0.3);
  if (candidateRoutes.length < totalVehicles) {
    candidateRoutes = allRoutes.slice(0, Math.max(totalVehicles, 20));
  }

  const hazardPlates = ['鄂A·H8921', '鄂A·H3329', '鄂F·H7712', '鄂B·H9021', '鄂D·H5518', '鄂C·H1289', '鄂E·H6610'];
  const hazardCargos = ['液氨 (3类危化品)', '液化石油气 (LPG)', '汽油 (高危易燃)', '柴油运输', '液氯 (危化品)'];
  
  const passengerPlates = ['鄂A·K3512', '鄂A·K9982', '鄂F·K1209', '鄂D·K8812', '鄂C·K5531', '鄂E·K7740'];
  const passengerRoutes = ['武汉 ➔ 宜昌', '武汉 ➔ 襄阳', '黄冈 ➔ 武汉', '荆州 ➔ 武汉', '十堰 ➔ 襄阳'];

  const touristPlates = ['鄂F·T9918', '鄂A·T8823', '鄂E·T6612', '鄂H·T3390', '鄂C·T1120'];
  const touristRoutes = ['神农架专线', '武当山专线', '三峡大坝专线', '恩施大峡谷线'];

  const lkywCategories = ['hazard', 'passenger', 'tourist'];

  for (let i = 0; i < totalVehicles; i++) {
    // 均匀分散分配到全省不同的主干道线路上，防止重叠
    const routeIndex = i % candidateRoutes.length;
    const route = candidateRoutes[routeIndex];
    const category = lkywCategories[i % 3];

    let plate, cargo, speed, dotColor;
    if (category === 'hazard') {
      plate = hazardPlates[i % hazardPlates.length];
      cargo = hazardCargos[i % hazardCargos.length];
      speed = 78 + Math.floor(Math.random() * 14);
      dotColor = '#ff3344';
    } else if (category === 'passenger') {
      plate = passengerPlates[i % passengerPlates.length];
      cargo = passengerRoutes[i % passengerRoutes.length];
      speed = 85 + Math.floor(Math.random() * 12);
      dotColor = '#00ffaa';
    } else {
      plate = touristPlates[i % touristPlates.length];
      cargo = touristRoutes[i % touristRoutes.length];
      speed = 80 + Math.floor(Math.random() * 10);
      dotColor = '#00e5ff';
    }

    // 关键修复：黄金分割错开初始起点，即使在同一条线路上也绝不重叠
    const staggerRatio = ((i * 0.382 + (i / totalVehicles)) % 1.0);
    const startDist = staggerRatio * route.totalDist;
    const travelTime = 2.0 + Math.random() * 1.5;
    const vehicleSpeed = route.totalDist / travelTime;

    const isReverse = i % 2 === 1;

    const canvas = createVehicleBillboardCanvas(category, plate, speed);

    const initialPos = getPointAtDistance(route, startDist);
    if (!initialPos) continue;

    const billboard = lkywBillboardCollection.add({
      position: initialPos,
      image: canvas,
      scale: 0.65,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      heightReference: Cesium.HeightReference.NONE,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    });

    const point = lkywPointCollection.add({
      position: initialPos,
      color: Cesium.Color.fromCssColorString(dotColor),
      pixelSize: 4.0,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 1.0,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    });

    lkywVehicles.push({
      billboard,
      point,
      category,
      plate,
      cargo,
      speed,
      route,
      currentDist: startDist,
      speedVal: vehicleSpeed,
      direction: isReverse ? -1 : 1
    });
  }

  // 应用类别筛选
  toggleVehicleFilter(trafficConfig.activeCategory);

  viewer.scene.primitives.add(lkywBillboardCollection);
  viewer.scene.primitives.add(lkywPointCollection);
}

function initTrafficVehiclesFromGeoJson(geojson) {
  if (!viewer || !geojson || !geojson.features) return;

  if (trafficPointCollection) {
    viewer.scene.primitives.remove(trafficPointCollection);
    trafficPointCollection = null;
  }
  if (trafficAnimationRemoveListener) {
    trafficAnimationRemoveListener();
    trafficAnimationRemoveListener = null;
  }

  trafficVehicles = [];
  trafficPointCollection = new Cesium.PointPrimitiveCollection();

  const allRoutes = [];

  geojson.features.forEach(feature => {
    const geom = feature.geometry;
    if (!geom) return;

    const addRoute = (coords) => {
      if (!coords || coords.length < 2) return;
      const segmentLengths = [0];
      let totalDist = 0;

      for (let i = 0; i < coords.length - 1; i++) {
        const ptA = coords[i];
        const ptB = coords[i + 1];
        const midLat = (ptA[1] + ptB[1]) / 2;
        const dx = (ptB[0] - ptA[0]) * 111000 * Math.cos((midLat * Math.PI) / 180);
        const dy = (ptB[1] - ptA[1]) * 111000;
        const dist = Math.sqrt(dx * dx + dy * dy);
        totalDist += dist;
        segmentLengths.push(totalDist);
      }

      if (totalDist > 800) {
        allRoutes.push({
          coords,
          segmentLengths,
          totalDist
        });
      }
    };

    if (geom.type === 'LineString') {
      addRoute(geom.coordinates);
    } else if (geom.type === 'MultiLineString') {
      geom.coordinates.forEach(coords => addRoute(coords));
    }
  });

  if (allRoutes.length === 0) return;

  // 背景车流按长度排序
  allRoutes.sort((a, b) => b.totalDist - a.totalDist);

  let candidateRoutes = allRoutes.filter(r => r.totalDist >= trafficConfig.minDistance * 0.3);
  if (candidateRoutes.length < 15) {
    candidateRoutes = allRoutes.slice(0, Math.max(30, allRoutes.length));
  }

  candidateRoutes.forEach((route, routeIndex) => {
    const vehicleCount = route.totalDist > 20000 ? 5 : (route.totalDist > 8000 ? 3 : 2);

    for (let k = 0; k < vehicleCount; k++) {
      const isReverse = (routeIndex + k) % 2 === 1;

      // 关键分配：按全省在途占比分配点位类型 (22%危化品赤红, 48%班线客车翠绿, 30%旅游包车青蓝)
      const randCat = Math.random();
      let category = 'passenger';
      let dotColor = '#00E676'; // 绿

      if (randCat < 0.22) {
        category = 'hazard';
        dotColor = '#FF2D55'; // 大红警示点
      } else if (randCat < 0.70) {
        category = 'passenger';
        dotColor = '#00E676'; // 翠绿
      } else {
        category = 'tourist';
        dotColor = '#00B0FF'; // 青蓝
      }

      const initialColor = Cesium.Color.fromCssColorString(dotColor).withAlpha(0.85);
      const pixelSize = category === 'hazard' ? 4.0 : 3.0;

      const startDist = ((k / vehicleCount) * 0.8 + Math.random() * 0.2) * route.totalDist;
      const travelTime = 1.5 + Math.random() * 1.0;
      const speed = route.totalDist / travelTime;

      const initialPos = getPointAtDistance(route, startDist);
      if (!initialPos) continue;

      const pt = trafficPointCollection.add({
        position: initialPos,
        color: initialColor,
        pixelSize: pixelSize,
        outlineColor: Cesium.Color.fromCssColorString(dotColor).withAlpha(0.3),
        outlineWidth: 1.0,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      });

      trafficVehicles.push({
        primitive: pt,
        route: route,
        category: category,
        dotColor: dotColor,
        currentDist: startDist,
        speed: speed,
        direction: isReverse ? -1 : 1
      });
    }
  });

  // 初始化完成后立即应用一次当前分类筛选状态
  toggleVehicleFilter(activeVehicleFilter.value);

  viewer.scene.primitives.add(trafficPointCollection);

  let lastTime = performance.now();
  trafficAnimationRemoveListener = viewer.scene.preRender.addEventListener(() => {
    const now = performance.now();
    const dt = Math.min((now - lastTime) / 1000.0, 0.1);
    lastTime = now;

    const currentSpeedFactor = trafficConfig.speedFactor;

    for (let i = 0; i < trafficVehicles.length; i++) {
      const v = trafficVehicles[i];
      v.currentDist += v.direction * (v.speed * currentSpeedFactor) * dt;
      if (v.currentDist > v.route.totalDist) {
        v.currentDist = 0;
      } else if (v.currentDist < 0) {
        v.currentDist = v.route.totalDist;
      }
      const pos = getPointAtDistance(v.route, v.currentDist);
      if (pos) {
        v.primitive.position = pos;
      }
    }

    if (lkywVehicles && lkywVehicles.length > 0) {
      for (let i = 0; i < lkywVehicles.length; i++) {
        const lv = lkywVehicles[i];
        lv.currentDist += lv.direction * (lv.speedVal * currentSpeedFactor) * dt;
        if (lv.currentDist > lv.route.totalDist) {
          lv.currentDist = 0;
        } else if (lv.currentDist < 0) {
          lv.currentDist = lv.route.totalDist;
        }
        const lpos = getPointAtDistance(lv.route, lv.currentDist);
        if (lpos) {
          lv.billboard.position = lpos;
          lv.point.position = lpos;
        }
      }
    }

    // 强行触发帧渲染，防止按需渲染（requestRenderMode）下场景动画暂停
    if (viewer && viewer.scene && viewer.scene.requestRenderMode) {
      viewer.scene.requestRender();
    }
  });
}


function getPointAtDistance(route, dist) {
  const lengths = route.segmentLengths;
  const coords = route.coords;
  if (!lengths || lengths.length < 2) return null;

  const d = Math.max(0, Math.min(dist, route.totalDist));

  let segIdx = 0;
  for (let i = 0; i < lengths.length - 1; i++) {
    if (d >= lengths[i] && d <= lengths[i + 1]) {
      segIdx = i;
      break;
    }
  }

  const segStartDist = lengths[segIdx];
  const segEndDist = lengths[segIdx + 1];
  const segLen = segEndDist - segStartDist;
  const t = segLen > 0 ? (d - segStartDist) / segLen : 0;

  const pA = coords[segIdx];
  const pB = coords[segIdx + 1];

  const lng = pA[0] + (pB[0] - pA[0]) * t;
  const lat = pA[1] + (pB[1] - pA[1]) * t;

  return Cesium.Cartesian3.fromDegrees(lng, lat, 10);
}

function updateTruckSequence(phaseIndex, pointId = '') {
  if (!viewer) return
  
  const targetModelId = phaseToModelMap[phaseIndex] || null
  
  // 1. 物理显隐状态：通过控制 alpha 或 scale 来实现，而不是 entity.show，因为我们要预加载
  // 这里我们已经通过 CallbackProperty 控制了 scale

  // 2. 动画触发逻辑：
  // - 如果物理模型发生变化（如从正常行驶切到事故模型），必须触发播放
  // - 如果物理模型没变（如从事故发生切到次生灾害），则保持当前帧（不重播），满足用户“在最后一帧静止”的需求
  const isModelChanged = targetModelId !== currentActiveModelId
  const isInitialSwitch = (phaseIndex <= 1 && lastPhaseIndex <= 1 && phaseIndex !== lastPhaseIndex)
  
  if (targetModelId) {
    truckEntities.forEach(entity => {
      const isTarget = entity.id === targetModelId
      if (isTarget) {
        entity.show = true
      } else {
        entity.show = !modelsReadyStatus[entity.id]
      }
    })
    
    // 无人机阶段（阶段6、7、8）不播放动画，保持事故发生后的最后一帧
    if (phaseIndex < 6 && (isModelChanged || isInitialSwitch)) {
      const entity = truckEntities.find(e => e.id === targetModelId)
      if (entity) {
        const durationMap = { 1: 3, 2: 2, 3: 3, 4: 3, 5: 3 }
        const duration = durationMap[phaseIndex] || 3
        playEntityAnimation(entity, false, duration)
      }
    }
  }
  
  currentActiveModelId = targetModelId
  lastPhaseIndex = phaseIndex

  const isTruckFocus = pointId === 'accident_blue' || props.focusedPointId === 'accident_blue';

  const isBigFire = (phaseIndex === 5);
  const smokeScaleBase = isBigFire ? 2.8 : 1.0;
  const fireScaleBase = isBigFire ? 2.0 : 1.0;

  if (smokeParticle) {
    // 只有在聚焦该点且阶段 >= 3 时才显示，防止回退时粒子残留
    smokeParticle.show = isTruckFocus && (phaseIndex >= 3);
    smokeParticle.startScale = 0.5 * smokeScaleBase;
    smokeParticle.endScale = 2.0 * smokeScaleBase;
    smokeParticle.emissionRate = (phaseIndex >= 3) ? 60.0 : 0.0;
  }
  if (fireParticle) {
    // 只有在聚焦该点且阶段 >= 4 时才显示
    fireParticle.show = isTruckFocus && (phaseIndex >= 4);
    fireParticle.startScale = 0.3 * fireScaleBase;
    fireParticle.endScale = 1.2 * fireScaleBase;
    fireParticle.emissionRate = (phaseIndex >= 4) ? 80.0 : 0.0;
  }
}

// 油罐车模型序列更新函数
function updateTankerSequence(phaseIndex, pointId = '') {
  if (!viewer) return
  
  const targetModelId = tankerPhaseToModelMap[phaseIndex] || null

  const isModelChanged = targetModelId !== currentActiveTankerModelId
  const isInitialSwitch = (phaseIndex <= 1 && lastPhaseIndex <= 1 && phaseIndex !== lastPhaseIndex)

  if (targetModelId && (isModelChanged || isInitialSwitch)) {
    tankerEntities.forEach(entity => {
      const isTarget = entity.id === targetModelId
      if (isTarget) {
        entity.show = true
      } else {
        entity.show = !modelsReadyStatus[entity.id]
      }
    })
    const entity = tankerEntities.find(e => e.id === targetModelId)
    if (entity) {
      const durationMap = { 1: 3, 2: 2, 3: 3, 4: 3, 5: 3 }
      const duration = durationMap[phaseIndex] || 3
      playEntityAnimation(entity, false, duration)
    }
  }
  
  currentActiveTankerModelId = targetModelId
  lastTankerPhaseIndex = phaseIndex

  // 全时段就绪：泄露与弥漫效果根据focusedPointId决定是否显示
  const isTankerFocus = pointId === 'accident_red' || props.focusedPointId === 'accident_red';

  if (leakParticle) {
    // 只有在聚焦该点且阶段 >= 3 时才显示
    leakParticle.show = isTankerFocus && (phaseIndex >= 3);
    // 阶段3（泄露）开始产生
    leakParticle.emissionRate = (phaseIndex >= 3) ? 45.0 : 0.0; 
  }
  
  if (diffusionParticle) {
    // 只有在聚焦该点且阶段 >= 4 时才显示
    diffusionParticle.show = isTankerFocus && (phaseIndex >= 4);
    // 阶段4（弥漫）开始产生，阶段5（扩散）显著增强
    if (phaseIndex === 4) {
      diffusionParticle.emissionRate = 100.0; // 提升初始浓度
    } else if (phaseIndex >= 5) {
      diffusionParticle.emissionRate = 180.0; // 显著增强，提供大范围浓烈雾气效果
    } else {
      diffusionParticle.emissionRate = 0.0;
    }
  }
}

function playEntityAnimation(entity, loop = false, duration = 0, speedMultiplier = 1.0) {
  if (!viewer || !entity) return;

  const tryPlay = (attemptsLeft) => {
    if (attemptsLeft <= 0) {
      console.warn(`[Cesium] 播放动画超时，模型未能及时就绪: ${entity.id}`);
      return;
    }

    try {
      let p = primitiveCache.get(entity.id);
      if (!p) p = findModelPrimitive(viewer.scene.primitives, entity);
      if (!p) p = findModelPrimitive(viewer.scene.groundPrimitives, entity);

      // 检查模型是否完全加载就绪
      const isReady = p && (
        p.ready || 
        (p.readyPromise && p.readyPromise.state === 'fulfilled') || 
        p._ready || 
        (p.model && p.model.ready)
      );

      if (p && isReady && p.activeAnimations && typeof p.activeAnimations.addAll === 'function') {
        console.log(`[Cesium] 成功找到模型且已就绪，开始强制播放全轨道动画: ${entity.id}`);
        try {
          p.activeAnimations.removeAll();
          const options = {
            loop: loop ? Cesium.ModelAnimationLoop.REPEAT : Cesium.ModelAnimationLoop.NONE,
            multiplier: speedMultiplier, // 默认倍速
            startTime: viewer.clock.currentTime,
            removeOnStop: false // 停止时保留在最后一帧状态
          };
          
          // 调用 addAll 强制激活模型内所有的 animation tracks
          const addedAnims = p.activeAnimations.addAll(options);
          
          // 如果用户指定了明确的 duration，我们动态计算 speedMultiplier，使动画恰好在 duration 时间内播完
          if (duration > 0 && addedAnims && addedAnims.length > 0) {
            addedAnims.forEach(anim => {
              if (anim.startTime && anim.stopTime) {
                const nativeDuration = Cesium.JulianDate.secondsDifference(anim.stopTime, anim.startTime);
                if (nativeDuration > 0) {
                  anim.multiplier = nativeDuration / duration;
                  // 更新停止时间，使其准确在 duration 后停止
                  anim.stopTime = Cesium.JulianDate.addSeconds(anim.startTime, duration, new Cesium.JulianDate());
                }
              }
            });
            console.log(`[Cesium] 动画已调整: 目标时长 = ${duration}s`);
          } else if (duration > 0) {
            // 回退方案：如果没有成功读取到动画时间，按原逻辑强行截断
            p.activeAnimations.removeAll();
            options.stopTime = Cesium.JulianDate.addSeconds(viewer.clock.currentTime, duration, new Cesium.JulianDate());
            p.activeAnimations.addAll(options);
          }
        } catch (animError) {
          console.warn('播放动画时出现警告:', animError.message);
        }
      } else {
        // 如果未找到或未就绪，等待 200ms 后重试
        setTimeout(() => tryPlay(attemptsLeft - 1), 200);
      }
    } catch (error) {
      console.warn('查找实体时出现警告:', error.message);
    }
  };

  // 启动轮询检查，最多重试 50 次 (约 10 秒)
  tryPlay(50);
}
// 👇 注意这里，我帮你把 isVisibleFn 参数加进来了！
function createLightFOV(viewer, id, lng, lat, height, heading, pitch, angle = 20, maxRange = 80, isVisibleFn) {
  const segments = 64; 

  // 1. 获取探头的世界坐标和地表法线（向上的向量）
  const origin = Cesium.Cartesian3.fromDegrees(lng, lat, height);
  const surfaceNormal = Cesium.Ellipsoid.WGS84.geodeticSurfaceNormal(origin);

  // 2. 根据 Heading, Pitch, Roll 计算局部旋转矩阵
  const hpr = new Cesium.HeadingPitchRoll(
    Cesium.Math.toRadians(heading),
    Cesium.Math.toRadians(pitch),
    0
  );
  // 获取局部到世界坐标的变换矩阵
  const transform = Cesium.Transforms.headingPitchRollToFixedFrame(origin, hpr);

  const vertices = [];
  
  // 顶点0：探头原点（在相对坐标系中就是 0,0,0）
  vertices.push(0, 0, 0);

  // 计算视场半角的三角函数
  const halfAngle = Cesium.Math.toRadians(angle);
  const cosA = Math.cos(halfAngle);
  const sinA = Math.sin(halfAngle);

  // 3. 生成圆锥射线，并计算与地面的精准交点
  for (let i = 0; i < segments; i++) {
    const phi = (i / segments) * Math.PI * 2;
    
    // 生成局部坐标系下的射线方向 (Cesium 默认朝向是 +X 轴)
    const dirLocal = new Cesium.Cartesian3(
      cosA,
      sinA * Math.cos(phi),
      sinA * Math.sin(phi)
    );

    // 将局部射线方向转换为世界方向向量
    const dirWorld = Cesium.Matrix4.multiplyByPointAsVector(transform, dirLocal, new Cesium.Cartesian3());
    Cesium.Cartesian3.normalize(dirWorld, dirWorld);

    // 核心算法：射线与地面平面的相交计算
    const dot = Cesium.Cartesian3.dot(dirWorld, surfaceNormal);
    
    let t = maxRange; // 默认最远射程
    
    // dot < 0 表示射线是指向地面的；如果 >= 0 则是射向天空，按最大射程截断
    if (dot < -0.00001) { 
      // 计算射线到达地面的距离
      const distanceToGround = -height / dot;
      // 取 地面距离 和 最大射程 的最小值，防止斜射时无限延伸
      t = Math.min(distanceToGround, maxRange);
    }

    // 计算相对原点的偏移量，避免 WebGL 渲染大坐标抖动
    const relativeHitPoint = Cesium.Cartesian3.multiplyByScalar(dirWorld, t, new Cesium.Cartesian3());
    
    vertices.push(relativeHitPoint.x, relativeHitPoint.y, relativeHitPoint.z);
  }

  // 4. 构建索引
  const indices = [];
  for (let i = 0; i < segments; i++) {
    const next = (i + 1) % segments;
    indices.push(0, i + 1, next + 1);
  }

  // 5. 组装几何体
  const geometry = new Cesium.Geometry({
    attributes: {
      position: new Cesium.GeometryAttribute({
        componentDatatype: Cesium.ComponentDatatype.DOUBLE,
        componentsPerAttribute: 3,
        values: new Float64Array(vertices)
      })
    },
    indices: new Uint16Array(indices),
    primitiveType: Cesium.PrimitiveType.TRIANGLES,
    boundingSphere: Cesium.BoundingSphere.fromVertices(vertices)
  });

  const instance = new Cesium.GeometryInstance({
    geometry: geometry,
    id: id,
    // 将偏移量矩阵赋给实例，彻底解决画面抖动问题
    modelMatrix: Cesium.Matrix4.fromTranslation(origin),
    attributes: {
      color: Cesium.ColorGeometryInstanceAttribute.fromColor(
        Cesium.Color.CYAN.withAlpha(0.25)
      )
    }
  });

  // 👇👇👇 核心修改：提前计算并锁死图元出生时的显示状态
  // 👇👇👇 核心修改：提前计算并锁死图元出生时的显示状态
  const initialShow = typeof isVisibleFn === 'function' ? isVisibleFn() : true;

  const primitive = viewer.scene.primitives.add(
    new Cesium.Primitive({
      geometryInstances: instance,
      asynchronous: false, 
      compressVertices: false,
      show: initialShow, // 👈 锁死初始状态
      appearance: new Cesium.PerInstanceColorAppearance({
        flat: true, 
        translucent: true,
        closed: false 
      })
    })
  );

  // 👇👇👇 进阶版动态监听器：解决按需渲染不刷新的问题
  if (typeof isVisibleFn === 'function') {
    let lastShowState = initialShow; // 缓存上一次的状态
    
    viewer.scene.preUpdate.addEventListener(() => {
      const shouldShow = isVisibleFn();
      
      // 只有在状态发生【切换】的那一瞬间，才执行更新
      if (shouldShow !== lastShowState) {
        primitive.show = shouldShow;
        lastShowState = shouldShow;
        
        // 🚨 终极保险：如果你开启了按需渲染，强制 Cesium 重绘一帧，让光斑瞬间蹦出来！
        if (viewer.scene.requestRenderMode) {
          viewer.scene.requestRender();
        }
      }
    });
  }
  
  return primitive;
}
function replayCurrentPhase() {
  if (currentActiveModelId) {
    const entity = truckEntities.find(e => e.id === currentActiveModelId)
    if (entity) playEntityAnimation(entity)
  }
}

function addEventEntities() {
  // 接入 6 个 light.glb 3D灯光模型
  // 接入 6 个 light.glb 3D灯光模型
  // 接入 6 个 light.glb 3D灯光模型
  
lights.forEach((l) => {
if (['light1', 'light2', 'light3'].includes(l.id)) {
    
    const heightOffset = 8.0; 
    const pitchAngle = -45;   

    let headingOffset = 0; 
    let fovAngle = 22;     
    let maxRange = 100;    

    if (l.id === 'light1') {
      headingOffset = -150;  
      fovAngle = 20;       
      maxRange = 80;       
    }
    if (l.id === 'light2') {
      headingOffset = 0; 
      fovAngle = 35;       
      maxRange = 250;      
    }
    if (l.id === 'light3') {
      headingOffset = 180;   
      fovAngle = 35;       
      maxRange = 200;      
    }

    createLightFOV(
      viewer,
      `${l.id}-fov`,
      Number(l.lng),
      Number(l.lat),
      Number(l.height) + heightOffset,
      Number(l.heading) + headingOffset,  
      pitchAngle,                         
      fovAngle, 
      maxRange, 
      
      // 👇👇👇 修改后的阶段截断控制逻辑
      () => {
        // 🎯 核心修改：使用 >= 2。代表从第 2 阶段开始，以及后面的 3、4、5... 阶段，都会一直显示！
        if (Number(props.activePhaseIndex) >= 2) { 
          return true; // 显示视场
        }

        // 如果是 0 或 1 阶段，就会返回 false 保持隐藏
        return false; 
      }
      // 👆👆👆
    );
  }
  if (l.id === 'light6') return;



  // =====================================
  // 1. light1 light2 light3 添加感知视场
  // ====================================

  // =====================================
  // 2. 原路灯模型
  // =====================================


  viewer.entities.add({

    id:`${l.id}-glb-entity`,

    name:`事故现场灯光模型-${l.id}`,


    show:
    new Cesium.CallbackProperty(
      ()=>l.show,
      false
    ),


    position:
    new Cesium.CallbackProperty(()=>{


      return Cesium.Cartesian3.fromDegrees(

        Number(l.lng),

        Number(l.lat),

        Number(l.height)

      );


    },false),



    orientation:
    new Cesium.CallbackProperty(()=>{


      const position =
      Cesium.Cartesian3.fromDegrees(

        Number(l.lng),

        Number(l.lat),

        Number(l.height)

      );


      const hpr =
      new Cesium.HeadingPitchRoll(

        Cesium.Math.toRadians(
          Number(l.heading)
        ),

        Cesium.Math.toRadians(
          Number(l.pitch)
        ),

        Cesium.Math.toRadians(
          Number(l.roll)
        )

      );


      return Cesium.Transforms.headingPitchRollQuaternion(
        position,
        hpr
      );


    },false),


    model:{


      uri:'/Dashboard/models/light.glb',


      scale:
      new Cesium.CallbackProperty(
        ()=>l.scale,
        false
      ),


      heightReference:
      Cesium.HeightReference.CLAMP_TO_GROUND


    }


  });






  // =====================================
  // 3. light1-3 到基站通信链路
  // =====================================


  if(['light1','light2','light3'].includes(l.id)){


    viewer.entities.add({

      id:`line-link-from-${l.id}-to-jizhan`,


      name:`数据传输链路:${l.id}->5G基站`,


      show:
      new Cesium.CallbackProperty(()=>{


        return (

          currentScene.value==='truck'

          &&

          jizhanAdjust.show

          &&

          l.show

        );


      },false),



      polyline:{


        positions:
        new Cesium.CallbackProperty(()=>{


          const jizhanTop =
          getModelTopPosition(

            jizhanAdjust.lng,

            jizhanAdjust.lat,

            jizhanAdjust.height,

            jizhanAdjust.heading,

            jizhanAdjust.pitch,

            jizhanAdjust.roll,

            JIZHAN_TOP_OFFSET

          );



          const lightTop =
          getModelTopPosition(

            l.lng,

            l.lat,

            l.height,

            l.heading,

            l.pitch,

            l.roll,

            LIGHT_TOP_OFFSET

          );



          return [

            lightTop,

            jizhanTop

          ];


        },false),



        width:3.0,


        material:
        new DynamicFlowMaterialProperty({

          color:Cesium.Color.CYAN,

          speed:3.5,

          repeat:8.0

        })


      }


    });


  }



});
  // 📡 接入 jizhan.glb 3D 5G通信基站模型 (货车追尾事故现场)
  viewer.entities.add({
    id: 'jizhan-glb-entity',
    name: '货车追尾现场5G通信基站模型',
    show: new Cesium.CallbackProperty(() => {
      return currentScene.value === 'truck' && jizhanAdjust.show;
    }, false),
    position: new Cesium.CallbackProperty(() => {
      return Cesium.Cartesian3.fromDegrees(Number(jizhanAdjust.lng), Number(jizhanAdjust.lat), Number(jizhanAdjust.height));
    }, false),
    orientation: new Cesium.CallbackProperty(() => {
      const position = Cesium.Cartesian3.fromDegrees(Number(jizhanAdjust.lng), Number(jizhanAdjust.lat), Number(jizhanAdjust.height));
      const hpr = new Cesium.HeadingPitchRoll(
        Cesium.Math.toRadians(Number(jizhanAdjust.heading)),
        Cesium.Math.toRadians(Number(jizhanAdjust.pitch)),
        Cesium.Math.toRadians(Number(jizhanAdjust.roll))
      );
      return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
    }, false),
    model: {
      uri: '/Dashboard/models/jizhan.glb',
      scale: new Cesium.CallbackProperty(() => jizhanAdjust.scale, false),
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    }
  });

// 👇👇👇【最终修正：严格贴合物理高度的感知视场角】👇👇👇
  
  focusAreaEntity = viewer.entities.add({
    id: 'event-area',
    show: false,
    position: Cesium.Cartesian3.fromDegrees(114.35, 30.55, 0),
    ellipse: {
      semiMinorAxis: 150000, semiMajorAxis: 190000, material: toCesiumColor('#00e5ff', 0.06),
      outline: true, outlineColor: toCesiumColor('#00e5ff', 0.32), height: 0,
    },
  })

  // 创建高精度绿色救援装备图标
  const rescueSvgIcon = `data:image/svg+xml;utf8,` + encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="48" height="48">
      <polygon points="50,5 95,30 95,75 50,98 5,75 5,30" fill="rgba(0, 229, 90, 0.18)" stroke="#00e575" stroke-width="6"/>
      <path d="M25,50 L40,50 M60,50 L75,50 M50,25 L50,40 M50,60 L50,75 M35,35 L65,65 M35,65 L65,35" stroke="#00e575" stroke-width="5"/>
      <circle cx="50" cy="50" r="10" fill="#00e575"/>
    </svg>
  `);

  rescueMarkerEntity = viewer.entities.add({
    id: 'rescue-marker',
    position: new Cesium.CallbackProperty(() => {
      return Cesium.Cartesian3.fromDegrees(rescueCoords.lng, rescueCoords.lat, rescueCoords.height);
    }, false),
    billboard: {
      image: rescueSvgIcon,
      width: 24,
      height: 24,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM
    },
    show: false
  });

  popupEntity = viewer.entities.add({
    id: 'event-popup',
    position: Cesium.Cartesian3.fromDegrees(114.35, 30.55, 500),
    label: {
      backgroundColor: toCesiumColor('#061628', 0.88), backgroundPadding: new Cesium.Cartesian2(16, 12),
      pixelOffset: new Cesium.Cartesian2(0, -60), disableDepthTestDistance: Number.POSITIVE_INFINITY,
      horizontalOrigin: Cesium.HorizontalOrigin.CENTER, verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      style: Cesium.LabelStyle.FILL, scale: 0.96,
    },
  })

  connectionLineEntity = viewer.entities.add({
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        if (!connectionLineEntity || !connectionLineEntity.show) return []
        const pos = popupEntity.position.getValue(viewer.clock.currentTime)
        if (!pos) return []
        const carto = Cesium.Cartographic.fromCartesian(pos)
        const groundPos = Cesium.Cartesian3.fromDegrees(
          Cesium.Math.toDegrees(carto.longitude),
          Cesium.Math.toDegrees(carto.latitude),
          0
        )
        return [groundPos, pos]
      }, false),
      width: 3,
      material: Cesium.Color.CYAN.withAlpha(0.7),
      show: false
    }
  })

  Object.values(scenarioPoints).filter(p => p.id.startsWith('accident_')).forEach(point => {
    let positionCallback;
    if (point.id === 'accident_blue') {
      positionCallback = new Cesium.CallbackProperty(() => {
        return Cesium.Cartesian3.fromDegrees(Number(truckPointAdjust.lng) || point.longitude, Number(truckPointAdjust.lat) || point.latitude, 0);
      }, false);
    } else if (point.id === 'accident_red') {
      positionCallback = new Cesium.CallbackProperty(() => {
        return Cesium.Cartesian3.fromDegrees(Number(tankerPointAdjust.lng) || point.longitude, Number(tankerPointAdjust.lat) || point.latitude, 0);
      }, false);
    } else {
      positionCallback = Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, 0);
    }
    
    viewer.entities.add({
      id: `marker-${point.id}`,
      position: positionCallback,
      point: {
        pixelSize: 10,
        color: Cesium.Color.fromCssColorString(point.color),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })

    // 添加波浪闪烁效果
    const waveColor = Cesium.Color.fromCssColorString(point.color);
    viewer.entities.add({
      id: `wave-${point.id}`,
      position: positionCallback,
      point: {
        pixelSize: new Cesium.CallbackProperty(() => {
          const t = (Date.now() % 1500) / 1500;
          return 10 + t * 40; // 从 10 像素扩展到 50 像素
        }, false),
        color: Cesium.Color.TRANSPARENT, // 内部透明，仅保留外圈
        outlineColor: new Cesium.CallbackProperty(() => {
          const t = (Date.now() % 1500) / 1500;
          return waveColor.withAlpha(1.0 - Math.pow(t, 1.2)); // 调整透明度衰减曲线
        }, false),
        outlineWidth: 3, // 增加线宽，看起来是一圈明显的波浪
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
  })

  truckModelConfigs.forEach((config) => {
    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false,
      position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(Number(truckAdjust.lng)||0, Number(truckAdjust.lat)||0, Number(truckAdjust.height)||0), false),
      orientation: new Cesium.CallbackProperty(() => {
        const position = Cesium.Cartesian3.fromDegrees(Number(truckAdjust.lng)||0, Number(truckAdjust.lat)||0, Number(truckAdjust.height)||0);
        const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(truckAdjust.heading)||0), 0, 0);
        return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
      }, false),
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => {
          const targetModelId = phaseToModelMap[props.activePhaseIndex]
          // 始终保持一个微小但存在的比例，配合 minimumPixelSize 强制加载
          if (config.id === targetModelId) return truckAdjust.scale
          return 0.001
        }, false),
        minimumPixelSize: 1, // 关键：强制 Cesium 始终渲染该模型，从而触发加载
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, // 使用 Cesium 原生贴地
        // 关闭原生动画循环，交由 updateTruckSequence 和 playEntityAnimation 手动控制只播一次并定格
        runAnimations: false
      }
    })
    entity.show = true // 强制开启显示以触发加载
    truckEntities.push(entity)
  })

  tankerModelConfigs.forEach((config) => {
    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false,
      position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(Number(tankerAdjust.lng)||0, Number(tankerAdjust.lat)||0, Number(tankerAdjust.height)||0), false),
      orientation: new Cesium.CallbackProperty(() => {
        const position = Cesium.Cartesian3.fromDegrees(Number(tankerAdjust.lng)||0, Number(tankerAdjust.lat)||0, Number(tankerAdjust.height)||0);
        const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(tankerAdjust.heading)||0), 0, 0);
        return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
      }, false),
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => {
          const targetModelId = tankerPhaseToModelMap[props.activePhaseIndex]
          if (config.id === targetModelId) return tankerAdjust.scale
          return 0.001
        }, false),
        minimumPixelSize: 1, // 关键：强制加载
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, // 使用 Cesium 原生贴地
        // 关闭原生动画循环，手动控制
        runAnimations: false
      }
    })
    entity.show = true
    tankerEntities.push(entity)
  })

  // 初始化无人机模型（用于货车追尾现场的无人装备出动阶段）
  // 初始化无人机模型（用于货车追尾现场的无人装备出动阶段）
  uavModelConfigs.forEach((config) => {
    console.log(`[Cesium] 正在初始化无人机实体: ${config.id}, 路径: ${config.uri}`);

    const uavPosition = new Cesium.CallbackProperty(() => {
      // 加上各自的停靠点偏移，形成编队
      const startLng = (Number(uavAdjust.lng) || 113.418173) + (config.lonOffset || 0);
      const startLat = (Number(uavAdjust.lat) || 30.321919) + (config.latOffset || 0);
      const startHeight = Number(uavAdjust.height) || 18.5;

      const targetLng = (Number(truckAdjust.lng) || 113.104833) + (config.lonOffset || 0);
      const targetLat = (Number(truckAdjust.lat) || 30.385469) + (config.latOffset || 0);
      const targetHeight = startHeight; 

      if (props.activePhaseIndex === 6) {
        if (currentMissionDataSource) {
          const entity = currentMissionDataSource.entities.getById('UAV');
          if (entity) {
            const pos = entity.position.getValue(viewer.clock.currentTime);
            if (pos) return pos;
          }
        }
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else if (props.activePhaseIndex < 6) {
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else if (props.activePhaseIndex === 7) {
        if (!phase7StartTime) { phase7StartTime = Date.now(); }
        const elapsed = Date.now() - phase7StartTime;
        const duration = 6000; 
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        const lng = startLng + (targetLng - startLng) * easeT;
        const lat = startLat + (targetLat - startLat) * easeT;
        const height = startHeight + (targetHeight - startHeight) * easeT;
        return Cesium.Cartesian3.fromDegrees(lng, lat, height);
      } else {
        // 阶段 >= 8：无人机围绕事故点做圆周绕飞拍照
        if (!uavOrbitStartTime) { uavOrbitStartTime = Date.now(); }
        const elapsed = Date.now() - uavOrbitStartTime;
        const period = 12000; 
        const rawAngle = (elapsed / period) * 2.0 * Math.PI;
        const baseAngle = Math.min(rawAngle, 2.0 * Math.PI); 
        const angle = baseAngle + (config.angleOffset || 0); // 👈 加上这架无人机的专属相位角
        
        const radiusLng = 0.00055;
        const radiusLat = 0.00045;
        
        // 绕飞中心为纯事故中心点，保证编队完美圆形
        const centerLng = Number(truckAdjust.lng) || 113.104833;
        const centerLat = Number(truckAdjust.lat) || 30.385469;

        const currentLng = centerLng + radiusLng * Math.cos(angle);
        const currentLat = centerLat + radiusLat * Math.sin(angle);

        // 触发多角度照片拍摄状态 (只让 1 号主无人机触发，避免 3 份叠加)
        if (config.id === 'uav_model_move') {
          if (baseAngle >= 0.5 * Math.PI && !capturedPhotos.value[0]) {
            capturedPhotos.value[0] = true; activePhotoIndex.value = 0;
            triggerPhotoAnimation(0, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight));
          }
          if (baseAngle >= 1.0 * Math.PI && !capturedPhotos.value[1]) {
            capturedPhotos.value[1] = true; activePhotoIndex.value = 1;
            triggerPhotoAnimation(1, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight));
          }
          if (baseAngle >= 1.5 * Math.PI && !capturedPhotos.value[2]) {
            capturedPhotos.value[2] = true; activePhotoIndex.value = 2;
            triggerPhotoAnimation(2, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight));
          }
          if (baseAngle >= 2.0 * Math.PI && !capturedPhotos.value[3]) {
            capturedPhotos.value[3] = true; activePhotoIndex.value = 3;
            triggerPhotoAnimation(3, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight));
          }
        }
        return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight);
      }
    }, false);

    const uavOrientation = new Cesium.CallbackProperty(() => {
      const pos = uavPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;

      let headingRad;
      if (props.activePhaseIndex === 6) {
        if (currentMissionDataSource) {
          const mEntity = currentMissionDataSource.entities.getById('UAV');
          if (mEntity) {
            const nextTime = Cesium.JulianDate.addSeconds(viewer.clock.currentTime, 0.5, new Cesium.JulianDate());
            const nextPos = mEntity.position.getValue(nextTime);
            if (nextPos) {
              const cartoCur = Cesium.Cartographic.fromCartesian(pos);
              const cartoNext = Cesium.Cartographic.fromCartesian(nextPos);
              headingRad = Math.PI / 2 - Math.atan2(
                Cesium.Math.toDegrees(cartoNext.latitude) - Cesium.Math.toDegrees(cartoCur.latitude),
                Cesium.Math.toDegrees(cartoNext.longitude) - Cesium.Math.toDegrees(cartoCur.longitude)
              );
            } else {
              headingRad = Cesium.Math.toRadians(Number(uavAdjust.heading) || 18);
            }
          } else {
            headingRad = Cesium.Math.toRadians(Number(uavAdjust.heading) || 18);
          }
        } else {
          headingRad = Cesium.Math.toRadians(Number(uavAdjust.heading) || 18);
        }
      } else if (props.activePhaseIndex >= 8) {
        const targetLng = Number(truckAdjust.lng) || 113.104833;
        const targetLat = Number(truckAdjust.lat) || 30.385469;
        const carto = Cesium.Cartographic.fromCartesian(pos);
        const currentLng = Cesium.Math.toDegrees(carto.longitude);
        const currentLat = Cesium.Math.toDegrees(carto.latitude);
        headingRad = Math.PI / 2 - Math.atan2(targetLat - currentLat, targetLng - currentLng);
      } else {
        headingRad = Cesium.Math.toRadians(Number(uavAdjust.heading) || 18);
      }

      const hpr = new Cesium.HeadingPitchRoll(headingRad, 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(pos, hpr);
    }, false);

    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false,
      position: uavPosition,
      orientation: uavOrientation,
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => uavAdjust.scale > 0 ? uavAdjust.scale : 0.1, false),
        minimumPixelSize: 1, 
        heightReference: Cesium.HeightReference.NONE,
        runAnimations: false
      }
    });

    const UAV_DEBUG_MODE = true; 
    viewer.entities.add({
      id: `line-link-uav-${config.id}-to-jizhan`,
      name: `无人机数据链路`,
      show: new Cesium.CallbackProperty(() => {
        // 🚨 只有当本体显示，且阶段大于8时才显示链路，防止 3个模型生成 6条线
        return Number(props.activePhaseIndex) >= 8 && entity.show;
      }, false),
      polyline: {
        positions: new Cesium.CallbackProperty((time) => {
          if (Number(props.activePhaseIndex) < 8) return [];
          const pos = entity.position.getValue(time);
          if (!pos) return [];

          const targetPos = Cesium.Cartesian3.fromDegrees(tankerPointAdjust.lng, tankerPointAdjust.lat, 0);
          const posCarto = Cesium.Cartographic.fromCartesian(pos);
          const flatPos = Cesium.Cartesian3.fromRadians(posCarto.longitude, posCarto.latitude, 0);
          const distance = Cesium.Cartesian3.distance(flatPos, targetPos);

          if (!UAV_DEBUG_MODE && distance > 200) return [];

          const jizhanTop = getModelTopPosition(
            jizhanAdjust.lng, jizhanAdjust.lat, jizhanAdjust.height,
            jizhanAdjust.heading, jizhanAdjust.pitch, jizhanAdjust.roll, JIZHAN_TOP_OFFSET
          );
          return [pos, jizhanTop];
        }, false),
        width: 3.5,
        material: new DynamicFlowMaterialProperty({
          color: Cesium.Color.ORANGE, 
          speed: 5.5,
          repeat: 5.0
        })
      }
    });
    uavEntities.push(entity);
  });

  // 初始化救援车
  // 初始化救援车（多车道战术编队行驶）
  // 初始化救援车（多车道战术编队行驶 + 现场动态环绕巡逻）
  // 初始化救援车（多车道战术编队行驶 + 现场动态环绕巡逻）
  // 初始化救援车（多车道战术编队行驶 + 丝滑物理转向）
  // 初始化救援车（多车道战术编队行驶 + 丝滑物理转向）
  rescueCarModelConfigs.forEach((config, index) => {
    console.log(`[Cesium] 正在初始化救援车实体: ${config.id}, 路径: ${config.uri}`);

    // 🚨 核心修复：为每辆车独立绑定 Cesium 宇宙时钟锚点，杜绝乱飞闪现
    let phase7StartJulian = undefined;
    let phase8StartJulian = undefined;
    let currentHeading = undefined;
    let lastLocalPhase = -1;

    const rescueCarPosition = new Cesium.CallbackProperty((time) => {
      // 监听用户切换阶段，一旦切换立刻重置时间锚点
      if (lastLocalPhase !== props.activePhaseIndex) {
        phase7StartJulian = Cesium.JulianDate.clone(time);
        phase8StartJulian = Cesium.JulianDate.clone(time);
        lastLocalPhase = props.activePhaseIndex;
      }

      const baseStartLng = Number(rescueCarAdjust.lng) || 113.1073;
      const baseStartLat = Number(rescueCarAdjust.lat) || 30.3849;
      const baseAccidentLng = Number(truckAdjust.lng) || 113.104833;
      const baseAccidentLat = Number(truckAdjust.lat) || 30.385469;
      const startHeight = Number(rescueCarAdjust.height) || -1.5;

      const startLng = baseStartLng + (config.lonOffset || 0);
      const startLat = baseStartLat + (config.latOffset || 0);

      const factor = config.stopFactor || 0.78;
      const targetLng = baseStartLng + factor * (baseAccidentLng - baseStartLng) + (config.lonOffset || 0);
      const targetLat = baseStartLat + factor * (baseAccidentLat - baseStartLat) + (config.latOffset || 0);
      const targetHeight = startHeight; 

      if (props.activePhaseIndex < 7) {
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else if (props.activePhaseIndex === 7) {
        const elapsed = Math.max(0, Cesium.JulianDate.secondsDifference(time, phase7StartJulian));
        const duration = 6.0; // 6秒行驶完毕
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        
        const lng = startLng + (targetLng - startLng) * easeT;
        const lat = startLat + (targetLat - startLat) * easeT;
        return Cesium.Cartesian3.fromDegrees(lng, lat, targetHeight);
      } else {
        const elapsed = Math.max(0, Cesium.JulianDate.secondsDifference(time, phase8StartJulian));
        const period = 20.0; // 绕场一周 20 秒
        
        const dLng = targetLng - baseAccidentLng;
        const dLat = targetLat - baseAccidentLat;
        const radius = Math.sqrt(dLng * dLng + dLat * dLat);
        const startAngle = Math.atan2(dLat, dLng);

        const angle = startAngle + (elapsed / period) * 2.0 * Math.PI;

        const currentLng = baseAccidentLng + radius * Math.cos(angle);
        const currentLat = baseAccidentLat + radius * Math.sin(angle);

        return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, targetHeight);
      }
    }, false);

    const rescueCarOrientation = new Cesium.CallbackProperty((time) => {
      const pos = rescueCarPosition.getValue(time);
      if (!pos) return undefined;
      
      let targetHeadingRad;
      const nextTime = Cesium.JulianDate.addSeconds(time, 0.2, new Cesium.JulianDate());
      const nextPos = rescueCarPosition.getValue(nextTime);
      
      const baseStartLng = Number(rescueCarAdjust.lng) || 113.1073;
      const baseStartLat = Number(rescueCarAdjust.lat) || 30.3849;
      const baseAccidentLng = Number(truckAdjust.lng) || 113.104833;
      const baseAccidentLat = Number(truckAdjust.lat) || 30.385469;
      
      if (nextPos && Cesium.Cartesian3.distance(pos, nextPos) > 0.001) {
        const cartoCur = Cesium.Cartographic.fromCartesian(pos);
        const cartoNext = Cesium.Cartographic.fromCartesian(nextPos);
        const dLng = (cartoNext.longitude - cartoCur.longitude) * Math.cos(cartoCur.latitude);
        const dLat = cartoNext.latitude - cartoCur.latitude;
        
        // 🚨 治愈螃蟹步核心算法：地理真实角度扣除模型自带的 90 度横向偏角，数学化简后刚好等于 -atan2
        targetHeadingRad = -Math.atan2(dLat, dLng);
      } else {
        // 静止状态下的朝向
        const dLng = (baseAccidentLng - baseStartLng) * Math.cos(baseStartLat * Math.PI / 180);
        const dLat = baseAccidentLat - baseStartLat;
        targetHeadingRad = -Math.atan2(dLat, dLng);
      }

      // 🚨 加入平滑阻尼器，消除直角拐弯时的 90 度顿挫闪现，实现完美漂移入弯
      if (currentHeading === undefined) {
        currentHeading = targetHeadingRad;
      } else {
        let diff = targetHeadingRad - currentHeading;
        diff = Math.atan2(Math.sin(diff), Math.cos(diff)); // 归一化，保证方向盘走最短路径
        currentHeading += diff * 0.15; 
      }

      const hpr = new Cesium.HeadingPitchRoll(currentHeading, 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(pos, hpr);
    }, false);

    if (index === 0) {
      sharedTruckRescueCarPosition = rescueCarPosition;
    }

    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: false,
      position: rescueCarPosition,
      orientation: rescueCarOrientation,
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => Number(rescueCarAdjust.scale) || 1.0, false),
        minimumPixelSize: 16, 
        heightReference: Cesium.HeightReference.NONE, 
        runAnimations: true
      }
    });
    rescueCarEntities.push(entity);
  });

  // 初始化油罐车场景的无人机模型
  // 初始化油罐车场景的无人机模型
  uavModelConfigs.forEach((config) => {
    console.log(`[Cesium] 正在初始化油罐车场景无人机实体: ${config.id}, 路径: ${config.uri}`);

    const tankerUavPosition = new Cesium.CallbackProperty(() => {
      const startHeight = Number(tankerUavAdjust.height) || 11.5;
      const targetLng = (Number(tankerPointAdjust.lng) || 114.8945) + (config.lonOffset || 0);
      const targetLat = (Number(tankerPointAdjust.lat) || 30.632161) + (config.latOffset || 0);

      if (props.activePhaseIndex <= 7) {
        let baseLng, baseLat;
        if (sharedTankerRescueCarPosition) {
          const carPos = sharedTankerRescueCarPosition.getValue(viewer.clock.currentTime);
          if (carPos) {
            const cartographic = Cesium.Cartographic.fromCartesian(carPos);
            baseLng = Cesium.Math.toDegrees(cartographic.longitude);
            baseLat = Cesium.Math.toDegrees(cartographic.latitude);
          } else {
            const startLng = Number(tankerRescueCarAdjust.lng) || 114.895791;
            const startLat = Number(tankerRescueCarAdjust.lat) || 30.631361;
            baseLng = startLng + TANKER_STOP_FACTOR * ((Number(tankerPointAdjust.lng) || 114.8945) - startLng);
            baseLat = startLat + TANKER_STOP_FACTOR * ((Number(tankerPointAdjust.lat) || 30.632161) - startLat);
          }
        }
        const midLng = baseLng + 0.5 * (targetLng - baseLng);
        const midLat = baseLat + 0.5 * (targetLat - baseLat);
        return Cesium.Cartesian3.fromDegrees(midLng, midLat, startHeight);
      } else {
        if (!tankerUavOrbitStartTime) { tankerUavOrbitStartTime = Date.now(); }
        const elapsed = Date.now() - tankerUavOrbitStartTime;
        
        let carLng, carLat;
        if (sharedTankerRescueCarPosition) {
          const carPos = sharedTankerRescueCarPosition.getValue(viewer.clock.currentTime);
          if (carPos) {
            const cartographic = Cesium.Cartographic.fromCartesian(carPos);
            carLng = Cesium.Math.toDegrees(cartographic.longitude);
            carLat = Cesium.Math.toDegrees(cartographic.latitude);
          }
        }
        
        const centerLng = Number(tankerPointAdjust.lng) || 114.8945;
        const centerLat = Number(tankerPointAdjust.lat) || 30.632161;

        const uavStartLng = carLng + 0.5 * (targetLng - carLng);
        const uavStartLat = carLat + 0.5 * (targetLat - carLat);

        const orbitDuration = 12000;
        const dLng = uavStartLng - centerLng;
        const dLat = uavStartLat - centerLat;
        const radius = Math.sqrt(dLng * dLng + dLat * dLat);
        const startAngle = Math.atan2(dLat, dLng);

        if (elapsed < orbitDuration) {
          const rawAngle = startAngle - (elapsed / orbitDuration) * 2.0 * Math.PI;
          const baseAngle = Math.max(rawAngle, startAngle - 2.0 * Math.PI); 
          const angle = baseAngle + (config.angleOffset || 0); // 👈 加入角度编队偏移
          
          const currentLng = centerLng + radius * Math.cos(angle);
          const currentLat = centerLat + radius * Math.sin(angle);
          
          if (config.id === 'uav_model_move') {
            const angleDiff = startAngle - baseAngle; 
            if (angleDiff >= 0.5 * Math.PI && !capturedPhotos.value[0]) {
              capturedPhotos.value[0] = true; activePhotoIndex.value = 0;
              triggerPhotoAnimation(0, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
            }
            if (angleDiff >= 1.0 * Math.PI && !capturedPhotos.value[1]) {
              capturedPhotos.value[1] = true; activePhotoIndex.value = 1;
              triggerPhotoAnimation(1, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
            }
            if (angleDiff >= 1.5 * Math.PI && !capturedPhotos.value[2]) {
              capturedPhotos.value[2] = true; activePhotoIndex.value = 2;
              triggerPhotoAnimation(2, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
            }
            if (angleDiff >= 1.95 * Math.PI && !capturedPhotos.value[3]) {
              capturedPhotos.value[3] = true; activePhotoIndex.value = 3;
              triggerPhotoAnimation(3, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
            }
          }
          return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight);
        } else {
          const finalAngle = startAngle - 2.0 * Math.PI + (config.angleOffset || 0);
          const currentLng = centerLng + radius * Math.cos(finalAngle);
          const currentLat = centerLat + radius * Math.sin(finalAngle);
          
          if (config.id === 'uav_model_move' && !capturedPhotos.value[3]) {
            capturedPhotos.value[3] = true; activePhotoIndex.value = 3;
            triggerPhotoAnimation(3, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight));
          }
          return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight);
        }
      }
    }, false);

    const tankerUavOrientation = new Cesium.CallbackProperty(() => {
      const pos = tankerUavPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;

      let headingRad;
      if (props.activePhaseIndex >= 8) {
        const targetLng = Number(tankerPointAdjust.lng) || 114.8945;
        const targetLat = Number(tankerPointAdjust.lat) || 30.632161;
        const carto = Cesium.Cartographic.fromCartesian(pos);
        headingRad = Math.PI / 2 - Math.atan2(targetLat - Cesium.Math.toDegrees(carto.latitude), targetLng - Cesium.Math.toDegrees(carto.longitude));
      } else {
        headingRad = Cesium.Math.toRadians(Number(tankerUavAdjust.heading) || 18);
      }

      return Cesium.Transforms.headingPitchRollQuaternion(pos, new Cesium.HeadingPitchRoll(headingRad, 0, 0));
    }, false);

    const entity = viewer.entities.add({
      id: config.id + '_tanker',
      name: config.label + ' (油罐车)',
      show: false,
      position: tankerUavPosition,
      orientation: tankerUavOrientation,
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => tankerUavAdjust.scale > 0 ? tankerUavAdjust.scale : 0.1, false),
        minimumPixelSize: 1, 
        heightReference: Cesium.HeightReference.NONE,
        runAnimations: false
      }
    });
    tankerUavEntities.push(entity);
  });

  // 初始化油罐车场景的救援车
  // 初始化油罐车场景的救援车（并排编队）
  // 初始化油罐车场景的救援车（并排编队 + 现场动态环绕巡逻）
  // 初始化油罐车场景的救援车（并排编队 + 丝滑物理转向）
  // 初始化油罐车场景的救援车（并排编队 + 丝滑物理转向）
  tankerRescueCarModelConfigs.forEach((config, index) => {
    console.log(`[Cesium] 正在初始化油罐车场景救援车实体: ${config.id}, 路径: ${config.uri}`);

    let phase7StartJulian = undefined;
    let phase8StartJulian = undefined;
    let currentHeading = undefined;
    let lastLocalPhase = -1;

    const tankerRescueCarPosition = new Cesium.CallbackProperty((time) => {
      if (lastLocalPhase !== props.activePhaseIndex) {
        phase7StartJulian = Cesium.JulianDate.clone(time);
        phase8StartJulian = Cesium.JulianDate.clone(time);
        lastLocalPhase = props.activePhaseIndex;
      }

      const baseStartLng = Number(tankerRescueCarAdjust.lng) || 114.895791;
      const baseStartLat = Number(tankerRescueCarAdjust.lat) || 30.631361;
      const baseTargetLng = Number(tankerPointAdjust.lng) || 114.8945;
      const baseTargetLat = Number(tankerPointAdjust.lat) || 30.632161;
      const startHeight = Number(tankerRescueCarAdjust.height) || -1.5;

      const startLng = baseStartLng + (config.lonOffset || 0);
      const startLat = baseStartLat + (config.latOffset || 0);

      const factor = config.stopFactor || 0.40;
      const actualTargetLng = baseStartLng + factor * (baseTargetLng - baseStartLng) + (config.lonOffset || 0);
      const actualTargetLat = baseStartLat + factor * (baseTargetLat - baseStartLat) + (config.latOffset || 0);

      if (props.activePhaseIndex < 7) {
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else if (props.activePhaseIndex === 7) {
        const elapsed = Math.max(0, Cesium.JulianDate.secondsDifference(time, phase7StartJulian));
        const duration = 6.0;
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        const lng = startLng + (actualTargetLng - startLng) * easeT;
        const lat = startLat + (actualTargetLat - startLat) * easeT;
        return Cesium.Cartesian3.fromDegrees(lng, lat, startHeight);
      } else {
        const elapsed = Math.max(0, Cesium.JulianDate.secondsDifference(time, phase8StartJulian));
        const period = 20.0; 

        const dLng = actualTargetLng - baseTargetLng;
        const dLat = actualTargetLat - baseTargetLat;
        const radius = Math.sqrt(dLng * dLng + dLat * dLat);
        const startAngle = Math.atan2(dLat, dLng);

        const angle = startAngle + (elapsed / period) * 2.0 * Math.PI;
        const currentLng = baseTargetLng + radius * Math.cos(angle);
        const currentLat = baseTargetLat + radius * Math.sin(angle);

        return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, startHeight);
      }
    }, false);

    const tankerRescueCarOrientation = new Cesium.CallbackProperty((time) => {
      const pos = tankerRescueCarPosition.getValue(time);
      if (!pos) return undefined;
      
      let targetHeadingRad;
      const nextTime = Cesium.JulianDate.addSeconds(time, 0.2, new Cesium.JulianDate());
      const nextPos = tankerRescueCarPosition.getValue(nextTime);
      
      const baseStartLng = Number(tankerRescueCarAdjust.lng) || 114.895791;
      const baseStartLat = Number(tankerRescueCarAdjust.lat) || 30.631361;
      const baseTargetLng = Number(tankerPointAdjust.lng) || 114.8945;
      const baseTargetLat = Number(tankerPointAdjust.lat) || 30.632161;
      
      if (nextPos && Cesium.Cartesian3.distance(pos, nextPos) > 0.001) {
        const cartoCur = Cesium.Cartographic.fromCartesian(pos);
        const cartoNext = Cesium.Cartographic.fromCartesian(nextPos);
        const dLng = (cartoNext.longitude - cartoCur.longitude) * Math.cos(cartoCur.latitude);
        const dLat = cartoNext.latitude - cartoCur.latitude;
        targetHeadingRad = -Math.atan2(dLat, dLng);
      } else {
        const dLng = (baseTargetLng - baseStartLng) * Math.cos(baseStartLat * Math.PI / 180);
        const dLat = baseTargetLat - baseStartLat;
        targetHeadingRad = -Math.atan2(dLat, dLng);
      }

      if (currentHeading === undefined) {
        currentHeading = targetHeadingRad;
      } else {
        let diff = targetHeadingRad - currentHeading;
        diff = Math.atan2(Math.sin(diff), Math.cos(diff));
        currentHeading += diff * 0.15; 
      }

      const hpr = new Cesium.HeadingPitchRoll(currentHeading, 0, 0);
      return Cesium.Transforms.headingPitchRollQuaternion(pos, hpr);
    }, false);

    if (index === 0) {
      sharedTankerRescueCarPosition = tankerRescueCarPosition;
    }

    const entity = viewer.entities.add({
      id: config.id,
      name: config.label + ' (油罐车)',
      show: false,
      position: tankerRescueCarPosition,
      orientation: tankerRescueCarOrientation,
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => Number(tankerRescueCarAdjust.scale) || 1.0, false),
        minimumPixelSize: 16,
        heightReference: Cesium.HeightReference.NONE,
        runAnimations: true
      }
    });
    tankerRescueCarEntities.push(entity);
  });
// =========================================================
  // 🛰️ 新增：绑定真实数据的 无人机 & 2辆无人车 动态回传链路
  // =========================================================

  // 1. 绑定无人机 (UAV) 链路

  // 2. 绑定 2辆无人车 (UGV) 链路
  // 遍历你存放无人车实体的 rescueCarEntities 数组，自动为两辆车分别建立连线
  // =========================================================
  // 🛰️ 新增：绑定真实数据的 无人车 (UGV) 动态回传链路
  // =========================================================

  // 1. 绑定无人机 (UAV) 链路 (这部分不用动，前面已经改好了)

  // 2. 绑定 2个无人车 (UGV) 节点链路
  // =========================================================
  // 🛰️ 新增：绑定 3个实体编队 × 每个实体2辆车 = 6条 动态回传链路
  // =========================================================

  // =========================================================
  // 🛰️ 新增：绑定 3个实体编队 × 每个实体2辆车 = 6条 动态回传链路
  // =========================================================

  rescueCarEntities.forEach((carEntity, modelIndex) => {
    
    // 每个 GLB 实体内部有两辆车并排，循环2次打出2条线
    [0, 1].forEach((innerCarIndex) => {
      
      viewer.entities.add({
        id: `line-link-car${modelIndex + 1}-${innerCarIndex + 1}-to-jizhan-real`,
        name: `第${modelIndex + 1}编队 - 第${innerCarIndex + 1}辆无人车数据链路`,
        
        show: new Cesium.CallbackProperty(() => {
          return Number(props.activePhaseIndex) >= 8 && carEntity.show;
        }, false),
        
        polyline: {
          positions: new Cesium.CallbackProperty((time) => {
            if (Number(props.activePhaseIndex) < 8) return [];

            // 获取车队的中心世界坐标和三维姿态（包含朝向、俯仰、翻滚）
            const carCartesian = carEntity.position.getValue(time);
            const carOrientation = carEntity.orientation.getValue(time);
            if (!carCartesian || !carOrientation) return [];

            const jizhanTop = getModelTopPosition(
              jizhanAdjust.lng, jizhanAdjust.lat, jizhanAdjust.height,
              jizhanAdjust.heading, jizhanAdjust.pitch, jizhanAdjust.roll, JIZHAN_TOP_OFFSET
            );

            // 🚨 核心空间几何算法：相对于车体中心的局部偏移（单位：米）
            // 如果你发现连线偏前/偏后了，调整 Y 的值；如果宽度不够，调整 X 的值；如果太高太低，调整 Z 的值。
            // 这里默认向左/向右偏移 1.8 米，高度抬升 1.2 米
            const offsetX = (innerCarIndex === 0) ? -1.8 : 1.8; // X轴通常控制左右
            const offsetY = 0.0;  // Y轴通常控制前后
            const offsetZ = 1.2;  // Z轴控制上下

            const localOffset = new Cesium.Cartesian3(offsetX, offsetY, offsetZ);

            // 将局部偏移通过车辆当前的四元数旋转，转换为真实的地球世界偏移向量
            const rotationMatrix = Cesium.Matrix3.fromQuaternion(carOrientation);
            const worldOffset = Cesium.Matrix3.multiplyByVector(rotationMatrix, localOffset, new Cesium.Cartesian3());

            // 车辆中心点 + 经过旋转计算的绝对偏移 = 焊死在车顶左右侧的天线坐标！
            const antennaPos = Cesium.Cartesian3.add(carCartesian, worldOffset, new Cesium.Cartesian3());

            return [ antennaPos, jizhanTop ];
          }, false),
          width: 3.5,
          material: new DynamicFlowMaterialProperty({
            color: Cesium.Color.CHARTREUSE,
            speed: 4.5,
            repeat: 6.0
          })
        }
      });
      
    });
  });
  viewer.screenSpaceEventHandler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.position);
    if (Cesium.defined(pickedObject)) {
      const entity = pickedObject.id;
      const primitive = pickedObject.primitive;
      
      const entityId = entity ? entity.id : null;
      
      // 1. 判断是否点击了烟雾粒子或三维车辆模型，若是且当前是中视角，则拉近到近视角
      const isSmokeClick = (primitive === smokeParticle || primitive === fireParticle || primitive === leakParticle || primitive === diffusionParticle);
      const isModelClick = entityId && (entityId === 'model_accident' || entityId === 'tanker_accident' || entityId === 'model_normal' || entityId === 'tanker_normal');
      
      if (isSmokeClick || isModelClick) {
        let emitId = null;
        if (primitive === smokeParticle || primitive === fireParticle || entityId === 'model_accident' || entityId === 'model_normal') {
          emitId = 'accident_blue';
        } else if (primitive === leakParticle || primitive === diffusionParticle || entityId === 'tanker_accident' || entityId === 'tanker_normal') {
          emitId = 'accident_red';
        }
        
        if (emitId) {
          emit('accident-picked', emitId);
          goToCloseView(emitId);
          return;
        }
      }
      
      // 2. 判断是否点击了地图上的定位标记或波浪光圈，若是则定位到远视角并展示事故图片悬浮窗
      if (entityId) {
        let emitId = null;
        if (entityId === 'accident_blue' || entityId === 'marker-accident_blue' || entityId === 'wave-accident_blue') {
          emitId = 'accident_blue';
        } else if (entityId === 'accident_red' || entityId === 'marker-accident_red' || entityId === 'wave-accident_red') {
          emitId = 'accident_red';
        }
        
        if (emitId) {
          emit('accident-picked', emitId);
          zoomToPoint(emitId);
          return;
        }
      }
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}

function updatePhaseScene(index, animate = false) {
  if (!viewer || !props.phases.length || !focusAreaEntity) return

  if (animate && isFlying) {
    try {
      viewer.camera.cancelFlight();
    } catch (e) {}
    isFlying = false;
  }

  try {
    if (index !== 7) {
      phase7StartTime = 0;
    }
    if (index !== 8) {
      uavOrbitStartTime = 0;
      tankerUavOrbitStartTime = 0;
      capturedPhotos.value = [false, false, false, false];
      activePhotoIndex.value = null;
    }
    const phase = props.phases[index] || props.phases[0]
    const pointId = props.focusedPointId || phase.focusPoint || 'gateway'
    const point = scenarioPoints[pointId] || scenarioPoints.gateway

    let lng = point.longitude, lat = point.latitude;
    if (pointId === 'accident_blue') {
      lng = truckAdjust.lng; lat = truckAdjust.lat;
    } else if (pointId === 'accident_red') {
      lng = tankerPointAdjust.lng; lat = tankerPointAdjust.lat;
    }

    // 无论在哪个场景，都让所有模型保持 show: true 状态以触发预加载
    // 但通过 scale 来控制真正可见的模型
    if (pointId === 'accident_blue') {
      updateTruckSequence(index, pointId)
      if (leakParticle) leakParticle.show = false
      if (diffusionParticle) diffusionParticle.show = false
    } else if (pointId === 'accident_red') {
      updateTankerSequence(index, pointId)
      if (smokeParticle) smokeParticle.show = false
      if (fireParticle) fireParticle.show = false
    } else {
      if (smokeParticle) smokeParticle.show = false
      if (fireParticle) fireParticle.show = false
      if (leakParticle) leakParticle.show = false
      if (diffusionParticle) diffusionParticle.show = false
    }

    focusAreaEntity.position = Cesium.Cartesian3.fromDegrees(lng, lat, 0)

    // 悬浮窗展示逻辑：在货车追尾现场和油罐车泄露现场的“无人装备出动阶段”(索引 6) 、 “无人感知部署阶段”(索引 7) 、 “救援装备出动阶段”(索引 9) 、 “救援任务执行阶段”(索引 10) 显示
    const isTruckScene = (pointId === 'accident_blue');
    const isTankerScene = (pointId === 'accident_red');

    if (isTruckScene && index === 4) {
      detectionPopup.show = true;
      detectionPopup.state = 'idle';
      detectionPopup.progress = 0;
    } else {
      detectionPopup.show = false;
    }

    if (isTruckScene && index === 8) {
      simulationPopup.show = true;
    } else {
      simulationPopup.show = false;
    }

    if (isTruckScene && index === 6) {
      rescuePopup.title = '无人装备出动';
      rescuePopup.status = '已出发';
      rescueCoords.lng = 113.418173;
      rescueCoords.lat = 30.321919;
      rescueCoords.height = 24.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
    } else if (isTruckScene && index === 7) {
      rescuePopup.title = '无人感知部署';
      rescuePopup.status = '已到达';
      rescueCoords.lng = 113.104833;
      rescueCoords.lat = 30.385469;
      rescueCoords.height = 24.0;
      
      // 飞行/行驶动画耗时约6秒，在第5秒（即将到达的最后一秒）再显示标记和悬浮窗，避免突兀
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
      
      setTimeout(() => {
        if (props.focusedPointId === 'accident_blue' && Number(props.activePhaseIndex) === 7) {
          if (rescueMarkerEntity) rescueMarkerEntity.show = true;
          rescuePopup.show = true;
        }
      }, 5000);
    } else if (isTruckScene && index === 9) {
      rescuePopup.title = '救援装备出动';
      rescuePopup.status = '已出发';
      rescueCoords.lng = 113.418173;
      rescueCoords.lat = 30.321919;
      rescueCoords.height = 24.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
    } else if (isTruckScene && index === 10) {
      rescuePopup.title = '救援任务执行';
      rescuePopup.status = '执行中';
      rescueCoords.lng = 113.104833;
      rescueCoords.lat = 30.385469;
      rescueCoords.height = 24.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
    } else if (isTankerScene && index === 6) {
      rescuePopup.title = '无人装备出动';
      rescuePopup.status = '已出发';
      // 跟随无人机位置，悬浮窗显示在无人机头顶上方
      rescueCoords.lng = tankerUavAdjust.lng;
      rescueCoords.lat = tankerUavAdjust.lat;
      rescueCoords.height = tankerUavAdjust.height + 8.0; // 显示在无人机头顶上方
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
    } else if (isTankerScene && index === 7) {
      rescuePopup.title = '无人机感知部署';
      rescuePopup.status = '已到达';
      // 油罐车事故点 (使用动态的 tankerPointAdjust)
      rescueCoords.lng = tankerPointAdjust.lng;
      rescueCoords.lat = tankerPointAdjust.lat;
      rescueCoords.height = 17.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
      
      setTimeout(() => {
        if (props.focusedPointId === 'accident_red' && Number(props.activePhaseIndex) === 7) {
          if (rescueMarkerEntity) rescueMarkerEntity.show = true;
          rescuePopup.show = true;
        }
      }, 5000);
    } else if (isTankerScene && index === 9) {
      rescuePopup.title = '救援装备出动';
      rescuePopup.status = '已出发';
      rescueCoords.lng = tankerPointAdjust.lng;
      rescueCoords.lat = tankerPointAdjust.lat;
      rescueCoords.height = 17.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
    } else if (isTankerScene && index === 10) {
      rescuePopup.title = '救援任务执行';
      rescuePopup.status = '执行中';
      rescueCoords.lng = tankerPointAdjust.lng;
      rescueCoords.lat = tankerPointAdjust.lat;
      rescueCoords.height = 17.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
    } else {
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
    }

    if (index >= 6) {
      if (!currentMissionDataSource) {
        loadMission();
      }

      // 根据用户要求，当在货车现场进入"无人装备出动"(阶段6)时，视角飞向大范围侧倾透视视角
      if (pointId === 'accident_blue' && index === 6) {
        stopAutoRotate();
        try {
          viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
        } catch (e) {}
        isFlying = true;
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(113.26, 29.96, 39000), // 侧倾透视视角，将相机向南平移并微调高度以完整居中路线
          orientation: {
            heading: Cesium.Math.toRadians(350.0),
            pitch: Cesium.Math.toRadians(-35.0),
            roll: 0.0
          },
          duration: 1.8,
          complete: () => {
            isFlying = false;
          }
        });
      }
    } else {
      if (currentMissionDataSource) {
        viewer.dataSources.remove(currentMissionDataSource);
        currentMissionDataSource = null;
      }
      
      // 强力清除可能因为异步加载残留的其他 CZML 数据源
      if (viewer && viewer.dataSources) {
        const dsLength = viewer.dataSources.length;
        for (let i = dsLength - 1; i >= 0; i--) {
          const ds = viewer.dataSources.get(i);
          if (ds instanceof Cesium.CzmlDataSource) {
            viewer.dataSources.remove(ds, true);
          }
        }
      }

      // 恢复正常的时间流速，防止粒子和模型动画过快
      viewer.clock.multiplier = 1.0;
    }

    if (popupEntity) {
      // 隐藏悬浮窗和连接线（根据用户要求取消显示）
      popupEntity.show = false
      if (connectionLineEntity) connectionLineEntity.show = false

      if (index >= 6) {
        // 在货车追尾现场的无人机阶段显示无人机模型和救援车并隐藏所有粒子效果
        // 在货车追尾现场的无人机阶段显示无人机模型和救援车并隐藏所有粒子效果
        if (pointId === 'accident_blue') {
          uavEntities.forEach(entity => {
            // 🚨 核心修改：使用 includes('move') 来动态匹配 1/2/3 号无人机
            const isTarget = (index === 6 && !entity.id.includes('move')) || (index >= 7 && entity.id.includes('move'));
            if (isTarget) {
              const needsAnimation = !entity.show || (entity.id.includes('move') && index === 7 && lastUavPhaseIndex !== 7);
              entity.show = true;
              if (needsAnimation) {
                playEntityAnimation(entity, true, 0, 6.0);
              }
            } else {
              entity.show = false;
            }
          });
          // ...后面保持不变
          // 恢复显示救援车模型
          rescueCarEntities.forEach(entity => { entity.show = true });
          
          // 隐藏油罐车场景的无人机和救援车
          tankerUavEntities.forEach(entity => { entity.show = false })
          tankerRescueCarEntities.forEach(entity => { entity.show = false })
          
          // 隐藏所有粒子效果，只保留模型
          if (smokeParticle) smokeParticle.show = false
          if (fireParticle) fireParticle.show = false
          if (leakParticle) leakParticle.show = false
          if (diffusionParticle) diffusionParticle.show = false
        } else if (pointId === 'accident_red') {
          // 在油罐车泄露现场的无人机阶段显示无人机模型和救援车并隐藏所有粒子效果
          tankerUavEntities.forEach(entity => {
            // 🚨 核心修改同上
            const isTarget = (index === 6 && !entity.id.includes('move')) || (index >= 7 && entity.id.includes('move'));
            if (isTarget) {
              const needsAnimation = !entity.show || (entity.id.includes('move') && index === 7 && lastTankerUavPhaseIndex !== 7);
              entity.show = true;
              if (needsAnimation) {
                playEntityAnimation(entity, true, 0, 6.0);
              }
            } else {
              entity.show = false;
            }
          });
          tankerRescueCarEntities.forEach(entity => { entity.show = true });
          
          // 隐藏货车场景的无人机和救援车
          uavEntities.forEach(entity => { entity.show = false })
          rescueCarEntities.forEach(entity => { entity.show = false })
          
          // 隐藏所有粒子效果，只保留模型
          if (smokeParticle) smokeParticle.show = false
          if (fireParticle) fireParticle.show = false
          if (leakParticle) leakParticle.show = false
          if (diffusionParticle) diffusionParticle.show = false
        } else {
          // 如果视角切换到其他地方，隐藏所有无人机和救援车
          uavEntities.forEach(entity => { entity.show = false })
          rescueCarEntities.forEach(entity => { entity.show = false })
          tankerUavEntities.forEach(entity => { entity.show = false })
          tankerRescueCarEntities.forEach(entity => { entity.show = false })
        }
      } else {
        // 前置阶段隐藏悬浮窗和连接线
        popupEntity.show = false
        if (connectionLineEntity) connectionLineEntity.show = false
        // 隐藏所有无人机模型和救援车
        uavEntities.forEach(entity => { entity.show = false })
        rescueCarEntities.forEach(entity => { entity.show = false })
        tankerUavEntities.forEach(entity => { entity.show = false })
        tankerRescueCarEntities.forEach(entity => { entity.show = false })
      }
    }

    lastUavPhaseIndex = index;
    lastTankerUavPhaseIndex = index;

    if (!spinCallback && props.focusedPointId && !isFlying) applyOrbitView(animate)
  } catch (error) {
    console.warn('更新阶段场景时出现警告:', error.message)
  }
}

function updateMarkerVisibility() {
  if (!viewer) return;
  // 当没有聚焦点或者处于远景视角时显示标记
  const showMarkers = !props.focusedPointId || accidentViewLevel.value === 'far';
  const entitiesToToggle = [
    'marker-accident_blue', 'wave-accident_blue',
    'marker-accident_red', 'wave-accident_red'
  ];
  entitiesToToggle.forEach(id => {
    const entity = viewer.entities.getById(id);
    if (entity) {
      entity.show = showMarkers;
    }
  });
}

function zoomToPoint(pointId) {
  if (!viewer || isFlying) return
  const point = scenarioPoints[pointId]
  if (!point) return
  
  stopAutoRotate()
  isFlying = true
  
  accidentViewLevel.value = 'far'
  updateMarkerVisibility()
  
  try {
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  } catch (e) {}

  const destHeight = 120000;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, destHeight),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-60), roll: 0.0 },
    duration: 1.5,
    complete: () => {
      isFlying = false
      
      // 显示事故图片悬浮窗
      accidentDetailPopup.show = true
      accidentDetailPopup.pointId = pointId
      accidentDetailPopup.title = pointId === 'accident_blue' ? '高速公路 - 货车追尾事故现场' : '化工园区 - 油罐车泄漏事故现场'
      accidentDetailPopup.img = pointId === 'accident_blue' ? '/Dashboard/images/uav_aerial_photo.png' : '/Dashboard/images/tanker_aerial_photo.png'
      
      applyOrbitView()
    }
  })
}

function goToMediumView() {
  if (!viewer || isFlying || !accidentDetailPopup.pointId) return
  const pointId = accidentDetailPopup.pointId
  const point = scenarioPoints[pointId]
  if (!point) return
  
  accidentDetailPopup.show = false
  accidentViewLevel.value = 'medium'
  updateMarkerVisibility()
  isFlying = true
  
  try {
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  } catch (e) {}
  
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, 2000),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-45), roll: 0.0 },
    duration: 1.5,
    complete: () => {
      isFlying = false
      applyOrbitView()
      if (pointId === 'accident_blue') {
        updateTruckSequence(props.activePhaseIndex)
      } else if (pointId === 'accident_red') {
        updateTankerSequence(props.activePhaseIndex)
      }
    }
  })
}

function goToCloseView(pointId) {
  if (!viewer || isFlying) return
  const point = scenarioPoints[pointId]
  if (!point) return
  
  accidentDetailPopup.show = false
  accidentViewLevel.value = 'close'
  updateMarkerVisibility()
  isFlying = true
  
  stopAutoRotate()
  
  try {
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  } catch (e) {}
  
  const destHeight = pointId === 'accident_red' ? 100 : 75;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, destHeight),
    orientation: {
      heading: Cesium.Math.toRadians(8),
      pitch: Cesium.Math.toRadians(-20),
      roll: 0.0
    },
    duration: 1.5,
    complete: () => {
      isFlying = false
      applyOrbitView()
    }
  })
}

// 监听微调值的变化同步更新模型与粒子位置
watch([() => truckAdjust.lng, () => truckAdjust.lat, () => truckAdjust.heading, () => truckAdjust.height], () => {
  if (typeof truckAdjust.lng !== 'number' || typeof truckAdjust.lat !== 'number' || typeof truckAdjust.height !== 'number' || typeof truckAdjust.heading !== 'number') return;
  const position = Cesium.Cartesian3.fromDegrees(truckAdjust.lng, truckAdjust.lat, truckAdjust.height);
  const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(truckAdjust.heading), 0, 0);
  const orientation = Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
  
  truckEntities.forEach(entity => {
    entity.position = position;
    entity.orientation = orientation;
  });

  const matrix = Cesium.Transforms.eastNorthUpToFixedFrame(position);
  if (smokeParticle) smokeParticle.modelMatrix = matrix;
  if (fireParticle) fireParticle.modelMatrix = matrix;
});

// 监听油罐车微调变化
watch([() => tankerAdjust.lng, () => tankerAdjust.lat, () => tankerAdjust.heading, () => tankerAdjust.height], () => {
  if (typeof tankerAdjust.lng !== 'number' || typeof tankerAdjust.lat !== 'number' || typeof tankerAdjust.height !== 'number' || typeof tankerAdjust.heading !== 'number') return;
  const position = Cesium.Cartesian3.fromDegrees(tankerAdjust.lng, tankerAdjust.lat, tankerAdjust.height);
  const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(tankerAdjust.heading), 0, 0);
  const orientation = Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
  
  tankerEntities.forEach(entity => {
    entity.position = position;
    entity.orientation = orientation;
  });
});

// 监听救援车微调变化 (位置、角度和缩放已完全由 CallbackProperty 接管，此处无需手动更新 Entity 属性)

// 监听油罐车事故点位置与车身朝向变化同步更新泄露与弥漫效果位置
watch([() => tankerPointAdjust.lng, () => tankerPointAdjust.lat, () => tankerAdjust.heading], () => {
  if (typeof tankerPointAdjust.lng !== 'number' || typeof tankerPointAdjust.lat !== 'number') return;
  
  // 泄露粒子系统使用车身朝向对齐的坐标系，使侧向喷射角度正确
  const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(tankerAdjust.heading) || 36), 0, 0);
  const leakMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(Cesium.Cartesian3.fromDegrees(tankerPointAdjust.lng, tankerPointAdjust.lat, 0.8), hpr);
  if (leakParticle) leakParticle.modelMatrix = leakMatrix;

  // 弥漫粒子系统保持 ENU 坐标系以利于风向漂移
  const diffMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(tankerPointAdjust.lng, tankerPointAdjust.lat, 0.0));
  if (diffusionParticle) diffusionParticle.modelMatrix = diffMatrix;
});

// 监听无人机微调变化 (位置和角度已完全由 CallbackProperty 接管，此处无需手动更新 Entity 属性)

// 无人机控制函数
function showUav() {
  uavEntities.forEach(entity => { entity.show = true })
  console.log('无人机已显示')
}

function hideUav() {
  uavEntities.forEach(entity => { entity.show = false })
  console.log('无人机已隐藏')
}

function resetView() {
  if (!viewer || isFlying) return
  stopAutoRotate()
  isFlying = true
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(112.5, 30.6, 1200000),
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-90),
      roll: 0.0
    },
    duration: 1.5,
    complete: () => {
      isFlying = false
    }
  })
  console.log('地图已重置回湖北全图概览')
}

defineExpose({ zoomToPoint, resetView, capturedPhotos, activePhotoIndex, currentTimeStr });

watch(() => props.activePhaseIndex, (next, prev) => {
  accidentViewLevel.value = null;
  if (next === 7 && prev !== 7) {
    phase7StartTime = Date.now();
    tankerPhase7StartTime = Date.now();
  } else if (next < 7) {
    phase7StartTime = 0;
    tankerPhase7StartTime = 0;
  }
  
  if (next >= 4 && (prev < 4 || !diffusionStartTime)) {
    diffusionStartTime = Date.now();
  } else if (next < 4) {
    diffusionStartTime = 0;
  }

  if (cameraAdjust.phaseIndex !== next + 1) {
    cameraAdjust.phaseIndex = next + 1
    const scene = cameraAdjust.scene
    const cfg = (defaultPhaseCameraConfigs[scene] && defaultPhaseCameraConfigs[scene][next + 1]) || { range: 1440, pitch: -39, heading: -5 }
    cameraAdjust.range = cfg.range
    cameraAdjust.pitch = cfg.pitch
    cameraAdjust.heading = cfg.heading
  }

  updatePhaseScene(next, true);
});

watch(accidentViewLevel, () => {
  updateMarkerVisibility()
})

watch(() => props.focusedPointId, (newVal) => {
  if (newVal) {
    accidentViewLevel.value = 'far'
  } else {
    accidentDetailPopup.show = false
  }
  if (newVal === 'accident_blue') {
    cameraAdjust.scene = 'truck'
  } else if (newVal === 'accident_red') {
    cameraAdjust.scene = 'tanker'
  }
  updateMarkerVisibility()
  updatePhaseScene(props.activePhaseIndex);
});

onMounted(() => {
  initViewer()
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
})
onBeforeUnmount(() => {
  stopAutoRotate()
  if (timeInterval) clearInterval(timeInterval)
  if (viewer) {
    viewer.scene.postRender.removeEventListener(updateModelsReadyStatus)
    viewer.scene.postRender.removeEventListener(updatePopupPosition)
    if (smokeParticle) viewer.scene.primitives.remove(smokeParticle)
    if (fireParticle) viewer.scene.primitives.remove(fireParticle)
    if (leakParticle) viewer.scene.primitives.remove(leakParticle)
    if (diffusionParticle) viewer.scene.primitives.remove(diffusionParticle)
    viewer.destroy()
  }
})
</script>

<style scoped>
/* 仿真推演悬浮窗样式 */
.simulation-popup-panel {
  position: absolute;
  width: 290px;
  background: rgba(8, 12, 28, 0.94);
  border: 1px solid rgba(0, 255, 180, 0.5);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8), 0 0 16px rgba(0, 255, 180, 0.2);
  z-index: 1000;
  overflow: hidden;
  backdrop-filter: blur(12px);
  pointer-events: auto;
  transform: translate(-50%, -100%);
  animation: simPanelFadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #e2e8f0;
}

@keyframes simPanelFadeIn {
  from {
    opacity: 0;
    transform: translate(-50%, -90%) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -100%) scale(1);
  }
}

.simulation-popup-header {
  background: rgba(0, 255, 180, 0.12);
  border-bottom: 1px solid rgba(0, 255, 180, 0.25);
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.simulation-icon {
  font-size: 14px;
}

.simulation-popup-panel .close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.simulation-popup-panel .close-btn:hover {
  color: #f1f5f9;
}

.simulation-popup-content {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.enter-sim-btn {
  width: 100%;
  padding: 10px 14px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: white;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.enter-sim-btn:hover {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  border-color: #34d399;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.5);
  transform: translateY(-1px);
}

.enter-sim-btn:active {
  transform: translateY(0);
}

.arrow-icon {
  font-weight: bold;
  transition: transform 0.2s;
}

.enter-sim-btn:hover .arrow-icon {
  transform: translateX(3px);
}

.simulation-popup-arrow {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translate(-50%, 100%);
  width: 0;
  height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 10px solid rgba(8, 12, 28, 0.94);
}

/* 实时视频检测悬浮窗样式 */
.detection-popup-panel {
  position: absolute;
  width: 540px;
  background: rgba(7, 11, 26, 0.92);
  border: 1px solid rgba(0, 180, 255, 0.5);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.75), 0 0 16px rgba(0, 180, 255, 0.25);
  z-index: 1000;
  overflow: hidden;
  backdrop-filter: blur(12px);
  pointer-events: auto;
  transform: translate(-50%, -100%);
  animation: detectionPanelFadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #e2e8f0;
}

@keyframes detectionPanelFadeIn {
  from {
    opacity: 0;
    transform: translate(-50%, -90%) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -100%) scale(1);
  }
}

.detection-popup-header {
  background: rgba(0, 180, 255, 0.15);
  border-bottom: 1px solid rgba(0, 180, 255, 0.25);
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background-color: #ef4444;
  border-radius: 50%;
  box-shadow: 0 0 8px #ef4444;
  animation: pulseRed 1.8s infinite;
}

@keyframes pulseRed {
  0% {
    transform: scale(0.9);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  }
  70% {
    transform: scale(1.1);
    box-shadow: 0 0 0 6px rgba(239, 68, 68, 0);
  }
  100% {
    transform: scale(0.9);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
  }
}

.header-title {
  font-size: 14px;
  font-weight: 600;
  color: #38bdf8;
  letter-spacing: 0.5px;
}

.detection-popup-panel .close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.detection-popup-panel .close-btn:hover {
  color: #f1f5f9;
}

.detection-popup-content {
  display: flex;
  padding: 14px;
  gap: 14px;
}

/* Image Container */
.detection-img-container {
  position: relative;
  width: 260px;
  height: 180px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  background: #000;
}

.detection-raw-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* SVG Overlay & Bounding Boxes */
.detection-svg-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.box-rect {
  fill: none;
  stroke-width: 2px;
  vector-effect: non-scaling-stroke;
  animation: drawBox 0.5s ease-out forwards;
}

.box-label {
  font-size: 10px;
  font-weight: bold;
  fill: #fff;
  paint-order: stroke;
  stroke: #000;
  stroke-width: 2px;
  stroke-linejoin: round;
}

@keyframes drawBox {
  from {
    stroke-dasharray: 200;
    stroke-dashoffset: 200;
  }
  to {
    stroke-dasharray: 200;
    stroke-dashoffset: 0;
  }
}

.rect-fire {
  stroke: #ef4444;
}
.label-fire {
  fill: #fca5a5;
}

.rect-truck {
  stroke: #3b82f6;
}
.label-truck {
  fill: #93c5fd;
}

.rect-smoke {
  stroke: #f59e0b;
}
.label-smoke {
  fill: #fde047;
}

/* Scanning Effect */
.scanning-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, rgba(0,180,255,0) 0%, rgba(0,180,255,1) 50%, rgba(0,180,255,0) 100%);
  box-shadow: 0 0 8px rgba(0, 180, 255, 0.8);
  animation: scanMove 1.5s linear infinite;
}

@keyframes scanMove {
  0% { top: 0%; }
  50% { top: 100%; }
  100% { top: 0%; }
}

.scanning-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 12px;
  font-weight: 500;
  color: #38bdf8;
  text-shadow: 0 0 6px rgba(56, 189, 248, 0.6);
}

/* Control Panel */
.detection-control-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 180px;
}

.panel-section-title {
  font-size: 11px;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 1px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 4px;
}

.desc-text {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
  margin-bottom: 14px;
}

/* Buttons */
.detect-btn {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: white;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.detect-btn:hover {
  background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
  border-color: #38bdf8;
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
}

.pulse-button {
  animation: buttonPulse 2s infinite;
}

@keyframes buttonPulse {
  0% { box-shadow: 0 0 0 0 rgba(3, 105, 161, 0.7); }
  70% { box-shadow: 0 0 0 6px rgba(3, 105, 161, 0); }
  100% { box-shadow: 0 0 0 0 rgba(3, 105, 161, 0); }
}

/* Spinner */
.state-detecting-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(56, 189, 248, 0.1);
  border-top-color: #38bdf8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 12px;
  color: #38bdf8;
  margin-bottom: 8px;
}

.progress-bar-container {
  width: 80%;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: #38bdf8;
  transition: width 0.1s linear;
}

/* Results State */
.state-results-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-indicator {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: bold;
}

.status-indicator.warning {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #fca5a5;
}

.result-count {
  font-size: 11px;
  color: #94a3b8;
}

.detection-items-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detect-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  font-size: 12px;
}

.detect-item .item-icon {
  margin-right: 6px;
}

.detect-item .item-name {
  flex: 1;
  color: #cbd5e1;
}

.detect-item .item-conf {
  font-weight: 600;
  font-family: monospace;
}

.detect-item.fire .item-conf { color: #fca5a5; }
.detect-item.truck .item-conf { color: #93c5fd; }
.detect-item.smoke .item-conf { color: #fde047; }

.report-box {
  background: rgba(245, 158, 11, 0.07);
  border-left: 3px solid #f59e0b;
  padding: 8px 10px;
  border-radius: 0 4px 4px 0;
  font-size: 11px;
  color: #fcd34d;
  line-height: 1.4;
}

.reset-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #94a3b8;
  padding: 6px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.reset-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #f1f5f9;
  border-color: rgba(255, 255, 255, 0.3);
}

/* Arrow styling for popup alignment */
.detection-popup-arrow {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translate(-50%, 100%);
  width: 0;
  height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 10px solid rgba(7, 11, 26, 0.92);
}

.cesium-wrapper, .cesium-container { width: 100%; height: 100%; position: relative; }

/* 无人机拍照侦察悬浮窗样式 */
.uav-photo-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  width: 350px;
  background: rgba(7, 11, 25, 0.9);
  border: 1px solid rgba(0, 255, 255, 0.45);
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.65), 0 0 12px rgba(0, 255, 255, 0.2);
  z-index: 1000;
  overflow: hidden;
  backdrop-filter: blur(10px);
  animation: photoPanelFadeIn 0.3s ease-out;
  pointer-events: auto;
}

.uav-photo-header {
  background: rgba(0, 255, 255, 0.12);
  border-bottom: 1px solid rgba(0, 255, 255, 0.25);
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.uav-photo-icon {
  font-size: 14px;
}

.uav-photo-title {
  color: #00ffff;
  font-size: 13px;
  font-weight: bold;
  letter-spacing: 0.5px;
}

.uav-status-tag {
  margin-left: auto;
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(255, 169, 64, 0.15);
  color: #ffa940;
  border: 1px solid rgba(255, 169, 64, 0.35);
  border-radius: 4px;
  font-weight: bold;
  white-space: nowrap;
}

.uav-status-tag.status-done {
  background: rgba(82, 196, 26, 0.15);
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.35);
}

.uav-photo-content {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.uav-main-photo-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: #000;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.uav-photo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #888;
  font-size: 12px;
  gap: 10px;
}

.radar-scan {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px dashed #00ffff;
  animation: spin 3s linear infinite;
}

.uav-photo-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 模拟多角度透视和裁剪效果 */
.photo-angle-0 {
  transform: scale(1.0);
}
.photo-angle-1 {
  transform: scale(1.22) rotate(90deg);
}
.photo-angle-2 {
  transform: scale(1.15) scaleX(-1);
}
.photo-angle-3 {
  transform: scale(1.3) rotate(270deg);
}

.uav-photo-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.85), transparent);
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
  font-family: monospace;
  font-size: 11px;
}

.uav-photo-timestamp {
  color: #ff4d4f;
  font-weight: bold;
}

.uav-photo-coords {
  color: #00e5ff;
}

.uav-thumbnails-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
}

.uav-thumb-box {
  flex: 1;
  aspect-ratio: 16 / 10;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
  overflow: hidden;
  position: relative;
  cursor: not-allowed;
  transition: all 0.25s ease;
}

.uav-thumb-box.is-captured {
  border: 1px solid rgba(255, 255, 255, 0.3);
  cursor: pointer;
}

.uav-thumb-box.is-captured:hover {
  border-color: #00ffff;
  transform: translateY(-2px);
}

.uav-thumb-box.is-captured.is-active {
  border: 1.5px solid #00ffff;
  box-shadow: 0 0 8px rgba(0, 255, 255, 0.4);
}

.uav-thumb-inner {
  width: 100%;
  height: 100%;
  position: relative;
}

.uav-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-badge {
  position: absolute;
  top: 2px;
  left: 2px;
  background: rgba(0, 0, 0, 0.75);
  color: #00ffff;
  font-size: 8px;
  padding: 1px 3px;
  border-radius: 2px;
  font-family: monospace;
  font-weight: bold;
  border: 0.5px solid rgba(0, 255, 255, 0.3);
}

.uav-thumb-lock {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.4;
}

.lock-icon {
  font-size: 11px;
}

@keyframes photoPanelFadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 避难点 HTML 悬浮窗样式 */
/* 事故详情悬浮窗样式 */
.accident-detail-popup {
  position: absolute;
  z-index: 1001;
  transform: translate(-50%, -100%);
  width: 200px;
  background: rgba(10, 25, 50, 0.92);
  border: 1.5px solid rgba(0, 229, 255, 0.6);
  border-radius: 6px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.8), 0 0 12px rgba(0, 229, 255, 0.35);
  overflow: visible;
  pointer-events: auto;
  backdrop-filter: blur(8px);
  animation: popupFadeIn 0.3s ease-out;
}

@keyframes popupFadeIn {
  from { opacity: 0; transform: translate(-50%, -95%) scale(0.95); }
  to { opacity: 1; transform: translate(-50%, -100%) scale(1); }
}

.accident-detail-header {
  background: linear-gradient(90deg, rgba(0, 229, 255, 0.25), rgba(0, 100, 255, 0.25));
  border-bottom: 1.5px solid rgba(0, 229, 255, 0.4);
  color: #00e5ff;
  padding: 4px 8px;
  font-weight: bold;
  font-size: 11px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top-left-radius: 5px;
  border-top-right-radius: 5px;
}

.accident-detail-header .close-btn {
  background: none;
  border: none;
  color: #00e5ff;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.accident-detail-header .close-btn:hover {
  color: #ffffff;
}

.accident-detail-body {
  padding: 5px;
}

.accident-detail-body .img-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 3px;
  overflow: hidden;
  border: 1px solid rgba(0, 229, 255, 0.25);
  cursor: pointer;
}

.accident-detail-body .accident-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.accident-detail-body .img-wrapper:hover .accident-img {
  transform: scale(1.05);
}

.accident-detail-body .img-hover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 10px;
  gap: 3px;
  opacity: 0.85;
  transition: background 0.3s ease, opacity 0.3s ease;
}

.accident-detail-body .img-wrapper:hover .img-hover-overlay {
  background: rgba(0, 0, 0, 0.2);
  opacity: 1;
}

.accident-detail-body .zoom-icon {
  font-size: 13px;
}

.accident-detail-arrow {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 0;
  border: 8px solid transparent;
  border-top-color: rgba(10, 25, 50, 0.92);
  border-bottom: 0;
  margin-left: -8px;
  margin-bottom: -8px;
}

.shelter-popup-panel {
  position: absolute;
  z-index: 1000;
  transform: translate(-50%, -100%);
  width: 170px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  overflow: visible;
  pointer-events: auto;
}

.shelter-popup-header {
  background-color: #b49b1c; /* 芥末黄/金黄色 */
  color: white;
  padding: 4px 8px;
  font-weight: bold;
  font-size: 11px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
}

.shelter-popup-header .close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.shelter-popup-header .close-btn:hover {
  opacity: 0.8;
}

.shelter-popup-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  color: #333;
}

.shelter-popup-table td {
  padding: 4px 6px;
  border: 1px solid #dff0f6;
  text-align: center;
}

.shelter-popup-table td.label {
  background-color: #e0f0f5;
  color: #555;
  font-weight: bold;
  width: 45%;
}

.shelter-popup-table td.value {
  background-color: white;
  color: #333;
}

.shelter-popup-arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid white;
  filter: drop-shadow(0 2px 2px rgba(0, 0, 0, 0.15));
}
.globe-mask {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(2, 10, 22, 0.88); color: rgba(255, 255, 255, 0.78);
}
.debug-panel {
  position: absolute; top: 100px; right: 20px; z-index: 999;
  background: rgba(0, 0, 0, 0.85); padding: 15px; border-radius: 8px; border: 1px solid #00e5ff; color: white; width: 220px;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
}
.debug-panel h4 {
  margin: 0 0 12px 0; color: #00e5ff; font-size: 14px; text-align: center;
}
.debug-panel div {
  margin-bottom: 8px;
}
.debug-panel label {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px;
}
.debug-panel input {
  width: 80px; padding: 4px; border: 1px solid #333; border-radius: 4px;
  background: rgba(255,255,255,0.1); color: white; font-size: 12px;
}
.scene-switcher .switch-buttons {
  display: flex; gap: 6px;
}
.scene-switcher .switch-buttons button {
  flex: 1; padding: 6px 8px; border: 1px solid #333; border-radius: 4px;
  background: rgba(255,255,255,0.1); color: white; font-size: 11px;
  cursor: pointer; transition: all 0.2s;
}
.scene-switcher .switch-buttons button:hover {
  background: rgba(0, 229, 255, 0.2);
}
.scene-switcher .switch-buttons button.active {
  background: linear-gradient(135deg, #00e5ff, #0080ff);
  color: #061628;
  font-weight: bold;
  border-color: #00e5ff;
}
.debug-panel button {
  width: 100%; margin-top: 5px; padding: 6px; border: none; border-radius: 4px;
  background: linear-gradient(135deg, #00e5ff, #0080ff); color: #061628;
  font-size: 12px; font-weight: bold; cursor: pointer;
}
.debug-panel button:hover {
  opacity: 0.9;
}
.debug-row { margin-bottom: 10px; display: flex; flex-direction: column; }
.debug-panel h3 { margin: 0 0 15px 0; color: #00e5ff; font-size: 16px; }
.phase-indicator { display: flex; gap: 4px; margin-top: 8px; }
.phase-indicator span { flex: 1; height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; }
.phase-indicator span.active { background: #00e5ff; box-shadow: 0 0 8px #00e5ff; }
.play-btn {
  background: #00e5ff; color: #061628; border: none; padding: 8px; border-radius: 4px; cursor: pointer; font-weight: bold;
}

/* 无人车实时数据悬浮窗 - 赛博朋克深色主题 - 紧凑版 */
.ugv-panel {
  position: absolute;
  width: 175px;
  background: rgba(7, 11, 25, 0.85);
  border-radius: 5px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6), 0 0 8px rgba(0, 255, 255, 0.15);
  font-family: "JetBrains Mono", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #fff;
  z-index: 1000;
  pointer-events: none;
  overflow: hidden;
  border: 1px solid rgba(0, 255, 255, 0.25);
  backdrop-filter: blur(6px);
  transform: translate(-50%, -100%);
}

/* 顶部霓虹边框高光 */
.ugv-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00ffff, transparent);
}

.ugv-panel::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid rgba(0, 255, 255, 0.4);
  filter: drop-shadow(0 1px 3px rgba(0, 255, 255, 0.3));
}

.ugv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.12);
  background: rgba(0, 255, 255, 0.04);
}

.ugv-title {
  font-weight: bold;
  font-size: 11px;
  color: #00ffff;
  letter-spacing: 0.5px;
}

.ugv-status {
  font-size: 9px;
  color: #00ff88;
  font-weight: bold;
  padding: 1px 4px;
  background: rgba(0, 255, 136, 0.08);
  border: 1px solid rgba(0, 255, 136, 0.25);
  border-radius: 2px;
}

.ugv-status.offline {
  color: #ffb4b4;
  background: rgba(168, 54, 54, 0.18);
  border-color: rgba(255, 180, 180, 0.28);
}

.ugv-data {
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ugv-row {
  display: flex;
  gap: 4px;
}

.ugv-item {
  flex: 1;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  padding: 4px 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: background 0.3s;
}

.ugv-item.full-width {
  flex: 100%;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.ugv-label {
  font-size: 10px;
  color: #8fa3b0;
}

.ugv-value {
  font-size: 11px;
  font-weight: 700;
  color: #e0f2fe;
  text-shadow: 0 0 4px rgba(224, 242, 254, 0.3);
}

.ugv-footer {
  text-align: right;
  padding: 5px 10px;
  font-size: 9px;
  color: #00ffff;
  background: rgba(0, 255, 255, 0.04);
  border-top: 1px solid rgba(0, 255, 255, 0.12);
  opacity: 0.8;
  cursor: pointer;
  pointer-events: auto;
  transition: opacity 0.2s, background 0.2s;
}

.ugv-footer:hover {
  opacity: 1;
  background: rgba(0, 255, 255, 0.12);
}

/* 城市行政区划说明悬浮窗样式 */
.city-popup-panel {
  position: absolute;
  z-index: 1000;
  transform: translate(-50%, -100%);
  width: 220px;
  background: rgba(7, 11, 25, 0.9);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6), 0 0 10px rgba(0, 229, 255, 0.2);
  overflow: visible;
  pointer-events: auto;
  border: 1px solid rgba(0, 229, 255, 0.3);
  backdrop-filter: blur(8px);
  padding: 0;
  color: #ffffff;
}

.city-popup-header {
  background: linear-gradient(90deg, rgba(255, 0, 127, 0.2), rgba(255, 0, 127, 0.05));
  border-bottom: 1px solid rgba(255, 0, 127, 0.3);
  color: #ff007f;
  padding: 8px 12px;
  font-weight: bold;
  font-size: 13px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
}

.city-popup-header.is-huanggang {
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.2), rgba(255, 215, 0, 0.05));
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  color: #ffd700;
}

.city-popup-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.city-close-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.city-close-btn:hover {
  color: #ffffff;
}

.city-popup-body {
  padding: 10px 12px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.city-info-item {
  display: flex;
  line-height: 1.4;
}

.info-label {
  color: #8fa3b0;
  width: 65px;
  flex-shrink: 0;
}

.info-value {
  color: #e0f2fe;
}

.info-value.desc {
  text-align: justify;
}

.city-popup-arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid rgba(7, 11, 25, 0.9);
}

/* 城市悬浮提示框样式 - 高端玻璃拟态 */
.city-tooltip {
  position: absolute;
  z-index: 1001;
  pointer-events: none;
  background: rgba(7, 11, 25, 0.76);
  border: 1px solid rgba(0, 229, 255, 0.35);
  border-radius: 4px;
  padding: 6px 12px;
  color: #ffffff;
  font-size: 13px;
  font-weight: bold;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5), 0 0 8px rgba(0, 229, 255, 0.15);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  gap: 6px;
  transition: opacity 0.15s ease-out;
}

.city-icon {
  color: #00ffd8;
  filter: drop-shadow(0 0 2px rgba(0, 255, 216, 0.6));
}

.city-name {
  letter-spacing: 0.5px;
  text-shadow: 0 0 4px rgba(255, 255, 255, 0.3);
}

/* 现场灯光微调面板样式 - 高端玻璃拟态 */
.light-control-panel {
  position: absolute;
  bottom: 120px;
  right: 20px;
  width: 320px;
  background: rgba(7, 16, 32, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 15px rgba(0, 229, 255, 0.15);
  backdrop-filter: blur(10px);
  z-index: 1010;
  color: #e2f1ff;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.light-panel-header {
  padding: 10px 14px;
  background: linear-gradient(90deg, rgba(0, 229, 255, 0.2), rgba(0, 229, 255, 0.05));
  border-bottom: 1px solid rgba(0, 229, 255, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.light-panel-title {
  font-size: 14px;
  font-weight: bold;
  letter-spacing: 0.5px;
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.6);
}

.light-panel-toggle {
  font-size: 12px;
  color: rgba(0, 229, 255, 0.8);
}

.light-panel-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 420px;
  overflow-y: auto;
}

/* 自定义滚动条 */
.light-panel-body::-webkit-scrollbar {
  width: 4px;
}
.light-panel-body::-webkit-scrollbar-thumb {
  background: rgba(0, 229, 255, 0.3);
  border-radius: 2px;
}

.light-control-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.light-control-label {
  font-size: 12px;
  color: #8fa5c0;
  min-width: 80px;
}

.light-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #00ffd8;
}

.light-input-num {
  width: 140px;
  background: rgba(4, 10, 20, 0.8);
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 4px;
  padding: 4px 8px;
  color: #ffffff;
  font-size: 12px;
  text-align: right;
  transition: border-color 0.2s;
}
.light-input-num:focus {
  border-color: #00ffd8;
  outline: none;
  box-shadow: 0 0 5px rgba(0, 255, 216, 0.3);
}

.light-slider-container {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 200px;
}

.light-slider {
  flex-grow: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  outline: none;
  cursor: pointer;
  accent-color: #00ffd8;
}

.light-val-text {
  font-size: 12px;
  color: #00ffd8;
  width: 45px;
  text-align: right;
  font-family: monospace;
}

.light-slider-input {
  width: 60px;
  background: rgba(4, 10, 20, 0.8);
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 4px;
  padding: 4px 6px;
  color: #00ffd8;
  font-size: 12px;
  text-align: center;
  transition: border-color 0.2s;
  font-family: monospace;
}
.light-slider-input:focus {
  border-color: #00ffd8;
  outline: none;
  box-shadow: 0 0 5px rgba(0, 255, 216, 0.3);
}
/* 隐藏默认上下箭头 */
.light-slider-input::-webkit-outer-spin-button,
.light-slider-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.light-slider-input[type=number] {
  -moz-appearance: textfield;
}

.light-panel-buttons {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.light-btn {
  flex-grow: 1;
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-radius: 4px;
  padding: 6px 0;
  color: #00ffd8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.light-btn:hover {
  background: rgba(0, 229, 255, 0.2);
  border-color: #00ffd8;
  box-shadow: 0 0 8px rgba(0, 255, 216, 0.3);
}

.light-btn.btn-primary {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.3), rgba(0, 255, 216, 0.15));
  color: #ffffff;
  border-color: #00ffd8;
  font-weight: bold;
}
.light-btn.btn-primary:hover {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.45), rgba(0, 255, 216, 0.25));
  box-shadow: 0 0 12px rgba(0, 255, 216, 0.5);
}

.light-copied-msg {
  font-size: 11px;
  color: #10b981;
  text-align: center;
  margin-top: 4px;
  animation: fadeIn 0.2s ease-out;
}

/* 📡 两客一危 湖北省交通数字孪生智控终端 (右侧高精对称伸缩侧边栏) CSS */
.lkyw-monitor-hud.high-end-panel {
  position: absolute;
  top: 16px;
  bottom: 16px;
  right: 16px;
  width: 420px;
  height: calc(100% - 32px);
  background: rgba(10, 19, 35, 0.82);
  backdrop-filter: blur(20px) saturate(140%);
  display: flex;
  flex-direction: column;
  overflow: visible;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6), inset 0 0 15px rgba(0, 242, 254, 0.08);
  border: 1px solid rgba(0, 242, 254, 0.22);
  border-radius: 14px;
  z-index: 10;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  pointer-events: auto;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 0;
}

.lkyw-monitor-hud.high-end-panel.collapsed {
  transform: translateX(calc(100% + 20px));
}

/* 右侧侧边栏 对称 toggle-btn 折叠收缩按键 */
.toggle-btn-right-sidebar {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  left: -18px;
  width: 18px;
  height: 60px;
  background: rgba(10, 19, 35, 0.9);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-right: none;
  border-radius: 8px 0 0 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #00f2fe;
  font-size: 10px;
  transition: all 0.2s;
  z-index: 11;
  padding: 0;
}

.toggle-btn-right-sidebar:hover {
  color: #ffffff;
  background: rgba(0, 242, 254, 0.2);
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
}

/* 头部 Header 与左侧边栏完全对称对齐 */
.lkyw-monitor-hud .sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 242, 254, 0.15);
  background: rgba(0, 0, 0, 0.25);
  border-radius: 12px 12px 0 0;
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.lkyw-monitor-hud .sidebar-header::before {
  content: '';
  position: absolute;
  left: 0;
  top: 18px;
  bottom: 18px;
  width: 4px;
  background: #00f2fe;
  border-radius: 0 4px 4px 0;
  box-shadow: 0 0 8px rgba(0, 242, 254, 0.7);
}

.lkyw-monitor-hud .sidebar-title {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
}

.lkyw-monitor-hud .sidebar-subtitle {
  font-size: 11px;
  color: #00f2fe;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: inline-block;
  margin-top: 3px;
  opacity: 0.85;
}

.lkyw-hud-status-badge {
  font-size: 10px;
  font-family: monospace;
  font-weight: bold;
  color: #00ffaa;
  background: rgba(0, 255, 170, 0.12);
  border: 1px solid rgba(0, 255, 170, 0.35);
  padding: 3px 8px;
  border-radius: 4px;
  white-space: nowrap;
  letter-spacing: 0.5px;
  box-shadow: 0 0 8px rgba(0, 255, 170, 0.2);
}

/* 滚动内容区 */
.hud-scroll-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hud-scroll-content::-webkit-scrollbar {
  width: 6px;
}
.hud-scroll-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 99px;
}

/* 四角发光装甲装饰 */
.hud-corner {
  position: absolute;
  width: 8px;
  height: 8px;
  border-color: #00ffd8;
  border-style: solid;
  pointer-events: none;
  filter: drop-shadow(0 0 4px #00ffd8);
}
.hud-corner.top-left { top: -1px; left: -1px; border-width: 2px 0 0 2px; border-top-left-radius: 4px; }
.hud-corner.top-right { top: -1px; right: -1px; border-width: 2px 2px 0 0; border-top-right-radius: 4px; }
.hud-corner.bottom-left { bottom: -1px; left: -1px; border-width: 0 0 2px 2px; border-bottom-left-radius: 4px; }
.hud-corner.bottom-right { bottom: -1px; right: -1px; border-width: 0 2px 2px 0; border-bottom-right-radius: 4px; }

.lkyw-hud-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  padding-bottom: 8px;
  margin-bottom: 10px;
}

.header-main-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 8px;
}

.header-title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.hud-title-icon {
  font-size: 14px;
  filter: drop-shadow(0 0 4px rgba(0, 229, 255, 0.8));
}

.lkyw-hud-title {
  color: #00ffd8;
  font-size: 13px;
  font-weight: bold;
  letter-spacing: 0.5px;
  text-shadow: 0 0 8px rgba(0, 255, 216, 0.4);
}

.lkyw-hud-status-badge {
  font-size: 9.5px;
  color: #00ffaa;
  background: rgba(0, 255, 170, 0.12);
  border: 1px solid rgba(0, 255, 170, 0.35);
  border-radius: 10px;
  padding: 2px 8px;
  font-family: monospace;
  box-shadow: 0 0 8px rgba(0, 255, 170, 0.2);
}

/* 视图切换 Tabs */
.hud-mode-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}

.mode-btn {
  flex: 1;
  padding: 5px 0;
  background: rgba(0, 229, 255, 0.05);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 6px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.mode-btn:hover {
  background: rgba(0, 229, 255, 0.15);
  color: #00ffd8;
}

.mode-btn.active {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.25), rgba(0, 255, 170, 0.15));
  border-color: #00ffd8;
  color: #ffffff;
  box-shadow: 0 0 10px rgba(0, 255, 216, 0.3);
}

/* ⚠️ 风险预警 & 卡口排行 & 智能推演 — 统一对称左侧栏风格 CSS */
.hud-tab-pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: tabFadeIn 0.3s ease-out;
}

/* 风险矩阵概览 4格统计 */
.risk-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.risk-summary-item {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 8px 4px;
  text-align: center;
  transition: border-color 0.2s;
}
.risk-summary-item:hover {
  border-color: rgba(0, 242, 254, 0.35);
}
/* 状态色仅用于左侧竖边线，不污染背景 */
.risk-summary-item.red  { border-left: 3px solid rgba(255, 80, 100, 0.6); }
.risk-summary-item.gold { border-left: 3px solid rgba(0, 242, 254, 0.5); }
.risk-summary-item.orange { border-left: 3px solid rgba(200, 220, 255, 0.4); }
.risk-summary-item.blue { border-left: 3px solid rgba(0, 242, 254, 0.6); }

.risk-num {
  font-size: 18px;
  font-weight: 700;
  display: block;
  color: #00f2fe;
}
/* 高危数字用白色+下划线区分，不用红色 */
.risk-summary-item.red .risk-num { color: #ffffff; }

.risk-lbl {
  font-size: 10px;
  color: #64748b;
  white-space: nowrap;
}

/* 风险车辆列表 */
.risk-vehicle-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.risk-card-item {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.2s ease;
}
.risk-card-item:hover {
  border-color: rgba(0, 242, 254, 0.35);
  background: rgba(15, 23, 42, 0.7);
}
/* 风险等级用左侧竖线区分，避免过于刺眼 */
.risk-card-item.high-risk { border-left: 3px solid rgba(255, 90, 100, 0.7); }
.risk-card-item.mid-risk  { border-left: 3px solid rgba(0, 242, 254, 0.5); }
.risk-card-item.low-risk  { border-left: 3px solid rgba(0, 242, 254, 0.25); }

.risk-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.risk-plate {
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
}
.risk-type-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(0, 242, 254, 0.08);
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.2);
}
/* 不同类型用同色系，仅透明度区分 */
.risk-type-tag.hazard    { color: #e2e8f0; border-color: rgba(200,200,200,0.2); }
.risk-type-tag.passenger { color: #00f2fe; }
.risk-type-tag.tourist   { color: #a5d8ff; border-color: rgba(0,200,255,0.2); }

.risk-level-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}
.risk-level-badge.red    { background: rgba(255,80,100,0.15); color: #fca5a5; border: 1px solid rgba(255,80,100,0.3); }
.risk-level-badge.orange { background: rgba(0, 242, 254, 0.08); color: #a5d8ff; border: 1px solid rgba(0,242,254,0.2); }
.risk-level-badge.gold   { background: rgba(0, 242, 254, 0.05); color: #94a3b8; border: 1px solid rgba(0,242,254,0.15); }

.risk-reason {
  font-size: 11px;
  color: #cbd5e1;
  font-weight: 500;
}
.risk-meta-row {
  font-size: 11px;
  color: #64748b;
}

.risk-action-btn {
  align-self: flex-end;
  background: transparent;
  border: 1px solid rgba(0, 242, 254, 0.3);
  color: #00f2fe;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.risk-action-btn:hover {
  background: rgba(0, 242, 254, 0.1);
  border-color: rgba(0, 242, 254, 0.5);
  color: #ffffff;
}

/* 卡口排行卡片 */
.checkpoint-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.checkpoint-card {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s;
}
.checkpoint-card:hover {
  border-color: rgba(0, 242, 254, 0.3);
  background: rgba(15, 23, 42, 0.7);
}
.cp-rank-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cp-rank {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}
/* 排名标识使用青色深色调，避免金色/银色刺眼 */
.cp-rank.gold   { background: rgba(0, 242, 254, 0.2); color: #ffffff; border: 1px solid rgba(0,242,254,0.4); }
.cp-rank.silver { background: rgba(0, 242, 254, 0.08); color: #a5d8ff; border: 1px solid rgba(0,242,254,0.2); }
.cp-rank.border { background: rgba(255,255,255,0.05); color: #94a3b8; border: 1px solid rgba(255,255,255,0.12); }

.cp-name {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  flex: 1;
  margin-left: 8px;
}
.cp-status {
  font-size: 10px;
  font-weight: 600;
}
.cp-status.green  { color: #00f2fe; }
.cp-status.gold   { color: #a5d8ff; }
.cp-status.orange { color: #94a3b8; }

.cp-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  background: rgba(0, 0, 0, 0.2);
  padding: 8px;
  border-radius: 6px;
  border: 1px solid rgba(0, 242, 254, 0.08);
}
.cp-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.cp-label {
  font-size: 10px;
  color: #64748b;
}
.cp-val {
  font-size: 13px;
  font-weight: 700;
  color: #00f2fe;
}
.cp-val.green  { color: #00f2fe; }
.cp-val.gold   { color: #a5d8ff; }
.cp-val.orange { color: #cbd5e1; }
.cp-val small { font-size: 9px; font-weight: normal; color: #64748b; }

/* 智能推演 */
.ai-metrics-panel {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}
.ai-lbl { color: #94a3b8; }
.ai-val { font-weight: 600; color: #00f2fe; }
.ai-val.highlight { color: #00f2fe; }
.ai-val.green     { color: #00f2fe; }
.ai-val.gold      { color: #a5d8ff; }

.resource-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.resource-card {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 8px;
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: border-color 0.2s;
}
.resource-card:hover {
  border-color: rgba(0, 242, 254, 0.3);
}
.res-icon { font-size: 18px; opacity: 0.85; }
.res-info { display: flex; flex-direction: column; gap: 2px; }
.res-title {
  font-size: 11px;
  font-weight: 600;
  color: #cbd5e1;
}
.res-val {
  font-size: 11px;
  font-weight: 600;
  color: #00f2fe;
}
.res-val.green { color: #00f2fe; }
.res-val.blue  { color: #a5d8ff; }
.res-val.gold  { color: #94a3b8; }

.ai-dispatch-btn {
  width: 100%;
  margin-top: 6px;
  padding: 10px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid rgba(0, 242, 254, 0.4);
  color: #00f2fe;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  letter-spacing: 0.5px;
}
.ai-dispatch-btn:hover {
  background: rgba(0, 242, 254, 0.12);
  border-color: rgba(0, 242, 254, 0.7);
  color: #ffffff;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.25);
}



.cyber-border-flow-panel {
  margin-bottom: 12px;
  background: linear-gradient(135deg, rgba(8, 20, 38, 0.9), rgba(12, 28, 52, 0.9));
  border: 1px solid rgba(0, 255, 216, 0.35);
  border-radius: 8px;
  padding: 10px 12px;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.12);
  position: relative;
}

.border-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 5px;
  border-bottom: 1px dashed rgba(0, 229, 255, 0.2);
}

.border-title {
  font-size: 11.5px;
  font-weight: bold;
  color: #00ffd8;
  letter-spacing: 0.5px;
  text-shadow: 0 0 6px rgba(0, 255, 216, 0.5);
}

.net-inflow-badge {
  font-size: 9.5px;
  padding: 1px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-weight: bold;
}
.net-inflow-badge.pos {
  background: rgba(0, 255, 170, 0.15);
  color: #00ffaa;
  border: 0.5px solid rgba(0, 255, 170, 0.4);
}
.net-inflow-badge.neg {
  background: rgba(255, 77, 109, 0.15);
  color: #ff4d6d;
  border: 0.5px solid rgba(255, 77, 109, 0.4);
}

.border-flow-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.border-flow-card {
  background: rgba(4, 12, 24, 0.7);
  border-radius: 6px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.border-flow-card.in {
  border: 1px solid rgba(0, 255, 170, 0.4);
  box-shadow: inset 0 0 10px rgba(0, 255, 170, 0.1);
}

.border-flow-card.out {
  border: 1px solid rgba(255, 215, 0, 0.4);
  box-shadow: inset 0 0 10px rgba(255, 215, 0, 0.1);
}

.border-flow-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.flow-label {
  font-size: 10px;
  color: #94a3b8;
  font-weight: bold;
}

.flow-anim-arrow {
  font-family: monospace;
  font-size: 10px;
  font-weight: bold;
  letter-spacing: -1px;
}
.flow-anim-arrow.green { color: #00ffaa; animation: arrowPulseGreen 1.2s infinite linear; }
.flow-anim-arrow.gold { color: #ffd700; animation: arrowPulseGold 1.2s infinite linear; }

@keyframes arrowPulseGreen {
  0% { opacity: 0.3; transform: translateX(-2px); }
  50% { opacity: 1; transform: translateX(2px); text-shadow: 0 0 6px #00ffaa; }
  100% { opacity: 0.3; transform: translateX(-2px); }
}

@keyframes arrowPulseGold {
  0% { opacity: 0.3; transform: translateX(2px); }
  50% { opacity: 1; transform: translateX(-2px); text-shadow: 0 0 6px #ffd700; }
  100% { opacity: 0.3; transform: translateX(2px); }
}

.border-flow-val {
  font-size: 16px;
  font-weight: bold;
  font-family: monospace;
}
.border-flow-val.green { color: #00ffaa; text-shadow: 0 0 8px rgba(0, 255, 170, 0.4); }
.border-flow-val.gold { color: #ffd700; text-shadow: 0 0 8px rgba(255, 215, 0, 0.4); }

.flow-unit {
  font-size: 9.5px;
  color: #64748b;
  font-weight: normal;
}

/* 赛博卡片级 进出省对撞数据舱 */
.cyber-flow-box-group {
  display: flex;
  gap: 6px;
}

.cyber-flow-box {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 3px 7px;
  border-radius: 4px;
  font-size: 10px;
  font-family: monospace;
  transition: all 0.3s ease;
}

.cyber-flow-box.in {
  background: rgba(0, 255, 170, 0.08);
  border: 1px solid rgba(0, 255, 170, 0.35);
}
.cyber-flow-box.out {
  background: rgba(255, 215, 0, 0.08);
  border: 1px solid rgba(255, 215, 0, 0.35);
}

.cyber-flow-box.flash {
  transform: scale(1.05);
  box-shadow: 0 0 10px currentColor;
}

.box-icon {
  font-size: 9px;
  font-weight: bold;
  color: #cbd5e1;
}

.box-val {
  font-weight: bold;
  font-size: 11px;
}
.box-val.green { color: #00ffaa; }
.box-val.gold { color: #ffd700; }

/* 图表 Block 通用样式 */
.hud-chart-section {
  margin-top: 10px;
  background: rgba(10, 20, 36, 0.6);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 8px;
  padding: 10px 12px;
}

.chart-title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 4px;
}

.chart-title {
  font-size: 11.5px;
  font-weight: bold;
  color: #e2f1ff;
  letter-spacing: 0.5px;
}

.chart-sub {
  font-size: 9.5px;
  color: #64748b;
  font-family: monospace;
}

/* 🍩 极光 SVG 饼图样式 */
.pie-chart-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.svg-pie-wrapper {
  position: relative;
  width: 90px;
  height: 90px;
  flex-shrink: 0;
}

.pie-svg {
  width: 100%;
  height: 100%;
}

.pie-arc {
  transition: stroke-dasharray 0.8s ease, stroke-dashoffset 0.8s ease;
  filter: drop-shadow(0 0 4px currentColor);
}

.pie-center-info {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.pie-total-num {
  font-size: 13px;
  font-weight: bold;
  color: #ffffff;
  font-family: monospace;
  line-height: 1;
}

.pie-total-unit {
  font-size: 8.5px;
  color: #64748b;
  margin-top: 2px;
}

.pie-legend {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  padding: 3px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: background 0.2s ease;
}

.legend-row:hover {
  background: rgba(0, 229, 255, 0.1);
}

.legend-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.legend-dot.red { background: #FF2D55; box-shadow: 0 0 6px #FF2D55; }
.legend-dot.green { background: #00E676; box-shadow: 0 0 6px #00E676; }
.legend-dot.blue { background: #00B0FF; box-shadow: 0 0 6px #00B0FF; }

.legend-name {
  color: #cbd5e1;
  font-size: 10.5px;
  flex-grow: 1;
}

.legend-val {
  font-weight: bold;
  font-family: monospace;
  font-size: 11px;
}
.legend-val.red { color: #ff4d6d; }
.legend-val.green { color: #00ffaa; }
.legend-val.blue { color: #00f0ff; }

/* 📊 3D 柱状图样式 */
.bar-chart-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.bar-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10.5px;
}

.highway-name {
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 5px;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  font-size: 9px;
  font-style: normal;
  font-family: monospace;
}

.rank-badge.rank-1 { background: rgba(255, 77, 109, 0.25); color: #ff4d6d; border: 1px solid rgba(255, 77, 109, 0.5); }
.rank-badge.rank-2 { background: rgba(255, 215, 0, 0.25); color: #ffd700; border: 1px solid rgba(255, 215, 0, 0.5); }
.rank-badge.rank-3 { background: rgba(0, 229, 255, 0.25); color: #00ffd8; border: 1px solid rgba(0, 229, 255, 0.5); }

.bar-val-block {
  display: flex;
  align-items: center;
  gap: 6px;
}

.bar-count {
  font-family: monospace;
  font-weight: bold;
  color: #00ffd8;
  font-size: 11px;
}

.hazard-tag {
  font-size: 8.5px;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(0, 255, 170, 0.1);
  color: #00ffaa;
  border: 1px solid rgba(0, 255, 170, 0.25);
  font-family: monospace;
}

.hazard-tag.alert {
  background: rgba(255, 77, 109, 0.15);
  color: #ff4d6d;
  border-color: rgba(255, 77, 109, 0.4);
}

.bar-track {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(0, 229, 255, 0.4), rgba(0, 255, 170, 0.9));
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.25, 1, 0.5, 1);
  position: relative;
  box-shadow: 0 0 8px rgba(0, 255, 170, 0.4);
}

.bar-fill.high {
  background: linear-gradient(90deg, rgba(255, 160, 0, 0.6), rgba(255, 45, 85, 0.95));
  box-shadow: 0 0 8px rgba(255, 45, 85, 0.5);
}

.bar-glow-cap {
  position: absolute;
  right: 0;
  top: 0;
  width: 3px;
  height: 100%;
  background: #ffffff;
  box-shadow: 0 0 6px #ffffff;
  border-radius: 2px;
}

/* 📸 实时抓拍流列表 CSS */
.camera-log-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.camera-log-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  padding: 3px 6px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.camera-log-item.newest {
  border-color: rgba(0, 255, 216, 0.4);
  background: rgba(0, 229, 255, 0.1);
  animation: logSlideIn 0.4s ease-out;
}

@keyframes logSlideIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.log-time {
  font-family: monospace;
  color: #64748b;
  font-size: 9px;
}

.log-loc {
  color: #cbd5e1;
  font-size: 9.5px;
  max-width: 95px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-plate {
  font-family: monospace;
  font-weight: bold;
  color: #00ffd8;
  font-size: 10px;
}

.log-tag {
  font-size: 8.5px;
  padding: 0px 4px;
  border-radius: 3px;
  font-family: monospace;
}

.log-tag.in {
  background: rgba(0, 255, 170, 0.15);
  color: #00ffaa;
  border: 0.5px solid rgba(0, 255, 170, 0.3);
}

.log-tag.out {
  background: rgba(255, 215, 0, 0.15);
  color: #ffd700;
  border: 0.5px solid rgba(255, 215, 0, 0.3);
}

.lkyw-hud-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lkyw-hud-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.lkyw-hud-card:hover {
  background: rgba(15, 23, 42, 0.9);
  transform: translateX(-2px);
}

.lkyw-hud-card.hazard.active, .lkyw-hud-card.hazard:hover {
  border-color: rgba(255, 77, 109, 0.6);
  box-shadow: 0 0 10px rgba(255, 77, 109, 0.2);
}

.lkyw-hud-card.passenger.active, .lkyw-hud-card.passenger:hover {
  border-color: rgba(0, 255, 170, 0.6);
  box-shadow: 0 0 10px rgba(0, 255, 170, 0.2);
}

.lkyw-hud-card.tourist.active, .lkyw-hud-card.tourist:hover {
  border-color: rgba(0, 240, 255, 0.6);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.2);
}

.lkyw-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.lkyw-icon {
  font-size: 13px;
}

.lkyw-label {
  font-size: 12px;
  color: #cbd5e1;
  font-weight: bold;
}

.lkyw-subbadge {
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: auto;
}

.lkyw-subbadge.red {
  background: rgba(255, 77, 109, 0.15);
  color: #ff4d6d;
  border: 0.5px solid rgba(255, 77, 109, 0.4);
}

.lkyw-subbadge.green {
  background: rgba(0, 255, 170, 0.15);
  color: #00ffaa;
  border: 0.5px solid rgba(0, 255, 170, 0.4);
}

.lkyw-subbadge.blue {
  background: rgba(0, 240, 255, 0.15);
  color: #00f0ff;
  border: 0.5px solid rgba(0, 240, 255, 0.4);
}

.lkyw-card-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-top: 4px;
}

.lkyw-val-block {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.lkyw-value {
  font-size: 17px;
  font-weight: bold;
  font-family: monospace;
  transition: all 0.3s ease;
}

.lkyw-value.red { color: #ff4d6d; }
.lkyw-value.green { color: #00ffaa; }
.lkyw-value.blue { color: #00f0ff; }

.lkyw-value.pulse {
  animation: numPulse 0.6s ease-out;
}

@keyframes numPulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); filter: brightness(1.5); }
  100% { transform: scale(1); }
}

.lkyw-unit {
  font-size: 10px;
  color: #64748b;
}

.lkyw-border-flow {
  display: flex;
  gap: 5px;
}

.flow-tag {
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 9.5px;
  font-family: monospace;
  transition: all 0.3s ease;
}

.flow-tag.in {
  background: rgba(0, 255, 170, 0.12);
  color: #00ffaa;
  border: 1px solid rgba(0, 255, 170, 0.3);
}

.flow-tag.out {
  background: rgba(255, 215, 0, 0.12);
  color: #ffd700;
  border: 1px solid rgba(255, 215, 0, 0.3);
}

.flow-tag.flash {
  transform: scale(1.12);
  box-shadow: 0 0 10px currentColor;
}

.lkyw-card-footer-tip {
  margin-top: 6px;
  padding-top: 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 9.5px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot-indicator {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.dot-indicator.red { background: #ff2d55; box-shadow: 0 0 6px #ff2d55; }
.dot-indicator.green { background: #00e676; box-shadow: 0 0 6px #00e676; }
.dot-indicator.blue { background: #00b0ff; box-shadow: 0 0 6px #00b0ff; }

.lkyw-hud-footer {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #94a3b8;
}

.lkyw-footer-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.dot.gold { background: #ffe082; box-shadow: 0 0 4px #ffe082; }
.dot.green { background: #00ffaa; box-shadow: 0 0 4px #00ffaa; }

/* 🛠️ 右下角微调控制台 悬浮按钮 Dock */
.bottom-right-tool-dock {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 1025;
  display: flex;
  gap: 10px;
  background: rgba(5, 14, 26, 0.88);
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid rgba(0, 229, 255, 0.35);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.7), 0 0 15px rgba(0, 229, 255, 0.15);
  backdrop-filter: blur(12px);
}

.dock-tool-btn {
  background: rgba(10, 25, 45, 0.7);
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: bold;
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  user-select: none;
}

.dock-tool-btn.camera-btn {
  border: 1px dashed #00ffd8;
  color: #00ffd8;
}
.dock-tool-btn.camera-btn:hover,
.dock-tool-btn.camera-btn.active {
  background: rgba(0, 229, 255, 0.25);
  border-style: solid;
  border-color: #00ffd8;
  box-shadow: 0 0 15px rgba(0, 255, 216, 0.5);
}

.dock-tool-btn.traffic-btn {
  border: 1px dashed #ffd700;
  color: #ffd700;
}
.dock-tool-btn.traffic-btn:hover,
.dock-tool-btn.traffic-btn.active {
  background: rgba(255, 215, 0, 0.25);
  border-style: solid;
  border-color: #ffd700;
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.5);
}

.dock-tool-btn.light-btn {
  border: 1px dashed #38bdf8;
  color: #38bdf8;
}
.dock-tool-btn.light-btn:hover,
.dock-tool-btn.light-btn.active {
  background: rgba(56, 189, 248, 0.25);
  border-style: solid;
  border-color: #38bdf8;
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.5);
}

/* 🛠️ 右下角微调弹窗面板堆叠容器 */
.bottom-right-panels-stack {
  position: absolute;
  bottom: 75px;
  right: 20px;
  z-index: 1020;
  display: flex;
  flex-direction: column-reverse;
  align-items: flex-end;
  gap: 12px;
  max-height: calc(100vh - 150px);
  overflow-y: auto;
  pointer-events: none;
  padding-right: 2px;
}

.bottom-right-panels-stack > * {
  pointer-events: auto;
  position: relative !important;
  top: auto !important;
  bottom: auto !important;
  right: auto !important;
  margin: 0 !important;
}

/* 车流调节 弹窗面板 */
.traffic-adjust-modal {
  border-color: #ffd700 !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8), 0 0 20px rgba(255, 215, 0, 0.25) !important;
}

.gold-title {
  color: #ffd700 !important;
  text-shadow: 0 0 8px rgba(255, 215, 0, 0.5) !important;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.gold-tag {
  font-size: 12px;
  font-family: monospace;
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 215, 0, 0.15);
  border: 1px solid rgba(255, 215, 0, 0.4);
  color: #ffd700;
}

.gold-slider {
  accent-color: #ffd700 !important;
}

.gold-input {
  border-color: #d4af37 !important;
  color: #ffd700 !important;
}

.gold-btn {
  background: rgba(255, 215, 0, 0.15) !important;
  border: 1px solid #ffd700 !important;
  color: #ffd700 !important;
}

.gold-btn:hover {
  background: rgba(255, 215, 0, 0.3) !important;
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.5) !important;
}

/* 车辆类型筛选 Tabs */
.vehicle-filter-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.vehicle-filter-tabs button {
  flex: 1;
  min-width: 70px;
  padding: 6px 8px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 215, 0, 0.3);
  color: #cbd5e1;
  font-size: 11px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.vehicle-filter-tabs button.active {
  background: rgba(255, 215, 0, 0.2);
  border-color: #ffd700;
  color: #ffd700;
  font-weight: bold;
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
}


/* 📹 全阶段相机视角微调工具 弹窗面板 */
.camera-adjust-modal {
  width: 380px;
  background: linear-gradient(180deg, rgba(9, 25, 43, 0.96) 0%, rgba(5, 14, 26, 0.96) 100%);
  border: 1.5px solid #00ffd8;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 255, 216, 0.25);
  backdrop-filter: blur(12px);
  color: #ffffff;
  overflow: hidden;
  animation: modalFadeIn 0.3s ease-out;
}

@keyframes modalFadeIn {
  from { opacity: 0; transform: translateY(-10px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.camera-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(0, 229, 255, 0.08);
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
}

.camera-modal-header .header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: bold;
  color: #00ffd8;
  text-shadow: 0 0 8px rgba(0, 255, 216, 0.5);
}

.camera-modal-header .close-btn {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #a0aec0;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.camera-modal-header .close-btn:hover {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

.camera-modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 场景切换 */
.scene-toggle-group {
  display: flex;
  gap: 10px;
}

.scene-toggle-group button {
  flex: 1;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 229, 255, 0.3);
  color: #a0aec0;
  font-size: 13px;
  font-weight: bold;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.scene-toggle-group button.active {
  background: rgba(0, 229, 255, 0.15);
  border-color: #00ffd8;
  color: #00ffd8;
  box-shadow: inset 0 0 10px rgba(0, 255, 216, 0.3), 0 0 10px rgba(0, 255, 216, 0.2);
}

/* 下拉框行 */
.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-label {
  font-size: 13px;
  color: #cbd5e1;
  min-width: 80px;
}

.phase-select {
  flex: 1;
  background: rgba(4, 15, 30, 0.9);
  border: 1px solid #00a8cc;
  border-radius: 6px;
  padding: 6px 12px;
  color: #00ffd8;
  font-size: 13px;
  outline: none;
  cursor: pointer;
}

/* 滑块行 */
.slider-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.slider-label {
  font-size: 13px;
  color: #cbd5e1;
}

.slider-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cyber-range-slider {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  outline: none;
  accent-color: #00ffd8;
  cursor: pointer;
}

.cyber-num-input {
  width: 70px;
  background: rgba(4, 15, 30, 0.9);
  border: 1px solid #00a8cc;
  border-radius: 6px;
  padding: 4px 8px;
  color: #00ffd8;
  font-size: 13px;
  font-family: monospace;
  text-align: center;
  outline: none;
}

.cyber-num-input:focus {
  border-color: #00ffd8;
  box-shadow: 0 0 8px rgba(0, 255, 216, 0.4);
}

/* 按钮组 */
.btn-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 6px;
}

.action-btn-reset,
.action-btn-copy {
  width: 100%;
  padding: 10px 0;
  border-radius: 6px;
  font-size: 13px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.action-btn-reset {
  background: rgba(0, 229, 255, 0.12);
  border: 1px solid #00c8e6;
  color: #00ffd8;
}

.action-btn-reset:hover {
  background: rgba(0, 229, 255, 0.25);
  box-shadow: 0 0 12px rgba(0, 255, 216, 0.4);
}

.action-btn-copy {
  background: rgba(0, 160, 200, 0.25);
  border: 1px solid #00ffd8;
  color: #ffffff;
}

.action-btn-copy:hover {
  background: rgba(0, 229, 255, 0.4);
  box-shadow: 0 0 15px rgba(0, 255, 216, 0.5);
}

.copied-feedback {
  font-size: 12px;
  color: #00ffd8;
  text-align: center;
  margin-top: 4px;
}

/* 🏷️ 地图行政区划标注字号控制台 */
.map-label-style-control {
  margin-bottom: 12px;
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(0, 242, 254, 0.25);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 0 15px rgba(0, 242, 254, 0.08);
}

.control-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-title {
  font-size: 12px;
  font-weight: 600;
  color: #ffffff;
}

.control-value-badge {
  font-size: 11px;
  font-weight: 700;
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid rgba(0, 242, 254, 0.3);
  padding: 1px 8px;
  border-radius: 10px;
  font-family: monospace;
}

.control-slider-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.size-icon {
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
}

.size-icon.big {
  font-size: 14px;
  color: #00f2fe;
}

.dock-tool-btn.label-btn {
  background: rgba(0, 242, 254, 0.1);
  border-color: rgba(0, 242, 254, 0.3);
  color: #00f2fe;
}

.dock-tool-btn.label-btn:hover,
.dock-tool-btn.label-btn.active {
  background: rgba(0, 242, 254, 0.25);
  border-color: #00f2fe;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.4);
}

/* 6灯光选项卡选择样式 */
.light-select-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  width: 200px;
}

.light-tab-btn {
  flex-grow: 1;
  min-width: 58px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  padding: 4px 0;
  color: #a0aec0;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.light-tab-btn:hover {
  background: rgba(0, 229, 255, 0.1);
  border-color: rgba(0, 229, 255, 0.4);
  color: #00ffd8;
}

.light-tab-btn.active {
  background: rgba(0, 229, 255, 0.25);
  border-color: #00ffd8;
  color: #ffffff;
  box-shadow: 0 0 8px rgba(0, 255, 216, 0.2);
}
</style>



<style>
.flying-photo {
  position: fixed;
  z-index: 9999;
  background-size: cover;
  background-position: center;
  border: 2px solid #00e5ff;
  border-radius: 4px;
  box-shadow: 0 0 15px rgba(0, 229, 255, 0.8);
  transition: all 0.8s cubic-bezier(0.25, 1, 0.5, 1);
  pointer-events: none;
}
</style>