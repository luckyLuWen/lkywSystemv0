from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import redis
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field


REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
STREAM_NAME = os.getenv("INTEGRATION_STREAM_NAME", "lkyw.events")
COMMAND_STREAM_NAME = os.getenv("INTEGRATION_COMMAND_STREAM_NAME", "lkyw.commands")
COMMAND_STATUS_KEY = os.getenv("INTEGRATION_COMMAND_STATUS_KEY", "lkyw.command.status")
MAX_STREAM_LENGTH = int(os.getenv("INTEGRATION_STREAM_MAXLEN", "10000"))
MAX_COMMAND_STREAM_LENGTH = int(os.getenv("INTEGRATION_COMMAND_STREAM_MAXLEN", "10000"))
SSE_BLOCK_MS = int(os.getenv("INTEGRATION_SSE_BLOCK_MS", "5000"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redis_client() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


redis_conn = redis_client()
app = FastAPI(title="LKYW Integration Hub", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


DASHBOARD_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LKYW Integration Hub</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f6f7f9; color: #17202a; }
    header { padding: 18px 24px; background: #17202a; color: #fff; }
    main { display: grid; grid-template-columns: 320px 1fr; gap: 16px; padding: 16px; }
    section { background: #fff; border: 1px solid #d8dde3; border-radius: 8px; padding: 16px; }
    h1 { margin: 0; font-size: 20px; }
    h2 { margin: 0 0 12px; font-size: 16px; }
    .kv { display: grid; grid-template-columns: 88px 1fr; gap: 8px; font-size: 13px; }
    .ok { color: #0f766e; font-weight: 700; }
    .bad { color: #b42318; font-weight: 700; }
    .event { border-top: 1px solid #edf0f3; padding: 12px 0; }
    .type { font-weight: 700; }
    .meta { color: #667085; font-size: 12px; margin-top: 4px; }
    pre { background: #f2f4f7; padding: 10px; overflow: auto; border-radius: 6px; font-size: 12px; }
    code { background: #edf0f3; padding: 2px 5px; border-radius: 4px; }
  </style>
</head>
<body>
  <header>
    <h1>LKYW Integration Hub</h1>
  </header>
  <main>
    <section>
      <h2>Hub Status</h2>
      <div class="kv">
        <div>Connection</div><div id="conn">connecting...</div>
        <div>Redis</div><div id="redis">checking...</div>
        <div>Stream</div><div id="stream">-</div>
      </div>
      <h2 style="margin-top:20px">Endpoints</h2>
      <p><code>GET /api/health</code></p>
      <p><code>POST /api/commands</code></p>
      <p><code>GET /api/commands/recent</code></p>
      <p><code>GET /api/commands/status</code></p>
      <p><code>GET /api/events/recent</code></p>
      <p><code>GET /api/events/stream</code></p>
      <p><code>POST /api/events</code></p>
      <h2 style="margin-top:20px">Command Demo</h2>
      <p>
        <button onclick="sendCommand('sensor.sampling.start','sensor-management-edge',{})">Start Sensor</button>
        <button onclick="sendCommand('sensor.sampling.stop','sensor-management-edge',{})">Stop Sensor</button>
      </p>
      <p>
        <button onclick="sendCommand('detection.rtsp.start','real-time-detection',{streamId:'rtsp_cam_01',rtspUrl:'rtsp://localhost:8554/live',cameraName:'RTSP Camera'})">Start RTSP</button>
        <button onclick="sendCommand('detection.rtsp.stop','real-time-detection',{streamId:'rtsp_cam_01'})">Stop RTSP</button>
      </p>
    </section>
    <section>
      <h2>Recent Integration Events</h2>
      <div id="events">waiting for events...</div>
    </section>
  </main>
  <script>
    const eventsEl = document.getElementById('events');
    const connEl = document.getElementById('conn');
    const redisEl = document.getElementById('redis');
    const streamEl = document.getElementById('stream');
    const events = [];

    function render() {
      eventsEl.innerHTML = events.length ? '' : 'waiting for events...';
      events.slice(0, 80).forEach((evt) => {
        const item = document.createElement('div');
        item.className = 'event';
        item.innerHTML = `
          <div class="type">${evt.type || 'unknown'}</div>
          <div class="meta">${evt.timestamp || ''} | ${evt.source || ''} | ${evt.severity || 'info'} | ${evt.streamId || ''}</div>
          <pre>${JSON.stringify(evt.payload || {}, null, 2)}</pre>
        `;
        eventsEl.appendChild(item);
      });
    }

    function addEvent(evt) {
      events.unshift(evt);
      if (events.length > 100) events.pop();
      render();
    }

    async function refreshHealth() {
      try {
        const res = await fetch('/api/health');
        const data = await res.json();
        redisEl.textContent = data.redis && data.redis.ok ? 'ok' : 'unavailable';
        redisEl.className = data.redis && data.redis.ok ? 'ok' : 'bad';
        const eventText = data.stream ? `${data.stream.name} (${data.stream.length ?? '-'})` : '-';
        const commandText = data.commandStream ? `${data.commandStream.name} (${data.commandStream.length ?? '-'})` : '-';
        streamEl.textContent = `${eventText} / ${commandText}`;
      } catch (err) {
        redisEl.textContent = 'health check failed';
        redisEl.className = 'bad';
      }
    }

    async function loadRecent() {
      try {
        const res = await fetch('/api/events/recent?count=30');
        if (!res.ok) return;
        const data = await res.json();
        (data.events || []).reverse().forEach(addEvent);
      } catch (err) {}
    }

    async function sendCommand(type, target, payload) {
      await fetch('/api/commands', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          type,
          target,
          source: 'hub-dashboard',
          payload: payload || {}
        })
      });
      refreshHealth();
    }

    refreshHealth();
    loadRecent();
    setInterval(refreshHealth, 5000);

    const source = new EventSource('/api/events/stream');
    source.addEventListener('integration-ready', () => {
      connEl.textContent = 'connected';
      connEl.className = 'ok';
    });
    source.addEventListener('integration-event', (message) => {
      addEvent(JSON.parse(message.data));
      refreshHealth();
    });
    source.addEventListener('integration-error', (message) => {
      connEl.textContent = 'stream error';
      connEl.className = 'bad';
      try { addEvent(JSON.parse(message.data)); } catch (err) {}
    });
    source.onerror = () => {
      connEl.textContent = 'reconnecting';
      connEl.className = 'bad';
    };
  </script>
</body>
</html>
"""


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "integration-hub",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "health": "/api/health",
        "commandPublish": "POST /api/commands",
        "commandPoll": "GET /api/commands/poll",
        "commandRecent": "GET /api/commands/recent",
        "commandStatus": "GET /api/commands/status",
        "publish": "POST /api/events",
        "recent": "GET /api/events/recent",
        "stream": "GET /api/events/stream",
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


class IntegrationEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="eventId")
    type: str
    source: str
    subject: str = ""
    severity: str = "info"
    timestamp: str = Field(default_factory=utc_now_iso)
    version: int = 1
    correlation_id: str = Field(default="", alias="correlationId")
    trace_id: str = Field(default="", alias="traceId")
    host: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class IntegrationCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="commandId")
    type: str
    target: str
    source: str = "home-dashboard"
    subject: str = ""
    timestamp: str = Field(default_factory=utc_now_iso)
    version: int = 1
    timeout_ms: int = Field(default=30000, alias="timeoutMs")
    correlation_id: str = Field(default="", alias="correlationId")
    trace_id: str = Field(default="", alias="traceId")
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


def event_to_stream_fields(event: IntegrationEvent) -> Dict[str, str]:
    data = event.dict(by_alias=True)
    payload = data.pop("payload", {})
    return {
        "event": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    }


def command_to_stream_fields(command: IntegrationCommand) -> Dict[str, str]:
    data = command.dict(by_alias=True)
    payload = data.pop("payload", {})
    return {
        "command": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    }


def stream_fields_to_event(stream_id: str, fields: Dict[str, str]) -> Dict[str, Any]:
    try:
        event_meta = json.loads(fields.get("event", "{}"))
    except json.JSONDecodeError:
        event_meta = {}
    try:
        payload = json.loads(fields.get("payload", "{}"))
    except json.JSONDecodeError:
        payload = {}
    event_meta["streamId"] = stream_id
    event_meta["payload"] = payload
    return event_meta


def stream_fields_to_command(stream_id: str, fields: Dict[str, str]) -> Dict[str, Any]:
    try:
        command_meta = json.loads(fields.get("command", "{}"))
    except json.JSONDecodeError:
        command_meta = {}
    try:
        payload = json.loads(fields.get("payload", "{}"))
    except json.JSONDecodeError:
        payload = {}
    command_meta["streamId"] = stream_id
    command_meta["payload"] = payload
    return command_meta


def append_event_to_stream(event: IntegrationEvent) -> str:
    return redis_conn.xadd(
        STREAM_NAME,
        event_to_stream_fields(event),
        maxlen=MAX_STREAM_LENGTH,
        approximate=True,
    )


def read_recent_events(count: int) -> List[Dict[str, Any]]:
    items = redis_conn.xrevrange(STREAM_NAME, count=count)
    return [stream_fields_to_event(stream_id, fields) for stream_id, fields in reversed(items)]


def read_recent_commands(count: int) -> List[Dict[str, Any]]:
    items = redis_conn.xrevrange(COMMAND_STREAM_NAME, count=count)
    return [stream_fields_to_command(stream_id, fields) for stream_id, fields in reversed(items)]


def command_matches_target(command: Dict[str, Any], targets: List[str]) -> bool:
    command_target = str(command.get("target") or "").strip()
    normalized_targets = {str(item).strip() for item in targets if str(item).strip()}
    return command_target == "*" or command_target in normalized_targets


def update_command_status(command_id: str, partial: Dict[str, Any]) -> None:
    if not command_id:
        return

    record: Dict[str, Any] = {"commandId": command_id}
    raw = redis_conn.hget(COMMAND_STATUS_KEY, command_id)
    if raw:
        try:
            stored = json.loads(raw)
            if isinstance(stored, dict):
                record.update(stored)
        except json.JSONDecodeError:
            pass

    record.update(partial)
    record["commandId"] = command_id
    record["updatedAt"] = utc_now_iso()
    redis_conn.hset(
        COMMAND_STATUS_KEY,
        command_id,
        json.dumps(record, ensure_ascii=False, separators=(",", ":")),
    )


def read_command_statuses(count: int) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for raw in redis_conn.hvals(COMMAND_STATUS_KEY):
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)

    records.sort(key=lambda item: str(item.get("updatedAt") or item.get("timestamp") or ""), reverse=True)
    return records[:count]


def apply_command_event_to_status(event: IntegrationEvent, stream_id: str) -> None:
    if not event.type.startswith("command."):
        return

    command_id = (
        str(event.payload.get("commandId") or "").strip()
        or event.correlation_id
        or event.subject
    )
    if not command_id:
        return

    status = event.type.split(".", 1)[1]
    update_command_status(
        command_id,
        {
            "status": status,
            "eventStreamId": stream_id,
            "eventType": event.type,
            "source": event.source,
            "target": event.payload.get("target", ""),
            "commandType": event.payload.get("commandType", event.payload.get("type", "")),
            "subject": event.subject,
            "severity": event.severity,
            "message": event.payload.get("message", ""),
            "result": event.payload.get("result"),
            "error": event.payload.get("error", ""),
            "timestamp": event.timestamp,
        },
    )


@app.get("/api/health")
def health() -> Dict[str, Any]:
    try:
        pong = redis_conn.ping()
        length = redis_conn.xlen(STREAM_NAME)
        command_length = redis_conn.xlen(COMMAND_STREAM_NAME)
        command_status_count = redis_conn.hlen(COMMAND_STATUS_KEY)
    except redis.RedisError as exc:
        return {
            "ok": False,
            "service": "integration-hub",
            "redis": {"ok": False, "url": REDIS_URL, "error": str(exc)},
            "stream": {"name": STREAM_NAME, "length": None},
            "commandStream": {"name": COMMAND_STREAM_NAME, "length": None},
            "commandStatus": {"key": COMMAND_STATUS_KEY, "count": None},
            "checkedAt": utc_now_iso(),
        }

    return {
        "ok": True,
        "service": "integration-hub",
        "redis": {"ok": bool(pong), "url": REDIS_URL},
        "stream": {"name": STREAM_NAME, "length": length, "maxlen": MAX_STREAM_LENGTH},
        "commandStream": {
            "name": COMMAND_STREAM_NAME,
            "length": command_length,
            "maxlen": MAX_COMMAND_STREAM_LENGTH,
        },
        "commandStatus": {"key": COMMAND_STATUS_KEY, "count": command_status_count},
        "checkedAt": utc_now_iso(),
    }


@app.post("/api/events")
def publish_event(event: IntegrationEvent, request: Request) -> Dict[str, Any]:
    if not event.source or not event.type:
        raise HTTPException(status_code=400, detail="event source and type are required")

    try:
        stream_id = append_event_to_stream(event)
        apply_command_event_to_status(event, stream_id)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"redis_unavailable:{exc}") from exc

    return {
        "ok": True,
        "stream": STREAM_NAME,
        "streamId": stream_id,
        "eventId": event.event_id,
        "receivedFrom": request.client.host if request.client else "",
    }


@app.post("/api/commands")
def publish_command(command: IntegrationCommand, request: Request) -> Dict[str, Any]:
    if not command.source or not command.type or not command.target:
        raise HTTPException(status_code=400, detail="command source, type and target are required")

    try:
        command_stream_id = redis_conn.xadd(
            COMMAND_STREAM_NAME,
            command_to_stream_fields(command),
            maxlen=MAX_COMMAND_STREAM_LENGTH,
            approximate=True,
        )
        update_command_status(
            command.command_id,
            {
                "status": "submitted",
                "commandStreamId": command_stream_id,
                "commandType": command.type,
                "source": command.source,
                "target": command.target,
                "subject": command.subject,
                "timestamp": command.timestamp,
                "timeoutMs": command.timeout_ms,
                "payload": command.payload,
            },
        )
        submitted_event = IntegrationEvent(
            type="command.submitted",
            source="integration-hub",
            subject=command.command_id,
            severity="info",
            correlation_id=command.command_id,
            trace_id=command.trace_id,
            payload={
                "commandId": command.command_id,
                "commandType": command.type,
                "source": command.source,
                "target": command.target,
                "subject": command.subject,
                "status": "submitted",
                "commandStreamId": command_stream_id,
                "timeoutMs": command.timeout_ms,
                "payload": command.payload,
            },
        )
        event_stream_id = append_event_to_stream(submitted_event)
        update_command_status(command.command_id, {"eventStreamId": event_stream_id})
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"redis_unavailable:{exc}") from exc

    return {
        "ok": True,
        "stream": COMMAND_STREAM_NAME,
        "streamId": command_stream_id,
        "eventStream": STREAM_NAME,
        "eventStreamId": event_stream_id,
        "commandId": command.command_id,
        "receivedFrom": request.client.host if request.client else "",
    }


@app.get("/api/commands")
def commands_index(count: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    return recent_commands(count)


@app.get("/api/commands/recent")
def recent_commands(count: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    try:
        commands = read_recent_commands(count)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"redis_unavailable:{exc}") from exc
    return {"ok": True, "stream": COMMAND_STREAM_NAME, "commands": commands}


@app.get("/api/commands/status")
def command_status(count: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    try:
        commands = read_command_statuses(count)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"redis_unavailable:{exc}") from exc
    return {"ok": True, "statusKey": COMMAND_STATUS_KEY, "commands": commands}


@app.get("/api/commands/poll")
def poll_commands(
    target: List[str] = Query(default=[]),
    last_id: str = Query(default="$", alias="lastId"),
    block_ms: int = Query(default=10000, ge=0, le=60000, alias="blockMs"),
    count: int = Query(default=10, ge=1, le=100),
) -> Dict[str, Any]:
    targets = [item for item in target if item]
    if not targets:
        raise HTTPException(status_code=400, detail="at least one target is required")

    current_id = last_id or "$"
    matched_commands: List[Dict[str, Any]] = []

    try:
        response = redis_conn.xread({COMMAND_STREAM_NAME: current_id}, block=block_ms, count=count)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"redis_unavailable:{exc}") from exc

    for _, entries in response:
        for stream_id, fields in entries:
            current_id = stream_id
            command = stream_fields_to_command(stream_id, fields)
            if command_matches_target(command, targets):
                matched_commands.append(command)

    return {
        "ok": True,
        "stream": COMMAND_STREAM_NAME,
        "lastId": current_id,
        "targets": targets,
        "commands": matched_commands,
    }


@app.get("/api/events")
def events_index(count: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    return recent_events(count)


@app.get("/api/events/recent")
def recent_events(count: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    try:
        events = read_recent_events(count)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"redis_unavailable:{exc}") from exc
    return {"ok": True, "stream": STREAM_NAME, "events": events}


def sse_encode(event_name: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_name}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}")
    return "\n".join(lines) + "\n\n"


def event_stream(last_id: str) -> Iterable[str]:
    current_id = last_id or "$"
    yield sse_encode(
        "integration-ready",
        {"ok": True, "stream": STREAM_NAME, "startedAt": utc_now_iso()},
    )

    while True:
        try:
            response = redis_conn.xread({STREAM_NAME: current_id}, block=SSE_BLOCK_MS, count=50)
        except redis.RedisError as exc:
            yield sse_encode("integration-error", {"ok": False, "error": str(exc), "at": utc_now_iso()})
            time.sleep(1)
            continue

        if not response:
            yield ": heartbeat\n\n"
            continue

        for _, entries in response:
            for stream_id, fields in entries:
                current_id = stream_id
                yield sse_encode("integration-event", stream_fields_to_event(stream_id, fields), stream_id)


@app.get("/api/events/stream")
def stream_events(last_id: str = Query(default="", alias="lastId")) -> StreamingResponse:
    return StreamingResponse(
        event_stream(last_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("INTEGRATION_HUB_HOST", "0.0.0.0"),
        port=int(os.getenv("INTEGRATION_HUB_PORT", "18701")),
    )
