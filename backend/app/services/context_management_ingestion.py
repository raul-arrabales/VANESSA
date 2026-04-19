from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .context_management_types import (
    ParsedIngestionDocument,
    _MAX_FILE_SIZE_BYTES,
    _SUPPORTED_UPLOAD_EXTENSIONS,
)
from .context_management_parsers import parse_ingestion_documents
from .platform_types import PlatformControlPlaneError


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


def _parse_source_documents(file_path: Path, *, relative_path: str, source: dict[str, Any]) -> list[ParsedIngestionDocument]:
    raw_bytes = _read_ingestion_bytes(
        file_path.read_bytes,
        filename=relative_path,
        too_large_code="source_file_too_large",
        too_large_message=f"Source files must be smaller than {_MAX_FILE_SIZE_BYTES} bytes",
        read_error_code="invalid_source_file",
        read_error_message="Source file could not be read",
        details_key="relative_path",
    )
    documents = parse_ingestion_documents(
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
                **dict(source.get("metadata_json") or source.get("metadata") or {}),
                "source_path": relative_path,
                "source_display_name": str(source.get("display_name") or "").strip() or None,
            },
        }
        for document in documents
    ]


def _source_document_changed(
    existing: dict[str, Any],
    *,
    parsed_document: ParsedIngestionDocument,
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


def _parse_upload_documents(file_storage: Any) -> list[ParsedIngestionDocument]:
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
    return parse_ingestion_documents(
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
