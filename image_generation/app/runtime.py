from __future__ import annotations

from typing import Any

from .constants import ROLE_GATEWAY, ROLE_TASKS
from .payloads import empty_response, fake_mode, normalize_tasks
from .workers.plate_logo import replace_plate_logos
from .workers.text_to_image import text_to_image_result


def generate_local(payload: dict[str, Any], *, allowed_tasks: set[str] | None = None) -> tuple[dict[str, Any], int]:
    tasks, error = normalize_tasks(payload)
    if error:
        return error, 400
    if allowed_tasks is not None:
        invalid_tasks = sorted(set(tasks) - allowed_tasks)
        if invalid_tasks:
            return {"error": "invalid_tasks", "message": "task is not supported by this worker", "tasks": invalid_tasks}, 400

    response = empty_response(payload)
    if "text_to_image" in tasks:
        try:
            response["image"] = text_to_image_result(payload)
        except Exception as exc:  # pragma: no cover - depends on optional model runtimes
            response["warnings"].append({"code": "text_to_image_runtime_error", "message": str(exc)})
    if "license_plate_logo_replacement" in tasks:
        try:
            image, placements, warnings = replace_plate_logos(payload)
            response["image"] = image
            response["placements"] = placements
            response["warnings"].extend(warnings)
        except Exception as exc:  # pragma: no cover
            response["warnings"].append({"code": "plate_logo_runtime_error", "message": str(exc)})

    if fake_mode() and response["image"] is None:
        response["warnings"].append({"code": "fake_output_unavailable", "message": "Fake image output could not be generated"})

    if not response["warnings"]:
        response.pop("warnings", None)
    return response, 200


def generate_for_role(payload: dict[str, Any], role: str) -> tuple[dict[str, Any], int]:
    if role == ROLE_GATEWAY:
        from .gateway import generate

        return generate(payload)
    return generate_local(payload, allowed_tasks=ROLE_TASKS.get(role, set()))
