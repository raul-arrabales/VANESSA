from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RetrievalSearchMethod = Literal["semantic", "keyword", "hybrid"]
RetrievalQueryPreprocessing = Literal["none", "normalize"]
RetrievalRelevanceKind = Literal["similarity", "keyword_score", "hybrid_score"]


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    index: str
    query: str
    top_k: int
    filters: dict[str, Any] = field(default_factory=dict)
    search_method: RetrievalSearchMethod = "semantic"
    query_preprocessing: RetrievalQueryPreprocessing = "none"
    hybrid_alpha: float | None = None


@dataclass(frozen=True, slots=True)
class RetrievalRelevanceComponents:
    semantic_score: float | None = None
    keyword_score: float | None = None


@dataclass(frozen=True, slots=True)
class RetrievalBranchResult:
    id: str
    text: str
    metadata: dict[str, Any]
    score: float
    score_kind: str


@dataclass(frozen=True, slots=True)
class RankedRetrievalResult:
    id: str
    text: str
    metadata: dict[str, Any]
    score: float
    score_kind: str
    relevance_score: float
    relevance_kind: RetrievalRelevanceKind
    relevance_components: RetrievalRelevanceComponents | None = None


@dataclass(frozen=True, slots=True)
class RetrievalCallMetadata:
    index: str
    query: str
    top_k: int
    search_method: RetrievalSearchMethod
    query_preprocessing: RetrievalQueryPreprocessing
    result_count: int
    hybrid_alpha: float | None = None
