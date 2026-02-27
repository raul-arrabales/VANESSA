from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..authz import require_auth
from ..config import get_auth_config
from ..services.policy_service import PolicyDeniedError, can_manage_entity
from ..services.registry_service import (
    create_entity_version,
    create_entity_with_version,
    get_entity,
    get_entity_versions,
    list_entities,
)
from ..services.sharing_service import get_shares, grant_share

bp = Blueprint("registry_generic", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


def _validate_non_model_entity_type(entity_type: str):
    normalized = entity_type.strip().lower()
    if normalized in {"model", "models"}:
        raise ValueError("invalid_entity_type")


@bp.get("/v1/registry/<entity_type>")
@require_auth
def list_entities_generic(entity_type: str):
    try:
        _validate_non_model_entity_type(entity_type)
        rows = list_entities(_database_url(), entity_type=entity_type)
    except ValueError as exc:
        return _json_error(400, "invalid_entity_type", str(exc))
    return jsonify({"items": rows}), 200


@bp.get("/v1/registry/<entity_type>/<entity_id>")
@require_auth
def get_entity_generic(entity_type: str, entity_id: str):
    try:
        _validate_non_model_entity_type(entity_type)
        entity = get_entity(_database_url(), entity_type=entity_type, entity_id=entity_id)
    except ValueError as exc:
        return _json_error(400, "invalid_entity_type", str(exc))

    if entity is None:
        return _json_error(404, "entity_not_found", "Entity not found")
    return jsonify({"entity": entity, "versions": get_entity_versions(_database_url(), entity_id=entity_id)}), 200


@bp.post("/v1/registry/<entity_type>/<entity_id>/versions")
@require_auth
def create_entity_version_generic(entity_type: str, entity_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    version = str(payload.get("version", "")).strip()
    spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else {}
    publish = bool(payload.get("publish", False))
    if not version:
        return _json_error(400, "invalid_version", "version is required")

    try:
        _validate_non_model_entity_type(entity_type)
        entity = get_entity(_database_url(), entity_type=entity_type, entity_id=entity_id)
    except ValueError as exc:
        return _json_error(400, "invalid_entity_type", str(exc))

    if entity is None:
        return _json_error(404, "entity_not_found", "Entity not found")

    if not can_manage_entity(current_user=g.current_user, owner_user_id=entity.get("owner_user_id")):
        return _json_error(403, "insufficient_role", "Only owner or superadmin can create versions")

    try:
        created = create_entity_version(
            _database_url(),
            entity_type=entity_type,
            entity_id=entity_id,
            version=version,
            spec=spec,
            publish=publish,
        )
    except LookupError:
        return _json_error(404, "entity_not_found", "Entity not found")
    except ValueError as exc:
        return _json_error(400, "invalid_version_payload", str(exc))

    return jsonify(created), 201


@bp.post("/v1/registry/<entity_type>/<entity_id>/share")
@require_auth
def share_entity_generic(entity_type: str, entity_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        _validate_non_model_entity_type(entity_type)
        entity = get_entity(_database_url(), entity_type=entity_type, entity_id=entity_id)
    except ValueError as exc:
        return _json_error(400, "invalid_entity_type", str(exc))

    if entity is None:
        return _json_error(404, "entity_not_found", "Entity not found")

    grantee_type = str(payload.get("grantee_type", "")).strip().lower()
    grantee_id_raw = payload.get("grantee_id")
    grantee_id = str(grantee_id_raw).strip() if grantee_id_raw is not None else None
    permission = str(payload.get("permission", "view")).strip().lower()

    try:
        share = grant_share(
            _database_url(),
            current_user=g.current_user,
            entity=entity,
            grantee_type=grantee_type,
            grantee_id=grantee_id,
            permission=permission,
        )
    except PolicyDeniedError as exc:
        return _json_error(403, "policy_denied", str(exc))
    except ValueError as exc:
        return _json_error(400, "invalid_share", str(exc))

    return jsonify({"share": share}), 201


@bp.get("/v1/registry/<entity_type>/<entity_id>/shares")
@require_auth
def list_shares_generic(entity_type: str, entity_id: str):
    try:
        _validate_non_model_entity_type(entity_type)
        entity = get_entity(_database_url(), entity_type=entity_type, entity_id=entity_id)
    except ValueError as exc:
        return _json_error(400, "invalid_entity_type", str(exc))

    if entity is None:
        return _json_error(404, "entity_not_found", "Entity not found")

    rows = get_shares(_database_url(), entity_id=entity_id)
    return jsonify({"shares": rows}), 200


@bp.post("/v1/registry/<entity_type>")
@require_auth
def create_entity_generic(entity_type: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    entity_id = str(payload.get("id", "")).strip()
    version = str(payload.get("version", "v1")).strip() or "v1"
    visibility = str(payload.get("visibility", "private")).strip().lower() or "private"
    publish = bool(payload.get("publish", False))
    spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else {}

    if not entity_id:
        return _json_error(400, "invalid_entity_id", "id is required")

    try:
        _validate_non_model_entity_type(entity_type)
        created = create_entity_with_version(
            _database_url(),
            entity_type=entity_type,
            entity_id=entity_id,
            owner_user_id=int(g.current_user["id"]),
            visibility=visibility,
            spec=spec,
            version=version,
            publish=publish,
        )
    except ValueError as exc:
        return _json_error(400, "invalid_entity", str(exc))
    except Exception as exc:  # noqa: BLE001
        text = str(exc)
        if "duplicate" in text.lower() or "unique" in text.lower():
            return _json_error(409, "duplicate_entity", "Entity already exists")
        return _json_error(500, "create_entity_failed", text)

    return jsonify(created), 201
