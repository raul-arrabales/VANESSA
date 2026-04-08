from __future__ import annotations

from app.services import retrieval_result_projection


def test_serialize_retrieval_source_preserves_source_shape_and_normalized_relevance_fields():
    payload = retrieval_result_projection.serialize_retrieval_source(
        {
            "id": "doc-1#0",
            "text": "A long explanation about retrieval in VANESSA.",
            "metadata": {
                "title": "Architecture Overview",
                "uri": "https://example.com/architecture",
                "source_type": "doc",
            },
            "score": 0.92,
            "score_kind": "similarity",
            "relevance_score": 0.88,
            "relevance_kind": "hybrid_score",
            "relevance_components": {
                "semantic_score": 0.91,
                "keyword_score": 0.85,
                "ignored": 1.0,
            },
        }
    )

    assert payload == {
        "id": "doc-1#0",
        "title": "Architecture Overview",
        "snippet": "A long explanation about retrieval in VANESSA.",
        "uri": "https://example.com/architecture",
        "source_type": "doc",
        "metadata": {
            "title": "Architecture Overview",
            "uri": "https://example.com/architecture",
            "source_type": "doc",
        },
        "score": 0.92,
        "score_kind": "similarity",
        "relevance_score": 0.88,
        "relevance_kind": "hybrid_score",
        "relevance_components": {
            "semantic_score": 0.91,
            "keyword_score": 0.85,
        },
    }


def test_project_retrieval_call_serializes_sources_and_summary():
    sources, retrieval = retrieval_result_projection.project_retrieval_call(
        {
            "index": "kb_product_docs",
            "top_k": 5,
            "search_method": "hybrid",
            "query_preprocessing": "normalize",
            "hybrid_alpha": 0.65,
            "result_count": 1,
            "results": [
                {
                    "id": "doc-1#0",
                    "text": "Chunk text",
                    "metadata": {"title": "Product Docs"},
                    "score": 0.812,
                    "score_kind": "hybrid_score",
                    "relevance_score": 0.812,
                    "relevance_kind": "hybrid_score",
                }
            ],
        }
    )

    assert sources == [
        {
            "id": "doc-1#0",
            "title": "Product Docs",
            "snippet": "Chunk text",
            "uri": None,
            "source_type": None,
            "metadata": {"title": "Product Docs"},
            "score": 0.812,
            "score_kind": "hybrid_score",
            "relevance_score": 0.812,
            "relevance_kind": "hybrid_score",
        }
    ]
    assert retrieval == {
        "index": "kb_product_docs",
        "result_count": 1,
        "search_method": "hybrid",
        "query_preprocessing": "normalize",
        "top_k": 5,
        "hybrid_alpha": 0.65,
    }


def test_normalize_execution_retrieval_returns_empty_defaults_without_retrieval_calls():
    sources, retrieval = retrieval_result_projection.normalize_execution_retrieval(
        {"result": {"retrieval_calls": []}}
    )

    assert sources == []
    assert retrieval == {
        "index": "",
        "result_count": 0,
    }
