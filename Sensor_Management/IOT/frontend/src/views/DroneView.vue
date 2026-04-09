<template>
  <div class="drone-page">
    <div class="header">
      <h2>🚁 无人机实时侦查终端</h2>
      <div class="status-badge" :class="{ live: isPlaying }">
        <span class="dot"></span> {{ isPlaying ? '实时图传中 (MJPEG)' : '信号中断' }}
      </div>
    </div>

    <div class="main-content">
      <div class="video-section">
        <div class="video-wrapper">
          <img 
            v-if="isPlaying"
            ref="videoElement" 
            :src="videoUrl"
            class="video-player" 
            crossorigin="anonymous" 
            alt="等待视频信号..."
          />
          <div v-else class="placeholder-box">
            <div class="icon">📡</div>
            <p>等待建立连接...</p>
          </div>
          
          <div v-if="isRecording" class="recording-badge">
            <div class="red-dot"></div> 
            REC {{ formatTime(recordingTime) }}
          </div>
        </div>

        <div class="play-controls">
          <div class="input-group">
            <span class="label">🔗 视频接口:</span>
            <input v-model="apiUrl" type="text" disabled />
          </div>
          <button @click="togglePlay" class="btn" :class="isPlaying ? 'btn-stop' : 'btn-start'">
            {{ isPlaying ? '⏹ 断开连接' : '▶ 建立连接' }}
          </button>
        </div>
      </div>

      <div class="control-panel">
        
        <div class="panel-card">
          <h3>📸 智能抓拍 (同步数据)</h3>
          <p class="desc">截图保存至 D:\sat\image，并关联传感器数据。</p>
          <div class="action-row">
            <button @click="manualSnapshot" :disabled="!isPlaying" class="btn btn-blue">
              📸 手动截图
            </button>
            <div class="toggle-group">
              <span class="label">自动抓拍 (0.5s):</span>
              <label class="switch">
                <input type="checkbox" v-model="isAutoCapturing" @change="handleAutoCaptureChange" :disabled="!isPlaying">
                <span class="slider round"></span>
              </label>
            </div>
          </div>
          <div class="log-box">
            <div v-for="(log, i) in captureLogs" :key="i" class="log-item">{{ log }}</div>
            <div v-if="captureLogs.length === 0" class="log-placeholder">暂无记录</div>
          </div>
        </div>

        <div class="panel-card">
          <h3>🎥 实时录像存证</h3>
          <p class="desc">录像结束时自动上传至 D:\sat\view。</p>
          <div class="action-row">
            <button 
              @click="toggleRecording" 
              :disabled="!isPlaying" 
              class="btn"
              :class="isRecording ? 'btn-red-outline' : 'btn-red'"
            >
              {{ isRecording ? '⏹ 结束并上传' : '● 开始录像' }}
            </button>
          </div>
          <div v-if="uploadStatus" class="upload-status" :class="{ error: uploadStatus.includes('失败') }">
            {{ uploadStatus }}
          </div>
        </div>

      </div>
    </div>

    <canvas ref="canvasElement" style="display: none;"></canvas>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue';

// --- 配置 ---
const PYTHON_STREAM_URL = 'http://localhost:8000/api/video_feed'; 
const API_BASE = 'http://localhost:8000/api';

// --- 状态 ---
const videoElement = ref(null);
const canvasElement = ref(null);
const isPlaying = ref(false);
const videoUrl = ref('');
const apiUrl = ref(PYTHON_STREAM_URL);

// 截图相关
const isAutoCapturing = ref(false);
const captureLogs = ref([]);
let captureTimer = null;

// 录像相关
const isRecording = ref(false);
const recordingTime = ref(0);
const uploadStatus = ref('');
let mediaRecorder = null;
let recordedChunks = [];
let recordTimerInterval = null;
let drawFrameId = null; // 用于 canvas 动画帧

// ================= 1. 播放逻辑 =================
const togglePlay = () => {
  if (isPlaying.value) stopPlay();
  else startPlay();
};

const startPlay = () => {
  // 加时间戳防止缓存
  videoUrl.value = `${PYTHON_STREAM_URL}?t=${new Date().getTime()}`;
  isPlaying.value = true;
};

const stopPlay = () => {
  videoUrl.value = '';
  isPlaying.value = false;
  
  // 停止所有附属功能
  if (isAutoCapturing.value) {
    isAutoCapturing.value = false;
    clearInterval(captureTimer);
  }
  if (isRecording.value) stopRecording();
};

// ================= 2. 截图上传逻辑 =================
const manualSnapshot = () => captureAndUpload("手动");

const handleAutoCaptureChange = () => {
  if (isAutoCapturing.value) {
    captureTimer = setInterval(() => captureAndUpload("自动"), 500); 
  } else {
    clearInterval(captureTimer);
  }
};

