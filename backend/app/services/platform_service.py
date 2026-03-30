from __future__ import annotations

from . import platform_bindings as _platform_bindings_module
from . import platform_deployments as _platform_deployments_module
from . import platform_local_slots as _platform_local_slots_module
from . import platform_providers as _platform_providers_module
from . import platform_runtime as _platform_runtime_module
from . import platform_serialization as _platform_serialization_module
from ..repositories import context_management as context_repo
from ..repositories import platform_control_plane as platform_repo
from ..repositories.modelops import get_model as get_model_by_id
from .platform_adapters import http_json_request
from .platform_bindings import (
    _adapter_from_binding,
    _coerce_binding_resources,
    _coerce_create_input,
    _coerce_json_object,
    _coerce_provider_input,
    _coerce_secret_refs,
    _known_capability_keys,
    _list_adapter_resources,
    _normalize_binding_resources,
    _provider_storage_config,
    _resolve_deployment_bindings,
    _validate_binding_resources,
    _validate_bound_resources_against_provider_inventory,
    _validate_deployment_profile_bindings,
    _validate_model_binding_resource,
    _validate_non_model_resources,
    _validate_provider_binding,
    _validate_vector_binding_resource,
)
from .platform_bootstrap import (
    _bootstrap_provider_config,
    _existing_bindings_by_capability,
    _existing_provider_rows_by_slug,
    _upsert_bootstrap_binding,
    ensure_platform_bootstrap_state,
)
from .platform_deployments import (
    activate_deployment_profile,
    clone_deployment_profile,
    create_deployment_profile,
    delete_deployment_profile,
    list_deployment_activation_audit,
    list_deployment_profiles,
    update_deployment_profile,
)
from .platform_local_slots import (
    _config_with_local_slot,
    _effective_local_slot,
    _is_local_model_slot_provider,
    _local_slot_payload_from_config,
    _local_slot_with_runtime_state,
    _normalized_optional_slot_string,
    _provider_runtime_inventory,
    _runtime_admin_base_url,
    _runtime_admin_load_model,
    _runtime_admin_state,
    _runtime_admin_unload_model,
    _update_provider_local_slot,
    assign_provider_loaded_model,
    clear_provider_loaded_model,
)
from .platform_providers import (
    create_provider,
    delete_provider,
    list_capabilities,
    list_provider_families,
    list_providers,
    update_provider,
    validate_provider,
)
from .platform_runtime import (
    _resolve_provider_binding,
    get_active_capability_statuses,
    get_active_platform_runtime,
    resolve_embeddings_adapter,
    resolve_llm_inference_adapter,
    resolve_mcp_runtime_adapter,
    resolve_sandbox_execution_adapter,
    resolve_vector_store_adapter,
)
from .platform_serialization import (
    _build_model_binding_resource,
    _is_cloud_provider_row,
    _runtime_identifier_for_resource,
    _runtime_model_identifier,
    _serialize_activation_audit_row,
    _serialize_binding_resource,
    _serialize_deployment_profile,
    _serialize_provider_family_row,
    _serialize_provider_row,
    _serialize_runtime_binding,
    _serialize_runtime_deployment_profile,
)
from .platform_shared import _expected_task_key, _runtime_model_entries_for_capability
from .platform_types import (
    ALL_CAPABILITIES,
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_MCP_RUNTIME,
    CAPABILITY_SANDBOX_EXECUTION,
    CAPABILITY_VECTOR_STORE,
    OPTIONAL_CAPABILITIES,
    REQUIRED_CAPABILITIES,
    DeploymentBindingInput,
    DeploymentProfileCreateInput,
    PlatformControlPlaneError,
    ProviderBinding,
)


def _sync_platform_helpers() -> None:
    _platform_runtime_module.ensure_platform_bootstrap_state = ensure_platform_bootstrap_state
    _platform_providers_module.ensure_platform_bootstrap_state = ensure_platform_bootstrap_state
    _platform_providers_module._adapter_from_binding = _adapter_from_binding
    _platform_providers_module._list_adapter_resources = _list_adapter_resources
    _platform_providers_module._serialize_binding_resource = _serialize_binding_resource
    _platform_providers_module._serialize_provider_row = _serialize_provider_row
    _platform_deployments_module.ensure_platform_bootstrap_state = ensure_platform_bootstrap_state
    _platform_bindings_module._known_capability_keys = _known_capability_keys
    _platform_bindings_module._validate_provider_binding = _validate_provider_binding
    _platform_serialization_module._effective_local_slot = _effective_local_slot
    _platform_local_slots_module._runtime_admin_state = _runtime_admin_state
    _platform_local_slots_module._provider_runtime_inventory = _provider_runtime_inventory
    _platform_local_slots_module.get_model_by_id = get_model_by_id


