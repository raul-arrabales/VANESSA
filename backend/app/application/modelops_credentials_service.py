from __future__ import annotations

from typing import Any

from ..repositories import modelops as modelops_repo
from ..repositories.model_credentials import (
    create_credential as _create_credential,
    list_credentials_for_user as _list_credentials_for_user,
    revoke_credential as _revoke_credential,
)
from ..services.modelops_common import ModelOpsError


def require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModelOpsError("invalid_payload", "Expected JSON object", status_code=400)
    return payload


def build_create_credential_request(payload: Any, *, current_user_id: int, actor_role: str) -> dict[str, Any]:
    body = require_json_object(payload)
    credential_scope = str(body.get("credential_scope", "personal")).strip().lower() or "personal"
    if credential_scope == "platform" and actor_role != "superadmin":
        raise ModelOpsError("forbidden", "Only superadmin can create platform credentials", status_code=403)

    owner_user_id = current_user_id if credential_scope == "personal" else int(body.get("owner_user_id", current_user_id))
    return {
        "owner_user_id": owner_user_id,
        "credential_scope": credential_scope,
        "provider_slug": str(body.get("provider", "openai_compatible")).strip().lower(),
        "display_name": str(body.get("display_name", "")).strip() or "credential",
        "api_base_url": str(body.get("api_base_url", "")).strip() or None,
        "api_key": str(body.get("api_key", "")).strip(),
    }


def list_credentials_for_user(database_url: str, *, requester_user_id: int, requester_role: str):
    return _list_credentials_for_user(
        database_url,
        requester_user_id=requester_user_id,
        requester_role=requester_role,
    )


def create_credential(database_url: str, **kwargs):
    try:
        return _create_credential(database_url, **kwargs)
    except ValueError as exc:
        if str(exc) == "duplicate_credential":
            raise ModelOpsError(
                "duplicate_credential",
                "A credential with this name already exists for the selected provider",
                status_code=409,
            ) from exc
        raise ModelOpsError(str(exc), "Invalid credential payload", status_code=400) from exc


def revoke_credential(database_url: str, *, credential_id: str, owner_user_id: int):
    try:
        revoked = _revoke_credential(
            database_url,
            credential_id=credential_id,
            owner_user_id=owner_user_id,
        )
    except ValueError as exc:
        raise ModelOpsError("invalid_credential_id", "credential_id must be a UUID", status_code=400) from exc
    if revoked is None:
        return None
    affected_models = modelops_repo.mark_models_for_revoked_credential(database_url, credential_id=credential_id)
    return {
        "credential": revoked,
        "affected_models": affected_models,
    }


def append_audit_event(database_url: str, **kwargs) -> None:
    modelops_repo.append_audit_event(database_url, **kwargs)
