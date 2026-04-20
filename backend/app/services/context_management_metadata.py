from __future__ import annotations

from typing import Any, Mapping

PDF_PAGE_CHUNKING_VERSION_KEY = "_page_chunking_version"
PDF_PAGE_CHUNKING_VERSION = 1
INTERNAL_METADATA_PREFIX = "_"


def is_internal_metadata_key(key: object) -> bool:
    return str(key or "").strip().startswith(INTERNAL_METADATA_PREFIX)


def public_chunk_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in dict(metadata or {}).items()
        if not is_internal_metadata_key(key)
    }


def with_pdf_page_chunking_marker(metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        **dict(metadata or {}),
        PDF_PAGE_CHUNKING_VERSION_KEY: PDF_PAGE_CHUNKING_VERSION,
    }


def has_pdf_page_chunking_marker(metadata: Mapping[str, Any] | None) -> bool:
    return dict(metadata or {}).get(PDF_PAGE_CHUNKING_VERSION_KEY) == PDF_PAGE_CHUNKING_VERSION