def list_capabilities(database_url: str, config):
    _sync_platform_helpers()
    return _platform_providers_module.list_capabilities(database_url, config)


def list_providers(database_url: str, config):
    _sync_platform_helpers()
    return _platform_providers_module.list_providers(database_url, config)


def list_provider_families(database_url: str, config):
    _sync_platform_helpers()
    return _platform_providers_module.list_provider_families(database_url, config)


def create_provider(database_url: str, *, config, payload):
    _sync_platform_helpers()
    return _platform_providers_module.create_provider(database_url, config=config, payload=payload)


def update_provider(database_url: str, *, config, provider_instance_id: str, payload):
    _sync_platform_helpers()
    return _platform_providers_module.update_provider(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
        payload=payload,
    )


def assign_provider_loaded_model(
    database_url: str,
    *,
    config,
    provider_instance_id: str,
    managed_model_id: str,
):
    _sync_platform_helpers()
    return _platform_providers_module.assign_provider_loaded_model(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
        managed_model_id=managed_model_id,
    )


def clear_provider_loaded_model(database_url: str, *, config, provider_instance_id: str):
    _sync_platform_helpers()
    return _platform_providers_module.clear_provider_loaded_model(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
    )


def delete_provider(database_url: str, *, config, provider_instance_id: str) -> None:
    _sync_platform_helpers()
    return _platform_providers_module.delete_provider(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
    )


def validate_provider(database_url: str, *, config, provider_instance_id: str):
    _sync_platform_helpers()
    return _platform_providers_module.validate_provider(
        database_url,
        config=config,
        provider_instance_id=provider_instance_id,
    )


def list_deployment_profiles(database_url: str, config):
    _sync_platform_helpers()
    return _platform_deployments_module.list_deployment_profiles(database_url, config)


def list_deployment_activation_audit(database_url: str, config):
    _sync_platform_helpers()
    return _platform_deployments_module.list_deployment_activation_audit(database_url, config)


def create_deployment_profile(database_url: str, *, config, payload, created_by_user_id: int):
    _sync_platform_helpers()
    return _platform_deployments_module.create_deployment_profile(
        database_url,
        config=config,
        payload=payload,
        created_by_user_id=created_by_user_id,
    )


def update_deployment_profile(
    database_url: str,
    *,
    config,
    deployment_profile_id: str,
    payload,
    updated_by_user_id: int,
):
    _sync_platform_helpers()
    return _platform_deployments_module.update_deployment_profile(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
        payload=payload,
        updated_by_user_id=updated_by_user_id,
    )


def update_deployment_profile_identity(
    database_url: str,
    *,
    config,
    deployment_profile_id: str,
    payload,
    updated_by_user_id: int,
):
    _sync_platform_helpers()
    return _platform_deployments_module.update_deployment_profile_identity(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
        payload=payload,
        updated_by_user_id=updated_by_user_id,
    )


def upsert_deployment_profile_binding(
    database_url: str,
    *,
    config,
    deployment_profile_id: str,
    capability_key: str,
    payload,
    updated_by_user_id: int,
):
    _sync_platform_helpers()
    return _platform_deployments_module.upsert_deployment_profile_binding(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
        capability_key=capability_key,
        payload=payload,
        updated_by_user_id=updated_by_user_id,
    )


def clone_deployment_profile(
    database_url: str,
    *,
    config,
    source_deployment_profile_id: str,
    payload,
    created_by_user_id: int,
):
    _sync_platform_helpers()
    return _platform_deployments_module.clone_deployment_profile(
        database_url,
        config=config,
        source_deployment_profile_id=source_deployment_profile_id,
        payload=payload,
        created_by_user_id=created_by_user_id,
    )


def delete_deployment_profile(database_url: str, *, config, deployment_profile_id: str) -> None:
    _sync_platform_helpers()
    return _platform_deployments_module.delete_deployment_profile(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
    )


def activate_deployment_profile(
    database_url: str,
    *,
    config,
    deployment_profile_id: str,
    activated_by_user_id: int,
):
    _sync_platform_helpers()
    return _platform_deployments_module.activate_deployment_profile(
        database_url,
        config=config,
        deployment_profile_id=deployment_profile_id,
        activated_by_user_id=activated_by_user_id,
    )


def resolve_llm_inference_adapter(database_url: str, config, *, provider_instance_id: str | None = None):
    _sync_platform_helpers()
    return _platform_runtime_module.resolve_llm_inference_adapter(
        database_url,
        config,
        provider_instance_id=provider_instance_id,
    )


def resolve_embeddings_adapter(database_url: str, config, *, provider_instance_id: str | None = None):
    _sync_platform_helpers()
    return _platform_runtime_module.resolve_embeddings_adapter(
        database_url,
        config,
        provider_instance_id=provider_instance_id,
    )


