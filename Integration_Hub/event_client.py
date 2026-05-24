from __future__ import annotations

import json
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def env_flag(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class IntegrationEventPublisher:
    """Small HTTP publisher used by subsystem backends.

    Subsystems should not talk to Redis/MQTT/Kafka directly. They post normalized
    domain events to Integration Hub, and the hub owns the backing event bus.
    """

    def __init__(
        self,
        source: str,
        hub_url: str | None = None,
        enabled: bool | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.source = source
        self.hub_url = (hub_url or os.getenv("INTEGRATION_HUB_URL", "http://127.0.0.1:18701")).rstrip("/")
        self.enabled = env_flag("INTEGRATION_EVENTS_ENABLED", "1") if enabled is None else enabled
        self.timeout_seconds = float(
            timeout_seconds if timeout_seconds is not None else os.getenv("INTEGRATION_EVENT_TIMEOUT_SECONDS", "0.5")
        )
        self.hostname = socket.gethostname()

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        subject: str = "",
        severity: str = "info",
        correlation_id: str = "",
        trace_id: str = "",
    ) -> bool:
        if not self.enabled:
            return False

        envelope = {
            "eventId": str(uuid.uuid4()),
            "type": event_type,
            "source": self.source,
            "subject": subject,
            "severity": severity,
            "timestamp": utc_now_iso(),
            "version": 1,
            "correlationId": correlation_id,
            "traceId": trace_id,
            "host": self.hostname,
            "payload": payload or {},
        }

        body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            f"{self.hub_url}/api/events",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return 200 <= response.status < 300
        except (error.URLError, TimeoutError, OSError, ValueError):
            return False


class IntegrationCommandClient:
    """HTTP command consumer used by subsystem backends.

    The client polls Integration Hub instead of talking to Redis directly. That
    keeps Redis Streams/Kafka/MQTT choices inside the hub boundary.
    """

    def __init__(
        self,
        target: str,
        targets: list[str] | None = None,
        hub_url: str | None = None,
        enabled: bool | None = None,
        timeout_seconds: float | None = None,
        block_ms: int | None = None,
    ) -> None:
        self.target = target
        self.targets = [item for item in (targets or [target]) if item]
        self.hub_url = (hub_url or os.getenv("INTEGRATION_HUB_URL", "http://127.0.0.1:18701")).rstrip("/")
        self.enabled = env_flag("INTEGRATION_COMMANDS_ENABLED", "1") if enabled is None else enabled
        self.block_ms = int(block_ms if block_ms is not None else os.getenv("INTEGRATION_COMMAND_BLOCK_MS", "10000"))
        self.timeout_seconds = float(
            timeout_seconds
            if timeout_seconds is not None
            else os.getenv("INTEGRATION_COMMAND_TIMEOUT_SECONDS", str(max(3, self.block_ms / 1000 + 2)))
        )
        self.last_id = os.getenv("INTEGRATION_COMMAND_LAST_ID", "$")

    def poll(self, count: int = 10) -> list[dict[str, Any]]:
        if not self.enabled or not self.targets:
            return []

        params: list[tuple[str, str]] = [
            ("lastId", self.last_id),
            ("blockMs", str(self.block_ms)),
            ("count", str(count)),
        ]
        for target in self.targets:
            params.append(("target", target))

        url = f"{self.hub_url}/api/commands/poll?{parse.urlencode(params)}"
        req = request.Request(url, method="GET")

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                if not (200 <= response.status < 300):
                    return []
                payload = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            return []

        self.last_id = payload.get("lastId") or self.last_id
        commands = payload.get("commands") or []
        return [item for item in commands if isinstance(item, dict)]


def build_command_status_payload(
    command: dict[str, Any],
    status: str,
    *,
    message: str = "",
    result: dict[str, Any] | None = None,
    error_message: str = "",
) -> dict[str, Any]:
    command_id = command.get("commandId") or command.get("command_id") or ""
    return {
        "commandId": command_id,
        "commandType": command.get("type", ""),
        "target": command.get("target", ""),
        "source": command.get("source", ""),
        "subject": command.get("subject", ""),
        "status": status,
        "message": message,
        "result": result or {},
        "error": error_message,
        "commandStreamId": command.get("streamId", ""),
        "updatedAt": utc_now_iso(),
    }
