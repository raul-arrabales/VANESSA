from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories.modelops import get_model as get_model_by_id
from ..repositories import platform_control_plane as platform_repo
from .platform_adapters import (
    EmbeddingsAdapter,
    LlmInferenceAdapter,
    McpRuntimeAdapter,
    OpenAICompatibleEmbeddingsAdapter,
    OpenAICompatibleLlmAdapter,
    QdrantVectorStoreAdapter,
    SandboxExecutionAdapter,
    VectorStoreAdapter,
    WeaviateVectorStoreAdapter,
    HttpMcpRuntimeAdapter,
    HttpSandboxExecutionAdapter,
    http_json_request,
)
from .platform_types import (
    ALL_CAPABILITIES,
    CAPABILITY_MCP_RUNTIME,
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_SANDBOX_EXECUTION,
    CAPABILITY_VECTOR_STORE,
    OPTIONAL_CAPABILITIES,
    REQUIRED_CAPABILITIES,
    DeploymentBindingInput,
    DeploymentProfileCreateInput,
    PlatformControlPlaneError,
    ProviderBinding,
)

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


def _known_capability_keys(database_url: str) -> set[str]:
    return {str(row["capability_key"]).strip().lower() for row in platform_repo.list_capabilities(database_url)}


def _upsert_bootstrap_binding(
    database_url: str,
    *,
    deployment_profile_id: str,
    capability_key: str,
    provider_instance_id: str,
    resources: list[dict[str, Any]],
    default_resource_id: str | None,
    binding_config: dict[str, Any],
    resource_policy: dict[str, Any],
) -> None:
    platform_repo.upsert_deployment_binding(
        database_url,
        deployment_profile_id=deployment_profile_id,
        capability_key=capability_key,
        provider_instance_id=provider_instance_id,
        resources=resources,
        default_resource_id=default_resource_id,
        binding_config=binding_config,
        resource_policy=resource_policy,
    )


def ensure_platform_bootstrap_state(database_url: str, config: AuthConfig) -> None:
    sandbox_url = str(getattr(config, "sandbox_url", "") or "").strip()
    mcp_gateway_url = str(getattr(config, "mcp_gateway_url", "") or "").strip()
    llm_request_timeout_seconds = int(getattr(config, "llm_request_timeout_seconds", 60) or 60)
    llm_local_upstream_model = str(
        getattr(config, "llm_local_upstream_model", "") or "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"
    ).strip() or "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"
    llm_local_embeddings_upstream_model = str(
        getattr(config, "llm_local_embeddings_upstream_model", "") or llm_local_upstream_model
    ).strip() or llm_local_upstream_model
    platform_repo.ensure_capability(
        database_url,
        capability_key=CAPABILITY_LLM_INFERENCE,
        display_name="LLM inference",
        description="Normalized chat and generation capability for model inference.",
        is_required=True,
    )
    platform_repo.ensure_capability(
        database_url,
        capability_key=CAPABILITY_EMBEDDINGS,
        display_name="Embeddings",
        description="Normalized text embeddings capability for retrieval and vector ingestion.",
        is_required=True,
    )
    platform_repo.ensure_capability(
        database_url,
        capability_key=CAPABILITY_VECTOR_STORE,
        display_name="Vector store",
        description="Semantic retrieval capability for embeddings and document search.",
        is_required=True,
    )
    platform_repo.ensure_capability(
        database_url,
        capability_key=CAPABILITY_MCP_RUNTIME,
        display_name="MCP runtime",
        description="Gateway capability for MCP-hosted tool execution.",
        is_required=False,
    )
    platform_repo.ensure_capability(
        database_url,
        capability_key=CAPABILITY_SANDBOX_EXECUTION,
        display_name="Sandbox execution",
        description="Isolated code-execution capability for agent tools.",
        is_required=False,
    )

    platform_repo.ensure_provider_family(
        database_url,
        provider_key="vllm_local",
        capability_key=CAPABILITY_LLM_INFERENCE,
        adapter_kind="openai_compatible_llm",
        display_name="vLLM local gateway",
        description="Current local-first LLM gateway backed by llm -> llm_runtime.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="llama_cpp_local",
        capability_key=CAPABILITY_LLM_INFERENCE,
        adapter_kind="openai_compatible_llm",
        display_name="llama.cpp local",
        description="OpenAI-compatible llama.cpp inference endpoint for local deployments.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="vllm_embeddings_local",
        capability_key=CAPABILITY_EMBEDDINGS,
        adapter_kind="openai_compatible_embeddings",
        display_name="vLLM embeddings local",
        description="Local embeddings provider exposed through the llm gateway.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="openai_compatible_cloud_llm",
        capability_key=CAPABILITY_LLM_INFERENCE,
        adapter_kind="openai_compatible_llm",
        display_name="OpenAI-compatible cloud LLM",
        description="Shared cloud LLM endpoint using OpenAI-compatible APIs and platform secret refs.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="openai_compatible_cloud_embeddings",
        capability_key=CAPABILITY_EMBEDDINGS,
        adapter_kind="openai_compatible_embeddings",
        display_name="OpenAI-compatible cloud embeddings",
        description="Shared cloud embeddings endpoint using OpenAI-compatible APIs and platform secret refs.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="weaviate_local",
        capability_key=CAPABILITY_VECTOR_STORE,
        adapter_kind="weaviate_http",
        display_name="Weaviate local",
        description="Local Weaviate semantic index endpoint.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="qdrant_local",
        capability_key=CAPABILITY_VECTOR_STORE,
        adapter_kind="qdrant_http",
        display_name="Qdrant local",
        description="Optional local Qdrant semantic index endpoint.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="mcp_gateway_local",
        capability_key=CAPABILITY_MCP_RUNTIME,
        adapter_kind="mcp_http",
        display_name="MCP gateway local",
        description="Optional local MCP runtime gateway for remote and general-purpose tools.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="sandbox_local",
        capability_key=CAPABILITY_SANDBOX_EXECUTION,
        adapter_kind="sandbox_http",
        display_name="Sandbox local",
        description="Local sandbox execution runtime for agent tools.",
    )

    vllm_provider = platform_repo.ensure_provider_instance(
        database_url,
        slug="vllm-local-gateway",
        provider_key="vllm_local",
        display_name="vLLM local gateway",
        description="Primary llm service entrypoint for the local vLLM stack.",
        endpoint_url=config.llm_url,
        healthcheck_url=config.llm_url.rstrip("/") + "/health",
        enabled=True,
        config_json={
            "models_path": "/v1/models",
            "chat_completion_path": "/v1/chat/completions",
            "runtime_base_url": getattr(config, "llm_inference_runtime_url", config.llm_runtime_url),
            "runtime_admin_base_url": getattr(config, "llm_inference_runtime_url", config.llm_runtime_url),
            "canonical_local_model_id": "local-vllm-default",
            "local_fallback_model_id": "local-vllm-default",
            "request_timeout_seconds": llm_request_timeout_seconds,
        },
    )
    weaviate_provider = platform_repo.ensure_provider_instance(
        database_url,
        slug="weaviate-local",
        provider_key="weaviate_local",
        display_name="Weaviate local",
        description="Primary Weaviate endpoint for semantic retrieval.",
        endpoint_url=config.weaviate_url,
        healthcheck_url=config.weaviate_url.rstrip("/") + "/v1/.well-known/ready",
        enabled=True,
        config_json={},
    )
    embeddings_provider = platform_repo.ensure_provider_instance(
        database_url,
        slug="vllm-embeddings-local",
        provider_key="vllm_embeddings_local",
        display_name="vLLM embeddings local",
        description="Primary llm gateway entrypoint for local embeddings generation.",
        endpoint_url=config.llm_url,
        healthcheck_url=config.llm_url.rstrip("/") + "/health",
        enabled=True,
        config_json={
            "models_path": "/v1/models",
            "embeddings_path": "/v1/embeddings",
            "input_type": "text",
            "runtime_base_url": getattr(config, "llm_embeddings_runtime_url", config.llm_runtime_url),
            "runtime_admin_base_url": getattr(config, "llm_embeddings_runtime_url", config.llm_runtime_url),
            "forced_model_id": "local-vllm-embeddings-default",
            "request_timeout_seconds": llm_request_timeout_seconds,
        },
    )
    sandbox_provider = None
    if sandbox_url:
        sandbox_provider = platform_repo.ensure_provider_instance(
            database_url,
            slug="sandbox-local",
            provider_key="sandbox_local",
            display_name="Sandbox local",
            description="Primary sandbox execution runtime for agent tools.",
            endpoint_url=sandbox_url,
            healthcheck_url=sandbox_url.rstrip("/") + "/health",
            enabled=True,
            config_json={
                "execute_path": "/v1/execute",
                "dry_run_code": "result = {'status': 'ok'}",
                "default_timeout_seconds": 5,
            },
        )
    llama_cpp_provider = platform_repo.ensure_provider_instance(
        database_url,
        slug="llama-cpp-local",
        provider_key="llama_cpp_local",
        display_name="llama.cpp local",
        description="Optional OpenAI-compatible llama.cpp endpoint for alternative local inference.",
        endpoint_url=(getattr(config, "llama_cpp_url", "") or "http://llama_cpp:8080"),
        healthcheck_url=None,
        enabled=bool(getattr(config, "llama_cpp_url", "").strip()),
        config_json={
            "models_path": "/v1/models",
            "chat_completion_path": "/v1/chat/completions",
            "request_format": "openai_chat",
            "canonical_local_model_id": "local-llama-cpp-default",
            "forced_model_id": "local-llama-cpp-default",
            "local_fallback_model_id": "local-llama-cpp-default",
            "request_timeout_seconds": llm_request_timeout_seconds,
        },
    )
    qdrant_provider = None
    if getattr(config, "qdrant_url", "").strip():
        qdrant_provider = platform_repo.ensure_provider_instance(
            database_url,
            slug="qdrant-local",
            provider_key="qdrant_local",
            display_name="Qdrant local",
            description="Optional Qdrant endpoint for alternate local retrieval.",
            endpoint_url=config.qdrant_url,
            healthcheck_url=config.qdrant_url.rstrip("/") + "/healthz",
            enabled=True,
            config_json={
                "collections_path": "/collections",
                "health_path": "/healthz",
                "default_vector_size": 1,
                "distance": "Cosine",
            },
        )
    mcp_gateway_provider = None
    if mcp_gateway_url:
        mcp_gateway_provider = platform_repo.ensure_provider_instance(
            database_url,
            slug="mcp-gateway-local",
            provider_key="mcp_gateway_local",
            display_name="MCP gateway local",
            description="Optional local MCP gateway for hosted tool runtimes.",
            endpoint_url=mcp_gateway_url,
            healthcheck_url=mcp_gateway_url.rstrip("/") + "/health",
            enabled=True,
            config_json={
                "invoke_path": "/v1/tools/invoke",
                "list_tools_path": "/v1/tools",
                "healthcheck_tool_name": "web_search",
            },
        )

    profile = platform_repo.ensure_deployment_profile(
        database_url,
        slug=_BOOTSTRAP_DEPLOYMENT_SLUG,
        display_name=_BOOTSTRAP_DEPLOYMENT_NAME,
        description=_BOOTSTRAP_DEPLOYMENT_DESCRIPTION,
        created_by_user_id=None,
        updated_by_user_id=None,
    )
    _upsert_bootstrap_binding(
        database_url,
        deployment_profile_id=str(profile["id"]),
        capability_key=CAPABILITY_LLM_INFERENCE,
        provider_instance_id=str(vllm_provider["id"]),
        resources=[],
        default_resource_id=None,
        binding_config={},
        resource_policy={},
    )
    _upsert_bootstrap_binding(
        database_url,
        deployment_profile_id=str(profile["id"]),
        capability_key=CAPABILITY_EMBEDDINGS,
        provider_instance_id=str(embeddings_provider["id"]),
        resources=[],
        default_resource_id=None,
        binding_config={},
        resource_policy={},
    )
    _upsert_bootstrap_binding(
        database_url,
        deployment_profile_id=str(profile["id"]),
        capability_key=CAPABILITY_VECTOR_STORE,
        provider_instance_id=str(weaviate_provider["id"]),
        resources=[],
        default_resource_id=None,
        binding_config={},
        resource_policy={"selection_mode": _VECTOR_SELECTION_DYNAMIC_NAMESPACE},
    )
    if sandbox_provider is not None and sandbox_provider.get("id"):
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(profile["id"]),
            capability_key=CAPABILITY_SANDBOX_EXECUTION,
            provider_instance_id=str(sandbox_provider["id"]),
            resources=[],
            default_resource_id=None,
            binding_config={},
            resource_policy={},
        )
    if mcp_gateway_provider is not None:
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(profile["id"]),
            capability_key=CAPABILITY_MCP_RUNTIME,
            provider_instance_id=str(mcp_gateway_provider["id"]),
            resources=[],
            default_resource_id=None,
            binding_config={},
            resource_policy={},
        )

    if getattr(config, "llama_cpp_url", "").strip():
        llama_profile = platform_repo.ensure_deployment_profile(
            database_url,
            slug=_LLAMA_CPP_DEPLOYMENT_SLUG,
            display_name=_LLAMA_CPP_DEPLOYMENT_NAME,
            description=_LLAMA_CPP_DEPLOYMENT_DESCRIPTION,
            created_by_user_id=None,
            updated_by_user_id=None,
        )
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(llama_profile["id"]),
            capability_key=CAPABILITY_LLM_INFERENCE,
            provider_instance_id=str(llama_cpp_provider["id"]),
            resources=[],
            default_resource_id=None,
            binding_config={},
            resource_policy={},
        )
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(llama_profile["id"]),
            capability_key=CAPABILITY_EMBEDDINGS,
            provider_instance_id=str(embeddings_provider["id"]),
            resources=[],
            default_resource_id=None,
            binding_config={},
            resource_policy={},
        )
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(llama_profile["id"]),
            capability_key=CAPABILITY_VECTOR_STORE,
            provider_instance_id=str(weaviate_provider["id"]),
            resources=[],
            default_resource_id=None,
            binding_config={},
            resource_policy={"selection_mode": _VECTOR_SELECTION_DYNAMIC_NAMESPACE},
        )
        if sandbox_provider is not None and sandbox_provider.get("id"):
            _upsert_bootstrap_binding(
                database_url,
                deployment_profile_id=str(llama_profile["id"]),
                capability_key=CAPABILITY_SANDBOX_EXECUTION,
                provider_instance_id=str(sandbox_provider["id"]),
                resources=[],
                default_resource_id=None,
                binding_config={},
                resource_policy={},
            )
        if mcp_gateway_provider is not None:
            _upsert_bootstrap_binding(
                database_url,
                deployment_profile_id=str(llama_profile["id"]),
                capability_key=CAPABILITY_MCP_RUNTIME,
                provider_instance_id=str(mcp_gateway_provider["id"]),
                resources=[],
                default_resource_id=None,
                binding_config={},
                resource_policy={},
            )

    if qdrant_provider is not None:
        qdrant_profile = platform_repo.ensure_deployment_profile(
            database_url,
            slug=_QDRANT_DEPLOYMENT_SLUG,
            display_name=_QDRANT_DEPLOYMENT_NAME,
            description=_QDRANT_DEPLOYMENT_DESCRIPTION,
            created_by_user_id=None,
            updated_by_user_id=None,
        )
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(qdrant_profile["id"]),
            capability_key=CAPABILITY_LLM_INFERENCE,
            provider_instance_id=str(vllm_provider["id"]),
            resources=[],
            default_resource_id=None,
            binding_config={},
            resource_policy={},
        )
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(qdrant_profile["id"]),
            capability_key=CAPABILITY_EMBEDDINGS,
            provider_instance_id=str(embeddings_provider["id"]),
            resources=[],
            default_resource_id=None,
            binding_config={},
            resource_policy={},
        )
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(qdrant_profile["id"]),
            capability_key=CAPABILITY_VECTOR_STORE,
            provider_instance_id=str(qdrant_provider["id"]),
            resources=[],
            default_resource_id=None,
            binding_config={},
            resource_policy={"selection_mode": _VECTOR_SELECTION_DYNAMIC_NAMESPACE},
        )
        if sandbox_provider is not None and sandbox_provider.get("id"):
            _upsert_bootstrap_binding(
                database_url,
                deployment_profile_id=str(qdrant_profile["id"]),
                capability_key=CAPABILITY_SANDBOX_EXECUTION,
                provider_instance_id=str(sandbox_provider["id"]),
                resources=[],
                default_resource_id=None,
                binding_config={},
                resource_policy={},
            )
        if mcp_gateway_provider is not None:
            _upsert_bootstrap_binding(
                database_url,
                deployment_profile_id=str(qdrant_profile["id"]),
                capability_key=CAPABILITY_MCP_RUNTIME,
                provider_instance_id=str(mcp_gateway_provider["id"]),
                resources=[],
                default_resource_id=None,
                binding_config={},
                resource_policy={},
            )

    if platform_repo.get_active_deployment(database_url) is None:
        platform_repo.activate_deployment_profile(
            database_url,
            deployment_profile_id=str(profile["id"]),
            activated_by_user_id=None,
        )


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


