import asyncio
import base64
import concurrent.futures
import copy
import csv
import io
import json
import math
import os
import random
import shutil
import socket
import sqlite3
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import cv2
import serial
from fastapi import FastAPI, File, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;udp|fflags;nobuffer|flags;low_delay|strict;experimental|max_delay;0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOSTNAME = socket.gethostname()
REPO_ROOT = Path(__file__).resolve().parents[3]
INTEGRATION_CLIENT_DIR = REPO_ROOT / "Integration_Hub"
if str(INTEGRATION_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_CLIENT_DIR))

try:
    from event_client import (
        IntegrationCommandClient,
        IntegrationEventPublisher,
        build_command_status_payload,
    )
except Exception:
    class IntegrationEventPublisher:
        def __init__(self, *args, **kwargs):
            pass

        def publish(self, *args, **kwargs):
            return False

    class IntegrationCommandClient:
        def __init__(self, *args, **kwargs):
            pass

        def poll(self, *args, **kwargs):
            return []

    def build_command_status_payload(command, status, **kwargs):
        return {"commandId": command.get("commandId", ""), "status": status, **kwargs}

DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "sensor_data.db"))
IMG_DIR = os.getenv("IMG_DIR", r"D:\sat\image")
VIDEO_DIR = os.getenv("VIDEO_DIR", r"D:\sat\view")

GATEWAY_MODE = os.getenv("SENSOR_GATEWAY_MODE", "edge").strip().lower() or "edge"
SIMULATE_SENSOR_DATA = os.getenv("SIMULATE_SENSOR_DATA", "0").strip().lower() in {"1", "true", "yes", "on"}
ENABLE_VIDEO_STREAM = os.getenv("ENABLE_VIDEO_STREAM", "1").strip().lower() in {"1", "true", "yes", "on"}
SYSTEM_RUNNING = os.getenv("SYSTEM_RUNNING", "1").strip().lower() in {"1", "true", "yes", "on"}
SAMPLING_INTERVAL_SECONDS = float(os.getenv("SAMPLING_INTERVAL_SECONDS", "0.5"))
NODE_OFFLINE_AFTER_SECONDS = float(os.getenv("NODE_OFFLINE_AFTER_SECONDS", "5"))
VIDEO_OFFLINE_AFTER_SECONDS = float(os.getenv("VIDEO_OFFLINE_AFTER_SECONDS", "5"))
SENSOR_EVENT_STATUS_INTERVAL_SECONDS = float(os.getenv("SENSOR_EVENT_STATUS_INTERVAL_SECONDS", "5"))
SENSOR_EVENT_THRESHOLD_COOLDOWN_SECONDS = float(os.getenv("SENSOR_EVENT_THRESHOLD_COOLDOWN_SECONDS", "60"))
SENSOR_THRESHOLDS = {
    "smoke": float(os.getenv("SENSOR_THRESHOLD_SMOKE", "600000")),
    "tvoc": float(os.getenv("SENSOR_THRESHOLD_TVOC", "2.0")),
    "co": float(os.getenv("SENSOR_THRESHOLD_CO", "50")),
}
INTEGRATION_SOURCE_ID = os.getenv("INTEGRATION_SOURCE_ID", f"sensor-management-{GATEWAY_MODE}")
EVENT_PUBLISHER = IntegrationEventPublisher(source=INTEGRATION_SOURCE_ID)
COMMAND_CLIENT = IntegrationCommandClient(
    target=INTEGRATION_SOURCE_ID,
    targets=[
        INTEGRATION_SOURCE_ID,
        "sensor-management",
        f"sensor-management-{GATEWAY_MODE}",
        "sensor",
    ],
)

DRONE_RTMP_URL = os.getenv("DRONE_RTMP_URL", "rtmp://192.168.0.67:1935/live/abc")

NODES: Dict[str, Dict[str, object]] = {
    "node1": {
        "label": "A",
        "display_name": "无人车 A",
        "type": "5in1",
        "url": os.getenv("NODE1_URL", "socket://192.168.0.219:10123"),
        "ser": None,
        "error_count": 0,
        "last_success_at": None,
        "last_error": "",
    },
    "node2": {
        "label": "B",
        "display_name": "无人车 B",
        "type": "5in1",
        "url": os.getenv("NODE2_URL", "socket://192.168.0.241:10123"),
        "ser": None,
        "error_count": 0,
        "last_success_at": None,
        "last_error": "",
    },
    "node3": {
        "label": "杆",
        "display_name": "固定杆",
        "type": "wind",
        "url": os.getenv("NODE3_URL", "socket://192.168.0.71:10123"),
        "ser": None,
        "error_count": 0,
        "last_success_at": None,
        "last_error": "",
    },
}

