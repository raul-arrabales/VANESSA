from __future__ import annotations

from typing import Any

TASK_LICENSE_PLATE_RECOGNITION = "license_plate_recognition"
TASK_OBJECT_DETECTION = "object_detection"
TASK_CAPTIONING = "captioning"
IMAGE_ANALYSIS_TASKS = (TASK_LICENSE_PLATE_RECOGNITION, TASK_OBJECT_DETECTION, TASK_CAPTIONING)
VALID_IMAGE_ANALYSIS_TASKS = set(IMAGE_ANALYSIS_TASKS)

TASK_KEY_IMAGE_PLATE_DETECTION = "image_plate_detection"
TASK_KEY_IMAGE_PLATE_OCR = "image_plate_ocr"
TASK_KEY_OBJECT_DETECTION = "object_detection"
TASK_KEY_IMAGE_CAPTIONING = "image_captioning"

IMAGE_ANALYSIS_TASK_DEFAULT_KEYS = {
    "plate_detector": TASK_KEY_IMAGE_PLATE_DETECTION,
    "plate_ocr": TASK_KEY_IMAGE_PLATE_OCR,
    "object_detector": TASK_KEY_OBJECT_DETECTION,
    "captioner": TASK_KEY_IMAGE_CAPTIONING,
}

IMAGE_ANALYSIS_TASK_GROUPS = {
    TASK_LICENSE_PLATE_RECOGNITION: ("plate_detector", "plate_ocr"),
    TASK_OBJECT_DETECTION: ("object_detector",),
    TASK_CAPTIONING: ("captioner",),
}

IMAGE_ANALYSIS_TASK_RESOURCE_KEYS = {
    task: {IMAGE_ANALYSIS_TASK_DEFAULT_KEYS[default_key] for default_key in default_keys}
    for task, default_keys in IMAGE_ANALYSIS_TASK_GROUPS.items()
}


def normalize_image_analysis_task_values(raw_tasks: Any) -> list[str]:
    if not isinstance(raw_tasks, list):
        return []
    return [str(item).strip().lower() for item in raw_tasks if str(item).strip()]


def invalid_image_analysis_tasks(tasks: list[str]) -> list[str]:
    return sorted({task for task in tasks if task not in VALID_IMAGE_ANALYSIS_TASKS})


def missing_task_defaults_for_tasks(tasks: list[str], task_defaults: dict[str, Any]) -> list[str]:
    return sorted(
        {
            default_key
            for task in tasks
            for default_key in IMAGE_ANALYSIS_TASK_GROUPS.get(task, ())
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
        for task, required_task_keys in IMAGE_ANALYSIS_TASK_RESOURCE_KEYS.items()
        if required_task_keys <= available_task_keys
    }
