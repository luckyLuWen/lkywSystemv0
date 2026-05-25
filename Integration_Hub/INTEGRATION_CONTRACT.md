# Integration Contract

所有子系统业务消息都先进入 Integration Hub。Hub 当前使用 Redis Streams，后续可以在 Hub 内部替换为 Kafka。

## Event Envelope

事件表示已经发生的事实，统一写入 `lkyw.events`。

```json
{
  "eventId": "uuid",
  "type": "sensor.observation.updated",
  "source": "sensor-management-edge",
  "subject": "sensor-gateway",
  "severity": "info",
  "timestamp": "2026-05-23T10:00:00+00:00",
  "version": 1,
  "correlationId": "",
  "traceId": "",
  "host": "host-name",
  "payload": {}
}
```

## Command Envelope

命令表示总系统希望目标子系统执行的意图，统一写入 `lkyw.commands`。

```json
{
  "commandId": "uuid",
  "type": "sensor.sampling.start",
  "target": "sensor-management-edge",
  "source": "home-dashboard",
  "subject": "sensor-gateway",
  "timestamp": "2026-05-23T10:00:00+00:00",
  "version": 1,
  "timeoutMs": 30000,
  "correlationId": "",
  "traceId": "",
  "payload": {}
}
```

## Demo Events

Sensor Management:

- `sensor.gateway.started`
- `sensor.gateway.stopped`
- `sensor.observation.updated`
- `sensor.threshold.exceeded`
- `sensor.sampling.started`
- `sensor.sampling.stopped`

Real-time Detection:

- `detection.stream.started`
- `detection.stream.stopped`
- `detection.fire.detected`
- `detection.accident.confirmed`

Command Lifecycle:

- `command.submitted`
- `command.accepted`
- `command.completed`
- `command.failed`

## Demo Commands

Sensor Management:

- `sensor.sampling.start`
- `sensor.sampling.stop`
- `sensor.sampling.set`

Real-time Detection:

- `detection.rtsp.start`
- `detection.rtsp.stop`

## Direction

- 首页 / 总系统 -> Integration Hub: HTTP `POST /api/commands`
- Integration Hub -> Redis Streams: `XADD lkyw.commands`
- 子系统后端 -> Integration Hub: HTTP `GET /api/commands/poll`
- 子系统后端 -> Integration Hub: HTTP `POST /api/events`
- Integration Hub -> Redis Streams: `XADD lkyw.events`
- Integration Hub -> 总系统首页: SSE `GET /api/events/stream`
