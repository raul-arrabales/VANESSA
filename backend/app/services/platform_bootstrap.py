from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from ..repositories import platform_control_plane as platform_repo
from .platform_adapters import http_json_request
from .platform_serialization import _build_model_binding_resource
from .platform_service_types import (
    _BOOTSTRAP_DEPLOYMENT_DESCRIPTION,
    _BOOTSTRAP_DEPLOYMENT_NAME,
    _BOOTSTRAP_DEPLOYMENT_SLUG,
    _CLOUD_PROVIDER_KEYS,
    _IMAGE_ANALYSIS_TASK_DEFAULT_KEYS,
    _IMAGE_SELECTION_TASK_DEFAULTS,
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
    CAPABILITY_IMAGE_ANALYSIS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_MCP_RUNTIME,
    CAPABILITY_SANDBOX_EXECUTION,
    CAPABILITY_VECTOR_STORE,
)


_IMAGE_ANALYSIS_MANAGED_MODEL_IDS = {
    "plate_detector": "image-analysis-plate-detector",
    "plate_ocr": "image-analysis-plate-ocr",
    "object_detector": "image-analysis-object-detector",
    "captioner": "image-analysis-captioner",
}


def _image_analysis_resource_url(provider_row: dict[str, Any]) -> str:
    endpoint_url = str(provider_row.get("endpoint_url") or "").strip()
    config_json = provider_row.get("config_json") if isinstance(provider_row.get("config_json"), dict) else {}
    path = str(config_json.get("resources_path") or "/v1/resources").strip() or "/v1/resources"
    return endpoint_url.rstrip("/") + path


def _provider_image_analysis_resources(provider_row: dict[str, Any]) -> list[dict[str, Any]]:
    payload, status_code = http_json_request(_image_analysis_resource_url(provider_row), method="GET")
    if payload is None or status_code < 200 or status_code >= 300:
        return []
    raw_resources = payload.get("resources") if isinstance(payload, dict) else []
    if not isinstance(raw_resources, list):
        return []
    return [dict(item) for item in raw_resources if isinstance(item, dict)]


def _image_analysis_model_fingerprint(*, resource: dict[str, Any], model_id: str, provider_resource_id: str, task_key: str, metadata: dict[str, Any]) -> str:
    return modelops_repo.compute_config_fingerprint(
        {
            "provider": "image_analysis_local",
            "provider_model_id": provider_resource_id,
            "source_id": str(resource.get("source_id") or provider_resource_id).strip() or provider_resource_id,
            "local_path": None,
            "backend_kind": "local",
            "availability": "offline_ready",
            "credential_id": None,
            "task_key": task_key,
            "hosting_kind": "local",
            "checksum": None,
            "revision": None,
            "metadata": metadata,
        }
    )


