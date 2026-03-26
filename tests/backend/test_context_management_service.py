from __future__ import annotations

import io

import pytest
from werkzeug.datastructures import FileStorage

from app.services import context_management  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError  # noqa: E402


def test_parse_upload_documents_supports_text_and_jsonl():
    text_file = FileStorage(stream=io.BytesIO(b"Hello knowledge base"), filename="notes.txt")
    jsonl_file = FileStorage(
        stream=io.BytesIO(b'{"title":"Doc A","text":"Alpha"}\n{"title":"Doc B","content":"Beta"}\n'),
        filename="docs.jsonl",
    )

    parsed_text = context_management._parse_upload_documents(text_file)  # type: ignore[attr-defined]
    parsed_jsonl = context_management._parse_upload_documents(jsonl_file)  # type: ignore[attr-defined]

    assert parsed_text == [
        {
            "title": "notes",
            "source_type": "upload",
            "source_name": "notes.txt",
            "text": "Hello knowledge base",
            "metadata": {},
        }
    ]
    assert [item["title"] for item in parsed_jsonl] == ["Doc A", "Doc B"]
    assert [item["text"] for item in parsed_jsonl] == ["Alpha", "Beta"]


def test_delete_knowledge_base_rejects_bound_deployments(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management.context_repo,
        "get_knowledge_base",
        lambda _db, _knowledge_base_id: {"id": "kb-primary", "index_name": "kb_product_docs", "backing_provider_key": "weaviate_local"},
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "count_deployment_bindings_for_knowledge_base",
        lambda _db, *, knowledge_base_id: 2,
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management.delete_knowledge_base(
            "ignored",
            config=object(),  # type: ignore[arg-type]
            knowledge_base_id="kb-primary",
        )

    assert exc_info.value.code == "knowledge_base_in_use"


def test_resync_knowledge_base_rebuilds_documents_and_updates_sync_state(monkeypatch: pytest.MonkeyPatch):
    sync_events: list[tuple[str, str]] = []
    upserted_chunks: list[tuple[str, int]] = []

    monkeypatch.setattr(
        context_management.context_repo,
        "get_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "slug": "product-docs",
            "display_name": "Product Docs",
            "index_name": "kb_product_docs",
            "backing_provider_key": "weaviate_local",
            "lifecycle_state": "active",
            "sync_status": "ready",
            "schema_json": {},
        },
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "list_documents",
        lambda _db, *, knowledge_base_id: [
            {
                "id": "doc-1",
                "knowledge_base_id": knowledge_base_id,
                "title": "Overview",
                "source_type": "manual",
                "source_name": "Manual",
                "uri": None,
                "text": "Alpha\n\nBeta",
                "metadata_json": {},
                "chunk_count": 1,
            }
        ],
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "mark_knowledge_base_syncing",
        lambda _db, *, knowledge_base_id, **_kwargs: sync_events.append((knowledge_base_id, "syncing")) or {"id": knowledge_base_id},
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "set_knowledge_base_sync_result",
        lambda _db, *, knowledge_base_id, sync_status, last_sync_summary, **_kwargs: sync_events.append((knowledge_base_id, sync_status)) or {
            "id": knowledge_base_id,
            "slug": "product-docs",
            "display_name": "Product Docs",
            "description": "docs",
            "index_name": "kb_product_docs",
            "backing_provider_key": "weaviate_local",
            "lifecycle_state": "active",
            "sync_status": sync_status,
            "schema_json": {},
            "document_count": 1,
            "last_sync_summary": last_sync_summary,
        },
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "set_document_chunk_count",
        lambda _db, *, document_id, chunk_count, **_kwargs: {
            "id": document_id,
            "knowledge_base_id": "kb-primary",
            "title": "Overview",
            "source_type": "manual",
            "source_name": "Manual",
            "uri": None,
            "text": "Alpha\n\nBeta",
            "metadata_json": {},
            "chunk_count": chunk_count,
        },
    )
    monkeypatch.setattr(context_management, "_refresh_document_count", lambda *_args, **_kwargs: None)

    class _Adapter:
        def delete_index(self, *, index_name: str):
            return {"index": {"name": index_name, "deleted": True}}

        def ensure_index(self, *, index_name: str, schema: dict[str, object]):
            return {"index": {"name": index_name, "status": "ready", "schema": schema}}

        def upsert(self, *, index_name: str, documents: list[dict[str, object]]):
            upserted_chunks.append((index_name, len(documents)))
            return {"index": index_name, "count": len(documents)}

    monkeypatch.setattr(context_management, "_resolve_knowledge_base_vector_adapter", lambda *_args, **_kwargs: _Adapter())

    payload = context_management.resync_knowledge_base(
        "ignored",
        config=object(),  # type: ignore[arg-type]
        knowledge_base_id="kb-primary",
        updated_by_user_id=1,
    )

    assert sync_events == [("kb-primary", "syncing"), ("kb-primary", "ready")]
    assert upserted_chunks == [("kb_product_docs", 1)]
    assert payload["sync_status"] == "ready"


