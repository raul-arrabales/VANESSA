from __future__ import annotations

"""Agent-engine retrieval scoring and fusion helpers; canonical contract: docs/services/retrieval_contract.md."""

import unicodedata

from .types import (
    RankedRetrievalResult,
    RetrievalBranchResult,
    RetrievalQueryPreprocessing,
    RetrievalRelevanceComponents,
    RetrievalRelevanceKind,
)


def preprocess_retrieval_query_text(
    query_text: str,
    *,
    query_preprocessing: RetrievalQueryPreprocessing,
) -> str:
    if query_preprocessing != "normalize":
        return query_text
    decomposed = unicodedata.normalize("NFKD", query_text)
    without_diacritics = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = without_diacritics.lower()
    normalized_chars = [ch if ch.isalnum() or ch.isspace() else " " for ch in lowered]
    return " ".join("".join(normalized_chars).split())


def coerce_query_result_score(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_branch_result_relevance(
    result: RetrievalBranchResult,
    *,
    search_method: str,
) -> tuple[float, RetrievalRelevanceKind]:
    if search_method == "keyword":
        return result.score, "keyword_score"
    if result.score_kind == "distance":
        return 1.0 - result.score, "similarity"
    return result.score, "similarity"


def rank_branch_results(
    results: list[RetrievalBranchResult],
    *,
    search_method: str,
) -> list[RankedRetrievalResult]:
    ranked_results: list[RankedRetrievalResult] = []
    for result in results:
        relevance_score, relevance_kind = normalize_branch_result_relevance(result, search_method=search_method)
        ranked_results.append(
            RankedRetrievalResult(
                id=result.id,
                text=result.text,
                metadata=result.metadata,
                score=result.score,
                score_kind=result.score_kind,
                relevance_score=relevance_score,
                relevance_kind=relevance_kind,
            )
        )
    return sorted(ranked_results, key=lambda item: item.relevance_score, reverse=True)


def normalize_keyword_relevance_scores(results: list[RankedRetrievalResult]) -> dict[str, float]:
    if not results:
        return {}
    raw_scores = {result.id: result.relevance_score for result in results}
    min_score = min(raw_scores.values())
    max_score = max(raw_scores.values())
    if max_score == min_score:
        return {result_id: 1.0 for result_id in raw_scores}
    return {
        result_id: (score - min_score) / (max_score - min_score)
        for result_id, score in raw_scores.items()
    }


def calculate_hybrid_branch_top_k(top_k: int) -> int:
    return min(max(top_k * 3, 10), 50)


def fuse_hybrid_results(
    semantic_results: list[RankedRetrievalResult],
    keyword_results: list[RankedRetrievalResult],
    *,
    hybrid_alpha: float,
    top_k: int,
) -> list[RankedRetrievalResult]:
    semantic_scores = {result.id: result.relevance_score for result in semantic_results}
    keyword_scores = normalize_keyword_relevance_scores(keyword_results)
    semantic_by_id = {result.id: result for result in semantic_results}
    keyword_by_id = {result.id: result for result in keyword_results}
    fused_results: list[RankedRetrievalResult] = []
    ordered_ids = list(dict.fromkeys([*semantic_by_id.keys(), *keyword_by_id.keys()]))

    for result_id in ordered_ids:
        semantic_score = semantic_scores.get(result_id, 0.0)
        keyword_score = keyword_scores.get(result_id, 0.0)
        semantic_result = semantic_by_id.get(result_id)
        keyword_result = keyword_by_id.get(result_id)
        base_result = semantic_result or keyword_result
        if base_result is None:
            continue
        fused_results.append(
            RankedRetrievalResult(
                id=base_result.id,
                text=base_result.text,
                metadata=base_result.metadata,
                score=(hybrid_alpha * semantic_score) + ((1.0 - hybrid_alpha) * keyword_score),
                score_kind="hybrid_score",
                relevance_score=(hybrid_alpha * semantic_score) + ((1.0 - hybrid_alpha) * keyword_score),
                relevance_kind="hybrid_score",
                relevance_components=RetrievalRelevanceComponents(
                    semantic_score=semantic_score,
                    keyword_score=keyword_score,
                ),
            )
        )

    return sorted(fused_results, key=lambda item: item.relevance_score, reverse=True)[:top_k]
