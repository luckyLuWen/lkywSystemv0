from __future__ import annotations

import json
import os
import platform
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

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
STREAMLIT_HEALTH_URL = f"http://127.0.0.1:{STREAMLIT_PORT}/_stcore/health"
PYTHON_BIN = os.environ.get("COMMAND_CENTER_PYTHON", sys.executable)
IS_WINDOWS = platform.system().lower().startswith("win")

DIRECT_OPENER = request.build_opener(request.ProxyHandler({}))

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


def probe_url(url: str) -> tuple[bool, str]:
    headers = {"User-Agent": "lkyw-collaborative-command-center/1.0"}
    for method in ("HEAD", "GET"):
        req = request.Request(url, headers=headers, method=method)
        try:
            with DIRECT_OPENER.open(req, timeout=4) as response:
                status_code = getattr(response, "status", 200)
                if 200 <= status_code < 400:
                    return True, f"HTTP {status_code}"
                return False, f"HTTP {status_code}"
        except error.HTTPError as exc:
            if 200 <= exc.code < 400:
                return True, f"HTTP {exc.code}"
            if method == "GET":
                return False, f"HTTP {exc.code}"
        except Exception as exc:
            if method == "GET":
                return False, str(exc)
    return False, "未知错误"


def stop_streamlit_process() -> None:
    global streamlit_process
    if streamlit_process is None:
        return
    pid = streamlit_process.pid
    if IS_WINDOWS and pid:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        try:
            streamlit_process.terminate()
            streamlit_process.wait(timeout=5)
        except Exception:
            try:
                streamlit_process.kill()
                streamlit_process.wait(timeout=5)
            except Exception:
                pass
    streamlit_process = None


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


def build_streamlit_service_status() -> dict[str, Any]:
    managed = streamlit_running()
    reachable, health_detail = probe_url(STREAMLIT_HEALTH_URL)

    return {
        "id": "streamlit",
        "label": "协同调度平台",
        "reachable": reachable,
        "running": managed or reachable,
        "managed": managed,
        "public_url": STREAMLIT_PUBLIC_URL,
        "health_url": STREAMLIT_HEALTH_URL,
        "health_detail": health_detail,
        "start_configured": True,
        "stop_configured": True,
    }


def build_command_center_service_status() -> dict[str, Any]:
    return {
        "id": "commandCenter",
        "label": "协同响应指挥后端",
        "reachable": True,
        "running": True,
        "managed": True,
        "public_url": f"http://127.0.0.1:{COMMAND_CENTER_PORT}",
        "health_url": f"http://127.0.0.1:{COMMAND_CENTER_PORT}/api/health",
        "health_detail": "HTTP 200",
        "start_configured": False,
        "stop_configured": False,
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
        "services": {
            "commandCenter": build_command_center_service_status(),
            "streamlit": build_streamlit_service_status(),
        },
        "artifacts": {
            "strategy_html": file_info(FOLIUM_PATH),
            "mission_czml": file_info(MISSION_PATH),
            "strategy_json": file_info(PATH_RESULT_PATH),
            "cesium_assets": {"exists": CESIUM_DIR.exists()},
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


# ── static file routes ──────────────────────────────────────────────

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


# ── health & status ─────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify(build_health_payload())


@app.route("/api/status")
def status():
    return jsonify(build_health_payload())


@app.route("/api/strategy_metrics")
def strategy_metrics():
    return jsonify(load_strategy_metrics())


# ── service management ──────────────────────────────────────────────

@app.route("/api/services")
def list_services():
    return jsonify({
        "ok": True,
        "services": {
            "commandCenter": build_command_center_service_status(),
            "streamlit": build_streamlit_service_status(),
        },
    })


@app.route("/api/services/<service_id>")
def get_service(service_id: str):
    if service_id == "commandCenter":
        return jsonify({"ok": True, "service": build_command_center_service_status()})
    if service_id == "streamlit":
        return jsonify({"ok": True, "service": build_streamlit_service_status()})
    return error_response(f"未知服务: {service_id}", 404)


@app.route("/api/services/<service_id>/start", methods=["POST"])
def start_service(service_id: str):
    if service_id == "commandCenter":
        return success_response("协同响应指挥后端已在运行")

    if service_id == "streamlit":
        global streamlit_process
        if streamlit_running():
            streamlit_reachable, _ = probe_url(STREAMLIT_HEALTH_URL)
            if streamlit_reachable:
                return success_response("协同调度平台已在运行", url=STREAMLIT_PUBLIC_URL)

        streamlit_process = subprocess.Popen(
            [
                PYTHON_BIN, "-m", "streamlit", "run", "app_2d.py",
                "--server.port", str(STREAMLIT_PORT),
                "--server.address", "0.0.0.0",
                "--server.headless", "true",
                "--server.enableCORS", "false",
                "--server.enableXsrfProtection", "false",
            ],
            cwd=BASE_DIR,
            text=True,
        )
        return success_response("协同调度平台已启动", url=STREAMLIT_PUBLIC_URL)

    return error_response(f"未知服务: {service_id}", 404)


@app.route("/api/services/<service_id>/stop", methods=["POST"])
def stop_service(service_id: str):
    if service_id == "commandCenter":
        return error_response(
            "协同响应指挥后端是主进程，无法通过 API 自行停止。请关闭终端窗口或按 Ctrl+C。",
            400,
        )

    if service_id == "streamlit":
        if not streamlit_running():
            return success_response("协同调度平台未在运行")

        stop_streamlit_process()
        return success_response("协同调度平台已停止")

    return error_response(f"未知服务: {service_id}", 404)


@app.route("/api/services/<service_id>/restart", methods=["POST"])
def restart_service(service_id: str):
    if service_id == "streamlit":
        stop_streamlit_process()
        return start_service(service_id)

    if service_id == "commandCenter":
        return error_response(
            "协同响应指挥后端是主进程，无法通过 API 自行重启。请手动重启。",
            400,
        )

    return error_response(f"未知服务: {service_id}", 404)


# ── business operations (backward-compatible) ────────────────────────

@app.route("/api/run_2d")
def run_2d():
    return start_service("streamlit")


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


# ── entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"协同响应指挥后端已启动: http://127.0.0.1:{COMMAND_CENTER_PORT}")
    print(f"  健康检查: http://127.0.0.1:{COMMAND_CENTER_PORT}/api/health")
    print(f"  服务管理: http://127.0.0.1:{COMMAND_CENTER_PORT}/api/services")
    app.run(host=COMMAND_CENTER_HOST, port=COMMAND_CENTER_PORT)
