from __future__ import annotations

from typing import Any

from .context_management_retrieval_types import KnowledgeBaseRetrievalOptions
from .platform_types import PlatformControlPlaneError


def _normalize_query_text(value: Any) -> str:
    query_text = str(value or "").strip()
    if not query_text:
        raise PlatformControlPlaneError("invalid_query_text", "query_text must be a non-empty string", status_code=400)
    return query_text


def _normalize_top_k(value: Any) -> int:
    if value is None:
        return 5
    if isinstance(value, bool):
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400)
    try:
        top_k = int(value)
    except (TypeError, ValueError) as exc:
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400) from exc
    if top_k <= 0:
        raise PlatformControlPlaneError("invalid_top_k", "top_k must be a positive integer", status_code=400)
    return top_k


def _normalize_search_method(value: Any) -> str:
    normalized = str(value or "semantic").strip().lower() or "semantic"
    if normalized not in {"semantic", "keyword", "hybrid"}:
        raise PlatformControlPlaneError(
            "invalid_search_method",
            "search_method must be one of semantic, keyword, or hybrid",
            status_code=400,
        )
    return normalized


def _normalize_query_preprocessing(value: Any) -> str:
    normalized = str(value or "none").strip().lower() or "none"
    if normalized not in {"none", "normalize"}:
        raise PlatformControlPlaneError(
            "invalid_query_preprocessing",
            "query_preprocessing must be one of none or normalize",
            status_code=400,
        )
    return normalized


def _normalize_hybrid_alpha(value: Any) -> float:
    if value in {None, ""}:
        return 0.5
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise PlatformControlPlaneError(
            "invalid_hybrid_alpha",
            "hybrid_alpha must be a number between 0.0 and 1.0",
            status_code=400,
        ) from exc
    if normalized < 0.0 or normalized > 1.0:
        raise PlatformControlPlaneError(
            "invalid_hybrid_alpha",
            "hybrid_alpha must be between 0.0 and 1.0",
            status_code=400,
        )
    return normalized


def normalize_knowledge_base_retrieval_options(payload: dict[str, Any]) -> KnowledgeBaseRetrievalOptions:
    query_text = _normalize_query_text(payload.get("query_text"))
    top_k = _normalize_top_k(payload.get("top_k"))
    search_method = _normalize_search_method(payload.get("search_method"))
    query_preprocessing = _normalize_query_preprocessing(payload.get("query_preprocessing"))
    hybrid_alpha = _normalize_hybrid_alpha(payload.get("hybrid_alpha")) if search_method == "hybrid" else None
    return KnowledgeBaseRetrievalOptions(
        query_text=query_text,
        top_k=top_k,
        search_method=search_method,  # type: ignore[arg-type]
        query_preprocessing=query_preprocessing,  # type: ignore[arg-type]
        hybrid_alpha=hybrid_alpha,
    )
