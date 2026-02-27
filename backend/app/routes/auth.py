from __future__ import annotations

from flask import Blueprint, jsonify, g

from ..authz import require_auth

bp = Blueprint("auth_v1", __name__)


@bp.get("/v1/auth/me")
@require_auth
def auth_me_v1():
    user = g.current_user
    return jsonify({
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "role": user["role"],
            "is_active": user["is_active"],
        }
    }), 200
