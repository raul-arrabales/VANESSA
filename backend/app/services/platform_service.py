from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import platform_control_plane as platform_repo
from .platform_adapters import (
    EmbeddingsAdapter,
    LlmInferenceAdapter,
    OpenAICompatibleEmbeddingsAdapter,
    OpenAICompatibleLlmAdapter,
    QdrantVectorStoreAdapter,
    VectorStoreAdapter,
    WeaviateVectorStoreAdapter,
)
from .platform_types import (
    CAPABILITY_EMBEDDINGS,
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
_QDRANT_DEPLOYMENT_SLUG = "local-qdrant"
_QDRANT_DEPLOYMENT_NAME = "Local Qdrant"
_QDRANT_DEPLOYMENT_DESCRIPTION = "Optional local profile using vLLM for LLM inference and Qdrant for vector storage."


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
            "forced_model_id": "local-vllm-embeddings-default",
            "input_type": "text",
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
            "forced_model_id": "local-llama-cpp-default",
            "local_fallback_model_id": "local-llama-cpp-default",
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
        capability_key=CAPABILITY_EMBEDDINGS,
        provider_instance_id=str(embeddings_provider["id"]),
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
            capability_key=CAPABILITY_EMBEDDINGS,
            provider_instance_id=str(embeddings_provider["id"]),
            binding_config={},
        )
        platform_repo.upsert_deployment_binding(
            database_url,
            deployment_profile_id=str(llama_profile["id"]),
            capability_key=CAPABILITY_VECTOR_STORE,
            provider_instance_id=str(weaviate_provider["id"]),
            binding_config={},
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
        platform_repo.upsert_deployment_binding(
            database_url,
            deployment_profile_id=str(qdrant_profile["id"]),
            capability_key=CAPABILITY_LLM_INFERENCE,
            provider_instance_id=str(vllm_provider["id"]),
            binding_config={},
        )
        platform_repo.upsert_deployment_binding(
            database_url,
            deployment_profile_id=str(qdrant_profile["id"]),
            capability_key=CAPABILITY_EMBEDDINGS,
            provider_instance_id=str(embeddings_provider["id"]),
            binding_config={},
        )
        platform_repo.upsert_deployment_binding(
            database_url,
            deployment_profile_id=str(qdrant_profile["id"]),
            capability_key=CAPABILITY_VECTOR_STORE,
            provider_instance_id=str(qdrant_provider["id"]),
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
    return _serialize_provider_row({**created, **(platform_repo.get_provider_instance(database_url, str(created["id"])) or {})})


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
    return _serialize_provider_row({**updated, **(platform_repo.get_provider_instance(database_url, provider_instance_id) or {})})


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
    normalized = _coerce_create_input(payload)
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
                    "binding_config": dict(binding.get("binding_config") or {}),
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

    if binding.capability_key == CAPABILITY_EMBEDDINGS:
        adapter = resolve_embeddings_adapter(database_url, config, provider_instance_id=provider_instance_id)
        health = adapter.health()
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


def get_active_platform_runtime(database_url: str, config: AuthConfig) -> dict[str, Any]:
    ensure_platform_bootstrap_state(database_url, config)
    llm_binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_LLM_INFERENCE,
        provider_instance_id=None,
    )
    embeddings_binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_EMBEDDINGS,
        provider_instance_id=None,
    )
    vector_binding = _resolve_provider_binding(
        database_url,
        config,
        capability_key=CAPABILITY_VECTOR_STORE,
        provider_instance_id=None,
    )
    if len({llm_binding.deployment_profile_id, embeddings_binding.deployment_profile_id, vector_binding.deployment_profile_id}) != 1:
        raise PlatformControlPlaneError(
            "active_deployment_profile_mismatch",
            "Active capability bindings do not point to the same deployment profile",
            status_code=503,
        )

    return {
        "deployment_profile": _serialize_runtime_deployment_profile(llm_binding),
        "capabilities": {
            CAPABILITY_LLM_INFERENCE: _serialize_runtime_binding(llm_binding),
            CAPABILITY_EMBEDDINGS: _serialize_runtime_binding(embeddings_binding),
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
                "binding_config": binding.binding_config,
            }
        )
        seen_capabilities.add(binding.capability_key)
    return resolved_bindings


def _validate_deployment_profile_bindings(
    database_url: str,
    config: AuthConfig,
    bindings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for binding in bindings:
        provider_instance_id = str(binding["provider_instance_id"])
        result = validate_provider(database_url, config=config, provider_instance_id=provider_instance_id)
        validation = dict(result.get("validation") or {})
        health = dict(validation.get("health") or {})
        reachable = bool(health.get("reachable"))
        models_reachable = validation.get("models_reachable")
        embeddings_reachable = validation.get("embeddings_reachable")
        capability = str(binding.get("capability_key", "")).strip().lower()
        failed = (
            not reachable
            or (capability == CAPABILITY_LLM_INFERENCE and models_reachable is False)
            or (capability == CAPABILITY_EMBEDDINGS and embeddings_reachable is False)
        )
        if failed:
            failures.append(
                {
                    "provider": result.get("provider"),
                    "validation": validation,
                }
            )
    return failures


def _serialize_provider_family_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_key": row["provider_key"],
        "capability": row["capability_key"],
        "adapter_kind": row["adapter_kind"],
        "display_name": row["display_name"],
        "description": row["description"],
    }


def _serialize_provider_row(row: dict[str, Any]) -> dict[str, Any]:
    config = dict(row.get("config_json") or {})
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
