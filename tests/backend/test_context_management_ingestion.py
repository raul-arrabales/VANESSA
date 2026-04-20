from __future__ import annotations

from app.services import context_management_parsers
from app.services.context_management_ingestion import _source_document_changed
from app.services import context_management_ingestion
from app.services.context_management_types import MAX_INGESTION_FILE_SIZE_BYTES
from app.services.platform_types import PlatformControlPlaneError


def test_extract_pdf_document_keeps_page_texts_with_page_numbers(monkeypatch):
    class _FakePage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _FakeReader:
        is_encrypted = False
        pages = [_FakePage("First page text"), _FakePage(""), _FakePage("Third page text")]

        def __init__(self, _stream):
            pass

    monkeypatch.setattr(
        context_management_parsers,
        "get_pdf_reader_dependencies",
        lambda: (_FakeReader, (ValueError,)),
    )

    document = context_management_parsers.extract_pdf_document(
        "architecture.pdf",
        b"%PDF",
        default_source_type="upload",
        default_source_name="architecture.pdf",
        invalid_pdf_code="invalid_upload_pdf",
        details_key="filename",
    )

    assert document == {
        "title": "architecture",
        "source_type": "upload",
        "source_name": "architecture.pdf",
        "uri": None,
        "text": "First page text\n\nThird page text",
        "metadata": {
            "page_count": 3,
            "source_filename": "architecture.pdf",
            "_page_chunking_version": 1,
        },
        "page_texts": [
            {"page_number": 1, "text": "First page text"},
            {"page_number": 3, "text": "Third page text"},
        ],
    }


def test_source_document_changed_when_existing_pdf_lacks_page_chunking_marker():
    existing = {
        "title": "architecture",
        "source_type": "local_directory",
        "source_name": "Docs",
        "uri": None,
        "text": "First page text\n\nThird page text",
        "metadata_json": {
            "page_count": 3,
            "source_filename": "architecture.pdf",
            "source_path": "architecture.pdf",
        },
        "chunk_count": 2,
        "source_path": "architecture.pdf",
        "source_document_key": "architecture.pdf#0",
        "managed_by_source": True,
    }
    parsed_document = {
        "title": "architecture",
        "source_type": "local_directory",
        "source_name": "Docs",
        "uri": None,
        "text": "First page text\n\nThird page text",
        "metadata": {
            "page_count": 3,
            "source_filename": "architecture.pdf",
            "source_path": "architecture.pdf",
            "_page_chunking_version": 1,
        },
    }

    assert _source_document_changed(
        existing,
        parsed_document=parsed_document,
        chunk_count=2,
        source_path="architecture.pdf",
        source_document_key="architecture.pdf#0",
    )


def test_ingestion_accepts_twenty_megabyte_payload():
    raw = context_management_ingestion._read_ingestion_bytes(
        lambda: b"x" * MAX_INGESTION_FILE_SIZE_BYTES,
        filename="large.md",
        too_large_code="too_large",
        too_large_message="too large",
        read_error_code="invalid",
        read_error_message="invalid",
        details_key="filename",
    )

    assert len(raw) == MAX_INGESTION_FILE_SIZE_BYTES


def test_ingestion_rejects_payload_above_twenty_megabytes():
    try:
        context_management_ingestion._read_ingestion_bytes(
            lambda: b"x" * (MAX_INGESTION_FILE_SIZE_BYTES + 1),
            filename="too-large.md",
            too_large_code="too_large",
            too_large_message="Uploaded files must be 20 MB or smaller",
            read_error_code="invalid",
            read_error_message="invalid",
            details_key="filename",
        )
    except PlatformControlPlaneError as exc:
        assert exc.code == "too_large"
        assert str(exc) == "Uploaded files must be 20 MB or smaller"
        assert exc.details["max_file_size_bytes"] == MAX_INGESTION_FILE_SIZE_BYTES
    else:
        raise AssertionError("Expected PlatformControlPlaneError")
