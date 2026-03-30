from __future__ import annotations

from typing import Any

from ..repositories import context_management as context_repo
from ..repositories.modelops import get_model as get_model_by_id
from ..repositories import platform_control_plane as platform_repo
from .context_management import build_knowledge_base_binding_resource
from .platform_adapters import (
    HttpMcpRuntimeAdapter,
    HttpSandboxExecutionAdapter,
    OpenAICompatibleEmbeddingsAdapter,
    OpenAICompatibleLlmAdapter,
    QdrantVectorStoreAdapter,
    WeaviateVectorStoreAdapter,
)
from .platform_serialization import (
    _build_model_binding_resource,
    _is_cloud_provider_row,
    _runtime_identifier_for_resource,
    _runtime_model_identifier,
    _serialize_binding_resource,
)
from .platform_service_types import (
    BindingResourcePayload,
    ProviderStoragePayload,
    _MODEL_BEARING_CAPABILITIES,
    _VECTOR_SELECTION_DYNAMIC_NAMESPACE,
    _VECTOR_SELECTION_EXPLICIT,
)
from .platform_shared import _expected_task_key, _runtime_model_entries_for_capability
from .platform_types import (
    CAPABILITY_EMBEDDINGS,
    CAPABILITY_LLM_INFERENCE,
    CAPABILITY_MCP_RUNTIME,
    CAPABILITY_SANDBOX_EXECUTION,
    CAPABILITY_VECTOR_STORE,
    DeploymentBindingInput,
    DeploymentProfileCreateInput,
    PlatformControlPlaneError,
    ProviderBinding,
    REQUIRED_CAPABILITIES,
)


def _known_capability_keys(database_url: str) -> set[str]:
    return {str(row["capability_key"]).strip().lower() for row in platform_repo.list_capabilities(database_url)}


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

    bindings = [_coerce_binding_input(database_url, item=item) for item in raw_bindings]

    return DeploymentProfileCreateInput(
        slug=slug,
        display_name=display_name,
        description=description,
        bindings=bindings,
    )


def _coerce_binding_input(
    database_url: str,
    *,
    item: dict[str, Any],
    capability_key: str | None = None,
) -> DeploymentBindingInput:
    if not isinstance(item, dict):
        raise PlatformControlPlaneError("invalid_binding", "Each binding must be an object", status_code=400)
    normalized_capability_key = str(capability_key or item.get("capability", "")).strip().lower()
    provider_instance_id = str(item.get("provider_id", "")).strip()
    if normalized_capability_key not in _known_capability_keys(database_url):
        raise PlatformControlPlaneError("invalid_capability", "Unsupported capability", status_code=400)
    if not provider_instance_id:
        raise PlatformControlPlaneError("invalid_provider_id", "provider_id is required", status_code=400)
    binding_config = item.get("config") if isinstance(item.get("config"), dict) else {}
    resource_policy = item.get("resource_policy") if isinstance(item.get("resource_policy"), dict) else {}
    resources = _coerce_binding_resources(item.get("resources"))
    default_resource_id = str(item.get("default_resource_id", "")).strip() or None
    return DeploymentBindingInput(
        capability_key=normalized_capability_key,
        provider_instance_id=provider_instance_id,
        resources=resources,
        default_resource_id=default_resource_id,
        binding_config=dict(binding_config),
        resource_policy=dict(resource_policy),
    )


def _coerce_provider_input(
    database_url: str,
    payload: dict[str, Any],
    *,
    is_update: bool,
    existing_provider: dict[str, Any] | None = None,
) -> ProviderStoragePayload:
    del is_update
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
    raw_config = payload.get(
        "config",
        _serialize_provider_row(existing_provider)["config"] if existing_provider is not None else {},
    )
    raw_secret_refs = payload.get(
        "secret_refs",
        _serialize_provider_row(existing_provider)["secret_refs"] if existing_provider is not None else {},
    )
    enabled = payload.get("enabled", existing_provider["enabled"] if existing_provider is not None else True)

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
    if not isinstance(enabled, bool):
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
        "enabled": enabled,
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


def _require_complete_provider_binding_set(resolved_bindings: list[dict[str, Any]]) -> None:
    bound_capabilities = {str(item.get("capability_key") or "").strip().lower() for item in resolved_bindings}
    missing_capabilities = sorted(REQUIRED_CAPABILITIES - bound_capabilities)
    if missing_capabilities:
        raise PlatformControlPlaneError(
            "deployment_profile_incomplete",
            "Deployment profile is missing required capability bindings",
            status_code=400,
            details={"missing_capabilities": missing_capabilities},
        )


