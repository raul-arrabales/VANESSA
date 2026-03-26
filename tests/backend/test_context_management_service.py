from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

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
    pdf_file = FileStorage(stream=io.BytesIO(b"%PDF-test"), filename="guide.pdf")

    class _FakePdfPage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _FakePdfReader:
        def __init__(self, _stream: io.BytesIO):
            self.is_encrypted = False
            self.pages = [_FakePdfPage("Page one"), _FakePdfPage("Page two")]

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(context_management, "_get_pdf_reader_dependencies", lambda: (_FakePdfReader, (RuntimeError,)))

    try:
        parsed_text = context_management._parse_upload_documents(text_file)  # type: ignore[attr-defined]
        parsed_jsonl = context_management._parse_upload_documents(jsonl_file)  # type: ignore[attr-defined]
        parsed_pdf = context_management._parse_upload_documents(pdf_file)  # type: ignore[attr-defined]
    finally:
        monkeypatch.undo()

    assert parsed_text == [
        {
            "title": "notes",
            "source_type": "upload",
            "source_name": "notes.txt",
            "uri": None,
            "text": "Hello knowledge base",
            "metadata": {},
        }
    ]
    assert [item["title"] for item in parsed_jsonl] == ["Doc A", "Doc B"]
    assert [item["text"] for item in parsed_jsonl] == ["Alpha", "Beta"]
    assert parsed_pdf == [
        {
            "title": "guide",
            "source_type": "upload",
            "source_name": "guide.pdf",
            "uri": None,
            "text": "Page one\n\nPage two",
            "metadata": {"page_count": 2, "source_filename": "guide.pdf"},
        }
    ]


def test_parse_upload_documents_rejects_encrypted_or_textless_pdf(monkeypatch: pytest.MonkeyPatch):
    encrypted_file = FileStorage(stream=io.BytesIO(b"%PDF-encrypted"), filename="locked.pdf")
    textless_file = FileStorage(stream=io.BytesIO(b"%PDF-empty"), filename="scan.pdf")

    class _FakePdfPage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _FakePdfReader:
        def __init__(self, stream: io.BytesIO):
            marker = stream.read().decode("utf-8")
            self.is_encrypted = marker == "%PDF-encrypted"
            self.pages = [_FakePdfPage("")] if marker == "%PDF-empty" else [_FakePdfPage("hello")]

    monkeypatch.setattr(context_management, "_get_pdf_reader_dependencies", lambda: (_FakePdfReader, (RuntimeError,)))

    with pytest.raises(PlatformControlPlaneError) as encrypted_exc:
        context_management._parse_upload_documents(encrypted_file)  # type: ignore[attr-defined]

    with pytest.raises(PlatformControlPlaneError) as textless_exc:
        context_management._parse_upload_documents(textless_file)  # type: ignore[attr-defined]

    assert encrypted_exc.value.code == "invalid_upload_pdf"
    assert "encrypted" in encrypted_exc.value.message.lower()
    assert textless_exc.value.code == "invalid_upload_pdf"
    assert "ocr" in textless_exc.value.message.lower()


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


def test_create_knowledge_source_validates_allowlisted_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    root = tmp_path / "context_sources"
    root.mkdir()
    (root / "docs").mkdir()

    monkeypatch.setattr(
        context_management,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {"id": "kb-primary"},
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "create_knowledge_source",
        lambda _db, **kwargs: {"id": "source-1", "knowledge_base_id": "kb-primary", **kwargs, "last_sync_status": "idle"},
    )

    created = context_management.create_knowledge_source(
        "ignored",
        config=SimpleNamespace(context_source_roots=(str(root),)),
        knowledge_base_id="kb-primary",
        payload={"display_name": "Docs folder", "relative_path": "docs"},
        created_by_user_id=1,
    )

    assert created["relative_path"] == "docs"

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management.create_knowledge_source(
            "ignored",
            config=SimpleNamespace(context_source_roots=(str(root),)),
            knowledge_base_id="kb-primary",
            payload={"display_name": "Bad folder", "relative_path": "../outside"},
            created_by_user_id=1,
        )

    assert exc_info.value.code == "invalid_source_relative_path"


