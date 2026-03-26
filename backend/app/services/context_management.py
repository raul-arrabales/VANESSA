from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..config import AuthConfig
from ..repositories import context_management as context_repo
from ..repositories import platform_control_plane as platform_repo
from .platform_types import CAPABILITY_VECTOR_STORE, PlatformControlPlaneError

_SUPPORTED_SCHEMA_PROPERTY_TYPES = {"text", "number", "int", "boolean"}
_SUPPORTED_UPLOAD_EXTENSIONS = {".txt", ".md", ".json", ".jsonl"}
_SUPPORTED_BACKING_PROVIDER_KEYS = {"weaviate_local"}
_KB_LIFECYCLE_STATES = {"active", "archived"}
_KB_SYNC_STATES = {"ready", "syncing", "error"}
_DEFAULT_BACKING_PROVIDER_KEY = "weaviate_local"
_DEFAULT_CHUNK_SIZE = 1000
_MAX_FILE_SIZE_BYTES = 1_000_000
_MAX_UPLOAD_FILES = 10
_MAX_UPLOAD_DOCUMENTS = 100


def list_knowledge_bases(
    database_url: str,
    *,
    eligible_only: bool = False,
    backing_provider_key: str | None = None,
) -> list[dict[str, Any]]:
    return [_serialize_knowledge_base(row) for row in context_repo.list_knowledge_bases(
        database_url,
        eligible_only=eligible_only,
        backing_provider_key=backing_provider_key,
    )]


def get_knowledge_base_detail(database_url: str, *, knowledge_base_id: str) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    deployment_usage = context_repo.list_knowledge_base_deployment_usage(database_url, knowledge_base_id=knowledge_base_id)
    return {
        **_serialize_knowledge_base(knowledge_base),
        "deployment_usage": [
            {
                "deployment_profile": {
                    "id": str(row.get("deployment_profile_id") or "").strip(),
                    "slug": str(row.get("deployment_profile_slug") or "").strip(),
                    "display_name": str(row.get("deployment_profile_display_name") or "").strip(),
                },
                "capability": str(row.get("capability_key") or "").strip(),
            }
            for row in deployment_usage
        ],
    }


def create_knowledge_base(
    database_url: str,
    *,
    config: AuthConfig,
    payload: dict[str, Any],
    created_by_user_id: int | None,
) -> dict[str, Any]:
    normalized = _normalize_knowledge_base_payload(payload, is_create=True)
    knowledge_base = context_repo.create_knowledge_base(
        database_url,
        slug=normalized["slug"],
        display_name=normalized["display_name"],
        description=normalized["description"],
        index_name=normalized["index_name"],
        backing_provider_key=normalized["backing_provider_key"],
        lifecycle_state=normalized["lifecycle_state"],
        sync_status="syncing",
        schema_json=normalized["schema"],
        created_by_user_id=created_by_user_id,
        updated_by_user_id=created_by_user_id,
    )
    context_repo.mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=str(knowledge_base["id"]),
        updated_by_user_id=created_by_user_id,
        last_sync_summary="Preparing managed knowledge base index.",
    )
    try:
        _ensure_knowledge_base_index(database_url, config, knowledge_base)
    except Exception:
        context_repo.set_knowledge_base_sync_result(
            database_url,
            knowledge_base_id=str(knowledge_base["id"]),
            sync_status="error",
            last_sync_error="Unable to prepare the backing vector index.",
            last_sync_summary="Knowledge base initialization failed.",
            updated_by_user_id=created_by_user_id,
        )
        raise
    refreshed = context_repo.set_knowledge_base_sync_result(
        database_url,
        knowledge_base_id=str(knowledge_base["id"]),
        sync_status="ready",
        last_sync_error=None,
        last_sync_summary="Managed knowledge base index is ready.",
        updated_by_user_id=created_by_user_id,
    )
    return _serialize_knowledge_base(refreshed or knowledge_base)


