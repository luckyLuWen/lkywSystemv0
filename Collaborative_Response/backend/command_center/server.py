from __future__ import annotations

import json
import os
import platform
import signal
import subprocess
import sys
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error, request as urllib_request

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
CESIUM_DIR = BASE_DIR / "Cesium"
PATH_RESULT_PATH = BASE_DIR / "path_result.json"
MISSION_PATH = BASE_DIR / "mission.czml"
FOLIUM_PATH = BASE_DIR / "wuhan_rescue_optimized.html"
RUNTIME_DIR = BASE_DIR / "runtime"
LOG_DIR = BASE_DIR / "logs"
SERVICES_CONFIG_PATH = BASE_DIR / "services.json"
SERVICES_LOCAL_CONFIG_PATH = BASE_DIR / "services.local.json"

IS_WINDOWS = platform.system().lower().startswith("win")
DIRECT_OPENER = urllib_request.build_opener(urllib_request.ProxyHandler({}))

RUNTIME_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

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

service_started_at = datetime.now(timezone.utc).isoformat()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def strip_prefix(value: str, prefix: str) -> str:
    if value.startswith(prefix):
        return value[len(prefix):]
    return value


def file_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "updated_at": None}
    return {
        "exists": True,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
    }


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


def success_response(message: str, **extra: Any):
    payload = {"ok": True, "message": message}
    payload.update(extra)
    return jsonify(payload)


def error_response(message: str, status_code: int = 500, **extra: Any):
    payload = {"ok": False, "message": message}
    payload.update(extra)
    return jsonify(payload), status_code


