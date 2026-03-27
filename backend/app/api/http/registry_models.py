from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ...application.registry_management_service import (
    RegistryManagementRequestError,
    create_registry_model_request,
    create_registry_model_version_request,
    get_registry_model_detail,
    list_registry_model_entities,
    list_registry_model_shares,
    share_registry_model_request,
)
from ...authz import require_role
from ...config import get_auth_config

bp = Blueprint("registry_models", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


@bp.get("/v1/registry/models")
@require_role("superadmin")
def list_model_entities():
    return jsonify({"items": list_registry_model_entities(_database_url())}), 200


@bp.get("/v1/registry/models/<entity_id>")
@require_role("superadmin")
def get_model_entity(entity_id: str):
    try:
        payload = get_registry_model_detail(_database_url(), entity_id=entity_id)
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 200


@bp.post("/v1/registry/models")
@require_role("superadmin")
def create_model_entity():
    try:
        payload = create_registry_model_request(
            _database_url(),
            payload=request.get_json(silent=True),
            owner_user_id=int(g.current_user["id"]),
        )
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 201


@bp.post("/v1/registry/models/<entity_id>/versions")
@require_role("superadmin")
def create_model_entity_version(entity_id: str):
    try:
        payload = create_registry_model_version_request(
            _database_url(),
            entity_id=entity_id,
            payload=request.get_json(silent=True),
            current_user=g.current_user,
        )
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 201


@bp.post("/v1/registry/models/<entity_id>/share")
@require_role("superadmin")
def share_model_entity(entity_id: str):
    try:
        share = share_registry_model_request(
            _database_url(),
            entity_id=entity_id,
            payload=request.get_json(silent=True),
            current_user=g.current_user,
        )
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify({"share": share}), 201


@bp.get("/v1/registry/models/<entity_id>/shares")
@require_role("superadmin")
def list_model_entity_shares(entity_id: str):
    try:
        rows = list_registry_model_shares(_database_url(), entity_id=entity_id)
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify({"shares": rows}), 200
