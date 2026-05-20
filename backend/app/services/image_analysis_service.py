from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from .platform_runtime import resolve_image_analysis_adapter
from .platform_types import PlatformControlPlaneError

_VALID_IMAGE_TASKS = {"license_plate_recognition", "object_detection", "captioning"}


def _require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PlatformControlPlaneError("invalid_payload", "Expected JSON object", status_code=400)
    return payload


def _normalize_tasks(raw_tasks: Any) -> list[str]:
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise PlatformControlPlaneError("invalid_tasks", "tasks must be a non-empty array", status_code=400)
    tasks = [str(item).strip().lower() for item in raw_tasks if str(item).strip()]
    invalid = sorted({task for task in tasks if task not in _VALID_IMAGE_TASKS})
    if invalid:
        raise PlatformControlPlaneError("invalid_tasks", "Unsupported image analysis task", status_code=400, details={"tasks": invalid})
    return tasks


def analyze_platform_image(database_url: str, config: AuthConfig, payload: Any) -> tuple[dict[str, Any] | None, int]:
    body = _require_json_object(payload)
    image = body.get("image")
    if not isinstance(image, dict):
        raise PlatformControlPlaneError("invalid_image", "image must be an object", status_code=400)
    data_base64 = str(image.get("data_base64") or "").strip()
    mime_type = str(image.get("mime_type") or "").strip()
    if not data_base64 or not mime_type:
        raise PlatformControlPlaneError("invalid_image", "image.data_base64 and image.mime_type are required", status_code=400)
    tasks = _normalize_tasks(body.get("tasks"))
    adapter = resolve_image_analysis_adapter(database_url, config)
    resource_policy = dict(adapter.binding.resource_policy or {})
    analysis_payload = {
        "image": {"data_base64": data_base64, "mime_type": mime_type},
        "tasks": tasks,
        "options": dict(body.get("options") or {}) if isinstance(body.get("options"), dict) else {},
        "runtime": {
            "resources": [dict(resource) for resource in adapter.binding.resources],
            "task_defaults": dict(resource_policy.get("task_defaults") or {}),
        },
    }
    return adapter.analyze(payload=analysis_payload)
