from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from .context_management_types import ParsedIngestionDocument, ParsedIngestionPage, _SUPPORTED_UPLOAD_EXTENSIONS
from .platform_types import PlatformControlPlaneError


def parse_ingestion_documents(
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
        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise PlatformControlPlaneError(
                invalid_json_code,
                f"{filename} contains invalid JSON",
                status_code=400,
                details={details_key: filename},
            ) from exc
        return documents_from_json_payload(
            parsed,
            filename=filename,
            invalid_json_code=invalid_json_code,
            details_key=details_key,
        )
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
            documents.extend(
                documents_from_json_payload(
                    parsed_line,
                    filename=filename,
                    invalid_json_code=invalid_json_code,
                    details_key=details_key,
                )
            )
        return documents
    if suffix == ".pdf":
        return [extract_pdf_document(
            filename,
            raw_bytes,
            default_source_type=default_source_type,
            default_source_name=default_source_name,
            invalid_pdf_code=invalid_pdf_code,
            details_key=details_key,
        )]
    raise PlatformControlPlaneError("unsupported_upload_type", "Unsupported upload type", status_code=400)


def documents_from_json_payload(
    payload: Any,
    *,
    filename: str,
    invalid_json_code: str,
    details_key: str,
) -> list[ParsedIngestionDocument]:
    if isinstance(payload, list):
        return [
            document_from_json_item(
                item,
                filename=filename,
                position=index,
                invalid_json_code=invalid_json_code,
                details_key=details_key,
            )
            for index, item in enumerate(payload)
        ]
    return [
        document_from_json_item(
            payload,
            filename=filename,
            position=0,
            invalid_json_code=invalid_json_code,
            details_key=details_key,
        )
    ]


def document_from_json_item(
    item: Any,
    *,
    filename: str,
    position: int,
    invalid_json_code: str,
    details_key: str,
) -> ParsedIngestionDocument:
    if not isinstance(item, dict):
        raise PlatformControlPlaneError(
            invalid_json_code,
            "JSON documents must be objects",
            status_code=400,
            details={details_key: filename, "position": position},
        )
    title = str(item.get("title") or item.get("name") or f"{Path(filename).stem}-{position + 1}").strip()
    text = str(item.get("text") or item.get("content") or "").strip()
    if not text:
        raise PlatformControlPlaneError(
            invalid_json_code,
            "JSON documents must include text or content",
            status_code=400,
            details={details_key: filename, "position": position},
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


def extract_pdf_document(
    filename: str,
    raw_bytes: bytes,
    *,
    default_source_type: str,
    default_source_name: str | None,
    invalid_pdf_code: str,
    details_key: str,
) -> ParsedIngestionDocument:
    PdfReader, pdf_error_types = get_pdf_reader_dependencies()
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
    extracted_pages: list[ParsedIngestionPage] = []
    for page_number, page in enumerate(pages, start=1):
        page_text = str(page.extract_text() or "").strip()
        if page_text:
            extracted_pages.append({"page_number": page_number, "text": page_text})
    text = "\n\n".join(page["text"] for page in extracted_pages).strip()
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
            "_page_chunking_version": 1,
        },
        "page_texts": extracted_pages,
    }


def get_pdf_reader_dependencies():
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