def create_provider(
    database_url: str,
    *,
    config: AuthConfig,
    payload: dict[str, Any],
) -> dict[str, Any]:
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
    normalized = _coerce_provider_input(
        database_url,
        payload,
        is_update=True,
        existing_provider=existing,
    )
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
    if not _is_local_model_slot_provider(provider_row):
        raise PlatformControlPlaneError(
            "provider_slot_unsupported",
            "Only local LLM and embeddings providers support loaded-model slots",
            status_code=409,
        )

    normalized_model_id = managed_model_id.strip()
    if not normalized_model_id:
        raise PlatformControlPlaneError("managed_model_required", "managed_model_id is required", status_code=400)
    model_row = get_model_by_id(database_url, normalized_model_id)
    if model_row is None:
        raise PlatformControlPlaneError("managed_model_not_found", "Managed model not found", status_code=404)

    capability_key = str(provider_row.get("capability_key") or "").strip().lower()
    expected_task_key = _TASK_KEY_LLM if capability_key == CAPABILITY_LLM_INFERENCE else _TASK_KEY_EMBEDDINGS
    task_key = str(model_row.get("task_key") or "").strip().lower()
    if task_key != expected_task_key:
        raise PlatformControlPlaneError(
            "managed_model_task_mismatch",
            f"Provider requires a model with task_key={expected_task_key}",
            status_code=409,
            details={"provider_instance_id": provider_instance_id, "managed_model_id": normalized_model_id},
        )
    if str(model_row.get("backend_kind") or "").strip().lower() != "local":
        raise PlatformControlPlaneError(
            "managed_model_backend_mismatch",
            "Local provider slots only support local managed models",
            status_code=409,
            details={"provider_instance_id": provider_instance_id, "managed_model_id": normalized_model_id},
        )

    runtime_model_id = _runtime_model_identifier(model_row)
    if not runtime_model_id:
        raise PlatformControlPlaneError(
            "provider_resource_id_required",
            "Selected local model must define a runtime identifier",
            status_code=400,
            details={"managed_model_id": normalized_model_id},
        )

    provider_config = dict(provider_row.get("config_json") or {})
    updated_config = _config_with_local_slot(
        provider_config,
        loaded_managed_model_id=normalized_model_id,
        loaded_managed_model_name=str(model_row.get("name") or normalized_model_id).strip() or normalized_model_id,
        loaded_runtime_model_id=runtime_model_id,
        loaded_local_path=str(model_row.get("local_path") or "").strip() or None,
        loaded_source_id=str(model_row.get("source_id") or "").strip() or None,
        load_state=_LOCAL_SLOT_STATE_LOADING,
        load_error=None,
    )

    updated = _update_provider_local_slot(
        database_url,
        provider_row=provider_row,
        config_json=updated_config,
    )
    runtime_state, status_code = _runtime_admin_load_model(
        {**provider_row, "config_json": updated_config},
        runtime_model_id=runtime_model_id,
        local_path=str(model_row.get("local_path") or "").strip(),
        managed_model_id=normalized_model_id,
        display_name=str(model_row.get("name") or normalized_model_id).strip() or normalized_model_id,
    )
    if status_code >= 400 and not (status_code == 404 and runtime_state is None):
        errored_config = _config_with_local_slot(
            updated_config,
            loaded_managed_model_id=normalized_model_id,
            loaded_managed_model_name=str(model_row.get("name") or normalized_model_id).strip() or normalized_model_id,
            loaded_runtime_model_id=runtime_model_id,
            loaded_local_path=str(model_row.get("local_path") or "").strip() or None,
            loaded_source_id=str(model_row.get("source_id") or "").strip() or None,
            load_state=_LOCAL_SLOT_STATE_ERROR,
            load_error=str((runtime_state or {}).get("message") or f"runtime_load_failed:{status_code}"),
        )
        updated = _update_provider_local_slot(
            database_url,
            provider_row={**provider_row, **updated},
            config_json=errored_config,
        )
    elif isinstance(runtime_state, dict):
        updated = _update_provider_local_slot(
            database_url,
            provider_row={**provider_row, **updated},
            config_json=_config_with_local_slot(
                updated_config,
                loaded_managed_model_id=normalized_model_id,
                loaded_managed_model_name=str(model_row.get("name") or normalized_model_id).strip() or normalized_model_id,
                loaded_runtime_model_id=str(runtime_state.get("runtime_model_id") or runtime_model_id).strip() or runtime_model_id,
                loaded_local_path=str(runtime_state.get("local_path") or model_row.get("local_path") or "").strip() or None,
                loaded_source_id=str(model_row.get("source_id") or "").strip() or None,
                load_state=str(runtime_state.get("load_state") or _LOCAL_SLOT_STATE_LOADING).strip().lower() or _LOCAL_SLOT_STATE_LOADING,
                load_error=str(runtime_state.get("last_error") or "").strip() or None,
            ),
        )
    return _serialize_provider_row({**(platform_repo.get_provider_instance(database_url, provider_instance_id) or {}), **updated})


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
    if not _is_local_model_slot_provider(provider_row):
        raise PlatformControlPlaneError(
            "provider_slot_unsupported",
            "Only local LLM and embeddings providers support loaded-model slots",
            status_code=409,
        )

    provider_config = dict(provider_row.get("config_json") or {})
    cleared_config = _config_with_local_slot(
        provider_config,
        loaded_managed_model_id=None,
        loaded_managed_model_name=None,
        loaded_runtime_model_id=None,
        loaded_local_path=None,
        loaded_source_id=None,
        load_state=_LOCAL_SLOT_STATE_EMPTY,
        load_error=None,
    )
    updated = _update_provider_local_slot(
        database_url,
        provider_row=provider_row,
        config_json=cleared_config,
    )
    runtime_state, status_code = _runtime_admin_unload_model({**provider_row, "config_json": cleared_config})
    if status_code >= 400 and not (status_code == 404 and runtime_state is None):
        updated = _update_provider_local_slot(
            database_url,
            provider_row={**provider_row, **updated},
            config_json=_config_with_local_slot(
                provider_config,
                loaded_managed_model_id=None,
                loaded_managed_model_name=None,
                loaded_runtime_model_id=None,
                loaded_local_path=None,
                loaded_source_id=None,
                load_state=_LOCAL_SLOT_STATE_ERROR,
                load_error=str((runtime_state or {}).get("message") or f"runtime_unload_failed:{status_code}"),
            ),
        )
    return _serialize_provider_row({**(platform_repo.get_provider_instance(database_url, provider_instance_id) or {}), **updated})


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


