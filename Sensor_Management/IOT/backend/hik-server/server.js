// server.js
import express from 'express';
import expressWs from 'express-ws';
import { spawn } from 'child_process';
import cors from 'cors';
import net from 'net';

const app = express();
expressWs(app);
app.use(cors())

// ffmpeg 安装路径
const ffmpegPath = "F:\\lkyw\\lkywSystemv0\\Sensor_Management\\IOT\\ffmpeg-7.1.1-essentials_build\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe";

// 摄像机推流地址
const cameraStreams = 'rtsp://admin:hik123456@192.168.0.186:554/Streaming/Channels/101';

// 摄像头接入状态管理
let cameraConnectionStatus = {
  connected: false,
  physical_connected: false,
  data_collection: false,
  last_check: null
};

// 检测摄像头是否在线
function checkCameraOnline(rtspUrl) {
  return new Promise((resolve) => {
    const match = rtspUrl.match(/rtsp:\/\/.*@([\d.]+):(\d+)\//);
    if (!match) return resolve(false);

    const host = match[1];
    const port = parseInt(match[2]);

    const socket = new net.Socket();
    let isConnected = false;

    socket.setTimeout(2000);

    socket
      .connect(port, host, () => {
        isConnected = true;
        socket.destroy();
        resolve(true);
      })
      .on('error', () => {
        resolve(false);
      })
      .on('timeout', () => {
        socket.destroy();
        resolve(false);
      })
      .on('close', () => {
        if (!isConnected) resolve(false);
      });
  });
}

// 摄像头接入控制接口
app.post('/sensor/camera/connect', async (req, res) => {
  try {
    // 检查物理连接
    const physicalConnected = await checkCameraOnline(cameraStreams);
    cameraConnectionStatus.physical_connected = physicalConnected;
    
    if (!physicalConnected) {
      return res.json({
        code: -1, 
        message: "摄像头物理连接不可用，请检查设备连接和网络配置",
        connected: false
      });
    }
    
    // 启用数据采集
    cameraConnectionStatus.connected = true;
    cameraConnectionStatus.data_collection = true;
    cameraConnectionStatus.last_check = new Date();
    
    console.log("✅ 摄像头已接入");
    res.json({
      code: 0, 
      message: "摄像头接入成功",
      connected: true
    });
    
  } catch (error) {
    console.error("摄像头接入错误:", error);
    res.json({
      code: -1,
      message: "摄像头接入失败",
      connected: false
    });
  }
});

app.post('/sensor/camera/disconnect', (req, res) => {
  // 禁用数据采集
  cameraConnectionStatus.connected = false;
  cameraConnectionStatus.data_collection = false;
  cameraConnectionStatus.last_check = new Date();
  
  console.log("⏸️ 摄像头已断开");
  res.json({
    code: 0, 
    message: "摄像头断开成功",
    connected: false
  });
});

app.get('/sensor/camera/status', async (req, res) => {
  try {
    // 每次获取状态时检查物理连接
    const physicalConnected = await checkCameraOnline(cameraStreams);
    cameraConnectionStatus.physical_connected = physicalConnected;
    cameraConnectionStatus.last_check = new Date();
    
    res.json({
      code: 0,
      connected: cameraConnectionStatus.connected,
      physical_connected: physicalConnected,
      data_collection: cameraConnectionStatus.data_collection,
      last_check: cameraConnectionStatus.last_check
    });
  } catch (error) {
    console.error("获取摄像头状态错误:", error);
    res.json({
      code: -1,
      connected: false,
      physical_connected: false,
      data_collection: false,
      last_check: cameraConnectionStatus.last_check
    });
  }
});

// ✅ 提供 HTTP 接口供前端调用检测摄像头状态
app.get('/test/hikCamera', async (req, res) => {
  const online = await checkCameraOnline(cameraStreams);
  if (online) {
    res.json({ code: 0, message: '✅ 摄像头在线' });
  } else {
    res.json({ code: -1, message: '❌ 摄像头离线或无法连接' });
  }
});

// WebSocket 视频流接口 - 添加接入状态检查
app.ws('/stream/hik', async (ws, req) => {
  // 检查摄像头是否已接入
  if (!cameraConnectionStatus.connected || !cameraConnectionStatus.data_collection) {
    ws.close(1008, '摄像头未接入');
    return;
  }

  // 检查物理连接
  const physicalConnected = await checkCameraOnline(cameraStreams);
  if (!physicalConnected) {
    ws.close(1008, '摄像头物理连接断开');
    return;
  }

  console.log('🟢 开始摄像头视频流传输');

  // FFmpeg 拉取 RTSP 并转成 MPEG1（jsmpeg 可解码）
  const ffmpeg = spawn(ffmpegPath, [
    '-rtsp_transport', 'tcp',
    '-i', cameraStreams,
    '-f', 'mpegts',
    '-b:v', '4000k',
    '-codec:v', 'mpeg1video',
    '-r', '25',
    '-'
  ]);
  
  // 将 FFmpeg 输出的流数据推送到前端 WebSocket
  ffmpeg.stdout.on('data', (chunk) => {
    if (ws.readyState === 1) {
      ws.send(chunk)
    }
  })

  // FFmpeg 错误输出
  ffmpeg.stderr.on('data', (data) => {
    const msg = data.toString()
    if (msg.includes('error')) console.error('⚠️ FFmpeg 错误:', msg)
  })

  // FFmpeg 进程退出
  ffmpeg.on('close', (code) => {
    console.log(`💡 FFmpeg 退出 (code=${code})`)
    if (ws.readyState === 1) {
      ws.close(1000, 'FFmpeg 结束')
    }
  })

  // 客户端断开时，结束 FFmpeg
  ws.on('close', () => {
    console.log('❌ WebSocket 客户端断开连接')
    ffmpeg.kill('SIGINT')
  })

  ws.on('error', (err) => {
    console.error('❌ WebSocket 错误:', err)
    ffmpeg.kill('SIGINT')
  })
});

const PORT = 3000;
app.listen(PORT, () => console.log('🚀 摄像头服务器已启动：http://localhost:3000'));