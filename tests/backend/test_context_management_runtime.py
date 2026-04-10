from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import (
    context_management_retrieval_pipeline,
    context_management_runtime,
    context_management_vectorization,
    platform_service,
)
from app.services.platform_types import PlatformControlPlaneError


def test_query_knowledge_base_rejects_active_provider_instance_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        context_management_retrieval_pipeline,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: {"embeddings": [[0.1, 0.2]]},
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-9", provider_key="qdrant_local"),
            query=lambda **_query_kwargs: {"index": "kb_product_docs", "results": []},
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(
                provider_instance_id="embedding-provider-1",
                provider_key="openai_compatible_cloud_embeddings",
                default_resource={"provider_resource_id": "text-embedding-3-small"},
            ),
        ),
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_runtime.query_knowledge_base(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            payload={"query_text": "hello"},
        )

    assert exc_info.value.code == "knowledge_base_provider_mismatch"
    assert exc_info.value.details == {
        "knowledge_base_id": "kb-primary",
        "knowledge_base_provider_instance_id": "provider-2",
        "active_provider_instance_id": "provider-9",
        "knowledge_base_provider_key": "weaviate_local",
        "active_provider_key": "qdrant_local",
    }


def test_query_knowledge_base_rejects_self_provided_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "self_provided",
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-2", provider_key="weaviate_local"),
            query=lambda **_query_kwargs: {"index": "kb_product_docs", "results": []},
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(
                provider_instance_id="embedding-provider-1",
                provider_key="openai_compatible_cloud_embeddings",
                default_resource={"provider_resource_id": "text-embedding-3-small"},
            ),
        ),
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_runtime.query_knowledge_base(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            payload={"query_text": "hello"},
        )

    assert exc_info.value.code == "knowledge_base_self_provided_query_unsupported"


def test_query_knowledge_base_rejects_embeddings_target_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-2", provider_key="weaviate_local"),
            query=lambda **_query_kwargs: {"index": "kb_product_docs", "results": []},
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(
                provider_instance_id="embedding-provider-1",
                provider_key="openai_compatible_cloud_embeddings",
                default_resource={"provider_resource_id": "text-embedding-3-large"},
            ),
        ),
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_runtime.query_knowledge_base(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            payload={"query_text": "hello"},
        )

    assert exc_info.value.code == "knowledge_base_embeddings_resource_mismatch"


