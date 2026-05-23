from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .constants import (
    DEFAULT_IMAGE_GENERATION_WORKERS,
    ROLE_PLATE_LOGO,
    ROLE_GATEWAY,
    ROLE_TASKS,
    ROLE_TEXT_TO_IMAGE,
    SERVICE_VERSION,
    TASK_ROLE,
    WORKER_ROLES,
)
from .payloads import empty_response, fake_mode, normalize_tasks
from .resources import resources_for_role, resources_for_roles


def enabled_worker_roles() -> tuple[str, ...]:
    raw = os.getenv("IMAGE_GENERATION_WORKERS", DEFAULT_IMAGE_GENERATION_WORKERS).strip().lower()
    if not raw:
        raw = DEFAULT_IMAGE_GENERATION_WORKERS
    if raw == "none":
        return ()
    roles: list[str] = []
    for item in raw.split(","):
        role = item.strip().lower()
        if role and role in WORKER_ROLES and role not in roles:
            roles.append(role)
    return tuple(roles)


def enabled_tasks() -> set[str]:
    tasks: set[str] = set()
    for role in enabled_worker_roles():
        tasks.update(ROLE_TASKS.get(role, set()))
    return tasks


def disabled_task_error(tasks: list[str]) -> dict[str, Any] | None:
    disabled_tasks = sorted(set(tasks) - enabled_tasks())
    if not disabled_tasks:
        return None
    disabled_roles = sorted({TASK_ROLE.get(task, "") for task in disabled_tasks if TASK_ROLE.get(task)})
    return {
        "error": "image_generation_task_disabled",
        "message": "Requested image-generation task is not enabled for this provider",
        "tasks": disabled_tasks,
        "workers": disabled_roles,
    }


def worker_url(role: str) -> str:
    env_names = {
        ROLE_TEXT_TO_IMAGE: "IMAGE_GENERATION_TEXT_TO_IMAGE_URL",
        ROLE_PLATE_LOGO: "IMAGE_GENERATION_PLATE_LOGO_URL",
    }
    defaults = {
        ROLE_TEXT_TO_IMAGE: "http://image_generation_text_to_image:8095",
        ROLE_PLATE_LOGO: "http://image_generation_plate_logo:8096",
    }
    env_name = env_names.get(role, "")
    default = defaults.get(role, "")
    return os.getenv(env_name, default).strip().rstrip("/") or default


def worker_timeout(role: str) -> float:
    env_names = {
        ROLE_TEXT_TO_IMAGE: "IMAGE_GENERATION_TEXT_TO_IMAGE_TIMEOUT_SECONDS",
        ROLE_PLATE_LOGO: "IMAGE_GENERATION_PLATE_LOGO_TIMEOUT_SECONDS",
    }
    defaults = {
        ROLE_TEXT_TO_IMAGE: 600.0,
        ROLE_PLATE_LOGO: 120.0,
    }
    try:
        timeout = float(os.getenv(env_names.get(role, ""), str(defaults.get(role, 120.0))))
    except ValueError:
        timeout = defaults.get(role, 120.0)
    return timeout if timeout > 0 else defaults.get(role, 120.0)


def gateway_health_worker_timeout() -> float:
    try:
        timeout = float(os.getenv("IMAGE_GENERATION_WORKER_HEALTH_TIMEOUT_SECONDS", "0.35"))
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
        ROLE_TEXT_TO_IMAGE: "text_to_image_worker_unavailable",
        ROLE_PLATE_LOGO: "plate_logo_worker_unavailable",
    }
    default_messages = {
        ROLE_TEXT_TO_IMAGE: "Text-to-image worker is unavailable",
        ROLE_PLATE_LOGO: "Plate logo replacement worker is unavailable",
    }
    return {
        "code": codes.get(role, "image_generation_worker_unavailable"),
        "message": message or default_messages.get(role, "Image generation worker is unavailable"),
        "status_code": status_code,
    }


def merge_worker_response(response: dict[str, Any], role: str, payload: dict[str, Any]) -> None:
    worker_warnings = payload.get("warnings")
    if isinstance(worker_warnings, list):
        response["warnings"].extend([item for item in worker_warnings if isinstance(item, dict)])
    image = payload.get("image")
    if isinstance(image, dict):
        response["image"] = image
    placements = payload.get("placements")
    if role == ROLE_PLATE_LOGO and isinstance(placements, list):
        response["placements"] = [item for item in placements if isinstance(item, dict)]


def gateway_worker_generate(role: str, payload: dict[str, Any], tasks: list[str]) -> tuple[dict[str, Any] | None, int, str | None]:
    worker_payload = {**payload, "tasks": tasks}
    return http_json(
        worker_url(role) + "/v1/generate",
        method="POST",
        payload=worker_payload,
        timeout_seconds=worker_timeout(role),
    )


def generate(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    tasks, error = normalize_tasks(payload)
    if error:
        return error, 400
    disabled_error = disabled_task_error(tasks)
    if disabled_error:
        return disabled_error, 409

    if fake_mode():
        from .runtime import generate_local

        return generate_local(payload)

    response = empty_response(payload)
    tasks_by_role: dict[str, list[str]] = {}
    for task in tasks:
        role = TASK_ROLE.get(task)
        if role:
            tasks_by_role.setdefault(role, []).append(task)

    for role, role_tasks in tasks_by_role.items():
        worker_payload, status_code, error_message = gateway_worker_generate(role, payload, role_tasks)
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
        "service": "image_generation" if role == ROLE_GATEWAY else f"image_generation_{role}",
        "role": role,
        "version": SERVICE_VERSION,
        "fake_mode": fake_mode(),
    }
    if role == ROLE_GATEWAY:
        payload["enabled_workers"] = list(enabled_worker_roles())
        payload["enabled_tasks"] = sorted(enabled_tasks())
    if role == ROLE_GATEWAY and not fake_mode():
        payload["workers"] = {worker_role: worker_health(worker_role) for worker_role in enabled_worker_roles()}
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
    if role != ROLE_GATEWAY:
        return {"resources": resources_for_role(role)}
    if fake_mode():
        return {"resources": resources_for_roles(enabled_worker_roles())}
    resources: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for worker_role in enabled_worker_roles():
        worker_resources, warning = resources_from_worker(worker_role)
        resources.extend(worker_resources)
        if warning:
            warnings.append(warning)
    payload: dict[str, Any] = {"resources": resources}
    if warnings:
        payload["warnings"] = warnings
    return payload