def test_sync_knowledge_source_reconciles_stable_documents_and_preserves_manual_documents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root = tmp_path / "context_sources"
    source_dir = root / "product_docs"
    source_dir.mkdir(parents=True)
    managed_file = source_dir / "overview.txt"
    managed_file.write_text("Alpha knowledge", encoding="utf-8")

    knowledge_base = {
        "id": "kb-primary",
        "slug": "product-docs",
        "display_name": "Product Docs",
        "description": "docs",
        "index_name": "kb_product_docs",
        "backing_provider_key": "weaviate_local",
        "lifecycle_state": "active",
        "sync_status": "ready",
        "schema_json": {},
    }
    source = {
        "id": "source-1",
        "knowledge_base_id": "kb-primary",
        "source_type": "local_directory",
        "display_name": "Docs folder",
        "relative_path": "product_docs",
        "include_globs": [],
        "exclude_globs": [],
        "lifecycle_state": "active",
        "last_sync_status": "idle",
    }
    documents: dict[str, dict[str, object]] = {
        "manual-1": {
            "id": "manual-1",
            "knowledge_base_id": "kb-primary",
            "title": "Manual Doc",
            "source_type": "manual",
            "source_name": "Manual",
            "uri": None,
            "text": "Manual text",
            "metadata_json": {},
            "chunk_count": 1,
            "source_id": None,
            "source_path": None,
            "source_document_key": None,
            "managed_by_source": False,
        }
    }
    sync_runs: list[dict[str, object]] = []

    monkeypatch.setattr(context_management, "_require_knowledge_base", lambda _db, _knowledge_base_id: knowledge_base)
    monkeypatch.setattr(
        context_management,
        "_require_knowledge_source",
        lambda _db, *, knowledge_base_id, source_id: source,
    )
    monkeypatch.setattr(context_management, "_mark_knowledge_base_syncing", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(
        context_management,
        "_mark_knowledge_base_sync_ready",
        lambda *_args, summary, **_kwargs: {**knowledge_base, "last_sync_summary": summary, "sync_status": "ready"},
    )
    monkeypatch.setattr(
        context_management,
        "_mark_knowledge_base_sync_error",
        lambda *_args, summary, **_kwargs: {**knowledge_base, "last_sync_summary": summary, "sync_status": "error"},
    )
    monkeypatch.setattr(context_management.context_repo, "mark_knowledge_source_syncing", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(
        context_management.context_repo,
        "set_knowledge_source_sync_result",
        lambda _db, *, last_sync_status, last_sync_error, **_kwargs: {
            **source,
            "last_sync_status": last_sync_status,
            "last_sync_error": last_sync_error,
        },
    )
    monkeypatch.setattr(context_management.context_repo, "get_document_by_source_key", lambda _db, *, source_document_key, **_kwargs: next(
        (dict(item) for item in documents.values() if item.get("source_document_key") == source_document_key),
        None,
    ))
    monkeypatch.setattr(
        context_management.context_repo,
        "create_document",
        lambda _db, **kwargs: documents.setdefault(
            str(kwargs["document_id"]),
            {
                "id": kwargs["document_id"],
                "knowledge_base_id": kwargs["knowledge_base_id"],
                "title": kwargs["title"],
                "source_type": kwargs["source_type"],
                "source_name": kwargs["source_name"],
                "uri": kwargs["uri"],
                "text": kwargs["text"],
                "metadata_json": kwargs["metadata_json"],
                "chunk_count": kwargs["chunk_count"],
                "source_id": kwargs["source_id"],
                "source_path": kwargs["source_path"],
                "source_document_key": kwargs["source_document_key"],
                "managed_by_source": kwargs["managed_by_source"],
            },
        ),
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "update_document",
        lambda _db, *, document_id, **kwargs: documents.__setitem__(
            document_id,
            {
                **documents[document_id],
                "title": kwargs["title"],
                "source_type": kwargs["source_type"],
                "source_name": kwargs["source_name"],
                "uri": kwargs["uri"],
                "text": kwargs["text"],
                "metadata_json": kwargs["metadata_json"],
                "chunk_count": kwargs["chunk_count"],
                "source_id": kwargs["source_id"],
                "source_path": kwargs["source_path"],
                "source_document_key": kwargs["source_document_key"],
                "managed_by_source": kwargs["managed_by_source"],
            },
        ) or documents[document_id],
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "delete_document",
        lambda _db, *, document_id, **_kwargs: documents.pop(document_id, None) is not None,
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "list_source_documents",
        lambda _db, *, source_id, **_kwargs: [dict(item) for item in documents.values() if item.get("source_id") == source_id],
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "list_documents",
        lambda _db, *, knowledge_base_id: [dict(item) for item in documents.values() if item.get("knowledge_base_id") == knowledge_base_id],
    )
    monkeypatch.setattr(context_management.context_repo, "set_knowledge_base_document_count", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(context_management, "_upsert_document_chunks", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management, "_delete_document_chunks", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management.context_repo,
        "create_sync_run",
        lambda _db, *, knowledge_base_id, source_id, created_by_user_id: (
            sync_runs.append(
                {
                    "id": f"run-{len(sync_runs) + 1}",
                    "knowledge_base_id": knowledge_base_id,
                    "source_id": source_id,
                    "status": "syncing",
                    "created_by_user_id": created_by_user_id,
                }
            )
            or sync_runs[-1]
        ),
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "finish_sync_run",
        lambda _db, *, run_id, status, scanned_file_count, changed_file_count, deleted_file_count, created_document_count, updated_document_count, deleted_document_count, error_summary: next(
            {
                **run,
                "status": status,
                "scanned_file_count": scanned_file_count,
                "changed_file_count": changed_file_count,
                "deleted_file_count": deleted_file_count,
                "created_document_count": created_document_count,
                "updated_document_count": updated_document_count,
                "deleted_document_count": deleted_document_count,
                "error_summary": error_summary,
            }
            for run in sync_runs
            if run["id"] == run_id
        ),
    )

    first = context_management.sync_knowledge_source(
        "ignored",
        config=SimpleNamespace(context_source_roots=(str(root),)),
        knowledge_base_id="kb-primary",
        source_id="source-1",
        updated_by_user_id=1,
    )

    managed_docs = [item for item in documents.values() if item.get("managed_by_source")]
    assert len(managed_docs) == 1
    assert first["sync_run"]["status"] == "ready"
    assert first["sync_run"]["scanned_file_count"] == 1
    assert first["sync_run"]["created_document_count"] == 1
    assert first["sync_run"]["changed_file_count"] == 1

    managed_file.write_text("Alpha knowledge updated", encoding="utf-8")

    second = context_management.sync_knowledge_source(
        "ignored",
        config=SimpleNamespace(context_source_roots=(str(root),)),
        knowledge_base_id="kb-primary",
        source_id="source-1",
        updated_by_user_id=1,
    )

    managed_docs = [item for item in documents.values() if item.get("managed_by_source")]
    assert len(managed_docs) == 1
    assert managed_docs[0]["text"] == "Alpha knowledge updated"
    assert second["sync_run"]["updated_document_count"] == 1

    managed_file.unlink()

    third = context_management.sync_knowledge_source(
        "ignored",
        config=SimpleNamespace(context_source_roots=(str(root),)),
        knowledge_base_id="kb-primary",
        source_id="source-1",
        updated_by_user_id=1,
    )

    managed_docs = [item for item in documents.values() if item.get("managed_by_source")]
    manual_docs = [item for item in documents.values() if not item.get("managed_by_source")]
    assert managed_docs == []
    assert len(manual_docs) == 1
    assert third["sync_run"]["deleted_document_count"] == 1
    assert third["sync_run"]["deleted_file_count"] == 1


def test_sync_knowledge_source_reconciles_pdf_documents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    root = tmp_path / "context_sources"
    source_dir = root / "product_docs"
    source_dir.mkdir(parents=True)
    managed_file = source_dir / "manual.pdf"
    managed_file.write_bytes(b"PDF_INITIAL")

    knowledge_base = {
        "id": "kb-primary",
        "slug": "product-docs",
        "display_name": "Product Docs",
        "description": "docs",
        "index_name": "kb_product_docs",
        "backing_provider_key": "weaviate_local",
        "lifecycle_state": "active",
        "sync_status": "ready",
        "schema_json": {},
    }
    source = {
        "id": "source-1",
        "knowledge_base_id": "kb-primary",
        "source_type": "local_directory",
        "display_name": "Docs folder",
        "relative_path": "product_docs",
        "include_globs": [],
        "exclude_globs": [],
        "lifecycle_state": "active",
        "last_sync_status": "idle",
    }
    documents: dict[str, dict[str, object]] = {}
    sync_runs: list[dict[str, object]] = []

    class _FakePdfPage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _FakePdfReader:
        def __init__(self, stream: io.BytesIO):
            marker = stream.read().decode("utf-8")
            self.is_encrypted = False
            if marker == "PDF_UPDATED":
                self.pages = [_FakePdfPage("Updated PDF text")]
            else:
                self.pages = [_FakePdfPage("Initial PDF text")]

    monkeypatch.setattr(context_management, "_get_pdf_reader_dependencies", lambda: (_FakePdfReader, (RuntimeError,)))
    monkeypatch.setattr(context_management, "_require_knowledge_base", lambda _db, _knowledge_base_id: knowledge_base)
    monkeypatch.setattr(
        context_management,
        "_require_knowledge_source",
        lambda _db, *, knowledge_base_id, source_id: source,
    )
    monkeypatch.setattr(context_management, "_mark_knowledge_base_syncing", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(
        context_management,
        "_mark_knowledge_base_sync_ready",
        lambda *_args, summary, **_kwargs: {**knowledge_base, "last_sync_summary": summary, "sync_status": "ready"},
    )
    monkeypatch.setattr(
        context_management,
        "_mark_knowledge_base_sync_error",
        lambda *_args, summary, **_kwargs: {**knowledge_base, "last_sync_summary": summary, "sync_status": "error"},
    )
    monkeypatch.setattr(context_management.context_repo, "mark_knowledge_source_syncing", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(
        context_management.context_repo,
        "set_knowledge_source_sync_result",
        lambda _db, *, last_sync_status, last_sync_error, **_kwargs: {
            **source,
            "last_sync_status": last_sync_status,
            "last_sync_error": last_sync_error,
        },
    )
    monkeypatch.setattr(context_management.context_repo, "get_document_by_source_key", lambda _db, *, source_document_key, **_kwargs: next(
        (dict(item) for item in documents.values() if item.get("source_document_key") == source_document_key),
        None,
    ))
    monkeypatch.setattr(
        context_management.context_repo,
        "create_document",
        lambda _db, **kwargs: documents.setdefault(
            str(kwargs["document_id"]),
            {
                "id": kwargs["document_id"],
                "knowledge_base_id": kwargs["knowledge_base_id"],
                "title": kwargs["title"],
                "source_type": kwargs["source_type"],
                "source_name": kwargs["source_name"],
                "uri": kwargs["uri"],
                "text": kwargs["text"],
                "metadata_json": kwargs["metadata_json"],
                "chunk_count": kwargs["chunk_count"],
                "source_id": kwargs["source_id"],
                "source_path": kwargs["source_path"],
                "source_document_key": kwargs["source_document_key"],
                "managed_by_source": kwargs["managed_by_source"],
            },
        ),
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "update_document",
        lambda _db, *, document_id, **kwargs: documents.__setitem__(
            document_id,
            {
                **documents[document_id],
                "title": kwargs["title"],
                "source_type": kwargs["source_type"],
                "source_name": kwargs["source_name"],
                "uri": kwargs["uri"],
                "text": kwargs["text"],
                "metadata_json": kwargs["metadata_json"],
                "chunk_count": kwargs["chunk_count"],
                "source_id": kwargs["source_id"],
                "source_path": kwargs["source_path"],
                "source_document_key": kwargs["source_document_key"],
                "managed_by_source": kwargs["managed_by_source"],
            },
        ) or documents[document_id],
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "delete_document",
        lambda _db, *, document_id, **_kwargs: documents.pop(document_id, None) is not None,
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "list_source_documents",
        lambda _db, *, source_id, **_kwargs: [dict(item) for item in documents.values() if item.get("source_id") == source_id],
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "list_documents",
        lambda _db, *, knowledge_base_id: [dict(item) for item in documents.values() if item.get("knowledge_base_id") == knowledge_base_id],
    )
    monkeypatch.setattr(context_management.context_repo, "set_knowledge_base_document_count", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(context_management, "_upsert_document_chunks", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management, "_delete_document_chunks", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management.context_repo,
        "create_sync_run",
        lambda _db, *, knowledge_base_id, source_id, created_by_user_id: (
            sync_runs.append(
                {
                    "id": f"run-{len(sync_runs) + 1}",
                    "knowledge_base_id": knowledge_base_id,
                    "source_id": source_id,
                    "status": "syncing",
                    "created_by_user_id": created_by_user_id,
                }
            )
            or sync_runs[-1]
        ),
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "finish_sync_run",
        lambda _db, *, run_id, status, scanned_file_count, changed_file_count, deleted_file_count, created_document_count, updated_document_count, deleted_document_count, error_summary: next(
            {
                **run,
                "status": status,
                "scanned_file_count": scanned_file_count,
                "changed_file_count": changed_file_count,
                "deleted_file_count": deleted_file_count,
                "created_document_count": created_document_count,
                "updated_document_count": updated_document_count,
                "deleted_document_count": deleted_document_count,
                "error_summary": error_summary,
            }
            for run in sync_runs
            if run["id"] == run_id
        ),
    )

    first = context_management.sync_knowledge_source(
        "ignored",
        config=SimpleNamespace(context_source_roots=(str(root),)),
        knowledge_base_id="kb-primary",
        source_id="source-1",
        updated_by_user_id=1,
    )

    managed_docs = [item for item in documents.values() if item.get("managed_by_source")]
    assert len(managed_docs) == 1
    assert managed_docs[0]["text"] == "Initial PDF text"
    assert managed_docs[0]["metadata_json"]["page_count"] == 1
    assert first["sync_run"]["created_document_count"] == 1

    managed_file.write_bytes(b"PDF_UPDATED")

    second = context_management.sync_knowledge_source(
        "ignored",
        config=SimpleNamespace(context_source_roots=(str(root),)),
        knowledge_base_id="kb-primary",
        source_id="source-1",
        updated_by_user_id=1,
    )

    managed_docs = [item for item in documents.values() if item.get("managed_by_source")]
    assert len(managed_docs) == 1
    assert managed_docs[0]["text"] == "Updated PDF text"
    assert second["sync_run"]["updated_document_count"] == 1

    managed_file.unlink()

    third = context_management.sync_knowledge_source(
        "ignored",
        config=SimpleNamespace(context_source_roots=(str(root),)),
        knowledge_base_id="kb-primary",
        source_id="source-1",
        updated_by_user_id=1,
    )

    assert [item for item in documents.values() if item.get("managed_by_source")] == []
    assert third["sync_run"]["deleted_document_count"] == 1
    assert third["sync_run"]["deleted_file_count"] == 1


def test_sync_knowledge_source_records_pdf_failure_summary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    root = tmp_path / "context_sources"
    source_dir = root / "product_docs"
    source_dir.mkdir(parents=True)
    (source_dir / "broken.pdf").write_bytes(b"PDF_BROKEN")

    knowledge_base = {
        "id": "kb-primary",
        "slug": "product-docs",
        "display_name": "Product Docs",
        "description": "docs",
        "index_name": "kb_product_docs",
        "backing_provider_key": "weaviate_local",
        "lifecycle_state": "active",
        "sync_status": "ready",
        "schema_json": {},
    }
    source = {
        "id": "source-1",
        "knowledge_base_id": "kb-primary",
        "source_type": "local_directory",
        "display_name": "Docs folder",
        "relative_path": "product_docs",
        "include_globs": [],
        "exclude_globs": [],
        "lifecycle_state": "active",
        "last_sync_status": "idle",
    }
    sync_runs: list[dict[str, object]] = []
    source_results: list[dict[str, object]] = []

    class _FakePdfReader:
        def __init__(self, _stream: io.BytesIO):
            self.is_encrypted = True
            self.pages = []

    monkeypatch.setattr(context_management, "_get_pdf_reader_dependencies", lambda: (_FakePdfReader, (RuntimeError,)))
    monkeypatch.setattr(context_management, "_require_knowledge_base", lambda _db, _knowledge_base_id: knowledge_base)
    monkeypatch.setattr(
        context_management,
        "_require_knowledge_source",
        lambda _db, *, knowledge_base_id, source_id: source,
    )
    monkeypatch.setattr(context_management, "_mark_knowledge_base_syncing", lambda *_args, **_kwargs: knowledge_base)
    monkeypatch.setattr(
        context_management,
        "_mark_knowledge_base_sync_error",
        lambda *_args, summary, **_kwargs: {**knowledge_base, "last_sync_summary": summary, "sync_status": "error"},
    )
    monkeypatch.setattr(context_management.context_repo, "mark_knowledge_source_syncing", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(
        context_management.context_repo,
        "set_knowledge_source_sync_result",
        lambda _db, *, last_sync_status, last_sync_error, **_kwargs: (
            source_results.append({"status": last_sync_status, "error": last_sync_error})
            or {
                **source,
                "last_sync_status": last_sync_status,
                "last_sync_error": last_sync_error,
            }
        ),
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "create_sync_run",
        lambda _db, *, knowledge_base_id, source_id, created_by_user_id: (
            sync_runs.append(
                {
                    "id": "run-1",
                    "knowledge_base_id": knowledge_base_id,
                    "source_id": source_id,
                    "status": "syncing",
                    "created_by_user_id": created_by_user_id,
                }
            )
            or sync_runs[-1]
        ),
    )
    monkeypatch.setattr(
        context_management.context_repo,
        "finish_sync_run",
        lambda _db, *, run_id, status, scanned_file_count, changed_file_count, deleted_file_count, created_document_count, updated_document_count, deleted_document_count, error_summary: {
            "id": run_id,
            "status": status,
            "scanned_file_count": scanned_file_count,
            "changed_file_count": changed_file_count,
            "deleted_file_count": deleted_file_count,
            "created_document_count": created_document_count,
            "updated_document_count": updated_document_count,
            "deleted_document_count": deleted_document_count,
            "error_summary": error_summary,
        },
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management.sync_knowledge_source(
            "ignored",
            config=SimpleNamespace(context_source_roots=(str(root),)),
            knowledge_base_id="kb-primary",
            source_id="source-1",
            updated_by_user_id=1,
        )

    assert exc_info.value.code == "invalid_source_pdf"
    assert "broken.pdf" in exc_info.value.message
    assert source_results[-1]["status"] == "error"
    assert "broken.pdf" in str(source_results[-1]["error"])
