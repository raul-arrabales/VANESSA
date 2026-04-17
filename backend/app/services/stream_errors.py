from __future__ import annotations

from typing import Any


def public_stream_error_payload(
    payload: dict[str, Any] | None,
    *,
    fallback_error: str,
    fallback_message: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"error": fallback_error, "message": fallback_message}

    error_value = payload.get("error")
    if isinstance(error_value, dict):
        error_code = str(error_value.get("code") or fallback_error)
        message = str(error_value.get("message") or payload.get("message") or fallback_message)
    else:
        error_code = str(error_value or fallback_error)
        message = str(payload.get("message") or fallback_message)

    details: dict[str, Any] = {
        "error": error_code,
        "message": message,
    }
    status_code = _coerce_status_code(payload.get("status_code") or payload.get("upstream_status_code"))
    if status_code is not None:
        details["status_code"] = status_code
    upstream_error = _upstream_error_summary(payload)
    if upstream_error:
        details["upstream_error"] = upstream_error
    return details


def _upstream_error_summary(payload: dict[str, Any]) -> dict[str, Any] | None:
    error_value = payload.get("error")
    if isinstance(error_value, dict):
        return {
            key: str(error_value[key])
            for key in ("code", "type", "param")
            if error_value.get(key) is not None
        } or None
    return None


def _coerce_status_code(value: Any) -> int | None:
    try:
        status_code = int(value)
    except (TypeError, ValueError):
        return None
    return status_code if status_code > 0 else None
