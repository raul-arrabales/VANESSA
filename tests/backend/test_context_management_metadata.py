from __future__ import annotations

from app.services.context_management_metadata import (
    PDF_PAGE_CHUNKING_VERSION,
    PDF_PAGE_CHUNKING_VERSION_KEY,
    has_pdf_page_chunking_marker,
    public_chunk_metadata,
    with_pdf_page_chunking_marker,
)


def test_public_chunk_metadata_preserves_page_number_and_strips_internal_keys():
    assert public_chunk_metadata({
        "page_number": 4,
        PDF_PAGE_CHUNKING_VERSION_KEY: PDF_PAGE_CHUNKING_VERSION,
        "_private_note": "hidden",
        "source_path": "docs/manual.pdf",
    }) == {
        "page_number": 4,
        "source_path": "docs/manual.pdf",
    }


def test_pdf_page_chunking_marker_helpers_share_version_constant():
    metadata = with_pdf_page_chunking_marker({"page_count": 12})

    assert metadata == {
        "page_count": 12,
        PDF_PAGE_CHUNKING_VERSION_KEY: PDF_PAGE_CHUNKING_VERSION,
    }
    assert has_pdf_page_chunking_marker(metadata)
