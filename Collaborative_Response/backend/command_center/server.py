from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
CESIUM_DIR = BASE_DIR / "Cesium"
PATH_RESULT_PATH = BASE_DIR / "path_result.json"
MISSION_PATH = BASE_DIR / "mission.czml"
FOLIUM_PATH = BASE_DIR / "wuhan_rescue_optimized.html"

COMMAND_CENTER_HOST = os.environ.get("COMMAND_CENTER_HOST", "0.0.0.0")
COMMAND_CENTER_PORT = int(os.environ.get("COMMAND_CENTER_PORT", "5001"))
STREAMLIT_PORT = int(os.environ.get("COMMAND_CENTER_STREAMLIT_PORT", "8501"))
STREAMLIT_PUBLIC_URL = os.environ.get(
    "COMMAND_CENTER_STREAMLIT_PUBLIC_URL",
    f"http://127.0.0.1:{STREAMLIT_PORT}/?embed=true",
)
PYTHON_BIN = os.environ.get("COMMAND_CENTER_PYTHON", sys.executable)

app = Flask(__name__)
CORS(app)

streamlit_process: subprocess.Popen[Any] | None = None
service_started_at = datetime.now(timezone.utc).isoformat()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "updated_at": None}

    return {
        "exists": True,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
    }


def streamlit_running() -> bool:
    global streamlit_process
    if streamlit_process is None:
        return False
    if streamlit_process.poll() is not None:
        streamlit_process = None
        return False
    return True


def run_script(script_name: str, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON_BIN, script_name, *extra_args],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )


def load_strategy_metrics() -> dict[str, Any]:
    if not PATH_RESULT_PATH.exists():
        return {
            "available": False,
            "message": "尚未生成策略评估结果",
            "metrics": {},
            "updated_at": None,
        }

    with PATH_RESULT_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return {
        "available": True,
        "message": "已读取当前策略评估结果",
        "metrics": payload.get("metrics", {}),
        "obstacles": payload.get("obstacles", []),
        "updated_at": file_info(PATH_RESULT_PATH)["updated_at"],
    }


def build_health_payload() -> dict[str, Any]:
    metrics = load_strategy_metrics()
    return {
        "ok": True,
        "service": {
            "name": "协同响应指挥后端",
            "started_at": service_started_at,
            "base_dir": str(BASE_DIR),
            "host": COMMAND_CENTER_HOST,
            "port": COMMAND_CENTER_PORT,
        },
        "artifacts": {
            "strategy_html": file_info(FOLIUM_PATH),
            "mission_czml": file_info(MISSION_PATH),
            "strategy_json": file_info(PATH_RESULT_PATH),
            "cesium_assets": {"exists": CESIUM_DIR.exists()},
        },
        "streamlit": {
            "running": streamlit_running(),
            "public_url": STREAMLIT_PUBLIC_URL,
        },
        "strategy_metrics": metrics,
        "checked_at": utc_now_iso(),
    }


def success_response(message: str, **extra: Any):
    payload = {"ok": True, "message": message}
    payload.update(extra)
    return jsonify(payload)


def error_response(message: str, status_code: int = 500, **extra: Any):
    payload = {"ok": False, "message": message}
    payload.update(extra)
    return jsonify(payload), status_code


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/cesium_viewer")
def cesium_viewer():
    return send_from_directory(BASE_DIR, "cesium_viewer.html")


@app.route("/wuhan_rescue_optimized.html")
def serve_folium_map():
    return send_from_directory(BASE_DIR, "wuhan_rescue_optimized.html")


@app.route("/mission.czml")
def serve_czml():
    return send_from_directory(BASE_DIR, "mission.czml")


@app.route("/path_result.json")
def serve_strategy_json():
    return send_from_directory(BASE_DIR, "path_result.json")


@app.route("/Cesium/<path:filename>")
def serve_cesium_assets(filename: str):
    return send_from_directory(CESIUM_DIR, filename)


@app.route("/api/health")
def health():
    return jsonify(build_health_payload())


@app.route("/api/status")
def status():
    return jsonify(build_health_payload())


@app.route("/api/strategy_metrics")
def strategy_metrics():
    return jsonify(load_strategy_metrics())


@app.route("/api/run_2d")
def run_2d():
    global streamlit_process
    if streamlit_running():
        return success_response("协同调度平台已在运行", url=STREAMLIT_PUBLIC_URL)

    streamlit_process = subprocess.Popen(
        [
            PYTHON_BIN,
            "-m",
            "streamlit",
            "run",
            "app_2d.py",
            "--server.port",
            str(STREAMLIT_PORT),
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
            "--server.enableCORS",
            "false",
            "--server.enableXsrfProtection",
            "false",
        ],
        cwd=BASE_DIR,
        text=True,
    )
    return success_response("协同调度平台已启动", url=STREAMLIT_PUBLIC_URL)


@app.route("/api/run_3d_strategy")
def run_3d_strategy():
    result = run_script("app_3d_strategy.py")
    if result.returncode != 0:
        return error_response(
            "二维动态推演生成失败",
            stderr=result.stderr.strip(),
            stdout=result.stdout.strip(),
        )

    return success_response(
        "二维动态推演与策略评估已刷新",
        url="/wuhan_rescue_optimized.html",
        metrics=load_strategy_metrics(),
    )


@app.route("/api/run_3d_cesium")
def run_3d_cesium():
    result = run_script("app_3d_cesium.py")
    if result.returncode != 0:
        return error_response(
            "三维态势地图生成失败",
            stderr=result.stderr.strip(),
            stdout=result.stdout.strip(),
        )

    return success_response(
        "三维态势地图已刷新",
        url="/cesium_viewer",
        mission=file_info(MISSION_PATH),
    )


if __name__ == "__main__":
    print(f"协同响应指挥后端已启动: http://127.0.0.1:{COMMAND_CENTER_PORT}")
    app.run(host=COMMAND_CENTER_HOST, port=COMMAND_CENTER_PORT)
