from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .constants import ROLE_ANPR, ROLE_CAPTIONING, ROLE_GATEWAY, ROLE_OBJECTS, ROLE_TASKS, SERVICE_VERSION, TASK_ROLE
from .payloads import decode_image, empty_response, fake_analyze, fake_mode, normalize_tasks
from .resources import resources_for_role


def worker_url(role: str) -> str:
    env_names = {
        ROLE_ANPR: "IMAGE_ANALYSIS_ANPR_URL",
        ROLE_OBJECTS: "IMAGE_ANALYSIS_OBJECTS_URL",
        ROLE_CAPTIONING: "IMAGE_ANALYSIS_CAPTIONING_URL",
    }
    defaults = {
        ROLE_ANPR: "http://image_analysis_anpr:8091",
        ROLE_OBJECTS: "http://image_analysis_objects:8092",
        ROLE_CAPTIONING: "http://image_analysis_captioning:8093",
    }
    env_name = env_names.get(role, "")
    default = defaults.get(role, "")
    return os.getenv(env_name, default).strip().rstrip("/") or default


def worker_timeout(role: str) -> float:
    env_names = {
        ROLE_ANPR: "IMAGE_ANALYSIS_ANPR_TIMEOUT_SECONDS",
        ROLE_OBJECTS: "IMAGE_ANALYSIS_OBJECTS_TIMEOUT_SECONDS",
        ROLE_CAPTIONING: "IMAGE_ANALYSIS_CAPTIONING_TIMEOUT_SECONDS",
    }
    defaults = {
        ROLE_ANPR: 120.0,
        ROLE_OBJECTS: 180.0,
        ROLE_CAPTIONING: 300.0,
    }
    try:
        timeout = float(os.getenv(env_names.get(role, ""), str(defaults.get(role, 120.0))))
    except ValueError:
        timeout = defaults.get(role, 120.0)
    return timeout if timeout > 0 else defaults.get(role, 120.0)


def gateway_health_worker_timeout() -> float:
    try:
        timeout = float(os.getenv("IMAGE_ANALYSIS_WORKER_HEALTH_TIMEOUT_SECONDS", "0.35"))
    except ValueError:
        timeout = 0.35
    return timeout if timeout > 0 else 0.35


