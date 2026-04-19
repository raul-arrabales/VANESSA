from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.retrieval import runtime as retrieval_runtime  # noqa: E402


def test_prepend_retrieval_context_uses_deduplicated_reference_citations():
    messages = [{"role": "user", "content": [{"type": "text", "text": "What is retrieval?"}]}]

    effective_messages = retrieval_runtime.prepend_retrieval_context(
        messages,
        retrieval_results=[
            {
                "id": "doc-1#0",
                "text": "First chunk",
                "metadata": {"title": "Guide", "source_path": "docs/guide.md"},
            },
            {
                "id": "doc-1#1",
                "text": "Second chunk",
                "metadata": {"title": "Guide", "source_path": "docs/guide.md"},
            },
            {
                "id": "doc-2#0",
                "text": "Other chunk",
                "metadata": {"title": "FAQ", "uri": "file:///docs/faq.pdf"},
            },
        ],
    )

    context_text = effective_messages[0]["content"][0]["text"]
    assert "bracketed numeric citations such as [1] or [1, 2]" in context_text
    assert context_text.count("Reference [1]") == 1
    assert context_text.count("Reference [2]") == 1
    assert "Chunk id=doc-1#0" in context_text
    assert "Chunk id=doc-1#1" in context_text
    assert "file=docs/guide.md" in context_text
    assert "file=file:///docs/faq.pdf" in context_text
    assert effective_messages[1:] == messages


def _runtime_snapshot() -> dict[str, object]:
    return {
        "deployment_profile": {"slug": "local-default"},
        "capabilities": {
            "embeddings": {"slug": "embeddings-local", "provider_key": "vllm_embeddings_local"},
            "vector_store": {"slug": "weaviate-local", "provider_key": "weaviate_local"},
        },
    }


def test_execute_retrieval_call_keyword_skips_embeddings_and_returns_canonical_scores(
    monkeypatch: pytest.MonkeyPatch,
):
    embeddings_called = {"value": False}

    monkeypatch.setattr(
        retrieval_runtime,
        "build_embeddings_runtime_client",
        lambda _runtime: type(
            "UnexpectedEmbeddingsClient",
            (),
            {"embed_texts": lambda self, **_kwargs: embeddings_called.__setitem__("value", True)},
        )(),
    )
    monkeypatch.setattr(
        retrieval_runtime,
        "build_vector_store_runtime_client",
        lambda _runtime: type(
            "FakeVectorClient",
            (),
            {
                "query": lambda self, **kwargs: {
                    "index": kwargs["index_name"],
                    "query": kwargs["query_text"],
                    "top_k": kwargs["top_k"],
                    "results": [
                        {
                            "id": "doc-1",
                            "text": "Keyword match text",
                            "metadata": {"title": "Keyword Doc"},
                            "score": 8.0,
                            "score_kind": "bm25",
                        }
                    ],
                }
            },
        )(),
    )

    embedding_call, retrieval_call, results = retrieval_runtime.execute_retrieval_call(
        retrieval_request=retrieval_runtime.RetrievalRequest(
            index="kb_product_docs",
            query="Raúl!!!",
            top_k=5,
            search_method="keyword",
            query_preprocessing="normalize",
        ),
        platform_runtime=_runtime_snapshot(),
    )

    assert embeddings_called["value"] is False
    assert embedding_call is None
    assert retrieval_call == {
        "provider_slug": "weaviate-local",
        "provider_key": "weaviate_local",
        "deployment_profile_slug": "local-default",
        "index": "kb_product_docs",
        "query": "raul",
        "top_k": 5,
        "search_method": "keyword",
        "query_preprocessing": "normalize",
        "result_count": 1,
        "results": [
            {
                "id": "doc-1",
                "text": "Keyword match text",
                "metadata": {"title": "Keyword Doc"},
                "score": 8.0,
                "score_kind": "bm25",
                "relevance_score": 8.0,
                "relevance_kind": "keyword_score",
            }
        ],
    }
    assert results == retrieval_call["results"]


def test_execute_retrieval_call_hybrid_fuses_semantic_and_keyword_results(
    monkeypatch: pytest.MonkeyPatch,
):
    seen_queries: list[tuple[str, int, str | None]] = []

    monkeypatch.setattr(
        retrieval_runtime,
        "build_embeddings_runtime_client",
        lambda _runtime: type(
            "FakeEmbeddingsClient",
            (),
            {
                "embed_texts": lambda self, **_kwargs: {
                    "embeddings": [[0.1, 0.2]],
                    "dimension": 2,
                    "status_code": 200,
                    "requested_model": "local-embeddings",
                }
            },
        )(),
    )

    def _query(self, **kwargs):
        seen_queries.append((kwargs["search_method"], kwargs["top_k"], kwargs["query_text"]))
        if kwargs["search_method"] == "semantic":
            return {
                "index": kwargs["index_name"],
                "results": [
                    {
                        "id": "doc-1",
                        "text": "semantic text",
                        "metadata": {"title": "Semantic Doc"},
                        "score": 0.9,
                        "score_kind": "similarity",
                    },
                    {
                        "id": "doc-2",
                        "text": "semantic only text",
                        "metadata": {"title": "Semantic Only"},
                        "score": 0.4,
                        "score_kind": "similarity",
                    },
                ],
            }
        return {
            "index": kwargs["index_name"],
            "results": [
                {
                    "id": "doc-1",
                    "text": "keyword text",
                    "metadata": {"title": "Semantic Doc"},
                    "score": 5.0,
                    "score_kind": "bm25",
                },
                {
                    "id": "doc-3",
                    "text": "keyword only text",
                    "metadata": {"title": "Keyword Only"},
                    "score": 1.0,
                    "score_kind": "bm25",
                },
            ],
        }

    monkeypatch.setattr(
        retrieval_runtime,
        "build_vector_store_runtime_client",
        lambda _runtime: type("FakeVectorClient", (), {"query": _query})(),
    )

    embedding_call, retrieval_call, results = retrieval_runtime.execute_retrieval_call(
        retrieval_request=retrieval_runtime.RetrievalRequest(
            index="kb_product_docs",
            query="Hybrid Query",
            top_k=2,
            search_method="hybrid",
            query_preprocessing="normalize",
            hybrid_alpha=0.5,
        ),
        platform_runtime=_runtime_snapshot(),
    )

    assert embedding_call is not None
    assert seen_queries == [
        ("semantic", 10, "hybrid query"),
        ("keyword", 10, "hybrid query"),
    ]
    assert retrieval_call["search_method"] == "hybrid"
    assert retrieval_call["query_preprocessing"] == "normalize"
    assert retrieval_call["hybrid_alpha"] == 0.5
    assert retrieval_call["result_count"] == 2
    assert results[0]["id"] == "doc-1"
    assert results[0]["score_kind"] == "hybrid_score"
    assert results[0]["relevance_kind"] == "hybrid_score"
    assert results[0]["relevance_components"] == {"semantic_score": 0.9, "keyword_score": 1.0}
    assert results[1]["id"] == "doc-2"
