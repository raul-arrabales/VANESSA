from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

KnowledgeBaseRetrievalSearchMethod = Literal["semantic", "keyword", "hybrid"]
KnowledgeBaseRetrievalQueryPreprocessing = Literal["none", "normalize"]
KnowledgeBaseRetrievalRelevanceKind = Literal["similarity", "keyword_score", "hybrid_score"]


@dataclass(frozen=True, slots=True)
class KnowledgeBaseRetrievalOptions:
    query_text: str
    top_k: int
    search_method: KnowledgeBaseRetrievalSearchMethod
    query_preprocessing: KnowledgeBaseRetrievalQueryPreprocessing
    hybrid_alpha: float | None = None
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeBaseRetrievalRelevanceComponents:
    semantic_score: float | None = None
    keyword_score: float | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeBaseRetrievalBranchResult:
    id: str
    text: str
    metadata: dict[str, Any]
    score: float
    score_kind: str


@dataclass(frozen=True, slots=True)
class KnowledgeBaseRankedRetrievalResult:
    id: str
    text: str
    metadata: dict[str, Any]
    relevance_score: float
    relevance_kind: KnowledgeBaseRetrievalRelevanceKind
    relevance_components: KnowledgeBaseRetrievalRelevanceComponents | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeBaseRetrievalExecution:
    index: str
    results: list[KnowledgeBaseRankedRetrievalResult]
