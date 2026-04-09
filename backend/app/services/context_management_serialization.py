from __future__ import annotations

import re
from typing import Any

from ..repositories import platform_control_plane as platform_repo
from .context_management_chunking import (
    normalize_knowledge_base_chunking,
    serialize_knowledge_base_chunking,
)
from .context_management_chunking_compatibility import assert_knowledge_base_chunking_compatible
from .context_management_shared import _is_knowledge_base_eligible, _normalize_source_relative_path
from .context_management_types import (
    _KB_LIFECYCLE_STATES,
    _SOURCE_LIFECYCLE_STATES,
    _SOURCE_TYPES,
    _SUPPORTED_SCHEMA_PROPERTY_TYPES,
)
from .platform_types import CAPABILITY_VECTOR_STORE, PlatformControlPlaneError


def _normalize_knowledge_base_payload(
    database_url: str,
    config: Any,
    payload: dict[str, Any],
    *,
    is_create: bool,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    has_chunking_update = any(key in payload for key in {"chunking", "chunking_strategy", "chunking_config_json"})
    slug = str(payload.get("slug", existing.get("slug", "") if existing else "")).strip().lower()
    display_name = str(payload.get("display_name", existing.get("display_name", "") if existing else "")).strip()
    description = str(payload.get("description", existing.get("description", "") if existing else "")).strip()
    lifecycle_state = str(payload.get("lifecycle_state", existing.get("lifecycle_state", "active") if existing else "active")).strip().lower()
    schema = _normalize_schema(payload.get("schema", existing.get("schema_json", {}) if existing else {}))
    if not is_create and ("backing_provider_instance_id" in payload or "backing_provider_key" in payload):
        raise PlatformControlPlaneError(
            "backing_provider_immutable",
            "backing_provider_instance_id cannot be changed after creation",
            status_code=400,
        )
    if not slug:
        raise PlatformControlPlaneError("invalid_slug", "slug is required", status_code=400)
    if not display_name:
        raise PlatformControlPlaneError("invalid_display_name", "display_name is required", status_code=400)
    if lifecycle_state not in _KB_LIFECYCLE_STATES:
        raise PlatformControlPlaneError("invalid_lifecycle_state", "lifecycle_state is unsupported", status_code=400)
    backing_provider_instance_id = str(
        payload.get(
            "backing_provider_instance_id",
            existing.get("backing_provider_instance_id", "") if existing else "",
        )
    ).strip()
    if is_create and not backing_provider_instance_id:
        raise PlatformControlPlaneError(
            "invalid_backing_provider_instance_id",
            "backing_provider_instance_id is required",
            status_code=400,
        )
    provider_row = None
    if backing_provider_instance_id:
        provider_row = platform_repo.get_provider_instance(database_url, backing_provider_instance_id)
    if backing_provider_instance_id and provider_row is None:
        raise PlatformControlPlaneError(
            "backing_provider_not_found",
            "Backing provider instance was not found",
            status_code=400,
        )
    if provider_row is not None and str(provider_row.get("capability_key") or "").strip().lower() != CAPABILITY_VECTOR_STORE:
        raise PlatformControlPlaneError(
            "invalid_backing_provider_capability",
            "Backing provider must be a vector store provider",
            status_code=400,
        )
    if provider_row is not None and not bool(provider_row.get("enabled", True)):
        raise PlatformControlPlaneError(
            "invalid_backing_provider_disabled",
            "Backing provider must be enabled",
            status_code=400,
        )
    from .context_management_vectorization import normalize_knowledge_base_vectorization

    vectorization = normalize_knowledge_base_vectorization(
        database_url,
        config=config,
        payload=payload,
        is_create=is_create,
        existing=existing,
        backing_provider=provider_row or existing,
    )
    chunking = normalize_knowledge_base_chunking(
        payload,
        is_create=is_create,
        existing=existing,
    )
    normalized_payload = {
        "slug": slug,
        "display_name": display_name,
        "description": description,
        "lifecycle_state": lifecycle_state,
        "backing_provider_instance_id": backing_provider_instance_id or None,
        "backing_provider_key": str(
            (provider_row or existing or {}).get("backing_provider_key")
            or (provider_row or {}).get("provider_key")
            or ""
        ).strip().lower(),
        "schema": schema,
        "index_name": str(existing.get("index_name") or "").strip() if existing else _default_index_name(slug),
        "vectorization": vectorization,
        "chunking": chunking,
    }
    if vectorization["mode"] == "vanessa_embeddings" and (is_create or has_chunking_update):
        assert_knowledge_base_chunking_compatible(
            database_url,
            knowledge_base={
                **(existing or {}),
                **normalized_payload,
                "vectorization_json": vectorization["vectorization_json"],
                "vectorization_mode": vectorization["mode"],
                "embedding_provider_instance_id": vectorization["embedding_provider_instance_id"],
                "embedding_resource_id": vectorization["embedding_resource_id"],
                "chunking_strategy": chunking["strategy"],
                "chunking_config_json": chunking["config"],
            },
            error_prefix="Selected KB chunking is incompatible with the configured embeddings model",
            status_code=400,
        )
    return normalized_payload


def _normalize_schema_profile_payload(database_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    slug = str(payload.get("slug", "")).strip().lower()
    display_name = str(payload.get("display_name", "")).strip()
    description = str(payload.get("description", "")).strip()
    provider_key = str(payload.get("provider_key", "")).strip().lower()
    schema = _normalize_schema(payload.get("schema"))
    if not slug:
        raise PlatformControlPlaneError("invalid_slug", "slug is required", status_code=400)
    if not display_name:
        raise PlatformControlPlaneError("invalid_display_name", "display_name is required", status_code=400)
    if not provider_key:
        raise PlatformControlPlaneError("invalid_provider_key", "provider_key is required", status_code=400)
    provider_family = platform_repo.get_provider_family(database_url, provider_key)
    if provider_family is None:
        raise PlatformControlPlaneError("provider_family_not_found", "Provider family not found", status_code=404)
    if str(provider_family.get("capability_key") or "").strip().lower() != CAPABILITY_VECTOR_STORE:
        raise PlatformControlPlaneError(
            "invalid_schema_profile_provider_capability",
            "Schema profiles can only target vector store provider families",
            status_code=400,
        )
    return {
        "slug": slug,
        "display_name": display_name,
        "description": description,
        "provider_key": provider_key,
        "schema": schema,
    }


def _normalize_document_payload(payload: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    title = str(payload.get("title", existing.get("title", "") if existing else "")).strip()
    source_type = str(payload.get("source_type", existing.get("source_type", "manual") if existing else "manual")).strip().lower() or "manual"
    source_name = str(payload.get("source_name", existing.get("source_name", "") if existing else "")).strip() or None
    uri = str(payload.get("uri", existing.get("uri", "") if existing else "")).strip() or None
    text = str(payload.get("text", existing.get("text", "") if existing else "")).strip()
    metadata = payload.get("metadata", existing.get("metadata_json", {}) if existing else {})
    if not title:
        raise PlatformControlPlaneError("invalid_title", "title is required", status_code=400)
    if not text:
        raise PlatformControlPlaneError("invalid_document_text", "text is required", status_code=400)
    if not isinstance(metadata, dict):
        raise PlatformControlPlaneError("invalid_metadata", "metadata must be an object", status_code=400)
    return {
        "title": title,
        "source_type": source_type,
        "source_name": source_name,
        "uri": uri,
        "text": text,
        "metadata": dict(metadata),
    }


def _normalize_schema_managed_metadata(
    schema: dict[str, Any],
    metadata: Any,
    *,
    existing_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_schema = _normalize_schema(schema)
    schema_properties = {
        str(item.get("name") or "").strip(): str(item.get("data_type") or "text").strip().lower() or "text"
        for item in list(normalized_schema.get("properties") or [])
    }
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise PlatformControlPlaneError("invalid_metadata", "metadata must be an object", status_code=400)
    normalized: dict[str, Any] = {}
    for key, value in metadata.items():
        property_name = str(key or "").strip()
        property_type = schema_properties.get(property_name)
        if not property_name or property_type is None:
            raise PlatformControlPlaneError(
                "invalid_metadata_key",
                f"metadata key '{property_name or key}' is not defined in the knowledge-base schema",
                status_code=400,
            )
        normalized[property_name] = _coerce_schema_managed_metadata_value(
            value,
            property_type=property_type,
            field_name=f"metadata.{property_name}",
        )
    if not existing_metadata:
        return normalized
    preserved = {
        str(key): value
        for key, value in existing_metadata.items()
        if str(key) not in schema_properties
    }
    return {
        **preserved,
        **normalized,
    }


def _normalize_knowledge_source_payload(
    payload: dict[str, Any],
    *,
    knowledge_base_schema: dict[str, Any] | None = None,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_type = str(payload.get("source_type", existing.get("source_type", "local_directory") if existing else "local_directory")).strip().lower() or "local_directory"
    display_name = str(payload.get("display_name", existing.get("display_name", "") if existing else "")).strip()
    relative_path = _normalize_source_relative_path(
        str(payload.get("relative_path", existing.get("relative_path", "") if existing else "")).strip()
    )
    lifecycle_state = str(payload.get("lifecycle_state", existing.get("lifecycle_state", "active") if existing else "active")).strip().lower() or "active"
    include_globs = _normalize_glob_list(payload.get("include_globs", existing.get("include_globs", []) if existing else []), field_name="include_globs")
    exclude_globs = _normalize_glob_list(payload.get("exclude_globs", existing.get("exclude_globs", []) if existing else []), field_name="exclude_globs")
    metadata = _normalize_schema_managed_metadata(
        knowledge_base_schema or {},
        payload.get("metadata", existing.get("metadata_json", {}) if existing else {}),
        existing_metadata=dict(existing.get("metadata_json") or {}) if existing else None,
    )
    if source_type not in _SOURCE_TYPES:
        raise PlatformControlPlaneError(
            "unsupported_source_type",
            "Only local_directory knowledge sources are supported.",
            status_code=400,
        )
    if not display_name:
        raise PlatformControlPlaneError("invalid_source_display_name", "display_name is required", status_code=400)
    if not relative_path:
        raise PlatformControlPlaneError("invalid_source_relative_path", "relative_path is required", status_code=400)
    if lifecycle_state not in _SOURCE_LIFECYCLE_STATES:
        raise PlatformControlPlaneError("invalid_source_lifecycle_state", "lifecycle_state is unsupported", status_code=400)
    return {
        "source_type": source_type,
        "display_name": display_name,
        "relative_path": relative_path,
        "include_globs": include_globs,
        "exclude_globs": exclude_globs,
        "metadata": metadata,
        "lifecycle_state": lifecycle_state,
    }


def _normalize_schema(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PlatformControlPlaneError("invalid_schema", "schema must be an object", status_code=400)
    raw_properties = value.get("properties")
    if raw_properties is None:
        return {}
    if not isinstance(raw_properties, list):
        raise PlatformControlPlaneError("invalid_schema_properties", "schema.properties must be an array", status_code=400)
    properties: list[dict[str, str]] = []
    for index, item in enumerate(raw_properties):
        if not isinstance(item, dict):
            raise PlatformControlPlaneError("invalid_schema_property", f"schema.properties[{index}] must be an object", status_code=400)
        name = str(item.get("name") or "").strip()
        data_type = str(item.get("data_type") or "text").strip().lower() or "text"
        if not name:
            raise PlatformControlPlaneError(
                "invalid_schema_property_name",
                f"schema.properties[{index}].name is required",
                status_code=400,
            )
        if data_type not in _SUPPORTED_SCHEMA_PROPERTY_TYPES:
            raise PlatformControlPlaneError(
                "invalid_schema_property_type",
                f"schema.properties[{index}].data_type must be one of text, number, int, boolean",
                status_code=400,
            )
        properties.append({"name": name, "data_type": data_type})
    return {"properties": properties}


def _default_index_name(slug: str) -> str:
    sanitized = re.sub(r"[^a-z0-9_]+", "_", slug.strip().lower().replace("-", "_")).strip("_")
    return f"kb_{sanitized or 'default'}"


def _normalize_glob_list(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PlatformControlPlaneError("invalid_source_globs", f"{field_name} must be an array of strings", status_code=400)
    normalized: list[str] = []
    for item in value:
        entry = str(item or "").strip()
        if entry:
            normalized.append(entry)
    return normalized


def _coerce_schema_managed_metadata_value(value: Any, *, property_type: str, field_name: str) -> str | int | float | bool:
    normalized_type = property_type.strip().lower()
    if normalized_type == "text":
        if isinstance(value, (dict, list)):
            raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be a string", status_code=400)
        return str(value)
    if normalized_type == "number":
        if isinstance(value, bool):
            raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be a number", status_code=400)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            try:
                return float(stripped)
            except ValueError as exc:
                raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be a number", status_code=400) from exc
        raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be a number", status_code=400)
    if normalized_type == "int":
        if isinstance(value, bool):
            raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be an integer", status_code=400)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if re.fullmatch(r"-?\d+", stripped):
                return int(stripped)
        raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be an integer", status_code=400)
    if normalized_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            stripped = value.strip().lower()
            if stripped == "true":
                return True
            if stripped == "false":
                return False
        raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} must be true or false", status_code=400)
    raise PlatformControlPlaneError("invalid_metadata_value", f"{field_name} has an unsupported metadata type", status_code=400)


def _serialize_knowledge_base(row: dict[str, Any]) -> dict[str, Any]:
    from .context_management_vectorization import serialize_knowledge_base_vectorization

    provider_instance_id = str(row.get("backing_provider_instance_id") or "").strip() or None
    provider_key = str(row.get("backing_provider_key") or "").strip() or None
    return {
        "id": str(row.get("id") or "").strip(),
        "slug": str(row.get("slug") or "").strip(),
        "display_name": str(row.get("display_name") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "index_name": str(row.get("index_name") or "").strip(),
        "backing_provider_instance_id": provider_instance_id,
        "backing_provider_key": provider_key,
        "backing_provider": (
            {
                "id": provider_instance_id,
                "slug": str(row.get("backing_provider_slug") or "").strip() or None,
                "provider_key": provider_key,
                "display_name": str(row.get("backing_provider_display_name") or "").strip() or None,
                "enabled": row.get("backing_provider_enabled") if row.get("backing_provider_enabled") is not None else None,
                "capability": str(row.get("backing_provider_capability") or "").strip() or None,
            }
            if provider_instance_id
            else None
        ),
        "lifecycle_state": str(row.get("lifecycle_state") or "").strip(),
        "sync_status": str(row.get("sync_status") or "").strip(),
        "schema": dict(row.get("schema_json") or {}),
        "vectorization": serialize_knowledge_base_vectorization(row),
        "chunking": serialize_knowledge_base_chunking(row),
        "document_count": int(row.get("document_count") or 0),
        "binding_count": int(row.get("binding_count") or 0),
        "eligible_for_binding": _is_knowledge_base_eligible(row),
        "last_sync_at": row.get("last_sync_at").isoformat() if row.get("last_sync_at") else None,
        "last_sync_error": str(row.get("last_sync_error") or "").strip() or None,
        "last_sync_summary": str(row.get("last_sync_summary") or "").strip() or None,
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _serialize_schema_profile(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or "").strip(),
        "slug": str(row.get("slug") or "").strip(),
        "display_name": str(row.get("display_name") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "provider_key": str(row.get("provider_key") or "").strip(),
        "is_system": bool(row.get("is_system")),
        "schema": dict(row.get("schema_json") or {}),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _serialize_document(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or "").strip(),
        "knowledge_base_id": str(row.get("knowledge_base_id") or "").strip(),
        "title": str(row.get("title") or "").strip(),
        "source_type": str(row.get("source_type") or "").strip(),
        "source_name": str(row.get("source_name") or "").strip() or None,
        "uri": str(row.get("uri") or "").strip() or None,
        "text": str(row.get("text") or ""),
        "metadata": dict(row.get("metadata_json") or {}),
        "chunk_count": int(row.get("chunk_count") or 0),
        "source_id": str(row.get("source_id") or "").strip() or None,
        "source_path": str(row.get("source_path") or "").strip() or None,
        "source_document_key": str(row.get("source_document_key") or "").strip() or None,
        "managed_by_source": bool(row.get("managed_by_source")),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _serialize_knowledge_source(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or "").strip(),
        "knowledge_base_id": str(row.get("knowledge_base_id") or "").strip(),
        "source_type": str(row.get("source_type") or "").strip(),
        "display_name": str(row.get("display_name") or "").strip(),
        "relative_path": str(row.get("relative_path") or "").strip(),
        "include_globs": list(row.get("include_globs") or []),
        "exclude_globs": list(row.get("exclude_globs") or []),
        "metadata": dict(row.get("metadata_json") or {}),
        "lifecycle_state": str(row.get("lifecycle_state") or "").strip(),
        "last_sync_status": str(row.get("last_sync_status") or "").strip(),
        "last_sync_at": row.get("last_sync_at").isoformat() if row.get("last_sync_at") else None,
        "last_sync_error": str(row.get("last_sync_error") or "").strip() or None,
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _serialize_sync_run(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or "").strip(),
        "knowledge_base_id": str(row.get("knowledge_base_id") or "").strip(),
        "source_id": str(row.get("source_id") or "").strip() or None,
        "source_display_name": str(row.get("source_display_name") or "").strip() or None,
        "status": str(row.get("status") or "").strip(),
        "scanned_file_count": int(row.get("scanned_file_count") or 0),
        "changed_file_count": int(row.get("changed_file_count") or 0),
        "deleted_file_count": int(row.get("deleted_file_count") or 0),
        "created_document_count": int(row.get("created_document_count") or 0),
        "updated_document_count": int(row.get("updated_document_count") or 0),
        "deleted_document_count": int(row.get("deleted_document_count") or 0),
        "error_summary": str(row.get("error_summary") or "").strip() or None,
        "started_at": row.get("started_at").isoformat() if row.get("started_at") else None,
        "finished_at": row.get("finished_at").isoformat() if row.get("finished_at") else None,
    }


def _serialize_runtime_knowledge_base(resource: dict[str, Any], *, default_resource_id: str | None) -> dict[str, Any]:
    metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
    knowledge_base_id = str(resource.get("knowledge_base_id") or resource.get("id") or "").strip()
    return {
        "id": knowledge_base_id,
        "display_name": str(resource.get("display_name") or metadata.get("name") or metadata.get("slug") or knowledge_base_id).strip(),
        "slug": str(metadata.get("slug") or "").strip() or None,
        "index_name": str(resource.get("provider_resource_id") or metadata.get("index_name") or "").strip(),
        "is_default": knowledge_base_id == (default_resource_id or ""),
        "is_eligible": True,
        "lifecycle_state": str(metadata.get("lifecycle_state") or "").strip() or None,
        "sync_status": str(metadata.get("sync_status") or "").strip() or None,
    }


def build_knowledge_base_binding_resource(knowledge_base: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(knowledge_base.get("id") or "").strip(),
        "resource_kind": "knowledge_base",
        "ref_type": "knowledge_base",
        "knowledge_base_id": str(knowledge_base.get("id") or "").strip(),
        "provider_resource_id": str(knowledge_base.get("index_name") or "").strip(),
        "display_name": str(knowledge_base.get("display_name") or knowledge_base.get("slug") or "").strip(),
        "metadata": {
            "slug": str(knowledge_base.get("slug") or "").strip(),
            "index_name": str(knowledge_base.get("index_name") or "").strip(),
            "backing_provider_instance_id": str(knowledge_base.get("backing_provider_instance_id") or "").strip() or None,
            "backing_provider_key": str(knowledge_base.get("backing_provider_key") or "").strip() or None,
            "lifecycle_state": str(knowledge_base.get("lifecycle_state") or "").strip(),
            "sync_status": str(knowledge_base.get("sync_status") or "").strip(),
            "document_count": int(knowledge_base.get("document_count") or 0),
        },
    }

def _serialize_query_result(
    result: Any,
    *,
    chunk_length_tokens: int | None = None,
    relevance_score: float | None = None,
    relevance_kind: str | None = None,
    relevance_components: dict[str, float] | None = None,
) -> dict[str, Any]:
    result_metadata = getattr(result, "metadata", None)
    if not isinstance(result_metadata, dict) and isinstance(result, dict):
        result_metadata = result.get("metadata")
    metadata = result_metadata if isinstance(result_metadata, dict) else {}
    result_text = getattr(result, "text", None)
    if result_text is None and isinstance(result, dict):
        result_text = result.get("text")
    text = " ".join(str(result_text or "").split())
    result_id = getattr(result, "id", None)
    if result_id is None and isinstance(result, dict):
        result_id = result.get("id")
    title = str(metadata.get("title") or result_id or "").strip()
    result_relevance_score = relevance_score
    if result_relevance_score is None:
        result_relevance_score = getattr(result, "relevance_score", None)
        if result_relevance_score is None and isinstance(result, dict):
            result_relevance_score = result.get("relevance_score")
    result_relevance_kind = relevance_kind
    if result_relevance_kind is None:
        result_relevance_kind = getattr(result, "relevance_kind", None)
        if result_relevance_kind is None and isinstance(result, dict):
            result_relevance_kind = result.get("relevance_kind")
    result_relevance_components = relevance_components
    if result_relevance_components is None:
        raw_components = getattr(result, "relevance_components", None)
        if raw_components is None and isinstance(result, dict):
            raw_components = result.get("relevance_components")
        if raw_components is not None:
            result_relevance_components = {
                key: value
                for key, value in {
                    "semantic_score": getattr(raw_components, "semantic_score", None)
                    if not isinstance(raw_components, dict)
                    else raw_components.get("semantic_score"),
                    "keyword_score": getattr(raw_components, "keyword_score", None)
                    if not isinstance(raw_components, dict)
                    else raw_components.get("keyword_score"),
                }.items()
                if isinstance(value, (int, float))
            }
    serialized = {
        "id": str(result_id or "").strip(),
        "title": title,
        "text": text,
        "uri": str(metadata.get("uri") or "").strip() or None,
        "source_type": str(metadata.get("source_type") or "").strip() or None,
        "metadata": metadata,
        "chunk_length_tokens": chunk_length_tokens if isinstance(chunk_length_tokens, int) and chunk_length_tokens >= 0 else 0,
        "relevance_score": float(result_relevance_score) if isinstance(result_relevance_score, (int, float)) else 0.0,
        "relevance_kind": str(result_relevance_kind or "").strip() or "similarity",
    }
    if isinstance(result_relevance_components, dict) and result_relevance_components:
        serialized["relevance_components"] = {
            key: float(value)
            for key, value in result_relevance_components.items()
            if key in {"semantic_score", "keyword_score"} and isinstance(value, (int, float))
        }
    return serialized
