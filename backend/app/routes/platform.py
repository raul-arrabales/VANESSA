from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..authz import require_auth, require_role
from ..config import get_auth_config
from ..services.platform_service import (
    activate_deployment_profile,
    clone_deployment_profile,
    create_deployment_profile,
    create_provider,
    delete_deployment_profile,
    delete_provider,
    list_capabilities,
    list_deployment_activation_audit,
    list_deployment_profiles,
    list_provider_families,
    list_providers,
    update_deployment_profile,
    update_provider,
    validate_provider,
)
from ..services.platform_types import PlatformControlPlaneError
from ..services.vector_store_service import (
    delete_vector_documents,
    ensure_vector_index,
    query_vector_documents,
    upsert_vector_documents,
)

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


@bp.get("/v1/platform/provider-families")
@require_role("superadmin")
def get_platform_provider_families_route():
    try:
        provider_families = list_provider_families(_database_url(), _config())
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"provider_families": provider_families}), 200


@bp.post("/v1/platform/providers")
@require_role("superadmin")
def create_platform_provider_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        provider = create_provider(_database_url(), config=_config(), payload=payload)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"provider": provider}), 201


@bp.put("/v1/platform/providers/<provider_id>")
@require_role("superadmin")
def update_platform_provider_route(provider_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        provider = update_provider(_database_url(), config=_config(), provider_instance_id=provider_id, payload=payload)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"provider": provider}), 200


@bp.delete("/v1/platform/providers/<provider_id>")
@require_role("superadmin")
def delete_platform_provider_route(provider_id: str):
    try:
        delete_provider(_database_url(), config=_config(), provider_instance_id=provider_id)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deleted": True, "provider_id": provider_id}), 200


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


@bp.get("/v1/platform/activation-audit")
@require_role("superadmin")
def get_platform_activation_audit_route():
    try:
        audit_rows = list_deployment_activation_audit(_database_url(), _config())
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"activation_audit": audit_rows}), 200


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


@bp.put("/v1/platform/deployments/<deployment_profile_id>")
@require_role("superadmin")
def update_platform_deployment_route(deployment_profile_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        deployment = update_deployment_profile(
            _database_url(),
            config=_config(),
            deployment_profile_id=deployment_profile_id,
            payload=payload,
            updated_by_user_id=int(g.current_user["id"]),
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deployment_profile": deployment}), 200


@bp.post("/v1/platform/deployments/<deployment_profile_id>/clone")
@require_role("superadmin")
def clone_platform_deployment_route(deployment_profile_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        deployment = clone_deployment_profile(
            _database_url(),
            config=_config(),
            source_deployment_profile_id=deployment_profile_id,
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


@bp.delete("/v1/platform/deployments/<deployment_profile_id>")
@require_role("superadmin")
def delete_platform_deployment_route(deployment_profile_id: str):
    try:
        delete_deployment_profile(
            _database_url(),
            config=_config(),
            deployment_profile_id=deployment_profile_id,
        )
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deleted": True, "deployment_profile_id": deployment_profile_id}), 200


@bp.post("/v1/platform/vector/indexes/ensure")
@require_role("superadmin")
def ensure_platform_vector_index_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        result = ensure_vector_index(_database_url(), _config(), payload)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(result), 200


@bp.post("/v1/platform/vector/documents/upsert")
@require_role("superadmin")
def upsert_platform_vector_documents_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        result = upsert_vector_documents(_database_url(), _config(), payload)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(result), 200


@bp.post("/v1/platform/vector/query")
@require_role("superadmin")
def query_platform_vector_documents_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        result = query_vector_documents(_database_url(), _config(), payload)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(result), 200


@bp.post("/v1/platform/vector/documents/delete")
@require_role("superadmin")
def delete_platform_vector_documents_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        result = delete_vector_documents(_database_url(), _config(), payload)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(result), 200
