from __future__ import annotations

from typing import Any, Callable

from ..repositories.policy_rules import (
    create_policy_rule as _create_policy_rule,
    list_policy_rules as _list_policy_rules,
)


class PolicyManagementRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def create_policy_rule_response(
    database_url: str,
    *,
    payload: Any,
    create_policy_rule_fn: Callable[..., dict[str, Any]] = _create_policy_rule,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PolicyManagementRequestError(
            status_code=400,
            code="invalid_payload",
            message="Expected JSON object",
        )

    scope_type = str(payload.get("scope_type", "")).strip().lower()
    scope_id = str(payload.get("scope_id", "")).strip()
    resource_type = str(payload.get("resource_type", "entity")).strip().lower() or "entity"
    resource_id = str(payload.get("resource_id", "")).strip()
    effect = str(payload.get("effect", "")).strip().lower()
    rule_json = payload.get("rule") if isinstance(payload.get("rule"), dict) else {}

    if not scope_type or not scope_id or not resource_id or not effect:
        raise PolicyManagementRequestError(
            status_code=400,
            code="invalid_policy_rule",
            message="scope_type, scope_id, resource_id and effect are required",
        )

    try:
        created = create_policy_rule_fn(
            database_url,
            scope_type=scope_type,
            scope_id=scope_id,
            resource_type=resource_type,
            resource_id=resource_id,
            effect=effect,
            rule_json=rule_json,
        )
    except ValueError as exc:
        raise PolicyManagementRequestError(
            status_code=400,
            code="invalid_policy_rule",
            message=str(exc),
        ) from exc

    return {"rule": created}


def list_policy_rules_response(
    database_url: str,
    *,
    args: Any,
    list_policy_rules_fn: Callable[..., list[dict[str, Any]]] = _list_policy_rules,
) -> dict[str, Any]:
    scope_type = str(args.get("scope_type", "")).strip().lower() or None
    scope_id = str(args.get("scope_id", "")).strip() or None
    rows = list_policy_rules_fn(
        database_url,
        scope_type=scope_type,
        scope_id=scope_id,
    )
    return {"rules": rows}
