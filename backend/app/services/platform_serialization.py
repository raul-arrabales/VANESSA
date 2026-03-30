from __future__ import annotations

from typing import Any

from .platform_local_slots import _effective_local_slot
from .platform_service_types import _CLOUD_PROVIDER_KEYS, _LOCAL_SLOT_CONFIG_KEYS
from .platform_types import ProviderBinding


def _normalized_optional_identifier(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.lower() in {"none", "null"}:
        return None
    return normalized


def _runtime_model_identifier(model_row: dict[str, Any]) -> str:
    provider_model_id = _normalized_optional_identifier(model_row.get("provider_model_id"))
    local_path = _normalized_optional_identifier(model_row.get("local_path"))
    return provider_model_id or local_path


def _is_cloud_provider_row(provider_row: dict[str, Any]) -> bool:
    provider_key = str(provider_row.get("provider_key", "")).strip().lower()
    return provider_key in _CLOUD_PROVIDER_KEYS


def _build_model_binding_resource(model_row: dict[str, Any], *, provider_resource_id: str) -> dict[str, Any]:
    managed_model_id = str(model_row.get("model_id") or model_row.get("id") or "").strip()
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


def _runtime_identifier_for_resource(resource: dict[str, Any]) -> str:
    provider_resource_id = _normalized_optional_identifier(resource.get("provider_resource_id"))
    if provider_resource_id:
        return provider_resource_id
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    provider_model_id = _normalized_optional_identifier(metadata.get("provider_model_id"))
    local_path = _normalized_optional_identifier(metadata.get("local_path"))
    source_id = _normalized_optional_identifier(metadata.get("source_id"))
    return provider_model_id or local_path or source_id


def _serialize_binding_resource(resource: dict[str, Any]) -> dict[str, Any]:
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    return {
        "id": str(resource.get("id") or "").strip(),
        "resource_kind": str(resource.get("resource_kind") or "").strip() or None,
        "ref_type": str(resource.get("ref_type") or "").strip() or None,
        "managed_model_id": _normalized_optional_identifier(resource.get("managed_model_id")),
        "knowledge_base_id": _normalized_optional_identifier(resource.get("knowledge_base_id")),
        "provider_resource_id": _normalized_optional_identifier(resource.get("provider_resource_id")),
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
