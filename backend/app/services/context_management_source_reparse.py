from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import context_management as context_repo
from .context_management_ingestion import _parse_source_documents, _source_document_key
from .context_management_shared import (
    _chunk_knowledge_base_page_texts,
    _chunk_knowledge_base_text,
    _resolve_source_directory,
)
from .context_management_types import KnowledgeBaseRecord, KnowledgeTextChunk
from .platform_types import PlatformControlPlaneError


def chunk_source_managed_document_for_resync(
    database_url: str,
    *,
    config: AuthConfig,
    knowledge_base: KnowledgeBaseRecord,
    document: dict[str, Any],
    source_cache: dict[str, dict[str, Any] | None],
) -> list[KnowledgeTextChunk] | None:
    if not bool(document.get("managed_by_source")):
        return None

    source_id = str(document.get("source_id") or "").strip()
    source_path = str(document.get("source_path") or "").strip()
    source_document_key = str(document.get("source_document_key") or "").strip()
    if not source_id or not source_path:
        return None

    if source_id not in source_cache:
        source_cache[source_id] = context_repo.get_knowledge_source(
            database_url,
            knowledge_base_id=str(knowledge_base["id"]),
            source_id=source_id,
        )
    source = source_cache.get(source_id)
    if not _is_reparseable_local_source(source):
        return None

    try:
        _, source_directory = _resolve_source_directory(
            config,
            str(source.get("relative_path") or "").strip(),
            require_exists=True,
        )
        parsed_documents = _parse_source_documents(
            source_directory / source_path,
            relative_path=source_path,
            source=source,
        )
    except PlatformControlPlaneError:
        raise
    except Exception:
        return None

    parsed_document = _matching_parsed_document(
        parsed_documents,
        source_path=source_path,
        source_document_key=source_document_key,
    )
    if parsed_document is None:
        return None
    return _chunk_parsed_document_for_resync(
        database_url,
        knowledge_base=knowledge_base,
        document=document,
        parsed_document=parsed_document,
    )


def _is_reparseable_local_source(source: dict[str, Any] | None) -> bool:
    return (
        source is not None
        and str(source.get("source_type") or "").strip().lower() == "local_directory"
        and str(source.get("lifecycle_state") or "").strip().lower() in {"", "active"}
    )


def _matching_parsed_document(
    parsed_documents: list[dict[str, Any]],
    *,
    source_path: str,
    source_document_key: str,
) -> dict[str, Any] | None:
    for position, parsed_document in enumerate(parsed_documents):
        if _source_document_key(source_path, position) == source_document_key:
            return parsed_document
    if len(parsed_documents) == 1 and not source_document_key:
        return parsed_documents[0]
    return None


def _chunk_parsed_document_for_resync(
    database_url: str,
    *,
    knowledge_base: KnowledgeBaseRecord,
    document: dict[str, Any],
    parsed_document: dict[str, Any],
) -> list[KnowledgeTextChunk]:
    page_texts = parsed_document.get("page_texts")
    if isinstance(page_texts, list) and page_texts:
        page_chunks = _chunk_knowledge_base_page_texts(
            database_url,
            knowledge_base=knowledge_base,
            page_texts=[page for page in page_texts if isinstance(page, dict)],
        )
        if page_chunks:
            return page_chunks
    return _chunk_knowledge_base_text(
        database_url,
        knowledge_base=knowledge_base,
        text=str(parsed_document.get("text") or document.get("text") or ""),
    )
