from __future__ import annotations

from typing import Any

from .base import EmbeddingsRuntimeClientError, LlmRuntimeClientError, RuntimeClientError
from .transport import DEFAULT_HTTP_TIMEOUT_SECONDS, JsonRequestFn


def normalized_optional_identifier(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.lower() in {"none", "null"}:
        return None
    return normalized


def binding_timeout_seconds(binding: dict[str, Any]) -> float:
    config = binding.get("config") if isinstance(binding.get("config"), dict) else {}
    raw_timeout = config.get("request_timeout_seconds", DEFAULT_HTTP_TIMEOUT_SECONDS)
    try:
        timeout_seconds = float(raw_timeout)
    except (TypeError, ValueError):
        return DEFAULT_HTTP_TIMEOUT_SECONDS
    return timeout_seconds if timeout_seconds > 0 else DEFAULT_HTTP_TIMEOUT_SECONDS


def coerce_platform_runtime(
    platform_runtime: dict[str, Any],
    *,
    error_cls: type[RuntimeClientError],
) -> tuple[dict[str, Any], dict[str, Any]]:
    deployment_profile = platform_runtime.get("deployment_profile")
    capabilities = platform_runtime.get("capabilities")
    if not isinstance(deployment_profile, dict) or not isinstance(capabilities, dict):
        raise error_cls(
            code="invalid_platform_runtime",
            message="platform_runtime is missing deployment profile or capabilities",
            status_code=500,
        )
    return deployment_profile, capabilities


def require_binding(
    capabilities: dict[str, Any],
    *,
    capability_key: str,
    missing_code: str,
    missing_message: str,
    error_cls: type[RuntimeClientError],
) -> dict[str, Any]:
    binding = capabilities.get(capability_key)
    if not isinstance(binding, dict):
        raise error_cls(
            code=missing_code,
            message=missing_message,
            status_code=500,
        )
    return binding


def require_supported_adapter_kind(
    binding: dict[str, Any],
    *,
    supported: set[str],
    unsupported_message: str,
    error_cls: type[RuntimeClientError],
) -> str:
    adapter_kind = str(binding.get("adapter_kind", "")).strip().lower()
    if adapter_kind not in supported:
        raise error_cls(
            code="unsupported_adapter_kind",
            message=unsupported_message,
            status_code=500,
            details={"adapter_kind": adapter_kind},
        )
    return adapter_kind


def resolve_effective_model(
    requested_model: str | None,
    llm_binding: dict[str, Any],
    *,
    request_json: JsonRequestFn,
) -> tuple[str, str]:
    selected_model = select_bound_resource(
        requested_model=requested_model,
        binding=llm_binding,
        error_cls=LlmRuntimeClientError,
    )
    return str(selected_model.get("id", "")).strip(), resolve_runtime_model_identifier(
        binding=llm_binding,
        resource=selected_model,
        error_cls=LlmRuntimeClientError,
        request_json=request_json,
    )


def resolve_effective_embedding_model(
    embeddings_binding: dict[str, Any],
    *,
    request_json: JsonRequestFn,
) -> tuple[str, str]:
    selected_model = select_bound_resource(
        requested_model=None,
        binding=embeddings_binding,
        error_cls=EmbeddingsRuntimeClientError,
    )
    return str(selected_model.get("id", "")).strip(), resolve_runtime_model_identifier(
        binding=embeddings_binding,
        resource=selected_model,
        error_cls=EmbeddingsRuntimeClientError,
        request_json=request_json,
    )


def select_bound_resource(
    *,
    requested_model: str | None,
    binding: dict[str, Any],
    error_cls: type[LlmRuntimeClientError] | type[EmbeddingsRuntimeClientError],
) -> dict[str, Any]:
    resources = binding.get("resources")
    if not isinstance(resources, list) or not resources:
        raise error_cls(
            code="missing_model_ref",
            message="No model was resolved for execution",
            status_code=500,
            details={"provider_slug": binding.get("slug")},
        )

    explicit_model = str(requested_model or "").strip()
    if explicit_model:
        for resource in resources:
            if isinstance(resource, dict) and str(resource.get("id", "")).strip() == explicit_model:
                return dict(resource)
        raise error_cls(
            code="requested_model_not_bound",
            message="Requested model is not bound by the active deployment binding",
            status_code=403,
            details={"provider_slug": binding.get("slug"), "requested_model": explicit_model},
        )

    default_model = binding.get("default_resource")
    if isinstance(default_model, dict) and str(default_model.get("id", "")).strip():
        return dict(default_model)
    default_model_id = str(binding.get("default_resource_id", "")).strip()
    if default_model_id:
        for resource in resources:
            if isinstance(resource, dict) and str(resource.get("id", "")).strip() == default_model_id:
                return dict(resource)
    raise error_cls(
        code="missing_model_ref",
        message="No model was resolved for execution",
        status_code=500,
        details={"provider_slug": binding.get("slug")},
    )


def resolve_runtime_model_identifier(
    *,
    binding: dict[str, Any],
    resource: dict[str, Any],
    error_cls: type[LlmRuntimeClientError] | type[EmbeddingsRuntimeClientError],
    request_json: JsonRequestFn,
) -> str:
    provider_resource_id = normalized_optional_identifier(resource.get("provider_resource_id"))
    if provider_resource_id:
        return provider_resource_id
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    provider_model_id = normalized_optional_identifier(metadata.get("provider_model_id"))
    if provider_model_id:
        return provider_model_id
    return resolve_local_runtime_model_identifier(
        binding=binding,
        served_model=resource,
        error_cls=error_cls,
        request_json=request_json,
    )


def resolve_local_runtime_model_identifier(
    *,
    binding: dict[str, Any],
    served_model: dict[str, Any],
    error_cls: type[LlmRuntimeClientError] | type[EmbeddingsRuntimeClientError],
    request_json: JsonRequestFn,
) -> str:
    models_payload, status_code = request_json(
        models_url(binding),
        method="GET",
        timeout_seconds=binding_timeout_seconds(binding),
    )
    if models_payload is None or not 200 <= status_code < 300:
        raise error_cls(
            code="model_inventory_unavailable",
            message="Unable to resolve a provider-facing model identifier",
            status_code=502 if status_code < 500 else status_code,
            details={"provider_slug": binding.get("slug"), "status_code": status_code},
        )
    available_ids = {
        str(item.get("id", "")).strip()
        for item in (models_payload.get("data") if isinstance(models_payload.get("data"), list) else [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    metadata = served_model.get("metadata") if isinstance(served_model.get("metadata"), dict) else {}
    binding_config = binding.get("config") if isinstance(binding.get("config"), dict) else {}
    served_local_path = normalized_optional_identifier(served_model.get("local_path")) or normalized_optional_identifier(
        metadata.get("local_path")
    )
    served_managed_model_id = normalized_optional_identifier(served_model.get("managed_model_id")) or normalized_optional_identifier(
        metadata.get("managed_model_id")
    )
    loaded_local_path = normalized_optional_identifier(binding_config.get("loaded_local_path"))
    loaded_managed_model_id = normalized_optional_identifier(binding_config.get("loaded_managed_model_id"))
    local_runtime_fallbacks: tuple[str | None, ...] = ()
    if (
        loaded_local_path
        and served_local_path
        and loaded_local_path == served_local_path
    ) or (
        loaded_managed_model_id
        and served_managed_model_id
        and loaded_managed_model_id == served_managed_model_id
    ):
        local_runtime_fallbacks = (
            normalized_optional_identifier(binding_config.get("loaded_runtime_model_id")),
            normalized_optional_identifier(binding_config.get("forced_model_id")),
            normalized_optional_identifier(binding_config.get("canonical_local_model_id")),
            normalized_optional_identifier(binding_config.get("local_fallback_model_id")),
        )
    for candidate in (
        served_local_path,
        normalized_optional_identifier(served_model.get("id")),
        normalized_optional_identifier(served_model.get("name")),
        normalized_optional_identifier(served_model.get("source_id")),
        *local_runtime_fallbacks,
    ):
        if candidate and candidate in available_ids:
            return candidate
    raise error_cls(
        code="requested_model_not_exposed",
        message="Requested model is not exposed by the active provider",
        status_code=409,
        details={
            "provider_slug": binding.get("slug"),
            "served_model_id": served_model.get("id"),
        },
    )


def models_url(binding: dict[str, Any]) -> str:
    config = binding.get("config") if isinstance(binding.get("config"), dict) else {}
    path = str(config.get("models_path", "/v1/models")).strip() or "/v1/models"
    endpoint_url = str(binding.get("endpoint_url", "")).rstrip("/")
    return endpoint_url + path
