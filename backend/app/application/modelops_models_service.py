from __future__ import annotations

from typing import Any

from ..services.modelops_common import ModelOpsError
from ..services.modelops_lifecycle import (
    activate_model as _activate_model,
    create_model as _create_model,
    deactivate_model as _deactivate_model,
    delete_model as _delete_model,
    register_existing_model as _register_existing_model,
    unregister_model as _unregister_model,
    update_model_credential as _update_model_credential,
)
from ..services.modelops_queries import (
    get_model_detail as _get_model_detail,
    get_model_usage as _get_model_usage,
    get_model_validations as _get_model_validations,
    list_models as _list_models,
)


def require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModelOpsError("invalid_payload", "Expected JSON object", status_code=400)
    return payload


def parse_capability_key(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized or None


def parse_eligible_only(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def parse_update_credential_request(payload: Any) -> str:
    body = require_json_object(payload)
    credential_id = str(body.get("credential_id", "")).strip()
    if not credential_id:
        raise ModelOpsError("missing_config", "credential_id is required", status_code=400)
    return credential_id


def parse_limit(value: Any, *, default: int, minimum: int, maximum: int, error_code: str = "invalid_limit") -> int:
    raw_value = str(value if value is not None else default).strip() or str(default)
    try:
        return max(minimum, min(maximum, int(raw_value)))
    except ValueError as exc:
        raise ModelOpsError(error_code, "limit must be an integer", status_code=400) from exc


def list_models(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    require_active: bool = False,
    capability_key: str | None = None,
):
    return _list_models(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        require_active=require_active,
        capability_key=capability_key,
    )


def create_model(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    payload: Any,
):
    return _create_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        payload=require_json_object(payload),
    )


def get_model_detail(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
):
    return _get_model_detail(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )


def get_model_usage(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
):
    return _get_model_usage(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )


def get_model_validations(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    limit: int = 20,
):
    return _get_model_validations(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
        limit=limit,
    )


def register_existing_model(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
):
    return _register_existing_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )


def activate_model(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
):
    return _activate_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )


def deactivate_model(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
):
    return _deactivate_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )


def unregister_model(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
):
    return _unregister_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )


def update_model_credential(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    credential_id: str,
):
    return _update_model_credential(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
        credential_id=credential_id,
    )


def delete_model(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> None:
    _delete_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
