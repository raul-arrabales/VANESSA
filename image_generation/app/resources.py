from __future__ import annotations

from typing import Any

from .constants import (
    DEFAULT_TEXT_TO_IMAGE_MODEL_ID,
    ROLE_GATEWAY,
    ROLE_PLATE_LOGO,
    ROLE_TEXT_TO_IMAGE,
    TASK_KEY_PLATE_LOGO_PROCESSOR,
    TASK_KEY_TEXT_TO_IMAGE,
)
from .payloads import resource_id


def resources() -> list[dict[str, Any]]:
    return [
        {
            "id": resource_id("IMAGE_GENERATION_TEXT_TO_IMAGE_MODEL_ID", DEFAULT_TEXT_TO_IMAGE_MODEL_ID),
            "display_name": "Tiny SD text-to-image generator",
            "provider_resource_id": resource_id("IMAGE_GENERATION_TEXT_TO_IMAGE_MODEL_ID", DEFAULT_TEXT_TO_IMAGE_MODEL_ID),
            "metadata": {
                "task_key": TASK_KEY_TEXT_TO_IMAGE,
                "engine": "diffusers",
                "default_model": DEFAULT_TEXT_TO_IMAGE_MODEL_ID,
            },
        },
        {
            "id": resource_id("IMAGE_GENERATION_PLATE_LOGO_PROCESSOR_ID", "plate-logo-processor-opencv"),
            "display_name": "License plate logo replacement processor",
            "provider_resource_id": resource_id("IMAGE_GENERATION_PLATE_LOGO_PROCESSOR_ID", "plate-logo-processor-opencv"),
            "resource_kind": "processor",
            "metadata": {"task_key": TASK_KEY_PLATE_LOGO_PROCESSOR, "engine": "opencv"},
        },
    ]


def resources_for_role(role: str) -> list[dict[str, Any]]:
    all_resources = resources()
    if role == ROLE_GATEWAY:
        return all_resources
    task_keys_by_role = {
        ROLE_TEXT_TO_IMAGE: {TASK_KEY_TEXT_TO_IMAGE},
        ROLE_PLATE_LOGO: {TASK_KEY_PLATE_LOGO_PROCESSOR},
    }
    task_keys = task_keys_by_role.get(role, set())
    return [resource for resource in all_resources if dict(resource.get("metadata") or {}).get("task_key") in task_keys]


def resources_for_roles(roles: list[str] | tuple[str, ...] | set[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for role in roles:
        if role == ROLE_GATEWAY:
            continue
        result.extend(resources_for_role(role))
    return result
