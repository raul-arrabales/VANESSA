from __future__ import annotations

from typing import Any

from ..repositories.registry import create_share_grant, list_share_grants
from .policy_service import PolicyDeniedError, can_manage_entity


def grant_share(
    database_url: str,
    *,
    current_user: dict[str, Any],
    entity: dict[str, Any],
    grantee_type: str,
    grantee_id: str | None,
    permission: str,
) -> dict[str, Any]:
    if not can_manage_entity(current_user=current_user, owner_user_id=entity.get("owner_user_id")):
        raise PolicyDeniedError("Only entity owner or superadmin can share this entity")

    return create_share_grant(
        database_url,
        entity_id=str(entity["entity_id"]),
        grantee_type=grantee_type,
        grantee_id=grantee_id,
        permission=permission,
        shared_by_user_id=int(current_user["id"]),
    )


def get_shares(database_url: str, *, entity_id: str) -> list[dict[str, Any]]:
    return list_share_grants(database_url, entity_id=entity_id)
