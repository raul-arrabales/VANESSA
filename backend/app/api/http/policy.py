from __future__ import annotations

from flask import Blueprint, jsonify, request

from ...application.policy_management_service import (
    PolicyManagementRequestError,
    create_policy_rule_response,
    list_policy_rules_response,
)
from ...authz import require_role
from ...config import get_auth_config
from ...repositories.policy_rules import create_policy_rule as _create_policy_rule
from ...repositories.policy_rules import list_policy_rules as _list_policy_rules

bp = Blueprint("policy", __name__)

create_policy_rule = _create_policy_rule
list_policy_rules = _list_policy_rules


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


@bp.post("/v1/policy/rules")
@require_role("superadmin")
def create_policy_rule_route():
    try:
        payload = create_policy_rule_response(
            _database_url(),
            payload=request.get_json(silent=True),
            create_policy_rule_fn=create_policy_rule,
        )
    except PolicyManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)

    return jsonify(payload), 201


@bp.get("/v1/policy/rules")
@require_role("superadmin")
def list_policy_rules_route():
    payload = list_policy_rules_response(
        _database_url(),
        args=request.args,
        list_policy_rules_fn=list_policy_rules,
    )
    return jsonify(payload), 200


__all__ = [
    "bp",
    "_database_url",
    "_json_error",
    "create_policy_rule",
    "list_policy_rules",
]
