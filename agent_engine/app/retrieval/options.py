from __future__ import annotations

"""Agent-engine retrieval request normalization; canonical contract: docs/services/retrieval_contract.md."""

from typing import Any

from .types import RetrievalRequest


def _normalize_query_text(value: Any) -> str:
    query_text = str(value or "").strip()
    if not query_text:
        raise ValueError("invalid_retrieval_input")
    return query_text


def _normalize_top_k(value: Any) -> int:
    if value is None:
        return 5
    if isinstance(value, bool):
        raise ValueError("invalid_retrieval_input")
    try:
        top_k = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_retrieval_input") from exc
    if top_k <= 0:
        raise ValueError("invalid_retrieval_input")
    return top_k


def _normalize_search_method(value: Any) -> str:
    normalized = str(value or "semantic").strip().lower() or "semantic"
    if normalized not in {"semantic", "keyword", "hybrid"}:
        raise ValueError("invalid_retrieval_input")
    return normalized


def _normalize_query_preprocessing(value: Any) -> str:
    normalized = str(value or "none").strip().lower() or "none"
    if normalized not in {"none", "normalize"}:
        raise ValueError("invalid_retrieval_input")
    return normalized


def _normalize_hybrid_alpha(value: Any) -> float:
    if value in {None, ""}:
        return 0.5
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_retrieval_input") from exc
    if normalized < 0.0 or normalized > 1.0:
        raise ValueError("invalid_retrieval_input")
    return normalized


def _normalize_filters(value: Any) -> dict[str, Any]:
    filters = {} if value is None else value
    if not isinstance(filters, dict):
        raise ValueError("invalid_retrieval_input")

    normalized_filters: dict[str, Any] = {}
    for key, filter_value in filters.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            raise ValueError("invalid_retrieval_input")
        if isinstance(filter_value, bool):
            normalized_filters[normalized_key] = filter_value
            continue
        if isinstance(filter_value, (int, float, str)):
            normalized_filters[normalized_key] = filter_value
            continue
        raise ValueError("invalid_retrieval_input")
    return normalized_filters


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    text_parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if str(part.get("type", "")).strip().lower() != "text":
            continue
        text = str(part.get("text", "")).strip()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


def derive_retrieval_query(execution_input: dict[str, Any]) -> str:
    prompt = str(execution_input.get("prompt", "")).strip()
    if prompt:
        return prompt

    raw_messages = execution_input.get("messages")
    if not isinstance(raw_messages, list):
        return ""
    for item in reversed(raw_messages):
        if not isinstance(item, dict):
            continue
        if str(item.get("role", "")).strip().lower() != "user":
            continue
        text = _message_text(item.get("content"))
        if text:
            return text
    return ""


def normalize_retrieval_request(execution_input: dict[str, Any]) -> RetrievalRequest | None:
    retrieval = execution_input.get("retrieval")
    if retrieval is None:
        return None
    if not isinstance(retrieval, dict):
        raise ValueError("invalid_retrieval_input")

    index_name = str(retrieval.get("index", "")).strip()
    if not index_name:
        raise ValueError("invalid_retrieval_input")

    raw_query = retrieval.get("query")
    if raw_query is not None:
        query_text = _normalize_query_text(raw_query)
    else:
        query_text = derive_retrieval_query(execution_input)
        if not query_text:
            raise ValueError("invalid_retrieval_input")

    top_k = _normalize_top_k(retrieval.get("top_k"))
    filters = _normalize_filters(retrieval.get("filters"))
    search_method = _normalize_search_method(retrieval.get("search_method"))
    query_preprocessing = _normalize_query_preprocessing(retrieval.get("query_preprocessing"))
    hybrid_alpha = _normalize_hybrid_alpha(retrieval.get("hybrid_alpha")) if search_method == "hybrid" else None

    return RetrievalRequest(
        index=index_name,
        query=query_text,
        top_k=top_k,
        filters=filters,
        search_method=search_method,  # type: ignore[arg-type]
        query_preprocessing=query_preprocessing,  # type: ignore[arg-type]
        hybrid_alpha=hybrid_alpha,
    )
