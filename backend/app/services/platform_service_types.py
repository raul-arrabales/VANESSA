from __future__ import annotations

from typing import Any, TypeAlias, TypedDict

from .platform_types import CAPABILITY_EMBEDDINGS, CAPABILITY_LLM_INFERENCE

ProviderRow: TypeAlias = dict[str, Any]
ProviderFamilyRow: TypeAlias = dict[str, Any]
DeploymentProfileRow: TypeAlias = dict[str, Any]
DeploymentBindingRow: TypeAlias = dict[str, Any]
ActivationAuditRow: TypeAlias = dict[str, Any]


class ProviderStoragePayload(TypedDict):
    provider_key: str
    slug: str
    display_name: str
    description: str
    endpoint_url: str
    healthcheck_url: str | None
    enabled: bool
    config: dict[str, Any]
    secret_refs: dict[str, str]


class BindingResourcePayload(TypedDict):
    id: str
    resource_kind: str
    ref_type: str
    managed_model_id: str | None
    knowledge_base_id: str | None
    provider_resource_id: str | None
    display_name: str | None
    metadata: dict[str, Any]


class LocalModelSlotState(TypedDict):
    loaded_managed_model_id: str | None
    loaded_managed_model_name: str | None
    loaded_runtime_model_id: str | None
    loaded_local_path: str | None
    loaded_source_id: str | None
    load_state: str
    load_error: str | None


class RuntimeCapabilityPayload(TypedDict):
    id: str
    slug: str
    provider_key: str
    display_name: str
    description: str
    adapter_kind: str
    endpoint_url: str
    healthcheck_url: str | None
    enabled: bool
    config: dict[str, Any]
    resources: list[dict[str, Any]]
    default_resource_id: str | None
    default_resource: dict[str, Any] | None
    resource_policy: dict[str, Any]
    binding_config: dict[str, Any]


_BOOTSTRAP_DEPLOYMENT_SLUG = "local-default"
_BOOTSTRAP_DEPLOYMENT_NAME = "Local Default"
_BOOTSTRAP_DEPLOYMENT_DESCRIPTION = "Bootstrapped local profile using current platform endpoint configuration."
_LLAMA_CPP_DEPLOYMENT_SLUG = "local-llama-cpp"
_LLAMA_CPP_DEPLOYMENT_NAME = "Local llama.cpp"
_LLAMA_CPP_DEPLOYMENT_DESCRIPTION = "Optional local profile using llama.cpp for LLM inference and Weaviate for vector storage."
_QDRANT_DEPLOYMENT_SLUG = "local-qdrant"
_QDRANT_DEPLOYMENT_NAME = "Local Qdrant"
_QDRANT_DEPLOYMENT_DESCRIPTION = "Optional local profile using vLLM for LLM inference and Qdrant for vector storage."
_TASK_KEY_EMBEDDINGS = "embeddings"
_TASK_KEY_LLM = "llm"
_CLOUD_PROVIDER_KEYS = {"openai_compatible_cloud_llm", "openai_compatible_cloud_embeddings"}
_MODEL_BEARING_CAPABILITIES = {CAPABILITY_LLM_INFERENCE, CAPABILITY_EMBEDDINGS}
_VECTOR_SELECTION_EXPLICIT = "explicit"
_VECTOR_SELECTION_DYNAMIC_NAMESPACE = "dynamic_namespace"
_LOCAL_SLOT_STATE_EMPTY = "empty"
_LOCAL_SLOT_STATE_LOADING = "loading"
_LOCAL_SLOT_STATE_RECONCILING = "reconciling"
_LOCAL_SLOT_STATE_LOADED = "loaded"
_LOCAL_SLOT_STATE_ERROR = "error"
_LOCAL_SLOT_CONFIG_KEYS = {
    "loaded_managed_model_id",
    "loaded_managed_model_name",
    "loaded_runtime_model_id",
    "loaded_local_path",
    "loaded_source_id",
    "load_state",
    "load_error",
}
