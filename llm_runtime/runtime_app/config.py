from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class RuntimeControllerConfig:
    capability: str
    service_name: str
    listen_host: str
    listen_port: int
    child_host: str
    child_port: int
    dtype: str
    device: str | None
    model_root: Path
    startup_local_path: str | None
    startup_runtime_model_id: str | None
    startup_display_name: str | None
    additional_args: tuple[str, ...]
    load_timeout_seconds: int
    health_poll_interval_seconds: float


def load_runtime_controller_config() -> RuntimeControllerConfig:
    capability = os.getenv("LLM_RUNTIME_CAPABILITY", "llm_inference").strip().lower() or "llm_inference"
    startup_local_path = (
        os.getenv(
            "LLM_EMBEDDINGS_LOCAL_MODEL_PATH" if capability == "embeddings" else "LLM_INFERENCE_LOCAL_MODEL_PATH",
            "",
        ).strip()
        or os.getenv("LLM_LOCAL_MODEL_PATH", "").strip()
        or None
    )
    startup_runtime_model_id = os.getenv("LLM_LOCAL_UPSTREAM_MODEL", "").strip() or startup_local_path
    if capability == "embeddings":
        startup_runtime_model_id = (
            os.getenv("LLM_LOCAL_EMBEDDINGS_UPSTREAM_MODEL", "").strip()
            or startup_runtime_model_id
        )
    startup_display_name = os.getenv("LLM_RUNTIME_STARTUP_DISPLAY_NAME", "").strip() or None
    additional_args = tuple(
        arg
        for arg in shlex.split(os.getenv("LLM_RUNTIME_ADDITIONAL_ARGS", ""))
        if arg.strip()
    )
    device = os.getenv("LLM_RUNTIME_DEVICE", "").strip() or None
    return RuntimeControllerConfig(
        capability=capability,
        service_name=os.getenv("LLM_RUNTIME_SERVICE_NAME", f"llm_runtime_{capability}").strip()
        or f"llm_runtime_{capability}",
        listen_host=os.getenv("LLM_RUNTIME_CONTROLLER_HOST", "0.0.0.0").strip() or "0.0.0.0",
        listen_port=_get_int_env("LLM_RUNTIME_CONTROLLER_PORT", 8000),
        child_host=os.getenv("LLM_RUNTIME_CHILD_HOST", "127.0.0.1").strip() or "127.0.0.1",
        child_port=_get_int_env("LLM_RUNTIME_CHILD_PORT", 8001),
        dtype=os.getenv("LLM_RUNTIME_DTYPE", "auto").strip() or "auto",
        device=device,
        model_root=Path(os.getenv("MODEL_STORAGE_ROOT", "/models/llm").strip() or "/models/llm"),
        startup_local_path=startup_local_path,
        startup_runtime_model_id=startup_runtime_model_id,
        startup_display_name=startup_display_name,
        additional_args=additional_args,
        load_timeout_seconds=_get_int_env("LLM_RUNTIME_LOAD_TIMEOUT_SECONDS", 180),
        health_poll_interval_seconds=0.5,
    )