CMD_SENSOR_5IN1 = bytes.fromhex("03 03 00 01 00 14 15 E7")
CMD_WIND = bytes.fromhex("01 03 00 04 00 02 85 CA")

latest_data = {
    "node1": {"temp": 0.0, "hum": 0.0, "smoke": 0, "tvoc": 0.0, "co": 0.0},
    "node2": {"temp": 0.0, "hum": 0.0, "smoke": 0, "tvoc": 0.0, "co": 0.0},
    "node3": {"wind": 0.0, "wind_dir": "--"},
}

data_lock = threading.Lock()
state_lock = threading.Lock()
LAST_SAMPLE_AT: Optional[datetime] = None
LAST_SAMPLE_DURATION_MS: Optional[float] = None
LAST_STATUS_EVENT_AT = 0.0
LAST_THRESHOLD_EVENT_AT: Dict[str, float] = {}


def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def isoformat_or_none(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat(timespec="seconds") if value else None


def init_db() -> None:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        ensure_directory(db_dir)
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                n1_temp REAL,
                n1_hum REAL,
                n1_smoke REAL,
                n1_tvoc REAL,
                n1_co REAL,
                n2_temp REAL,
                n2_hum REAL,
                n2_smoke REAL,
                n2_tvoc REAL,
                n2_co REAL,
                wind_speed REAL,
                wind_dir TEXT,
                image_path TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_to_db(data: dict, img_path: Optional[str] = None) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO records (
                timestamp,
                n1_temp,
                n1_hum,
                n1_smoke,
                n1_tvoc,
                n1_co,
                n2_temp,
                n2_hum,
                n2_smoke,
                n2_tvoc,
                n2_co,
                wind_speed,
                wind_dir,
                image_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(),
                data["node1"].get("temp", 0),
                data["node1"].get("hum", 0),
                data["node1"].get("smoke", 0),
                data["node1"].get("tvoc", 0),
                data["node1"].get("co", 0),
                data["node2"].get("temp", 0),
                data["node2"].get("hum", 0),
                data["node2"].get("smoke", 0),
                data["node2"].get("tvoc", 0),
                data["node2"].get("co", 0),
                data["node3"].get("wind", 0),
                data["node3"].get("wind_dir", "--"),
                img_path,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def clear_buffer(ser) -> None:
    try:
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)
    except Exception:
        pass


def smart_read_modbus(ser, expected_addr: int, expected_func: int, expected_len: int):
    try:
        raw = ser.read(expected_len + 5)
        if not raw:
            return None
        for index in range(len(raw) - 1):
            if raw[index] == expected_addr and raw[index + 1] == expected_func:
                if len(raw) - index >= expected_len:
                    return raw[index : index + expected_len]
        return None
    except Exception:
        return None


def ensure_conn(node_key: str):
    node = NODES[node_key]
    if node["error_count"] > 5:
        if node["ser"] is not None:
            try:
                node["ser"].close()
            except Exception:
                pass
        node["ser"] = None
        node["error_count"] = 0
    if node["ser"] is None:
        try:
            node["ser"] = serial.serial_for_url(node["url"], baudrate=9600, timeout=0.4)
        except Exception as error:
            node["ser"] = None
            node["last_error"] = str(error)
    return node["ser"]


def get_wind_dir_str(value: int) -> str:
    directions = [
        "北",
        "北偏东",
        "东北",
        "东偏北",
        "东",
        "东偏南",
        "东南",
        "南偏东",
        "南",
        "南偏西",
        "西南",
        "西偏南",
        "西",
        "西偏北",
        "西北",
        "北偏西",
    ]
    return directions[value] if 0 <= value < len(directions) else "未知"


def parse_5in1_data(raw: bytes):
    if len(raw) < 45:
        return None

    def get_reg(register_no: int) -> int:
        index = 3 + (register_no - 1) * 2
        return (raw[index] << 8) | raw[index + 1]

    raw_smoke_ppm = get_reg(11)
    smoke_ug = int(raw_smoke_ppm * 1227)
    return {
        "temp": round((get_reg(1) - 2000) / 100.0, 2),
        "hum": round(get_reg(2) / 100.0, 2),
        "smoke": smoke_ug,
        "tvoc": round(get_reg(14) / 100.0, 3),
        "co": round(get_reg(18) / 10.0, 1),
    }


def parse_wind_data(raw: bytes):
    if len(raw) < 9:
        return None
    wind_val = ((raw[3] << 8) | raw[4]) / 100.0
    dir_val = (raw[5] << 8) | raw[6]
    return {"wind": wind_val, "wind_dir": get_wind_dir_str(dir_val)}


def mark_node_success(node_key: str) -> None:
    with state_lock:
        NODES[node_key]["last_success_at"] = datetime.now()
        NODES[node_key]["last_error"] = ""
        NODES[node_key]["error_count"] = 0


def mark_node_failure(node_key: str, error: Optional[Exception] = None) -> None:
    with state_lock:
        NODES[node_key]["error_count"] += 1
        if error is not None:
            NODES[node_key]["last_error"] = str(error)


def read_single_node_task(node_key: str):
    node_cfg = NODES[node_key]
    ser = ensure_conn(node_key)
    if ser is None:
        mark_node_failure(node_key)
        return node_key, None

    try:
        clear_buffer(ser)
        if node_cfg["type"] == "wind":
            ser.write(CMD_WIND)
            payload = smart_read_modbus(ser, 0x01, 0x03, 9)
            parsed = parse_wind_data(payload) if payload else None
        else:
            ser.write(CMD_SENSOR_5IN1)
            payload = smart_read_modbus(ser, 0x03, 0x03, 45)
            parsed = parse_5in1_data(payload) if payload else None

        if parsed:
            mark_node_success(node_key)
            return node_key, parsed

        mark_node_failure(node_key)
        return node_key, None
    except Exception as error:
        mark_node_failure(node_key, error)
        return node_key, None


def build_simulated_payload() -> dict:
    now = time.time()
    cycle = now / 8.0

    data = {
        "node1": {
            "temp": round(27 + math.sin(cycle) * 3 + random.uniform(-0.3, 0.3), 2),
            "hum": round(55 + math.cos(cycle / 1.5) * 10 + random.uniform(-0.6, 0.6), 2),
            "smoke": int(18000 + abs(math.sin(cycle / 2)) * 12000 + random.uniform(0, 800)),
            "tvoc": round(0.35 + abs(math.sin(cycle / 1.8)) * 0.3, 3),
            "co": round(2.2 + abs(math.cos(cycle / 1.3)) * 1.5, 1),
        },
        "node2": {
            "temp": round(28 + math.cos(cycle * 0.9) * 2.5 + random.uniform(-0.3, 0.3), 2),
            "hum": round(52 + math.sin(cycle / 1.7) * 8 + random.uniform(-0.6, 0.6), 2),
            "smoke": int(22000 + abs(math.cos(cycle / 2.2)) * 15000 + random.uniform(0, 900)),
            "tvoc": round(0.42 + abs(math.cos(cycle / 1.4)) * 0.28, 3),
            "co": round(2.8 + abs(math.sin(cycle / 1.1)) * 1.6, 1),
        },
        "node3": {
            "wind": round(2.2 + abs(math.sin(cycle / 2.5)) * 1.8, 2),
            "wind_dir": random.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"]),
        },
    }

    with state_lock:
        timestamp = datetime.now()
        for node in NODES.values():
            node["last_success_at"] = timestamp
            node["last_error"] = ""
            node["error_count"] = 0

    return data


def publish_sensor_observation_event(sampled: dict, duration_ms: float) -> None:
    global LAST_STATUS_EVENT_AT

    now = time.time()
    if now - LAST_STATUS_EVENT_AT < SENSOR_EVENT_STATUS_INTERVAL_SECONDS:
        return

    LAST_STATUS_EVENT_AT = now
    EVENT_PUBLISHER.publish(
        "sensor.observation.updated",
        subject="sensor-gateway",
        payload={
            "mode": GATEWAY_MODE,
            "running": SYSTEM_RUNNING,
            "samplingIntervalSeconds": SAMPLING_INTERVAL_SECONDS,
            "sampleDurationMs": duration_ms,
            "sampledAt": datetime.now().isoformat(timespec="seconds"),
            "nodes": get_node_snapshot(),
            "latestData": sampled,
        },
    )


def publish_sensor_threshold_events(sampled: dict) -> None:
    now = time.time()
    for node_key in ("node1", "node2"):
        node_data = sampled.get(node_key) or {}
        node_cfg = NODES.get(node_key, {})
        for metric, threshold in SENSOR_THRESHOLDS.items():
            value = node_data.get(metric)
            if value is None or float(value) < threshold:
                continue

            event_key = f"{node_key}:{metric}"
            if now - LAST_THRESHOLD_EVENT_AT.get(event_key, 0.0) < SENSOR_EVENT_THRESHOLD_COOLDOWN_SECONDS:
                continue

            LAST_THRESHOLD_EVENT_AT[event_key] = now
            EVENT_PUBLISHER.publish(
                "sensor.threshold.exceeded",
                subject=event_key,
                severity="warn",
                payload={
                    "nodeId": node_key,
                    "nodeLabel": node_cfg.get("label", node_key),
                    "nodeName": node_cfg.get("display_name", node_key),
                    "metric": metric,
                    "value": value,
                    "threshold": threshold,
                    "mode": GATEWAY_MODE,
                    "sampledAt": datetime.now().isoformat(timespec="seconds"),
                },
            )


def publish_command_status(command: dict, status: str, message: str = "", result: Optional[dict] = None, error_message: str = "") -> None:
    command_id = command.get("commandId", "")
    severity = "error" if status == "failed" else "info"
    EVENT_PUBLISHER.publish(
        f"command.{status}",
        subject=command_id,
        severity=severity,
        correlation_id=command_id,
        payload=build_command_status_payload(
            command,
            status,
            message=message,
            result=result or {},
            error_message=error_message,
        ),
    )


def set_sampling_running(active: bool, origin: str = "api", command: Optional[dict] = None) -> dict:
    global SYSTEM_RUNNING

    with state_lock:
        previous_running = SYSTEM_RUNNING
        SYSTEM_RUNNING = bool(active)
        running = SYSTEM_RUNNING

    event_payload = {
        "previousRunning": previous_running,
        "running": running,
        "mode": GATEWAY_MODE,
        "origin": origin,
        "changedAt": datetime.now().isoformat(timespec="seconds"),
    }
    if command:
        event_payload["commandId"] = command.get("commandId", "")
        event_payload["commandType"] = command.get("type", "")

    EVENT_PUBLISHER.publish(
        "sensor.sampling.started" if running else "sensor.sampling.stopped",
        subject="sensor-gateway",
        correlation_id=command.get("commandId", "") if command else "",
        payload=event_payload,
    )
    return event_payload


def execute_sensor_command(command: dict) -> None:
    command_type = command.get("type", "")
    try:
        publish_command_status(command, "accepted", message="sensor command accepted")

        if command_type == "sensor.sampling.start":
            event_payload = set_sampling_running(True, origin="command", command=command)
        elif command_type == "sensor.sampling.stop":
            event_payload = set_sampling_running(False, origin="command", command=command)
        elif command_type == "sensor.sampling.set":
            active = bool((command.get("payload") or {}).get("active"))
            event_payload = set_sampling_running(active, origin="command", command=command)
        else:
            publish_command_status(
                command,
                "failed",
                message="unsupported sensor command",
                error_message=f"unsupported_command:{command_type}",
            )
            return

        publish_command_status(
            command,
            "completed",
            message="sensor command completed",
            result={"sampling": event_payload, "status": build_status_payload()},
        )
    except Exception as exc:
        publish_command_status(
            command,
            "failed",
            message="sensor command failed",
            error_message=str(exc),
        )


def command_task() -> None:
    while True:
        commands = COMMAND_CLIENT.poll(count=10)
        for command in commands:
            execute_sensor_command(command)
        if not commands:
            time.sleep(0.2)


def background_task() -> None:
    global LAST_SAMPLE_AT, LAST_SAMPLE_DURATION_MS, latest_data

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
    while True:
        loop_start = time.time()

        if not SYSTEM_RUNNING:
            time.sleep(1)
            continue

        if SIMULATE_SENSOR_DATA:
            sampled = build_simulated_payload()
        else:
            sampled = {"node1": {}, "node2": {}, "node3": {}}
            future_to_node = {
                executor.submit(read_single_node_task, key): key for key in ["node1", "node2", "node3"]
            }
            for future in concurrent.futures.as_completed(future_to_node):
                node_key, result = future.result()
                if result:
                    sampled[node_key] = result

            fallback_5in1 = {"temp": 0.0, "hum": 0.0, "smoke": 0, "tvoc": 0.0, "co": 0.0}
            fallback_wind = {"wind": 0.0, "wind_dir": "--"}
            for key in ["node1", "node2", "node3"]:
                if not sampled[key]:
                    sampled[key] = fallback_wind if NODES[key]["type"] == "wind" else fallback_5in1

        with data_lock:
            latest_data = sampled

        save_to_db(sampled)

        duration_ms = round((time.time() - loop_start) * 1000, 2)
        with state_lock:
            LAST_SAMPLE_AT = datetime.now()
            LAST_SAMPLE_DURATION_MS = duration_ms

        publish_sensor_observation_event(sampled, duration_ms)
        publish_sensor_threshold_events(sampled)

        sleep_time = max(0, SAMPLING_INTERVAL_SECONDS - (time.time() - loop_start))
        time.sleep(sleep_time)


class VideoStream:
    def __init__(self, url: str):
        self.url = url
        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        self.last_frame_at: Optional[datetime] = None
        self.last_error = ""
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self) -> None:
        count = 0
        while self.running:
            if self.cap.isOpened():
                self.cap.grab()
                count += 1
                if count % 3 == 0:
                    success, frame = self.cap.retrieve()
                    if success:
                        with self.lock:
                            self.frame = frame
                            self.last_frame_at = datetime.now()
                            self.last_error = ""
                    else:
                        self.last_error = "frame_retrieve_failed"
                        time.sleep(0.05)
                if count > 1000:
                    count = 0
            else:
                self.last_error = "stream_disconnected"
                time.sleep(0.5)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def is_online(self) -> bool:
        return bool(self.last_frame_at and (datetime.now() - self.last_frame_at).total_seconds() <= VIDEO_OFFLINE_AFTER_SECONDS)

    def status_snapshot(self) -> dict:
        return {
            "enabled": ENABLE_VIDEO_STREAM,
            "online": self.is_online(),
            "source": self.url,
            "last_frame_at": isoformat_or_none(self.last_frame_at),
            "last_error": self.last_error,
        }

    def stop(self) -> None:
        self.running = False
        try:
            self.thread.join(timeout=2)
        finally:
            self.cap.release()