def test_query_knowledge_base_semantic_normalizes_similarity_orders_results_and_preserves_metadata(
    monkeypatch: pytest.MonkeyPatch,
):
    captured_query_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "schema_json": {
                "properties": [
                    {"name": "category", "data_type": "text"},
                    {"name": "page_count", "data_type": "int"},
                    {"name": "published", "data_type": "boolean"},
                ]
            },
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        context_management_retrieval_pipeline,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: {"embeddings": [[0.1, 0.2]]},
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-2", provider_key="weaviate_local"),
            query=lambda **_query_kwargs: captured_query_kwargs.update(_query_kwargs) or {
                "index": "kb_product_docs",
                "results": [
                    {
                        "id": "doc-2#0",
                        "text": "high similarity chunk text for the top match",
                        "metadata": {
                            "document_id": "doc-2",
                            "chunk_index": 0,
                            "title": "FAQ",
                            "source_type": "manual",
                            "category": "faq",
                            "published": True,
                        },
                        "score": 0.91,
                        "score_kind": "similarity",
                    },
                    {
                        "id": "doc-1#0",
                        "text": "retrieved chunk text",
                        "metadata": {
                            "document_id": "doc-1",
                            "chunk_index": 0,
                            "title": "Architecture Overview",
                            "source_type": "local_directory",
                            "source_name": "Docs folder",
                            "uri": "https://example.com/overview",
                            "category": "guide",
                            "published": True,
                        },
                        "score": 0.23,
                        "score_kind": "distance",
                    },
                ],
            },
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(
                provider_instance_id="embedding-provider-1",
                provider_key="openai_compatible_cloud_embeddings",
                default_resource={"provider_resource_id": "text-embedding-3-small"},
            ),
        ),
    )
    monkeypatch.setattr(
        context_management_runtime,
        "resolve_knowledge_base_tokenizer",
        lambda *_args, **_kwargs: SimpleNamespace(encode=lambda text: text.split()),
    )

    payload = context_management_runtime.query_knowledge_base(
        "postgresql://ignored",
        config=object(),
        knowledge_base_id="kb-primary",
        payload={
            "query_text": "hello",
            "top_k": 5,
            "filters": {
                "category": "guide",
                "page_count": 2,
                "published": True,
            },
        },
    )

    assert captured_query_kwargs["query_text"] is None
    assert captured_query_kwargs["embedding"] == [0.1, 0.2]
    assert captured_query_kwargs["filters"] == {
        "category": "guide",
        "page_count": 2,
        "published": True,
    }
    assert payload["retrieval"] == {
        "index": "kb_product_docs",
        "result_count": 2,
        "top_k": 5,
        "search_method": "semantic",
        "query_preprocessing": "none",
    }
    assert payload["results"] == [
        {
            "id": "doc-2#0",
            "title": "FAQ",
            "text": "high similarity chunk text for the top match",
            "uri": None,
            "source_type": "manual",
            "metadata": {
                "document_id": "doc-2",
                "chunk_index": 0,
                "title": "FAQ",
                "source_type": "manual",
                "category": "faq",
                "published": True,
            },
            "chunk_length_tokens": 8,
            "relevance_score": 0.91,
            "relevance_kind": "similarity",
        },
        {
            "id": "doc-1#0",
            "title": "Architecture Overview",
            "text": "retrieved chunk text",
            "uri": "https://example.com/overview",
            "source_type": "local_directory",
            "metadata": {
                "document_id": "doc-1",
                "chunk_index": 0,
                "title": "Architecture Overview",
                "source_type": "local_directory",
                "source_name": "Docs folder",
                "uri": "https://example.com/overview",
                "category": "guide",
                "published": True,
            },
            "chunk_length_tokens": 3,
            "relevance_score": 0.77,
            "relevance_kind": "similarity",
        },
    ]


def test_query_knowledge_base_keyword_skips_embeddings_and_returns_keyword_scores(monkeypatch: pytest.MonkeyPatch):
    captured_query_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "schema_json": {
                "properties": [
                    {"name": "category", "data_type": "text"},
                    {"name": "published", "data_type": "boolean"},
                ]
            },
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-2", provider_key="weaviate_local"),
            query=lambda **_query_kwargs: captured_query_kwargs.update(_query_kwargs) or {
                "index": "kb_product_docs",
                "results": [
                    {
                        "id": "doc-1#0",
                        "text": "keyword matched chunk",
                        "metadata": {
                            "document_id": "doc-1",
                            "chunk_index": 0,
                            "title": "Keyword match",
                        },
                        "score": 3.2,
                        "score_kind": "bm25",
                    }
                ],
            },
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: pytest.fail("keyword search should not resolve embeddings adapter"),
    )
    monkeypatch.setattr(
        context_management_retrieval_pipeline,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: pytest.fail("keyword search should not embed the query"),
    )
    monkeypatch.setattr(
        context_management_runtime,
        "resolve_knowledge_base_tokenizer",
        lambda *_args, **_kwargs: SimpleNamespace(encode=lambda text: text.split()),
    )

    payload = context_management_runtime.query_knowledge_base(
        "postgresql://ignored",
        config=object(),
        knowledge_base_id="kb-primary",
        payload={
            "query_text": "hello",
            "top_k": 5,
            "search_method": "keyword",
            "filters": {
                "category": "guide",
                "published": False,
            },
        },
    )

    assert captured_query_kwargs["query_text"] == "hello"
    assert captured_query_kwargs["embedding"] is None
    assert captured_query_kwargs["filters"] == {
        "category": "guide",
        "published": False,
    }
    assert payload["retrieval"] == {
        "index": "kb_product_docs",
        "result_count": 1,
        "top_k": 5,
        "search_method": "keyword",
        "query_preprocessing": "none",
    }
    assert payload["results"] == [
        {
            "id": "doc-1#0",
            "title": "Keyword match",
            "text": "keyword matched chunk",
            "uri": None,
            "source_type": None,
            "metadata": {
                "document_id": "doc-1",
                "chunk_index": 0,
                "title": "Keyword match",
            },
            "chunk_length_tokens": 3,
            "relevance_score": 3.2,
            "relevance_kind": "keyword_score",
        }
    ]


