from __future__ import annotations

from app.services import context_management_retrieval_scoring
from tests.backend.support.context_management_retrieval_fixtures import make_branch_result, make_ranked_result


def test_rank_branch_results_normalizes_distance_to_similarity():
    ranked_results = context_management_retrieval_scoring.rank_branch_results(
        [
            make_branch_result(result_id="doc-1#0", score=0.3, score_kind="distance"),
            make_branch_result(result_id="doc-2#0", score=0.9, score_kind="similarity"),
        ],
        search_method="semantic",
    )

    assert [(result.id, result.relevance_score, result.relevance_kind) for result in ranked_results] == [
        ("doc-2#0", 0.9, "similarity"),
        ("doc-1#0", 0.7, "similarity"),
    ]


def test_normalize_keyword_relevance_scores_returns_one_for_equal_scores():
    normalized_scores = context_management_retrieval_scoring.normalize_keyword_relevance_scores(
        [
            make_ranked_result(result_id="doc-1#0", relevance_score=3.0, relevance_kind="keyword_score"),
            make_ranked_result(result_id="doc-2#0", relevance_score=3.0, relevance_kind="keyword_score"),
        ]
    )

    assert normalized_scores == {
        "doc-1#0": 1.0,
        "doc-2#0": 1.0,
    }


def test_fuse_hybrid_results_merges_by_id_and_sorts_descending():
    fused_results = context_management_retrieval_scoring.fuse_hybrid_results(
        [
            make_ranked_result(result_id="doc-1#0", relevance_score=0.9, relevance_kind="similarity"),
            make_ranked_result(result_id="doc-2#0", relevance_score=0.6, relevance_kind="similarity"),
        ],
        [
            make_ranked_result(result_id="doc-2#0", relevance_score=8.0, relevance_kind="keyword_score"),
            make_ranked_result(result_id="doc-3#0", relevance_score=2.0, relevance_kind="keyword_score"),
        ],
        hybrid_alpha=0.5,
        top_k=3,
    )

    assert [
        (
            result.id,
            result.relevance_score,
            result.relevance_kind,
            result.relevance_components.semantic_score if result.relevance_components else None,
            result.relevance_components.keyword_score if result.relevance_components else None,
        )
        for result in fused_results
    ] == [
        ("doc-2#0", 0.8, "hybrid_score", 0.6, 1.0),
        ("doc-1#0", 0.45, "hybrid_score", 0.9, 0.0),
        ("doc-3#0", 0.0, "hybrid_score", 0.0, 0.0),
    ]
