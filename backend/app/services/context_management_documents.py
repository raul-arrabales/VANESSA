from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..config import AuthConfig
from ..repositories import context_management as context_repo
from .context_management_ingestion import _parse_upload_documents
from .context_management_serialization import (
    _normalize_document_payload,
    _normalize_schema_managed_metadata,
    _serialize_document,
    _serialize_knowledge_base,
    _serialize_sync_run,
)
from .context_management_shared import (
    _chunk_knowledge_base_page_texts,
    _chunk_knowledge_base_text,
    _delete_document_chunks,
    _mark_knowledge_base_sync_error,
    _mark_knowledge_base_sync_ready,
    _mark_knowledge_base_syncing,
    _refresh_document_count,
    _require_knowledge_base,
    _resolve_knowledge_base_vector_adapter,
    _resolve_source_directory,
    _upsert_document_chunks,
)
from .context_management_types import (
    KnowledgeBaseRecord,
    KnowledgeTextChunk,
    _MAX_UPLOAD_DOCUMENTS,
    _MAX_UPLOAD_FILES,
)
from .context_management_vectorization import require_knowledge_base_text_ingestion_supported
from .platform_types import PlatformControlPlaneError


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
    require_knowledge_base_text_ingestion_supported(knowledge_base)
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=created_by_user_id,
        summary="Indexing knowledge-base document.",
    )
    document_id = str(uuid4())
    normalized = _normalize_document_payload(payload)
    normalized["metadata"] = _normalize_schema_managed_metadata(
        dict(knowledge_base.get("schema_json") or {}),
        normalized["metadata"],
    )
    chunks = _chunk_document_payload(
        database_url,
        knowledge_base=knowledge_base,
        text=normalized["text"],
        page_texts=payload.get("page_texts"),
    )
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
    require_knowledge_base_text_ingestion_supported(knowledge_base)
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
    normalized["metadata"] = _normalize_schema_managed_metadata(
        dict(knowledge_base.get("schema_json") or {}),
        normalized["metadata"],
        existing_metadata=dict(existing.get("metadata_json") or {}),
    )
    chunks = _chunk_document_payload(
        database_url,
        knowledge_base=knowledge_base,
        text=normalized["text"],
        page_texts=payload.get("page_texts"),
    )
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
    metadata: dict[str, Any] | None,
    created_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    require_knowledge_base_text_ingestion_supported(knowledge_base)
    if not files:
        raise PlatformControlPlaneError("invalid_upload", "At least one file is required", status_code=400)
    if len(files) > _MAX_UPLOAD_FILES:
        raise PlatformControlPlaneError(
            "upload_limit_exceeded",
            f"Upload supports at most {_MAX_UPLOAD_FILES} files at a time",
            status_code=400,
        )
    normalized_batch_metadata = _normalize_schema_managed_metadata(
        dict(knowledge_base.get("schema_json") or {}),
        metadata or {},
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
                    payload={
                        **parsed_document,
                        "metadata": {
                            **dict(parsed_document.get("metadata") or {}),
                            **normalized_batch_metadata,
                        },
                        "page_texts": list(parsed_document.get("page_texts") or []),
                    },
                    created_by_user_id=created_by_user_id,
                )
            )
    return {"documents": created_documents, "count": len(created_documents)}


def _chunk_document_payload(
    database_url: str,
    *,
    knowledge_base: KnowledgeBaseRecord,
    text: str,
    page_texts: Any,
) -> list[KnowledgeTextChunk]:
    if isinstance(page_texts, list) and page_texts:
        page_chunks = _chunk_knowledge_base_page_texts(
            database_url,
            knowledge_base=knowledge_base,
            page_texts=[page for page in page_texts if isinstance(page, dict)],
        )
        if page_chunks:
            return page_chunks
    return _chunk_knowledge_base_text(database_url, knowledge_base=knowledge_base, text=text)


def resync_knowledge_base(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base_id: str,
    updated_by_user_id: int | None,
) -> dict[str, Any]:
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    require_knowledge_base_text_ingestion_supported(knowledge_base)
    run = context_repo.create_sync_run(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=None,
        operation_type="knowledge_resync",
        created_by_user_id=updated_by_user_id,
    )
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary="Queued knowledge-base resync.",
    )
    return {
        "knowledge_base": _serialize_knowledge_base(
            context_repo.get_knowledge_base(database_url, knowledge_base_id) or knowledge_base
        ),
        "sync_run": _serialize_sync_run(run),
    }


