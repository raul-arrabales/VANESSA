from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..authz import require_auth, require_role
from ..config import get_auth_config
from ..services.platform_service import (
    activate_deployment_profile,
    create_deployment_profile,
    list_capabilities,
    list_deployment_profiles,
    list_providers,
    validate_provider,
)
from ..services.platform_types import PlatformControlPlaneError

bp = Blueprint("platform", __name__)


def _json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def _config():
    return get_auth_config()


def _database_url() -> str:
    return _config().database_url


@bp.get("/v1/platform/capabilities")
@require_auth
def get_platform_capabilities_route():
    try:
        capabilities = list_capabilities(_database_url(), _config())
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"capabilities": capabilities}), 200


@bp.get("/v1/platform/providers")
@require_role("superadmin")
def get_platform_providers_route():
    try:
        providers = list_providers(_database_url(), _config())
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"providers": providers}), 200


@bp.post("/v1/platform/providers/<provider_id>/validate")
@require_role("superadmin")
def validate_platform_provider_route(provider_id: str):
    try:
        payload = validate_provider(_database_url(), config=_config(), provider_instance_id=provider_id)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.get("/v1/platform/deployments")
@require_role("superadmin")
def get_platform_deployments_route():
    try:
        deployments = list_deployment_profiles(_database_url(), _config())
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deployments": deployments}), 200


@bp.post("/v1/platform/deployments")
@require_role("superadmin")
def create_platform_deployment_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        deployment = create_deployment_profile(
            _database_url(),
            config=_config(),
            payload=payload,
            created_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deployment_profile": deployment}), 201


@bp.post("/v1/platform/deployments/<deployment_profile_id>/activate")
@require_role("superadmin")
def activate_platform_deployment_route(deployment_profile_id: str):
    try:
        deployment = activate_deployment_profile(
            _database_url(),
            config=_config(),
            deployment_profile_id=deployment_profile_id,
            activated_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deployment_profile": deployment}), 200
