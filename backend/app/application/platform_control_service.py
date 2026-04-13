from __future__ import annotations

from typing import Any

from ..services.embeddings_service import embed_platform_inputs as _embed_platform_inputs
from ..services.platform_service import (
    activate_deployment_profile as _activate_deployment_profile,
    assign_provider_loaded_model as _assign_provider_loaded_model,
    clear_provider_loaded_model as _clear_provider_loaded_model,
    clone_deployment_profile as _clone_deployment_profile,
    create_deployment_profile as _create_deployment_profile,
    create_provider as _create_provider,
    delete_deployment_profile as _delete_deployment_profile,
    delete_provider as _delete_provider,
    list_capabilities as _list_capabilities,
    list_deployment_activation_audit as _list_deployment_activation_audit,
    list_deployment_profiles as _list_deployment_profiles,
    list_provider_families as _list_provider_families,
    list_providers as _list_providers,
    update_deployment_profile as _update_deployment_profile,
    update_deployment_profile_identity as _update_deployment_profile_identity,
    update_provider as _update_provider,
    upsert_deployment_profile_binding as _upsert_deployment_profile_binding,
    validate_provider as _validate_provider,
)
from ..services.vector_store_service import (
    delete_vector_documents as _delete_vector_documents,
    ensure_vector_index as _ensure_vector_index,
    query_vector_documents as _query_vector_documents,
    upsert_vector_documents as _upsert_vector_documents,
)


class PlatformControlRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PlatformControlRequestError(status_code=400, code="invalid_payload", message="Expected JSON object")
    return payload


def list_platform_capabilities(database_url: str, config):
    return _list_capabilities(database_url, config)


def list_platform_providers(database_url: str, config):
    return _list_providers(database_url, config)


def list_platform_provider_families(database_url: str, config):
    return _list_provider_families(database_url, config)


def create_platform_provider(database_url: str, *, config, payload: Any):
    return _create_provider(database_url, config=config, payload=_require_json_object(payload))


def update_platform_provider(database_url: str, *, config, provider_instance_id: str, payload: Any):
    return _update_provider(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
        payload=_require_json_object(payload),
    )


def delete_platform_provider(database_url: str, *, config, provider_instance_id: str) -> None:
    _delete_provider(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
    )


def validate_platform_provider(
    database_url: str,
    *,
    config,
    provider_instance_id: str,
    payload: Any | None = None,
    actor_user_id: int | None = None,
    actor_role: str = "user",
):
    body = _require_json_object(payload if payload is not None else {})
    return _validate_provider(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
        credential_id=str(body.get("credential_id", "")).strip() or None,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )


def assign_platform_provider_loaded_model(database_url: str, *, config, provider_instance_id: str, payload: Any):
    body = _require_json_object(payload)
    managed_model_id = str(body.get("managed_model_id", "")).strip()
    return _assign_provider_loaded_model(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
        managed_model_id=managed_model_id,
    )


def clear_platform_provider_loaded_model(database_url: str, *, config, provider_instance_id: str):
    return _clear_provider_loaded_model(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
    )


def list_platform_deployments(database_url: str, config):
    return _list_deployment_profiles(database_url, config)


def list_platform_activation_audit(database_url: str, config):
    return _list_deployment_activation_audit(database_url, config)


def create_platform_deployment(database_url: str, *, config, payload: Any, created_by_user_id: int):
    return _create_deployment_profile(
        database_url,
        config=config,
        payload=_require_json_object(payload),
        created_by_user_id=created_by_user_id,
    )


def update_platform_deployment(
    database_url: str,
    *,
    config,
    deployment_profile_id: str,
    payload: Any,
    updated_by_user_id: int,
):
    return _update_deployment_profile(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
        payload=_require_json_object(payload),
        updated_by_user_id=updated_by_user_id,
    )


def update_platform_deployment_identity(
    database_url: str,
    *,
    config,
    deployment_profile_id: str,
    payload: Any,
    updated_by_user_id: int,
):
    return _update_deployment_profile_identity(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
        payload=_require_json_object(payload),
        updated_by_user_id=updated_by_user_id,
    )


def upsert_platform_deployment_binding(
    database_url: str,
    *,
    config,
    deployment_profile_id: str,
    capability_key: str,
    payload: Any,
    updated_by_user_id: int,
):
    return _upsert_deployment_profile_binding(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
        capability_key=capability_key,
        payload=_require_json_object(payload),
        updated_by_user_id=updated_by_user_id,
    )


def clone_platform_deployment(
    database_url: str,
    *,
    config,
    source_deployment_profile_id: str,
    payload: Any,
    created_by_user_id: int,
):
    return _clone_deployment_profile(
        database_url,
        config=config,
        source_deployment_profile_id=source_deployment_profile_id,
        payload=_require_json_object(payload),
        created_by_user_id=created_by_user_id,
    )


def activate_platform_deployment(
    database_url: str,
    *,
    config,
    deployment_profile_id: str,
    activated_by_user_id: int,
):
    return _activate_deployment_profile(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
        activated_by_user_id=activated_by_user_id,
    )


def delete_platform_deployment(database_url: str, *, config, deployment_profile_id: str) -> None:
    _delete_deployment_profile(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
    )


def ensure_platform_vector_index(database_url: str, config, payload: Any):
    return _ensure_vector_index(database_url, config, _require_json_object(payload))


def embed_platform_inputs_request(database_url: str, config, payload: Any):
    return _embed_platform_inputs(database_url, config, _require_json_object(payload))


def upsert_platform_vector_documents(database_url: str, config, payload: Any):
    return _upsert_vector_documents(database_url, config, _require_json_object(payload))


def query_platform_vector_documents(database_url: str, config, payload: Any):
    return _query_vector_documents(database_url, config, _require_json_object(payload))


def delete_platform_vector_documents(database_url: str, config, payload: Any):
    return _delete_vector_documents(database_url, config, _require_json_object(payload))
