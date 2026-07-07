# 两客一危交通事故火灾检测系统

基于 YOLOv11 的实时交通事故火灾检测模块，用于识别两客一危车辆和普通车辆的火灾/正常状态，并提供 Flask 后端与 Vue 前端界面。

## 项目上下文

本目录是 `lkywSystemv0` 单体仓库中的实时检测子模块。

- 仓库地址：https://github.com/luckyLuWen/lkywSystemv0
- 模块目录：`Real-time_Detection/`
- 模块负责人：`zby`
- 当前开发分支：`feature/realtime-detection`
- PR 目标分支：`develop`
- GitHub 用户：`yingrushi0801`
- 总系统前端：`vue-project_all/`
- 总系统事件入口：`Integration_Hub/`

## 协作边界

1. 只修改 `Real-time_Detection/` 内的文件。
2. 如果需要修改仓库级全局配置或其他子模块，先明确提出，不直接修改。
3. `web_app/frontend/old_version/` 是未跟踪的旧版代码，不要修改。
4. 不主动执行 `git push --force`、重置、清理等破坏性 Git 命令。
5. 不主动提交 commit，除非明确要求。
6. Git 提交时，只允许将 `Real-time_Detection/` 目录下的改动纳入提交；任何其他子系统或仓库级文件都不得进入本模块的 commit。

## 环境配置

推荐使用仓库约定的 conda 环境：

```bash
conda activate lkywSystem
```

该环境位于：

```text
/home/zhangboyu/anaconda3/envs/lkywSystem
```

基础要求：

- Python 3.8+
- Node.js / npm，用于运行 Vue 前端
- CUDA 11.0+，可选，用于 GPU 加速
- 8GB+ RAM

安装后端依赖：

```bash
pip install -r requirements.txt
```

前端依赖由启动脚本自动检查并安装；也可以手动安装：

```bash
cd web_app/frontend/vue-frontend
npm install
```

## 快速启动

在模块根目录执行：

```bash
conda activate lkywSystem
cd Real-time_Detection

# 启动检测后端，API 默认端口 5000
bash start_backend.sh

# 新开一个终端启动 Vue 前端，默认端口 3000
bash start_vue.sh
```

默认服务地址：

- 后端 API：`http://127.0.0.1:5000`
- 后端健康检查：`http://127.0.0.1:5000/api/health`
- 前端开发服务器：`http://127.0.0.1:3000`

也可以手动启动：

```bash
# 后端
cd web_app/backend
python app.py

# 前端
cd web_app/frontend/vue-frontend
npm run dev
```


## 总系统集成

根据仓库根目录 README，`Real-time_Detection` 是 lkywSystem 总系统中的实时检测子系统，负责人为 `zby`。总系统前端 `vue-project_all` 负责首页、路由、状态卡和 iframe 集成，不作为四个子系统的统一后端启动器。

推荐本机联调端口：

| 模块 | 地址 |
| --- | --- |
| 总系统前端 | `http://127.0.0.1:5173` 或 Vite 实际输出地址 |
| 实时检测后端 | `http://127.0.0.1:5000` |
| Integration Hub | `http://127.0.0.1:18701` |
| 模拟传感器网关 | `http://127.0.0.1:18080` |
| 协同响应控制层 | `http://127.0.0.1:18601` |
| 协同响应指挥后端 | `http://127.0.0.1:5001` |
| 协同调度平台 Streamlit | `http://127.0.0.1:8501` |

总系统首页默认按 `http://127.0.0.1:5000` 检查实时检测后端。启动成功后应能访问：

```text
http://127.0.0.1:5000/api/health
```

该接口会返回服务状态、模型路径存在性、`model_ready` 和当前 RTSP 活跃流数量。总系统首页实时检测状态卡依赖这些信息判断后端在线和模型是否就绪。

### 从仓库根目录启动

除本模块内的 `start_backend.sh` 外，仓库根目录还提供了总系统联调用启动脚本：

```bash
cd ..
bash start_detection_backend.sh
```

Windows 环境可在仓库根目录运行：

```powershell
.\start_detection_backend.bat
```

根目录启动脚本会进入 `Real-time_Detection/web_app/backend` 并启动 `app.py`，默认监听 `5000`。脚本会检查默认模型路径：

```text
Real-time_Detection/runs/detect/lkyw_fire_detection/weights/best.pt
```

### 完整联调顺序

在仓库根目录按总系统 README 的约定启动事件入口和各后端：

```powershell
.\start_integration_hub.bat
.\start_sensor_gateway.bat
.\start_detection_backend.bat
.\start_Collaborative_Response.bat
```

然后启动总系统前端：

```bash
cd vue-project_all
npm install
npm run dev
```

