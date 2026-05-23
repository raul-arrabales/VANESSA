from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from .image_generation_tasks import (
    invalid_image_generation_tasks,
    missing_task_defaults_for_tasks,
    normalize_image_generation_task_values,
)
from .platform_runtime import resolve_image_generation_adapter
from .platform_types import PlatformControlPlaneError


def _require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PlatformControlPlaneError("invalid_payload", "Expected JSON object", status_code=400)
    return payload


def _normalize_tasks(raw_tasks: Any) -> list[str]:
    tasks = normalize_image_generation_task_values(raw_tasks)
    if not tasks:
        raise PlatformControlPlaneError("invalid_tasks", "tasks must be a non-empty array", status_code=400)
    invalid = invalid_image_generation_tasks(tasks)
    if invalid:
        raise PlatformControlPlaneError("invalid_tasks", "Unsupported image generation task", status_code=400, details={"tasks": invalid})
    return tasks


def missing_image_generation_task_defaults(tasks: list[str], task_defaults: dict[str, Any]) -> list[str]:
    return missing_task_defaults_for_tasks(tasks, task_defaults)


def require_image_generation_task_defaults(tasks: list[str], task_defaults: dict[str, Any]) -> None:
    missing_defaults = missing_image_generation_task_defaults(tasks, task_defaults)
    if missing_defaults:
        raise PlatformControlPlaneError(
            "missing_image_generation_task_defaults",
            "Active image_generation binding is missing task defaults for requested tasks",
            status_code=409,
            details={"missing_task_defaults": missing_defaults, "tasks": tasks},
        )


def generate_platform_image(database_url: str, config: AuthConfig, payload: Any) -> tuple[dict[str, Any] | None, int]:
    body = _require_json_object(payload)
    tasks = _normalize_tasks(body.get("tasks"))
    adapter = resolve_image_generation_adapter(database_url, config)
    resource_policy = dict(adapter.binding.resource_policy or {})
    task_defaults = dict(resource_policy.get("task_defaults") or {})
    require_image_generation_task_defaults(tasks, task_defaults)
    generation_payload = {
        "tasks": tasks,
        "prompt": str(body.get("prompt") or "").strip(),
        "negative_prompt": str(body.get("negative_prompt") or "").strip(),
        "car_image": body.get("car_image"),
        "logo_image": body.get("logo_image"),
        "plate_boxes": body.get("plate_boxes"),
        "options": dict(body.get("options") or {}) if isinstance(body.get("options"), dict) else {},
        "runtime": {
            "resources": [dict(resource) for resource in adapter.binding.resources],
            "task_defaults": task_defaults,
        },
    }
    return adapter.generate(payload=generation_payload)