def list_deployment_profiles(database_url: str, config: AuthConfig) -> list[dict[str, Any]]:
    ensure_platform_bootstrap_state(database_url, config)
    items: list[dict[str, Any]] = []
    for profile in platform_repo.list_deployment_profiles(database_url):
        bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=str(profile["id"]))
        items.append(_serialize_deployment_profile(profile, bindings))
    return items


def list_deployment_activation_audit(database_url: str, config: AuthConfig) -> list[dict[str, Any]]:
    ensure_platform_bootstrap_state(database_url, config)
    return [_serialize_activation_audit_row(row) for row in platform_repo.list_deployment_activation_audit(database_url)]


def create_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    payload: dict[str, Any],
    created_by_user_id: int,
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    normalized = _coerce_create_input(database_url, payload)
    resolved_bindings = _resolve_deployment_bindings(database_url, normalized.bindings)

    try:
        created = platform_repo.create_deployment_profile(
            database_url,
            slug=normalized.slug,
            display_name=normalized.display_name,
            description=normalized.description,
            bindings=resolved_bindings,
            created_by_user_id=created_by_user_id,
        )
    except Exception as exc:
        if "duplicate key value violates unique constraint" in str(exc).lower():
            raise PlatformControlPlaneError(
                "deployment_profile_exists",
                "Deployment profile slug already exists",
                status_code=409,
            ) from exc
        raise

    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=str(created["id"]))
    return _serialize_deployment_profile(created, bindings)


def update_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    deployment_profile_id: str,
    payload: dict[str, Any],
    updated_by_user_id: int,
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    existing = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    if existing is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    normalized = _coerce_create_input(database_url, payload)
    resolved_bindings = _resolve_deployment_bindings(database_url, normalized.bindings)
    try:
        updated = platform_repo.update_deployment_profile(
            database_url,
            deployment_profile_id=deployment_profile_id,
            slug=normalized.slug,
            display_name=normalized.display_name,
            description=normalized.description,
            bindings=resolved_bindings,
            updated_by_user_id=updated_by_user_id,
        )
    except Exception as exc:
        if "duplicate key value violates unique constraint" in str(exc).lower():
            raise PlatformControlPlaneError(
                "deployment_profile_exists",
                "Deployment profile slug already exists",
                status_code=409,
            ) from exc
        raise
    if updated is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=deployment_profile_id)
    return _serialize_deployment_profile(updated, bindings)


def clone_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    source_deployment_profile_id: str,
    payload: dict[str, Any],
    created_by_user_id: int,
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    source = platform_repo.get_deployment_profile(database_url, source_deployment_profile_id)
    if source is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    source_bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=source_deployment_profile_id)
    if not source_bindings:
        raise PlatformControlPlaneError(
            "deployment_profile_incomplete",
            "Deployment profile is missing required capability bindings",
            status_code=409,
        )
    slug = str(payload.get("slug", "")).strip().lower()
    display_name = str(payload.get("display_name", "")).strip()
    description = str(payload.get("description", source.get("description", ""))).strip()
    if not slug:
        raise PlatformControlPlaneError("invalid_slug", "slug is required", status_code=400)
    if not display_name:
        raise PlatformControlPlaneError("invalid_display_name", "display_name is required", status_code=400)
    try:
        created = platform_repo.create_deployment_profile(
            database_url,
            slug=slug,
            display_name=display_name,
            description=description,
            bindings=[
                {
                    "capability_key": str(binding["capability_key"]).strip().lower(),
                    "provider_instance_id": str(binding["provider_instance_id"]).strip(),
                    "resources": [
                        dict(resource)
                        for resource in (binding.get("resources") or [])
                        if isinstance(resource, dict)
                    ],
                    "default_resource_id": str(binding.get("default_resource_id") or "").strip() or None,
                    "binding_config": dict(binding.get("binding_config") or {}),
                    "resource_policy": dict(binding.get("resource_policy") or {}),
                }
                for binding in source_bindings
            ],
            created_by_user_id=created_by_user_id,
        )
    except Exception as exc:
        if "duplicate key value violates unique constraint" in str(exc).lower():
            raise PlatformControlPlaneError(
                "deployment_profile_exists",
                "Deployment profile slug already exists",
                status_code=409,
            ) from exc
        raise
    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=str(created["id"]))
    return _serialize_deployment_profile(created, bindings)


def delete_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    deployment_profile_id: str,
) -> None:
    ensure_platform_bootstrap_state(database_url, config)
    existing = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    if existing is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    if bool(existing.get("is_active")):
        raise PlatformControlPlaneError(
            "deployment_profile_active",
            "Active deployment profile cannot be deleted",
            status_code=409,
        )
    deleted = platform_repo.delete_deployment_profile(database_url, deployment_profile_id)
    if not deleted:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)


def activate_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    deployment_profile_id: str,
    activated_by_user_id: int,
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    profile = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    if profile is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)

    bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=deployment_profile_id)
    bound_capabilities = {str(binding["capability_key"]).strip().lower() for binding in bindings}
    missing_capabilities = sorted(REQUIRED_CAPABILITIES - bound_capabilities)
    if missing_capabilities:
        raise PlatformControlPlaneError(
            "deployment_profile_incomplete",
            "Deployment profile is missing required capability bindings",
            status_code=409,
            details={"missing_capabilities": missing_capabilities},
        )

    for binding in bindings:
        if not bool(binding.get("enabled", True)):
            raise PlatformControlPlaneError(
                "deployment_profile_disabled_provider",
                "Deployment profile references a disabled provider instance",
                status_code=409,
                details={"provider_instance_id": str(binding["provider_instance_id"])},
            )

    validation_failures = _validate_deployment_profile_bindings(database_url, config, bindings)
    if validation_failures:
        raise PlatformControlPlaneError(
            "deployment_profile_validation_failed",
            "Deployment profile preflight validation failed",
            status_code=409,
            details={"providers": validation_failures},
        )

    platform_repo.activate_deployment_profile(
        database_url,
        deployment_profile_id=deployment_profile_id,
        activated_by_user_id=activated_by_user_id,
    )
    refreshed = platform_repo.get_deployment_profile(database_url, deployment_profile_id)
    refreshed_bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=deployment_profile_id)
    if refreshed is None:
        raise PlatformControlPlaneError("deployment_profile_not_found", "Deployment profile not found", status_code=404)
    return _serialize_deployment_profile(refreshed, refreshed_bindings)


def validate_provider(database_url: str, *, config: AuthConfig, provider_instance_id: str) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    provider_row = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if provider_row is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)

    binding_row = platform_repo.get_active_binding_for_provider_instance(database_url, provider_instance_id=provider_instance_id)
    binding = ProviderBinding.from_row(binding_row or provider_row)
    if binding.capability_key == CAPABILITY_LLM_INFERENCE:
        adapter = _adapter_from_binding(binding)
        health = adapter.health()
        resources, resources_status = _list_adapter_resources(adapter)
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": {
                "health": health,
                "resources_reachable": 200 <= resources_status < 300,
                "resources_status_code": resources_status,
                "resources": [_serialize_binding_resource(resource) for resource in resources],
            },
        }

    if binding.capability_key == CAPABILITY_EMBEDDINGS:
        adapter = _adapter_from_binding(binding)
        health = adapter.health()
        resources, resources_status = _list_adapter_resources(adapter)
        if not binding.default_resource_id:
            return {
                "provider": _serialize_provider_row(provider_row),
                "validation": {
                    "health": health,
                    "embeddings_reachable": False,
                    "embeddings_status_code": 409,
                    "binding_error": "default_resource_required",
                    "resources_reachable": 200 <= resources_status < 300,
                    "resources_status_code": resources_status,
                    "resources": [_serialize_binding_resource(resource) for resource in resources],
                },
            }
        embeddings_payload, embeddings_status = adapter.embed_texts(texts=["healthcheck"])
        embeddings = embeddings_payload.get("embeddings") if isinstance(embeddings_payload, dict) else []
        embedding_dimension = len(embeddings[0]) if isinstance(embeddings, list) and embeddings else 0
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": {
                "health": health,
                "embeddings_reachable": embeddings_payload is not None and 200 <= embeddings_status < 300,
                "embeddings_status_code": embeddings_status,
                "embedding_dimension": embedding_dimension,
                "resources_reachable": 200 <= resources_status < 300,
                "resources_status_code": resources_status,
                "resources": [_serialize_binding_resource(resource) for resource in resources],
            },
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


