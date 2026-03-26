from __future__ import annotations

import fnmatch
import io
import json
import re
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from ..config import AuthConfig
from ..repositories import context_management as context_repo
from ..repositories import platform_control_plane as platform_repo
from .platform_types import CAPABILITY_VECTOR_STORE, PlatformControlPlaneError

_SUPPORTED_SCHEMA_PROPERTY_TYPES = {"text", "number", "int", "boolean"}
_SUPPORTED_UPLOAD_EXTENSIONS = {".txt", ".md", ".json", ".jsonl", ".pdf"}
_SUPPORTED_BACKING_PROVIDER_KEYS = {"weaviate_local"}
_KB_LIFECYCLE_STATES = {"active", "archived"}
_KB_SYNC_STATES = {"ready", "syncing", "error"}
_SOURCE_TYPES = {"local_directory"}
_SOURCE_LIFECYCLE_STATES = {"active", "archived"}
_SOURCE_SYNC_STATES = {"idle", "syncing", "ready", "error"}
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


def list_knowledge_sources(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    _require_knowledge_base(database_url, knowledge_base_id)
    return [_serialize_knowledge_source(row) for row in context_repo.list_knowledge_sources(
        database_url,
        knowledge_base_id=knowledge_base_id,
    )]


def create_knowledge_source(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    payload: dict[str, Any],
    created_by_user_id: int | None,
) -> dict[str, Any]:
    _require_knowledge_base(database_url, knowledge_base_id)
    normalized = _normalize_knowledge_source_payload(payload)
    _resolve_source_directory(config, normalized["relative_path"], require_exists=True)
    source = context_repo.create_knowledge_source(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_type=normalized["source_type"],
        display_name=normalized["display_name"],
        relative_path=normalized["relative_path"],
        include_globs=normalized["include_globs"],
        exclude_globs=normalized["exclude_globs"],
        lifecycle_state=normalized["lifecycle_state"],
        created_by_user_id=created_by_user_id,
        updated_by_user_id=created_by_user_id,
    )
    return _serialize_knowledge_source(source)


def update_knowledge_source(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    source_id: str,
    payload: dict[str, Any],
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    existing = _require_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id)
    normalized = _normalize_knowledge_source_payload(payload, existing=existing)
    _resolve_source_directory(config, normalized["relative_path"], require_exists=True)
    updated = context_repo.update_knowledge_source(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
        display_name=normalized["display_name"],
        relative_path=normalized["relative_path"],
        include_globs=normalized["include_globs"],
        exclude_globs=normalized["exclude_globs"],
        lifecycle_state=normalized["lifecycle_state"],
        updated_by_user_id=updated_by_user_id,
    )
    if updated is None:
        raise PlatformControlPlaneError("knowledge_source_not_found", "Knowledge source not found", status_code=404)
    return _serialize_knowledge_source(updated)


def delete_knowledge_source(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    source_id: str,
    updated_by_user_id: int | None,
) -> None:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    source = _require_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id)
    source_documents = context_repo.list_source_documents(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
    )
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary=f"Removing managed source '{source['display_name']}' and its indexed documents.",
    )
    try:
        for document in source_documents:
            _delete_document_chunks(
                database_url,
                config,
                knowledge_base=knowledge_base,
                document=document,
            )
            context_repo.delete_document(
                database_url,
                knowledge_base_id=knowledge_base_id,
                document_id=str(document["id"]),
            )
        if not context_repo.delete_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id):
            raise PlatformControlPlaneError("knowledge_source_not_found", "Knowledge source not found", status_code=404)
        _refresh_document_count(database_url, knowledge_base_id=knowledge_base_id, updated_by_user_id=updated_by_user_id)
        _mark_knowledge_base_sync_ready(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=f"Removed managed source '{source['display_name']}' and {len(source_documents)} sourced document(s).",
        )
    except Exception:
        _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=f"Removing managed source '{source['display_name']}' failed.",
        )
        raise