def _validate_knowledge_base_vectorization_bindings(
    database_url: str,
    *,
    resolved_bindings: list[dict[str, Any]],
) -> None:
    embeddings_binding = next(
        (item for item in resolved_bindings if str(item.get("capability_key") or "").strip().lower() == CAPABILITY_EMBEDDINGS),
        None,
    )
    vector_binding = next(
        (item for item in resolved_bindings if str(item.get("capability_key") or "").strip().lower() == CAPABILITY_VECTOR_STORE),
        None,
    )
    if embeddings_binding is None or vector_binding is None:
        return
    embeddings_provider_instance_id = str(embeddings_binding.get("provider_instance_id") or "").strip()
    default_resource = next(
        (
            resource
            for resource in embeddings_binding.get("resources") or []
            if isinstance(resource, dict)
            and str(resource.get("id") or "").strip() == str(embeddings_binding.get("default_resource_id") or "").strip()
        ),
        None,
    )
    embeddings_resource_id = _runtime_identifier_for_resource(default_resource or {})
    for resource in vector_binding.get("resources") or []:
        if not isinstance(resource, dict):
            continue
        knowledge_base_id = str(resource.get("knowledge_base_id") or "").strip()
        if not knowledge_base_id:
            continue
        knowledge_base = context_repo.get_knowledge_base(database_url, knowledge_base_id)
        if knowledge_base is None:
            continue
        vectorization_mode = str(knowledge_base.get("vectorization_mode") or "").strip().lower()
        if vectorization_mode == "self_provided":
            raise PlatformControlPlaneError(
                "resource_vectorization_unsupported",
                "Self-provided-vector knowledge bases cannot be bound to deployments yet.",
                status_code=400,
                details={"knowledge_base_id": knowledge_base_id, "vectorization_mode": vectorization_mode},
            )
        knowledge_base_embedding_provider_id = str(knowledge_base.get("embedding_provider_instance_id") or "").strip()
        knowledge_base_embedding_resource_id = str(knowledge_base.get("embedding_resource_id") or "").strip()
        if knowledge_base_embedding_provider_id != embeddings_provider_instance_id:
            raise PlatformControlPlaneError(
                "resource_embeddings_provider_mismatch",
                "Knowledge base embeddings provider must match the deployment embeddings provider.",
                status_code=400,
                details={
                    "knowledge_base_id": knowledge_base_id,
                    "knowledge_base_embedding_provider_instance_id": knowledge_base_embedding_provider_id or None,
                    "deployment_embedding_provider_instance_id": embeddings_provider_instance_id or None,
                },
            )
        if knowledge_base_embedding_resource_id != embeddings_resource_id:
            raise PlatformControlPlaneError(
                "resource_embeddings_resource_mismatch",
                "Knowledge base embeddings resource must match the deployment default embeddings resource.",
                status_code=400,
                details={
                    "knowledge_base_id": knowledge_base_id,
                    "knowledge_base_embedding_resource_id": knowledge_base_embedding_resource_id or None,
                    "deployment_embedding_resource_id": embeddings_resource_id or None,
                },
            )


