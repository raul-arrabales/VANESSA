from __future__ import annotations

from typing import Any

from .constants import DEFAULT_CAPTION_MODEL_ID, ROLE_ANPR, ROLE_CAPTIONING, ROLE_GATEWAY, ROLE_OBJECTS
from .payloads import resource_id


def resources() -> list[dict[str, Any]]:
    return [
        {
            "id": resource_id("IMAGE_ANALYSIS_PLATE_DETECTOR_MODEL_ID", "yolo-v9-t-384-license-plate-end2end"),
            "display_name": "License plate detector",
            "provider_resource_id": resource_id("IMAGE_ANALYSIS_PLATE_DETECTOR_MODEL_ID", "yolo-v9-t-384-license-plate-end2end"),
            "metadata": {"task_key": "image_plate_detection", "engine": "open-image-models"},
        },
        {
            "id": resource_id("IMAGE_ANALYSIS_PLATE_OCR_MODEL_ID", "cct-xs-v2-global-model"),
            "display_name": "License plate OCR",
            "provider_resource_id": resource_id("IMAGE_ANALYSIS_PLATE_OCR_MODEL_ID", "cct-xs-v2-global-model"),
            "metadata": {"task_key": "image_plate_ocr", "engine": "fast-plate-ocr"},
        },
        {
            "id": resource_id("IMAGE_ANALYSIS_OBJECT_DETECTOR_MODEL_ID", "rfdetr-nano"),
            "display_name": "Object detector",
            "provider_resource_id": resource_id("IMAGE_ANALYSIS_OBJECT_DETECTOR_MODEL_ID", "rfdetr-nano"),
            "metadata": {"task_key": "object_detection", "engine": "rf-detr"},
        },
        {
            "id": resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", DEFAULT_CAPTION_MODEL_ID),
            "display_name": "Image captioner",
            "provider_resource_id": resource_id("IMAGE_ANALYSIS_CAPTION_MODEL_ID", DEFAULT_CAPTION_MODEL_ID),
            "metadata": {"task_key": "image_captioning", "engine": "florence-2"},
        },
    ]


def resources_for_role(role: str) -> list[dict[str, Any]]:
    all_resources = resources()
    if role == ROLE_GATEWAY:
        return all_resources
    task_keys_by_role = {
        ROLE_ANPR: {"image_plate_detection", "image_plate_ocr"},
        ROLE_OBJECTS: {"object_detection"},
        ROLE_CAPTIONING: {"image_captioning"},
    }
    task_keys = task_keys_by_role.get(role, set())
    return [resource for resource in all_resources if dict(resource.get("metadata") or {}).get("task_key") in task_keys]