def list_knowledge_base_sync_runs(database_url: str, *, knowledge_base_id: str) -> list[dict[str, Any]]:
    _require_knowledge_base(database_url, knowledge_base_id)
    return [_serialize_sync_run(row) for row in context_repo.list_sync_runs(
        database_url,
        knowledge_base_id=knowledge_base_id,
    )]


def sync_knowledge_source(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    source_id: str,
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    source = _require_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id)
    if str(source.get("lifecycle_state") or "").strip().lower() != "active":
        raise PlatformControlPlaneError(
            "knowledge_source_inactive",
            "Only active knowledge sources can be synced.",
            status_code=409,
            details={"source_id": source_id, "lifecycle_state": source.get("lifecycle_state")},
        )
    _, source_directory = _resolve_source_directory(config, str(source.get("relative_path") or "").strip(), require_exists=True)
    run = context_repo.create_sync_run(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
        created_by_user_id=updated_by_user_id,
    )
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary=f"Syncing managed source '{source['display_name']}'.",
    )
    context_repo.mark_knowledge_source_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
    )
    try:
        result = _sync_knowledge_source_documents(
            database_url,
            config,
            knowledge_base=knowledge_base,
            source=source,
            source_directory=source_directory,
            updated_by_user_id=updated_by_user_id,
        )
        finished_run = context_repo.finish_sync_run(
            database_url,
            run_id=str(run["id"]),
            status="ready",
            scanned_file_count=result["scanned_file_count"],
            changed_file_count=result["changed_file_count"],
            deleted_file_count=result["deleted_file_count"],
            created_document_count=result["created_document_count"],
            updated_document_count=result["updated_document_count"],
            deleted_document_count=result["deleted_document_count"],
            error_summary=None,
        )
        refreshed_source = context_repo.set_knowledge_source_sync_result(
            database_url,
            knowledge_base_id=knowledge_base_id,
            source_id=source_id,
            last_sync_status="ready",
            last_sync_error=None,
        )
        refreshed_kb = _mark_knowledge_base_sync_ready(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=(
                f"Source '{source['display_name']}' synced "
                f"{result['created_document_count']} created, "
                f"{result['updated_document_count']} updated, "
                f"{result['deleted_document_count']} deleted document(s)."
            ),
        )
        return {
            "knowledge_base": _serialize_knowledge_base(refreshed_kb or knowledge_base),
            "source": _serialize_knowledge_source(refreshed_source or source),
            "sync_run": _serialize_sync_run(finished_run or run),
        }
    except Exception as exc:
        message = str(exc).strip() or "Knowledge source sync failed."
        finished_run = context_repo.finish_sync_run(
            database_url,
            run_id=str(run["id"]),
            status="error",
            scanned_file_count=0,
            changed_file_count=0,
            deleted_file_count=0,
            created_document_count=0,
            updated_document_count=0,
            deleted_document_count=0,
            error_summary=message,
        )
        refreshed_source = context_repo.set_knowledge_source_sync_result(
            database_url,
            knowledge_base_id=knowledge_base_id,
            source_id=source_id,
            last_sync_status="error",
            last_sync_error=message,
        )
        _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=f"Source '{source['display_name']}' sync failed.",
        )
        if isinstance(exc, PlatformControlPlaneError):
            raise
        raise PlatformControlPlaneError(
            "knowledge_source_sync_failed",
            message,
            status_code=500,
            details={
                "source_id": source_id,
                "knowledge_base_id": knowledge_base_id,
                "sync_run_id": str((finished_run or run).get("id") or "").strip(),
                "last_sync_status": str((refreshed_source or source).get("last_sync_status") or "").strip() or "error",
            },
        ) from exc


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
    if bool(existing.get("managed_by_source")):
        raise PlatformControlPlaneError(
            "knowledge_document_managed_by_source",
            "Source-managed documents must be edited through their knowledge source.",
            status_code=409,
            details={"document_id": document_id, "source_id": existing.get("source_id")},
        )
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
    if bool(document.get("managed_by_source")):
        raise PlatformControlPlaneError(
            "knowledge_document_managed_by_source",
            "Source-managed documents must be removed by syncing or deleting their knowledge source.",
            status_code=409,
            details={"document_id": document_id, "source_id": document.get("source_id")},
        )
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