def http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 5.0,
) -> tuple[dict[str, Any] | None, int, str | None]:
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310 - private compose URLs
            raw = response.read()
            if not raw:
                return {}, int(response.status), None
            parsed = json.loads(raw.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else {}, int(response.status), None
    except HTTPError as exc:
        raw_error = exc.read()
        try:
            parsed_error = json.loads(raw_error.decode("utf-8")) if raw_error else {}
        except Exception:
            parsed_error = {}
        return parsed_error if isinstance(parsed_error, dict) else {}, int(exc.code), str(exc)
    except (OSError, TimeoutError, URLError) as exc:
        return None, 0, str(exc)
    except json.JSONDecodeError as exc:
        return None, 502, str(exc)


def worker_warning(role: str, *, status_code: int, message: str | None) -> dict[str, Any]:
    codes = {
        ROLE_ANPR: "plate_worker_unavailable",
        ROLE_OBJECTS: "object_worker_unavailable",
        ROLE_CAPTIONING: "caption_worker_unavailable",
    }
    default_messages = {
        ROLE_ANPR: "License plate worker is unavailable",
        ROLE_OBJECTS: "Object detection worker is unavailable",
        ROLE_CAPTIONING: "Image captioning worker is unavailable",
    }
    return {
        "code": codes.get(role, "image_worker_unavailable"),
        "message": message or default_messages.get(role, "Image analysis worker is unavailable"),
        "status_code": status_code,
    }


def merge_worker_response(response: dict[str, Any], role: str, payload: dict[str, Any]) -> None:
    worker_image = payload.get("image") if isinstance(payload.get("image"), dict) else {}
    if response["image"].get("width", 0) <= 0 and isinstance(worker_image.get("width"), int):
        response["image"]["width"] = worker_image["width"]
    if response["image"].get("height", 0) <= 0 and isinstance(worker_image.get("height"), int):
        response["image"]["height"] = worker_image["height"]

    worker_warnings = payload.get("warnings")
    if isinstance(worker_warnings, list):
        response["warnings"].extend([item for item in worker_warnings if isinstance(item, dict)])

    if role == ROLE_ANPR:
        license_plates = payload.get("license_plates")
        response["license_plates"] = license_plates if isinstance(license_plates, list) else []
    elif role == ROLE_OBJECTS:
        objects = payload.get("objects")
        response["objects"] = objects if isinstance(objects, list) else []
    elif role == ROLE_CAPTIONING:
        caption = payload.get("caption")
        response["caption"] = caption if isinstance(caption, dict) else None


def gateway_worker_analyze(role: str, payload: dict[str, Any], tasks: list[str]) -> tuple[dict[str, Any] | None, int, str | None]:
    worker_payload = {**payload, "tasks": tasks}
    return http_json(
        worker_url(role) + "/v1/analyze",
        method="POST",
        payload=worker_payload,
        timeout_seconds=worker_timeout(role),
    )


def analyze(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    _raw, width, height, image, error = decode_image(payload)
    if error:
        return error, 400
    tasks, error = normalize_tasks(payload)
    if error:
        return error, 400

    if fake_mode():
        return fake_analyze(payload, tasks, width, height)

    response = empty_response(width, height, payload)
    if image is None:
        response["warnings"].append({"code": "image_runtime_unavailable", "message": "Pillow is unavailable in image_analysis gateway"})

    tasks_by_role: dict[str, list[str]] = {}
    for task in tasks:
        role = TASK_ROLE.get(task)
        if role:
            tasks_by_role.setdefault(role, []).append(task)

    for role, role_tasks in tasks_by_role.items():
        worker_payload, status_code, error_message = gateway_worker_analyze(role, payload, role_tasks)
        if worker_payload is None or status_code < 200 or status_code >= 300:
            message = None
            if isinstance(worker_payload, dict):
                message = str(worker_payload.get("message") or worker_payload.get("error") or "").strip() or None
            response["warnings"].append(worker_warning(role, status_code=status_code, message=message or error_message))
            continue
        merge_worker_response(response, role, worker_payload)

    if not response["warnings"]:
        response.pop("warnings", None)
    return response, 200


def worker_health(role: str) -> dict[str, Any]:
    payload, status_code, error_message = http_json(
        worker_url(role) + "/health",
        timeout_seconds=gateway_health_worker_timeout(),
    )
    return {
        "reachable": payload is not None and 200 <= status_code < 300,
        "status_code": status_code,
        "url": worker_url(role),
        "message": error_message,
    }


def health_for_role(role: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok",
        "service": "image_analysis" if role == ROLE_GATEWAY else f"image_analysis_{role}",
        "role": role,
        "version": SERVICE_VERSION,
        "fake_mode": fake_mode(),
    }
    if role == ROLE_GATEWAY and not fake_mode():
        payload["workers"] = {
            ROLE_ANPR: worker_health(ROLE_ANPR),
            ROLE_OBJECTS: worker_health(ROLE_OBJECTS),
            ROLE_CAPTIONING: worker_health(ROLE_CAPTIONING),
        }
    if role != ROLE_GATEWAY:
        payload["tasks"] = sorted(ROLE_TASKS.get(role, set()))
    return payload


def resources_from_worker(role: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    payload, status_code, error_message = http_json(
        worker_url(role) + "/v1/resources",
        timeout_seconds=gateway_health_worker_timeout(),
    )
    if payload is None or status_code < 200 or status_code >= 300:
        return [], worker_warning(role, status_code=status_code, message=error_message)
    raw_resources = payload.get("resources")
    if not isinstance(raw_resources, list):
        return [], worker_warning(role, status_code=502, message="Worker resources payload is malformed")
    return [resource for resource in raw_resources if isinstance(resource, dict)], None


def resources_payload_for_role(role: str) -> dict[str, Any]:
    if role != ROLE_GATEWAY or fake_mode():
        return {"resources": resources_for_role(role)}
    resources: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for worker_role in (ROLE_ANPR, ROLE_OBJECTS, ROLE_CAPTIONING):
        worker_resources, warning = resources_from_worker(worker_role)
        resources.extend(worker_resources)
        if warning:
            warnings.append(warning)
    payload: dict[str, Any] = {"resources": resources}
    if warnings:
        payload["warnings"] = warnings
    return payload
