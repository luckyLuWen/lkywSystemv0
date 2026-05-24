# Redis Streams 集成框架团队交接指南

本文面向首页维护者 ysl，以及感知传感器、实时检测、协同响应三个子系统负责人 lb / zby / dh。当前 v1.001.260524 已完成事件通道、命令通道、首页订阅和演示控制，可以进入本机联调阶段。

## 结论

现在统一边界是：

```text
子系统后端 / 总系统首页
  -> HTTP Integration Hub
  -> Redis Streams
  -> Integration Hub SSE
  -> 总系统首页态势池
```

不要让首页、iframe、子系统后端、Redis、设备消息互相直连。所有业务事实和控制意图都先进入 Integration Hub。

## 角色分工

| 角色 | 负责范围 | 主要文件 |
| --- | --- | --- |
| ysl | 首页态势池、SSE 订阅、命令按钮、事件展示、子系统摘要映射 | `vue-project_all/src/integration/*`、`vue-project_all/src/components/IntegrationEventMonitor.vue`、`vue-project_all/src/views/HomeDashboardView.vue` |
| lb | 感知 / 传感器事件发布、命令执行、状态回执 | `Sensor_Management/IOT/backend/main.py`、`Sensor_Management_sim/IOT/backend/main.py` |
| zby | 实时检测事件发布、RTSP 命令执行、状态回执 | `Real-time_Detection/web_app/backend/app.py`、`Real-time_Detection/web_app/backend/rtsp_detector.py` |
| dh | 协同响应后续接入事件 / 命令通道 | `Collaborative_Response/*`，接入前先对齐本文契约 |
| 集成维护者 | Hub API、Redis Streams、事件 / 命令契约 | `Integration_Hub/server.py`、`Integration_Hub/event_client.py`、`Integration_Hub/INTEGRATION_CONTRACT.md` |

## 每个人本机需要装什么

只改自己的子系统，并连接别人已经启动好的 Hub：

- 不需要本机 Redis
- 不需要安装 `Integration_Hub/requirements.txt`
- 只要保证子系统能访问 `INTEGRATION_HUB_URL`

要在自己电脑上跑完整系统：

- 需要 Redis Server
- 需要安装 `Integration_Hub/requirements.txt`
- 需要启动 Hub
- 需要启动自己相关的子系统后端
- ysl 还需要启动 `vue-project_all`

`event_client.py` 只用 Python 标准库；`redis` Python 包只在运行 Hub 时需要。

## 首次环境准备

安装 Hub Python 依赖：

```powershell
$env:LKYW_PYTHON_EXE="D:\CondaEnvs\yolov11_traffic_dev\python.exe"
& $env:LKYW_PYTHON_EXE -m pip install -r .\Integration_Hub\requirements.txt
```

如果没有统一 Conda 环境：

```powershell
python -m pip install -r .\Integration_Hub\requirements.txt
```

启动 Redis，二选一。

Docker：

```powershell
docker run --name lkyw-redis -p 6379:6379 -d redis:7
```

WSL Ubuntu：

```powershell
wsl -d Ubuntu-22.04
sudo apt update
sudo apt install -y redis-server
redis-server --bind 0.0.0.0 --port 6379
```

检查 Redis：

```powershell
wsl -d Ubuntu-22.04 -- redis-cli ping
```

预期返回：

```text
PONG
```

## 推荐启动顺序

```powershell
.\start_integration_hub.bat
.\start_sensor_gateway.bat
.\start_detection_backend.bat
cd .\vue-project_all
npm run dev
```

协同响应需要联调时再启动：

```powershell
.\start_Collaborative_Response.bat
```

启动后检查：

```text
http://127.0.0.1:18701/api/health
http://127.0.0.1:18701/dashboard
http://127.0.0.1:18701/api/events/recent?count=20
http://127.0.0.1:18701/api/commands/status?count=20
```

`api/health` 里应看到：

```json
{
  "ok": true,
  "redis": {
    "ok": true
  },
  "stream": {
    "name": "lkyw.events"
  },
  "commandStream": {
    "name": "lkyw.commands"
  }
}
```

## 事件通道

事件是已经发生的事实，例如：

```text
sensor.threshold.exceeded
detection.fire.detected
coordination.task.completed
command.completed
```

子系统发布事件时只调用：

```text
POST http://127.0.0.1:18701/api/events
```

Python 子系统优先使用：

```python
from event_client import IntegrationEventPublisher

publisher = IntegrationEventPublisher(source="sensor-management-edge")
publisher.publish(
    "sensor.observation.updated",
    subject="sensor-gateway",
    payload={"running": True},
)
```

