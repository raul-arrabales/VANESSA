from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from ..config import AuthConfig
from ..repositories import context_management as context_repo
from ..repositories import platform_control_plane as platform_repo
from .context_management_chunking import (
    build_chunking_state,
    chunk_text,
    resolve_knowledge_base_tokenizer,
)
from .context_management_chunking_compatibility import assert_knowledge_base_chunking_compatible
from .context_management_types import (
    KnowledgeBaseRecord,
    KnowledgeDocumentRecord,
    KnowledgeSourceRecord,
)
from .context_management_vectorization import (
    embed_knowledge_base_texts,
    require_knowledge_base_text_ingestion_supported,
)
from .platform_types import CAPABILITY_VECTOR_STORE, PlatformControlPlaneError


@dataclass(frozen=True)
class SourceSyncFailure:
    error: PlatformControlPlaneError
    message: str


def _chunk_document_text(text: str) -> list[str]:
    raise RuntimeError("_chunk_document_text requires a knowledge-base-aware chunking context")


def _chunk_knowledge_base_text(
    database_url: str,
    *,
    knowledge_base: KnowledgeBaseRecord,
    text: str,
) -> list[str]:
    return chunk_text(
        text,
        chunking=build_chunking_state(knowledge_base),
        tokenizer=resolve_knowledge_base_tokenizer(database_url, knowledge_base=knowledge_base),
    )


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


def _configured_source_roots(config: AuthConfig) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for raw_root in config.context_source_roots:
        normalized = str(raw_root).strip()
        if not normalized:
            continue
        path = Path(normalized).expanduser().resolve()
        key = str(path)
        if key in seen_paths:
            continue
        seen_paths.add(key)
        roots.append(
            {
                "id": f"root-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}",
                "display_name": key,
                "path": path,
            }
        )
    if not roots:
        raise PlatformControlPlaneError(
            "context_source_roots_not_configured",
            "No context source roots are configured.",
            status_code=500,
        )
    return roots


def _resolve_source_directory(
    config: AuthConfig,
    relative_path: str,
    *,
    require_exists: bool,
) -> tuple[str, Path]:
    normalized_relative_path = _normalize_source_relative_path(relative_path)
    if not normalized_relative_path:
        raise PlatformControlPlaneError("invalid_source_relative_path", "relative_path is required", status_code=400)
    configured_roots = [root["path"] for root in _configured_source_roots(config)]
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


def _chunk_document_id(document_id: str, index: int) -> str:
    return f"{document_id}::chunk::{index}"


def normalize_knowledge_source_sync_failure(
    exc: Exception,
    *,
    source_id: str,
    source_display_name: str,
    knowledge_base_id: str,
    sync_run_id: str,
    fallback_message: str = "Knowledge source sync failed.",
) -> SourceSyncFailure:
    normalized_message = str(exc).strip() or fallback_message.strip() or "Knowledge source sync failed."
    normalized_details = {
        "source_id": source_id,
        "source_display_name": source_display_name,
        "knowledge_base_id": knowledge_base_id,
        "sync_run_id": sync_run_id,
    }
    if isinstance(exc, PlatformControlPlaneError):
        merged_details = {
            **(exc.details if isinstance(exc.details, dict) else {}),
            **normalized_details,
        }
        return SourceSyncFailure(
            error=PlatformControlPlaneError(
                exc.code,
                normalized_message,
                status_code=exc.status_code,
                details=merged_details,
            ),
            message=normalized_message,
        )
    return SourceSyncFailure(
        error=PlatformControlPlaneError(
            "knowledge_source_sync_failed",
            normalized_message,
            status_code=500,
            details={
                **normalized_details,
                "original_exception_type": exc.__class__.__name__,
                "original_exception_message": str(exc).strip() or None,
            },
        ),
        message=normalized_message,
    )


