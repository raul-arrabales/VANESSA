from __future__ import annotations

from typing import Any

from .constants import ROLE_GATEWAY, ROLE_TASKS
from .payloads import decode_image, empty_response, fake_analyze, fake_mode, normalize_tasks
from .workers.anpr import plate_results
from .workers.captioning import caption_result
from .workers.objects import object_results


def analyze_local(payload: dict[str, Any], *, allowed_tasks: set[str] | None = None) -> tuple[dict[str, Any], int]:
    _raw, width, height, image, error = decode_image(payload)
    if error:
        return error, 400
    tasks, error = normalize_tasks(payload)
    if error:
        return error, 400
    if allowed_tasks is not None:
        invalid_tasks = sorted(set(tasks) - allowed_tasks)
        if invalid_tasks:
            return {"error": "invalid_tasks", "message": "task is not supported by this worker", "tasks": invalid_tasks}, 400

    response = empty_response(width, height, payload)

    if fake_mode():
        return fake_analyze(payload, tasks, width, height)

    if image is None:
        response["warnings"].append({"code": "image_runtime_unavailable", "message": "Pillow is unavailable"})
        return response, 200

    if "license_plate_recognition" in tasks:
        try:
            response["license_plates"] = plate_results(image, width, height, payload)
        except Exception as exc:  # pragma: no cover - depends on optional model runtimes
            response["warnings"].append({"code": "plate_runtime_error", "message": str(exc)})
    if "object_detection" in tasks:
        try:
            response["objects"] = object_results(image, width, height, payload)
        except Exception as exc:  # pragma: no cover
            response["warnings"].append({"code": "object_runtime_error", "message": str(exc)})
    if "captioning" in tasks:
        try:
            response["caption"] = caption_result(image, width, height, payload)
        except Exception as exc:  # pragma: no cover
            response["warnings"].append({"code": "caption_runtime_error", "message": str(exc)})
            response["caption"] = {
                "text": "",
                "captioner_model_id": response["model_resources"].get("captioner"),
                "status": "model_runtime_error",
            }

    if not response["warnings"]:
        response.pop("warnings", None)

    return response, 200


def analyze_for_role(payload: dict[str, Any], role: str) -> tuple[dict[str, Any], int]:
    if role == ROLE_GATEWAY:
        from .gateway import analyze

        return analyze(payload)
    return analyze_local(payload, allowed_tasks=ROLE_TASKS.get(role, set()))
