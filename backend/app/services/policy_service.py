from __future__ import annotations

from typing import Any

from ..repositories.policy_rules import evaluate_policy
from ..repositories.registry import list_entity_permissions_for_user


class PolicyDeniedError(RuntimeError):
    pass


def can_manage_entity(*, current_user: dict[str, Any], owner_user_id: int | None) -> bool:
    role = str(current_user.get("role", "user")).strip().lower()
    if role == "superadmin":
        return True
    if owner_user_id is None:
        return False
    return int(current_user.get("id", -1)) == int(owner_user_id)


def require_entity_permission(
    *,
    database_url: str,
    current_user: dict[str, Any],
    entity_id: str,
    required_permission: str,
) -> None:
    role = str(current_user.get("role", "user")).strip().lower()
    if role == "superadmin":
        return

    action = required_permission.strip().lower()
    decision = evaluate_policy(
        database_url,
        user_id=int(current_user["id"]),
        resource_type="entity",
        resource_id=entity_id,
        action=action,
    )
    if decision == "deny":
        raise PolicyDeniedError(f"Policy denies action '{action}' for entity '{entity_id}'")

    permissions = list_entity_permissions_for_user(
        database_url,
        entity_id=entity_id,
        user_id=int(current_user["id"]),
    )
    if "admin" in permissions:
        return

    if action in permissions:
        return

    # Explicit allow can grant access even if share/ownership does not.
    if decision == "allow":
        return

    raise PolicyDeniedError(f"Missing permission '{required_permission}' for entity '{entity_id}'")