事件信封：

```json
{
  "eventId": "uuid",
  "type": "sensor.observation.updated",
  "source": "sensor-management-edge",
  "subject": "sensor-gateway",
  "severity": "info",
  "timestamp": "2026-05-24T10:00:00+00:00",
  "version": 1,
  "correlationId": "",
  "traceId": "",
  "host": "host-name",
  "payload": {}
}
```

## 命令通道

命令是希望某个子系统执行的意图，例如：

```text
sensor.sampling.stop
detection.rtsp.start
coordination.resource.dispatch
```

首页或总系统发布命令时只调用：

```text
POST http://127.0.0.1:18701/api/commands
```

命令信封：

```json
{
  "commandId": "uuid",
  "type": "sensor.sampling.stop",
  "target": "sensor-management-edge",
  "source": "home-dashboard",
  "subject": "sensor-gateway",
  "timeoutMs": 30000,
  "payload": {
    "active": false
  }
}
```

Hub 会写入 `lkyw.commands`，并同步发布：

```text
command.submitted
```

子系统轮询命令时只调用 Hub：

```text
GET /api/commands/poll?target=sensor-management-edge&lastId=$&blockMs=10000&count=10
```

Python 子系统优先使用：

```python
from event_client import IntegrationCommandClient

client = IntegrationCommandClient(
    target="sensor-management-edge",
    targets=["sensor-management-edge", "sensor-management", "sensor"],
)

commands = client.poll(count=10)
```

子系统执行命令后必须回报：

```text
command.accepted
command.completed
command.failed
```

回报事件必须带同一个 `commandId`：

```python
publisher.publish(
    "command.completed",
    subject=command["commandId"],
    correlation_id=command["commandId"],
    payload={
        "commandId": command["commandId"],
        "commandType": command["type"],
        "target": command["target"],
        "status": "completed",
        "result": {},
    },
)
```

## ysl：首页维护要求

首页只订阅 Hub，不直接读 Redis。跨系统控制只发 Hub command，不直接调用子系统业务控制接口。

主要文件：

```text
vue-project_all/src/integration/integrationHubClient.js
vue-project_all/src/integration/situationStore.js
vue-project_all/src/components/IntegrationEventMonitor.vue
vue-project_all/src/views/HomeDashboardView.vue
vue-project_all/src/config/subsystems.js
```

新增首页态势字段时：

1. 先确认事件名已经登记到 `Integration_Hub/INTEGRATION_CONTRACT.md`。
2. 在 `situationStore.js` 的 `applyIntegrationEvent()` 中处理该事件。
3. 只把首页需要展示的摘要数据放入态势池。
4. 页面按钮发命令时调用 `publishIntegrationCommand()`。
5. 不要从首页直接调用 `Sensor_Management`、`Real-time_Detection` 或 `Collaborative_Response` 的跨系统控制接口。

首页命令示例：

```js
publishIntegrationCommand(hubBaseUrl, {
  type: 'sensor.sampling.stop',
  target: 'sensor-management-edge',
  source: 'home-dashboard',
  subject: 'sensor-gateway',
  payload: { active: false },
})
```

## lb：传感器子系统维护要求

当前已接入：

```text
Sensor_Management/IOT/backend/main.py
Sensor_Management_sim/IOT/backend/main.py
```

已支持命令：

```text
sensor.sampling.start
sensor.sampling.stop
sensor.sampling.set
```

已发布事件：

```text
sensor.gateway.started
sensor.gateway.stopped
sensor.observation.updated
sensor.threshold.exceeded
sensor.sampling.started
sensor.sampling.stopped
```

后续新增传感器告警时：

1. 事件名使用 `sensor.<resource>.<state>`。
2. 阈值、节点、采样时间必须放在 `payload`。
3. 不要在事件里放图片、视频帧或超大二进制数据。
4. 高频事件必须限频或聚合。
5. 命令执行必须幂等，重复收到 start/stop 不能导致异常。

## zby：实时检测子系统维护要求

当前已接入：

```text
Real-time_Detection/web_app/backend/app.py
Real-time_Detection/web_app/backend/rtsp_detector.py
```

已支持命令：

```text
detection.rtsp.start
detection.rtsp.stop
```

已发布事件：

```text
detection.stream.started
detection.stream.stopped
detection.fire.detected
detection.accident.confirmed
```

RTSP 启动命令示例：

```json
{
  "type": "detection.rtsp.start",
  "target": "real-time-detection",
  "subject": "rtsp_cam_01",
  "payload": {
    "streamId": "rtsp_cam_01",
    "rtspUrl": "rtsp://localhost:8554/live",
    "cameraName": "RTSP Camera"
  }
}
```

