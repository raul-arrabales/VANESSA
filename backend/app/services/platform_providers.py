from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..config import AuthConfig
from ..repositories import platform_control_plane as platform_repo
from ..repositories.model_credentials import get_active_credential_secret
from .platform_bindings import (
    _adapter_from_binding,
    _coerce_provider_input,
    _list_adapter_resources,
    _provider_storage_config,
    _validate_provider_binding,
)
from .platform_bootstrap import ensure_platform_bootstrap_state
from .platform_local_slots import assign_provider_loaded_model as _assign_provider_loaded_model
from .platform_local_slots import clear_provider_loaded_model as _clear_provider_loaded_model
from .platform_local_slots import _is_local_model_slot_provider
from .provider_origin_policy import assert_provider_allowed_for_current_runtime
from .platform_runtime import (
    resolve_mcp_runtime_adapter,
    resolve_sandbox_execution_adapter,
    resolve_vector_store_adapter,
)
from .platform_serialization import _serialize_binding_resource, _serialize_provider_family_row, _serialize_provider_row
from .platform_types import (
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_MCP_RUNTIME,
    CAPABILITY_SANDBOX_EXECUTION,
    CAPABILITY_VECTOR_STORE,
    PlatformControlPlaneError,
    ProviderBinding,
)

_OPENAI_COMPATIBLE_CLOUD_PROVIDER_KEYS = {
    "openai_compatible_cloud_llm",
    "openai_compatible_cloud_embeddings",
}
_OPENAI_COMPATIBLE_CREDENTIAL_PROVIDERS = {"openai", "openai_compatible"}
_OPENAI_DEFAULT_API_BASE_URL = "https://api.openai.com/v1"


def list_capabilities(database_url: str, config: AuthConfig) -> list[dict[str, Any]]:
    ensure_platform_bootstrap_state(database_url, config)
    active_by_capability: dict[str, dict[str, Any]] = {}
    for row in platform_repo.list_capabilities(database_url):
        capability_key = str(row["capability_key"]).strip().lower()
        try:
            active_row = platform_repo.get_active_binding_for_capability(database_url, capability_key=capability_key)
        except ValueError:
            active_row = None
        if active_row is not None:
            active_by_capability[capability_key] = active_row

    items: list[dict[str, Any]] = []
    for row in platform_repo.list_capabilities(database_url):
        capability_key = str(row["capability_key"])
        active_binding = active_by_capability.get(capability_key)
        items.append(
            {
                "capability": capability_key,
                "display_name": row["display_name"],
                "description": row["description"],
                "required": bool(row["is_required"]),
                "active_provider": (
                    {
                        "id": str(active_binding["provider_instance_id"]),
                        "slug": active_binding["provider_slug"],
                        "provider_key": active_binding["provider_key"],
                        "provider_origin": active_binding.get("provider_origin") or "local",
                        "display_name": active_binding["provider_display_name"],
                        "deployment_profile_id": str(active_binding["deployment_profile_id"]),
                        "deployment_profile_slug": active_binding["deployment_profile_slug"],
                    }
                    if active_binding is not None
                    else None
                ),
            }
        )
    return items


def list_providers(database_url: str, config: AuthConfig) -> list[dict[str, Any]]:
    ensure_platform_bootstrap_state(database_url, config)
    return [_serialize_provider_row(row) for row in platform_repo.list_provider_instances(database_url)]


def list_provider_families(database_url: str, config: AuthConfig) -> list[dict[str, Any]]:
    ensure_platform_bootstrap_state(database_url, config)
    return [_serialize_provider_family_row(row) for row in platform_repo.list_provider_families(database_url)]