def _upsert_document_chunks(
    database_url: str,
    config: AuthConfig,
    *,
    knowledge_base: KnowledgeBaseRecord,
    document: KnowledgeDocumentRecord,
    chunks: list[str],
) -> None:
    if not chunks:
        raise PlatformControlPlaneError("invalid_document_text", "text is required", status_code=400)
    require_knowledge_base_text_ingestion_supported(knowledge_base)
    source_display_name = str(document.get("source_name") or "").strip() or None
    source_id = str(document.get("source_id") or "").strip() or None
    document_title = str(document.get("title") or "").strip() or None
    error_prefix = "Unable to generate embeddings"
    if source_display_name and str(document.get("source_type") or "").strip().lower() == "local_directory":
        error_prefix = f"Unable to sync source '{source_display_name}'"
    elif document_title:
        error_prefix = f"Unable to index document '{document_title}'"
    assert_knowledge_base_chunking_compatible(
        database_url,
        knowledge_base=knowledge_base,
        error_prefix=error_prefix,
        status_code=409,
        details={
            "source_id": source_id,
            "source_display_name": source_display_name,
        },
    )
    adapter = _resolve_knowledge_base_vector_adapter(database_url, config, knowledge_base)
    adapter.ensure_index(index_name=str(knowledge_base["index_name"]), schema=dict(knowledge_base.get("schema_json") or {}))
    embeddings_payload = embed_knowledge_base_texts(
        database_url,
        config=config,
        knowledge_base=knowledge_base,
        texts=chunks,
    )
    embeddings = embeddings_payload.get("embeddings") if isinstance(embeddings_payload.get("embeddings"), list) else []
    documents = [
        {
            "id": _chunk_document_id(str(document["id"]), index),
            "text": chunk,
            "embedding": embeddings[index] if index < len(embeddings) else None,
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
    knowledge_base: KnowledgeBaseRecord,
    document: KnowledgeDocumentRecord,
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


def _ensure_knowledge_base_index(database_url: str, config: AuthConfig, knowledge_base: KnowledgeBaseRecord) -> None:
    adapter = _resolve_knowledge_base_vector_adapter(database_url, config, knowledge_base)
    adapter.ensure_index(
        index_name=str(knowledge_base["index_name"]),
        schema=dict(knowledge_base.get("schema_json") or {}),
    )


def _resolve_knowledge_base_vector_adapter(database_url: str, config: AuthConfig, knowledge_base: KnowledgeBaseRecord):
    from . import platform_service

    platform_service.ensure_platform_bootstrap_state(database_url, config)
    provider_instance_id = str(knowledge_base.get("backing_provider_instance_id") or "").strip()
    if not provider_instance_id:
        raise PlatformControlPlaneError(
            "vector_provider_not_found",
            "Backing vector provider is not configured",
            status_code=409,
            details={"knowledge_base_id": knowledge_base.get("id")},
        )
    provider_row = platform_repo.get_provider_instance(database_url, provider_instance_id)
    if provider_row is None:
        raise PlatformControlPlaneError(
            "vector_provider_not_found",
            "Backing vector provider is not configured",
            status_code=409,
            details={"provider_instance_id": provider_instance_id},
        )
    if str(provider_row.get("capability_key") or "").strip().lower() != CAPABILITY_VECTOR_STORE:
        raise PlatformControlPlaneError(
            "vector_provider_invalid",
            "Backing provider is not a vector store provider",
            status_code=409,
            details={"provider_instance_id": provider_instance_id},
        )
    if not bool(provider_row.get("enabled", True)):
        raise PlatformControlPlaneError(
            "vector_provider_disabled",
            "Backing vector provider is disabled",
            status_code=409,
            details={"provider_instance_id": provider_instance_id},
        )
    return platform_service.resolve_vector_store_adapter(
        database_url,
        config,
        provider_instance_id=provider_instance_id,
    )


def _require_knowledge_base(database_url: str, knowledge_base_id: str) -> KnowledgeBaseRecord:
    row = context_repo.get_knowledge_base(database_url, knowledge_base_id)
    if row is None:
        raise PlatformControlPlaneError("knowledge_base_not_found", "Knowledge base not found", status_code=404)
    return row


def _require_knowledge_source(database_url: str, *, knowledge_base_id: str, source_id: str) -> KnowledgeSourceRecord:
    row = context_repo.get_knowledge_source(database_url, knowledge_base_id=knowledge_base_id, source_id=source_id)
    if row is None:
        raise PlatformControlPlaneError("knowledge_source_not_found", "Knowledge source not found", status_code=404)
    return row


def _mark_knowledge_base_syncing(
    database_url: str,
    *,
    knowledge_base_id: str,
    updated_by_user_id: int | None,
    summary: str,
) -> KnowledgeBaseRecord | None:
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
) -> KnowledgeBaseRecord | None:
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
) -> KnowledgeBaseRecord | None:
    return context_repo.set_knowledge_base_sync_result(
        database_url,
        knowledge_base_id=knowledge_base_id,
        sync_status="error",
        last_sync_error=summary,
        last_sync_summary=summary,
        updated_by_user_id=updated_by_user_id,
    )


def _is_knowledge_base_eligible(row: dict[str, Any]) -> bool:
    return (
        str(row.get("lifecycle_state") or "").strip().lower() == "active"
        and str(row.get("sync_status") or "").strip().lower() == "ready"
    )
