from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ...application.runtime_profile_service_app import (
    RuntimeProfileRequestError,
    get_runtime_profile_state_response,
    update_runtime_profile_state_response,
)
from ...authz import require_auth, require_role
from ...config import get_auth_config
from ...services.runtime_profile_service import RuntimeProfileLockedError
from ...services.runtime_profile_service import resolve_runtime_profile_state as _resolve_runtime_profile_state
from ...services.runtime_profile_service import update_runtime_profile as _update_runtime_profile

bp = Blueprint("runtime", __name__)

resolve_runtime_profile_state = _resolve_runtime_profile_state
update_runtime_profile = _update_runtime_profile


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _config():
    return get_auth_config()


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
        return _json_error(exc.status_code, exc.code, exc.message)

    return jsonify(payload), 200


__all__ = [
    "bp",
    "_config",
    "_database_url",
    "_json_error",
    "RuntimeProfileLockedError",
    "resolve_runtime_profile_state",
    "update_runtime_profile",
]