def _normalize_source_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip().strip("/")
    if not normalized:
        return ""
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        raise PlatformControlPlaneError(
            "invalid_source_relative_path",
            "relative_path must stay within an allowlisted context source root.",
            status_code=400,
        )
    return "/".join(parts)


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


def _sync_knowledge_source_documents(
    database_url: str,
    config: AuthConfig,
    *,
    knowledge_base: dict[str, Any],
    source: dict[str, Any],
    source_directory: Path,
    updated_by_user_id: int | None,
) -> dict[str, int]:
    scanned_file_count = 0
    created_document_count = 0
    updated_document_count = 0
    deleted_document_count = 0
    changed_paths: set[str] = set()
    deleted_paths: set[str] = set()
    seen_keys: set[str] = set()
    source_id = str(source["id"])
    include_globs = list(source.get("include_globs") or [])
    exclude_globs = list(source.get("exclude_globs") or [])

    for file_path, relative_path in _iter_source_files(
        source_directory,
        include_globs=include_globs,
        exclude_globs=exclude_globs,
    ):
        scanned_file_count += 1
        parsed_documents = _parse_source_documents(file_path, relative_path=relative_path, source=source)
        for position, parsed_document in enumerate(parsed_documents):
            source_document_key = _source_document_key(relative_path, position)
            seen_keys.add(source_document_key)
            existing = context_repo.get_document_by_source_key(
                database_url,
                knowledge_base_id=str(knowledge_base["id"]),
                source_id=source_id,
                source_document_key=source_document_key,
            )
            chunks = _chunk_document_text(parsed_document["text"])
            if existing is None:
                document = context_repo.create_document(
                    database_url,
                    document_id=_source_document_id(source_id, source_document_key),
                    knowledge_base_id=str(knowledge_base["id"]),
                    title=parsed_document["title"],
                    source_type=parsed_document["source_type"],
                    source_name=parsed_document["source_name"],
                    uri=parsed_document["uri"],
                    text=parsed_document["text"],
                    metadata_json=parsed_document["metadata"],
                    chunk_count=len(chunks),
                    source_id=source_id,
                    source_path=relative_path,
                    source_document_key=source_document_key,
                    managed_by_source=True,
                    created_by_user_id=updated_by_user_id,
                    updated_by_user_id=updated_by_user_id,
                )
                _upsert_document_chunks(database_url, config, knowledge_base=knowledge_base, document=document, chunks=chunks)
                created_document_count += 1
                changed_paths.add(relative_path)
                continue
            if not _source_document_changed(
                existing,
                parsed_document=parsed_document,
                chunk_count=len(chunks),
                source_path=relative_path,
                source_document_key=source_document_key,
            ):
                continue
            _delete_document_chunks(database_url, config, knowledge_base=knowledge_base, document=existing)
            updated = context_repo.update_document(
                database_url,
                knowledge_base_id=str(knowledge_base["id"]),
                document_id=str(existing["id"]),
                title=parsed_document["title"],
                source_type=parsed_document["source_type"],
                source_name=parsed_document["source_name"],
                uri=parsed_document["uri"],
                text=parsed_document["text"],
                metadata_json=parsed_document["metadata"],
                chunk_count=len(chunks),
                source_id=source_id,
                source_path=relative_path,
                source_document_key=source_document_key,
                managed_by_source=True,
                updated_by_user_id=updated_by_user_id,
            )
            if updated is None:
                raise PlatformControlPlaneError("knowledge_document_not_found", "Knowledge document not found", status_code=404)
            _upsert_document_chunks(database_url, config, knowledge_base=knowledge_base, document=updated, chunks=chunks)
            updated_document_count += 1
            changed_paths.add(relative_path)

    existing_documents = context_repo.list_source_documents(
        database_url,
        knowledge_base_id=str(knowledge_base["id"]),
        source_id=source_id,
    )
    for document in existing_documents:
        source_document_key = str(document.get("source_document_key") or "").strip()
        if source_document_key in seen_keys:
            continue
        _delete_document_chunks(database_url, config, knowledge_base=knowledge_base, document=document)
        context_repo.delete_document(
            database_url,
            knowledge_base_id=str(knowledge_base["id"]),
            document_id=str(document["id"]),
        )
        deleted_document_count += 1
        source_path = str(document.get("source_path") or "").strip()
        if source_path:
            deleted_paths.add(source_path)

    _refresh_document_count(
        database_url,
        knowledge_base_id=str(knowledge_base["id"]),
        updated_by_user_id=updated_by_user_id,
    )
    return {
        "scanned_file_count": scanned_file_count,
        "changed_file_count": len(changed_paths),
        "deleted_file_count": len(deleted_paths),
        "created_document_count": created_document_count,
        "updated_document_count": updated_document_count,
        "deleted_document_count": deleted_document_count,
    }


