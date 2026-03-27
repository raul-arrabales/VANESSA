from __future__ import annotations

import re
from typing import Any

from .context_management_shared import _is_knowledge_base_eligible, _normalize_source_relative_path
from .context_management_types import (
    _DEFAULT_BACKING_PROVIDER_KEY,
    _KB_LIFECYCLE_STATES,
    _SOURCE_LIFECYCLE_STATES,
    _SOURCE_TYPES,
    _SUPPORTED_BACKING_PROVIDER_KEYS,
    _SUPPORTED_SCHEMA_PROPERTY_TYPES,
)
from .platform_types import PlatformControlPlaneError


def _normalize_knowledge_base_payload(
    payload: dict[str, Any],
    *,
    is_create: bool,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    slug = str(payload.get("slug", existing.get("slug", "") if existing else "")).strip().lower()
    display_name = str(payload.get("display_name", existing.get("display_name", "") if existing else "")).strip()
    description = str(payload.get("description", existing.get("description", "") if existing else "")).strip()
    lifecycle_state = str(payload.get("lifecycle_state", existing.get("lifecycle_state", "active") if existing else "active")).strip().lower()
    backing_provider_key = str(
        payload.get("backing_provider_key", existing.get("backing_provider_key", _DEFAULT_BACKING_PROVIDER_KEY) if existing else _DEFAULT_BACKING_PROVIDER_KEY)
    ).strip().lower()
    schema = _normalize_schema(payload.get("schema", existing.get("schema_json", {}) if existing else {}))
    if not slug:
        raise PlatformControlPlaneError("invalid_slug", "slug is required", status_code=400)
    if not display_name:
        raise PlatformControlPlaneError("invalid_display_name", "display_name is required", status_code=400)
    if lifecycle_state not in _KB_LIFECYCLE_STATES:
        raise PlatformControlPlaneError("invalid_lifecycle_state", "lifecycle_state is unsupported", status_code=400)
    if backing_provider_key not in _SUPPORTED_BACKING_PROVIDER_KEYS:
        raise PlatformControlPlaneError(
            "unsupported_backing_provider",
            "Only weaviate_local is supported for managed knowledge bases",
            status_code=400,
        )
    return {
        "slug": slug,
        "display_name": display_name,
        "description": description,
        "lifecycle_state": lifecycle_state,
        "backing_provider_key": backing_provider_key,
        "schema": schema,
        "index_name": str(existing.get("index_name") or "").strip() if existing else _default_index_name(slug),
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


def _normalize_knowledge_source_payload(
    payload: dict[str, Any],
    *,
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


def _serialize_knowledge_base(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or "").strip(),
        "slug": str(row.get("slug") or "").strip(),
        "display_name": str(row.get("display_name") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "index_name": str(row.get("index_name") or "").strip(),
        "backing_provider_key": str(row.get("backing_provider_key") or "").strip(),
        "lifecycle_state": str(row.get("lifecycle_state") or "").strip(),
        "sync_status": str(row.get("sync_status") or "").strip(),
        "schema": dict(row.get("schema_json") or {}),
        "document_count": int(row.get("document_count") or 0),
        "binding_count": int(row.get("binding_count") or 0),
        "eligible_for_binding": _is_knowledge_base_eligible(row),
        "last_sync_at": row.get("last_sync_at").isoformat() if row.get("last_sync_at") else None,
        "last_sync_error": str(row.get("last_sync_error") or "").strip() or None,
        "last_sync_summary": str(row.get("last_sync_summary") or "").strip() or None,
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
            "lifecycle_state": str(knowledge_base.get("lifecycle_state") or "").strip(),
            "sync_status": str(knowledge_base.get("sync_status") or "").strip(),
            "document_count": int(knowledge_base.get("document_count") or 0),
        },
    }


def _normalize_query_top_k(value: Any) -> int:
    if value is None:
        return 5
    if isinstance(value, bool):
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400)
    try:
        top_k = int(value)
    except (TypeError, ValueError) as exc:
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400) from exc
    if top_k <= 0:
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400)
    return top_k


def _serialize_query_result(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    text = " ".join(str(result.get("text") or "").split())
    snippet = text if len(text) <= 220 else text[:219].rstrip() + "…"
    title = str(metadata.get("title") or result.get("id") or "").strip()
    return {
        "id": str(result.get("id") or "").strip(),
        "title": title,
        "snippet": snippet,
        "uri": str(metadata.get("uri") or "").strip() or None,
        "source_type": str(metadata.get("source_type") or "").strip() or None,
        "metadata": metadata,
        "score": result.get("score"),
        "score_kind": result.get("score_kind"),
    }