def _validate_deployment_profile_bindings(
    database_url: str,
    config: Any,
    bindings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    del database_url, config
    failures: list[dict[str, Any]] = []
    non_blocking_binding_errors = {"default_resource_required"}
    non_blocking_resource_errors = {"resource_required"}
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
        blocking_resource_errors = [
            item
            for item in resource_errors
            if isinstance(item, dict) and str(item.get("code") or "").strip() not in non_blocking_resource_errors
        ] if isinstance(resource_errors, list) else []
        capability = str(binding.get("capability_key", "")).strip().lower()
        failed = (
            not reachable
            or (capability in {CAPABILITY_LLM_INFERENCE, CAPABILITY_VECTOR_STORE} and resources_reachable is False)
            or (capability == CAPABILITY_EMBEDDINGS and embeddings_reachable is False)
            or (capability == CAPABILITY_SANDBOX_EXECUTION and validation.get("execute_reachable") is False)
            or (capability == CAPABILITY_MCP_RUNTIME and validation.get("invoke_reachable") is False)
            or bool(binding_error and binding_error not in non_blocking_binding_errors)
            or bool(blocking_resource_errors)
        )
        if failed:
            failures.append({"provider": result.get("provider"), "validation": validation})
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
                "embeddings_reachable": None,
                "embeddings_status_code": None,
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


def _coerce_binding_resources(raw_resources: Any) -> list[BindingResourcePayload]:
    if raw_resources is None:
        return []
    if not isinstance(raw_resources, list):
        raise PlatformControlPlaneError("invalid_resources", "resources must be an array", status_code=400)
    normalized: list[BindingResourcePayload] = []
    for item in raw_resources:
        if not isinstance(item, dict):
            raise PlatformControlPlaneError("invalid_resource", "Each resource must be an object", status_code=400)
        resource_id = str(
            item.get("id")
            or item.get("managed_model_id")
            or item.get("knowledge_base_id")
            or item.get("provider_resource_id")
            or ""
        ).strip()
        if not resource_id:
            raise PlatformControlPlaneError("invalid_resource_id", "resource.id is required", status_code=400)
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        normalized.append(
            {
                "id": resource_id,
                "resource_kind": str(item.get("resource_kind") or "").strip().lower(),
                "ref_type": str(item.get("ref_type") or "").strip().lower(),
                "managed_model_id": str(item.get("managed_model_id") or "").strip() or None,
                "knowledge_base_id": str(item.get("knowledge_base_id") or "").strip() or None,
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
            database_url=database_url,
            provider_row=provider_row,
            capability_key=normalized_capability,
            resources=normalized_resources,
            default_resource_id=normalized_default,
            resource_policy=resource_policy,
        )
    if normalized_default and normalized_default not in {str(resource.get("id") or "").strip() for resource in normalized_resources}:
        raise PlatformControlPlaneError(
            "default_resource_not_bound",
            "default_resource_id must be present in resources",
            status_code=400,
            details={"default_resource_id": normalized_default},
        )

    if not normalized_resources:
        return {
            "resources": [],
            "default_resource_id": None,
        }

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
    database_url: str,
    provider_row: dict[str, Any],
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
        if default_resource_id and default_resource_id not in {str(resource.get("id") or "").strip() for resource in resources}:
            raise PlatformControlPlaneError(
                "default_resource_not_bound",
                "default_resource_id must be present in resources",
                status_code=400,
                details={"default_resource_id": default_resource_id},
            )
        if not resources:
            return {"resources": [], "default_resource_id": None}
        validated = []
        for resource in resources:
            validated.append(_validate_vector_binding_resource(database_url, provider_row=provider_row, resource=resource))
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


def _validate_vector_binding_resource(
    database_url: str,
    *,
    provider_row: dict[str, Any],
    resource: dict[str, Any],
) -> dict[str, Any]:
    ref_type = str(resource.get("ref_type") or "").strip().lower()
    knowledge_base_id = str(resource.get("knowledge_base_id") or resource.get("id") or "").strip()
    if ref_type == "knowledge_base" or knowledge_base_id and str(resource.get("knowledge_base_id") or "").strip():
        knowledge_base = context_repo.get_knowledge_base(database_url, knowledge_base_id)
        if knowledge_base is None:
            raise PlatformControlPlaneError(
                "resource_not_found",
                "Knowledge base resource was not found",
                status_code=404,
                details={"knowledge_base_id": knowledge_base_id},
            )
        if str(knowledge_base.get("lifecycle_state") or "").strip().lower() != "active":
            raise PlatformControlPlaneError(
                "resource_not_active",
                "Vector store bindings require an active knowledge base",
                status_code=409,
                details={"knowledge_base_id": knowledge_base_id},
            )
        if str(knowledge_base.get("sync_status") or "").strip().lower() != "ready":
            raise PlatformControlPlaneError(
                "resource_not_ready",
                "Vector store bindings require a ready knowledge base",
                status_code=409,
                details={"knowledge_base_id": knowledge_base_id},
            )
        if str(knowledge_base.get("backing_provider_instance_id") or "").strip() != str(provider_row.get("id") or "").strip():
            raise PlatformControlPlaneError(
                "resource_provider_mismatch",
                "Knowledge base backing provider must match the selected vector store provider",
                status_code=400,
                details={
                    "knowledge_base_id": knowledge_base_id,
                    "knowledge_base_provider_instance_id": knowledge_base.get("backing_provider_instance_id"),
                    "provider_instance_id": provider_row.get("id"),
                    "knowledge_base_provider_key": knowledge_base.get("backing_provider_key"),
                    "provider_key": provider_row.get("provider_key"),
                },
            )
        return build_knowledge_base_binding_resource(knowledge_base)

    return {
        "id": str(resource.get("id") or "").strip(),
        "resource_kind": str(resource.get("resource_kind") or "index").strip().lower() or "index",
        "ref_type": "provider_resource",
        "managed_model_id": None,
        "knowledge_base_id": None,
        "provider_resource_id": str(resource.get("provider_resource_id") or resource.get("id") or "").strip(),
        "display_name": str(resource.get("display_name") or resource.get("id") or "").strip(),
        "metadata": dict(resource.get("metadata") or {}),
    }


def _normalize_binding_resources(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    expected_task_key = _expected_task_key(capability_key)
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


from .platform_serialization import _serialize_provider_row  # noqa: E402
