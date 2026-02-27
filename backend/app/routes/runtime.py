from __future__ import annotations

from flask import Blueprint, jsonify, g, request

from ..authz import require_role
from ..config import get_auth_config
from ..services.runtime_profile_service import resolve_runtime_profile, update_runtime_profile

bp = Blueprint("runtime", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


@bp.get("/v1/runtime/profile")
def get_runtime_profile_route():
    profile = resolve_runtime_profile(_database_url())
    return jsonify({"profile": profile}), 200


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
    except ValueError as exc:
        return _json_error(400, "invalid_profile", str(exc))

    return jsonify({"profile": updated}), 200
