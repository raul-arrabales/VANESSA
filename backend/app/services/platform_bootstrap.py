from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import platform_control_plane as platform_repo
from .platform_service_types import (
    _BOOTSTRAP_DEPLOYMENT_DESCRIPTION,
    _BOOTSTRAP_DEPLOYMENT_NAME,
    _BOOTSTRAP_DEPLOYMENT_SLUG,
    _CLOUD_PROVIDER_KEYS,
    _LLAMA_CPP_DEPLOYMENT_DESCRIPTION,
    _LLAMA_CPP_DEPLOYMENT_NAME,
    _LLAMA_CPP_DEPLOYMENT_SLUG,
    _LOCAL_SLOT_CONFIG_KEYS,
    _MODEL_BEARING_CAPABILITIES,
    _QDRANT_DEPLOYMENT_DESCRIPTION,
    _QDRANT_DEPLOYMENT_NAME,
    _QDRANT_DEPLOYMENT_SLUG,
    _VECTOR_SELECTION_DYNAMIC_NAMESPACE,
)
from .platform_local_slots import reconcile_local_provider_slots
from .platform_types import (
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_MCP_RUNTIME,
    CAPABILITY_SANDBOX_EXECUTION,
    CAPABILITY_VECTOR_STORE,
)


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
    existing_binding: dict[str, Any] | None = None,
) -> None:
    effective_provider_instance_id = provider_instance_id
    effective_resources = [dict(resource) for resource in resources if isinstance(resource, dict)]
    effective_default_resource_id = default_resource_id
    effective_resource_policy = dict(resource_policy)
    if isinstance(existing_binding, dict):
        existing_provider_instance_id = str(existing_binding.get("provider_instance_id") or "").strip()
        if existing_provider_instance_id:
            effective_provider_instance_id = existing_provider_instance_id
    if (
        capability_key in _MODEL_BEARING_CAPABILITIES
        and not effective_resources
        and effective_default_resource_id is None
        and isinstance(existing_binding, dict)
    ):
        effective_resources = [
            dict(resource)
            for resource in (existing_binding.get("resources") or [])
            if isinstance(resource, dict)
        ]
        effective_default_resource_id = str(existing_binding.get("default_resource_id") or "").strip() or None
    if capability_key == CAPABILITY_VECTOR_STORE and isinstance(existing_binding, dict):
        existing_resources = [
            dict(resource)
            for resource in (existing_binding.get("resources") or [])
            if isinstance(resource, dict)
        ]
        existing_default_resource_id = str(existing_binding.get("default_resource_id") or "").strip() or None
        existing_resource_policy = (
            dict(existing_binding.get("resource_policy") or {})
            if isinstance(existing_binding.get("resource_policy"), dict)
            else {}
        )
        if existing_resources or existing_default_resource_id is not None or existing_resource_policy:
            if not effective_resources and effective_default_resource_id is None:
                effective_resources = existing_resources
                effective_default_resource_id = existing_default_resource_id
            effective_resource_policy = existing_resource_policy
    platform_repo.upsert_deployment_binding(
        database_url,
        deployment_profile_id=deployment_profile_id,
        capability_key=capability_key,
        provider_instance_id=effective_provider_instance_id,
        resources=effective_resources,
        default_resource_id=effective_default_resource_id,
        binding_config=binding_config,
        resource_policy=effective_resource_policy,
    )


def _existing_provider_rows_by_slug(database_url: str) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("slug") or "").strip().lower(): dict(row)
        for row in platform_repo.list_provider_instances(database_url)
        if isinstance(row, dict) and str(row.get("slug") or "").strip()
    }


def _bootstrap_provider_config(
    *,
    existing_providers_by_slug: dict[str, dict[str, Any]],
    slug: str,
    provider_key: str,
    capability_key: str,
    config_json: dict[str, Any],
) -> dict[str, Any]:
    merged_config = dict(config_json)
    normalized_slug = slug.strip().lower()
    normalized_provider_key = provider_key.strip().lower()
    normalized_capability = capability_key.strip().lower()
    if normalized_capability not in _MODEL_BEARING_CAPABILITIES or normalized_provider_key in _CLOUD_PROVIDER_KEYS:
        return merged_config
    existing_provider = existing_providers_by_slug.get(normalized_slug)
    if not isinstance(existing_provider, dict):
        return merged_config
    existing_config = dict(existing_provider.get("config_json") or {})
    for key in _LOCAL_SLOT_CONFIG_KEYS:
        if key in existing_config:
            merged_config[key] = existing_config[key]
    return merged_config