class ServiceManager:
    def __init__(self) -> None:
        self.started_at = utc_now_iso()
        self.lock = threading.Lock()
        self.processes: dict[str, subprocess.Popen[Any]] = {}
        self.config = self.load_config()

    def load_config(self) -> dict[str, Any]:
        if SERVICES_CONFIG_PATH.exists():
            with SERVICES_CONFIG_PATH.open("r", encoding="utf-8") as file:
                config = json.load(file)
        else:
            config = {"services": {}}

        if SERVICES_LOCAL_CONFIG_PATH.exists():
            with SERVICES_LOCAL_CONFIG_PATH.open("r", encoding="utf-8") as file:
                local_config = json.load(file)
            config = deep_merge(config, local_config)

        config.setdefault("services", {})
        return config

    def get_service(self, service_id: str) -> dict[str, Any]:
        service = self.config.get("services", {}).get(service_id)
        if not service:
            raise KeyError(f"未知服务: {service_id}")
        return service

    def pid_file_path(self, service_id: str) -> Path:
        return RUNTIME_DIR / f"{service_id}.pid"

    def log_file_paths(self, service_id: str) -> tuple[Path, Path]:
        return LOG_DIR / f"{service_id}.out.log", LOG_DIR / f"{service_id}.err.log"

    def write_pid(self, service_id: str, pid: int) -> None:
        self.pid_file_path(service_id).write_text(str(pid), encoding="utf-8")

    def read_pid(self, service_id: str) -> int | None:
        pid_file = self.pid_file_path(service_id)
        if not pid_file.exists():
            return None
        raw = pid_file.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def clear_pid(self, service_id: str) -> None:
        pid_file = self.pid_file_path(service_id)
        if pid_file.exists():
            pid_file.unlink()

    def tail_log(self, path: Path, lines: int = 20) -> str:
        if not path.exists():
            return ""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return ""
        return "\n".join(content[-lines:]).strip()

    def is_pid_running(self, pid: int | None) -> bool:
        if not pid:
            return False
        if IS_WINDOWS:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def resolve_working_directory(self, working_directory: str | None) -> str | None:
        if not working_directory:
            return None
        path = Path(working_directory)
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        return str(path)

    def run_command(
        self,
        command: Any,
        working_directory: str | None,
        shell: bool,
        background: bool,
        service_id: str | None = None,
    ) -> subprocess.Popen[Any] | subprocess.CompletedProcess[Any]:
        if not command:
            raise ValueError("未配置命令")

        if isinstance(command, (list, tuple)) and command:
            normalized_command = list(command)
            first = str(normalized_command[0]).strip().lower()
            if first in {"python", "python.exe"}:
                normalized_command[0] = sys.executable
            command = normalized_command

        kwargs: dict[str, Any] = {
            "cwd": self.resolve_working_directory(working_directory),
            "shell": shell,
            "text": True,
        }

        if background:
            stdout = None
            stderr = None
            if service_id:
                out_path, err_path = self.log_file_paths(service_id)
                stdout = out_path.open("a", encoding="utf-8")
                stderr = err_path.open("a", encoding="utf-8")
            kwargs["stdout"] = stdout
            kwargs["stderr"] = stderr
            if IS_WINDOWS:
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["start_new_session"] = True
            return subprocess.Popen(command, **kwargs)

        return subprocess.run(command, capture_output=True, check=False, **kwargs)

    def stop_pid(self, pid: int) -> None:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            return
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            return

    def probe_url(self, url: str | None) -> tuple[bool, str]:
        if not url:
            return False, "未配置检测地址"
        headers = {"User-Agent": "lkyw-collaborative-service-manager/1.0"}
        for method in ("HEAD", "GET"):
            req = urllib_request.Request(url, headers=headers, method=method)
            try:
                with DIRECT_OPENER.open(req, timeout=4) as response:
                    status_code = getattr(response, "status", 200)
                    if 200 <= status_code < 400:
                        return True, f"HTTP {status_code}"
                    return False, f"HTTP {status_code}"
            except urllib_error.HTTPError as exc:
                if 200 <= exc.code < 400:
                    return True, f"HTTP {exc.code}"
                if method == "GET":
                    return False, f"HTTP {exc.code}"
            except Exception as exc:
                if method == "GET":
                    return False, str(exc)
        return False, "未知错误"

    def is_service_running(self, service_id: str) -> bool:
        if service_id == "commandCenter":
            return True
        status = self.build_service_status(service_id)
        return status.get("running", False)

    def build_service_status(self, service_id: str) -> dict[str, Any]:
        if service_id == "commandCenter":
            return {
                "id": "commandCenter",
                "label": "协同响应指挥后端",
                "reachable": True,
                "health_detail": "HTTP 200",
                "managed": True,
                "running": True,
                "pid": os.getpid(),
                "public_url": f"http://127.0.0.1:{COMMAND_CENTER_PORT}",
                "health_url": f"http://127.0.0.1:{COMMAND_CENTER_PORT}/api/health",
                "working_directory": str(BASE_DIR),
                "start_configured": False,
                "stop_configured": False,
                "last_checked_at": utc_now_iso(),
            }

        service = self.get_service(service_id)
        pid = self.read_pid(service_id)
        managed_running = self.is_pid_running(pid)
        reachable, health_detail = self.probe_url(service.get("health_url"))

        if pid and not managed_running:
            self.clear_pid(service_id)
            pid = None

        process = self.processes.get(service_id)
        if process and process.poll() is not None:
            self.processes.pop(service_id, None)

        return {
            "id": service_id,
            "label": service.get("label", service_id),
            "reachable": reachable,
            "health_detail": health_detail,
            "managed": managed_running,
            "running": reachable or managed_running,
            "pid": pid,
            "public_url": service.get("public_url", ""),
            "health_url": service.get("health_url", ""),
            "working_directory": self.resolve_working_directory(service.get("working_directory")),
            "start_configured": bool(service.get("start_command")),
            "stop_configured": bool(service.get("stop_command")),
            "last_checked_at": utc_now_iso(),
        }

    def get_status(self) -> dict[str, Any]:
        services = {}
        services["commandCenter"] = self.build_service_status("commandCenter")
        for service_id in self.config.get("services", {}):
            services[service_id] = self.build_service_status(service_id)
        return {
            "ok": True,
            "service": {
                "name": "协同响应指挥后端 (含服务管理)",
                "started_at": service_started_at,
                "base_dir": str(BASE_DIR),
                "host": COMMAND_CENTER_HOST,
                "port": COMMAND_CENTER_PORT,
            },
            "services": services,
        }

    def start_service(self, service_id: str) -> dict[str, Any]:
        if service_id == "commandCenter":
            raise ValueError("指挥后端为当前进程，不支持远程启动")

        with self.lock:
            self.config = self.load_config()
            service = self.get_service(service_id)
            status = self.build_service_status(service_id)
            if status["running"]:
                return status

            command = service.get("start_command")
            if not command:
                raise ValueError(f"{status['label']} 未配置启动命令")

            process = self.run_command(
                command=command,
                working_directory=service.get("working_directory"),
                shell=bool(service.get("shell")),
                background=True,
                service_id=service_id,
            )
            self.processes[service_id] = process
            self.write_pid(service_id, process.pid)
            time.sleep(1.0)

            if process.poll() is not None:
                self.processes.pop(service_id, None)
                self.clear_pid(service_id)
                _, err_path = self.log_file_paths(service_id)
                error_excerpt = self.tail_log(err_path)
                label = service.get("label", service_id)
                if error_excerpt:
                    raise RuntimeError(f"{label} 启动失败:\n{error_excerpt}")
                raise RuntimeError(f"{label} 启动失败，进程已提前退出")

            return self.build_service_status(service_id)

    def stop_service(self, service_id: str) -> dict[str, Any]:
        if service_id == "commandCenter":
            raise ValueError("指挥后端为当前进程，不支持远程停止")

        with self.lock:
            self.config = self.load_config()
            service = self.get_service(service_id)
            stop_command = service.get("stop_command")

            if stop_command:
                self.run_command(
                    command=stop_command,
                    working_directory=service.get("working_directory"),
                    shell=bool(service.get("shell")),
                    background=False,
                )
            else:
                pid = self.read_pid(service_id)
                if pid:
                    self.stop_pid(pid)

            self.processes.pop(service_id, None)
            self.clear_pid(service_id)
            return self.build_service_status(service_id)