drone_stream: Optional[VideoStream] = VideoStream(DRONE_RTMP_URL) if ENABLE_VIDEO_STREAM else None


def generate_frames():
    if drone_stream is None:
        return
    while True:
        frame = drone_stream.read()
        if frame is None:
            time.sleep(0.1)
            continue
        try:
            frame = cv2.resize(frame, (640, 360))
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
            time.sleep(0.033)
        except Exception:
            time.sleep(0.05)


def get_node_snapshot() -> dict:
    now = datetime.now()
    snapshot = {}
    with state_lock:
        for key, node in NODES.items():
            last_success_at = node.get("last_success_at")
            online = bool(
                last_success_at
                and (now - last_success_at).total_seconds() <= NODE_OFFLINE_AFTER_SECONDS
            )
            snapshot[key] = {
                "label": node["label"],
                "display_name": node["display_name"],
                "type": node["type"],
                "address": node["url"],
                "online": online,
                "last_success_at": isoformat_or_none(last_success_at),
                "last_error": node.get("last_error", ""),
            }
    return snapshot


def get_database_status() -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        return {"ok": True, "path": DB_PATH}
    except Exception as error:
        return {"ok": False, "path": DB_PATH, "error": str(error)}


def get_video_status() -> dict:
    if drone_stream is None:
        return {
            "enabled": ENABLE_VIDEO_STREAM,
            "online": False,
            "source": DRONE_RTMP_URL,
            "last_frame_at": None,
            "last_error": "video_disabled",
        }
    return drone_stream.status_snapshot()