def create_provider(database_url: str, *, config: AuthConfig, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    normalized = _coerce_provider_input(database_url, payload, is_update=False)
    try:
        created = platform_repo.create_provider_instance(
            database_url,
            slug=normalized["slug"],
            provider_key=normalized["provider_key"],
            display_name=normalized["display_name"],
            description=normalized["description"],
            endpoint_url=normalized["endpoint_url"],
            healthcheck_url=normalized["healthcheck_url"],
            enabled=normalized["enabled"],
            config_json=_provider_storage_config(normalized["config"], normalized["secret_refs"]),
        )
    except Exception as exc:
        message = str(exc).lower()
        if "duplicate key value violates unique constraint" in message:
            raise PlatformControlPlaneError(
                "provider_instance_exists",
                "Provider instance slug already exists",
                status_code=409,
            ) from exc
        raise
    return _serialize_provider_row({**(platform_repo.get_provider_instance(database_url, str(created["id"])) or {}), **created})


def update_provider(
    database_url: str,
    *,
    config: AuthConfig,
    provider_instance_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    existing = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if existing is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
    normalized = _coerce_provider_input(database_url, payload, is_update=True, existing_provider=existing)
    try:
        updated = platform_repo.update_provider_instance(
            database_url,
            provider_instance_id=provider_instance_id,
            slug=normalized["slug"],
            display_name=normalized["display_name"],
            description=normalized["description"],
            endpoint_url=normalized["endpoint_url"],
            healthcheck_url=normalized["healthcheck_url"],
            enabled=normalized["enabled"],
            config_json=_provider_storage_config(normalized["config"], normalized["secret_refs"]),
        )
    except Exception as exc:
        if "duplicate key value violates unique constraint" in str(exc).lower():
            raise PlatformControlPlaneError(
                "provider_instance_exists",
                "Provider instance slug already exists",
                status_code=409,
            ) from exc
        raise
    if updated is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
    return _serialize_provider_row({**(platform_repo.get_provider_instance(database_url, provider_instance_id) or {}), **updated})


def assign_provider_loaded_model(
    database_url: str,
    *,
    config: AuthConfig,
    provider_instance_id: str,
    managed_model_id: str,
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    provider_row = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if provider_row is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
    return _assign_provider_loaded_model(database_url, provider_row=provider_row, managed_model_id=managed_model_id)


def clear_provider_loaded_model(
    database_url: str,
    *,
    config: AuthConfig,
    provider_instance_id: str,
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    provider_row = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if provider_row is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
    return _clear_provider_loaded_model(database_url, provider_row=provider_row)


def delete_provider(database_url: str, *, config: AuthConfig, provider_instance_id: str) -> None:
    ensure_platform_bootstrap_state(database_url, config)
    existing = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if existing is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
    binding_count = platform_repo.count_deployment_bindings_for_provider(database_url, provider_instance_id=provider_instance_id)
    if binding_count > 0:
        raise PlatformControlPlaneError(
            "provider_instance_in_use",
            "Provider instance is still referenced by deployment profiles",
            status_code=409,
            details={"binding_count": binding_count},
        )
    deleted = platform_repo.delete_provider_instance(database_url, provider_instance_id)
    if not deleted:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)


def validate_provider(
    database_url: str,
    *,
    config: AuthConfig,
    provider_instance_id: str,
    credential_id: str | None = None,
    actor_user_id: int | None = None,
    actor_role: str = "user",
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    provider_row = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if provider_row is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
    assert_provider_allowed_for_current_runtime(database_url, provider_row)

    binding_row = platform_repo.get_active_binding_for_provider_instance(database_url, provider_instance_id=provider_instance_id)
    binding = ProviderBinding.from_row(binding_row or provider_row)
    credential_summary: dict[str, Any] | None = None
    if credential_id:
        if actor_user_id is None:
            raise PlatformControlPlaneError("missing_actor", "Actor user id is required for credential validation", status_code=400)
        binding, credential_summary = _binding_with_validation_credential(
            database_url,
            config=config,
            binding=binding,
            credential_id=credential_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
    if binding.capability_key == CAPABILITY_LLM_INFERENCE:
        adapter = _adapter_from_binding(binding)
        health = adapter.health()
        resources, resources_status = _list_adapter_resources(adapter)
        validation = {
            "health": health,
            "resources_reachable": 200 <= resources_status < 300,
            "resources_status_code": resources_status,
            "resources": [_serialize_binding_resource(resource) for resource in resources],
        }
        if credential_summary:
            validation["credential"] = credential_summary
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": validation,
        }

    if binding.capability_key == CAPABILITY_EMBEDDINGS:
        adapter = _adapter_from_binding(binding)
        health = adapter.health()
        resources, resources_status = _list_adapter_resources(adapter)
        if not binding.default_resource_id:
            validation = {
                "health": health,
                "embeddings_reachable": False,
                "embeddings_status_code": 409,
                "binding_error": "default_resource_required",
                "resources_reachable": 200 <= resources_status < 300,
                "resources_status_code": resources_status,
                "resources": [_serialize_binding_resource(resource) for resource in resources],
            }
            if credential_summary:
                validation["credential"] = credential_summary
            return {
                "provider": _serialize_provider_row(provider_row),
                "validation": validation,
            }
        embeddings_payload, embeddings_status = adapter.embed_texts(texts=["healthcheck"])
        embeddings = embeddings_payload.get("embeddings") if isinstance(embeddings_payload, dict) else []
        embedding_dimension = len(embeddings[0]) if isinstance(embeddings, list) and embeddings else 0
        validation = {
            "health": health,
            "embeddings_reachable": embeddings_payload is not None and 200 <= embeddings_status < 300,
            "embeddings_status_code": embeddings_status,
            "embedding_dimension": embedding_dimension,
            "resources_reachable": 200 <= resources_status < 300,
            "resources_status_code": resources_status,
            "resources": [_serialize_binding_resource(resource) for resource in resources],
        }
        if credential_summary:
            validation["credential"] = credential_summary
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": validation,
        }

    if binding.capability_key == CAPABILITY_VECTOR_STORE:
        adapter = resolve_vector_store_adapter(database_url, config, provider_instance_id=provider_instance_id)
        resources, resources_status = _list_adapter_resources(adapter)
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": {
                "health": adapter.health(),
                "resources_reachable": 200 <= resources_status < 300,
                "resources_status_code": resources_status,
                "resources": [_serialize_binding_resource(resource) for resource in resources],
            },
        }

    if binding.capability_key == CAPABILITY_SANDBOX_EXECUTION:
        adapter = resolve_sandbox_execution_adapter(database_url, config, provider_instance_id=provider_instance_id)
        dry_run_payload, dry_run_status = adapter.execute_dry_run()
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": {
                "health": adapter.health(),
                "execute_reachable": dry_run_payload is not None and 200 <= dry_run_status < 300,
                "execute_status_code": dry_run_status,
            },
        }

    if binding.capability_key == CAPABILITY_MCP_RUNTIME:
        adapter = resolve_mcp_runtime_adapter(database_url, config, provider_instance_id=provider_instance_id)
        invoke_payload, invoke_status = adapter.invoke(
            tool_name=str(binding.config.get("healthcheck_tool_name", "web_search")),
            arguments={"query": "healthcheck", "top_k": 1},
            request_metadata={"validation": True},
        )
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": {
                "health": adapter.health(),
                "invoke_reachable": invoke_payload is not None and 200 <= invoke_status < 300,
                "invoke_status_code": invoke_status,
            },
        }

    raise PlatformControlPlaneError("unsupported_capability", "Unsupported capability", status_code=400)