def _iter_source_files(
    source_directory: Path,
    *,
    include_globs: list[str],
    exclude_globs: list[str],
) -> list[tuple[Path, str]]:
    matched: list[tuple[Path, str]] = []
    for file_path in sorted(source_directory.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in _SUPPORTED_UPLOAD_EXTENSIONS:
            continue
        relative_path = file_path.relative_to(source_directory).as_posix()
        if include_globs and not any(fnmatch.fnmatch(relative_path, pattern) for pattern in include_globs):
            continue
        if exclude_globs and any(fnmatch.fnmatch(relative_path, pattern) for pattern in exclude_globs):
            continue
        matched.append((file_path, relative_path))
    return matched


def _parse_source_documents(file_path: Path, *, relative_path: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    raw_bytes = _read_ingestion_bytes(
        file_path.read_bytes,
        filename=relative_path,
        too_large_code="source_file_too_large",
        too_large_message=f"Source files must be smaller than {_MAX_FILE_SIZE_BYTES} bytes",
        read_error_code="invalid_source_file",
        read_error_message="Source file could not be read",
        details_key="relative_path",
    )
    documents = _parse_ingestion_documents(
        relative_path,
        raw_bytes,
        default_source_type="local_directory",
        default_source_name=str(source.get("display_name") or "").strip() or relative_path,
        invalid_json_code="invalid_source_json",
        invalid_pdf_code="invalid_source_pdf",
        details_key="relative_path",
    )
    return [
        {
            **document,
            "source_type": "local_directory",
            "source_name": str(source.get("display_name") or "").strip() or relative_path,
            "metadata": {
                **dict(document.get("metadata") or {}),
                "source_path": relative_path,
                "source_display_name": str(source.get("display_name") or "").strip() or None,
            },
        }
        for document in documents
    ]


def _source_document_changed(
    existing: dict[str, Any],
    *,
    parsed_document: dict[str, Any],
    chunk_count: int,
    source_path: str,
    source_document_key: str,
) -> bool:
    return any(
        (
            str(existing.get("title") or "").strip() != parsed_document["title"],
            str(existing.get("source_type") or "").strip() != parsed_document["source_type"],
            str(existing.get("source_name") or "").strip() != str(parsed_document.get("source_name") or "").strip(),
            str(existing.get("uri") or "").strip() != str(parsed_document.get("uri") or "").strip(),
            str(existing.get("text") or "") != parsed_document["text"],
            dict(existing.get("metadata_json") or {}) != dict(parsed_document.get("metadata") or {}),
            int(existing.get("chunk_count") or 0) != chunk_count,
            str(existing.get("source_path") or "").strip() != source_path,
            str(existing.get("source_document_key") or "").strip() != source_document_key,
            not bool(existing.get("managed_by_source")),
        )
    )


def _source_document_key(relative_path: str, position: int) -> str:
    return f"{relative_path}#{position}"


def _source_document_id(source_id: str, source_document_key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"knowledge-source:{source_id}:{source_document_key}"))


def _resolve_source_directory(
    config: AuthConfig,
    relative_path: str,
    *,
    require_exists: bool,
) -> tuple[str, Path]:
    normalized_relative_path = _normalize_source_relative_path(relative_path)
    if not normalized_relative_path:
        raise PlatformControlPlaneError("invalid_source_relative_path", "relative_path is required", status_code=400)
    configured_roots = [Path(root).expanduser().resolve() for root in config.context_source_roots if str(root).strip()]
    if not configured_roots:
        raise PlatformControlPlaneError(
            "context_source_roots_not_configured",
            "No context source roots are configured.",
            status_code=500,
        )
    existing_candidates: list[Path] = []
    fallback_candidate: Path | None = None
    for root in configured_roots:
        candidate = (root / normalized_relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        fallback_candidate = fallback_candidate or candidate
        if candidate.exists():
            if not candidate.is_dir():
                raise PlatformControlPlaneError(
                    "knowledge_source_not_directory",
                    "Knowledge source path must point to a directory.",
                    status_code=400,
                    details={"relative_path": normalized_relative_path},
                )
            existing_candidates.append(candidate)
    if require_exists:
        if not existing_candidates:
            raise PlatformControlPlaneError(
                "knowledge_source_path_not_found",
                "Knowledge source directory was not found under the configured source roots.",
                status_code=400,
                details={"relative_path": normalized_relative_path},
            )
        if len(existing_candidates) > 1:
            raise PlatformControlPlaneError(
                "knowledge_source_path_ambiguous",
                "Knowledge source path matches multiple configured source roots.",
                status_code=400,
                details={"relative_path": normalized_relative_path},
            )
        return normalized_relative_path, existing_candidates[0]
    if fallback_candidate is None:
        raise PlatformControlPlaneError(
            "invalid_source_relative_path",
            "relative_path must stay within an allowlisted context source root.",
            status_code=400,
        )
    return normalized_relative_path, fallback_candidate


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


def _require_knowledge_source(database_url: str, *, knowledge_base_id: str, source_id: str) -> dict[str, Any]:
    row = context_repo.get_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id)
    if row is None:
        raise PlatformControlPlaneError("knowledge_source_not_found", "Knowledge source not found", status_code=404)
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
    raw_bytes = _read_ingestion_bytes(
        lambda: getattr(file_storage, "read")(),
        filename=filename,
        too_large_code="upload_limit_exceeded",
        too_large_message=f"Uploaded files must be smaller than {_MAX_FILE_SIZE_BYTES} bytes",
        read_error_code="invalid_upload",
        read_error_message="Uploaded file could not be read",
        details_key="filename",
    )
    return _parse_ingestion_documents(
        filename,
        raw_bytes,
        default_source_type="upload",
        default_source_name=filename or None,
        invalid_json_code="invalid_upload_json",
        invalid_pdf_code="invalid_upload_pdf",
        details_key="filename",
    )


def _read_ingestion_bytes(
    read_bytes: Any,
    *,
    filename: str,
    too_large_code: str,
    too_large_message: str,
    read_error_code: str,
    read_error_message: str,
    details_key: str,
) -> bytes:
    try:
        raw_bytes = read_bytes()
    except Exception as exc:
        raise PlatformControlPlaneError(
            read_error_code,
            read_error_message,
            status_code=400,
            details={details_key: filename},
        ) from exc
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise PlatformControlPlaneError(
            read_error_code,
            read_error_message,
            status_code=400,
            details={details_key: filename},
        )
    if len(raw_bytes) > _MAX_FILE_SIZE_BYTES:
        raise PlatformControlPlaneError(
            too_large_code,
            too_large_message,
            status_code=400,
            details={details_key: filename},
        )
    return bytes(raw_bytes)


def _parse_ingestion_documents(
    filename: str,
    raw_bytes: bytes,
    *,
    default_source_type: str,
    default_source_name: str | None,
    invalid_json_code: str,
    invalid_pdf_code: str,
    details_key: str,
) -> list[dict[str, Any]]:
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_UPLOAD_EXTENSIONS:
        raise PlatformControlPlaneError(
            "unsupported_upload_type",
            "Supported upload types are .txt, .md, .json, .jsonl, and .pdf",
            status_code=400,
            details={details_key: filename},
        )
    if suffix in {".txt", ".md"}:
        text = raw_bytes.decode("utf-8")
        return [{
            "title": Path(filename).stem or "Uploaded document",
            "source_type": default_source_type,
            "source_name": default_source_name,
            "uri": None,
            "text": text.strip(),
            "metadata": {},
        }]
    if suffix == ".json":
        parsed = json.loads(raw_bytes.decode("utf-8"))
        return _documents_from_json_payload(parsed, filename=filename)
    if suffix == ".jsonl":
        documents: list[dict[str, Any]] = []
        for line_number, line in enumerate(raw_bytes.decode("utf-8").splitlines(), start=1):
            normalized = line.strip()
            if not normalized:
                continue
            try:
                parsed_line = json.loads(normalized)
            except json.JSONDecodeError as exc:
                raise PlatformControlPlaneError(
                    invalid_json_code,
                    f"{filename} contains invalid JSON on line {line_number}",
                    status_code=400,
                ) from exc
            documents.extend(_documents_from_json_payload(parsed_line, filename=filename))
        return documents
    if suffix == ".pdf":
        return [_extract_pdf_document(
            filename,
            raw_bytes,
            default_source_type=default_source_type,
            default_source_name=default_source_name,
            invalid_pdf_code=invalid_pdf_code,
            details_key=details_key,
        )]
    raise PlatformControlPlaneError("unsupported_upload_type", "Unsupported upload type", status_code=400)


def _extract_pdf_document(
    filename: str,
    raw_bytes: bytes,
    *,
    default_source_type: str,
    default_source_name: str | None,
    invalid_pdf_code: str,
    details_key: str,
) -> dict[str, Any]:
    PdfReader, pdf_error_types = _get_pdf_reader_dependencies()
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except pdf_error_types as exc:
        raise PlatformControlPlaneError(
            invalid_pdf_code,
            f"{filename} could not be parsed as a PDF document",
            status_code=400,
            details={details_key: filename},
        ) from exc
    except Exception as exc:
        raise PlatformControlPlaneError(
            invalid_pdf_code,
            f"{filename} could not be parsed as a PDF document",
            status_code=400,
            details={details_key: filename},
        ) from exc
    if bool(getattr(reader, "is_encrypted", False)):
        raise PlatformControlPlaneError(
            invalid_pdf_code,
            f"{filename} is encrypted and cannot be imported",
            status_code=400,
            details={details_key: filename},
        )
    pages = list(getattr(reader, "pages", []))
    page_count = len(pages)
    extracted_pages: list[str] = []
    for page in pages:
        page_text = str(page.extract_text() or "").strip()
        if page_text:
            extracted_pages.append(page_text)
    text = "\n\n".join(extracted_pages).strip()
    if not text:
        raise PlatformControlPlaneError(
            invalid_pdf_code,
            f"{filename} does not contain extractable text. Scanned-image PDFs require OCR, which is not supported yet.",
            status_code=400,
            details={details_key: filename},
        )
    return {
        "title": Path(filename).stem or "Uploaded document",
        "source_type": default_source_type,
        "source_name": default_source_name,
        "uri": None,
        "text": text,
        "metadata": {
            "page_count": page_count,
            "source_filename": Path(filename).name,
        },
    }


def _get_pdf_reader_dependencies():
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ModuleNotFoundError as exc:
        raise PlatformControlPlaneError(
            "pdf_parser_unavailable",
            "PDF support is unavailable because the pypdf dependency is not installed.",
            status_code=500,
        ) from exc
    return PdfReader, (PdfReadError,)


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
