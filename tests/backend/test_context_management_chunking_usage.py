from __future__ import annotations

from pathlib import Path

from app.services import context_management_documents, context_management_sources


def _knowledge_base() -> dict[str, object]:
    return {
        "id": "kb-primary",
        "index_name": "kb_product_docs",
        "schema_json": {
            "properties": [
                {"name": "category", "data_type": "text"},
                {"name": "published", "data_type": "boolean"},
                {"name": "source_path", "data_type": "text"},
                {"name": "source_display_name", "data_type": "text"},
            ]
        },
        "chunking_strategy": "fixed_length",
        "chunking_config_json": {
            "unit": "tokens",
            "chunk_length": 300,
            "chunk_overlap": 60,
        },
        "vectorization_json": {
            "embedding_resource": {
                "id": "text-embedding-3-small",
                "provider_resource_id": "text-embedding-3-small",
                "metadata": {},
            }
        },
        "embedding_provider_instance_id": "embedding-provider-1",
        "embedding_resource_id": "text-embedding-3-small",
    }


def test_create_knowledge_base_document_uses_chunking_context(monkeypatch):
    created: dict[str, object] = {}
    upserted: dict[str, object] = {}
    knowledge_base = _knowledge_base()

    monkeypatch.setattr(context_management_documents, "_require_knowledge_base", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(context_management_documents, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_documents, "_mark_knowledge_base_syncing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_documents, "_mark_knowledge_base_sync_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_documents, "_refresh_document_count", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management_documents,
        "_chunk_knowledge_base_text",
        lambda *_args, **kwargs: ["chunk-1", "chunk-2"] if kwargs["text"] == "Hello world" else [],
    )

    def _create_document(_database_url: str, **kwargs):
        created.update(kwargs)
        return {
            "id": kwargs["document_id"],
            "knowledge_base_id": kwargs["knowledge_base_id"],
            "title": kwargs["title"],
            "text": kwargs["text"],
            "chunk_count": kwargs["chunk_count"],
            "metadata_json": kwargs["metadata_json"],
        }

    monkeypatch.setattr(context_management_documents.context_repo, "create_document", _create_document)

    def _upsert_document_chunks(_database_url: str, _config, *, knowledge_base, document, chunks):
        upserted["knowledge_base"] = knowledge_base
        upserted["document"] = document
        upserted["chunks"] = chunks

    monkeypatch.setattr(context_management_documents, "_upsert_document_chunks", _upsert_document_chunks)

    document = context_management_documents.create_knowledge_base_document(
        "postgresql://ignored",
        config=object(),
        knowledge_base_id="kb-primary",
        payload={
            "title": "Doc",
            "text": "Hello world",
            "source_type": "manual",
            "metadata": {
                "category": "guide",
                "published": True,
            },
        },
        created_by_user_id=7,
    )

    assert created["chunk_count"] == 2
    assert created["metadata_json"] == {
        "category": "guide",
        "published": True,
    }
    assert upserted["knowledge_base"] == knowledge_base
    assert upserted["document"]["metadata_json"] == {  # type: ignore[index]
        "category": "guide",
        "published": True,
    }
    assert upserted["chunks"] == ["chunk-1", "chunk-2"]
    assert document["chunk_count"] == 2


def test_update_knowledge_base_document_uses_chunking_context(monkeypatch):
    updated_call: dict[str, object] = {}
    upserted: dict[str, object] = {}
    knowledge_base = _knowledge_base()
    existing = {
        "id": "doc-1",
        "knowledge_base_id": "kb-primary",
        "title": "Doc",
        "text": "Old text",
        "source_type": "manual",
        "source_name": None,
        "uri": None,
        "metadata_json": {"category": "guide"},
        "managed_by_source": False,
        "chunk_count": 1,
    }

    monkeypatch.setattr(context_management_documents, "_require_knowledge_base", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(context_management_documents, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_documents.context_repo, "get_document", lambda *_args, **_kwargs: existing)
    monkeypatch.setattr(context_management_documents, "_mark_knowledge_base_syncing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_documents, "_mark_knowledge_base_sync_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_documents, "_refresh_document_count", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_documents, "_delete_document_chunks", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management_documents,
        "_chunk_knowledge_base_text",
        lambda *_args, **kwargs: ["chunk-1", "chunk-2", "chunk-3"] if kwargs["text"] == "Updated text" else [],
    )

    def _update_document(_database_url: str, **kwargs):
        updated_call.update(kwargs)
        return {
            **existing,
            "title": kwargs["title"],
            "text": kwargs["text"],
            "chunk_count": kwargs["chunk_count"],
            "metadata_json": kwargs["metadata_json"],
        }

    monkeypatch.setattr(context_management_documents.context_repo, "update_document", _update_document)

    def _upsert_document_chunks(_database_url: str, _config, *, knowledge_base, document, chunks):
        upserted["knowledge_base"] = knowledge_base
        upserted["document"] = document
        upserted["chunks"] = chunks

    monkeypatch.setattr(context_management_documents, "_upsert_document_chunks", _upsert_document_chunks)

    document = context_management_documents.update_knowledge_base_document(
        "postgresql://ignored",
        config=object(),
        knowledge_base_id="kb-primary",
        document_id="doc-1",
        payload={
            "title": "Doc",
            "text": "Updated text",
            "source_type": "manual",
            "metadata": {
                "category": "reference",
                "published": True,
            },
        },
        updated_by_user_id=8,
    )

    assert updated_call["chunk_count"] == 3
    assert updated_call["metadata_json"] == {
        "category": "reference",
        "published": True,
    }
    assert upserted["knowledge_base"] == knowledge_base
    assert upserted["document"]["metadata_json"] == {  # type: ignore[index]
        "category": "reference",
        "published": True,
    }
    assert upserted["chunks"] == ["chunk-1", "chunk-2", "chunk-3"]
    assert document["chunk_count"] == 3


def test_resync_knowledge_base_uses_chunking_context(monkeypatch):
    knowledge_base = _knowledge_base()
    chunk_texts: list[str] = []
    updated_counts: list[int] = []
    upserted_chunk_lists: list[list[str]] = []
    upserted_documents: list[dict[str, object]] = []

    monkeypatch.setattr(context_management_documents, "_require_knowledge_base", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(context_management_documents, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management_documents.context_repo,
        "list_documents",
        lambda *_args, **_kwargs: [
            {"id": "doc-1", "text": "Alpha text", "chunk_count": 1, "metadata_json": {"category": "guide"}},
            {"id": "doc-2", "text": "Beta text", "chunk_count": 0, "metadata_json": {"category": "faq"}},
        ],
    )
    monkeypatch.setattr(context_management_documents, "_mark_knowledge_base_syncing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management_documents,
        "_mark_knowledge_base_sync_ready",
        lambda *_args, **kwargs: {"id": "kb-primary", "last_sync_summary": kwargs["summary"]},
    )
    monkeypatch.setattr(context_management_documents, "_refresh_document_count", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management_documents,
        "_resolve_knowledge_base_vector_adapter",
        lambda *_args, **_kwargs: type(
            "_Adapter",
            (),
            {
                "delete_index": lambda self, **_kwargs: None,
                "ensure_index": lambda self, **_kwargs: None,
            },
        )(),
    )

    def _chunk_knowledge_base_text(_database_url: str, *, knowledge_base, text: str):
        chunk_texts.append(text)
        if text == "Alpha text":
            return ["alpha-1", "alpha-2"]
        return ["beta-1"]

    monkeypatch.setattr(context_management_documents, "_chunk_knowledge_base_text", _chunk_knowledge_base_text)

    def _set_document_chunk_count(_database_url: str, *, chunk_count: int, **kwargs):
        updated_counts.append(chunk_count)
        return {
            "id": kwargs["document_id"],
            "text": "Alpha text" if kwargs["document_id"] == "doc-1" else "Beta text",
            "chunk_count": chunk_count,
            "metadata_json": {"category": "guide"} if kwargs["document_id"] == "doc-1" else {"category": "faq"},
        }

    monkeypatch.setattr(context_management_documents.context_repo, "set_document_chunk_count", _set_document_chunk_count)
    monkeypatch.setattr(
        context_management_documents,
        "_upsert_document_chunks",
        lambda _database_url, _config, *, knowledge_base, document, chunks: (
            upserted_chunk_lists.append(chunks),
            upserted_documents.append(document),
        ),
    )
    monkeypatch.setattr(context_management_documents.context_repo, "get_knowledge_base", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(context_management_documents, "_serialize_knowledge_base", lambda row: row)

    refreshed = context_management_documents.resync_knowledge_base(
        "postgresql://ignored",
        config=object(),
        knowledge_base_id="kb-primary",
        updated_by_user_id=9,
    )

    assert chunk_texts == ["Alpha text", "Beta text"]
    assert updated_counts == [2, 1]
    assert upserted_chunk_lists == [["alpha-1", "alpha-2"], ["beta-1"]]
    assert [document["metadata_json"] for document in upserted_documents] == [  # type: ignore[index]
        {"category": "guide"},
        {"category": "faq"},
    ]
    assert refreshed["id"] == "kb-primary"


def test_source_sync_uses_chunking_context(monkeypatch):
    created_documents: list[dict[str, object]] = []
    upserted_chunk_lists: list[list[str]] = []
    upserted_documents: list[dict[str, object]] = []

    monkeypatch.setattr(
        context_management_sources,
        "_iter_source_files",
        lambda *_args, **_kwargs: [(Path("/tmp/source.txt"), "docs/source.txt")],
    )
    monkeypatch.setattr(
        context_management_sources,
        "_parse_source_documents",
        lambda *_args, **_kwargs: [
            {
                "title": "Source Doc",
                "source_type": "local_directory",
                "source_name": "Docs folder",
                "uri": None,
                "text": "Chunk this source document",
                "metadata": {
                    "category": "guide",
                    "source_path": "docs/source.txt",
                    "source_display_name": "Docs folder",
                },
            }
        ],
    )
    monkeypatch.setattr(
        context_management_sources.context_repo,
        "get_document_by_source_key",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        context_management_sources,
        "_chunk_knowledge_base_text",
        lambda *_args, **kwargs: ["source-1", "source-2"] if kwargs["text"] == "Chunk this source document" else [],
    )
    monkeypatch.setattr(
        context_management_sources.context_repo,
        "create_document",
        lambda _database_url, **kwargs: created_documents.append(kwargs) or {
            "id": kwargs["document_id"],
            "chunk_count": kwargs["chunk_count"],
            "metadata_json": kwargs["metadata_json"],
        },
    )
    monkeypatch.setattr(
        context_management_sources,
        "_upsert_document_chunks",
        lambda _database_url, _config, *, knowledge_base, document, chunks: (
            upserted_chunk_lists.append(chunks),
            upserted_documents.append(document),
        ),
    )
    monkeypatch.setattr(context_management_sources.context_repo, "list_source_documents", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(context_management_sources, "_refresh_document_count", lambda *_args, **_kwargs: None)

    summary = context_management_sources._sync_knowledge_source_documents(
        "postgresql://ignored",
        object(),
        knowledge_base=_knowledge_base(),
        source={
            "id": "source-1",
            "display_name": "Docs folder",
            "include_globs": ["**/*.txt"],
            "exclude_globs": [],
        },
        source_directory=Path("/tmp"),
        updated_by_user_id=10,
    )

    assert created_documents[0]["chunk_count"] == 2
    assert created_documents[0]["metadata_json"] == {
        "category": "guide",
        "source_path": "docs/source.txt",
        "source_display_name": "Docs folder",
    }
    assert upserted_chunk_lists == [["source-1", "source-2"]]
    assert upserted_documents[0]["metadata_json"] == {  # type: ignore[index]
        "category": "guide",
        "source_path": "docs/source.txt",
        "source_display_name": "Docs folder",
    }
    assert summary["created_document_count"] == 1
