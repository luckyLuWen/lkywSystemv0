<template>
  <div class="cesium-wrapper">
    <div id="cesiumContainer" ref="containerRef" class="cesium-container"></div>
    <div v-if="overviewAccident" class="accident-detail-backdrop" @click.self="overviewAccident = null" @keydown.esc="overviewAccident = null">
      <section class="accident-detail" role="dialog" aria-modal="true" aria-labelledby="accident-detail-title" tabindex="-1">
        <header><span>⚠ 历史事故档案 · {{ overviewAccident.city }}</span><button autofocus aria-label="关闭事故详情" @click="overviewAccident = null">×</button></header>
        <h2 id="accident-detail-title">{{ overviewAccident.title }}</h2>
        <div class="overview-accident-body">
          <figure><img v-if="overviewAccident.image" :src="overviewAccident.image" :alt="overviewAccident.title + '真实现场照片'" /><div v-else class="accident-photo-pending">现场原图待补充<br />可点击右侧来源查看事故报道</div></figure>
          <div><p class="accident-detail-date">{{ overviewAccident.date }}</p><p>{{ overviewAccident.location }}</p><p>{{ overviewAccident.description }}</p><a :href="overviewAccident.source" target="_blank" rel="noopener noreferrer">查看新闻来源与现场资料 ↗</a></div>
        </div>
      </section>
    </div>
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
    <div style="position: absolute; top: 20px; left: 20px; z-index: 2000; display: flex; flex-direction: column; gap: 20px; align-items: flex-start;">
      
      <!-- 1. 上方：立体传感网智能协同矩阵 (增加强制 relative，剥夺其绝对定位权，禁止重叠) -->
      <div 
        class="sensor-fusion-panel" 
        v-if="showFusionPanel"
        style="position: relative !important; top: auto !important; left: auto !important; bottom: auto !important; transform: none !important; margin: 0 !important;"
      >
        <div class="fusion-header">
          <span class="icon">🔗</span>
          <span class="title">立体传感网智能协同矩阵</span>
          <div class="pulse-indicator"></div>
        </div>
        
        <ul class="fusion-list">
          <li>
            <span class="node-name">🚗 车载节点</span>
            <span class="status-tag" :class="sensorFusionState.car.statusClass">{{ sensorFusionState.car.text }}</span>
          </li>
          <li>
            <span class="node-name">💡 路侧节点</span>
            <span class="status-tag" :class="sensorFusionState.light.statusClass">{{ sensorFusionState.light.text }}</span>
          </li>
          <li>
            <span class="node-name">🚁 空基节点</span>
            <span class="status-tag" :class="sensorFusionState.uav.statusClass">{{ sensorFusionState.uav.text }}</span>
          </li>
          <li>
            <span class="node-name">🚙 地基节点</span>
            <span class="status-tag" :class="sensorFusionState.ugv.statusClass">{{ sensorFusionState.ugv.text }}</span>
          </li>
        </ul>

        <div class="fusion-footer">
          <div class="footer-row">
            <span>综合协同研判:</span>
            <strong :class="{'text-red': props.activePhaseIndex >= 2}">{{ sensorFusionState.resultText }}</strong>
          </div>
          <div class="footer-row">
            <span>多源融合置信度:</span>
            <strong class="text-cyan">{{ sensorFusionState.confidence }}</strong>
          </div>
        </div>
      </div>

      <!-- 2. 下方：阶段十 传感网原型放大镜悬浮窗 (同样剥夺绝对定位权，自动排在下方) -->
      <div 
        v-if="activePhaseIndex === 9 && showMagnifier" 
        class="prototype-magnifier-popup"
        style="position: relative !important; top: auto !important; left: auto !important; bottom: auto !important; transform: none !important; margin: 0 !important;"
      >
        <div class="popup-header">
          <span class="icon">🔍</span>
          <span class="title">立体组网传感网原型解析</span>
          <button class="close-btn" @click="showMagnifier = false">×</button>
        </div>

        <div class="popup-body">
          <div class="prototype-image-container">
            <img src="/Dashboard/images/传感网原型.png" alt="传感网原型" class="custom-prototype-img" />
          </div>

          <div class="prototype-desc">
            <h4 class="desc-title">多源异构感知架构</h4>
            <ul class="desc-list">
              <li><strong>高速通信链路：</strong>核心控制指令通过 WebSocket 协议全双工直达底层节点，确保低延迟。</li>
              <li><strong>空基巡航层：</strong>无人机搭载红外热成像相机，执行大范围视场唤醒与全局热点追踪。</li>
              <li><strong>地基监测层：</strong>两台无人车呈非线性包围态势，挂载五类传感器监测阵列抵近核心区采样。</li>
              <li><strong>泛在基础设施：</strong>智慧路灯与通信基站提供基础环境支撑与边缘计算中继。</li>
            </ul>
          </div>
        </div>
      </div>

    </div>
    <!-- 湖北省地图车辆运行图例：在综合态势未选中的迎宾地图右上角显示。 -->
    <Transition name="legend-slide">
      <div
        v-if="props.landingView && !props.focusedPointId"
        class="hubei-map-legend"
        :style="{ right: legendRightOffset }"
      >
        <div class="legend-header">
          <span class="legend-title">两客一危 运行图例</span>
        </div>
        <div class="legend-body">
          <!-- 危化品车 -->
          <div class="legend-row hazard-row" :style="{ borderLeftColor: MAP_VEHICLE_STYLES.hazard.color }">
            <span class="legend-glow-dot" :style="{ backgroundColor: MAP_VEHICLE_STYLES.hazard.color }"></span>
            <span class="legend-text-main">危化品运输车</span>
          </div>

          <!-- 公路客运 -->
          <div class="legend-row legend-guide-row" style="--guide-color: #9ed9e5" title="重点演示车辆">
            <i class="legend-map-guide__plate" aria-hidden="true">鄂</i><span class="legend-text-main">车牌标签</span>
          </div>

          <!-- 旅游客运 -->
          <div class="legend-row tourist-row" :style="{ borderLeftColor: MAP_VEHICLE_STYLES.tourist.color }">
            <span class="legend-glow-dot" :style="{ backgroundColor: MAP_VEHICLE_STYLES.tourist.color }"></span>
            <span class="legend-text-main">旅游客运</span>
          </div>
          <div class="legend-row legend-guide-row" style="--guide-color: #87e2ef" title="湖北省范围">
            <i class="legend-map-guide__line" aria-hidden="true"></i><span class="legend-text-main">省域电子围栏</span>
          </div>
          <div class="legend-row passenger-row" :style="{ borderLeftColor: MAP_VEHICLE_STYLES.passenger.color }">
            <span class="legend-glow-dot" :style="{ backgroundColor: MAP_VEHICLE_STYLES.passenger.color }"></span>
            <span class="legend-text-main">公路客运</span>
          </div>
          <div class="legend-row legend-guide-row" style="--guide-color: #e6bb68" title="事故位置入口">
            <i class="legend-map-guide__alert" aria-hidden="true">!</i><span class="legend-text-main">警示标记</span>
          </div>
        </div>
      </div>
    </Transition>
    <div v-if="loading" class="globe-mask" role="status" aria-live="polite">
      <div class="globe-loading-content">
        <img class="globe-loading-image" draggable="false" src="/hud-assets/loading-wave.webp" alt="" />
        <span>三维地图加载中...</span>
      </div>
    </div>
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

    <!-- 故事线检测告警弹窗：事故发生 / 次生灾害起火 -->
    <div
      v-if="detectionPopup.show && currentStoryDetectionScenario"
      class="detection-popup-panel story-detection-alert"
      :class="`is-${currentStoryDetectionScenario.level}`"
      :style="{ left: detectionPopup.x + 'px', top: detectionPopup.y + 'px' }"
    >
      <div class="detection-popup-header">
        <div class="header-title-wrap">
          <span class="pulse-dot"></span>
          <span class="header-title">{{ currentStoryDetectionScenario.title }}</span>
        </div>
        <button class="close-btn" @click="detectionPopup.show = false">×</button>
      </div>

      <div class="detection-popup-content story-detection-content">
        <div class="detection-img-container story-detection-img-container">
          <img :src="currentStoryDetectionScenario.imageSrc" class="detection-raw-img" alt="事故检测画面" />

          <svg v-if="detectionPopup.state === 'detected'" class="detection-svg-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
            <g
              v-for="box in detectionPopup.boxes"
              :key="box.label"
              class="box-group"
            >
              <rect
                :x="box.x"
                :y="box.y"
                :width="box.width"
                :height="box.height"
                class="box-rect"
                :class="box.kind === 'fire' ? 'rect-story-fire' : 'rect-story-warning'"
              />
              <text
                :x="box.x"
                :y="Math.max(6, box.y - 3)"
                class="box-label story-box-label"
                :class="box.kind === 'fire' ? 'label-story-fire' : 'label-story-warning'"
              >
                {{ box.label }}
              </text>
            </g>
          </svg>

          <div v-if="detectionPopup.state === 'detecting'" class="scanning-line"></div>
          <div v-if="detectionPopup.state === 'detecting'" class="scanning-overlay">{{ currentStoryDetectionScenario.model }} 图像推理中...</div>
        </div>

        <div class="detection-control-panel story-result-panel">
          <div class="panel-section-title story-panel-title-row">
            <span>模型检测结果</span>
            <span
              v-if="detectionPopup.state !== 'detecting'"
              class="status-indicator"
              :class="currentStoryDetectionScenario.level === 'critical' ? 'critical' : 'warning'"
            >
              {{ currentStoryDetectionScenario.statusBadge }}
            </span>
          </div>
          <div class="story-model-row">
            <span>检测模型</span>
            <strong>{{ currentStoryDetectionScenario.model }}</strong>
          </div>
          <div v-if="detectionPopup.state === 'detecting'" class="state-detecting-wrap story-detecting-wrap">
            <div class="spinner"></div>
            <p class="loading-text">正在运行推理：{{ detectionPopup.progress }}%</p>
            <div class="progress-bar-container">
              <div class="progress-bar-fill" :style="{ width: detectionPopup.progress + '%' }"></div>
            </div>
          </div>

          <div v-else class="state-results-wrap story-results-wrap">
            <div class="story-confidence-grid">
              <div class="story-confidence-card">
                <span class="confidence-label">检测类别</span>
                <strong>{{ detectionPopup.modelClass || '--' }}</strong>
              </div>
              <div class="story-confidence-card emphasis">
                <span class="confidence-label">置信度</span>
                <strong>{{ formatDetectionConfidence(detectionPopup.confidence) }}</strong>
              </div>
            </div>

            <div v-if="detectionPopup.modelClassZh" class="story-zh-banner">
              <strong>{{ detectionPopup.modelClassZh }}</strong>
            </div>



            <div v-if="detectionPopup.error" class="story-detection-note">{{ detectionPopup.error }}</div>
          </div>
        </div>
      </div>

      <div v-if="detectionPopup.state !== 'detecting'" class="story-advice-bar">
        <div class="story-advice-main">
          <span class="story-advice-title">应对建议</span>
          <span class="story-advice-text">{{ currentStoryDetectionScenario.report }}</span>
        </div>
        <button class="reset-btn story-advice-action" @click="rerunStoryDetection">重新检测</button>
      </div>

      <div class="detection-popup-arrow"></div>
    </div>

    <!-- light1 路侧摄像头模拟监控视频 -->
    <div
      v-if="cameraStreamPopup.show"
      class="camera-stream-popup"
      :style="{ left: cameraStreamPopup.x + 'px', top: cameraStreamPopup.y + 'px' }"
    >
      <div class="camera-stream-header">
        <div class="camera-title-wrap">
          <span class="camera-live-dot"></span>
          <span class="camera-stream-title">{{ cameraStreamPopup.title }}</span>
        </div>
        <button class="close-btn" @click="cameraStreamPopup.show = false">×</button>
      </div>
      <div class="camera-stream-body">
        <div class="camera-video-wrap">
          <video
            ref="cameraStreamVideoRef"
            class="camera-stream-video"
            :src="cameraStreamPopup.videoSrc"
            autoplay
            muted
            loop
            playsinline
            controls
            @timeupdate="syncCameraVideoBoxes"
            @seeking="syncCameraVideoBoxes"
            @seeked="syncCameraVideoBoxes"
            @play="syncCameraVideoBoxes"
            @loadedmetadata="syncCameraVideoBoxes"
          ></video>
          <svg
            v-if="cameraStreamPopup.activeVideoBoxes.length"
            class="camera-video-overlay"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <g
              v-for="(box, index) in cameraStreamPopup.activeVideoBoxes"
              :key="`${box.label}-${index}`"
            >
              <rect
                :x="box.x"
                :y="box.y"
                :width="box.width"
                :height="box.height"
                :class="['camera-box-rect', box.kind]"
              />
              <text
                :x="box.x"
                :y="box.labelY"
                :class="['camera-box-label', box.kind]"
              >{{ box.label }} {{ box.confidence }}</text>
            </g>
          </svg>
        </div>
        <div class="camera-info-grid compact">
          <div class="camera-info-item online">
            <span>摄像头状态</span>
            <strong>{{ cameraStreamPopup.status }}</strong>
          </div>
          <div class="camera-info-item">
            <span>当前阶段</span>
            <strong>{{ props.phases?.[props.activePhaseIndex]?.shortLabel || '--' }}</strong>
          </div>
        </div>
        <div class="camera-detection-panel" :class="`is-${cameraStreamPopup.detectionState}`">
          <div class="camera-detection-head">
            <span>{{ cameraStreamPopup.modelName }} 视频检测</span>
            <strong>{{ cameraStreamPopup.detectionStatus }}</strong>
          </div>
          <div class="camera-detection-body">
            <template v-if="cameraStreamPopup.detectionState === 'done'">
              <div class="camera-live-result-head">
                <span>当前画面检测结果</span>
                <strong>{{ cameraStreamPopup.activeVideoBoxes.length ? '已识别' : '未检测到目标' }}</strong>
              </div>
              <div v-if="cameraStreamPopup.activeVideoBoxes.length" class="camera-live-result-list">
                <div
                  v-for="(box, index) in cameraStreamPopup.activeVideoBoxes"
                  :key="`${box.label}-${index}`"
                  class="camera-live-result-item"
                  :class="box.kind"
                >
                  <span>{{ box.label }}</span>
                  <strong>{{ box.confidence }}</strong>
                </div>
              </div>
            </template>
            <template v-else>
              <span>{{ cameraStreamPopup.detectionMessage }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 移除旧的独立 secondaryDisasterVideoPopup，已完全合并至下方的统一三维实景重构工作台中 -->


    <div
      v-if="simulationPopup.show && Number(props.activePhaseIndex) === 11 && (props.focusedPointId === 'accident_blue' || props.focusedPointId === 'accident_red')"
      class="simulation-popup-panel"
      :style="{ left: simulationPopup.x + 'px', top: simulationPopup.y + 'px' }"
    >
      <div class="simulation-popup-header">
        <div class="header-title-wrap">
          <span class="pulse-indicator"><i></i></span>
          <span class="header-title">救援路线仿真推演</span>
        </div>
        <button class="close-btn" @click="simulationPopup.show = false">×</button>
      </div>
      
      <div class="simulation-popup-content">
        <div class="status-tag-row">
          <span class="status-tag ready">{{ rescueDispatchPending ? '● 路线加载中…' : '● 救援路线' }}</span>
          <span class="status-tag info">路径规划</span>
        </div>
        <p class="desc-text">空地协同感知数据已同步，可查看当前事故现场的多智能体协同救援路线仿真推演方案。</p>
        
        <button class="enter-sim-btn" @click="enterSimulation">
          <span>开启路线仿真推演</span>
          <svg class="arrow-svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
          </svg>
        </button>
      </div>
      
      <div class="simulation-popup-arrow"></div>
    </div>

    <!-- ✈️ 无人机出发悬浮窗 -->
    <div
      v-if="rescuePopup.show" 
      class="shelter-popup-panel uav-dispatch-popup"
      :style="{ left: rescuePopup.x + 'px', top: rescuePopup.y + 'px' }"
    >
      <div class="shelter-popup-header uav-dispatch-header">
        <div class="dispatch-title-row">
          <span class="dispatch-icon">✈️</span>
          <span>{{ rescuePopup.title }}</span>
        </div>
        <button class="close-btn" @click="rescuePopup.show = false">×</button>
      </div>
      <table class="shelter-popup-table">
        <tbody>
          <tr>
            <td class="label">机型</td>
            <td class="value highlight-cyan">{{ rescuePopup.model }}</td>
          </tr>
          <tr>
            <td class="label">飞行高度</td>
            <td class="value">{{ rescuePopup.altitude }}</td>
          </tr>
          <tr>
            <td class="label">飞行速度</td>
            <td class="value">{{ rescuePopup.speed }}</td>
          </tr>
          <tr>
            <td class="label">出动状态</td>
            <td class="value status-launched">{{ rescuePopup.status }}</td>
          </tr>
        </tbody>
      </table>
      <div class="shelter-popup-arrow"></div>
    </div>

    <!-- 🚗 无人车出发悬浮窗 (含传感器实时数据) -->
    <div
      v-if="ugvPopup.show" 
      class="shelter-popup-panel ugv-dispatch-popup"
      :style="{ left: ugvPopup.x + 'px', top: ugvPopup.y + 'px' }"
    >
      <div class="shelter-popup-header ugv-dispatch-header">
        <div class="dispatch-title-row">
          <span class="dispatch-icon">🚗</span>
          <span>{{ ugvPopup.title }}</span>
        </div>
        <button class="close-btn" @click="ugvPopup.show = false">×</button>
      </div>
      <table class="shelter-popup-table">
        <tbody>
          <tr>
            <td class="label">车型</td>
            <td class="value highlight-blue">{{ ugvPopup.model }}</td>
          </tr>
          <tr>
            <td class="label">出动数量</td>
            <td class="value">{{ ugvPopup.count }}</td>
          </tr>
          <tr>
            <td class="label">行进速度</td>
            <td class="value">{{ ugvPopup.speed }}</td>
          </tr>
          <tr>
            <td class="label">出动状态</td>
            <td class="value status-launched">{{ ugvPopup.status }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 无人车 A / B 实时传感数据面板 (从出发阶段起显示) -->
      <div v-if="props.activePhaseIndex >= 8 && props.sensorData" class="ugv-sensor-section">
        <div class="ugv-sensor-tabs">
          <button 
            :class="['ugv-sensor-tab', { active: activeUgvSensorTab === 'A' }]" 
            @click="activeUgvSensorTab = 'A'"
          >地面感知单元-001 <span class="ugv-tab-status" :class="{ offline: !props.isWsConnected }">{{ props.isWsConnected ? '在线' : '离线' }}</span></button>
          <button 
            :class="['ugv-sensor-tab', { active: activeUgvSensorTab === 'B' }]" 
            @click="activeUgvSensorTab = 'B'"
          >地面感知单元-002 <span class="ugv-tab-status" :class="{ offline: !props.isWsConnected }">{{ props.isWsConnected ? '在线' : '离线' }}</span></button>
        </div>
        <div class="ugv-sensor-body">
          <!-- 无人车 A 数据 -->
          <div v-if="activeUgvSensorTab === 'A'" class="ugv-sensor-grid">
            <div class="ugv-sensor-item"><span class="ugv-sensor-label">温度</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvA.temp : '--' }}</span></div>
            <div class="ugv-sensor-item"><span class="ugv-sensor-label">湿度</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvA.hum + '%' : '--' }}</span></div>
            <div class="ugv-sensor-item"><span class="ugv-sensor-label">TVOC</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvA.tvoc : '--' }}</span></div>
            <div class="ugv-sensor-item"><span class="ugv-sensor-label">CO</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvA.co : '--' }}</span></div>
            <div class="ugv-sensor-item wide"><span class="ugv-sensor-label">烟雾</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvA.smoke + ' ug' : '--' }}</span></div>
          </div>
          <!-- 无人车 B 数据 -->
          <div v-if="activeUgvSensorTab === 'B'" class="ugv-sensor-grid">
            <div class="ugv-sensor-item"><span class="ugv-sensor-label">温度</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvB.temp : '--' }}</span></div>
            <div class="ugv-sensor-item"><span class="ugv-sensor-label">湿度</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvB.hum + '%' : '--' }}</span></div>
            <div class="ugv-sensor-item"><span class="ugv-sensor-label">TVOC</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvB.tvoc : '--' }}</span></div>
            <div class="ugv-sensor-item"><span class="ugv-sensor-label">CO</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvB.co : '--' }}</span></div>
            <div class="ugv-sensor-item wide"><span class="ugv-sensor-label">烟雾</span><span class="ugv-sensor-val">{{ props.isWsConnected ? ugvB.smoke + ' ug' : '--' }}</span></div>
          </div>
          <div class="ugv-sensor-detail-link" @click="goToSensorManage(activeUgvSensorTab === 'A' ? 'node1' : 'node2')">点击查看详情 →</div>
        </div>
      </div>

      <div class="shelter-popup-arrow ugv-arrow"></div>
    </div>

    <!-- 🚁 无人机多源影像驱动 · 三维实景数字孪生重构工作台 (阶段 9：无人感知执行) -->
    <div
      v-if="props.activePhaseIndex === 9 && isReconstructionPanelVisible" 
      class="reconstruction-fusion-panel"
    >
      <div class="glass-bg"></div>
      <div class="panel-content-wrapper">
        <!-- 头部标题栏与状态 -->
        <div class="fusion-panel-header">
          <div class="title-cluster">
            <span class="fusion-icon">🚁</span>
            <div class="title-text-wrap">
              <span class="main-title">多源影像驱动 · 三维实景数字孪生重构</span>
              <span class="sub-title">UAV Multi-View 3D Reconstruction Pipeline</span>
            </div>
          </div>
          <div class="header-right-controls">
            <!-- 双模态切换 Tab -->
            <div class="mode-tab-group">
              <button 
                type="button" 
                class="mode-tab-btn" 
                :class="{ active: reconstructionActiveTab === 'photo' }"
                @click="reconstructionActiveTab = 'photo'"
              >
                <span>📷 环绕航拍</span>
                <span class="badge">{{ capturedCount }}/4</span>
              </button>
              <button 
                type="button" 
                class="mode-tab-btn" 
                :class="{ active: reconstructionActiveTab === '3d' }"
                @click="reconstructionActiveTab = '3d'"
              >
                <span>🧊 三维孪生</span>
                <span class="badge-building" v-if="reconstructionProcessState === 'building'">构建中</span>
                <span class="badge-ready" v-else-if="reconstructionProcessState === 'done'">已生成</span>
                <span class="badge" v-else>待采集</span>
              </button>
            </div>
            <button class="panel-close-btn" @click="isReconstructionPanelVisible = false">×</button>
          </div>
        </div>

        <div class="fusion-panel-body">
          <!-- 核心视窗展示区 -->
          <div class="viewport-stage">
            <!-- 模式 1：无人机多视角航拍大图 -->
            <div v-show="reconstructionActiveTab === 'photo'" class="stage-view photo-mode-view">
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
                  <div class="uav-photo-coords">
                    {{ getAngleName(activePhotoIndex) }} 
                    ({{ props.phases[0]?.id.startsWith('t-') ? '113.1048°E, 30.3855°N' : '114.8933°E, 30.6317°N' }})
                  </div>
                </div>

                <!-- 模拟 SfM 特征点与几何边缘检测光栅 -->
                <div class="sfm-feature-grid" v-if="activePhotoIndex !== null">
                  <div class="feature-crosshair c1"></div>
                  <div class="feature-crosshair c2"></div>
                  <div class="feature-crosshair c3"></div>
                  <div class="feature-tag">SfM 特征匹配: 32,840 pts</div>
                </div>
              </div>
            </div>

            <!-- 模式 2：三维实景孪生重构动态模型与点云预览 -->
            <div v-show="reconstructionActiveTab === '3d'" class="stage-view model-mode-view">
              <!-- A. 正在构建中状态 (未拍完4张，或拍完4张正在执行重构算子) -->
              <div v-if="reconstructionProcessState !== 'done'" class="reconstruction-building-state">
                <div class="building-spinner-wrap">
                  <div class="holo-scanner-ring"></div>
                  <div class="holo-scanner-core">
                    <span class="pct-num">{{ reconstructionProgress }}%</span>
                  </div>
                </div>
                <div class="building-text-wrap">
                  <div class="building-status-title">
                    <span class="pulse-spark">⚡</span>
                    {{ reconstructionProcessState === 'building' ? '多源影像三维实景智能重建中...' : '等待 4 组环绕航拍数据输入...' }}
                  </div>
                  <div class="building-status-desc">{{ reconstructionStageText }}</div>
                </div>
                <div class="building-progress-bar-wrap">
                  <div class="building-progress-bar-fill" :style="{ width: reconstructionProgress + '%' }"></div>
                </div>
                <div class="building-sub-stats">
                  <span>输入源: {{ capturedCount }}/4 视角</span>
                  <span>算法: SfM + 3DGS</span>
                  <span>目标层级: LOD 4</span>
                </div>
              </div>

              <!-- B. 重建完成：加载并展示真实三维模型视频 -->
              <div v-else class="video-container" @click="$router.push('/modeling')">
                <video
                  :src="currentScene === 'tanker' ? '/Dashboard/videos/油罐车泄露现场.mp4' : '/Dashboard/videos/货车追尾现场.mp4'"
                  autoplay
                  loop
                  muted
                  playsinline
                  class="twin-video"
                ></video>
                <div class="scan-line"></div>
                <div class="point-cloud-grid"></div>
                <div class="video-overlay-text">
                  <span class="pulse-dot"></span>
                  三维高斯溅射 (3DGS) 与点云实景重构完成
                </div>
                <div class="hover-cta-overlay">
                  <div class="cta-inner">
                    <span class="cta-icon">🖱️</span>
                    <span class="cta-text">点击深入三维交互重建控制台</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 4 组航拍多视角采集序列与重构输入流 -->
          <div class="capture-stream-strip">
            <div class="stream-title-row">
              <span class="stream-label">
                <span class="dot" :class="{ 'is-complete': capturedCount === 4 }"></span>
                多源影像输入 ({{ capturedCount }}/4 视点对齐)
              </span>
              <span class="engine-tag" :class="{ 'is-converged': capturedCount === 4 }">
                {{ capturedCount === 4 ? '✨ 多视角三角解算完成 · 重构收敛' : `⏳ 正在解算空间几何 (${capturedCount * 25}%)` }}
              </span>
            </div>

            <!-- 4 张多角度抓拍缩略图 -->
            <div class="uav-thumbnails-row">
              <div 
                v-for="i in [0, 1, 2, 3]" 
                :key="i"
                class="uav-thumb-box"
                :class="{ 
                  'is-captured': capturedPhotos[i], 
                  'is-active': activePhotoIndex === i && reconstructionActiveTab === 'photo'
                }"
                @click="handleSelectPhotoThumb(i)"
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

          <!-- 重构指标与一键入舱行动按钮 (重构指标等三维模型生成完成后再出现) -->
          <div class="reconstruction-footer-actions">
            <div class="metrics-grid" v-if="reconstructionProcessState === 'done'">
              <div class="metric-item">
                <span class="k">重构算法</span>
                <span class="v highlight">SfM + 3DGS</span>
              </div>
              <div class="metric-item">
                <span class="k">模型精度</span>
                <span class="v">LOD 4</span>
              </div>
              <div class="metric-item">
                <span class="k">几何误差</span>
                <span class="v green">&lt; 2.4cm</span>
              </div>
            </div>
            <div class="metrics-grid placeholder-grid" v-else>
              <span class="metrics-calculating-hint">
                <i class="calculating-dot"></i>
                模型几何与精度指标解算中...
              </span>
            </div>

            <button class="enter-modeling-cta-btn" type="button" @click="$router.push('/modeling')">
              <span class="btn-glow" v-if="reconstructionProcessState === 'done'"></span>
              <span class="btn-text">进入场景重建控制台</span>
              <svg class="arrow-svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 无人车 A/B 实时数据已合并至上方无人车出发悬浮窗中 -->



    <!-- 两客一危 湖北省交通数字孪生智控终端 (右侧高精对称伸缩侧边栏) -->
    <div class="lkyw-monitor-hud high-end-panel" :class="{ collapsed: isHudCollapsed }">
      <!-- 侧边伸缩拉手按键 (与左侧边栏高精对称的 toggle-btn) -->
      <button 
        class="toggle-btn toggle-btn-right-sidebar" 
        type="button" 
        :title="isHudCollapsed ? '点击展开智控终端' : '点击收起智控终端'"
        @click="isHudCollapsed = !isHudCollapsed"
      >
        <img
          class="sidebar-toggle-icon"
          :src="isHudCollapsed ? '/hud-assets/closeIcon/right_left_arrow.png' : '/hud-assets/closeIcon/right_right_arrow.png'"
          alt=""
        />
      </button>

      <!-- 头部标题与 LIVE 状态标识 (与左侧边栏 .sidebar-header 规格风格完全一致对齐) -->
      <div class="sidebar-header">
        <div class="header-main-title">
          <div class="header-title-block">
            <h2 class="sidebar-title">两客一危救援指挥室 实时信息</h2>
          </div>
          <span class="lkyw-hud-status-badge">● LIVE</span>
        </div>
      </div>

      <!-- 标题下方的功能导航：使用机场资产包的导航按钮切图。 -->
      <nav class="hud-mode-tabs" aria-label="指挥信息视图">
        <button class="mode-btn" :class="{ active: activeHudTab === 'overview' }" @click="activeHudTab = 'overview'">全景总览</button>
        <button class="mode-btn" :class="{ active: activeHudTab === 'risk' }" @click="activeHudTab = 'risk'">风险预警</button>
        <button class="mode-btn" :class="{ active: activeHudTab === 'checkpoint' }" @click="activeHudTab = 'checkpoint'">卡口排行</button>
      </nav>

      <!-- 右侧业务主体：每个标签拥有独立布局，切换后不保留总览的空白占位。 -->
      <div class="hud-scroll-content" :class="`hud-scroll-content--${activeHudTab}`">
        <section v-show="activeHudTab === 'overview'" class="airport-command-slot airport-command-slot--summary">
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

        </section>

        <section v-show="activeHudTab === 'overview'" class="airport-command-slot airport-command-slot--fleet">
      <!-- 1. 在途监控卡片列表 (全景总览模式展示) -->
      <div v-show="activeHudTab === 'overview'" style="display: flex; justify-content: space-between; align-items: center; margin: 10px 14px 8px;">
        <span style="color: #94a3b8; font-size: 13px; font-weight: 500; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">在途分类监控</span>
        <button 
          @click="toggleVehicleFilter('all')"
          style="background: transparent; border: 1px solid #00f2fe; color: #00f2fe; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; cursor: pointer; transition: all 0.3s;"
          :style="activeVehicleFilter === 'all' ? 'background: rgba(0,242,254,0.25); box-shadow: 0 0 10px rgba(0,242,254,0.4); text-shadow: 0 0 5px #00f2fe;' : 'opacity: 0.7; border-color: rgba(0,242,254,0.5);'"
        >
          显示全部3种车辆
        </button>
      </div>
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

        <!-- 公路客运 -->
        <div 
          class="lkyw-hud-card passenger" 
          :class="{ active: activeVehicleFilter === 'passenger' }" 
          @click="toggleVehicleFilter('passenger')"
        >
          <div class="lkyw-card-header">
            <span class="lkyw-label">公路客运</span>
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
            <span class="dot-indicator green"></span> 绿色图例对应公路客运点位 (演示标牌: {{ activePassengerDemoCount }} 辆)
          </div>
        </div>

        <!-- 旅游客运 -->
        <div 
          class="lkyw-hud-card tourist" 
          :class="{ active: activeVehicleFilter === 'tourist' }" 
          @click="toggleVehicleFilter('tourist')"
        >
          <div class="lkyw-card-header">
            <span class="lkyw-label">旅游客运</span>
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
            <span class="dot-indicator blue"></span> 蓝色图例对应旅游客运点位 (演示标牌: {{ activeTouristDemoCount }} 辆)
          </div>
        </div>
      </div>

        </section>

        <section class="airport-command-slot airport-command-slot--detail" :class="{ 'overview-layout': activeHudTab === 'overview', 'tab-layout': activeHudTab !== 'overview' }">
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
              <span class="legend-name">公路客运</span>
              <span class="legend-val green">{{ passengerRatioPercent }}%</span>
            </div>
            <div class="legend-row tourist" @click="toggleVehicleFilter('tourist')">
              <span class="legend-dot blue"></span>
              <span class="legend-name">旅游客运</span>
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
            <span class="risk-num">{{ riskStats.highRiskCount }}</span>
            <span class="risk-lbl">高危车辆</span>
          </div>
          <div class="risk-summary-item gold">
            <span class="risk-num">{{ riskStats.speedingCount }}</span>
            <span class="risk-lbl">超速预警</span>
          </div>
          <div class="risk-summary-item orange">
            <span class="risk-num">{{ riskStats.fatigueCount }}</span>
            <span class="risk-lbl">疲劳驾驶</span>
          </div>
          <div class="risk-summary-item blue">
            <span class="risk-num">{{ riskStats.deviationCount }}</span>
            <span class="risk-lbl">路线偏离</span>
          </div>
        </div>

        <div class="hud-control-row" aria-label="风险处置快捷操作">
          <button type="button" @click="focusRiskVehicleOnMap(riskVehicles[0])">定位最高风险</button>
          <button type="button" @click="activeHudTab = 'checkpoint'">查看关联卡口</button>
          <button type="button" @click="toggleVehicleFilter('all')">恢复全量车辆</button>
        </div>

        <div class="chart-title-bar" style="margin-top: 10px;">
          <span class="chart-title">实时高危车辆告警流</span>
          <span class="chart-sub">LIVE ALERT</span>
        </div>

        <div class="risk-vehicle-list">
          <div v-for="(item, idx) in riskVehicles" :key="item.plate + idx" class="risk-card-item" :class="item.levelClass === 'red' ? 'high-risk' : (item.levelClass === 'orange' ? 'mid-risk' : 'low-risk')">
            <div class="risk-card-top">
              <span class="risk-plate">{{ item.plate }}</span>
              <span class="risk-type-tag" :class="item.class">{{ item.type }}</span>
              <span class="risk-level-badge" :class="item.levelClass">{{ item.level }}</span>
            </div>
            <div class="risk-card-body">
              <div class="risk-reason">{{ item.reason }}</div>
              <div class="risk-meta-row">位置: {{ item.location }}</div>
              <div class="risk-meta-row">驾驶员: {{ item.driver }}</div>
            </div>
            <button class="risk-action-btn" @click="focusRiskVehicleOnMap(item)">
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

        <div class="checkpoint-overview">
          <span><b>{{ checkpoints.length }}</b> 个重点卡口</span>
          <span>累计入省 <b>{{ totalInboundCount.toLocaleString() }}</b></span>
          <span>累计出省 <b>{{ totalOutboundCount.toLocaleString() }}</b></span>
        </div>

        <div class="checkpoint-list">
          <div v-for="cp in checkpoints" :key="cp.name" class="checkpoint-card">
            <div class="cp-rank-header">
              <span class="cp-rank" :class="cp.rankClass">{{ cp.rank }}</span>
              <span class="cp-name">{{ cp.name }}</span>
              <span class="cp-status" :class="cp.statusClass">{{ cp.status }}</span>
            </div>
            <div class="cp-stats-row">
              <div class="cp-stat">
                <span class="cp-label">流量</span>
                <span class="cp-val" :class="cp.statusClass">{{ cp.flow.toLocaleString() }} <small>辆/h</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计入省</span>
                <span class="cp-val green">{{ cp.inflow.toLocaleString() }} <small>辆</small></span>
              </div>
              <div class="cp-stat">
                <span class="cp-label">累计出省</span>
                <span class="cp-val gold">{{ cp.outflow.toLocaleString() }} <small>辆</small></span>
              </div>
            </div>
          </div>
        </div>
      </div>


        </section>
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




    <!-- 救援装备出动操控面板已被移除，逻辑改为自动触发 -->

    <!-- ============================================================
         协同响应效能指标悬浮窗 (右上角，无人装备出动 Phase 7/11 时显示)
         ============================================================ -->
    <Transition name="metrics-popup-fade">
      <div
        v-if="strategyMetricsPanel.show"
        class="collab-metrics-popup"
        :class="{ 'is-loading': strategyMetricsPanel.loading }"
      >
        <!-- 标题栏 -->
        <div class="cmp-header">
          <div class="cmp-title-row">
            <span class="cmp-icon">📊</span>
            <span class="cmp-title">协同响应效能指标</span>
            <span v-if="strategyMetricsPanel.loading" class="cmp-pulse"></span>
          </div>
          <div v-if="strategyMetricsPanel.data" class="cmp-scene-label">
            {{ strategyMetricsPanel.data.end_point_name || '——' }}
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="strategyMetricsPanel.loading && !strategyMetricsPanel.data" class="cmp-loading">
          <div class="cmp-spin"></div>
          <span>正在读取效能数据...</span>
        </div>

        <!-- 无数据 -->
        <div v-else-if="!strategyMetricsPanel.data" class="cmp-empty">
          <span>⚠️ 暂无规划数据</span>
          <small>请先在协同响应面板生成推演</small>
        </div>

        <!-- 主体数据 -->
        <template v-else>
          <!-- 时间指标 -->
          <div class="cmp-section-title">⏱ 时间指标</div>
          <div class="cmp-metrics-grid">
            <div class="cmp-metric-card">
              <span class="cmp-val cmp-cyan">{{ strategyMetricsPanel.data.metrics?.carTime || '--' }}<small> min</small></span>
              <span class="cmp-lbl">UGV 耗时</span>
            </div>
            <div class="cmp-metric-card">
              <span class="cmp-val cmp-cyan">{{ strategyMetricsPanel.data.metrics?.uavTime || '--' }}<small> min</small></span>
              <span class="cmp-lbl">UAV 飞行</span>
            </div>
            <div class="cmp-metric-card">
              <span class="cmp-val cmp-amber">{{ strategyMetricsPanel.data.metrics?.delay || '--' }}<small> s</small></span>
              <span class="cmp-lbl">地面待机</span>
            </div>
            <div class="cmp-metric-card" :class="{ 'cmp-perfect': parseFloat(strategyMetricsPanel.data.metrics?.timeDiff) === 0 }">
              <span class="cmp-val" :class="parseFloat(strategyMetricsPanel.data.metrics?.timeDiff) === 0 ? 'cmp-green' : 'cmp-amber'">
                {{ strategyMetricsPanel.data.metrics?.timeDiff || '0.0' }}<small> s</small>
              </span>
              <span class="cmp-lbl">协同时间差</span>
            </div>
          </div>

          <!-- 距离 & 能耗 -->
          <div class="cmp-section-title" style="margin-top: 10px;">📏 距离 & 能耗</div>
          <div class="cmp-metrics-grid">
            <div class="cmp-metric-card">
              <span class="cmp-val cmp-purple">{{ strategyMetricsPanel.data.comparison?.carDistKm || '--' }}<small> km</small></span>
              <span class="cmp-lbl">UGV 行驶</span>
            </div>
            <div class="cmp-metric-card">
              <span class="cmp-val cmp-purple">{{ strategyMetricsPanel.data.comparison?.uavDistKm || '--' }}<small> km</small></span>
              <span class="cmp-lbl">UAV 飞行</span>
            </div>
            <div class="cmp-metric-card" style="grid-column: span 2;">
              <span class="cmp-val cmp-pink">{{ strategyMetricsPanel.data.metrics?.uavEnergy || '--' }}<small> Wh</small></span>
              <span class="cmp-lbl">无人机能耗</span>
            </div>
          </div>

          <!-- 算法对比 -->
          <div v-if="strategyMetricsPanel.data.comparison" class="cmp-compare-row">
            <span class="cmp-compare-badge">Dijkstra</span> 节省 {{ strategyMetricsPanel.data.comparison.carSavingKm }} km vs BFS
            &nbsp;|&nbsp;
            <span class="cmp-compare-badge">A*</span> 节省 {{ strategyMetricsPanel.data.comparison.uavSavingKm }} km vs Greedy
          </div>

          <!-- 速度 & 场景 -->
          <div class="cmp-footer-row">
            <span>🚗 {{ strategyMetricsPanel.data.speeds?.car_kmh || 80 }} km/h</span>
            <span>🛸 {{ strategyMetricsPanel.data.speeds?.uav_ms || 20 }} m/s</span>
            <span v-if="strategyMetricsPanel.data.scenario?.ugv_blocked" class="cmp-tag-warn">拥堵</span>
            <span v-if="strategyMetricsPanel.data.scenario?.uav_smoke" class="cmp-tag-warn">禁飞×{{ strategyMetricsPanel.data.scenario?.nfz_count }}</span>
          </div>
        </template>

        <!-- 更新时间 -->
        <div v-if="strategyMetricsPanel.updatedAt" class="cmp-updated-at">
          更新: {{ strategyMetricsPanel.updatedAt }}
        </div>
      </div>
    </Transition>

    <!-- ============================================================
         多智能体全局寻优决策日志悬浮窗 (右上角，救援装备出动 Phase 11 时显示)
         ============================================================ -->
    <Transition name="agent-log-fade">
      <div
        v-if="multiAgentLogPanel.show"
        class="agent-log-popup"
      >
        <!-- 标题栏 -->
        <div class="alp-header">
          <div class="alp-title-row">
            <span class="alp-icon">🧠</span>
            <div class="alp-title-text">
              <span class="alp-title">多智能体全局寻优决策日志</span>
              <span class="alp-subtitle">Global Optimization Log</span>
            </div>
            <span class="alp-badge">决策已锚定</span>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="multiAgentLogPanel.loading && !multiAgentLogPanel.data" class="alp-loading">
          <div class="alp-spin"></div>
          <span>正在加载决策日志...</span>
        </div>

        <!-- 无数据 -->
        <div v-else-if="!multiAgentLogPanel.data" class="alp-empty">
          <span>⚠️ 暂无多智能体规划数据</span>
          <small>请先在协同响应面板中运行多智能体寻优</small>
        </div>

        <!-- 主体：决策矩阵 -->
        <template v-else>
          <!-- Tab 按钮切换条 -->
          <div class="alp-tabs">
            <button
              v-for="(agent, key) in multiAgentLogPanel.data.agents"
              :key="key"
              class="alp-tab-btn"
              :class="{ active: selectedAgentKey === key }"
              :style="{ '--btn-color': agent.color }"
              @click="selectedAgentKey = key"
            >
              {{ agentShortNames[key] || agent.label }}
            </button>
          </div>

          <!-- 单个选中智能体决策卡片 -->
          <div class="alp-decision-single" v-if="multiAgentLogPanel.data.agents[selectedAgentKey]">
            <div
              class="alp-agent-card"
              :style="{ '--alp-color': multiAgentLogPanel.data.agents[selectedAgentKey].color }"
            >
              <!-- 智能体头部：采用纵向堆叠布局防止名字挤压折行 -->
              <div class="alp-agent-head">
                <span class="alp-agent-label">{{ multiAgentLogPanel.data.agents[selectedAgentKey].label }}</span>
                <span class="alp-agent-winner">{{ multiAgentLogPanel.data.agents[selectedAgentKey].poi.name }}</span>
              </div>
              <!-- 距离指标 -->
              <div class="alp-stats">
                <div class="alp-stat-row alp-highlight">
                  <span class="stat-lbl">最优路网拓扑距离</span>
                  <span class="stat-val">{{ multiAgentLogPanel.data.agents[selectedAgentKey].poi.net_dist_km }} km</span>
                </div>
                <div class="alp-stat-row">
                  <span class="stat-lbl">空间直线初筛距离</span>
                  <span class="stat-val">{{ multiAgentLogPanel.data.agents[selectedAgentKey].poi.dist_km }} km</span>
                </div>
              </div>
              <!-- 淘汰名录 -->
              <div v-if="multiAgentLogPanel.data.agents[selectedAgentKey].losers && multiAgentLogPanel.data.agents[selectedAgentKey].losers.length > 0" class="alp-losers">
                <div class="alp-losers-title">候选节点动态剔除名录</div>
                <div v-for="(loser, idx) in multiAgentLogPanel.data.agents[selectedAgentKey].losers" :key="idx" class="alp-loser-item">
                  <div class="alp-loser-name">✕ {{ loser.name }}</div>
                  <div class="alp-loser-reason">{{ loser.reason }}</div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </Transition>
  </div>
</template>

<script setup>
// 1. 顶端高度修正常量 (如果连线太高/太低，调这两个数字)
const JIZHAN_TOP_OFFSET = 18.0;  
const LIGHT_TOP_OFFSET = 7.5;    
// ==========================================
// 🌟 核心：多维异构传感网协同矩阵动态状态
// ==========================================
const fusionPanelConfig = reactive({
  show: true // 控制面板是否显示
});
// 进入事故场景后固定展示协同矩阵；推演阶段切换会重置视角层级，不能再以该瞬时状态控制面板可见性。
const showFusionPanel = computed(() => {
  const isAccidentScene = props.focusedPointId === 'accident_blue' || props.focusedPointId === 'accident_red'
  return fusionPanelConfig.show && isAccidentScene
})

// 假设 activePhaseIndex 是通过 props 传入的，或者是定义在当前组件的 ref
// const props = defineProps({ activePhaseIndex: Number });

// 1. 定义控制放大镜悬浮窗显示状态的变量

// 根据当前的推演阶段，动态计算 4 个传感器的协同状态
const sensorFusionState = computed(() => {
  const phase = Number(props.activePhaseIndex);
  const isTanker = currentScene.value === 'tanker'; // 判断是不是油罐车场景

  return {
    // 1. 车端节点状态
    car: {
      text: phase >= 2 ? (isTanker ? '检测到侧翻倾角异常' : '检测到异常冲击') : '平稳运行，各项数据正常',
      statusClass: phase >= 2 ? 'alert' : 'normal'
    },
    // 2. 路侧节点状态
    light: {
      text: phase >= 4 ? '视场唤醒，视觉特征提取完成' : '休眠中，低功耗待机',
      statusClass: phase >= 4 ? 'active' : 'waiting'
    },
    // 3. 空基节点 (无人机) 状态
    uav: {
      text: phase >= 8 ? '已到达，红外全景推流中' : (phase >= 3 ? '飞行侦察中...' : '基地待命'),
      statusClass: phase >= 8 ? 'active' : (phase >= 3 ? 'moving' : 'waiting')
    },
    // 4. 地基节点 (无人车) 状态
    ugv: {
      text: phase >= 10 ? '已切入核心区，五合一嗅探中' : (phase >= 8 ? '地面行进中...' : '基地待命'),
      statusClass: phase >= 10 ? 'active' : (phase >= 8 ? 'moving' : 'waiting')
    },
    // 5. 综合研判结果
    resultText: phase >= 10 
      ? (isTanker ? '油罐侧翻特大泄露 (空地协同确证)' : '货车追尾引发大火 (空地协同确证)') 
      : (phase >= 2 ? '疑似交通事故 (单节点报警)' : '全域路网安全'),
    confidence: phase >= 8 ? '98.5%' : (phase >= 4 ? '76.2%' : (phase >= 2 ? '45.0%' : '--'))
  };
});
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

// 立体围栏侧壁材质：水平亮带持续向下扫描。使用独立的材质类型，
// 不影响页面中已经使用 DynamicFlowLine 的道路、航线等效果。
Cesium.Material._materialCache.addMaterial('ElectronicFenceWallFlow', {
  fabric: {
    type: 'ElectronicFenceWallFlow',
    uniforms: {
      color: new Cesium.Color(0.0, 0.62, 1.0, 0.62),
      speed: 1.15,
      // 减少重复次数，拉开相邻流光带的距离，使首页总览也能辨认出上升/流动过程。
      repeat: 3.0
    },
    source: `
      czm_material czm_getMaterial(czm_materialInput materialInput) {
        czm_material material = czm_getDefaultMaterial(materialInput);
        float scan = fract(materialInput.st.t * repeat - czm_frameNumber * speed / 100.0);
        float stripe = smoothstep(0.0, 0.12, scan) * (1.0 - smoothstep(0.22, 0.48, scan));
        float grid = step(0.94, fract(materialInput.st.s * 36.0));
        material.diffuse = color.rgb;
        material.alpha = color.a * (0.18 + stripe * 0.82 + grid * 0.18);
        material.emission = color.rgb * (stripe * 0.72 + grid * 0.16);
        return material;
      }
    `
  }
});

class ElectronicFenceWallFlowMaterialProperty {
  constructor(options = {}) {
    this._definitionChanged = new Cesium.Event()
    this.color = options.color || Cesium.Color.fromCssColorString('#008cff').withAlpha(0.62)
    this.speed = options.speed || 1.15
    this.repeat = options.repeat || 3.0
  }
  get isConstant() { return false }
  get definitionChanged() { return this._definitionChanged }
  getType() { return 'ElectronicFenceWallFlow' }
  getValue(time, result) {
    if (!Cesium.defined(result)) result = {}
    result.color = Cesium.Color.clone(this.color, result.color)
    result.speed = this.speed
    result.repeat = this.repeat
    return result
  }
  equals(other) { return this === other }
}
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
import { onBeforeUnmount, onMounted, onActivated, onDeactivated, ref, watch, reactive, computed } from 'vue'
import savedStoryCameraViews from '../../config/storyCameraViews.json'
import { useRouter } from 'vue-router'
import * as Cesium from 'cesium'
import { MAP_VEHICLE_STYLES } from '../../config/mapVehicleStyles'

const isComponentActive = ref(true)
import {
  buildRealtimeDetectionApiUrl,
  getCollaborativeCommandCenterBaseUrl,
  getRealtimeDetectionBaseUrl,
} from '../../config/subsystems'

const props = defineProps({
  phases: { type: Array, default: () => [] },
  activePhaseIndex: { type: Number, default: 0 },
  focusedPointId: { type: String, default: '' },
  sensorData: { type: Object, default: () => ({}) },
  isWsConnected: { type: Boolean, default: false },
  landingView: { type: Boolean, default: false },
  rightSidebarCollapsed: { type: Boolean, default: false }
})
const showMagnifier = ref(false);

// 2. 监听阶段索引的变化
watch(
  () => props.activePhaseIndex, // 如果是当前组件内的 ref，直接写 () => props.activePhaseIndex
  (newIndex) => {
    // 阶段九的数组索引为 8
    if (newIndex === 9) {
      // 进入阶段九时，自动弹出悬浮窗
      showMagnifier.value = true;
      
      // 可选：你还可以在这里触发 Cesium 相机的视角调整，聚焦到无人车阵列
      // focusOnSensorNetwork();
    } else {
      // 离开阶段九时，自动关闭悬浮窗，保持界面整洁
      showMagnifier.value = false;
    }
  },
  { immediate: true } // immediate 确保如果页面刷新直接进入阶段九，也能正常弹出
);
<<<<<<< HEAD
const emit = defineEmits(['accident-picked', 'models-ready', 'update:activePhaseIndex', 'reconstruction-ready', 'playback-durations'])
=======
const emit = defineEmits(['accident-picked', 'models-ready', 'update:activePhaseIndex', 'reconstruction-ready', 'playback-durations', 'loading-change', 'vehicle-layer-change'])
const overviewAccident = ref(null)
const overviewAccidents = {
  accident_blue: { id: 'accident_blue', city: '湖北 · 仙桃', title: '随岳高速客货车追尾起火事故', date: '2011年7月4日', location: '随岳高速229公里附近 · 仙桃市毛嘴镇珠玑村', description: '货车与客车发生追尾碰撞，两车翻出高速公路护栏后起火。事故造成23人死亡、29人不同程度受伤，现场开展灭火、搜救与车辆残骸清理。', caption: '真实事故现场 · 中新社发 张畅 摄 / 中国新闻网', image: '/Dashboard/images/xiantao-20110704-news.jpg', source: 'https://www.chinanews.com/tp/hd2011/2011/07-04/54148.shtml' },
  accident_red: { id: 'accident_red', city: '湖北 · 黄冈团风', title: '甲醇槽罐车侧翻泄漏事故', date: '2021年6月18日 07:14左右', location: 'G347国道 · 团风县迎宾大道环岛', description: '一辆装载33.3吨甲醇的槽罐车侧翻并发生泄漏。消防、公安、环保、住建等部门联合处置，采取警戒疏散、稀释降毒、冷却保护和倒罐转运，经过近7小时排除险情，无人员伤亡。', caption: '事故场景参考图', imageSource: 'https://www.chinanews.com/sh/2018/06-09/8534066.shtml', image: '/Dashboard/images/methanol-reference-qinzhou.jpg', source: 'https://www.wangkanglawyer.com/2327.html' }
}

>>>>>>> lkywSystem/develop


const router = useRouter()

const STORY_DETECTION_SCENARIOS = {
  accident: {
    key: 'accident',
    phaseIndex: 2,
    model: 'SFGA-YOLO26M',
    level: 'warning',
    title: '事故发生检测告警',
    phaseLabel: '事故发生',
    statusBadge: '黄色告警',
    imageSrc: '/Dashboard/images/story-accident-detection.png',
    fileName: 'story-accident-detection.png',
    imageWidth: 1456,
    imageHeight: 1024,
    results: ['两客一危车辆', '碰撞无火'],
    report: '检测到两客一危车辆发生碰撞，当前画面未识别明火，建议进入事故确认与现场管控流程。',
    boxes: [
      { x: 18, y: 43, width: 52, height: 24, label: '两客一危车辆', kind: 'warning' },
      { x: 39, y: 50, width: 12, height: 12, label: '碰撞无火', kind: 'warning' }
    ]
  },
  fire: {
    key: 'fire',
    phaseIndex: 6,
    model: 'SFGA-YOLO26M',
    level: 'critical',
    title: '次生灾害起火告警',
    phaseLabel: '次生灾害（起火）',
    statusBadge: '红色告警',
    imageSrc: '/Dashboard/images/story-fire-detection.png',
    fileName: 'story-fire-detection.png',
    imageWidth: 1456,
    imageHeight: 1024,
    results: ['两客一危车辆', '碰撞起火'],
    report: '检测到事故车辆起火并伴随浓烟，建议立即触发消防救援与交通封控联动。',
    boxes: [
      { x: 24, y: 42, width: 61, height: 25, label: '两客一危车辆', kind: 'fire' },
      { x: 37, y: 21, width: 34, height: 43, label: '碰撞起火', kind: 'fire' }
    ]
  },
  tankerAccident: {
    key: 'tankerAccident',
    phaseIndex: 2,
    model: 'SFGA-YOLO26M',
    level: 'warning',
    title: '事故发生检测告警',
    phaseLabel: '事故发生（侧翻）',
    statusBadge: '黄色告警',
    imageSrc: '/Dashboard/images/tanker-accident-detection.png',
    fileName: 'tanker-accident-detection.png',
    imageWidth: 727,
    imageHeight: 538,
    results: ['化学品运输车', '侧翻事故'],
    report: '检测到油罐车发生侧翻事故，当前画面未识别危化品泄露，建议立即启动事故确认与现场警戒。',
    boxes: [
      { x: 25, y: 27, width: 55, height: 42, label: '化学品运输车', kind: 'warning' }
    ]
  },
  tankerLeak: {
    key: 'tankerLeak',
    phaseIndex: 5,
    model: 'LCA-YOLO26N',
    level: 'critical',
    title: '次生灾害泄露告警',
    phaseLabel: '次生灾害（泄露）',
    statusBadge: '红色告警',
    imageSrc: '/Dashboard/images/tanker-leak-detection.png',
    fileName: 'tanker-leak-detection.png',
    imageWidth: 2852,
    imageHeight: 1600,
    results: ['危化品泄露'],
    report: '检测到槽罐车罐体出现甲醇泄漏迹象，建议立即布设空气监测与封控半径。白色雾效为泄漏可视化示意，甲醇蒸气本身无色。',
    boxes: [
      { x: 39, y: 18, width: 30, height: 30, label: '危化品泄露', kind: 'fire' }
    ]
  },
  tankerFill: {
    key: 'tankerFill',
    phaseIndex: 6,
    model: 'LCA-YOLO26N',
    level: 'critical',
    title: '次生灾害弥漫告警',
    phaseLabel: '次生灾害（弥漫）',
    statusBadge: '红色告警',
    imageSrc: '/Dashboard/images/tanker-leak-detection.png',
    fileName: 'tanker-diffusion-detection.png',
    imageWidth: 2852,
    imageHeight: 1600,
    results: ['危化品泄露', '气体弥漫'],
    report: '检测到甲醇泄漏风险并向周边扩散，建议立即进行交通封控与空气浓度监测。白色雾效用于扩散可视化示意，甲醇蒸气本身无色。',
    boxes: [
      { x: 45, y: 15, width: 35, height: 34, label: '气体弥漫', kind: 'fire' },
      { x: 43, y: 32, width: 18, height: 20, label: '危化品泄露', kind: 'fire' }
    ]
  }
}


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
  range: 600,
  pitch: -20,
  heading: -25,
  copiedMsg: ''
})

// 按事故场景和阶段分别记录调整前视角，恢复操作不重启阶段动画。
// 首页行政区矢量面默认采用用户确认的 100% 亮度；右侧“矢量亮度”按钮可实时调整。
const vectorLayerConfig = reactive({
  show: false,
  opacity: 100
})

// ⚡ 智能体出动速度微调配置
const agentSpeedConfig = reactive({
  uavDuration: 6.0,         // 无人机出动动画时长 (秒)
  ugvDuration: 6.0,          // 无人车出动动画时长 (秒)
  multiAgentMultiplier: 20 // 救援装备出动默认 20 倍速
});

// 时间轴不能使用固定秒数：首阶段的四辆车具有不同的错峰发车时间与速度。
// 以最晚抵达终点的车辆为准，再留出短暂终帧展示时间。
function getStartStageCompletionMs() {
  const routeDurationMs = Math.max(5, Number(startStageVehicleAdjust.loopDurationSec) || 18) * 1000
  const completionRatio = Math.max(...startStageVehicleConfigs.map(({ delayRatio = 0, speedFactor = 1 }) => {
    return Number(delayRatio) + 1 / Math.max(0.01, Number(speedFactor) || 1)
  }))
  return Math.ceil(routeDurationMs * completionRatio) + 800
}

function emitPlaybackDurations() {
  const isTruck = props.phases?.[0]?.id?.startsWith('t-')
  const uavDurationMs = Math.max(1, Number(agentSpeedConfig.uavDuration) || 6) * 1000
  const ugvDurationMs = Math.max(1, Number(agentSpeedConfig.ugvDuration) || 6) * 1000
  const vehicleAnimationMs = isTruck ? 4000 : 3000

  emit('playback-durations', {
    // 0：四辆初始车辆的实际最晚到达时间（根据当前控制面板参数实时计算）
    0: getStartStageCompletionMs(),
    // 1、2：GLB 动画文件中的实际时长（货车 4s，油罐车 3s）+ 终帧展示
    1: vehicleAnimationMs + 800,
    2: vehicleAnimationMs + 800,
    // 3、7：使用当前无人机/无人车速度控制值，取并行动画中较长的一项
    3: uavDurationMs + 800,
    4: 8800,
    5: 6000,
    6: 6000,
    7: (isTruck ? Math.max(uavDurationMs, ugvDurationMs) : Math.max(uavDurationMs, 10000)) + 800,
    8: 6800,
    // 完整环绕航拍 12s + 三维重建 2.2s；额外由 reconstruction-ready 信号兜底。
    9: 15000,
    10: 4000
  })
}

watch(() => agentSpeedConfig.multiAgentMultiplier, (newVal) => {
  if (viewer && viewer.clock && Number(props.activePhaseIndex) === 11) {
    viewer.clock.multiplier = Number(newVal);
  }
});

// 🚗 全省车流与巡航动态控制面板 状态
const trafficConfig = reactive({
  show: false,
  speedFactor: 0.1,     // 速度倍率 (0.1x ~ 10.0x)
  minDistance: 43000,   // 最短行驶路线段长度 (默认 43.0 km)
  vehicleCount: 14,     // 巡航车辆显示数量：默认降低密度，避免省域视图标记拥挤
  activeCategory: 'all' // 车辆类型筛选: 'all' | 'hazard' | 'passenger' | 'tourist'
})

// 🏷️ 市级行政区文字标注微调面板 状态
const labelConfig = reactive({
  show: false,
  fontSize: 18,      // 省域总览采用辅助说明字号，避免城市名遮挡底图
  outlineWidth: 2
})

// 保存市级文字标注 Entity 引用
const cityLabelEntities = []

function updateCityLabelsFont() {
  if (!viewer) return
  const fontStr = `600 ${labelConfig.fontSize}px "Microsoft YaHei UI", "Microsoft YaHei", sans-serif`
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






const initialPhaseCameraConfigs = {
  truck: {
    1: { range: 600, pitch: -20, heading: -25 },
    2: { range: 480, pitch: -25, heading: 33 },
    3: { range: 480, pitch: -25, heading: 33 },
    4: { range: 100000, pitch: -90, heading: -3 },
    5: { range: 480, pitch: -25, heading: 33 },
    6: { range: 480, pitch: -25, heading: 33 },
    7: { range: 480, pitch: -25, heading: 33 },
    8: { range: 70650, pitch: -90, heading: 350 },
    9: { range: 480, pitch: -25, heading: 33 },
    10: { range: 500, pitch: -21, heading: 28 },
    11: { range: 500, pitch: -21, heading: 28 },
    12: { range: 62750, pitch: -79, heading: 5 }
  },
  tanker: {
    1: { range: 1000, pitch: -28, heading: -90 },
    2: { range: 950, pitch: -35, heading: -15 },
    3: { range: 480, pitch: -25, heading: 33 },
    4: { range: 9000, pitch: -45, heading: 352 },
    5: { range: 480, pitch: -40, heading: -20 },
    6: { range: 480, pitch: -40, heading: -20 },
    7: { range: 1600, pitch: -45, heading: 0 },
    8: { range: 9000, pitch: -45, heading: 352 },
    9: { range: 600, pitch: -30, heading: -10 },
    10: { range: 600, pitch: -18, heading: -21 },
    11: { range: 600, pitch: -18, heading: -21 },
    12: { range: 9000, pitch: -45, heading: 352 }
  }
}

const defaultPhaseCameraConfigs = reactive(JSON.parse(JSON.stringify(initialPhaseCameraConfigs)))


















// 现场灯光微调相关状态与控制
const isLightPanelExpanded = ref(false)

const coordCopiedMessage = ref('')

const activeLightIndex = ref(0)
const lights = reactive([
  { id: 'light1', name: '灯光 1', show: true, lng: 113.104364, lat: 30.385512, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light2', name: '灯光 2', show: true, lng: 113.105781, lat: 30.385317, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light3', name: '灯光 3', show: true, lng: 113.104482, lat: 30.385632, height: 8.5, scale: 0.003, heading: 198, pitch: 0, roll: 0 },
  { id: 'light4', name: '灯光 4', show: true, lng: 114.891139, lat: 30.630711, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light5', name: '灯光 5', show: true, lng: 114.892307, lat:30.631017, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  
  { id: 'light6', name: '灯光 6 (原3D自带)', show: true, lng: 114.893327, lat: 30.631683, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { 
 id: 'light7', 
 name: '灯光 7', 
 show: true,
 lng: 113.106921,
 lat: 30.385029,
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
 lng: 113.105697,
 lat:30.385135,
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
 lng: 113.106826,
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
 lng: 113.103274,
 lat:30.385803,
 height: 8.5,
 scale: 0.003,
 heading: 201,
 pitch: 0,
 roll: 0
},
{ id: 'light11', name: '灯光 11', show: true, lng: 113.103434, lat: 30.385999, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light12', name: '灯光 12', show: true, lng: 113.101849, lat: 30.386164, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light13', name: '灯光 13', show: true, lng: 113.102025, lat: 30.386324, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light14', name: '灯光 14', show: true, lng: 113.099968, lat: 30.386693, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light15', name: '灯光 15', show: true, lng: 113.100141, lat:30.386877, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light16', name: '灯光 16', show: true, lng:113.097772, lat: 30.387416, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light17', name: '灯光 17', show: true, lng: 113.0977, lat:30.387665, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light18', name: '灯光 18', show: true, lng:113.096165, lat: 30.38803, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
 { id: 'light19', name: '灯光 19', show: true, lng: 113.109018, lat: 30.384654, height: 8.5, scale: 0.003, heading: 16, pitch: 0, roll: 0 },
  { id: 'light20', name: '灯光 20', show: true, lng:113.108726, lat:30.384424, height: 8.5, scale: 0.003, heading: 201, pitch: 0, roll: 0 },
  { id: 'light21', name: '灯光 21', show: true, lng: 113.110784, lat: 30.384221, height: 8.5, scale: 0.003, heading: 198, pitch: 0, roll: 0 },
   { id: 'light22', name: '灯光 22', show: true, lng: 113.110784, lat:30.384051, height: 8.5, scale: 0.003, heading: 198, pitch: 0, roll: 0 },
{ id: 'light23', name: '灯光 23', show: true, lng: 114.89137, lat: 30.630524, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light24', name: '灯光 24', show: true, lng: 114.892206, lat: 30.631211, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light25', name: '灯光 25', show: true, lng: 114.890568, lat: 30.630524, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light26', name: '灯光 26', show: true, lng: 114.893113, lat:30.631378, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
   { id: 'light27', name: '灯光 27', show: true, lng:114.890608, lat: 30.629945, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light28', name: '灯光 28', show: true, lng: 114.892978, lat:30.631556, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light29', name: '灯光 29', show: true, lng:114.890126, lat: 30.629685, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light30', name: '灯光 30', show: true, lng: 114.893848, lat:30.631709, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light31 ', name: '灯光 31', show: true, lng:114.890115, lat: 30.630225, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light32', name: '灯光 32', show: true, lng: 114.893781, lat:30.631934, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light33', name: '灯光 33', show: true, lng:114.890104, lat: 30.630925, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light34', name: '灯光 34', show: true, lng: 114.894522, lat:30.632024, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light35', name: '灯光 35', show: true, lng:114.890479, lat: 30.631868, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
  { id: 'light36', name: '灯光 36', show: true, lng:114.894522, lat:30.632274, height: 8.5, scale: 0.003, heading: 0, pitch: 0, roll: 0 },
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
const tankerJizhanAdjust = reactive({
  show: true,
  lng: 114.891890, 
  lat: 30.631250,
  height: 1.5,
  scale: 0.01,
  heading: 45,
  pitch: 0,
  roll: 0
})
const currentJizhanAdjust = computed(() => {
  return currentScene.value === 'truck' ? jizhanAdjust : tankerJizhanAdjust;
})
function snapJizhanToDefault() {
  if (currentScene.value === 'truck') {
    jizhanAdjust.lng = 113.105385;
    jizhanAdjust.lat = 30.385795;
    jizhanAdjust.height = -1.9;
    jizhanAdjust.scale = 0.01;
    jizhanAdjust.heading = 99;
    jizhanAdjust.pitch = 0;
    jizhanAdjust.roll = 0;
  } else {
    tankerJizhanAdjust.lng = 114.894463;
    tankerJizhanAdjust.lat = 30.632121;
    tankerJizhanAdjust.height = -1.9;
    tankerJizhanAdjust.scale = 0.01;
    tankerJizhanAdjust.heading = 45;
    tankerJizhanAdjust.pitch = 0;
    tankerJizhanAdjust.roll = 0;
  }
}

function copyJizhanCoords() {
  const obj = currentJizhanAdjust.value;
  const text = `lng: ${obj.lng.toFixed(6)}, lat: ${obj.lat.toFixed(6)}, height: ${obj.height}, scale: ${obj.scale}, heading: ${obj.heading}, pitch: ${obj.pitch}, roll: ${obj.roll}`;
  navigator.clipboard.writeText(text).then(() => {
    jizhanCopiedMessage.value = '当前基站配置参数已成功复制到剪贴板！';
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
function togglePanel(panelName) {
  if (panelName === 'camera') {
    const nextVal = !cameraAdjust.show;
    closeAllPanelsExcept(panelName);
    cameraAdjust.show = nextVal;
  } else if (panelName === 'traffic') {
    const nextVal = !trafficConfig.show;
    closeAllPanelsExcept(panelName);
    trafficConfig.show = nextVal;
  } else if (panelName === 'startCar') {
    const nextVal = !startStageVehicleAdjust.show;
    closeAllPanelsExcept(panelName);
    startStageVehicleAdjust.show = nextVal;
  } else if (panelName === 'tanker') {
    const nextVal = !isTankerPanelExpanded.value;
    closeAllPanelsExcept(panelName);
    isTankerPanelExpanded.value = nextVal;
  } else if (panelName === 'uavugv') {
    const nextVal = !isUavUgvPanelExpanded.value;
    closeAllPanelsExcept(panelName);
    isUavUgvPanelExpanded.value = nextVal;
  } else if (panelName === 'ugvPopup') {
    const nextVal = !isUgvPopupPanelExpanded.value;
    closeAllPanelsExcept(panelName);
    isUgvPopupPanelExpanded.value = nextVal;
  } else if (panelName === 'uavPopup') {
    const nextVal = !isUavPopupPanelExpanded.value;
    closeAllPanelsExcept(panelName);
    isUavPopupPanelExpanded.value = nextVal;
  } else if (panelName === 'simulationPopup') {
    const nextVal = !isSimulationPopupPanelExpanded.value;
    closeAllPanelsExcept(panelName);
    isSimulationPopupPanelExpanded.value = nextVal;
  }
}

function closeAllPanelsExcept(exceptPanel) {
  if (exceptPanel !== 'camera') cameraAdjust.show = false;
  if (exceptPanel !== 'traffic') trafficConfig.show = false;
  if (exceptPanel !== 'startCar') startStageVehicleAdjust.show = false;
  if (exceptPanel !== 'tanker') isTankerPanelExpanded.value = false;
  if (exceptPanel !== 'uavugv') isUavUgvPanelExpanded.value = false;
  if (exceptPanel !== 'ugvPopup') isUgvPopupPanelExpanded.value = false;
  if (exceptPanel !== 'uavPopup') isUavPopupPanelExpanded.value = false;
  if (exceptPanel !== 'simulationPopup') isSimulationPopupPanelExpanded.value = false;
  if (exceptPanel !== 'secPopup') isSecDisasterPopupPanelExpanded.value = false;
}




function toggleLightPanel() {
  togglePanel('light');
}

function snapLightTo(sceneType) {
  if (sceneType === 'truck') {
    lightAdjust.lng = 113.105001;
    lightAdjust.lat = 30.385353;
    lightAdjust.height = 8.5;
    lightAdjust.heading = 16;
  } else if (sceneType === 'tanker') {
    lightAdjust.lng = 114.894472;
    lightAdjust.lat = 30.632203;
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
coordCopiedMessage.value = '复制失败，请手动记录';
  });
}











// 🛰️ 微调控制台面板展开状态与控制函数
const isTankerPanelExpanded = ref(false)
const isUavUgvPanelExpanded = ref(false)
const isUgvPopupPanelExpanded = ref(false)
const isUavPopupPanelExpanded = ref(false)
const isSimulationPopupPanelExpanded = ref(false)











// 🔥💨 后期感知阶段（7阶段及以后）粒子微调参数与控制
const isLateFirePanelExpanded = ref(false);
const lateFireCopiedMessage = ref('');
const activeParticleTab = ref('fire');

function toggleLateFirePanel() {
  togglePanel('lateFire');
}

const lateFireAdjust = reactive({
  imageWidth: 10,
  imageHeight: 10,
  emissionRate: 20.0,
  endScale: 0.6,
  maxSpeed: 0.4,
  gravity: 0.2,
  drag: 0.92,
  minSpeed: 0.1,
  startScale: 0.2,
  minLife: 2.0,
  maxLife: 4.0
});

function resetLateFireParams() {
  lateFireAdjust.imageWidth = 10;
  lateFireAdjust.imageHeight = 10;
  lateFireAdjust.emissionRate = 20.0;
  lateFireAdjust.endScale = 0.6;
  lateFireAdjust.maxSpeed = 0.4;
  lateFireAdjust.gravity = 0.2;
  lateFireAdjust.drag = 0.92;
  lateFireAdjust.minSpeed = 0.1;
  lateFireAdjust.startScale = 0.2;
  lateFireAdjust.minLife = 2.0;
  lateFireAdjust.maxLife = 4.0;
}

function copyLateFireParams() {
  const params = `lateFireAdjust.imageWidth = ${lateFireAdjust.imageWidth};\nlateFireAdjust.imageHeight = ${lateFireAdjust.imageHeight};\nlateFireAdjust.emissionRate = ${lateFireAdjust.emissionRate};\nlateFireAdjust.endScale = ${lateFireAdjust.endScale};\nlateFireAdjust.maxSpeed = ${lateFireAdjust.maxSpeed};\nlateFireAdjust.gravity = ${lateFireAdjust.gravity};\nlateFireAdjust.drag = ${lateFireAdjust.drag};\nlateFireAdjust.minSpeed = ${lateFireAdjust.minSpeed};\nlateFireAdjust.startScale = ${lateFireAdjust.startScale};\nlateFireAdjust.minLife = ${lateFireAdjust.minLife};\nlateFireAdjust.maxLife = ${lateFireAdjust.maxLife};`;
  navigator.clipboard.writeText(params).then(() => {
    lateFireCopiedMessage.value = '已成功复制火焰参数到剪贴板！';
    setTimeout(() => {
      lateFireCopiedMessage.value = '';
    }, 2000);
  }).catch(err => {
    console.error('复制失败:', err);
    lateFireCopiedMessage.value = '复制失败，请手动记录';
    setTimeout(() => {
      lateFireCopiedMessage.value = '';
    }, 2000);
  });
}

// 实时监听微调面板数值变化，热更新火焰粒子系统参数
watch(lateFireAdjust, (newVals) => {
  if (fireParticle && props.activePhaseIndex >= 6) {
    const isBigFire = (props.activePhaseIndex === 6);
    const fireScaleBase = isBigFire ? 2.0 : 1.0;

    fireParticle.startScale = newVals.startScale * fireScaleBase;
    fireParticle.endScale = newVals.endScale * fireScaleBase;
    fireParticle.emissionRate = newVals.emissionRate;
    fireParticle.imageSize = new Cesium.Cartesian2(newVals.imageWidth, newVals.imageHeight);
    fireParticle.minimumSpeed = newVals.minSpeed;
    fireParticle.maximumSpeed = newVals.maxSpeed;
    fireParticle.minimumParticleLife = newVals.minLife;
    fireParticle.maximumParticleLife = newVals.maxLife;
    fireParticle.updateCallback = (particle, dt) => {
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, newVals.gravity * dt, gravityScratch);
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);

      const dragFactor = Math.pow(newVals.drag, dt * 60);
      particle.velocity.x *= dragFactor;
      particle.velocity.y *= dragFactor;
      particle.velocity.z *= dragFactor;
    };
  }
}, { deep: true });

// 💨 烟雾粒子微调参数与控制
const lateSmokeAdjust = reactive({
  imageWidth: 15,
  imageHeight: 15,
  emissionRate: 20.0,
  endScale: 2.0,
  maxSpeed: 1.5,
  gravity: 1.0,
  drag: 0.95,
  minSpeed: 0.5,
  startScale: 0.5,
  minLife: 3.0,
  maxLife: 6.0
});

function resetLateSmokeParams() {
  lateSmokeAdjust.imageWidth = 15;
  lateSmokeAdjust.imageHeight = 15;
  lateSmokeAdjust.emissionRate = 20.0;
  lateSmokeAdjust.endScale = 2.0;
  lateSmokeAdjust.maxSpeed = 1.5;
  lateSmokeAdjust.gravity = 1.0;
  lateSmokeAdjust.drag = 0.95;
  lateSmokeAdjust.minSpeed = 0.5;
  lateSmokeAdjust.startScale = 0.5;
  lateSmokeAdjust.minLife = 3.0;
  lateSmokeAdjust.maxLife = 6.0;
}

function copyLateSmokeParams() {
  const params = `lateSmokeAdjust.imageWidth = ${lateSmokeAdjust.imageWidth};\nlateSmokeAdjust.imageHeight = ${lateSmokeAdjust.imageHeight};\nlateSmokeAdjust.emissionRate = ${lateSmokeAdjust.emissionRate};\nlateSmokeAdjust.endScale = ${lateSmokeAdjust.endScale};\nlateSmokeAdjust.maxSpeed = ${lateSmokeAdjust.maxSpeed};\nlateSmokeAdjust.gravity = ${lateSmokeAdjust.gravity};\nlateSmokeAdjust.drag = ${lateSmokeAdjust.drag};\nlateSmokeAdjust.minSpeed = ${lateSmokeAdjust.minSpeed};\nlateSmokeAdjust.startScale = ${lateSmokeAdjust.startScale};\nlateSmokeAdjust.minLife = ${lateSmokeAdjust.minLife};\nlateSmokeAdjust.maxLife = ${lateSmokeAdjust.maxLife};`;
  navigator.clipboard.writeText(params).then(() => {
    lateFireCopiedMessage.value = '已成功复制烟雾参数到剪贴板！';
    setTimeout(() => {
      lateFireCopiedMessage.value = '';
    }, 2000);
  }).catch(err => {
    console.error('复制失败:', err);
    lateFireCopiedMessage.value = '复制失败，请手动记录';
    setTimeout(() => {
      lateFireCopiedMessage.value = '';
    }, 2000);
  });
}

// 实时监听微调面板数值变化，热更新烟雾粒子系统参数
watch(lateSmokeAdjust, (newVals) => {
  if (smokeParticle && props.activePhaseIndex >= 5) {
    const smokeScaleBase = 0.35;

    smokeParticle.startScale = newVals.startScale * smokeScaleBase;
    smokeParticle.endScale = newVals.endScale * smokeScaleBase;
    smokeParticle.emissionRate = newVals.emissionRate;
    smokeParticle.imageSize = new Cesium.Cartesian2(newVals.imageWidth, newVals.imageHeight);
    smokeParticle.minimumSpeed = newVals.minSpeed;
    smokeParticle.maximumSpeed = newVals.maxSpeed;
    smokeParticle.minimumParticleLife = newVals.minLife;
    smokeParticle.maximumParticleLife = newVals.maxLife;
    smokeParticle.updateCallback = (particle, dt) => {
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, newVals.gravity * dt, gravityScratch);
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);

      const dragFactor = Math.pow(newVals.drag, dt * 60);
      particle.velocity.x *= dragFactor;
      particle.velocity.y *= dragFactor;
      particle.velocity.z *= dragFactor;
    };
  }
}, { deep: true });

// 自动检测场景切换并联动灯光坐标

function goToSensorManage(target = '') {
  const query = target ? { target } : {}
  router.push({ path: '/sensor-manage', query })
}

// 当前选中的场景
const currentScene = ref('truck')

function isStorySceneFocused() {
  return props.focusedPointId === 'accident_blue' || props.focusedPointId === 'accident_red'
}

// 无人机视频/图像时间戳更新
const currentTimeStr = ref('')
const updateTime = () => {
  const now = new Date()
  const pad = (num) => String(num).padStart(2, '0')
  currentTimeStr.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}
let timeInterval = null

// 阶段索引到模型id的映射
const phaseToModelMap = {
  0: null,
  1: 'model_normal',
  2: 'model_accident',
  3: 'model_accident',
  4: 'model_accident',
  5: 'model_accident',
  6: 'model_accident',
  7: 'model_accident',
  8: 'model_accident',
  9: 'model_accident',
  10: 'model_accident',
  11: 'model_accident'
}

// 油罐车阶段索引到模型id的映射
const tankerPhaseToModelMap = {
  0: null,
  1: 'tanker_normal',
  2: 'tanker_accident',
  3: 'tanker_accident',
  4: 'tanker_accident',
  5: 'tanker_accident',
  6: 'tanker_accident',
  7: 'tanker_accident',
  8: 'tanker_accident',
  9: 'tanker_accident',
  10: 'tanker_accident',
  11: 'tanker_accident'
}

// 无人机多角度照片拍摄状态与三维实景重构控制台
const capturedPhotos = ref([false, false, false, false])
const activePhotoIndex = ref(null)
const isReconstructionPanelVisible = ref(true)
const reconstructionActiveTab = ref('photo') // 'photo' | '3d'
const reconstructionProcessState = ref('capturing') // 'capturing' | 'building' | 'done'
const reconstructionProgress = ref(0)
const reconstructionStageText = ref('等待航拍多源影像采集对齐...')
let reconstructionBuildTimer = null

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

const handleSelectPhotoThumb = (index) => {
  if (capturedPhotos.value[index]) {
    activePhotoIndex.value = index
    reconstructionActiveTab.value = 'photo'
  }
}

// 监听航拍抓拍张数：抓拍过程中保持 photo 模式，抓拍完4张后先展示“正在构建三维模型中...”，构建完成后再加载显示三维模型
watch(capturedCount, (newCount) => {
  if (newCount < 4) {
    reconstructionProcessState.value = 'capturing'
    reconstructionProgress.value = newCount * 20
    reconstructionStageText.value = `已采集 ${newCount}/4 视角，正在等待全部方位对齐...`
  } else if (newCount === 4) {
    // 4 张抓拍全部完成：自动进入“正在构建三维模型”过程，完成后加载模型
    reconstructionProcessState.value = 'building'
    reconstructionActiveTab.value = '3d'
    reconstructionProgress.value = 35
    reconstructionStageText.value = '4 组多视角影像采集完成，正在执行空三解算与特征匹配...'

    if (reconstructionBuildTimer) clearTimeout(reconstructionBuildTimer)

    setTimeout(() => {
      if (capturedCount.value === 4) {
        reconstructionProgress.value = 70
        reconstructionStageText.value = 'SfM 稀疏点云稠密化中，求解空间几何三角网与深度图...'
      }
    }, 700)

    setTimeout(() => {
      if (capturedCount.value === 4) {
        reconstructionProgress.value = 92
        reconstructionStageText.value = '3DGS 神经辐射场迭代收敛中，生成实景纹理映射...'
      }
    }, 1500)

    setTimeout(() => {
      if (capturedCount.value === 4) {
        reconstructionProgress.value = 100
        reconstructionProcessState.value = 'done'
        reconstructionStageText.value = '✨ 三维实景数字孪生模型构建完成！'
        reconstructionActiveTab.value = '3d'
        // 完成模型构建后，才允许时间轴离开“无人感知执行”。
        emit('reconstruction-ready', true)
      }
    }, 2200)
  }
})

const currentPhotoSrc = computed(() => {
  const isTruck = props.phases[0]?.id.startsWith('t-')
  return isTruck ? '/Dashboard/images/uav_aerial_photo.png' : '/Dashboard/images/tanker_aerial_photo.png'
})

const flyingPhotos = ref([]);

function triggerPhotoAnimation(index, cartesianPos) {
  if (!viewer) return;
  // 信号干扰阶段（index 10）和救援装备出动阶段（index 11）严禁拍摄和飞图
  const currentPhase = Number(props.activePhaseIndex);
  if (currentPhase >= 10) {
    flyingPhotos.value = [];
    return;
  }
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

const isSecDisasterPopupPanelExpanded = ref(false);

const truckSecPopupAdjust = reactive({
  xOffset: -575,
  yOffset: 44
});

const tankerSecPopupAdjust = reactive({
  xOffset: -1991,
  yOffset: 124
});

 // 'truck' | 'tanker'





const secondaryDisasterVideoPopup = reactive({
  show: true,
  x: 500,
  y: 200,
  title: '次生灾害精细建模',
});

// 无人机出动状态与坐标
const rescueCoords = reactive({ lng: 113.10725, lat: 30.38491, height: 24.0 });



const rescuePopup = reactive({
  show: true,
  title: '无人机出发',
  model: 'DJI M300 RTK',
  altitude: '100 m',
  speed: '15 m/s',
  status: '已出发',
  x: 0,
  y: 0,
  xOffset: -10,
  yOffset: 15
});

// 无人车出动状态与坐标
const ugvCoords = reactive({ lng: 113.10725, lat: 30.38491, height: 5.0 });

const ugvPopup = reactive({
  show: true,
  title: '无人车出发',
  model: 'SCOUT 2.0',
  count: '4 辆',
  speed: '5 km/h',
  status: '已出发',
  x: 0,
  y: 0,
  xOffset: -27,
  yOffset: -133
});

// 场景隔离的悬浮窗微调存储
const truckRescuePopupAdjust = reactive({
  xOffset: -10,
  yOffset: 15,
  reachedXOffset: 161,
  reachedYOffset: -62
});

const tankerRescuePopupAdjust = reactive({
  xOffset: -239,
  yOffset: -9,
  reachedXOffset: 186,
  reachedYOffset: -434
});

const truckUgvPopupAdjust = reactive({
  xOffset: -27,
  yOffset: -133,
  reachedXOffset: -200,
  reachedYOffset: 143
});

const tankerUgvPopupAdjust = reactive({
  xOffset: 115,
  yOffset: -133,
  reachedXOffset: -540,
  reachedYOffset: 274
});



// 🛣️ 整体向东/西/南/北快捷平移整条道路航点轨迹 (米)


// 📋 复制最新调整好的道路航点 Coordinates 代码


// 监听微调变更，自动回写到对应场景配置中
watch(() => [rescuePopup.xOffset, rescuePopup.yOffset], ([x, y]) => {
  const isTanker = currentScene.value === 'tanker';
  const target = isTanker ? tankerRescuePopupAdjust : truckRescuePopupAdjust;
  if (rescuePopup.title === '无人机已到达') {
    target.reachedXOffset = x;
    target.reachedYOffset = y;
  } else {
    target.xOffset = x;
    target.yOffset = y;
  }
});

watch(() => [ugvPopup.xOffset, ugvPopup.yOffset], ([x, y]) => {
  const isTanker = currentScene.value === 'tanker';
  const target = isTanker ? tankerUgvPopupAdjust : truckUgvPopupAdjust;
  if (ugvPopup.title === '无人车已就位') {
    target.reachedXOffset = x;
    target.reachedYOffset = y;
  } else {
    target.xOffset = x;
    target.yOffset = y;
  }
});









// 无人车传感器面板的 A/B 切换标签
const activeUgvSensorTab = ref('A');

// 城市高亮上浮高度 (仙桃与黄冈)
const xiantaoHeight = ref(0);
const huanggangHeight = ref(0);

let rescueMarkerEntity = null;

let sharedTruckRescueCarPosition = null;
let sharedTankerRescueCarPosition = null;
let sharedTruckUavPosition = null;
let sharedTankerUavPosition = null;

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


const currentTruckAdjust = computed(() => {
  return currentScene.value === 'truck' ? truckAdjust : tankerAdjust
})

const currentPointAdjust = computed(() => {
  return currentScene.value === 'truck' ? truckPointAdjust : tankerPointAdjust
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
  lng: 114.894463,
  lat: 30.632121,
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
// 救援车配置（2个模型，每个模型2辆车，合计4辆。利用 stopFactor 组成一字纵队）
const rescueCarModelConfigs = [
  { id: 'rescue_car_model_1', uri: '/Dashboard/models/recure car.glb', label: '1号车队(前)', stopFactor: 0.78 },
  { id: 'rescue_car_model_2', uri: '/Dashboard/models/recure car.glb', label: '2号车队(后)', stopFactor: 0.72 }
]

// 油罐车场景救援车配置（同理，一字纵队排开）
const tankerRescueCarModelConfigs = [
  { id: 'tanker_rescue_car_model_1', uri: '/Dashboard/models/recure car_2.glb', label: '1号油罐救援(前)', stopFactor: 0.78 },
  { id: 'tanker_rescue_car_model_2', uri: '/Dashboard/models/recure car_2.glb', label: '2号油罐救援(后)', stopFactor: 0.72 }
]

// 货车追尾现场 - 仿真开始节点贴地行驶车流配置 (0-1.glb, 0-2.glb, 0-3.glb, 0-4.glb)
// 固化用户调试确认的 P1 ~ P8 8 个核心沥青公路中线航点
const startStageRoadWaypoints = reactive([
  [113.108860, 30.384539], // P1
  [113.106710, 30.385000], // P2
  [113.104870, 30.385469], // P3 (事故现场中心)
  [113.103030, 30.385937], // P4
  [113.101490, 30.386398], // P5
  [113.099960, 30.386858], // P6
  [113.098420, 30.387319], // P7
  [113.097190, 30.387779]  // P8
])

const tankerRoute1Waypoints = reactive([
  [114.889520, 30.635000],
  [114.889960, 30.633500],
  [114.890180, 30.632203],
  [114.890180, 30.631000],
  [114.890180, 30.630180]
])

const tankerRoute2Waypoints = reactive([
  [114.884250, 30.625090],
  [114.886010, 30.626490],
  [114.887760, 30.627890],
  [114.888420, 30.628420],
  [114.889740, 30.629470]
])

const startStageVehicleConfigs = [
  { id: 'start_stage_car_01', uri: '/Dashboard/models/0-1.glb', label: '仿真初始车辆01(大客车)', delayRatio: 0.00, speedFactor: 0.85, laneOffset: 0.000025, scale: 0.82 },
  { id: 'start_stage_car_02', uri: '/Dashboard/models/0-2.glb', label: '仿真初始车辆02(跑车)', delayRatio: 0.12, speedFactor: 1.20, laneOffset: -0.000025, scale: 0.82 },
  { id: 'start_stage_car_03', uri: '/Dashboard/models/0-3.glb', label: '仿真初始车辆03(轿车)', delayRatio: 0.24, speedFactor: 1.05, laneOffset: -0.000020, scale: 0.82 },
  { id: 'start_stage_car_04', uri: '/Dashboard/models/0-4.glb', label: '仿真初始车辆04(轿跑)', delayRatio: 0.36, speedFactor: 0.95, laneOffset: 0.000020, scale: 0.82 }
]

let startStageVehicleEntities = []

// 🚚 仿真初始车流 (0-1~0-4.glb) 动态微调面板状态
const startStageVehicleAdjust = reactive({
  show: false,
  isPaused: false,         // 默认【开始行驶】状态（点击仿真开始即可播放车流行驶动画）
  showRoadLine: true,      // 路线与航点 Marker 隐藏/显示开关（开启显示 P1~P8 航点与路线）
  activeTab: 'car1',       // 默认激活 0-1.glb (车辆01) 独立控制面板
  selectedWaypointIndex: 0, // 默认选中 P1 道路航点索引 (0~7)
  selectedTankerRouteIndex: 0, // 油罐车路线选择 (0: 路线1 南北, 1: 路线2 东西)
  loopDurationSec:6,     // 单圈时长(s)
  
  // 🚚 货车追尾现场 - 4 辆车的独立缩放、航向及经纬度参数
  carsTruck: [
    { name: '0-1.glb (车辆01)', scale: 0.40, lngOffset: 0.0, latOffset: 0.0, heading: -166 },
    { name: '0-2.glb (车辆02)', scale: 1.00, lngOffset: -0.00010, latOffset: 0.0, heading: -92 },
    { name: '0-3.glb (车辆03)', scale: 4.30, lngOffset: 0.00020, latOffset: 0.0, heading: -92 },
    { name: '0-4.glb (车辆04)', scale: 2.45, lngOffset: 0.0, latOffset: 0.0, heading: -88 }
  ],
  // ⛽ 油罐车泄露现场 - 4 辆车的独立缩放、航向及经纬度参数
  carsTanker: [
    { name: '0-1.glb (车辆01)', scale: 0.60, lngOffset: 0.0001, latOffset: 0.0, heading: -166 },
    { name: '0-2.glb (车辆02)', scale: 1.50, lngOffset: -0.00010, latOffset: 0.0, heading: -92 },
    { name: '0-3.glb (车辆03)', scale: 6.65, lngOffset: 0.00010, latOffset: 0.0, heading: -92 },
    { name: '0-4.glb (车辆04)', scale: 5.10, lngOffset: -0.00020, latOffset: 0.0, heading: -88 }
  ],
  
  copiedMsg: ''
})

watch(
  () => [
    props.phases?.[0]?.id,
    startStageVehicleAdjust.loopDurationSec,
    agentSpeedConfig.uavDuration,
    agentSpeedConfig.ugvDuration
  ],
  emitPlaybackDurations,
  { immediate: true }
)

// 根据当前场景返回对应的 cars 数组
const activeCars = computed(() =>
  currentScene.value === 'tanker' ? startStageVehicleAdjust.carsTanker : startStageVehicleAdjust.carsTruck
)





let startStageVehicleLastFrameTime = Date.now()
let startStageVehicleRunningTimeMs = 0

// Catmull-Rom 样条平滑轨迹插值计算器（支持车辆沿真实 Cesium 弧形公路自然转弯）
function getCatmullRomSplinePoint(pts, globalT) {
  const n = pts.length;
  if (n < 2) return { lng: pts[0][0], lat: pts[0][1], baseHeadingRad: 0 };
  
  let t = Math.max(0.0, Math.min(globalT, 1.0));

  const totalSegments = n - 1;
  const scaledT = t * totalSegments;
  const idx = Math.min(Math.floor(scaledT), totalSegments - 1);
  const u = scaledT - idx;

  const p0 = pts[Math.max(0, idx - 1)];
  const p1 = pts[idx];
  const p2 = pts[Math.min(n - 1, idx + 1)];
  const p3 = pts[Math.min(n - 1, idx + 2)];

  const u2 = u * u;
  const u3 = u2 * u;

  // Catmull-Rom 位置基函数
  const f0 = -0.5 * u3 + u2 - 0.5 * u;
  const f1 = 1.5 * u3 - 2.5 * u2 + 1.0;
  const f2 = -1.5 * u3 + 2.0 * u2 + 0.5 * u;
  const f3 = 0.5 * u3 - 0.5 * u2;

  const lng = p0[0] * f0 + p1[0] * f1 + p2[0] * f2 + p3[0] * f3;
  const lat = p0[1] * f0 + p1[1] * f1 + p2[1] * f2 + p3[1] * f3;

  // 一阶导数（用于导出现在时刻平滑的切线行驶方向 Heading）
  const df0 = -1.5 * u2 + 2.0 * u - 0.5;
  const df1 = 4.5 * u2 - 5.0 * u;
  const df2 = -4.5 * u2 + 4.0 * u + 0.5;
  const df3 = 1.5 * u2 - 1.0 * u;

  const dLngdt = p0[0] * df0 + p1[0] * df1 + p2[0] * df2 + p3[0] * df3;
  const dLatdt = p0[1] * df0 + p1[1] * df1 + p2[1] * df2 + p3[1] * df3;

  const cosLat = Math.cos(Cesium.Math.toRadians(lat));
  const dX = dLngdt * cosLat;
  const dY = dLatdt;
  const baseHeadingRad = Math.atan2(dX, dY);

  return { lng, lat, baseHeadingRad };
}

function getStartStageVehiclePosAndOrient(index, overrideDelay) {
  const now = Date.now()
  const delta = now - startStageVehicleLastFrameTime
  startStageVehicleLastFrameTime = now

  if (!startStageVehicleAdjust.isPaused) {
    startStageVehicleRunningTimeMs += delta
  }

  const carsArr = activeCars.value
  const carParam = (carsArr && carsArr[index])
    ? carsArr[index]
    : { scale: 1.0, lngOffset: 0, latOffset: 0, heading: 0 }

  const totalLngOffset = carParam.lngOffset || 0
  const totalLatOffset = carParam.latOffset || 0
  const totalHeadingOffset = carParam.heading || 0

  let waypoints = startStageRoadWaypoints;
  if (typeof currentScene !== 'undefined' && currentScene.value === 'tanker') {
    waypoints = (index < 2) ? tankerRoute1Waypoints : tankerRoute2Waypoints;
  }

  if (!waypoints || waypoints.length < 2) {
    const pos = Cesium.Cartesian3.fromDegrees(113.104833 + totalLngOffset, 30.385469 + totalLatOffset, 0)
    const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(17 + totalHeadingOffset), 0, 0)
    const orient = Cesium.Transforms.headingPitchRollQuaternion(pos, hpr)
    return { position: pos, orientation: orient }
  }

  const config = startStageVehicleConfigs[index] || { delayRatio: 0, speedFactor: 1.0, laneOffset: 0 }

  const durationMs = (startStageVehicleAdjust.loopDurationSec || 18) * 1000
  const speedFactor = config.speedFactor || 1.0
  const delayRatio = overrideDelay !== undefined ? overrideDelay : (config.delayRatio !== undefined ? config.delayRatio : 0)

  // 所有车辆均从 P1 起点发车，按 delayRatio 间隔依次错峰发车
  const globalProgress = startStageVehicleRunningTimeMs / durationMs
  const elapsedProgress = globalProgress - delayRatio

  let t = 0
  if (elapsedProgress > 0) {
    // 已经到了发车时刻，从 P1 出发沿着公路中线向前行驶（单次播放，到达终点后停止）
    t = Math.min(elapsedProgress * speedFactor, 1.0)
  } else {
    // 尚未到达发车时刻，停留在 P1 起点等待发车
    t = 0
  }

  // 采用 Catmull-Rom 样条算法进行道路平滑弧线插值与动态切线姿态推算
  const spline = getCatmullRomSplinePoint(waypoints, t);

  // 根据道路切线方向求出垂直法线，进行车道横向偏移 (快车走左侧超车道, 慢车走右侧行车道)
  const laneOffset = config.laneOffset || 0
  const normalLng = Math.cos(spline.baseHeadingRad) * laneOffset
  const normalLat = -Math.sin(spline.baseHeadingRad) * laneOffset

  const finalLng = spline.lng + totalLngOffset + normalLng;
  const finalLat = spline.lat + totalLatOffset + normalLat;
  const position = Cesium.Cartesian3.fromDegrees(finalLng, finalLat, 0);

  // 车辆沿着真实的公路弧线切线自然转弯 + 附加用户独立的 Heading 微调值
  const headingRad = spline.baseHeadingRad + Cesium.Math.toRadians(totalHeadingOffset);
  const orientation = Cesium.Transforms.headingPitchRollQuaternion(
    position,
    new Cesium.HeadingPitchRoll(headingRad, 0, 0)
  );

  return { position, orientation }
}

// 无人机位置调整（起始点：仙桃市三伏潭镇专职消防队）
const uavAdjust = reactive({
  scale: 58.3,
  heading: 18,
  lng: 113.202,
  lat: 30.3268,
  height: 98.8
});

const rescueCarAdjust = reactive({
  scale: 260.7,
  heading: 195,
  moveHeading: 0,
  lng: 113.1073,
  lat: 30.3849,
  height: -1.8
});

let uavEntities = []
let rescueCarEntities = []
let phase3StartTime = 0
let phase4StartTime = 0
let phase6StartTime = 0
let phase7StartTime = 0
let phase8StartTime = 0
let uavOrbitStartTime = 0
let diffusionStartTime = 0
let lastUavPhaseIndex = -1
let uavRotorAngle = 0

// 油罐车场景的无人机和救援车配置（独立控制）
const tankerUavAdjust = reactive({
  scale: 67.3,
  heading: 34,
  lng: 114.89539,
  lat: 30.63129,
  height: 120.0
});

const tankerRescueCarAdjust = reactive({
  scale: 250,
  heading: 88,       // 部署阶段航向（阶段7~8）
  execHeading: 150,  // 执行阶段航向（阶段9+）
  moveHeading: 0,
  lng: 114.894141,
  lat: 30.631815,
  height: 0.0
});








let highlightPathEntity = null;

function updateHighlightPath(positions) {
  if (!viewer) return;
  
  if (highlightPathEntity) {
    viewer.entities.remove(highlightPathEntity);
    highlightPathEntity = null;
  }
  
  if (!positions || positions.length < 2) return;
  
  highlightPathEntity = viewer.entities.add({
    id: 'Car_Path_Highlight',
    name: '无人感知部署段 (200m)',
    show: Number(props.activePhaseIndex) >= 7,
    polyline: {
      positions: positions,
      width: 6,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.2,
        color: Cesium.Color.fromCssColorString('#00ffcc')
      }),
      clampToGround: true
    }
  });
}

function getPathTotalLength(pathPoints) {
  if (!pathPoints || pathPoints.length < 2) return 0;
  let totalLength = 0;
  for (let i = 0; i < pathPoints.length - 1; i++) {
    totalLength += Cesium.Cartesian3.distance(pathPoints[i], pathPoints[i+1]);
  }
  return totalLength;
}

function getQueryTime(viewerTime) {
  const t = viewerTime || (viewer && viewer.clock && viewer.clock.currentTime);
  if (currentMissionDataSource && currentMissionDataSource.clock && currentMissionDataSource.clock.stopTime) {
    if (t && Cesium.JulianDate.compare(t, currentMissionDataSource.clock.stopTime) > 0) {
      return currentMissionDataSource.clock.stopTime;
    }
  }
  return t;
}

function getUgvLast200mPosition(currentSceneName, activePhaseIndex, phaseStartTime, viewerTime, stopFactor) {
  if (!viewer || !currentMissionDataSource) return null;
  
  const carPath = currentMissionDataSource.entities.getById('Car_Path') || currentMissionDataSource.entities.getById('AgentPath_road');
  if (!carPath || !carPath.polyline || !carPath.polyline.positions) return null;
  
  const queryTime = getQueryTime(viewerTime);
  const rawPositions = carPath.polyline.positions.getValue(queryTime) ||
                    carPath.polyline.positions.getValue(new Cesium.JulianDate());
  if (!rawPositions || rawPositions.length < 2) return null;
  
  let positions = rawPositions;
  
  const fullLength = getPathTotalLength(positions);
  
  const baseStopDist = currentSceneName === 'tanker' ? 80.0 : 50.0;
  const factor = stopFactor !== undefined ? stopFactor : 0.78;
  const targetStopDist = baseStopDist + (0.78 - factor) * 250.0;
  
  const ratio200m = fullLength > 0.0 ? Math.max(0.0, fullLength - targetStopDist - 200.0) / fullLength : 0.0;
  const ratioStop = fullLength > 0.0 ? Math.max(0.0, fullLength - targetStopDist) / fullLength : 0.0;
  
  if (activePhaseIndex === 7) {
    // 阶段6：无人装备出动。从起点行驶到最后200m起点 (6秒内)
    if (currentSceneName === 'truck') {
      if (!phase6StartTime) {
        phase6StartTime = Date.now();
      }
    } else {
      if (!tankerPhase6StartTime) {
        tankerPhase6StartTime = Date.now();
      }
    }
    const actualStartTime = currentSceneName === 'truck' ? phase6StartTime : tankerPhase6StartTime;
    const elapsed = Date.now() - actualStartTime;
    const duration = currentSceneName === 'truck' ? agentSpeedConfig.ugvDuration * 1000 : 10000;
    const t = Math.min(elapsed / duration, 1.0);
    
    if (t >= 1.0) {
      const pos200m = getPositionAtRatio(positions, ratio200m);
      const pos200mNext = getPositionAtRatio(positions, Math.min(ratio200m + 0.01, 1.0));
      const baseHeading = getSegmentHeading(positions[positions.length - 2], positions[positions.length - 1]);
      const heading = (pos200m && pos200mNext) ? getSegmentHeading(pos200m, pos200mNext) : baseHeading;
      return { pos: pos200m, headingRad: heading };
    }
    
    const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const currentRatio = ratio200m * easeT;
    const pos = getPositionAtRatio(positions, currentRatio);
    
    const nextT = Math.min((elapsed + 100) / duration, 1.0);
    const nextEaseT = nextT < 0.5 ? 2 * nextT * nextT : 1 - Math.pow(-2 * nextT + 2, 2) / 2;
    const nextRatio = ratio200m * nextEaseT;
    const nextPos = getPositionAtRatio(positions, nextRatio);
    let heading = 0;
    if (pos && nextPos) {
      heading = getSegmentHeading(pos, nextPos);
    }
    return { pos, headingRad: heading };
    
  } else if (activePhaseIndex === 8) {
    // 阶段7：从200米起点运动到终点 (6秒内)
    if (currentSceneName === 'truck') {
      if (!phase7StartTime) {
        phase7StartTime = Date.now();
      }
    } else {
      if (!tankerPhase7StartTime) {
        tankerPhase7StartTime = Date.now();
      }
    }
    const actualStartTime = currentSceneName === 'truck' ? phase7StartTime : tankerPhase7StartTime;
    const elapsed = Date.now() - actualStartTime;
    const duration = 6000;
    const t = Math.min(elapsed / duration, 1.0);
    
    if (t >= 1.0) {
      const finalPos = getPositionAtRatio(positions, ratioStop);
      const finalPosPrev = getPositionAtRatio(positions, Math.max(0.0, ratioStop - 0.01));
      const heading = (finalPosPrev && finalPos) ? getSegmentHeading(finalPosPrev, finalPos) : 0;
      return { pos: finalPos, headingRad: heading, isParked: true };
    }
    
    const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const currentRatio = ratio200m + (ratioStop - ratio200m) * easeT;
    const pos = getPositionAtRatio(positions, currentRatio);
    
    const nextT = Math.min((elapsed + 100) / duration, 1.0);
    const nextEaseT = nextT < 0.5 ? 2 * nextT * nextT : 1 - Math.pow(-2 * nextT + 2, 2) / 2;
    const nextRatio = ratio200m + (ratioStop - ratio200m) * nextEaseT;
    const nextPos = getPositionAtRatio(positions, nextRatio);
    let heading = 0;
    if (pos && nextPos) {
      heading = getSegmentHeading(pos, nextPos);
    }
    return { pos, headingRad: heading };
    
  } else {
    // 阶段8及以后：停在现场终点处
    const finalPos = getPositionAtRatio(positions, ratioStop);
    const finalPosPrev = getPositionAtRatio(positions, Math.max(0.0, ratioStop - 0.01));
    const heading = (finalPosPrev && finalPos) ? getSegmentHeading(finalPosPrev, finalPos) : 0;
    return { pos: finalPos, headingRad: heading, isParked: true };
  }
}

function getSegmentHeading(p1, p2) {
  if (!p1 || !p2) return 0;
  const cartoCur = Cesium.Cartographic.fromCartesian(p1);
  const cartoNext = Cesium.Cartographic.fromCartesian(p2);
  return Math.PI / 2 - Math.atan2(
    Cesium.Math.toDegrees(cartoNext.latitude) - Cesium.Math.toDegrees(cartoCur.latitude),
    Cesium.Math.toDegrees(cartoNext.longitude) - Cesium.Math.toDegrees(cartoCur.longitude)
  );
}

function getPositionAtRatio(pathPoints, ratio) {
  if (!pathPoints || pathPoints.length === 0) return null;
  if (pathPoints.length === 1) return pathPoints[0];
  
  let totalLength = 0;
  const segmentLengths = [];
  for (let i = 0; i < pathPoints.length - 1; i++) {
    const len = Cesium.Cartesian3.distance(pathPoints[i], pathPoints[i+1]);
    segmentLengths.push(len);
    totalLength += len;
  }
  
  if (totalLength === 0) return pathPoints[0];
  
  const targetDist = totalLength * ratio;
  let currentDist = 0;
  
  for (let i = 0; i < pathPoints.length - 1; i++) {
    const len = segmentLengths[i];
    if (currentDist + len >= targetDist) {
      const remaining = targetDist - currentDist;
      const fraction = len > 0 ? (remaining / len) : 0;
      const result = new Cesium.Cartesian3();
      Cesium.Cartesian3.lerp(pathPoints[i], pathPoints[i+1], fraction, result);
      return result;
    }
    currentDist += len;
  }
  return pathPoints[pathPoints.length - 1];
}


const TANKER_STOP_FACTOR = 1.0;

// 油罐车场景的无人机和救援车实体数组
let tankerUavEntities = []
let tankerRescueCarEntities = []
let tankerPhase3StartTime = 0
let tankerPhase4StartTime = 0
let tankerPhase6StartTime = 0
let tankerPhase7StartTime = 0
let tankerPhase8StartTime = 0
let tankerUavOrbitStartTime = 0
let lastTankerUavPhaseIndex = -1

const containerRef = ref(null)
const loading = ref(true)
const errorMessage = ref('')


// 父级侧栏与本组件的地图遮罩共享同一加载状态，避免加载时只虚化一侧。
watch(loading, (isLoading) => emit('loading-change', isLoading), { immediate: true })

let viewer = null
let spinCallback = null
let lastSpinAt = 0
let debugHandler = null
let removeLightListener = null
let initViewerTimeout = null
// 电子围栏作为独立图层维护：后续接入后端围栏坐标时，仅需替换传入的经纬度数组。
let electronicFenceEntities = []

// 市级边界、文字和围栏顶面共享同一高度，避免立体顶面遮挡行政信息。
const ELECTRONIC_FENCE_ROOF_HEIGHT = 18000
// 分离相机航向角
let truckOrbitHeading = Cesium.Math.toRadians(8)
let tankerOrbitHeading = Cesium.Math.toRadians(8)
let focusAreaEntity = null
let popupEntity = null 
let connectionLineEntity = null

// 事故现场三级视角状态与路侧摄像头解锁状态
const accidentViewLevel = ref(null) // 'far', 'medium', 'close', null (默认推演视角)
const light1Unlocked = ref(false)
const light23Unlocked = ref(false)

function isCameraDetailView(level = accidentViewLevel.value) {
  return level === 'medium' || level === 'close'
}

function isLight1CameraUnlocked() {
  return (light1Unlocked.value || props.focusedPointId === 'accident_blue') && accidentViewLevel.value !== 'far'
}

function isLight23CameraUnlocked() {
  return (light23Unlocked.value || props.focusedPointId === 'accident_red') && accidentViewLevel.value !== 'far'
}
const accidentDetailPopup = reactive({
  show: false,
  x: 0,
  y: 0,
  title: '',
  img: '',
  pointId: ''
})

// 故事线实时检测告警弹窗状态
const detectionPopup = reactive({
  show: false,
  state: 'idle', // 'idle' | 'detecting' | 'detected'
  progress: 0,
  x: 0,
  y: 0,
  scenarioKey: '',
  confidence: null,
  modelClass: '',
  modelClassZh: '',
  boxes: [],
  detectedItems: [],
  error: ''
})

let detectionTimer = null
let storyDetectionRequestId = 0

const cameraStreamVideoRef = ref(null)

const CAMERA_STREAM_CONFIGS = {
  light1: {
    title: '前方路侧摄像头',
    location: 'light1 路侧监控点',
    videoSrc: '/Dashboard/videos/light1-kling3.mp4',
    videoFileName: 'light1-kling3.mp4',
    model: 'SFGA-YOLO26M',
    startTime: '2.2'
  },
  light23: {
    title: '前方路侧摄像头',
    location: 'light23 路侧监控点',
    videoSrc: '/Dashboard/videos/light23-kling4.mp4',
    videoFileName: 'kling4.mp4',
    model: 'LCA-YOLO26N',
    startTime: '2.5'
  }
}

const cameraStreamPopup = reactive({
  show: false,
  x: 0,
  y: 0,
  title: '前方路侧摄像头',
  location: 'light1 路侧监控点',
  status: '在线',
  videoSrc: '/Dashboard/videos/light1-kling3.mp4',
  modelName: 'SFGA-YOLO26M',
  detectionState: 'idle',
  detectionStatus: '待检测',
  detectionMessage: '点击摄像头后自动从视频 2.2s 处开始检测',
  sampledFrames: 0,
  detectionCount: 0,
  bestLabel: '',
  bestConfidence: '--',
  videoWidth: 0,
  videoHeight: 0,
  videoFrames: [],
  activeVideoBoxes: []
})
let cameraVideoDetectionRequestId = 0

function resetCameraVideoDetectionState(config = CAMERA_STREAM_CONFIGS.light1) {
  cameraStreamPopup.detectionState = 'detecting'
  cameraStreamPopup.detectionStatus = '检测中'
  cameraStreamPopup.detectionMessage = `正在调用 ${config.model}，从视频 ${config.startTime}s 后开始抽帧检测...`
  cameraStreamPopup.sampledFrames = 0
  cameraStreamPopup.detectionCount = 0
  cameraStreamPopup.bestLabel = ''
  cameraStreamPopup.bestConfidence = '--'
  cameraStreamPopup.videoWidth = 0
  cameraStreamPopup.videoHeight = 0
  cameraStreamPopup.videoFrames = []
  cameraStreamPopup.activeVideoBoxes = []
}

function getCameraVideoBoxKind(className) {
  const key = String(className || '').toLowerCase()
  if (key.includes('nofire') || key.includes('no_fire') || key.includes('normal') || key.includes('无火') || key.includes('正常')) {
    return 'nofire'
  }
  if (key.includes('fire') || key.includes('火')) return 'fire'
  return 'default'
}

function normalizeCameraVideoFrame(frame, videoWidth, videoHeight) {
  const width = Math.max(Number(videoWidth) || 1, 1)
  const height = Math.max(Number(videoHeight) || 1, 1)
  const parsedTime = Number(frame?.time_s)
  const timeSeconds = Number.isFinite(parsedTime)
    ? parsedTime
    : (Number.parseFloat(String(frame?.time || '').replace('s', '')) || 0)

  const boxes = (Array.isArray(frame?.detections) ? frame.detections : [])
    .map((item) => {
      const coordinates = Array.isArray(item?.bbox) ? item.bbox.map(Number) : []
      if (coordinates.length < 4 || coordinates.some((value) => !Number.isFinite(value))) return null
      const [x1, y1, x2, y2] = coordinates
      const left = Math.max(0, Math.min(x1, width))
      const top = Math.max(0, Math.min(y1, height))
      const right = Math.max(left, Math.min(x2, width))
      const bottom = Math.max(top, Math.min(y2, height))
      if (right <= left || bottom <= top) return null
      const x = (left / width) * 100
      const y = (top / height) * 100
      const boxWidth = ((right - left) / width) * 100
      const boxHeight = ((bottom - top) / height) * 100
      return {
        x,
        y,
        width: boxWidth,
        height: boxHeight,
        labelY: Math.max(4, y - 1),
        label: item?.class || '目标',
        confidence: formatDetectionConfidence(item?.confidence),
        kind: getCameraVideoBoxKind(item?.class)
      }
    })
    .filter(Boolean)

  return { timeSeconds, boxes }
}

function syncCameraVideoBoxes() {
  const video = cameraStreamVideoRef.value
  const frames = cameraStreamPopup.videoFrames
  const currentTime = Number(video?.currentTime)
  if (!video || !frames.length || !Number.isFinite(currentTime)) {
    cameraStreamPopup.activeVideoBoxes = []
    return
  }

  let activeFrame = null
  for (const frame of frames) {
    if (frame.timeSeconds <= currentTime) {
      activeFrame = frame
    } else {
      break
    }
  }
  cameraStreamPopup.activeVideoBoxes = activeFrame?.boxes || []
}

function summarizeVideoDetections(frames) {
  let detectionCount = 0
  let bestDetection = null
  ;(frames || []).forEach((frame) => {
    const detections = Array.isArray(frame.detections) ? frame.detections : []
    detectionCount += detections.length
    detections.forEach((item) => {
      const confidence = Number(item.confidence)
      if (!Number.isFinite(confidence)) return
      if (!bestDetection || confidence > Number(bestDetection.confidence)) {
        bestDetection = item
      }
    })
  })
  return { detectionCount, bestDetection }
}

async function runCameraVideoDetection(lightId = 'light1') {
  const config = CAMERA_STREAM_CONFIGS[lightId] || CAMERA_STREAM_CONFIGS.light1
  const requestId = ++cameraVideoDetectionRequestId
  resetCameraVideoDetectionState(config)

  try {
    const videoResponse = await fetch(cameraStreamPopup.videoSrc, { cache: 'no-store' })
    if (!videoResponse.ok) throw new Error(`video HTTP ${videoResponse.status}`)

    const videoBlob = await videoResponse.blob()
    const formData = new FormData()
    formData.append('file', videoBlob, config.videoFileName)
    formData.append('model', config.model)
    formData.append('conf', '0.25')
    formData.append('iou', '0.45')
    formData.append('interval', '15')
    formData.append('start_time', config.startTime)

    const response = await fetch(buildRealtimeDetectionApiUrl('api/detect/video', getRealtimeDetectionBaseUrl()), {
      method: 'POST',
      body: formData
    })
    if (!response.ok) throw new Error(`detection HTTP ${response.status}`)

    const payload = await response.json()
    if (requestId !== cameraVideoDetectionRequestId) return
    if (!payload.success) throw new Error(payload.error || '检测失败')

    const frames = Array.isArray(payload.frames) ? payload.frames : []
    const videoWidth = Number(payload.video_width) || Number(cameraStreamVideoRef.value?.videoWidth) || 1
    const videoHeight = Number(payload.video_height) || Number(cameraStreamVideoRef.value?.videoHeight) || 1
    cameraStreamPopup.videoWidth = videoWidth
    cameraStreamPopup.videoHeight = videoHeight
    cameraStreamPopup.videoFrames = frames.map((frame) => (
      normalizeCameraVideoFrame(frame, videoWidth, videoHeight)
    ))
    syncCameraVideoBoxes()
    const { detectionCount, bestDetection } = summarizeVideoDetections(frames)
    cameraStreamPopup.detectionState = 'done'
    cameraStreamPopup.detectionStatus = '完成'
    cameraStreamPopup.sampledFrames = payload.sampled_frames || frames.length
    cameraStreamPopup.detectionCount = detectionCount
    cameraStreamPopup.bestLabel = bestDetection?.class || ''
    cameraStreamPopup.bestConfidence = bestDetection ? formatDetectionConfidence(bestDetection.confidence) : '--'
    cameraStreamPopup.detectionMessage = detectionCount ? '检测完成' : '检测完成，未发现目标'
  } catch (error) {
    if (requestId !== cameraVideoDetectionRequestId) return
    cameraStreamPopup.detectionState = 'error'
    cameraStreamPopup.detectionStatus = '失败'
    cameraStreamPopup.detectionMessage = `视频检测失败，请确认实时检测后端已启动且 ${config.model} 可用。`
  }
}

async function runLight1VideoDetection() {
  await runCameraVideoDetection('light1')
}

function openCameraStream(lightId = 'light1', movement) {
  const config = CAMERA_STREAM_CONFIGS[lightId] || CAMERA_STREAM_CONFIGS.light1
  cameraStreamPopup.title = config.title
  cameraStreamPopup.location = config.location
  cameraStreamPopup.videoSrc = config.videoSrc
  cameraStreamPopup.modelName = config.model

  const canvas = viewer?.scene?.canvas
  const width = canvas?.clientWidth || window.innerWidth || 1200
  const height = canvas?.clientHeight || window.innerHeight || 720
  const clickX = Number(movement?.position?.x) || width * 0.62

  const popupWidth = 480
  // 偏左上方排布定位（Y 固定置于顶部 80px 安全区域），确保完全避开中央 3D 事故主体与底部时间线
  cameraStreamPopup.x = Math.max(24, Math.min(clickX - popupWidth - 40, width - popupWidth - 360))
  cameraStreamPopup.y = 80
  cameraStreamPopup.show = true
  runCameraVideoDetection(lightId)
}

function openLight1CameraStream(movement) {
  openCameraStream('light1', movement)
}

const currentStoryDetectionScenario = computed(() => {
  return STORY_DETECTION_SCENARIOS[detectionPopup.scenarioKey] || null
})

function updateStoryDetectionPopupPosition() {
  const canvas = viewer?.scene?.canvas
  const width = canvas?.clientWidth || window.innerWidth || 1200
  const wrapper = canvas?.closest('.home-dashboard')
  const sidebarWidth = wrapper ? parseFloat(getComputedStyle(wrapper).getPropertyValue('--layout-right-reserve')) : 440
  // CSS 负责侧栏避让；保留坐标供其他调用兼容。
  detectionPopup.x = Math.max(20, width - (Number.isFinite(sidebarWidth) ? sidebarWidth : 440) - 500)
  detectionPopup.y = 210
}

function isTruckStoryline() {
  return props.phases?.[0]?.id?.startsWith('t-')
}

function getStoryDetectionScenario(index) {
  const isTruck = isTruckStoryline();
  const phase = props.phases?.[Number(index)];
  const phaseId = phase?.id || '';

  if (isTruck) {
    if (phaseId === 't-accident' || Number(index) === STORY_DETECTION_SCENARIOS.accident.phaseIndex) {
      return STORY_DETECTION_SCENARIOS.accident;
    }
    if (phaseId === 't-fire' || Number(index) === STORY_DETECTION_SCENARIOS.fire.phaseIndex) {
      return STORY_DETECTION_SCENARIOS.fire;
    }
  } else {
    // 油罐车场景
    if (phaseId === 'l-accident' || Number(index) === STORY_DETECTION_SCENARIOS.tankerAccident.phaseIndex) {
      return STORY_DETECTION_SCENARIOS.tankerAccident;
    }
    if (phaseId === 'l-leak' || Number(index) === STORY_DETECTION_SCENARIOS.tankerLeak.phaseIndex) {
      return STORY_DETECTION_SCENARIOS.tankerLeak;
    }
    if (phaseId === 'l-fill' || Number(index) === STORY_DETECTION_SCENARIOS.tankerFill.phaseIndex) {
      return STORY_DETECTION_SCENARIOS.tankerFill;
    }
  }
  return null;
}

function formatDetectionConfidence(value) {
  if (value === null || value === undefined || value === '') return '--'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '--'
  return `${(numeric * 100).toFixed(1)}%`
}

function getStoryDetectionClassZh(className) {
  if (!className) return ''
  const key = String(className).trim().toLowerCase().replace(/[-\s]+/g, '_').replace(/_/g, '')
  const labels = {
    lkywfire: '两客一危车辆碰撞起火',
    lkyw_fire: '两客一危车辆碰撞起火',
    lkywFire: '两客一危车辆碰撞起火',
    lkywnofire: '两客一危车辆碰撞无火',
    lkyw_nofire: '两客一危车辆碰撞无火',
    lkywNofire: '两客一危车辆碰撞无火',
    lkywnormal: '两客一危车辆碰撞无火',
    lkyw_normal: '两客一危车辆碰撞无火',
    lkywNormal: '两客一危车辆碰撞无火',
    carfire: '小汽车碰撞起火',
    car_fire: '小汽车碰撞起火',
    carFire: '小汽车碰撞起火',
    carnofire: '小汽车碰撞无火',
    car_nofire: '小汽车碰撞无火',
    carNofire: '小汽车碰撞无火',
    carnormal: '小汽车碰撞无火',
    car_normal: '小汽车碰撞无火',
    carNormal: '小汽车碰撞无火',
    leak: '危化品泄露',
    hazmat_leak: '危化品泄露',
    tank_leak: '危化品泄露',
    accident: '危化品泄露',
    noleak: '未发现危化品泄露',
    no_leak: '未发现危化品泄露',
    tank_normal: '未发现危化品泄露',
    normal: '未发现危化品泄露'
  }
  return labels[key] || labels[String(className).trim().toLowerCase()] || ''
}

function getStoryDetectionClassLabel(className) {
  return className || '检测目标'
}

function normalizeStoryDetectionBoxes(detections, scenario) {
  if (!Array.isArray(detections) || detections.length === 0) return []

  const imageWidth = scenario.imageWidth || 1456
  const imageHeight = scenario.imageHeight || 1024

  return detections.map((item) => {
    const bbox = Array.isArray(item.bbox) ? item.bbox : []
    const [x1, y1, x2, y2] = bbox.map(Number)
    if (![x1, y1, x2, y2].every(Number.isFinite)) return null

    return {
      x: Math.max(0, Math.min(100, (x1 / imageWidth) * 100)),
      y: Math.max(0, Math.min(100, (y1 / imageHeight) * 100)),
      width: Math.max(2, Math.min(100, ((x2 - x1) / imageWidth) * 100)),
      height: Math.max(2, Math.min(100, ((y2 - y1) / imageHeight) * 100)),
      label: item.class || '检测目标',
      kind: scenario.level === 'critical' ? 'fire' : 'warning'
    }
  }).filter(Boolean)
}

function normalizeStoryDetectedItems(detections) {
  if (!Array.isArray(detections)) return []
  return detections.map((item) => {
    const rawClass = item.class || item.label || '目标'
    const zh = getStoryDetectionClassZh(rawClass)
    return {
      rawLabel: rawClass,
      zh: zh,
      label: rawClass,
      confidence: formatDetectionConfidence(item.confidence)
    }
  })
}

function clearDetectionTimer() {
  if (detectionTimer) {
    clearInterval(detectionTimer)
    detectionTimer = null
  }
}

async function runStoryDetection(scenario) {
  if (!scenario) return

  const requestId = ++storyDetectionRequestId
  clearDetectionTimer()
  detectionPopup.state = 'detecting'
  detectionPopup.progress = 0
  detectionPopup.confidence = null
  detectionPopup.modelClass = ''
  detectionPopup.boxes = []
  detectionPopup.detectedItems = []
  detectionPopup.error = ''

  detectionTimer = setInterval(() => {
    detectionPopup.progress = Math.min(92, detectionPopup.progress + 8)
  }, 120)

  try {
    const imageResponse = await fetch(scenario.imageSrc, { cache: 'no-store' })
    if (!imageResponse.ok) throw new Error(`image HTTP ${imageResponse.status}`)

    const imageBlob = await imageResponse.blob()
    const formData = new FormData()
    formData.append('file', imageBlob, scenario.fileName)
    formData.append('model', scenario.model || 'SFGA-YOLO26M')
    formData.append('conf', '0.25')
    formData.append('iou', '0.45')

    const response = await fetch(buildRealtimeDetectionApiUrl('api/detect/image', getRealtimeDetectionBaseUrl()), {
      method: 'POST',
      body: formData
    })
    if (!response.ok) throw new Error(`detection HTTP ${response.status}`)

    const payload = await response.json()
    if (requestId !== storyDetectionRequestId) return
    if (payload.success === false) throw new Error(payload.error || '检测失败')

    const detections = Array.isArray(payload.detections) ? payload.detections : []
    const bestDetection = detections.reduce((best, item) => {
      const confidence = Number(item.confidence)
      if (!Number.isFinite(confidence)) return best
      if (!best || confidence > Number(best.confidence)) return item
      return best
    }, null)
    detectionPopup.confidence = bestDetection ? Number(bestDetection.confidence) : null
    detectionPopup.modelClass = bestDetection ? (bestDetection.class || bestDetection.label || '') : ''
    detectionPopup.modelClassZh = bestDetection ? getStoryDetectionClassZh(bestDetection.class) : ''
    detectionPopup.detectedItems = normalizeStoryDetectedItems(detections)
    detectionPopup.boxes = normalizeStoryDetectionBoxes(detections, scenario)
    if (!detections.length) {
      detectionPopup.error = '后端检测完成，当前图像未返回目标。'
    } else if (!detectionPopup.boxes.length) {
      detectionPopup.error = '后端检测完成，但返回结果不包含可绘制的 bbox。'
    }
  } catch (error) {
    if (requestId !== storyDetectionRequestId) return
    detectionPopup.confidence = null
    detectionPopup.modelClass = ''
    detectionPopup.modelClassZh = ''
    detectionPopup.detectedItems = []
    detectionPopup.boxes = []
    detectionPopup.error = `检测失败：${error instanceof Error ? error.message : String(error)}`
  } finally {
    if (requestId === storyDetectionRequestId) {
      clearDetectionTimer()
      detectionPopup.progress = 100
      detectionPopup.state = 'detected'
    }
  }
}

function activateStoryDetectionPopup(index) {
  const scenario = getStoryDetectionScenario(index)
  if (!scenario) {
    detectionPopup.show = false
    detectionPopup.scenarioKey = ''
    clearDetectionTimer()
    return
  }

  detectionPopup.show = true
  updateStoryDetectionPopupPosition()
  if (detectionPopup.scenarioKey !== scenario.key || detectionPopup.state !== 'detected') {
    detectionPopup.scenarioKey = scenario.key
    runStoryDetection(scenario)
  }
}

function rerunStoryDetection() {
  const scenario = currentStoryDetectionScenario.value
  if (scenario) runStoryDetection(scenario)
}

// 仿真推演悬浮窗状态
const simulationPopup = reactive({
  show: false,
  x: 0,
  y: 0,
  xOffset: -580,
  yOffset: -90
})

function enterSimulation() {
  const isTanker = props.focusedPointId === 'accident_red' || currentScene.value === 'tanker';
  const city = isTanker ? 'huanggang' : 'xiantao';
  const scene = isTanker ? 'leakage' : 'rear-end';
  router.push(`/simulation?city=${city}&scene=${scene}`);
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
let currentLoadMissionId = 0;
const missionDataSourceCache = new Map(); // 缓存加载过的 CZML 数据源，避免重复请求和卡顿

// 多智能体 CZML 会在离开救援阶段时被隐藏。再次进入时，不能只复用数据源，
// 还必须显式恢复五类救援路线和站点的绘制状态。
function syncMultiAgentRouteVisibility(dataSource, visible) {
<<<<<<< HEAD
=======
  hideTankerSiteLabel(dataSource)
>>>>>>> lkywSystem/develop
  if (!dataSource || !dataSource.entities) return

  dataSource.entities.values.forEach(entity => {
    const id = String(entity.id || '')
    if (id.startsWith('AgentPath_')) {
      entity.show = visible
<<<<<<< HEAD
      if (entity.polyline) entity.polyline.show = visible
=======
      if (entity.polyline) {
        entity.polyline.show = visible
        // 路线贴合地图表面，避免固定海拔落入地面或被表面遮挡。
        entity.polyline.clampToGround = true
        entity.polyline.width = 5
        entity.polyline.zIndex = 20
      }
>>>>>>> lkywSystem/develop
    } else if (id.startsWith('Agent_') || id.startsWith('AgentPOI_')) {
      entity.show = visible
    } else if (id.startsWith('AgentCP_') || id === 'StartMarker') {
      // 中间集散点和重复起点不参与主路线展示，避免遮挡五类规划线。
      entity.show = false
    }
  })
}

<<<<<<< HEAD
function syncAutonomousRouteTelemetry(dataSource, hidden) {
  if (!dataSource || !dataSource.entities) return
  dataSource.entities.values.forEach(entity => {
    const id = String(entity.id || '')
    if (id.startsWith('CarCP_') || id.startsWith('UAVCP_') || id === 'CarInfo' || id === 'UAVInfo') {
      entity.show = !hidden
=======
function hideTankerSiteLabel(dataSource) {
  const marker = dataSource?.entities?.getById('EndMarker')
  const text = marker?.label?.text?.getValue(viewer?.clock.currentTime)
  if (typeof text === 'string' && text.includes('油罐车')) marker.label.show = false
}
function syncAutonomousRouteTelemetry(dataSource, hidden) {
  hideTankerSiteLabel(dataSource)
  if (!dataSource || !dataSource.entities) return
  // 航线端点标注随数据源一起缓存，位置始终取自实际规划航线。
  const route = dataSource.entities.getById('UAV_Path')
  if (route?.polyline) {
    for (const [id, text, first] of [
      ['uav_dispatch_fire_station', '消防站', true],
      ['uav_dispatch_accident', '事故点', false]
    ]) {
      if (dataSource.entities.getById(id)) continue
      dataSource.entities.add({
        id,
        show: true,
        position: new Cesium.CallbackProperty(time => {
          const points = route.polyline.positions?.getValue(time)
          return points?.length ? points[first ? 0 : points.length - 1] : undefined
        }, false),
        label: {
          show: new Cesium.CallbackProperty(() => [3, 7].includes(Number(props.activePhaseIndex)), false),
          text,
          font: 'bold 18px sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          showBackground: false,
          backgroundColor: Cesium.Color.fromCssColorString('#062b3ddd'),
          pixelOffset: new Cesium.Cartesian2(0, -28),
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        }
      })
    }
  }
  dataSource.entities.values.forEach(entity => {
    const id = String(entity.id || '')
    const phase = Number(props.activePhaseIndex)
    if (id.startsWith('CarCP_') || id === 'CarInfo') {
      entity.show = phase >= 7 && phase < 11
    } else if (id.startsWith('UAVCP_') || id === 'UAVInfo') {
      entity.show = !hidden && phase >= 3 && phase < 11
>>>>>>> lkywSystem/develop
    }
  })
}

<<<<<<< HEAD
=======
// 提前准备救援路线；同一现场的并发调用共用一次请求。
const rescuePreparation = new Map()
function prepareRescueRoutes(endpoint) {
  if (rescuePreparation.has(endpoint)) return rescuePreparation.get(endpoint)
  const pending = (async () => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 180000)
    try {
      const response = await fetch(`${getCollaborativeCommandCenterBaseUrl()}/api/run_multi_agent?end_point=${endpoint}`, { signal: controller.signal })
      if (!response.ok) throw new Error('救援路线准备失败，请重新进入该阶段重试')
      return response
    } finally { clearTimeout(timer) }
  })()
  rescuePreparation.set(endpoint, pending)
  pending.catch(() => rescuePreparation.delete(endpoint))
  return pending
}
>>>>>>> lkywSystem/develop
const loadMission = async (isMultiAgent = false) => {
  if (!viewer) return;
  const loadId = ++currentLoadMissionId;
  const endpoint = currentScene.value === 'truck' ? 'crash' : 'leak';
  const cacheKey = `${endpoint}_${isMultiAgent ? 'multi' : 'single'}`;

  // 1. 如果当前已经挂载了匹配的数据源，直接更新可见性，0ms 响应
  if (
    currentMissionDataSource &&
    currentMissionDataSource._lastEndpoint === endpoint &&
    !!currentMissionDataSource._isMultiAgent === isMultiAgent
  ) {
    if (isMultiAgent) {
      syncMultiAgentRouteVisibility(currentMissionDataSource, Number(props.activePhaseIndex) >= 11)
    } else {
      syncAutonomousRouteTelemetry(currentMissionDataSource, endpoint === 'crash' && Number(props.activePhaseIndex) === 3)
    }
    return;
  }

  // 2. 如果内存缓存中有，直接取缓存挂载，0ms 切换
  if (missionDataSourceCache.has(cacheKey)) {
    const cachedDS = missionDataSourceCache.get(cacheKey);
    if (currentMissionDataSource && currentMissionDataSource !== cachedDS) {
      try {
        viewer.dataSources.remove(currentMissionDataSource, false);
      } catch (e) {}
    }
    if (!viewer.dataSources.contains(cachedDS)) {
      viewer.dataSources.add(cachedDS);
    }
    currentMissionDataSource = cachedDS;
    if (isMultiAgent) {
      cachedDS.entities.values.forEach(entity => { entity.availability = undefined })
      syncMultiAgentRouteVisibility(cachedDS, Number(props.activePhaseIndex) >= 11)
    } else {
      syncAutonomousRouteTelemetry(cachedDS, endpoint === 'crash' && Number(props.activePhaseIndex) === 3)
    }
    return;
  }

  try {
    const baseUrl = getCollaborativeCommandCenterBaseUrl();
    
    // 如果是加载多智能体（5类救援路线），立刻隐藏原有的无人机/无人车路线，防止后台计算期间页面显示错误的旧路线
    if (isMultiAgent && currentMissionDataSource) {
      ['UAV_Path', 'Car_Path', 'UAV_Path_glow', 'Car_Path_glow'].forEach(id => {
        const entity = currentMissionDataSource.entities.getById(id);
        if (entity) {
          entity.show = false;
        }
      });
    }

    // 触发后端生成正确的 CZML（单机路线 vs 多智能体救援路线），等待后端把正确版本写入 mission.czml
    try {
      const apiPath = isMultiAgent ? 'api/run_multi_agent' : 'api/run_3d_strategy';
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), isMultiAgent ? 180000 : 8000); // 首次五类路网规划需要更长时间
      const resp = isMultiAgent ? await prepareRescueRoutes(endpoint) : await fetch(`${baseUrl}/${apiPath}?end_point=${endpoint}`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (isMultiAgent && !resp.ok) throw new Error('五类救援路线规划失败，请检查后端服务');
      if (resp.ok) {
        console.log(`[Cesium] 后端 ${apiPath} 调用成功, endpoint=${endpoint}`);
      }
    } catch (e) {
      if (isMultiAgent) throw e;
      console.warn('[Cesium] 触发策略生成已跳过或超时，尝试直接加载已有 CZML:', e);
    }
    
    if (loadId !== currentLoadMissionId) return;
    if (props.activePhaseIndex < 3) return;
    
    // 加载最新的 czml（带时间戳防缓存）
    const czmlUrl = `${baseUrl}/mission.czml?t=${Date.now()}&ep=${endpoint}&multi=${isMultiAgent ? 1 : 0}`;
    const dataSource = await Cesium.CzmlDataSource.load(czmlUrl);
    
    if (loadId !== currentLoadMissionId) return;
    if (props.activePhaseIndex < 3) return;

    // 验证加载的 CZML 是否匹配请求类型：单机路线必须包含 UAV_Path，多智能体必须包含 AgentPath_*
    const hasUavPath = !!dataSource.entities.getById('UAV_Path');
    const hasAgentPath = dataSource.entities.values.some(e => e.id && e.id.startsWith('AgentPath_'));
    
    if (isMultiAgent && !hasAgentPath) {
      throw new Error('未获取到五类救援路线，已停止使用旧的无人机路线，请重新进入该阶段重试');
    }

    if (!isMultiAgent && !hasUavPath && hasAgentPath) {
      // 加载到了多智能体 CZML（mission.czml 被覆盖），强制刷新重新生成单机路线
      console.warn('[Cesium] 检测到 mission.czml 是多智能体版本，强制重新生成单机无人机路线...');
      try {
        const controller2 = new AbortController();
        const timeoutId2 = setTimeout(() => controller2.abort(), 8000);
        await fetch(`${baseUrl}/api/run_3d_strategy?end_point=${endpoint}&refresh=1`, { signal: controller2.signal });
        clearTimeout(timeoutId2);
        // 重新加载
        const czmlUrl2 = `${baseUrl}/mission.czml?t=${Date.now()}&force=1`;
        const ds2 = await Cesium.CzmlDataSource.load(czmlUrl2);
        if (loadId === currentLoadMissionId && ds2.entities.getById('UAV_Path')) {
          // 使用正确的数据源
          Object.assign(dataSource, {}); // discard
          if (currentMissionDataSource) {
            viewer.dataSources.remove(currentMissionDataSource, false);
          }
          ds2._lastEndpoint = endpoint;
          ds2._isMultiAgent = isMultiAgent;
          ds2.entities.values.forEach(entity => { entity.availability = undefined; });
          currentMissionDataSource = ds2;
          missionDataSourceCache.set(cacheKey, ds2);
          viewer.dataSources.add(ds2);
          console.log('[Cesium] 单机无人机路线已成功重新加载，UAV_Path 已就绪');
          return;
        }
      } catch (e) {
        console.warn('[Cesium] 强制刷新单机路线失败:', e);
      }
    }

    if (currentMissionDataSource) {
      viewer.dataSources.remove(currentMissionDataSource, false);
    }
    
    dataSource._lastEndpoint = endpoint;
    dataSource._isMultiAgent = isMultiAgent;
    
    // 清除 CZML 实体的时间范围可用性限制，防止时间走完或越界时实体在地图上消失
    dataSource.entities.values.forEach(entity => {
      entity.availability = undefined;
    });

    currentMissionDataSource = dataSource;
    missionDataSourceCache.set(cacheKey, dataSource);

    const phaseIdx = Number(props.activePhaseIndex);
    // 第 12 阶段是“救援装备出动”：此时只显示多智能体救援路线，不能复用无人装备阶段的路径。
    const showAutonomousUavRoute = phaseIdx >= 3 && phaseIdx < 11 && !isMultiAgent;
    const showAutonomousUgvRoute = phaseIdx >= 7 && phaseIdx < 11 && !isMultiAgent;
    // 客车追尾的“无人机出动”仅展示航线与真实无人机模型；隐藏 CZML 附带的
    // 红/蓝动态点、进度检查点和信息标签，避免它们被误认为额外目标。
    const hideTruckUavDispatchTelemetry = endpoint === 'crash' && phaseIdx === 3;

    // 让 CZML 的 UAV 和 Car 实体位置与自定义 3D 模型位置完全对齐，避免分叉
    const czmlCar = dataSource.entities.getById('Car');
    if (czmlCar) {
      czmlCar.show = showAutonomousUgvRoute;
      czmlCar.path = undefined; // 必须将 path 设为 undefined，否则 CallbackProperty 导致 Cesium PathVisualizer 在更新轨迹线时崩溃
      if (!czmlCar.originalPosition) {
        czmlCar.originalPosition = czmlCar.position;
      }
      czmlCar.position = new Cesium.CallbackProperty(() => {
        const isTanker = props.focusedPointId === 'accident_red';
        const callback = isTanker ? sharedTankerRescueCarPosition : sharedTruckRescueCarPosition;
        if (callback) {
          return callback.getValue(viewer.clock.currentTime);
        }
        return czmlCar.originalPosition ? czmlCar.originalPosition.getValue(getQueryTime()) : null;
      }, false);
    }
    
    const czmlUav = dataSource.entities.getById('UAV');
    if (czmlUav) {
      // 保留主无人机的红色大位置点；仅隐藏路径上的小型进度检查点。
      czmlUav.show = showAutonomousUavRoute;
      if (czmlUav.model) {
        czmlUav.model.runAnimations = true;
      }
      czmlUav.path = undefined; // 必须将 path 设为 undefined，否则 CallbackProperty 导致 Cesium PathVisualizer 在更新轨迹线时崩溃
      if (!czmlUav.originalPosition) {
        czmlUav.originalPosition = czmlUav.position;
      }
      czmlUav.position = new Cesium.CallbackProperty(() => {
        const isTanker = props.focusedPointId === 'accident_red';
        const callback = isTanker ? sharedTankerUavPosition : sharedTruckUavPosition;
        if (callback) {
          return callback.getValue(viewer.clock.currentTime);
        }
        return czmlUav.originalPosition ? czmlUav.originalPosition.getValue(getQueryTime()) : null;
      }, false);
    }

    // 确保从 CZML 加载的规划路线实体在地图上根据阶段可见
    const uavPath = dataSource.entities.getById('UAV_Path');
    if (uavPath) {
      uavPath.show = showAutonomousUavRoute;
      if (uavPath.polyline) uavPath.polyline.show = showAutonomousUavRoute;
    }
    const uavPathGlow = dataSource.entities.getById('UAV_Path_glow');
    if (uavPathGlow) {
      uavPathGlow.show = showAutonomousUavRoute;
      if (uavPathGlow.polyline) uavPathGlow.polyline.show = showAutonomousUavRoute;
    }
    const carPath = dataSource.entities.getById('Car_Path');
    if (carPath) {
      carPath.show = showAutonomousUgvRoute;
      if (carPath.polyline) {
        carPath.polyline.show = showAutonomousUgvRoute;
      }
    }
    const carPathGlow = dataSource.entities.getById('Car_Path_glow');
    if (carPathGlow) {
      carPathGlow.show = showAutonomousUgvRoute;
      if (carPathGlow.polyline) {
        carPathGlow.polyline.show = showAutonomousUgvRoute;
      }
    }

    syncAutonomousRouteTelemetry(dataSource, hideTruckUavDispatchTelemetry)

    viewer.dataSources.add(dataSource);

    // 首次加载与缓存复用保持一致：路线实体和折线都立即可见，
    // 不依赖后续阶段更新的异步时机。
    if (isMultiAgent) {
      syncMultiAgentRouteVisibility(dataSource, phaseIdx >= 11)
    }

    // 同步时间轴
    if (dataSource.clock) {
      viewer.clock.startTime = dataSource.clock.startTime;
      viewer.clock.stopTime = dataSource.clock.stopTime;
      
      if (phaseIdx === 7) {
        viewer.clock.currentTime = dataSource.clock.startTime;
        viewer.clock.multiplier = 190.0;
        viewer.clock.shouldAnimate = true;
      } else if (isMultiAgent) {
        viewer.clock.currentTime = dataSource.clock.startTime;
        viewer.clock.shouldAnimate = true;
        viewer.clock.multiplier = agentSpeedConfig.multiAgentMultiplier;
        viewer.clock.clockRange = Cesium.ClockRange.UNBOUNDED;
      } else if (phaseIdx >= 7) {
        viewer.clock.currentTime = dataSource.clock.stopTime;
        viewer.clock.shouldAnimate = true;
        viewer.clock.multiplier = 1.0;
        viewer.clock.clockRange = Cesium.ClockRange.UNBOUNDED;
      } else {
        viewer.clock.currentTime = dataSource.clock.currentTime;
        viewer.clock.clockRange = dataSource.clock.clockRange;
      }
    }
    if (carPath && carPath.polyline) {
        const positions = carPath.polyline.positions.getValue(getQueryTime()) ||
                          carPath.polyline.positions.getValue(new Cesium.JulianDate());
        if (positions && positions.length >= 2) {
          const last200mPoints = [];
          let accumDist = 0;
          const targetDist = 200.0;
          
          last200mPoints.unshift(positions[positions.length - 1]);
          
          for (let i = positions.length - 1; i > 0; i--) {
            const pCurrent = positions[i];
            const pPrev = positions[i - 1];
            const dist = Cesium.Cartesian3.distance(pCurrent, pPrev);
            
            if (accumDist + dist >= targetDist) {
              const remaining = targetDist - accumDist;
              const fraction = dist > 0 ? (remaining / dist) : 0;
              const lerpedCartesian = new Cesium.Cartesian3();
              Cesium.Cartesian3.lerp(pCurrent, pPrev, fraction, lerpedCartesian);
              last200mPoints.unshift(lerpedCartesian);
              break;
            } else {
              accumDist += dist;
              last200mPoints.unshift(pPrev);
            }
          }
          updateHighlightPath(last200mPoints);
        }
      }
    // 仅在第 7 阶段（无人装备出动）或第 12 阶段（救援装备多智能体）设置高速巡航，其他阶段（包括正常行驶/事故阶段）必须严格保持 1.0x 原速！
    if (phaseIdx === 7) {
      viewer.clock.multiplier = 190.0;
    } else if (isMultiAgent || phaseIdx === 11) {
      viewer.clock.multiplier = Number(agentSpeedConfig.multiAgentMultiplier) || 20;
    } else {
      viewer.clock.multiplier = 1.0;
    }
    viewer.clock.shouldAnimate = true;
    
    // 加载完成后强制刷新实体显隐状态，使 5 类救援装备和路径线能立刻展示
    if (typeof updatePhaseScene === 'function') {
      updatePhaseScene(phaseIdx, false);
    }
    
    // 更新救援装备出动面板的状态反馈
    if (isMultiAgent) {
      rescueDispatchStatus.value = '✅ 救援装备已出动';
      rescueDispatchPending.value = false;
      setTimeout(() => { rescueDispatchStatus.value = '' }, 4000);
    }
  } catch (error) {
    console.error('加载三维轨迹 CZML 失败:', error);
    if (isMultiAgent) {
      rescueDispatchStatus.value = '❌ 失败: ' + (error instanceof Error ? error.message : String(error));
      rescueDispatchPending.value = false;
      setTimeout(() => { rescueDispatchStatus.value = '' }, 4000);
    }
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
  if (!viewer || isOverviewTransition) return;
  
  // 节流：每 20 帧检查一次，不需要每帧都进行昂贵的递归搜索
  readyCheckFrameCounter++;
  if (readyCheckFrameCounter % 20 !== 0) return;

  let changed = false;
  const allEntities = [...truckEntities, ...tankerEntities, ...uavEntities, ...tankerUavEntities];
  
  allEntities.forEach(entity => {
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
        if (!modelsReadyStatus[entity.id]) {
          modelsReadyStatus[entity.id] = true;
          changed = true;
          console.log(`[Cesium] 检测到模型就绪: ${entity.id}`);
          if (entity.id === 'model_normal' && props.activePhaseIndex === 1 && currentScene.value === 'truck') {
            playEntityAnimation(entity, false, 0, 1.0);
          } else if (entity.id === 'tanker_normal' && props.activePhaseIndex === 1 && currentScene.value === 'tanker') {
            playEntityAnimation(entity, false, 0, 1.0);
          } else if (entity.id === 'model_accident' && props.activePhaseIndex >= 3 && currentScene.value === 'truck') {
            freezeEntityAtEnd(entity);
          } else if (entity.id === 'tanker_accident' && props.activePhaseIndex >= 3 && currentScene.value === 'tanker') {
            freezeEntityAtEnd(entity);
          }
        }

        // 核心修复逻辑：如果是无人机，且可见，则强制要求以高速持续旋转
        if (entity.id.includes('uav_model') && entity.show) {
          const hasNoAnimations = !p.activeAnimations || p.activeAnimations.length === 0;
          if (!p._customAnimStarted || hasNoAnimations) {
            console.log(`[Cesium] 正在强制接管无人机螺旋桨动画: ${entity.id}`);
            try {
              if (p.activeAnimations) {
                p.activeAnimations.removeAll();
                const options = {
                  loop: Cesium.ModelAnimationLoop.REPEAT,
                  multiplier: 150.0,
                  startTime: viewer.clock.currentTime,
                  removeOnStop: false
                };
                p.activeAnimations.addAll(options);
              }
              p._customAnimStarted = true;
            } catch (animErr) {
              console.warn(`[Cesium] 激活无人机螺旋桨动画失败: ${entity.id}`, animErr);
            }
          }
        }
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
  accident_blue: { id: 'accident_blue', label: '客车追尾现场', longitude: 113.104833, latitude: 30.385469, color: '#ffea00' }, // 改为黄色
  // 两个事故现场使用一致的黄色告警语义，地图点位与波纹会自动继承该颜色。
  accident_red: { id: 'accident_red', label: '油罐车泄露现场', longitude: 114.894472, latitude: 30.632203, color: '#ffea00' },
}

// 省域总览取景点：镜头中心略向南取，使湖北主体在屏幕内整体上移，
// 为底部操控条留出清晰空间。
// 首页迎宾视角拉近至省域占据画面主体，综合态势继续使用独立的总览距离。
const LANDING_VIEW_RANGE = 860000
const LANDING_VIEW_PITCH = -25

const DEFAULT_OVERVIEW = {
  longitude: 112.5,
  latitude: 30.7,
  range: 1450000
}

function toCesiumColor(color, alpha = 1) {
  return Cesium.Color.fromCssColorString(color).withAlpha(alpha)
}

/**
 * 将二维行政边界转换为带网格顶面、立体侧壁和脉冲轮廓的电子围栏。
 * 只使用 Cesium Entity / MaterialProperty，完全不依赖后端渲染服务。
 */
function addElectronicFence(coords, fenceId = 'default') {
  if (!viewer || !Array.isArray(coords) || coords.length < 3) return

  // GeoJSON 通常已闭合；这里统一补齐闭合点，保证 wall 与各层轮廓连续。
  const ring = coords.map(([lng, lat]) => [Number(lng), Number(lat)])
  const first = ring[0]
  const last = ring[ring.length - 1]
  if (first[0] !== last[0] || first[1] !== last[1]) ring.push([...first])

  const flatDegrees = ring.flat()
  // 参考效果的重点是“悬浮地图块”，而非贴地围栏；湖北尺度下需要足够的高度
  // 才能在倾斜总览相机中清楚看见规则侧壁。
  const roofHeight = ELECTRONIC_FENCE_ROOF_HEIGHT
  const makeHeightPositions = (height) => Cesium.Cartesian3.fromDegreesArrayHeights(
    ring.flatMap(([lng, lat]) => [lng, lat, height])
  )
  const add = (entity) => {
    const created = viewer.entities.add({
      ...entity,
      show: true
    })
    electronicFenceEntities.push(created)
    return created
  }

  // 网格化顶面：半透明地表可保留遥感图纹理，网格提供数字孪生的电子感。
  add({
    id: `electronic-fence-${fenceId}-surface`,
    name: '电子围栏监测区域',
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(flatDegrees)),
      height: roofHeight,
      material: new Cesium.GridMaterialProperty({
        // 让卫星底图透出，网格只承担轮廓与数字化纹理，而不是覆盖整张底图。
        color: Cesium.Color.fromCssColorString('#00d9ff').withAlpha(0.25),
        cellAlpha: 0.07,
        lineCount: new Cesium.Cartesian2(72, 72),
        lineThickness: new Cesium.Cartesian2(0.9, 0.9)
      }),
      outline: false
    }
  })

  // 半透明侧壁让围栏从平面区域变成立体电子边界；材质中的扫描线
  // 沿墙体高度持续流动，复现参考效果的侧边流光。
  add({
    id: `electronic-fence-${fenceId}-wall`,
    wall: {
      positions: Cesium.Cartesian3.fromDegreesArray(flatDegrees),
      minimumHeights: ring.map(() => 0),
      maximumHeights: ring.map(() => roofHeight),
      material: new ElectronicFenceWallFlowMaterialProperty({
        color: Cesium.Color.fromCssColorString('#008cff').withAlpha(0.64),
        speed: 1.15,
        // 原先 8 条流光带在首页视角过于密集；调整为 3 条以突出动态方向。
        repeat: 3
      })
    }
  })

  // 仅勾勒顶面边界：取消底部多层高亮轮廓，避免湖北下方再出现一张发光地图。
  // 保留侧壁本身的轻微流光以体现悬浮层次。
  add({
    id: `electronic-fence-${fenceId}-flow`,
    polyline: {
      positions: makeHeightPositions(roofHeight + 16),
      width: 6.2,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.18,
        color: Cesium.Color.WHITE.withAlpha(0.92)
      }),
      clampToGround: false
    }
  })
}

function applyOrbitView(animate = false, ignoreSaved = false) {
  if (isOverviewTransition) return
  if (!viewer) return
  const savedCamera = savedStoryCameraViews[`${props.focusedPointId}:${props.activePhaseIndex}`];
  if (!ignoreSaved && props.focusedPointId && savedCamera && accidentViewLevel.value !== 'far') {
    stopAutoRotate();
    viewer.camera.cancelFlight();
    isFlying = false;
    viewer.trackedEntity = undefined;
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(savedCamera.longitude, savedCamera.latitude, savedCamera.height),
      orientation: { heading: Cesium.Math.toRadians(savedCamera.heading), pitch: Cesium.Math.toRadians(savedCamera.pitch), roll: Cesium.Math.toRadians(savedCamera.roll) }
    });
    viewer.scene.requestRender();
    return;
  }
  if (isFlying && !animate) {
    try {
      viewer.camera.cancelFlight();
    } catch (e) {}
    isFlying = false;
  }
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
    // 省域总览向北取景，将湖北主体下移，避免被顶部系统标题遮挡。
    lng = DEFAULT_OVERVIEW.longitude; lat = DEFAULT_OVERVIEW.latitude;
  }

  try {
    const target = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
    
    // 省域总览采用倾斜俯视，才能同时看到蓝色顶面和下方的分层侧墙。
    let range = props.landingView ? LANDING_VIEW_RANGE : DEFAULT_OVERVIEW.range
    let pitch = Cesium.Math.toRadians(props.landingView ? LANDING_VIEW_PITCH : -57)
    let finalHeading = 0

    if (isFocused) {
      if (accidentViewLevel.value === 'far') {
        range = 120000
        pitch = Cesium.Math.toRadians(-60)
        finalHeading = (props.focusedPointId === 'accident_red' ? tankerOrbitHeading : truckOrbitHeading)
      } else if (accidentViewLevel.value === 'close') {
        range = props.focusedPointId === 'accident_red' ? 100 : 75
        pitch = Cesium.Math.toRadians(-20)
        finalHeading = Cesium.Math.toRadians(8)
      } else {
        // 'medium' 现场视角或常规推演视角：统一使用当前推演阶段（如仿真开始）的相机配置，实现第三视角与推演视角100%同步
        const pIdx = (props.activePhaseIndex !== undefined && props.activePhaseIndex !== null) ? (props.activePhaseIndex + 1) : 1
        const scene = props.focusedPointId === 'accident_red' ? 'tanker' : 'truck'
        const cfg = (defaultPhaseCameraConfigs[scene] && defaultPhaseCameraConfigs[scene][pIdx]) || { range: 600, pitch: -11, heading: -39 }
        
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
        duration: 0.6,
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
      try {
        viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(finalHeading, pitch, range))
      } catch (e) {
        viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
        viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(finalHeading, pitch, range));
      }
    }
  } catch (error) {
    console.warn('应用轨道视角时出现警告:', error.message)
  }
}

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

// 创建更加逼真的浓烟升腾系统 (放大基础尺寸与扩散体积)
function createSmokeSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/smoke.png',
    startColor: new Cesium.Color(0.2, 0.2, 0.2, 0.65), // 初始浓密深灰
    endColor: new Cesium.Color(0.6, 0.6, 0.6, 0.0),   // 最终淡灰自然扩散完全透明
    startScale: 1.2, // 初始比例
    endScale: 9.5,   // 升空后大面积扩散覆盖
    minimumParticleLife: 3.5, // 延长寿命，形成连贯巨大的浓烟气柱
    maximumParticleLife: 6.8, 
    minimumSpeed: 1.5, 
    maximumSpeed: 3.8, 
    imageSize: new Cesium.Cartesian2(7.5, 7.5), // 加大至 7.5 米 3D 基础尺寸，增强宏观可见度
    emissionRate: 28.0, // 充足的发散密度，维持浓烟连贯质感
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(3.5), // 发射源扩展至 3.5 米球体
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 模拟受热热升力与平缓风向漂移 (局部法线向上归一化向量)
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 2.2 * dt, gravityScratch); 
      Cesium.Cartesian3.add(particle.velocity, gravityScratch, particle.velocity);
    }
  });
}

// 创建更加逼真的火焰/爆炸系统
function createFireSystem(lng, lat) {
  return new Cesium.ParticleSystem({
    image: '/Dashboard/images/explosion00.png',
    startColor: new Cesium.Color(1.0, 0.6, 0.2, 0.8), // 偏橘黄色的火焰，稍微透明一点防止刺眼
    endColor: new Cesium.Color(0.8, 0.1, 0.0, 0.0),   // 消失时的深红
    startScale: 1.5, // 与烟雾保持一致
    endScale: 12.0, // 与烟雾保持一致
    minimumParticleLife: 4.0, // 与烟雾保持一致
    maximumParticleLife: 8.0, // 与烟雾保持一致
    minimumSpeed: 1.0, // 与烟雾保持一致
    maximumSpeed: 2.5, // 与烟雾保持一致
    imageSize: new Cesium.Cartesian2(25, 25), // 与烟雾保持一致
    emissionRate: 25.0, // 与烟雾保持一致
    lifetime: 16.0,
    emitter: new Cesium.SphereEmitter(5.0), // 与烟雾保持一致
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lng, lat, 0.0)),
    sizeInMeters: true,
    show: false,
    updateCallback: (particle, dt) => {
      // 与烟雾保持一致
      const gravityScratch = new Cesium.Cartesian3();
      Cesium.Cartesian3.normalize(particle.position, gravityScratch);
      Cesium.Cartesian3.multiplyByScalar(gravityScratch, 1.5 * dt, gravityScratch); 
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
    startColor: new Cesium.Color(0.85, 0.9, 0.95, 0.35), // 白色半透明扩散示意，甲醇蒸气本身无色
    endColor: new Cesium.Color(0.95, 0.97, 1.0, 0.0),       // 渐变至完全透明
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

let lastPopupPositionUpdate = 0;
function updatePopupPosition() {
  if (!viewer) return;
  const now = performance.now();
  if (now - lastPopupPositionUpdate < 33) return;
  lastPopupPositionUpdate = now;

  // 绑定事故现场红点/蓝点坐标，确保无人机/无人车悬浮窗与红蓝事故点强绑定
  const targetPointId = currentScene.value === 'truck' ? 'accident_blue' : 'accident_red';
  const targetPoint = scenarioPoints[targetPointId];
  const defaultLng = targetPoint ? (targetPoint.longitude || targetPoint.lon) : (currentScene.value === 'truck' ? 113.104833 : 114.8945);
  const defaultLat = targetPoint ? (targetPoint.latitude || targetPoint.lat) : (currentScene.value === 'truck' ? 30.385469 : 30.632161);

  // 1. 无人机悬浮窗：优先跟随行驶的 3D 无人机，否则强绑定红蓝事故点
  if (rescuePopup.show) {
    let bound = false;
    if (Number(props.activePhaseIndex) === 7) {
      const isTanker = currentScene.value === 'tanker' || props.focusedPointId === 'accident_red';
      const uavIds = isTanker ? ['uav_model_move_tanker', 'uav_model_tanker'] : ['uav_model_move', 'uav_model'];
      for (const id of uavIds) {
        const uavEntity = viewer.entities.getById(id);
        if (uavEntity) {
          const pos = uavEntity.position.getValue(viewer.clock.currentTime);
          if (pos) {
            const cartographic = Cesium.Cartographic.fromCartesian(pos);
            rescueCoords.lng = Cesium.Math.toDegrees(cartographic.longitude);
            rescueCoords.lat = Cesium.Math.toDegrees(cartographic.latitude);
            rescueCoords.height = cartographic.height + 10.0;
            bound = true;
            break;
          }
        }
      }
    }
    if (!bound) {
      rescueCoords.lng = defaultLng;
      rescueCoords.lat = defaultLat;
      rescueCoords.height = 10.0;
    }

    const cartesian = Cesium.Cartesian3.fromDegrees(rescueCoords.lng, rescueCoords.lat, rescueCoords.height);
    const canvasPosition = viewer.scene.cartesianToCanvasCoordinates(cartesian);
    if (canvasPosition) {
      rescuePopup.x = canvasPosition.x + (rescuePopup.xOffset !== undefined ? rescuePopup.xOffset : (rescuePopup.title === '无人机已到达' ? 161 : -10));
      rescuePopup.y = canvasPosition.y + (rescuePopup.yOffset !== undefined ? rescuePopup.yOffset : (rescuePopup.title === '无人机已到达' ? -62 : 15));
    }
  }

  // 2. 无人车悬浮窗：优先跟随行驶的 3D 无人车，否则强绑定红蓝事故点
  if (ugvPopup.show) {
    let bound = false;
    if (Number(props.activePhaseIndex) === 7) {
      const isTanker = currentScene.value === 'tanker' || props.focusedPointId === 'accident_red';
      const carIds = isTanker ? ['tanker_rescue_car_model_1', 'tanker_rescue_car_model_2'] : ['rescue_car_model_1', 'rescue_car_model_2'];
      for (const id of carIds) {
        const carEntity = viewer.entities.getById(id);
        if (carEntity) {
          const pos = carEntity.position.getValue(viewer.clock.currentTime);
          if (pos) {
            const cartographic = Cesium.Cartographic.fromCartesian(pos);
            ugvCoords.lng = Cesium.Math.toDegrees(cartographic.longitude);
            ugvCoords.lat = Cesium.Math.toDegrees(cartographic.latitude);
            ugvCoords.height = cartographic.height + 10.0;
            bound = true;
            break;
          }
        }
      }
    }
    if (!bound) {
      ugvCoords.lng = defaultLng;
      ugvCoords.lat = defaultLat;
      ugvCoords.height = 10.0;
    }

    const cartesian = Cesium.Cartesian3.fromDegrees(ugvCoords.lng, ugvCoords.lat, ugvCoords.height);
    const canvasPosition = viewer.scene.cartesianToCanvasCoordinates(cartesian);
    if (canvasPosition) {
      const fallbackX = ugvPopup.title === '无人车已就位' ? (currentScene.value === 'tanker' ? -2 : -200) : -27;
      const fallbackY = ugvPopup.title === '无人车已就位' ? (currentScene.value === 'tanker' ? -175 : 143) : -133;
      ugvPopup.x = canvasPosition.x + (ugvPopup.xOffset !== undefined ? ugvPopup.xOffset : fallbackX);
      ugvPopup.y = canvasPosition.y + (ugvPopup.yOffset !== undefined ? ugvPopup.yOffset : fallbackY);
    }
  }

  if (detectionPopup.show && currentStoryDetectionScenario.value) {
    updateStoryDetectionPopupPosition();
  }

  // 更新仿真推演悬浮窗坐标 (当位于货车追尾现场或油罐车泄漏现场的“信号干扰”阶段 index === 10 时)
  if (simulationPopup.show && Number(props.activePhaseIndex) === 11 && (props.focusedPointId === 'accident_blue' || props.focusedPointId === 'accident_red')) {
    const isTruck = props.focusedPointId === 'accident_blue';
    const lng = isTruck ? (Number(truckAdjust.lng) || 113.104833) : (Number(tankerPointAdjust.lng) || 114.8945);
    const lat = isTruck ? (Number(truckAdjust.lat) || 30.385469) : (Number(tankerPointAdjust.lat) || 30.632161);
    const cartesian = Cesium.Cartesian3.fromDegrees(lng, lat, 20.0);
    const canvasPosition = viewer.scene.cartesianToCanvasCoordinates(cartesian);
    if (canvasPosition) {
      simulationPopup.x = canvasPosition.x + (simulationPopup.xOffset || 0);
      simulationPopup.y = canvasPosition.y + (simulationPopup.yOffset || 0);
    }
  }

  // 精细建模悬浮窗 (在货车追尾与油罐车泄漏两个场景的“无人感知执行”阶段 index === 9 显示)
  const pIdxSec = Number(props.activePhaseIndex);
  const showSecPopup = (pIdxSec === 9);

  if (showSecPopup) {
    secondaryDisasterVideoPopup.show = true;
    const pointId = currentScene.value === 'truck' ? 'accident_blue' : 'accident_red';
    const p = scenarioPoints[pointId];
    let posCalculated = false;
    if (p) {
      const lng = p.longitude || p.lon;
      const lat = p.latitude || p.lat;
      const c3 = Cesium.Cartesian3.fromDegrees(lng, lat, 10);
      const cp = viewer.scene.cartesianToCanvasCoordinates(c3);
        if (cp && cp.x > 0 && cp.y > 0) {
          const adjust = currentScene.value === 'truck' ? truckSecPopupAdjust : tankerSecPopupAdjust;
          secondaryDisasterVideoPopup.x = cp.x + adjust.xOffset;
          secondaryDisasterVideoPopup.y = cp.y + adjust.yOffset;
          posCalculated = true;
        }
    }
    if (!posCalculated) {
      const canvas = viewer?.scene?.canvas;
      const width = canvas?.clientWidth || window.innerWidth || 1200;
      secondaryDisasterVideoPopup.x = width * 0.55;
      secondaryDisasterVideoPopup.y = 180;
    }
  } else {
    secondaryDisasterVideoPopup.show = false;
  }



    // 更新无人机悬浮窗坐标 (绑定蓝色点或红色点，仅在到达现场后的阶段 >= 8 时显示为固定位置)
    if (props.activePhaseIndex >= 8 && rescuePopup.show) {
      const pointId = currentScene.value === 'truck' ? 'accident_blue' : 'accident_red';
      const p = scenarioPoints[pointId];
      if (p) {
        const c3 = Cesium.Cartesian3.fromDegrees((p.longitude || p.lon), (p.latitude || p.lat), 10);
        const cp = viewer.scene.cartesianToCanvasCoordinates(c3);
        if (cp) {
          rescuePopup.x = cp.x + rescuePopup.xOffset;
          rescuePopup.y = cp.y + rescuePopup.yOffset;
        }
      }
    }

    // 更新无人车悬浮窗坐标 (绑定蓝色点或红色点，仅在到达现场后的阶段 >= 8 时显示为固定位置)
    if (props.activePhaseIndex >= 8 && ugvPopup.show) {
      const pointId = currentScene.value === 'truck' ? 'accident_blue' : 'accident_red';
      const p = scenarioPoints[pointId];
      if (p) {
        const c3 = Cesium.Cartesian3.fromDegrees((p.longitude || p.lon), (p.latitude || p.lat), 10);
        const cp = viewer.scene.cartesianToCanvasCoordinates(c3);
        if (cp) {
          ugvPopup.x = cp.x + ugvPopup.xOffset;
          ugvPopup.y = cp.y + ugvPopup.yOffset;
        }
      }
    }

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

  // 更新无人车浮窗坐标与数据 (从出发阶段起更新，也就是 activePhaseIndex >= 7)
  if (props.activePhaseIndex >= 7) {
    const isTanker = props.focusedPointId === 'accident_red';
    const carPosCallback = isTanker ? sharedTankerRescueCarPosition : sharedTruckRescueCarPosition;
    
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

// 绘制湖北省行政边界外框线：保留科技感，但避免抢占卫星底图视觉重心。
function drawBoundaryLine(coords) {
  if (!viewer) return;
  const positions = convertCoordsToCartesians(coords);
  viewer.entities.add({
    name: '湖北省行政边界',
    polyline: {
      positions: positions,
      width: 2.8,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.14,
        color: Cesium.Color.fromCssColorString('#46dfff')
      }),
      clampToGround: true
    }
  });
}

// 绘制市级行政区区划边界与点击面：弱化为背景信息，重点城市再以色彩提示。
function drawCityBoundary(coords, colorStr, name, id) {
  if (!viewer) return;
  // 市界线提升到围栏顶面，形成与示例相同的“分区浮在网格上方”的层次。
  const positions = Cesium.Cartesian3.fromDegreesArrayHeights(
    coords.flatMap(([lng, lat]) => [lng, lat, ELECTRONIC_FENCE_ROOF_HEIGHT + 30])
  );
  
  // 1. 细边线，避免和省级边界、路网产生视觉竞争。
  viewer.entities.add({
    id: id + '-line',
    name: name,
    polyline: {
      positions: positions,
      width: 2.6,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.18,
        color: Cesium.Color.WHITE.withAlpha(0.9)
      }),
      clampToGround: false
    }
  });

  // 2. 每个行政区都是同高度的独立蓝色顶面：外圈可看到分层侧壁，
  // 内部仍只保留白色分区线，避免相邻城市的侧墙互相遮挡。
  // GridMaterial 的单元带透明度，单独使用会透出未加载影像时的黑色画布。
  // 先铺实色底板，保证每个市级区域都有稳定、清晰的青蓝底色。
  viewer.entities.add({
    id: id + '-base',
    name: `${name}底板`,
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      height: ELECTRONIC_FENCE_ROOF_HEIGHT - 24,
      // 底板和顶层共同响应亮度控件，底板保持略低的透明度以维持层次。
      material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(
        () => Cesium.Color.fromCssColorString('#087d9c').withAlpha(vectorLayerConfig.opacity / 100 * 0.84),
        false
      )),
      classificationType: Cesium.ClassificationType.BOTH,
      outline: false
    }
  });

  // 网格悬于底板上方，既保留数字孪生纹理，又不会出现黑底。
  viewer.entities.add({
    id: id,
    name: name,
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      height: ELECTRONIC_FENCE_ROOF_HEIGHT,
      // 不使用 GridMaterial：该材质会在非线条区域混入深色着色结果。
      // 纯色面保证市级地图在任何底图状态下均为清爽的青蓝色。
      // 顶层行政区面同步响应亮度；边界线仍保持原有亮度，方便识别分区。
      material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(
        () => Cesium.Color.fromCssColorString('#139fbe').withAlpha(vectorLayerConfig.opacity / 100),
        false
      )),
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
    if (!viewer) return;
    if (!response.ok) throw new Error('读取 hubei_cities.json 失败');
    const geojson = await response.json();
    if (!viewer) return;
    
    geojson.features.forEach(feature => {
      const properties = feature.properties || {};
      const name = properties.name || '';
      const adcode = properties.adcode;
      const geometry = feature.geometry;
      if (!name || !geometry) return;

      // 统一低饱和蓝青，重点城市仅做克制的色彩提示。
      let colorStr = '#58c9e8';
      if (name.includes('武汉')) {
        colorStr = '#57d7ff';
      } else if (name.includes('黄冈')) {
        colorStr = '#e6bd63';
      } else if (name.includes('仙桃')) {
        colorStr = '#df79ae';
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

      // 2. 添加低干扰市级文字标注。
      const center = properties.centroid || properties.center;
      if (center && center.length >= 2) {
        const labelEntity = viewer.entities.add({
          // 文字也置于网格顶面上方，既不会被顶面遮挡，也不会与路网点位争抢层级。
          position: Cesium.Cartesian3.fromDegrees(center[0], center[1], ELECTRONIC_FENCE_ROOF_HEIGHT + 180),
          label: {
            text: `${name}`,
            // 市名属于省域视图的一级信息：不跟随普通标注缩得过小。
            font: `800 ${Math.max(labelConfig.fontSize, 22)}px "Microsoft YaHei UI", "Microsoft YaHei", sans-serif`,
            fillColor: Cesium.Color.fromCssColorString('#f5ffff'),
            // 标签直接叠加在地图上，仅保留深青描边以确保亮色底图上的可读性。
            outlineColor: Cesium.Color.fromCssColorString('#06374a'),
            outlineWidth: Math.max(labelConfig.outlineWidth, 5),
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            // 加载遮罩显示期间隐藏市级名称，保留 Cesium 球体作为加载背景。
            show: new Cesium.CallbackProperty(() => !loading.value, false),
            showBackground: false,
            // 随相机距离自动缩放：近看正常大小，拉远时缩小
            scaleByDistance: new Cesium.NearFarScalar(300000, 1.12, 2500000, 0.9),
            // 省域总览依然保持清晰可读。
            translucencyByDistance: new Cesium.NearFarScalar(650000, 1.0, 2200000, 0.94)
          }
        });
        cityLabelEntities.push(labelEntity);
        syncOverviewPointVisibility();
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
    if (!viewer) return;
    if (!response.ok) throw new Error('读取 hubei.json 失败');
    const geojson = await response.json();
    if (!viewer) return;

    const holes = [];
    const fenceRings = [];
    let regionIndex = 0;
    geojson.features.forEach(feature => {
      const geometry = feature.geometry;
      if (geometry.type === 'Polygon') {
        const outerRing = convertCoordsToCartesians(geometry.coordinates[0]);
        fenceRings.push(geometry.coordinates[0]);
        holes.push(new Cesium.PolygonHierarchy(outerRing));
        drawBoundaryLine(geometry.coordinates[0]);
        viewer.entities.add({
          id: `hubei-basemap-tint-${regionIndex++}`,
          polygon: {
            hierarchy: new Cesium.PolygonHierarchy(outerRing),
            // 省内底图略微提亮，保留卫星纹理并为青蓝网格提供明亮承托。
            material: Cesium.Color.fromCssColorString('#16769a').withAlpha(0.12),
            classificationType: Cesium.ClassificationType.BOTH,
            outline: false
          }
        });
      } else if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach(polygon => {
          const outerRing = convertCoordsToCartesians(polygon[0]);
          fenceRings.push(polygon[0]);
          holes.push(new Cesium.PolygonHierarchy(outerRing));
          drawBoundaryLine(polygon[0]);
          viewer.entities.add({
            id: `hubei-basemap-tint-${regionIndex++}`,
            polygon: {
              hierarchy: new Cesium.PolygonHierarchy(outerRing),
            // 与主区域保持一致，避免多岛区域呈现突兀的黑底。
            material: Cesium.Color.fromCssColorString('#16769a').withAlpha(0.12),
              classificationType: Cesium.ClassificationType.BOTH,
              outline: false
            }
          });
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

    // 将湖北省作为“空洞”添加到反向遮罩中。外围仅做轻微压暗，
    // 使湖北以外的卫星底图、河流与地貌也能和参考图一样清晰可见。
    viewer.entities.add({
      id: 'hubei-mask',
      name: '湖北省行政边界反向遮罩',
      polygon: {
        hierarchy: worldPolygonHierarchy,
        material: Cesium.Color.fromCssColorString('#06111d').withAlpha(0.28),
        classificationType: Cesium.ClassificationType.BOTH,
        outline: false
      }
    });

    // 以现有湖北行政边界作为默认围栏，避免出现与底图不贴合的演示多边形。
    // 新项目接入时可把 fenceRings[0] 换为业务端下发的 GeoJSON 环坐标。
    if (fenceRings.length > 0) {
      addElectronicFence(fenceRings[0], 'hubei');
      syncOverviewPointVisibility();
    }

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
  if (containerRef.value.offsetWidth === 0 || containerRef.value.offsetHeight === 0) {
    console.log('[Cesium] 容器尺寸为 0，延迟 100ms 重新尝试初始化...')
    initViewerTimeout = setTimeout(initViewer, 100)
    return
  }
  console.log('[Cesium] 容器元素:', containerRef.value)
  console.log('[Cesium] 容器尺寸:', containerRef.value.offsetWidth, 'x', containerRef.value.offsetHeight)
  
  // 屏蔽 Cesium 默认的红色崩溃弹窗，由 Vue 捕获并友好提示
  if (typeof window !== 'undefined' && window.Cesium) {
    try {
      if (typeof window.Cesium.showHtmlErrorPanel === 'function') {
        window.Cesium.showHtmlErrorPanel = function(title, message, error) {
          console.error('[Cesium Widget Error]', title, message, error);
        };
      }
      if (window.Cesium.CesiumWidget && window.Cesium.CesiumWidget.prototype) {
        window.Cesium.CesiumWidget.prototype.showErrorPanel = function(title, message, error) {
          console.error('[Cesium Widget Proto Error Blocked]', title, message, error);
        };
      }
    } catch (e) {}
  }

  try {
    try {
      console.log('[Cesium] 尝试创建 WebGL 2 Viewer 实例...')
    viewer = new Cesium.Viewer(containerRef.value, {
      animation: false, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
      infoBox: false, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
      timeline: false, shouldAnimate: true, skyAtmosphere: false, baseLayer: false,
      contextOptions: {
        webgl: {
          failIfMajorPerformanceCaveat: false
        }
      }
    })
  } catch (e1) {
    console.warn('[Cesium] WebGL 2 创建失败，尝试降级创建 WebGL 1 Viewer...', e1.message)
    try {
      viewer = new Cesium.Viewer(containerRef.value, {
        animation: false, baseLayerPicker: false, fullscreenButton: false, geocoder: false, homeButton: false,
        infoBox: false, navigationHelpButton: false, sceneModePicker: false, selectionIndicator: false,
        timeline: false, shouldAnimate: true, skyAtmosphere: false, baseLayer: false,
        contextOptions: {
          requestWebgl1: true,
          webgl: {
            failIfMajorPerformanceCaveat: false
          }
        }
      })
    } catch (e2) {
      throw new Error('WebGL 1/2 均初始化失败: ' + e2.message);
    }
  }
  
  window.viewer = viewer

  console.log('[Cesium] Viewer 实例创建成功')
    
    // 关闭地球物理光照（防止因为时差导致场景处于黑夜）
    viewer.scene.globe.enableLighting = false
    
    // 关键修复：添加“相机头灯”，将环境光强制绑定到相机视角前方，这样不管什么角度看模型，模型都是被照亮的
    viewer.scene.light = new Cesium.DirectionalLight({
      direction: viewer.camera.direction
    })
    removeLightListener = viewer.scene.preRender.addEventListener(function(scene, time) {
      scene.light.direction = Cesium.Cartesian3.clone(scene.camera.directionWC, scene.light.direction)

      // 🚁 强行驱动无人机 4 个螺旋桨节点高频 Y 轴旋转（保留原始 0.01 比例与各挂座 3D 偏移位移，彻底解决不旋转与变大问题）
      uavRotorAngle += 0.55;
      const propellerDefaults = {
        'Propeller_1': { trans: new Cesium.Cartesian3(-0.085382, 0.057920, 0.075441), dir: 1 },
        'Propeller_2': { trans: new Cesium.Cartesian3(-0.085382, 0.057920, -0.070529), dir: -1 },
        'Propeller_3': { trans: new Cesium.Cartesian3(0.085382, 0.057920, -0.070529), dir: 1 },
        'Propeller_4': { trans: new Cesium.Cartesian3(0.085382, 0.057920, 0.075441), dir: -1 }
      };
      const defaultScale = new Cesium.Cartesian3(0.01, 0.01, 0.01);

      const allUavs = [...(uavEntities || []), ...(tankerUavEntities || [])];
      allUavs.forEach(entity => {
        if (entity && entity.show) {
          let p = primitiveCache.get(entity.id);
          // 模型查找由 updateModelsReadyStatus 统一节流，渲染帧只读取缓存。
          if (p) {
            const modelObj = p.model || p;
            if (modelObj && typeof modelObj.getNode === 'function') {
              Object.keys(propellerDefaults).forEach(nodeName => {
                try {
                  const node = modelObj.getNode(nodeName);
                  if (node) {
                    const info = propellerDefaults[nodeName];
                    let trans = info.trans;
                    if (node.translation) {
                      if (typeof node.translation.x === 'number') trans = node.translation;
                      else if (Array.isArray(node.translation) && node.translation.length >= 3) {
                        trans = new Cesium.Cartesian3(node.translation[0], node.translation[1], node.translation[2]);
                      }
                    }
                    let scale = defaultScale;
                    if (node.scale) {
                      if (typeof node.scale.x === 'number') scale = node.scale;
                      else if (Array.isArray(node.scale) && node.scale.length >= 3) {
                        scale = new Cesium.Cartesian3(node.scale[0], node.scale[1], node.scale[2]);
                      }
                    }
                    const rotM3 = Cesium.Matrix3.fromRotationY(uavRotorAngle * info.dir);
                    const rotTransM4 = Cesium.Matrix4.fromRotationTranslation(rotM3, trans);
                    node.matrix = Cesium.Matrix4.multiplyByScale(rotTransM4, scale, new Cesium.Matrix4());
                  }
                } catch (e) {}
              });
            }
          }
        }
      });
    })

     viewer.cesiumWidget.creditContainer.style.display = 'none'

    // 临时调试点击事件，获取道路精确坐标
    debugHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
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
          // 点击黄冈市行政区域 → 不需要跳转到第二视角
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
    console.log('[Cesium] 加载并校正 ArcGIS 深色卫星底图...')
    try {
      const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
        'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
      )
      if (!viewer) return
      const imageryLayer = viewer.imageryLayers.addImageryProvider(imagery)
      // 外围维持较暗的卫星底图，湖北省内的透明叠色和网格则会更明亮、清楚。
      imageryLayer.brightness = 0.9
      imageryLayer.contrast = 1.1
      imageryLayer.saturation = 0.72
      imageryLayer.gamma = 1.0
      imageryLayer.hue = -0.02
      console.log('[Cesium] ArcGIS 深色卫星底图加载成功')
    } catch (e) {
      if (!viewer) return
      console.warn('[Cesium] ArcGIS 影像图层加载失败，使用本地离线底图:', e.message)
      const fallbackProvider = await Cesium.TileMapServiceImageryProvider.fromUrl(
        Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII')
      )
      const fallbackLayer = viewer.imageryLayers.addImageryProvider(fallbackProvider)
      fallbackLayer.brightness = 0.9
      fallbackLayer.contrast = 1.1
      fallbackLayer.saturation = 0.72
      fallbackLayer.gamma = 1.0
    }

    if (!viewer) return
    // 加载湖北省行政边界反向蒙版
    try {
      await loadHubeiMask()
    } catch (e) {
      console.warn('初始化湖北省遮罩蒙版时出现警告:', e.message)
    }

    if (!viewer) return
    // 加载仙桃市和黄冈市行政边界
    try {
      await loadCityBoundaries()
    } catch (e) {
      console.warn('初始化仙桃市和黄冈市边界时出现警告:', e.message)
    }

    if (!viewer) return
    try {
      await loadHubeiRoads()
    } catch (e) {
      console.warn('初始化湖北省干线路网和两客一危车辆时出现警告:', e.message)
    }

    if (!viewer) return
    try {
      addEventEntities()
    } catch (e) {
      console.warn('添加事件实体时出现警告:', e.message)
    }

    if (!viewer) return
    try {
      smokeParticle = viewer.scene.primitives.add(createSmokeSystem(truckAdjust.lng, truckAdjust.lat))
      fireParticle = viewer.scene.primitives.add(createFireSystem(truckAdjust.lng, truckAdjust.lat))
      leakParticle = viewer.scene.primitives.add(createLeakSystem(tankerPointAdjust.lng, tankerPointAdjust.lat))
      diffusionParticle = viewer.scene.primitives.add(createDiffusionSystem(tankerPointAdjust.lng, tankerPointAdjust.lat))
    } catch (e) {
      console.warn('初始化粒子系统时出现警告:', e.message)
    }

    if (!viewer) return
    try {
      applyOrbitView()
    } catch (e) {
      console.warn('应用初始视角时出现警告:', e.message)
    }

    if (!viewer) return
    try {
      updatePhaseScene(props.activePhaseIndex)
    } catch (e) {
      console.warn('更新初始场景时出现警告:', e.message)
    }

    if (!viewer) return
    viewer.scene.postRender.addEventListener(updateModelsReadyStatus)
    viewer.scene.postRender.addEventListener(updatePopupPosition)

    loading.value = false
  } catch (error) {
    errorMessage.value = '三维地球 WebGL 初始化失败（可能由于浏览器 WebGL 上下文耗尽或未开启显卡硬件加速），请尝试在浏览器设置中开启“使用硬件加速”并刷新页面重试。'
    loading.value = false
    console.error('三维地球初始化失败:', error)
  }
}

// 两客一危在途监控分类筛选与状态
const activeVehicleFilter = ref('all');
// 无人机出动阶段不显示背景车流中的红/蓝微型态势点，避免与主无人机位置点混淆。
const suppressAuxiliaryTrafficPoints = ref(false);
const lkywVehicles = ref([]);
let lkywBillboardCollection = null;
let lkywPointCollection = null;
let trafficVehicles = [];
let trafficPointCollection = null;
let trafficAnimationRemoveListener = null;
// 事故近景保留电子围栏，隐藏省域边界标记与总览车流。
function syncOverviewPointVisibility() {
  const visible = !(props.focusedPointId && Number(props.activePhaseIndex) >= 1);
  if (trafficPointCollection) trafficPointCollection.show = visible;
  if (lkywPointCollection) lkywPointCollection.show = visible;
  if (lkywBillboardCollection) lkywBillboardCollection.show = visible;
  if (!viewer) return;
  viewer.entities.values.forEach(entity => {
    if (entity.name === '湖北省行政边界' || String(entity.id).startsWith('city-boundary-') || (String(entity.id).startsWith('electronic-fence-') && String(entity.id).endsWith('-surface'))) {
      entity.show = visible;
    }
  });
  viewer.scene.requestRender();
}
watch(() => [props.focusedPointId, props.activePhaseIndex], syncOverviewPointVisibility);

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

// ⚠️ 实时风险预警与省界卡口排名数据
const riskStats = reactive({
  highRiskCount: 14,
  speedingCount: 8,
  fatigueCount: 6,
  deviationCount: 2
});

const riskVehicles = reactive([
  {
    plate: '鄂A-H8921',
    type: '危化品 · 液化气',
    class: 'hazard',
    level: '高危告警',
    levelClass: 'red',
    reason: '严重超速 (98km/h) · 罐体压力异常偏高',
    location: '沪渝高速 G50 KM412 (仙桃段)',
    driver: '李*强 (138****5921)',
    lng: 113.45,
    lat: 30.36
  },
  {
    plate: '鄂C-K5531',
    type: '危化品 · 汽油',
    class: 'hazard',
    level: '高危告警',
    levelClass: 'red',
    reason: '连续驾驶超 4 小时 (疲劳驾驶警报)',
    location: '福银高速 G70 KM285 (襄阳段)',
    driver: '王*伟 (139****1842)',
    lng: 112.14,
    lat: 32.04
  },
  {
    plate: '鄂B-H9021',
    type: '公路客运 · 49座',
    class: 'passenger',
    level: '偏离线路',
    levelClass: 'orange',
    reason: '偏离核定运行线路 (超出 12 公里)',
    location: '沪蓉高速 G42 KM198 (宜昌段)',
    driver: '张*国 (137****3310)',
    lng: 111.28,
    lat: 30.69
  },
  {
    plate: '鄂F-T9918',
    type: '旅游客运',
    class: 'tourist',
    level: '违规时段',
    levelClass: 'gold',
    reason: '违规夜间 2:00-5:00 仍处于行驶状态',
    location: '汉十高速 S82 KM120 (十堰段)',
    driver: '陈*龙 (136****9088)',
    lng: 110.79,
    lat: 32.65
  }
]);

const checkpoints = reactive([
  {
    rank: 'TOP 1',
    rankClass: 'gold',
    name: '临湘湖北省界卡口 (G4京港澳)',
    status: '畅通',
    statusClass: 'green',
    flow: 1842,
    inflow: 1020,
    outflow: 822
  },
  {
    rank: 'TOP 2',
    rankClass: 'gold',
    name: '黄梅九江大桥卡口 (G70福银)',
    status: '繁忙',
    statusClass: 'gold',
    flow: 1560,
    inflow: 840,
    outflow: 720
  },
  {
    rank: 'TOP 3',
    rankClass: 'silver',
    name: '荆州长江大桥卡口 (G55二广)',
    status: '畅通',
    statusClass: 'green',
    flow: 1320,
    inflow: 710,
    outflow: 610
  },
  {
    rank: 'TOP 4',
    rankClass: 'border',
    name: '京港澳赤壁卡口 (G4)',
    status: '缓行',
    statusClass: 'orange',
    flow: 1180,
    inflow: 650,
    outflow: 530
  },
  {
    rank: 'TOP 5',
    rankClass: 'border',
    name: '鄂陕界关防卡口 (G7011)',
    status: '畅通',
    statusClass: 'green',
    flow: 950,
    inflow: 510,
    outflow: 440
  }
]);

const firstNames = ['张', '李', '王', '刘', '陈', '杨', '赵', '黄', '周', '吴'];
const lastNames = ['伟', '强', '芳', '军', '杰', '敏', '超', '勇', '平', '国'];
const riskLocationsList = [
  '沪渝高速 G50 KM412 (仙桃段)',
  '福银高速 G70 KM285 (襄阳段)',
  '沪蓉高速 G42 KM198 (宜昌段)',
  '汉十高速 S82 KM120 (十堰段)',
  '京港澳高速 G4 KM105 (咸宁段)',
  '大广高速 G45 KM320 (黄冈段)'
];

function generateRandomDriver() {
  const f = firstNames[Math.floor(Math.random() * firstNames.length)];
  const l = lastNames[Math.floor(Math.random() * lastNames.length)];
  const num = Math.floor(1000 + Math.random() * 9000);
  const prefix = ['138', '139', '135', '136', '137', '186', '189'][Math.floor(Math.random() * 7)];
  return `${f}*${l} (${prefix}****${num})`;
}

// 🛠️ 大屏 HUD 高阶视图 Tabs 模式 ('overview' | 'risk' | 'checkpoint' | 'ai')
const activeHudTab = ref('overview');

let activeFocusedRiskEntity = null;
let activeFocusedRiskPoint = null;
let trackedRiskVehicle = null;

const focusRiskVehicleOnMap = (item) => {
  if (!viewer || !item) return;
  const { lng, lat, plate, type, levelClass, reason } = item;

  // 1. 清除上一次的追踪点与大标牌，并显隐复原上一次被追踪车辆的默认小标牌
  if (viewer) {
    viewer.trackedEntity = undefined;
  }
  if (activeFocusedRiskEntity) {
    viewer.entities.remove(activeFocusedRiskEntity);
    activeFocusedRiskEntity = null;
  }
  if (activeFocusedRiskPoint) {
    viewer.entities.remove(activeFocusedRiskPoint);
    activeFocusedRiskPoint = null;
  }
  if (trackedRiskVehicle && trackedRiskVehicle.billboard) {
    trackedRiskVehicle.billboard.show = true; // 复原前一辆车的常规车牌浮标显示
    trackedRiskVehicle = null;
  }

  // 2. 在在途移动车辆中寻找匹配或分配一辆移动点位
  let matched = null;
  let targetLng = lng;
  let targetLat = lat;

  if (lkywVehicles.value && lkywVehicles.value.length > 0) {
    const focusPlate = plate.replace('-', '·');
    matched = lkywVehicles.value.find(v => v.plate === focusPlate);
    
    // 如果该随机车牌目前没有对应的移动实体，随机抽调一辆同类型（或任意）移动车辆重设车牌并追踪
    if (!matched) {
      const candidates = lkywVehicles.value.filter(v => v.category === (item.class || 'hazard'));
      matched = candidates.length > 0 ? candidates[Math.floor(Math.random() * candidates.length)] : lkywVehicles.value[0];
      if (matched) {
        matched.plate = plate.replace('-', '·');
        const newCanvas = createVehicleBillboardCanvas(matched.category, matched.plate, matched.speed);
        matched.billboard.image = newCanvas;
      }
    }
  }

  if (matched) {
    trackedRiskVehicle = matched;
    // 关键：隐退这辆车默认的常规车牌浮标，避免与其上方的预警大悬浮窗口互相重叠打架
    if (matched.billboard) {
      matched.billboard.show = false;
    }
    const cartesian = matched.billboard.position;
    const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
    targetLng = Cesium.Math.toDegrees(cartographic.longitude);
    targetLat = Cesium.Math.toDegrees(cartographic.latitude);
  } else {
    trackedRiskVehicle = null;
  }

  // 3. 构造动态跟随逻辑（当车辆在道路上行驶时，预警大标牌与红点 100% 实时平滑跟随车辆，绝不留在原地与后续车辆重叠）
  const dynamicPosition = new Cesium.CallbackProperty(() => {
    if (trackedRiskVehicle && trackedRiskVehicle.billboard && trackedRiskVehicle.billboard.position) {
      return trackedRiskVehicle.billboard.position;
    }
    return Cesium.Cartesian3.fromDegrees(targetLng, targetLat);
  }, false);

  // 4. 绘制带有预警详情的赛博风险大标牌（增加 pixelOffset 垂直向上避让 28px）
  const canvas = createRiskVehicleCanvas(plate, type, reason);

  activeFocusedRiskEntity = viewer.entities.add({
    position: dynamicPosition,
    billboard: {
      image: canvas,
      scale: 0.8,
      pixelOffset: new Cesium.Cartesian2(0, -28), // 向上抬高避开下方红点与模型
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  });

  let dotColor = '#FF3344';
  if (levelClass === 'orange') {
    dotColor = '#FF8F00';
  } else if (levelClass === 'gold') {
    dotColor = '#FFD700';
  }

  activeFocusedRiskPoint = viewer.entities.add({
    position: dynamicPosition,
    point: {
      color: Cesium.Color.fromCssColorString(dotColor),
      pixelSize: 10.0,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2.0,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  });

  // 设置跟随相机偏移量（西南偏南 1500m 距离，1000m 高度俯瞰视角）
  activeFocusedRiskPoint.viewFrom = new Cesium.Cartesian3(-1500, -1500, 1000);

  // 5. 照相机飞抵该移动点位并锁定追踪
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(targetLng, targetLat, 2500),
    orientation: {
      heading: Cesium.Math.toRadians(0.0),
      pitch: Cesium.Math.toRadians(-45.0),
      roll: 0.0
    },
    duration: 1.2,
    complete: () => {
      if (viewer && activeFocusedRiskPoint) {
        viewer.trackedEntity = activeFocusedRiskPoint; // 启用相机自动平滑跟车
      }
    }
  });
};

function createRiskVehicleCanvas(plate, type, reason) {
  const scaleFactor = 2;
  const logicalWidth = 190;
  const logicalHeight = 44;
  const canvas = document.createElement('canvas');
  canvas.width = logicalWidth * scaleFactor;
  canvas.height = logicalHeight * scaleFactor;
  const ctx = canvas.getContext('2d');

  ctx.scale(scaleFactor, scaleFactor);

  const themeColor = '#FF3344';
  const cardW = 182;
  const cardH = 36;
  const cardX = 4;
  const cardY = 3;

  ctx.save();
  ctx.shadowColor = themeColor;
  ctx.shadowBlur = 8;
  ctx.fillStyle = 'rgba(15, 6, 12, 0.92)';
  ctx.strokeStyle = themeColor;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  if (typeof ctx.roundRect === 'function') {
    ctx.roundRect(cardX, cardY, cardW, cardH, 8);
  } else {
    ctx.rect(cardX, cardY, cardW, cardH);
  }
  ctx.fill();
  ctx.stroke();
  ctx.restore();

  ctx.fillStyle = themeColor;
  ctx.fillRect(cardX + 2, cardY + 2, 4, cardH - 4);

  ctx.font = 'bold 11px -apple-system, sans-serif';
  ctx.fillStyle = '#FFFFFF';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillText(plate, cardX + 12, cardY + 6);

  ctx.font = '9px sans-serif';
  ctx.fillStyle = '#FFAAAA';
  ctx.fillText(type, cardX + 75, cardY + 8);

  ctx.font = '9px sans-serif';
  ctx.fillStyle = '#FFD700';
  ctx.fillText(reason.length > 25 ? reason.substring(0, 24) + '...' : reason, cardX + 12, cardY + 20);

  ctx.fillStyle = themeColor;
  ctx.beginPath();
  ctx.moveTo(logicalWidth / 2 - 4, cardY + cardH);
  ctx.lineTo(logicalWidth / 2 + 4, cardY + cardH);
  ctx.lineTo(logicalWidth / 2, cardY + cardH + 5);
  ctx.closePath();
  ctx.fill();

  return canvas;
}

// 切换页签时，自动释放地图上的预警跟随与点位
watch(activeHudTab, (newTab) => {
  if (newTab !== 'risk') {
    if (viewer) {
      viewer.trackedEntity = undefined;
    }
    if (activeFocusedRiskEntity) {
      viewer.entities.remove(activeFocusedRiskEntity);
      activeFocusedRiskEntity = null;
    }
    if (activeFocusedRiskPoint) {
      viewer.entities.remove(activeFocusedRiskPoint);
      activeFocusedRiskPoint = null;
    }
    trackedRiskVehicle = null;
  }
});

const handleAutoDispatchTrigger = () => {
  alert('🤖 全省应急联动机制已成功开启！系统正在推演最佳调度路线与巡逻无人机航线。');
};
// 🛠️ 右侧智控终端面板 展开/收起 状态
const isHudCollapsed = ref(false);

const legendRightOffset = computed(() => {
  // 为首页右侧态势栏（含外边距和间隙）预留空间，避免图例被侧栏遮挡。
  return 'var(--layout-right-reserve, 470px)';
});

const activeHazardDemoCount = computed(() => {
  if (!lkywVehicles.value) return 0;
  return lkywVehicles.value.filter(v => v.category === 'hazard').length;
});

const activePassengerDemoCount = computed(() => {
  if (!lkywVehicles.value) return 0;
  return lkywVehicles.value.filter(v => v.category === 'passenger').length;
});

const activeTouristDemoCount = computed(() => {
  if (!lkywVehicles.value) return 0;
  return lkywVehicles.value.filter(v => v.category === 'tourist').length;
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
  { time: '19:09:39', location: '京港澳赤壁卡口', plate: '鄂C-K5531', category: '公路客运', action: '出省' },
  { time: '19:09:37', location: '沪蓉鄂东大桥', plate: '鄂F-T9918', category: '旅游客运', action: '入省' }
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
      const randomCat = cat === 'hazard' ? '危化品' : (cat === 'passenger' ? '公路客运' : '旅游客运');
      
      latestCameraLogs.unshift({
        time: timeStr,
        location: randomLoc,
        plate: generateRandomPlate(),
        category: randomCat,
        action: isEntry ? '入省' : '出省'
      });
      if (latestCameraLogs.length > 4) latestCameraLogs.pop();
    }

    // 4. 实时风险预警动态更新与流转
    if (Math.random() > 0.82) {
      const alarmTypes = [
        {
          type: '危化品 · 液化气',
          class: 'hazard',
          level: '高危告警',
          levelClass: 'red',
          reasonTemplate: '严重超速 (SPEEDkm/h) · 罐体压力异常偏高',
          statKey: 'speedingCount'
        },
        {
          type: '危化品 · 汽油',
          class: 'hazard',
          level: '高危告警',
          levelClass: 'red',
          reasonTemplate: '连续驾驶超 HOURS 小时 (疲劳驾驶警报)',
          statKey: 'fatigueCount'
        },
        {
          type: '公路客运 · 49座',
          class: 'passenger',
          level: '偏离线路',
          levelClass: 'orange',
          reasonTemplate: '偏离核定运行线路 (超出 DIST 公里)',
          statKey: 'deviationCount'
        },
        {
          type: '旅游客运',
          class: 'tourist',
          level: '违规时段',
          levelClass: 'gold',
          reasonTemplate: '违规夜间 2:00-5:00 仍处于行驶状态',
          statKey: 'fatigueCount'
        }
      ];

      const chosen = alarmTypes[Math.floor(Math.random() * alarmTypes.length)];
      let reason = chosen.reasonTemplate;
      if (reason.includes('SPEED')) {
        reason = reason.replace('SPEED', Math.floor(95 + Math.random() * 25));
      }
      if (reason.includes('HOURS')) {
        reason = reason.replace('HOURS', (4.1 + Math.random() * 2).toFixed(1));
      }
      if (reason.includes('DIST')) {
        reason = reason.replace('DIST', Math.floor(10 + Math.random() * 15));
      }

      const newAlert = {
        plate: generateRandomPlate(),
        type: chosen.type,
        class: chosen.class,
        level: chosen.level,
        levelClass: chosen.levelClass,
        reason: reason,
        location: riskLocationsList[Math.floor(Math.random() * riskLocationsList.length)],
        driver: generateRandomDriver(),
        lng: 110 + Math.random() * 5,
        lat: 30 + Math.random() * 2
      };

      riskVehicles.unshift(newAlert);
      if (riskVehicles.length > 4) {
        riskVehicles.pop();
      }

      riskStats[chosen.statKey]++;
      riskStats.highRiskCount = riskStats.speedingCount + riskStats.fatigueCount + riskStats.deviationCount;
    }

    if (Math.random() > 0.7) {
      const keys = ['speedingCount', 'fatigueCount', 'deviationCount'];
      const key = keys[Math.floor(Math.random() * keys.length)];
      const delta = Math.random() > 0.5 ? 1 : -1;
      riskStats[key] = Math.max(1, riskStats[key] + delta);
      riskStats.highRiskCount = riskStats.speedingCount + riskStats.fatigueCount + riskStats.deviationCount;
    }

    // 5. 卡口流量实时变化排行 Top 5
    checkpoints.forEach(cp => {
      const flowDelta = (Math.random() > 0.5 ? 1 : -1) * (Math.floor(Math.random() * 8) + 1);
      cp.flow = Math.max(500, cp.flow + flowDelta);
      
      const inDelta = Math.random() > 0.4 ? (Math.floor(Math.random() * 2) + 1) : 0;
      const outDelta = Math.random() > 0.4 ? (Math.floor(Math.random() * 2) + 1) : 0;
      cp.inflow += inDelta;
      cp.outflow += outDelta;

      if (cp.flow > 1600) {
        cp.status = '繁忙';
        cp.statusClass = 'gold';
      } else if (cp.flow > 1200 && cp.flow <= 1600) {
        cp.status = '缓行';
        cp.statusClass = 'orange';
      } else {
        cp.status = '畅通';
        cp.statusClass = 'green';
      }
    });

    checkpoints.sort((a, b) => b.flow - a.flow);
    checkpoints.forEach((cp, index) => {
      cp.rank = `TOP ${index + 1}`;
      cp.rankClass = index === 0 || index === 1 ? 'gold' : (index === 2 ? 'silver' : 'border');
    });

  }, 850);
}

// 启动省界卡口实时流转模拟
startHudStatsSimulation();

function toggleVehicleFilter(filterType, preserveSelection = false) {
  // 允许点击已选中的类别时取消选中，恢复显示全部车辆
  if (!preserveSelection && activeVehicleFilter.value === filterType && filterType !== 'all') {
    filterType = 'all';
  }
  
  activeVehicleFilter.value = filterType;
  trafficConfig.activeCategory = filterType;

  // 1. 过滤精细重点巡航 Demo 悬浮标牌
  if (lkywVehicles.value && lkywVehicles.value.length > 0) {
    lkywVehicles.value.forEach(item => {
      if (suppressAuxiliaryTrafficPoints.value && (item.category === 'hazard' || item.category === 'tourist')) {
        if (item.billboard) item.billboard.show = false;
        if (item.point) item.point.show = false;
        return;
      }
      const isMatch = (filterType === 'all' || item.category === filterType);
      if (item.billboard) item.billboard.show = isMatch;
      if (item.point) item.point.show = isMatch;
    });
  }

  // 分类筛选同步作用于背景车辆点与重点标牌。
  if (trafficVehicles && trafficVehicles.length > 0) {
    trafficVehicles.forEach(v => {
      if (!v.primitive) return;
      if (suppressAuxiliaryTrafficPoints.value && (v.category === 'hazard' || v.category === 'tourist')) {
        v.primitive.show = false;
        return;
      }
      if (filterType === 'all') {
        v.primitive.show = true;
        v.primitive.color = Cesium.Color.fromCssColorString(v.dotColor).withAlpha(0.85);
        v.primitive.pixelSize = v.category === 'hazard' ? 5.5 : 4.5;
      } else if (v.category === filterType) {
        v.primitive.show = true;
        v.primitive.color = Cesium.Color.fromCssColorString(v.dotColor).withAlpha(1.0);
        v.primitive.pixelSize = 7.0;
      } else {
        v.primitive.show = false;
      }
    });
  }
  const counts = { hazard: 0, passenger: 0, tourist: 0 };
  for (const vehicle of [...trafficVehicles, ...lkywVehicles.value]) {
    if (vehicle.primitive?.show || vehicle.point?.show) counts[vehicle.category]++;
  }
  emit('vehicle-layer-change', { category: filterType, counts });
}

// 动态绘制 "两客一危" 车辆的紧凑道路标记：仅保留车牌与速度，避免与地图车辆定位点重复。
function createVehicleBillboardCanvas(category, plate, speed) {
  const scaleFactor = 2;
  const logicalWidth = 118;
  const logicalHeight = 26;
  const canvas = document.createElement('canvas');
  canvas.width = logicalWidth * scaleFactor;
  canvas.height = logicalHeight * scaleFactor;
  const ctx = canvas.getContext('2d');
  ctx.scale(scaleFactor, scaleFactor);

  const themeColor = MAP_VEHICLE_STYLES[category].color;
  const cardX = 5;
  const cardY = 3;
  const cardW = 109;
  const cardH = 19;

  // 低遮挡的半透明信息胶囊，不再使用大面积深色矩形底框。
  ctx.save();
  const cardGrad = ctx.createLinearGradient(cardX, cardY, cardX, cardY + cardH);
  cardGrad.addColorStop(0, 'rgba(8, 39, 57, 0.66)');
  cardGrad.addColorStop(1, 'rgba(3, 22, 39, 0.52)');
  ctx.fillStyle = cardGrad;
  ctx.strokeStyle = `${themeColor}B8`;
  ctx.lineWidth = 0.9;
  ctx.beginPath();
  if (typeof ctx.roundRect === 'function') ctx.roundRect(cardX, cardY, cardW, cardH, 8);
  else ctx.rect(cardX, cardY, cardW, cardH);
  ctx.fill();
  ctx.stroke();
  ctx.restore();

  // 车牌与速度维持可读，同时降低总览时的视觉重量。
  ctx.font = '700 10.5px -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif';
  ctx.fillStyle = '#FFFFFF';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText(plate, cardX + 7, cardY + cardH / 2 + 0.5);
  ctx.strokeStyle = 'rgba(219, 246, 255, 0.22)';
  ctx.lineWidth = 0.7;
  ctx.beginPath();
  ctx.moveTo(cardX + 67, cardY + 4);
  ctx.lineTo(cardX + 67, cardY + cardH - 4);
  ctx.stroke();
  ctx.font = '700 9.5px "Orbitron", monospace';
  ctx.fillStyle = '#E8F7FF';
  ctx.textAlign = 'right';
  ctx.fillText(`${speed}`, cardX + cardW - 13, cardY + cardH / 2 + 0.5);
  ctx.font = '6.5px sans-serif';
  ctx.fillStyle = 'rgba(225, 247, 255, 0.72)';
  ctx.fillText('km/h', cardX + cardW - 4, cardY + cardH / 2 + 0.8);

  // 细锚点确保标记仍精确指向道路位置。
  ctx.fillStyle = themeColor;
  ctx.beginPath();
  ctx.moveTo(logicalWidth / 2 - 2.5, cardY + cardH);
  ctx.lineTo(logicalWidth / 2 + 2.5, cardY + cardH);
  ctx.lineTo(logicalWidth / 2, logicalHeight - 1);
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
      if (!viewer) return;
      if (!response.ok) return;
      cachedHubeiGeojson = await response.json();
      if (!viewer) return;
    }
    const geojson = cachedHubeiGeojson;
    if (!viewer) return;

    // 路网、车流及其标题统一置于湖北省发亮顶面之上，避免被悬浮地图遮挡。
    const highwaysSource = await Cesium.GeoJsonDataSource.load(geojson, {
      clampToGround: false
    });
    if (!viewer) return;
    
    // 路网改为低亮度蓝青，服务于车辆态势而非抢占注意力。
    const roadMaterial = new Cesium.ColorMaterialProperty(
      Cesium.Color.fromCssColorString('#57c7df').withAlpha(0.28)
    );

    const roadSurfaceHeight = 0;
    const now = Cesium.JulianDate.now();
    highwaysSource.entities.values.forEach(entity => {
      if (entity.polyline) {
        const positions = entity.polyline.positions?.getValue(now);
        if (positions?.length) {
          entity.polyline.positions = new Cesium.ConstantProperty(
            positions.map((position) => {
              const cartographic = Cesium.Cartographic.fromCartesian(position);
              return Cesium.Cartesian3.fromRadians(
                cartographic.longitude,
                cartographic.latitude,
                roadSurfaceHeight
              );
            })
          );
        }
        entity.polyline.clampToGround = true;
        entity.polyline.material = roadMaterial;
        entity.polyline.width = 0.8;
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

  lkywVehicles.value = [];
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

  const totalVehicles = Math.min(trafficConfig.vehicleCount, 40);
  
  // 优先应用 UI 设置的最小距离过滤
  let validRoutes = allRoutes.filter(r => r.totalDist >= trafficConfig.minDistance * 0.3);
  
  // 如果符合条件的路线太少，则降低阈值以保证全省有车（特别是保护十堰等山区短路段）
  if (validRoutes.length < totalVehicles) {
    validRoutes = allRoutes.filter(r => r.totalDist >= 3000);
    if (validRoutes.length < totalVehicles) validRoutes = allRoutes;
  }

  // 关键修复：按路线中心点的经度从西向东排序，确保全省东西跨度（最西边的十堰、恩施等）都能均匀覆盖
  validRoutes.sort((a, b) => {
    const ptA = a.coords[Math.floor(a.coords.length / 2)];
    const ptB = b.coords[Math.floor(b.coords.length / 2)];
    return ptA[0] - ptB[0];
  });

  // 均匀采样抽取线路，绝对保证地理分布的广泛性
  let candidateRoutes = [];
  const step = validRoutes.length / totalVehicles;
  for (let i = 0; i < totalVehicles; i++) {
    candidateRoutes.push(validRoutes[Math.floor(i * step)]);
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
      dotColor = MAP_VEHICLE_STYLES.hazard.color;
    } else if (category === 'passenger') {
      plate = passengerPlates[i % passengerPlates.length];
      cargo = passengerRoutes[i % passengerRoutes.length];
      speed = 85 + Math.floor(Math.random() * 12);
      dotColor = MAP_VEHICLE_STYLES.passenger.color;
    } else {
      plate = touristPlates[i % touristPlates.length];
      cargo = touristRoutes[i % touristRoutes.length];
      speed = 80 + Math.floor(Math.random() * 10);
      dotColor = MAP_VEHICLE_STYLES.tourist.color;
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
      // 紧凑标记避免遮挡省域卫星底图，近看仍可辨识车牌与速度。
      scale: 0.9,
      scaleByDistance: new Cesium.NearFarScalar(200000, 1.0, 2500000, 0.72),
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      heightReference: Cesium.HeightReference.NONE,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    });

    const point = lkywPointCollection.add({
      position: initialPos,
      color: Cesium.Color.fromCssColorString(dotColor),
      pixelSize: 5.0,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 1.0,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    });

    lkywVehicles.value.push({
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
  syncOverviewPointVisibility();
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

  // 背景车流降低过滤阈值，避免强行按长度截断导致山区(十堰)无背景车
  let candidateRoutes = allRoutes.filter(r => r.totalDist >= trafficConfig.minDistance * 0.2);
  if (candidateRoutes.length < 30) {
    candidateRoutes = allRoutes.filter(r => r.totalDist >= 3000);
    if (candidateRoutes.length < 30) candidateRoutes = allRoutes;
  }
  
  // 随机打乱背景候选路线，防止集中在某一区域，确保自然分布
  candidateRoutes.sort(() => Math.random() - 0.5);

  candidateRoutes.forEach((route, routeIndex) => {
    const vehicleCount = route.totalDist > 20000 ? 2 : 1;

    for (let k = 0; k < vehicleCount; k++) {
      const isReverse = (routeIndex + k) % 2 === 1;

      // 按演示比例分配类型，颜色统一由地图样式配置提供。
      const randCat = Math.random();
      let category = 'passenger';

      if (randCat < 0.22) {
        category = 'hazard';
      } else if (randCat < 0.70) {
        category = 'passenger';
      } else {
        category = 'tourist';
      }

      const dotColor = MAP_VEHICLE_STYLES[category].color;
      const initialColor = Cesium.Color.fromCssColorString(dotColor).withAlpha(0.95);
      const pixelSize = category === 'hazard' ? 5.5 : 4.5;

      const startDist = ((k / vehicleCount) * 0.8 + Math.random() * 0.2) * route.totalDist;
      const travelTime = 1.5 + Math.random() * 1.0;
      const speed = route.totalDist / travelTime;

      const initialPos = getPointAtDistance(route, startDist);
      if (!initialPos) continue;

      const pt = trafficPointCollection.add({
        position: initialPos,
        color: initialColor,
        pixelSize: pixelSize,
        outlineColor: Cesium.Color.fromCssColorString('#153746').withAlpha(0.85),
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
  syncOverviewPointVisibility();

  let lastTime = performance.now();
  let speedUpdateAccumulator = 0;
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

    if (lkywVehicles.value && lkywVehicles.value.length > 0) {
      for (let i = 0; i < lkywVehicles.value.length; i++) {
        const lv = lkywVehicles.value[i];
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

    // 🚚 实时同步追踪预警车辆的位置，使其小红点与标牌跟随运动
    if (trackedRiskVehicle && activeFocusedRiskEntity && activeFocusedRiskPoint) {
      const currentPos = trackedRiskVehicle.billboard.position;
      activeFocusedRiskEntity.position = currentPos;
      activeFocusedRiskPoint.position = currentPos;
    }

    // 随机浮动两客一危车辆时速显示，使孪生大屏更有动态感 (每隔 0.8 秒更新一次，仅在组件激活状态下更新 texture 防止 canvas 脱离 DOM 导致 TextureAtlas 损坏)
    speedUpdateAccumulator += dt;
    if (isComponentActive.value && !isOverviewTransition && speedUpdateAccumulator >= 0.8) {
      speedUpdateAccumulator = 0;
      if (lkywVehicles.value && lkywVehicles.value.length > 0) {
        lkywVehicles.value.forEach(lv => {
          const diff = Math.random() > 0.5 ? 1 : -1;
          lv.speed = Math.max(65, Math.min(115, lv.speed + diff));
          if (lv._displayedSpeed === lv.speed) return;
          lv._displayedSpeed = lv.speed;
          const newCanvas = createVehicleBillboardCanvas(lv.category, lv.plate, lv.speed);
          lv.billboard.image = newCanvas;
        });
      }
    }

    // ⚡ 强行接管并驱动所有无人机（包括货车现场与油罐车现场的各个编队）旋翼旋转动画。
    // 由于无人机使用 Date.now() 实时间隔来计算飞行轨道（确保暂停时也处于动画飞舞状态），
    // 我们的螺旋桨动画也必须独立于 Cesium 虚拟时钟（即使时钟暂停，螺旋桨也必须以真实时间轴持续高速旋转）。
    try {
      if (viewer && viewer.clock && viewer.clock.currentTime) {
        const allUavEntities = [...(uavEntities || []), ...(tankerUavEntities || [])];
        const realTimeSec = performance.now() / 1000.0;
        allUavEntities.forEach(entity => {
          if (entity && entity.show) {
            const p = primitiveCache.get(entity.id);
            if (p && p.activeAnimations && p.activeAnimations.length > 0) {
              const len = p.activeAnimations.length;
              for (let j = 0; j < len; j++) {
                const anim = p.activeAnimations.get(j);
                if (anim) {
                  const newTime = Cesium.JulianDate.addSeconds(
                    viewer.clock.currentTime,
                    -realTimeSec,
                    new Cesium.JulianDate()
                  );
                  // 优先修改私有属性 _startTime 绕过 Cesium 官方 API 对只读属性的严格写限制，防止在严格模式下抛出 TypeError
                  try {
                    if (typeof anim._startTime !== 'undefined') {
                      anim._startTime = newTime;
                    }
                  } catch (e) {}
                }
              }
            }
          }
        });
      }
    } catch (animErr) {
      // 异常捕获机制，保证即使发生意外异常也绝不卡死渲染线程和时间轴
      console.warn('[Cesium] UAV rotors animation error:', animErr);
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

  // 标记和车牌标题高于路网，确保始终显示在发亮地图的最上层。
  return Cesium.Cartesian3.fromDegrees(
    lng,
    lat,
    (props.focusedPointId && Number(props.activePhaseIndex) >= 1) ? 2 : ELECTRONIC_FENCE_ROOF_HEIGHT + 105
  );
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
  
  // 仿真初始车流 (0-1~0-4.glb) 在仿真开始节点 (phaseIndex === 0) 显示
  startStageVehicleEntities.forEach(entity => {
    entity.show = (isStorySceneFocused() && (currentScene.value === 'truck' || currentScene.value === 'tanker') && phaseIndex === 0)
  })

  // 保持模型在 WebGL 渲染管线中常驻（由 scale 动态控制可见性为 0 或 0.82），避免切阶段时 GPU 着色器重编译掉帧
  truckEntities.forEach(entity => { entity.show = true })

  if (targetModelId) {
    const entity = truckEntities.find(e => e.id === targetModelId)
    if (entity) {
      if (phaseIndex === 1) {
        // 阶段 1：正常行驶阶段，单次平稳播放正常行驶动画（只播一次并在终点定格，不循环）
        playEntityAnimation(entity, false, 0, 1.0)
      } else if (phaseIndex === 2) {
        // 阶段 2：事故发生瞬间，播放撞击追尾/破坏动画过程（只播一次并在最后定格）
        playEntityAnimation(entity, false, 0, 1.0)
      } else if (phaseIndex >= 3) {
        // 阶段 3 及之后（无人机出动、无人机侦察、次生灾害、无人感知等全部后续阶段）：
        // 事故已经发生完毕，两车必须定格在事故发生后的最后一帧（倒塌撞毁状态）
        freezeEntityAtEnd(entity)
      }
    }
  } else {
    // 阶段0（仿真开始）：停止所有货车模型的动画运算，释放 CPU
    truckEntities.forEach(entity => {
      const p = primitiveCache.get(entity.id) || findModelPrimitive(viewer.scene.primitives, entity)
      if (p && p.activeAnimations) {
        try { p.activeAnimations.removeAll() } catch (e) {}
      }
    })
  }
  
  currentActiveModelId = targetModelId
  lastPhaseIndex = phaseIndex

  const isTruckFocus = pointId === 'accident_blue' || props.focusedPointId === 'accident_blue';

  const isBigFire = (phaseIndex === 6);
  let smokeScaleBase = 1.0;
  let smokeEmissionRate = 35.0;

  if (isBigFire) {
    smokeScaleBase = 1.5;
    smokeEmissionRate = 40.0;
  } else if (phaseIndex >= 8) {
    smokeScaleBase = 0.35;
    smokeEmissionRate = 20.0;
  }

  const fireScaleBase = isBigFire ? 1.1 : 0.9;

  if (smokeParticle) {
    // 只有在聚焦该点且阶段 >= 5 时才显示（次生灾害烟雾/起火阶段）
    smokeParticle.show = isTruckFocus && (phaseIndex >= 5);
  }
  if (fireParticle) {
    // 只有在聚焦该点且阶段 >= 6 时才显示（次生灾害起火阶段）
    fireParticle.show = isTruckFocus && (phaseIndex >= 6);
    
    if (phaseIndex >= 8) {
      // 8 阶段及以后 (无人感知部署、感知执行等)：事故中后期火势自然减弱，使用微调参数
      fireParticle.startScale = lateFireAdjust.startScale * fireScaleBase;
      fireParticle.endScale = lateFireAdjust.endScale * fireScaleBase;
      fireParticle.emissionRate = lateFireAdjust.emissionRate; 
      fireParticle.imageSize = new Cesium.Cartesian2(lateFireAdjust.imageWidth, lateFireAdjust.imageHeight); 
      fireParticle.minimumSpeed = lateFireAdjust.minSpeed; 
      fireParticle.maximumSpeed = lateFireAdjust.maxSpeed;
      fireParticle.minimumParticleLife = lateFireAdjust.minLife;
      fireParticle.maximumParticleLife = lateFireAdjust.maxLife;
      fireParticle.updateCallback = (particle, dt) => {
        particle.velocity.z += (lateFireAdjust.gravity || 3.0) * dt;
        const dragFactor = Math.pow(lateFireAdjust.drag || 0.98, dt * 60);
        particle.velocity.x *= dragFactor;
        particle.velocity.y *= dragFactor;
        particle.velocity.z *= dragFactor;
      };
    } else {
      // 5, 6, 7 阶段 (起火爆发期)：精致跃动火舌（无 NaN 抖动闪烁）
      fireParticle.startScale = 0.3 * fireScaleBase;
      fireParticle.endScale = 1.0 * fireScaleBase;
      fireParticle.emissionRate = 32.0; 
      fireParticle.imageSize = new Cesium.Cartesian2(14, 14);
      fireParticle.minimumSpeed = 2.0;
      fireParticle.maximumSpeed = 4.5;
      fireParticle.minimumParticleLife = 0.6;
      fireParticle.maximumParticleLife = 1.4;
      fireParticle.updateCallback = (particle, dt) => {
        particle.velocity.z += 4.0 * dt;
      };
    }
  }
}

// 油罐车模型序列更新函数
function updateTankerSequence(phaseIndex, pointId = '') {
  if (!viewer) return
  
  const targetModelId = tankerPhaseToModelMap[phaseIndex] || null

  const isModelChanged = targetModelId !== currentActiveTankerModelId
  const isInitialSwitch = (phaseIndex <= 1 && lastTankerPhaseIndex <= 1 && phaseIndex !== lastTankerPhaseIndex)

  // 保持模型常驻
  tankerEntities.forEach(entity => { entity.show = true })

  if (targetModelId) {
    const entity = tankerEntities.find(e => e.id === targetModelId)
    if (entity) {
      if (phaseIndex === 1) {
        // 阶段 1：正常行驶阶段，单次平稳播放正常行驶动画（只播一次并在终点定格，不循环）
        playEntityAnimation(entity, false, 0, 1.0)
      } else if (phaseIndex === 2) {
        // 阶段 2：事故发生（侧翻）瞬间，播放侧翻动画过程（只播一次并在最后定格）
        playEntityAnimation(entity, false, 0, 1.0)
      } else if (phaseIndex >= 3) {
        // 阶段 3 及之后（无人机出动、无人机侦察、次生灾害泄露/弥漫等）：
        // 事故已发生完毕，油罐车必须定格在侧翻后的最后一帧状态
        freezeEntityAtEnd(entity)
      }
    }
  } else if (!targetModelId) {
    // 阶段0（仿真开始）：停止所有油罐车模型的动画运算
    tankerEntities.forEach(entity => {
      const p = primitiveCache.get(entity.id) || findModelPrimitive(viewer.scene.primitives, entity)
      if (p && p.activeAnimations) {
        try { p.activeAnimations.removeAll() } catch (e) {}
      }
    })
  }
  
  currentActiveTankerModelId = targetModelId
  lastTankerPhaseIndex = phaseIndex

  // 仿真初始车流 (0-1~0-4.glb) 在仿真开始节点 (phaseIndex === 0) 显示
  startStageVehicleEntities.forEach(entity => {
    entity.show = (isStorySceneFocused() && (currentScene.value === 'truck' || currentScene.value === 'tanker') && phaseIndex === 0)
  })

  // 全时段就绪：泄露与弥漫效果根据focusedPointId决定是否显示
  const isTankerFocus = pointId === 'accident_red' || props.focusedPointId === 'accident_red';

  if (leakParticle) {
    // 只有在聚焦该点且阶段 >= 5 时才显示（次生灾害泄露阶段）
    leakParticle.show = isTankerFocus && (phaseIndex >= 5);
    // 阶段5（泄露）开始产生
    leakParticle.emissionRate = (phaseIndex >= 5) ? 45.0 : 0.0; 
  }
  
  if (diffusionParticle) {
    // 只有在聚焦该点且阶段 >= 6 时才显示（次生灾害弥漫阶段）
    diffusionParticle.show = isTankerFocus && (phaseIndex >= 6);
    // 阶段5（弥漫）开始产生，阶段6（扩散）显著增强
    if (phaseIndex === 5) {
      diffusionParticle.emissionRate = 100.0; // 提升初始浓度
    } else if (phaseIndex >= 6) {
      diffusionParticle.emissionRate = 180.0; // 显著增强，提供大范围浓烈雾气效果
    } else {
      diffusionParticle.emissionRate = 0.0;
    }
  }
}

// 强制将模型动画定格在事故发生后的最后一帧（倒塌/侧翻/撞毁完成状态）
function freezeEntityAtEnd(entity) {
  if (!viewer || !entity) return;

  const tryFreeze = (attemptsLeft) => {
    if (attemptsLeft <= 0) return;

    try {
      let p = primitiveCache.get(entity.id);
      if (!p) {
        p = findModelPrimitive(viewer.scene.primitives, entity);
        if (!p) p = findModelPrimitive(viewer.scene.groundPrimitives, entity);
        if (p) primitiveCache.set(entity.id, p);
      }

      const isReady = p && (
        p.ready || 
        (p.readyPromise && p.readyPromise.state === 'fulfilled') || 
        p._ready || 
        (p.model && p.model.ready)
      );

      if (p && isReady && p.activeAnimations && typeof p.activeAnimations.addAll === 'function') {
        p.activeAnimations.removeAll();
        // 直接指定动画末帧，避免路线 CZML 切换时钟后回到初始位置。
        p.activeAnimations.animateWhilePaused = true;
        p.activeAnimations.addAll({
          loop: Cesium.ModelAnimationLoop.NONE,
          animationTime: () => 1.0,
          removeOnStop: false
        });
        p._playingLoopEntityId = null;
      } else {
        setTimeout(() => tryFreeze(attemptsLeft - 1), 200);
      }
    } catch (error) {
      console.warn('freezeEntityAtEnd warning:', error.message);
    }
  };

  tryFreeze(15);
}

function playEntityAnimation(entity, loop = false, duration = 0, speedMultiplier = 1.0) {
  if (!viewer || !entity) return;

  // 1. 彻底净化 Cesium 核心时钟基准：重置为独立、干净的当前绝对时间，
  // 坚决防止被 CZML 历史时间戳（2025年）或 190x 异常倍速污染导致的“1帧跳过/卡顿跳到终点”问题
  const cleanNow = Cesium.JulianDate.now();
  if (viewer.clock) {
    viewer.clock.currentTime = cleanNow;
    viewer.clock.startTime = cleanNow;
    viewer.clock.stopTime = Cesium.JulianDate.addDays(cleanNow, 1, new Cesium.JulianDate());
    viewer.clock.clockRange = Cesium.ClockRange.UNBOUNDED;
    viewer.clock.multiplier = 1.0;
    viewer.clock.shouldAnimate = true;
  }

  // 2. 释放同组非激活模型的动画计算，避免 90MB 双模型同时占用 CPU 进行骨骼蒙皮计算
  const allRelatedEntities = [...truckEntities, ...tankerEntities];
  allRelatedEntities.forEach(other => {
    if (other && other.id !== entity.id && !other.id.includes('uav')) {
      const otherP = primitiveCache.get(other.id) || findModelPrimitive(viewer.scene.primitives, other);
      if (otherP && otherP.activeAnimations && typeof otherP.activeAnimations.removeAll === 'function') {
        try {
          otherP.activeAnimations.removeAll();
        } catch (e) {}
      }
    }
  });

  const tryPlay = (attemptsLeft) => {
    if (attemptsLeft <= 0) {
      return;
    }

    try {
      let p = primitiveCache.get(entity.id);
      if (!p) {
        p = findModelPrimitive(viewer.scene.primitives, entity);
        if (!p) p = findModelPrimitive(viewer.scene.groundPrimitives, entity);
        if (p) primitiveCache.set(entity.id, p);
      }

      // 检查模型是否完全加载就绪
      const isReady = p && (
        p.ready || 
        (p.readyPromise && p.readyPromise.state === 'fulfilled') || 
        p._ready || 
        (p.model && p.model.ready)
      );

      if (p && isReady && p.activeAnimations && typeof p.activeAnimations.addAll === 'function') {
        try {
          p.activeAnimations.removeAll();
          
          // 获取当前时钟精确起始时间
          const startJulian = Cesium.JulianDate.clone(viewer.clock.currentTime);

          const options = {
            loop: loop ? Cesium.ModelAnimationLoop.REPEAT : Cesium.ModelAnimationLoop.NONE,
            multiplier: speedMultiplier || 1.0,
            startTime: startJulian,
            removeOnStop: false // 停止时保留在最后一帧状态
          };
          
          // 调用 addAll 强制激活模型内所有的 animation tracks
          const addedAnims = p.activeAnimations.addAll(options);
          p._playingLoopEntityId = entity.id;
          
          // 仅在非循环且指定了明确时长时才按 duration 动态截断/调速
          if (!loop && duration > 0 && addedAnims && addedAnims.length > 0) {
            addedAnims.forEach(anim => {
              if (anim.startTime && anim.stopTime) {
                const nativeDuration = Cesium.JulianDate.secondsDifference(anim.stopTime, anim.startTime);
                if (nativeDuration > 0) {
                  anim.multiplier = (nativeDuration / duration) * (speedMultiplier || 1.0);
                  anim.stopTime = Cesium.JulianDate.addSeconds(anim.startTime, duration, new Cesium.JulianDate());
                }
              }
            });
          }
        } catch (animError) {
          console.warn('播放动画时出现警告:', animError.message);
        }
      } else {
        // 如果未找到或未就绪，等待 100ms 后重试
        setTimeout(() => tryPlay(attemptsLeft - 1), 100);
      }
    } catch (error) {
      console.warn('查找实体时出现警告:', error.message);
    }
  };

  // 启动轮询检查，最多重试 15 次
  tryPlay(15);
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

  // 接入 6 个 light.glb 3D灯光模型及相关链路/视场
 lights.forEach((l) => {
    // 🚨 动态判断核心：依靠经度物理隔离两个场景（彻底解决重名 ID 问题）
    // 请确保 114.0 是你用来划分两个场景的正确经度！
    const isTruckLight = Number(l.lng) < 114.0;
    const isTankerLight = !isTruckLight;
    
    // =====================================
    // 1. 添加感知视场 (排除了 light6 自带路灯)
    // =====================================
    if (['light1', 'light2', 'light3', 'light4', 'light5', 'light8', 'light23', 'light24'].includes(l.id)) {
      const heightOffset = 8.0;
      const pitchAngle = -45;

      let headingOffset = 0;
      let fovAngle = 22;
      let maxRange = 100;

      // 根据 ID 匹配视场参数（参数不用改，因为是按需微调的）
      if (l.id === 'light1') { headingOffset = 0; fovAngle = 35; maxRange = 250; }
      if (l.id === 'light2') { headingOffset = 0; fovAngle = 35; maxRange = 250; }
      if (l.id === 'light3') { headingOffset = 180; fovAngle = 35; maxRange = 250; }
      if (l.id === 'light8') { headingOffset = 0; fovAngle = 35; maxRange = 250; }
      if (l.id === 'light23') { headingOffset = -45; fovAngle = 35; maxRange = 250; }
      if (l.id === 'light24') { headingOffset = -225; fovAngle = 35; maxRange = 250; }
      if (l.id === 'light4') { headingOffset = -25; fovAngle = 30; maxRange = 300; }
      if (l.id === 'light5') { headingOffset = 165; fovAngle = 30; maxRange = 150; }

      // 为 FOV 生成唯一的场景前缀 ID，防止两个场景都有 light1 导致覆盖
      const fovId = isTruckLight ? `truck-${l.id}-fov` : `tanker-${l.id}-fov`;

      createLightFOV(
        viewer, fovId,
        Number(l.lng), Number(l.lat), Number(l.height) + heightOffset,
        Number(l.heading) + headingOffset, pitchAngle, fovAngle, maxRange,
        () => {
          // 只在对应的场景、阶段大于2、且完成两步解锁后显示
          const isCurrentScene = isTruckLight ? (currentScene.value === 'truck') : (currentScene.value === 'tanker');
          // 两个视频故事点的感知圈只在第三视角近距离显示，避免首页/中视角留下蓝色同心圆。
          if (l.id === 'light1') return Number(props.activePhaseIndex) >= 2 && isCurrentScene && isLight1CameraUnlocked() && accidentViewLevel.value === 'close';
          if (l.id === 'light23') return Number(props.activePhaseIndex) >= 2 && isCurrentScene && isLight23CameraUnlocked() && accidentViewLevel.value === 'close';
          return Number(props.activePhaseIndex) >= 2 && isCurrentScene;
        }
      );
    }

    // =====================================
    // 2. 加载路灯 3D 模型
    // =====================================
    if (l.id === 'light6') return;

    // 模型 ID 也加上场景前缀，彻底解决 Cesium 的 Entity ID 冲突问题
    const modelEntityId = isTruckLight ? `truck-${l.id}-glb-entity` : `tanker-${l.id}-glb-entity`;

    viewer.entities.add({
      id: modelEntityId,
      name: `事故现场灯光模型-${l.id}`,
      show: new Cesium.CallbackProperty(() => {
        const isCurrentScene = isTruckLight ? (currentScene.value === 'truck') : (currentScene.value === 'tanker');
        if (!isCurrentScene || !l.show) return false;
        if (l.id === 'light1') return isLight1CameraUnlocked() && accidentViewLevel.value === 'close';
        if (l.id === 'light23') return isLight23CameraUnlocked() && accidentViewLevel.value === 'close';
        return true;
      }, false),
      position: new Cesium.CallbackProperty(() => Cesium.Cartesian3.fromDegrees(Number(l.lng), Number(l.lat), Number(l.height)), false),
      orientation: new Cesium.CallbackProperty(() => {
        const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(l.heading)), Cesium.Math.toRadians(Number(l.pitch)), Cesium.Math.toRadians(Number(l.roll)));
        return Cesium.Transforms.headingPitchRollQuaternion(Cesium.Cartesian3.fromDegrees(Number(l.lng), Number(l.lat), Number(l.height)), hpr);
      }, false),
      model: {
        uri: '/Dashboard/models/light.glb',
        scale: new Cesium.CallbackProperty(() => l.scale, false),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        silhouetteColor: new Cesium.CallbackProperty(() => {
          if (l.id === 'light1' && currentScene.value === 'truck' && isLight1CameraUnlocked()) {
            return Cesium.Color.fromCssColorString('#38bdf8');
          }
          if (l.id === 'light23' && currentScene.value === 'tanker' && isLight23CameraUnlocked()) {
            return Cesium.Color.fromCssColorString('#38bdf8');
          }
          return undefined;
        }, false),
        silhouetteSize: new Cesium.CallbackProperty(() => {
          if (l.id === 'light1' && currentScene.value === 'truck' && isLight1CameraUnlocked()) {
            return 3.0;
          }
          if (l.id === 'light23' && currentScene.value === 'tanker' && isLight23CameraUnlocked()) {
            return 3.0;
          }
          return 0.0;
        }, false)
      }
    });

    // =====================================
    // 3. 路灯到对应基站的通信链路
    // =====================================
    if (['light1', 'light2', 'light3', 'light4', 'light5', 'light8', 'light23', 'light24'].includes(l.id)) {
      
      // 线条 ID 加上场景前缀
      const lineId = isTruckLight ? `line-link-from-truck-${l.id}-to-jizhan` : `line-link-from-tanker-${l.id}-to-jizhan`;

      viewer.entities.add({
        id: lineId, 
        name: `数据传输链路:${l.id}->动态核心节点`,
        show: new Cesium.CallbackProperty(() => {
          // 💡 严格判断阵营与场景
          if (isTruckLight) return currentScene.value === 'truck' && l.show;
          if (isTankerLight) return currentScene.value === 'tanker' && l.show;
          return false;
        }, false),
        polyline: {
          positions: new Cesium.CallbackProperty((time) => {
            // 🚨 最强防御墙：货车的灯在油罐车场景绝对不画，油罐车的灯在货车场景绝对不画！
            if (isTruckLight && currentScene.value !== 'truck') return [];
            if (isTankerLight && currentScene.value !== 'tanker') return [];

            const lightTop = getModelTopPosition(l.lng, l.lat, l.height, l.heading, l.pitch, l.roll, LIGHT_TOP_OFFSET);

            const phase = Number(props.activePhaseIndex);

            // 🚨 故事点十 (阶段 10)：信号干扰，基站断联，链路物理转移至各自场景的 1 号无人车
            if (phase >= 10) {
              const targetUgv = isTruckLight ? rescueCarEntities[0] : tankerRescueCarEntities[0];
              if (targetUgv) {
                const ugvPos = targetUgv.position.getValue(time);
                if (ugvPos) return [lightTop, ugvPos];
              }
              return []; // 找不到无人车则返回空（不绘制）
            }

            // 🌟 常规阶段 (阶段 0 到 8)：正常连向各自专属的 5G 基站
            const targetJizhan = isTruckLight ? jizhanAdjust : tankerJizhanAdjust;
            if (!targetJizhan || !targetJizhan.show) return []; // 常规阶段如果基站没出来，就不连线
            
            const jizhanTop = getModelTopPosition(
              targetJizhan.lng, targetJizhan.lat, targetJizhan.height, 
              targetJizhan.heading, targetJizhan.pitch, targetJizhan.roll, JIZHAN_TOP_OFFSET
            );
            return [lightTop, jizhanTop];
          }, false),
          width: 3.0,
          arcType: Cesium.ArcType.NONE, 
          material: new DynamicFlowMaterialProperty({ color: Cesium.Color.CYAN, speed: 3.5, repeat: 8.0 })
        }
      });
    }
  });
  const light1 = lights.find((item) => item.id === 'light1')
  if (light1) {
    viewer.entities.add({
      id: 'light1-camera-marker',
      name: '前方路侧摄像头可点击标记',
      show: new Cesium.CallbackProperty(() => {
        // 视频故事点只在货车事故现场的第三视角（近距离）开放，避免首页总览出现无关标记。
        return currentScene.value === 'truck' && light1.show && isLight1CameraUnlocked() && accidentViewLevel.value === 'close'
      }, false),
      position: new Cesium.CallbackProperty(() => {
        return Cesium.Cartesian3.fromDegrees(Number(light1.lng), Number(light1.lat), Number(light1.height) + 16)
      }, false),
      point: {
        pixelSize: 18,
        color: Cesium.Color.fromCssColorString('#38bdf8').withAlpha(0.92),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: '',
        font: '13px sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        showBackground: true,
        backgroundColor: new Cesium.Color(0.02, 0.08, 0.18, 0.8),
        backgroundPadding: new Cesium.Cartesian2(6, 4),
        pixelOffset: new Cesium.Cartesian2(-45, -28),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
  }

  const light23 = lights.find((item) => item.id === 'light23')
  if (light23) {
    viewer.entities.add({
      id: 'light23-camera-marker',
      name: '前方路侧摄像头可点击标记',
      show: new Cesium.CallbackProperty(() => {
        // 视频故事点只在油罐车事故现场的第三视角（近距离）开放，避免首页总览出现无关标记。
        return currentScene.value === 'tanker' && light23.show && isLight23CameraUnlocked() && accidentViewLevel.value === 'close'
      }, false),
      position: new Cesium.CallbackProperty(() => {
        return Cesium.Cartesian3.fromDegrees(Number(light23.lng), Number(light23.lat), Number(light23.height) + 16)
      }, false),
      point: {
        pixelSize: 18,
        color: Cesium.Color.fromCssColorString('#38bdf8').withAlpha(0.92),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: '',
        font: '13px sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        showBackground: true,
        backgroundColor: new Cesium.Color(0.02, 0.08, 0.18, 0.8),
        backgroundPadding: new Cesium.Cartesian2(6, 4),
        pixelOffset: new Cesium.Cartesian2(-45, -28),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
  }

  // 📡 接入 jizhan.glb 3D 5G通信基站模型 (货车追尾事故现场)
  viewer.entities.add({
    id: 'jizhan-glb-entity',
    name: '客车追尾现场5G通信基站模型',
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
  viewer.entities.add({
    id: 'tanker-jizhan-glb-entity',
    name: '油罐车现场5G通信基站模型',
    show: new Cesium.CallbackProperty(() => {
      return currentScene.value === 'tanker' && tankerJizhanAdjust.show;
    }, false),
    position: new Cesium.CallbackProperty(() => {
      return Cesium.Cartesian3.fromDegrees(Number(tankerJizhanAdjust.lng), Number(tankerJizhanAdjust.lat), Number(tankerJizhanAdjust.height));
    }, false),
    orientation: new Cesium.CallbackProperty(() => {
      const position = Cesium.Cartesian3.fromDegrees(Number(tankerJizhanAdjust.lng), Number(tankerJizhanAdjust.lat), Number(tankerJizhanAdjust.height));
      const hpr = new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(Number(tankerJizhanAdjust.heading)), Cesium.Math.toRadians(Number(tankerJizhanAdjust.pitch)), Cesium.Math.toRadians(Number(tankerJizhanAdjust.roll)));
      return Cesium.Transforms.headingPitchRollQuaternion(position, hpr);
    }, false),
    model: { uri: '/Dashboard/models/jizhan.glb', scale: new Cesium.CallbackProperty(() => tankerJizhanAdjust.scale, false), heightReference: Cesium.HeightReference.CLAMP_TO_GROUND }
  });

  // 🗺️ 无人机绕飞盘旋轨迹 (货车追尾场景)
  viewer.entities.add({
    id: 'uav-orbit-path-truck',
    name: '货车场景无人机盘旋轨迹',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        let centerLng = Number(truckAdjust.lng) || 113.104833;
        let centerLat = Number(truckAdjust.lat) || 30.385469;
        let centerHeight = Number(uavAdjust.height) || 18.5;

        if (currentMissionDataSource) {
          const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
          if (pathEntity && pathEntity.polyline && pathEntity.polyline.positions) {
            const positions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                              pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
            if (positions && positions.length > 0) {
              const pEnd = positions[positions.length - 1];
              const cartoEnd = Cesium.Cartographic.fromCartesian(pEnd);
              centerLng = Cesium.Math.toDegrees(cartoEnd.longitude);
              centerLat = Cesium.Math.toDegrees(cartoEnd.latitude);
              centerHeight = cartoEnd.height;
            }
          }
        }

        const pts = [];
        for (let i = 0; i <= 72; i++) {
          const angle = (i / 72) * 2.0 * Math.PI;
          const lng = centerLng + 0.00055 * Math.cos(angle);
          const lat = centerLat + 0.00045 * Math.sin(angle);
          pts.push(Cesium.Cartesian3.fromDegrees(lng, lat, centerHeight));
        }
        return pts;
      }, false),
      width: 3.0,
      material: new Cesium.PolylineDashMaterialProperty({
        color: Cesium.Color.fromCssColorString('#00f2fe'),
        dashLength: 16.0
      })
    }
  });

  // 🗺️ 无人机绕飞盘旋轨迹 (油罐车泄漏场景)
  viewer.entities.add({
    id: 'uav-orbit-path-tanker',
    name: '油罐车场景无人机盘旋轨迹',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        let centerLng = Number(tankerPointAdjust.lng) || 114.89209;
        let centerLat = Number(tankerPointAdjust.lat) || 30.63101;
        let centerHeight = Number(tankerUavAdjust.height) || 120.0;

        if (currentMissionDataSource) {
          const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
          if (pathEntity && pathEntity.polyline && pathEntity.polyline.positions) {
            const positions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                              pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
            if (positions && positions.length > 0) {
              const pEnd = positions[positions.length - 1];
              const cartoEnd = Cesium.Cartographic.fromCartesian(pEnd);
              centerLng = Cesium.Math.toDegrees(cartoEnd.longitude);
              centerLat = Cesium.Math.toDegrees(cartoEnd.latitude);
              centerHeight = cartoEnd.height;
            }
          }
        }

        const pts = [];
        for (let i = 0; i <= 72; i++) {
          const angle = (i / 72) * 2.0 * Math.PI;
          const lng = centerLng + 0.0005 * Math.cos(angle);
          const lat = centerLat + 0.0005 * Math.sin(angle);
          pts.push(Cesium.Cartesian3.fromDegrees(lng, lat, centerHeight));
        }
        return pts;
      }, false),
      width: 3.0,
      material: new Cesium.PolylineDashMaterialProperty({
        color: Cesium.Color.fromCssColorString('#00f2fe'),
        dashLength: 16.0
      })
    }
  });

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
        const pos = popupEntity.position.getValue(getQueryTime())
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

    // 事故点告警图标：绑定两个场景的经纬度，省域总览中直观提示待处置事件。
    viewer.entities.add({
      id: `alert-marker-${point.id}`,
      name: `${point.label}告警`,
      position: positionCallback,
      billboard: {
        show: new Cesium.CallbackProperty(() => !props.focusedPointId, false),
        image: '/Dashboard/images/accident-alert-beacon.png',
        // 总览视角下需要更醒目：两个事故告警点放大，并保留呼吸式提示。
        scale: new Cesium.CallbackProperty(() => 0.9 + Math.sin(Date.now() / 360) * 0.09, false),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, 8),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scaleByDistance: new Cesium.NearFarScalar(120000, 1.08, 1800000, 0.72),
        translucencyByDistance: new Cesium.NearFarScalar(1600000, 1.0, 3000000, 0.72)
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
          if (config.id === targetModelId) return truckAdjust.scale
          return 0.0
        }, false),
        minimumPixelSize: new Cesium.CallbackProperty(() => {
          const targetModelId = phaseToModelMap[props.activePhaseIndex]
          return config.id === targetModelId ? 1 : 0
        }, false),
        heightReference: Cesium.HeightReference.NONE,
        // 关闭原生动画循环，交由 updateTruckSequence 和 playEntityAnimation 手动控制只播一次并定格
        runAnimations: false,
        silhouetteColor: Cesium.Color.fromCssColorString('#00f2fe'),
        silhouetteSize: new Cesium.CallbackProperty(() => {
          const targetModelId = phaseToModelMap[props.activePhaseIndex]
          return config.id === targetModelId ? 2.0 : 0.0
        }, false)
      }
    })
    entity.show = true // 保持常驻 WebGL 缓存，避免动态切换时的着色器重编译丢帧
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
          return 0.0
        }, false),
        minimumPixelSize: new Cesium.CallbackProperty(() => {
          const targetModelId = tankerPhaseToModelMap[props.activePhaseIndex]
          return config.id === targetModelId ? 1 : 0
        }, false),
        heightReference: Cesium.HeightReference.NONE,
        // 关闭原生动画循环，手动控制
        runAnimations: false,
        silhouetteColor: Cesium.Color.fromCssColorString('#ffea00'),
        silhouetteSize: new Cesium.CallbackProperty(() => {
          const targetModelId = tankerPhaseToModelMap[props.activePhaseIndex]
          return config.id === targetModelId ? 2.0 : 0.0
        }, false)
      }
    })
    entity.show = true
    tankerEntities.push(entity)
  })

  // 初始化 0-1.glb, 0-2.glb, 0-3.glb, 0-4.glb 仿真初始节点贴地行驶车辆
  startStageVehicleConfigs.forEach((config, index) => {
    const entity = viewer.entities.add({
      id: config.id,
      name: config.label,
      show: new Cesium.CallbackProperty(() => {
        // 仅进入事故故事线后，仿真开始节点车辆才显示并贴地行驶
        return isStorySceneFocused() && (currentScene.value === 'truck' || currentScene.value === 'tanker') && props.activePhaseIndex === 0
      }, false),
      position: new Cesium.CallbackProperty(() => {
        return getStartStageVehiclePosAndOrient(index, config.delayRatio).position
      }, false),
      orientation: new Cesium.CallbackProperty(() => {
        return getStartStageVehiclePosAndOrient(index, config.delayRatio).orientation
      }, false),
      model: {
        uri: config.uri,
        scale: new Cesium.CallbackProperty(() => {
          // 仅进入事故故事线且处于仿真开始节点时渲染几何大小
          if (!isStorySceneFocused() || (currentScene.value !== 'truck' && currentScene.value !== 'tanker') || props.activePhaseIndex !== 0) {
            return 0;
          }
          const carsArr = activeCars.value
          const carParam = (carsArr && carsArr[index])
            ? carsArr[index]
            : { scale: 1.0 }
          return carParam.scale || 1.0
        }, false),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, // 使用 Cesium 原生贴地
        silhouetteColor: Cesium.Color.fromCssColorString('#00f2fe'),
        silhouetteSize: 1.0
      }
    })
    startStageVehicleEntities.push(entity)
  })

  // 🛣️ 初始化 0-1~0-4 初始车流沥青公路轨迹线段 (Polyline) 及 P1 ~ P8 航点标记 Entities
  viewer.entities.add({
    id: 'start_stage_road_polyline',
    name: '初始车流沥青公路轨迹线',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const positions = []
        for (let i = 0; i <= 100; i++) {
          const pt = getCatmullRomSplinePoint(startStageRoadWaypoints, i / 100.0)
          positions.push(Cesium.Cartesian3.fromDegrees(pt.lng, pt.lat, 0.5))
        }
        return positions
      }, false),
      width: 4,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.25,
        taperPower: 1.0,
        color: Cesium.Color.fromCssColorString('#00f2fe')
      }),
      clampToGround: true
    }
  })

  // 为 P1 ~ P8 8个航点添加 3D 地球 Entity 标注 (Point + Label)
  for (let i = 0; i < 8; i++) {
    viewer.entities.add({
      id: `start_stage_road_waypoint_p${i + 1}`,
      name: `航点 P${i + 1}`,
      show: false,
      position: new Cesium.CallbackProperty(() => {
        const pt = startStageRoadWaypoints[i]
        if (!pt) return Cesium.Cartesian3.fromDegrees(113.104870, 30.385469, 1.0)
        return Cesium.Cartesian3.fromDegrees(pt[0], pt[1], 1.0)
      }, false),
      point: {
        pixelSize: new Cesium.CallbackProperty(() => {
          return startStageVehicleAdjust.selectedWaypointIndex === i ? 14 : 10
        }, false),
        color: new Cesium.CallbackProperty(() => {
          return startStageVehicleAdjust.selectedWaypointIndex === i 
            ? Cesium.Color.YELLOW 
            : Cesium.Color.fromCssColorString('#00f2fe')
        }, false),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: `P${i + 1}`,
        font: 'bold 15px sans-serif',
        fillColor: new Cesium.CallbackProperty(() => {
          return startStageVehicleAdjust.selectedWaypointIndex === i 
            ? Cesium.Color.YELLOW 
            : Cesium.Color.WHITE
        }, false),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -20),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
  }

  // 🛣️ 油罐车路线1 (Polyline)
  viewer.entities.add({
    id: 'tanker_route1_polyline',
    name: '油罐车路线1轨迹线',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const positions = []
        for (let i = 0; i <= 100; i++) {
          const pt = getCatmullRomSplinePoint(tankerRoute1Waypoints, i / 100.0)
          positions.push(Cesium.Cartesian3.fromDegrees(pt.lng, pt.lat, 0.5))
        }
        return positions
      }, false),
      width: 4,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.25,
        taperPower: 1.0,
        color: Cesium.Color.fromCssColorString('#00f2fe')
      }),
      clampToGround: true
    }
  })

  // 🛣️ 油罐车路线2 (Polyline)
  viewer.entities.add({
    id: 'tanker_route2_polyline',
    name: '油罐车路线2轨迹线',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const positions = []
        for (let i = 0; i <= 100; i++) {
          const pt = getCatmullRomSplinePoint(tankerRoute2Waypoints, i / 100.0)
          positions.push(Cesium.Cartesian3.fromDegrees(pt.lng, pt.lat, 0.5))
        }
        return positions
      }, false),
      width: 4,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.25,
        taperPower: 1.0,
        color: Cesium.Color.fromCssColorString('#ff6464')
      }),
      clampToGround: true
    }
  })

  // 油罐车路线1 航点 Markers (P1~P5)
  for (let i = 0; i < 5; i++) {
    viewer.entities.add({
      id: `tanker_route1_waypoint_p${i + 1}`,
      name: `路线1 航点 P${i + 1}`,
      show: false,
      position: new Cesium.CallbackProperty(() => {
        const pt = tankerRoute1Waypoints[i]
        if (!pt) return Cesium.Cartesian3.fromDegrees(114.894472, 30.632203, 1.0)
        return Cesium.Cartesian3.fromDegrees(pt[0], pt[1], 1.0)
      }, false),
      point: {
        pixelSize: new Cesium.CallbackProperty(() => {
          return (startStageVehicleAdjust.selectedTankerRouteIndex === 0 && startStageVehicleAdjust.selectedWaypointIndex === i) ? 14 : 10
        }, false),
        color: new Cesium.CallbackProperty(() => {
          return (startStageVehicleAdjust.selectedTankerRouteIndex === 0 && startStageVehicleAdjust.selectedWaypointIndex === i)
            ? Cesium.Color.YELLOW 
            : Cesium.Color.fromCssColorString('#00f2fe')
        }, false),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: `R1-P${i + 1}`,
        font: 'bold 14px sans-serif',
        fillColor: new Cesium.CallbackProperty(() => {
          return (startStageVehicleAdjust.selectedTankerRouteIndex === 0 && startStageVehicleAdjust.selectedWaypointIndex === i)
            ? Cesium.Color.YELLOW 
            : Cesium.Color.WHITE
        }, false),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -20),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
  }

  // 油罐车路线2 航点 Markers (P1~P5)
  for (let i = 0; i < 5; i++) {
    viewer.entities.add({
      id: `tanker_route2_waypoint_p${i + 1}`,
      name: `路线2 航点 P${i + 1}`,
      show: false,
      position: new Cesium.CallbackProperty(() => {
        const pt = tankerRoute2Waypoints[i]
        if (!pt) return Cesium.Cartesian3.fromDegrees(114.894472, 30.632203, 1.0)
        return Cesium.Cartesian3.fromDegrees(pt[0], pt[1], 1.0)
      }, false),
      point: {
        pixelSize: new Cesium.CallbackProperty(() => {
          return (startStageVehicleAdjust.selectedTankerRouteIndex === 1 && startStageVehicleAdjust.selectedWaypointIndex === i) ? 14 : 10
        }, false),
        color: new Cesium.CallbackProperty(() => {
          return (startStageVehicleAdjust.selectedTankerRouteIndex === 1 && startStageVehicleAdjust.selectedWaypointIndex === i)
            ? Cesium.Color.YELLOW 
            : Cesium.Color.fromCssColorString('#ff6464')
        }, false),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: `R2-P${i + 1}`,
        font: 'bold 14px sans-serif',
        fillColor: new Cesium.CallbackProperty(() => {
          return (startStageVehicleAdjust.selectedTankerRouteIndex === 1 && startStageVehicleAdjust.selectedWaypointIndex === i)
            ? Cesium.Color.YELLOW 
            : Cesium.Color.WHITE
        }, false),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -20),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
  }

  // 初始化无人机模型（用于货车追尾现场的无人装备出动阶段）
  // 初始化无人机模型（用于货车追尾现场的无人装备出动阶段）
  uavModelConfigs.forEach((config) => {
    console.log(`[Cesium] 正在初始化无人机实体: ${config.id}, 路径: ${config.uri}`);

    const uavPosition = new Cesium.CallbackProperty(() => {
      if (lastUavPhaseIndex !== props.activePhaseIndex) {
        phase3StartTime = 0;
        phase4StartTime = 0;
        phase6StartTime = 0;
        phase7StartTime = 0;
        phase8StartTime = 0;
        uavOrbitStartTime = 0;
        lastUavPhaseIndex = props.activePhaseIndex;
      }
      const startLng = Number(uavAdjust.lng) || 113.202;
      const startLat = Number(uavAdjust.lat) || 30.3268;
      const startHeight = Number(uavAdjust.height) || 18.5;

      const targetLng = (Number(truckAdjust.lng) || 113.104833) + (config.lonOffset || 0);
      const targetLat = (Number(truckAdjust.lat) || 30.385469) + (config.latOffset || 0);
      const targetHeight = startHeight; 

      let circleCenterLng = targetLng;
      let circleCenterLat = targetLat;
      let circleCenterHeight = startHeight;

      if (currentMissionDataSource) {
        const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
        if (pathEntity && pathEntity.polyline && pathEntity.polyline.positions) {
          const positions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                            pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
          if (positions && positions.length > 0) {
            const pEnd = positions[positions.length - 1];
            const cartoEnd = Cesium.Cartographic.fromCartesian(pEnd);
            circleCenterLng = Cesium.Math.toDegrees(cartoEnd.longitude);
            circleCenterLat = Cesium.Math.toDegrees(cartoEnd.latitude);
            circleCenterHeight = cartoEnd.height;
          }
        }
      }

      if (props.activePhaseIndex === 4) {
        // 阶段 4（无人机侦察）：从距离事故点 200m 处飞行向事故点
        if (!currentMissionDataSource) {
          return Cesium.Cartesian3.fromDegrees(targetLng, targetLat, startHeight);
        }
        const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
        if (!pathEntity || !pathEntity.polyline || !pathEntity.polyline.positions) {
          return Cesium.Cartesian3.fromDegrees(targetLng, targetLat, startHeight);
        }
        const rawPositions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                          pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
        if (!rawPositions || rawPositions.length <= 1) {
          return Cesium.Cartesian3.fromDegrees(targetLng, targetLat, startHeight);
        }

        if (!phase4StartTime) {
          phase4StartTime = Date.now();
        }
        const elapsed = Date.now() - phase4StartTime;
        const duration = 8000;
        
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        let positions = rawPositions;
        const pEnd = positions[positions.length - 1];
        let startIndex = 0;
        const targetDistance = 200.0;
        for (let i = positions.length - 2; i >= 0; i--) {
          const dist = Cesium.Cartesian3.distance(positions[i], pEnd);
          if (dist >= targetDistance) {
            startIndex = i;
            break;
          }
        }
        const subPositions = positions.slice(startIndex);
        if (subPositions.length > 1) {
          const pos = getPositionAtRatio(subPositions, easeT);
          if (pos) return pos;
        }
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);

      } else if (props.activePhaseIndex === 5 || props.activePhaseIndex === 6) {
        // 阶段 5 (次生灾害烟雾) 与 阶段 6 (次生灾害起火)：单架无人机围绕事故点做圆周绕飞旋转
        if (!uavOrbitStartTime) { uavOrbitStartTime = Date.now(); }
        const elapsed = Date.now() - uavOrbitStartTime;
        const period = 12000; // 12秒一圈
        const angle = (elapsed / period) * 2.0 * Math.PI;
        
        const radiusLng = 0.00055;
        const radiusLat = 0.00045;
        const centerLng = (Number(truckAdjust.lng) || 113.104833);
        const centerLat = (Number(truckAdjust.lat) || 30.385469);
        const centerHeight = 100.0;

        const currentLng = centerLng + radiusLng * Math.cos(angle);
        const currentLat = centerLat + radiusLat * Math.sin(angle);

        return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, centerHeight);

      } else if (props.activePhaseIndex === 3 || props.activePhaseIndex === 7) {
        // 阶段 3（无人机出动）或阶段 7（无人装备出动）：无人机从基地出发，运动到距离事故点 200 米处停下
        if (!currentMissionDataSource) {
          return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
        }
        const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
        if (!pathEntity || !pathEntity.polyline || !pathEntity.polyline.positions) {
          return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
        }
        const rawPositions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                          pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
        if (!rawPositions || rawPositions.length <= 1) {
          return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
        }

        const isPhase3 = props.activePhaseIndex === 3;
        if (isPhase3 && !phase3StartTime) {
          phase3StartTime = Date.now();
        } else if (!isPhase3 && !phase7StartTime) {
          phase7StartTime = Date.now();
        }

        const elapsed = Date.now() - (isPhase3 ? phase3StartTime : phase7StartTime);
        const duration = agentSpeedConfig.uavDuration * 1000;
        
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        const pEnd = rawPositions[rawPositions.length - 1];
        let startIndex = 0;
        const targetDistance = 200.0;
        for (let i = rawPositions.length - 2; i >= 0; i--) {
          const dist = Cesium.Cartesian3.distance(rawPositions[i], pEnd);
          if (dist >= targetDistance) {
            startIndex = i;
            break;
          }
        }
        const activePositions = rawPositions.slice(0, startIndex + 1);
        if (activePositions.length > 1) {
          const pos = getPositionAtRatio(activePositions, easeT);
          if (pos) return pos;
        }
        return activePositions[activePositions.length - 1] || Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);

      } else if (props.activePhaseIndex < 3) {
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else if (props.activePhaseIndex === 8) {
        // 阶段 8（无人感知部署）：无人机从距离事故点 200 米处平滑运动向事故点
        if (!phase8StartTime) { phase8StartTime = Date.now(); }
        const elapsed = Date.now() - phase8StartTime;
        const duration = 6000; 
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        if (currentMissionDataSource) {
          const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
          if (pathEntity && pathEntity.polyline && pathEntity.polyline.positions) {
            const rawPositions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                              pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
            if (rawPositions && rawPositions.length > 1) {
              const pEnd = rawPositions[rawPositions.length - 1];
              let startIndex = 0;
              const targetDistance = 200.0;
              for (let i = rawPositions.length - 2; i >= 0; i--) {
                const dist = Cesium.Cartesian3.distance(rawPositions[i], pEnd);
                if (dist >= targetDistance) {
                  startIndex = i;
                  break;
                }
              }
              const subPositions = rawPositions.slice(startIndex);
              if (subPositions.length > 1) {
                const pos = getPositionAtRatio(subPositions, easeT);
                if (pos) return pos;
              }
            }
          }
        }
        return Cesium.Cartesian3.fromDegrees(startLng, startLat, startHeight);
      } else {
        // 阶段 >= 9：无人机围绕事故点做圆周绕飞拍照
        if (!uavOrbitStartTime) { uavOrbitStartTime = Date.now(); }
        const elapsed = Date.now() - uavOrbitStartTime;
        const period = 12000; 
        const rawAngle = (elapsed / period) * 2.0 * Math.PI;
        const baseAngle = Math.min(rawAngle, 2.0 * Math.PI); 
        const angle = baseAngle + (config.angleOffset || 0); // 👈 加上这架无人机的专属相位角
        
        const radiusLng = 0.00055;
        const radiusLat = 0.00045;
        
const currentLng = circleCenterLng + radiusLng * Math.cos(angle);
        const currentLat = circleCenterLat + radiusLat * Math.sin(angle);

        // 触发多角度照片拍摄状态 (仅在“无人感知执行”阶段 index === 9 拍摄，信号干扰与救援出动阶段绝不拍摄)
        if (config.id === 'uav_model_move' && props.activePhaseIndex === 9) {
          // 注意这里为了保险，统一用你之前的 baseAngle 或者 angle (取决于你们外层作用域谁表示累积弧度，通常 angle 比较保险)
          if (angle >= 0.5 * Math.PI && !capturedPhotos.value[0]) {
            capturedPhotos.value[0] = true;
            activePhotoIndex.value = 0;
            triggerPhotoAnimation(0, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, circleCenterHeight));
          }
          if (angle >= 1.0 * Math.PI && !capturedPhotos.value[1]) {
            capturedPhotos.value[1] = true;
            activePhotoIndex.value = 1;
            triggerPhotoAnimation(1, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, circleCenterHeight));
          }
          if (angle >= 1.5 * Math.PI && !capturedPhotos.value[2]) {
            capturedPhotos.value[2] = true;
            activePhotoIndex.value = 2;
            triggerPhotoAnimation(2, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, circleCenterHeight));
          }
          if (angle >= 2.0 * Math.PI && !capturedPhotos.value[3]) {
            capturedPhotos.value[3] = true;
            activePhotoIndex.value = 3;
            triggerPhotoAnimation(3, Cesium.Cartesian3.fromDegrees(currentLng, currentLat, circleCenterHeight));
          }
        }

        return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, circleCenterHeight);
      }
    }, false);

    const uavOrientation = new Cesium.CallbackProperty(() => {
      const pos = uavPosition.getValue(viewer.clock.currentTime);
      if (!pos) return undefined;

      let headingRad;
      if (props.activePhaseIndex >= 3 && props.activePhaseIndex < 8) {
        if (currentMissionDataSource) {
          const entity = currentMissionDataSource.entities.getById('UAV');
          if (entity) {
            const queryTime = getQueryTime(viewer.clock.currentTime);
            const nextTime = Cesium.JulianDate.addSeconds(queryTime, 0.5, new Cesium.JulianDate());
            const nextPos = entity.position.getValue(nextTime);
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
      } else if (props.activePhaseIndex === 8) {
        if (currentMissionDataSource) {
          const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
          if (pathEntity && pathEntity.polyline && pathEntity.polyline.positions) {
            const positions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                              pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
            if (positions && positions.length > 1) {
              const pEnd = positions[positions.length - 1];
              let startIndex = 0;
              const targetDistance = 180.0;
              for (let i = positions.length - 2; i >= 0; i--) {
                const dist = Cesium.Cartesian3.distance(positions[i], pEnd);
                if (dist >= targetDistance) {
                  startIndex = i;
                  break;
                }
              }
              const subPositions = positions.slice(startIndex);
              if (subPositions.length > 1) {
                const segmentCount = subPositions.length - 1;
                const elapsed = Date.now() - phase7StartTime;
                const duration = agentSpeedConfig.ugvDuration * 1000;
                const t = Math.min((elapsed + 100) / duration, 1.0);
                const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
                
                const scaledT = easeT * segmentCount;
                const idx = Math.min(Math.floor(scaledT), segmentCount - 1);
                const localT = scaledT - idx;
                const nextPos = Cesium.Cartesian3.lerp(subPositions[idx], subPositions[idx + 1], localT, new Cesium.Cartesian3());
                
                const cartoCur = Cesium.Cartographic.fromCartesian(pos);
                const cartoNext = Cesium.Cartographic.fromCartesian(nextPos);
                headingRad = Math.PI / 2 - Math.atan2(
                  Cesium.Math.toDegrees(cartoNext.latitude) - Cesium.Math.toDegrees(cartoCur.latitude),
                  Cesium.Math.toDegrees(cartoNext.longitude) - Cesium.Math.toDegrees(cartoCur.longitude)
                );
              }
            }
          }
        }
        if (headingRad === undefined) {
          const headingDeg = Number(uavAdjust.heading) || 18;
          headingRad = Cesium.Math.toRadians(headingDeg);
        }
      } else if (props.activePhaseIndex >= 9) {
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
        minimumPixelSize: 1, // 改为 1 像素，使无人机完全遵循真实的 3D 空间透视，随视角远近自然缩放
        heightReference: Cesium.HeightReference.NONE,
        // 开启无人机 3D 模型内置螺旋臂/螺旋桨的高速旋转动画
        runAnimations: true,
        silhouetteColor: Cesium.Color.fromCssColorString('#00f2fe'),
        silhouetteSize: 2.0
      }
    });

    const UAV_DEBUG_MODE = true; 
   // 🚨 动态分配起始阶段：第一架(index 0)在阶段5连线，其余的在阶段9连线
   // 只要判断这架无人机的 ID 是不是数组里的第一个即可。
// 请看看你第一架无人机的 config.id 是什么，比如是 'uav-1'
// 🚨 只要 ID 是 'uav_model' 或者 'uav_model_move'，就是第一架无人机，阶段 5 连线，其余阶段 9 连线
// 🚨 1. 判断是否是第一架无人机 (名字里不带 _2 和 _3)
    const isFirstUAV = !config.id.includes('_2') && !config.id.includes('_3');

    viewer.entities.add({
      id: `line-link-uav-${config.id}-to-jizhan`, // 保持原有 ID 方便清理
      name: `无人机数据链路`,
      show: new Cesium.CallbackProperty((time) => {
        let isEntityShowing = false;
        if (entity.show !== undefined) {
          isEntityShowing = typeof entity.show.getValue === 'function' ? entity.show.getValue(time) : !!entity.show;
        }
        
        const phase = Number(props.activePhaseIndex);
        
        // 🚨 2. 精准定义连线时机
        let isLineActive = false;
        if (isFirstUAV) {
          // 第一架无人机：仅在 5, 6, 9及以上 连线。(7, 8 强制断开)
          isLineActive = (phase === 5 || phase === 6 || phase >= 9);
        } else {
          // 其余增援无人机：阶段 9 及以上才连线
          isLineActive = phase >= 9;
        }

        return isLineActive && isEntityShowing;
      }, false),
      polyline: {
        positions: new Cesium.CallbackProperty((time) => {
          if (currentScene.value !== 'truck') return [];
          const phase = Number(props.activePhaseIndex);

          // 🚨 3. 与上面保持一致的防御性校验，不该连线的阶段直接返回空坐标
          let isLineActive = false;
          if (isFirstUAV) {
            isLineActive = (phase === 5 || phase === 6 || phase >= 9);
          } else {
            isLineActive = phase >= 9;
          }
          if (!isLineActive) return [];
          const pos = entity.position.getValue(time);
          if (!pos) return [];

          // 🚨 故事点十 (阶段 10)：信号受干扰，全部切断基站，将数据直连至地面 1 号无人车
          if (phase >= 10) {
            const targetUgv = rescueCarEntities[0];
            if (targetUgv) {
              const ugvPos = targetUgv.position.getValue(time);
              if (ugvPos) return [pos, ugvPos];
            }
            return [];
          }
          
          // 🌟 常规连线阶段 (5, 6, 9)：正常连向 5G 基站
          const jizhanTop = getModelTopPosition(
            jizhanAdjust.lng, jizhanAdjust.lat, jizhanAdjust.height,
            jizhanAdjust.heading, jizhanAdjust.pitch, jizhanAdjust.roll, JIZHAN_TOP_OFFSET
          );
          return [pos, jizhanTop];
        }, false),
        width: 3.5,
        arcType: Cesium.ArcType.NONE, // 强制直线
        material: new DynamicFlowMaterialProperty({ color: Cesium.Color.ORANGE, speed: 5.5, repeat: 5.0 })
      }
    });
    uavEntities.push(entity);
    if (config.id === 'uav_model') {
      sharedTruckUavPosition = uavPosition;
    }
  });

  function generateOrbitRingPositions(centerLng, centerLat, centerHeight, radiusLng, radiusLat, count = 72) {
    const points = [];
    for (let i = 0; i <= count; i++) {
      const angle = (i / count) * 2.0 * Math.PI;
      const lng = centerLng + radiusLng * Math.cos(angle);
      const lat = centerLat + radiusLat * Math.sin(angle);
      points.push(Cesium.Cartesian3.fromDegrees(lng, lat, centerHeight));
    }
    return points;
  }

  // (A) 货车现场 - 科技风无人机盘旋轨迹（双层光流 + 极光外包络）
  viewer.entities.add({
    id: 'uav-orbit-ring-glow-truck',
    name: '货车现场无人机盘旋轨迹外发光',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const centerLng = Number(truckAdjust.lng) || 113.104833;
        const centerLat = Number(truckAdjust.lat) || 30.385469;
        return generateOrbitRingPositions(centerLng, centerLat, 100.0, 0.00055, 0.00045);
      }, false),
      width: 7.0,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.35,
        taperPower: 0.8,
        color: Cesium.Color.fromCssColorString('#00f2fe').withAlpha(0.6)
      })
    }
  });

  viewer.entities.add({
    id: 'uav-orbit-ring-flow-truck',
    name: '货车现场无人机盘旋轨迹光流脉冲',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const centerLng = Number(truckAdjust.lng) || 113.104833;
        const centerLat = Number(truckAdjust.lat) || 30.385469;
        return generateOrbitRingPositions(centerLng, centerLat, 100.0, 0.00055, 0.00045);
      }, false),
      width: 4.0,
      material: new DynamicFlowMaterialProperty({
        color: Cesium.Color.fromCssColorString('#00ffffff'),
        speed: 4.5,
        repeat: 12.0
      })
    }
  });

  // (B) 油罐车现场 - 科技风无人机盘旋轨迹
  viewer.entities.add({
    id: 'uav-orbit-ring-glow-tanker',
    name: '油罐车现场无人机盘旋轨迹外发光',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const centerLng = Number(tankerPointAdjust.lng) || 114.9238;
        const centerLat = Number(tankerPointAdjust.lat) || 30.5158;
        return generateOrbitRingPositions(centerLng, centerLat, 100.0, 0.00055, 0.00045);
      }, false),
      width: 7.0,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.35,
        taperPower: 0.8,
        color: Cesium.Color.fromCssColorString('#00f2fe').withAlpha(0.6)
      })
    }
  });

  viewer.entities.add({
    id: 'uav-orbit-ring-flow-tanker',
    name: '油罐车现场无人机盘旋轨迹光流脉冲',
    show: false,
    polyline: {
      positions: new Cesium.CallbackProperty(() => {
        const centerLng = Number(tankerPointAdjust.lng) || 114.9238;
        const centerLat = Number(tankerPointAdjust.lat) || 30.5158;
        return generateOrbitRingPositions(centerLng, centerLat, 100.0, 0.00055, 0.00045);
      }, false),
      width: 4.0,
      material: new DynamicFlowMaterialProperty({
        color: Cesium.Color.fromCssColorString('#00ffffff'),
        speed: 4.5,
        repeat: 12.0
      })
    }
  });

  // 初始化救援车
  // 初始化救援车（多车道战术编队行驶）
  // 初始化救援车（多车道战术编队行驶 + 现场动态环绕巡逻）
  // 初始化救援车（多车道战术编队行驶 + 现场动态环绕巡逻）
  // 初始化救援车（多车道战术编队行驶 + 丝滑物理转向）
  // 初始化救援车（多车道战术编队行驶 + 丝滑物理转向）
  // 初始化救援车（一字编队行驶 + 到达后驻停）
  rescueCarModelConfigs.forEach((config, index) => {
    console.log(`[Cesium] 正在初始化救援车实体: ${config.id}, 路径: ${config.uri}`);

    let phase7StartJulian = undefined;
    let lastLocalPhase = -1;

    const rescueCarPosition = new Cesium.CallbackProperty((time) => {
      if (lastLocalPhase !== props.activePhaseIndex) {
        phase7StartJulian = Cesium.JulianDate.clone(time);
        lastLocalPhase = props.activePhaseIndex;
      }

      const baseStartLng = Number(rescueCarAdjust.lng) || 113.1073;
      const baseStartLat = Number(rescueCarAdjust.lat) || 30.3849;
      const baseAccidentLng = Number(truckAdjust.lng) || 113.104833;
      const baseAccidentLat = Number(truckAdjust.lat) || 30.385469;
      const startHeight = Number(rescueCarAdjust.height) || -1.5;

      // 投影计算：合并冗余代码，沿着起火点和初始坐标直线前进，在前方停车
      const factor = config.stopFactor || 0.78;
      const targetLng = baseStartLng + factor * (baseAccidentLng - baseStartLng);
      const targetLat = baseStartLat + factor * (baseAccidentLat - baseStartLat);

      if (props.activePhaseIndex >= 7) {
        const ugvInfo = getUgvLast200mPosition('truck', props.activePhaseIndex, phase7StartTime, viewer.clock.currentTime, config.stopFactor);
        if (ugvInfo && ugvInfo.pos) {
          const carto = Cesium.Cartographic.fromCartesian(ugvInfo.pos);
          let baseHeight = carto.height;
          if (viewer && viewer.scene && viewer.scene.globe) {
            const terrainHeight = viewer.scene.globe.getHeight(carto);
            if (terrainHeight !== undefined) baseHeight = terrainHeight;
          }
          carto.height = baseHeight + (Number(rescueCarAdjust.height) || 0.0);
          return Cesium.Cartographic.toCartesian(carto);
        }
        if (currentMissionDataSource) {
          const entity = currentMissionDataSource.entities.getById('Car');
          if (entity) {
            const pos = entity.originalPosition ? entity.originalPosition.getValue(getQueryTime()) : entity.position.getValue(getQueryTime());
            if (pos) {
              const carto = Cesium.Cartographic.fromCartesian(pos);
              let baseHeight = carto.height;
              if (viewer && viewer.scene && viewer.scene.globe) {
                const terrainHeight = viewer.scene.globe.getHeight(carto);
                if (terrainHeight !== undefined) baseHeight = terrainHeight;
              }
              carto.height = baseHeight + (Number(rescueCarAdjust.height) || 0.0);
              return Cesium.Cartographic.toCartesian(carto);
            }
          }
        }
      }
      
      if (props.activePhaseIndex >= 6) {
        // 阶段 7 及以上（无人感知部署、信号干扰等）：统一稳定就位于事故现场前沿部署点
        return Cesium.Cartesian3.fromDegrees(targetLng, targetLat, startHeight);
      } else {
        // 阶段 < 6（初始阶段）：在起点停泊
        return Cesium.Cartesian3.fromDegrees(baseStartLng, baseStartLat, startHeight);
      }
    }, false);

    const rescueCarOrientation = new Cesium.CallbackProperty((time) => {
      const pos = rescueCarPosition.getValue(time);
      if (!pos) return undefined;
      
      let headingRad;
      if (props.activePhaseIndex >= 7) {
        const ugvInfo = getUgvLast200mPosition('truck', props.activePhaseIndex, phase7StartTime, viewer.clock.currentTime, config.stopFactor);
        if (ugvInfo && ugvInfo.headingRad !== undefined) {
          const headingDeg = Number(rescueCarAdjust.heading) || 195;
          headingRad = Cesium.Math.toRadians(headingDeg);
        } else if (currentMissionDataSource) {
          const entity = currentMissionDataSource.entities.getById('Car');
          if (entity) {
            const nextTime = Cesium.JulianDate.addSeconds(getQueryTime(), 0.5, new Cesium.JulianDate());
            const nextPos = entity.position.getValue(nextTime);
            if (nextPos) {
              const cartoCur = Cesium.Cartographic.fromCartesian(pos);
              const cartoNext = Cesium.Cartographic.fromCartesian(nextPos);
              headingRad = Math.PI / 2 - Math.atan2(
                Cesium.Math.toDegrees(cartoNext.latitude) - Cesium.Math.toDegrees(cartoCur.latitude),
                Cesium.Math.toDegrees(cartoNext.longitude) - Cesium.Math.toDegrees(cartoCur.longitude)
              ) + Cesium.Math.toRadians(Number(rescueCarAdjust.moveHeading) || 0);
            } else {
              headingRad = Cesium.Math.toRadians(Number(rescueCarAdjust.heading) || 195);
            }
          } else {
            headingRad = Cesium.Math.toRadians(Number(rescueCarAdjust.heading) || 195);
          }
        } else {
          headingRad = Cesium.Math.toRadians(Number(rescueCarAdjust.heading) || 195);
        }
      } else {
        // 阶段 < 6：尚未出发，处于初始停泊状态，听从滑块
        const headingDeg = Number(rescueCarAdjust.heading) || 195;
        headingRad = Cesium.Math.toRadians(headingDeg);
      }
      
      // 修复：废弃原本强制覆盖航向的 Bug 代码，使用上面动态算出来的 headingRad
      const hpr = new Cesium.HeadingPitchRoll(headingRad, 0, 0);
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
        runAnimations: true,
        silhouetteColor: Cesium.Color.fromCssColorString('#00ffaa'),
        silhouetteSize: 2.0
      }
    });
    rescueCarEntities.push(entity);
  });

  // 初始化油罐车场景的无人机模型
  // 初始化油罐车场景的无人机模型
  uavModelConfigs.forEach((config) => {
    console.log(`[Cesium] 正在初始化油罐车场景无人机实体: ${config.id}, 路径: ${config.uri}`);

    const tankerUavPosition = new Cesium.CallbackProperty(() => {
      if (lastTankerUavPhaseIndex !== props.activePhaseIndex) {
        tankerPhase3StartTime = 0;
        tankerPhase4StartTime = 0;
        tankerPhase6StartTime = 0;
        tankerPhase7StartTime = 0;
        tankerPhase8StartTime = 0;
        tankerUavOrbitStartTime = 0;
        lastTankerUavPhaseIndex = props.activePhaseIndex;
      }
      const startHeight = Number(tankerUavAdjust.height) || 120.0;
      
      // 融合你的偏移量与同事的中心点逻辑
      const baseTargetLng = Number(tankerPointAdjust.lng) || 114.89209;
      const baseTargetLat = Number(tankerPointAdjust.lat) || 30.63101;
      const targetLng = baseTargetLng + (config.lonOffset || 0);
      const targetLat = baseTargetLat + (config.latOffset || 0);

      let circleCenterLng = targetLng;
      let circleCenterLat = targetLat;
      let circleCenterHeight = startHeight;

      if (currentMissionDataSource) {
        const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
        if (pathEntity && pathEntity.polyline && pathEntity.polyline.positions) {
          const positions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                            pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
          if (positions && positions.length > 0) {
            const pEnd = positions[positions.length - 1];
            const cartoEnd = Cesium.Cartographic.fromCartesian(pEnd);
            // 加上编队偏移量，让不同无人机的绕飞中心散开
            circleCenterLng = Cesium.Math.toDegrees(cartoEnd.longitude) + (config.lonOffset || 0);
            circleCenterLat = Cesium.Math.toDegrees(cartoEnd.latitude) + (config.latOffset || 0);
            circleCenterHeight = cartoEnd.height;
          }
        }
      }

      if (props.activePhaseIndex === 4) {
        // 阶段 4（无人机侦察）：无人机从距事故点 200 米处向前匀速飞行抵达现场
        const centerLng = Number(tankerPointAdjust.lng) || 114.9238;
        const centerLat = Number(tankerPointAdjust.lat) || 30.5158;

        if (!currentMissionDataSource) {
          return Cesium.Cartesian3.fromDegrees(centerLng + (config.lonOffset || 0), centerLat + (config.latOffset || 0), startHeight);
        }
        const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
        if (!pathEntity || !pathEntity.polyline || !pathEntity.polyline.positions) {
          return Cesium.Cartesian3.fromDegrees(centerLng + (config.lonOffset || 0), centerLat + (config.latOffset || 0), startHeight);
        }
        const rawPositions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                          pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
        if (!rawPositions || rawPositions.length <= 1) {
          return Cesium.Cartesian3.fromDegrees(centerLng + (config.lonOffset || 0), centerLat + (config.latOffset || 0), startHeight);
        }

        if (!tankerPhase4StartTime) {
          tankerPhase4StartTime = Date.now();
        }
        const elapsed = Date.now() - tankerPhase4StartTime;
        const duration = 8000;
        
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        let positions = rawPositions;
        const pEnd = positions[positions.length - 1];
        let startIndex = 0;
        const targetDistance = 200.0;
        for (let i = positions.length - 2; i >= 0; i--) {
          const dist = Cesium.Cartesian3.distance(positions[i], pEnd);
          if (dist >= targetDistance) {
            startIndex = i;
            break;
          }
        }
        const subPositions = positions.slice(startIndex);
        if (subPositions.length > 1) {
          const pos = getPositionAtRatio(subPositions, easeT);
          if (pos) {
              const carto = Cesium.Cartographic.fromCartesian(pos);
              return Cesium.Cartesian3.fromDegrees(
                  Cesium.Math.toDegrees(carto.longitude) + (config.lonOffset || 0),
                  Cesium.Math.toDegrees(carto.latitude) + (config.latOffset || 0),
                  carto.height
              );
          }
        }
        return Cesium.Cartesian3.fromDegrees(centerLng + (config.lonOffset || 0), centerLat + (config.latOffset || 0), startHeight);

      } else if (props.activePhaseIndex === 5 || props.activePhaseIndex === 6) {
        if (!tankerUavOrbitStartTime) { tankerUavOrbitStartTime = Date.now(); }
        const elapsed = Date.now() - tankerUavOrbitStartTime;
        const period = 12000;
        const angle = (elapsed / period) * 2.0 * Math.PI;
        
        const radiusLng = 0.00055;
        const radiusLat = 0.00045;
        const centerLng = Number(tankerPointAdjust.lng) || 114.9238;
        const centerLat = Number(tankerPointAdjust.lat) || 30.5158;
        const centerHeight = 100.0;

        const currentLng = centerLng + radiusLng * Math.cos(angle) + (config.lonOffset || 0);
        const currentLat = centerLat + radiusLat * Math.sin(angle) + (config.latOffset || 0);

        return Cesium.Cartesian3.fromDegrees(currentLng, currentLat, centerHeight);

      } else if (props.activePhaseIndex === 3 || props.activePhaseIndex === 7) {
        // 阶段 3（无人机出动）或 阶段 7（无人装备出动）：无人机运动到距离事故点 200 米处停下
        if (!currentMissionDataSource) {
          return Cesium.Cartesian3.fromDegrees(114.9238 + (config.lonOffset || 0), 30.5158 + (config.latOffset || 0), startHeight);
        }
        const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
        if (!pathEntity || !pathEntity.polyline || !pathEntity.polyline.positions) {
          return Cesium.Cartesian3.fromDegrees(114.9238 + (config.lonOffset || 0), 30.5158 + (config.latOffset || 0), startHeight);
        }
        const rawPositions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                          pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
        if (!rawPositions || rawPositions.length <= 1) {
          return Cesium.Cartesian3.fromDegrees(114.9238 + (config.lonOffset || 0), 30.5158 + (config.latOffset || 0), startHeight);
        }

        const isPhase3 = props.activePhaseIndex === 3;
        if (isPhase3 && !tankerPhase3StartTime) {
          tankerPhase3StartTime = Date.now();
        } else if (!isPhase3 && !tankerPhase7StartTime) {
          tankerPhase7StartTime = Date.now();
        }

        const elapsed = Date.now() - (isPhase3 ? tankerPhase3StartTime : tankerPhase7StartTime);
        const duration = agentSpeedConfig.uavDuration * 1000;
        
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        // 截取从起点到距终点200m处的路线段
        const pEnd = rawPositions[rawPositions.length - 1];
        let stopIndex = 0;
        const targetDistance = 200.0;
        for (let i = rawPositions.length - 2; i >= 0; i--) {
          const dist = Cesium.Cartesian3.distance(rawPositions[i], pEnd);
          if (dist >= targetDistance) {
            stopIndex = i;
            break;
          }
        }
        const activePositions = rawPositions.slice(0, stopIndex + 1);
        if (activePositions.length > 1) {
          const pos = getPositionAtRatio(activePositions, easeT);
          if (pos) {
              const carto = Cesium.Cartographic.fromCartesian(pos);
              return Cesium.Cartesian3.fromDegrees(
                  Cesium.Math.toDegrees(carto.longitude) + (config.lonOffset || 0),
                  Cesium.Math.toDegrees(carto.latitude) + (config.latOffset || 0),
                  carto.height
              );
          }
        }
        if (activePositions.length > 0) {
            const pos = activePositions[activePositions.length - 1];
            const carto = Cesium.Cartographic.fromCartesian(pos);
            return Cesium.Cartesian3.fromDegrees(
                Cesium.Math.toDegrees(carto.longitude) + (config.lonOffset || 0),
                Cesium.Math.toDegrees(carto.latitude) + (config.latOffset || 0),
                carto.height
            );
        }
        return Cesium.Cartesian3.fromDegrees(114.9238 + (config.lonOffset || 0), 30.5158 + (config.latOffset || 0), startHeight);

      } else if (props.activePhaseIndex < 3) {
        return Cesium.Cartesian3.fromDegrees(114.9238 + (config.lonOffset || 0), 30.5158 + (config.latOffset || 0), startHeight);
      } else if (props.activePhaseIndex === 8) {
        // 阶段 8（无人感知部署）：无人机从距离事故点 200 米处平滑运动向事故点
        if (!tankerPhase8StartTime) {
          tankerPhase8StartTime = Date.now();
        }
        const elapsed = Date.now() - tankerPhase8StartTime;
        const duration = 6000;
        const t = Math.min(elapsed / duration, 1.0);
        const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

        if (currentMissionDataSource) {
          const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
          if (pathEntity && pathEntity.polyline && pathEntity.polyline.positions) {
            const rawPositions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                              pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
            if (rawPositions && rawPositions.length > 1) {
              const pEnd = rawPositions[rawPositions.length - 1];
              let startIndex = 0;
              const targetDistance = 200.0;
              for (let i = rawPositions.length - 2; i >= 0; i--) {
                const dist = Cesium.Cartesian3.distance(rawPositions[i], pEnd);
                if (dist >= targetDistance) {
                  startIndex = i;
                  break;
                }
              }
              const subPositions = rawPositions.slice(startIndex);
              if (subPositions.length > 1) {
                const pos = getPositionAtRatio(subPositions, easeT);
                if (pos) {
                  const carto = Cesium.Cartographic.fromCartesian(pos);
                  return Cesium.Cartesian3.fromDegrees(
                    Cesium.Math.toDegrees(carto.longitude) + (config.lonOffset || 0),
                    Cesium.Math.toDegrees(carto.latitude) + (config.latOffset || 0),
                    carto.height
                  );
                }
              }
            }
          }
        }
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
        
        // 使用同事最新架构中计算出来的安全圆心，而不是写死的数字
        const centerLng = circleCenterLng;
        const centerLat = circleCenterLat;
        const startHeight = circleCenterHeight;

        // 如果获取不到车的位置，提供一个后备逻辑计算角度
        let uavStartLng = centerLng + 0.0005; 
        let uavStartLat = centerLat;
        if (carLng && carLat) {
           uavStartLng = carLng + 0.5 * (targetLng - carLng);
           uavStartLat = carLat + 0.5 * (targetLat - carLat);
        }

        const orbitDuration = 12000;
        const dLng = uavStartLng - centerLng;
        const dLat = uavStartLat - centerLat;
        // 如果 dLng, dLat 为 0 (发生边界异常)，使用默认半径 0.0005 (约 50 米)
        const radius = (dLng === 0 && dLat === 0) ? 0.0005 : Math.sqrt(dLng * dLng + dLat * dLat);
        const startAngle = (dLng === 0 && dLat === 0) ? 0 : Math.atan2(dLat, dLng);

        if (elapsed < orbitDuration) {
          const rawAngle = startAngle - (elapsed / orbitDuration) * 2.0 * Math.PI;
          const baseAngle = Math.max(rawAngle, startAngle - 2.0 * Math.PI); 
          // 👈 加入你的关键角度编队偏移
          const angle = baseAngle + (config.angleOffset || 0); 
          
          const currentLng = centerLng + radius * Math.cos(angle);
          const currentLat = centerLat + radius * Math.sin(angle);
          
          // 仅在无人感知执行阶段 (index === 9) 拍摄照片，信号干扰与救援装备出动阶段严禁拍摄/飞图
          if (config.id === 'uav_model_move' && props.activePhaseIndex === 9) {
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
          
          if (config.id === 'uav_model_move' && props.activePhaseIndex === 9 && !capturedPhotos.value[3]) {
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
if (props.activePhaseIndex === 3 || props.activePhaseIndex === 7) {
        if (currentMissionDataSource) {
          const pathEntity = currentMissionDataSource.entities.getById('UAV_Path');
          if (pathEntity && pathEntity.polyline && pathEntity.polyline.positions) {
            const positions = pathEntity.polyline.positions.getValue(getQueryTime()) ||
                              pathEntity.polyline.positions.getValue(new Cesium.JulianDate());
            if (positions && positions.length > 1) {
              const pEnd = positions[positions.length - 1];
              let startIndex = 0;
              const targetDistance = 180.0;
              for (let i = positions.length - 2; i >= 0; i--) {
                const dist = Cesium.Cartesian3.distance(positions[i], pEnd);
                if (dist >= targetDistance) {
                  startIndex = i;
                  break;
                }
              }
              const subPositions = positions.slice(startIndex);
              if (subPositions.length > 1) {
                const segmentCount = subPositions.length - 1;
                const elapsed = Date.now() - phase7StartTime;
                const duration = agentSpeedConfig.ugvDuration * 1000;
                const t = Math.min((elapsed + 100) / duration, 1.0);
                const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
                
                const scaledT = easeT * segmentCount;
                const idx = Math.min(Math.floor(scaledT), segmentCount - 1);
                const localT = scaledT - idx;
                const nextPos = Cesium.Cartesian3.lerp(subPositions[idx], subPositions[idx + 1], localT, new Cesium.Cartesian3());
                
                const cartoCur = Cesium.Cartographic.fromCartesian(pos);
                const cartoNext = Cesium.Cartographic.fromCartesian(nextPos);
                headingRad = Math.PI / 2 - Math.atan2(
                  Cesium.Math.toDegrees(cartoNext.latitude) - Cesium.Math.toDegrees(cartoCur.latitude),
                  Cesium.Math.toDegrees(cartoNext.longitude) - Cesium.Math.toDegrees(cartoCur.longitude)
                );
              }
            }
          }
        }
        if (headingRad === undefined) {
          const headingDeg = Number(tankerUavAdjust.heading) || 18;
          headingRad = Cesium.Math.toRadians(headingDeg);
        }
      } else if (props.activePhaseIndex >= 9) {
        // 计算无人机当前位置指向事故中心的朝向角度，使镜头始终对准事故车拍照
        // (已加入编队偏移量适配多机协同)
        const targetLng = (Number(tankerPointAdjust.lng) || 114.89209) + (config.lonOffset || 0);
        const targetLat = (Number(tankerPointAdjust.lat) || 30.63101) + (config.latOffset || 0);
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
        minimumPixelSize: 1, // 改为 1 像素，使无人机完全遵循真实的 3D 空间透视，随视角远近自然缩放
        heightReference: Cesium.HeightReference.NONE,
        // 开启无人机 3D 模型内置螺旋臂/螺旋桨的高速旋转动画
        runAnimations: true,
        silhouetteColor: Cesium.Color.fromCssColorString('#00f2fe'),
        silhouetteSize: 2.0
      }
    });
    // 🚨 新增：油罐车无人机连接到专属基站
    // 🚨 1. 判断是否是第一架无人机 (ID 名字里不带 _2 和 _3)
    const isFirstUAV = !config.id.includes('_2') && !config.id.includes('_3');

    viewer.entities.add({
      id: `line-link-tanker-uav-${config.id}-to-jizhan`, // 保持油罐车专属 ID 唯一性
      name: `油罐车场景无人机数据链路`,
      show: new Cesium.CallbackProperty((time) => {
        // 🚨 场景隔离：只有在油罐车场景才显示
        if (currentScene.value !== 'tanker') return false;

        let isEntityShowing = false;
        if (entity.show !== undefined) {
          isEntityShowing = typeof entity.show.getValue === 'function' ? entity.show.getValue(time) : !!entity.show;
        }
        
        const phase = Number(props.activePhaseIndex);
        
        // 🚨 2. 精准定义连线时机
        let isLineActive = false;
        if (isFirstUAV) {
          // 第一架无人机：仅在 5, 6, 9及以上 连线。(7, 8 强制断开)
          isLineActive = (phase === 5 || phase === 6 || phase >= 9);
        } else {
          // 其余增援无人机：阶段 9 及以上才连线
          isLineActive = phase >= 9;
        }

        return isLineActive && isEntityShowing;
      }, false),
      polyline: {
        positions: new Cesium.CallbackProperty((time) => {
          // 🚨 场景校验：不是油罐车场景绝对不计算连线坐标
          if (currentScene.value !== 'tanker') return [];
          const phase = Number(props.activePhaseIndex);

          // 🚨 3. 与 show 保持一致的阶段校验
          let isLineActive = false;
          if (isFirstUAV) {
            isLineActive = (phase === 5 || phase === 6 || phase >= 9);
          } else {
            isLineActive = phase >= 9;
          }
          if (!isLineActive) return [];

          const pos = entity.position.getValue(time);
          if (!pos) return [];

          // 🚨 故事点十 (阶段 10)：信号受干扰，全部切断基站，将数据直连至【油罐车场景】的 1 号无人车
          if (phase >= 10) {
            const targetUgv = tankerRescueCarEntities[0]; // 👈 注意：抓取油罐车场景的无人车
            if (targetUgv) {
              const ugvPos = targetUgv.position.getValue(time);
              if (ugvPos) return [pos, ugvPos];
            }
            return [];
          }
          
          // 🌟 常规连线阶段 (5, 6, 9)：正常连向【油罐车场景】的 5G 基站
          if (!tankerJizhanAdjust) return []; // 防御性判断
          const jizhanTop = getModelTopPosition(
            tankerJizhanAdjust.lng, tankerJizhanAdjust.lat, tankerJizhanAdjust.height,
            tankerJizhanAdjust.heading, tankerJizhanAdjust.pitch, tankerJizhanAdjust.roll, JIZHAN_TOP_OFFSET
          ); // 👈 注意：这里抓取的是 tankerJizhanAdjust
          
          return [pos, jizhanTop];
        }, false),
        width: 3.5,
        arcType: Cesium.ArcType.NONE, // 强制直线
        material: new DynamicFlowMaterialProperty({ color: Cesium.Color.ORANGE, speed: 5.5, repeat: 5.0 })
      }
    });
    tankerUavEntities.push(entity);
    if (config.id === 'uav_model') {
      sharedTankerUavPosition = tankerUavPosition;
    }
  });

  // 初始化油罐车场景的救援车
  // 初始化油罐车场景的救援车（并排编队）
  // 初始化油罐车场景的救援车（并排编队 + 现场动态环绕巡逻）
  // 初始化油罐车场景的救援车（并排编队 + 丝滑物理转向）
  // 初始化油罐车场景的救援车（并排编队 + 丝滑物理转向）
  // 初始化油罐车场景的救援车（一字编队行驶 + 到达后驻停）
  // ==========================================
// 🚨 油罐车场景无人车引擎：平滑进场 + 巡逻
// ==========================================
tankerRescueCarModelConfigs.forEach((config, index) => {
  let tankerBaseStartLng = Number(tankerRescueCarAdjust.lng) || 114.895791;
  let tankerBaseStartLat = Number(tankerRescueCarAdjust.lat) || 30.631361;
  let tankerBaseTargetLng = Number(tankerPointAdjust.lng) || 114.8945;
  let tankerBaseTargetLat = Number(tankerPointAdjust.lat) || 30.632161;
  const tankerStartHeight = Number(tankerRescueCarAdjust.height) || -1.5;

  // 空间错开：防止两辆车重叠
  if (index === 1) {
     tankerBaseStartLng += 0.000035; tankerBaseStartLat -= 0.000025;
     tankerBaseTargetLng += 0.000035; tankerBaseTargetLat -= 0.000025;
  }

  const tankerFactor = config.stopFactor || 0.40;
  const tankerActualTargetLng = tankerBaseStartLng + tankerFactor * (tankerBaseTargetLng - tankerBaseStartLng);
  const tankerActualTargetLat = tankerBaseStartLat + tankerFactor * (tankerBaseTargetLat - tankerBaseStartLat);

  let tankerPhase7StartJulian = null;
  let tankerLastLocalPhase = -1;

const tankerRescueCarPosition = new Cesium.CallbackProperty((time) => {
    const phase = Number(props.activePhaseIndex);
    if (tankerLastLocalPhase !== phase) {
      tankerPhase7StartJulian = Cesium.JulianDate.clone(time);
      tankerLastLocalPhase = phase;
    }

    if (phase < 7) {
      return Cesium.Cartesian3.fromDegrees(tankerBaseStartLng, tankerBaseStartLat, tankerStartHeight);
    } else if (phase === 7 || phase === 8) {
      // 阶段 7~8：沿规划路线行驶
      const ugvInfo = getUgvLast200mPosition('tanker', phase, null, time, config.stopFactor);
      if (ugvInfo && ugvInfo.pos) {
        const carto = Cesium.Cartographic.fromCartesian(ugvInfo.pos);
        let baseHeight = carto.height;
        if (viewer && viewer.scene && viewer.scene.globe) {
          const terrainHeight = viewer.scene.globe.getHeight(carto);
          if (terrainHeight !== undefined) baseHeight = terrainHeight;
        }
        carto.height = baseHeight + tankerStartHeight;
        return Cesium.Cartographic.toCartesian(carto);
      }
      // 降级：直线插值
      const elapsed = Math.max(0, Cesium.JulianDate.secondsDifference(time, tankerPhase7StartJulian));
      const duration = 10.0;
      const t = Math.min(elapsed / duration, 1.0);
      const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      const lng = tankerBaseStartLng + (tankerActualTargetLng - tankerBaseStartLng) * easeT;
      const lat = tankerBaseStartLat + (tankerActualTargetLat - tankerBaseStartLat) * easeT;
      return Cesium.Cartesian3.fromDegrees(lng, lat, tankerStartHeight);
    } else {
      // =====================================
      // 🌟 阶段 9 及以上：无人感知执行阶段，开启动态巡逻游走！
      // =====================================
      const patrolSpeed = 0.4;         // 游走速度
      const patrolDistance = 0.00008;  // 游走范围
      const roadAngleRad = Cesium.Math.toRadians(90); // 游走轴向 (如果发现车横向漂移，可改为 0)
      
      // 使用 index * Math.PI 让两辆车运动方向相反，形成交错巡逻效果
      const wave = Math.sin((Date.now() / 1000.0) * patrolSpeed + (index * Math.PI));

      const ugvInfo = getUgvLast200mPosition('tanker', phase, null, time, config.stopFactor);
      if (ugvInfo && ugvInfo.pos) {
        const carto = Cesium.Cartographic.fromCartesian(ugvInfo.pos);
        let baseHeight = carto.height;
        if (viewer && viewer.scene && viewer.scene.globe) {
          const terrainHeight = viewer.scene.globe.getHeight(carto);
          if (terrainHeight !== undefined) baseHeight = terrainHeight;
        }
        // 核心：在静止坐标上叠加游走偏移量
        const curLng = Cesium.Math.toDegrees(carto.longitude) + wave * patrolDistance * Math.cos(roadAngleRad);
        const curLat = Cesium.Math.toDegrees(carto.latitude) + wave * patrolDistance * Math.sin(roadAngleRad);
        return Cesium.Cartesian3.fromDegrees(curLng, curLat, baseHeight + tankerStartHeight);
      }
      
      // 降级：无法读取路径时，基于预计算终点进行游走
      const curLng = tankerActualTargetLng + wave * patrolDistance * Math.cos(roadAngleRad);
      const curLat = tankerActualTargetLat + wave * patrolDistance * Math.sin(roadAngleRad);
      return Cesium.Cartesian3.fromDegrees(curLng, curLat, tankerStartHeight);
    }
  }, false);

  const tankerRescueCarOrientation = new Cesium.CallbackProperty((time) => {
    const phase = Number(props.activePhaseIndex);
    const pos = tankerRescueCarPosition.getValue(time);
    if (!pos) return Cesium.Quaternion.IDENTITY;

    // 🌟 部署阶段航向滑块偏移量（阶段 7~8）
    const deployUiOffsetRad = Cesium.Math.toRadians(Number(tankerRescueCarAdjust.heading) || 0);
    // 🌟 执行阶段航向滑块偏移量（阶段 9+）
    const execUiOffsetRad = Cesium.Math.toRadians(Number(tankerRescueCarAdjust.execHeading) || 0);

    const flip180 = Math.PI; 

    let headingRad = 0;
    if (phase >= 7 && phase < 9) {
      // 部署阶段 (7~8)：优先使用路径规划方向 + 部署航向偏移
      const ugvInfo = getUgvLast200mPosition('tanker', phase, null, time, config.stopFactor);
      if (ugvInfo && ugvInfo.headingRad !== undefined) {
        headingRad = ugvInfo.headingRad + flip180 + deployUiOffsetRad;
      } else {
        const dx = tankerActualTargetLng - tankerBaseStartLng;
        const dy = tankerActualTargetLat - tankerBaseStartLat;
        headingRad = Math.atan2(dx, dy) + flip180 + deployUiOffsetRad;
      }
    } else {
      // 执行阶段 (9+)：使用独立配置的执行航向偏移
      headingRad = Cesium.Math.toRadians(0) + flip180 + execUiOffsetRad;
    }
    
    const hpr = new Cesium.HeadingPitchRoll(headingRad, 0, 0);
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
      runAnimations: true,
      silhouetteColor: Cesium.Color.fromCssColorString('#00ffaa'),
      silhouetteSize: 2.0
    }
  });
  tankerRescueCarEntities.push(entity);
});

// ==========================================
// 📡 油罐车数据链路与面板 (彻底分离防断线)
// ==========================================
[0, 1].forEach((modelIndex) => {
  // 1. 油罐车终端面板
  viewer.entities.add({
    id: `network-label-tanker-car${modelIndex + 1}`,
    position: new Cesium.CallbackProperty((time) => {
      const carList = tankerRescueCarEntities.value || tankerRescueCarEntities;
      const carEntity = carList[modelIndex];
      if (!carEntity) return undefined;
      const carPos = carEntity.position.getValue(time);
      if (!carPos) return undefined;
      const carto = Cesium.Cartographic.fromCartesian(carPos);
      return Cesium.Cartesian3.fromDegrees(Cesium.Math.toDegrees(carto.longitude), Cesium.Math.toDegrees(carto.latitude), carto.height + 3.5);
    }, false),
    show: new Cesium.CallbackProperty((time) => {
      if (currentScene.value !== 'tanker') return false;
      const carList = tankerRescueCarEntities.value || tankerRescueCarEntities;
      const carEntity = carList[modelIndex];
      if (!carEntity) return false;
      
      let visible = true;
      if (carEntity.show !== undefined) {
        visible = typeof carEntity.show.getValue === 'function' ? carEntity.show.getValue(time) : !!carEntity.show;
      }
      if (Number(props.activePhaseIndex) >= 9 && Number(props.activePhaseIndex) < 11 && visible) return true;
      carEntity._netTime = null;
      return false;
    }, false),
    label: {
      text: new Cesium.CallbackProperty(() => {
        if (currentScene.value !== 'tanker') return '';
        if (Number(props.activePhaseIndex) < 9 || Number(props.activePhaseIndex) >= 11) return '';
        if (Number(props.activePhaseIndex) >= 10) {
           if (modelIndex === 0) return `[RELAY] 启用临时通信中继\n▶ 核心链路: 已接管\n▶ 延迟: 8ms`;
           return `▶ 环境数据流: ACTIVE\n▶ 上传至中继: 稳定`;
        }
        const carList = tankerRescueCarEntities.value || tankerRescueCarEntities;
        const carEntity = carList[modelIndex];
        if (!carEntity) return '';
        if (!carEntity._netTime) carEntity._netTime = Date.now();
        const elapsed = (Date.now() - carEntity._netTime) / 1000.0;
        if (elapsed < 1.5) return `[SYS] 扫描 5G 信号...`;
        if (elapsed < 3.5) return `[NET] 建立 WebSocket 专线...`;
        return `▶ 环境数据流: ACTIVE\n▶ 延迟: 12ms`;
      }, false),
      font: '14px monospace',
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      fillColor: new Cesium.CallbackProperty(() => (Number(props.activePhaseIndex) >= 10 && modelIndex === 0) ? Cesium.Color.GOLD : Cesium.Color.LIME, false),
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 2,
      showBackground: true,
      backgroundColor: new Cesium.Color(0.1, 0.1, 0.1, 0.8),
      backgroundPadding: new Cesium.Cartesian2(10, 10),
      
      // =====================================
      // 🌟 核心修复：双翼展开布局，彻底告别重叠！
      // =====================================
      horizontalOrigin: modelIndex === 0 ? Cesium.HorizontalOrigin.RIGHT : Cesium.HorizontalOrigin.LEFT,
      pixelOffset: new Cesium.Cartesian2(modelIndex === 0 ? -30 : 30, -45),
      
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  });

  // 2. 油罐车不死版连线
  [0, 1].forEach((innerCarIndex) => {
    viewer.entities.add({
      id: `line-link-tanker-car${modelIndex + 1}-${innerCarIndex + 1}-to-jizhan-immortal`,
      name: `油罐车动态中心数据链路`,
      show: new Cesium.CallbackProperty((time) => {
        if (currentScene.value !== 'tanker') return false;
        const phase = Number(props.activePhaseIndex);
        if (phase >= 10 && modelIndex === 0) return false;

        const carList = tankerRescueCarEntities.value || tankerRescueCarEntities;
        const carEntity = carList[modelIndex];
        if (!carEntity) return false;

        if (phase < 9) {
           carEntity._myNetTime = null;
           return false;
        }

        let visible = true;
        if (carEntity.show !== undefined) {
          visible = typeof carEntity.show.getValue === 'function' ? carEntity.show.getValue(time) : !!carEntity.show;
        }
        if (!visible) {
           carEntity._myNetTime = null;
           return false;
        }
        if (!carEntity._myNetTime) carEntity._myNetTime = Date.now();
        return ((Date.now() - carEntity._myNetTime) / 1000.0) >= 3.5;
      }, false),
      polyline: {
        positions: new Cesium.CallbackProperty((time) => {
          if (currentScene.value !== 'tanker') return [];
          const phase = Number(props.activePhaseIndex);
          if (phase < 9) return [];

          const carList = tankerRescueCarEntities.value || tankerRescueCarEntities;
          const carEntity = carList[modelIndex];

          if (!carEntity || !carEntity.position || !carEntity.orientation) return [];
          const carCartesian = carEntity.position.getValue(time);
          const carOrientation = carEntity.orientation.getValue(time);
          if (!carCartesian || !carOrientation) return [];

          const offsetX = 0.0;
          const offsetY = (innerCarIndex === 0) ? 1.5 : -1.5;
          const offsetZ = 1.6;
          const localOffset = new Cesium.Cartesian3(offsetX, offsetY, offsetZ);
          const rotationMatrix = Cesium.Matrix3.fromQuaternion(carOrientation);
          const worldOffset = Cesium.Matrix3.multiplyByVector(rotationMatrix, localOffset, new Cesium.Cartesian3());
          const startPos = Cesium.Cartesian3.add(carCartesian, worldOffset, new Cesium.Cartesian3());

          if (phase >= 10) {
            if (modelIndex === 0) return [];
            const relayUgv = carList[0];
            if (relayUgv && relayUgv.position) {
              const ugvPos = relayUgv.position.getValue(time);
              if (ugvPos) return [startPos, ugvPos];
            }
            return [];
          }

          const targetJizhan = tankerJizhanAdjust.value || tankerJizhanAdjust;
          if (!targetJizhan || !targetJizhan.show) return [];

          const jizhanTop = getModelTopPosition(
            targetJizhan.lng, targetJizhan.lat, targetJizhan.height,
            targetJizhan.heading, targetJizhan.pitch, targetJizhan.roll, JIZHAN_TOP_OFFSET
          );

          return [startPos, jizhanTop];
        }, false),
        width: 4.0,
        arcType: Cesium.ArcType.NONE,
        material: new DynamicFlowMaterialProperty({ color: Cesium.Color.CHARTREUSE, speed: 4.5, repeat: 6.0 })
      }
    });
  });
});
// =========================================================

// 1. 货车追尾现场 - 编队无人车链路 (连向 5G 基站)
// 🚨 设定移动参数（可根据现场视觉效果微调）
const roadAngleDeg = 45; // 道路走向角度，0为东西，90为南北（控制移动方向避免下田地）
const roadAngleRad = Cesium.Math.toRadians(roadAngleDeg);
const patrolDistance = 0.00005; // 往复移动范围，大概 5 米
const patrolSpeed = 0.5; // 移动速度
// 🚨 全局时间轴锚点，控制组网生命周期
// ==========================================
// 还原版：无人车端（阶段 8 开始游走 + 绿色连线）
// ==========================================
// ==========================================
// 还原版：无人车端（阶段 8 开始游走 + 绿色连线）
// ==========================================
// ==========================================
// 1. 基站端：新增组网雷达波与调度面板 (严格锁定阶段 8)
// ==========================================
// (1) 基站向外发送的 5G 探测波纹
// ==========================================
// 🚨 终极核武器：全局强制校验器
// 彻底屏蔽 NaN、undefined 导致的幽灵渲染
// ==========================================
// 🚨 终极核武器：全局强制校验器
// 彻底屏蔽 NaN、undefined 导致的幽灵渲染
const isPhase8Ready = () => {
  const phase = Number(props.activePhaseIndex);
  return !isNaN(phase) && phase >= 8 && currentScene.value === 'truck';
};

// ==========================================
// 1. 基站端：组网雷达波与调度面板
// ==========================================
// 🧹 清理历史残留 (防止 Vite 热更新产生幽灵)
['jizhan-broadcast-wave-truck', 'jizhan-network-panel-truck', 'jizhan-broadcast-wave-truck-safe', 'jizhan-network-panel-truck-safe'].forEach(id => viewer.entities.removeById(id));

// (1) 基站向外发送的 5G 探测波纹
let _cachedWaveFrameTime = 0;
let _cachedWaveRadius = 0.1;

function getJizhanWaveRadius() {
  if (Number(props.activePhaseIndex) < 8) return 0.1;
  if (!jizhanAdjust._netTime) jizhanAdjust._netTime = Date.now();
  const now = Date.now();
  if (now - _cachedWaveFrameTime > 8) {
    _cachedWaveFrameTime = now;
    _cachedWaveRadius = Math.max(0.1, (((now - jizhanAdjust._netTime) / 1000.0) % 2.0) * 40.0);
  }
  return _cachedWaveRadius;
}

viewer.entities.add({
  id: 'jizhan-broadcast-wave-truck',
  name: '基站广播信号',
  position: Cesium.Cartesian3.fromDegrees(jizhanAdjust.lng, jizhanAdjust.lat, jizhanAdjust.height),
  show: new Cesium.CallbackProperty(() => {
    if (!isPhase8Ready()) {
      jizhanAdjust._netTime = null; // 不达标，立刻清空计时器并隐藏
      return false;
    }
    return true;
  }, false),
  ellipse: {
    semiMinorAxis: new Cesium.CallbackProperty(getJizhanWaveRadius, false),
    semiMajorAxis: new Cesium.CallbackProperty(getJizhanWaveRadius, false),
    material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(() => {
      if (Number(props.activePhaseIndex) < 8 || !jizhanAdjust._netTime) return Cesium.Color.TRANSPARENT;
      const alpha = Math.max(0, 1.0 - ((((Date.now() - jizhanAdjust._netTime) / 1000.0) % 2.0) / 2.0));
      return Cesium.Color.CYAN.withAlpha(alpha * 0.6);
    }, false)),
    height: jizhanAdjust.height + 0.1,
  }
});

// (2) 基站头顶的主控面板
viewer.entities.add({
  id: 'jizhan-network-panel-truck',
  position: Cesium.Cartesian3.fromDegrees(jizhanAdjust.lng, jizhanAdjust.lat, jizhanAdjust.height + 6.5),
  show: new Cesium.CallbackProperty(() => {
    if (!isPhase8Ready() || !jizhanAdjust.show) {
       jizhanAdjust._netTime = null; 
       return false;
    }
    return true;
  }, false),
  label: {
    text: new Cesium.CallbackProperty(() => {
      if (Number(props.activePhaseIndex) < 8 || !jizhanAdjust._netTime) return '';
      const elapsed = (Date.now() - jizhanAdjust._netTime) / 1000.0;
      if (elapsed < 1.5) return `[CORE] 5G 核心网激活\n广播探测波纹...`;
      if (elapsed < 3.5) return `[CORE] 捕获设备握手请求\n分配密钥并开通专线...`;
      return `[CORE] 星型网络组网完毕\n▶ 主控链路: 稳定\n▶ 上行吞吐: 1.2 Gbps`;
    }, false),
    font: '14px monospace',
    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
    fillColor: Cesium.Color.CYAN,
    outlineColor: Cesium.Color.BLACK,
    outlineWidth: 2,
    showBackground: true,
    backgroundColor: new Cesium.Color(0.05, 0.1, 0.2, 0.8),
    backgroundPadding: new Cesium.Cartesian2(12, 12),
    pixelOffset: new Cesium.Cartesian2(0, -30),
    horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
    disableDepthTestDistance: Number.POSITIVE_INFINITY
  }
});
// ==========================================
// 🚨 油罐车场景：基站端组网雷达波与调度面板
// ==========================================
// 🧹 清理历史残留，防止热更新报错
['jizhan-broadcast-wave-tanker', 'jizhan-network-panel-tanker'].forEach(id => viewer.entities.removeById(id));

// 专属波纹半径计算器
let _cachedTankerWaveFrameTime = 0;
let _cachedTankerWaveRadius = 0.1;

function getTankerJizhanWaveRadius() {
  if (Number(props.activePhaseIndex) < 8 || currentScene.value !== 'tanker') return 0.1;
  if (!tankerJizhanAdjust._netTime) tankerJizhanAdjust._netTime = Date.now();
  const now = Date.now();
  if (now - _cachedTankerWaveFrameTime > 8) {
    _cachedTankerWaveFrameTime = now;
    _cachedTankerWaveRadius = Math.max(0.1, (((now - tankerJizhanAdjust._netTime) / 1000.0) % 2.0) * 40.0);
  }
  return _cachedTankerWaveRadius;
}

// (1) 油罐车基站向外发送的 5G 探测波纹
viewer.entities.add({
  id: 'jizhan-broadcast-wave-tanker',
  name: '油罐车基站广播信号',
  // 使用 CallbackProperty 让波纹跟随右下角滑块实时移动
  position: new Cesium.CallbackProperty(() => {
    return Cesium.Cartesian3.fromDegrees(tankerJizhanAdjust.lng, tankerJizhanAdjust.lat, tankerJizhanAdjust.height);
  }, false),
  show: new Cesium.CallbackProperty(() => {
    // 拦截：阶段不到8，或者当前不是油罐车场景，立即隐藏并清空计时
    if (Number(props.activePhaseIndex) < 8 || currentScene.value !== 'tanker') {
      tankerJizhanAdjust._netTime = null; 
      return false;
    }
    return true;
  }, false),
  ellipse: {
    semiMinorAxis: new Cesium.CallbackProperty(getTankerJizhanWaveRadius, false),
    semiMajorAxis: new Cesium.CallbackProperty(getTankerJizhanWaveRadius, false),
    material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(() => {
      if (Number(props.activePhaseIndex) < 8 || currentScene.value !== 'tanker' || !tankerJizhanAdjust._netTime) {
        return Cesium.Color.TRANSPARENT;
      }
      const alpha = Math.max(0, 1.0 - ((((Date.now() - tankerJizhanAdjust._netTime) / 1000.0) % 2.0) / 2.0));
      return Cesium.Color.CYAN.withAlpha(alpha * 0.6); // 保持科技蓝
    }, false)),
    height: new Cesium.CallbackProperty(() => tankerJizhanAdjust.height + 0.1, false),
  }
});

// (2) 油罐车基站头顶的主控面板
viewer.entities.add({
  id: 'jizhan-network-panel-tanker',
  position: new Cesium.CallbackProperty(() => {
    return Cesium.Cartesian3.fromDegrees(tankerJizhanAdjust.lng, tankerJizhanAdjust.lat, tankerJizhanAdjust.height + 6.5);
  }, false),
  show: new Cesium.CallbackProperty(() => {
    if (Number(props.activePhaseIndex) < 8 || currentScene.value !== 'tanker' || !tankerJizhanAdjust.show) {
       tankerJizhanAdjust._netTime = null; 
       return false;
    }
    return true;
  }, false),
  label: {
    text: new Cesium.CallbackProperty(() => {
      if (Number(props.activePhaseIndex) < 8 || currentScene.value !== 'tanker' || !tankerJizhanAdjust._netTime) return '';
      const elapsed = (Date.now() - tankerJizhanAdjust._netTime) / 1000.0;
      if (elapsed < 1.5) return `[CORE] 5G 核心网激活\n广播探测波纹...`;
      if (elapsed < 3.5) return `[CORE] 捕获设备握手请求\n分配密钥并开通专线...`;
      return `[CORE] 星型网络组网完毕\n▶ 主控链路: 稳定\n▶ 上行吞吐: 1.2 Gbps`;
    }, false),
    font: '14px monospace',
    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
    fillColor: Cesium.Color.CYAN,
    outlineColor: Cesium.Color.BLACK,
    outlineWidth: 2,
    showBackground: true,
    backgroundColor: new Cesium.Color(0.05, 0.1, 0.2, 0.8),
    backgroundPadding: new Cesium.Cartesian2(12, 12),
    pixelOffset: new Cesium.Cartesian2(0, -30),
    horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
    disableDepthTestDistance: Number.POSITIVE_INFINITY
  }
});
// ==========================================
// 2. 无人车端：游走 + 终端面板 + 链路
// ==========================================
// ==========================================
// 还原版：货车场景无人车端（阶段 8 开始游走 + 绿色连线）
// ==========================================
const truckRoadAngleRad = Cesium.Math.toRadians(45); 
const truckPatrolDistance = 0.00005;
const truckPatrolSpeed = 0.5;

rescueCarEntities.forEach((carEntity, modelIndex) => {
  
  // 🧹 每次热更新时，先铲除这台车之前绑定的旧实体，彻底消灭幽灵！
  [
    `network-label-car${modelIndex + 1}`, `network-label-car-safe${modelIndex + 1}`,
    `line-handshake-car${modelIndex + 1}-1`, `line-handshake-car-safe${modelIndex + 1}-1`,
    `line-handshake-car${modelIndex + 1}-2`, `line-handshake-car-safe${modelIndex + 1}-2`,
    `line-link-car${modelIndex + 1}-1-to-jizhan-real`, `line-link-car${modelIndex + 1}-2-to-jizhan-real`
  ].forEach(id => viewer.entities.removeById(id));

  const originalPosition = carEntity.position;
  let lastValidPos = undefined;

  // (1) 货车车辆游走
  carEntity.position = new Cesium.CallbackProperty((time) => {
    if (isPhase8Ready()) {
      const basePos = originalPosition ? originalPosition.getValue(time) : undefined;
      if (basePos) lastValidPos = basePos;
      const targetPos = basePos || lastValidPos;
      if (!targetPos) return undefined;

      const carto = Cesium.Cartographic.fromCartesian(targetPos);
      const wave = Math.sin((Date.now() / 1000.0) * truckPatrolSpeed + (modelIndex * Math.PI));
      const curLng = Cesium.Math.toDegrees(carto.longitude) + wave * truckPatrolDistance * Math.cos(truckRoadAngleRad);
      const curLat = Cesium.Math.toDegrees(carto.latitude) + wave * truckPatrolDistance * Math.sin(truckRoadAngleRad);

      return Cesium.Cartesian3.fromDegrees(curLng, curLat, carto.height);
    }
    return originalPosition ? originalPosition.getValue(time) : undefined;
  }, false);

  const isCarVisible = (time) => {
    let visible = carEntity.show;
    if (visible && typeof visible.getValue === 'function') visible = visible.getValue(time);
    return !!visible;
  };

  // (2) 货车车辆终端状态面板
  viewer.entities.add({
    id: `network-label-car${modelIndex + 1}`,
    position: new Cesium.CallbackProperty((time) => {
      const carPos = carEntity.position.getValue(time);
      if (!carPos) return undefined;
      const carto = Cesium.Cartographic.fromCartesian(carPos);
      return Cesium.Cartesian3.fromDegrees(Cesium.Math.toDegrees(carto.longitude), Cesium.Math.toDegrees(carto.latitude), carto.height + 3.5);
    }, false),
    show: new Cesium.CallbackProperty((time) => {
      if (currentScene.value !== 'truck') return false; 
      if (Number(props.activePhaseIndex) >= 9 && Number(props.activePhaseIndex) < 11 && isCarVisible(time)) return true;
      carEntity._netTime = null; 
      return false;
    }, false),
    label: {
      text: new Cesium.CallbackProperty(() => {
        if (currentScene.value !== 'truck') return '';
        if (Number(props.activePhaseIndex) < 9 || Number(props.activePhaseIndex) >= 11) return ''; 
        if (Number(props.activePhaseIndex) >= 10) {
           if (modelIndex === 0) return `[RELAY] 启用临时通信中继\n▶ 核心链路: 已接管\n▶ 延迟: 8ms`;
           return `▶ 环境数据流: ACTIVE\n▶ 上传至中继: 稳定`;
        }
        if (!carEntity._netTime) carEntity._netTime = Date.now();
        const elapsed = (Date.now() - carEntity._netTime) / 1000.0;
        if (elapsed < 1.5) return `[SYS] 扫描 5G 信号...`;
        if (elapsed < 3.5) return `[NET] 建立 WebSocket 专线...`;
        return `▶ 环境数据流: ACTIVE\n▶ 延迟: 12ms`;
      }, false),
      font: '14px monospace',
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      fillColor: new Cesium.CallbackProperty(() => (Number(props.activePhaseIndex) >= 10 && modelIndex === 0) ? Cesium.Color.GOLD : Cesium.Color.LIME, false),
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 2,
      showBackground: true,
      backgroundColor: new Cesium.Color(0.1, 0.1, 0.1, 0.8),
      backgroundPadding: new Cesium.Cartesian2(10, 10),
      
      // =====================================
      // 🌟 核心修复：双翼展开布局，货车面板也不会重叠了！
      // =====================================
      horizontalOrigin: modelIndex === 0 ? Cesium.HorizontalOrigin.RIGHT : Cesium.HorizontalOrigin.LEFT,
      pixelOffset: new Cesium.Cartesian2(modelIndex === 0 ? -30 : 30, -45),
      
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  });

  // (3) 货车场景链路绘制 
  [0, 1].forEach((innerCarIndex) => {
    viewer.entities.add({
      id: `line-link-car${modelIndex + 1}-${innerCarIndex + 1}-to-jizhan-real`,
      name: `货车动态中心数据链路`,
      show: new Cesium.CallbackProperty((time) => {
        if (currentScene.value !== 'truck') return false; 
        if (Number(props.activePhaseIndex) >= 10 && modelIndex === 0) return false;
        if (Number(props.activePhaseIndex) >= 9 && isCarVisible(time) && carEntity._netTime) {
           return ((Date.now() - carEntity._netTime) / 1000.0) >= 3.5; 
        }
        return false; 
      }, false),
      polyline: {
        positions: new Cesium.CallbackProperty((time) => {
          if (currentScene.value !== 'truck') return []; 
          if (Number(props.activePhaseIndex) < 9) return [];
          
          const carCartesian = carEntity.position.getValue(time);
          const carOrientation = carEntity.orientation.getValue(time);
          if (!carCartesian || !carOrientation) return [];

          const localOffset = new Cesium.Cartesian3(0.0, (innerCarIndex === 0) ? 1.5 : -1.5, 1.6);
          const rotationMatrix = Cesium.Matrix3.fromQuaternion(carOrientation);
          const worldOffset = Cesium.Matrix3.multiplyByVector(rotationMatrix, localOffset, new Cesium.Cartesian3());
          const startPos = Cesium.Cartesian3.add(carCartesian, worldOffset, new Cesium.Cartesian3());

          if (Number(props.activePhaseIndex) >= 10) {
            if (modelIndex === 0) return []; 
            const relayUgv = rescueCarEntities[0]; 
            if (relayUgv) {
              const ugv1Pos = relayUgv.position.getValue(time);
              if (ugv1Pos) return [startPos, ugv1Pos];
            }
            return [];
          }

          if (!jizhanAdjust || !jizhanAdjust.show) return []; 
          const jizhanTop = getModelTopPosition(
            jizhanAdjust.lng, jizhanAdjust.lat, jizhanAdjust.height,
            jizhanAdjust.heading, jizhanAdjust.pitch, jizhanAdjust.roll, JIZHAN_TOP_OFFSET
          );
          return [startPos, jizhanTop];
        }, false),
        width: 3.5,
        arcType: Cesium.ArcType.NONE,
        material: new DynamicFlowMaterialProperty({ color: Cesium.Color.CHARTREUSE, speed: 4.5, repeat: 6.0 })
      }
    });
  });
});
// ==========================================

  viewer.screenSpaceEventHandler.setInputAction((movement) => {
    const pickedObject = viewer.scene.pick(movement.position);
    if (Cesium.defined(pickedObject)) {
      const entity = pickedObject.id;
      const primitive = pickedObject.primitive;
      
      const entityId = entity ? entity.id : null;

      if (entityId === 'truck-light1-glb-entity' || entityId === 'light1-camera-marker') {
        if (currentScene.value === 'truck' && isLight1CameraUnlocked()) {
          openCameraStream('light1', movement);
        }
        return;
      }
      if (entityId === 'tanker-light23-glb-entity' || entityId === 'light23-camera-marker') {
        if (currentScene.value === 'tanker' && isLight23CameraUnlocked()) {
          openCameraStream('light23', movement);
        }
        return;
      }
      
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
          if (!props.focusedPointId) {
            overviewAccident.value = overviewAccidents[emitId];
            return;
          }
          emit('accident-picked', emitId);
          goToCloseView(emitId);
          return;
        }
      }
      
      // 2. 判断是否点击了地图上的定位标记或波浪光圈，若是则定位到远视角并展示事故图片悬浮窗
      if (entityId) {
        let emitId = null;
        if (entityId === 'accident_blue' || entityId === 'marker-accident_blue' || entityId === 'wave-accident_blue' || entityId === 'alert-marker-accident_blue') {
          emitId = 'accident_blue';
        } else if (entityId === 'accident_red' || entityId === 'marker-accident_red' || entityId === 'wave-accident_red' || entityId === 'alert-marker-accident_red') {
          emitId = 'accident_red';
        }
        
        if (emitId) {
          if (!props.focusedPointId) {
            overviewAccident.value = overviewAccidents[emitId];
            return;
          }
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

  if (index === 0) {
    startStageVehicleRunningTimeMs = 0;
    startStageVehicleLastFrameTime = Date.now();
    startStageVehicleAdjust.isPaused = false;
  } else if (index === 1) {
    startStageVehicleAdjust.isPaused = false;
  }

  if (animate && isFlying) {
    try {
      viewer.camera.cancelFlight();
    } catch (e) {}
    isFlying = false;
  }

  try {
    phase6StartTime = 0;
    tankerPhase6StartTime = 0;
    if (index !== 3) {
      phase3StartTime = 0;
      tankerPhase3StartTime = 0;
    }
    if (index !== 4) {
      phase4StartTime = 0;
      tankerPhase4StartTime = 0;
    } else {
      phase4StartTime = 0; // 强制重置货车追尾现场【无人机侦察】起始时间，使无人机从 200m 外向现场平滑飞行
      tankerPhase4StartTime = 0; // 强制重置油罐车泄露现场【无人机侦察】起始时间
    }
    if (index !== 7) {
      phase7StartTime = 0;
      tankerPhase7StartTime = 0;
    }
    if (index !== 8) {
      phase8StartTime = 0;
      tankerPhase8StartTime = 0;
    }
    if (index !== 9) {
      uavOrbitStartTime = 0;
      tankerUavOrbitStartTime = 0;
      capturedPhotos.value = [false, false, false, false];
      activePhotoIndex.value = null;
      flyingPhotos.value = [];
    }
    const phase = props.phases[index] || props.phases[0]
    const hasFocusedPoint = !!props.focusedPointId
    const pointId = hasFocusedPoint ? props.focusedPointId : 'gateway'
    const shouldSuppressAuxiliaryTraffic = pointId === 'accident_blue' && index === 3
    if (suppressAuxiliaryTrafficPoints.value !== shouldSuppressAuxiliaryTraffic) {
      suppressAuxiliaryTrafficPoints.value = shouldSuppressAuxiliaryTraffic
      // 保持用户当前的车流筛选状态，仅刷新阶段专属可见性。
      toggleVehicleFilter(activeVehicleFilter.value, true)
    }

    // 🗺️ 隐/显盘旋轨迹实体：仅在第5阶段“次生灾害（烟雾/泄露）”和第6阶段“次生灾害（起火/弥漫）”显现
    const isSmokeOrFirePhase = (index === 5 || index === 6);
    let isTruckScene = (pointId === 'accident_blue' || pointId === 'gateway' || !props.focusedPointId);
    let isTankerScene = (pointId === 'accident_red');

    ['uav-orbit-ring-glow-truck', 'uav-orbit-ring-flow-truck'].forEach(id => {
      const e = viewer.entities.getById(id);
      if (e) e.show = isTruckScene && isSmokeOrFirePhase;
    });
    ['uav-orbit-ring-glow-tanker', 'uav-orbit-ring-flow-tanker'].forEach(id => {
      const e = viewer.entities.getById(id);
      if (e) e.show = isTankerScene && isSmokeOrFirePhase;
    });
    ['uav-orbit-path-truck', 'uav-orbit-path-tanker'].forEach(id => {
      const e = viewer.entities.getById(id);
      if (e) e.show = false;
    });
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
      if (typeof currentScene !== 'undefined' && currentScene.value !== undefined) {
        currentScene.value = 'truck';
      }
      updateTruckSequence(index, pointId)
      if (leakParticle) leakParticle.show = false
      if (diffusionParticle) diffusionParticle.show = false
    } else if (pointId === 'accident_red') {
      if (typeof currentScene !== 'undefined' && currentScene.value !== undefined) {
        currentScene.value = 'tanker';
      }
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

    // 悬浮窗展示逻辑：在货车追尾现场和油罐车泄露现场的“无人装备出动阶段”(索引 7) 、 “无人感知部署阶段”(索引 8) 、 “救援装备出动阶段”(索引 9) 显示
    isTruckScene = (pointId === 'accident_blue');
    isTankerScene = (pointId === 'accident_red');

    activateStoryDetectionPopup(index)

    if ((isTruckScene || isTankerScene) && index === 11) {
      simulationPopup.show = true;
    } else {
      simulationPopup.show = false;
    }

    if (isTruckScene && index === 7) {
      // 无人机浮窗
      rescuePopup.title = '无人机出发';
      rescuePopup.model = 'DJI M300 RTK';
      rescuePopup.altitude = '100 m';
      rescuePopup.speed = '15 m/s';
      rescuePopup.status = '已出发';
      rescuePopup.xOffset = truckRescuePopupAdjust.xOffset;
      rescuePopup.yOffset = truckRescuePopupAdjust.yOffset;
      rescueCoords.lng = 113.202;
      rescueCoords.lat = 30.3268;
      rescueCoords.height = 120.0;
      // 无人车浮窗
      ugvPopup.title = '无人车出发';
      ugvPopup.model = 'SCOUT 2.0';
      ugvPopup.count = '2 辆';
      ugvPopup.speed = '5 km/h';
      ugvPopup.status = '已出发';
      ugvPopup.xOffset = truckUgvPopupAdjust.xOffset;
      ugvPopup.yOffset = truckUgvPopupAdjust.yOffset;
      ugvCoords.lng = 113.202;
      ugvCoords.lat = 30.3268;
      ugvCoords.height = 10.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
      ugvPopup.show = true;
    } else if (isTruckScene && index === 11) {
      rescuePopup.title = '救援车出动';
      rescuePopup.model = '多维救援协同';
      rescuePopup.altitude = '--';
      rescuePopup.speed = '协同编队';
      rescuePopup.status = '出动中';
      rescuePopup.xOffset = truckRescuePopupAdjust.xOffset;
      rescuePopup.yOffset = truckRescuePopupAdjust.yOffset;
      rescueCoords.lng = 113.202;
      rescueCoords.lat = 30.3268;
      rescueCoords.height = 120.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
      ugvPopup.show = false;

      if (!window.__multiAgentTriggeredFor || window.__multiAgentTriggeredFor !== 'truck') {
          window.__multiAgentTriggeredFor = 'truck';
          rescueDispatchScene.value = 'crash';
          triggerRescueMultiAgent();
      }
    } else if (isTankerScene && index === 7) {
      // 油罐车场景无人机
      rescuePopup.title = '无人机出发';
      rescuePopup.model = 'DJI M300 RTK';
      rescuePopup.altitude = String(Math.round(tankerUavAdjust.height)) + ' m';
      rescuePopup.speed = '12 m/s';
      rescuePopup.status = '已出发';
      rescuePopup.xOffset = tankerRescuePopupAdjust.xOffset;
      rescuePopup.yOffset = tankerRescuePopupAdjust.yOffset;
      rescueCoords.lng = 114.9238;
      rescueCoords.lat = 30.5158;
      rescueCoords.height = tankerUavAdjust.height + 10.0;
      // 油罐车场景无人车
      ugvPopup.title = '无人车出发';
      ugvPopup.model = 'SCOUT 2.0';
      ugvPopup.count = '2 辆';
      ugvPopup.speed = '5 km/h';
      ugvPopup.status = '已出发';
      ugvPopup.xOffset = tankerUgvPopupAdjust.xOffset;
      ugvPopup.yOffset = tankerUgvPopupAdjust.yOffset;
      ugvCoords.lng = 114.9238;
      ugvCoords.lat = 30.5158;
      ugvCoords.height = 15.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = true;
      rescuePopup.show = true;
      ugvPopup.show = true;
    } else if (isTankerScene && index === 11) {
      rescuePopup.title = '救援车出动';
      rescuePopup.model = '多维救援协同';
      rescuePopup.altitude = '--';
      rescuePopup.speed = '协同编队';
      rescuePopup.status = '出动中';
      rescuePopup.xOffset = tankerRescuePopupAdjust.xOffset;
      rescuePopup.yOffset = tankerRescuePopupAdjust.yOffset;
      rescueCoords.lng = tankerPointAdjust.lng;
      rescueCoords.lat = tankerPointAdjust.lat;
      rescueCoords.height = 17.0;
      
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
      ugvPopup.show = false;

      if (!window.__multiAgentTriggeredFor || window.__multiAgentTriggeredFor !== 'leak') {
          window.__multiAgentTriggeredFor = 'leak';
          rescueDispatchScene.value = 'leak';
          triggerRescueMultiAgent();
      }
    } else {
      if (rescueMarkerEntity) rescueMarkerEntity.show = false;
      rescuePopup.show = false;
      ugvPopup.show = false;
    }

    if (index === 10) {
      prepareRescueRoutes(currentScene.value === 'truck' ? 'crash' : 'leak').catch(error => console.warn('[救援路线预加载]', error));
    }
    if (index >= 3) {
      const expectedEndpoint = currentScene.value === 'truck' ? 'crash' : 'leak';
      const needsMultiAgent = (index === 11);
      if (
        !currentMissionDataSource ||
        currentMissionDataSource._lastEndpoint !== expectedEndpoint ||
        !!currentMissionDataSource._isMultiAgent !== needsMultiAgent
      ) {
        loadMission(needsMultiAgent);
      }

      // 同事的补丁：如果数据源已加载，显式确保规划路线可见，防止 Bug 导致线段丢失
      if (currentMissionDataSource) {
          // 第 12 阶段仅保留多智能体救援路线，避免等待救援规划时残留无人装备路线。
          const showAutonomousUavRoute = index >= 3 && index < 11;
          const showAutonomousUgvRoute = index >= 7 && index < 11;
          const hideTruckUavDispatchTelemetry = pointId === 'accident_blue' && index === 3;
          const uavPath = currentMissionDataSource.entities.getById('UAV_Path');
          if (uavPath) {
            uavPath.show = showAutonomousUavRoute;
            if (uavPath.polyline) uavPath.polyline.show = showAutonomousUavRoute;
          }
          const uavPathGlow = currentMissionDataSource.entities.getById('UAV_Path_glow');
          if (uavPathGlow) {
            uavPathGlow.show = showAutonomousUavRoute;
            if (uavPathGlow.polyline) uavPathGlow.polyline.show = showAutonomousUavRoute;
          }

          const carPath = currentMissionDataSource.entities.getById('Car_Path');
          if (carPath) {
            carPath.show = showAutonomousUgvRoute;
            if (carPath.polyline) carPath.polyline.show = showAutonomousUgvRoute;
          }
          const carPathGlow = currentMissionDataSource.entities.getById('Car_Path_glow');
          if (carPathGlow) {
            carPathGlow.show = showAutonomousUgvRoute;
            if (carPathGlow.polyline) carPathGlow.polyline.show = showAutonomousUgvRoute;
          }
          const czmlCar = currentMissionDataSource.entities.getById('Car');
          if (czmlCar) {
            czmlCar.show = showAutonomousUgvRoute;
          }
          if (highlightPathEntity) {
            highlightPathEntity.show = showAutonomousUgvRoute;
            if (highlightPathEntity.polyline) highlightPathEntity.polyline.show = showAutonomousUgvRoute;
          }
          const highlightPath = viewer && viewer.entities ? viewer.entities.getById('Car_Path_Highlight') : null;
          if (highlightPath) {
            highlightPath.show = showAutonomousUgvRoute;
            if (highlightPath.polyline) highlightPath.polyline.show = showAutonomousUgvRoute;
          }
          const czmlUav = currentMissionDataSource.entities.getById('UAV');
          if (czmlUav) {
            // 保留主无人机的红色大位置点；仅隐藏路径上的小型进度检查点。
            czmlUav.show = showAutonomousUavRoute;
          }
          syncAutonomousRouteTelemetry(currentMissionDataSource, hideTruckUavDispatchTelemetry)

          // 多智能体路径在第 12 阶段(index 11)“救援装备出动”及后续显示
          const multiAgentPrefixes = ['Agent_', 'AgentPath_', 'AgentPOI_', 'AgentCP_'];
          currentMissionDataSource.entities.values.forEach(entity => {
              const id = entity.id;
              if (id) {
                  if (id.startsWith('AgentCP_') || id === 'StartMarker') {
                      // 仅仅隐藏中间集散点(CP)与重复起点(StartMarker)
                      entity.show = false;
                  } else if (multiAgentPrefixes.some(prefix => id.startsWith(prefix))) {
                      const shouldShow = (index >= 11);
                      entity.show = shouldShow;
                  }
              }
          });
      }

      // 根据用户要求，当在货车或油罐车现场进入"无人装备出动"(阶段7)时，视角飞向微调面板中对应的视角，支持动态同步
      if ((pointId === 'accident_blue' || pointId === 'accident_red') && index === 7) {
        stopAutoRotate();
        const sceneKey = pointId === 'accident_red' ? 'tanker' : 'truck';
        const cfg = defaultPhaseCameraConfigs[sceneKey][8];
        const headingRad = Cesium.Math.toRadians(cfg.heading);
        const pitchRad = Cesium.Math.toRadians(cfg.pitch);
        const range = cfg.range;
        const targetLng = sceneKey === 'tanker' ? (Number(tankerPointAdjust.lng) || 114.894472) : (Number(truckAdjust.lng) || 113.104833);
        const targetLat = sceneKey === 'tanker' ? (Number(tankerPointAdjust.lat) || 30.632203) : (Number(truckAdjust.lat) || 30.385469);
        const targetCartesian = Cesium.Cartesian3.fromDegrees(targetLng, targetLat, 0);

        if (animate) {
          try {
            viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
          } catch (e) {}
          isFlying = true;
          viewer.camera.flyToBoundingSphere(new Cesium.BoundingSphere(targetCartesian, 0), {
            offset: new Cesium.HeadingPitchRange(headingRad, pitchRad, range),
            duration: 0.6,
            complete: () => {
              isFlying = false;
              try {
                if (viewer && !spinCallback) {
                  viewer.camera.lookAt(targetCartesian, new Cesium.HeadingPitchRange(headingRad, pitchRad, range));
                }
              } catch (e) {}
            },
            cancel: () => {
              isFlying = false;
            }
          });
        } else {
          try {
            viewer.camera.lookAt(targetCartesian, new Cesium.HeadingPitchRange(headingRad, pitchRad, range));
          } catch (e) {
            viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
            viewer.camera.lookAt(targetCartesian, new Cesium.HeadingPitchRange(headingRad, pitchRad, range));
          }
        }
      }
    } else {
      if (currentMissionDataSource) {
        viewer.dataSources.remove(currentMissionDataSource);
        currentMissionDataSource = null;
      }
      if (highlightPathEntity) {
        viewer.entities.remove(highlightPathEntity);
        highlightPathEntity = null;
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

      // 恢复正常的时间流速（第 12 阶段保持多智能体播放倍速）
      if (index !== 11) {
        viewer.clock.multiplier = 1.0;
      }
    }

    if (popupEntity) {
      // 隐藏悬浮窗和连接线（根据用户要求取消显示）
      popupEntity.show = false
      if (connectionLineEntity) connectionLineEntity.show = false

      if (index === 10) {
      prepareRescueRoutes(currentScene.value === 'truck' ? 'crash' : 'leak').catch(error => console.warn('[救援路线预加载]', error));
    }
    if (index >= 3) {
        // 在货车追尾现场的无人机阶段显示无人机模型和救援车并隐藏所有粒子效果
        if (pointId === 'accident_blue') {
          uavEntities.forEach(entity => {
            let isTarget = false;
            if (index >= 3 && index <= 6) {
              isTarget = (entity.id === 'uav_model' || entity.id === 'uav_model_move');
            } else if (index === 7 || index === 8) {
              isTarget = (entity.id === 'uav_model_move');
            } else if (index >= 9) {
              isTarget = entity.id.includes('move');
            }

            if (isTarget) {
              entity.show = true;
              playEntityAnimation(entity, true, 0, 6.0);
            } else {
              entity.show = false;
            }
          });
          // 恢复显示救援车模型（只有进入“无人装备出动”至“信号干扰阶段”才显示无人车，第12阶段自动隐藏，腾出干净屏幕）
          rescueCarEntities.forEach(entity => { entity.show = (index >= 7 && index < 11); });
          
          // 隐藏油罐车场景的无人机和救援车
          tankerUavEntities.forEach(entity => { entity.show = false });
          tankerRescueCarEntities.forEach(entity => { entity.show = (pointId === 'accident_red' && index >= 7 && index < 11); });
          
          // 隐藏所有泄露和扩散粒子，但保留货车场景所需的烟雾与火焰粒子（由 updateTruckSequence 控制其具体大小）
          if (leakParticle) leakParticle.show = false
          if (diffusionParticle) diffusionParticle.show = false
          if (index >= 8) {
            if (smokeParticle) smokeParticle.show = false
            if (fireParticle) fireParticle.show = false
          }
        } else if (pointId === 'accident_red') {
          // 在油罐车泄露现场的无人机阶段显示无人机模型和救援车并隐藏所有粒子效果
          tankerUavEntities.forEach(entity => {
            let isTarget = false;
            if (index >= 3 && index <= 6) {
              isTarget = (entity.id === 'uav_model_tanker' || entity.id === 'uav_model_move_tanker');
            } else if (index === 7 || index === 8) {
              isTarget = (entity.id === 'uav_model_move_tanker');
            } else if (index >= 9) {
              isTarget = entity.id.includes('move');
            }

            if (isTarget) {
              entity.show = true;
              playEntityAnimation(entity, true, 0, 6.0);
            } else {
              entity.show = false;
            }
          });
          tankerRescueCarEntities.forEach(entity => { entity.show = (index >= 7 && index < 11); });
          
          // 隐藏货车场景的无人机和救援车
          uavEntities.forEach(entity => { entity.show = false })
          rescueCarEntities.forEach(entity => { entity.show = false })
          
          // 隐藏货车的烟雾与火焰，但根据阶段显示油罐车的泄露与扩散粒子
          if (smokeParticle) smokeParticle.show = false
          if (fireParticle) fireParticle.show = false
          if (leakParticle) leakParticle.show = (index >= 5)
          if (diffusionParticle) diffusionParticle.show = (index >= 6)
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
  // 告警标记只在综合态势总览显示，故事线的全部阶段均隐藏。
  const showMarkers = !props.focusedPointId;
  const entitiesToToggle = [
    'marker-accident_blue', 'wave-accident_blue', 'alert-marker-accident_blue',
    'marker-accident_red', 'wave-accident_red', 'alert-marker-accident_red'
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
  
  light1Unlocked.value = false
  light23Unlocked.value = false
  cameraStreamPopup.show = false

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
  
  if (pointId === 'accident_blue') {
    light1Unlocked.value = true;
  } else if (pointId === 'accident_red') {
    light23Unlocked.value = true;
  }

  accidentDetailPopup.show = false
  accidentViewLevel.value = 'medium'
  updateMarkerVisibility()
  isFlying = true
  
  try {
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  } catch (e) {}

  let lng = point.longitude
  let lat = point.latitude
  if (pointId === 'accident_blue') {
    lng = truckAdjust.lng; lat = truckAdjust.lat;
  } else if (pointId === 'accident_red') {
    lng = tankerPointAdjust.lng; lat = tankerPointAdjust.lat;
  }

  const target = Cesium.Cartesian3.fromDegrees(lng, lat, 0)
  const pIdx = (props.activePhaseIndex !== undefined && props.activePhaseIndex !== null) ? (props.activePhaseIndex + 1) : 1
  const scene = pointId === 'accident_red' ? 'tanker' : 'truck'
  const cfg = (defaultPhaseCameraConfigs[scene] && defaultPhaseCameraConfigs[scene][pIdx]) || { range: 600, pitch: -11, heading: -39 }

  const range = cfg.range
  const pitch = Cesium.Math.toRadians(cfg.pitch)
  const finalHeading = Cesium.Math.toRadians(cfg.heading)

  viewer.camera.flyToBoundingSphere(new Cesium.BoundingSphere(target, 0), {
    offset: new Cesium.HeadingPitchRange(finalHeading, pitch, range),
    duration: 1.5,
    complete: () => {
      isFlying = false
      try {
        if (viewer && !spinCallback) {
          viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(finalHeading, pitch, range));
        }
      } catch (e) {}
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

watch(() => props.landingView, () => { resetView() })

let isOverviewTransition = false
let overviewAnimationFrame = 0

function resetView() {
  if (!viewer) return
  cancelAnimationFrame(overviewAnimationFrame)
  viewer.camera.cancelFlight()
  light1Unlocked.value = false
  light23Unlocked.value = false
  cameraStreamPopup.show = false
  accidentDetailPopup.show = false
  stopAutoRotate()
  const camera = viewer.camera
  camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  const target = Cesium.Cartesian3.fromDegrees(DEFAULT_OVERVIEW.longitude, DEFAULT_OVERVIEW.latitude, 0)
  const frame = Cesium.Transforms.eastNorthUpToFixedFrame(target)
  const inverse = Cesium.Matrix4.inverseTransformation(frame, new Cesium.Matrix4())
  const local = Cesium.Matrix4.multiplyByPoint(inverse, camera.positionWC, new Cesium.Cartesian3())
  const startRange = Cesium.Cartesian3.magnitude(local)
  const startPitch = -Math.asin(Cesium.Math.clamp(local.z / Math.max(startRange, 1), -1, 1))
  const startHeading = Math.atan2(-local.x, -local.y)
  const endRange = props.landingView ? LANDING_VIEW_RANGE : DEFAULT_OVERVIEW.range
  const endPitch = Cesium.Math.toRadians(props.landingView ? LANDING_VIEW_PITCH : -57)
  const started = performance.now()
  isOverviewTransition = true
  isFlying = true
  const step = (now) => {
    if (!viewer || viewer.isDestroyed()) return
    const t = Math.min((now - started) / 1200, 1)
    const eased = t * t * (3 - 2 * t)
    camera.lookAt(target, new Cesium.HeadingPitchRange(
      startHeading * (1 - eased),
      startPitch + (endPitch - startPitch) * eased,
      startRange + (endRange - startRange) * eased
    ))
    if (t < 1) {
      overviewAnimationFrame = requestAnimationFrame(step)
    } else {
      camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
      isFlying = false
      isOverviewTransition = false
      overviewAnimationFrame = 0
    }
  }
  overviewAnimationFrame = requestAnimationFrame(step)
}

defineExpose({ 
  setMapVehicleCategory: (category) => toggleVehicleFilter(category, true),
  zoomToPoint, 
  resetView, 
  capturedPhotos, 
  activePhotoIndex, 
  currentTimeStr,
  triggerPhaseReplay: (idx) => updatePhaseScene(Number(idx), false)
});

watch(
  () => [props.activePhaseIndex, props.phases?.[props.activePhaseIndex]?.id, props.phases?.[0]?.id],
  ([phaseIndex]) => {
    activateStoryDetectionPopup(Number(phaseIndex))
  },
  { immediate: true, flush: 'post' }
)

watch(() => props.activePhaseIndex, (next, prev) => {
  const shouldShowPopup = Number(next) === 9;
  secondaryDisasterVideoPopup.show = shouldShowPopup;
  if (shouldShowPopup) {
    isReconstructionPanelVisible.value = true;
  }
  if (Number(next) === 11) {
    simulationPopup.show = true;
  } else {
    simulationPopup.show = false;
  }
  // 每次重新进入无人感知执行，都必须等待本轮采集与重建完成。
  if (Number(next) === 9 && Number(prev) !== 9) {
    emit('reconstruction-ready', false)
  }
  accidentViewLevel.value = null;
  stopAutoRotate();
  if (next === 4 && prev !== 4) {
    phase6StartTime = Date.now();
    tankerPhase6StartTime = Date.now();
  } else if (next === 5 || next === 6) {
    uavOrbitStartTime = Date.now();
    tankerUavOrbitStartTime = Date.now();
  } else if (next === 7 && prev !== 7) {
    phase7StartTime = Date.now();
    tankerPhase7StartTime = Date.now();
  } else if (next === 8 && prev !== 8) {
    phase8StartTime = Date.now();
    tankerPhase8StartTime = Date.now();
  } else if (next === 11) {
    // 进入第 12 阶段(index 11)时自动执行救援装备出动，这里只更新 pending 文本状态，
    // 具体的 CZML 生成与数据加载交给 updatePhaseScene 通用逻辑中唯一的 loadMission 调用，防止并发冲突！
    rescueDispatchScene.value = currentScene.value === 'truck' ? 'crash' : 'leak';
    rescueDispatchPending.value = true;
    rescueDispatchStatus.value = '救援装备出动中...';
  } else if (next < 3) {
    phase3StartTime = 0;
    tankerPhase3StartTime = 0;
    phase6StartTime = 0;
    tankerPhase6StartTime = 0;
    phase7StartTime = 0;
    tankerPhase7StartTime = 0;
    phase8StartTime = 0;
    tankerPhase8StartTime = 0;
    uavOrbitStartTime = 0;
    tankerUavOrbitStartTime = 0;
  }
  
  if (next >= 4 && (prev < 4 || !diffusionStartTime)) {
    diffusionStartTime = Date.now();
  } else if (next < 4) {
    diffusionStartTime = 0;
  }

  // 同步 Cesium 时钟时间与动画播放状态
  if (viewer) {
    viewer.clock.shouldAnimate = true;
    if (next === 11) {
      viewer.clock.multiplier = Number(agentSpeedConfig.multiAgentMultiplier) || 20;
      if (currentMissionDataSource && currentMissionDataSource.clock) {
        viewer.clock.currentTime = currentMissionDataSource.clock.startTime;
      }
    } else {
      viewer.clock.multiplier = 1.0;
    }
    viewer.clock.clockRange = Cesium.ClockRange.UNBOUNDED;
  }

  // 自动对齐场景并加载该阶段配置；未进入故事线时保持主页地图态
  if (props.focusedPointId) {
    const scene = props.focusedPointId === 'accident_red' ? 'tanker' : 'truck'
    cameraAdjust.scene = scene
    cameraAdjust.phaseIndex = next + 1
    const cfg = (defaultPhaseCameraConfigs[scene] && defaultPhaseCameraConfigs[scene][next + 1]) || { range: 1440, pitch: -39, heading: -5 }
    cameraAdjust.range = cfg.range
    cameraAdjust.pitch = cfg.pitch
    cameraAdjust.heading = cfg.heading
  }

  updatePhaseScene(next, false);
}, { immediate: true, flush: 'post' });

watch(() => [props.landingView, props.activePhaseIndex, accidentViewLevel.value], () => {
  updateMarkerVisibility()
})

watch(() => props.focusedPointId, (newVal, oldVal) => {
  if (newVal === oldVal) return;
  if (newVal) {
    if (props.activePhaseIndex === undefined || props.activePhaseIndex === null || props.activePhaseIndex < 0) {
      accidentViewLevel.value = 'far'
    } else {
      accidentViewLevel.value = null
    }
  } else {
    accidentDetailPopup.show = false
    cameraStreamPopup.show = false
    light1Unlocked.value = false
    light23Unlocked.value = false
  }
  if (newVal === 'accident_blue') {
    if (typeof currentScene !== 'undefined') {
      currentScene.value = 'truck'
    }
  } else if (newVal === 'accident_red') {
    if (typeof currentScene !== 'undefined') {
      currentScene.value = 'tanker'
    }
  }
  // 切换场景时，重置初始车流时间并使其开始运动
  startStageVehicleRunningTimeMs = 0;
  startStageVehicleLastFrameTime = Date.now();
  startStageVehicleAdjust.isPaused = false;
  
  updateMarkerVisibility()
  updatePhaseScene(props.activePhaseIndex, false);
});

onMounted(() => {
  initViewer()
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
})
onActivated(() => {
  isComponentActive.value = true
  if (viewer && !viewer.isDestroyed()) {
    try {
      viewer.resize()
      viewer.scene.requestRender()
    } catch (e) {}
  }
  // 从子模块返回地图大屏首页时，自动重置并重新构建车辆与赛博标牌，确保牌子 100% 恢复正常显示
  if (cachedHubeiGeojson) {
    reApplyTrafficRoutes()
  }
})
onDeactivated(() => {
  isComponentActive.value = false
})
onBeforeUnmount(() => {

  cancelAnimationFrame(overviewAnimationFrame)
  stopAutoRotate()
  if (timeInterval) {
    clearInterval(timeInterval)
    timeInterval = null
  }
  if (hudStatsTimer) {
    clearInterval(hudStatsTimer)
    hudStatsTimer = null
  }
  clearDetectionTimer()
  if (animationCheckTimer) {
    clearInterval(animationCheckTimer)
    animationCheckTimer = null
  }
  if (initViewerTimeout) {
    clearTimeout(initViewerTimeout)
    initViewerTimeout = null
  }
  if (hoverHandler) {
    hoverHandler.destroy()
    hoverHandler = null
  }
  if (trafficAnimationRemoveListener) {
    trafficAnimationRemoveListener()
    trafficAnimationRemoveListener = null
  }
  if (removeLightListener) {
    removeLightListener()
    removeLightListener = null
  }
  if (debugHandler) {
    debugHandler.destroy()
    debugHandler = null
  }
  if (viewer) {
    viewer.scene.postRender.removeEventListener(updateModelsReadyStatus)
    viewer.scene.postRender.removeEventListener(updatePopupPosition)
    if (smokeParticle) {
      viewer.scene.primitives.remove(smokeParticle)
      smokeParticle = null
    }
    if (fireParticle) {
      viewer.scene.primitives.remove(fireParticle)
      fireParticle = null
    }
    if (leakParticle) {
      viewer.scene.primitives.remove(leakParticle)
      leakParticle = null
    }
    if (diffusionParticle) {
      viewer.scene.primitives.remove(diffusionParticle)
      diffusionParticle = null
    }

    try {
      if (viewer && !viewer.isDestroyed()) {
        viewer.destroy()
      }
    } catch (destroyError) {
      console.warn('销毁 viewer 时出错:', destroyError)
    }
    viewer = null
    window.viewer = null
  }
})

// ================================================================
// 🚨 救援装备出动操控面板 (对应故事线阶段 11 - activePhaseIndex === 11)
// 功能与协同响应三维态势地图的"救援装备出动"面板完全一致
// ================================================================
const rescueDispatchScene = ref('crash')  // 'crash' | 'leak'
const rescueDispatchPending = ref(false)
const rescueDispatchStatus = ref('')

// 自动根据当前故事线场景同步选择事故场景
watch(
  () => props.phases,
  (phases) => {
    if (!phases || phases.length === 0) return
    const firstId = phases[0]?.id || ''
    if (firstId.startsWith('t-')) {
      rescueDispatchScene.value = 'crash'
    } else if (firstId.startsWith('l-')) {
      rescueDispatchScene.value = 'leak'
    }
  },
  { immediate: true }
)

function buildCommandCenterApiUrl(path) {
  const base = getCollaborativeCommandCenterBaseUrl().replace(/\/+$/, '')
  return `${base}/${path.replace(/^\/+/, '')}`
}

// ============================================================
// 协同响应效能指标悬浮窗 — 数据层
// ============================================================
const strategyMetricsPanel = reactive({
  show: false,
  loading: false,
  data: null,
  updatedAt: '',
})

let _metricsPollingTimer = null

async function fetchStrategyMetrics() {
  strategyMetricsPanel.loading = true
  try {
    const url = buildCommandCenterApiUrl('api/strategy_metrics')
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error('HTTP ' + res.status)
    const data = await res.json()
    if (data && data.available !== false) {
      strategyMetricsPanel.data = data
      // 格式化更新时间
      if (data.updated_at) {
        try {
          strategyMetricsPanel.updatedAt = new Date(data.updated_at).toLocaleTimeString('zh-CN', { hour12: false })
        } catch {
          strategyMetricsPanel.updatedAt = ''
        }
      }
    } else {
      strategyMetricsPanel.data = null
    }
  } catch {
    // 网络不通时保留旧数据，不报错
  } finally {
    strategyMetricsPanel.loading = false
  }
}

function startMetricsPolling() {
  fetchStrategyMetrics()
  if (!_metricsPollingTimer) {
    _metricsPollingTimer = setInterval(fetchStrategyMetrics, 5000)
  }
}

function stopMetricsPolling() {
  if (_metricsPollingTimer) {
    clearInterval(_metricsPollingTimer)
    _metricsPollingTimer = null
  }
}

// 监听阶段变化：仅在无人装备出动 (7) 时展示效能指标悬浮窗
watch(
  () => props.activePhaseIndex,
  (newIdx) => {
    const phase = Number(newIdx)
    if (phase === 7) {
      strategyMetricsPanel.show = true
      startMetricsPolling()
    } else {
      strategyMetricsPanel.show = false
      stopMetricsPolling()
    }
  },
  { immediate: true }
)

// 组件卸载时清理 timer
onBeforeUnmount(() => {
  stopMetricsPolling()
})

// ============================================================
// 多智能体全局寻优决策日志悬浮窗 — 数据层 (phase 11 救援装备出动)
// ============================================================
const multiAgentLogPanel = reactive({
  show: false,
  loading: false,
  data: null,   // multi_agent 字段：{ scenario, agents: { medical, fire, police, hazmat, road } }
})

const selectedAgentKey = ref('fire')
const agentShortNames = {
  fire: '消防',
  hazmat: '防化',
  medical: '医疗',
  police: '公安',
  road: '路政'
}

let _agentLogPollingTimer = null

async function fetchMultiAgentLog() {
  multiAgentLogPanel.loading = true
  try {
    // 必须传入 scenario 参数，后台才能加载对应的 multi_agent_result_{scenario}.json
    const scenario = rescueDispatchScene.value || 'crash'
    const url = buildCommandCenterApiUrl(`api/strategy_metrics?scenario=${scenario}`)
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error('HTTP ' + res.status)
    const payload = await res.json()
    // 取 multi_agent 子字段
    if (payload && payload.multi_agent && payload.multi_agent.agents) {
      multiAgentLogPanel.data = payload.multi_agent
    } else {
      multiAgentLogPanel.data = null
    }
  } catch {
    // 网络不通时保留旧数据
  } finally {
    multiAgentLogPanel.loading = false
  }
}

function startAgentLogPolling() {
  fetchMultiAgentLog()
  if (!_agentLogPollingTimer) {
    _agentLogPollingTimer = setInterval(fetchMultiAgentLog, 5000)
  }
}

function stopAgentLogPolling() {
  if (_agentLogPollingTimer) {
    clearInterval(_agentLogPollingTimer)
    _agentLogPollingTimer = null
  }
}

// 监听阶段变化：进入救援装备出动 (11) 时展示多智能体决策日志
watch(
  () => props.activePhaseIndex,
  (newIdx) => {
    const phase = Number(newIdx)
    if (phase === 11) {
      multiAgentLogPanel.show = true
      startAgentLogPolling()
    } else {
      multiAgentLogPanel.show = false
      stopAgentLogPolling()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  stopAgentLogPolling()
})

// 无人装备出动 (镜像 triggerCesiumUGVUAV)
async function triggerRescueUGVUAV() {
  rescueDispatchPending.value = true
  rescueDispatchStatus.value = '无人装备出动中...'
  try {
    const url = buildCommandCenterApiUrl(`api/run_3d_cesium?end_point=${rescueDispatchScene.value}`)
    const r = await fetch(url)
    if (!r.ok) throw new Error('HTTP ' + r.status)
    rescueDispatchStatus.value = '✅ 无人装备已出动'
  } catch (e) {
    rescueDispatchStatus.value = '失败: ' + (e instanceof Error ? e.message : String(e))
  } finally {
    rescueDispatchPending.value = false
    setTimeout(() => { rescueDispatchStatus.value = '' }, 4000)
  }
}

// 救援装备出动 (镜像 triggerCesiumMultiAgent，strategy 固定为 rcd)
async function triggerRescueMultiAgent() {
  rescueDispatchPending.value = true
  rescueDispatchStatus.value = '救援装备出动中...'
  try {
    // 强制加载包含协同救援规划路线的 CZML，它内部会调用 api/run_multi_agent 接口
    if (typeof loadMission === 'function') {
        await loadMission(true);
    } else {
        const url = buildCommandCenterApiUrl(`api/run_multi_agent?end_point=${rescueDispatchScene.value}&strategy=rcd`)
        const r = await fetch(url)
        if (!r.ok) throw new Error('HTTP ' + r.status)
    }
    // 路线数据源装载完成后立即刷新决策日志；不再等待下一轮 5 秒轮询，
    // 保证五类路线与右上角寻优结果同步出现。
    await fetchMultiAgentLog()
    rescueDispatchStatus.value = '✅ 救援装备已出动'
  } catch (e) {
    rescueDispatchStatus.value = '失败: ' + (e instanceof Error ? e.message : String(e))
  } finally {
    rescueDispatchPending.value = false
    setTimeout(() => { rescueDispatchStatus.value = '' }, 4000)
  }
}
</script>

<style scoped>
.accident-detail-backdrop { position: absolute; inset: 0; z-index: 3000; display: grid; place-items: center; background: #00101c99; padding: 24px; }
.accident-detail { width: min(900px, 92vw); max-height: 85vh; overflow: auto; padding: 24px; box-sizing: border-box; background: linear-gradient(135deg,#092c3b,#061521); color: #dff7ff; border: 1px solid #d9ac44; border-radius: 12px; box-shadow: 0 24px 80px #0009; }
.accident-detail header,.accident-detail footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; } .accident-detail header { color: #ffd878; } .accident-detail h2 { margin: 18px 0; font-size: 25px; } .overview-accident-body { display: grid; grid-template-columns: 1.1fr 1fr; gap: 24px; } .accident-detail figure { margin: 0; } .accident-detail img { width: 100%; height: 250px; object-fit: cover; border-radius: 6px; } .accident-detail figcaption,.accident-detail footer span { font-size: 12px; color: #9bbac6; } .accident-detail p { line-height: 1.8; margin: 0 0 12px; } .accident-detail-date { color: #ffd878; } .accident-detail a { color: #63e4ff; } .accident-detail footer { justify-content: flex-end; margin-top: 24px; border-top: 1px solid #285164; padding-top: 16px; } .accident-detail button { color: #e8fbff; background: #105168; border: 1px solid #3ba6c3; padding: 9px 16px; border-radius: 5px; cursor: pointer; } @media(max-width: 700px) { .overview-accident-body { grid-template-columns: 1fr; } }
/* 仿真推演悬浮窗样式 */
.simulation-popup-panel {
  position: absolute;
  width: 320px;
  background: rgba(10, 18, 30, 0.72);
  border: 1px solid rgba(0, 255, 180, 0.35);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.65), 0 0 20px rgba(0, 255, 180, 0.15);
  z-index: 1000;
  overflow: hidden;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  pointer-events: auto;
  transform: translate(-50%, -100%);
  animation: simPanelFadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #f8fafc;
}
.simulation-popup-panel:hover {
  border-color: rgba(0, 255, 180, 0.65);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.75), 0 0 24px rgba(0, 255, 180, 0.28);
  transform: translate(-50%, -101%) scale(1.01);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
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
  background: linear-gradient(90deg, rgba(0, 255, 180, 0.15) 0%, transparent 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.simulation-popup-header .header-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.simulation-popup-header .header-title {
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 1px;
}

.pulse-indicator {
  width: 6px;
  height: 6px;
  background: #00ffb4;
  border-radius: 50%;
  box-shadow: 0 0 8px #00ffb4;
  display: inline-block;
  animation: header-pulse 1.5s infinite;
}
@keyframes header-pulse {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

.simulation-popup-panel .close-btn {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.simulation-popup-panel .close-btn:hover {
  color: #ff4757;
}

.simulation-popup-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-tag-row {
  display: flex;
  gap: 6px;
}

.status-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
}
.status-tag.ready {
  color: #00ffb4;
  background: rgba(0, 255, 180, 0.1);
  border: 1px solid rgba(0, 255, 180, 0.2);
}
.status-tag.info {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.2);
}

.simulation-popup-content .desc-text {
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.82);
  margin: 0;
}

.enter-sim-btn {
  width: 100%;
  padding: 10px 14px;
  background: linear-gradient(135deg, rgba(0, 255, 180, 0.15) 0%, rgba(0, 150, 255, 0.15) 100%);
  border: 1px solid rgba(0, 255, 180, 0.35);
  color: #00ffcc;
  border-radius: 6px;
  font-size: 13px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-shadow: 0 0 5px rgba(0, 255, 180, 0.6);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.enter-sim-btn:hover {
  background: linear-gradient(135deg, rgba(0, 255, 180, 0.28) 0%, rgba(0, 150, 255, 0.28) 100%);
  border-color: #00ffb4;
  box-shadow: 0 0 12px rgba(0, 255, 180, 0.4);
  transform: scale(1.02);
}
.enter-sim-btn .arrow-svg {
  transition: transform 0.3s ease;
}
.enter-sim-btn:hover .arrow-svg {
  transform: translateX(4px);
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
  border-top: 10px solid rgba(10, 18, 30, 0.72);
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

.rect-leak {
  stroke: #10b981;
}
.label-leak {
  fill: #a7f3d0;
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
.detect-item.leak .item-conf { color: #34d399; }

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


.camera-stream-popup {
  position: absolute;
  width: 480px;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  border: 1px solid rgba(56, 189, 248, 0.42);
  border-radius: 8px;
  background: rgba(3, 7, 18, 0.94);
  box-shadow: 0 10px 34px rgba(0, 0, 0, 0.62), 0 0 20px rgba(56, 189, 248, 0.16);
  z-index: 880;
  backdrop-filter: blur(8px);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.camera-stream-header {
  min-height: 44px;
  padding: 8px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(56, 189, 248, 0.22);
  background: rgba(14, 165, 233, 0.12);
}

.camera-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.camera-live-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 10px #22c55e;
}

.camera-stream-title {
  color: #e0f2fe;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0;
}

.camera-stream-header .close-btn {
  font-size: 20px;
}

.camera-stream-body {
  padding: 10px 12px;
}

.camera-video-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: 6px;
  background: #000;
}

.camera-stream-video {
  display: block;
  width: 100%;
  height: 100%;
  background: #000;
  border-radius: 6px;
  object-fit: fill;
}

.camera-video-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: visible;
}

.camera-box-rect {
  fill: transparent;
  stroke-width: 0.8;
  vector-effect: non-scaling-stroke;
}

.camera-box-rect.fire {
  stroke: #ef4444;
}

.camera-box-rect.nofire {
  stroke: #f59e0b;
}

.camera-box-rect.default {
  stroke: #38bdf8;
}

.camera-box-label {
  font-size: 4px;
  font-weight: 700;
  paint-order: stroke;
  stroke: rgba(2, 6, 23, 0.9);
  stroke-width: 0.55px;
  stroke-linejoin: round;
}

.camera-box-label.fire {
  fill: #fecaca;
}

.camera-box-label.nofire {
  fill: #fde68a;
}

.camera-box-label.default {
  fill: #bae6fd;
}

.camera-info-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.camera-info-item {
  min-height: 58px;
  padding: 10px 14px;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.64);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
}

.camera-info-item span {
  color: rgba(226, 232, 240, 0.75);
  font-size: 17px;
  font-weight: 600;
}

.camera-info-item strong {
  color: #f8fafc;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.15;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.camera-info-item.online strong {
  color: #86efac;
}

.camera-detection-panel {
  margin-top: 12px;
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 6px;
  background: rgba(8, 47, 73, 0.28);
  overflow: hidden;
}

.camera-detection-panel.is-error {
  border-color: rgba(239, 68, 68, 0.45);
  background: rgba(127, 29, 29, 0.22);
}

.camera-detection-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  color: #e0f2fe;
  font-size: 19px;
  font-weight: 600;
}

.camera-detection-head strong {
  color: #67e8f9;
  font-size: 19px;
  font-weight: 700;
  white-space: nowrap;
}

.camera-detection-panel.is-error .camera-detection-head strong {
  color: #fecaca;
}

.camera-detection-body {
  padding: 12px 14px;
  color: rgba(226, 232, 240, 0.85);
  font-size: 19px;
}

.camera-live-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  color: rgba(226, 232, 240, 0.8);
  font-size: 19px;
  font-weight: 600;
}

.camera-live-result-head strong {
  color: #67e8f9;
  font-size: 20px;
  font-weight: 700;
  white-space: nowrap;
}

.camera-live-result-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.camera-live-result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  padding: 8px 12px;
  border: 1px solid rgba(56, 189, 248, 0.24);
  border-radius: 4px;
  background: rgba(15, 23, 42, 0.58);
  font-size: 19px;
  font-weight: 600;
}

.camera-live-result-item span {
  min-width: 0;
  overflow: hidden;
  color: #e2e8f0;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 19px;
}

.camera-live-result-item strong {
  flex: 0 0 auto;
  color: #bae6fd;
  font-size: 19px;
  font-weight: 700;
}

.camera-live-result-item.fire {
  border-color: rgba(239, 68, 68, 0.56);
  background: rgba(127, 29, 29, 0.22);
}

.camera-live-result-item.fire strong {
  color: #fecaca;
}

.camera-live-result-item.nofire {
  border-color: rgba(245, 158, 11, 0.56);
  background: rgba(120, 53, 15, 0.22);
}

.camera-live-result-item.nofire strong {
  color: #fde68a;
}

.story-detection-alert {
  width: 840px;
  max-height: calc(100vh - 96px);
  transform: translateX(-50%);
  animation: storyDetectionPanelFadeIn 0.25s ease-out;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

@keyframes storyDetectionPanelFadeIn {
  from {
    opacity: 0;
    transform: translate(-50%, 8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0) scale(1);
  }
}

.story-detection-alert.is-warning {
  border-color: rgba(251, 191, 36, 0.72);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.75), 0 0 20px rgba(251, 191, 36, 0.26);
}

.story-detection-alert.is-critical {
  border-color: rgba(239, 68, 68, 0.78);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.78), 0 0 22px rgba(239, 68, 68, 0.34);
}

.story-detection-alert.is-warning .detection-popup-header {
  background: rgba(251, 191, 36, 0.18);
  border-bottom-color: rgba(251, 191, 36, 0.32);
}

.story-detection-alert.is-critical .detection-popup-header {
  background: rgba(239, 68, 68, 0.18);
  border-bottom-color: rgba(239, 68, 68, 0.36);
}

.story-detection-alert.is-warning .header-title {
  color: #fde68a;
}

.story-detection-alert.is-critical .header-title {
  color: #fecaca;
}

.story-detection-alert .detection-popup-header {
  min-height: 44px;
  padding: 10px 16px;
}

.story-detection-alert .header-title {
  font-size: 22px;
  font-weight: 700;
}

.story-detection-alert .close-btn {
  font-size: 22px;
}

.story-detection-alert.is-warning .pulse-dot {
  background-color: #f59e0b;
  box-shadow: 0 0 8px #f59e0b;
}

.story-detection-content {
  align-items: flex-start;
  gap: 16px;
  padding: 12px 16px 16px;
}

.story-detection-img-container {
  width: 440px;
  height: 264px;
  border-color: rgba(255, 255, 255, 0.18);
}

.story-detection-img-container .detection-raw-img {
  object-fit: fill;
}

.story-result-panel {
  flex: 1;
  min-width: 0;
  padding: 4px 8px 0;
}

.story-result-panel .panel-section-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 6px;
  color: #93c5fd;
  text-shadow: 0 0 6px rgba(56, 189, 248, 0.35);
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

.story-panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.story-panel-title-row .status-indicator {
  flex: 0 0 auto;
  padding: 4px 12px;
  font-size: 16px;
  font-weight: 700;
}

.story-model-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
  font-size: 21px;
  color: #dbeafe;
}

.story-model-row strong {
  color: #f8fafc;
  font-size: 21px;
  font-weight: 700;
  text-align: right;
}

.story-detecting-wrap {
  margin-top: 18px;
}

.story-results-wrap {
  margin-top: 6px;
}

.story-result-summary {
  gap: 10px;
}

.story-confidence-grid {
  display: grid;
  grid-template-columns: 1.25fr 0.75fr;
  gap: 10px;
  margin-top: 6px;
}

.story-confidence-card {
  min-height: 76px;
  padding: 10px 10px;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(15, 23, 42, 0.58);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
}

.story-confidence-card.emphasis {
  border-color: rgba(56, 189, 248, 0.45);
  background: rgba(8, 47, 73, 0.5);
}

.story-zh-banner {
  margin-top: 10px;
  padding: 12px 16px;
  border-radius: 6px;
  border: 1px solid rgba(56, 189, 248, 0.4);
  background: rgba(14, 165, 233, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.story-zh-banner strong {
  color: #38bdf8;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.5px;
  line-height: 1.3;
}

.confidence-label {
  color: rgba(226, 232, 240, 0.78);
  font-size: 20px;
  font-weight: 600;
}

.story-confidence-card strong {
  color: #f8fafc;
  font-size: 28px;
  line-height: 1.15;
  letter-spacing: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.story-confidence-card.emphasis strong {
  font-size: 28px;
}

.story-detection-alert.is-warning .story-confidence-card.emphasis strong {
  color: #fde047;
}

.story-detection-alert.is-critical .story-confidence-card.emphasis strong {
  color: #fca5a5;
}

.status-indicator.critical {
  background: rgba(239, 68, 68, 0.18);
  color: #fecaca;
  border: 1px solid rgba(239, 68, 68, 0.48);
}

.status-indicator.warning {
  background: rgba(245, 158, 11, 0.18);
  color: #fde68a;
  border: 1px solid rgba(245, 158, 11, 0.48);
}

.story-detection-items {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.story-detection-items .detect-item {
  min-height: 28px;
  padding: 5px 8px;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  white-space: nowrap;
}

.story-detection-items .detect-item .item-zh {
  color: #38bdf8;
  font-weight: 600;
}

.story-advice-bar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 110px;
  align-items: stretch;
  gap: 12px;
  margin: 0 16px 16px;
}

.story-advice-main {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  min-height: 56px;
  padding: 10px 14px;
  border-radius: 4px;
  border-left: 3px solid #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  color: #fcd34d;
}

.story-detection-alert.is-critical .story-advice-main {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  color: #fecaca;
}

.story-advice-title {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 4px;
  border: 1px solid rgba(245, 158, 11, 0.48);
  background: rgba(245, 158, 11, 0.18);
  color: #fde68a;
  font-size: 20px;
  font-weight: 800;
  white-space: nowrap;
}

.story-detection-alert.is-critical .story-advice-title {
  border-color: rgba(239, 68, 68, 0.52);
  background: rgba(239, 68, 68, 0.18);
  color: #fecaca;
}

.story-advice-text {
  font-size: 20px;
  line-height: 1.45;
  font-weight: 600;
}

.story-advice-action {
  width: 100%;
  height: auto !important;
  margin-top: 0 !important;
  font-size: 18px !important;
}

.story-report-box {
  font-size: 18px;
  line-height: 1.45;
  padding: 8px 10px;
}

.story-detection-alert .reset-btn {
  height: 36px;
  margin-top: 8px;
  font-size: 18px;
}

.detect-item.warning-event {
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(245, 158, 11, 0.1);
}

.story-report-box {
  margin-top: 8px;
}

.story-detection-note {
  margin-top: 8px;
  color: rgba(255, 255, 255, 0.52);
  font-size: 13px;
  line-height: 1.45;
}

.story-detection-alert .box-rect {
  animation: none;
  stroke-dasharray: none;
  stroke-dashoffset: 0;
  stroke-linejoin: round;
}

.story-detection-alert .detection-svg-overlay {
  overflow: visible;
}

.rect-story-warning {
  stroke: #f59e0b;
}

.rect-story-fire {
  stroke: #ef4444;
}

.story-box-label {
  font-size: 4px;
}

.label-story-warning {
  fill: #fde68a;
}

.label-story-fire {
  fill: #fecaca;
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

/* =========================================================
   🚁 无人机多源影像驱动 · 三维实景数字孪生重构工作台 (高级玻璃拟态与赛博全息)
========================================================= */
.reconstruction-fusion-panel {
  position: absolute;
  top: 75px;
  right: 20px;
  width: 600px;
  max-height: calc(100vh - 270px);
  background: rgba(8, 14, 28, 0.94);
  border: 1px solid rgba(0, 242, 254, 0.55);
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.75), 0 0 24px rgba(0, 242, 254, 0.22);
  z-index: 990;
  overflow: hidden;
  backdrop-filter: blur(16px);
  display: flex;
  flex-direction: column;
  animation: fusionPanelFadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: auto;
  font-family: 'Times New Roman', 'Microsoft YaHei', '微软雅黑', sans-serif !important;
}

@keyframes fusionPanelFadeIn {
  from { opacity: 0; transform: translateY(-12px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.reconstruction-fusion-panel .glass-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(0, 242, 254, 0.12), transparent 70%),
              linear-gradient(180deg, rgba(14, 165, 233, 0.08) 0%, transparent 100%);
  pointer-events: none;
}

.reconstruction-fusion-panel .panel-content-wrapper {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.fusion-panel-header {
  min-height: 52px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(0, 242, 254, 0.25);
  background: rgba(0, 242, 254, 0.08);
}

.title-cluster {
  display: flex;
  align-items: center;
  gap: 10px;
}

.fusion-icon {
  font-size: 20px;
  filter: drop-shadow(0 0 6px rgba(0, 242, 254, 0.8));
}

.title-text-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.main-title {
  color: #e0f2fe;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
}

.sub-title {
  color: rgba(186, 230, 253, 0.6);
  font-size: 11px;
  font-family: Arial, sans-serif;
  letter-spacing: 0.3px;
}

.header-right-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-tab-group {
  display: flex;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
}

.mode-tab-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: rgba(226, 232, 240, 0.75);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.mode-tab-btn:hover {
  color: #fff;
  background: rgba(0, 242, 254, 0.15);
}

.mode-tab-btn.active {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.35), rgba(4, 120, 87, 0.45));
  color: #00f2fe;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.3);
}

.mode-tab-btn .badge {
  font-size: 10px;
  padding: 1px 5px;
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
  border-radius: 999px;
}

.mode-tab-btn .badge-building {
  font-size: 10px;
  padding: 1px 6px;
  background: rgba(245, 158, 11, 0.35);
  color: #fde047;
  border-radius: 999px;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
  animation: pulseBadge 1.2s infinite ease-in-out;
}

@keyframes pulseBadge {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.65; transform: scale(0.96); }
}

.mode-tab-btn .badge-ready {
  font-size: 10px;
  padding: 1px 5px;
  background: rgba(34, 197, 94, 0.25);
  color: #4ade80;
  border-radius: 999px;
}

.panel-close-btn {
  background: transparent;
  border: none;
  color: rgba(226, 232, 240, 0.6);
  font-size: 20px;
  cursor: pointer;
  line-height: 1;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.panel-close-btn:hover {
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.15);
}

.fusion-panel-body {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

/* 核心展示区 */
.viewport-stage {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  overflow: hidden;
  background: #020617;
  border: 1px solid rgba(0, 242, 254, 0.3);
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.8);
}

.stage-view {
  width: 100%;
  height: 100%;
  position: relative;
}

/* 三维实景重构中全息界面 */
.reconstruction-building-state {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 24px;
  gap: 12px;
  background: radial-gradient(circle at center, rgba(14, 165, 233, 0.15) 0%, rgba(2, 6, 23, 0.98) 75%);
  box-sizing: border-box;
}

.building-spinner-wrap {
  position: relative;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.holo-scanner-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px dashed rgba(0, 242, 254, 0.8);
  border-top-color: #38bdf8;
  border-right-color: transparent;
  animation: spinRing 2s linear infinite;
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
}

@keyframes spinRing {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.holo-scanner-core {
  position: relative;
  z-index: 2;
  font-family: monospace;
  font-size: 16px;
  font-weight: 700;
  color: #00f2fe;
  text-shadow: 0 0 8px #00f2fe;
}

.building-text-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
}

.building-status-title {
  color: #e0f2fe;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
}

.building-status-title .pulse-spark {
  color: #fbbf24;
  animation: pulseSpark 0.8s ease-in-out infinite alternate;
}

@keyframes pulseSpark {
  from { transform: scale(0.9); opacity: 0.7; }
  to { transform: scale(1.2); opacity: 1; }
}

.building-status-desc {
  color: rgba(186, 230, 253, 0.75);
  font-size: 12px;
  max-width: 480px;
  line-height: 1.4;
}

.building-progress-bar-wrap {
  width: 80%;
  height: 6px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 999px;
  overflow: hidden;
}

.building-progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #0284c7 0%, #00f2fe 70%, #38bdf8 100%);
  border-radius: 999px;
  box-shadow: 0 0 10px #00f2fe;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.building-sub-stats {
  display: flex;
  gap: 16px;
  color: rgba(148, 163, 184, 0.7);
  font-size: 11px;
  font-family: Arial, sans-serif;
}

.stage-view .uav-main-photo-wrapper,
.stage-view .video-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.stage-view .twin-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
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
  padding: 10px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
  font-family: monospace;
  font-size: 13px;
}

.uav-photo-timestamp {
  color: #ff4d4f;
  font-weight: bold;
}

.uav-photo-coords {
  color: #00e5ff;
}

/* 点云全息线网与扫描线特效 */
.point-cloud-grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(0, 242, 254, 0.08) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 242, 254, 0.08) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
}

.sfm-feature-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.feature-crosshair {
  position: absolute;
  width: 24px;
  height: 24px;
  border: 1px dashed rgba(0, 242, 254, 0.7);
  border-radius: 50%;
  animation: pulseRotate 4s linear infinite;
}

.feature-crosshair::after {
  content: '';
  position: absolute;
  top: 50%; left: 50%;
  width: 4px; height: 4px;
  background: #00f2fe;
  border-radius: 50%;
  transform: translate(-50%, -50%);
}

.feature-crosshair.c1 { top: 35%; left: 45%; }
.feature-crosshair.c2 { top: 55%; left: 65%; }
.feature-crosshair.c3 { top: 40%; left: 70%; }

.feature-tag {
  position: absolute;
  bottom: 8px;
  right: 10px;
  background: rgba(3, 7, 18, 0.85);
  border: 1px solid rgba(0, 242, 254, 0.4);
  padding: 3px 8px;
  border-radius: 4px;
  color: #00f2fe;
  font-size: 11px;
  font-weight: 600;
}

@keyframes pulseRotate {
  0% { transform: scale(1) rotate(0deg); opacity: 0.8; }
  50% { transform: scale(1.15) rotate(180deg); opacity: 1; }
  100% { transform: scale(1) rotate(360deg); opacity: 0.8; }
}

/* 4 组航拍多视角采集序列与重构输入流 */
.capture-stream-strip {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stream-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stream-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 600;
}

.stream-label .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f59e0b;
  box-shadow: 0 0 6px #f59e0b;
}

.stream-label .dot.is-complete {
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}

.engine-tag {
  font-size: 11px;
  color: #fbbf24;
  font-weight: 600;
}

.engine-tag.is-converged {
  color: #4ade80;
  text-shadow: 0 0 8px rgba(74, 222, 128, 0.4);
}

.uav-thumbnails-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.uav-thumb-box {
  position: relative;
  aspect-ratio: 16 / 10;
  background: rgba(2, 6, 23, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.uav-thumb-box:hover {
  border-color: rgba(0, 242, 254, 0.6);
  transform: translateY(-2px);
}

.uav-thumb-box.is-active {
  border-color: #00f2fe;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.5);
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
  top: 3px;
  left: 3px;
  padding: 1px 5px;
  background: rgba(3, 7, 18, 0.85);
  border: 1px solid rgba(0, 242, 254, 0.5);
  border-radius: 3px;
  color: #00f2fe;
  font-size: 10px;
  font-weight: 700;
}

.uav-thumb-lock {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(148, 163, 184, 0.4);
  font-size: 14px;
}

/* 重构指标与一键入舱行动按钮 */
.reconstruction-footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 4px;
}

.metrics-grid {
  display: flex;
  align-items: center;
  gap: 12px;
  animation: metricsFadeIn 0.3s ease-out;
}

.metrics-grid.placeholder-grid {
  display: flex;
  align-items: center;
}

.metrics-calculating-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: rgba(148, 163, 184, 0.65);
  font-size: 11px;
}

.calculating-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 6px #38bdf8;
  animation: pulseDot 1s infinite alternate ease-in-out;
}

@keyframes pulseDot {
  from { opacity: 0.3; transform: scale(0.8); }
  to { opacity: 1; transform: scale(1.2); }
}

@keyframes metricsFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-item .k {
  color: rgba(148, 163, 184, 0.7);
  font-size: 11px;
}

.metric-item .v {
  color: #f8fafc;
  font-size: 13px;
  font-weight: 700;
}

.metric-item .v.highlight {
  color: #38bdf8;
}

.metric-item .v.green {
  color: #4ade80;
}

.enter-modeling-cta-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.3) 0%, rgba(14, 165, 233, 0.45) 100%);
  border: 1px solid rgba(0, 242, 254, 0.7);
  border-radius: 6px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 242, 254, 0.25);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  white-space: nowrap;
}

.enter-modeling-cta-btn:hover {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.5) 0%, rgba(14, 165, 233, 0.75) 100%);
  border-color: #00f2fe;
  box-shadow: 0 6px 24px rgba(0, 242, 254, 0.5);
  transform: translateY(-1px);
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
/* ✈️ 无人机出发浮窗 — 青色科技主题 */
.uav-dispatch-popup {
  width: 190px;
  background: rgba(5, 18, 38, 0.95);
  border: 1px solid rgba(0, 229, 255, 0.5);
  border-radius: 6px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.6), 0 0 14px rgba(0, 229, 255, 0.2);
  backdrop-filter: blur(12px);
  transform: translate(-50%, 0) !important; /* 朝下显示：移除向上的-100%偏移 */
}

.uav-dispatch-popup .shelter-popup-arrow {
  top: -6px;
  bottom: auto;
  border-top: 0;
  border-bottom: 6px solid rgba(5, 18, 38, 0.95);
  filter: drop-shadow(0 -2px 2px rgba(0, 0, 0, 0.15));
}

.uav-dispatch-header {
  background: linear-gradient(90deg, rgba(0, 180, 220, 0.85), rgba(0, 120, 160, 0.7)) !important;
  border-bottom: 1px solid rgba(0, 229, 255, 0.4);
  padding: 6px 10px !important;
}

/* 🚗 无人车出发浮窗 — 蓝色科技主题 (含传感器数据) */
.ugv-dispatch-popup {
  width: 220px;
  background: rgba(5, 10, 40, 0.95);
  border: 1px solid rgba(70, 130, 255, 0.5);
  border-radius: 6px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.6), 0 0 14px rgba(70, 130, 255, 0.2);
  backdrop-filter: blur(12px);
}

.ugv-dispatch-header {
  background: linear-gradient(90deg, rgba(40, 80, 200, 0.85), rgba(20, 50, 160, 0.7)) !important;
  border-bottom: 1px solid rgba(70, 130, 255, 0.4);
  padding: 6px 10px !important;
}

.dispatch-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: bold;
  letter-spacing: 0.5px;
}

.dispatch-icon {
  font-size: 13px;
}

/* 深色面板的表格通用样式覆盖 */
.uav-dispatch-popup .shelter-popup-table,
.ugv-dispatch-popup .shelter-popup-table {
  font-size: 11px;
  color: #c8e6f0;
}

.uav-dispatch-popup .shelter-popup-table td,
.ugv-dispatch-popup .shelter-popup-table td {
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 5px 8px;
}

.uav-dispatch-popup .shelter-popup-table td.label {
  background: rgba(0, 150, 190, 0.2);
  color: #7dd8f0;
  font-weight: bold;
}

.uav-dispatch-popup .shelter-popup-table td.value {
  background: rgba(0, 20, 45, 0.6);
  color: #e0f4ff;
}

.ugv-dispatch-popup .shelter-popup-table td.label {
  background: rgba(40, 80, 180, 0.25);
  color: #93b8ff;
  font-weight: bold;
}

.ugv-dispatch-popup .shelter-popup-table td.value {
  background: rgba(5, 10, 40, 0.6);
  color: #d0dfff;
}

/* 无人车浮窗的箭头颜色 */
.shelter-popup-arrow.ugv-arrow {
  border-top-color: rgba(5, 10, 40, 0.95);
}

/* 高亮值样式 */
.highlight-cyan {
  color: #00e5ff !important;
  font-weight: bold !important;
  text-shadow: 0 0 6px rgba(0, 229, 255, 0.5);
}

.highlight-blue {
  color: #6aabff !important;
  font-weight: bold !important;
  text-shadow: 0 0 6px rgba(106, 171, 255, 0.5);
}

.status-launched {
  color: #00ff88 !important;
  font-weight: bold !important;
  text-shadow: 0 0 5px rgba(0, 255, 136, 0.4);
}

/* 无人车传感器数据合并面板样式 */
.ugv-sensor-section {
  border-top: 1px solid rgba(70, 130, 255, 0.25);
}

.ugv-sensor-tabs {
  display: flex;
  gap: 0;
  background: rgba(20, 40, 90, 0.3);
}

.ugv-sensor-tab {
  flex: 1;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 6px 8px;
  font-size: 11px;
  font-weight: bold;
  color: #8aafcc;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  transition: all 0.2s ease;
  font-family: inherit;
}

.ugv-sensor-tab:hover {
  color: #b0d8ff;
  background: rgba(70, 130, 255, 0.1);
}

.ugv-sensor-tab.active {
  color: #6aabff;
  border-bottom-color: #6aabff;
  background: rgba(70, 130, 255, 0.15);
}

.ugv-tab-status {
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 2px;
  background: rgba(0, 255, 136, 0.08);
  border: 1px solid rgba(0, 255, 136, 0.25);
  color: #00ff88;
  font-weight: bold;
}

.ugv-tab-status.offline {
  color: #ffb4b4;
  background: rgba(168, 54, 54, 0.18);
  border-color: rgba(255, 180, 180, 0.28);
}

.ugv-sensor-body {
  padding: 6px;
}

.ugv-sensor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.ugv-sensor-item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  padding: 4px 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ugv-sensor-item.wide {
  grid-column: 1 / -1;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.ugv-sensor-label {
  font-size: 10px;
  color: #8fa3b0;
}

.ugv-sensor-val {
  font-size: 11px;
  font-weight: 700;
  color: #e0f2fe;
  text-shadow: 0 0 4px rgba(224, 242, 254, 0.3);
  font-family: "JetBrains Mono", monospace;
}

.ugv-sensor-detail-link {
  text-align: right;
  padding: 5px 6px 3px;
  font-size: 9px;
  color: #6aabff;
  cursor: pointer;
  transition: color 0.2s;
}

.ugv-sensor-detail-link:hover {
  color: #a0cfff;
}

.globe-mask {
  position: absolute; z-index: 3000; inset: 0; display: flex; align-items: center; justify-content: center;
  background: radial-gradient(circle at center, rgba(12, 35, 66, .78), rgba(2, 10, 22, .95)); color: rgba(224, 247, 255, .9);
}
.globe-loading-content { user-select: none; caret-color: transparent; display: flex; flex-direction: column; align-items: center; gap: 14px; font-size: 16px; letter-spacing: 2px; text-shadow: 0 0 12px rgba(38, 205, 255, .85); }
.globe-loading-image {
  width: min(560px, 72vw);
  height: auto;
  object-fit: contain;
  animation: globe-loading-pulse 2.4s ease-in-out infinite;
}
@keyframes globe-loading-pulse { 0%, 100% { transform: scale(.94); opacity: .78; } 50% { transform: scale(1.04); opacity: 1; } }
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

/* 自定义滚动条 */

.light-val-text {
  font-size: 12px;
  color: #00ffd8;
  width: 45px;
  text-align: right;
  font-family: monospace;
}
/* 隐藏默认上下箭头 */

/* 📡 两客一危 湖北省交通数字孪生智控终端 (右侧高精对称伸缩侧边栏) CSS */
.lkyw-monitor-hud.high-end-panel {
  position: absolute;
  top: 16px;
  bottom: 16px;
  right: 16px;
  /* 收纳进机场切图右侧栏的可用空间，内部原有标签页和滚动内容不变。 */
  width: clamp(280px, 19vw, 365px);
  height: calc(100% - 32px);
  background: rgba(10, 19, 35, 0.92);
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
  height: 88px;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 11;
  padding: 0;
}

.toggle-btn-right-sidebar:hover {
  filter: brightness(1.2) drop-shadow(0 0 7px rgba(0, 242, 254, 0.65));
}

.sidebar-toggle-icon {
  display: block;
  width: 18px;
  height: 88px;
  object-fit: contain;
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
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
}

.lkyw-monitor-hud .sidebar-subtitle {
  font-size: 16px;
  color: #00f2fe;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: inline-block;
  margin-top: 3px;
  opacity: 0.85;
}

.lkyw-hud-status-badge {
  font-size: 15px;
  font-family: monospace;
  font-weight: bold;
  color: #00ffaa;
  background: rgba(0, 255, 170, 0.12);
  border: 1px solid rgba(0, 255, 170, 0.35);
  padding: 4px 14px;
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
/* 立体传感网协同矩阵：沿用主页侧栏的字体层级与青蓝 HUD 视觉。 */
.sensor-fusion-panel {
  --fusion-line: rgba(69, 203, 218, 0.52);
  position: relative;
  width: 380px;
  color: #dff8ff;
  font-family: 'LkywOppoSans', "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  font-size: 15px;
  line-height: 1.45;
  background:
    linear-gradient(145deg, rgba(1, 35, 57, 0.94), rgba(3, 17, 31, 0.88)),
    repeating-linear-gradient(0deg, transparent 0 27px, rgba(115, 221, 255, 0.035) 28px);
  border: 1px solid var(--fusion-line);
  box-shadow: inset 0 0 28px rgba(0, 191, 255, 0.12), 0 10px 30px rgba(0, 8, 18, 0.58);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  clip-path: polygon(0 10px, 10px 0, calc(100% - 10px) 0, 100% 10px, 100% calc(100% - 10px), calc(100% - 10px) 100%, 10px 100%, 0 calc(100% - 10px));
  overflow: hidden;
  pointer-events: auto;
  z-index: 900;
}

.sensor-fusion-panel::before,
.sensor-fusion-panel::after {
  position: absolute;
  z-index: 2;
  width: 42px;
  height: 2px;
  content: '';
  background: #69e7ff;
  box-shadow: 0 0 10px #13bbff;
}

.sensor-fusion-panel::before { top: 0; left: 18px; }
.sensor-fusion-panel::after { right: 18px; bottom: 0; }

.fusion-header {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 45px;
  padding: 0 14px;
  background: linear-gradient(90deg, rgba(35, 129, 153, 0.38), rgba(0, 28, 49, 0.12));
  border-bottom: 1px solid rgba(81, 212, 255, 0.3);
}

.fusion-header::before {
  width: 4px;
  height: 20px;
  margin-right: 9px;
  content: '';
  background: #1dddf4;
  box-shadow: 0 0 7px rgba(29, 221, 244, 0.9);
}

.fusion-header .icon { margin-right: 8px; font-size: 15px; filter: drop-shadow(0 0 4px rgba(67, 229, 255, 0.55)); }
.fusion-header .title {
  color: #f1fdff;
  font-family: 'LkywTencentSans', "Microsoft YaHei", sans-serif;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.35px;
  text-shadow: 0 0 8px rgba(109, 231, 249, 0.28);
}

/* 右侧跳动的呼吸灯 */
.pulse-indicator {
  margin-left: auto;
  width: 7px;
  height: 7px;
  background: #17efaa;
  border-radius: 50%;
  box-shadow: 0 0 7px #17efaa;
  animation: pulseAnim 1.5s infinite;
}
@keyframes pulseAnim {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

.fusion-list {
  list-style: none;
  padding: 10px 14px;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.fusion-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 43px;
  padding: 0 6px;
  border-bottom: 1px solid rgba(105, 191, 214, 0.16);
  background: transparent;
}

.fusion-list li:last-child { border-bottom: 0; }

.node-name { color: #e6f7fa; font-size: 15px; font-weight: 600; letter-spacing: 0.15px; }

/* 动态状态标签的颜色变化 */
.sensor-fusion-panel .status-tag {
  max-width: 238px;
  padding: 4px 7px;
  border-radius: 3px;
  color: #9fc5cf;
  font-family: 'LkywOppoSans', "Microsoft YaHei", sans-serif;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.3;
  text-align: right;
}
.sensor-fusion-panel .status-tag.normal { color: #a6cbd3; }
.sensor-fusion-panel .status-tag.waiting { color: #789daa; background: rgba(82, 170, 190, 0.08); }
.sensor-fusion-panel .status-tag.alert { color: #ff8795; background: rgba(255, 77, 109, 0.1); border: 1px solid rgba(255, 77, 109, 0.28); }
.sensor-fusion-panel .status-tag.moving { color: #ffd176; background: rgba(255, 193, 71, 0.1); border: 1px solid rgba(255, 193, 71, 0.25); }
.sensor-fusion-panel .status-tag.active { color: #62ebb1; background: rgba(31, 186, 107, 0.1); border: 1px solid rgba(31, 186, 107, 0.26); }

.fusion-footer {
  padding: 10px 14px 12px;
  background: rgba(2, 24, 40, 0.58);
  border-top: 1px solid rgba(81, 212, 255, 0.22);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.footer-row { display: flex; justify-content: space-between; gap: 14px; color: #9dc0c9; font-size: 13px; }
.footer-row strong { color: #e5f6f8; font-size: 13px; font-weight: 600; text-align: right; }
.sensor-fusion-panel .text-red { color: #ff8795; }
.sensor-fusion-panel .text-cyan {
  color: #72edff;
  font-family: 'LkywDigital', "DIN Alternate", Arial, sans-serif;
  font-size: 17px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.hud-title-icon {
  font-size: 14px;
  filter: drop-shadow(0 0 4px rgba(0, 229, 255, 0.8));
}

.lkyw-hud-title {
  color: #00ffd8;
  font-size: 19px;
  font-weight: bold;
  letter-spacing: 0.5px;
  text-shadow: 0 0 8px rgba(0, 255, 216, 0.4);
}

.lkyw-hud-status-badge {
  font-size: 15px;
  color: #00ffaa;
  background: rgba(0, 255, 170, 0.12);
  border: 1px solid rgba(0, 255, 170, 0.35);
  border-radius: 10px;
  padding: 3px 9px;
  font-family: monospace;
  box-shadow: 0 0 8px rgba(0, 255, 170, 0.2);
}

/* 视图切换 Tabs */
.hud-mode-tabs {
  display: flex;
  gap: 8px;
  margin: 8px 10px;
  padding: 0;
}

.mode-btn {
  flex: 1;
  min-width: 0;
  height: 24px;
  padding: 0 3px;
  background: transparent url('/hud-assets/pill-default.svg') center / 100% 100% no-repeat;
  border: 0;
  color: #b8e7ff;
  font-size: 11px;
  font-weight: bold;
  font-style: italic;
  letter-spacing: .5px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.mode-btn:hover {
  filter: brightness(1.2);
  color: #e8fbff;
}

.mode-btn.active {
  background: transparent url('/hud-assets/pill-active.svg') center / 100% 100% no-repeat;
  color: #edffd5;
  box-shadow: 0 0 8px rgba(114, 244, 124, .2);
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
  font-size: 28px;
  font-weight: 700;
  display: block;
  color: #00f2fe;
}
/* 高危数字用白色+下划线区分，不用红色 */
.risk-summary-item.red .risk-num { color: #ffffff; }

.risk-lbl {
  font-size: 15px;
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
  font-size: 19px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
}
.risk-type-tag {
  font-size: 14.5px;
  padding: 2px 7px;
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
  font-size: 14.5px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
}
.risk-level-badge.red    { background: rgba(255,80,100,0.15); color: #fca5a5; border: 1px solid rgba(255,80,100,0.3); }
.risk-level-badge.orange { background: rgba(0, 242, 254, 0.08); color: #a5d8ff; border: 1px solid rgba(0,242,254,0.2); }
.risk-level-badge.gold   { background: rgba(0, 242, 254, 0.05); color: #94a3b8; border: 1px solid rgba(0,242,254,0.15); }

.risk-reason {
  font-size: 17px;
  color: #cbd5e1;
  font-weight: 500;
}
.risk-meta-row {
  font-size: 15.5px;
  color: #64748b;
}

.risk-action-btn {
  align-self: flex-end;
  background: transparent;
  border: 1px solid rgba(0, 242, 254, 0.3);
  color: #00f2fe;
  font-size: 15.5px;
  font-weight: 600;
  padding: 6px 14px;
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
  font-size: 16px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}
/* 排名标识使用青色深色调，避免金色/银色刺眼 */
.cp-rank.gold   { background: rgba(0, 242, 254, 0.2); color: #ffffff; border: 1px solid rgba(0,242,254,0.4); }
.cp-rank.silver { background: rgba(0, 242, 254, 0.08); color: #a5d8ff; border: 1px solid rgba(0,242,254,0.2); }
.cp-rank.border { background: rgba(255,255,255,0.05); color: #94a3b8; border: 1px solid rgba(255,255,255,0.12); }

.cp-name {
  font-size: 19px;
  font-weight: 600;
  color: #ffffff;
  flex: 1;
  margin-left: 8px;
}
.cp-status {
  font-size: 16px;
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
  font-size: 16px;
  color: #64748b;
}
.cp-val {
  font-size: 19.5px;
  font-weight: 700;
  color: #00f2fe;
}
.cp-val.green  { color: #00f2fe; }
.cp-val.gold   { color: #a5d8ff; }
.cp-val.orange { color: #cbd5e1; }
.cp-val small { font-size: 13.5px; font-weight: normal; color: #64748b; }

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
  font-size: 17.5px;
  font-weight: bold;
  color: #00ffd8;
  letter-spacing: 0.5px;
  text-shadow: 0 0 6px rgba(0, 255, 216, 0.5);
}

.net-inflow-badge {
  font-size: 14.5px;
  padding: 2px 7px;
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
  font-size: 16px;
  color: #94a3b8;
  font-weight: bold;
}

.flow-anim-arrow {
  font-family: monospace;
  font-size: 16px;
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
  font-size: 25px;
  font-weight: bold;
  font-family: monospace;
}
.border-flow-val.green { color: #00ffaa; text-shadow: 0 0 8px rgba(0, 255, 170, 0.4); }
.border-flow-val.gold { color: #ffd700; text-shadow: 0 0 8px rgba(255, 215, 0, 0.4); }

.flow-unit {
  font-size: 14.5px;
  color: #64748b;
  font-weight: normal;
}

/* 赛博卡片级 进出省对撞数据舱 */
.cyber-flow-box-group {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.cyber-flow-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 14.5px;
  font-family: monospace;
  transition: all 0.3s ease;
  white-space: nowrap;
  flex-shrink: 0;
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
  font-size: 13.5px;
  font-weight: bold;
  color: #cbd5e1;
  white-space: nowrap;
  flex-shrink: 0;
}

.box-val {
  font-weight: bold;
  font-size: 17px;
  white-space: nowrap;
  flex-shrink: 0;
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
  font-size: 17.5px;
  font-weight: bold;
  color: #e2f1ff;
  letter-spacing: 0.5px;
}

.chart-sub {
  font-size: 14.5px;
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
  width: 124px;
  height: 124px;
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
  font-size: 21px;
  font-weight: bold;
  color: #ffffff;
  font-family: monospace;
  line-height: 1.1;
}

.pie-total-unit {
  font-size: 13.5px;
  color: #8fa2c4;
  margin-top: 4px;
  white-space: nowrap;
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
  gap: 8px;
  font-size: 17px;
  padding: 5px 10px;
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
  font-size: 16.5px;
  flex-grow: 1;
}

.legend-val {
  font-weight: bold;
  font-family: monospace;
  font-size: 17px;
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
  font-size: 16.5px;
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
  width: 20px;
  height: 20px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  font-size: 14px;
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
  font-size: 17px;
}

.hazard-tag {
  font-size: 13.5px;
  padding: 1px 5px;
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
  font-size: 15px;
  padding: 4px 8px;
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
  font-size: 13.5px;
}

.log-loc {
  color: #cbd5e1;
  font-size: 14.5px;
  max-width: 150px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-plate {
  font-family: monospace;
  font-weight: bold;
  color: #00ffd8;
  font-size: 15.5px;
}

.log-tag {
  font-size: 13.5px;
  padding: 1px 4px;
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
  font-size: 18px;
  color: #cbd5e1;
  font-weight: bold;
}

.lkyw-subbadge {
  font-size: 14px;
  padding: 2px 7px;
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
  font-size: 26px;
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
  font-size: 16px;
  color: #64748b;
}

.lkyw-border-flow {
  display: flex;
  gap: 5px;
}

.flow-tag {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 14.5px;
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
  font-size: 14.5px;
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
  font-size: 16px;
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

/* 🗺️ 湖北省地图车辆运行图例：沿用首页侧栏的深蓝玻璃态与青色描边。 */
.hubei-map-legend {
  position: absolute;
  top: 90px;
  width: 340px;
  min-width: 0;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(2, 26, 43, .90), rgba(2, 13, 28, .84));
  border: 1px solid rgba(32, 216, 255, .48);
  box-shadow: 0 14px 34px rgba(0, 0, 0, .42), inset 0 0 30px rgba(0, 199, 255, .07);
  border-radius: 7px;
  padding: 10px;
  z-index: 15;
  backdrop-filter: blur(10px);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  transition: right 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: auto;
}

.legend-row.legend-guide-row { border-left-color: var(--guide-color); background: rgba(4, 43, 54, .36); }
.legend-guide-row i { display: inline-block; flex: 0 0 14px; text-align: center; font-style: normal; }
.legend-map-guide__line { height: 1px; background: #87e2ef; box-shadow: 0 0 3px #8be4ef66; }
.legend-map-guide__plate { color: #9ed9e5; font-size: 9px; padding: 1px; border: 1px solid #78b7c666; border-radius: 3px; }
.legend-map-guide__alert { color: #e6bb68; font-size: 17px; font-weight: 700; }

.legend-slide-enter-active,
.legend-slide-leave-active {
  transition: opacity 0.24s ease, transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.legend-slide-enter-from,
.legend-slide-leave-to {
  opacity: 0;
  transform: translateX(28px);
}

.legend-header {
  min-height: 31px;
  display: flex;
  align-items: center;
  padding: 0 9px;
  margin: -10px -10px 10px;
  border-bottom: 1px solid rgba(126, 212, 236, .25);
  background: linear-gradient(90deg, rgba(35, 129, 153, .3), transparent);
}

.legend-title {
  color: #ddfbff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: .5px;
}

.legend-title::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 16px;
  margin-right: 8px;
  vertical-align: -3px;
  background: #1dddf4;
  box-shadow: 0 0 6px rgba(29, 221, 244, .85);
}

.legend-body { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
.hubei-map-legend .legend-row { min-width: 0; min-height: 42px; gap: 7px; padding: 7px; }
.hubei-map-legend .legend-text-main { white-space: nowrap; }

/* 单行图例与首页车辆分类卡保持一致。 */
.legend-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  border-radius: 0;
  padding: 7px 9px;
  box-sizing: border-box;
  transition: all 0.2s ease;
  border: 1px solid rgba(58, 182, 210, .22);
  border-left: 3px solid #ff536d;
  background: rgba(50, 14, 31, .36);
}

.legend-row:hover {
  background: rgba(0, 117, 148, .26);
  box-shadow: inset 0 0 14px rgba(25, 220, 255, .08), 0 0 10px rgba(25, 220, 255, .15);
}

.hazard-row {
  border-left-color: #ff536d;
}
.hazard-row:hover {
  border-color: rgba(255, 83, 109, .62);
  border-left-color: #ff536d;
}

.passenger-row {
  border-left-color: #44e99e;
  background: rgba(5, 69, 57, .36);
}
.passenger-row:hover {
  border-color: rgba(68, 233, 158, .62);
  border-left-color: #44e99e;
}

.tourist-row {
  border-left-color: #44c8ff;
  background: rgba(4, 52, 84, .38);
}
.tourist-row:hover {
  border-color: rgba(68, 200, 255, .62);
  border-left-color: #44c8ff;
}

/* 呼吸发光点 */
.legend-glow-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  position: relative;
}

.legend-glow-dot::after {
  content: '';
  position: absolute;
  top: -3px;
  left: -3px;
  right: -3px;
  bottom: -3px;
  border-radius: 50%;
  background: inherit;
  opacity: 0.4;
  animation: dot-pulse 1.8s infinite ease-in-out;
}

@keyframes dot-pulse {
  0% { transform: scale(1); opacity: 0.4; }
  50% { transform: scale(1.8); opacity: 0; }
  100% { transform: scale(1); opacity: 0.4; }
}

.legend-glow-dot.red {
  background-color: #ff3344;
  box-shadow: 0 0 8px #ff3344;
}

.legend-glow-dot.green {
  background-color: #00ffaa;
  box-shadow: 0 0 8px #00ffaa;
}

.legend-glow-dot.blue {
  background-color: #00e5ff;
  box-shadow: 0 0 8px #00e5ff;
}

/* 文字排版 */
.legend-text-main {
  font-size: 14px;
  font-weight: 700;
  color: #effdff;
  white-space: nowrap;
}

.legend-text-sub {
  font-size: 10px;
  color: #8fa0dd;
  font-family: monospace;
  background: rgba(255, 255, 255, 0.04);
  padding: 2px 6px;
  border-radius: 4px;
}

/* 🛠️ 右下角微调弹窗面板堆叠容器 */

/* 车流调节 弹窗面板 */

/* 车辆类型筛选 Tabs */

/* 候选节点动态剔除名录样式 (二级标题与各节点字号放大) */
.alp-losers { 
  border-top: 1px dashed rgba(255,255,255,0.12); 
  padding-top: 12px; 
  margin-top: 10px;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
}
.alp-losers-title { 
  font-size: var(--hud-h2-font-size, 16px); 
  font-weight: 700;
  color: #00ffff; 
  margin-bottom: 10px; 
  letter-spacing: 0.5px;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
  text-shadow: 0 0 6px rgba(0, 255, 255, 0.3);
}
.alp-loser-item { 
  background: rgba(239, 68, 68, 0.08);
  border-left: 3px solid rgba(239, 68, 68, 0.5);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 8px; 
}
.alp-loser-item:last-child { margin-bottom: 0; }
.alp-loser-name { 
  font-size: 15px; 
  color: #ffffff; 
  font-weight: 700;
  letter-spacing: 0.3px;
}
.alp-loser-reason { 
  font-size: 14px; 
  color: #fca5a5; 
  margin-top: 4px;
  line-height: 1.4;
}

/* 📹 全阶段相机视角微调工具 弹窗面板 */

@keyframes modalFadeIn {
  from { opacity: 0; transform: translateY(-10px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* 场景切换 */

/* 下拉框行 */

/* 滑块行 */

/* 按钮组 */





/* ⛽ 油罐车模型与泄漏点微调面板专属橙色高端拟态样式 */

/* 🤖 无人装备微调面板专属炫绿高端拟态样式 */

/* 🚗 无人车悬浮窗微调面板专属蓝色高端拟态样式 */

/* 🚁 无人机悬浮窗微调面板专属青色高端拟态样式 */
.accident-detail { width: min(1120px, 94vw); font-size: 19px; }
.accident-detail h2 { font-size: 30px; }
.accident-detail header { font-size: 18px; }
.accident-detail p { font-size: 19px; line-height: 1.9; }
.accident-detail img { height: 340px; object-fit: contain; background: #020d16; }
.accident-detail figcaption,.accident-detail footer span { font-size: 15px; }
.accident-detail button { font-size: 18px; }
.accident-photo-pending { height: 300px; display: grid; place-content: center; text-align: center; line-height: 2; background: #06121c; color: #a8c5ce; }
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

/* ==========================================
   阶段 9：传感网原型解析悬浮窗 (图片版)
========================================== */
/* 弹窗整体容器 */
/* ==========================================
   阶段 9：传感网原型解析悬浮窗 (图片版) - 特大字体版
========================================== */
/* 弹窗整体容器 */
.prototype-magnifier-popup {
  position: absolute; 
  top: 40px;    
  left: 80px;  
  transform: none; 
  background: rgba(10, 20, 35, 0.9);
  border: 1px solid rgba(0, 229, 255, 0.5);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
  border-radius: 8px;
  width: 900px; /* 🚨 弹窗拉宽到 900px，防止特大字体挤换行 */
  z-index: 1000;
  backdrop-filter: blur(10px);
}

/* 🚨 核武器：强制该弹窗内所有元素的字体必须是微软雅黑！ */
.prototype-magnifier-popup,
.prototype-magnifier-popup * {
  font-family: "Microsoft YaHei", "微软雅黑", sans-serif !important;
}

/* 头部标题区域 */
.prototype-magnifier-popup .popup-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(45, 183, 245, 0.3);
  background: linear-gradient(90deg, rgba(45, 183, 245, 0.15) 0%, transparent 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #2db7f5;
}

.prototype-magnifier-popup .popup-header .icon {
  font-size: 26px !important; /* 🚨 图标调大 */
  margin-right: 12px;
}

.prototype-magnifier-popup .popup-header .title {
  font-size: 24px !important; /* 🚨 主标题特大 */
  font-weight: bold !important;
  flex: 1;
  letter-spacing: 2px;
}

.prototype-magnifier-popup .close-btn {
  background: none;
  border: none;
  color: #8fa5c0;
  font-size: 28px !important; 
  cursor: pointer;
  transition: color 0.3s;
  line-height: 1;
}

.prototype-magnifier-popup .close-btn:hover {
  color: #ff4d4f;
}

/* 主体内容布局 */
.prototype-magnifier-popup .popup-body {
  display: flex;
  padding: 28px;
  gap: 30px;
  align-items: center; 
}

/* 左侧图片容器 */
.prototype-magnifier-popup .prototype-image-container {
  width: 320px; /* 🚨 图片区域也随之拉宽 */
  height: 230px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(16, 40, 70, 0.4);
  border: 1px dashed rgba(45, 183, 245, 0.4);
  border-radius: 6px;
  padding: 12px;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);
}

.prototype-magnifier-popup .custom-prototype-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 0 6px rgba(45, 183, 245, 0.6));
}

/* 右侧文本介绍样式 */
.prototype-magnifier-popup .prototype-desc {
  flex: 1;
  color: #a0d8ef; 
  font-size: 18px !important; /* 🚨 正文基础字号特大 */
  line-height: 1.8 !important; 
}

.prototype-magnifier-popup .desc-title {
  color: #00e5ff;
  margin-top: 0;
  margin-bottom: 18px !important;
  font-size: 22px !important; /* 🚨 小标题特大 */
  font-weight: bold !important;
  border-left: 4px solid #00e5ff;
  padding-left: 10px;
}

.prototype-magnifier-popup .desc-list {
  padding-left: 20px;
  margin: 0;
  list-style-type: none; 
}

.prototype-magnifier-popup .desc-list li {
  margin-bottom: 16px !important;
  position: relative;
  font-size: 18px !important; /* 🚨 列表文字特大 */
}

/* 列表自定义发光圆点 */
.prototype-magnifier-popup .desc-list li::before {
  content: "";
  position: absolute;
  left: -18px;
  top: 10px; 
  width: 8px;
  height: 8px;
  background: #2db7f5;
  border-radius: 50%;
  box-shadow: 0 0 6px #2db7f5;
}

.prototype-magnifier-popup .desc-list strong {
  color: #fff;
  font-size: 20px !important; /* 🚨 重点前缀词特大 */
  font-weight: bold !important;
}
.phase-desc-card {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 650px; /* 宽度调整至容纳图片和文字 */
  background: rgba(12, 22, 38, 0.9);
  border: 1px solid rgba(45, 183, 245, 0.5);
  border-radius: 8px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5), 0 0 15px rgba(45, 183, 245, 0.2);
  z-index: 1000;
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
}

/* 头部标题区域 */
.prototype-magnifier-popup .popup-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(45, 183, 245, 0.3);
  background: linear-gradient(90deg, rgba(45, 183, 245, 0.15) 0%, transparent 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #2db7f5;
}

.prototype-magnifier-popup .popup-header .icon {
  font-size: 18px;
  margin-right: 8px;
}

.prototype-magnifier-popup .popup-header .title {
  font-size: 16px;
  font-weight: bold;
  flex: 1;
  letter-spacing: 1px;
}

.prototype-magnifier-popup .close-btn {
  background: none;
  border: none;
  color: #8fa5c0;
  font-size: 22px;
  cursor: pointer;
  transition: color 0.3s;
  line-height: 1;
}

.prototype-magnifier-popup .close-btn:hover {
  color: #ff4d4f;
}

/* 主体内容布局 */
.prototype-magnifier-popup .popup-body {
  display: flex;
  padding: 24px;
  gap: 24px;
  align-items: center; /* 垂直居中对齐 */
}

/* 左侧图片容器 */
.prototype-magnifier-popup .prototype-image-container {
  width: 280px; /* 控制图片区域的宽度 */
  height: 200px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(16, 40, 70, 0.4);
  border: 1px dashed rgba(45, 183, 245, 0.4);
  border-radius: 6px;
  padding: 10px;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);
}

/* 自定义抠图样式 */
.prototype-magnifier-popup .custom-prototype-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  /* 给透明底的抠图加上赛博发光轮廓，自动捕捉你抠图的边缘 */
  filter: drop-shadow(0 0 6px rgba(45, 183, 245, 0.6));
}

/* 右侧文本介绍样式 */
.prototype-magnifier-popup .prototype-desc {
  flex: 1;
  color: #a0d8ef; /* 柔和的科技蓝白 */
  font-size: 13px;
  line-height: 1.6;
}

.prototype-magnifier-popup .desc-title {
  color: #00e5ff;
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: bold;
  border-left: 3px solid #00e5ff;
  padding-left: 8px;
}

.prototype-magnifier-popup .desc-list {
  padding-left: 16px;
  margin: 0;
  list-style-type: none; /* 使用自定义的发光圆点 */
}

.prototype-magnifier-popup .desc-list li {
  margin-bottom: 12px;
  position: relative;
}

/* 列表自定义发光圆点 */
.prototype-magnifier-popup .desc-list li::before {
  content: "";
  position: absolute;
  left: -14px;
  top: 6px;
  width: 5px;
  height: 5px;
  background: #2db7f5;
  border-radius: 50%;
  box-shadow: 0 0 5px #2db7f5;
}

.prototype-magnifier-popup .desc-list strong {
  color: #fff;
}
/* ========================================
   📋 推演阶段说明悬浮卡片
   ======================================== */
.phase-desc-card {
  
}
/* ================================================================
   🚨 救援装备出动操控面板样式
   ================================================================ */
.rescue-dispatch-panel {
  position: absolute;
  right: 28px;
  bottom: 200px;
  width: 340px;
  z-index: 700;
  background: rgba(6, 12, 26, 0.94);
  backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: 14px;
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.75),
    0 0 20px rgba(239, 68, 68, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Microsoft YaHei', sans-serif;
  overflow: hidden;
}

.rescue-panel-header {
  padding: 14px 16px 10px;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.18), rgba(185, 28, 28, 0.08));
  border-bottom: 1px solid rgba(239, 68, 68, 0.2);
}

.rescue-panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.rescue-panel-icon {
  font-size: 18px;
  animation: rescue-pulse 2s ease-in-out infinite;
}

@keyframes rescue-pulse {
  0%, 100% { filter: drop-shadow(0 0 4px rgba(239, 68, 68, 0.6)); }
  50% { filter: drop-shadow(0 0 10px rgba(239, 68, 68, 0.9)); }
}

.rescue-panel-title {
  font-size: 15px;
  font-weight: 700;
  color: #fca5a5;
  letter-spacing: 0.5px;
  flex: 1;
}

.rescue-panel-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 20px;
  background: rgba(52, 211, 153, 0.15);
  border: 1px solid rgba(52, 211, 153, 0.35);
  color: #34d399;
  letter-spacing: 0.3px;
}

.rescue-panel-badge.badge-active {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
  color: #fca5a5;
  animation: badge-blink 1s step-start infinite;
}

@keyframes badge-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.rescue-panel-subtitle {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
  line-height: 1.5;
}

.rescue-panel-body {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rescue-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rescue-field-label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.rescue-scene-tabs {
  display: flex;
  gap: 6px;
}

.rescue-scene-btn {
  flex: 1;
  padding: 7px 6px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.55);
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  text-align: center;
}

.rescue-scene-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.rescue-scene-btn.active {
  background: rgba(239, 68, 68, 0.15);
  border-color: #ef4444;
  color: #fff;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.2);
}

.rescue-strategy-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.rescue-strategy-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.4);
  color: #a5b4fc;
}

.rescue-strategy-info {
  font-size: 10.5px;
  color: rgba(255, 255, 255, 0.4);
  font-style: italic;
}

.rescue-btn-row {
  display: flex;
  gap: 8px;
}

.rescue-ugvuav-btn,
.rescue-dispatch-btn {
  flex: 1;
  padding: 10px 8px;
  border: none;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.rescue-ugvuav-btn {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(37, 99, 235, 0.2));
  border: 1px solid rgba(59, 130, 246, 0.45);
  color: #93c5fd;
}

.rescue-ugvuav-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.4), rgba(37, 99, 235, 0.35));
  border-color: #3b82f6;
  color: #fff;
  box-shadow: 0 0 14px rgba(59, 130, 246, 0.35);
  transform: translateY(-1px);
}

.rescue-dispatch-btn {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.3), rgba(185, 28, 28, 0.25));
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #fca5a5;
}

.rescue-dispatch-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.5), rgba(185, 28, 28, 0.4));
  border-color: #ef4444;
  color: #fff;
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.4);
  transform: translateY(-1px);
}

.rescue-ugvuav-btn:disabled,
.rescue-dispatch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-icon-small {
  font-size: 13px;
}

.rescue-status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(52, 211, 153, 0.08);
  border: 1px solid rgba(52, 211, 153, 0.25);
  border-radius: 6px;
  font-size: 12px;
  color: #34d399;
  font-weight: 600;
}

.rescue-status-bar.status-error {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.25);
  color: #fca5a5;
}

.status-dot-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  flex-shrink: 0;
  animation: rescue-status-pulse 1.2s ease-in-out infinite;
}

.rescue-status-bar.status-error .status-dot-pulse {
  background: #ef4444;
}

@keyframes rescue-status-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

/* 救援装备面板 入场/退场过渡动画 */
.rescue-panel-slide-enter-active,
.rescue-panel-slide-leave-active {
  transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.rescue-panel-slide-enter-from {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}

.rescue-panel-slide-leave-to {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}

/* 高级毛玻璃悬浮窗样式 */
.premium-modeling-popup {
  position: absolute;
  width: 320px;
  border-radius: 12px;
  overflow: hidden;
  pointer-events: auto;
  z-index: 9999;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 255, 255, 0.2);
}
.premium-modeling-popup:hover {
  transform: translateY(-2px) scale(1.01);
  border-color: rgba(0, 255, 255, 0.6);
  box-shadow: 0 12px 40px rgba(0, 255, 255, 0.3);
}

.premium-modeling-popup .glass-bg {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(10, 15, 30, 0.7);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  z-index: 1;
}
.premium-modeling-popup .popup-content-wrapper {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
}
.premium-modeling-popup .popup-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(90deg, rgba(0,255,255,0.15) 0%, transparent 100%);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.premium-modeling-popup .title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.premium-modeling-popup .popup-header .title {
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 1px;
}
.premium-modeling-popup .status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #00ffcc;
  background: rgba(0, 255, 204, 0.1);
  padding: 2px 6px;
  border-radius: 10px;
  border: 1px solid rgba(0, 255, 204, 0.2);
  font-weight: bold;
}
.premium-modeling-popup .status-badge i {
  width: 6px;
  height: 6px;
  background: #00ffcc;
  border-radius: 50%;
  box-shadow: 0 0 8px #00ffcc;
  animation: cta-pulse 1.5s infinite;
}
@keyframes cta-pulse {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

.premium-modeling-popup .popup-header .close-btn {
  background: none;
  border: none;
  color: rgba(255,255,255,0.6);
  font-size: 20px;
  cursor: pointer;
  transition: color 0.2s;
}
.premium-modeling-popup .popup-header .close-btn:hover {
  color: #ff4757;
}
.premium-modeling-popup .popup-body {
  padding: 16px;
}
.premium-modeling-popup .video-container {
  position: relative;
  width: 100%;
  height: 150px;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0,255,255,0.25);
  transition: border-color 0.3s ease;
}
.premium-modeling-popup:hover .video-container {
  border-color: rgba(0, 255, 255, 0.6);
}

.premium-modeling-popup .scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: rgba(0, 255, 255, 0.3);
  box-shadow: 0 0 8px rgba(0, 255, 255, 0.7);
  animation: scan 4s linear infinite;
  pointer-events: none;
  z-index: 2;
}
@keyframes scan {
  0% { top: 0; }
  100% { top: 100%; }
}

.premium-modeling-popup .video-overlay-text {
  position: absolute;
  top: 10px;
  left: 10px;
  color: rgba(0,255,255,0.9);
  font-size: 11px;
  font-weight: bold;
  z-index: 3;
  pointer-events: none;
  text-shadow: 0 2px 4px rgba(0,0,0,0.8);
}
.premium-modeling-popup .ripple-effect {
  position: absolute;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(0,255,255,0.08) 0%, transparent 75%);
  animation: pulse-ring 2s infinite;
  pointer-events: none;
  z-index: 2;
}
@keyframes pulse-ring {
  0% { transform: scale(0.96); opacity: 0.4; }
  50% { transform: scale(1.04); opacity: 0.8; }
  100% { transform: scale(0.96); opacity: 0.4; }
}

.premium-modeling-popup .hover-cta-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(8, 15, 30, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 4;
  pointer-events: none;
}
.premium-modeling-popup .video-container:hover .hover-cta-overlay {
  opacity: 1;
}
.premium-modeling-popup .cta-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #00ffff;
  font-weight: bold;
  font-size: 12px;
  text-shadow: 0 0 8px rgba(0, 255, 255, 0.8);
  text-align: center;
  padding: 0 16px;
}
.premium-modeling-popup .cta-icon {
  font-size: 18px;
  animation: bounce 1.5s infinite;
}
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.premium-modeling-popup .action-btn-wrap {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}
.premium-modeling-popup .cyber-action-btn {
  width: 100%;
  padding: 8px 16px;
  background: linear-gradient(135deg, rgba(0, 255, 255, 0.15) 0%, rgba(0, 150, 255, 0.15) 100%);
  border: 1px solid rgba(0, 255, 255, 0.35);
  color: #00ffff;
  border-radius: 6px;
  font-size: 13px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  text-shadow: 0 0 5px rgba(0, 255, 255, 0.6);
}
.premium-modeling-popup .cyber-action-btn:hover {
  background: linear-gradient(135deg, rgba(0, 255, 255, 0.28) 0%, rgba(0, 150, 255, 0.28) 100%);
  border-color: #00ffff;
  box-shadow: 0 0 12px rgba(0, 255, 255, 0.4);
  transform: scale(1.02);
}
.premium-modeling-popup .arrow-svg {
  transition: transform 0.3s ease;
}
.premium-modeling-popup .cyber-action-btn:hover .arrow-svg {
  transform: translateX(4px);
}

.premium-modeling-popup .popup-footer {
  display: flex;
  justify-content: space-between;
  padding: 8px 16px;
  background: rgba(0,0,0,0.3);
  border-top: 1px solid rgba(255,255,255,0.05);
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

/* ===========================================================
   协同响应效能指标悬浮窗 — 右上角
   =========================================================== */
.collab-metrics-popup {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 296px;
  z-index: 9200;
  pointer-events: auto;
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(6, 18, 38, 0.96) 0%, rgba(10, 25, 48, 0.96) 100%);
  border: 1px solid rgba(0, 212, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 200, 255, 0.15), 0 2px 12px rgba(0,0,0,0.5);
  backdrop-filter: blur(14px);
  padding: 14px 16px 12px;
  font-family: 'Inter', 'Microsoft YaHei', sans-serif;
  font-size: 12px;
  color: rgba(255,255,255,0.88);
}

/* 入场/离场动画 */
.metrics-popup-fade-enter-active,
.metrics-popup-fade-leave-active {
  transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.metrics-popup-fade-enter-from,
.metrics-popup-fade-leave-to {
  opacity: 0;
  transform: translateY(-12px) scale(0.96);
}

/* 标题区 */
.cmp-header {
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.18);
  padding-bottom: 8px;
}
.cmp-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cmp-icon {
  font-size: 20px;
  filter: drop-shadow(0 0 6px rgba(0, 242, 254, 0.6));
}
.cmp-title {
  font-size: var(--hud-h1-font-size, 20px);
  font-weight: var(--hud-h1-font-weight, 700);
  color: var(--hud-h1-color, #00f2fe);
  letter-spacing: 0.5px;
  flex: 1;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
}
.cmp-pulse {
  width: 9px; height: 9px;
  border-radius: 50%;
  background: #00f2fe;
  box-shadow: 0 0 8px #00f2fe;
  animation: cmp-blink 1s infinite;
}
@keyframes cmp-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}
.cmp-scene-label {
  margin-top: 4px;
  font-size: var(--hud-subtitle-font-size, 13px);
  color: rgba(226, 241, 255, 0.75);
  letter-spacing: 0.3px;
}

/* 分区标题 (二级标题 16px) */
.cmp-section-title {
  font-size: var(--hud-h2-font-size, 16px);
  font-weight: var(--hud-h2-font-weight, 600);
  color: var(--hud-h2-color, #e2f1ff);
  margin-top: 10px;
  margin-bottom: 6px;
  letter-spacing: 0.4px;
  text-shadow: 0 0 6px rgba(0, 242, 254, 0.3);
}

/* 指标网格 */
.cmp-metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.cmp-metric-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 8px 10px 6px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: background 0.2s;
}
.cmp-metric-card:hover { background: rgba(0,242,254,0.08); }
.cmp-metric-card.cmp-perfect { border-color: rgba(52,211,153,0.45); }
.cmp-val {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
}
.cmp-val small { font-size: 13px; font-weight: 500; margin-left: 2px; opacity: 0.85; }
.cmp-lbl { font-size: 13px; color: rgba(226, 241, 255, 0.75); }
.cmp-cyan  { color: #00ffff; }
.cmp-amber { color: #fbbf24; }
.cmp-green { color: #34d399; }
.cmp-purple{ color: #a78bfa; }
.cmp-pink  { color: #f472b6; }

/* 算法对比行 */
.cmp-compare-row {
  margin-top: 10px;
  font-size: 13px;
  color: rgba(226, 241, 255, 0.8);
  line-height: 1.6;
}
.cmp-compare-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0,242,254,0.15);
  color: #00ffff;
  font-size: 12px;
  font-weight: 600;
}

/* 速度 & 场景标签行 */
.cmp-footer-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255,255,255,0.08);
  font-size: 13px;
  color: rgba(226, 241, 255, 0.8);
  flex-wrap: wrap;
}
.cmp-tag-warn {
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(251,191,36,0.18);
  color: #fbbf24;
  font-size: 10px;
  font-weight: 600;
  border: 1px solid rgba(251,191,36,0.3);
}

/* 更新时间 */
.cmp-updated-at {
  margin-top: 6px;
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  text-align: right;
}

/* 加载中状态 */
.cmp-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  color: rgba(255,255,255,0.5);
  font-size: 11px;
}
.cmp-spin {
  width: 14px; height: 14px;
  border: 2px solid rgba(0,212,255,0.3);
  border-top-color: #00d4ff;
  border-radius: 50%;
  animation: cmp-spin 0.8s linear infinite;
}
@keyframes cmp-spin { to { transform: rotate(360deg); } }

/* 空数据状态 */
.cmp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 0;
  color: rgba(255,255,255,0.45);
  font-size: 11px;
}
.cmp-empty small { font-size: 10px; color: rgba(255,255,255,0.3); }

/* ===========================================================
   多智能体全局寻优决策日志悬浮窗 — 右上角 (Phase 11)
   =========================================================== */
.agent-log-popup {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 420px;
  max-height: calc(100vh - 60px);
  z-index: 9200;
  pointer-events: auto;
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(8, 16, 36, 0.98) 0%, rgba(12, 24, 52, 0.98) 100%);
  border: 1px solid rgba(56, 189, 248, 0.28);
  box-shadow: 0 12px 40px rgba(8, 16, 36, 0.6), 0 0 20px rgba(56, 189, 248, 0.08);
  backdrop-filter: blur(16px);
  display: flex;
  flex-direction: column;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
  color: rgba(255,255,255,0.92);
}

/* 入场/离场动画 */
.agent-log-fade-enter-active,
.agent-log-fade-leave-active {
  transition: opacity 0.38s cubic-bezier(0.25, 0.8, 0.25, 1), transform 0.38s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.agent-log-fade-enter-from,
.agent-log-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

/* 标题栏 */
.alp-header {
  padding: 14px 18px 12px;
  background: rgba(15, 23, 42, 0.6);
  border-bottom: 1px solid rgba(56, 189, 248, 0.15);
  flex-shrink: 0;
}
.alp-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.alp-icon {
  font-size: 22px;
  flex-shrink: 0;
  filter: drop-shadow(0 0 6px rgba(0, 242, 254, 0.6));
}
.alp-title-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.alp-title {
  font-size: var(--hud-h1-font-size, 20px);
  font-weight: var(--hud-h1-font-weight, 700);
  color: var(--hud-h1-color, #00f2fe);
  letter-spacing: 0.5px;
  line-height: 1.25;
  white-space: nowrap;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
}
.alp-subtitle {
  font-size: var(--hud-subtitle-font-size, 13px);
  color: rgba(226, 241, 255, 0.7);
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
  margin-top: 3px;
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.alp-badge {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 9px;
  border-radius: 6px;
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
  letter-spacing: 0.5px;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
  white-space: nowrap;
}

/* Tab 切换栏 */
.alp-tabs {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  background: rgba(15, 23, 42, 0.4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}
.alp-tab-btn {
  flex: 1;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: #cbd5e1;
  font-size: 14px;
  font-weight: 600;
  padding: 6px 0;
  cursor: pointer;
  transition: all 0.25s ease;
  text-align: center;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
}
.alp-tab-btn:hover {
  color: #ffffff;
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(56, 189, 248, 0.3);
}
.alp-tab-btn.active {
  background: rgba(15, 23, 42, 0.85);
  color: var(--btn-color);
  border: 1px solid var(--btn-color);
  box-shadow: 0 0 8px var(--btn-color);
  font-weight: 700;
}

/* 决策卡片单栏区域 */
.alp-decision-single {
  overflow-y: auto;
  padding: 12px;
  flex: 1;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
}
.alp-decision-single::-webkit-scrollbar { width: 4px; }
.alp-decision-single::-webkit-scrollbar-thumb { background: rgba(56,189,248,0.25); border-radius: 2px; }

.alp-agent-card {
  position: relative;
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.55) 0%, rgba(15, 23, 42, 0.65) 100%);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-left: 4px solid var(--alp-color);
  border-radius: 8px;
  padding: 14px 16px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
}
.alp-agent-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.25);
  border-color: rgba(255,255,255,0.1);
}
/* 卡片左上角柔和渐变微光 */
.alp-agent-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: radial-gradient(circle at 0% 0%, var(--alp-color) 0%, transparent 45%);
  opacity: 0.07;
  pointer-events: none;
  border-radius: 8px;
}

/* 头部：改用纵向排列 */
.alp-agent-head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 10px;
}
.alp-agent-label {
  font-size: 18px;
  font-weight: 700;
  color: var(--alp-color);
  letter-spacing: 0.5px;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
}
.alp-agent-winner {
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.4;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
  text-shadow: 0 0 6px rgba(255, 255, 255, 0.3);
}

/* 指标区 */
.alp-stats {
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
}
.alp-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #cbd5e1;
  margin-bottom: 8px;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
}
.alp-stat-row:last-child { margin-bottom: 0; }
.alp-highlight { color: #ffffff; }
.alp-highlight .stat-val { color: #00ffff; font-weight: 700; }
.stat-lbl { font-size: 14px; font-weight: 600; color: #e2e8f0; }
.stat-val { font-family: 'Microsoft YaHei', '微软雅黑', sans-serif; font-size: 15px; font-weight: 700; color: #cbd5e1; }


.alp-loser-reason { 
  font-size: 11px; 
  color: #f87171; 
  margin-top: 2px; 
}

/* 加载/空状态 */
.alp-loading, .alp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  font-size: 13px;
  color: rgba(255,255,255,0.45);
}
.alp-loading { flex-direction: row; }
.alp-spin {
  width: 18px; height: 18px;
  border: 2px solid rgba(56,189,248,0.3);
  border-top-color: #38bdf8;
  border-radius: 50%;
  animation: alpSpin 0.8s linear infinite;
}
@keyframes alpSpin { to { transform: rotate(360deg); } }
.alp-empty small { font-size: 11px; color: rgba(255,255,255,0.3); }

/*
 * 总览切图采用固定的数据矩阵，而不是三段独立滚动区。
 * 卡口汇总、车辆分类和图表/流量信息会同时留在当前视口内，避免用户通过滑块查找数据。
 */
.lkyw-monitor-hud.high-end-panel .hud-scroll-content {
  display: grid;
  grid-template-rows: minmax(104px, .68fr) minmax(156px, 1fr) minmax(238px, 1.55fr);
  gap: 8px;
  padding: 8px;
  overflow: hidden;
}
.airport-command-slot {
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(51, 168, 217, .5);
  background: linear-gradient(145deg, rgba(4, 31, 55, .94), rgba(3, 20, 38, .9));
  box-shadow: inset 0 0 18px rgba(0, 214, 255, .07);
}
.airport-command-slot--summary .cyber-border-flow-panel { margin: 6px 8px; padding: 7px 9px; }
.airport-command-slot--summary .border-panel-header { margin-bottom: 5px; padding-bottom: 3px; }
.airport-command-slot--summary .border-title { font-size: 13px; }
.airport-command-slot--summary .net-inflow-badge { font-size: 11px; }
.airport-command-slot--summary .border-flow-card { padding: 5px 7px; }
.airport-command-slot--summary .flow-label,
.airport-command-slot--summary .flow-anim-arrow { font-size: 12px; }
.airport-command-slot--summary .border-flow-val { font-size: 20px; }
.airport-command-slot--summary .flow-unit { font-size: 11px; }

/* 三种车辆以同级数据格同时呈现，点击仍可筛选地图车辆。 */
.airport-command-slot--fleet > div:first-child {
  margin: 6px 8px 4px !important;
}
.airport-command-slot--fleet > div:first-child span { font-size: 12px !important; }
.airport-command-slot--fleet > div:first-child button { padding: 3px 7px !important; font-size: 10px !important; }
.airport-command-slot--fleet .lkyw-hud-grid {
  margin: 0 8px 7px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 5px;
}
.airport-command-slot--fleet .lkyw-hud-card {
  min-width: 0;
  min-height: 103px;
  padding: 6px;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}
.airport-command-slot--fleet .lkyw-hud-card:hover { transform: translateY(-2px); }
.airport-command-slot--fleet .lkyw-card-header { margin-bottom: 3px; align-items: flex-start; }
.airport-command-slot--fleet .lkyw-label { font-size: 12px; line-height: 1.2; }
.airport-command-slot--fleet .lkyw-subbadge {
  font-size: 9px;
  padding: 1px 3px;
  white-space: nowrap;
}
.airport-command-slot--fleet .lkyw-card-main { display: block; margin-top: 0; }
.airport-command-slot--fleet .lkyw-val-block { gap: 2px; }
.airport-command-slot--fleet .lkyw-value { font-size: 20px; }
.airport-command-slot--fleet .lkyw-unit { font-size: 10px; }
.airport-command-slot--fleet .cyber-flow-box-group { gap: 3px; margin-top: 5px; }
.airport-command-slot--fleet .cyber-flow-box {
  min-width: 0;
  flex: 1;
  display: block;
  padding: 3px;
  text-align: center;
}
.airport-command-slot--fleet .box-icon,
.airport-command-slot--fleet .box-val { display: block; font-size: 9px; }
.airport-command-slot--fleet .box-val { margin-top: 2px; font-size: 11px; }
.airport-command-slot--fleet .lkyw-card-footer-tip { display: none; }

/* 图表区为 2 × 2 资料格：占比分布、抓拍流和干线流量都无需滚动即可浏览。 */
.airport-command-slot--detail.overview-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.06fr) minmax(0, .94fr);
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: 5px;
  padding: 5px;
}
.airport-command-slot--detail.overview-layout .hud-chart-section {
  min-width: 0;
  min-height: 0;
  margin: 0;
  padding: 6px;
  overflow: hidden;
  border-radius: 4px;
}
.airport-command-slot--detail.overview-layout .pie-section { grid-row: 1 / span 2; }
.airport-command-slot--detail.overview-layout .chart-title-bar { margin-bottom: 4px; padding-bottom: 3px; }
.airport-command-slot--detail.overview-layout .chart-title { font-size: 11px; }
.airport-command-slot--detail.overview-layout .chart-sub { font-size: 9px; }
.airport-command-slot--detail.overview-layout .pie-chart-container { display: block; }
.airport-command-slot--detail.overview-layout .svg-pie-wrapper { width: 88px; height: 88px; margin: 0 auto 5px; }
.airport-command-slot--detail.overview-layout .pie-total-num { font-size: 15px; }
.airport-command-slot--detail.overview-layout .pie-total-unit { font-size: 9px; margin-top: 1px; }
.airport-command-slot--detail.overview-layout .pie-legend { gap: 3px; }
.airport-command-slot--detail.overview-layout .legend-row { gap: 4px; padding: 3px 4px; font-size: 10px; }
.airport-command-slot--detail.overview-layout .legend-name,
.airport-command-slot--detail.overview-layout .legend-val { font-size: 10px; }
.airport-command-slot--detail.overview-layout .camera-log-list { gap: 2px; }
.airport-command-slot--detail.overview-layout .camera-log-item { padding: 3px 2px; gap: 3px; }
.airport-command-slot--detail.overview-layout .camera-log-item:nth-child(n + 4) { display: none; }
.airport-command-slot--detail.overview-layout .log-time,
.airport-command-slot--detail.overview-layout .log-loc,
.airport-command-slot--detail.overview-layout .log-plate,
.airport-command-slot--detail.overview-layout .log-tag { font-size: 9px; }
.airport-command-slot--detail.overview-layout .log-loc { max-width: 55px; }
.airport-command-slot--detail.overview-layout .bar-chart-list { gap: 3px; }
.airport-command-slot--detail.overview-layout .bar-item:nth-child(n + 4) { display: none; }
.airport-command-slot--detail.overview-layout .bar-info-row { margin-bottom: 2px; }
.airport-command-slot--detail.overview-layout .highway-name,
.airport-command-slot--detail.overview-layout .bar-count,
.airport-command-slot--detail.overview-layout .hazard-tag { font-size: 9px; }
.airport-command-slot--detail.overview-layout .rank-badge { transform: scale(.8); transform-origin: left center; }
.airport-command-slot--detail.overview-layout .bar-track { height: 4px; }

/* 风险预警与卡口排行沿用原有自适应内容高度，避免切换标签后被总览网格裁切。 */
.airport-command-slot--detail:not(.overview-layout) { overflow: auto; }

/* 风险预警、卡口排行使用整块主体空间；不再继承总览的三段占位格。 */
.lkyw-monitor-hud.high-end-panel .hud-scroll-content--risk,
.lkyw-monitor-hud.high-end-panel .hud-scroll-content--checkpoint {
  display: flex;
  flex-direction: column;
  padding: 8px;
  overflow: hidden;
}
.hud-scroll-content--risk .airport-command-slot--detail,
.hud-scroll-content--checkpoint .airport-command-slot--detail {
  flex: 1;
  min-height: 0;
}
.airport-command-slot--detail.tab-layout {
  display: flex;
  flex-direction: column;
  padding: 9px;
  overflow: hidden;
}
.airport-command-slot--detail.tab-layout .hud-tab-pane {
  height: 100%;
  min-height: 0;
  gap: 8px;
}
.airport-command-slot--detail.tab-layout .chart-title-bar {
  margin: 0;
  padding-bottom: 5px;
}
.airport-command-slot--detail.tab-layout .chart-title { font-size: 14px; }
.airport-command-slot--detail.tab-layout .chart-sub { font-size: 10px; }

/* 风险标签页：指标、处置控件与告警卡片同时可见，便于指挥操作。 */
.airport-command-slot--detail.tab-layout .risk-summary-grid { gap: 5px; }
.airport-command-slot--detail.tab-layout .risk-summary-item { padding: 6px 2px; border-radius: 5px; }
.airport-command-slot--detail.tab-layout .risk-num { font-size: 22px; line-height: 1; }
.airport-command-slot--detail.tab-layout .risk-lbl { font-size: 10px; }
.hud-control-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 5px;
}
.hud-control-row button {
  min-width: 0;
  padding: 5px 3px;
  border: 1px solid rgba(0, 229, 255, .38);
  border-radius: 4px;
  background: rgba(0, 117, 158, .14);
  color: #9cecff;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
}
.hud-control-row button:hover { background: rgba(0, 229, 255, .17); color: #fff; }
.airport-command-slot--detail.tab-layout .risk-vehicle-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 5px;
}
.airport-command-slot--detail.tab-layout .risk-card-item { padding: 7px 8px; gap: 3px; border-radius: 5px; }
.airport-command-slot--detail.tab-layout .risk-plate { font-size: 14px; }
.airport-command-slot--detail.tab-layout .risk-type-tag,
.airport-command-slot--detail.tab-layout .risk-level-badge { font-size: 10px; padding: 2px 4px; }
.airport-command-slot--detail.tab-layout .risk-reason { font-size: 11px; line-height: 1.35; }
.airport-command-slot--detail.tab-layout .risk-meta-row { font-size: 10px; line-height: 1.25; }
.airport-command-slot--detail.tab-layout .risk-action-btn { padding: 4px 8px; font-size: 10px; border-radius: 4px; }

/* 卡口页：用摘要与紧凑排行卡替代留白，关键流量指标一眼可读。 */
.checkpoint-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  padding: 6px;
  border: 1px solid rgba(0, 229, 255, .16);
  background: rgba(0, 101, 142, .1);
}
.checkpoint-overview span { color: #7eabc1; font-size: 10px; text-align: center; }
.checkpoint-overview b { display: block; margin-bottom: 1px; color: #20e6ff; font-size: 13px; }
.airport-command-slot--detail.tab-layout .checkpoint-list { gap: 5px; }
.airport-command-slot--detail.tab-layout .checkpoint-card { padding: 7px; gap: 4px; border-radius: 5px; }
.airport-command-slot--detail.tab-layout .cp-rank { font-size: 10px; padding: 3px 4px; }
.airport-command-slot--detail.tab-layout .cp-name { margin-left: 5px; font-size: 12px; line-height: 1.25; }
.airport-command-slot--detail.tab-layout .cp-status { font-size: 11px; white-space: nowrap; }
.airport-command-slot--detail.tab-layout .cp-stats-row { gap: 3px; padding: 4px; }
.airport-command-slot--detail.tab-layout .cp-label { font-size: 10px; }
.airport-command-slot--detail.tab-layout .cp-val { font-size: 13px; }
.airport-command-slot--detail.tab-layout .cp-val small { font-size: 9px; }

/* 总览恢复为纵向信息流：按业务阅读顺序逐块向下排列，不再横向拼接数据卡。 */
.lkyw-monitor-hud.high-end-panel .hud-scroll-content--overview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  overflow-y: auto;
  scrollbar-width: none;
}
.lkyw-monitor-hud.high-end-panel .hud-scroll-content--overview::-webkit-scrollbar { display: none; }
.hud-scroll-content--overview > .airport-command-slot {
  flex: 0 0 auto;
  overflow: visible;
}
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-hud-grid {
  grid-template-columns: 1fr;
  gap: 7px;
}
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-hud-card {
  min-height: 0;
  padding: 8px 10px;
}
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-card-header { align-items: center; }
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-label { font-size: 15px; }
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-subbadge { font-size: 11px; padding: 2px 5px; }
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-card-main { display: flex; }
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-value { font-size: 24px; }
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-unit { font-size: 12px; }
.hud-scroll-content--overview .airport-command-slot--fleet .cyber-flow-box-group { margin-top: 0; gap: 5px; }
.hud-scroll-content--overview .airport-command-slot--fleet .cyber-flow-box {
  display: flex;
  padding: 4px 7px;
  text-align: left;
}
.hud-scroll-content--overview .airport-command-slot--fleet .box-icon,
.hud-scroll-content--overview .airport-command-slot--fleet .box-val { display: inline; font-size: 11px; }
.hud-scroll-content--overview .airport-command-slot--fleet .box-val { margin: 0 0 0 4px; font-size: 12px; }
.hud-scroll-content--overview .airport-command-slot--fleet .lkyw-card-footer-tip { display: flex; font-size: 11px; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout {
  display: block;
  padding: 8px;
}
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .hud-chart-section {
  margin: 0 0 8px;
  padding: 10px;
  overflow: visible;
}
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .pie-section { display: block; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .chart-title { font-size: 14px; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .chart-sub { font-size: 11px; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .pie-chart-container { display: flex; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .svg-pie-wrapper { width: 112px; height: 112px; margin: 0; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .pie-total-num { font-size: 19px; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .pie-total-unit { font-size: 11px; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .pie-legend { gap: 5px; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .legend-row { padding: 4px 6px; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .legend-name,
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .legend-val { font-size: 12px; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .camera-log-item:nth-child(n + 4) { display: flex; }
.hud-scroll-content--overview .airport-command-slot--detail.overview-layout .bar-item:nth-child(n + 4) { display: block; }

/* 低分辨率屏幕继续保持同一套固定格局。 */
@media (max-height: 820px) {
  .lkyw-monitor-hud.high-end-panel .hud-scroll-content {
    grid-template-rows: minmax(96px, .65fr) minmax(145px, .98fr) minmax(214px, 1.45fr);
  }
  .airport-command-slot--fleet .lkyw-hud-card { min-height: 95px; }
  .airport-command-slot--detail .svg-pie-wrapper { width: 78px; height: 78px; }
}

/* =========================================================
   故事线控件统一视觉规范
   与首页左侧栏共享：中文界面字体、青蓝分栏标题、紧凑间距和数据字形。
========================================================= */
.cesium-wrapper {
  --story-panel-bg: linear-gradient(145deg, rgba(1, 35, 57, 0.9), rgba(3, 17, 31, 0.82));
  --story-panel-line: rgba(42, 193, 223, 0.34);
  --story-divider: rgba(105, 191, 214, 0.18);
  --story-title-bg: linear-gradient(90deg, rgba(35, 129, 153, 0.3), transparent);
  --story-title-color: #eafcff;
  --story-copy-color: #a6cbd3;
  --story-accent: #1dddf4;
  --story-font-body: 'LkywOppoSans', "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif;
  --story-font-title: 'LkywTencentSans', "Microsoft YaHei", sans-serif;
  --story-font-data: 'LkywDigital', "DIN Alternate", "Arial Narrow", Arial, sans-serif;
}

.accident-detail-popup,
.story-detection-alert,
.camera-stream-popup,
.simulation-popup-panel,
.shelter-popup-panel,
.reconstruction-fusion-panel,
.prototype-magnifier-popup,
.sensor-fusion-panel {
  color: var(--story-title-color);
  font-family: var(--story-font-body) !important;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
  background: var(--story-panel-bg);
  border: 1px solid var(--story-panel-line);
  border-radius: 6px;
  box-shadow: inset 0 0 24px rgba(0, 191, 255, 0.07), 0 10px 30px rgba(0, 8, 18, 0.52);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.accident-detail-popup button,
.story-detection-alert button,
.camera-stream-popup button,
.simulation-popup-panel button,
.shelter-popup-panel button,
.reconstruction-fusion-panel button,
.prototype-magnifier-popup button,
.sensor-fusion-panel button {
  font-family: var(--story-font-body);
}

.accident-detail-header,
.detection-popup-header,
.camera-stream-header,
.simulation-popup-header,
.shelter-popup-header,
.fusion-panel-header,
.prototype-magnifier-popup .popup-header,
.sensor-fusion-panel .fusion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  padding: 0 12px;
  border-bottom: 1px solid rgba(126, 212, 236, 0.25);
  border-radius: 0;
  background: var(--story-title-bg);
}

.accident-detail-header > span:first-child,
.detection-popup-header .header-title,
.camera-stream-title,
.simulation-popup-header .header-title,
.shelter-popup-header .dispatch-title-row,
.fusion-panel-header .main-title,
.prototype-magnifier-popup .popup-header .title,
.sensor-fusion-panel .fusion-header .title {
  color: var(--story-title-color);
  font-family: var(--story-font-title);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.3px;
  text-shadow: 0 0 8px rgba(109, 231, 249, 0.28);
}

.detection-popup-header::before,
.camera-stream-header::before,
.simulation-popup-header::before,
.shelter-popup-header::before,
.fusion-panel-header::before,
.prototype-magnifier-popup .popup-header::before,
.sensor-fusion-panel .fusion-header::before {
  flex: 0 0 auto;
  width: 4px;
  height: 18px;
  margin-right: 8px;
  content: '';
  background: var(--story-accent);
  box-shadow: 0 0 6px rgba(29, 221, 244, 0.85);
}

.detection-popup-header .header-title-wrap,
.camera-stream-header .camera-title-wrap,
.simulation-popup-header .header-title-wrap,
.shelter-popup-header .dispatch-title-row,
.fusion-panel-header .title-cluster {
  flex: 1;
  min-width: 0;
}

.accident-detail-popup .close-btn,
.story-detection-alert .close-btn,
.camera-stream-popup .close-btn,
.simulation-popup-panel .close-btn,
.shelter-popup-panel .close-btn,
.reconstruction-fusion-panel .panel-close-btn,
.prototype-magnifier-popup .close-btn {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: #8fb9c4;
  font-size: 18px;
  line-height: 1;
}

.accident-detail-popup .close-btn:hover,
.story-detection-alert .close-btn:hover,
.camera-stream-popup .close-btn:hover,
.simulation-popup-panel .close-btn:hover,
.shelter-popup-panel .close-btn:hover,
.reconstruction-fusion-panel .panel-close-btn:hover,
.prototype-magnifier-popup .close-btn:hover {
  border-color: rgba(255, 135, 149, 0.3);
  background: rgba(255, 77, 109, 0.1);
  color: #ff8795;
}

.detection-popup-content,
.camera-stream-body,
.simulation-popup-content,
.prototype-magnifier-popup .popup-body,
.reconstruction-fusion-panel .fusion-panel-body {
  padding: 14px;
  gap: 12px;
}

.simulation-popup-content .desc-text,
.camera-stream-popup,
.story-detection-alert,
.prototype-magnifier-popup .prototype-desc,
.reconstruction-fusion-panel {
  color: var(--story-copy-color);
  font-size: 14px;
  line-height: 1.55;
}

.story-confidence-card strong,
.camera-info-item strong,
.camera-live-result-item strong,
.shelter-popup-table td.value,
.reconstruction-fusion-panel .metric-value,
.sensor-fusion-panel .text-cyan {
  font-family: var(--story-font-data);
  font-variant-numeric: tabular-nums;
}

.story-confidence-card,
.camera-info-item,
.camera-detection-panel,
.story-advice-bar,
.prototype-magnifier-popup .prototype-desc {
  border: 1px solid rgba(93, 197, 214, 0.24);
  border-radius: 5px;
  background: rgba(2, 42, 61, 0.3);
}

.simulation-popup-panel .enter-sim-btn,
.story-detection-alert .reset-btn,
.reconstruction-fusion-panel .mode-tab-btn,
.reconstruction-fusion-panel .enter-modeling-cta-btn,
.ugv-sensor-tab {
  min-height: 34px;
  border: 1px solid rgba(34, 182, 216, 0.42);
  border-radius: 4px;
  background: rgba(0, 117, 148, 0.16);
  color: #72efff;
  font-size: 13px;
  font-weight: 600;
  text-shadow: none;
}

/* 无人机、无人车信息窗由旧白色表格统一为侧栏式深色信息行。 */
.shelter-popup-panel {
  width: 240px;
  overflow: visible;
}

.shelter-popup-table {
  color: #c9edf2;
  font-size: 13px;
}

.shelter-popup-table td {
  padding: 8px 10px;
  border: 0;
  border-bottom: 1px solid var(--story-divider);
}

.shelter-popup-table td.label {
  width: 44%;
  color: #9dc0c9;
  background: transparent;
  font-weight: 500;
  text-align: left;
}

.shelter-popup-table td.value {
  color: #e5f6f8;
  background: transparent;
  font-size: 14px;
  font-weight: 700;
  text-align: right;
}

.shelter-popup-arrow,
.ugv-dispatch-popup .ugv-arrow {
  border-top-color: rgba(3, 17, 31, 0.9);
}

/* 立体传感网矩阵完全采用首页左侧栏的分栏与信息行节奏。 */
.sensor-fusion-panel {
  width: clamp(360px, 22vw, 440px);
  zoom: 1.1;
  clip-path: none;
  overflow: hidden;
  font-size: 15px;
  line-height: 1.45;
}

.sensor-fusion-panel::before,
.sensor-fusion-panel::after {
  display: none;
}

.sensor-fusion-panel .fusion-header {
  min-height: 44px;
  padding: 0 14px;
}

.sensor-fusion-panel .fusion-header::before {
  height: 19px;
  margin-right: 9px;
}

.sensor-fusion-panel .fusion-header .icon {
  margin-right: 8px;
  font-size: 19px;
}

.sensor-fusion-panel .fusion-header .title {
  font-size: 20px;
}

.sensor-fusion-panel .fusion-list {
  gap: 0;
  padding: 8px 14px;
}

.sensor-fusion-panel .fusion-list li {
  min-height: 58px;
  padding: 8px 7px;
  border-bottom: 1px solid var(--story-divider);
}

.sensor-fusion-panel .node-name {
  color: #f1fdff;
  font-family: var(--story-font-title);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.sensor-fusion-panel .status-tag {
  max-width: 230px;
  padding: 5px 8px;
  color: #a6cbd3;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.35;
}

.sensor-fusion-panel .fusion-footer {
  gap: 9px;
  padding: 12px 14px 14px;
  border-top: 1px solid rgba(81, 212, 255, 0.22);
  background: rgba(2, 24, 40, 0.42);
}

.sensor-fusion-panel .footer-row {
  align-items: center;
  color: #9dc0c9;
  font-size: 15px;
}

.sensor-fusion-panel .footer-row strong {
  color: #e5f6f8;
  font-size: 15px;
  font-weight: 600;
}

.sensor-fusion-panel .text-cyan {
  color: #72efff;
  font-size: 20px;
}

@media (max-width: 1050px) {
  .sensor-fusion-panel { width: 330px; }
  .sensor-fusion-panel .fusion-list li { min-height: 52px; }
}

.accident-detail { width: min(1120px, 94vw); font-size: 19px; }
.accident-detail h2 { font-size: 30px; }
.accident-detail header { font-size: 18px; }
.accident-detail p { font-size: 19px; line-height: 1.9; }
.accident-detail img { height: 340px; object-fit: contain; background: #020d16; }
.accident-detail figcaption,.accident-detail footer span { font-size: 15px; }
.accident-detail button { font-size: 18px; }
.accident-photo-pending { height: 300px; display: grid; place-content: center; text-align: center; line-height: 2; background: #06121c; color: #a8c5ce; }
</style>

<style scoped>
.accident-detail-backdrop { position: absolute; inset: 0; z-index: 3000; display: grid; place-items: center; background: #00101c99; padding: 24px; }
.accident-detail { width: min(900px, 92vw); max-height: 85vh; overflow: auto; padding: 24px; box-sizing: border-box; background: linear-gradient(135deg,#092c3b,#061521); color: #dff7ff; border: 1px solid #d9ac44; border-radius: 12px; box-shadow: 0 24px 80px #0009; }
.accident-detail header,.accident-detail footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; } .accident-detail header { color: #ffd878; } .accident-detail h2 { margin: 18px 0; font-size: 25px; } .overview-accident-body { display: grid; grid-template-columns: 1.1fr 1fr; gap: 24px; } .accident-detail figure { margin: 0; } .accident-detail img { width: 100%; height: 250px; object-fit: cover; border-radius: 6px; } .accident-detail figcaption,.accident-detail footer span { font-size: 12px; color: #9bbac6; } .accident-detail p { line-height: 1.8; margin: 0 0 12px; } .accident-detail-date { color: #ffd878; } .accident-detail a { color: #63e4ff; } .accident-detail footer { justify-content: flex-end; margin-top: 24px; border-top: 1px solid #285164; padding-top: 16px; } .accident-detail button { color: #e8fbff; background: #105168; border: 1px solid #3ba6c3; padding: 9px 16px; border-radius: 5px; cursor: pointer; } @media(max-width: 700px) { .overview-accident-body { grid-template-columns: 1fr; } }
.story-detection-alert, .camera-stream-panel { box-sizing: border-box; max-width: max(280px, calc(100% - var(--layout-left-reserve, 20px) - var(--layout-right-reserve, 20px) - 32px)); max-height: calc(100% - var(--layout-timeline-space, 220px) - 80px); overflow-y: auto; }
.story-detection-alert { scrollbar-width: none; }
.story-detection-alert::-webkit-scrollbar { display: none; width: 0; height: 0; }
.story-detection-alert { left: auto !important; right: var(--layout-right-reserve, 20px); top: 80px !important; transform: none !important; }
.collab-metrics-popup, .agent-log-popup { right: var(--layout-right-reserve, 20px); top: 80px; box-sizing: border-box; max-width: calc(100% - var(--layout-left-reserve, 20px) - var(--layout-right-reserve, 20px)); max-height: calc(100% - var(--layout-timeline-space, 220px) - 96px); overflow-y: auto; }
.accident-detail { width: min(1120px, 94vw); font-size: 19px; }
.accident-detail h2 { font-size: 30px; }
.accident-detail header { font-size: 18px; }
.accident-detail p { font-size: 19px; line-height: 1.9; }
.accident-detail img { height: 340px; object-fit: contain; background: #020d16; }
.accident-detail figcaption,.accident-detail footer span { font-size: 15px; }
.accident-detail button { font-size: 18px; }
.accident-photo-pending { height: 300px; display: grid; place-content: center; text-align: center; line-height: 2; background: #06121c; color: #a8c5ce; }
.accident-detail { width: min(1280px, 94vw); padding: 30px; font-family: 'LkywOppoSans', var(--font-family-ui); font-size: 24px; }
.accident-detail header { font-family: 'LkywTencentSans', var(--font-family-ui); font-size: 23px; }
.accident-detail h2 { font-family: 'LkywTencentSans', var(--font-family-ui); font-size: 36px; line-height: 1.45; }
.accident-detail p { font-family: 'LkywOppoSans', var(--font-family-ui); font-size: 24px; line-height: 1.85; margin-bottom: 18px; }
.accident-detail a { font-family: 'LkywOppoSans', var(--font-family-ui); font-size: 23px; }
.overview-accident-body { grid-template-columns: 1fr 1.1fr; gap: 28px; }
.accident-detail img { height: 390px; }
@media(max-width: 700px) { .overview-accident-body { grid-template-columns: 1fr; } .accident-detail p,.accident-detail a { font-size: 20px; } .accident-detail h2 { font-size: 28px; } }
</style>