def perform_knowledge_base_resync_run(
    database_url: str,
    *,
    config: AuthConfig,
    run: dict[str, Any],
) -> dict[str, Any]:
    knowledge_base_id = str(run.get("knowledge_base_id") or "").strip()
    updated_by_user_id = int(run["created_by_user_id"]) if run.get("created_by_user_id") is not None else None
    knowledge_base = _require_knowledge_base(database_url, knowledge_base_id)
    require_knowledge_base_text_ingestion_supported(knowledge_base)
    documents = context_repo.list_documents(database_url, knowledge_base_id=knowledge_base_id)
    _mark_knowledge_base_syncing(
        database_url,
        knowledge_base_id=knowledge_base_id,
        updated_by_user_id=updated_by_user_id,
        summary="Rebuilding vector index from stored documents.",
    )
    try:
        source_scanned_file_count = 0
        source_changed_file_count = 0
        source_deleted_file_count = 0
        source_created_document_count = 0
        source_updated_document_count = 0
        source_deleted_document_count = 0
        context_repo.update_sync_run_progress(
            database_url,
            run_id=str(run["id"]),
            current_step="Reconciling active sources.",
            current_path=None,
        )
        for source in context_repo.list_knowledge_sources(database_url, knowledge_base_id=knowledge_base_id):
            if str(source.get("lifecycle_state") or "").strip().lower() != "active":
                continue
            from .context_management_sources import _sync_knowledge_source_documents

            _, source_directory = _resolve_source_directory(
                config,
                str(source.get("relative_path") or "").strip(),
                require_exists=True,
            )
            context_repo.mark_knowledge_source_syncing(
                database_url,
                knowledge_base_id=knowledge_base_id,
                source_id=str(source["id"]),
            )
            try:
                source_result = _sync_knowledge_source_documents(
                    database_url,
                    config,
                    knowledge_base=knowledge_base,
                    source=source,
                    source_directory=source_directory,
                    sync_run_id=str(run["id"]),
                    updated_by_user_id=updated_by_user_id,
                )
            except Exception as exc:
                context_repo.set_knowledge_source_sync_result(
                    database_url,
                    knowledge_base_id=knowledge_base_id,
                    source_id=str(source["id"]),
                    last_sync_status="error",
                    last_sync_error=str(exc) or "Knowledge source sync failed.",
                )
                raise
            source_scanned_file_count += source_result["scanned_file_count"]
            source_changed_file_count += source_result["changed_file_count"]
            source_deleted_file_count += source_result["deleted_file_count"]
            source_created_document_count += source_result["created_document_count"]
            source_updated_document_count += source_result["updated_document_count"]
            source_deleted_document_count += source_result["deleted_document_count"]
            context_repo.set_knowledge_source_sync_result(
                database_url,
                knowledge_base_id=knowledge_base_id,
                source_id=str(source["id"]),
                last_sync_status="ready",
                last_sync_error=None,
            )

        documents = context_repo.list_documents(database_url, knowledge_base_id=knowledge_base_id)
        context_repo.update_sync_run_progress(
            database_url,
            run_id=str(run["id"]),
            total_document_count=len(documents),
            processed_document_count=0,
            current_step="Rebuilding vector index.",
            current_path=None,
        )
        adapter = _resolve_knowledge_base_vector_adapter(database_url, config, knowledge_base)
        adapter.delete_index(index_name=str(knowledge_base["index_name"]))
        adapter.ensure_index(
            index_name=str(knowledge_base["index_name"]),
            schema=dict(knowledge_base.get("schema_json") or {}),
        )
        total_chunks = 0
        processed_document_count = 0
        for document in documents:
            chunks = _chunk_knowledge_base_text(
                database_url,
                knowledge_base=knowledge_base,
                text=str(document.get("text") or ""),
            )
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
            processed_document_count += 1
            context_repo.update_sync_run_progress(
                database_url,
                run_id=str(run["id"]),
                processed_document_count=processed_document_count,
                current_step="Rebuilding vector index.",
                current_path=str(document.get("source_path") or document.get("title") or "").strip() or None,
            )
        _refresh_document_count(database_url, knowledge_base_id=knowledge_base_id, updated_by_user_id=updated_by_user_id)
        refreshed = _mark_knowledge_base_sync_ready(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary=f"Resynced {len(documents)} document(s) and {total_chunks} chunk(s).",
        )
        finished_run = context_repo.finish_sync_run(
            database_url,
            run_id=str(run["id"]),
            status="ready",
            scanned_file_count=source_scanned_file_count,
            changed_file_count=source_changed_file_count,
            deleted_file_count=source_deleted_file_count,
            created_document_count=source_created_document_count,
            updated_document_count=source_updated_document_count,
            deleted_document_count=source_deleted_document_count,
            error_summary=None,
        )
        return {
            "knowledge_base": _serialize_knowledge_base(
                context_repo.get_knowledge_base(database_url, knowledge_base_id)
                or refreshed
                or _require_knowledge_base(database_url, knowledge_base_id)
            ),
            "sync_run": _serialize_sync_run(finished_run or run),
        }
    except Exception as exc:
        context_repo.finish_sync_run(
            database_url,
            run_id=str(run["id"]),
            status="error",
            scanned_file_count=0,
            changed_file_count=0,
            deleted_file_count=0,
            created_document_count=0,
            updated_document_count=0,
            deleted_document_count=0,
            error_summary=str(exc) or "Knowledge-base resync failed.",
        )
        _mark_knowledge_base_sync_error(
            database_url,
            knowledge_base_id=knowledge_base_id,
            updated_by_user_id=updated_by_user_id,
            summary="Knowledge-base resync failed.",
        )
        raise