def _existing_bindings_by_capability(
    database_url: str,
    *,
    deployment_profile_id: str,
) -> dict[str, dict[str, Any]]:
    return {
        str(binding.get("capability_key") or "").strip().lower(): dict(binding)
        for binding in platform_repo.list_deployment_bindings(
            database_url,
            deployment_profile_id=deployment_profile_id,
        )
        if isinstance(binding, dict) and str(binding.get("capability_key") or "").strip()
    }


def ensure_platform_bootstrap_state(database_url: str, config: AuthConfig) -> None:
    sandbox_url = str(getattr(config, "sandbox_url", "") or "").strip()
    mcp_gateway_url = str(getattr(config, "mcp_gateway_url", "") or "").strip()
    llm_request_timeout_seconds = int(getattr(config, "llm_request_timeout_seconds", 60) or 60)
    llm_local_upstream_model = str(
        getattr(config, "llm_local_upstream_model", "") or "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"
    ).strip() or "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"
    existing_providers_by_slug = _existing_provider_rows_by_slug(database_url)
    llm_local_embeddings_upstream_model = str(
        getattr(config, "llm_local_embeddings_upstream_model", "") or llm_local_upstream_model
    ).strip() or llm_local_upstream_model

    platform_repo.ensure_capability(database_url, capability_key=CAPABILITY_LLM_INFERENCE, display_name="LLM inference", description="Normalized chat and generation capability for model inference.", is_required=True)
    platform_repo.ensure_capability(database_url, capability_key=CAPABILITY_EMBEDDINGS, display_name="Embeddings", description="Normalized text embeddings capability for retrieval and vector ingestion.", is_required=True)
    platform_repo.ensure_capability(database_url, capability_key=CAPABILITY_VECTOR_STORE, display_name="Vector store", description="Semantic retrieval capability for embeddings and document search.", is_required=True)
    platform_repo.ensure_capability(database_url, capability_key=CAPABILITY_MCP_RUNTIME, display_name="MCP runtime", description="Gateway capability for MCP-hosted tool execution.", is_required=False)
    platform_repo.ensure_capability(database_url, capability_key=CAPABILITY_SANDBOX_EXECUTION, display_name="Sandbox execution", description="Isolated code-execution capability for agent tools.", is_required=False)

    platform_repo.ensure_provider_family(
        database_url,
        provider_key="vllm_local",
        capability_key=CAPABILITY_LLM_INFERENCE,
        adapter_kind="openai_compatible_llm",
        provider_origin="local",
        display_name="vLLM local gateway",
        description="Current local-first LLM gateway backed by llm -> llm_runtime.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="llama_cpp_local",
        capability_key=CAPABILITY_LLM_INFERENCE,
        adapter_kind="openai_compatible_llm",
        provider_origin="local",
        display_name="llama.cpp local",
        description="OpenAI-compatible llama.cpp inference endpoint for local deployments.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="vllm_embeddings_local",
        capability_key=CAPABILITY_EMBEDDINGS,
        adapter_kind="openai_compatible_embeddings",
        provider_origin="local",
        display_name="vLLM embeddings local",
        description="Local embeddings provider exposed through the llm gateway.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="openai_compatible_cloud_llm",
        capability_key=CAPABILITY_LLM_INFERENCE,
        adapter_kind="openai_compatible_llm",
        provider_origin="cloud",
        display_name="OpenAI-compatible cloud LLM",
        description="Shared cloud LLM endpoint using OpenAI-compatible APIs and platform secret refs.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="openai_compatible_cloud_embeddings",
        capability_key=CAPABILITY_EMBEDDINGS,
        adapter_kind="openai_compatible_embeddings",
        provider_origin="cloud",
        display_name="OpenAI-compatible cloud embeddings",
        description="Shared cloud embeddings endpoint using OpenAI-compatible APIs and platform secret refs.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="weaviate_local",
        capability_key=CAPABILITY_VECTOR_STORE,
        adapter_kind="weaviate_http",
        provider_origin="local",
        display_name="Weaviate local",
        description="Local Weaviate semantic index endpoint.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="qdrant_local",
        capability_key=CAPABILITY_VECTOR_STORE,
        adapter_kind="qdrant_http",
        provider_origin="local",
        display_name="Qdrant local",
        description="Optional local Qdrant semantic index endpoint.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="mcp_gateway_local",
        capability_key=CAPABILITY_MCP_RUNTIME,
        adapter_kind="mcp_http",
        provider_origin="local",
        display_name="MCP gateway local",
        description="Optional local MCP runtime gateway for remote and general-purpose tools.",
    )
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="sandbox_local",
        capability_key=CAPABILITY_SANDBOX_EXECUTION,
        adapter_kind="sandbox_http",
        provider_origin="local",
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
        config_json=_bootstrap_provider_config(
            existing_providers_by_slug=existing_providers_by_slug,
            slug="vllm-local-gateway",
            provider_key="vllm_local",
            capability_key=CAPABILITY_LLM_INFERENCE,
            config_json={
                "models_path": "/v1/models",
                "chat_completion_path": "/v1/chat/completions",
                "runtime_base_url": getattr(config, "llm_inference_runtime_url", config.llm_runtime_url),
                "runtime_admin_base_url": getattr(config, "llm_inference_runtime_url", config.llm_runtime_url),
                "canonical_local_model_id": "local-vllm-default",
                "local_fallback_model_id": "local-vllm-default",
                "request_timeout_seconds": llm_request_timeout_seconds,
            },
        ),
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
        config_json=_bootstrap_provider_config(
            existing_providers_by_slug=existing_providers_by_slug,
            slug="vllm-embeddings-local",
            provider_key="vllm_embeddings_local",
            capability_key=CAPABILITY_EMBEDDINGS,
            config_json={
                "models_path": "/v1/models",
                "embeddings_path": "/v1/embeddings",
                "input_type": "text",
                "runtime_base_url": getattr(config, "llm_embeddings_runtime_url", config.llm_runtime_url),
                "runtime_admin_base_url": getattr(config, "llm_embeddings_runtime_url", config.llm_runtime_url),
                "forced_model_id": "local-vllm-embeddings-default",
                "request_timeout_seconds": llm_request_timeout_seconds,
            },
        ),
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
            config_json={"execute_path": "/v1/execute", "dry_run_code": "result = {'status': 'ok'}", "default_timeout_seconds": 5},
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
        config_json=_bootstrap_provider_config(
            existing_providers_by_slug=existing_providers_by_slug,
            slug="llama-cpp-local",
            provider_key="llama_cpp_local",
            capability_key=CAPABILITY_LLM_INFERENCE,
            config_json={
                "models_path": "/v1/models",
                "chat_completion_path": "/v1/chat/completions",
                "request_format": "openai_chat",
                "canonical_local_model_id": "local-llama-cpp-default",
                "forced_model_id": "local-llama-cpp-default",
                "local_fallback_model_id": "local-llama-cpp-default",
                "request_timeout_seconds": llm_request_timeout_seconds,
            },
        ),
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
            config_json={"collections_path": "/collections", "health_path": "/healthz", "default_vector_size": 1, "distance": "Cosine"},
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
            config_json={"invoke_path": "/v1/tools/invoke", "list_tools_path": "/v1/tools", "healthcheck_tool_name": "web_search"},
        )

    reconciled_providers = {
        str(item.get("slug") or "").strip(): item
        for item in reconcile_local_provider_slots(
            database_url,
            provider_rows=[
                provider
                for provider in [vllm_provider, embeddings_provider, llama_cpp_provider]
                if isinstance(provider, dict)
            ],
        )
        if isinstance(item, dict) and str(item.get("slug") or "").strip()
    }
    vllm_provider = reconciled_providers.get("vllm-local-gateway", vllm_provider)
    embeddings_provider = reconciled_providers.get("vllm-embeddings-local", embeddings_provider)
    llama_cpp_provider = reconciled_providers.get("llama-cpp-local", llama_cpp_provider)

    profile = platform_repo.ensure_deployment_profile(database_url, slug=_BOOTSTRAP_DEPLOYMENT_SLUG, display_name=_BOOTSTRAP_DEPLOYMENT_NAME, description=_BOOTSTRAP_DEPLOYMENT_DESCRIPTION, created_by_user_id=None, updated_by_user_id=None)
    default_bindings_by_capability = _existing_bindings_by_capability(database_url, deployment_profile_id=str(profile["id"]))
    _upsert_bootstrap_binding(database_url, deployment_profile_id=str(profile["id"]), capability_key=CAPABILITY_LLM_INFERENCE, provider_instance_id=str(vllm_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={}, existing_binding=default_bindings_by_capability.get(CAPABILITY_LLM_INFERENCE))
    _upsert_bootstrap_binding(database_url, deployment_profile_id=str(profile["id"]), capability_key=CAPABILITY_EMBEDDINGS, provider_instance_id=str(embeddings_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={}, existing_binding=default_bindings_by_capability.get(CAPABILITY_EMBEDDINGS))
    _upsert_bootstrap_binding(database_url, deployment_profile_id=str(profile["id"]), capability_key=CAPABILITY_VECTOR_STORE, provider_instance_id=str(weaviate_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={"selection_mode": _VECTOR_SELECTION_DYNAMIC_NAMESPACE}, existing_binding=default_bindings_by_capability.get(CAPABILITY_VECTOR_STORE))
    if sandbox_provider is not None and sandbox_provider.get("id"):
        _upsert_bootstrap_binding(database_url, deployment_profile_id=str(profile["id"]), capability_key=CAPABILITY_SANDBOX_EXECUTION, provider_instance_id=str(sandbox_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={})
    if mcp_gateway_provider is not None:
        _upsert_bootstrap_binding(database_url, deployment_profile_id=str(profile["id"]), capability_key=CAPABILITY_MCP_RUNTIME, provider_instance_id=str(mcp_gateway_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={})

    if getattr(config, "llama_cpp_url", "").strip():
        llama_profile = platform_repo.ensure_deployment_profile(database_url, slug=_LLAMA_CPP_DEPLOYMENT_SLUG, display_name=_LLAMA_CPP_DEPLOYMENT_NAME, description=_LLAMA_CPP_DEPLOYMENT_DESCRIPTION, created_by_user_id=None, updated_by_user_id=None)
        llama_bindings_by_capability = _existing_bindings_by_capability(database_url, deployment_profile_id=str(llama_profile["id"]))
        _upsert_bootstrap_binding(database_url, deployment_profile_id=str(llama_profile["id"]), capability_key=CAPABILITY_LLM_INFERENCE, provider_instance_id=str(llama_cpp_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={}, existing_binding=llama_bindings_by_capability.get(CAPABILITY_LLM_INFERENCE))
        _upsert_bootstrap_binding(database_url, deployment_profile_id=str(llama_profile["id"]), capability_key=CAPABILITY_EMBEDDINGS, provider_instance_id=str(embeddings_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={}, existing_binding=llama_bindings_by_capability.get(CAPABILITY_EMBEDDINGS))
        _upsert_bootstrap_binding(database_url, deployment_profile_id=str(llama_profile["id"]), capability_key=CAPABILITY_VECTOR_STORE, provider_instance_id=str(weaviate_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={"selection_mode": _VECTOR_SELECTION_DYNAMIC_NAMESPACE}, existing_binding=llama_bindings_by_capability.get(CAPABILITY_VECTOR_STORE))
        if sandbox_provider is not None and sandbox_provider.get("id"):
            _upsert_bootstrap_binding(database_url, deployment_profile_id=str(llama_profile["id"]), capability_key=CAPABILITY_SANDBOX_EXECUTION, provider_instance_id=str(sandbox_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={})
        if mcp_gateway_provider is not None:
            _upsert_bootstrap_binding(database_url, deployment_profile_id=str(llama_profile["id"]), capability_key=CAPABILITY_MCP_RUNTIME, provider_instance_id=str(mcp_gateway_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={})

    if qdrant_provider is not None:
        qdrant_profile = platform_repo.ensure_deployment_profile(database_url, slug=_QDRANT_DEPLOYMENT_SLUG, display_name=_QDRANT_DEPLOYMENT_NAME, description=_QDRANT_DEPLOYMENT_DESCRIPTION, created_by_user_id=None, updated_by_user_id=None)
        qdrant_bindings_by_capability = _existing_bindings_by_capability(database_url, deployment_profile_id=str(qdrant_profile["id"]))
        _upsert_bootstrap_binding(database_url, deployment_profile_id=str(qdrant_profile["id"]), capability_key=CAPABILITY_LLM_INFERENCE, provider_instance_id=str(vllm_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={}, existing_binding=qdrant_bindings_by_capability.get(CAPABILITY_LLM_INFERENCE))
        _upsert_bootstrap_binding(database_url, deployment_profile_id=str(qdrant_profile["id"]), capability_key=CAPABILITY_EMBEDDINGS, provider_instance_id=str(embeddings_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={}, existing_binding=qdrant_bindings_by_capability.get(CAPABILITY_EMBEDDINGS))
        _upsert_bootstrap_binding(database_url, deployment_profile_id=str(qdrant_profile["id"]), capability_key=CAPABILITY_VECTOR_STORE, provider_instance_id=str(qdrant_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={"selection_mode": _VECTOR_SELECTION_DYNAMIC_NAMESPACE}, existing_binding=qdrant_bindings_by_capability.get(CAPABILITY_VECTOR_STORE))
        if sandbox_provider is not None and sandbox_provider.get("id"):
            _upsert_bootstrap_binding(database_url, deployment_profile_id=str(qdrant_profile["id"]), capability_key=CAPABILITY_SANDBOX_EXECUTION, provider_instance_id=str(sandbox_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={})
        if mcp_gateway_provider is not None:
            _upsert_bootstrap_binding(database_url, deployment_profile_id=str(qdrant_profile["id"]), capability_key=CAPABILITY_MCP_RUNTIME, provider_instance_id=str(mcp_gateway_provider["id"]), resources=[], default_resource_id=None, binding_config={}, resource_policy={})

    if platform_repo.get_active_deployment(database_url) is None:
        platform_repo.activate_deployment_profile(database_url, deployment_profile_id=str(profile["id"]), activated_by_user_id=None)
