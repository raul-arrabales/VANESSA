from __future__ import annotations

from typing import Any

from app.services.context_management_retrieval_types import (
    KnowledgeBaseRankedRetrievalResult,
    KnowledgeBaseRetrievalBranchResult,
    KnowledgeBaseRetrievalRelevanceComponents,
)


def make_branch_result(
    *,
    result_id: str = "doc-1#0",
    text: str = "retrieved chunk text",
    metadata: dict[str, Any] | None = None,
    score: float = 0.5,
    score_kind: str = "similarity",
) -> KnowledgeBaseRetrievalBranchResult:
    return KnowledgeBaseRetrievalBranchResult(
        id=result_id,
        text=text,
        metadata=metadata or {"title": "Architecture Overview", "document_id": "doc-1", "chunk_index": 0},
        score=score,
        score_kind=score_kind,
    )


def make_ranked_result(
    *,
    result_id: str = "doc-1#0",
    text: str = "retrieved chunk text",
    metadata: dict[str, Any] | None = None,
    relevance_score: float = 0.5,
    relevance_kind: str = "similarity",
    semantic_score: float | None = None,
    keyword_score: float | None = None,
) -> KnowledgeBaseRankedRetrievalResult:
    relevance_components = None
    if semantic_score is not None or keyword_score is not None:
        relevance_components = KnowledgeBaseRetrievalRelevanceComponents(
            semantic_score=semantic_score,
            keyword_score=keyword_score,
        )
    return KnowledgeBaseRankedRetrievalResult(
        id=result_id,
        text=text,
        metadata=metadata or {"title": "Architecture Overview", "document_id": "doc-1", "chunk_index": 0},
        relevance_score=relevance_score,
        relevance_kind=relevance_kind,  # type: ignore[arg-type]
        relevance_components=relevance_components,
    )