def test_query_knowledge_base_normalizes_query_text_when_preprocessing_is_enabled(monkeypatch: pytest.MonkeyPatch):
    captured_query_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-2", provider_key="weaviate_local"),
            query=lambda **_query_kwargs: captured_query_kwargs.update(_query_kwargs) or {"index": "kb_product_docs", "results": []},
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: pytest.fail("keyword search should not resolve embeddings adapter"),
    )
    monkeypatch.setattr(
        context_management_retrieval_pipeline,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: pytest.fail("keyword search should not embed the query"),
    )
    monkeypatch.setattr(
        context_management_runtime,
        "resolve_knowledge_base_tokenizer",
        lambda *_args, **_kwargs: SimpleNamespace(encode=lambda text: text.split()),
    )

    payload = context_management_runtime.query_knowledge_base(
        "postgresql://ignored",
        config=object(),
        knowledge_base_id="kb-primary",
        payload={
            "query_text": "  Raúl!!! & Co.  ",
            "top_k": 5,
            "search_method": "keyword",
            "query_preprocessing": "normalize",
        },
    )

    assert captured_query_kwargs["query_text"] == "raul co"
    assert payload["retrieval"] == {
        "index": "kb_product_docs",
        "result_count": 0,
        "top_k": 5,
        "search_method": "keyword",
        "query_preprocessing": "normalize",
    }


