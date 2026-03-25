from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import RuntimeControllerConfig

_DEFAULT_TIMEOUT_SECONDS = 2.0


def _http_json_request(
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any] | None, int]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            return (json.loads(raw) if raw else {}), int(response.status)
    except TimeoutError:
        return None, 504
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {"error": "upstream_error"}
        except ValueError:
            parsed = {"error": "upstream_error", "body": raw}
        return parsed, int(exc.code)
    except URLError:
        return None, 502


@dataclass
class RuntimeState:
    load_state: str = "empty"
    runtime_model_id: str | None = None
    local_path: str | None = None
    managed_model_id: str | None = None
    display_name: str | None = None
    last_error: str | None = None

    def as_payload(self, capability: str) -> dict[str, Any]:
        return {
            "capability": capability,
            "load_state": self.load_state,
            "runtime_model_id": self.runtime_model_id,
            "local_path": self.local_path,
            "managed_model_id": self.managed_model_id,
            "display_name": self.display_name,
            "last_error": self.last_error,
        }


class RuntimeController:
    def __init__(self, config: RuntimeControllerConfig) -> None:
        self._config = config
        self._lock = threading.RLock()
        self._process: subprocess.Popen[bytes] | None = None
        self._state = RuntimeState()

    @property
    def config(self) -> RuntimeControllerConfig:
        return self._config

    def startup(self) -> None:
        if not self._config.startup_local_path or not self._config.startup_runtime_model_id:
            return
        try:
            self.load_model(
                runtime_model_id=self._config.startup_runtime_model_id,
                local_path=self._config.startup_local_path,
                managed_model_id=None,
                display_name=self._config.startup_display_name,
            )
        except ValueError as exc:
            with self._lock:
                self._state = RuntimeState(
                    load_state="error",
                    runtime_model_id=self._config.startup_runtime_model_id,
                    local_path=self._config.startup_local_path,
                    display_name=self._config.startup_display_name,
                    last_error=str(exc),
                )

    def shutdown(self) -> None:
        with self._lock:
            self._stop_process_locked()

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return self._state.as_payload(self._config.capability)

    def load_model(
        self,
        *,
        runtime_model_id: str,
        local_path: str,
        managed_model_id: str | None,
        display_name: str | None,
    ) -> dict[str, Any]:
        normalized_runtime_id = runtime_model_id.strip()
        normalized_local_path = local_path.strip()
        if not normalized_runtime_id:
            raise ValueError("runtime_model_id is required")
        if not normalized_local_path:
            raise ValueError("local_path is required")
        local_path_obj = Path(normalized_local_path)
        if not str(local_path_obj).startswith(str(self._config.model_root)):
            raise ValueError(f"local_path must stay under {self._config.model_root}")
        if not local_path_obj.exists():
            raise ValueError(f"local_path does not exist: {normalized_local_path}")

        with self._lock:
            self._stop_process_locked()
            self._state = RuntimeState(
                load_state="loading",
                runtime_model_id=normalized_runtime_id,
                local_path=normalized_local_path,
                managed_model_id=managed_model_id.strip() if managed_model_id else None,
                display_name=display_name.strip() if display_name else None,
                last_error=None,
            )
            command = self._build_command(normalized_local_path, normalized_runtime_id)
            self._process = subprocess.Popen(command)  # noqa: S603
            thread = threading.Thread(
                target=self._await_runtime_ready,
                args=(normalized_runtime_id, normalized_local_path),
                daemon=True,
            )
            thread.start()
            return self._state.as_payload(self._config.capability)

    def unload_model(self) -> dict[str, Any]:
        with self._lock:
            self._stop_process_locked()
            self._state = RuntimeState()
            return self._state.as_payload(self._config.capability)

    def child_base_url(self) -> str:
        return f"http://{self._config.child_host}:{self._config.child_port}"

    def _build_command(self, local_path: str, runtime_model_id: str) -> list[str]:
        command = [
            "vllm",
            "serve",
            local_path,
            "--host",
            self._config.child_host,
            "--port",
            str(self._config.child_port),
            "--served-model-name",
            runtime_model_id,
            "--dtype",
            self._config.dtype,
        ]
        if self._config.device:
            command.extend(["--device", self._config.device])
        command.extend(self._config.additional_args)
        return command

    def _stop_process_locked(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def _await_runtime_ready(self, runtime_model_id: str, local_path: str) -> None:
        deadline = time.monotonic() + self._config.load_timeout_seconds
        models_url = self.child_base_url().rstrip("/") + "/v1/models"
        while time.monotonic() < deadline:
            with self._lock:
                process = self._process
                current_state = self._state
            if current_state.runtime_model_id != runtime_model_id or current_state.local_path != local_path:
                return
            if process is None:
                return
            if process.poll() is not None:
                with self._lock:
                    if self._state.runtime_model_id == runtime_model_id:
                        self._state.load_state = "error"
                        self._state.last_error = f"runtime_exited:{process.returncode}"
                return
            payload, status_code = _http_json_request(models_url, method="GET", timeout_seconds=1.5)
            if 200 <= status_code < 300 and isinstance(payload, dict):
                data = payload.get("data")
                if isinstance(data, list) and any(
                    isinstance(item, dict) and str(item.get("id") or "").strip() == runtime_model_id
                    for item in data
                ):
                    with self._lock:
                        if self._state.runtime_model_id == runtime_model_id:
                            self._state.load_state = "loaded"
                            self._state.last_error = None
                    return
            time.sleep(self._config.health_poll_interval_seconds)
        with self._lock:
            if self._state.runtime_model_id == runtime_model_id:
                self._state.load_state = "error"
                self._state.last_error = "runtime_load_timeout"
                self._stop_process_locked()
