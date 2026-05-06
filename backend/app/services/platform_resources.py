from __future__ import annotations

from typing import Any


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
    return provider_model_id or local_path or ""


def _runtime_identifier_for_resource(resource: dict[str, Any]) -> str:
    provider_resource_id = _normalized_optional_identifier(resource.get("provider_resource_id"))
    if provider_resource_id:
        return provider_resource_id
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    provider_model_id = _normalized_optional_identifier(metadata.get("provider_model_id"))
    local_path = _normalized_optional_identifier(metadata.get("local_path"))
    source_id = _normalized_optional_identifier(metadata.get("source_id"))
    return provider_model_id or local_path or source_id or ""


def _default_resource_runtime_identifier(resource: dict[str, Any]) -> str:
    return _runtime_identifier_for_resource(resource or {})