def test_query_knowledge_base_hybrid_fuses_branch_scores_and_returns_component_breakdown(
    monkeypatch: pytest.MonkeyPatch,
):
    captured_queries: list[dict[str, object]] = []
    embedded_texts: list[str] = []

    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "schema_json": {
                "properties": [
                    {"name": "category", "data_type": "text"},
                    {"name": "page_count", "data_type": "int"},
                ]
            },
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        context_management_retrieval_pipeline,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: embedded_texts.extend(_kwargs["texts"]) or {"embeddings": [[0.4, 0.6]]},
    )

    def _query(**query_kwargs):
        captured_queries.append(query_kwargs)
        if query_kwargs.get("embedding") is not None:
            return {
                "index": "kb_product_docs",
                "results": [
                    {
                        "id": "doc-1#0",
                        "text": "semantic branch result one",
                        "metadata": {"title": "Architecture Overview", "document_id": "doc-1", "chunk_index": 0},
                        "score": 0.95,
                        "score_kind": "similarity",
                    },
                    {
                        "id": "doc-2#0",
                        "text": "semantic branch result two",
                        "metadata": {"title": "FAQ", "document_id": "doc-2", "chunk_index": 0},
                        "score": 0.20,
                        "score_kind": "distance",
                    },
                ],
            }
        return {
            "index": "kb_product_docs",
            "results": [
                {
                    "id": "doc-2#0",
                    "text": "keyword branch result two",
                    "metadata": {"title": "FAQ", "document_id": "doc-2", "chunk_index": 0},
                    "score": 8.0,
                    "score_kind": "bm25",
                },
                {
                    "id": "doc-3#0",
                    "text": "keyword branch result three",
                    "metadata": {"title": "Operator Guide", "document_id": "doc-3", "chunk_index": 0},
                    "score": 5.0,
                    "score_kind": "bm25",
                },
                {
                    "id": "doc-4#0",
                    "text": "keyword branch result four",
                    "metadata": {"title": "Release Notes", "document_id": "doc-4", "chunk_index": 0},
                    "score": 2.0,
                    "score_kind": "bm25",
                },
            ],
        }

    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-2", provider_key="weaviate_local"),
            query=_query,
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(
                provider_instance_id="embedding-provider-1",
                provider_key="openai_compatible_cloud_embeddings",
                default_resource={"provider_resource_id": "text-embedding-3-small"},
            ),
        ),
    )
    monkeypatch.setattr(
        context_management_runtime,
        "resolve_knowledge_base_tokenizer",
        lambda *_args, **_kwargs: SimpleNamespace(encode=lambda text: text.split()),
    )

    payload = context_management_runtime.query_knowledge_base(
        "postgresql://ignored",
        config=object(),
        knowledge_base_id="kb-primary",
        payload={
            "query_text": "  Raúl!!!  ",
            "top_k": 4,
            "search_method": "hybrid",
            "query_preprocessing": "normalize",
            "filters": {
                "category": "guide",
                "page_count": 3,
            },
        },
    )

    assert embedded_texts == ["raul"]
    assert len(captured_queries) == 2
    assert captured_queries[0]["query_text"] is None
    assert captured_queries[0]["embedding"] == [0.4, 0.6]
    assert captured_queries[0]["top_k"] == 12
    assert captured_queries[0]["filters"] == {
        "category": "guide",
        "page_count": 3,
    }
    assert captured_queries[1]["query_text"] == "raul"
    assert captured_queries[1]["embedding"] is None
    assert captured_queries[1]["top_k"] == 12
    assert captured_queries[1]["filters"] == {
        "category": "guide",
        "page_count": 3,
    }
    assert payload["retrieval"] == {
        "index": "kb_product_docs",
        "result_count": 4,
        "top_k": 4,
        "search_method": "hybrid",
        "query_preprocessing": "normalize",
        "hybrid_alpha": 0.5,
    }
    assert payload["results"] == [
        {
            "id": "doc-2#0",
            "title": "FAQ",
            "text": "semantic branch result two",
            "uri": None,
            "source_type": None,
            "metadata": {"title": "FAQ", "document_id": "doc-2", "chunk_index": 0},
            "chunk_length_tokens": 4,
            "relevance_score": 0.9,
            "relevance_kind": "hybrid_score",
            "relevance_components": {
                "semantic_score": 0.8,
                "keyword_score": 1.0,
            },
        },
        {
            "id": "doc-1#0",
            "title": "Architecture Overview",
            "text": "semantic branch result one",
            "uri": None,
            "source_type": None,
            "metadata": {"title": "Architecture Overview", "document_id": "doc-1", "chunk_index": 0},
            "chunk_length_tokens": 4,
            "relevance_score": 0.475,
            "relevance_kind": "hybrid_score",
            "relevance_components": {
                "semantic_score": 0.95,
                "keyword_score": 0.0,
            },
        },
        {
            "id": "doc-3#0",
            "title": "Operator Guide",
            "text": "keyword branch result three",
            "uri": None,
            "source_type": None,
            "metadata": {"title": "Operator Guide", "document_id": "doc-3", "chunk_index": 0},
            "chunk_length_tokens": 4,
            "relevance_score": 0.25,
            "relevance_kind": "hybrid_score",
            "relevance_components": {
                "semantic_score": 0.0,
                "keyword_score": 0.5,
            },
        },
        {
            "id": "doc-4#0",
            "title": "Release Notes",
            "text": "keyword branch result four",
            "uri": None,
            "source_type": None,
            "metadata": {"title": "Release Notes", "document_id": "doc-4", "chunk_index": 0},
            "chunk_length_tokens": 4,
            "relevance_score": 0.0,
            "relevance_kind": "hybrid_score",
            "relevance_components": {
                "semantic_score": 0.0,
                "keyword_score": 0.0,
            },
        },
    ]


def test_query_knowledge_base_hybrid_rejects_invalid_alpha(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_runtime.query_knowledge_base(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            payload={"query_text": "hello", "search_method": "hybrid", "hybrid_alpha": 1.5},
        )

    assert exc_info.value.code == "invalid_hybrid_alpha"