def resolve_llm_inference_adapter(
    database_url: str,
    config: AuthConfig,
    *,
    provider_instance_id: str | None = None,
) -> LlmInferenceAdapter:
    binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_LLM_INFERENCE,
        provider_instance_id=provider_instance_id,
    )
    if binding.adapter_kind == "openai_compatible_llm":
        return OpenAICompatibleLlmAdapter(binding)
    raise PlatformControlPlaneError("unsupported_adapter_kind", "Unsupported LLM adapter kind", status_code=500)


def resolve_embeddings_adapter(
    database_url: str,
    config: AuthConfig,
    *,
    provider_instance_id: str | None = None,
) -> EmbeddingsAdapter:
    binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_EMBEDDINGS,
        provider_instance_id=provider_instance_id,
    )
    if binding.adapter_kind == "openai_compatible_embeddings":
        return OpenAICompatibleEmbeddingsAdapter(binding)
    raise PlatformControlPlaneError("unsupported_adapter_kind", "Unsupported embeddings adapter kind", status_code=500)


def resolve_vector_store_adapter(
    database_url: str,
    config: AuthConfig,
    *,
    provider_instance_id: str | None = None,
) -> VectorStoreAdapter:
    binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_VECTOR_STORE,
        provider_instance_id=provider_instance_id,
    )
    if binding.adapter_kind == "weaviate_http":
        return WeaviateVectorStoreAdapter(binding)
    if binding.adapter_kind == "qdrant_http":
        return QdrantVectorStoreAdapter(binding)
    raise PlatformControlPlaneError("unsupported_adapter_kind", "Unsupported vector adapter kind", status_code=500)


def resolve_sandbox_execution_adapter(
    database_url: str,
    config: AuthConfig,
    *,
    provider_instance_id: str | None = None,
) -> SandboxExecutionAdapter:
    binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_SANDBOX_EXECUTION,
        provider_instance_id=provider_instance_id,
    )
    if binding.adapter_kind == "sandbox_http":
        return HttpSandboxExecutionAdapter(binding)
    raise PlatformControlPlaneError("unsupported_adapter_kind", "Unsupported sandbox adapter kind", status_code=500)


def resolve_mcp_runtime_adapter(
    database_url: str,
    config: AuthConfig,
    *,
    provider_instance_id: str | None = None,
) -> McpRuntimeAdapter:
    binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_MCP_RUNTIME,
        provider_instance_id=provider_instance_id,
    )
    if binding.adapter_kind == "mcp_http":
        return HttpMcpRuntimeAdapter(binding)
    raise PlatformControlPlaneError("unsupported_adapter_kind", "Unsupported MCP adapter kind", status_code=500)


def get_active_platform_runtime(database_url: str, config: AuthConfig) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    required_bindings = {
        CAPABILITY_LLM_INFERENCE: _resolve_provider_binding(
            database_url,
            config,
            capability_key=CAPABILITY_LLM_INFERENCE,
            provider_instance_id=None,
        ),
        CAPABILITY_EMBEDDINGS: _resolve_provider_binding(
            database_url,
            config,
            capability_key=CAPABILITY_EMBEDDINGS,
            provider_instance_id=None,
        ),
        CAPABILITY_VECTOR_STORE: _resolve_provider_binding(
            database_url,
            config,
            capability_key=CAPABILITY_VECTOR_STORE,
            provider_instance_id=None,
        ),
    }
    if len({binding.deployment_profile_id for binding in required_bindings.values()}) != 1:
        raise PlatformControlPlaneError(
            "active_deployment_profile_mismatch",
            "Active capability bindings do not point to the same deployment profile",
            status_code=503,
        )

    active_capabilities: dict[str, dict[str, Any]] = {
        capability_key: _serialize_runtime_binding(binding)
        for capability_key, binding in required_bindings.items()
    }
    deployment_binding = next(iter(required_bindings.values()))
    for capability_key in OPTIONAL_CAPABILITIES:
        try:
            optional_binding = _resolve_provider_binding(
                database_url,
                config,
                capability_key=capability_key,
                provider_instance_id=None,
            )
        except PlatformControlPlaneError as exc:
            if exc.code == "active_binding_not_found":
                continue
            raise
        if optional_binding.deployment_profile_id != deployment_binding.deployment_profile_id:
            raise PlatformControlPlaneError(
                "active_deployment_profile_mismatch",
                "Active capability bindings do not point to the same deployment profile",
                status_code=503,
            )
        active_capabilities[capability_key] = _serialize_runtime_binding(optional_binding)

    return {
        "deployment_profile": _serialize_runtime_deployment_profile(deployment_binding),
        "capabilities": active_capabilities,
    }


def get_active_capability_statuses(database_url: str, config: AuthConfig) -> list[dict[str, Any]]:
    ensure_platform_bootstrap_state(database_url, config)
    statuses: list[dict[str, Any]] = []

    llm_adapter = resolve_llm_inference_adapter(database_url, config)
    statuses.append(
        {
            "capability": CAPABILITY_LLM_INFERENCE,
            "provider": {
                "id": llm_adapter.binding.provider_instance_id,
                "slug": llm_adapter.binding.provider_slug,
                "provider_key": llm_adapter.binding.provider_key,
                "display_name": llm_adapter.binding.provider_display_name,
            },
            "deployment_profile": {
                "id": llm_adapter.binding.deployment_profile_id,
                "slug": llm_adapter.binding.deployment_profile_slug,
                "display_name": llm_adapter.binding.deployment_profile_display_name,
            },
            "health": llm_adapter.health(),
        }
    )

    embeddings_adapter = resolve_embeddings_adapter(database_url, config)
    statuses.append(
        {
            "capability": CAPABILITY_EMBEDDINGS,
            "provider": {
                "id": embeddings_adapter.binding.provider_instance_id,
                "slug": embeddings_adapter.binding.provider_slug,
                "provider_key": embeddings_adapter.binding.provider_key,
                "display_name": embeddings_adapter.binding.provider_display_name,
            },
            "deployment_profile": {
                "id": embeddings_adapter.binding.deployment_profile_id,
                "slug": embeddings_adapter.binding.deployment_profile_slug,
                "display_name": embeddings_adapter.binding.deployment_profile_display_name,
            },
            "health": embeddings_adapter.health(),
        }
    )

    vector_adapter = resolve_vector_store_adapter(database_url, config)
    statuses.append(
        {
            "capability": CAPABILITY_VECTOR_STORE,
            "provider": {
                "id": vector_adapter.binding.provider_instance_id,
                "slug": vector_adapter.binding.provider_slug,
                "provider_key": vector_adapter.binding.provider_key,
                "display_name": vector_adapter.binding.provider_display_name,
            },
            "deployment_profile": {
                "id": vector_adapter.binding.deployment_profile_id,
                "slug": vector_adapter.binding.deployment_profile_slug,
                "display_name": vector_adapter.binding.deployment_profile_display_name,
            },
            "health": vector_adapter.health(),
        }
    )

    try:
        sandbox_adapter = resolve_sandbox_execution_adapter(database_url, config)
        statuses.append(
            {
                "capability": CAPABILITY_SANDBOX_EXECUTION,
                "provider": {
                    "id": sandbox_adapter.binding.provider_instance_id,
                    "slug": sandbox_adapter.binding.provider_slug,
                    "provider_key": sandbox_adapter.binding.provider_key,
                    "display_name": sandbox_adapter.binding.provider_display_name,
                },
                "deployment_profile": {
                    "id": sandbox_adapter.binding.deployment_profile_id,
                    "slug": sandbox_adapter.binding.deployment_profile_slug,
                    "display_name": sandbox_adapter.binding.deployment_profile_display_name,
                },
                "health": sandbox_adapter.health(),
            }
        )
    except PlatformControlPlaneError as exc:
        if exc.code != "active_binding_not_found":
            raise

    try:
        mcp_adapter = resolve_mcp_runtime_adapter(database_url, config)
        statuses.append(
            {
                "capability": CAPABILITY_MCP_RUNTIME,
                "provider": {
                    "id": mcp_adapter.binding.provider_instance_id,
                    "slug": mcp_adapter.binding.provider_slug,
                    "provider_key": mcp_adapter.binding.provider_key,
                    "display_name": mcp_adapter.binding.provider_display_name,
                },
                "deployment_profile": {
                    "id": mcp_adapter.binding.deployment_profile_id,
                    "slug": mcp_adapter.binding.deployment_profile_slug,
                    "display_name": mcp_adapter.binding.deployment_profile_display_name,
                },
                "health": mcp_adapter.health(),
            }
        )
    except PlatformControlPlaneError as exc:
        if exc.code != "active_binding_not_found":
            raise

    return statuses


def _resolve_provider_binding(
    database_url: str,
    config: AuthConfig,
    *,
    capability_key: str,
    provider_instance_id: str | None,
) -> ProviderBinding:
    ensure_platform_bootstrap_state(database_url, config)
    if provider_instance_id:
        row = platform_repo.get_active_binding_for_provider_instance(database_url, provider_instance_id=provider_instance_id)
        if row is None:
            row = platform_repo.get_provider_instance(database_url, provider_instance_id)
        if row is None:
            raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
        if str(row["capability_key"]).strip().lower() != capability_key:
            raise PlatformControlPlaneError(
                "provider_capability_mismatch",
                "Provider instance does not implement the requested capability",
                status_code=400,
            )
        return ProviderBinding.from_row(row)

    row = platform_repo.get_active_binding_for_capability(database_url, capability_key=capability_key)
    if row is None:
        raise PlatformControlPlaneError(
            "active_binding_not_found",
            f"No active provider binding for capability '{capability_key}'",
            status_code=503,
        )
    binding = ProviderBinding.from_row(row)
    if not binding.enabled:
        raise PlatformControlPlaneError(
            "active_provider_disabled",
            f"Active provider '{binding.provider_slug}' is disabled",
            status_code=503,
        )
    return binding


