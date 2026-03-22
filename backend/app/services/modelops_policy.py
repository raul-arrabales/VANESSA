from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from .modelops_common import ModelOpsError
from .runtime_profile_service import resolve_runtime_profile


def can_manage_model(row: dict[str, Any], *, actor_user_id: int, actor_role: str, action: str) -> None:
    normalized_role = actor_role.strip().lower()
    owner_type = str(row.get("owner_type", "")).strip().lower() or modelops_repo.infer_owner_type(row)
    owner_user_id = int(row.get("owner_user_id") or 0)
    is_owned_by_actor = owner_type == modelops_repo.OWNER_USER and owner_user_id == actor_user_id

    if normalized_role == "superadmin":
        return
    if normalized_role == "admin":
        if action in {"validate", "activate", "deactivate"}:
            return
        if action in {"list", "read"}:
            return
        raise ModelOpsError("forbidden", "Admins cannot perform this model lifecycle action", status_code=403)
    if normalized_role == "user":
        if is_owned_by_actor and action in {"read", "activate", "deactivate", "delete", "unregister"}:
            return
        if is_owned_by_actor and action == "create":
            return
    raise ModelOpsError("forbidden", "You do not have access to this model action", status_code=403)


def get_accessible_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = modelops_repo.get_model(database_url, model_id)
    if row is None:
        raise ModelOpsError("not_found", "Model not found", status_code=404)
    if actor_role == "superadmin":
        return row

    runtime_profile = resolve_runtime_profile(database_url)
    visible_models = modelops_repo.list_models_for_actor(
        database_url,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        runtime_profile=runtime_profile,
        require_active=False,
    )
    if not any(str(item.get("model_id")) == model_id.strip() for item in visible_models):
        raise ModelOpsError("not_found", "Model not found", status_code=404)
    return row
