from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..repositories.policy_rules import create_policy_rule, list_policy_rules

bp = Blueprint("policy", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


@bp.post("/v1/policy/rules")
@require_role("superadmin")
def create_policy_rule_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    scope_type = str(payload.get("scope_type", "")).strip().lower()
    scope_id = str(payload.get("scope_id", "")).strip()
    resource_type = str(payload.get("resource_type", "entity")).strip().lower() or "entity"
    resource_id = str(payload.get("resource_id", "")).strip()
    effect = str(payload.get("effect", "")).strip().lower()
    rule_json = payload.get("rule") if isinstance(payload.get("rule"), dict) else {}

    if not scope_type or not scope_id or not resource_id or not effect:
        return _json_error(400, "invalid_policy_rule", "scope_type, scope_id, resource_id and effect are required")

    try:
        created = create_policy_rule(
            get_auth_config().database_url,
            scope_type=scope_type,
            scope_id=scope_id,
            resource_type=resource_type,
            resource_id=resource_id,
            effect=effect,
            rule_json=rule_json,
        )
    except ValueError as exc:
        return _json_error(400, "invalid_policy_rule", str(exc))

    return jsonify({"rule": created}), 201


@bp.get("/v1/policy/rules")
@require_role("superadmin")
def list_policy_rules_route():
    scope_type = str(request.args.get("scope_type", "")).strip().lower() or None
    scope_id = str(request.args.get("scope_id", "")).strip() or None
    rows = list_policy_rules(
        get_auth_config().database_url,
        scope_type=scope_type,
        scope_id=scope_id,
    )
    return jsonify({"rules": rows}), 200
