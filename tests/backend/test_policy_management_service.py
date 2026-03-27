from __future__ import annotations

import pytest

from app.application import policy_management_service


def test_create_policy_rule_requires_core_fields() -> None:
    with pytest.raises(policy_management_service.PolicyManagementRequestError) as exc_info:
        policy_management_service.create_policy_rule_response(
            "postgresql://ignored",
            payload={"scope_type": "user"},
        )

    assert exc_info.value.code == "invalid_policy_rule"


def test_list_policy_rules_normalizes_scope_filters() -> None:
    captured: dict[str, object] = {}

    def _list_policy_rules(_database_url: str, *, scope_type: str | None, scope_id: str | None):
        captured["scope_type"] = scope_type
        captured["scope_id"] = scope_id
        return [{"id": 1, "scope_type": scope_type, "scope_id": scope_id}]

    payload = policy_management_service.list_policy_rules_response(
        "postgresql://ignored",
        args={"scope_type": " USER ", "scope_id": " 7 "},
        list_policy_rules_fn=_list_policy_rules,
    )

    assert captured == {"scope_type": "user", "scope_id": "7"}
    assert payload["rules"][0]["scope_type"] == "user"
