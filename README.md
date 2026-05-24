# lkywSystem

## 项目结构

- `vue-project_all`：总系统前端壳，负责首页、路由、状态卡和 iframe 集成。
- `Collaborative_Response`：协同响应子系统，负责人 `dh`。
- `Constructive simulation`：建构仿真子系统，负责人 `ysl`。
- `Real-time_Detection`：实时检测子系统，负责人 `zby`。
- `Sensor_Management`：真实边缘端传感器管理子系统，负责人 `lb`。
- `Sensor_Management_sim`：本机模拟边缘网关，用于办公室端联调。
- `Integration_Hub`：总系统业务事件入口，当前使用 Redis Streams 承载事件流。
- `scripts/sync-subsystems.ps1`：将子系统构建结果同步到 `vue-project_all/public`。

## 当前运行边界

- `vue-project_all` 不是四个子系统的统一后端启动器。
- 它负责接入各子系统前端，并通过状态卡和按钮调用对应后端接口。
- `lb` 的真实传感器管理后端应部署在边缘设备。
- 当前仓库内的 `Sensor_Management_sim` 用来在开发电脑上模拟边缘网关。

## 推荐本机联调端口

| 模块 | 地址 |
| --- | --- |
| 总系统前端 | `http://127.0.0.1:5173` 或 Vite 实际输出地址 |
| 模拟传感器网关 | `http://127.0.0.1:18080` |
| 实时检测后端 | `http://127.0.0.1:5000` |
| 协同响应控制层 | `http://127.0.0.1:18601` |
| 协同响应指挥后端 | `http://127.0.0.1:5001` |
| 协同调度平台 Streamlit | `http://127.0.0.1:8501` |
| Integration Hub | `http://127.0.0.1:18701` |

总系统首页默认已经按这套端口配置：

- 传感器网关默认地址：`http://127.0.0.1:18080`
- 实时检测默认地址：`http://127.0.0.1:5000`
- 协同响应控制层默认地址：`http://127.0.0.1:18601`
- 协同响应指挥后端默认地址：`http://127.0.0.1:5001`
- 协同调度平台默认地址：`http://127.0.0.1:8501/?embed=true`

## Python 环境

当前已验证 `D:\CondaEnvs\yolov11_traffic_dev\python.exe` 具备以下运行条件：

- `dh` 协同响应后端与 Streamlit 所需依赖
- `zby` 实时检测后端所需依赖
- `Sensor_Management_sim` 所需依赖

`zby` 的模型文件路径为：
```text
.\liangkeweb\lkywSystem\Real-time_Detection\runs\detect\lkyw_fire_detection\weights\best.pt
```

## 一键启动脚本
仓库根目录提供 3 个常用脚本 (如需在ubuntu开发，请自行改为相应功能的.sh)。

### 1. 启动模拟传感器网关
```powershell
.\start_sensor_gateway.bat
```
作用：
- 使用 `yolov11_traffic_dev` 环境启动 `Sensor_Management_sim`
- 默认监听 `18080`
- 默认开启模拟采样
- 默认关闭视频流

启动成功后可访问：
```text
http://127.0.0.1:18080/api/health
```

### 2. 启动实时检测后端
```powershell
.\start_detection_backend.bat
```
作用：
- 使用 `yolov11_traffic_dev` 环境启动 `Real-time_Detection\web_app\backend\app.py`
- 自动注入 `YOLO11N_MODEL_PATH`
- 默认监听 `5000`

启动成功后可访问：

```text
http://127.0.0.1:5000/api/health
```

### 3. 启动协同响应控制层
```powershell
.\start_Collaborative_Response.bat
```
作用：

- 使用 `yolov11_traffic_dev` 环境启动 `Collaborative_Response\service_manager\server.py`
- 默认监听 `18601`
- 由控制层再去拉起 `commandCenter` 和 `streamlit`

启动成功后可访问：

```text
http://127.0.0.1:18601/api/health
```

### 4. 启动总系统事件入口
先启动本机 Redis：
```powershell
docker run --name lkyw-redis -p 6379:6379 -d redis:7
```

再启动 Integration Hub：
```powershell
.\start_integration_hub.bat
```

启动成功后可访问：

```text
http://127.0.0.1:18701/api/health
```

说明：
- 这个脚本启动的是控制层，不是直接把协同响应所有页面都起完。
- 真正的二维推演和三维指挥后端，可以通过总系统首页状态卡或控制层接口继续启动。

## 完整联调步骤

### step 1. 启动事件入口和三个后端
```powershell
.\start_integration_hub.bat
.\start_sensor_gateway.bat
.\start_detection_backend.bat
.\start_Collaborative_Response.bat
```

### step 2. 启动总系统前端
```powershell
cd .\vue-project_all
npm install
npm run dev
```

### 3. 打开总系统首页
进入浏览器后重点检查：
- 首页传感器状态卡是否显示 `127.0.0.1:18080` 在线
- 首页实时检测状态卡是否显示 `127.0.0.1:5000` 在线且模型已就绪
- 首页协同响应状态卡是否显示控制层 `127.0.0.1:18601` 在线
然后可以继续：
- 在首页或传感器管理页点击“开始采集 / 停止采集”
- 在首页实时检测卡点击“开始检测 / 停止检测”
- 在首页协同响应卡点击启动 `commandCenter` 或 `streamlit`

## 子系统改动后同步到总系统
如果某个子系统前端页面改了，且希望 `vue-project_all/public` 中的集成副本同步更新，执行：
```powershell
.\scripts\sync-subsystems.ps1
```

该脚本会刷新：

- `vue-project_all/public/collaborative-response`
- `vue-project_all/public/constructive-simulation`
- `vue-project_all/public/realtime-detection`
- `vue-project_all/public/sensor-management`

## GitHub 协作方式
推荐分支模型：

- `main`：稳定发布
- `develop`：日常集成
- `feature/<module>-<topic>`：个人功能分支
- `hotfix/<topic>`：线上修复

### 负责人如何工作

1. 维护 `main` 和 `develop`
2. 审核 `lb / dh / ysl / zby` 提交到 `develop` 的 PR
3. 处理跨子系统集成
4. 最终把 `develop` 合并到 `main`

### 四位同事如何工作

- `lb` 主要改 `Sensor_Management/`，必要时也改 `Sensor_Management_sim/`
- `dh` 主要改 `Collaborative_Response/`
- `ysl` 主要改 `Constructive simulation/`
- `zby` 主要改 `Real-time_Detection/`

标准流程：

```powershell
git switch develop
git pull origin develop
git switch -c feature/<module>-<topic>
```

开发要求：

- 只改自己负责目录相关代码
- 在自己操作系统环境下完成运行验证
- 如果前端改动影响总系统静态集成页，额外执行 `.\scripts\sync-subsystems.ps1`

提交方式：

```powershell
git add .
git commit -m "feat: 说明本次改动"
git push origin feature/<module>-<topic>
```

然后发起到 `develop` 的 Pull Request。
