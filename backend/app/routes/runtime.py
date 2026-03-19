from __future__ import annotations

from flask import Blueprint, jsonify, g, request

from ..authz import require_auth, require_role
from ..config import get_auth_config
from ..services.runtime_profile_service import (
    RuntimeProfileLockedError,
    resolve_runtime_profile_state,
    update_runtime_profile,
)

bp = Blueprint("runtime", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


def _serialize_runtime_profile_state(state):
    return {
        "profile": state.profile,
        "locked": state.locked,
        "source": state.source,
    }


@bp.get("/v1/runtime/profile")
@require_auth
def get_runtime_profile_route():
    state = resolve_runtime_profile_state(_database_url())
    return jsonify(_serialize_runtime_profile_state(state)), 200


@bp.put("/v1/runtime/profile")
@require_role("superadmin")
def set_runtime_profile_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    profile = str(payload.get("profile", "")).strip().lower()
    if not profile:
        return _json_error(400, "invalid_profile", "profile is required")

    try:
        updated = update_runtime_profile(
            _database_url(),
            profile=profile,
            updated_by_user_id=int(g.current_user["id"]),
        )
    except RuntimeProfileLockedError as exc:
        return _json_error(409, "runtime_profile_locked", str(exc))
    except ValueError as exc:
        return _json_error(400, "invalid_profile", str(exc))

    return jsonify({"profile": updated, "locked": False, "source": "database"}), 200