def _coerce_create_input(database_url: str, payload: dict[str, Any]) -> DeploymentProfileCreateInput:
    slug = str(payload.get("slug", "")).strip().lower()
    display_name = str(payload.get("display_name", "")).strip()
    description = str(payload.get("description", "")).strip()
    raw_bindings = payload.get("bindings")

    if not slug:
        raise PlatformControlPlaneError("invalid_slug", "slug is required", status_code=400)
    if not display_name:
        raise PlatformControlPlaneError("invalid_display_name", "display_name is required", status_code=400)
    if not isinstance(raw_bindings, list) or not raw_bindings:
        raise PlatformControlPlaneError("invalid_bindings", "bindings must be a non-empty array", status_code=400)

    bindings: list[DeploymentBindingInput] = []
    for item in raw_bindings:
        if not isinstance(item, dict):
            raise PlatformControlPlaneError("invalid_binding", "Each binding must be an object", status_code=400)
        capability_key = str(item.get("capability", "")).strip().lower()
        provider_instance_id = str(item.get("provider_id", "")).strip()
        if capability_key not in _known_capability_keys(database_url):
            raise PlatformControlPlaneError("invalid_capability", "Unsupported capability", status_code=400)
        if not provider_instance_id:
            raise PlatformControlPlaneError("invalid_provider_id", "provider_id is required", status_code=400)
        binding_config = item.get("config") if isinstance(item.get("config"), dict) else {}
        resource_policy = item.get("resource_policy") if isinstance(item.get("resource_policy"), dict) else {}
        resources = _coerce_binding_resources(item.get("resources"))
        default_resource_id = str(item.get("default_resource_id", "")).strip() or None
        bindings.append(
            DeploymentBindingInput(
                capability_key=capability_key,
                provider_instance_id=provider_instance_id,
                resources=resources,
                default_resource_id=default_resource_id,
                binding_config=dict(binding_config),
                resource_policy=dict(resource_policy),
            )
        )

    return DeploymentProfileCreateInput(
        slug=slug,
        display_name=display_name,
        description=description,
        bindings=bindings,
    )


