from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from ..config import AuthConfig
from ..repositories import platform_control_plane as platform_repo
from .platform_adapters import (
    EmbeddingsAdapter,
    HttpMcpRuntimeAdapter,
    HttpSandboxExecutionAdapter,
    LlmInferenceAdapter,
    McpRuntimeAdapter,
    OpenAICompatibleEmbeddingsAdapter,
    OpenAICompatibleLlmAdapter,
    QdrantVectorStoreAdapter,
    SandboxExecutionAdapter,
    VectorStoreAdapter,
    WeaviateVectorStoreAdapter,
)
from .platform_bootstrap import ensure_platform_bootstrap_state
from .platform_credential_refs import resolve_binding_modelops_credential
from .platform_serialization import _serialize_runtime_binding, _serialize_runtime_deployment_profile
from .platform_types import (
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_MCP_RUNTIME,
    CAPABILITY_SANDBOX_EXECUTION,
    CAPABILITY_VECTOR_STORE,
    OPTIONAL_CAPABILITIES,
    PlatformControlPlaneError,
    ProviderBinding,
)
from .provider_origin_policy import assert_provider_allowed_for_current_runtime


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
        assert_provider_allowed_for_current_runtime(database_url, row)
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
    assert_provider_allowed_for_current_runtime(database_url, row)
    return binding


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
    binding, _credential_summary = resolve_binding_modelops_credential(database_url, config=config, binding=binding)
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
    binding, _credential_summary = resolve_binding_modelops_credential(database_url, config=config, binding=binding)
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
    binding, _credential_summary = resolve_binding_modelops_credential(database_url, config=config, binding=binding)
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
    binding, _credential_summary = resolve_binding_modelops_credential(database_url, config=config, binding=binding)
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
    binding, _credential_summary = resolve_binding_modelops_credential(database_url, config=config, binding=binding)
    if binding.adapter_kind == "mcp_http":
        return HttpMcpRuntimeAdapter(binding)
    raise PlatformControlPlaneError("unsupported_adapter_kind", "Unsupported MCP adapter kind", status_code=500)


def get_active_platform_runtime(
    database_url: str,
    config: AuthConfig,
    *,
    include_runtime_secrets: bool = False,
) -> dict[str, Any]:
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

    if include_runtime_secrets:
        required_bindings = {
            capability_key: resolve_binding_modelops_credential(database_url, config=config, binding=binding)[0]
            for capability_key, binding in required_bindings.items()
        }
    active_capabilities: dict[str, dict[str, Any]] = {
        capability_key: _serialize_runtime_binding(binding) for capability_key, binding in required_bindings.items()
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
        if include_runtime_secrets:
            optional_binding, _credential_summary = resolve_binding_modelops_credential(
                database_url,
                config=config,
                binding=optional_binding,
            )
        active_capabilities[capability_key] = _serialize_runtime_binding(optional_binding)

    return {
        "deployment_profile": _serialize_runtime_deployment_profile(deployment_binding),
        "capabilities": active_capabilities,
    }


def get_active_platform_runtime_for_dispatch(
    database_url: str,
    config: AuthConfig,
    *,
    get_active_platform_runtime_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolver = get_active_platform_runtime_fn or get_active_platform_runtime
    if _accepts_include_runtime_secrets(resolver):
        return resolver(database_url, config, include_runtime_secrets=True)
    return resolver(database_url, config)


def _accepts_include_runtime_secrets(resolver: Callable[..., dict[str, Any]]) -> bool:
    try:
        signature = inspect.signature(resolver)
    except (TypeError, ValueError):
        return True
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            return True
        if parameter.name == "include_runtime_secrets":
            return True
    return False


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
                "provider_origin": llm_adapter.binding.provider_origin,
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
                "provider_origin": embeddings_adapter.binding.provider_origin,
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
                "provider_origin": vector_adapter.binding.provider_origin,
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
                    "provider_origin": sandbox_adapter.binding.provider_origin,
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
                    "provider_origin": mcp_adapter.binding.provider_origin,
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
