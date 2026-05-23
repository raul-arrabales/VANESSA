from __future__ import annotations

import base64
import os
from io import BytesIO
from typing import Any

from .constants import VALID_TASKS

try:  # pragma: no cover - optional in very small test envs
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]


def fake_mode() -> bool:
    return os.getenv("IMAGE_GENERATION_FAKE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def resource_id(env_name: str, default: str) -> str:
    return os.getenv(env_name, default).strip() or default


def encode_image(image: Any, *, mime_type: str = "image/png") -> dict[str, Any]:
    if Image is None:
        return {"data_base64": "", "mime_type": mime_type, "width": 0, "height": 0}
    format_name = "PNG" if mime_type == "image/png" else "JPEG"
    output = BytesIO()
    image.save(output, format=format_name)
    width, height = image.size
    return {
        "data_base64": base64.b64encode(output.getvalue()).decode("ascii"),
        "mime_type": mime_type,
        "width": int(width),
        "height": int(height),
    }


def decode_image_payload(value: Any, *, field_name: str) -> tuple[bytes, int, int, Any | None, dict[str, Any] | None]:
    if not isinstance(value, dict):
        return b"", 0, 0, None, {"error": f"invalid_{field_name}", "message": f"{field_name} must be an object"}
    mime_type = str(value.get("mime_type") or "").strip().lower()
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        return b"", 0, 0, None, {"error": f"invalid_{field_name}", "message": f"unsupported {field_name}.mime_type"}
    data_base64 = str(value.get("data_base64") or "").strip()
    if not data_base64:
        return b"", 0, 0, None, {"error": f"invalid_{field_name}", "message": f"{field_name}.data_base64 is required"}
    try:
        raw = base64.b64decode(data_base64, validate=True)
    except ValueError:
        return b"", 0, 0, None, {"error": f"invalid_{field_name}", "message": f"{field_name}.data_base64 is invalid"}
    if Image is None:
        return raw, 0, 0, None, None
    try:
        with Image.open(BytesIO(raw)) as image:
            normalized = image.convert("RGBA")
            width, height = normalized.size
    except Exception:
        return b"", 0, 0, None, {"error": f"invalid_{field_name}", "message": f"{field_name} payload could not be decoded"}
    return raw, int(width), int(height), normalized, None


def normalize_tasks(payload: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        return [], {"error": "invalid_tasks", "message": "tasks must be a non-empty array"}
    tasks = [str(item).strip().lower() for item in raw_tasks if str(item).strip()]
    invalid = sorted({task for task in tasks if task not in VALID_TASKS})
    if invalid:
        return [], {"error": "invalid_tasks", "message": "unsupported image generation task", "tasks": invalid}
    return tasks, None


def int_option(payload: dict[str, Any], name: str, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    try:
        value = int(options.get(name, payload.get(name, default)))
    except (TypeError, ValueError):
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def float_option(payload: dict[str, Any], name: str, default: float) -> float:
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    try:
        return float(options.get(name, payload.get(name, default)))
    except (TypeError, ValueError):
        return default


def runtime_defaults(payload: dict[str, Any]) -> dict[str, str]:
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    task_defaults = runtime.get("task_defaults") if isinstance(runtime.get("task_defaults"), dict) else {}
    return {str(key): str(value) for key, value in task_defaults.items() if str(value).strip()}


def empty_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "image": None,
        "placements": [],
        "model_resources": runtime_defaults(payload),
        "warnings": [],
    }


def fake_generated_image(prompt: str, *, width: int, height: int) -> Any:
    if Image is None:
        return None
    image = Image.new("RGB", (max(1, width), max(1, height)), (36, 40, 46))
    if ImageDraw is not None:
        draw = ImageDraw.Draw(image)
        draw.rectangle((12, 12, image.width - 12, image.height - 12), outline=(130, 210, 180), width=3)
        draw.text((20, 20), (prompt or "VANESSA image")[:80], fill=(240, 240, 240))
    return image
