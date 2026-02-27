from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..repositories.model_assignments import list_scope_assignments, upsert_scope_assignment
from ..repositories.model_access import (
    assign_model_access,
    find_model_definition,
    list_effective_allowed_models,
)

bp = Blueprint("model_governance_v1", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


def _serialize_model_definition(row: dict[str, object]) -> dict[str, object]:
    return {
        "model_id": row.get("model_id"),
        "provider": row.get("provider"),
        "metadata": row.get("metadata") or {},
        "provider_config_ref": row.get("provider_config_ref"),
    }


def _serialize_assignment(row: dict[str, object]) -> dict[str, object]:
    model_ids_raw = row.get("model_ids") or []
    return {
        "scope": row.get("scope"),
        "model_ids": [str(item) for item in model_ids_raw if str(item).strip()],
    }


@bp.get("/v1/model-governance/assignments")
@require_role("admin")
def list_assignments_v1():
    rows = list_scope_assignments(_database_url())
    return jsonify({"assignments": [_serialize_assignment(row) for row in rows]}), 200


@bp.put("/v1/model-governance/assignments")
@require_role("admin")
def update_assignment_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    scope = str(payload.get("scope", "")).strip().lower()
    model_ids = payload.get("model_ids")
    if not isinstance(model_ids, list):
        return _json_error(400, "invalid_model_ids", "model_ids must be an array")

    try:
        saved = upsert_scope_assignment(
            _database_url(),
            scope=scope,
            model_ids=[str(item) for item in model_ids],
            updated_by_user_id=int(g.current_user["id"]),
        )
    except ValueError:
        return _json_error(400, "invalid_scope", "scope must be user, admin, or superadmin")

    return jsonify({"assignment": _serialize_assignment(saved)}), 200


@bp.post("/v1/model-governance/access-assignments")
@require_role("admin")
def assign_access_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    model_id = str(payload.get("model_id", "")).strip()
    scope_type = str(payload.get("scope_type", "")).strip().lower()
    scope_id = str(payload.get("scope_id", "")).strip()
    if not model_id:
        return _json_error(400, "invalid_model_id", "model_id is required")
    if scope_type not in {"org", "group", "user"}:
        return _json_error(400, "invalid_scope_type", "scope_type must be org, group, or user")
    if not scope_id:
        return _json_error(400, "invalid_scope_id", "scope_id is required")

    if find_model_definition(_database_url(), model_id) is None:
        return _json_error(404, "model_not_found", "Model definition not found")

    assigned = assign_model_access(
        _database_url(),
        model_id=model_id,
        scope_type=scope_type,
        scope_id=scope_id,
        assigned_by_user_id=int(g.current_user["id"]),
    )
    return (
        jsonify(
            {
                "assignment": {
                    "model_id": assigned["model_id"],
                    "scope_type": assigned["scope_type"],
                    "scope_id": assigned["scope_id"],
                }
            }
        ),
        201,
    )


@bp.get("/v1/model-governance/allowed")
@require_role("user")
def list_allowed_models_v1():
    org_id = str(request.args.get("org_id", "")).strip() or None
    group_id = str(request.args.get("group_id", "")).strip() or None
    models = list_effective_allowed_models(
        _database_url(),
        user_id=int(g.current_user["id"]),
        org_id=org_id,
        group_id=group_id,
    )
    return jsonify({"models": [_serialize_model_definition(model) for model in models]}), 200


@bp.get("/v1/model-governance/enabled")
@require_role("user")
def list_enabled_models_v1():
    org_id = str(request.args.get("org_id", "")).strip() or None
    group_id = str(request.args.get("group_id", "")).strip() or None
    models = list_effective_allowed_models(
        _database_url(),
        user_id=int(g.current_user["id"]),
        org_id=org_id,
        group_id=group_id,
    )
    normalized = [
        {
            "id": str(model.get("model_id", "")),
            "name": str((model.get("metadata") or {}).get("name") or model.get("model_id", "")),
            "provider": model.get("provider"),
            "description": str((model.get("metadata") or {}).get("description", "")) or None,
        }
        for model in models
    ]
    return jsonify({"models": normalized}), 200
