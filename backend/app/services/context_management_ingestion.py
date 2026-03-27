from __future__ import annotations

import fnmatch
import io
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .context_management_types import (
    ParsedIngestionDocument,
    _MAX_FILE_SIZE_BYTES,
    _SUPPORTED_UPLOAD_EXTENSIONS,
)
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
) -> list[ParsedIngestionDocument]:
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
        documents: list[ParsedIngestionDocument] = []
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
) -> ParsedIngestionDocument:
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


def _documents_from_json_payload(payload: Any, *, filename: str) -> list[ParsedIngestionDocument]:
    if isinstance(payload, list):
        return [_document_from_json_item(item, filename=filename, position=index) for index, item in enumerate(payload)]
    return [_document_from_json_item(payload, filename=filename, position=0)]


def _document_from_json_item(item: Any, *, filename: str, position: int) -> ParsedIngestionDocument:
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
