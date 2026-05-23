from __future__ import annotations

from typing import Any

TASK_TEXT_TO_IMAGE = "text_to_image"
TASK_LICENSE_PLATE_LOGO_REPLACEMENT = "license_plate_logo_replacement"
IMAGE_GENERATION_TASKS = (TASK_TEXT_TO_IMAGE, TASK_LICENSE_PLATE_LOGO_REPLACEMENT)
VALID_IMAGE_GENERATION_TASKS = set(IMAGE_GENERATION_TASKS)

TASK_KEY_TEXT_TO_IMAGE = "image_text_to_image"
TASK_KEY_PLATE_LOGO_PROCESSOR = "image_plate_logo_replacement"

IMAGE_GENERATION_TASK_DEFAULT_KEYS = {
    "generator": TASK_KEY_TEXT_TO_IMAGE,
    "plate_logo_processor": TASK_KEY_PLATE_LOGO_PROCESSOR,
}

IMAGE_GENERATION_TASK_GROUPS = {
    TASK_TEXT_TO_IMAGE: ("generator",),
    TASK_LICENSE_PLATE_LOGO_REPLACEMENT: ("plate_logo_processor",),
}

IMAGE_GENERATION_MODEL_DEFAULT_KEYS = {"generator"}

IMAGE_GENERATION_TASK_RESOURCE_KEYS = {
    task: {IMAGE_GENERATION_TASK_DEFAULT_KEYS[default_key] for default_key in default_keys}
    for task, default_keys in IMAGE_GENERATION_TASK_GROUPS.items()
}


def normalize_image_generation_task_values(raw_tasks: Any) -> list[str]:
    if not isinstance(raw_tasks, list):
        return []
    return [str(item).strip().lower() for item in raw_tasks if str(item).strip()]


def invalid_image_generation_tasks(tasks: list[str]) -> list[str]:
    return sorted({task for task in tasks if task not in VALID_IMAGE_GENERATION_TASKS})


def missing_task_defaults_for_tasks(tasks: list[str], task_defaults: dict[str, Any]) -> list[str]:
    return sorted(
        {
            default_key
            for task in tasks
            for default_key in IMAGE_GENERATION_TASK_GROUPS.get(task, ())
            if not str(task_defaults.get(default_key) or "").strip()
        }
    )


def task_keys_from_resources(resources: list[dict[str, Any]]) -> set[str]:
    return {
        str((resource.get("metadata") or {}).get("task_key") or "").strip().lower()
        for resource in resources
        if isinstance(resource, dict)
    }


def available_tasks_from_resources(resources: list[dict[str, Any]]) -> set[str]:
    available_task_keys = task_keys_from_resources(resources)
    return {
        task
        for task, required_task_keys in IMAGE_GENERATION_TASK_RESOURCE_KEYS.items()
        if required_task_keys <= available_task_keys
    }
