from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import platform_control_plane as platform_repo
from .platform_adapters import LlmInferenceAdapter, OpenAICompatibleLlmAdapter, VectorStoreAdapter, WeaviateVectorStoreAdapter
from .platform_types import (
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_VECTOR_STORE,
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


def ensure_platform_bootstrap_state(database_url: str, config: AuthConfig) -> None:
    platform_repo.ensure_capability(
        database_url,
        capability_key=CAPABILITY_LLM_INFERENCE,
        display_name="LLM inference",
        description="Normalized chat and generation capability for model inference.",
        is_required=True,
    )
    platform_repo.ensure_capability(
        database_url,
        capability_key=CAPABILITY_VECTOR_STORE,
        display_name="Vector store",
        description="Semantic retrieval capability for embeddings and document search.",
        is_required=True,
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
        provider_key="weaviate_local",
        capability_key=CAPABILITY_VECTOR_STORE,
        adapter_kind="weaviate_http",
        display_name="Weaviate local",
        description="Local Weaviate semantic index endpoint.",
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
            "runtime_base_url": config.llm_runtime_url,
            "local_fallback_model_id": "local-vllm-default",
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
            "forced_model_id": "local-llama-cpp-default",
            "local_fallback_model_id": "local-llama-cpp-default",
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
    platform_repo.upsert_deployment_binding(
        database_url,
        deployment_profile_id=str(profile["id"]),
        capability_key=CAPABILITY_LLM_INFERENCE,
        provider_instance_id=str(vllm_provider["id"]),
        binding_config={},
    )
    platform_repo.upsert_deployment_binding(
        database_url,
        deployment_profile_id=str(profile["id"]),
        capability_key=CAPABILITY_VECTOR_STORE,
        provider_instance_id=str(weaviate_provider["id"]),
        binding_config={},
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
        platform_repo.upsert_deployment_binding(
            database_url,
            deployment_profile_id=str(llama_profile["id"]),
            capability_key=CAPABILITY_LLM_INFERENCE,
            provider_instance_id=str(llama_cpp_provider["id"]),
            binding_config={},
        )
        platform_repo.upsert_deployment_binding(
            database_url,
            deployment_profile_id=str(llama_profile["id"]),
            capability_key=CAPABILITY_VECTOR_STORE,
            provider_instance_id=str(weaviate_provider["id"]),
            binding_config={},
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
    for capability_key in REQUIRED_CAPABILITIES:
        row = platform_repo.get_active_binding_for_capability(database_url, capability_key=capability_key)
        if row is not None:
            active_by_capability[capability_key] = row

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


def list_deployment_profiles(database_url: str, config: AuthConfig) -> list[dict[str, Any]]:
    ensure_platform_bootstrap_state(database_url, config)
    items: list[dict[str, Any]] = []
    for profile in platform_repo.list_deployment_profiles(database_url):
        bindings = platform_repo.list_deployment_bindings(database_url, deployment_profile_id=str(profile["id"]))
        items.append(_serialize_deployment_profile(profile, bindings))
    return items


def create_deployment_profile(
    database_url: str,
    *,
    config: AuthConfig,
    payload: dict[str, Any],
    created_by_user_id: int,
) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    normalized = _coerce_create_input(payload)
    seen_capabilities: set[str] = set()
    resolved_bindings: list[dict[str, Any]] = []

    for binding in normalized.bindings:
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
                "binding_config": binding.binding_config,
            }
        )
        seen_capabilities.add(binding.capability_key)

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

    binding = ProviderBinding.from_row(provider_row)
    if binding.capability_key == CAPABILITY_LLM_INFERENCE:
        adapter = resolve_llm_inference_adapter(database_url, config, provider_instance_id=provider_instance_id)
        health = adapter.health()
        models_payload, models_status = adapter.list_models()
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": {
                "health": health,
                "models_reachable": models_payload is not None and 200 <= models_status < 300,
                "models_status_code": models_status,
            },
        }

    if binding.capability_key == CAPABILITY_VECTOR_STORE:
        adapter = resolve_vector_store_adapter(database_url, config, provider_instance_id=provider_instance_id)
        return {
            "provider": _serialize_provider_row(provider_row),
            "validation": {
                "health": adapter.health(),
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
    raise PlatformControlPlaneError("unsupported_adapter_kind", "Unsupported vector adapter kind", status_code=500)


def get_active_platform_runtime(database_url: str, config: AuthConfig) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    llm_binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_LLM_INFERENCE,
        provider_instance_id=None,
    )
    vector_binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_VECTOR_STORE,
        provider_instance_id=None,
    )
    if llm_binding.deployment_profile_id != vector_binding.deployment_profile_id:
        raise PlatformControlPlaneError(
            "active_deployment_profile_mismatch",
            "Active capability bindings do not point to the same deployment profile",
            status_code=503,
        )

    return {
        "deployment_profile": _serialize_runtime_deployment_profile(llm_binding),
        "capabilities": {
            CAPABILITY_LLM_INFERENCE: _serialize_runtime_binding(llm_binding),
            CAPABILITY_VECTOR_STORE: _serialize_runtime_binding(vector_binding),
        },
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


def _coerce_create_input(payload: dict[str, Any]) -> DeploymentProfileCreateInput:
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
        if capability_key not in REQUIRED_CAPABILITIES:
            raise PlatformControlPlaneError("invalid_capability", "Unsupported capability", status_code=400)
        if not provider_instance_id:
            raise PlatformControlPlaneError("invalid_provider_id", "provider_id is required", status_code=400)
        binding_config = item.get("config") if isinstance(item.get("config"), dict) else {}
        bindings.append(
            DeploymentBindingInput(
                capability_key=capability_key,
                provider_instance_id=provider_instance_id,
                binding_config=dict(binding_config),
            )
        )

    return DeploymentProfileCreateInput(
        slug=slug,
        display_name=display_name,
        description=description,
        bindings=bindings,
    )


def _serialize_provider_row(row: dict[str, Any]) -> dict[str, Any]:
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
        "config": dict(row.get("config_json") or {}),
    }


def _serialize_runtime_binding(binding: ProviderBinding) -> dict[str, Any]:
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
            {
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
                "config": dict(binding.get("binding_config") or {}),
            }
            for binding in bindings
        ],
    }