manager = ServiceManager()


def build_health_payload() -> dict[str, Any]:
    metrics = load_strategy_metrics()
    full_status = manager.get_status()
    return {
        "ok": True,
        "service": full_status["service"],
        "artifacts": {
            "strategy_html": file_info(FOLIUM_PATH),
            "mission_czml": file_info(MISSION_PATH),
            "strategy_json": file_info(PATH_RESULT_PATH),
            "cesium_assets": {"exists": CESIUM_DIR.exists()},
        },
        "streamlit": {
            "running": manager.is_service_running("streamlit"),
            "public_url": STREAMLIT_PUBLIC_URL,
        },
        "strategy_metrics": metrics,
        "services": full_status.get("services", {}),
        "checked_at": utc_now_iso(),
    }


# ── Static / view routes ──────────────────────────────────────────────

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


# ── API routes ────────────────────────────────────────────────────────

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
    try:
        if manager.is_service_running("streamlit"):
            return success_response("协同调度平台已在运行", url=STREAMLIT_PUBLIC_URL)
        manager.start_service("streamlit")
        return success_response("协同调度平台已启动", url=STREAMLIT_PUBLIC_URL)
    except (ValueError, RuntimeError) as exc:
        return error_response(str(exc))


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


# ── Service management API routes ─────────────────────────────────────

@app.route("/api/services")
def api_list_services():
    return jsonify(manager.get_status())


@app.route("/api/services/<service_id>")
def api_get_service(service_id: str):
    try:
        return jsonify({"ok": True, "service": manager.build_service_status(service_id)})
    except KeyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/api/services/<service_id>/start", methods=["POST"])
def api_start_service(service_id: str):
    try:
        svc = manager.start_service(service_id)
        return jsonify({"ok": True, "service": svc})
    except KeyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    except (ValueError, RuntimeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/services/<service_id>/stop", methods=["POST"])
def api_stop_service(service_id: str):
    try:
        svc = manager.stop_service(service_id)
        return jsonify({"ok": True, "service": svc})
    except KeyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/services/<service_id>/restart", methods=["POST"])
def api_restart_service(service_id: str):
    try:
        manager.stop_service(service_id)
        svc = manager.start_service(service_id)
        return jsonify({"ok": True, "service": svc})
    except KeyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/reload-config", methods=["POST"])
def api_reload_config():
    with manager.lock:
        manager.config = manager.load_config()
    return jsonify({"ok": True, "status": manager.get_status()})


if __name__ == "__main__":
    print(f"协同响应指挥后端已启动: http://127.0.0.1:{COMMAND_CENTER_PORT}")
    print(f"  API 健康检查: http://127.0.0.1:{COMMAND_CENTER_PORT}/api/health")
    print(f"  服务管理:     http://127.0.0.1:{COMMAND_CENTER_PORT}/api/services")
    app.run(host=COMMAND_CENTER_HOST, port=COMMAND_CENTER_PORT, threaded=True)
