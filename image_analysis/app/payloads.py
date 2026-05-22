from __future__ import annotations

import base64
import os
from io import BytesIO
from typing import Any

from .constants import VALID_TASKS

try:  # pragma: no cover - optional dependency in lightweight test environments
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]


def fake_mode() -> bool:
    return os.getenv("IMAGE_ANALYSIS_FAKE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def resource_id(env_name: str, default: str) -> str:
    return os.getenv(env_name, default).strip() or default


def decode_image(payload: dict[str, Any]) -> tuple[bytes, int, int, Any | None, dict[str, Any] | None]:
    image_payload = payload.get("image")
    if not isinstance(image_payload, dict):
        return b"", 0, 0, None, {"error": "invalid_image", "message": "image must be an object"}
    mime_type = str(image_payload.get("mime_type") or "").strip().lower()
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        return b"", 0, 0, None, {"error": "invalid_image", "message": "unsupported image.mime_type"}
    data_base64 = str(image_payload.get("data_base64") or "").strip()
    if not data_base64:
        return b"", 0, 0, None, {"error": "invalid_image", "message": "image.data_base64 is required"}
    try:
        raw = base64.b64decode(data_base64, validate=True)
    except ValueError:
        return b"", 0, 0, None, {"error": "invalid_image", "message": "image.data_base64 is invalid"}
    if Image is None:
        return raw, 0, 0, None, None
    try:
        with Image.open(BytesIO(raw)) as image:
            rgb_image = image.convert("RGB")
            width, height = rgb_image.size
    except Exception:
        return b"", 0, 0, None, {"error": "invalid_image", "message": "image payload could not be decoded"}
    return raw, int(width), int(height), rgb_image, None


def normalize_tasks(payload: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        return [], {"error": "invalid_tasks", "message": "tasks must be a non-empty array"}
    tasks = [str(item).strip().lower() for item in raw_tasks if str(item).strip()]
    invalid = sorted({task for task in tasks if task not in VALID_TASKS})
    if invalid:
        return [], {"error": "invalid_tasks", "message": "unsupported image analysis task", "tasks": invalid}
    return tasks, None


def box(width: int, height: int) -> list[int]:
    w = max(width, 1)
    h = max(height, 1)
    return [max(0, w // 4), max(0, h // 3), max(1, (w * 3) // 4), max(1, h // 2)]


def normalized_box(box_value: list[int], width: int, height: int) -> list[float]:
    w = max(width, 1)
    h = max(height, 1)
    return [
        round(box_value[0] / w, 6),
        round(box_value[1] / h, 6),
        round(box_value[2] / w, 6),
        round(box_value[3] / h, 6),
    ]


def float_option(payload: dict[str, Any], name: str, default: float) -> float:
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    thresholds = payload.get("thresholds") if isinstance(payload.get("thresholds"), dict) else {}
    value = options.get(name, thresholds.get(name, default))
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def int_option(payload: dict[str, Any], name: str, default: int) -> int:
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    value = options.get(name, payload.get(name, default))
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def runtime_defaults(payload: dict[str, Any]) -> dict[str, str]:
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    task_defaults = runtime.get("task_defaults") if isinstance(runtime.get("task_defaults"), dict) else {}
    return {str(key): str(value) for key, value in task_defaults.items() if str(value).strip()}


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_box_xyxy(value: Any) -> list[int] | None:
    if value is None:
        return None
    try:
        values = list(value)
    except TypeError:
        return None
    if len(values) < 4:
        return None
    return [int(round(float(values[index]))) for index in range(4)]


def empty_response(width: int, height: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "image": {"width": width, "height": height},
        "license_plates": [],
        "objects": [],
        "caption": None,
        "model_resources": runtime_defaults(payload),
        "warnings": [],
    }


def fake_analyze(payload: dict[str, Any], tasks: list[str], width: int, height: int) -> tuple[dict[str, Any], int]:
    response = empty_response(width, height, payload)
    fake_box = box(width, height)
    if "license_plate_recognition" in tasks:
        response["license_plates"] = [
            {
                "text": os.getenv("IMAGE_ANALYSIS_FAKE_PLATE_TEXT", "LOCAL123"),
                "text_confidence": 0.99,
                "box_xyxy": fake_box,
                "box_normalized_xyxy": normalized_box(fake_box, width, height),
                "plate_detector_model_id": response["model_resources"].get("plate_detector"),
                "plate_ocr_model_id": response["model_resources"].get("plate_ocr"),
            }
        ]
    if "object_detection" in tasks:
        response["objects"] = [
            {
                "label": "vehicle",
                "confidence": 0.95,
                "box_xyxy": fake_box,
                "box_normalized_xyxy": normalized_box(fake_box, width, height),
                "object_detector_model_id": response["model_resources"].get("object_detector"),
            }
        ]
    if "captioning" in tasks:
        response["caption"] = {
            "text": "A vehicle is visible in the image.",
            "captioner_model_id": response["model_resources"].get("captioner"),
        }
    response.pop("warnings", None)
    return response, 200