def update_knowledge_base(
    database_url: str,
    *,
    knowledge_base_id: str,
    payload: dict[str, Any],
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    existing = _require_knowledge_base(database_url, knowledge_base_id)
    normalized = _normalize_knowledge_base_payload(payload, is_create=False, existing=existing)
    if (
        normalized["lifecycle_state"] == "archived"
        and str(existing.get("lifecycle_state") or "").strip().lower() != "archived"
    ):
        binding_count = context_repo.count_deployment_bindings_for_knowledge_base(
            database_url,
            knowledge_base_id=knowledge_base_id,
        )
        if binding_count > 0:
            raise PlatformControlPlaneError(
                "knowledge_base_in_use",
                "Knowledge base is still bound to one or more deployments",
                status_code=409,
                details={"binding_count": binding_count, "knowledge_base_id": knowledge_base_id},
            )
    updated = context_repo.update_knowledge_base(
        database_url,
        knowledge_base_id=knowledge_base_id,
        slug=normalized["slug"],
        display_name=normalized["display_name"],
        description=normalized["description"],
        lifecycle_state=normalized["lifecycle_state"],
        sync_status=str(existing.get("sync_status") or "ready"),
        updated_by_user_id=updated_by_user_id,
    )
    if updated is None:
        raise PlatformControlPlaneError("knowledge_base_not_found", "Knowledge base not found", status_code=404)
    return _serialize_knowledge_base(updated)


def delete_knowledge_base(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
) -> None:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    binding_count = context_repo.count_deployment_bindings_for_knowledge_base(
        database_url,
        knowledge_base_id=knowledge_base_id,
    )
    if binding_count > 0:
        raise PlatformControlPlaneError(
            "knowledge_base_in_use",
            "Knowledge base is still bound to one or more deployments",
            status_code=409,
            details={"binding_count": binding_count, "knowledge_base_id": knowledge_base_id},
        )
    documents = context_repo.list_documents(database_url, knowledge_base_id=knowledge_base_id)
    for document in documents:
        _delete_document_chunks(
            database_url,
            config,
            knowledge_base=knowledge_base,
            document=document,
        )
    if not context_repo.delete_knowledge_base(database_url, knowledge_base_id):
        raise PlatformControlPlaneError("knowledge_base_not_found", "Knowledge base not found", status_code=404)


def list_knowledge_base_documents(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    _require_knowledge_base(database_url, knowledge_base_id)
    return [_serialize_document(row) for row in context_repo.list_documents(database_url, knowledge_base_id=knowledge_base_id)]


def create_knowledge_base_document(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    payload: dict[str, Any],
    created_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=created_by_user_id,
        summary="Indexing knowledge-base document.",
    )
    document_id = str(uuid4())
    normalized = _normalize_document_payload(payload)
    chunks = _chunk_document_text(normalized["text"])
    document = context_repo.create_document(
        database_url,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
        title=normalized["title"],
        source_type=normalized["source_type"],
        source_name=normalized["source_name"],
        uri=normalized["uri"],
        text=normalized["text"],
        metadata_json=normalized["metadata"],
        chunk_count=len(chunks),
        created_by_user_id=created_by_user_id,
        updated_by_user_id=created_by_user_id,
    )
    try:
        _upsert_document_chunks(database_url, config, knowledge_base=knowledge_base, document=document, chunks=chunks)
    except Exception:
        context_repo.delete_document(database_url, knowledge_base_id=knowledge_base_id, document_id=document_id)
        _refresh_document_count(database_url, knowledge_base_id=knowledge_base_id, updated_by_user_id=created_by_user_id)
        _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=created_by_user_id,
            summary="Document indexing failed.",
        )
        raise
    _refresh_document_count(database_url, knowledge_base_id=knowledge_base_id, updated_by_user_id=created_by_user_id)
    _mark_knowledge_base_sync_ready(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=created_by_user_id,
        summary="Knowledge-base document indexed successfully.",
    )
    return _serialize_document(document)


def update_knowledge_base_document(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    document_id: str,
    payload: dict[str, Any],
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    existing = context_repo.get_document(database_url, knowledge_base_id=knowledge_base_id, document_id=document_id)
    if existing is None:
        raise PlatformControlPlaneError("knowledge_document_not_found", "Knowledge document not found", status_code=404)
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary="Re-indexing knowledge-base document.",
    )
    normalized = _normalize_document_payload(payload, existing=existing)
    chunks = _chunk_document_text(normalized["text"])
    try:
        _delete_document_chunks(database_url, config, knowledge_base=knowledge_base, document=existing)
        updated = context_repo.update_document(
            database_url,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            title=normalized["title"],
            source_type=normalized["source_type"],
            source_name=normalized["source_name"],
            uri=normalized["uri"],
            text=normalized["text"],
            metadata_json=normalized["metadata"],
            chunk_count=len(chunks),
            updated_by_user_id=updated_by_user_id,
        )
        if updated is None:
            raise PlatformControlPlaneError("knowledge_document_not_found", "Knowledge document not found", status_code=404)
        _upsert_document_chunks(database_url, config, knowledge_base=knowledge_base, document=updated, chunks=chunks)
        _refresh_document_count(database_url, knowledge_base_id=knowledge_base_id, updated_by_user_id=updated_by_user_id)
        _mark_knowledge_base_sync_ready(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary="Knowledge-base document re-indexed successfully.",
        )
        return _serialize_document(updated)
    except Exception:
        _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary="Document re-index failed.",
        )
        raise