def build_status_payload() -> dict:
    with state_lock:
        last_sample_at = LAST_SAMPLE_AT
        last_sample_duration_ms = LAST_SAMPLE_DURATION_MS

    return {
        "gateway_online": True,
        "mode": GATEWAY_MODE,
        "running": SYSTEM_RUNNING,
        "sampling_interval_seconds": SAMPLING_INTERVAL_SECONDS,
        "last_sample_at": isoformat_or_none(last_sample_at),
        "last_sample_duration_ms": last_sample_duration_ms,
        "database": get_database_status(),
        "video": get_video_status(),
        "nodes": get_node_snapshot(),
    }


def build_health_payload() -> dict:
    status = build_status_payload()
    status.update(
        {
            "ok": True,
            "service": "sensor-management-edge",
            "hostname": HOSTNAME,
            "db_path": DB_PATH,
        }
    )
    return status


class ImageModel(BaseModel):
    image: str


class ControlModel(BaseModel):
    active: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directory(IMG_DIR)
    ensure_directory(VIDEO_DIR)
    init_db()
    worker = threading.Thread(target=background_task, daemon=True)
    worker.start()
    command_worker = threading.Thread(target=command_task, daemon=True)
    command_worker.start()
    EVENT_PUBLISHER.publish("sensor.gateway.started", subject="sensor-gateway", payload=build_health_payload())
    yield
    EVENT_PUBLISHER.publish("sensor.gateway.stopped", subject="sensor-gateway", payload={"mode": GATEWAY_MODE})
    if drone_stream is not None:
        drone_stream.stop()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return build_health_payload()