def _ensure_image_analysis_modelops_resources(
    database_url: str,
    *,
    config: AuthConfig,
    provider_row: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    resources_by_task = {
        str((resource.get("metadata") or {}).get("task_key") or "").strip().lower(): resource
        for resource in _provider_image_analysis_resources(provider_row)
        if isinstance(resource.get("metadata"), dict)
    }
    if not resources_by_task:
        return [], {}

    bound_resources: list[dict[str, Any]] = []
    task_defaults: dict[str, str] = {}
    task_default_key_by_task = {task_key: default_key for default_key, task_key in _IMAGE_ANALYSIS_TASK_DEFAULT_KEYS.items()}
    node_id = str(getattr(config, "modelops_node_id", "") or "local-node").strip() or "local-node"

    for default_key, task_key in _IMAGE_ANALYSIS_TASK_DEFAULT_KEYS.items():
        runtime_resource = resources_by_task.get(task_key)
        if not runtime_resource:
            continue
        model_id = _IMAGE_ANALYSIS_MANAGED_MODEL_IDS[default_key]
        provider_resource_id = str(runtime_resource.get("provider_resource_id") or runtime_resource.get("id") or model_id).strip()
        if not provider_resource_id:
            continue
        runtime_metadata = runtime_resource.get("metadata") if isinstance(runtime_resource.get("metadata"), dict) else {}
        metadata = {
            **runtime_metadata,
            "capability": "image_analysis",
            "managed_by": "platform_bootstrap",
            "task_default_key": task_default_key_by_task[task_key],
            "provider_resource_id": provider_resource_id,
        }
        fingerprint = _image_analysis_model_fingerprint(
            resource=runtime_resource,
            model_id=model_id,
            provider_resource_id=provider_resource_id,
            task_key=task_key,
            metadata=metadata,
        )
        model_row = modelops_repo.get_model(database_url, model_id)
        if model_row is None or str(model_row.get("current_config_fingerprint") or "").strip() != fingerprint:
            model_row = modelops_repo.upsert_model_record(
                database_url,
                model_id=model_id,
                node_id=node_id,
                name=str(runtime_resource.get("display_name") or model_id).strip(),
                provider="image_analysis_local",
                task_key=task_key,
                category=modelops_repo.infer_category(task_key),
                backend_kind="local",
                source_kind="local_folder",
                availability="offline_ready",
                visibility_scope="platform",
                owner_type=modelops_repo.OWNER_PLATFORM,
                owner_user_id=None,
                provider_model_id=provider_resource_id,
                credential_id=None,
                source_id=str(runtime_resource.get("source_id") or provider_resource_id).strip() or provider_resource_id,
                local_path=None,
                status="available",
                lifecycle_state=modelops_repo.LIFECYCLE_REGISTERED,
                metadata=metadata,
                comment="Bootstrapped from the local image-analysis provider inventory.",
                model_size_billion=None,
                created_by_user_id=None,
                registered_by_user_id=None,
            )

        validation_current = bool(model_row.get("is_validation_current"))
        validation_success = str(model_row.get("last_validation_status") or "").strip().lower() == modelops_repo.VALIDATION_SUCCESS
        if not validation_current or not validation_success:
            modelops_repo.append_validation(
                database_url,
                model_id=model_id,
                validator_kind="image_analysis_provider_inventory",
                trigger_reason="platform_bootstrap",
                result=modelops_repo.VALIDATION_SUCCESS,
                summary="Local image-analysis provider advertises this resource.",
                error_details={"provider_instance_id": str(provider_row.get("id") or ""), "provider_resource_id": provider_resource_id},
                config_fingerprint=str(model_row.get("current_config_fingerprint") or fingerprint),
                validated_by_user_id=None,
            )
        if str(model_row.get("lifecycle_state") or "").strip().lower() != modelops_repo.LIFECYCLE_ACTIVE:
            modelops_repo.activate_model(database_url, model_id=model_id)

        active_row = modelops_repo.get_model(database_url, model_id) or model_row
        bound_resources.append(_build_model_binding_resource(active_row, provider_resource_id=provider_resource_id))
        task_defaults[default_key] = model_id

    plate_defaults = {"plate_detector", "plate_ocr"}
    if bool(plate_defaults & set(task_defaults)) and not plate_defaults <= set(task_defaults):
        bound_resources = [
            resource
            for resource in bound_resources
            if str((resource.get("metadata") or {}).get("task_key") or "").strip().lower()
            not in {_IMAGE_ANALYSIS_TASK_DEFAULT_KEYS["plate_detector"], _IMAGE_ANALYSIS_TASK_DEFAULT_KEYS["plate_ocr"]}
        ]
        for default_key in plate_defaults:
            task_defaults.pop(default_key, None)
    if not task_defaults:
        return [], {}
    return bound_resources, task_defaults


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
        if isinstance(existing_binding.get("resource_policy"), dict):
            effective_resource_policy = dict(existing_binding.get("resource_policy") or {})
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
    image_analysis_url = str(getattr(config, "image_analysis_url", "") or "").strip()
    llm_request_timeout_seconds = int(getattr(config, "llm_request_timeout_seconds", 60) or 60)
    image_analysis_request_timeout_seconds = int(
        getattr(config, "image_analysis_request_timeout_seconds", 300) or 300
    )
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
    platform_repo.ensure_capability(database_url, capability_key=CAPABILITY_IMAGE_ANALYSIS, display_name="Image analysis", description="Local image understanding capability for license plates, object detection, and captioning.", is_required=False)

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
    platform_repo.ensure_provider_family(
        database_url,
        provider_key="image_analysis_local",
        capability_key=CAPABILITY_IMAGE_ANALYSIS,
        adapter_kind="image_analysis_http",
        provider_origin="local",
        display_name="Image analysis local",
        description="Optional local image-analysis runtime for ANPR, object detection, and captioning.",
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
    image_analysis_provider = None
    if image_analysis_url:
        image_analysis_provider = platform_repo.ensure_provider_instance(
            database_url,
            slug="image-analysis-local",
            provider_key="image_analysis_local",
            display_name="Image analysis local",
            description="Optional local image-analysis runtime.",
            endpoint_url=image_analysis_url,
            healthcheck_url=image_analysis_url.rstrip("/") + "/health",
            enabled=True,
            config_json={
                "resources_path": "/v1/resources",
                "analyze_path": "/v1/analyze",
                "request_timeout_seconds": image_analysis_request_timeout_seconds,
            },
        )
    image_analysis_resources: list[dict[str, Any]] = []
    image_analysis_task_defaults: dict[str, str] = {}
    if image_analysis_provider is not None:
        image_analysis_resources, image_analysis_task_defaults = _ensure_image_analysis_modelops_resources(
            database_url,
            config=config,
            provider_row=image_analysis_provider,
        )
    image_analysis_resource_policy = (
        {"selection_mode": _IMAGE_SELECTION_TASK_DEFAULTS, "task_defaults": image_analysis_task_defaults}
        if image_analysis_resources and image_analysis_task_defaults
        else {}
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
    if image_analysis_provider is not None:
        _upsert_bootstrap_binding(
            database_url,
            deployment_profile_id=str(profile["id"]),
            capability_key=CAPABILITY_IMAGE_ANALYSIS,
            provider_instance_id=str(image_analysis_provider["id"]),
            resources=image_analysis_resources,
            default_resource_id=None,
            binding_config={},
            resource_policy=image_analysis_resource_policy,
            existing_binding=default_bindings_by_capability.get(CAPABILITY_IMAGE_ANALYSIS),
        )

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
        if image_analysis_provider is not None and image_analysis_resource_policy:
            _upsert_bootstrap_binding(database_url, deployment_profile_id=str(llama_profile["id"]), capability_key=CAPABILITY_IMAGE_ANALYSIS, provider_instance_id=str(image_analysis_provider["id"]), resources=image_analysis_resources, default_resource_id=None, binding_config={}, resource_policy=image_analysis_resource_policy, existing_binding=llama_bindings_by_capability.get(CAPABILITY_IMAGE_ANALYSIS))

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
        if image_analysis_provider is not None and image_analysis_resource_policy:
            _upsert_bootstrap_binding(database_url, deployment_profile_id=str(qdrant_profile["id"]), capability_key=CAPABILITY_IMAGE_ANALYSIS, provider_instance_id=str(image_analysis_provider["id"]), resources=image_analysis_resources, default_resource_id=None, binding_config={}, resource_policy=image_analysis_resource_policy, existing_binding=qdrant_bindings_by_capability.get(CAPABILITY_IMAGE_ANALYSIS))

    if platform_repo.get_active_deployment(database_url) is None:
        platform_repo.activate_deployment_profile(database_url, deployment_profile_id=str(profile["id"]), activated_by_user_id=None)