const captureAndUpload = async (type) => {
  if (!videoElement.value || !canvasElement.value) return;
  const img = videoElement.value;
  const canvas = canvasElement.value;
  const ctx = canvas.getContext('2d');

  if (img.naturalWidth === 0) return;

  // 绘图
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  ctx.drawImage(img, 0, 0);

  // 转 Base64 上传
  const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
  
  try {
    const res = await fetch(`${API_BASE}/save_drone_image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataUrl })
    });
    const data = await res.json();
    const timeStr = new Date().toLocaleTimeString();
    if (data.status === 'success') addLog(`[${timeStr}] ${type}抓拍成功`);
    else addLog(`[${timeStr}] ❌: ${data.msg}`);
  } catch (e) { console.error(e); }
};

const addLog = (msg) => {
  captureLogs.value.unshift(msg);
  if (captureLogs.value.length > 5) captureLogs.value.pop();
};

// ================= 3. 录像逻辑 (Canvas 转录黑科技) =================
const toggleRecording = () => {
  if (isRecording.value) stopRecording();
  else startRecording();
};

const startRecording = () => {
  if (!videoElement.value || !canvasElement.value) return;
  const img = videoElement.value;
  const canvas = canvasElement.value;
  const ctx = canvas.getContext('2d');

  if (img.naturalWidth === 0) {
    alert("视频未加载，无法录制");
    return;
  }

  // 1. 启动循环绘图 (把 img 画到 canvas 上，形成连续动画)
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  
  const drawLoop = () => {
    if (!isRecording.value) return;
    ctx.drawImage(img, 0, 0);
    drawFrameId = requestAnimationFrame(drawLoop);
  };
  isRecording.value = true; // 先标记为true
  drawLoop(); // 启动绘图循环

  // 2. 从 Canvas 捕获视频流 (30 FPS)
  const stream = canvas.captureStream(30);
  
  // 3. 启动录制
  mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
  recordedChunks = [];

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) recordedChunks.push(e.data);
  };

  mediaRecorder.onstop = uploadVideo; // 停止时触发上传

  mediaRecorder.start();
  
  // UI 计时
  recordingTime.value = 0;
  uploadStatus.value = '正在录制...';
  recordTimerInterval = setInterval(() => {
    recordingTime.value++;
  }, 1000);
};

const stopRecording = () => {
  if (!isRecording.value) return;

  // 停止录制器
  if (mediaRecorder) mediaRecorder.stop();
  
  // 停止 Canvas 绘图循环
  cancelAnimationFrame(drawFrameId);
  
  isRecording.value = false;
  clearInterval(recordTimerInterval);
};

const uploadVideo = async () => {
  uploadStatus.value = '⏳ 正在上传至 D:\\sat\\view ...';
  
  // 生成 Blob 文件
  const blob = new Blob(recordedChunks, { type: 'video/webm' });
  const formData = new FormData();
  formData.append('file', blob, 'recording.webm');

  try {
    const res = await fetch(`${API_BASE}/save_drone_video`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.status === 'success') {
      uploadStatus.value = `✅ 保存成功: ${data.path}`;
    } else {
      uploadStatus.value = `❌ 保存失败: ${data.msg}`;
    }
  } catch (e) {
    uploadStatus.value = '❌ 网络上传错误';
  }
};

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
};

onBeforeUnmount(() => {
  stopPlay();
});
</script>

<style scoped>
.drone-page { padding: 20px; height: 100vh; background: #f0f2f5; display: flex; flex-direction: column; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: white; padding: 15px 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.header h2 { margin: 0; color: #2c3e50; }

.status-badge { padding: 6px 12px; background: #eee; border-radius: 20px; font-size: 0.9rem; color: #666; display: flex; align-items: center; gap: 8px; }
.status-badge.live { background: #def7ec; color: #03543f; }
.dot { width: 8px; height: 8px; background: #999; border-radius: 50%; }
.live .dot { background: #31c48d; box-shadow: 0 0 5px #31c48d; }

.main-content { display: flex; gap: 20px; flex: 1; min-height: 0; }

/* 视频区 */
.video-section { flex: 2; display: flex; flex-direction: column; gap: 15px; }
.video-wrapper { background: black; border-radius: 12px; flex: 1; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.video-player { width: 100%; height: 100%; object-fit: contain; display: block; }

.recording-badge { position: absolute; top: 15px; right: 15px; background: rgba(220, 38, 38, 0.9); color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; display: flex; align-items: center; gap: 6px; animation: pulse 1s infinite; }
.red-dot { width: 8px; height: 8px; background: white; border-radius: 50%; }

.placeholder-box { color: #666; text-align: center; }
.placeholder-box .icon { font-size: 3rem; margin-bottom: 10px; opacity: 0.5; }

.play-controls { background: white; padding: 15px; border-radius: 12px; display: flex; gap: 15px; align-items: center; }
.input-group { flex: 1; display: flex; align-items: center; gap: 10px; }
.input-group input { flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 6px; background: #f9f9f9; color: #666; }

/* 右侧控制区 */
.control-panel { flex: 1; display: flex; flex-direction: column; gap: 20px; }
.panel-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.panel-card h3 { margin: 0 0 5px 0; color: #333; font-size: 1.1rem; }
.desc { color: #888; font-size: 0.85rem; margin-bottom: 15px; }

.action-row { display: flex; align-items: center; justify-content: space-between; gap: 15px; margin-bottom: 15px; }
.toggle-group { display: flex; align-items: center; gap: 10px; font-size: 0.9rem; color: #555; }

/* 开关样式 */
.switch { position: relative; display: inline-block; width: 40px; height: 20px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 34px; }
.slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 2px; bottom: 2px; background-color: white; transition: .4s; border-radius: 50%; }
input:checked + .slider { background-color: #2196F3; }
input:checked + .slider:before { transform: translateX(20px); }

.log-box { background: #f8f9fa; padding: 10px; border-radius: 6px; height: 120px; overflow-y: auto; font-size: 0.85rem; border: 1px solid #eee; }
.log-item { margin-bottom: 4px; color: #444; border-bottom: 1px solid #eee; padding-bottom: 2px; }
.log-placeholder { text-align: center; color: #ccc; margin-top: 40px; }

.btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; transition: all 0.2s; white-space: nowrap; }
.btn-start { background: #10b981; color: white; }
.btn-stop { background: #ef4444; color: white; }
.btn-blue { background: #3b82f6; color: white; }
.btn-red { background: #ef4444; color: white; }
.btn-red-outline { background: transparent; border: 1px solid #ef4444; color: #ef4444; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.upload-status { font-size: 0.85rem; color: #666; margin-top: 10px; text-align: center; }
.upload-status.error { color: #ef4444; }

@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
</style>