后续新增检测类型时：

1. 事件名使用 `detection.<object>.<state>`。
2. RTSP 流 ID 必须稳定，推荐默认 `rtsp_cam_01`。
3. 高频检测结果不全量推首页，只推关键态势事件。
4. 原始帧、截图、视频文件走子系统自己的文件服务，事件里只放 URL、ID、摘要。
5. start/stop 命令必须支持重复调用。

## dh：协同响应子系统接入要求

协同响应目前还没有接入命令消费者。接入时不要让首页直接控制协同响应内部服务，应复用 Hub 通道。

建议目标名：

```text
collaborative-response
collaborative-command-center
collaborative-simulation
```

建议事件：

```text
coordination.service.started
coordination.service.stopped
coordination.plan.created
coordination.plan.updated
coordination.task.assigned
coordination.task.completed
coordination.resource.dispatched
```

建议命令：

```text
coordination.service.start
coordination.service.stop
coordination.plan.create
coordination.task.assign
coordination.resource.dispatch
```

接入步骤：

1. 在协同响应后端引入 `Integration_Hub/event_client.py`。
2. 创建 `IntegrationEventPublisher(source="collaborative-response")`。
3. 创建 `IntegrationCommandClient(target="collaborative-response")`。
4. 后台线程轮询 `/api/commands/poll`。
5. 执行命令后发布 `command.accepted/completed/failed`。
6. 把协同业务状态变化发布为 `coordination.*` 事件。
7. 通知 ysl 在首页 `situationStore.js` 增加对应订阅映射。

## 命名规范

事件命名：

```text
<subsystem>.<resource>.<past-tense/state>
```

推荐：

```text
sensor.threshold.exceeded
detection.fire.detected
coordination.task.completed
```

命令命名：

```text
<subsystem>.<resource>.<verb>
```

推荐：

```text
sensor.sampling.start
detection.rtsp.stop
coordination.resource.dispatch
```

不要使用：

```text
start
stop
update
message
test
```

## 联调检查清单

每个负责人提交前至少检查：

```text
GET http://127.0.0.1:18701/api/health
GET http://127.0.0.1:18701/dashboard
GET http://127.0.0.1:18701/api/events/recent?count=20
GET http://127.0.0.1:18701/api/commands/status?count=20
```

命令联调顺序：

1. 首页点击命令按钮。
2. Hub `/api/commands/recent` 能看到命令。
3. Hub `/api/events/recent` 能看到 `command.submitted`。
4. 子系统日志能看到命令被轮询到。
5. Hub `/api/events/recent` 能看到 `command.accepted`。
6. 执行成功后能看到 `command.completed`。
7. 首页命令列表状态从 `submitted` 变成 `completed` 或 `failed`。

## 常见问题

- `api/health` 里 `redis.ok=false`：Redis 没启动，或端口不是 `6379`。
- 命令一直是 `submitted`：目标子系统没启动、没重启到新代码，或 `target` 写错。
- 子系统收不到命令：检查 `INTEGRATION_HUB_URL` 和 `IntegrationCommandClient(target=...)`。
- 首页没有事件：先看 Hub `/dashboard`，再看 `/api/events/recent`。
- 多人共用 Hub：可以，但要统一 `INTEGRATION_HUB_URL`，并避免命令 target 冲突。
- 子系统离线时发命令：第一版会停留在 `submitted`，第二阶段再做 timeout 扫描。

## 第二阶段方向

v1.001.260524 用于本机联调和轻量实时通知，还不是生产级可靠事件平台。后续增强项：

- Redis Streams consumer group 和确认机制
- 命令超时扫描与 `command.timeout`
- 幂等表，防止同一 `commandId` 重复执行
- Dead Letter Stream，例如 `lkyw.commands.deadletter`
- 事件 schema 校验和版本兼容策略
- 权限认证，限制谁能发命令
- OpenTelemetry `traceId` 串联
- Redis Streams 到 Kafka 的 adapter
- 首页按 subsystem 聚合健康状态

## 禁止事项

- 禁止子系统直接写 `lkyw.events` 或 `lkyw.commands`。
- 禁止首页直接访问 Redis。
- 禁止 iframe 用 `postMessage` 传核心业务命令。
- 禁止把高频视频帧、图片二进制、大数组塞进事件 `payload`。
- 禁止未登记事件名就直接接入首页展示。
- 禁止命令执行后没有 `command.completed` 或 `command.failed`。
