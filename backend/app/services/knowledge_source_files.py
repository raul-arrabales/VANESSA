from __future__ import annotations

from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path
from typing import Any

from ..repositories import context_management as context_repo
from .context_management import resolve_runtime_knowledge_base_selection
from .context_management_shared import _resolve_source_directory
from .platform_service import get_active_platform_runtime
from .platform_types import PlatformControlPlaneError


INLINE_SOURCE_FILE_EXTENSIONS = {".json", ".jsonl", ".md", ".pdf", ".txt"}


@dataclass(frozen=True)
class KnowledgeSourceFile:
    path: Path
    mimetype: str | None
    as_attachment: bool
    download_name: str


def _normalize_document_source_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip().strip("/")
    if not normalized:
        raise PlatformControlPlaneError(
            "source_file_not_available",
            "This document does not have a backing local source file.",
            status_code=409,
        )
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        raise PlatformControlPlaneError(
            "invalid_source_file_path",
            "Document source path must stay within its knowledge source directory.",
            status_code=404,
        )
    return "/".join(parts)


def _resolve_document_file_path(source_directory: Path, source_path: str) -> Path:
    normalized_source_path = _normalize_document_source_path(source_path)
    candidate = (source_directory / normalized_source_path).resolve()
    try:
        candidate.relative_to(source_directory)
    except ValueError as exc:
        raise PlatformControlPlaneError(
            "invalid_source_file_path",
            "Document source path must stay within its knowledge source directory.",
            status_code=404,
        ) from exc
    if not candidate.exists() or not candidate.is_file():
        raise PlatformControlPlaneError(
            "source_file_not_found",
            "The referenced source file was not found.",
            status_code=404,
        )
    return candidate


def resolve_knowledge_source_file(
    database_url: str,
    *,
    config: Any,
    knowledge_base_id: str,
    document_id: str,
) -> KnowledgeSourceFile:
    platform_runtime = get_active_platform_runtime(database_url, config)
    resolve_runtime_knowledge_base_selection(
        platform_runtime,
        database_url=database_url,
        knowledge_base_id=knowledge_base_id,
    )

    document = context_repo.get_document(
        database_url,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
    )
    if document is None:
        raise PlatformControlPlaneError(
            "knowledge_document_not_found",
            "Knowledge document not found.",
            status_code=404,
        )
    if not bool(document.get("managed_by_source")):
        raise PlatformControlPlaneError(
            "source_file_not_available",
            "Only source-managed local-directory documents have source files.",
            status_code=409,
        )
    source_id = str(document.get("source_id") or "").strip()
    source_path = str(document.get("source_path") or "").strip()
    if not source_id or not source_path:
        raise PlatformControlPlaneError(
            "source_file_not_available",
            "This document does not have a backing local source file.",
            status_code=409,
        )

    source = context_repo.get_knowledge_source(
        database_url,
        knowledge_base_id=knowledge_base_id,
        source_id=source_id,
    )
    if source is None or str(source.get("source_type") or "").strip().lower() != "local_directory":
        raise PlatformControlPlaneError(
            "knowledge_source_not_found",
            "Knowledge source not found.",
            status_code=404,
        )

    try:
        _, source_directory = _resolve_source_directory(
            config,
            str(source.get("relative_path") or "").strip(),
            require_exists=True,
        )
    except PlatformControlPlaneError as exc:
        if exc.code == "knowledge_source_path_not_found":
            raise PlatformControlPlaneError(
                "source_file_not_found",
                "The referenced source file was not found.",
                status_code=404,
                details=exc.details,
            ) from exc
        raise
    file_path = _resolve_document_file_path(source_directory, source_path)
    mimetype = guess_type(file_path.name)[0]
    return KnowledgeSourceFile(
        path=file_path,
        mimetype=mimetype,
        as_attachment=file_path.suffix.lower() not in INLINE_SOURCE_FILE_EXTENSIONS,
        download_name=file_path.name,
    )