def _coerce_provider_input(
    database_url: str,
    payload: dict[str, Any],
    *,
    is_update: bool,
    existing_provider: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_key = (
        str(existing_provider["provider_key"]).strip().lower()
        if existing_provider is not None
        else str(payload.get("provider_key", "")).strip().lower()
    )
    slug = str(payload.get("slug", existing_provider["slug"] if existing_provider else "")).strip().lower()
    display_name = str(payload.get("display_name", existing_provider["display_name"] if existing_provider else "")).strip()
    description = str(payload.get("description", existing_provider["description"] if existing_provider else "")).strip()
    endpoint_url = str(payload.get("endpoint_url", existing_provider["endpoint_url"] if existing_provider else "")).strip()
    healthcheck_url = str(payload.get("healthcheck_url", existing_provider.get("healthcheck_url", "") if existing_provider else "")).strip() or None
    enabled = payload.get("enabled", existing_provider["enabled"] if existing_provider is not None else True)
    raw_config = payload.get("config", _serialize_provider_row(existing_provider)["config"] if existing_provider is not None else {})
    raw_secret_refs = payload.get("secret_refs", _serialize_provider_row(existing_provider)["secret_refs"] if existing_provider is not None else {})

    if not provider_key:
        raise PlatformControlPlaneError("invalid_provider_key", "provider_key is required", status_code=400)
    if platform_repo.get_provider_family(database_url, provider_key) is None:
        raise PlatformControlPlaneError("provider_family_not_found", "Provider family not found", status_code=404)
    if not slug:
        raise PlatformControlPlaneError("invalid_slug", "slug is required", status_code=400)
    if not display_name:
        raise PlatformControlPlaneError("invalid_display_name", "display_name is required", status_code=400)
    if not endpoint_url:
        raise PlatformControlPlaneError("invalid_endpoint_url", "endpoint_url is required", status_code=400)
    if isinstance(enabled, bool):
        normalized_enabled = enabled
    else:
        raise PlatformControlPlaneError("invalid_enabled", "enabled must be a boolean", status_code=400)
    config = _coerce_json_object(raw_config, error_code="invalid_provider_config", message="config must be an object")
    secret_refs = _coerce_secret_refs(raw_secret_refs)
    return {
        "provider_key": provider_key,
        "slug": slug,
        "display_name": display_name,
        "description": description,
        "endpoint_url": endpoint_url,
        "healthcheck_url": healthcheck_url,
        "enabled": normalized_enabled,
        "config": config,
        "secret_refs": secret_refs,
    }


def _coerce_json_object(raw: Any, *, error_code: str, message: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise PlatformControlPlaneError(error_code, message, status_code=400)
    return dict(raw)


def _coerce_secret_refs(raw: Any) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise PlatformControlPlaneError("invalid_secret_refs", "secret_refs must be an object", status_code=400)
    normalized: dict[str, str] = {}
    for key, value in raw.items():
        normalized_key = str(key).strip()
        normalized_value = str(value).strip()
        if not normalized_key or not normalized_value:
            raise PlatformControlPlaneError("invalid_secret_refs", "secret_refs must contain non-empty string values", status_code=400)
        normalized[normalized_key] = normalized_value
    return normalized


def _provider_storage_config(config: dict[str, Any], secret_refs: dict[str, str]) -> dict[str, Any]:
    stored = dict(config)
    if secret_refs:
        stored["secret_refs"] = dict(secret_refs)
    else:
        stored.pop("secret_refs", None)
    return stored


def _normalized_optional_slot_string(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.lower() in {"none", "null"}:
        return None
    return normalized


def _local_slot_payload_from_config(config: dict[str, Any]) -> dict[str, Any]:
    loaded_managed_model_id = _normalized_optional_slot_string(config.get("loaded_managed_model_id"))
    loaded_managed_model_name = _normalized_optional_slot_string(config.get("loaded_managed_model_name"))
    loaded_runtime_model_id = _normalized_optional_slot_string(config.get("loaded_runtime_model_id"))
    loaded_local_path = _normalized_optional_slot_string(config.get("loaded_local_path"))
    loaded_source_id = _normalized_optional_slot_string(config.get("loaded_source_id"))
    load_error = _normalized_optional_slot_string(config.get("load_error"))
    raw_state = str(config.get("load_state") or "").strip().lower()
    if loaded_managed_model_id:
        load_state = raw_state or _LOCAL_SLOT_STATE_RECONCILING
    elif raw_state == _LOCAL_SLOT_STATE_ERROR:
        load_state = _LOCAL_SLOT_STATE_ERROR
    else:
        load_state = _LOCAL_SLOT_STATE_EMPTY
    return {
        "loaded_managed_model_id": loaded_managed_model_id,
        "loaded_managed_model_name": loaded_managed_model_name,
        "loaded_runtime_model_id": loaded_runtime_model_id,
        "loaded_local_path": loaded_local_path,
        "loaded_source_id": loaded_source_id,
        "load_state": load_state,
        "load_error": load_error,
    }


def _config_with_local_slot(
    config: dict[str, Any],
    *,
    loaded_managed_model_id: str | None,
    loaded_managed_model_name: str | None,
    loaded_runtime_model_id: str | None,
    loaded_local_path: str | None,
    loaded_source_id: str | None,
    load_state: str,
    load_error: str | None = None,
) -> dict[str, Any]:
    updated = {
        key: value
        for key, value in dict(config).items()
        if key not in _LOCAL_SLOT_CONFIG_KEYS
    }
    if loaded_managed_model_id:
        updated["loaded_managed_model_id"] = loaded_managed_model_id
    if loaded_managed_model_name:
        updated["loaded_managed_model_name"] = loaded_managed_model_name
    if loaded_runtime_model_id:
        updated["loaded_runtime_model_id"] = loaded_runtime_model_id
    if loaded_local_path:
        updated["loaded_local_path"] = loaded_local_path
    if loaded_source_id:
        updated["loaded_source_id"] = loaded_source_id
    updated["load_state"] = load_state
    if load_error:
        updated["load_error"] = load_error
    return updated


def _is_local_model_slot_provider(row: dict[str, Any]) -> bool:
    capability_key = str(row.get("capability_key") or "").strip().lower()
    provider_key = str(row.get("provider_key") or "").strip().lower()
    return capability_key in _MODEL_BEARING_CAPABILITIES and provider_key not in _CLOUD_PROVIDER_KEYS


def _runtime_admin_base_url(provider_row: dict[str, Any]) -> str | None:
    config = provider_row.get("config_json") if isinstance(provider_row.get("config_json"), dict) else {}
    runtime_admin_base_url = str(config.get("runtime_admin_base_url") or "").strip()
    if runtime_admin_base_url:
        return runtime_admin_base_url.rstrip("/")
    runtime_base_url = str(config.get("runtime_base_url") or "").strip()
    if runtime_base_url:
        return runtime_base_url.rstrip("/").removesuffix("/v1")
    return None


def _runtime_admin_state(provider_row: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    runtime_admin_base_url = _runtime_admin_base_url(provider_row)
    if not runtime_admin_base_url:
        return None, 404
    payload, status_code = http_json_request(
        f"{runtime_admin_base_url}/v1/admin/runtime-state",
        method="GET",
        timeout_seconds=5.0,
    )
    if isinstance(payload, dict) and isinstance(payload.get("detail"), dict):
        detail = payload.get("detail")
        return dict(detail), status_code
    return (dict(payload) if isinstance(payload, dict) else None), status_code


def _runtime_admin_load_model(
    provider_row: dict[str, Any],
    *,
    runtime_model_id: str,
    local_path: str,
    managed_model_id: str,
    display_name: str,
) -> tuple[dict[str, Any] | None, int]:
    runtime_admin_base_url = _runtime_admin_base_url(provider_row)
    if not runtime_admin_base_url:
        return None, 404
    payload, status_code = http_json_request(
        f"{runtime_admin_base_url}/v1/admin/load-model",
        method="POST",
        payload={
            "runtime_model_id": runtime_model_id,
            "local_path": local_path,
            "managed_model_id": managed_model_id,
            "display_name": display_name,
        },
        timeout_seconds=8.0,
    )
    if isinstance(payload, dict) and isinstance(payload.get("detail"), dict):
        detail = payload.get("detail")
        return dict(detail), status_code
    return (dict(payload) if isinstance(payload, dict) else None), status_code


def _runtime_admin_unload_model(provider_row: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    runtime_admin_base_url = _runtime_admin_base_url(provider_row)
    if not runtime_admin_base_url:
        return None, 404
    payload, status_code = http_json_request(
        f"{runtime_admin_base_url}/v1/admin/unload-model",
        method="POST",
        timeout_seconds=8.0,
    )
    if isinstance(payload, dict) and isinstance(payload.get("detail"), dict):
        detail = payload.get("detail")
        return dict(detail), status_code
    return (dict(payload) if isinstance(payload, dict) else None), status_code


def _local_slot_with_runtime_state(slot: dict[str, Any], runtime_state: dict[str, Any] | None, status_code: int) -> dict[str, Any]:
    resolved = dict(slot)
    if not isinstance(runtime_state, dict):
        if resolved.get("loaded_managed_model_id"):
            resolved["load_state"] = _LOCAL_SLOT_STATE_ERROR
            if not resolved.get("load_error"):
                resolved["load_error"] = f"runtime_state_unavailable:{status_code}"
        return resolved
    managed_model_id = _normalized_optional_slot_string(runtime_state.get("managed_model_id"))
    display_name = _normalized_optional_slot_string(runtime_state.get("display_name"))
    runtime_model_id = _normalized_optional_slot_string(runtime_state.get("runtime_model_id"))
    local_path = _normalized_optional_slot_string(runtime_state.get("local_path"))
    last_error = _normalized_optional_slot_string(runtime_state.get("last_error"))
    raw_state = str(runtime_state.get("load_state") or "").strip().lower()
    if managed_model_id and not resolved.get("loaded_managed_model_id"):
        resolved["loaded_managed_model_id"] = managed_model_id
    if display_name and not resolved.get("loaded_managed_model_name"):
        resolved["loaded_managed_model_name"] = display_name
    if runtime_model_id:
        resolved["loaded_runtime_model_id"] = runtime_model_id
    if local_path:
        resolved["loaded_local_path"] = local_path
    if raw_state in {
        _LOCAL_SLOT_STATE_EMPTY,
        _LOCAL_SLOT_STATE_LOADING,
        _LOCAL_SLOT_STATE_RECONCILING,
        _LOCAL_SLOT_STATE_LOADED,
        _LOCAL_SLOT_STATE_ERROR,
    }:
        resolved["load_state"] = raw_state
    if last_error:
        resolved["load_error"] = last_error
    elif resolved.get("load_state") == _LOCAL_SLOT_STATE_LOADED:
        resolved["load_error"] = None
    return resolved


def _update_provider_local_slot(
    database_url: str,
    *,
    provider_row: dict[str, Any],
    config_json: dict[str, Any],
) -> dict[str, Any]:
    updated = platform_repo.update_provider_instance(
        database_url,
        provider_instance_id=str(provider_row.get("id") or "").strip(),
        slug=str(provider_row.get("slug") or "").strip(),
        display_name=str(provider_row.get("display_name") or "").strip(),
        description=str(provider_row.get("description") or "").strip(),
        endpoint_url=str(provider_row.get("endpoint_url") or "").strip(),
        healthcheck_url=str(provider_row.get("healthcheck_url") or "").strip() or None,
        enabled=bool(provider_row.get("enabled")),
        config_json=config_json,
    )
    if updated is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
    return updated


def _runtime_model_entries_for_capability(
    capability_key: str,
    payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw_items = payload.get("data")
    if not isinstance(raw_items, list):
        return []
    normalized_capability = capability_key.strip().lower()
    filtered: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        capabilities = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
        supports_text = bool(capabilities.get("text"))
        supports_embeddings = bool(capabilities.get("embeddings"))
        include_item = False
        if normalized_capability == CAPABILITY_LLM_INFERENCE:
            include_item = supports_text
        elif normalized_capability == CAPABILITY_EMBEDDINGS:
            include_item = supports_embeddings
        if include_item and str(item.get("id") or "").strip():
            filtered.append(dict(item))
    return filtered


def _provider_runtime_inventory(provider_row: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    if not _is_local_model_slot_provider(provider_row):
        return [], 200
    binding = ProviderBinding.from_row(provider_row)
    try:
        adapter = _adapter_from_binding(binding)
    except PlatformControlPlaneError:
        return [], 500
    list_models = getattr(adapter, "list_models", None)
    if not callable(list_models):
        return [], 200
    try:
        payload, status_code = list_models()
    except PlatformControlPlaneError:
        return [], 502
    return _runtime_model_entries_for_capability(binding.capability_key, payload), status_code


def _effective_local_slot(provider_row: dict[str, Any]) -> dict[str, Any]:
    config = dict(provider_row.get("config_json") or {})
    slot = _local_slot_payload_from_config(config)
    if not _is_local_model_slot_provider(provider_row):
        return slot
    runtime_state, runtime_status = _runtime_admin_state(provider_row)
    if runtime_state is not None:
        slot = _local_slot_with_runtime_state(slot, runtime_state, runtime_status)
    runtime_items, status_code = _provider_runtime_inventory(provider_row)
    loaded_runtime_model_id = str(slot.get("loaded_runtime_model_id") or "").strip()
    if not loaded_runtime_model_id:
        return slot
    available_ids = {
        str(item.get("id") or "").strip()
        for item in runtime_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if loaded_runtime_model_id in available_ids:
        slot["load_state"] = _LOCAL_SLOT_STATE_LOADED
        slot["load_error"] = None
        return slot
    if slot.get("load_state") == _LOCAL_SLOT_STATE_LOADING:
        return slot
    if 200 <= status_code < 300:
        slot["load_state"] = _LOCAL_SLOT_STATE_RECONCILING
        return slot
    slot["load_state"] = _LOCAL_SLOT_STATE_ERROR
    if not slot.get("load_error"):
        slot["load_error"] = f"runtime_inventory_unavailable:{status_code}"
    return slot


def _resolve_deployment_bindings(database_url: str, bindings: list[DeploymentBindingInput]) -> list[dict[str, Any]]:
    seen_capabilities: set[str] = set()
    resolved_bindings: list[dict[str, Any]] = []
    for binding in bindings:
        if binding.capability_key in seen_capabilities:
            raise PlatformControlPlaneError(
                "duplicate_capability_binding",
                f"Capability '{binding.capability_key}' is bound more than once",
                status_code=400,
            )
        provider = platform_repo.get_provider_instance(database_url, binding.provider_instance_id)
        if provider is None:
            raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
        if str(provider["capability_key"]).strip().lower() != binding.capability_key:
            raise PlatformControlPlaneError(
                "provider_capability_mismatch",
                "Provider instance does not implement the requested capability",
                status_code=400,
            )
        resolved_bindings.append(
            {
                "capability_key": binding.capability_key,
                "provider_instance_id": binding.provider_instance_id,
                **_validate_binding_resources(
                    database_url,
                    provider_row=provider,
                    capability_key=binding.capability_key,
                    resources=binding.resources,
                    default_resource_id=binding.default_resource_id,
                    resource_policy=binding.resource_policy,
                ),
                "binding_config": binding.binding_config,
                "resource_policy": binding.resource_policy,
            }
        )
        seen_capabilities.add(binding.capability_key)
    return resolved_bindings


def _validate_deployment_profile_bindings(
    database_url: str,
    config: AuthConfig,
    bindings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    del database_url, config
    failures: list[dict[str, Any]] = []
    for binding in bindings:
        provider_binding = ProviderBinding.from_row(binding)
        validation = _validate_provider_binding(provider_binding)
        result = {
            "provider": {
                "id": provider_binding.provider_instance_id,
                "slug": provider_binding.provider_slug or provider_binding.provider_instance_id,
                "provider_key": provider_binding.provider_key,
                "display_name": provider_binding.provider_display_name,
            },
            "validation": validation,
        }
        health = dict(validation.get("health") or {})
        reachable = bool(health.get("reachable"))
        resources_reachable = validation.get("resources_reachable")
        embeddings_reachable = validation.get("embeddings_reachable")
        binding_error = str(validation.get("binding_error") or "").strip() or None
        resource_errors = validation.get("resource_errors")
        capability = str(binding.get("capability_key", "")).strip().lower()
        failed = (
            not reachable
            or (capability in {CAPABILITY_LLM_INFERENCE, CAPABILITY_VECTOR_STORE} and resources_reachable is False)
            or (capability == CAPABILITY_EMBEDDINGS and embeddings_reachable is False)
            or (capability == CAPABILITY_SANDBOX_EXECUTION and validation.get("execute_reachable") is False)
            or (capability == CAPABILITY_MCP_RUNTIME and validation.get("invoke_reachable") is False)
            or bool(binding_error)
            or (isinstance(resource_errors, list) and len(resource_errors) > 0)
        )
        if failed:
            failures.append(
                {
                    "provider": result.get("provider"),
                    "validation": validation,
                }
            )
    return failures


def _adapter_from_binding(binding: ProviderBinding) -> Any:
    if binding.adapter_kind == "openai_compatible_llm":
        return OpenAICompatibleLlmAdapter(binding)
    if binding.adapter_kind == "openai_compatible_embeddings":
        return OpenAICompatibleEmbeddingsAdapter(binding)
    if binding.adapter_kind == "weaviate_http":
        return WeaviateVectorStoreAdapter(binding)
    if binding.adapter_kind == "qdrant_http":
        return QdrantVectorStoreAdapter(binding)
    if binding.adapter_kind == "sandbox_http":
        return HttpSandboxExecutionAdapter(binding)
    if binding.adapter_kind == "mcp_http":
        return HttpMcpRuntimeAdapter(binding)
    raise PlatformControlPlaneError("unsupported_adapter_kind", "Unsupported adapter kind", status_code=500)


def _list_adapter_resources(adapter: Any) -> tuple[list[dict[str, Any]], int]:
    list_resources = getattr(adapter, "list_resources", None)
    if callable(list_resources):
        payload = list_resources()
        if isinstance(payload, tuple) and len(payload) == 2 and isinstance(payload[0], list):
            return payload
    list_models = getattr(adapter, "list_models", None)
    if callable(list_models):
        payload, status_code = list_models()
        items = _runtime_model_entries_for_capability(
            str(getattr(adapter.binding, "capability_key", "")).strip().lower(),
            payload if isinstance(payload, dict) else None,
        )
        return [
            {
                "id": str(item.get("id") or "").strip(),
                "resource_kind": "model",
                "ref_type": "provider_resource",
                "managed_model_id": None,
                "provider_resource_id": str(item.get("id") or "").strip() or None,
                "display_name": item.get("id"),
                "metadata": {},
            }
            for item in items
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ], status_code
    return [], 200


def _validate_provider_binding(binding: ProviderBinding) -> dict[str, Any]:
    adapter = _adapter_from_binding(binding)
    if binding.capability_key == CAPABILITY_LLM_INFERENCE:
        health = adapter.health()
        resources, resources_status = _list_adapter_resources(adapter)
        resource_errors = _validate_bound_resources_against_provider_inventory(
            binding,
            resources if 200 <= resources_status < 300 else None,
        )
        return {
            "health": health,
            "resources_reachable": 200 <= resources_status < 300,
            "resources_status_code": resources_status,
            "resources": [_serialize_binding_resource(resource) for resource in resources],
            "resource_errors": resource_errors,
        }
    if binding.capability_key == CAPABILITY_EMBEDDINGS:
        health = adapter.health()
        resources, resources_status = _list_adapter_resources(adapter)
        if not binding.default_resource_id:
            return {
                "health": health,
                "embeddings_reachable": False,
                "embeddings_status_code": 409,
                "binding_error": "default_resource_required",
                "resources_reachable": 200 <= resources_status < 300,
                "resources_status_code": resources_status,
                "resources": [_serialize_binding_resource(resource) for resource in resources],
            }
        embeddings_payload, embeddings_status = adapter.embed_texts(texts=["healthcheck"])
        embeddings = embeddings_payload.get("embeddings") if isinstance(embeddings_payload, dict) else []
        embedding_dimension = len(embeddings[0]) if isinstance(embeddings, list) and embeddings else 0
        return {
            "health": health,
            "embeddings_reachable": embeddings_payload is not None and 200 <= embeddings_status < 300,
            "embeddings_status_code": embeddings_status,
            "embedding_dimension": embedding_dimension,
            "resources_reachable": 200 <= resources_status < 300,
            "resources_status_code": resources_status,
            "resources": [_serialize_binding_resource(resource) for resource in resources],
        }
    if binding.capability_key == CAPABILITY_VECTOR_STORE:
        resources, resources_status = _list_adapter_resources(adapter)
        return {
            "health": adapter.health(),
            "resources_reachable": 200 <= resources_status < 300,
            "resources_status_code": resources_status,
            "resources": [_serialize_binding_resource(resource) for resource in resources],
        }
    if binding.capability_key == CAPABILITY_SANDBOX_EXECUTION:
        dry_run_payload, dry_run_status = adapter.execute_dry_run()
        return {
            "health": adapter.health(),
            "execute_reachable": dry_run_payload is not None and 200 <= dry_run_status < 300,
            "execute_status_code": dry_run_status,
        }
    if binding.capability_key == CAPABILITY_MCP_RUNTIME:
        invoke_payload, invoke_status = adapter.invoke(
            tool_name=str(binding.config.get("healthcheck_tool_name", "web_search")),
            arguments={"query": "healthcheck", "top_k": 1},
            request_metadata={"validation": True},
        )
        return {
            "health": adapter.health(),
            "invoke_reachable": invoke_payload is not None and 200 <= invoke_status < 300,
            "invoke_status_code": invoke_status,
        }
    raise PlatformControlPlaneError("unsupported_capability", "Unsupported capability", status_code=400)


def _coerce_binding_resources(raw_resources: Any) -> list[dict[str, Any]]:
    if raw_resources is None:
        return []
    if not isinstance(raw_resources, list):
        raise PlatformControlPlaneError("invalid_resources", "resources must be an array", status_code=400)
    normalized: list[dict[str, Any]] = []
    for item in raw_resources:
        if not isinstance(item, dict):
            raise PlatformControlPlaneError("invalid_resource", "Each resource must be an object", status_code=400)
        resource_id = str(item.get("id") or item.get("managed_model_id") or item.get("provider_resource_id") or "").strip()
        if not resource_id:
            raise PlatformControlPlaneError("invalid_resource_id", "resource.id is required", status_code=400)
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        normalized.append(
            {
                "id": resource_id,
                "resource_kind": str(item.get("resource_kind") or "").strip().lower(),
                "ref_type": str(item.get("ref_type") or "").strip().lower(),
                "managed_model_id": str(item.get("managed_model_id") or "").strip() or None,
                "provider_resource_id": str(item.get("provider_resource_id") or "").strip() or None,
                "display_name": str(item.get("display_name") or "").strip() or None,
                "metadata": dict(metadata),
            }
        )
    return normalized


def _validate_binding_resources(
    database_url: str,
    *,
    provider_row: dict[str, Any],
    capability_key: str,
    resources: list[dict[str, Any]],
    default_resource_id: str | None,
    resource_policy: dict[str, Any],
) -> dict[str, Any]:
    normalized_capability = capability_key.strip().lower()
    normalized_resources = _normalize_binding_resources(resources)
    normalized_default = str(default_resource_id or "").strip() or None
    requires_models = normalized_capability in _MODEL_BEARING_CAPABILITIES
    if not requires_models:
        return _validate_non_model_resources(
            capability_key=normalized_capability,
            resources=normalized_resources,
            default_resource_id=normalized_default,
            resource_policy=resource_policy,
        )
    if not normalized_resources:
        raise PlatformControlPlaneError(
            "resource_required",
            f"{normalized_capability} bindings require at least one bound model resource",
            status_code=400,
        )
    if not normalized_default:
        raise PlatformControlPlaneError(
            "default_resource_required",
            "default_resource_id is required when model resources are present",
            status_code=400,
        )
    if normalized_default not in {str(resource.get("id") or "").strip() for resource in normalized_resources}:
        raise PlatformControlPlaneError(
            "default_resource_not_bound",
            "default_resource_id must be present in resources",
            status_code=400,
            details={"default_resource_id": normalized_default},
        )

    validated_resources: list[dict[str, Any]] = []
    for resource in normalized_resources:
        validated_resources.append(
            _validate_model_binding_resource(
            database_url,
            provider_row=provider_row,
            capability_key=normalized_capability,
            resource=resource,
        )
        )
    return {
        "resources": validated_resources,
        "default_resource_id": normalized_default,
    }


def _validate_non_model_resources(
    *,
    capability_key: str,
    resources: list[dict[str, Any]],
    default_resource_id: str | None,
    resource_policy: dict[str, Any],
) -> dict[str, Any]:
    if capability_key != CAPABILITY_VECTOR_STORE:
        if resources or default_resource_id or resource_policy:
            raise PlatformControlPlaneError(
                "resources_not_allowed",
                f"Capability '{capability_key}' does not support deployment resources",
                status_code=400,
            )
        return {"resources": [], "default_resource_id": None}
    selection_mode = str(resource_policy.get("selection_mode") or _VECTOR_SELECTION_EXPLICIT).strip().lower()
    if selection_mode == _VECTOR_SELECTION_EXPLICIT:
        if not resources:
            raise PlatformControlPlaneError(
                "resource_required",
                "Vector store bindings in explicit mode require at least one bound resource",
                status_code=400,
            )
        if default_resource_id and default_resource_id not in {str(resource.get("id") or "").strip() for resource in resources}:
            raise PlatformControlPlaneError(
                "default_resource_not_bound",
                "default_resource_id must be present in resources",
                status_code=400,
                details={"default_resource_id": default_resource_id},
            )
        validated = []
        for resource in resources:
            validated.append(
                {
                    "id": str(resource.get("id") or "").strip(),
                    "resource_kind": str(resource.get("resource_kind") or "index").strip().lower() or "index",
                    "ref_type": "provider_resource",
                    "managed_model_id": None,
                    "provider_resource_id": str(resource.get("provider_resource_id") or resource.get("id") or "").strip(),
                    "display_name": str(resource.get("display_name") or resource.get("id") or "").strip(),
                    "metadata": dict(resource.get("metadata") or {}),
                }
            )
        return {"resources": validated, "default_resource_id": default_resource_id}
    if selection_mode == _VECTOR_SELECTION_DYNAMIC_NAMESPACE:
        namespace_prefix = str(resource_policy.get("namespace_prefix") or "").strip()
        if not namespace_prefix:
            raise PlatformControlPlaneError(
                "invalid_resource_policy",
                "vector_store dynamic_namespace bindings require resource_policy.namespace_prefix",
                status_code=400,
            )
        if resources or default_resource_id:
            raise PlatformControlPlaneError(
                "resources_not_allowed",
                "vector_store dynamic_namespace bindings must not define explicit resources or a default resource",
                status_code=400,
            )
        return {"resources": [], "default_resource_id": None}
    raise PlatformControlPlaneError(
        "invalid_resource_policy",
        "resource_policy.selection_mode is unsupported",
        status_code=400,
        details={"selection_mode": selection_mode},
    )


def _normalize_binding_resources(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[str] = []
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for resource in resources:
        normalized_resource_id = str(resource.get("id") or "").strip()
        if not normalized_resource_id:
            continue
        if normalized_resource_id in seen:
            raise PlatformControlPlaneError(
                "duplicate_resource",
                "A deployment binding cannot include the same resource more than once",
                status_code=400,
                details={"resource_id": normalized_resource_id},
            )
        seen.add(normalized_resource_id)
        items.append(dict(resource))
    return items


def _validate_model_binding_resource(
    database_url: str,
    *,
    provider_row: dict[str, Any],
    capability_key: str,
    resource: dict[str, Any],
) -> dict[str, Any]:
    managed_model_id = str(resource.get("managed_model_id") or resource.get("id") or "").strip()
    model_row = get_model_by_id(database_url, managed_model_id)
    if model_row is None:
        raise PlatformControlPlaneError(
            "resource_not_found",
            "Managed model resource was not found",
            status_code=404,
            details={"resource_id": resource.get("id"), "managed_model_id": managed_model_id},
        )

    expected_task_key = _TASK_KEY_LLM if capability_key == CAPABILITY_LLM_INFERENCE else _TASK_KEY_EMBEDDINGS
    task_key = str(model_row.get("task_key", "")).strip().lower()
    if task_key != expected_task_key:
        raise PlatformControlPlaneError(
            "resource_task_mismatch",
            f"{capability_key} bindings require a model with task_key={expected_task_key}",
            status_code=400,
            details={"resource_id": resource.get("id"), "managed_model_id": managed_model_id, "task_key": model_row.get("task_key")},
        )
    if str(model_row.get("lifecycle_state", "")).strip().lower() != "active":
        raise PlatformControlPlaneError(
            "resource_not_active",
            f"{capability_key} bindings require an active model",
            status_code=409,
            details={"resource_id": resource.get("id"), "managed_model_id": managed_model_id},
        )
    if not bool(model_row.get("is_validation_current")) or str(model_row.get("last_validation_status", "")).strip().lower() != "success":
        raise PlatformControlPlaneError(
            "resource_not_validated",
            f"{capability_key} bindings require a validated model",
            status_code=409,
            details={"resource_id": resource.get("id"), "managed_model_id": managed_model_id},
        )

    if _is_cloud_provider_row(provider_row):
        if str(model_row.get("backend_kind", "")).strip().lower() != "external_api":
            raise PlatformControlPlaneError(
                "resource_backend_mismatch",
                "Cloud providers require an external_api model",
                status_code=400,
                details={"resource_id": resource.get("id"), "managed_model_id": managed_model_id},
            )
        if not str(model_row.get("provider_model_id", "")).strip():
            raise PlatformControlPlaneError(
                "provider_resource_id_required",
                "Cloud providers require provider_model_id on the selected model",
                status_code=400,
                details={"resource_id": resource.get("id"), "managed_model_id": managed_model_id},
            )
        provider_resource_id = str(model_row.get("provider_model_id", "")).strip()
        return _build_model_binding_resource(model_row, provider_resource_id=provider_resource_id)

    backend_kind = str(model_row.get("backend_kind", "")).strip().lower()
    availability = str(model_row.get("availability", "")).strip().lower()
    if backend_kind != "local" and availability != "offline_ready":
        raise PlatformControlPlaneError(
            "resource_backend_mismatch",
            "Local providers require a local or offline-ready model",
            status_code=400,
            details={"resource_id": resource.get("id"), "managed_model_id": managed_model_id},
        )
    runtime_model_identifier = _runtime_model_identifier(model_row)
    if not runtime_model_identifier:
        raise PlatformControlPlaneError(
            "provider_resource_id_required",
            "Selected model must define provider_model_id or local_path",
            status_code=400,
            details={"resource_id": resource.get("id"), "managed_model_id": managed_model_id},
        )
    return _build_model_binding_resource(model_row, provider_resource_id=runtime_model_identifier)


def _build_model_binding_resource(model_row: dict[str, Any], *, provider_resource_id: str) -> dict[str, Any]:
    managed_model_id = str(model_row.get("id") or model_row.get("model_id") or "").strip()
    return {
        "id": managed_model_id,
        "resource_kind": "model",
        "ref_type": "managed_model",
        "managed_model_id": managed_model_id,
        "provider_resource_id": provider_resource_id,
        "display_name": str(model_row.get("name") or managed_model_id).strip(),
        "metadata": {
            "name": model_row.get("name"),
            "provider": model_row.get("provider"),
            "backend": model_row.get("backend_kind"),
            "task_key": model_row.get("task_key"),
            "provider_model_id": model_row.get("provider_model_id"),
            "local_path": model_row.get("local_path"),
            "source_id": model_row.get("source_id"),
            "availability": model_row.get("availability"),
        },
    }


def _validate_bound_resources_against_provider_inventory(
    binding: ProviderBinding,
    provider_resources: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not binding.resources:
        return [{"code": "resource_required", "message": "At least one resource is required"}]
    if provider_resources is None:
        return []
    available_ids = {
        str(item.get("provider_resource_id") or item.get("id") or "").strip()
        for item in provider_resources
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    if not available_ids:
        return []
    errors: list[dict[str, Any]] = []
    for resource in binding.resources:
        runtime_identifier = _runtime_identifier_for_resource(resource)
        if runtime_identifier and runtime_identifier not in available_ids:
            errors.append(
                {
                    "code": "resource_not_exposed",
                    "resource_id": resource.get("id"),
                    "provider_resource_id": runtime_identifier,
                }
            )
    return errors


def _runtime_model_identifier(model_row: dict[str, Any]) -> str:
    provider_model_id = str(model_row.get("provider_model_id", "")).strip()
    local_path = str(model_row.get("local_path", "")).strip()
    return provider_model_id or local_path


def _is_cloud_provider_row(provider_row: dict[str, Any]) -> bool:
    provider_key = str(provider_row.get("provider_key", "")).strip().lower()
    return provider_key in _CLOUD_PROVIDER_KEYS


def _runtime_identifier_for_resource(resource: dict[str, Any]) -> str:
    provider_resource_id = str(resource.get("provider_resource_id", "")).strip()
    if provider_resource_id:
        return provider_resource_id
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    provider_model_id = str(metadata.get("provider_model_id", "")).strip()
    local_path = str(metadata.get("local_path", "")).strip()
    source_id = str(metadata.get("source_id", "")).strip()
    return provider_model_id or local_path or source_id


def _serialize_binding_resource(resource: dict[str, Any]) -> dict[str, Any]:
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    return {
        "id": str(resource.get("id") or "").strip(),
        "resource_kind": str(resource.get("resource_kind") or "").strip() or None,
        "ref_type": str(resource.get("ref_type") or "").strip() or None,
        "managed_model_id": str(resource.get("managed_model_id") or "").strip() or None,
        "provider_resource_id": str(resource.get("provider_resource_id") or "").strip() or None,
        "display_name": resource.get("display_name") or metadata.get("name"),
        "metadata": dict(metadata),
        "name": metadata.get("name"),
        "provider": metadata.get("provider"),
        "backend": metadata.get("backend"),
        "task_key": metadata.get("task_key"),
        "provider_model_id": metadata.get("provider_model_id"),
        "local_path": metadata.get("local_path"),
        "source_id": metadata.get("source_id"),
        "availability": metadata.get("availability"),
    }


def _serialize_provider_family_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_key": row["provider_key"],
        "capability": row["capability_key"],
        "adapter_kind": row["adapter_kind"],
        "display_name": row["display_name"],
        "description": row["description"],
    }


def _serialize_provider_row(row: dict[str, Any]) -> dict[str, Any]:
    raw_config = dict(row.get("config_json") or {})
    local_slot = _effective_local_slot({**row, "config_json": raw_config})
    config = {
        key: value
        for key, value in raw_config.items()
        if key not in _LOCAL_SLOT_CONFIG_KEYS
    }
    secret_refs = config.pop("secret_refs", {})
    if not isinstance(secret_refs, dict):
        secret_refs = {}
    return {
        "id": str(row["id"]),
        "slug": row["slug"],
        "provider_key": row["provider_key"],
        "capability": row["capability_key"],
        "adapter_kind": row["adapter_kind"],
        "display_name": row["display_name"],
        "description": row["description"],
        "endpoint_url": row["endpoint_url"],
        "healthcheck_url": row.get("healthcheck_url"),
        "enabled": bool(row["enabled"]),
        "config": config,
        "secret_refs": dict(secret_refs),
        **local_slot,
    }


def _serialize_runtime_binding(binding: ProviderBinding) -> dict[str, Any]:
    default_resource = _serialize_binding_resource(binding.default_resource) if binding.default_resource else None
    return {
        "id": binding.provider_instance_id,
        "slug": binding.provider_slug,
        "provider_key": binding.provider_key,
        "display_name": binding.provider_display_name,
        "description": binding.provider_description,
        "adapter_kind": binding.adapter_kind,
        "endpoint_url": binding.endpoint_url,
        "healthcheck_url": binding.healthcheck_url,
        "enabled": binding.enabled,
        "config": dict(binding.config),
        "resources": [_serialize_binding_resource(resource) for resource in binding.resources],
        "default_resource_id": binding.default_resource_id,
        "default_resource": default_resource,
        "resource_policy": dict(binding.resource_policy),
        "binding_config": dict(binding.binding_config),
    }


def _serialize_runtime_deployment_profile(binding: ProviderBinding) -> dict[str, Any]:
    return {
        "id": binding.deployment_profile_id,
        "slug": binding.deployment_profile_slug,
        "display_name": binding.deployment_profile_display_name,
    }


def _serialize_deployment_profile(profile: dict[str, Any], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": str(profile["id"]),
        "slug": profile["slug"],
        "display_name": profile["display_name"],
        "description": profile["description"],
        "is_active": bool(profile.get("is_active", False)),
        "bindings": [
            (lambda serialized_resources, default_resource: {
                "capability": binding["capability_key"],
                "provider": {
                    "id": str(binding["provider_instance_id"]),
                    "slug": binding["provider_slug"],
                    "provider_key": binding["provider_key"],
                    "display_name": binding["provider_display_name"],
                    "endpoint_url": binding["endpoint_url"],
                    "enabled": bool(binding["enabled"]),
                    "adapter_kind": binding["adapter_kind"],
                },
                "resources": serialized_resources,
                "default_resource_id": str(binding.get("default_resource_id") or "").strip() or None,
                "default_resource": default_resource,
                "resource_policy": dict(binding.get("resource_policy") or {}),
                "config": dict(binding.get("binding_config") or {}),
            })(
                [
                    _serialize_binding_resource(resource)
                    for resource in (binding.get("resources") or [])
                    if isinstance(resource, dict)
                ],
                (
                    _serialize_binding_resource(binding["default_resource"])
                    if isinstance(binding.get("default_resource"), dict)
                    else None
                ),
            )
            for binding in bindings
        ],
    }


def _serialize_activation_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "deployment_profile": {
            "id": str(row["deployment_profile_id"]),
            "slug": row["deployment_profile_slug"],
            "display_name": row["deployment_profile_display_name"],
        },
        "previous_deployment_profile": (
            {
                "id": str(row["previous_deployment_profile_id"]),
                "slug": row["previous_deployment_profile_slug"],
                "display_name": row["previous_deployment_profile_display_name"],
            }
            if row.get("previous_deployment_profile_id")
            else None
        ),
        "activated_by_user_id": row.get("activated_by_user_id"),
        "activated_at": row["activated_at"].isoformat() if hasattr(row.get("activated_at"), "isoformat") else row["activated_at"],
    }
