from __future__ import annotations

from app.services import context_management_shared
from app.services.context_management_types import _DEFAULT_EMBEDDINGS_SAFE_CHUNK_SIZE


def test_chunk_document_text_keeps_short_text_as_single_chunk():
    chunks = context_management_shared._chunk_document_text("short text")

    assert chunks == ["short text"]


def test_chunk_document_text_preserves_paragraph_grouping_within_safe_limit():
    text = "alpha paragraph\n\nbeta paragraph"

    chunks = context_management_shared._chunk_document_text(text)

    assert chunks == [text]


def test_chunk_document_text_splits_long_paragraph_into_safe_chunks():
    text = "a" * (_DEFAULT_EMBEDDINGS_SAFE_CHUNK_SIZE + 25)

    chunks = context_management_shared._chunk_document_text(text)

    assert len(chunks) == 2
    assert all(len(chunk) <= _DEFAULT_EMBEDDINGS_SAFE_CHUNK_SIZE for chunk in chunks)
    assert "".join(chunks) == text


def test_chunk_document_text_never_exceeds_embeddings_safe_chunk_size():
    text = "\n\n".join(
        [
            "a" * (_DEFAULT_EMBEDDINGS_SAFE_CHUNK_SIZE - 10),
            "b" * (_DEFAULT_EMBEDDINGS_SAFE_CHUNK_SIZE - 10),
            "c" * (_DEFAULT_EMBEDDINGS_SAFE_CHUNK_SIZE + 50),
        ]
    )

    chunks = context_management_shared._chunk_document_text(text)

    assert chunks
    assert all(len(chunk) <= _DEFAULT_EMBEDDINGS_SAFE_CHUNK_SIZE for chunk in chunks)
