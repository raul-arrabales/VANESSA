from __future__ import annotations

import json

from flask import Blueprint, Response, g, jsonify, request, stream_with_context

from ...application.runtime_profile_service_app import (
    RuntimeProfileRequestError,
    get_runtime_profile_state_response,
    update_runtime_profile_state_response,
)
from ...authz import require_auth, require_role
from ...services.cloud_traffic import publish_cloud_traffic_event, stream_cloud_traffic_events
from ...services.runtime_profile_service import RuntimeProfileLockedError
from ...services.runtime_profile_service import resolve_runtime_profile_state as _resolve_runtime_profile_state
from ...services.runtime_profile_service import update_runtime_profile as _update_runtime_profile

bp = Blueprint("runtime", __name__)

resolve_runtime_profile_state = _resolve_runtime_profile_state
update_runtime_profile = _update_runtime_profile


def _json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def _config():
    from ... import app as app_module

    return app_module._get_config()


def _database_url() -> str:
    return _config().database_url


@bp.get("/v1/runtime/profile")
@require_auth
def get_runtime_profile_route():
    payload = get_runtime_profile_state_response(
        _database_url(),
        resolve_runtime_profile_state_fn=resolve_runtime_profile_state,
    )
    return jsonify(payload), 200


@bp.put("/v1/runtime/profile")
@require_role("superadmin")
def set_runtime_profile_route():
    try:
        payload = update_runtime_profile_state_response(
            _database_url(),
            payload=request.get_json(silent=True),
            updated_by_user_id=int(g.current_user["id"]),
            update_runtime_profile_fn=update_runtime_profile,
        )
    except RuntimeProfileRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)

    return jsonify(payload), 200


@bp.get("/v1/runtime/cloud-traffic/events")
@require_auth
def stream_cloud_traffic_events_route():
    def _events():
        for event in stream_cloud_traffic_events():
            if event is None:
                yield ": keepalive\n\n"
                continue
            yield f"event: cloud_traffic\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"

    return Response(
        stream_with_context(_events()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@bp.post("/v1/internal/cloud-traffic/events")
def publish_internal_cloud_traffic_event_route():
    token = request.headers.get("X-Service-Token", "").strip()
    if not token or token != _config().agent_engine_service_token:
        return _json_error(401, "invalid_service_token", "Missing or invalid service token")
    try:
        event = publish_cloud_traffic_event(request.get_json(silent=True) or {}, config=_config())
    except ValueError as exc:
        return _json_error(400, "invalid_cloud_traffic_event", str(exc))
    return jsonify({"event": event}), 202


__all__ = [
    "bp",
    "_config",
    "_database_url",
    "_json_error",
    "RuntimeProfileLockedError",
    "resolve_runtime_profile_state",
    "update_runtime_profile",
]