@app.get("/api/status")
def status():
    return build_status_payload()


@app.post("/api/control")
def control(payload: ControlModel):
    set_sampling_running(payload.active, origin="api")
    return build_status_payload()


@app.get("/api/video_feed")
def video_feed():
    if drone_stream is None:
        return Response(status_code=503, content="video_disabled", media_type="text/plain")
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/save_drone_image")
def save_drone_image(data: ImageModel):
    snapshot = copy.deepcopy(latest_data)
    try:
        encoded = data.image.split(",", 1)[1] if "base64," in data.image else data.image
        image_data = base64.b64decode(encoded)
        filename = datetime.now().strftime("%m%d_%H%M%S_%f")[:-3] + ".jpg"
        filepath = os.path.join(IMG_DIR, filename)
        with open(filepath, "wb") as file_obj:
            file_obj.write(image_data)
        save_to_db(snapshot, img_path=filepath)
        return {"status": "success", "path": filepath}
    except Exception as error:
        return {"status": "error", "msg": str(error)}


@app.post("/api/save_drone_video")
async def save_drone_video(file: UploadFile = File(...)):
    snapshot = copy.deepcopy(latest_data)
    try:
        filename = f"Drone_Record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
        filepath = os.path.join(VIDEO_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        save_to_db(snapshot, img_path=filepath)
        return {"status": "success", "path": filepath}
    except Exception as error:
        return {"status": "error", "msg": str(error)}


@app.get("/api/history")
def get_history_api(limit: int = 100, start: Optional[str] = None, end: Optional[str] = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if start and end:
            cursor.execute(
                "SELECT * FROM records WHERE timestamp BETWEEN ? AND ? ORDER BY id ASC",
                (start, end),
            )
        else:
            cursor.execute("SELECT * FROM records ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        if not (start and end):
            rows = list(reversed(rows))
        return [dict(row) for row in rows]
    except Exception:
        return []


@app.get("/api/export")
def export_csv(start: Optional[str] = None, end: Optional[str] = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if start and end:
            cursor.execute(
                "SELECT * FROM records WHERE timestamp BETWEEN ? AND ? ORDER BY id DESC",
                (start, end),
            )
        else:
            cursor.execute("SELECT * FROM records ORDER BY id DESC LIMIT 50000")
        rows = cursor.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "ID",
                "Timestamp",
                "N1 Temp",
                "N1 Hum",
                "N1 Smoke(ug/m3)",
                "N1 TVOC",
                "N1 CO",
                "N2 Temp",
                "N2 Hum",
                "N2 Smoke(ug/m3)",
                "N2 TVOC",
                "N2 CO",
                "N3 Wind Speed",
                "N3 Wind Direction",
                "Image Path",
            ]
        )
        for row in rows:
            writer.writerow(row)

        return Response(
            content="\ufeff" + output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=data.csv"},
        )
    except Exception as error:
        return {"error": str(error)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(json.dumps(latest_data, ensure_ascii=False))
            await asyncio.sleep(SAMPLING_INTERVAL_SECONDS)
    except Exception:
        return


DIST_DIR = os.path.join(BASE_DIR, "dist")
if os.path.exists(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_vue(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws"):
            return Response(status_code=404)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
