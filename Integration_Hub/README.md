# Integration Hub

Integration Hub 是总系统唯一的业务集成入口（内部版本 v1.001.260524 ）。子系统后端只通过 HTTP 与 Hub 通信，不直接访问 Redis / MQTT / Kafka。

团队协作和联调规范见：[TEAM_INTEGRATION_GUIDE.md](./TEAM_INTEGRATION_GUIDE.md)。
事件 / 命令契约见：[INTEGRATION_CONTRACT.md](./INTEGRATION_CONTRACT.md)。

## 当前能力

- 事件通道：`POST /api/events` -> `lkyw.events` -> SSE -> 首页
- 命令通道：`POST /api/commands` -> `lkyw.commands` -> 子系统轮询 -> `command.*` 回执事件
- 可视化观察页：`http://127.0.0.1:18701/dashboard`
- 健康检查：`http://127.0.0.1:18701/api/health`

## 谁需要安装什么

如果某个同学只改自己的子系统代码，并连接别人已经启动好的 Hub，不需要本机安装 Redis，也不需要安装 `Integration_Hub/requirements.txt`。

如果某个同学要在自己的电脑上运行完整系统，或者要自己启动 `start_integration_hub.bat`，就必须准备：

- Python 环境
- `Integration_Hub/requirements.txt` 中的 Python 包
- Redis Server，默认监听 `127.0.0.1:6379`
- 总系统前端的 Node/npm 环境

当前 `event_client.py` 本身只使用 Python 标准库。`redis` Python 包只在运行 Hub 服务时需要。

## 首次安装 Hub 依赖

推荐使用项目统一 Python 环境：

```powershell
$env:LKYW_PYTHON_EXE="D:\CondaEnvs\yolov11_traffic_dev\python.exe"
& $env:LKYW_PYTHON_EXE -m pip install -r .\Integration_Hub\requirements.txt
```

如果没有这个 Conda 环境，可以用自己的 Python：

```powershell
python -m pip install -r .\Integration_Hub\requirements.txt
```

依赖清单：

```text
fastapi
uvicorn
redis>=5.0.0
```

## 启动 Redis

方式一：Docker

```powershell
docker run --name lkyw-redis -p 6379:6379 -d redis:7
```

方式二：WSL Ubuntu

```powershell
wsl -d Ubuntu-22.04
sudo apt update
sudo apt install -y redis-server
redis-server --bind 0.0.0.0 --port 6379
```

另开一个 PowerShell 检查：

```powershell
wsl -d Ubuntu-22.04 -- redis-cli ping
```

返回 `PONG` 表示 Redis 正常。Hub 的健康检查里 `redis.ok` 也应为 `true`。

## 启动 Hub

```powershell
.\start_integration_hub.bat
```

或者手动启动：

```powershell
cd .\Integration_Hub
python server.py
```

默认配置：

```text
Hub: http://127.0.0.1:18701
Redis: redis://127.0.0.1:6379/0
Event Stream: lkyw.events
Command Stream: lkyw.commands
Command Status Hash: lkyw.command.status
```

可通过环境变量覆盖：

```powershell
$env:REDIS_URL="redis://127.0.0.1:6379/0"
$env:INTEGRATION_HUB_PORT="18701"
```

## 联调启动顺序

```powershell
.\start_integration_hub.bat
.\start_sensor_gateway.bat
.\start_detection_backend.bat
cd .\vue-project_all
npm run dev
```

如果协同响应也要联调，再启动：

```powershell
.\start_Collaborative_Response.bat
```

## 常用接口

```text
GET  http://127.0.0.1:18701/
GET  http://127.0.0.1:18701/dashboard
GET  http://127.0.0.1:18701/api/health
GET  http://127.0.0.1:18701/api/events/recent
GET  http://127.0.0.1:18701/api/events/stream
GET  http://127.0.0.1:18701/api/commands/recent
GET  http://127.0.0.1:18701/api/commands/status
POST http://127.0.0.1:18701/api/events
POST http://127.0.0.1:18701/api/commands
```

## 命令示例

```json
{
  "type": "sensor.sampling.start",
  "target": "sensor-management-edge",
  "source": "home-dashboard",
  "subject": "sensor-gateway",
  "payload": {
    "active": true
  }
}
```

Hub 写入 `lkyw.commands` 后会同步发布 `command.submitted`。目标子系统轮询 Hub 的 `/api/commands/poll`，执行后再通过 `/api/events` 发布 `command.accepted`、`command.completed` 或 `command.failed`。

## 常见问题

- `api/health` 里 `redis.ok=false`：Redis 没启动，或者不是默认 `6379` 端口。
- 命令一直停在 `submitted`：目标子系统没启动、没重启到新代码，或者 `target` 不匹配。
- 首页没有事件：先看 `/dashboard`，再看 `/api/events/recent`，确认 Hub 是否已经收到事件。
- 子系统能不能直接连 Redis：不能。子系统只调用 Hub。
- 首页能不能直接控制子系统：跨系统控制统一走 `POST /api/commands`，执行结果从 `command.*` 事件回来。
- 多人开发能不能共用一个 Hub：可以，把子系统环境变量 `INTEGRATION_HUB_URL` 指向同一个 Hub 地址即可。

## v1.001.260524版本说明

v1.001.260524版本适合本机联调和轻量实时通知。生产级可靠事件平台还需要增强，包括 consumer group、命令幂等、超时扫描、dead letter、权限认证、schema 校验和 Kafka adapter。