def test_update_knowledge_base_rejects_archiving_when_bound(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management.context_repo,
        "get_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "slug": "product-docs",
            "display_name": "Product Docs",
            "description": "docs",
            "index_name": "kb_product_docs",
            "backing_provider_key": "weaviate_local",
            "lifecycle_state": "active",
            "sync_status": "ready",
            "schema_json": {},
        },
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "count_deployment_bindings_for_knowledge_base",
        lambda _db, *, knowledge_base_id: 1,
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management.update_knowledge_base(
            "ignored",
            knowledge_base_id="kb-primary",
            payload={
                "slug": "product-docs",
                "display_name": "Product Docs",
                "description": "docs",
                "lifecycle_state": "archived",
            },
            updated_by_user_id=1,
        )

    assert exc_info.value.code == "knowledge_base_in_use"


def test_list_active_runtime_knowledge_bases_excludes_non_ready_bindings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management.context_repo,
        "get_knowledge_bases",
        lambda _db, _ids: [
            {
                "id": "kb-ready",
                "lifecycle_state": "active",
                "sync_status": "ready",
            },
            {
                "id": "kb-archived",
                "lifecycle_state": "archived",
                "sync_status": "ready",
            },
        ],
    )

    payload = context_management.list_active_runtime_knowledge_bases(
        {
            "capabilities": {
                "vector_store": {
                    "resources": [
                        {
                            "id": "kb-ready",
                            "ref_type": "knowledge_base",
                            "knowledge_base_id": "kb-ready",
                            "provider_resource_id": "kb_ready",
                            "display_name": "Ready KB",
                            "metadata": {"slug": "ready-kb", "index_name": "kb_ready"},
                        },
                        {
                            "id": "kb-archived",
                            "ref_type": "knowledge_base",
                            "knowledge_base_id": "kb-archived",
                            "provider_resource_id": "kb_archived",
                            "display_name": "Archived KB",
                            "metadata": {"slug": "archived-kb", "index_name": "kb_archived"},
                        },
                    ],
                    "default_resource_id": "kb-archived",
                    "resource_policy": {"selection_mode": "explicit"},
                }
            }
        },
        database_url="ignored",
    )

    assert [item["id"] for item in payload["knowledge_bases"]] == ["kb-ready"]
    assert payload["default_knowledge_base_id"] == "kb-ready"


def test_query_knowledge_base_uses_active_runtime_embeddings_and_vector_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management.context_repo,
        "get_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "slug": "product-docs",
            "display_name": "Product Docs",
            "description": "docs",
            "index_name": "kb_product_docs",
            "backing_provider_key": "weaviate_local",
            "lifecycle_state": "active",
            "sync_status": "ready",
            "schema_json": {},
        },
    )
    monkeypatch.setattr(
        "app.services.embeddings_service.embed_text_inputs",
        lambda _db, _config, texts: {"embeddings": [[0.1, 0.2]], "count": len(texts), "dimension": 2},
    )

    class _Binding:
        provider_key = "weaviate_local"

    class _Adapter:
        binding = _Binding()

        def query(self, *, index_name: str, query_text, embedding, top_k: int, filters: dict[str, object]):
            assert query_text is None
            assert embedding == [0.1, 0.2]
            assert top_k == 3
            assert filters == {}
            return {
                "index": index_name,
                "results": [
                    {
                        "id": "doc-1",
                        "text": "Alpha beta gamma",
                        "metadata": {"title": "Overview", "uri": "https://example.com/overview", "source_type": "manual"},
                        "score": 0.91,
                        "score_kind": "similarity",
                    }
                ],
            }

    monkeypatch.setattr("app.services.platform_service.resolve_vector_store_adapter", lambda _db, _config: _Adapter())

    payload = context_management.query_knowledge_base(
        "ignored",
        config=object(),  # type: ignore[arg-type]
        knowledge_base_id="kb-primary",
        payload={"query_text": "hello", "top_k": 3},
    )

    assert payload["retrieval"] == {"index": "kb_product_docs", "result_count": 1, "top_k": 3}
    assert payload["results"][0]["title"] == "Overview"
