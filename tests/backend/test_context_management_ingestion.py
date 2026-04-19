from __future__ import annotations

from app.services import context_management_ingestion


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
        context_management_ingestion,
        "_get_pdf_reader_dependencies",
        lambda: (_FakeReader, (ValueError,)),
    )

    document = context_management_ingestion._extract_pdf_document(  # type: ignore[attr-defined]
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
        },
        "page_texts": [
            {"page_number": 1, "text": "First page text"},
            {"page_number": 3, "text": "Third page text"},
        ],
    }