def delete_knowledge_base_document(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    document_id: str,
    updated_by_user_id: int | None,
) -> None:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    document = context_repo.get_document(database_url, knowledge_base_id=knowledge_base_id, document_id=document_id)
    if document is None:
        raise PlatformControlPlaneError("knowledge_document_not_found", "Knowledge document not found", status_code=404)
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary="Removing knowledge-base document from the vector index.",
    )
    try:
        _delete_document_chunks(database_url, config, knowledge_base=knowledge_base, document=document)
        if not context_repo.delete_document(database_url, knowledge_base_id=knowledge_base_id, document_id=document_id):
            raise PlatformControlPlaneError("knowledge_document_not_found", "Knowledge document not found", status_code=404)
        _refresh_document_count(database_url, knowledge_base_id=knowledge_base_id, updated_by_user_id=updated_by_user_id)
        _mark_knowledge_base_sync_ready(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary="Knowledge-base document deleted and index updated.",
        )
    except Exception:
        _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary="Document deletion sync failed.",
        )
        raise


def upload_knowledge_base_documents(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    files: list[Any],
    created_by_user_id: int | None,
) -> dict[str, Any]:
    _require_knowledge_base(database_url, knowledge_base_id)
    if not files:
        raise PlatformControlPlaneError("invalid_upload", "At least one file is required", status_code=400)
    if len(files) > _MAX_UPLOAD_FILES:
        raise PlatformControlPlaneError(
            "upload_limit_exceeded",
            f"Upload supports at most {_MAX_UPLOAD_FILES} files at a time",
            status_code=400,
        )
    created_documents: list[dict[str, Any]] = []
    for file_storage in files:
        parsed_documents = _parse_upload_documents(file_storage)
        if len(created_documents) + len(parsed_documents) > _MAX_UPLOAD_DOCUMENTS:
            raise PlatformControlPlaneError(
                "upload_limit_exceeded",
                f"Upload supports at most {_MAX_UPLOAD_DOCUMENTS} documents at a time",
                status_code=400,
            )
        for parsed_document in parsed_documents:
            created_documents.append(
                create_knowledge_base_document(
                    database_url,
                    config=config,
                    knowledge_base_id=knowledge_base_id,
                    payload=parsed_document,
                    created_by_user_id=created_by_user_id,
                )
            )
    return {"documents": created_documents, "count": len(created_documents)}


