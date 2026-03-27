from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ...application.registry_management_service import (
    RegistryManagementRequestError,
    create_registry_entity_request,
    create_registry_entity_version_request,
    get_registry_entity_detail,
    list_registry_entities,
    list_registry_entity_shares,
    share_registry_entity_request,
)
from ...authz import require_auth
from ...config import get_auth_config

bp = Blueprint("registry_generic", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


@bp.get("/v1/registry/<entity_type>")
@require_auth
def list_entities_generic(entity_type: str):
    try:
        rows = list_registry_entities(_database_url(), entity_type=entity_type)
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify({"items": rows}), 200


@bp.get("/v1/registry/<entity_type>/<entity_id>")
@require_auth
def get_entity_generic(entity_type: str, entity_id: str):
    try:
        payload = get_registry_entity_detail(_database_url(), entity_type=entity_type, entity_id=entity_id)
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 200


@bp.post("/v1/registry/<entity_type>/<entity_id>/versions")
@require_auth
def create_entity_version_generic(entity_type: str, entity_id: str):
    try:
        payload = create_registry_entity_version_request(
            _database_url(),
            entity_type=entity_type,
            entity_id=entity_id,
            payload=request.get_json(silent=True),
            current_user=g.current_user,
        )
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 201


@bp.post("/v1/registry/<entity_type>/<entity_id>/share")
@require_auth
def share_entity_generic(entity_type: str, entity_id: str):
    try:
        share = share_registry_entity_request(
            _database_url(),
            entity_type=entity_type,
            entity_id=entity_id,
            payload=request.get_json(silent=True),
            current_user=g.current_user,
        )
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify({"share": share}), 201


@bp.get("/v1/registry/<entity_type>/<entity_id>/shares")
@require_auth
def list_shares_generic(entity_type: str, entity_id: str):
    try:
        rows = list_registry_entity_shares(_database_url(), entity_type=entity_type, entity_id=entity_id)
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify({"shares": rows}), 200


@bp.post("/v1/registry/<entity_type>")
@require_auth
def create_entity_generic(entity_type: str):
    try:
        payload = create_registry_entity_request(
            _database_url(),
            entity_type=entity_type,
            payload=request.get_json(silent=True),
            owner_user_id=int(g.current_user["id"]),
        )
    except RegistryManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 201
