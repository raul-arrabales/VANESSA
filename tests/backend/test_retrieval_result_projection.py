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


def test_project_retrieval_call_serializes_sources_summary_and_references():
    sources, retrieval, references = retrieval_result_projection.project_retrieval_call(
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
                    "metadata": {
                        "title": "Product Docs",
                        "source_path": "docs/product.md",
                        "source_name": "Product handbook",
                        "page_number": 2,
                    },
                    "score": 0.812,
                    "score_kind": "hybrid_score",
                    "relevance_score": 0.812,
                    "relevance_kind": "hybrid_score",
                },
                {
                    "id": "doc-1#1",
                    "text": "More chunk text",
                    "metadata": {
                        "title": "Product Docs",
                        "source_path": "docs/product.md",
                        "source_name": "Product handbook",
                        "pages": [3, 2],
                    },
                    "score": 0.712,
                    "score_kind": "hybrid_score",
                    "relevance_score": 0.712,
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
            "metadata": {
                "title": "Product Docs",
                "source_path": "docs/product.md",
                "source_name": "Product handbook",
                "page_number": 2,
            },
            "score": 0.812,
            "score_kind": "hybrid_score",
            "relevance_score": 0.812,
            "relevance_kind": "hybrid_score",
            "reference_id": "ref-1",
            "citation_label": "[1]",
        },
        {
            "id": "doc-1#1",
            "title": "Product Docs",
            "snippet": "More chunk text",
            "uri": None,
            "source_type": None,
            "metadata": {
                "title": "Product Docs",
                "source_path": "docs/product.md",
                "source_name": "Product handbook",
                "pages": [3, 2],
            },
            "score": 0.712,
            "score_kind": "hybrid_score",
            "relevance_score": 0.712,
            "relevance_kind": "hybrid_score",
            "reference_id": "ref-1",
            "citation_label": "[1]",
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
    assert references == [
        {
            "id": "ref-1",
            "citation_label": "[1]",
            "title": "Product Docs",
            "description": "Product handbook",
            "uri": None,
            "file_reference": "docs/product.md",
            "pages": [2, 3],
            "source_ids": ["doc-1#0", "doc-1#1"],
        }
    ]


def test_normalize_execution_retrieval_returns_empty_defaults_without_retrieval_calls():
    sources, retrieval, references = retrieval_result_projection.normalize_execution_retrieval(
        {"result": {"retrieval_calls": []}}
    )

    assert sources == []
    assert references == []
    assert retrieval == {
        "index": "",
        "result_count": 0,
    }


def test_build_retrieval_references_uses_uri_groups_and_page_ranges():
    references, source_lookup = retrieval_result_projection.build_retrieval_references(
        [
            {
                "id": "doc-a#0",
                "metadata": {
                    "title": "Architecture",
                    "uri": "file:///docs/architecture.pdf",
                    "description": "Architecture guide",
                    "page_start": 4,
                    "page_end": 5,
                },
            },
            {
                "id": "doc-b#0",
                "metadata": {
                    "title": "FAQ",
                    "source_filename": "faq.md",
                    "page_count": 12,
                },
            },
        ]
    )

    assert references == [
        {
            "id": "ref-1",
            "citation_label": "[1]",
            "title": "Architecture",
            "description": "Architecture guide",
            "uri": "file:///docs/architecture.pdf",
            "file_reference": "file:///docs/architecture.pdf",
            "pages": [4, 5],
            "source_ids": ["doc-a#0"],
        },
        {
            "id": "ref-2",
            "citation_label": "[2]",
            "title": "FAQ",
            "description": "FAQ",
            "uri": None,
            "file_reference": "faq.md",
            "pages": [],
            "source_ids": ["doc-b#0"],
        },
    ]
    assert source_lookup == {
        "doc-a#0": {"reference_id": "ref-1", "citation_label": "[1]"},
        "doc-b#0": {"reference_id": "ref-2", "citation_label": "[2]"},
    }