def resync_knowledge_base(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    documents = context_repo.list_documents(database_url, knowledge_base_id=knowledge_base_id)
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary="Rebuilding vector index from stored documents.",
    )
    try:
        adapter = _resolve_knowledge_base_vector_adapter(database_url, config, knowledge_base)
        adapter.delete_index(index_name=str(knowledge_base["index_name"]))
        adapter.ensure_index(
            index_name=str(knowledge_base["index_name"]),
            schema=dict(knowledge_base.get("schema_json") or {}),
        )
        total_chunks = 0
        for document in documents:
            chunks = _chunk_document_text(str(document.get("text") or ""))
            total_chunks += len(chunks)
            synced_document = document
            if int(document.get("chunk_count") or 0) != len(chunks):
                updated_document = context_repo.set_document_chunk_count(
                    database_url,
                    knowledge_base_id=knowledge_base_id,
                    document_id=str(document["id"]),
                    chunk_count=len(chunks),
                    updated_by_user_id=updated_by_user_id,
                )
                if updated_document is not None:
                    synced_document = updated_document
            if chunks:
                _upsert_document_chunks(
                    database_url,
                    config,
                    knowledge_base=knowledge_base,
                    document=synced_document,
                    chunks=chunks,
                )
        _refresh_document_count(database_url, knowledge_base_id=knowledge_base_id, updated_by_user_id=updated_by_user_id)
        refreshed = _mark_knowledge_base_sync_ready(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=f"Resynced {len(documents)} document(s) and {total_chunks} chunk(s).",
        )
        return _serialize_knowledge_base(refreshed or _require_knowledge_base(database_url, knowledge_base_id))
    except Exception:
        refreshed = _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary="Knowledge-base resync failed.",
        )
        if refreshed is not None:
            knowledge_base = refreshed
        raise


