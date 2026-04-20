from __future__ import annotations

from pathlib import Path

from app.services import context_management_source_reparse


def test_source_managed_reparse_returns_page_chunks(monkeypatch):
    monkeypatch.setattr(
        context_management_source_reparse.context_repo,
        "get_knowledge_source",
        lambda *_args, **_kwargs: {
            "id": "source-1",
            "source_type": "local_directory",
            "relative_path": "docs",
            "lifecycle_state": "active",
        },
    )
    monkeypatch.setattr(
        context_management_source_reparse,
        "_resolve_source_directory",
        lambda *_args, **_kwargs: ("docs", Path("/tmp/docs")),
    )
    monkeypatch.setattr(
        context_management_source_reparse,
        "_parse_source_documents",
        lambda *_args, **_kwargs: [{
            "text": "Page one\n\nPage two",
            "page_texts": [
                {"page_number": 1, "text": "Page one"},
                {"page_number": 2, "text": "Page two"},
            ],
        }],
    )
    monkeypatch.setattr(
        context_management_source_reparse,
        "_chunk_knowledge_base_page_texts",
        lambda *_args, **_kwargs: [
            {"text": "page-one-chunk", "metadata": {"page_number": 1}},
            {"text": "page-two-chunk", "metadata": {"page_number": 2}},
        ],
    )

    chunks = context_management_source_reparse.chunk_source_managed_document_for_resync(
        "postgresql://ignored",
        config=object(),
        knowledge_base={"id": "kb-primary"},
        document={
            "text": "stored text",
            "source_id": "source-1",
            "source_path": "manual.pdf",
            "source_document_key": "manual.pdf#0",
            "managed_by_source": True,
        },
        source_cache={},
    )

    assert chunks == [
        {"text": "page-one-chunk", "metadata": {"page_number": 1}},
        {"text": "page-two-chunk", "metadata": {"page_number": 2}},
    ]


def test_source_managed_reparse_returns_none_for_manual_document():
    assert context_management_source_reparse.chunk_source_managed_document_for_resync(
        "postgresql://ignored",
        config=object(),
        knowledge_base={"id": "kb-primary"},
        document={"text": "stored text", "managed_by_source": False},
        source_cache={},
    ) is None