def _binding_with_validation_credential(
    database_url: str,
    *,
    config: AuthConfig,
    binding: ProviderBinding,
    credential_id: str,
    actor_user_id: int,
    actor_role: str,
) -> tuple[ProviderBinding, dict[str, Any]]:
    if binding.provider_key not in _OPENAI_COMPATIBLE_CLOUD_PROVIDER_KEYS:
        raise PlatformControlPlaneError(
            "credential_validation_unsupported",
            "BYOK credential validation is only supported for OpenAI-compatible cloud providers",
            status_code=409,
        )
    try:
        secret = get_active_credential_secret(
            database_url,
            credential_id=credential_id,
            requester_user_id=actor_user_id,
            requester_role=actor_role,
            encryption_key=config.model_credentials_encryption_key,
        )
    except ValueError as exc:
        raise PlatformControlPlaneError("invalid_credential_id", "credential_id must be a UUID", status_code=400) from exc
    if secret is None:
        raise PlatformControlPlaneError("credential_not_found", "Active credential not found", status_code=404)

    credential_provider = str(secret.get("provider_slug") or "").strip().lower()
    if credential_provider not in _OPENAI_COMPATIBLE_CREDENTIAL_PROVIDERS:
        raise PlatformControlPlaneError(
            "credential_provider_mismatch",
            "Credential provider does not match this platform provider",
            status_code=409,
            details={"credential_provider": credential_provider, "provider_key": binding.provider_key},
        )

    credential_base_url = str(secret.get("api_base_url") or "").strip()
    if not credential_base_url and credential_provider == "openai":
        credential_base_url = _OPENAI_DEFAULT_API_BASE_URL
    endpoint_url = credential_base_url or binding.endpoint_url
    if not endpoint_url:
        raise PlatformControlPlaneError(
            "missing_credential_api_base_url",
            "Credential is missing api_base_url and the provider has no endpoint URL",
            status_code=400,
        )

    next_config = dict(binding.config)
    secret_refs = dict(next_config.get("secret_refs") or {})
    secret_refs["api_key"] = str(secret.get("api_key") or "").strip()
    next_config["secret_refs"] = secret_refs

    return replace(binding, endpoint_url=endpoint_url, healthcheck_url=None, config=next_config), {
        "id": str(secret.get("id") or credential_id),
        "provider": credential_provider,
        "display_name": str(secret.get("display_name") or ""),
        "api_base_url": credential_base_url or None,
    }