def resolve_vector_store_adapter(database_url: str, config, *, provider_instance_id: str | None = None):
    _sync_platform_helpers()
    return _platform_runtime_module.resolve_vector_store_adapter(
        database_url,
        config,
        provider_instance_id=provider_instance_id,
    )


def resolve_sandbox_execution_adapter(database_url: str, config, *, provider_instance_id: str | None = None):
    _sync_platform_helpers()
    return _platform_runtime_module.resolve_sandbox_execution_adapter(
        database_url,
        config,
        provider_instance_id=provider_instance_id,
    )


def resolve_mcp_runtime_adapter(database_url: str, config, *, provider_instance_id: str | None = None):
    _sync_platform_helpers()
    return _platform_runtime_module.resolve_mcp_runtime_adapter(
        database_url,
        config,
        provider_instance_id=provider_instance_id,
    )


def get_active_platform_runtime(database_url: str, config):
    _sync_platform_helpers()
    return _platform_runtime_module.get_active_platform_runtime(database_url, config)


def get_active_capability_statuses(database_url: str, config):
    _sync_platform_helpers()
    return _platform_runtime_module.get_active_capability_statuses(database_url, config)


def _validate_deployment_profile_bindings(database_url: str, config, bindings):
    _sync_platform_helpers()
    return _platform_bindings_module._validate_deployment_profile_bindings(database_url, config, bindings)


def _effective_local_slot(provider_row):
    _sync_platform_helpers()
    return _platform_local_slots_module._effective_local_slot(provider_row)

__all__ = [
    "ALL_CAPABILITIES",
    "CAPABILITY_EMBEDDINGS",
    "CAPABILITY_LLM_INFERENCE",
    "CAPABILITY_MCP_RUNTIME",
    "CAPABILITY_SANDBOX_EXECUTION",
    "CAPABILITY_VECTOR_STORE",
    "DeploymentBindingInput",
    "DeploymentProfileCreateInput",
    "OPTIONAL_CAPABILITIES",
    "PlatformControlPlaneError",
    "ProviderBinding",
    "REQUIRED_CAPABILITIES",
    "_adapter_from_binding",
    "_bootstrap_provider_config",
    "_build_model_binding_resource",
    "_coerce_binding_resources",
    "_coerce_create_input",
    "_coerce_json_object",
    "_coerce_provider_input",
    "_coerce_secret_refs",
    "_config_with_local_slot",
    "_effective_local_slot",
    "_existing_bindings_by_capability",
    "_existing_provider_rows_by_slug",
    "_expected_task_key",
    "_is_cloud_provider_row",
    "_is_local_model_slot_provider",
    "_known_capability_keys",
    "_list_adapter_resources",
    "_local_slot_payload_from_config",
    "_local_slot_with_runtime_state",
    "_normalize_binding_resources",
    "_normalized_optional_slot_string",
    "_provider_runtime_inventory",
    "_provider_storage_config",
    "_resolve_deployment_bindings",
    "_resolve_provider_binding",
    "_runtime_admin_base_url",
    "_runtime_admin_load_model",
    "_runtime_admin_state",
    "_runtime_admin_unload_model",
    "_runtime_identifier_for_resource",
    "_runtime_model_entries_for_capability",
    "_runtime_model_identifier",
    "_serialize_activation_audit_row",
    "_serialize_binding_resource",
    "_serialize_deployment_profile",
    "_serialize_provider_family_row",
    "_serialize_provider_row",
    "_serialize_runtime_binding",
    "_serialize_runtime_deployment_profile",
    "_update_provider_local_slot",
    "_upsert_bootstrap_binding",
    "_validate_binding_resources",
    "_validate_bound_resources_against_provider_inventory",
    "_validate_deployment_profile_bindings",
    "_validate_model_binding_resource",
    "_validate_non_model_resources",
    "_validate_provider_binding",
    "_validate_vector_binding_resource",
    "activate_deployment_profile",
    "assign_provider_loaded_model",
    "clear_provider_loaded_model",
    "clone_deployment_profile",
    "context_repo",
    "create_deployment_profile",
    "create_provider",
    "delete_deployment_profile",
    "delete_provider",
    "ensure_platform_bootstrap_state",
    "get_active_capability_statuses",
    "get_active_platform_runtime",
    "get_model_by_id",
    "http_json_request",
    "list_capabilities",
    "list_deployment_activation_audit",
    "list_deployment_profiles",
    "list_provider_families",
    "list_providers",
    "platform_repo",
    "resolve_embeddings_adapter",
    "resolve_llm_inference_adapter",
    "resolve_mcp_runtime_adapter",
    "resolve_sandbox_execution_adapter",
    "resolve_vector_store_adapter",
    "update_deployment_profile",
    "update_provider",
    "validate_provider",
]