打开总系统首页后，重点确认实时检测状态卡显示 `127.0.0.1:5000` 在线且模型已就绪。

### 同步到总系统静态集成页

如果本模块前端页面发生改动，并且需要刷新 `vue-project_all/public/realtime-detection` 中的集成副本，在仓库根目录执行：

```powershell
.\scripts\sync-subsystems.ps1
```

## 运行配置

### 后端

后端入口为 `web_app/backend/app.py`，默认配置如下：

- Host：`0.0.0.0`
- Port：`5000`
- Debug：由环境变量 `FLASK_DEBUG` 控制，默认开启
- 上传目录：`web_app/backend/uploads`
- 检测结果目录：`web_app/backend/results`
- 最大上传文件：`100MB`
- 允许文件类型：`png`、`jpg`、`jpeg`、`bmp`、`webp`、`mp4`、`avi`、`mov`

常用环境变量：

```bash
export FLASK_DEBUG=1
export INTEGRATION_SOURCE_ID=real-time-detection
export DETECTION_EVENT_COOLDOWN_SECONDS=10
export INTEGRATION_COMMANDS_START_ON_REQUEST=1
```

### 前端

前端入口位于 `web_app/frontend/vue-frontend/`，使用 Vue 3 + Vite。

- 开发命令：`npm run dev`
- 构建命令：`npm run build`
- 预览命令：`npm run preview`
- Vite 开发端口：`3000`
- 默认后端地址：`http://127.0.0.1:5000`

## 模型配置

后端会优先扫描以下目录中的模型权重：

```text
LKYWDataset_weights/*/best.pt
```

如果该目录没有可用权重，会回退到：

```text
runs/detect/lkyw_fire_detection/weights/best.pt
```

由于模型文件较大，通常不随仓库提交。请将训练好的 `best.pt` 放到上述路径之一。

## 检测类别

- `lkyw_fire`：两客一危车辆火灾
- `lkyw_normal`：两客一危车辆正常
- `car_fire`：普通车辆火灾
- `car_normal`：普通车辆正常

## 主要功能

- 图片检测
- 视频抽帧检测
- 本地摄像头实时检测
- RTSP 流检测，支持 OBS 推流
- 检测历史与统计接口
- 与上层 `Integration_Hub` 的事件/命令集成

## RTSP 实时检测

默认 RTSP 地址：

```text
rtsp://localhost:8554/live
```

使用 OBS Studio 推流：

1. 安装 OBS Studio。
2. 安装 `obs-rtspserver` 插件。
3. 配置 RTSP 服务端口 `8554`。
4. 在前端选择 RTSP 流模式。
5. 启动实时检测。

RTSP 配置文件：

```text
web_app/backend/rtsp_config.json
```

## 模块结构

```text
Real-time_Detection/
├── web_app/
│   ├── backend/                    # Flask 检测后端
│   │   ├── app.py                  # 后端入口
│   │   ├── config.py               # 后端配置
│   │   ├── rtsp_detector.py        # RTSP 检测
│   │   ├── rtsp_config.json        # RTSP 配置
│   │   ├── database.py             # 检测记录数据库
│   │   ├── history_routes.py       # 历史记录接口
│   │   └── stats_routes.py         # 统计接口
│   └── frontend/
│       └── vue-frontend/           # Vue 3 + Vite 前端
├── train_yolov11.py                # YOLOv11 训练脚本
├── augment_train_dataset.py        # 数据增强
├── generate_training_plots.py      # 训练图表生成
├── dataset_split.py                # 数据集划分
├── start_backend.sh                # 后端启动脚本
├── start_vue.sh                    # 前端启动脚本
├── requirements.txt                # 后端 Python 依赖
└── LKYWDataset_weights/            # 训练权重目录
```

## 训练模型

```python
from ultralytics import YOLO

model = YOLO("yolo11n.pt")

model.train(
    data="dataset_split/dataset.yaml",
    epochs=100,
    imgsz=640,
    batch=16,
)
```

## 模型性能

| 模型 | mAP50 | mAP50-95 | 速度 | 参数量 |
| --- | --- | --- | --- | --- |
| YOLOv11n | 87.25% | 65.8% | ~10 ms | 2.6M |
| YOLOv11s | 89.5% | 68.2% | ~15 ms | 9.4M |

## 文档

- [远程服务器部署说明](远程服务器部署说明.md)
- [项目清理指南](项目清理指南.md)

## 注意事项

1. 实时检测推荐使用 GPU 加速。
2. 训练数据集和模型权重通常需要单独准备。
3. 后端依赖 `Integration_Hub` 时会自动尝试从仓库根目录加载集成客户端；如果该模块不可用，会使用降级实现，不影响基础检测功能。
