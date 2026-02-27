from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("system_v1", __name__)


@bp.get("/v1/system/ping")
def system_ping_v1():
    return jsonify({"status": "ok", "service": "backend", "api": "v1"}), 200
