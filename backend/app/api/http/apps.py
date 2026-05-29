from __future__ import annotations

from flask import Blueprint, jsonify

from ...application.apps_service import get_published_app, list_published_apps
from ...authz import require_role
from ...config import get_auth_config

bp = Blueprint("apps", __name__)


def _database_url() -> str:
    return get_auth_config().database_url


@bp.get("/v1/apps")
@require_role("user")
def list_apps_route():
    return jsonify({"apps": list_published_apps(_database_url())}), 200


@bp.get("/v1/apps/<app_id>")
@require_role("user")
def get_app_route(app_id: str):
    app = get_published_app(_database_url(), app_id=app_id)
    if app is None:
        return jsonify({"error": "app_not_found", "message": "App not found"}), 404
    return jsonify({"app": app}), 200