def query_knowledge_base(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from .embeddings_service import embed_text_inputs
    from .platform_service import resolve_vector_store_adapter

    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    if not _is_knowledge_base_eligible(knowledge_base):
        raise PlatformControlPlaneError(
            "knowledge_base_not_ready",
            "Only active and ready knowledge bases can be queried.",
            status_code=409,
            details={"knowledge_base_id": knowledge_base_id},
        )
    query_text = str(payload.get("query_text") or "").strip()
    if not query_text:
        raise PlatformControlPlaneError("invalid_query_text", "query_text must be a non-empty string", status_code=400)
    top_k = _normalize_query_top_k(payload.get("top_k"))
    vector_adapter = resolve_vector_store_adapter(database_url, config)
    if str(vector_adapter.binding.provider_key or "").strip().lower() != str(knowledge_base.get("backing_provider_key") or "").strip().lower():
        raise PlatformControlPlaneError(
            "knowledge_base_provider_mismatch",
            "The active deployment vector store provider does not match this knowledge base.",
            status_code=409,
            details={
                "knowledge_base_id": knowledge_base_id,
                "knowledge_base_provider_key": knowledge_base.get("backing_provider_key"),
                "active_provider_key": vector_adapter.binding.provider_key,
            },
        )
    embedding_payload = embed_text_inputs(database_url, config, [query_text])
    query_payload = vector_adapter.query(
        index_name=str(knowledge_base["index_name"]),
        query_text=None,
        embedding=embedding_payload["embeddings"][0],
        top_k=top_k,
        filters={},
    )
    results = query_payload.get("results") if isinstance(query_payload.get("results"), list) else []
    return {
        "knowledge_base_id": str(knowledge_base["id"]),
        "retrieval": {
            "index": str(query_payload.get("index") or knowledge_base.get("index_name") or "").strip(),
            "result_count": len(results),
            "top_k": top_k,
        },
        "results": [_serialize_query_result(item) for item in results if isinstance(item, dict)],
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


def list_active_runtime_knowledge_bases(
    platform_runtime: dict[str, Any],
    *,
    database_url: str | None = None,
) -> dict[str, Any]:
    capabilities = platform_runtime.get("capabilities") if isinstance(platform_runtime.get("capabilities"), dict) else {}
    vector_store = capabilities.get(CAPABILITY_VECTOR_STORE) if isinstance(capabilities.get(CAPABILITY_VECTOR_STORE), dict) else {}
    resources = vector_store.get("resources") if isinstance(vector_store.get("resources"), list) else []
    knowledge_bases = [
        _serialize_runtime_knowledge_base(item, default_resource_id=str(vector_store.get("default_resource_id") or "").strip() or None)
        for item in resources
        if isinstance(item, dict) and str(item.get("ref_type") or "").strip().lower() == "knowledge_base"
    ]
    if database_url:
        current_rows = {
            str(row.get("id") or "").strip(): row
            for row in context_repo.get_knowledge_bases(database_url, [str(item["id"]) for item in knowledge_bases])
        }
        knowledge_bases = [
            {
                **item,
                "is_eligible": _is_knowledge_base_eligible(current_rows[item["id"]]),
                "lifecycle_state": str(current_rows[item["id"]].get("lifecycle_state") or "").strip() or None,
                "sync_status": str(current_rows[item["id"]].get("sync_status") or "").strip() or None,
            }
            for item in knowledge_bases
            if item["id"] in current_rows and _is_knowledge_base_eligible(current_rows[item["id"]])
        ]
    default_knowledge_base_id = next((item["id"] for item in knowledge_bases if item["is_default"]), None)
    if default_knowledge_base_id is None and len(knowledge_bases) == 1:
        default_knowledge_base_id = knowledge_bases[0]["id"]
    selection_mode = str((vector_store.get("resource_policy") or {}).get("selection_mode") or "explicit").strip().lower()
    configuration_message = None
    if not knowledge_bases:
        if selection_mode == "dynamic_namespace":
            configuration_message = (
                "The active deployment uses dynamic vector namespaces and has no managed knowledge bases bound."
            )
        else:
            configuration_message = "The active deployment has no managed knowledge bases bound."
    return {
        "knowledge_bases": knowledge_bases,
        "default_knowledge_base_id": default_knowledge_base_id,
        "selection_required": len(knowledge_bases) > 1 and default_knowledge_base_id is None,
        "configuration_message": configuration_message,
    }


def resolve_runtime_knowledge_base_selection(
    platform_runtime: dict[str, Any],
    *,
    database_url: str | None = None,
    knowledge_base_id: str | None,
) -> dict[str, Any]:
    options = list_active_runtime_knowledge_bases(platform_runtime, database_url=database_url)
    knowledge_bases = options["knowledge_bases"]
    normalized_id = str(knowledge_base_id or "").strip() or None
    if not knowledge_bases:
        raise PlatformControlPlaneError(
            "knowledge_base_not_configured",
            str(options.get("configuration_message") or "No managed knowledge bases are bound to the active deployment."),
            status_code=409,
        )
    if normalized_id:
        selected = next((item for item in knowledge_bases if item["id"] == normalized_id), None)
        if selected is None:
            raise PlatformControlPlaneError(
                "knowledge_base_not_bound",
                "Requested knowledge base is not bound to the active deployment",
                status_code=403,
                details={"knowledge_base_id": normalized_id},
            )
        return selected
    if options["default_knowledge_base_id"]:
        selected = next((item for item in knowledge_bases if item["id"] == options["default_knowledge_base_id"]), None)
        if selected is not None:
            return selected
    if len(knowledge_bases) == 1:
        return knowledge_bases[0]
    raise PlatformControlPlaneError(
        "knowledge_base_required",
        "Select a knowledge base before starting knowledge chat.",
        status_code=400,
    )


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


def _chunk_document_text(text: str) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    chunks: list[str] = []
    paragraphs = [item.strip() for item in normalized.split("\n\n") if item.strip()]
    current = ""
    for paragraph in paragraphs or [normalized]:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= _DEFAULT_CHUNK_SIZE:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(paragraph) > _DEFAULT_CHUNK_SIZE:
            chunks.append(paragraph[:_DEFAULT_CHUNK_SIZE].strip())
            paragraph = paragraph[_DEFAULT_CHUNK_SIZE :].strip()
        current = paragraph
    if current:
        chunks.append(current)
    return [item for item in chunks if item]


def _upsert_document_chunks(
    database_url: str,
    config: AuthConfig,
    *,
    knowledge_base: dict[str, Any],
    document: dict[str, Any],
    chunks: list[str],
) -> None:
    if not chunks:
        raise PlatformControlPlaneError("invalid_document_text", "text is required", status_code=400)
    adapter = _resolve_knowledge_base_vector_adapter(database_url, config, knowledge_base)
    adapter.ensure_index(index_name=str(knowledge_base["index_name"]), schema=dict(knowledge_base.get("schema_json") or {}))
    documents = [
        {
            "id": _chunk_document_id(str(document["id"]), index),
            "text": chunk,
            "metadata": {
                "knowledge_base_id": str(knowledge_base["id"]),
                "document_id": str(document["id"]),
                "chunk_index": index,
                "title": str(document.get("title") or "").strip(),
                "source_type": str(document.get("source_type") or "").strip(),
                "source_name": str(document.get("source_name") or "").strip() or None,
                "uri": str(document.get("uri") or "").strip() or None,
            },
        }
        for index, chunk in enumerate(chunks)
    ]
    adapter.upsert(index_name=str(knowledge_base["index_name"]), documents=documents)


def _delete_document_chunks(
    database_url: str,
    config: AuthConfig,
    *,
    knowledge_base: dict[str, Any],
    document: dict[str, Any],
) -> None:
    chunk_count = int(document.get("chunk_count") or 0)
    if chunk_count <= 0:
        return
    adapter = _resolve_knowledge_base_vector_adapter(database_url, config, knowledge_base)
    adapter.delete(
        index_name=str(knowledge_base["index_name"]),
        ids=[_chunk_document_id(str(document["id"]), index) for index in range(chunk_count)],
    )


def _refresh_document_count(database_url: str, *, knowledge_base_id: str, updated_by_user_id: int | None) -> None:
    count = len(context_repo.list_documents(database_url, knowledge_base_id=knowledge_base_id))
    context_repo.set_knowledge_base_document_count(
        database_url,
        knowledge_base_id=knowledge_base_id,
        document_count=count,
        updated_by_user_id=updated_by_user_id,
    )


def _ensure_knowledge_base_index(database_url: str, config: AuthConfig, knowledge_base: dict[str, Any]) -> None:
    adapter = _resolve_knowledge_base_vector_adapter(database_url, config, knowledge_base)
    adapter.ensure_index(
        index_name=str(knowledge_base["index_name"]),
        schema=dict(knowledge_base.get("schema_json") or {}),
    )


def _resolve_knowledge_base_vector_adapter(database_url: str, config: AuthConfig, knowledge_base: dict[str, Any]):
    from . import platform_service

    platform_service.ensure_platform_bootstrap_state(database_url, config)
    provider_key = str(knowledge_base.get("backing_provider_key") or "").strip().lower()
    provider_row = next(
        (
            row for row in platform_repo.list_provider_instances(database_url)
            if str(row.get("capability_key") or "").strip().lower() == CAPABILITY_VECTOR_STORE
            and str(row.get("provider_key") or "").strip().lower() == provider_key
            and bool(row.get("enabled", True))
        ),
        None,
    )
    if provider_row is None:
        raise PlatformControlPlaneError(
            "vector_provider_not_found",
            "Backing vector provider is not configured",
            status_code=409,
            details={"provider_key": provider_key},
        )
    return platform_service.resolve_vector_store_adapter(
        database_url,
        config,
        provider_instance_id=str(provider_row["id"]),
    )


def _require_knowledge_base(database_url: str, knowledge_base_id: str) -> dict[str, Any]:
    row = context_repo.get_knowledge_base(database_url, knowledge_base_id)
    if row is None:
        raise PlatformControlPlaneError("knowledge_base_not_found", "Knowledge base not found", status_code=404)
    return row


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
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
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


def _mark_knowledge_base_syncing(
    database_url: str,
    *,
    knowledge_base_id: str,
    updated_by_user_id: int | None,
    summary: str,
) -> dict[str, Any] | None:
    return context_repo.mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        last_sync_summary=summary,
    )


def _mark_knowledge_base_sync_ready(
    database_url: str,
    *,
    knowledge_base_id: str,
    updated_by_user_id: int | None,
    summary: str,
) -> dict[str, Any] | None:
    return context_repo.set_knowledge_base_sync_result(
        database_url,
        knowledge_base_id=knowledge_base_id,
        sync_status="ready",
        last_sync_error=None,
        last_sync_summary=summary,
        updated_by_user_id=updated_by_user_id,
    )


def _mark_knowledge_base_sync_error(
    database_url: str,
    *,
    knowledge_base_id: str,
    updated_by_user_id: int | None,
    summary: str,
) -> dict[str, Any] | None:
    return context_repo.set_knowledge_base_sync_result(
        database_url,
        knowledge_base_id=knowledge_base_id,
        sync_status="error",
        last_sync_error=summary,
        last_sync_summary=summary,
        updated_by_user_id=updated_by_user_id,
    )


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


def _is_knowledge_base_eligible(row: dict[str, Any]) -> bool:
    return (
        str(row.get("lifecycle_state") or "").strip().lower() == "active"
        and str(row.get("sync_status") or "").strip().lower() == "ready"
    )


def _chunk_document_id(document_id: str, index: int) -> str:
    return f"{document_id}::chunk::{index}"


def _parse_upload_documents(file_storage: Any) -> list[dict[str, Any]]:
    filename = str(getattr(file_storage, "filename", "") or "").strip()
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_UPLOAD_EXTENSIONS:
        raise PlatformControlPlaneError(
            "unsupported_upload_type",
            "Supported upload types are .txt, .md, .json, and .jsonl",
            status_code=400,
            details={"filename": filename},
        )
    raw_bytes = file_storage.read()
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise PlatformControlPlaneError("invalid_upload", "Uploaded file could not be read", status_code=400)
    if len(raw_bytes) > _MAX_FILE_SIZE_BYTES:
        raise PlatformControlPlaneError(
            "upload_limit_exceeded",
            f"Uploaded files must be smaller than {_MAX_FILE_SIZE_BYTES} bytes",
            status_code=400,
            details={"filename": filename},
        )
    text = raw_bytes.decode("utf-8")
    if suffix in {".txt", ".md"}:
        return [{
            "title": Path(filename).stem or "Uploaded document",
            "source_type": "upload",
            "source_name": filename or None,
            "text": text.strip(),
            "metadata": {},
        }]
    if suffix == ".json":
        parsed = json.loads(text)
        return _documents_from_json_payload(parsed, filename=filename)
    if suffix == ".jsonl":
        documents = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            normalized = line.strip()
            if not normalized:
                continue
            try:
                parsed_line = json.loads(normalized)
            except json.JSONDecodeError as exc:
                raise PlatformControlPlaneError(
                    "invalid_upload_json",
                    f"{filename} contains invalid JSON on line {line_number}",
                    status_code=400,
                ) from exc
            documents.extend(_documents_from_json_payload(parsed_line, filename=filename))
        return documents
    raise PlatformControlPlaneError("unsupported_upload_type", "Unsupported upload type", status_code=400)


def _documents_from_json_payload(payload: Any, *, filename: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [_document_from_json_item(item, filename=filename, position=index) for index, item in enumerate(payload)]
    return [_document_from_json_item(payload, filename=filename, position=0)]


def _document_from_json_item(item: Any, *, filename: str, position: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise PlatformControlPlaneError(
            "invalid_upload_json",
            "Uploaded JSON documents must be objects",
            status_code=400,
            details={"filename": filename, "position": position},
        )
    title = str(item.get("title") or item.get("name") or f"{Path(filename).stem}-{position + 1}").strip()
    text = str(item.get("text") or item.get("content") or "").strip()
    if not text:
        raise PlatformControlPlaneError(
            "invalid_upload_json",
            "Uploaded JSON documents must include text or content",
            status_code=400,
            details={"filename": filename, "position": position},
        )
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    return {
        "title": title,
        "source_type": str(item.get("source_type") or "upload").strip().lower() or "upload",
        "source_name": str(item.get("source_name") or filename).strip() or None,
        "uri": str(item.get("uri") or "").strip() or None,
        "text": text,
        "metadata": dict(metadata),
    }
