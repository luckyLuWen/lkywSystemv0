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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error, request


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
LOG_DIR = BASE_DIR / "logs"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config.example.json"
LOCAL_CONFIG_PATH = BASE_DIR / "config.local.json"
IS_WINDOWS = platform.system().lower().startswith("win")
DIRECT_OPENER = request.build_opener(request.ProxyHandler({}))

RUNTIME_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


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


class ServiceManager:
    def __init__(self) -> None:
        self.started_at = utc_now_iso()
        self.lock = threading.Lock()
        self.processes: dict[str, subprocess.Popen[Any]] = {}
        self.config = self.load_config()

    def load_config(self) -> dict[str, Any]:
        if not EXAMPLE_CONFIG_PATH.exists():
            raise FileNotFoundError(f"缺少配置模板: {EXAMPLE_CONFIG_PATH}")

        with EXAMPLE_CONFIG_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)

        if LOCAL_CONFIG_PATH.exists():
            with LOCAL_CONFIG_PATH.open("r", encoding="utf-8") as file:
                local_config = json.load(file)
            config = deep_merge(config, local_config)

        config.setdefault("controller", {})
        config.setdefault("services", {})
        return config

    def controller_settings(self) -> dict[str, Any]:
        return self.config.get("controller", {})

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

    def build_service_status(self, service_id: str) -> dict[str, Any]:
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
        for service_id in self.config.get("services", {}):
            services[service_id] = self.build_service_status(service_id)

        return {
            "ok": True,
            "controller": {
                "name": "协同响应服务控制层",
                "started_at": self.started_at,
                "host": self.controller_settings().get("host", "127.0.0.1"),
                "port": self.controller_settings().get("port", 18601),
            },
            "services": services,
        }

    def start_service(self, service_id: str) -> dict[str, Any]:
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


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "LkywCollaborativeServiceManager/1.1"

    def _json_response(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sys.stdout.write(f"[{timestamp}] {self.address_string()} {format % args}\n")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._json_response(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]

        if path in {"/api/health", "/api/services"}:
            self._json_response(200, manager.get_status())
            return

        if path.startswith("/api/services/"):
            service_id = strip_prefix(path, "/api/services/").strip("/")
            try:
                payload = {"ok": True, "service": manager.build_service_status(service_id)}
                self._json_response(200, payload)
            except KeyError as exc:
                self._json_response(404, {"ok": False, "error": str(exc)})
            return

        self._json_response(404, {"ok": False, "error": "未找到接口"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]

        if path == "/api/reload-config":
            manager.config = manager.load_config()
            self._json_response(200, {"ok": True, "status": manager.get_status()})
            return

        if not path.startswith("/api/services/"):
            self._json_response(404, {"ok": False, "error": "未找到接口"})
            return

        tail = strip_prefix(path, "/api/services/")
        parts = [item for item in tail.split("/") if item]
        if len(parts) != 2:
            self._json_response(404, {"ok": False, "error": "未找到接口"})
            return

        service_id, action = parts

        try:
            if action == "start":
                service = manager.start_service(service_id)
                self._json_response(200, {"ok": True, "service": service})
                return

            if action == "stop":
                service = manager.stop_service(service_id)
                self._json_response(200, {"ok": True, "service": service})
                return

            if action == "restart":
                manager.stop_service(service_id)
                service = manager.start_service(service_id)
                self._json_response(200, {"ok": True, "service": service})
                return

            self._json_response(404, {"ok": False, "error": "未找到接口"})
        except KeyError as exc:
            self._json_response(404, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"ok": False, "error": str(exc)})


def main() -> None:
    settings = manager.controller_settings()
    host = settings.get("host", "127.0.0.1")
    port = int(settings.get("port", 18601))

    server = ThreadingHTTPServer((host, port), RequestHandler)
    print(f"协同响应服务控制层已启动: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
